#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 스켈레톤 임포터 모듈

이 모듈은 Interchange Framework를 사용하여 FBX 파일에서 스켈레톤 에셋을 
UE5로 임포트하는 기능을 제공합니다.
"""

from typing import Optional, Dict, Any, List, Callable

import unreal

from .interchangeImporterBase import InterchangeImporterBase
from .interchangePipelineSettings import InterchangePipelineSettings, InterchangePipelinePreset
from ..logger import ue5_logger


class InterchangeSkeletonImporter(InterchangeImporterBase):
    """
    Interchange Framework 기반 스켈레톤 임포터.
    
    FBX 파일에서 스켈레톤을 추출하여 UE5로 임포트합니다.
    """
    
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        """
        InterchangeSkeletonImporter 초기화.
        
        Args:
            inContentRootPrefix: UE5 Content 디렉토리의 루트 경로
            inFbxRootPrefix: FBX 파일들이 위치한 루트 경로
        """
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "Skeleton")
        
        self._pipelineSettings = InterchangePipelineSettings("Skeleton")
        ue5_logger.info("InterchangeSkeletonImporter 초기화 완료")
    
    @property
    def asset_type(self) -> str:
        """에셋 타입을 반환합니다."""
        return "Skeleton"
    
    # ========================================================================
    # 단일 임포트 (동기)
    # ========================================================================
    
    def import_skeleton(
        self, 
        inFbxFile: str, 
        inAssetName: str = None, 
        inDescription: str = None
    ) -> Dict[str, Any]:
        """
        FBX 파일에서 스켈레톤을 임포트합니다. (동기 방식)
        
        Args:
            inFbxFile: FBX 파일 경로
            inAssetName: 에셋 이름 (None이면 FBX 파일명 사용)
            inDescription: 소스 컨트롤 체크인 설명
            
        Returns:
            임포트 결과 딕셔너리
        """
        ue5_logger.info(f"Interchange 스켈레톤 임포트 시작: {inFbxFile}")
        
        # 경로 준비
        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        
        # 스켈레톤 이름 생성 (기존 네이밍 로직 재사용)
        skeletonName = self.naming.replace_name_part(
            "AssetType", 
            assetName, 
            self.naming.get_name_part("AssetType").get_value_by_description("Skeleton")
        )
        
        assetFullPath = f"{destinationPath}/{assetName}"
        skeletonFullPath = f"{destinationPath}/{skeletonName}"
        
        # 소스 컨트롤 체크아웃
        if unreal.Paths.file_exists(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)
        if unreal.Paths.file_exists(skeletonFullPath):
            unreal.SourceControl.check_out_or_add_file(skeletonFullPath, silent=True)
        
        # Interchange 임포트 실행
        sourceData = self._create_source_data(inFbxFile)
        pipelinePaths = self._pipelineSettings.get_pipeline_paths(InterchangePipelinePreset.SKELETON)
        importParams = self._create_import_params(inOverridePipelines=pipelinePaths)
        
        importedObjects = self._execute_import(destinationPath, sourceData, importParams)
        
        if len(importedObjects) == 0:
            error_msg = f"스켈레톤 임포트 실패: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 임포트된 스켈레탈 메시에서 스켈레톤 추출 및 이름 변경
        importedSkeletalMesh = None
        for asset in importedObjects:
            if isinstance(asset, unreal.SkeletalMesh):
                importedSkeletalMesh = asset
                break
        
        if importedSkeletalMesh is None:
            error_msg = f"임포트된 스켈레탈 메시를 찾을 수 없음: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        importedSkeleton = importedSkeletalMesh.skeleton
        
        # 스켈레톤 이름 변경
        skeletonRenameData = unreal.AssetRenameData(importedSkeleton, destinationPath, skeletonName)
        unreal.AssetToolsHelpers.get_asset_tools().rename_assets([skeletonRenameData])
        
        # 소스 컨트롤 체크인
        skeletonSystemFullPath = unreal.SystemLibrary.get_system_path(importedSkeletalMesh.skeleton)
        importedObjectPaths = self.get_dirty_deps(skeletonSystemFullPath)
        importedObjectPaths.append(skeletonSystemFullPath)
        
        checkInDescription = f"Skeleton Imported by {inFbxFile} to {skeletonFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription
        
        if self.is_development_mode():
            ue5_logger.info(f"개발 모드 - 스켈레톤 임포트 완료: {inFbxFile}")
        else:
            unreal.SourceControl.check_in_files(importedObjectPaths, checkInDescription, silent=True)
        
        ue5_logger.info(f"Interchange 스켈레톤 임포트 성공: {inFbxFile} -> {skeletonName}")
        
        return self._create_interchange_result_dict(
            inFbxFile, 
            destinationPath, 
            skeletonName, 
            True,
            importedObjects
        )
    
    # ========================================================================
    # 배치 임포트 (비동기)
    # ========================================================================
    
    def import_skeletons(
        self, 
        inFbxFiles: List[str], 
        inAssetNames: List[str] = None,
        inDescription: str = None,
        inOnAssetDone: Optional[Callable[[unreal.Object], None]] = None,
        inOnBatchComplete: Optional[Callable[[List[unreal.Object]], None]] = None
    ) -> Dict[str, Any]:
        """
        여러 FBX 파일에서 스켈레톤을 배치 임포트합니다. (비동기 방식)
        
        Args:
            inFbxFiles: FBX 파일 경로 리스트
            inAssetNames: 에셋 이름 리스트 (None이면 FBX 파일명 사용)
            inDescription: 소스 컨트롤 체크인 설명
            inOnAssetDone: 개별 에셋 완료 콜백
            inOnBatchComplete: 전체 배치 완료 콜백
            
        Returns:
            배치 임포트 결과 딕셔너리
        """
        ue5_logger.info(f"Interchange 스켈레톤 배치 임포트 시작: {len(inFbxFiles)}개 파일")
        
        if inAssetNames is not None and len(inFbxFiles) != len(inAssetNames):
            error_msg = "FBX 파일과 에셋 이름의 개수가 일치하지 않습니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        results = []
        
        # 각 파일에 대해 순차적으로 임포트 (동기 방식으로 처리)
        for index, fbxFile in enumerate(inFbxFiles):
            try:
                cusAssetName = inAssetNames[index] if inAssetNames else None
                result = self.import_skeleton(fbxFile, cusAssetName, inDescription=None)
                results.append(result)
                
                # 콜백 호출
                if inOnAssetDone and result.get("ImportedObjects"):
                    for obj in result["ImportedObjects"]:
                        inOnAssetDone(obj)
                
            except Exception as e:
                ue5_logger.error(f"스켈레톤 임포트 실패: {fbxFile}, 에러: {e}")
                results.append({
                    "SourceFile": fbxFile,
                    "Success": False,
                    "Error": str(e)
                })
        
        # 배치 완료 콜백
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
            "TotalCount": len(inFbxFiles),
            "SuccessCount": successCount,
            "FailedCount": failedCount,
            "Results": results,
            "Errors": [r.get("Error") for r in results if r.get("Error")]
        }
        
        ue5_logger.info(f"Interchange 스켈레톤 배치 임포트 완료: 성공 {successCount}/{len(inFbxFiles)}")
        
        return batchResult
