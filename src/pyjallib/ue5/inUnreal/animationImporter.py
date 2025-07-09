#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 애니메이션 임포터 모듈

이 모듈은 FBX 파일에서 애니메이션 에셋을 UE5로 임포트하는 기능을 제공합니다.
PyJalLib의 naming 모듈을 사용하여 에셋 이름을 자동 생성합니다.
"""

import unreal
from pathlib import Path
from typing import Optional, Dict, Any

# UE5 모듈 import
from .baseImporter import BaseImporter
from ..logger import ue5_logger
from .importerSettings import ImporterSettings

class AnimationImporter(BaseImporter):
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "Animation")
        ue5_logger.info("AnimationImporter 초기화 완료")
    
    @property
    def asset_type(self) -> str:
        return "Animation"
    
    def _create_batch_import_description(self, inFbxFiles: list[str], inAssetFullPaths: list[str]) -> str:
        """
        배치 임포트용 간결한 디스크립션 생성
        
        Args:
            inFbxFiles (list[str]): 임포트된 FBX 파일 목록
            inAssetFullPaths (list[str]): 임포트된 에셋 전체 경로 목록
            
        Returns:
            str: 간결한 디스크립션
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
    
    def create_import_task(self, inFbxFile: str, inDestinationPath: str, inFbxSkeletonPath: str):
        """애니메이션 임포트를 위한 태스크 생성 - 스켈레톤 필수 지정"""
        ue5_logger.debug(f"애니메이션 임포트 태스크 생성 시작: {inFbxFile}")
        
        importOptions = self.importerSettings.load_options()
        ue5_logger.debug("애니메이션 임포트 옵션 로드 완료")
        
        # 스켈레톤 필수 설정
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
        
        animSkeleton = skeletonAssetData.get_asset()
        importOptions.set_editor_property('skeleton', animSkeleton)
        ue5_logger.debug(f"스켈레톤 설정됨: {animSkeleton.get_name()}")
        
        # 에셋 이름 결정: FBX 파일 이름에서 확장자 제거
        assetName = Path(inFbxFile).stem
        
        task = unreal.AssetImportTask()
        task.automated = True
        task.destination_path = inDestinationPath
        task.filename = inFbxFile
        task.destination_name = assetName
        task.replace_existing = True
        task.save = True
        task.options = importOptions
        
        ue5_logger.debug(f"애니메이션 임포트 태스크 생성 완료: Destination={inDestinationPath}, AssetName={assetName}")
        return task
    
    def import_animation(self, inFbxFile: str, inFbxSkeletonPath: str, inAssetName: str = None, inDescription: str = None):
        ue5_logger.info(f"애니메이션 임포트 시작: {inFbxFile}")
        
        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"
        
        # 기존 에셋이 있는 경우 소스 컨트롤에서 체크아웃
        if unreal.Paths.file_exists(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)
        
        task = self.create_import_task(inFbxFile, destinationPath, inFbxSkeletonPath)
        
        ue5_logger.info(f"애니메이션 임포트 실행: {inFbxFile} -> {destinationPath}/{assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        
        result = task.get_objects()
        if len(result) == 0:
            error_msg = f"애니메이션 임포트 실패: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        importedObjectPaths = task.imported_object_paths
        refObjectPaths = self.get_dirty_deps(assetFullPath)
        
        allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))
        for assetPath in allImportRelatedPaths:
            unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)
        
        checkInDescription = f"Animation Imported by {inFbxFile} to {assetFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription
        
        # unreal.SourceControl.check_in_files(allImportRelatedPaths, checkInDescription, silent=True)
        
        ue5_logger.info(f"애니메이션 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        return self._create_result_dict(inFbxFile, destinationPath, assetName, True) 
    
    def import_animations(self, inFbxFiles: list[str], inFbxSkeletonPaths: list[str], inAssetNames: list[str] = None, inDescription: str = None):
        ue5_logger.info(f"애니메이션 임포트 시작: {inFbxFiles}")
        
        if len(inFbxFiles) != len(inFbxSkeletonPaths):
            error_msg = "애니메이션 임포트에는 파일과 스켈레톤이 같은 개수여야 합니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        if inAssetNames is not None and len(inFbxFiles) != len(inAssetNames):
            error_msg = "애니메이션 임포트에는 파일과 에셋 이름이 같은 개수여야 합니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        destinationPaths = []
        assetNames = []
        assetFullPaths = []
        tasks = []
        for index, fbxFile in enumerate(inFbxFiles):
            cusAssetName = None
            if inAssetNames is not None:
                cusAssetName = inAssetNames[index]
            destinationPath, assetName = self._prepare_import_paths(fbxFile, cusAssetName)
            
            destinationPaths.append(destinationPath)
            assetNames.append(assetName)
            assetFullPath = f"{destinationPath}/{assetName}"
            assetFullPaths.append(assetFullPath)
            
            if unreal.Paths.file_exists(assetFullPath):
                unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)
            
            task = self.create_import_task(fbxFile, destinationPath, inFbxSkeletonPaths[index])
            tasks.append(task)
        
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
        
        batchImportedAssetPaths = []
        for index, task in enumerate(tasks):
            result = task.get_objects()
            if len(result) == 0:
                error_msg = f"애니메이션 임포트 실패: {inFbxFiles[index]}"
                ue5_logger.error(error_msg)
                raise ValueError(error_msg)
            
            importedObjectPaths = task.imported_object_paths
            refObjectPaths = self.get_dirty_deps(assetFullPaths[index])
            
            allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))
            for assetPath in allImportRelatedPaths:
                unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)
                batchImportedAssetPaths.append(assetPath)
        
        batchImportedAssetPaths = list(dict.fromkeys(batchImportedAssetPaths))
            
        # 배치 임포트용 간결한 디스크립션 생성
        if inDescription is not None:
            checkInDescription = inDescription
        else:
            checkInDescription = self._create_batch_import_description(inFbxFiles, assetFullPaths)
            
        ue5_logger.info(f"퍼포스 디스크립션: {checkInDescription}")
        
        # unreal.SourceControl.check_in_files(batchImportedAssetPaths, checkInDescription, silent=True)
        
        ue5_logger.info(f"애니메이션 임포트 완료: {inFbxFiles}")