#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 애니메이션 임포터 모듈

이 모듈은 Interchange Framework를 사용하여 FBX 파일에서 애니메이션 에셋을
UE5로 임포트하는 기능을 제공합니다.
"""

from typing import Optional, Dict, Any, List, Callable

import unreal

from .interchangeImporterBase import InterchangeImporterBase
from .interchangePipelineSettings import InterchangePipelineSettings, InterchangePipelinePreset
from ..logger import ue5_logger


class InterchangeAnimationImporter(InterchangeImporterBase):
    """
    Interchange Framework 기반 애니메이션 임포터.
    
    FBX 파일에서 애니메이션을 추출하여 UE5로 임포트합니다.
    기존 스켈레톤 참조가 필수입니다.
    """
    
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        """
        InterchangeAnimationImporter 초기화.
        
        Args:
            inContentRootPrefix: UE5 Content 디렉토리의 루트 경로
            inFbxRootPrefix: FBX 파일들이 위치한 루트 경로
        """
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "Animation")
        
        self._pipelineSettings = InterchangePipelineSettings("Animation")
        ue5_logger.info("InterchangeAnimationImporter 초기화 완료")
    
    @property
    def asset_type(self) -> str:
        """에셋 타입을 반환합니다."""
        return "Animation"
    
    # ========================================================================
    # 스켈레톤 검증
    # ========================================================================
    
    def _validate_skeleton(self, inFbxSkeletonPath: str) -> unreal.Skeleton:
        """
        스켈레톤 경로를 검증하고 스켈레톤 에셋을 반환합니다.
        
        Args:
            inFbxSkeletonPath: 스켈레톤 FBX 경로
            
        Returns:
            스켈레톤 에셋
            
        Raises:
            ValueError: 스켈레톤을 찾을 수 없는 경우
        """
        if inFbxSkeletonPath is None:
            error_msg = "애니메이션 임포트에는 스켈레톤이 필수입니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        skeletonPath = self.convert_fbx_path_to_skeleton_path(inFbxSkeletonPath)
        skeletonAssetData = unreal.EditorAssetLibrary.find_asset_data(skeletonPath)
        
        if not skeletonAssetData.is_valid():
            error_msg = f"스켈레톤 에셋을 찾을 수 없음: {skeletonPath}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        skeleton = skeletonAssetData.get_asset()
        ue5_logger.debug(f"스켈레톤 검증 완료: {skeleton.get_name()}")
        return skeleton
    
    # ========================================================================
    # 배치 디스크립션 생성 (기존 animationImporter와 동일)
    # ========================================================================
    
    def _create_batch_import_description(
        self, 
        inFbxFiles: List[str], 
        inAssetFullPaths: List[str]
    ) -> str:
        """
        배치 임포트용 간결한 디스크립션을 생성합니다.
        
        Args:
            inFbxFiles: 임포트된 FBX 파일 목록
            inAssetFullPaths: 임포트된 에셋 전체 경로 목록
            
        Returns:
            간결한 디스크립션 문자열
        """
        totalCount = len(inFbxFiles)
        
        if totalCount <= 3:
            # 3개 이하면 모든 경로 표시
            fbxList = ", ".join(inFbxFiles)
            assetList = ", ".join(inAssetFullPaths)
            return f"Animation Batch Import ({totalCount} files): {fbxList} -> {assetList}"
        else:
            # 3개 초과면 처음 3개만 표시하고 나머지는 개수로 표시
            fbxList = ", ".join(inFbxFiles[:3]) + f" ... (and {totalCount - 3} more)"
            assetList = ", ".join(inAssetFullPaths[:3]) + f" ... (and {totalCount - 3} more)"
            return f"Animation Batch Import ({totalCount} files): {fbxList} -> {assetList}"
    
    # ========================================================================
    # 단일 임포트 (동기)
    # ========================================================================
    
    def import_animation(
        self, 
        inFbxFile: str, 
        inFbxSkeletonPath: str,
        inAssetName: str = None, 
        inDescription: str = None
    ) -> Dict[str, Any]:
        """
        FBX 파일에서 애니메이션을 임포트합니다. (동기 방식)
        
        Args:
            inFbxFile: FBX 파일 경로
            inFbxSkeletonPath: 스켈레톤 FBX 파일 경로
            inAssetName: 에셋 이름 (None이면 FBX 파일명 사용)
            inDescription: 소스 컨트롤 체크인 설명
            
        Returns:
            임포트 결과 딕셔너리
        """
        ue5_logger.info(f"Interchange 애니메이션 임포트 시작: {inFbxFile}")
        
        # 스켈레톤 검증
        skeleton = self._validate_skeleton(inFbxSkeletonPath)
        
        # 경로 준비
        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"
        
        # 소스 컨트롤 체크아웃
        if unreal.Paths.file_exists(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)
        
        # Interchange 임포트 실행
        sourceData = self._create_source_data(inFbxFile)
        pipelinePaths = self._pipelineSettings.get_pipeline_paths(InterchangePipelinePreset.ANIMATION)
        importParams = self._create_import_params(inOverridePipelines=pipelinePaths)
        
        # 스켈레톤 설정을 파이프라인 속성 오버라이드로 처리
        self._pipelineSettings.set_property_override("skeleton", skeleton)
        
        importedObjects = self._execute_import(destinationPath, sourceData, importParams)
        
        if len(importedObjects) == 0:
            error_msg = f"애니메이션 임포트 실패: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 소스 컨트롤 체크인
        importedObjectPaths = []
        refObjectPaths = self.get_dirty_deps(assetFullPath)
        
        for obj in importedObjects:
            objPath = unreal.SystemLibrary.get_system_path(obj)
            if objPath:
                importedObjectPaths.append(objPath)
        
        allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))
        
        for assetPath in allImportRelatedPaths:
            unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)
        
        checkInDescription = f"Animation Imported by {inFbxFile} to {assetFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription
        
        if self.is_development_mode():
            ue5_logger.info(f"개발 모드 - 애니메이션 임포트 완료: {inFbxFile}")
        else:
            unreal.SourceControl.check_in_files(allImportRelatedPaths, checkInDescription, silent=True)
        
        ue5_logger.info(f"Interchange 애니메이션 임포트 성공: {inFbxFile} -> {assetName}")
        
        return self._create_interchange_result_dict(
            inFbxFile, 
            destinationPath, 
            assetName, 
            True,
            importedObjects
        )
    
    # ========================================================================
    # 배치 임포트 (비동기)
    # ========================================================================
    
    def import_animations(
        self, 
        inFbxFiles: List[str], 
        inFbxSkeletonPaths: List[str],
        inAssetNames: List[str] = None,
        inDescription: str = None,
        inOnAssetDone: Optional[Callable[[unreal.Object], None]] = None,
        inOnBatchComplete: Optional[Callable[[List[unreal.Object]], None]] = None
    ) -> Dict[str, Any]:
        """
        여러 FBX 파일에서 애니메이션을 배치 임포트합니다. (비동기 방식)
        
        Args:
            inFbxFiles: FBX 파일 경로 리스트
            inFbxSkeletonPaths: 스켈레톤 FBX 파일 경로 리스트
            inAssetNames: 에셋 이름 리스트 (None이면 FBX 파일명 사용)
            inDescription: 소스 컨트롤 체크인 설명
            inOnAssetDone: 개별 에셋 완료 콜백
            inOnBatchComplete: 전체 배치 완료 콜백
            
        Returns:
            배치 임포트 결과 딕셔너리
        """
        ue5_logger.info(f"Interchange 애니메이션 배치 임포트 시작: {len(inFbxFiles)}개 파일")
        
        # 입력 검증
        if len(inFbxFiles) != len(inFbxSkeletonPaths):
            error_msg = "FBX 파일과 스켈레톤 경로의 개수가 일치하지 않습니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        if inAssetNames is not None and len(inFbxFiles) != len(inAssetNames):
            error_msg = "FBX 파일과 에셋 이름의 개수가 일치하지 않습니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        results = []
        assetFullPaths = []
        batchImportedPaths = []
        
        # 각 파일에 대해 순차적으로 임포트 (동기 방식으로 처리)
        for index, fbxFile in enumerate(inFbxFiles):
            try:
                cusAssetName = inAssetNames[index] if inAssetNames else None
                skeletonPath = inFbxSkeletonPaths[index]
                
                result = self.import_animation(
                    fbxFile, 
                    skeletonPath, 
                    cusAssetName, 
                    inDescription=None  # 개별 체크인 생략, 배치 완료 후 일괄 처리
                )
                results.append(result)
                
                assetFullPath = f"{result['Path']}/{result['Name']}"
                assetFullPaths.append(assetFullPath)
                
                # 임포트된 객체 경로 수집
                for obj in result.get("ImportedObjects", []):
                    objPath = unreal.SystemLibrary.get_system_path(obj)
                    if objPath:
                        batchImportedPaths.append(objPath)
                
                # 콜백 호출
                if inOnAssetDone and result.get("ImportedObjects"):
                    for obj in result["ImportedObjects"]:
                        inOnAssetDone(obj)
                
            except Exception as e:
                ue5_logger.error(f"애니메이션 임포트 실패: {fbxFile}, 에러: {e}")
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
        
        # 배치 체크인 (개발 모드가 아닐 때)
        if not self.is_development_mode() and batchImportedPaths:
            batchImportedPaths = list(dict.fromkeys(batchImportedPaths))
            
            if inDescription is not None:
                checkInDescription = inDescription
            else:
                checkInDescription = self._create_batch_import_description(inFbxFiles, assetFullPaths)
            
            unreal.SourceControl.check_in_files(batchImportedPaths, checkInDescription, silent=True)
            ue5_logger.info(f"배치 임포트 체크인 완료: {len(batchImportedPaths)}개 파일")
        
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
        
        ue5_logger.info(f"Interchange 애니메이션 배치 임포트 완료: 성공 {successCount}/{len(inFbxFiles)}")
        
        return batchResult
