#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 자동 쇄골 체인(AutoClavicle Chain) 모듈

AutoClavicle 클래스가 생성한 자동 쇄골 뼈대를 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 자동 쇄골 뼈대 및 헬퍼 객체 관리
- 체인의 속성 변경 및 업데이트
- 쇄골 리프트 스케일 조정
- 생성된 체인 구성요소 삭제

## 사용 예시
```python
# 자동 쇄골 체인 생성 예시
from pyjallib.max import AutoClavicle, AutoClavicleChain
from pymxs import runtime as rt

# 선택된 쇄골과 상완 객체
clavicle = rt.selection[0]
upperArm = rt.selection[1]

# AutoClavicle 클래스 인스턴스 생성
auto_clavicle = AutoClavicle()

# 자동 쇄골 뼈대 생성
result = auto_clavicle.create_bones(clavicle, upperArm, liftScale=0.8)

# 생성된 뼈대로 AutoClavicleChain 인스턴스 생성
chain = AutoClavicleChain.from_auto_clavicle_result(result)

# 체인의 LiftScale 수정
chain.update_lift_scale(0.9)

# 필요 없어지면 체인의 모든 뼈대와 헬퍼 삭제
# chain.delete_all()
```
"""

from pymxs import runtime as rt
from .header import jal


class AutoClavicleChain:
    """
    # AutoClavicleChain 클래스
    
    자동 쇄골 뼈대와 관련 헬퍼 객체들을 관리하는 클래스입니다.
    
    ## 주요 기능
    - 자동 쇄골 시스템 컴포넌트 그룹화 관리
    - 뼈대와 헬퍼 객체에 대한 접근 제공
    - 체인 속성 변경 및 업데이트
    - 체인의 모든 구성요소 삭제 지원
    
    ## 사용 목적
    AutoClavicle 클래스가 생성한 뼈대 및 헬퍼 객체들을 편리하게 관리하기 위한
    래퍼(wrapper) 클래스로, 복잡한 자동 쇄골 시스템을 단일 객체로 다룰 수 있게 합니다.
    """
    
    def __init__(self, inResult):
        """
        AutoClavicleChain 클래스를 초기화합니다.
        
        ## Parameters
        - inResult (dict): AutoClavicle 클래스의 생성 결과 딕셔너리
            - "Bones": 생성된 뼈 객체 배열
            - "Helpers": 생성된 헬퍼 객체 배열
            - "Clavicle": 원본 쇄골 뼈 참조
            - "UpperArm": 원본 상완 뼈 참조
            - "LiftScale": 적용된 들어올림 스케일 값
        """
        self.bones = inResult.get("Bones", [])
        self.helpers = inResult.get("Helpers", [])
        self.clavicle = inResult.get("Clavicle", None)
        self.upperArm = inResult.get("UpperArm", None)
        self.liftScale = inResult.get("LiftScale", 0.8)
    
    def get_bones(self):
        """
        체인의 모든 뼈대 객체를 가져옵니다.
        
        ## Returns
        - list: 모든 뼈대 객체의 배열
            - 체인이 비어있는 경우 빈 배열 반환
        """
        if self.is_empty():
            return []
        
        return self.bones
    
    def get_helpers(self):
        """
        체인의 모든 헬퍼 객체를 가져옵니다.
        
        ## Returns
        - list: 모든 헬퍼 객체의 배열
            - 체인이 비어있는 경우 빈 배열 반환
        """
        if self.is_empty():
            return []
        
        return self.helpers
    
    def is_empty(self):
        """
        체인이 비어있는지 확인합니다.
        
        ## Returns
        - bool: 체인이 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0
    
    def clear(self):
        """
        체인의 모든 뼈대와 헬퍼 참조를 제거합니다.
        
        3ds Max 씬에서 객체를 삭제하지 않고 메모리에서만 참조를 제거합니다.
        """
        self.bones = []
        self.helpers = []
        self.clavicle = None
        self.upperArm = None
    
    def delete_all(self):
        """
        체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제합니다.
        
        ## Returns
        - bool: 삭제 성공 여부
            - 체인이 비어있거나 삭제 중 오류 발생 시 False 반환
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
        자동 쇄골의 들어올림 스케일을 업데이트합니다.
        
        ## Parameters
        - newLiftScale (float): 새로운 들어올림 스케일 (기본값: 0.8)
            
        ## Returns
        - bool: 업데이트 성공 여부
            - 체인이 비어있거나, 쇄골/상완 참조가 유효하지 않거나, 
              재생성 실패 시 False 반환
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
        AutoClavicle 클래스의 결과로부터 AutoClavicleChain 인스턴스를 생성합니다.
        
        ## Parameters
        - inResult (dict): AutoClavicle 클래스의 메서드가 반환한 결과값 딕셔너리
            
        ## Returns
        - AutoClavicleChain: 생성된 AutoClavicleChain 인스턴스
        """
        chain = cls(inResult)
        return chain
