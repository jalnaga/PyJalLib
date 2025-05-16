#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 볼륨 뼈대 체인(VolumeBoneChain) 모듈

3ds Max에서 관절의 볼륨감을 유지하기 위한 보조 본 그룹을 관리하는 모듈입니다.

## 주요 기능
- 볼륨 본 그룹 통합 관리 및 속성 접근
- 볼륨 크기, 회전 및 이동 축 동적 업데이트
- 회전 영향도 조절
- 볼륨 본 체인 삭제 및 초기화

## 구현 정보
- VolumeBone 클래스가 생성한 본 시스템의 래퍼 클래스
- pymxs 모듈을 통해 3ds Max API 접근
- jal.volumeBone을 통한 볼륨 본 재생성
"""

import copy

from pymxs import runtime as rt
from .header import jal

class VolumeBoneChain:
    """
    # VolumeBoneChain 클래스
    
    VolumeBone 클래스로 생성된 볼륨 본 세트를 관리하는 클래스입니다.
    
    ## 주요 기능
    - 볼륨 본 체인 통합 관리 및 속성 접근
    - 볼륨 크기, 회전 축, 이동 축 등 동적 업데이트
    - 회전 영향도 조절
    - 볼륨 본 체인 관련 정보 조회
    - 일괄 삭제 및 초기화
    
    ## 구현 정보
    - VolumeBone.create_bones() 메서드의 결과를 관리
    - copy 모듈을 활용한 속성 딥 카피
    - jal.volumeBone을 통한 재생성 로직
    
    ## 사용 예시
    ```python
    # VolumeBone 클래스의 결과로부터 생성
    volume_bone = VolumeBone()
    result = volume_bone.create_bones(elbow_bone, upper_arm, 
                                      inRotAxises=["X", "Z"],
                                      inTransAxises=["PosY", "PosZ"])
    chain = VolumeBoneChain.from_volume_bone_result(result)
    
    # 체인 속성 및 관리 기능 사용
    print(f"볼륨 크기: {chain.get_volume_size()}")
    print(f"볼륨 본 개수: {len(chain.bones)}")
    
    # 볼륨 속성 동적 업데이트
    chain.update_volume_size(15.0)    # 볼륨 크기 변경
    chain.update_rot_scale(0.5)       # 회전 영향도 변경
    chain.update_rot_axises(["Y", "Z"])  # 회전 축 업데이트
    ```
    """
    
    def __init__(self, inResult):
        """
        볼륨 본 체인 클래스를 초기화합니다.
        
        ## Parameters
        - inResult (dict): VolumeBone 클래스의 create_bones 메서드가 반환한 결과 딕셔너리
            - RootBone: 루트 본 객체
            - RotHelper: 회전 헬퍼 객체
            - RotScale: 회전 가중치 값
            - Limb: 타겟 팔다리 객체
            - LimbParent: 타겟의 부모 객체
            - Bones: 생성된 볼륨 본 배열
            - RotAxises: 회전 축 배열
            - TransAxises: 이동 축 배열
            - TransScales: 이동 스케일 배열
            - VolumeSize: 볼륨 크기 값
        """
        self.rootBone = inResult.get("RootBone", None)
        self.rotHelper = inResult.get("RotHelper", None)
        self.rotScale = inResult.get("RotScale", 0.0)
        self.limb = inResult.get("Limb", None)
        self.limbParent = inResult.get("LimbParent", None)
        self.bones = inResult.get("Bones", [])
        self.rotAxises = inResult.get("RotAxises", [])
        self.transAxises = inResult.get("TransAxises", [])
        self.transScales = inResult.get("TransScales", [])
        self.volumeSize = inResult.get("VolumeSize", 0.0)
    
    def get_volume_size(self):
        """
        볼륨 뼈대의 크기를 가져옵니다.
        
        ## Returns
        - float: 현재 설정된 볼륨 크기 값
        """
        return self.volumeSize
    
    def is_empty(self):
        """
        체인이 비어있는지 확인합니다.
        
        ## Returns
        - bool: 체인이 비어있으면 True, 하나 이상의 본이 있으면 False
        """
        return len(self.bones) == 0
    
    def clear(self):
        """
        체인의 모든 뼈대 및 헬퍼 참조를 제거합니다.
        
        ## 동작 방식
        객체에 저장된 모든 참조를 초기화하지만 3ds Max 씬에서 객체를 삭제하지는 않습니다.
        """
        self.rootBone = None
        self.rotHelper = None
        self.rotScale = 0.0
        self.limb = None
        self.limbParent = None
        self.bones = []
        self.rotAxises = []
        self.transAxises = []
        self.transScales = []
        self.volumeSize = 0.0
    
    def delete_all(self):
        """
        체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제합니다.
        
        ## Returns
        - bool: 삭제 성공 여부 (True/False)
        
        ## 동작 방식
        1. 체인이 비어있는지 확인
        2. 루트 본, 회전 헬퍼, 모든 볼륨 본을 씬에서 삭제
        3. 체인 참조 초기화
        """
        if self.is_empty():
            return False
            
        try:
            # 루트 본 삭제
            if self.rootBone:
                rt.delete(self.rootBone)
            
            # 회전 헬퍼 삭제
            if self.rotHelper:
                rt.delete(self.rotHelper)
                
            # 뼈대 삭제
            for bone in self.bones:
                rt.delete(bone)
                                
            self.rotAxises = []
            self.transAxises = []
            self.transScales = []    
                
            self.clear()
            return True
        except:
            return False
    
    def update_volume_size(self, inNewSize):
        """
        볼륨 뼈대의 크기를 업데이트합니다.
        
        ## Parameters
        - inNewSize (float): 새로운 볼륨 크기 값
            
        ## Returns
        - bool: 업데이트 성공 여부 (True/False)
        
        ## 동작 방식
        1. 기존의 볼륨 본 체인 설정을 백업
        2. 모든 본과 헬퍼를 삭제
        3. 새로운 크기로 jal.volumeBone.create_bones() 호출하여 재생성
        4. 생성 결과를 현재 객체에 적용
        """
        if self.is_empty() or self.limb is None:
            return False
            
        try:
            # 필요한 값들 백업
            limb = self.limb
            limbParent = self.limbParent 
            rotScale = self.rotScale
            rotAxises = copy.deepcopy(self.rotAxises)
            transAxises = copy.deepcopy(self.transAxises)
            transScales = copy.deepcopy(self.transScales)
            
            self.delete_all()
            # VolumeBone 클래스를 통해 새로운 볼륨 뼈대 생성
            result = jal.volumeBone.create_bones(limb, limbParent, inVolumeSize=inNewSize, 
                                                 inRotScale=rotScale, inRotAxises=rotAxises, 
                                                 inTransAxises=transAxises, inTransScales=transScales)
            
            # 속성들 한번에 업데이트
            for key, value in result.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.volumeSize = inNewSize
            
            return True
        except:
            return False
    
    def update_rot_axises(self, inNewRotAxises):
        """
        볼륨 뼈대의 회전 축을 업데이트합니다.
    
        ## Parameters
        - inNewRotAxises (list): 새로운 회전 축 리스트 (["X", "Y", "Z"] 등)
        
        ## Returns
        - bool: 업데이트 성공 여부 (True/False)
        
        ## 동작 방식
        1. 기존의 볼륨 본 체인 설정을 백업
        2. 모든 본과 헬퍼를 삭제
        3. 새로운 회전 축으로 jal.volumeBone.create_bones() 호출하여 재생성
        4. 생성 결과를 현재 객체에 적용
        """
        if self.is_empty() or self.limb is None:
            return False
        
        try:
            # 필요한 값들 백업
            limb = self.limb
            limbParent = self.limbParent 
            rotScale = self.rotScale
            volumeSize = self.volumeSize
            transAxises = copy.deepcopy(self.transAxises)
            transScales = copy.deepcopy(self.transScales)
            
            self.delete_all()
            # VolumeBone 클래스를 통해 새로운 볼륨 뼈대 생성
            result = jal.volumeBone.create_bones(limb, limbParent, inVolumeSize=volumeSize, 
                                                inRotScale=rotScale, inRotAxises=inNewRotAxises, 
                                                inTransAxises=transAxises, inTransScales=transScales)
            
            # 속성들 한번에 업데이트
            for key, value in result.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            return True
        except:
            return False

    def update_trans_axises(self, inNewTransAxises):
        """
        볼륨 뼈대의 이동 축을 업데이트합니다.
    
        ## Parameters
        - inNewTransAxises (list): 새로운 이동 축 리스트 (["PosX", "NegY", "PosZ"] 등)
        
        ## Returns
        - bool: 업데이트 성공 여부 (True/False)
        
        ## 동작 방식
        1. 기존의 볼륨 본 체인 설정을 백업
        2. 모든 본과 헬퍼를 삭제
        3. 새로운 이동 축으로 jal.volumeBone.create_bones() 호출하여 재생성
        4. 생성 결과를 현재 객체에 적용
        """
        if self.is_empty() or self.limb is None:
            return False
        
        try:
            # 필요한 값들 백업
            limb = self.limb
            limbParent = self.limbParent 
            rotScale = self.rotScale
            volumeSize = self.volumeSize
            rotAxises = copy.deepcopy(self.rotAxises)
            transScales = copy.deepcopy(self.transScales)
            
            self.delete_all()
            # VolumeBone 클래스를 통해 새로운 볼륨 뼈대 생성
            result = jal.volumeBone.create_bones(limb, limbParent, inVolumeSize=volumeSize, 
                                                inRotScale=rotScale, inRotAxises=rotAxises, 
                                                inTransAxises=inNewTransAxises, inTransScales=transScales)
            
            # 속성들 한번에 업데이트
            for key, value in result.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            return True
        except:
            return False

    def update_trans_scales(self, inNewTransScales):
        """
        볼륨 뼈대의 이동 스케일을 업데이트합니다.
    
        ## Parameters
        - inNewTransScales (list): 새로운 이동 스케일 리스트 ([1.0, 0.8, 1.2] 등)
        
        ## Returns
        - bool: 업데이트 성공 여부 (True/False)
        
        ## 동작 방식
        1. 기존의 볼륨 본 체인 설정을 백업
        2. 모든 본과 헬퍼를 삭제
        3. 새로운 이동 스케일로 jal.volumeBone.create_bones() 호출하여 재생성
        4. 생성 결과를 현재 객체에 적용
        """
        if self.is_empty() or self.limb is None:
            return False
        
        try:
            # 필요한 값들 백업
            limb = self.limb
            limbParent = self.limbParent 
            rotScale = self.rotScale
            volumeSize = self.volumeSize
            rotAxises = copy.deepcopy(self.rotAxises)
            transAxises = copy.deepcopy(self.transAxises)
            
            self.delete_all()
            # VolumeBone 클래스를 통해 새로운 볼륨 뼈대 생성
            result = jal.volumeBone.create_bones(limb, limbParent, inVolumeSize=volumeSize, 
                                                inRotScale=rotScale, inRotAxises=rotAxises, 
                                                inTransAxises=transAxises, inTransScales=inNewTransScales)
            
            # 속성들 한번에 업데이트
            for key, value in result.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            return True
        except:
            return False
    
    def update_rot_scale(self, inNewRotScale):
        """
        볼륨 뼈대의 회전 스케일을 업데이트합니다.
    
        ## Parameters
        - inNewRotScale (float): 새로운 회전 스케일 값 (0.0~1.0)
        
        ## Returns
        - bool: 업데이트 성공 여부 (True/False)
        
        ## 동작 방식
        1. 기존의 볼륨 본 체인 설정을 백업
        2. 모든 본과 헬퍼를 삭제
        3. 새로운 회전 스케일로 jal.volumeBone.create_bones() 호출하여 재생성
        4. 생성 결과를 현재 객체에 적용
        """
        if self.is_empty() or self.limb is None:
            return False
        
        try:
            # 필요한 값들 백업
            limb = self.limb
            limbParent = self.limbParent 
            volumeSize = self.volumeSize
            rotAxises = copy.deepcopy(self.rotAxises)
            transAxises = copy.deepcopy(self.transAxises)
            transScales = copy.deepcopy(self.transScales)
            
            self.delete_all()
            # VolumeBone 클래스를 통해 새로운 볼륨 뼈대 생성
            result = jal.volumeBone.create_bones(limb, limbParent, inVolumeSize=volumeSize, 
                                                inRotScale=inNewRotScale, inRotAxises=rotAxises, 
                                                inTransAxises=transAxises, inTransScales=transScales)
            
            # 속성들 한번에 업데이트
            for key, value in result.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        
            return True
        except:
            return False
    
    @classmethod
    def from_volume_bone_result(cls, inResult):
        """
        VolumeBone 클래스의 결과로부터 VolumeBoneChain 인스턴스를 생성합니다.
        
        ## Parameters
        - inResult (dict): VolumeBone 클래스의 create_bones() 메서드가 반환한 결과 딕셔너리
            
        ## Returns
        - VolumeBoneChain: 생성된 VolumeBoneChain 인스턴스
        
        ## 동작 방식
        결과 딕셔너리를 사용하여 새 VolumeBoneChain 인스턴스를 생성하고 반환합니다.
        """
        chain = cls(inResult)
        return chain
