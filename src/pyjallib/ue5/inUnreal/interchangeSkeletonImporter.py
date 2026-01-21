#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 스켈레톤 임포터 모듈

이 모듈은 Interchange Framework를 사용하여 FBX 파일에서 스켈레톤 에셋을 
UE5로 임포트하는 기능을 제공합니다.

의존성: 파이썬 표준 라이브러리 + unreal + pathUtils만 사용
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

import unreal

try:
    from . import pathUtils
    from .interchangeImporterBase import InterchangeImporterBase
    from .interchangePipelineSettings import InterchangePipelineSettings, InterchangePipelinePreset
except ImportError:
    import pathUtils
    from interchangeImporterBase import InterchangeImporterBase
    from interchangePipelineSettings import InterchangePipelineSettings, InterchangePipelinePreset


class InterchangeSkeletonImporter(InterchangeImporterBase):
    """
    Interchange Framework 기반 스켈레톤 임포터.
    
    FBX 파일에서 스켈레톤을 추출하여 UE5로 임포트합니다.
    외부 패키지 의존성 없이 파이썬 표준 라이브러리와 unreal 모듈만 사용합니다.
    """
    
    # 스켈레톤 에셋 접두사 (기본값)
    DEFAULT_SKELETON_PREFIX = "SK_"
    
    def __init__(self):
        """
        InterchangeSkeletonImporter 초기화.
        """
        super().__init__()
        self._pipelineSettings = InterchangePipelineSettings("Skeleton")
        unreal.log("[InterchangeSkeletonImporter] 초기화 완료")
    
    @property
    def asset_type(self) -> str:
        """에셋 타입을 반환합니다."""
        return "Skeleton"
    
    # ========================================================================
    # 단일 임포트 (동기)
    # ========================================================================
    
    def import_skeleton(
        self, 
        inFbxPath: str, 
        inDestinationPath: str,
        inAssetName: str = None, 
        inDescription: str = None
    ) -> Dict[str, Any]:
        """
        FBX 파일에서 스켈레톤을 임포트합니다. (동기 방식)
        
        Args:
            inFbxPath: FBX 파일의 절대 경로
            inDestinationPath: /Game/... 형식의 Content 목적지 경로
            inAssetName: 에셋 이름 (None이면 FBX 파일명 기반 자동 생성)
            inDescription: 소스 컨트롤 체크인 설명
            
        Returns:
            임포트 결과 딕셔너리
            
        Example:
            >>> importer = InterchangeSkeletonImporter()
            >>> result = importer.import_skeleton(
            ...     inFbxPath="D:/Export/FBX/Hero/SK_Hero.fbx",
            ...     inDestinationPath="/Game/Characters/Hero",
            ...     inAssetName="SK_Hero"  # 선택적
            ... )
        """
        unreal.log(f"[InterchangeSkeletonImporter] 스켈레톤 임포트 시작: {inFbxPath}")
        
        # FBX 파일 검증
        if not pathUtils.validate_fbx_file(inFbxPath):
            error_msg = f"FBX 파일 검증 실패: {inFbxPath}"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        
        # Content 경로 정규화 (절대 경로 → /Game/... 자동 변환)
        normalizedDestPath = pathUtils.normalize_content_path(inDestinationPath)
        if normalizedDestPath is None:
            error_msg = f"Content 경로 변환 실패: {inDestinationPath}"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        inDestinationPath = normalizedDestPath
        
        # 에셋 이름 결정 (제공되지 않으면 FBX 파일명에서 생성)
        if inAssetName is None:
            fbxFileName = Path(inFbxPath).stem
            # 스켈레톤 접두사가 없으면 추가
            if not fbxFileName.startswith(self.DEFAULT_SKELETON_PREFIX):
                inAssetName = f"{self.DEFAULT_SKELETON_PREFIX}{fbxFileName}"
            else:
                inAssetName = fbxFileName
        
        # 스켈레톤 이름 생성 (에셋 이름 기반)
        skeletonName = inAssetName
        
        # 임포트 준비 (디렉토리 생성 + 기존 파일 체크아웃)
        assetFullPath = self._prepare_asset_for_import(inDestinationPath, inAssetName)
        if assetFullPath is None:
            error_msg = f"임포트 준비 실패: {inDestinationPath}/{inAssetName}"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        
        skeletonFullPath = f"{inDestinationPath}/{skeletonName}"
        
        # 스켈레톤 파일도 체크아웃
        pathUtils.checkout_or_add_file(skeletonFullPath)
        
        # Interchange 임포트 실행
        sourceData = self._create_source_data(inFbxPath)
        pipelinePaths = self._pipelineSettings.get_pipeline_paths(InterchangePipelinePreset.SKELETON)
        importParams = self._create_import_params(inOverridePipelines=pipelinePaths)
        
        importedObjects = self._execute_import(inDestinationPath, sourceData, importParams)
        
        if len(importedObjects) == 0:
            error_msg = f"스켈레톤 임포트 실패 (임포트된 오브젝트 없음): {inFbxPath}"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        
        # 임포트된 스켈레탈 메시에서 스켈레톤 추출 및 이름 변경
        importedSkeletalMesh = None
        for asset in importedObjects:
            if isinstance(asset, unreal.SkeletalMesh):
                importedSkeletalMesh = asset
                break
        
        if importedSkeletalMesh is None:
            error_msg = f"임포트된 스켈레탈 메시를 찾을 수 없음: {inFbxPath}"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        
        importedSkeleton = importedSkeletalMesh.skeleton
        
        # 스켈레톤 이름 변경
        skeletonRenameData = unreal.AssetRenameData(importedSkeleton, inDestinationPath, skeletonName)
        unreal.AssetToolsHelpers.get_asset_tools().rename_assets([skeletonRenameData])
        
        # 소스 컨트롤 체크인
        skeletonSystemFullPath = unreal.SystemLibrary.get_system_path(importedSkeletalMesh.skeleton)
        importedObjectPaths = self.get_dirty_deps(skeletonSystemFullPath)
        importedObjectPaths.append(skeletonSystemFullPath)
        
        checkInDescription = f"Skeleton Imported by {inFbxPath} to {skeletonFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription
        
        if self.is_development_mode():
            unreal.log(f"[InterchangeSkeletonImporter] 개발 모드 - 스켈레톤 임포트 완료: {inFbxPath}")
        else:
            unreal.SourceControl.check_in_files(importedObjectPaths, checkInDescription, silent=True)
        
        unreal.log(f"[InterchangeSkeletonImporter] 스켈레톤 임포트 성공: {inFbxPath} -> {skeletonName}")
        
        return self._create_interchange_result_dict(
            inFbxPath, 
            inDestinationPath, 
            skeletonName, 
            True,
            importedObjects
        )
    
    # ========================================================================
    # 배치 임포트 (동기)
    # ========================================================================
    
    def import_skeletons(
        self, 
        inFbxPaths: List[str],
        inDestinationPaths: List[str],
        inAssetNames: List[str] = None,
        inDescription: str = None,
        inOnAssetDone: Optional[Callable[[unreal.Object], None]] = None,
        inOnBatchComplete: Optional[Callable[[List[unreal.Object]], None]] = None
    ) -> Dict[str, Any]:
        """
        여러 FBX 파일에서 스켈레톤을 배치 임포트합니다. (동기 방식)
        
        Args:
            inFbxPaths: FBX 파일 절대 경로 리스트
            inDestinationPaths: /Game/... 형식의 Content 목적지 경로 리스트
            inAssetNames: 에셋 이름 리스트 (None이면 FBX 파일명 기반 자동 생성)
            inDescription: 소스 컨트롤 체크인 설명
            inOnAssetDone: 개별 에셋 완료 콜백
            inOnBatchComplete: 전체 배치 완료 콜백
            
        Returns:
            배치 임포트 결과 딕셔너리
            
        Example:
            >>> importer = InterchangeSkeletonImporter()
            >>> result = importer.import_skeletons(
            ...     inFbxPaths=["D:/FBX/Hero.fbx", "D:/FBX/Villain.fbx"],
            ...     inDestinationPaths=["/Game/Characters/Hero", "/Game/Characters/Villain"],
            ...     inAssetNames=["SK_Hero", "SK_Villain"]
            ... )
        """
        unreal.log(f"[InterchangeSkeletonImporter] 스켈레톤 배치 임포트 시작: {len(inFbxPaths)}개 파일")
        
        # 입력 검증: FBX 경로와 목적지 경로 개수 일치
        if len(inFbxPaths) != len(inDestinationPaths):
            error_msg = "FBX 파일 경로와 목적지 경로의 개수가 일치하지 않습니다"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        
        # 입력 검증: 에셋 이름이 제공된 경우 개수 일치
        if inAssetNames is not None and len(inFbxPaths) != len(inAssetNames):
            error_msg = "FBX 파일과 에셋 이름의 개수가 일치하지 않습니다"
            unreal.log_error(f"[InterchangeSkeletonImporter] {error_msg}")
            raise ValueError(error_msg)
        
        results = []
        
        # 각 파일에 대해 순차적으로 임포트
        for index, fbxPath in enumerate(inFbxPaths):
            try:
                destPath = inDestinationPaths[index]
                assetName = inAssetNames[index] if inAssetNames else None
                
                result = self.import_skeleton(
                    inFbxPath=fbxPath, 
                    inDestinationPath=destPath, 
                    inAssetName=assetName, 
                    inDescription=inDescription
                )
                results.append(result)
                
                # 개별 에셋 완료 콜백 호출
                if inOnAssetDone and result.get("ImportedObjects"):
                    for obj in result["ImportedObjects"]:
                        inOnAssetDone(obj)
                
            except Exception as e:
                unreal.log_error(f"[InterchangeSkeletonImporter] 스켈레톤 임포트 실패: {fbxPath}, 에러: {e}")
                results.append({
                    "SourceFile": fbxPath,
                    "Success": False,
                    "Error": str(e)
                })
        
        # 배치 완료 콜백 호출
        if inOnBatchComplete:
            allObjects = []
            for result in results:
                if result.get("ImportedObjects"):
                    allObjects.extend(result["ImportedObjects"])
            inOnBatchComplete(allObjects)
        
        # 결과 집계
        successCount = len([r for r in results if r.get("Success", False)])
        failedCount = len(results) - successCount
        
        batchResult = {
            "TotalCount": len(inFbxPaths),
            "SuccessCount": successCount,
            "FailedCount": failedCount,
            "Results": results,
            "Errors": [r.get("Error") for r in results if r.get("Error")]
        }
        
        unreal.log(f"[InterchangeSkeletonImporter] 스켈레톤 배치 임포트 완료: 성공 {successCount}/{len(inFbxPaths)}")
        
        return batchResult
