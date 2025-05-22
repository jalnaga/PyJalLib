#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
뼈대 체인(Bone Chain) 기본 클래스 - 뼈대 체인 관리를 위한 공통 기능 제공

이 모듈은 다양한 뼈대 체인 클래스의 기본 부모 클래스로 사용됩니다.
AutoClavicleChain, GroinBoneChain, VolumeBoneChain, TwistBoneChain 등의
특수 목적 뼈대 체인들이 상속받아 사용하며, 공통된 관리 기능을 제공합니다.

기본 클래스는 다음과 같은 공통 기능을 제공합니다:
- 체인의 뼈대 및 헬퍼 관리
- 체인 비우기/삭제 기능
- 체인 상태 확인 기능
"""

from pymxs import runtime as rt
from pyjallib.max.header import get_pyjallibmaxheader

jal = get_pyjallibmaxheader()

class BoneChain:
    """
    뼈대 체인을 관리하는 기본 클래스
    
    다양한 뼈대 체인의 공통 기능을 담당하는 부모 클래스입니다.
    뼈대와 헬퍼를 저장하고 기본적인 조작 기능을 제공합니다.
    """
    
    def __init__(self, inResult=None):
        """
        클래스 초기화
        
        Args:
            inResult (dict, optional): 뼈대 생성 결과 데이터를 담은 딕셔너리. 기본값은 None
        """
        # 기본 속성 초기화
        if inResult is None:
            # inResult가 None이면 속성들을 빈 리스트로 초기화
            self.bones = []
            self.helpers = []
            self.result = {}  # 빈 딕셔너리로 초기화
            self.sourceBones = []
            self.parameters = []
        else:
            self.bones = inResult.get("Bones", [])
            self.helpers = inResult.get("Helpers", [])
            self.result = inResult  # 원본 결과 보존
            self.sourceBones = inResult.get("SourceBones", [])
            self.parameters = inResult.get("Parameters", [])
        
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        Returns:
            bool: 체인이 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0
    
    def clear(self):
        """체인의 모든 뼈대와 헬퍼 참조 제거"""
        self.bones = []
        self.helpers = []
        self.sourceBones = []
        self.parameters = []
        
    def delete(self):
        """
        체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            bool: 삭제 성공 여부
        """
        if self.is_empty() and not self.helpers:
            return False
            
        try:
            # 뼈대 삭제
            if self.bones:
                for bone in self.bones:
                    if rt.isValidNode(bone):
                        rt.delete(bone)
            
            # 헬퍼 삭제
            if self.helpers:
                for helper in self.helpers:
                    if rt.isValidNode(helper):
                        rt.delete(helper)
            
            self.bones = []
            self.helpers = []
            
            return True
        except:
            return False
    
    def delete_all(self):
        """
        체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            bool: 삭제 성공 여부
        """
        if self.is_empty() and not self.helpers:
            return False
            
        try:
            # 뼈대 삭제
            if self.bones:
                for bone in self.bones:
                    if rt.isValidNode(bone):
                        rt.delete(bone)
            
            # 헬퍼 삭제
            if self.helpers:
                for helper in self.helpers:
                    if rt.isValidNode(helper):
                        rt.delete(helper)
                
            self.clear()
            return True
        except:
            return False
    
    def get_bones(self):
        """
        체인의 모든 뼈대 가져오기
        
        Returns:
            list: 모든 뼈대 객체의 배열
        """
        if self.is_empty():
            return []
        
        return self.bones
    
    def get_helpers(self):
        """
        체인의 모든 헬퍼 가져오기
        
        Returns:
            list: 모든 헬퍼 객체의 배열
        """
        if not self.helpers:
            return []
        
        return self.helpers
    
    @classmethod
    def from_result(cls, inResult):
        """
        결과 딕셔너리로부터 체인 인스턴스 생성
        
        Args:
            inResult (dict): 뼈대 생성 결과를 담은 딕셔너리
            
        Returns:
            BoneChain: 생성된 체인 인스턴스
        """
        return cls(inResult)
    
    def update_from_result(self, inResult):
        """
        기존 체인 인스턴스를 결과 딕셔너리로부터 업데이트
        
        이미 생성된 체인 객체의 내용을 새로운 결과 데이터로 갱신합니다.
        
        Args:
            inResult (dict): 뼈대 생성 결과를 담은 딕셔너리
            
        Returns:
            self: 메서드 체이닝을 위한 자기 자신 반환
        """
        if inResult is None:
            return self
            
        self.bones = inResult.get("Bones", [])
        self.helpers = inResult.get("Helpers", [])
        self.result = inResult  # 원본 결과 보존
        self.sourceBones = inResult.get("SourceBones", [])
        self.parameters = inResult.get("Parameters", [])
        
        return self
