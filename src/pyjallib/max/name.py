#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max용 이름 처리 모듈
3ds Max에 특화된 네이밍 기능 (pymxs 의존)
"""

import os

from pymxs import runtime as rt
from pyjallib.naming import Naming

class Name(Naming):
    """Naming을 상속하여 3ds Max 특화 노드 네이밍 기능을 제공한다."""

    def __init__(self, configPath=None):
        """Name 클래스를 초기화한다.

        Args:
            configPath (str | None): 네이밍 설정 JSON 파일 경로. None이면 기본
                3DSMaxNamingConfig.json을 로드한다.
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
    # get_<NamePart 이름>_values 메소드들
    def get_Base_values(self):
        """Base 부분의 사전 정의 값 목록을 반환한다.

        Returns:
            list[str]: Base 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Base")
    
    def get_Type_values(self):
        """Type 부분의 사전 정의 값 목록을 반환한다.

        Returns:
            list[str]: Type 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Type")
    
    def get_Side_values(self):
        """Side 부분의 사전 정의 값 목록을 반환한다.

        Returns:
            list[str]: Side 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Side")
    
    def get_FrontBack_values(self):
        """FrontBack 부분의 사전 정의 값 목록을 반환한다.

        Returns:
            list[str]: FrontBack 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("FrontBack")
    
    def get_Nub_values(self):
        """Nub 부분의 사전 정의 값 목록을 반환한다.

        Returns:
            list[str]: Nub 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Nub")
    
    # is_<NamePart 이름> 메소드들
    def is_Base(self, inStr):
        """문자열이 Base 부분의 사전 정의 값인지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Base 부분의 사전 정의 값이면 True
        """
        return self.is_in_name_part_predefined_values("Base", inStr)
    
    def is_Type(self, inStr):
        """문자열이 Type 부분의 사전 정의 값인지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Type 부분의 사전 정의 값이면 True
        """
        return self.is_in_name_part_predefined_values("Type", inStr)
    
    def is_Side(self, inStr):
        """문자열이 Side 부분의 사전 정의 값인지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Side 부분의 사전 정의 값이면 True
        """
        return self.is_in_name_part_predefined_values("Side", inStr)
    
    def is_FrontBack(self, inStr):
        """문자열이 FrontBack 부분의 사전 정의 값인지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: FrontBack 부분의 사전 정의 값이면 True
        """
        return self.is_in_name_part_predefined_values("FrontBack", inStr)
    
    def is_Nub(self, inStr):
        """문자열이 Nub 부분의 사전 정의 값인지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Nub 부분의 사전 정의 값이면 True
        """
        return self.is_in_name_part_predefined_values("Nub", inStr)
    
    # has_<NamePart 이름> 메소드들
    def has_Base(self, inStr):
        """문자열에 Base 부분의 사전 정의 값이 포함되어 있는지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Base 부분의 사전 정의 값이 포함되어 있으면 True
        """
        return self.has_name_part("Base", inStr)
    
    def has_Type(self, inStr):
        """문자열에 Type 부분의 사전 정의 값이 포함되어 있는지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Type 부분의 사전 정의 값이 포함되어 있으면 True
        """
        return self.has_name_part("Type", inStr)
    
    def has_Side(self, inStr):
        """문자열에 Side 부분의 사전 정의 값이 포함되어 있는지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Side 부분의 사전 정의 값이 포함되어 있으면 True
        """
        return self.has_name_part("Side", inStr)
    
    def has_FrontBack(self, inStr):
        """문자열에 FrontBack 부분의 사전 정의 값이 포함되어 있는지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: FrontBack 부분의 사전 정의 값이 포함되어 있으면 True
        """
        return self.has_name_part("FrontBack", inStr)
    
    def has_Nub(self, inStr):
        """문자열에 Nub 부분의 사전 정의 값이 포함되어 있는지 확인한다.

        Args:
            inStr (str): 확인할 문자열

        Returns:
            bool: Nub 부분의 사전 정의 값이 포함되어 있으면 True
        """
        return self.has_name_part("Nub", inStr)
    
    # replace_<NamePart 이름> 메소드들
    def replace_Base(self, inStr, inNewName):
        """문자열의 Base 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("Base", inStr, inNewName)
    
    def replace_Type(self, inStr, inNewName):
        """문자열의 Type 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("Type", inStr, inNewName)
    
    def replace_Side(self, inStr, inNewName):
        """문자열의 Side 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("Side", inStr, inNewName)
    
    def replace_FrontBack(self, inStr, inNewName):
        """문자열의 FrontBack 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("FrontBack", inStr, inNewName)
    
    def replace_RealName(self, inStr, inNewName):
        """문자열의 RealName 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("RealName", inStr, inNewName)
    
    def replace_Index(self, inStr, inNewName):
        """문자열의 Index 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름 (숫자 문자열)

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("Index", inStr, inNewName)
    
    def replace_Nub(self, inStr, inNewName):
        """문자열의 Nub 부분을 새 이름으로 변경한다.

        Args:
            inStr (str): 처리할 문자열
            inNewName (str): 새 이름

        Returns:
            str: 변경된 문자열
        """
        return self.replace_name_part("Nub", inStr, inNewName)
    
    # remove_<NamePart 이름> 메소드들
    def remove_Base(self, inStr):
        """문자열에서 Base 부분을 제거한다.

        Args:
            inStr (str): 처리할 문자열

        Returns:
            str: Base 부분이 제거된 문자열
        """
        return self.remove_name_part("Base", inStr)
    
    def remove_Type(self, inStr):
        """문자열에서 Type 부분을 제거한다.

        Args:
            inStr (str): 처리할 문자열

        Returns:
            str: Type 부분이 제거된 문자열
        """
        return self.remove_name_part("Type", inStr)
    
    def remove_Side(self, inStr):
        """문자열에서 Side 부분을 제거한다.

        Args:
            inStr (str): 처리할 문자열

        Returns:
            str: Side 부분이 제거된 문자열
        """
        return self.remove_name_part("Side", inStr)
    
    def remove_FrontBack(self, inStr):
        """문자열에서 FrontBack 부분을 제거한다.

        Args:
            inStr (str): 처리할 문자열

        Returns:
            str: FrontBack 부분이 제거된 문자열
        """
        return self.remove_name_part("FrontBack", inStr)
    
    def remove_Index(self, inStr):
        """문자열에서 Index 부분을 제거한다.

        Args:
            inStr (str): 처리할 문자열

        Returns:
            str: Index 부분이 제거된 문자열
        """
        return self.remove_name_part("Index", inStr)
    
    def remove_Nub(self, inStr):
        """문자열에서 Nub 부분을 제거한다.

        Args:
            inStr (str): 처리할 문자열

        Returns:
            str: Nub 부분이 제거된 문자열
        """
        return self.remove_name_part("Nub", inStr)
    
    # pymxs 의존적인 메소드 구현
    
    def gen_unique_name(self, inStr):
        """씬 내 동일 패턴 객체 수를 세어 고유한 이름을 생성한다.

        Index 부분을 와일드카드로 바꿔 이름이 일치하는 객체를 검색하고,
        일치 개수 + 1을 새 Index로 지정한다.

        Args:
            inStr (str): 기준 이름 문자열

        Returns:
            str: 고유한 이름 문자열
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
        """두 객체의 이름을 대소문자 구분 없이 비교한다 (정렬용).

        Args:
            inObjA (rt.Node): 첫 번째 객체
            inObjB (rt.Node): 두 번째 객체

        Returns:
            int: inObjA 이름이 크면 1, 작으면 -1, 같으면 0
        """
        # Python에서는 대소문자 구분 없는 비교를 위해 lower() 사용
        return 1 if inObjA.name.lower() > inObjB.name.lower() else -1 if inObjA.name.lower() < inObjB.name.lower() else 0
    
    def sort_by_name(self, inArray):
        """객체 배열을 이름 기준으로 정렬한다 (대소문자 구분 없음).

        Args:
            inArray (list[rt.Node]): 정렬할 객체 배열

        Returns:
            list[rt.Node]: 이름 기준으로 정렬된 객체 리스트
        """
        # Python의 sorted 함수와 key를 사용하여 이름 기준 정렬
        return sorted(inArray, key=lambda obj: obj.name.lower())
        
    def gen_mirroring_name(self, inStr):
        """미러링된 이름을 생성한다 (Side 또는 FrontBack 교체).

        기반 클래스의 미러링으로 이름이 변경되지 않으면, Side/FrontBack이
        있는 경우 고유한 이름을 생성하고, 없는 경우 RealName에 "Mirrored"
        접미사를 추가한다.

        Args:
            inStr (str): 처리할 이름 문자열

        Returns:
            str: 미러링된 이름 문자열
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
        """Type 부분에서 Description이 "Parent"인 사전 정의 값을 반환한다.

        Returns:
            str: 부모 타입 이름 문자열. 찾지 못하면 빈 문자열
        """
        return self.get_name_part_value_by_description("Type", "Parent")

    def get_dummy_value(self):
        """Type 부분에서 Description이 "Dummy"인 사전 정의 값을 반환한다.

        Returns:
            str: 더미 타입 이름 문자열. 찾지 못하면 빈 문자열
        """
        return self.get_name_part_value_by_description("Type", "Dummy")

    def get_exposeTm_value(self):
        """Type 부분에서 Description이 "ExposeTM"인 사전 정의 값을 반환한다.

        Returns:
            str: ExposeTm 타입 이름 문자열. 찾지 못하면 빈 문자열
        """
        return self.get_name_part_value_by_description("Type", "ExposeTM")

    def get_ik_value(self):
        """Type 부분에서 Description이 "IK"인 사전 정의 값을 반환한다.

        Returns:
            str: IK 타입 이름 문자열. 찾지 못하면 빈 문자열
        """
        return self.get_name_part_value_by_description("Type", "IK")

    def get_target_value(self):
        """Type 부분에서 Description이 "Target"인 사전 정의 값을 반환한다.

        Returns:
            str: 타겟 타입 이름 문자열. 찾지 못하면 빈 문자열
        """
        return self.get_name_part_value_by_description("Type", "Target")