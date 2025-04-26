#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max용 이름 처리 모듈
3ds Max에 특화된 네이밍 기능 (pymxs 의존)
"""

from pymxs import runtime as rt
from pyjallib.naming import Naming
from pyjallib.namePart import NamePart, NamePartType

class Name(Naming):
    """
    3ds Max 노드 이름 관리를 위한 클래스
    Naming 클래스를 상속받으며, Max 특화 기능 제공
    """
    
    def __init__(self, configPath=None):
        """
        클래스 초기화
        
        Args:
            configPath: 설정 파일 경로 (기본값: None)
                        설정 파일이 제공되면 해당 파일에서 설정을 로드함
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
            # 설정 파일이 없는 경우, 기본 설정값으로 초기화
            # Base 부분 (PREFIX 타입)
            basePart = NamePart("Base", NamePartType.PREFIX, 
                             ["b", "Bip001"], 
                             ["SkinBone", "Biped"])
            # Type 부분 (PREFIX 타입)
            typePart = NamePart("Type", NamePartType.PREFIX, 
                             ["P", "Dum", "Exp", "IK", "T"], 
                             ["Parent", "Dummy", "ExposeTM", "IK", "Target"])
            # Side 부분 (PREFIX 타입)
            sidePart = NamePart("Side", NamePartType.PREFIX,
                             ["L", "R"], 
                             ["Left", "Right"],
                             True)
            # FrontBack 부분 (PREFIX 타입)
            frontBackPart = NamePart("FrontBack", NamePartType.PREFIX,
                                 ["F", "B"], 
                                 ["Front", "Back"],
                                 True)
            # RealName 부분 (REALNAME 타입)
            realNamePart = NamePart("RealName", NamePartType.REALNAME, [], [])
            # Index 부분 (INDEX 타입)
            indexPart = NamePart("Index", NamePartType.INDEX, [], [])
            # Nub 부분 (SUFFIX 타입)
            nubPart = NamePart("Nub", NamePartType.SUFFIX,
                             ["Nub"], 
                             ["Nub"])
            # 기본 순서대로 설정
            self._nameParts = [basePart, typePart, sidePart, frontBackPart, realNamePart, indexPart, nubPart]
    
    # NamePart 직접 액세스 메소드들
    # get_<NamePart 이름>_values 메소드들
    def get_Base_values(self):
        """
        Base 부분의 사전 정의 값 목록 반환
        
        Returns:
            Base 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Base")
    
    def get_Type_values(self):
        """
        Type 부분의 사전 정의 값 목록 반환
        
        Returns:
            Type 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Type")
    
    def get_Side_values(self):
        """
        Side 부분의 사전 정의 값 목록 반환
        
        Returns:
            Side 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Side")
    
    def get_FrontBack_values(self):
        """
        FrontBack 부분의 사전 정의 값 목록 반환
        
        Returns:
            FrontBack 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("FrontBack")
    
    def get_Nub_values(self):
        """
        Nub 부분의 사전 정의 값 목록 반환
        
        Returns:
            Nub 부분의 사전 정의 값 목록
        """
        return self.get_name_part_predefined_values("Nub")
    
    # is_<NamePart 이름> 메소드들
    def is_Base(self, inStr):
        """
        문자열이 Base 부분의 사전 정의 값인지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Base 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Base", inStr)
    
    def is_Type(self, inStr):
        """
        문자열이 Type 부분의 사전 정의 값인지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Type 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Type", inStr)
    
    def is_Side(self, inStr):
        """
        문자열이 Side 부분의 사전 정의 값인지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Side 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Side", inStr)
    
    def is_FrontBack(self, inStr):
        """
        문자열이 FrontBack 부분의 사전 정의 값인지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            FrontBack 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("FrontBack", inStr)
    
    def is_Nub(self, inStr):
        """
        문자열이 Nub 부분의 사전 정의 값인지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Nub 부분의 사전 정의 값이면 True, 아니면 False
        """
        return self.is_in_name_part_predefined_values("Nub", inStr)
    
    # has_<NamePart 이름> 메소드들
    def has_Base(self, inStr):
        """
        문자열에 Base 부분의 사전 정의 값이 포함되어 있는지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Base 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Base", inStr)
    
    def has_Type(self, inStr):
        """
        문자열에 Type 부분의 사전 정의 값이 포함되어 있는지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Type 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Type", inStr)
    
    def has_Side(self, inStr):
        """
        문자열에 Side 부분의 사전 정의 값이 포함되어 있는지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Side 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Side", inStr)
    
    def has_FrontBack(self, inStr):
        """
        문자열에 FrontBack 부분의 사전 정의 값이 포함되어 있는지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            FrontBack 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("FrontBack", inStr)
    
    def has_Nub(self, inStr):
        """
        문자열에 Nub 부분의 사전 정의 값이 포함되어 있는지 확인
        
        Args:
            inStr: 확인할 문자열
            
        Returns:
            Nub 부분의 사전 정의 값이 포함되어 있으면 True, 아니면 False
        """
        return self.has_name_part("Nub", inStr)
    
    # replace_<NamePart 이름> 메소드들
    def replace_Base(self, inStr, inNewName):
        """
        문자열의 Base 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("Base", inStr, inNewName)
    
    def replace_Type(self, inStr, inNewName):
        """
        문자열의 Type 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("Type", inStr, inNewName)
    
    def replace_Side(self, inStr, inNewName):
        """
        문자열의 Side 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("Side", inStr, inNewName)
    
    def replace_FrontBack(self, inStr, inNewName):
        """
        문자열의 FrontBack 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("FrontBack", inStr, inNewName)
    
    def replace_RealName(self, inStr, inNewName):
        """
        문자열의 RealName 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("RealName", inStr, inNewName)
    
    def replace_Index(self, inStr, inNewName):
        """
        문자열의 Index 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름 (숫자 문자열)
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("Index", inStr, inNewName)
    
    def replace_Nub(self, inStr, inNewName):
        """
        문자열의 Nub 부분을 새 이름으로 변경
        
        Args:
            inStr: 처리할 문자열
            inNewName: 새 이름
            
        Returns:
            변경된 문자열
        """
        return self.replace_name_part("Nub", inStr, inNewName)
    
    # remove_<NamePart 이름> 메소드들
    def remove_Base(self, inStr):
        """
        문자열에서 Base 부분 제거
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            Base 부분이 제거된 문자열
        """
        return self.remove_name_part("Base", inStr)
    
    def remove_Type(self, inStr):
        """
        문자열에서 Type 부분 제거
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            Type 부분이 제거된 문자열
        """
        return self.remove_name_part("Type", inStr)
    
    def remove_Side(self, inStr):
        """
        문자열에서 Side 부분 제거
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            Side 부분이 제거된 문자열
        """
        return self.remove_name_part("Side", inStr)
    
    def remove_FrontBack(self, inStr):
        """
        문자열에서 FrontBack 부분 제거
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            FrontBack 부분이 제거된 문자열
        """
        return self.remove_name_part("FrontBack", inStr)
    
    def remove_Index(self, inStr):
        """
        문자열에서 Index 부분 제거
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            Index 부분이 제거된 문자열
        """
        return self.remove_name_part("Index", inStr)
    
    def remove_Nub(self, inStr):
        """
        문자열에서 Nub 부분 제거
        
        Args:
            inStr: 처리할 문자열
            
        Returns:
            Nub 부분이 제거된 문자열
        """
        return self.remove_name_part("Nub", inStr)
    
    # pymxs 의존적인 메소드 구현
    
    def gen_unique_name(self, inStr):
        """
        고유한 이름 생성
        
        Args:
            inStr: 기준 이름 문자열
            
        Returns:
            고유한 이름 문자열
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
        두 객체의 이름 비교 (정렬용)
        
        Args:
            inObjA: 첫 번째 객체
            inObjB: 두 번째 객체
            
        Returns:
            비교 결과 (inObjA.name < inObjB.name: 음수, inObjA.name == inObjB.name: 0, inObjA.name > inObjB.name: 양수)
        """
        # Python에서는 대소문자 구분 없는 비교를 위해 lower() 사용
        return 1 if inObjA.name.lower() > inObjB.name.lower() else -1 if inObjA.name.lower() < inObjB.name.lower() else 0
    
    def sort_by_name(self, inArray):
        """
        객체 배열을 이름 기준으로 정렬
        
        Args:
            inArray: 정렬할 객체 배열
            
        Returns:
            이름 기준으로 정렬된 객체 배열
        """
        # Python의 sorted 함수와 key를 사용하여 이름 기준 정렬
        return sorted(inArray, key=lambda obj: obj.name.lower())
        
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
        부모 이름 문자열 반환
        
        Returns:
            부모 이름 문자열
        """
        return self.get_name_part_value_by_description("Type", "Parent")

    def get_dummy_value(self):
        """
        더미 이름 문자열 반환
        
        Returns:
            더미 이름 문자열
        """
        return self.get_name_part_value_by_description("Type", "Dummy")

    def get_exposeTm_value(self):
        """
        ExposeTm 이름 문자열 반환
        
        Returns:
            ExposeTm 이름 문자열
        """
        return self.get_name_part_value_by_description("Type", "ExposeTM")

    def get_ik_value(self):
        """
        IK 이름 문자열 반환
        
        Returns:
            IK 이름 문자열
        """
        return self.get_name_part_value_by_description("Type", "IK")

    def get_target_value(self):
        """
        타겟 이름 문자열 반환
        
        Returns:
            타겟 이름 문자열
        """
        return self.get_name_part_value_by_description("Type", "Target")