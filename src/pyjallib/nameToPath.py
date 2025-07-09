#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
nameToPath 모듈 - 이름과 경로 변환 관련 기능
이름 규칙에 따라 경로를 생성하거나 경로에서 이름을 추출하는 기능 제공
"""

import os
import json
import re
from pathlib import PureWindowsPath
from typing import Optional, Dict, Any, List

from pyjallib.naming import Naming
from pyjallib.namePart import NamePartType

class NameToPath(Naming):
    """
    NameToPath 클래스는 Naming 클래스를 상속받아 이름을 기반으로 경로를 생성하는 기능을 제공합니다.
    """
    def __init__(self, configPath: str, rootPath: str = None, sourceNaming: Naming = None):
        """
        생성자 메서드입니다.
        :param configPath: 설정 파일의 경로
        :param rootPath: 루트 경로 (기본값: None)
        :param sourceNaming: 소스 이름을 처리하기 위한 Naming 객체 (기본값: None)
        """
        # 부모 클래스(Naming) 생성자 호출
        super().__init__(configPath)
        self._rootPath = None
        if rootPath:
            self.set_root_path(rootPath)
        # 소스 네이밍 객체 설정
        self.sourceNaming = sourceNaming
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Windows 경로 정규화
        :param path: 정규화할 경로
        :return: 정규화된 경로
        """
        if not path:
            return path
        return str(PureWindowsPath(path))
    
    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        """
        폴더명 안전 변환 - Windows 파일시스템 제약사항 준수
        :param name: 변환할 폴더명
        :return: 안전한 폴더명
        """
        if not name:
            return name
        invalidChars = r'[<>:"/\\|?*]'
        return re.sub(invalidChars, '_', name).strip()
    
    @property
    def rootPath(self) -> str:
        """루트 경로 getter"""
        return self._rootPath
    
    @rootPath.setter
    def rootPath(self, path: str) -> None:
        """루트 경로 setter - 자동으로 정규화"""
        self._rootPath = self._normalize_path(path) if path else None
    
    def set_root_path(self, inRootPath: str):
        """
        루트 경로를 설정합니다.
        입력된 경로를 정규화하고 유효성을 검증합니다.
        
        :param inRootPath: 루트 경로 (문자열)
        :return: 정규화된 경로
        :raises ValueError: 경로가 존재하지 않는 경우
        """
        if inRootPath:
            # 경로 정규화 (상대 경로를 절대 경로로 변환, Windows 경로 정규화)
            normalized_path = self._normalize_path(os.path.abspath(inRootPath))
            
            # 경로 존재 여부 확인 (선택적)
            if not os.path.exists(normalized_path):
                raise ValueError(f"경로가 존재하지 않습니다: {normalized_path}")
            
            self._rootPath = normalized_path
            return self._rootPath
        else:
            self._rootPath = None
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
                value = inPartsDict[partName]
                # 폴더명 안전 변환 적용
                combinedNameArray[i] = self._sanitize_folder_name(str(value)) if value else ""
                
        # 배열을 문자열로 결합
        newName = self._combine(combinedNameArray, inFilChar)
        return newName
                
    
    def gen_path(self, inStr, inIncludeRealName: bool = False):
        """
        입력된 문자열을 기반으로 경로를 생성합니다.
        
        :param inStr: 경로를 생성할 문자열 (이름)
        :param inIncludeRealName: 실제 이름을 경로에 포함할지 여부
        :return: 생성된 경로 (문자열)
        :raises ValueError: 루트 경로가 설정되지 않았거나 이름을 변환할 수 없는 경우
        """
        if not self._rootPath:
            raise ValueError("루트 경로가 설정되지 않았습니다.")
        
        # 이름을 딕셔너리로 변환
        nameDict = self.sourceNaming.convert_to_dictionary(inStr) if self.sourceNaming else self.convert_to_dictionary(inStr)
        if not nameDict:
            raise ValueError(f"이름을 변환할 수 없습니다: {inStr}")
        print(f"Name Dictionary: {nameDict}")
        
        pathDict = {}
        
        # 선택된 NamePart 값들을 설명으로 변환하여 폴더 이름으로 사용
        for key, value in nameDict.items():
            if self.sourceNaming:
                namePart = self.sourceNaming.get_name_part(key)
                if self.get_name_part(namePart.get_name()):
                    if namePart.get_type().value == NamePartType.REALNAME.value:
                        # 실제 이름인 경우, 해당 이름을 사용
                        pathDict[key] = value
                    else:
                        pathDict[key] = namePart.get_description_by_value(value)
            else:
                # sourceNaming이 없는 경우 직접 처리
                namePart = self.get_name_part(key)
                if namePart:
                    if namePart.get_type().value == NamePartType.REALNAME.value:
                        pathDict[key] = value
                    else:
                        pathDict[key] = namePart.get_description_by_value(value)
        
        # 실제 이름 포함 옵션 처리
        if inIncludeRealName and "RealName" in nameDict:
            pathDict["RealName"] = nameDict["RealName"]
        
        combinedPath = self.combine(pathDict)
        finalPath = os.path.join(self._rootPath, combinedPath)
        
        return self._normalize_path(finalPath)

    def generate_path(self, inputName: str, inIncludeRealName: bool = False) -> str:
        """
        gen_path의 별칭 메서드 - orvlib 호환성을 위한 메서드
        
        :param inputName: 경로를 생성할 문자열 (이름)
        :param inIncludeRealName: 실제 이름을 경로에 포함할지 여부
        :return: 생성된 경로 (문자열)
        """
        return self.gen_path(inputName, inIncludeRealName)

    def parse_name(self, inName: str):
        """
        convert_to_dictionary의 별칭 메서드 - orvlib 호환성을 위한 메서드
        
        :param inName: 파싱할 이름
        :return: 파싱된 딕셔너리
        """
        return self.convert_to_dictionary(inName)
