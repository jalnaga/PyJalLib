#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고간 부 본 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .constraint import Constraint
from .bip import Bip
from .bone import Bone
from .helper import Helper
from .twistBone import TwistBone

class GroinBone:
    """
    고간 부 본 관련 기능을 위한 클래스
    3DS Max에서 고간 부 본을 생성하고 관리하는 기능을 제공합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, constService=None, bipService=None, boneService=None, twistBoneService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: 바이페드 서비스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # Ensure dependent services use the potentially newly created instances
        self.const = constService if constService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(animService=self.anim, nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.twistBone = twistBoneService if twistBoneService else TwistBone(nameService=self.name, animService=self.anim, constService=self.const, bipService=self.bip, boneService=self.bone)
        self.helper = helperService if helperService else Helper(nameService=self.name)
    
    def create_bone(self, inObj):
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
        
        groinBones = self.bone.create_simple_bone(3.0, bipObj.name +" Groin 00", size=2)
        groinBones[0].transform = pelvisHelper.transform
        groinBones[0].parent = pelvis
        
        self.const.assign_rot_const_multi(groinBones[0], [pelvisHelper, lThigh, rThigh])
        rotConst = self.const.get_rot_list_controller(groinBones[0])[1]
        rotConst.setWeight(1, 40.0)
        rotConst.setWeight(2, 30.0)
        rotConst.setWeight(3, 30.0)
        
        
        