"""
UE5 스켈레톤 임포터 모듈

이 모듈은 FBX 파일에서 스켈레톤 에셋을 UE5로 임포트하는 기능을 제공합니다.
PyJalLib의 naming 모듈을 사용하여 에셋 이름을 자동 생성합니다.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

import unreal

# PyJalLib 모듈 import
from pyjallib import naming

# UE5 모듈 import
from .importer_settings import ImporterSettings

class SkeletonImporter:
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        self.importerSettings = ImporterSettings(inContentRootPrefix=inContentRootPrefix, inFbxRootPrefix=inFbxRootPrefix, inPresetName="Skeleton")
    
    def import_skeleton(self, inFbxFile: str):
        assetPath = self.importerSettings.convert_fbx_path_to_content_path(inFbxFile)
        if assetPath == "":
            raise ValueError(f"FBX 파일 경로가 올바르지 않습니다: {inFbxFile}")
        
        # Path 객체에서 파일 이름과 경로 분리
        assetPathObj = Path(assetPath)
        destinationPath = str(assetPathObj.parent)
        fileName = str(assetPathObj.stem)
        
        importOptions = self.importerSettings.load_options()
        
        task = unreal.AssetImportTask()
        task.automated = True
        task.destination_path = destinationPath
        task.filename = fileName
        task.replace_existing = True
        task.save = True
        task.options = importOptions
        
        taskResultDict = {
            "SourceFile": "",
            "Path": "",
            "Name": "",
            "Type": "",
            "Success": False
        }
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        
        result = task.get_objects()
        if len(result) == 0:
            taskResultDict["SourceFile"] = inFbxFile
            taskResultDict["Path"] = destinationPath
            taskResultDict["Name"] = fileName
            taskResultDict["Type"] = "Skeleton"
            taskResultDict["Success"] = False
            raise ValueError(f"스켈레톤 임포트 실패: {inFbxFile}")
        
        taskResultDict["SourceFile"] = inFbxFile
        taskResultDict["Path"] = destinationPath
        taskResultDict["Name"] = fileName
        taskResultDict["Type"] = "Skeleton"
        taskResultDict["Success"] = True
        
        return taskResultDict
        
        
        
        
        
        
        