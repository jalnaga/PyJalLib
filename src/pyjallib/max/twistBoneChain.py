#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
트위스트 뼈대 체인(Twist Bone Chain) 관련 기능을 제공하는 클래스.
TwistBone 클래스가 생성한 트위스트 뼈대들을 관리하고 접근하는 인터페이스를 제공합니다.

Examples:
    # 트위스트 체인 생성 예시
    from pyjallib.max import TwistBone, TwistBoneChain
    from pymxs import runtime as rt
    
    # 바이페드 캐릭터에서 선택된 객체 가져오기
    sel_obj = rt.selection[0]
    
    # TwistBone 클래스 인스턴스 생성
    twist_bone = TwistBone()
    
    # 상완 트위스트 뼈대 체인 생성 (5개의 뼈대)
    twist_result = twist_bone.create_upperArm_type(sel_obj, 5)
    
    # 생성된 뼈대로 TwistBoneChain 인스턴스 생성
    chain = TwistBoneChain.from_twist_bone_result(
        twist_result, 
        source_bone=sel_obj, 
        type_name='upperArm'
    )
    
    # 체인 관리 기능 사용
    first_bone = chain.get_first_bone()
    last_bone = chain.get_last_bone()
    middle_bone = chain.get_bone_at_index(2)
    
    # 체인의 모든 뼈대 이름 변경
    chain.rename_bones(prefix="custom_", suffix="_twist")
    
    # 필요 없어지면 체인의 모든 뼈대 삭제
    # chain.delete_all()
"""

from pymxs import runtime as rt
from .header import jal

class TwistBoneChain:
    def __init__(self, bones=None):
        """
        클래스 초기화.
        
        Args:
            bones: 트위스트 뼈대 체인을 구성하는 뼈대 배열 (기본값: None)
        """
        self.bones = bones if bones else []
        self.source_bone = None  # 트위스트의 원본 뼈대 (예: 상완, 전완 등)
        self.type = None  # 트위스트 타입 ('upperArm', 'foreArm', 'thigh', 'calf', 'bend')
    
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
        return len(self.bones)
    
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
    
    def rename_bones(self, prefix="", suffix=""):
        """
        체인의 모든 뼈대 이름 변경
        
        Args:
            prefix: 추가할 접두사 (기본값: "")
            suffix: 추가할 접미사 (기본값: "")
        """
        for i, bone in enumerate(self.bones):
            current_name = bone.name
            # 인덱스 부분을 찾아서 유지
            index_part = ""
            for char in current_name[::-1]:  # 뒤에서부터 검색
                if char.isdigit():
                    index_part = char + index_part
                else:
                    break
                    
            if index_part:
                new_name = f"{prefix}{current_name.rstrip(index_part)}{suffix}{index_part}"
            else:
                new_name = f"{prefix}{current_name}{suffix}{i}"
                
            bone.name = new_name
    
    def get_type(self):
        """
        트위스트 뼈대 체인의 타입을 반환합니다.
        
        Returns:
            트위스트 뼈대 체인의 타입 ('upperArm', 'foreArm', 'thigh', 'calf', 'bend' 중 하나) 또는 None
        """
        return self.type
    
    @classmethod
    def from_twist_bone_result(cls, twist_bone_result, source_bone=None, type_name=None):
        """
        TwistBone 클래스의 결과로부터 TwistBoneChain 인스턴스 생성
        
        Args:
            twist_bone_result: TwistBone 클래스의 메서드가 반환한 뼈대 배열
            source_bone: 원본 뼈대 객체 (기본값: None)
            type_name: 트위스트 뼈대 타입 (기본값: None)
            
        Returns:
            TwistBoneChain 인스턴스
        """
        chain = cls(twist_bone_result)
        
        if source_bone:
            chain.source_bone = source_bone
            
        if type_name:
            chain.type = type_name
            
        return chain