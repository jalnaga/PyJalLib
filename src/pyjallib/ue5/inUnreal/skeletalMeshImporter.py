#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 스켈레탈 메쉬 임포터 모듈
UE5에서 스켈레탈 메쉬를 임포트하는 기능을 제공합니다.
"""

import unreal
from pathlib import Path
from typing import Optional, Dict, Any

from ..logger import ue5_logger
from .importerSettings import ImporterSettings

# UE5 모듈 import
from .baseImporter import BaseImporter

class SkeletalMeshImporter(BaseImporter):
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "SkeletalMesh")
        ue5_logger.info("SkeletalMeshImporter 초기화 완료")
    
    @property
    def asset_type(self) -> str:
        return "SkeletalMesh"
    
    def _create_import_task(self, inFbxFile: str, inDestinationPath: str, inFbxSkeletonPath: str):
        """스켈레탈 메시 임포트를 위한 태스크 생성 - 스켈레톤 필수 지정"""
        ue5_logger.debug(f"스켈레탈 메시 임포트 태스크 생성 시작: {inFbxFile}")
        
        importOptions = self.importerSettings.load_options()
        ue5_logger.debug("스켈레탈 메시 임포트 옵션 로드 완료")
        
        # 스켈레톤 필수 설정
        if inFbxSkeletonPath is None:
            error_msg = "스켈레탈 메시 임포트에는 스켈레톤이 필수입니다"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        skeletonPath = self.convert_fbx_path_to_skeleton_path(inFbxSkeletonPath)
        skeletonAssetData = unreal.EditorAssetLibrary.find_asset_data(skeletonPath)
        if not skeletonAssetData.is_valid():
            error_msg = f"스켈레톤 에셋을 찾을 수 없음: {skeletonPath}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        skeletalSkeleton = skeletonAssetData.get_asset()
        importOptions.set_editor_property('skeleton', skeletalSkeleton)
        ue5_logger.debug(f"스켈레톤 설정됨: {skeletalSkeleton.get_name()}")
        
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
        
        ue5_logger.debug(f"스켈레탈 메시 임포트 태스크 생성 완료: Destination={inDestinationPath}, AssetName={assetName}")
        return task
    
    def import_skeletal_mesh(self, inFbxFile: str, inFbxSkeletonPath: str, inAssetName: str = None, inDescription: str = None):
        ue5_logger.info(f"스켈레탈 메시 임포트 시작: {inFbxFile}")
        
        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"
        
        # 기존 에셋이 있는 경우 소스 컨트롤에서 체크아웃
        if unreal.Paths.file_exists(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)
        
        task = self._create_import_task(inFbxFile, destinationPath, inFbxSkeletonPath)
        
        ue5_logger.info(f"스켈레탈 메시 임포트 실행: {inFbxFile} -> {destinationPath}/{assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        
        result = task.get_objects()
        if len(result) == 0:
            error_msg = f"스켈레탈 메시 임포트 실패: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 임포트된 스켈레탈 메시 에셋의 시스템 경로 가져오기
        importedSkeletalMesh = None
        for asset in result:
            if isinstance(asset, unreal.SkeletalMesh):
                importedSkeletalMesh = asset
                break
        
        if importedSkeletalMesh is None:
            error_msg = f"스켈레탈 메시 에셋을 찾을 수 없음: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        skeletalMeshSystemFullPath = unreal.SystemLibrary.get_system_path(importedSkeletalMesh)
        
        checkInDescription = f"SkeletalMesh Imported by {inFbxFile} to {assetFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription
        
        # unreal.SourceControl.check_in_files([skeletalMeshSystemFullPath], checkInDescription, silent=True)
        
        ue5_logger.info(f"스켈레탈 메시 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        return self._create_result_dict(inFbxFile, destinationPath, assetName, True) 