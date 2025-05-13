#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
볼륨 뼈대 체인(Volume Bone Chain) 관련 기능을 제공하는 클래스.
VolumeBone 클래스가 생성한 볼륨 뼈대들을 관리하고 접근하는 인터페이스를 제공합니다.

Examples:
    # 볼륨 체인 생성 예시
    from pyjallib.max import VolumeBone, VolumeBoneChain
    from pymxs import runtime as rt
    
    # 캐릭터에서 선택된 객체 가져오기
    sel_obj = rt.selection[0]
    
    # VolumeBone 클래스 인스턴스 생성
    volume_bone = VolumeBone()
    
    # 볼륨 뼈대 생성
    volume_result = volume_bone.create_volume(sel_obj, 4, 30.0)
    
    # 생성된 뼈대로 VolumeBoneChain 인스턴스 생성
    chain = VolumeBoneChain.from_volume_bone_result(volume_result)
    
    # 체인 관리 기능 사용
    first_bone = chain.get_first_bone()
    last_bone = chain.get_last_bone()
    middle_bone = chain.get_bone_at_index(2)
    
    # 체인의 모든 뼈대 이름 변경
    chain.rename_bones(prefix="custom_", suffix="_volume")
    
    # 필요 없어지면 체인의 모든 뼈대 삭제
    # chain.delete_all()
"""

import copy

from pymxs import runtime as rt
from .header import jal

class VolumeBoneChain:
    def __init__(self, inResult):
        """
        클래스 초기화.
        
        Args:
            inResult: VolumeBone 클래스의 결과 딕셔너리
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
        
        Returns:
            볼륨 크기 값
        """
        return self.volumeSize
    
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        Returns:
            체인이 비어있으면 True, 아니면 False
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
