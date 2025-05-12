#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
자동 쇄골 체인(AutoClavicle Chain) 관련 기능을 제공하는 클래스.
AutoClavicle 클래스가 생성한 자동 쇄골 뼈대들을 관리하고 접근하는 인터페이스를 제공합니다.

Examples:
    # 자동 쇄골 체인 생성 예시
    from pyjallib.max import AutoClavicle, AutoClavicleChain
    from pymxs import runtime as rt
    
    # 선택된 쇄골과 상완 객체
    clavicle = rt.selection[0]
    upperArm = rt.selection[1]
    
    # AutoClavicle 클래스 인스턴스 생성
    auto_clavicle = AutoClavicle()
    
    # 자동 쇄골 뼈대 생성
    clavicle_bones = auto_clavicle.create_bones(clavicle, upperArm, liftScale=0.8)
    
    # 생성된 뼈대로 AutoClavicleChain 인스턴스 생성
    chain = AutoClavicleChain.from_auto_clavicle_result(
        {
            "Bones": clavicle_bones,
            "Helpers": auto_clavicle.helpers,
            "Clavicle": clavicle,
            "UpperArm": upperArm,
            "LiftScale": 0.8
        }
    )
    
    # 체인 관리 기능 사용
    bone = chain.get_bone()
    
    # 체인의 모든 뼈대 이름 변경
    chain.rename_bones(prefix="character_", suffix="_autoClavicle")
    
    # 체인의 LiftScale 수정
    chain.update_lift_scale(0.9)
    
    # 필요 없어지면 체인의 모든 뼈대와 헬퍼 삭제
    # chain.delete_all()
"""

from pymxs import runtime as rt
from .header import jal


class AutoClavicleChain:
    def __init__(self, inResult):
        """
        클래스 초기화.
        
        Args:
            inResult: AutoClavicle 클래스의 생성 결과 (딕셔너리)
        """
        self.bones = inResult.get("Bones", [])
        self.helpers = inResult.get("Helpers", [])
        self.clavicle = inResult.get("Clavicle", None)
        self.upperArm = inResult.get("UpperArm", None)
        self.liftScale = inResult.get("LiftScale", 0.8)
    
    def get_bones(self):
        """
        체인의 모든 뼈대 가져오기
        
        Returns:
            모든 뼈대 객체의 배열
        """
        if self.is_empty():
            return []
        
        return self.bones
    
    def get_helpers(self):
        """
        체인의 모든 헬퍼 가져오기
        
        Returns:
            모든 헬퍼 객체의 배열
        """
        if self.is_empty():
            return []
        
        return self.helpers
    
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        Returns:
            체인이 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0
    
    def clear(self):
        """체인의 모든 뼈대와 헬퍼 참조 제거"""
        self.bones = []
        self.helpers = []
        self.clavicle = None
        self.upperArm = None
    
    def delete_all(self):
        """
        체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            삭제 성공 여부 (boolean)
        """
        if self.is_empty():
            return False
            
        try:
            for bone in self.bones:
                if rt.isValidNode(bone):
                    rt.delete(bone)
            
            for helper in self.helpers:
                if rt.isValidNode(helper):
                    rt.delete(helper)
                
            self.clear()
            return True
        except:
            return False
    
    def update_lift_scale(self, newLiftScale=0.8):
        """
        자동 쇄골의 들어올림 스케일 업데이트
        
        Args:
            newLiftScale: 새로운 들어올림 스케일 (기본값: 0.8)
            
        Returns:
            업데이트 성공 여부 (boolean)
        """
        if self.is_empty() or not rt.isValidNode(self.clavicle) or not rt.isValidNode(self.upperArm):
            return False
        
        clavicle = self.clavicle
        upperArm = self.upperArm
        
        # 기존 본과 헬퍼 삭제
        self.delete_all()
        
        # 새로운 LiftScale 값 설정
        self.liftScale = newLiftScale
        self.clavicle = clavicle
        self.upperArm = upperArm
        
        # 재생성
        result = jal.autoClavicle.create_bones(self.clavicle, self.upperArm, self.liftScale)
        if result:
            return True
        
        return False
    
    @classmethod
    def from_auto_clavicle_result(cls, inResult):
        """
        AutoClavicle 클래스의 결과로부터 AutoClavicleChain 인스턴스 생성
        
        Args:
            inResult: AutoClavicle 클래스의 메서드가 반환한 결과값 딕셔너리
            
        Returns:
            AutoClavicleChain 인스턴스
        """
        chain = cls(inResult)
        return chain
