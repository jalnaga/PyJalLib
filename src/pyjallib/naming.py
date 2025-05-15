#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# Naming 모듈

이름 규칙을 정의하고 관리하며 이를 기반으로 이름을 생성하고 분석하는 기능을 제공하는 모듈입니다.

## 주요 기능
- NamePart 객체를 기반으로 조직화된 이름 생성 및 분석
- 이름 구성 요소의 추출 및 조작
- 이름 형식 변환 및 패턴 매칭
- 인덱스 관리 및 정렬 기능

## 클래스
- Naming: 이름 규칙 관리 및 이름 조작 기능을 제공하는 주요 클래스
"""

import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, Tuple

# NamePart와 NamingConfig 임포트
from pyjallib.namePart import NamePart, NamePartType
from pyjallib.namingConfig import NamingConfig

class Naming:
    """
    # Naming 클래스
    
    이름을 구성하는 각 부분을 관리하고 이를 기반으로 이름을 생성, 분석 및 조작하는 기능을 제공합니다.
    
    ## 주요 기능
    - 이름 구성 요소(prefix, suffix, realname, index 등) 관리
    - 사전 정의된 이름 형식에 따른 이름 생성 및 분석
    - 이름 부분별 추출 및 조작
    - 이름 형식 변환(설명, 한국어 설명 등)
    - 인덱스 관리 및 정렬
    
    ## 사용 예시
    ```python
    # 설정 파일로 초기화
    naming = Naming("naming_config.json")
    
    # 이름 생성
    name = naming.combine({"Prefix": "Pr", "RealName": "Arm", "Index": "01"}, "_")
    # 결과: "Pr_Arm_01"
    
    # 이름 분석
    parts_dict = naming.convert_to_dictionary("Pr_Arm_01")
    # 결과: {"Prefix": "Pr", "RealName": "Arm", "Index": "01"}
    ```
    """
    
    def __init__(self, configPath=None):
        """
        Naming 클래스 초기화
        
        ## Parameters
        - configPath (str): 설정 파일 경로 (기본값: None)
                         설정 파일이 제공되면 해당 파일에서 설정을 로드함
        """
        # 기본 설정값
        self._paddingNum = 2
        self._configPath = configPath
        
        # 기본 namePart 초기화 (각 부분에 사전 정의 값 직접 설정)
        self._nameParts = []
        
        # Prefix 부분 (PREFIX 타입)
        prefixPart = NamePart("Prefix", NamePartType.PREFIX, ["Pr"], ["Prefix"])
        
        # RealName 부분 (REALNAME 타입)
        realNamePart = NamePart("RealName", NamePartType.REALNAME, [], [])
        
        # Index 부분 (INDEX 타입)
        indexPart = NamePart("Index", NamePartType.INDEX, [], [])
        
        # Suffix 부분 (SUFFIX 타입)
        suffixPart = NamePart("Suffix", NamePartType.SUFFIX, ["Su"], ["Suffix"])
        
        # 기본 순서대로 설정
        self._nameParts = [prefixPart, realNamePart, indexPart, suffixPart]
        
        # 설정 파일이 제공된 경우 로드
        if configPath:
            self.load_from_config_file(configPath)
        else:
            # 기본 JSON 설정 파일 로드 시도
            self.load_default_config()

    # ---- String 관련 메소드들 (내부 사용 헬퍼 메소드) ----
    
    def _split_into_string_and_digit(self, inStr):
        """
        문자열을 문자부분과 숫자부분으로 분리합니다.
        
        ## Parameters
        - inStr (str): 분리할 문자열
            
        ## Returns
        - tuple: (문자부분, 숫자부분) 튜플
        """
        match = re.match(r'^(.*?)(\d*)$', inStr)
        if match:
            return match.group(1), match.group(2)
        return inStr, ""

    def _compare_string(self, inStr1, inStr2):
        """
        대소문자 구분 없이 문자열을 비교합니다.
        
        ## Parameters
        - inStr1 (str): 첫 번째 문자열
        - inStr2 (str): 두 번째 문자열
            
        ## Returns
        - int: 비교 결과 (inStr1 < inStr2: 음수, inStr1 == inStr2: 0, inStr1 > inStr2: 양수)
        """
        if inStr1.lower() < inStr2.lower():
            return -1
        elif inStr1.lower() > inStr2.lower():
            return 1
        return 0

    def _sort_by_alphabet(self, inArray):
        """
        배열 내 문자열을 알파벳 순으로 정렬합니다.
        
        ## Parameters
        - inArray (list): 정렬할 문자열 배열
            
        ## Returns
        - list: 알파벳 순으로 정렬된 문자열 배열
        """
        return sorted(inArray, key=lambda x: x.lower())

    def _get_filtering_char(self, inStr):
        """
        문자열에서 사용된 구분자 문자를 찾습니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - str: 구분자 문자 (' ' 또는 '_' 또는 '')
        """
        if ' ' in inStr:
            return ' '
        if '_' in inStr:
            return '_'
        return ''

    def _filter_by_filtering_char(self, inStr):
        """
        구분자 문자로 문자열을 분할합니다.
        
        ## Parameters
        - inStr (str): 분할할 문자열
            
        ## Returns
        - list: 분할된 문자열 리스트
        """
        filChar = self._get_filtering_char(inStr)
        
        if not filChar:
            return [inStr]
            
        return [part for part in inStr.split(filChar) if part]

    def _filter_by_upper_case(self, inStr):
        """
        대문자로 시작하는 부분을 기준으로 문자열을 분할합니다.
        
        ## Parameters
        - inStr (str): 분할할 문자열
            
        ## Returns
        - list: 분할된 문자열 리스트
        """
        if not inStr:
            return []
            
        result = []
        currentPart = inStr[0]
        
        for i in range(1, len(inStr)):
            if inStr[i].isupper():
                result.append(currentPart)
                currentPart = inStr[i]
            else:
                currentPart += inStr[i]
                
        if currentPart:
            result.append(currentPart)
            
        return result

    def _has_digit(self, inStr):
        """
        문자열에 숫자가 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: 숫자가 포함되어 있으면 True, 아니면 False
        """
        return any(char.isdigit() for char in inStr)

    def _split_to_array(self, inStr):
        """
        문자열을 구분자 또는 대문자로 분할하고 숫자 부분도 분리합니다.
        
        ## Parameters
        - inStr (str): 분할할 문자열
            
        ## Returns
        - list: 분할된 문자열 리스트
        """
        filChar = self._get_filtering_char(inStr)
        
        if not filChar:
            resultArray = self._filter_by_upper_case(inStr)
            tempArray = []
            
            for item in resultArray:
                if self._has_digit(item):
                    stringPart, digitPart = self._split_into_string_and_digit(item)
                    if stringPart:
                        tempArray.append(stringPart)
                    if digitPart:
                        tempArray.append(digitPart)
                else:
                    tempArray.append(item)
                    
            return tempArray
        else:
            return self._filter_by_filtering_char(inStr)

    def _remove_empty_string_in_array(self, inArray):
        """
        배열에서 빈 문자열을 제거합니다.
        
        ## Parameters
        - inArray (list): 처리할 배열
            
        ## Returns
        - list: 빈 문자열이 제거된 배열
        """
        return [item for item in inArray if item]

    def _combine(self, inArray, inFilChar=" "):
        """
        문자열 배열을 하나의 문자열로 결합합니다.
        
        ## Parameters
        - inArray (list): 결합할 문자열 배열
        - inFilChar (str): 구분자 (기본값: 공백)
            
        ## Returns
        - str: 결합된 문자열
        """
        refinedArray = self._remove_empty_string_in_array(inArray)
        
        if not refinedArray:
            return ""
            
        if len(refinedArray) == 1:
            return refinedArray[0]
            
        return inFilChar.join(refinedArray)

    # ---- Name 관련 메서드들 ----
    
    def get_padding_num(self):
        """
        패딩 숫자를 가져옵니다.
        
        ## Returns
        - int: 패딩 숫자
        """
        return self._paddingNum

    def get_name_part(self, inNamePartName):
        """
        namePart 이름으로 NamePart 객체를 가져옵니다.
        
        ## Parameters
        - inNamePartName (str): 가져올 NamePart의 이름 ("Prefix", "RealName", "Suffix", "Index" 등)
            
        ## Returns
        - NamePart: 해당 NamePart 객체, 존재하지 않으면 None
        """
        for part in self._nameParts:
            if part.get_name() == inNamePartName:
                return part
        return None
     
    def get_name_part_index(self, inNamePartName):
        """
        namePart 이름으로 인덱스를 가져옵니다.
        
        ## Parameters
        - inNamePartName (str): 가져올 NamePart의 이름 ("Prefix", "RealName", "Suffix", "Index" 등)
            
        ## Returns
        - int: 해당 NamePart의 인덱스, 존재하지 않으면 -1
        """
        for i, part in enumerate(self._nameParts):
            if part.get_name() == inNamePartName:
                return i
        return -1

    def get_name_part_predefined_values(self, inNamePartName):
        """
        namePart의 사전 정의 값을 가져옵니다.
        
        ## Parameters
        - inNamePartName (str): 가져올 NamePart의 이름 ("Prefix", "RealName", "Suffix", "Index" 등)
            
        ## Returns
        - list: 해당 NamePart의 사전 정의 값 리스트, 존재하지 않으면 빈 리스트
        """
        partObj = self.get_name_part(inNamePartName)
        if partObj:
            return partObj.get_predefined_values()
        return []
    
    def is_in_name_part_predefined_values(self, inNamePartName, inStr):
        """
        지정된 namePart에 해당하는 부분이 문자열에 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inNamePartName (str): 확인할 namePart 이름 ("Base", "Type", "Side" 등)
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: 포함되어 있으면 True, 아니면 False
        """
        partObj = self.get_name_part(inNamePartName)
        if not partObj:
            return False
        
        partType = partObj.get_type()
        if not partType:
            return False
            
        partValues = partObj.get_predefined_values()
        
        if partType == NamePartType.PREFIX or partType == NamePartType.SUFFIX:
            return any(item in inStr for item in partValues)
        
        return False

    def get_name_part_value_by_description(self, inNamePartName, inDescription):
        """
        지정된 namePart에 해당하는 부분을 문자열에서 추출합니다.
        
        ## Parameters
        - inNamePartName (str): 추출할 namePart 이름 ("Base", "Type", "Side" 등)
        - inDescription (str): predefined value에서 찾기위한 description 문자열
            
        ## Returns
        - str: 지정된 namePart에 해당하는 문자열
        """
        partObj = self.get_name_part(inNamePartName)
        if not partObj:
            return ""
        
        partType = partObj.get_type()
        if not partType:
            return ""
            
        partValues = partObj.get_predefined_values()
        
        if partType == NamePartType.PREFIX or partType == NamePartType.SUFFIX:
            try:
                foundIndex = partObj._descriptions.index(inDescription)
                return partValues[foundIndex]
            except ValueError:
                return ""

    def pick_name(self, inNamePartName, inStr):
        """
        문자열에서 지정된 namePart에 해당하는 부분을 선택합니다.
        
        ## Parameters
        - inNamePartName (str): 선택할 namePart 이름
        - inStr (str): 처리할 문자열
        
        ## Returns
        - str: 선택된 namePart 값
        """
        nameArray = self._split_to_array(inStr)
        returnStr = ""
        
        partObj = self.get_name_part(inNamePartName)
        if not partObj:
            return returnStr
        
        partType = partObj.get_type()
        if not partType:
            return returnStr
            
        partValues = partObj.get_predefined_values()
        if partType != NamePartType.INDEX and partType != NamePartType.REALNAME and not partValues:
            return returnStr
        
        if partType == NamePartType.PREFIX:
            for item in nameArray:
                if item in partValues:
                    returnStr = item
                    break
        
        if partType == NamePartType.SUFFIX:
            for i in range(len(nameArray) - 1, -1, -1):
                if nameArray[i] in partValues:
                    returnStr = nameArray[i]
                    break
                
        if partType == NamePartType.INDEX:
            if self.get_name_part_index("Index") > self.get_name_part_index("RealName"):
                for i in range(len(nameArray) - 1, -1, -1):
                    if nameArray[i].isdigit():
                        returnStr = nameArray[i]
                        break
            else:
                for item in nameArray:
                    if item.isdigit():
                        returnStr = item
                        break
        
        return returnStr
        
    def get_name(self, inNamePartName, inStr):
        """
        지정된 namePart에 해당하는 부분을 문자열에서 추출합니다.
        
        ## Parameters
        - inNamePartName (str): 추출할 namePart 이름
        - inStr (str): 처리할 문자열
        
        ## Returns
        - str: 추출된 namePart 값
        """
        nameArray = self._split_to_array(inStr)
        returnStr = ""
        
        partType = self.get_name_part(inNamePartName).get_type()
        
        foundName = self.pick_name(inNamePartName, inStr)
        if foundName == "":
            return returnStr
        partIndex = self.get_name_part_index(inNamePartName)
        foundIndex = nameArray.index(foundName)
        
        if partType == NamePartType.PREFIX:
            if foundIndex >= 0:
                prevNameParts = self._nameParts[:partIndex]
                prevNames = [self.pick_name(part.get_name(), inStr) for part in prevNameParts]
                prevNamesInNameArray = nameArray[:foundIndex]
                for prevName in prevNames:
                    if prevName in prevNamesInNameArray:
                        prevNamesInNameArray.remove(prevName)
                if len(prevNamesInNameArray) == 0 :
                    returnStr = foundName
        
        if partType == NamePartType.SUFFIX:
            if foundIndex >= 0:
                nextNameParts = self._nameParts[partIndex + 1:]
                nextNames = [self.pick_name(part.get_name(), inStr) for part in nextNameParts]
                nextNamesInNameArray = nameArray[foundIndex + 1:]
                for nextName in nextNames:
                    if nextName in nextNamesInNameArray:
                        nextNamesInNameArray.remove(nextName)
                if len(nextNamesInNameArray) == 0 :
                    returnStr = foundName
        
        if partType == NamePartType.INDEX:
            returnStr = self.pick_name(inNamePartName, inStr)
                
        return returnStr
    
    def combine(self, inPartsDict={}, inFilChar=" "):
        """
        namingConfig에서 정의된 nameParts와 그 순서에 따라 이름 부분들을 조합하여 완전한 이름을 생성합니다.
        
        ## Parameters
        - inPartsDict (dict): namePart 이름과 값의 딕셔너리 (예: {"Base": "b", "Type": "P", "Side": "L"})
        - inFilChar (str): 구분자 문자 (기본값: " ")
        
        ## Returns
        - str: 조합된 이름 문자열
        """
        combinedNameArray = [""] * len(self._nameParts)
        
        for i, part in enumerate(self._nameParts):
            partName = part.get_name()
            if partName in inPartsDict:
                combinedNameArray[i] = inPartsDict[partName]
                
        newName = self._combine(combinedNameArray, inFilChar)
        newName = self.set_index_padding_num(newName)
        return newName
    
    def get_RealName(self, inStr):
        """
        문자열에서 실제 이름 부분을 추출합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        
        ## Returns
        - str: 실제 이름 부분 문자열
        """
        filChar = self._get_filtering_char(inStr)
        nameArray = self._split_to_array(inStr)
        
        nonRealNameArray = []
        for part in self._nameParts:
            partName = part.get_name()
            partType = part.get_type()
            if partType != NamePartType.REALNAME:
                foundName = self.get_name(partName, inStr)
                nonRealNameArray.append(foundName)
        
        for item in nonRealNameArray:
            if item in nameArray:
                nameArray.remove(item)
                
        return self._combine(nameArray, filChar)

    def get_non_RealName(self, inStr):
        """
        실제 이름 부분을 제외한 이름을 가져옵니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        
        ## Returns
        - str: 실제 이름이 제외된 이름 문자열
        """
        filChar = self._get_filtering_char(inStr)
        
        nonRealNameArray = []
        for part in self._nameParts:
            partName = part.get_name()
            partType = part.get_type()
            if partType != NamePartType.REALNAME:
                foundName = self.get_name(partName, inStr)
                nonRealNameArray.append(foundName)
        
        return self._combine(nonRealNameArray, filChar)
                
    def convert_name_to_array(self, inStr):
        """
        문자열 이름을 이름 부분 배열로 변환합니다.
        
        ## Parameters
        - inStr (str): 변환할 이름 문자열
        
        ## Returns
        - list: 이름 부분 배열 (Base, Type, Side, FrontBack, RealName, Index, Nub 등)
        """
        returnArray = [""] * len(self._nameParts)
        
        for i, part in enumerate(self._nameParts):
            partName = part.get_name()
            
            if partName == "RealName":
                realNameIndex = i
                continue
                
            partValue = self.get_name(partName, inStr)
            returnArray[i] = partValue
        
        if 'realNameIndex' in locals():
            realNameStr = self.get_RealName(inStr)
            returnArray[realNameIndex] = realNameStr
        
        return returnArray
    
    def convert_to_dictionary(self, inStr):
        """
        문자열 이름을 이름 부분 딕셔너리로 변환합니다.
        
        ## Parameters
        - inStr (str): 변환할 이름 문자열
        
        ## Returns
        - dict: 이름 부분 딕셔너리 (키: namePart 이름, 값: 추출된 값)
        """
        returnDict = {}
        
        for part in self._nameParts:
            partName = part.get_name()
            
            if partName == "RealName":
                continue
                
            partValue = self.get_name(partName, inStr)
            returnDict[partName] = partValue
        
        realNameStr = self.get_RealName(inStr)
        returnDict["RealName"] = realNameStr
        
        return returnDict
    
    def convert_to_description(self, inStr):
        """
        문자열 이름을 설명으로 변환합니다.
        
        ## Parameters
        - inStr (str): 변환할 이름 문자열
        
        ## Returns
        - str: 설명 문자열 (예: "b_P_L_Arm")
        """
        nameDic = self.convert_to_dictionary(inStr)
        descriptionDic = {}
        filteringChar = self._get_filtering_char(inStr)
        descName = inStr
        if nameDic:
            for namePartName, value in nameDic.items():
                namePart = self.get_name_part(namePartName)
                desc = namePart.get_description_by_value(value)

                if desc == "" and value != "":
                    desc = value

                descriptionDic[namePartName] = desc

            descName = self.combine(descriptionDic, filteringChar)
        
        return descName
    
    def convert_to_korean_description(self, inStr):
        """
        문자열 이름을 한국어 설명으로 변환합니다.
        
        ## Parameters
        - inStr (str): 변환할 이름 문자열
        
        ## Returns
        - str: 한국어 설명 문자열 (예: "팔_왼쪽_팔")
        """
        nameDic = self.convert_to_dictionary(inStr)
        korDescDic = {}
        filteringChar = self._get_filtering_char(inStr)
        korDescName = inStr
        if nameDic:
            for namePartName, value in nameDic.items():
                namePart = self.get_name_part(namePartName)
                desc = namePart.get_description_by_value(value)
                korDesc = namePart.get_korean_description_by_value(value)

                if korDesc == "" and desc != "":
                    korDesc = desc

                korDescDic[namePartName] = korDesc

            korDescName = self.combine(korDescDic, filteringChar)
        
        return korDescName
    
    def has_name_part(self, inPart, inStr):
        """
        문자열에 특정 namePart가 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inPart (str): 확인할 namePart 이름 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
        - inStr (str): 확인할 문자열
        
        ## Returns
        - bool: 포함되어 있으면 True, 아니면 False
        """
        return self.get_name(inPart, inStr) != ""
    
    def add_prefix_to_name_part(self, inPart, inStr, inPrefix):
        """
        이름의 특정 부분에 접두사를 추가합니다.
        
        ## Parameters
        - inPart (str): 수정할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
        - inStr (str): 처리할 이름 문자열
        - inPrefix (str): 추가할 접두사
        
        ## Returns
        - str: 수정된 이름 문자열
        """
        returnStr = inStr
        
        if inPrefix:
            filChar = self._get_filtering_char(inStr)
            nameArray = self.convert_name_to_array(inStr)
            partIndex = self.get_name_part_index(inPart)
                
            nameArray[partIndex] = inPrefix + nameArray[partIndex]
                    
            returnStr = self._combine(nameArray, filChar)
                
        return returnStr
    
    def add_suffix_to_name_part(self, inPart, inStr, inSuffix):
        """
        이름의 특정 부분에 접미사를 추가합니다.
        
        ## Parameters
        - inPart (str): 수정할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
        - inStr (str): 처리할 이름 문자열
        - inSuffix (str): 추가할 접미사
        
        ## Returns
        - str: 수정된 이름 문자열
        """
        returnStr = inStr
        
        if inSuffix:
            filChar = self._get_filtering_char(inStr)
            nameArray = self.convert_name_to_array(inStr)
            partIndex = self.get_name_part_index(inPart)
                
            nameArray[partIndex] = nameArray[partIndex] + inSuffix
                    
            returnStr = self._combine(nameArray, filChar)
                
        return returnStr

    def add_prefix_to_real_name(self, inStr, inPrefix):
        """
        실제 이름 부분에 접두사를 추가합니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        - inPrefix (str): 추가할 접두사
        
        ## Returns
        - str: 수정된 이름 문자열
        """
        return self.add_prefix_to_name_part("RealName", inStr, inPrefix)

    def add_suffix_to_real_name(self, inStr, inSuffix):
        """
        실제 이름 부분에 접미사를 추가합니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        - inSuffix (str): 추가할 접미사
        
        ## Returns
        - str: 수정된 이름 문자열
        """
        return self.add_suffix_to_name_part("RealName", inStr, inSuffix)
    
    def convert_digit_into_padding_string(self, inDigit, inPaddingNum=None):
        """
        숫자를 패딩된 문자열로 변환합니다.
        
        ## Parameters
        - inDigit (Union[int, str]): 변환할 숫자 또는 숫자 문자열
        - inPaddingNum (int, optional): 패딩 자릿수 (기본값: 클래스의 _paddingNum)
        
        ## Returns
        - str: 패딩된 문자열
        """
        if inPaddingNum is None:
            inPaddingNum = self._paddingNum
            
        digitNum = 0
        
        if isinstance(inDigit, int):
            digitNum = inDigit
        elif isinstance(inDigit, str):
            if inDigit.isdigit():
                digitNum = int(inDigit)
                
        return f"{digitNum:0{inPaddingNum}d}"

    def set_index_padding_num(self, inStr, inPaddingNum=None):
        """
        이름의 인덱스 부분 패딩을 설정합니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        - inPaddingNum (int, optional): 설정할 패딩 자릿수 (기본값: 클래스의 _paddingNum)
        
        ## Returns
        - str: 패딩이 적용된 이름 문자열
        """
        if inPaddingNum is None:
            inPaddingNum = self._paddingNum
            
        filChar = self._get_filtering_char(inStr)
        nameArray = self.convert_name_to_array(inStr)
        indexIndex = self.get_name_part_index("Index")
        indexStr = self.get_name("Index", inStr)
        
        if indexStr:
            indexStr = self.convert_digit_into_padding_string(indexStr, inPaddingNum)
            nameArray[indexIndex] = indexStr
            
        return self._combine(nameArray, filChar)

    def get_index_padding_num(self, inStr):
        """
        이름의 인덱스 부분 패딩 자릿수를 가져옵니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        
        ## Returns
        - int: 인덱스 패딩 자릿수
        """
        indexVal = self.get_name("Index", inStr)
        
        if indexVal:
            return len(indexVal)
            
        return 1

    def increase_index(self, inStr, inAmount):
        """
        이름의 인덱스 부분 값을 증가시킵니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        - inAmount (int): 증가시킬 값
        
        ## Returns
        - str: 인덱스가 증가된 이름 문자열
        """
        newName = inStr
        filChar = self._get_filtering_char(inStr)
        nameArray = self.convert_name_to_array(inStr)
        indexIndex = self.get_name_part_index("Index")
        
        if indexIndex >= 0:
            indexStr = ""
            indexPaddingNum = self._paddingNum
            indexNum = -99999
            
            if not nameArray[indexIndex]:
                indexNum = -1
            else:
                try:
                    indexNum = int(nameArray[indexIndex])
                    indexPaddingNum = len(nameArray[indexIndex])
                except ValueError:
                    pass
            
            indexNum += inAmount
            
            if indexNum < 0:
                indexNum = 0
            
            indexStr = f"{indexNum:0{indexPaddingNum}d}"
            nameArray[indexIndex] = indexStr
            newName = self._combine(nameArray, filChar)
            newName = self.set_index_padding_num(newName)
            
        return newName

    def get_index_as_digit(self, inStr):
        """
        이름의 인덱스를 숫자로 변환합니다.
        
        ## Parameters
        - inStr (str): 변환할 이름 문자열
        
        ## Returns
        - int: 숫자로 변환된 인덱스 (인덱스가 없으면 False)
        """
        indexStr = self.get_name("Index", inStr)
            
        if indexStr:
            try:
                return int(indexStr)
            except ValueError:
                pass
                
        return False

    def sort_by_index(self, inNameArray):
        """
        이름 배열을 인덱스 기준으로 정렬합니다.
        
        ## Parameters
        - inNameArray (list): 정렬할 이름 배열
        
        ## Returns
        - list: 인덱스 기준으로 정렬된 이름 배열
        """
        if not inNameArray:
            return []
            
        @dataclass
        class IndexSorting:
            oriIndex: int
            newIndex: int
                
        structArray = []
        
        for i, name in enumerate(inNameArray):
            tempIndex = self.get_index_as_digit(name)
            
            if tempIndex is False:
                structArray.append(IndexSorting(i, 0))
            else:
                structArray.append(IndexSorting(i, tempIndex))
                
        structArray.sort(key=lambda x: x.newIndex)
        
        sortedNameArray = []
        for struct in structArray:
            sortedNameArray.append(inNameArray[struct.oriIndex])
            
        return sortedNameArray
    
    def get_string(self, inStr):
        """
        인덱스 부분을 제외한 이름 문자열을 가져옵니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        
        ## Returns
        - str: 인덱스가 제외된 이름 문자열
        """
        filChar = self._get_filtering_char(inStr)
        nameArray = self.convert_name_to_array(inStr)
        indexOrder = self.get_name_part_index("Index")
        
        returnNameArray = nameArray.copy()
        returnNameArray[indexOrder] = ""
        
        return self._combine(returnNameArray, filChar)

    def gen_mirroring_name(self, inStr):
        """
        미러링된 이름을 생성합니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        
        ## Returns
        - str: 미러링된 이름 문자열
        """
        nameArray = self.convert_name_to_array(inStr)
            
        for part in self._nameParts:
            partName = part.get_name()
            partType = part.get_type()
            if (partType != NamePartType.REALNAME or partType != NamePartType.INDEX) and part.is_direction():
                partIndex = self.get_name_part_index(partName)
                foundName = self.get_name(partName, inStr)
                opositeName = part.get_most_different_weight_value(foundName)
                if opositeName and foundName != opositeName:
                    nameArray[partIndex] = opositeName
        
        returnName = self._combine(nameArray, self._get_filtering_char(inStr))
        
        return returnName

    def replace_filtering_char(self, inStr, inNewFilChar):
        """
        이름의 구분자 문자를 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
        - inNewFilChar (str): 새 구분자 문자
        
        ## Returns
        - str: 구분자가 변경된 이름 문자열
        """
        nameArray = self.convert_name_to_array(inStr)
        return self._combine(nameArray, inNewFilChar)

    def replace_name_part(self, inPart, inStr, inNewName):
        """
        이름의 특정 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inPart (str): 수정할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
        - inStr (str): 처리할 이름 문자열
        - inNewName (str): 새 이름
        
        ## Returns
        - str: 수정된 이름 문자열
        """
        nameArray = self.convert_name_to_array(inStr)
        partIndex = self.get_name_part_index(inPart)
        
        if partIndex >= 0:
            nameArray[partIndex] = inNewName
        
        newName = self._combine(nameArray, self._get_filtering_char(inStr))
        newName = self.set_index_padding_num(newName)
        
        return newName

    def remove_name_part(self, inPart, inStr):
        """
        이름의 특정 부분을 제거합니다.
        
        ## Parameters
        - inPart (str): 제거할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
        - inStr (str): 처리할 이름 문자열
        
        ## Returns
        - str: 수정된 이름 문자열
        """
        nameArray = self.convert_name_to_array(inStr)
        partIndex = self.get_name_part_index(inPart)
        
        if partIndex >= 0:
            nameArray[partIndex] = ""
            
        newName = self._combine(nameArray, self._get_filtering_char(inStr))
        newName = self.set_index_padding_num(newName)
        
        return newName

    def load_from_config_file(self, configPath=None):
        """
        설정 파일에서 설정을 로드합니다.
        
        ## Parameters
        - configPath (str, optional): 설정 파일 경로 (기본값: self._configPath)
        
        ## Returns
        - bool: 로드 성공 여부 (True/False)
        """
        if not configPath:
            configPath = self._configPath
            
        if not configPath:
            print("설정 파일 경로가 제공되지 않았습니다.")
            return False
            
        config = NamingConfig()
        if config.load(configPath):
            result = config.apply_to_naming(self)
            if result:
                self._configPath = configPath
            return result
        else:
            print(f"설정 파일 로드 실패: {configPath}")
            return False
    
    def load_default_config(self):
        """
        기본 설정을 로드합니다.
        
        ## Returns
        - bool: 항상 True 반환 (기본 설정은 __init__에서 이미 설정됨)
        """
        return True

    def get_config_path(self):
        """
        현재 설정 파일 경로를 가져옵니다.
        
        ## Returns
        - str: 설정 파일 경로 (없으면 빈 문자열)
        """
        return self._configPath or ""
