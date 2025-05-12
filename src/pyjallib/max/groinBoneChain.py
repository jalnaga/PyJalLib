#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고간 부 본 체인(Groin Bone Chain) 관련 기능을 제공하는 클래스.
GroinBone 클래스가 생성한 고간 부 본들과 헬퍼들을 관리하고 접근하는 인터페이스를 제공합니다.

Examples:
    # GroinBone 클래스로 고간 본 생성 후 체인으로 관리하기
    groin_bone = GroinBone()
    biped_obj = rt.selection[0]  # 선택된 바이패드 객체
    
    # 고간 본 생성
    success = groin_bone.create_bone(biped_obj, 40.0, 60.0)
    if success:
        # 생성된 본과 헬퍼로 체인 생성
        chain = GroinBoneChain.from_groin_bone_result(
            groin_bone.genBones, 
            groin_bone.genHelpers,
            biped_obj,
            40.0,
            60.0
        )
        
        # 체인 가중치 업데이트
        chain.update_weights(35.0, 65.0)
        
        # 본과 헬퍼 이름 변경
        chain.rename_bones(prefix="Character_", suffix="_Groin")
        chain.rename_helpers(prefix="Character_", suffix="_Helper")
        
        # 현재 가중치 값 확인
        pelvis_w, thigh_w = chain.get_weights()
        print(f"Current weights: Pelvis={pelvis_w}, Thigh={thigh_w}")
        
        # 체인 삭제
        # chain.delete_all()
"""

from pymxs import runtime as rt
from .header import jal

class GroinBoneChain:
    def __init__(self, inResult):
        """
        클래스 초기화.
        
        Args:
            bones: 고간 부 본 체인을 구성하는 뼈대 배열 (기본값: None)
            helpers: 고간 부 본과 연관된 헬퍼 객체 배열 (기본값: None)
            biped_obj: 연관된 Biped 객체 (기본값: None)
        """
        self.pelvis =inResult["Pelvis"]
        self.lThighTwist = inResult["LThighTwist"]
        self.rThighTwist = inResult["RThighTwist"]
        self.bones = inResult["Bones"]
        self.helpers = inResult["Helpers"]
        self.pelvisWeight = inResult["PelvisWeight"]
        self.thighWeight = inResult["ThighWeight"]
    
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        Returns:
            본과 헬퍼가 모두 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0 and len(self.helpers) == 0
    
    def clear(self):
        """체인의 모든 본과 헬퍼 참조 제거"""
        self.bones = []
        self.helpers = []
        self.pelvis = None
        self.lThighTwist = None
        self.rThighTwist = None
        self.pelvisWeight = 40.0  # 기본 골반 가중치
        self.thighWeight = 60.0   # 기본 허벅지 가중치
        
    def delete(self):
        """
        체인의 모든 본과 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            삭제 성공 여부 (boolean)
        """
        if self.is_empty():
            return False
            
        try:
            rt.delete(self.bones)
            rt.delete(self.helpers)
            return True
        except:
            return False
    
    def delete_all(self):
        """
        체인의 모든 본과 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            삭제 성공 여부 (boolean)
        """
        if self.is_empty():
            return False
            
        try:
            rt.delete(self.bones)
            rt.delete(self.helpers)
            self.clear()
            return True
        except:
            return False
    
    def update_weights(self, pelvisWeight=None, thighWeight=None):
        """
        고간 부 본의 가중치 업데이트
        
        Args:
            pelvisWeight: 골반 가중치 (None인 경우 현재 값 유지)
            thighWeight: 허벅지 가중치 (None인 경우 현재 값 유지)
            
        Returns:
            업데이트 성공 여부 (boolean)
        """
        if self.is_empty():
            return False
            
        # 새 가중치 설정
        if pelvisWeight is not None:
            self.pelvisWeight = pelvisWeight
        if thighWeight is not None:
            self.thighWeight = thighWeight
        
        self.delete()
        result = jal.groinBone.create_bone(
            self.pelvis, 
            self.lThighTwist, 
            self.rThighTwist, 
            self.pelvisWeight, 
            self.thighWeight
        )
        self.bones = result["Bones"]
        self.helpers = result["Helpers"]
            
    def get_weights(self):
        """
        현재 설정된 가중치 값 가져오기
        
        Returns:
            (pelvis_weight, thigh_weight) 형태의 튜플
        """
        return (self.pelvis_weight, self.thigh_weight)
    
    @classmethod
    def from_groin_bone_result(cls, inResult):
        """
        GroinBone 클래스의 결과로부터 GroinBoneChain 인스턴스 생성
        
        Args:
            bones: GroinBone 클래스가 생성한 뼈대 배열
            helpers: GroinBone 클래스가 생성한 헬퍼 배열
            biped_obj: 연관된 Biped 객체 (기본값: None)
            pelvisWeight: 골반 가중치 (기본값: 40.0)
            thighWeight: 허벅지 가중치 (기본값: 60.0)
            
        Returns:
            GroinBoneChain 인스턴스
        """
        chain = cls(inResult)
        
        return chain