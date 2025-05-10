#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고간 부 본 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공
"""

from pymxs import runtime as rt

from .header import jal

class GroinBone:
    """
    고간 부 본 관련 기능을 위한 클래스
    3DS Max에서 고간 부 본을 생성하고 관리하는 기능을 제공합니다.
    """
    
    def __init__(self):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: 바이페드 서비스 (제공되지 않으면 새로 생성)
        """
        self.name = jal.name
        self.anim = jal.anim
        # Ensure dependent services use the potentially newly created instances
        self.const = jal.constraint
        self.bip = jal.bip
        self.bone = jal.bone
        self.twistBone = jal.twistBone
        self.helper = jal.helper
        
        self.bipObj = None
        self.genBones = []
        self.genHelpers = []
    
    def create_bone(self, inObj, inPelvisWeight=40.0, inThighWeight=60.0):
        """
        고간 부 본을 생성하는 메소드.
        
        Args:
            name: 생성할 본의 이름
            parent: 부모 본 (제공되지 않으면 None)
        
        Returns:
            생성된 본 객체
        """
        if self.bip.is_biped_object(inObj) == False:
            rt.messageBox("This is not a biped object.")
            return False
        
        bipObj = self.bip.get_com(inObj)
        self.bipObj = bipObj
        
        lThigh = self.bip.get_grouped_nodes(inObj, "lLeg")[0]
        rThigh = self.bip.get_grouped_nodes(inObj, "rLeg")[0]
        pelvis = self.bip.get_grouped_nodes(inObj, "pelvis")[0]
        
        lThighTwists = self.twistBone.get_thigh_type(lThigh)
        rThighTwists = self.twistBone.get_thigh_type(rThigh)
        
        if len(lThighTwists) == 0 or len(rThighTwists) == 0:
            rt.messageBox("There is no twist bone.")
            return False
        
        pelvisHelper = self.helper.create_point(bipObj.name + " Dum Groin 00")
        pelvisHelper.transform = bipObj.transform
        self.anim.rotate_local(pelvisHelper, 90, 0, 0)
        self.anim.rotate_local(pelvisHelper, 0, 0, -90)
        pelvisHelper.parent = pelvis
        self.helper.set_shape_to_box(pelvisHelper)
        self.genHelpers.append(pelvisHelper)
        
        groinBones = self.bone.create_simple_bone(3.0, bipObj.name +" Groin 00", size=2)
        groinBones[0].transform = pelvisHelper.transform
        groinBones[0].parent = pelvis
        for groinBone in groinBones:
            self.genBones.append(groinBone)
        
        self.const.assign_rot_const_multi(groinBones[0], [pelvisHelper, lThigh, rThigh])
        rotConst = self.const.get_rot_list_controller(groinBones[0])[1]
        rotConst.setWeight(1, inPelvisWeight)
        rotConst.setWeight(2, inThighWeight/2.0)
        rotConst.setWeight(3, inThighWeight/2.0)
        
    def delete(self):
        """
        생성된 고간 부 본과 헬퍼를 삭제하는 메소드.
        
        Returns:
            None
        """
        rt.delete(self.genBones)
        rt.delete(self.genHelpers)
        
        self.genBones = []
        self.genHelpers = []
    
    def update_weight(self, inPelvisWeight=40.0, inThighWeight=60.0):
        """
        고간 부 본의 가중치를 업데이트하는 메소드.
        
        Args:
            inPelvisWeight: 골반 가중치
            inThighWeight: 허벅지 가중치
        
        Returns:
            None
        """
        if len(self.genBones) == 0:
            return False
        
        self.delete()
        self.create_bone(self.bipObj, inPelvisWeight, inThighWeight)
        
        
        