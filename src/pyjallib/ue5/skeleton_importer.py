#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 스켈레톤 임포터 모듈

이 모듈은 FBX 파일에서 스켈레톤 에셋을 UE5로 임포트하는 기능을 제공합니다.
PyJalLib의 naming 모듈을 사용하여 에셋 이름을 자동 생성합니다.
"""

import unreal
from pathlib import Path
from typing import Optional, Dict, Any

# UE5 모듈 import
from .base_importer import BaseImporter
from .logger import ue5_logger
from .importer_settings import ImporterSettings

class SkeletonImporter(BaseImporter):
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "Skeleton")
        ue5_logger.info("SkeletonImporter 초기화 완료")
    
    @property
    def asset_type(self) -> str:
        return "Skeleton"
    
    def _create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """스켈레톤 임포트를 위한 태스크 생성 - 새 스켈레톤 생성"""
        ue5_logger.debug(f"스켈레톤 임포트 태스크 생성 시작: {inFbxFile}")
        
        importOptions = self.importerSettings.load_options()
        ue5_logger.debug("스켈레톤 임포트 옵션 로드 완료")
        
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
        
        ue5_logger.debug(f"스켈레톤 임포트 태스크 생성 완료: Destination={inDestinationPath}, AssetName={assetName}")
        return task
    
    def import_skeleton(self, inFbxFile: str, inAssetName: str = None):
        ue5_logger.info(f"스켈레톤 임포트 시작: {inFbxFile}")
        
        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        
        task = self._create_import_task(inFbxFile, destinationPath)
        # task의 destination_name을 실제 assetName으로 업데이트
        
        skeletonPrefix = self.naming.get_name_part("AssetType").get_value_by_description("Skeleton")
        print(f"assetName: {assetName}, skeletonPrefix: {skeletonPrefix}")
        newName = self.naming.replace_name_part("AssetType", assetName, skeletonPrefix)
        print(f"newName: {newName}")
        
        # task.destination_name = assetName
        
        # ue5_logger.info(f"스켈레톤 임포트 실행: {inFbxFile} -> {destinationPath}/{assetName}")
        # unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        
        # result = task.get_objects()
        # if len(result) == 0:
        #     error_msg = f"스켈레톤 임포트 실패: {inFbxFile}"
        #     ue5_logger.error(error_msg)
        #     raise ValueError(error_msg)
        
        # ue5_logger.info(f"스켈레톤 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        # return self._create_result_dict(inFbxFile, destinationPath, assetName, True)
        
        
        
        
        
        
        