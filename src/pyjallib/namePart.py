#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# namePart 모듈

이름의 각 부분을 체계적으로 표현하고 관리하는 모듈입니다.

## 주요 기능
- 이름 부분(name part)의 유형 정의 (PREFIX, SUFFIX, REALNAME, INDEX)
- 사전 정의된 값과 가중치 매핑 관리
- 이름 부분에 대한 설명(영문/한글) 관리
- 값 유효성 검증 및 조회 기능

## 클래스
- NamePartType: 이름 부분의 유형을 정의하는 열거형 클래스
- NamePart: 이름 부분을 관리하는 주요 클래스, 값과 설명, 가중치 등을 처리
"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum, auto

class NamePartType(Enum):
    """
    이름 부분(name part)의 유형을 정의하는 열거형 클래스.
    
    - PREFIX: RealName 앞에 오는 부분, 사전 정의 값 필수
    - SUFFIX: RealName 뒤에 오는 부분, 사전 정의 값 필수
    - REALNAME: 실제 이름 부분, 자유 텍스트 가능
    - INDEX: 숫자만 허용되는 부분
    - UNDEFINED: 정의되지 않은 타입 (기본값)
    """
    PREFIX = auto()
    SUFFIX = auto()
    REALNAME = auto()
    INDEX = auto()
    UNDEFINED = auto()

