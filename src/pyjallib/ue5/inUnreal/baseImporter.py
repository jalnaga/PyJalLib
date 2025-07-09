#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 베이스 임포터 모듈
UE5 에셋 임포트의 기본 기능을 제공하는 추상 클래스입니다.
"""

import json
import os
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from pyjallib.naming import Naming

import unreal

# UE5 모듈 import
from .importerSettings import ImporterSettings
from ..logger import ue5_logger

class BaseImporter(ABC):
    """모든 UE5 임포터의 베이스 클래스"""
    
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str, inPresetName: str):
        self.contentRootPrefix = inContentRootPrefix
        self.fbxRootPrefix = inFbxRootPrefix
        self.importerSettings = ImporterSettings(
            inContentRootPrefix=inContentRootPrefix, 
            inFbxRootPrefix=inFbxRootPrefix, 
            inPresetName=inPresetName
        )
        config_path = str(Path(__file__).parent.parent / "ConfigFiles" / "UE5NamingConfig.json")
        self.naming = Naming(configPath=config_path)
        ue5_logger.debug(f"BaseImporter 초기화: ContentRoot={inContentRootPrefix}, FbxRoot={inFbxRootPrefix}, Preset={inPresetName}")
    
    @property
    @abstractmethod
    def asset_type(self) -> str:
        """에셋 타입을 반환하는 추상 프로퍼티"""
        pass
    
    def convert_fbx_path_to_absolute_content_path(self, inFbxPath: str) -> str:
        """
        FBX 파일 경로를 UE5 Content 경로로 변환합니다.
        fbxRootPrefix가 inFbxPath의 prefix일 경우, contentRootPrefix로 치환합니다.
        Args:
            inFbxPath (str): 변환할 FBX 파일 경로
        Returns:
            str: 변환된 Content 경로
        """
        ue5_logger.debug(f"FBX 경로 변환 시작: {inFbxPath}")
        
        fbxRoot = Path(self.fbxRootPrefix).resolve()
        contentRoot = Path(self.contentRootPrefix).resolve()
        fbxPath = Path(inFbxPath).resolve()

        if str(fbxPath).startswith(str(fbxRoot)):
            relative_path = fbxPath.relative_to(fbxRoot)
            result_path = str(contentRoot / relative_path)
            ue5_logger.debug(f"경로 변환 완료: {inFbxPath} -> {result_path}")
            return result_path
        else:
            ue5_logger.error(f"입력 경로가 fbxRootPrefix로 시작하지 않습니다: {inFbxPath}")
            return ""
    
    def convert_fbx_path_to_content_path(self, inFbxPath: str) -> str:
        ue5_logger.debug(f"Content 경로 변환 시작: {inFbxPath}")
        
        absoluteContentPath = self.convert_fbx_path_to_absolute_content_path(inFbxPath)
        if absoluteContentPath == "":
            return ""
        
        # UE5 프로젝트의 Content 디렉토리 경로 가져오기
        contentPath = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
        
        absoluteContentPathObj = Path(absoluteContentPath)
        contentPathObj = Path(contentPath)
        
        # absoluteContentPath가 contentPath로 시작하는지 확인
        if str(absoluteContentPathObj).startswith(str(contentPathObj)):
            # contentPath 부분을 /Game/으로 직접 치환
            relativePath = absoluteContentPathObj.relative_to(contentPathObj)
            # pathlib을 사용하여 경로 정규화
            normalizedPath = Path(relativePath).as_posix()
            result_path = f"/Game/{normalizedPath}"
            
            # UE5 내장 함수를 사용하여 경로 정규화
            normalizedResultPath = unreal.Paths.normalize_directory_name(result_path)
            
            ue5_logger.debug(f"Content 경로 변환 완료: {inFbxPath} -> {normalizedResultPath}")
            return normalizedResultPath
        else:
            ue5_logger.error(f"절대 경로가 콘텐츠 디렉토리로 시작하지 않습니다: {absoluteContentPath}")
            return ""
        
    def convert_fbx_path_to_skeleton_path(self, inFbxPath: str) -> str:
        """
        FBX 파일 경로를 스켈레톤 경로로 변환합니다.
        fbxRootPrefix가 inFbxPath의 prefix일 경우, contentRootPrefix로 치환합니다.
        """
        skeletonPath = self.convert_fbx_path_to_content_path(inFbxPath)
        if skeletonPath == "":
            return ""
        
        destinationPath = unreal.Paths.get_path(skeletonPath)
        assetName = unreal.Paths.get_base_filename(skeletonPath)
        assetName = self.naming.replace_name_part("AssetType", assetName, self.naming.get_name_part("AssetType").get_value_by_description("Skeleton"))
        skeletonFullPath = f"{destinationPath}/{assetName}"
        return skeletonFullPath
    
    def _create_result_dict(self, inSourceFile: str, inPath: str, inName: str, inSuccess: bool = True):
        """결과 딕셔너리를 생성하는 공통 메서드"""
        result = {
            "SourceFile": inSourceFile,
            "Path": inPath,
            "Name": inName,
            "Type": self.asset_type,
            "Success": inSuccess
        }
        ue5_logger.debug(f"결과 딕셔너리 생성: {result}")
        return result
    
    def _prepare_import_paths(self, inFbxFile: str, inAssetName: str = None):
        """임포트 경로를 준비하는 공통 메서드"""
        ue5_logger.info(f"임포트 경로 준비 시작: {inFbxFile}")
        
        assetPath = self.convert_fbx_path_to_content_path(inFbxFile)
        if assetPath == "":
            error_msg = f"FBX 파일 경로가 올바르지 않습니다: {inFbxFile}"
            ue5_logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 경로에서 파일명 분리
        destinationPath = unreal.Paths.get_path(assetPath)
        assetName = unreal.Paths.get_base_filename(assetPath)
        
        # 에셋 이름 결정: 입력된 이름이 있으면 사용, 없으면 FBX 파일 이름에서 확장자 제거
        if inAssetName is not None:
            assetName = inAssetName

        ue5_logger.info(f"임포트 경로 정보: Destination={destinationPath}, AssetName={assetName}")

        if not unreal.Paths.directory_exists(destinationPath):
            ue5_logger.info(f"디렉토리 생성: {destinationPath}")
            unreal.EditorAssetLibrary.make_directory(destinationPath)
        
        if unreal.Paths.file_exists(assetPath):
            ue5_logger.info(f"기존 파일 체크아웃: {assetPath}")
            unreal.SourceControl.check_out_or_add_file(assetPath)
        
        return destinationPath, assetName
    
    @abstractmethod
    def create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """임포트 태스크를 생성하는 추상 메서드 - 각 임포터에서 구현"""
        pass 
    
    def get_dirty_deps(self, inAssetPath: str):
        returnList = []
        
        assetRegistry = unreal.AssetRegistryHelpers.get_asset_registry()
        assetData = unreal.EditorAssetLibrary.find_asset_data(inAssetPath)
        
        ue5_logger.error(f"assetData: {assetData.asset_name}")
        
        depPackages = assetRegistry.get_dependencies(
            assetData.package_name,  
            unreal.AssetRegistryDependencyOptions(
                include_soft_package_references=False,  # Soft reference 제외
                include_hard_package_references=True,   # Hard reference만
                include_searchable_names=False,
                include_soft_management_references=False,
                include_hard_management_references=False
            )
        )
        
        if depPackages is not None:
            for dep in depPackages:
                depPathStart = str(dep).split('/')[1]
                assetPathStart = str(assetData.package_name).split('/')[1]
                if depPathStart == assetPathStart:
                    if unreal.EditorAssetLibrary.save_asset(dep, only_if_is_dirty=True):
                        returnList.append(dep)
        
        return returnList