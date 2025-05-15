#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# nameToPath 모듈

이름 규칙에 따라 파일 경로를 생성하거나 경로에서 이름을 추출하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 이름 형식 기반 경로 생성
- 이름 구성 요소에 기반한 디렉토리 구조 생성
- 경로 정규화 및 유효성 검증

## 클래스
- NameToPath: Naming 클래스를 상속받아 이름 기반 경로 생성 기능을 제공
"""

import os
import json
from typing import Optional, Dict, Any, List

from pyjallib.naming import Naming
from pyjallib.namePart import NamePartType

class NameToPath(Naming):
    """
    # NameToPath 클래스
    
    Naming 클래스를 상속받아 이름을 기반으로 경로를 생성하는 기능을 제공합니다.
    
    ## 주요 기능
    - 이름 규칙에 따른 디렉토리 경로 생성
    - 루트 경로 설정 및 관리
    - 이름 구성요소를 경로 구성요소로 변환
    
    ## 사용 예시
    ```python
    # 설정 파일과 루트 경로로 초기화
    n2p = NameToPath("naming_config.json", "D:/Projects")
    
    # 이름으로부터 경로 생성
    path = n2p.gen_path("Side_L_Type_Arm_Name_Robot")
    # 결과: D:/Projects/Left/Arm/Robot
    ```
    """
    def __init__(self, configPath: str, rootPath: str = None, sourceNaming: Naming = None):
        """
        NameToPath 클래스 초기화
        
        ## Parameters
        - configPath (str): 설정 파일의 경로
        - rootPath (str): 루트 경로 (기본값: None)
        - sourceNaming (Naming): 소스 이름을 처리하기 위한 Naming 객체 (기본값: None)
        """
        # 부모 클래스(Naming) 생성자 호출
        super().__init__(configPath)
        self.rootPath = None
        if rootPath:
            self.set_root_path(rootPath)
        # 소스 네이밍 객체 설정
        self.sourceNaming = sourceNaming
    
    def set_root_path(self, inRootPath: str):
        """
        루트 경로를 설정합니다.
        
        입력된 경로를 정규화하고 유효성을 검증합니다.
        
        ## Parameters
        - inRootPath (str): 설정할 루트 경로
            
        ## Returns
        - str or None: 정규화된 경로, 입력이 없으면 None
            
        ## Raises
        - ValueError: 경로가 존재하지 않는 경우
        """
        if inRootPath:
            # 경로 정규화 (상대 경로를 절대 경로로 변환, '/' 대신 '\' 사용 등)
            normalized_path = os.path.normpath(os.path.abspath(inRootPath))
            
            # 경로 존재 여부 확인 (선택적)
            if not os.path.exists(normalized_path):
                raise ValueError(f"경로가 존재하지 않습니다: {normalized_path}")
            
            self.rootPath = normalized_path
            return self.rootPath
        else:
            self.rootPath = None
            return None
    
    def combine(self, inPartsDict={}, inFilChar=os.sep) -> str:
        """
        딕셔너리의 값들을 설정된 순서에 따라 문자열로 결합합니다.
        
        ## Parameters
        - inPartsDict (dict): 결합할 키-값 쌍을 포함하는 딕셔너리
        - inFilChar (str): 값들을 구분할 구분자 (기본값: OS 경로 구분자)
            
        ## Returns
        - str: 결합된 문자열 (경로)
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
                
    
    def gen_path(self, inStr):
        """
        입력된 문자열(이름)을 기반으로 경로를 생성합니다.
        
        소스 네이밍 객체를 사용하여 이름을 딕셔너리로 변환한 후,
        이를 기반으로 경로를 생성합니다.
        
        ## Parameters
        - inStr (str): 경로를 생성할 문자열 (이름)
            
        ## Returns
        - str: 생성된 전체 경로
            
        ## Raises
        - ValueError: 루트 경로가 설정되지 않았거나 이름을 변환할 수 없는 경우
        """
        if not self.rootPath:
            raise ValueError("루트 경로가 설정되지 않았습니다.")
        
        # 이름을 딕셔너리로 변환
        nameDict = self.sourceNaming.convert_to_dictionary(inStr)
        if not nameDict:
            raise ValueError(f"이름을 변환할 수 없습니다: {inStr}")
        print(f"Name Dictionary: {nameDict}")
        
        pathDict = {}
        
        # 선택된 NamePart 값들을 설명으로 변환하여 폴더 이름으로 사용
        for key, value in nameDict.items():
            namePart = self.sourceNaming.get_name_part(key)
            if self.get_name_part(namePart.get_name()):
                if namePart.get_type() == NamePartType.REALNAME:
                    # 실제 이름인 경우, 해당 이름을 사용
                    pathDict[key] = value
                else:
                    pathDict[key] = namePart.get_description_by_value(value)
        
        combinedPath = self.combine(pathDict)
        finalPath = os.path.join(self.rootPath, combinedPath)
        
        return os.path.normpath(finalPath)
