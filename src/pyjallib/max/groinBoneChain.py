#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 고간 부 본 체인(Groin Bone Chain) 모듈

GroinBone 클래스가 생성한 고간 부 본들과 헬퍼들을 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 고간 부 본 구성요소 통합 관리
- 고간 부 본과 연결된 헬퍼 객체 접근
- 가중치 업데이트 및 수정
- 체인 구성요소 삭제 및 초기화

## 사용 예시
```python
# GroinBone 클래스로 고간 본 생성
groin_bone = GroinBone()
result = groin_bone.create_bone(pelvis, lThighTwist, rThighTwist)

# 생성된 결과로 체인 생성
chain = GroinBoneChain.from_groin_bone_result(result)

# 체인 가중치 업데이트
chain.update_weights(35.0, 65.0)

# 현재 가중치 값 확인
pelvis_w, thigh_w = chain.get_weights()

# 체인 삭제
chain.delete_all()
```
"""

from pymxs import runtime as rt
from .header import jal

class GroinBoneChain:
    """
    # GroinBoneChain 클래스
    
    고간 부 본과 관련 헬퍼 객체들을 관리하는 래퍼 클래스입니다.
    
    ## 주요 기능
    - 고간 부 본 구성요소(뼈대, 헬퍼, 참조 객체) 통합 관리
    - 골반 및 허벅지 트위스트 가중치 업데이트
    - 체인 구성요소 제거 및 초기화
    - 체인 상태 확인 및 가중치 정보 접근
    
    ## 구현 정보
    - GroinBone 클래스의 생성 결과를 활용하여 체인 객체 구성
    - 가중치 변경 시 구성요소 재생성을 통한 업데이트
    
    ## 사용 예시
    GroinBone 클래스로 생성한 고간 본 결과를 래핑하여 관리합니다:
    ```python
    # 체인 생성
    chain = GroinBoneChain.from_groin_bone_result(result)
    
    # 가중치 업데이트
    chain.update_weights(35.0, 65.0)
    
    # 필요 없어지면 체인 삭제
    chain.delete_all()
    ```
    """
    
    def __init__(self, inResult):
        """
        GroinBoneChain 클래스를 초기화합니다.
        
        ## Parameters
        - inResult (dict): GroinBone.create_bone() 메소드의 결과 딕셔너리
            - "Pelvis": 골반 객체
            - "LThighTwist": 왼쪽 허벅지 트위스트 객체
            - "RThighTwist": 오른쪽 허벅지 트위스트 객체
            - "Bones": 생성된 뼈대 배열
            - "Helpers": 생성된 헬퍼 객체 배열
            - "PelvisWeight": 골반 가중치
            - "ThighWeight": 허벅지 가중치
        """
        self.pelvis = inResult["Pelvis"]
        self.lThighTwist = inResult["LThighTwist"]
        self.rThighTwist = inResult["RThighTwist"]
        self.bones = inResult["Bones"]
        self.helpers = inResult["Helpers"]
        self.pelvisWeight = inResult["PelvisWeight"]
        self.thighWeight = inResult["ThighWeight"]
    
    def is_empty(self):
        """
        체인이 비어있는지 확인합니다.
        
        ## Returns
        - bool: 본과 헬퍼가 모두 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0 and len(self.helpers) == 0
    
    def clear(self):
        """
        체인의 모든 본과 헬퍼 참조를 제거합니다.
        
        3ds Max 씬에서 객체를 삭제하지 않고 메모리상의 참조만 초기화합니다.
        """
        self.bones = []
        self.helpers = []
        self.pelvis = None
        self.lThighTwist = None
        self.rThighTwist = None
        self.pelvisWeight = 40.0  # 기본 골반 가중치
        self.thighWeight = 60.0   # 기본 허벅지 가중치
        
    def delete(self):
        """
        체인의 모든 본과 헬퍼를 3ds Max 씬에서 삭제합니다.
        
        ## Returns
        - bool: 삭제 성공 여부
            - 체인이 비어있거나 삭제 중 오류 발생 시 False 반환
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
        체인의 모든 본과 헬퍼를 3ds Max 씬에서 삭제하고 참조를 초기화합니다.
        
        ## Returns
        - bool: 삭제 성공 여부
            - 체인이 비어있거나 삭제 중 오류 발생 시 False 반환
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
        고간 부 본의 가중치를 업데이트합니다.
        
        ## Parameters
        - pelvisWeight (float, optional): 골반 가중치 (None인 경우 현재 값 유지)
        - thighWeight (float, optional): 허벅지 가중치 (None인 경우 현재 값 유지)
            
        ## Returns
        - bool: 업데이트 성공 여부
            - 체인이 비어있거나 업데이트 중 오류 발생 시 False 반환
        
        ## 동작 방식
        1. 현재 본과 헬퍼 삭제
        2. 새 가중치로 고간 부 본 재생성
        3. 새 본과 헬퍼 참조 업데이트
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
        현재 설정된 가중치 값을 가져옵니다.
        
        ## Returns
        - tuple: (pelvis_weight, thigh_weight) 형태의 튜플
            - 골반 가중치와 허벅지 가중치 값 반환
        """
        return (self.pelvis_weight, self.thigh_weight)
    
    @classmethod
    def from_groin_bone_result(cls, inResult):
        """
        GroinBone 클래스의 결과로부터 GroinBoneChain 인스턴스를 생성합니다.
        
        ## Parameters
        - inResult (dict): GroinBone.create_bone() 메소드의 결과 딕셔너리
            
        ## Returns
        - GroinBoneChain: 생성된 GroinBoneChain 인스턴스
        
        ## 사용 예시
        ```python
        result = groin_bone.create_bone(pelvis, lThighTwist, rThighTwist)
        chain = GroinBoneChain.from_groin_bone_result(result)
        ```
        """
        chain = cls(inResult)
        
        return chain