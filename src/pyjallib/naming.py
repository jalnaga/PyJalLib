#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Naming 모듈 - 이름 규칙 관리 및 적용 기능 제공
NamePart 객체를 기반으로 조직화된 이름 생성 및 분석 기능 구현
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
    노드 이름을 관리하기 위한 기본 클래스.
    기본적인 이름 구성 요소를 정의하고 관리합니다.
    이 클래스는 하위 클래스에서 확장하여 특정 목적에 맞게 사용할 수 있습니다.
    """
    
    def __init__(self, configPath=None):
        """
        클래스 초기화 및 기본 설정값 정의
        
        Args:
            configPath: 설정 파일 경로 (기본값: None)
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
        문자열을 문자부분과 숫자부분으로 분리
        
        Args:
            inStr: 분리할 문자열
            
        Returns:
            튜플 (문자부분, 숫자부분)
        """
        match = re.match(r'^(.*?)(\d*)$', inStr)
        if match:
            return match.group(1), match.group(2)
        return inStr, ""

    def _compare_string(self, inStr1, inStr2):
        """
        대소문자 구분 없이 문자열 비교
        
        Args:
            inStr1: 첫 번째 문자열
            inStr2: 두 번째 문자열
            
        Returns:
            비교 결과 (inStr1 < inStr2: 음수, inStr1 == inStr2: 0, inStr1 > inStr2: 양수)
        """
        # Python에서는 대소문자 구분 없는 비교를 위해 lower() 메서드 사용
        if inStr1.lower() < inStr2.lower():
            return -1
        elif inStr1.lower() > inStr2.lower():
            return 1
        return 0

    def _sort_by_alphabet(self, inArray):
        """
        배열 내 문자열을 알파벳 순으로 정렬
        
        Args:
            inArray: 정렬할 배열
            
        Returns:
            정렬된 배열
        """
        # Python의 sorted 함수와 lambda를 사용하여 대소문자 구분 없이 정렬
        return sorted(inArray, key=lambda x: x.lower())

    def _get_filtering_char(self, inStr):
        """
        문자열에서 사용된 구분자 문자 찾기
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            구분자 문자 (' ' 또는 '_' 또는 '')
        """
        if ' ' in inStr:
            return ' '
        if '_' in inStr:
            return '_'
        return ''

    def _filter_by_filtering_char(self, inStr):
        """
        구분자 문자로 문자열 분할
        
        Args:
            inStr: 분할할 문자열
            
        Returns:
            분할된 문자열 리스트
        """
        filChar = self._get_filtering_char(inStr)
        
        if not filChar:
            return [inStr]
            
        # 빈 문자열 제거하며 분할
        return [part for part in inStr.split(filChar) if part]

    def _filter_by_upper_case(self, inStr):
        """
        대문자로 시작하는 부분을 기준으로 문자열 분할
        
        Args:
            inStr: 분할할 문자열
            
        Returns:
            분할된 문자열 리스트
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
        문자열에 숫자가 포함되어 있는지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            숫자가 포함되어 있으면 True, 아니면 False
        """
        return any(char.isdigit() for char in inStr)

    def _split_to_array(self, inStr):
        """
        문자열을 구분자 또는 대문자로 분할하고 숫자 부분도 분리
        
        Args:
            inStr: 분할할 문자열
            
        Returns:
            분할된 문자열 리스트
        """
        filChar = self._get_filtering_char(inStr)
        
        if not filChar:
            # 구분자가 없을 경우 대문자로 분할
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
            # 구분자가 있을 경우 구분자로 분할
            return self._filter_by_filtering_char(inStr)

    def _remove_empty_string_in_array(self, inArray):
        """
        배열에서 빈 문자열 제거
        
        Args:
            inArray: 처리할 배열
            
        Returns:
            빈 문자열이 제거된 배열
        """
        return [item for item in inArray if item]

    def _combine(self, inArray, inFilChar=" "):
        """
        문자열 배열을 하나의 문자열로 결합
        
        Args:
            inArray: 결합할 문자열 배열
            filChar: 구분자 (기본값: 공백)
            
        Returns:
            결합된 문자열
        """
        refinedArray = self._remove_empty_string_in_array(inArray)
        
        if not refinedArray:
            return ""
            
        if len(refinedArray) == 1:
            return refinedArray[0]
            
        return inFilChar.join(refinedArray)

    # ---- Name 관련 메서드들 ----
    
    # 사전 정의 값 편집 메서드 제거 (namingConfig를 통해서만 변경 가능)

    def get_padding_num(self):
        """
        패딩 숫자 가져오기
        
        Returns:
            패딩 숫자
        """
        return self._paddingNum

    def get_name_part(self, inNamePartName):
        """
        namePart 이름으로 NamePart 객체 가져오기
        
        Args:
            namePart: 가져올 NamePart의 이름 ("Prefix", "RealName", "Suffix", "Index" 등)
            
        Returns:
            해당 NamePart 객체, 존재하지 않으면 None
        """
        for part in self._nameParts:
            if part.get_name() == inNamePartName:
                return part
        return None
     
    def get_name_part_index(self, inNamePartName):
        """
        namePart 이름으로 인덱스 가져오기
        
        Args:
            namePart: 가져올 NamePart의 이름 ("Prefix", "RealName", "Suffix", "Index" 등)
            
        Returns:
            해당 NamePart의 인덱스, 존재하지 않으면 -1
        """
        for i, part in enumerate(self._nameParts):
            if part.get_name() == inNamePartName:
                return i
        return -1

    def get_name_part_predefined_values(self, inNamePartName):
        """
        namePart의 사전 정의 값 가져오기
        
        Args:
            namePart: 가져올 NamePart의 이름 ("Prefix", "RealName", "Suffix", "Index" 등)
            
        Returns:
            해당 NamePart의 사전 정의 값 리스트, 존재하지 않으면 빈 리스트
        """
        partObj = self.get_name_part(inNamePartName)
        if partObj:
            return partObj.get_predefined_values()
        return []
    
    def is_in_name_part_predefined_values(self, inNamePartName, inStr):
        """
        지정된 namePart에 해당하는 부분이 문자열에 포함되어 있는지 확인
        
        Args:
            namePart: 확인할 namePart 이름 ("Base", "Type", "Side" 등)
            inStr: 확인할 문자열
            
        Returns:
            포함되어 있으면 True, 아니면 False
        """
        partObj = self.get_name_part(inNamePartName)
        if not partObj:
            return False
        
        partType = partObj.get_type()
        if not partType:
            return False
            
        partValues = partObj.get_predefined_values()
        
        if partType.value == NamePartType.PREFIX.value or partType.value == NamePartType.SUFFIX.value:
            return any(item in inStr for item in partValues)
        
        return False

    def get_name_part_value_by_description(self, inNamePartName, inDescription):
        """
        지정된 namePart에 해당하는 부분을 문자열에서 추출
        
        Args:
            namePart: 추출할 namePart 이름 ("Base", "Type", "Side" 등)
            inDescription: predefined value에서 찾기위한 description 문자열
            
        Returns:
            지정된 namePart에 해당하는 문자열
        """
        partObj = self.get_name_part(inNamePartName)
        if not partObj:
            return ""
        
        partType = partObj.get_type()
        if not partType:
            return ""
            
        partValues = partObj.get_predefined_values()
        
        if partType.value == NamePartType.PREFIX.value or partType.value == NamePartType.SUFFIX.value:
            try:
                foundIndex = partObj._descriptions.index(inDescription)
                return partValues[foundIndex]
            except ValueError:
                # Description not found in the list
                return ""

    def pick_name(self, inNamePartName, inStr):
        nameArray = self._split_to_array(inStr)
        returnStr = ""
        
        # namePart 문자열 목록 가져오기
        partObj = self.get_name_part(inNamePartName)
        if not partObj:
            return returnStr
        
        partType = partObj.get_type()
        if not partType:
            return returnStr
        
        partValues = partObj.get_predefined_values()
        if partType.value != NamePartType.INDEX.value and partType.value != NamePartType.REALNAME.value and not partValues:
            return returnStr
        
        if partType.value == NamePartType.PREFIX.value:
            for item in nameArray:
                if item in partValues:
                    returnStr = item
                    break
        
        if partType.value == NamePartType.SUFFIX.value:
            for i in range(len(nameArray) - 1, -1, -1):
                if nameArray[i] in partValues:
                    returnStr = nameArray[i]
                    break
        
        if partType.value == NamePartType.INDEX.value:
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
        지정된 namePart에 해당하는 부분을 문자열에서 추출
        
        Args:
            namePart: 추출할 namePart 이름 ("Base", "Type", "Side" 등)
            inStr: 처리할 문자열
            
        Returns:
            지정된 namePart에 해당하는 문자열
        """
        nameArray = self._split_to_array(inStr)
        returnStr = ""
        
        partType = self.get_name_part(inNamePartName).get_type()
        
        foundName = self.pick_name(inNamePartName, inStr)
        if foundName == "":
            return returnStr
        partIndex = self.get_name_part_index(inNamePartName)
        foundIndex = nameArray.index(foundName)
        
        if partType.value == NamePartType.PREFIX.value:
            if foundIndex >= 0:
                prevNameParts = self._nameParts[:partIndex]
                prevNames = [self.pick_name(part.get_name(), inStr) for part in prevNameParts]
                prevNamesInNameArray = nameArray[:foundIndex]
                for prevName in prevNames:
                    if prevName in prevNamesInNameArray:
                        prevNamesInNameArray.remove(prevName)
                if len(prevNamesInNameArray) == 0 :
                    returnStr = foundName
    
        if partType.value == NamePartType.SUFFIX.value:
            if foundIndex >= 0:
                nextNameParts = self._nameParts[partIndex + 1:]
                nextNames = [self.pick_name(part.get_name(), inStr) for part in nextNameParts]
                nextNamesInNameArray = nameArray[foundIndex + 1:]
                for nextName in nextNames:
                    if nextName in nextNamesInNameArray:
                        nextNamesInNameArray.remove(nextName)
                if len(nextNamesInNameArray) == 0 :
                    returnStr = foundName
    
        if partType.value == NamePartType.INDEX.value:
            returnStr = self.pick_name(inNamePartName, inStr)
                
        return returnStr
    
    def combine(self, inPartsDict={}, inFilChar=" "):
        """
        namingConfig에서 정의된 nameParts와 그 순서에 따라 이름 부분들을 조합하여 완전한 이름 생성
        
        Args:
            parts_dict: namePart 이름과 값의 딕셔너리 (예: {"Base": "b", "Type": "P", "Side": "L"})
            inFilChar: 구분자 문자 (기본값: " ")
            
        Returns:
            조합된 이름 문자열
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
        newName = self.set_index_padding_num(newName)
        return newName
    
    def get_RealName(self, inStr):
        """
        문자열에서 실제 이름 부분 추출
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            실제 이름 부분 문자열
        """
        filChar = self._get_filtering_char(inStr)
        nameArray = self._split_to_array(inStr)
        
        # 모든 nameParts 중 RealName이 아닌 것들의 값을 수집
        nonRealNameArray = []
        for part in self._nameParts:
            partName = part.get_name()
            partType = part.get_type()
            if partType.value != NamePartType.REALNAME.value:
                foundName = self.get_name(partName, inStr)
                nonRealNameArray.append(foundName)
        
        for item in nonRealNameArray:
            if item in nameArray:
                nameArray.remove(item)
                
        # 구분자로 결합
        return self._combine(nameArray, filChar)

    def get_non_RealName(self, inStr):
        """
        실제 이름 부분을 제외한 이름 가져오기
        
        Args:
            inStr: 처리할 이름 문자열
            
        Returns:
            실제 이름이 제외된 이름 문자열
        """
        filChar = self._get_filtering_char(inStr)
        
        # 모든 nameParts 중 RealName이 아닌 것들의 값을 수집
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
        문자열 이름을 이름 부분 배열로 변환
        
        Args:
            inStr: 변환할 이름 문자열
            
        Returns:
            이름 부분 배열 (Base, Type, Side, FrontBack, RealName, Index, Nub 등)
        """
        returnArray = [""] * len(self._nameParts)
        
        # 각 namePart에 대해 처리
        for i, part in enumerate(self._nameParts):
            partName = part.get_name()
            
            # 특수 케이스인 RealName은 마지막에 처리하기 위해 저장
            if partName == "RealName":
                realNameIndex = i
                continue
                
            # get_name 메소드를 사용하여 해당 부분 추출
            partValue = self.get_name(partName, inStr)
            returnArray[i] = partValue
        
        # 마지막으로 RealName 처리 (다른 모든 부분을 찾은 후에 수행해야 함)
        if 'realNameIndex' in locals():
            realNameStr = self.get_RealName(inStr)
            returnArray[realNameIndex] = realNameStr
        
        return returnArray
    
    def convert_to_dictionary(self, inStr):
        """
        문자열 이름을 이름 부분 딕셔너리로 변환
        
        Args:
            inStr: 변환할 이름 문자열
            
        Returns:
            이름 부분 딕셔너리 (키: namePart 이름, 값: 추출된 값)
            예: {"Base": "b", "Type": "P", "Side": "L", "RealName": "Arm", ...}
        """
        returnDict = {}
        
        # 각 namePart에 대해 처리
        for part in self._nameParts:
            partName = part.get_name()
            
            # 특수 케이스인 RealName은 마지막에 처리하기 위해 저장
            if partName == "RealName":
                continue
                
            # get_name 메소드를 사용하여 해당 부분 추출
            partValue = self.get_name(partName, inStr)
            returnDict[partName] = partValue
        
        # 마지막으로 RealName 처리 (다른 모든 부분을 찾은 후에 수행해야 함)
        realNameStr = self.get_RealName(inStr)
        returnDict["RealName"] = realNameStr
        
        return returnDict
    
    def convert_to_description(self, inStr):
        """
        문자열 이름을 설명으로 변환
        
        Args:
            inStr: 변환할 이름 문자열
            
        Returns:
            설명 문자열 (예: "b_P_L_Arm")
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

                descriptionDic[namePartName] = desc # Store in dictionary for later use

            descName = self.combine(descriptionDic, filteringChar)
        
        return descName
    
    def convert_to_korean_description(self, inStr):
        """
        문자열 이름을 한국어 설명으로 변환
        
        Args:
            inStr: 변환할 이름 문자열
            
        Returns:
            한국어 설명 문자열 (예: "팔_왼쪽_팔")
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

                korDescDic[namePartName] = korDesc # Store in dictionary for later use

            korDescName = self.combine(korDescDic, filteringChar)
        
        return korDescName
    
    def has_name_part(self, inPart, inStr):
        """
        문자열에 특정 namePart가 포함되어 있는지 확인
        
        Args:
            inPart: 확인할 namePart 이름 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
            inStr: 확인할 문자열
            
        Returns:
            포함되어 있으면 True, 아니면 False
        """
        return self.get_name(inPart, inStr) != ""
    
    def add_prefix_to_name_part(self, inPart, inStr, inPrefix):
        """
        이름의 특정 부분에 접두사 추가
        
        Args:
            inPart: 수정할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
            inStr: 처리할 이름 문자열
            inPrefix: 추가할 접두사
            
        Returns:
            수정된 이름 문자열
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
        이름의 특정 부분에 접미사 추가
        
        Args:
            inPart: 수정할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
            inStr: 처리할 이름 문자열
            inSuffix: 추가할 접미사
            
        Returns:
            수정된 이름 문자열
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
        실제 이름 부분에 접두사 추가
        
        Args:
            inStr: 처리할 이름 문자열
            inPrefix: 추가할 접두사
            
        Returns:
            수정된 이름 문자열
        """
        return self.add_prefix_to_name_part("RealName", inStr, inPrefix)

    def add_suffix_to_real_name(self, inStr, inSuffix):
        """
        실제 이름 부분에 접미사 추가
        
        Args:
            inStr: 처리할 이름 문자열
            inSuffix: 추가할 접미사
            
        Returns:
            수정된 이름 문자열
        """
        return self.add_suffix_to_name_part("RealName", inStr, inSuffix)
    
    def convert_digit_into_padding_string(self, inDigit, inPaddingNum=None):
        """
        숫자를 패딩된 문자열로 변환
        
        Args:
            inDigit: 변환할 숫자 또는 숫자 문자열
            inPaddingNum: 패딩 자릿수 (기본값: 클래스의 _paddingNum)
            
        Returns:
            패딩된 문자열
        """
        if inPaddingNum is None:
            inPaddingNum = self._paddingNum
            
        digitNum = 0
        
        if isinstance(inDigit, int):
            digitNum = inDigit
        elif isinstance(inDigit, str):
            if inDigit.isdigit():
                digitNum = int(inDigit)
                
        # Python의 문자열 포맷팅을 사용하여 패딩
        return f"{digitNum:0{inPaddingNum}d}"

    def set_index_padding_num(self, inStr, inPaddingNum=None):
        """
        이름의 인덱스 부분 패딩 설정
        
        Args:
            inStr: 처리할 이름 문자열
            inPaddingNum: 설정할 패딩 자릿수 (기본값: 클래스의 _paddingNum)
            
        Returns:
            패딩이 적용된 이름 문자열
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
        이름의 인덱스 부분 패딩 자릿수 가져오기
        
        Args:
            inStr: 처리할 이름 문자열
            
        Returns:
            인덱스 패딩 자릿수
        """
        indexVal = self.get_name("Index", inStr)
        
        if indexVal:
            return len(indexVal)
            
        return 1

    def increase_index(self, inStr, inAmount):
        """
        이름의 인덱스 부분 값 증가
        
        Args:
            inStr: 처리할 이름 문자열
            inAmount: 증가시킬 값
            
        Returns:
            인덱스가 증가된 이름 문자열
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
            
            # Python의 문자열 포맷팅을 사용하여 패딩
            indexStr = f"{indexNum:0{indexPaddingNum}d}"
            nameArray[indexIndex] = indexStr
            newName = self._combine(nameArray, filChar)
            newName = self.set_index_padding_num(newName)
            
        return newName

    def get_index_as_digit(self, inStr):
        """
        이름의 인덱스를 숫자로 변환
        
        Args:
            inStr: 변환할 이름 문자열
            
        Returns:
            숫자로 변환된 인덱스 (넙이 있으면 -1, 인덱스가 없으면 False)
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
        이름 배열을 인덱스 기준으로 정렬
        
        Args:
            inNameArray: 정렬할 이름 배열
            
        Returns:
            인덱스 기준으로 정렬된 이름 배열
        """
        if not inNameArray:
            return []
            
        # 정렬을 위한 보조 클래스 정의
        @dataclass
        class IndexSorting:
            oriIndex: int
            newIndex: int
                
        # 각 이름의 인덱스를 추출하여 정렬 정보 생성
        structArray = []
        
        for i, name in enumerate(inNameArray):
            tempIndex = self.get_index_as_digit(name)
            
            if tempIndex is False:
                structArray.append(IndexSorting(i, 0))
            else:
                structArray.append(IndexSorting(i, tempIndex))
                
        # 인덱스 기준으로 정렬
        structArray.sort(key=lambda x: x.newIndex)
        
        # 정렬된 순서로 결과 배열 생성
        sortedNameArray = []
        for struct in structArray:
            sortedNameArray.append(inNameArray[struct.oriIndex])
            
        return sortedNameArray
    
    def get_string(self, inStr):
        """
        인덱스 부분을 제외한 이름 문자열 가져오기
        
        Args:
            inStr: 처리할 이름 문자열
            
        Returns:
            인덱스가 제외된 이름 문자열
        """
        filChar = self._get_filtering_char(inStr)
        nameArray = self.convert_name_to_array(inStr)
        indexOrder = self.get_name_part_index("Index")
        
        # 인덱스 부분 제거
        returnNameArray = nameArray.copy()
        returnNameArray[indexOrder] = ""
        
        return self._combine(returnNameArray, filChar)

    def gen_mirroring_name(self, inStr):
        """
        미러링된 이름 생성 (측면 또는 앞/뒤 변경)
        
        이름에서 Side와 FrontBack namePart를 자동으로 검색하고,
        발견된 값의 semanticmapping weight와 가장 차이가 큰 값으로 교체합니다.
        
        Args:
            inStr: 처리할 이름 문자열
            
        Returns:
            미러링된 이름 문자열
        """
        nameArray = self.convert_name_to_array(inStr)
            
        for part in self._nameParts:
            partName = part.get_name()
            partType = part.get_type()
            if (partType.value != NamePartType.REALNAME.value and partType.value != NamePartType.INDEX.value) and part.is_direction():
                partIndex = self.get_name_part_index(partName)
                foundName = self.get_name(partName, inStr)
                opositeName = part.get_most_different_weight_value(foundName)
                if opositeName and foundName != opositeName:
                    nameArray[partIndex] = opositeName
    
        returnName = self._combine(nameArray, self._get_filtering_char(inStr))
        
        return returnName

    def replace_filtering_char(self, inStr, inNewFilChar):
        """
        이름의 구분자 문자 변경
        
        Args:
            inStr: 처리할 이름 문자열
            inNewFilChar: 새 구분자 문자
            
        Returns:
            구분자가 변경된 이름 문자열
        """
        nameArray = self.convert_name_to_array(inStr)
        return self._combine(nameArray, inNewFilChar)

    def replace_name_part(self, inPart, inStr, inNewName):
        """
        이름의 특정 부분을 새 이름으로 변경
        
        Args:
            inPart: 수정할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
            inStr: 처리할 이름 문자열
            inNewName: 새 이름
        
        Returns:
            수정된 이름 문자열
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
        이름의 특정 부분 제거
        
        Args:
            inPart: 제거할 부분 ("Base", "Type", "Side", "FrontBack", "RealName", "Index")
            inStr: 처리할 이름 문자열
            
        Returns:
            수정된 이름 문자열
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
        설정 파일에서 설정 로드
        
        Args:
            configPath: 설정 파일 경로 (기본값: self._configPath)
            
        Returns:
            로드 성공 여부 (True/False)
        """
        # 경로가 없으면 인스턴스 생성 시 설정된 경로 사용
        if not configPath:
            configPath = self._configPath
            
        if not configPath:
            print("설정 파일 경로가 제공되지 않았습니다.")
            return False
            
        # NamingConfig 인스턴스 생성 및 설정 로드
        config = NamingConfig()
        if config.load(configPath):
            # 설정을 Naming 인스턴스에 적용
            result = config.apply_to_naming(self)
            if result:
                self._configPath = configPath  # 성공적으로 로드한 경로 저장
            return result
        else:
            print(f"설정 파일 로드 실패: {configPath}")
            return False
    
    def load_default_config(self):
        """
        기본 설정 로드 (현재는 아무 작업도 수행하지 않음)
        
        Returns:
            항상 True 반환 (기본 설정은 __init__에서 이미 설정됨)
        """
        # 이 메소드는 현재 __init__에서 설정한 기본값을 그대로 사용하므로
        # 아무 작업도 수행하지 않습니다.
        return True

    def get_config_path(self):
        """
        현재 설정 파일 경로 가져오기
        
        Returns:
            설정 파일 경로 (없으면 빈 문자열)
        """
        return self._configPath or ""