class NamePart:
    """
    # NamePart 클래스
    
    이름의 각 구성 부분(name part)을 관리하는 클래스입니다.
    
    ## 주요 기능
    - 이름 부분의 타입(PREFIX, SUFFIX, REALNAME, INDEX) 관리
    - 사전 정의된 값 목록 관리 및 가중치 자동 할당
    - 값에 대한 영문/한글 설명 관리
    - 값의 유효성 검증 및 조회 기능
    - 직렬화(to_dict)와 역직렬화(from_dict) 지원
    
    ## 사용 예시
    ```python
    # Side 이름 부분 생성 (PREFIX 타입)
    side = NamePart("Side", NamePartType.PREFIX, ["L", "R"], ["Left", "Right"])
    
    # 값 추가 및 설명 설정
    side.add_predefined_value("M", "Middle", "중앙")
    
    # 값 유효성 검증
    is_valid = side.validate_value("L")  # True
    ```
    """
    
    def __init__(self, inName="", inType=NamePartType.UNDEFINED, inPredefinedValues=None, inDescriptions=None, inIsDirection=False, inKoreanDescriptions=None):
        """
        NamePart 클래스 초기화
        
        ## Parameters
        - inName (str): 이름 부분의 이름 (예: "Base", "Type", "Side" 등)
        - inType (NamePartType): NamePart의 타입 (NamePartType 열거형 값)
        - inPredefinedValues (list): 사전 선언된 값 목록 (기본값: None, 빈 리스트로 초기화)
        - inDescriptions (list): 사전 선언된 값들의 설명 목록 (기본값: None, 빈 리스트로 초기화)
        - inIsDirection (bool): 방향성 여부 (기본값: False)
        - inKoreanDescriptions (list): 사전 선언된 값들의 한국어 설명 목록 (기본값: None, 빈 리스트로 초기화)
        """
        self._name = inName
        self._predefinedValues = inPredefinedValues if inPredefinedValues is not None else []
        self._weights = []
        self._type = inType
        self._descriptions = inDescriptions if inDescriptions is not None else [""] * len(self._predefinedValues)
        self._koreanDescriptions = inKoreanDescriptions if inKoreanDescriptions is not None else [""] * len(self._predefinedValues) # Add korean descriptions
        self._isDirection = inIsDirection if inIsDirection is True else False  # 방향성 여부 (기본값: False)
        
        # 길이 일치 확인 (Descriptions)
        if len(self._descriptions) < len(self._predefinedValues):
            self._descriptions.extend([""] * (len(self._predefinedValues) - len(self._descriptions)))
        elif len(self._descriptions) > len(self._predefinedValues):
            self._descriptions = self._descriptions[:len(self._predefinedValues)]

        # 길이 일치 확인 (Korean Descriptions)
        if len(self._koreanDescriptions) < len(self._predefinedValues):
            self._koreanDescriptions.extend([""] * (len(self._predefinedValues) - len(self._koreanDescriptions)))
        elif len(self._koreanDescriptions) > len(self._predefinedValues):
            self._koreanDescriptions = self._koreanDescriptions[:len(self._predefinedValues)]
        
        # 타입에 따른 기본 값 설정
        self._initialize_type_defaults()
        self._update_weights()
    
    def _initialize_type_defaults(self):
        """
        타입에 따른 기본 설정을 초기화합니다.
        """
        if self._type == NamePartType.INDEX:
            # Index 타입은 숫자만 처리하므로 predefined values는 사용하지 않음
            self._predefinedValues = []
            self._descriptions = []
            self._koreanDescriptions = [] # Clear korean descriptions
            self._weights = []
        elif self._type == NamePartType.REALNAME:
            # RealName 타입은 predefined values를 사용하지 않음
            self._predefinedValues = []
            self._descriptions = []
            self._koreanDescriptions = [] # Clear korean descriptions
            self._weights = []
    
    def _update_weights(self):
        """
        predefined values의 순서에 따라 자동으로 가중치를 설정합니다.
        값들은 5부터 시작해서 5씩 증가하는 가중치를 갖습니다.
        """
        # REALNAME이나 INDEX 타입인 경우 weights를 사용하지 않음
        if self._type == NamePartType.REALNAME or self._type == NamePartType.INDEX:
            self._weights = []
            return
            
        self._weights = []
        # 가중치는 5부터 시작해서 5씩 증가 (순서대로 내림차순 가중치)
        num_values = len(self._predefinedValues)
        for i in num_values:
            weight_value = 5 * (i + 1)  # 내림차순 가중치
            self._weights.append(weight_value)
    
    def set_name(self, inName):
        """
        이름 부분의 이름을 설정합니다.
        
        ## Parameters
        - inName (str): 설정할 이름
        """
        self._name = inName
    
    def get_name(self):
        """
        이름 부분의 이름을 반환합니다.
        
        ## Returns
        - str: 이름 부분의 이름
        """
        return self._name
    
    def set_type(self, inType):
        """
        이름 부분의 타입을 설정합니다.
        
        ## Parameters
        - inType (NamePartType): 설정할 타입 (NamePartType 열거형 값)
        """
        self._type = inType
        self._initialize_type_defaults()
        self._update_weights()
    
    def get_type(self):
        """
        이름 부분의 타입을 반환합니다.
        
        ## Returns
        - NamePartType: 이름 부분의 타입 (NamePartType 열거형 값)
        """
        return self._type
    
    def is_prefix(self):
        """
        이름 부분이 PREFIX 타입인지 확인합니다.
        
        ## Returns
        - bool: PREFIX 타입이면 True, 아니면 False
        """
        return self._type == NamePartType.PREFIX
    
    def is_suffix(self):
        """
        이름 부분이 SUFFIX 타입인지 확인합니다.
        
        ## Returns
        - bool: SUFFIX 타입이면 True, 아니면 False
        """
        return self._type == NamePartType.SUFFIX
    
    def is_realname(self):
        """
        이름 부분이 REALNAME 타입인지 확인합니다.
        
        ## Returns
        - bool: REALNAME 타입이면 True, 아니면 False
        """
        return self._type == NamePartType.REALNAME
    
    def is_index(self):
        """
        이름 부분이 INDEX 타입인지 확인합니다.
        
        ## Returns
        - bool: INDEX 타입이면 True, 아니면 False
        """
        return self._type == NamePartType.INDEX
    
    def add_predefined_value(self, inValue, inDescription="", inKoreanDescription=""):
        """
        사전 선언된 값 목록에 새 값을 추가합니다.
        
        ## Parameters
        - inValue (str): 추가할 값
        - inDescription (str): 추가할 값에 대한 설명 (기본값: 빈 문자열)
        - inKoreanDescription (str): 추가할 값에 대한 한국어 설명 (기본값: 빈 문자열)
            
        ## Returns
        - bool: 추가 성공 여부 (이미 존재하는 경우 False)
        """
        if self._type == NamePartType.REALNAME or self._type == NamePartType.INDEX:
            return False
            
        if inValue not in self._predefinedValues:
            self._predefinedValues.append(inValue)
            self._descriptions.append(inDescription)
            self._koreanDescriptions.append(inKoreanDescription) # Add korean description
            self._update_weights()  # 가중치 자동 업데이트
            return True
        return False
    
    def remove_predefined_value(self, inValue):
        """
        사전 선언된 값 목록에서 값을 제거합니다.
        
        ## Parameters
        - inValue (str): 제거할 값
            
        ## Returns
        - bool: 제거 성공 여부 (존재하지 않는 경우 False)
        """
        if inValue in self._predefinedValues:
            index = self._predefinedValues.index(inValue)
            self._predefinedValues.remove(inValue)
            self._descriptions.pop(index)
            self._koreanDescriptions.pop(index) # Remove korean description
            if index < len(self._weights):
                self._weights.pop(index)
            self._update_weights()  # 가중치 자동 업데이트
            return True
        return False
    
    def set_predefined_values(self, inValues, inDescriptions=None, inKoreanDescriptions=None):
        """
        사전 선언된 값 목록을 설정합니다.
        
        ## Parameters
        - inValues (list): 설정할 값 목록
        - inDescriptions (list): 설정할 값들의 설명 목록 (기본값: None, 빈 문자열로 초기화)
        - inKoreanDescriptions (list): 설정할 값들의 한국어 설명 목록 (기본값: None, 빈 문자열로 초기화)
        """
        if self._type == NamePartType.REALNAME or self._type == NamePartType.INDEX:
            return
            
        self._predefinedValues = inValues.copy() if inValues else []
        
        if inDescriptions:
            self._descriptions = inDescriptions.copy()
            if len(self._descriptions) < len(self._predefinedValues):
                self._descriptions.extend([""] * (len(self._predefinedValues) - len(self._descriptions)))
            elif len(self._descriptions) > len(self._predefinedValues):
                self._descriptions = self._descriptions[:len(self._predefinedValues)]
        else:
            self._descriptions = [""] * len(self._predefinedValues)

        if inKoreanDescriptions:
            self._koreanDescriptions = inKoreanDescriptions.copy()
            if len(self._koreanDescriptions) < len(self._predefinedValues):
                self._koreanDescriptions.extend([""] * (len(self._predefinedValues) - len(self._koreanDescriptions)))
            elif len(self._koreanDescriptions) > len(self._predefinedValues):
                self._koreanDescriptions = self._koreanDescriptions[:len(self._predefinedValues)]
        else:
            self._koreanDescriptions = [""] * len(self._predefinedValues)
        
        self._update_weights()
    
    def get_predefined_values(self):
        """
        사전 선언된 값 목록을 반환합니다.
        
        ## Returns
        - list: 사전 선언된 값 목록
        """
        return self._predefinedValues.copy()
    
    def contains_value(self, inValue):
        """
        특정 값이 사전 선언된 값 목록에 있는지 확인합니다.
        
        ## Parameters
        - inValue (str): 확인할 값
            
        ## Returns
        - bool: 값이 존재하면 True, 아니면 False
        """
        if self._type == NamePartType.INDEX:
            return isinstance(inValue, str) and inValue.isdigit()
            
        return inValue in self._predefinedValues
    
    def get_value_at_index(self, inIndex):
        """
        지정된 인덱스의 사전 선언된 값을 반환합니다.
        
        ## Parameters
        - inIndex (int): 값의 인덱스
            
        ## Returns
        - str or None: 값 (인덱스가 범위를 벗어나면 None)
        """
        if 0 <= inIndex < len(self._predefinedValues):
            return self._predefinedValues[inIndex]
        return None
    
    def get_value_count(self):
        """
        사전 선언된 값의 개수를 반환합니다.
        
        ## Returns
        - int: 값 개수
        """
        return len(self._predefinedValues)
    
    def clear_predefined_values(self):
        """
        모든 사전 선언된 값을 제거합니다.
        """
        if self._type == NamePartType.REALNAME or self._type == NamePartType.INDEX:
            return
            
        self._predefinedValues.clear()
        self._descriptions.clear()
        self._koreanDescriptions.clear() # Clear korean descriptions
        self._weights.clear()  # 가중치도 초기화
    
    def get_value_by_weight(self, inRank=0):
        """
        지정된 가중치에 해당하는 값을 반환합니다.
        
        ## Parameters
        - inRank (int): 찾을 가중치 값 (기본값: 0)
            
        ## Returns
        - str: 해당 가중치의 값, 없으면 빈 문자열
        """
        returnStr = ""
        if len(self._predefinedValues) != len(self._weights) or len(self._predefinedValues) <= 0:
            return returnStr
        foundIndex = self._weights.index(inRank)
        returnStr = self._predefinedValues[foundIndex] if foundIndex >= 0 else self._predefinedValues[0]
        
        return returnStr
    
    def get_most_different_weight_value(self, inValue):
        """
        주어진 값의 가중치와 가장 차이가 큰 값을 반환합니다.
        
        ## Parameters
        - inValue (str): 기준이 되는 값
            
        ## Returns
        - str: 가중치 차이가 가장 큰 값, 없으면 빈 문자열
        """
        if len(self._predefinedValues) != len(self._weights) or len(self._predefinedValues) <= 0:
            return ""
            
        if inValue not in self._predefinedValues:
            return ""
            
        index = self._predefinedValues.index(inValue)
        currentWeight = self._weights[index]
            
        maxDiff = -1
        maxDiffValue = ""
        
        for i, predValue in enumerate(self._predefinedValues):
            if predValue == inValue:
                continue
                
            predWeight = self._weights[i] if i < len(self._weights) else 0
            diff = abs(currentWeight - predWeight)
            if diff > maxDiff:
                maxDiff = diff
                maxDiffValue = predValue
                
        return maxDiffValue
    
    def get_value_by_min_weight(self):
        """
        가중치가 가장 낮은 값을 반환합니다.
        
        ## Returns
        - str: 가중치가 가장 낮은 값, 없으면 빈 문자열
        """
        if len(self._predefinedValues) != len(self._weights) or len(self._predefinedValues) <= 0:
            return ""
        return self._predefinedValues[0]
    
    def get_value_by_max_weight(self):
        """
        가중치가 가장 높은 값을 반환합니다.
        
        ## Returns
        - str: 가중치가 가장 높은 값, 없으면 빈 문자열
        """
        if len(self._predefinedValues) != len(self._weights) or len(self._predefinedValues) <= 0:
            return ""
        return self._predefinedValues[-1]
    
    def validate_value(self, inValue):
        """
        값이 이 NamePart 타입에 유효한지 검증합니다.
        
        ## Parameters
        - inValue (str): 검증할 값
            
        ## Returns
        - bool: 유효하면 True, 아니면 False
        """
        if self._type == NamePartType.INDEX:
            return isinstance(inValue, str) and inValue.isdigit()
            
        if (self._type == NamePartType.PREFIX or self._type == NamePartType.SUFFIX) and self._predefinedValues:
            return inValue in self._predefinedValues
            
        if self._type == NamePartType.REALNAME:
            return isinstance(inValue, str)
            
        return True
    
    def set_description(self, inValue, inDescription):
        """
        특정 predefined value의 설명을 설정합니다.
        
        ## Parameters
        - inValue (str): 설명을 설정할 값
        - inDescription (str): 설정할 설명
            
        ## Returns
        - bool: 설정 성공 여부 (값이 존재하지 않는 경우 False)
        """
        if inValue in self._predefinedValues:
            index = self._predefinedValues.index(inValue)
            self._descriptions[index] = inDescription
            return True
        return False
    
    def get_description_by_value(self, inValue):
        """
        특정 predefined value의 설명을 반환합니다.
        
        ## Parameters
        - inValue (str): 설명을 가져올 값
            
        ## Returns
        - str: 해당 값의 설명, 값이 존재하지 않으면 빈 문자열
        """
        if inValue in self._predefinedValues:
            index = self._predefinedValues.index(inValue)
            return self._descriptions[index]
        return ""
    
    def get_descriptions(self):
        """
        모든 설명을 반환합니다.
        
        ## Returns
        - list: 설명 목록
        """
        return self._descriptions.copy()
    
    def get_value_by_description(self, inDescription):
        """
        특정 설명에 해당하는 값을 반환합니다.
        
        ## Parameters
        - inDescription (str): 찾을 설명
            
        ## Returns
        - str: 해당 설명의 값, 없으면 빈 문자열
        """
        if inDescription in self._descriptions:
            index = self._descriptions.index(inDescription)
            return self._predefinedValues[index]
        return ""
    
    def get_value_with_description(self, inIndex):
        """
        지정된 인덱스의 값과 설명을 튜플로 반환합니다.
        
        ## Parameters
        - inIndex (int): 값의 인덱스
            
        ## Returns
        - tuple: (값, 설명) 튜플, 인덱스가 범위를 벗어나면 (None, None)
        """
        if 0 <= inIndex < len(self._predefinedValues):
            return (self._predefinedValues[inIndex], self._descriptions[inIndex])
        return (None, None)
    
    def get_values_with_descriptions(self):
        """
        모든 값과 설명의 튜플 리스트를 반환합니다.
        
        ## Returns
        - list: (값, 설명) 튜플의 리스트
        """
        return list(zip(self._predefinedValues, self._descriptions))

    def set_korean_description(self, inValue, inKoreanDescription):
        """
        특정 predefined value의 한국어 설명을 설정합니다.
        
        ## Parameters
        - inValue (str): 설명을 설정할 값
        - inKoreanDescription (str): 설정할 한국어 설명
            
        ## Returns
        - bool: 설정 성공 여부 (값이 존재하지 않는 경우 False)
        """
        if inValue in self._predefinedValues:
            index = self._predefinedValues.index(inValue)
            self._koreanDescriptions[index] = inKoreanDescription
            return True
        return False
    
    def get_korean_description_by_value(self, inValue):
        """
        특정 predefined value의 한국어 설명을 반환합니다.
        
        ## Parameters
        - inValue (str): 설명을 가져올 값
            
        ## Returns
        - str: 해당 값의 한국어 설명, 값이 존재하지 않으면 빈 문자열
        """
        if inValue in self._predefinedValues:
            index = self._predefinedValues.index(inValue)
            return self._koreanDescriptions[index]
        return ""
    
    def get_korean_descriptions(self):
        """
        모든 한국어 설명을 반환합니다.
        
        ## Returns
        - list: 한국어 설명 목록
        """
        return self._koreanDescriptions.copy()
    
    def get_value_by_korean_description(self, inKoreanDescription):
        """
        특정 한국어 설명에 해당하는 값을 반환합니다.
        
        ## Parameters
        - inKoreanDescription (str): 찾을 한국어 설명
            
        ## Returns
        - str: 해당 설명의 값, 없으면 빈 문자열
        """
        if inKoreanDescription in self._koreanDescriptions:
            index = self._koreanDescriptions.index(inKoreanDescription)
            return self._predefinedValues[index]
        return ""
    
    def get_value_with_korean_description(self, inIndex):
        """
        지정된 인덱스의 값과 한국어 설명을 튜플로 반환합니다.
        
        ## Parameters
        - inIndex (int): 값의 인덱스
            
        ## Returns
        - tuple: (값, 한국어 설명) 튜플, 인덱스가 범위를 벗어나면 (None, None)
        """
        if 0 <= inIndex < len(self._predefinedValues):
            return (self._predefinedValues[inIndex], self._koreanDescriptions[inIndex])
        return (None, None)
    
    def get_values_with_korean_descriptions(self):
        """
        모든 값과 한국어 설명의 튜플 리스트를 반환합니다.
        
        ## Returns
        - list: (값, 한국어 설명) 튜플의 리스트
        """
        return list(zip(self._predefinedValues, self._koreanDescriptions))
    
    def is_direction(self):
        """
        방향성 여부를 반환합니다.
        
        ## Returns
        - bool: 방향성 여부 (True/False)
        """
        return self._isDirection
    
    def to_dict(self):
        """
        NamePart 객체를 사전 형태로 변환합니다.
        
        ## Returns
        - dict: 사전 형태의 NamePart 정보
        """
        return {
            "name": self._name,
            "predefinedValues": self._predefinedValues.copy(),
            "weights": self._weights.copy(),  # 가중치를 리스트 형태로 직접 전달
            "type": self._type.name if hasattr(self._type, 'name') else str(self._type),
            "descriptions": self._descriptions.copy(),
            "koreanDescriptions": self._koreanDescriptions.copy(), # Add korean descriptions
            "isDirection": self._isDirection
        }
    
    @staticmethod
    def from_dict(inData):
        """
        사전 형태의 데이터로부터 NamePart 객체를 생성합니다.
        
        ## Parameters
        - inData (dict): 사전 형태의 NamePart 정보
            - name: 이름 부분의 이름
            - type: 타입 문자열
            - predefinedValues: 사전 정의된 값 목록
            - descriptions: 설명 목록
            - isDirection: 방향성 여부
            - koreanDescriptions: 한국어 설명 목록
            
        ## Returns
        - NamePart: 생성된 NamePart 객체
            - 유효하지 않은 데이터인 경우 빈 NamePart 객체 반환
        """
        if isinstance(inData, dict) and "name" in inData:
            type_str = inData.get("type", "UNDEFINED")
            try:
                part_type = NamePartType[type_str] if isinstance(type_str, str) else NamePartType.UNDEFINED
            except KeyError:
                part_type = NamePartType.UNDEFINED
                
            result = NamePart(
                inData["name"],
                part_type,
                inData.get("predefinedValues", []),
                inData.get("descriptions", []),
                inData.get("isDirection", False),
                inData.get("koreanDescriptions", [])
            )
            
            return result
        return NamePart()