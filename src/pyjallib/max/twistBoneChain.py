#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
트위스트 뼈대 체인(Twist Bone Chain) 모듈 - 트위스트 뼈대 그룹 관리 기능 제공

이 모듈은 TwistBone 클래스가 생성한 트위스트 뼈대들을 하나의 체인으로 관리하고
간편하게 접근할 수 있는 인터페이스를 제공합니다. 일반적으로 캐릭터 리깅에서
팔, 다리 등의 관절 부위에 자연스러운 회전 움직임을 구현하기 위해 사용됩니다.

TwistBoneChain 클래스는 다음과 같은 주요 기능을 제공합니다:
- 트위스트 뼈대 체인의 개별 뼈대 접근
- 체인의 첫 번째/마지막 뼈대 쉽게 가져오기
- 체인의 모든 뼈대를 한 번에 삭제하기
- 체인의 타입 정보 관리 (상체/하체)

Examples:
    # 트위스트 체인 생성 및 관리 예시
    from pyjallib.max import TwistBone, TwistBoneChain
    from pymxs import runtime as rt
    
    # 트위스트 뼈대를 생성할 뼈대 객체와 그 자식 객체 가져오기
    parent_bone = rt.selection[0]  # 예: 상완 뼈대
    child_bone = parent_bone.children[0]  # 예: 전완 뼈대
    
    # TwistBone 클래스 인스턴스 생성
    twist_bone = TwistBone()
    
    # 상완(Upper) 타입의 트위스트 뼈대 체인 생성 (4개의 뼈대)
    twist_result = twist_bone.create_upper_limb_bones(parent_bone, child_bone, 4)
    
    # 생성된 결과로 TwistBoneChain 인스턴스 생성
    chain = TwistBoneChain.from_twist_bone_result(twist_result)
    
    # 체인 관리 기능 사용
    first_bone = chain.get_first_bone()  # 첫 번째 트위스트 뼈대
    last_bone = chain.get_last_bone()    # 마지막 트위스트 뼈대
    middle_bone = chain.get_bone_at_index(2)  # 특정 인덱스의 뼈대
    
    # 체인 정보 확인
    bone_count = chain.get_count()  # 체인의 뼈대 개수
    chain_type = chain.get_type()   # 체인의 타입 (Upper 또는 Lower)
    
    # 필요 없어지면 체인의 모든 뼈대 삭제
    # chain.delete_all()
"""

from pymxs import runtime as rt
from .header import jal

class TwistBoneChain:
    def __init__(self, inResult):
        """
        클래스 초기화.
        
        Args:
            bones: 트위스트 뼈대 체인을 구성하는 뼈대 배열 (기본값: None)
        """
        self.bones = inResult["Bones"]
        self.type = inResult["Type"]
        self.limb = inResult["Limb"]
        self.child = inResult["Child"]
        self.twistNum = inResult["TwistNum"]
    
    def get_bone_at_index(self, index):
        """
        지정된 인덱스의 트위스트 뼈대 가져오기
        
        Args:
            index: 가져올 뼈대의 인덱스
            
        Returns:
            해당 인덱스의 뼈대 객체 또는 None (인덱스가 범위를 벗어난 경우)
        """
        if 0 <= index < len(self.bones):
            return self.bones[index]
        return None
    
    def get_first_bone(self):
        """
        체인의 첫 번째 트위스트 뼈대 가져오기
        
        Returns:
            첫 번째 뼈대 객체 또는 None (체인이 비어있는 경우)
        """
        return self.bones[0] if self.bones else None
    
    def get_last_bone(self):
        """
        체인의 마지막 트위스트 뼈대 가져오기
        
        Returns:
            마지막 뼈대 객체 또는 None (체인이 비어있는 경우)
        """
        return self.bones[-1] if self.bones else None
    
    def get_count(self):
        """
        체인의 트위스트 뼈대 개수 가져오기
        
        Returns:
            뼈대 개수
        """
        return self.twistNum
    
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        Returns:
            체인이 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0
    
    def clear(self):
        """체인의 모든 뼈대 제거"""
        self.bones = []
    
    def delete_all(self):
        """
        체인의 모든 뼈대를 3ds Max 씬에서 삭제
        
        Returns:
            삭제 성공 여부 (boolean)
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
        
        Returns:
            트위스트 뼈대 체인의 타입 ('upperArm', 'foreArm', 'thigh', 'calf', 'bend' 중 하나) 또는 None
        """
        return self.type
    
    @classmethod
    def from_twist_bone_result(cls, inResult):
        """
        TwistBone 클래스의 결과로부터 TwistBoneChain 인스턴스 생성
        
        Args:
            twist_bone_result: TwistBone 클래스의 메서드가 반환한 뼈대 배열
            source_bone: 원본 뼈대 객체 (기본값: None)
            type_name: 트위스트 뼈대 타입 (기본값: None)
            
        Returns:
            TwistBoneChain 인스턴스
        """
        chain = cls(inResult)
            
        return chain