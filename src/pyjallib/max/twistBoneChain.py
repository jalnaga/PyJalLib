#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 트위스트 뼈대 체인(TwistBoneChain) 모듈

3ds Max에서 트위스트 뼈대 그룹을 관리하고 제어하는 기능을 제공하는 모듈입니다.

## 주요 기능
- TwistBone 클래스가 생성한 트위스트 뼈대들의 통합 관리
- 트위스트 체인의 개별 뼈대 접근 및 조작
- 체인의 첫 번째/마지막 뼈대 쉽게 가져오기
- 트위스트 체인 타입 정보 관리 (Upper/Lower)
- 체인의 모든 뼈대를 한 번에 삭제하기

## 구현 정보
- TwistBone 클래스의 결과를 관리하는 래퍼 클래스
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt
from .header import jal

class TwistBoneChain:
    """
    # TwistBoneChain 클래스
    
    TwistBone 클래스가 생성한 트위스트 뼈대들을 하나의 체인으로 관리하는 클래스입니다.
    
    ## 주요 기능
    - 트위스트 뼈대 체인의 개별 뼈대 접근 및 관리
    - 체인의 첫 번째/마지막 뼈대 빠르게 접근
    - 체인의 모든 뼈대를 한 번에 삭제
    - 체인의 타입 정보 관리 (Upper/Lower)
    - 체인의 정보(뼈대 수, 소스 뼈대 등) 조회
    
    ## 구현 정보
    - TwistBone.create_*_limb_bones() 메서드의 결과를 관리
    - 체인 내 뼈대들에 대한 인터페이스 제공
    
    ## 사용 예시
    ```python
    # TwistBone 클래스의 결과로부터 생성
    twist_bone = TwistBone()
    result = twist_bone.create_upper_limb_bones(upper_arm, lower_arm)
    chain = TwistBoneChain.from_twist_bone_result(result)
    
    # 체인 관리 기능 사용
    first_bone = chain.get_first_bone()  # 첫 번째 트위스트 뼈대
    last_bone = chain.get_last_bone()    # 마지막 트위스트 뼈대
    middle_bone = chain.get_bone_at_index(2)  # 특정 인덱스의 뼈대
    
    # 체인 정보 확인
    bone_count = chain.get_count()  # 체인의 뼈대 개수
    chain_type = chain.get_type()   # 체인의 타입 (Upper 또는 Lower)
    
    # 필요 없어지면 체인의 모든 뼈대 삭제
    chain.delete_all()
    ```
    """

    def __init__(self, inResult):
        """
        TwistBoneChain 클래스를 초기화합니다.
        
        ## Parameters
        - inResult (dict): TwistBone 클래스의 create_*_limb_bones() 메서드가 반환한 결과 딕셔너리
            - "Bones": 생성된 뼈대 객체 배열
            - "Type": 체인 타입 ("Upper" 또는 "Lower")
            - "Limb": 원본 부모 뼈대 객체
            - "Child": 원본 자식 뼈대 객체
            - "TwistNum": 생성된 트위스트 뼈대 개수
        """
        self.bones = inResult["Bones"]
        self.type = inResult["Type"]
        self.limb = inResult["Limb"]
        self.child = inResult["Child"]
        self.twistNum = inResult["TwistNum"]
    
    def get_bone_at_index(self, index):
        """
        지정된 인덱스의 트위스트 뼈대를 가져옵니다.
        
        ## Parameters
        - index (int): 가져올 뼈대의 인덱스 (0부터 시작)
            
        ## Returns
        - MaxObject: 해당 인덱스의 뼈대 객체 또는 None (인덱스가 범위를 벗어난 경우)
        
        ## 동작 방식
        bones 배열에서 지정된 인덱스의 뼈대를 반환합니다.
        인덱스가 유효 범위를 벗어나면 None을 반환합니다.
        """
        if 0 <= index < len(self.bones):
            return self.bones[index]
        return None
    
    def get_first_bone(self):
        """
        체인의 첫 번째 트위스트 뼈대를 가져옵니다.
        
        ## Returns
        - MaxObject: 첫 번째 뼈대 객체 또는 None (체인이 비어있는 경우)
        
        ## 동작 방식
        bones 배열의 첫 번째 요소를 반환합니다.
        배열이 비어있으면 None을 반환합니다.
        """
        return self.bones[0] if self.bones else None
    
    def get_last_bone(self):
        """
        체인의 마지막 트위스트 뼈대를 가져옵니다.
        
        ## Returns
        - MaxObject: 마지막 뼈대 객체 또는 None (체인이 비어있는 경우)
        
        ## 동작 방식
        bones 배열의 마지막 요소를 반환합니다.
        배열이 비어있으면 None을 반환합니다.
        """
        return self.bones[-1] if self.bones else None
    
    def get_count(self):
        """
        체인의 트위스트 뼈대 개수를 가져옵니다.
        
        ## Returns
        - int: 뼈대 개수
        
        ## 동작 방식
        TwistBone 클래스에서 지정된 트위스트 뼈대 개수(twistNum)를 반환합니다.
        """
        return self.twistNum
    
    def is_empty(self):
        """
        체인이 비어있는지 확인합니다.
        
        ## Returns
        - bool: 체인이 비어있으면 True, 아니면 False
        
        ## 동작 방식
        bones 배열의 길이가 0인지 확인합니다.
        """
        return len(self.bones) == 0
    
    def clear(self):
        """
        체인의 모든 뼈대 참조를 제거합니다.
        
        ## 동작 방식
        bones 배열을 비웁니다. 실제 3ds Max 씬에서는 객체가 삭제되지 않습니다.
        """
        self.bones = []
    
    def delete_all(self):
        """
        체인의 모든 뼈대를 3ds Max 씬에서 삭제합니다.
        
        ## Returns
        - bool: 삭제 성공 여부 (True/False)
        
        ## 동작 방식
        1. 체인이 비어있는지 확인
        2. 비어있지 않으면 모든 뼈대를 3ds Max에서 삭제
        3. 체인의 참조를 clear() 메서드로 제거
        """
        if not self.bones:
            return False
            
        try:
            for bone in self.bones:
                rt.delete(bone)
            self.clear()
            return True
        except:
            return False
    
    def get_type(self):
        """
        트위스트 뼈대 체인의 타입을 반환합니다.
        
        ## Returns
        - str: 트위스트 뼈대 체인의 타입 ('Upper' 또는 'Lower')
        
        ## 동작 방식
        TwistBone 클래스에서 설정된 체인 타입 정보를 반환합니다.
        """
        return self.type
    
    @classmethod
    def from_twist_bone_result(cls, inResult):
        """
        TwistBone 클래스의 결과로부터 TwistBoneChain 인스턴스를 생성합니다.
        
        ## Parameters
        - inResult (dict): TwistBone 클래스의 create_*_limb_bones() 메서드가 반환한 결과 딕셔너리
            
        ## Returns
        - TwistBoneChain: 생성된 TwistBoneChain 인스턴스
        
        ## 동작 방식
        TwistBone 클래스의 결과 딕셔너리를 받아 새 TwistBoneChain 인스턴스를 생성합니다.
        """
        chain = cls(inResult)
            
        return chain