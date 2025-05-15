#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 3ds Max 이름 처리 모듈

3ds Max 객체의 이름을 체계적으로 관리하고 변환하는 기능을 제공하는 모듈입니다.

## 주요 기능
- Naming 클래스 기능을 3ds Max에 특화된 형태로 확장
- 3ds Max 객체 이름 생성 및 관리
- 객체 이름의 패턴 매칭 및 변환
- 미러링, 고유 이름 생성 등 Max 워크플로우 지원

## 구현 정보
- pyjallib의 Naming 클래스를 상속하여 3ds Max 특화 기능 제공
- pymxs 모듈을 통해 3ds Max API 접근
"""

import os

from pymxs import runtime as rt
from pyjallib.naming import Naming
from pyjallib.namePart import NamePart, NamePartType

class Name(Naming):
    """
    # Name 클래스
    
    3ds Max 객체의 이름을 관리하는 클래스입니다.
    
    ## 주요 기능
    - Naming 클래스를 상속하여 3ds Max 특화 이름 관리 기능 제공
    - Max 객체 이름 규칙 적용 및 추출
    - 객체 타입별 특수 네이밍 처리 (Dummy, IK, Target 등)
    - 고유 이름 생성 및 미러링 이름 처리
    
    ## 구현 정보
    - 3ds Max 이름 규칙에 따른 NamePart 확장
    - pymxs.runtime을 통한 Max 객체 접근 및 처리
    
    ## 사용 예시
    ```python
    # Name 객체 생성
    name = Name()
    
    # Type 부분 교체
    new_name = name.replace_Type(obj.name, "Jnt")
    
    # 고유 이름 생성
    unique_name = name.gen_unique_name("Bone_01")
    
    # 미러링 이름 생성
    mirrored_name = name.gen_mirroring_name("L_Arm_01")
    ```
    """
    
    def __init__(self, configPath=None):
        """
        Name 클래스를 초기화합니다.
        
        ## Parameters
        - configPath (str, optional): 설정 파일 경로 (기본값: None)
            - 설정 파일이 제공되면 해당 파일의 이름 규칙을 로드
            - 제공되지 않으면 기본 설정 파일(3DSMaxNamingConfig.json)을 사용
        """
        # 기본 설정값
        self._paddingNum = 2
        self._configPath = configPath
        
        # 기본 namePart 초기화 (각 부분에 사전 정의 값 직접 설정)
        self._nameParts = []
        
        if configPath:
            # 사용자가 지정한 설정 파일 사용
            self.load_from_config_file(configPath=configPath)
        else:
            configDir = os.path.join(os.path.dirname(__file__), "ConfigFiles")
            nameConfigDir = os.path.join(configDir, "3DSMaxNamingConfig.json")
            self.load_from_config_file(configPath=nameConfigDir)
    
    # NamePart 직접 액세스 메소드들
    def get_Base_values(self):
        """
        Base 부분의 사전 정의 값 목록을 반환합니다.
        
        ## Returns
        - list: Base 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Base")
    
    def get_Type_values(self):
        """
        Type 부분의 사전 정의 값 목록을 반환합니다.
        
        ## Returns
        - list: Type 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Type")
    
    def get_Side_values(self):
        """
        Side 부분의 사전 정의 값 목록을 반환합니다.
        
        ## Returns
        - list: Side 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Side")
    
    def get_FrontBack_values(self):
        """
        FrontBack 부분의 사전 정의 값 목록을 반환합니다.
        
        ## Returns
        - list: FrontBack 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("FrontBack")
    
    def get_Nub_values(self):
        """
        Nub 부분의 사전 정의 값 목록을 반환합니다.
        
        ## Returns
        - list: Nub 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Nub")
    
    # is_<NamePart 이름> 메소드들
    def is_Base(self, inStr):
        """
        문자열이 Base 부분의 사전 정의 값인지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Base 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Base", inStr)
    
    def is_Type(self, inStr):
        """
        문자열이 Type 부분의 사전 정의 값인지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Type 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Type", inStr)
    
    def is_Side(self, inStr):
        """
        문자열이 Side 부분의 사전 정의 값인지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Side 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Side", inStr)
    
    def is_FrontBack(self, inStr):
        """
        문자열이 FrontBack 부분의 사전 정의 값인지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: FrontBack 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("FrontBack", inStr)
    
    def is_Nub(self, inStr):
        """
        문자열이 Nub 부분의 사전 정의 값인지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Nub 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Nub", inStr)
    
    # has_<NamePart 이름> 메소드들
    def has_Base(self, inStr):
        """
        문자열에 Base 부분의 사전 정의 값이 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Base 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Base", inStr)
    
    def has_Type(self, inStr):
        """
        문자열에 Type 부분의 사전 정의 값이 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Type 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Type", inStr)
    
    def has_Side(self, inStr):
        """
        문자열에 Side 부분의 사전 정의 값이 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Side 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Side", inStr)
    
    def has_FrontBack(self, inStr):
        """
        문자열에 FrontBack 부분의 사전 정의 값이 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: FrontBack 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("FrontBack", inStr)
    
    def has_Nub(self, inStr):
        """
        문자열에 Nub 부분의 사전 정의 값이 포함되어 있는지 확인합니다.
        
        ## Parameters
        - inStr (str): 확인할 문자열
            
        ## Returns
        - bool: Nub 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Nub", inStr)
    
    # replace_<NamePart 이름> 메소드들
    def replace_Base(self, inStr, inNewName):
        """
        문자열의 Base 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("Base", inStr, inNewName)
    
    def replace_Type(self, inStr, inNewName):
        """
        문자열의 Type 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("Type", inStr, inNewName)
    
    def replace_Side(self, inStr, inNewName):
        """
        문자열의 Side 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("Side", inStr, inNewName)
    
    def replace_FrontBack(self, inStr, inNewName):
        """
        문자열의 FrontBack 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("FrontBack", inStr, inNewName)
    
    def replace_RealName(self, inStr, inNewName):
        """
        문자열의 RealName 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("RealName", inStr, inNewName)
    
    def replace_Index(self, inStr, inNewName):
        """
        문자열의 Index 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름 (숫자 문자열)
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("Index", inStr, inNewName)
    
    def replace_Nub(self, inStr, inNewName):
        """
        문자열의 Nub 부분을 새 이름으로 변경합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
        - inNewName (str): 새 이름
            
        ## Returns
        - str: 변경된 문자열
        """
        return self.replace_name_part("Nub", inStr, inNewName)
    
    # remove_<NamePart 이름> 메소드들
    def remove_Base(self, inStr):
        """
        문자열에서 Base 부분을 제거합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
            
        ## Returns
        - str: Base 부분이 제거된 문자열
        """
        return self.remove_name_part("Base", inStr)
    
    def remove_Type(self, inStr):
        """
        문자열에서 Type 부분을 제거합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
            
        ## Returns
        - str: Type 부분이 제거된 문자열
        """
        return self.remove_name_part("Type", inStr)
    
    def remove_Side(self, inStr):
        """
        문자열에서 Side 부분을 제거합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
            
        ## Returns
        - str: Side 부분이 제거된 문자열
        """
        return self.remove_name_part("Side", inStr)
    
    def remove_FrontBack(self, inStr):
        """
        문자열에서 FrontBack 부분을 제거합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
            
        ## Returns
        - str: FrontBack 부분이 제거된 문자열
        """
        return self.remove_name_part("FrontBack", inStr)
    
    def remove_Index(self, inStr):
        """
        문자열에서 Index 부분을 제거합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
            
        ## Returns
        - str: Index 부분이 제거된 문자열
        """
        return self.remove_name_part("Index", inStr)
    
    def remove_Nub(self, inStr):
        """
        문자열에서 Nub 부분을 제거합니다.
        
        ## Parameters
        - inStr (str): 처리할 문자열
            
        ## Returns
        - str: Nub 부분이 제거된 문자열
        """
        return self.remove_name_part("Nub", inStr)
    
    # pymxs 의존적인 메소드 구현
    def gen_unique_name(self, inStr):
        """
        고유한 이름을 생성합니다.
        
        ## Parameters
        - inStr (str): 기준 이름 문자열
            
        ## Returns
        - str: 고유한 이름 문자열
        
        ## 동작 방식
        1. 패턴 문자열 생성 (인덱스 부분을 '*'로 대체)
        2. pymxs를 사용하여 씬 내 모든 객체 이름과 패턴 매칭
        3. 일치하는 객체 수를 카운트하여 새 인덱스 적용
        """
        pattern_str = self.replace_Index(inStr, "*")
        
        # pymxs를 사용하여 객체 이름을 패턴과 매칭하여 검색
        matched_objects = []
        
        # 모든 객체 중에서 패턴과 일치하는 이름 찾기
        for obj in rt.objects:
            if rt.matchPattern(obj.name, pattern=pattern_str):
                matched_objects.append(obj)
                
        return self.replace_Index(inStr, str(len(matched_objects) + 1))
    
    def compare_name(self, inObjA, inObjB):
        """
        두 객체의 이름을 비교합니다(정렬용).
        
        ## Parameters
        - inObjA (MaxObject): 첫 번째 객체
        - inObjB (MaxObject): 두 번째 객체
            
        ## Returns
        - int: 비교 결과
            - inObjA.name < inObjB.name: 음수
            - inObjA.name == inObjB.name: 0
            - inObjA.name > inObjB.name: 양수
        """
        # Python에서는 대소문자 구분 없는 비교를 위해 lower() 사용
        return 1 if inObjA.name.lower() > inObjB.name.lower() else -1 if inObjA.name.lower() < inObjB.name.lower() else 0
    
    def sort_by_name(self, inArray):
        """
        객체 배열을 이름 기준으로 정렬합니다.
        
        ## Parameters
        - inArray (list): 정렬할 객체 배열
            
        ## Returns
        - list: 이름 기준으로 정렬된 객체 배열
        """
        # Python의 sorted 함수와 key를 사용하여 이름 기준 정렬
        return sorted(inArray, key=lambda obj: obj.name.lower())
        
    def gen_mirroring_name(self, inStr):
        """
        미러링된 이름을 생성합니다.
        
        ## Parameters
        - inStr (str): 처리할 이름 문자열
            
        ## Returns
        - str: 미러링된 이름 문자열
        
        ## 동작 방식
        1. 부모 클래스의 gen_mirroring_name 메서드 호출
        2. 이름이 변경되지 않았다면:
           - Side나 FrontBack이 있으면 고유한 이름 생성
           - 없으면 "Mirrored" 접미사 추가
        """
        return_name = super().gen_mirroring_name(inStr)
        
        # 이름이 변경되지 않았다면 고유한 이름 생성
        if return_name == inStr:
            if self.has_Side(inStr) or self.has_FrontBack(inStr):
                return_name = self.gen_unique_name(inStr)
            else:
                return_name = self.add_suffix_to_real_name(inStr, "Mirrored")
            
        return return_name
    
    # Type name Part에서 Description으로 지정된 predefined value를 가져오는 메소드들
    def get_parent_value(self):
        """
        부모 이름 문자열을 반환합니다.
        
        ## Returns
        - str: 부모 이름 문자열 (Type 부분에서 "Parent" 설명을 가진 값)
        """
        return self.get_name_part_value_by_description("Type", "Parent")

    def get_dummy_value(self):
        """
        더미 이름 문자열을 반환합니다.
        
        ## Returns
        - str: 더미 이름 문자열 (Type 부분에서 "Dummy" 설명을 가진 값)
        """
        return self.get_name_part_value_by_description("Type", "Dummy")

    def get_exposeTm_value(self):
        """
        ExposeTm 이름 문자열을 반환합니다.
        
        ## Returns
        - str: ExposeTm 이름 문자열 (Type 부분에서 "ExposeTM" 설명을 가진 값)
        """
        return self.get_name_part_value_by_description("Type", "ExposeTM")

    def get_ik_value(self):
        """
        IK 이름 문자열을 반환합니다.
        
        ## Returns
        - str: IK 이름 문자열 (Type 부분에서 "IK" 설명을 가진 값)
        """
        return self.get_name_part_value_by_description("Type", "IK")

    def get_target_value(self):
        """
        타겟 이름 문자열을 반환합니다.
        
        ## Returns
        - str: 타겟 이름 문자열 (Type 부분에서 "Target" 설명을 가진 값)
        """
        return self.get_name_part_value_by_description("Type", "Target")