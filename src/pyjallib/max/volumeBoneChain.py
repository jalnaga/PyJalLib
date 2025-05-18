#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
볼륨 뼈대 체인(Volume Bone Chain) 모듈 - 3ds Max 캐릭터 리깅을 위한 볼륨 본 시스템

이 모듈은 VolumeBone 클래스가 생성한 볼륨 본 세트를 관리하고 제어하는 기능을 제공합니다.
관절 회전 시 부피 감소를 방지하기 위한 보조 본 시스템으로, 특히 캐릭터 팔다리나 
관절 부위의 자연스러운 움직임을 구현하는 데 유용합니다.

Examples:
    # 기본 볼륨 체인 생성 예시
    from pyjallib.max import VolumeBone, VolumeBoneChain
    from pymxs import runtime as rt
    
    # 캐릭터에서 팔꿈치 뼈대와 상위 부모 가져오기
    elbow_bone = rt.getNodeByName("L_Elbow_Bone")
    upper_arm = rt.getNodeByName("L_UpperArm_Bone")
    
    # VolumeBone 클래스 인스턴스 생성
    volume_bone = VolumeBone()
    
    # 다양한 옵션으로 볼륨 뼈대 생성
    volume_result = volume_bone.create_bones(
        elbow_bone,                   # 관절 본
        upper_arm,                    # 관절 부모
        inRotScale=0.7,               # 회전 영향도 (0.0 ~ 1.0)
        inVolumeSize=10.0,            # 볼륨 크기
        inRotAxises=["X", "Z"],       # 회전 감지 축 (여러 축 지정 가능)
        inTransAxises=["PosY", "PosZ"], # 이동 방향 축
        inTransScales=[1.0, 0.8]      # 각 방향별 이동 스케일
    )
    
    # 생성된 뼈대로 VolumeBoneChain 인스턴스 생성
    chain = VolumeBoneChain.from_volume_bone_result(volume_result)
    
    # 체인 속성 및 관리 기능 사용
    print(f"볼륨 크기: {chain.get_volume_size()}")
    print(f"볼륨 본 개수: {len(chain.bones)}")
    
    # 볼륨 속성 동적 업데이트
    chain.update_volume_size(15.0)    # 볼륨 크기 변경
    chain.update_rot_scale(0.5)       # 회전 영향도 변경
    
    # 회전 축 업데이트
    chain.update_rot_axises(["Y", "Z"])
    
    # 이동 축 업데이트
    chain.update_trans_axises(["PosX", "PosZ"])
    
    # 이동 스케일 업데이트
    chain.update_trans_scales([0.7, 1.2])
    
    # 필요 없어지면 체인의 모든 뼈대 삭제
    # chain.delete_all()
"""

import copy

from pymxs import runtime as rt
from pyjallib.max.header import get_pyjallibmaxheader
jal = get_pyjallibmaxheader()

class VolumeBoneChain:
    """
    볼륨 본 체인 관리 클래스
    
    VolumeBone 클래스로 생성된 볼륨 본들의 집합을 관리하는 클래스입니다.
    볼륨 본의 크기 조절, 회전 및 이동 축 변경, 스케일 조정 등의 기능을 제공하며,
    여러 개의 볼륨 본을 하나의 논리적 체인으로 관리합니다.
    생성된 볼륨 본 체인은 캐릭터 관절의 자연스러운 변형을 위해 사용됩니다.
    """
    
    def __init__(self, inResult):
        """
        볼륨 본 체인 클래스 초기화
        
        VolumeBone 클래스의 create_bones 메서드로부터 생성된 결과 딕셔너리를 
        받아 볼륨 본 체인을 구성합니다.
        
        Args:
            inResult: VolumeBone 클래스의 create_bones 메서드가 반환한 결과 딕셔너리
                      (루트 본, 회전 헬퍼, 회전 축, 이동 축, 볼륨 크기 등의 정보 포함)
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
        볼륨 뼈대의 크기 가져오기
        
        볼륨 본 생성 시 설정된 크기 값을 반환합니다. 이 값은 관절의 볼륨감 정도를
        결정합니다.
        
        Returns:
            float: 현재 설정된 볼륨 크기 값
        """
        return self.volumeSize
    
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        볼륨 본 체인에 본이 하나라도 존재하는지 확인합니다.
        
        Returns:
            bool: 체인이 비어있으면 True, 하나 이상의 본이 있으면 False
        """
        return len(self.bones) == 0
    
    def clear(self):
        """체인의 모든 뼈대 및 헬퍼 참조 제거"""
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
        체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            삭제 성공 여부 (boolean)
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
        볼륨 뼈대의 크기 업데이트
        
        Args:
            inNewSize: 새로운 볼륨 크기 값
            
        Returns:
            업데이트 성공 여부 (boolean)
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
        볼륨 뼈대의 회전 축을 업데이트
    
        Args:
            inNewRotAxises: 새로운 회전 축 리스트
        
        Returns:
            업데이트 성공 여부 (boolean)
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
        볼륨 뼈대의 이동 축을 업데이트
    
        Args:
            inNewTransAxises: 새로운 이동 축 리스트
        
        Returns:
            업데이트 성공 여부 (boolean)
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
        볼륨 뼈대의 이동 스케일을 업데이트
    
        Args:
            inNewTransScales: 새로운 이동 스케일 리스트
        
        Returns:
            업데이트 성공 여부 (boolean)
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
        볼륨 뼈대의 회전 스케일을 업데이트
    
        Args:
            inNewRotScale: 새로운 회전 스케일 값
        
        Returns:
            업데이트 성공 여부 (boolean)
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
        VolumeBone 클래스의 결과로부터 VolumeBoneChain 인스턴스 생성
        
        Args:
            inResult: VolumeBone 클래스의 메서드가 반환한 결과 딕셔너리
            
        Returns:
            VolumeBoneChain 인스턴스
        """
        chain = cls(inResult)
        return chain
