#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
입력된 네이밍 규칙에 따라 경로를 생성하고, 윈도우즈용 폴더명을 안전하게 변환하는 기능을 제공하는 클래스.
"""

from pathlib import PureWindowsPath
import os
import re
from typing import Optional, Dict, Any, List

from pyjallib.naming import Naming
from pyjallib.namingConfig import NamingConfig


class NameToPath(Naming):
    """
    네이밍 규칙에 따라 경로를 생성하고, 폴더명을 안전하게 변환하는 기능을 제공하는 클래스.
    """
    def __init__(self, inputConfigPath: str, pathConfigPath: str, rootPath: str = None):
        """
        NameToPath 초기화
        
        :param inputConfigPath: 입력 이름 파싱용 설정 파일 경로
        :param pathConfigPath: 경로 생성용 설정 파일 경로  
        :param rootPath: 루트 경로 (옵션)
        """
        super().__init__()
        self.pathConfig = NamingConfig()
        self.pathConfig.load(pathConfigPath)
        
        # 루트 경로 설정 (pathAndFiles 의존성 제거)
        if rootPath is not None:
            self.rootPath = self._normalize_path(rootPath)
        else:
            self.rootPath = None
            
        self.load_from_config_file(inputConfigPath)

    @staticmethod
    def _normalize_path(path: str) -> str:
        """경로를 윈도우즈 형식으로 정규화"""
        if not path:
            return path
        return str(PureWindowsPath(path))

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        """폴더명에서 유효하지 않은 문자를 제거"""
        invalidChars = r'[<>:"/\\|?*]'
        return re.sub(invalidChars, '_', name).strip()

    @property
    def rootPathProp(self) -> str:
        """루트 경로 속성 getter"""
        return self.rootPath

    @rootPathProp.setter
    def rootPathProp(self, path: str) -> None:
        """루트 경로 속성 setter"""
        self.rootPath = self._normalize_path(path)

    def generate_path(self, inputName: str, inIncludeRealName: bool = False) -> str:
        """
        입력된 이름을 기반으로 경로를 생성
        
        :param inputName: 파싱할 입력 이름
        :param inIncludeRealName: 실제 이름을 경로에 포함할지 여부
        :return: 생성된 경로
        """
        parsedDict = self.parse_name(inputName)
        nameParts = self.pathConfig.get_part_order()
        folders = [
            self._sanitize_folder_name(self.pathConfig.get_part(part).get_description_by_value(parsedDict[part]))
            for part in nameParts if part in parsedDict and self.pathConfig.get_part(part).get_description_by_value(parsedDict[part])
        ]
        if inIncludeRealName:
            folders.append(self._sanitize_folder_name(parsedDict["RealName"]))
        
        if self.rootPath:
            fullPath = os.path.join(self.rootPath, *folders)
        else:
            fullPath = os.path.join(*folders) if folders else ""
        return self._normalize_path(fullPath)

    def parse_name(self, inName: str):
        """이름을 파싱하여 딕셔너리로 변환"""
        return self.convert_to_dictionary(inName)
    
    def set_root_path(self, inRootPath: str) -> str:
        """
        루트 경로를 설정합니다.
        입력된 경로를 정규화하고 유효성을 검증합니다.
        
        :param inRootPath: 루트 경로 (문자열)
        :return: 정규화된 경로
        :raises ValueError: 경로가 존재하지 않는 경우
        """
        if inRootPath:
            normalized_path = self._normalize_path(inRootPath)
            if not os.path.exists(normalized_path):
                raise ValueError(f"경로가 존재하지 않습니다: {normalized_path}")
            self.rootPath = normalized_path
            return self.rootPath
        else:
            self.rootPath = None
            return None

    def combine(self, inPartsDict={}, inFilChar=os.sep) -> str:
        """
        딕셔너리의 값들을 설정된 순서에 따라 문자열로 결합합니다. (인덱스 제외)

        :param inPartsDict: 결합할 키-값 쌍을 포함하는 딕셔너리
        :param inFilChar: 값들을 구분할 구분자 (기본값: os.sep)
        :return: 결합된 문자열
        """
        # 결과 배열 초기화 (빈 문자열로)
        combinedNameArray = [""] * len(self._nameParts)
        
        # 각 namePart에 대해
        for i, part in enumerate(self._nameParts):
            partName = part.get_name()
            # 딕셔너리에서 해당 부분의 값 가져오기 (없으면 빈 문자열 사용)
            if partName in inPartsDict:
                combinedNameArray[i] = inPartsDict[partName]
                
        # 배열을 문자열로 결합
        newName = self._combine(combinedNameArray, inFilChar)
        return newName