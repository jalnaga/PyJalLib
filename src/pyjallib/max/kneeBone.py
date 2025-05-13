#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
자동 쇄골(AutoClavicle) 모듈 - 3ds Max용 자동화된 쇄골 기능 제공
원본 MAXScript의 autoclavicle.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint
from .volumeBone import VolumeBone

class KneeBone:
    """
    자동 무릎 본(AutoKnee) 관련 기능을 제공하는 클래스.
    MAXScript의 _AutoKneeBone 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, volumeBoneService=None):
        """
        클래스 초기화
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.volumeBone = volumeBoneService if volumeBoneService else VolumeBone(nameService=self.name, animService=self.anim, constraintService=self.const, boneService=self.bone, helperService=self.helper)
        
        self.pelvis = None
        self.thigh = None
        self.calf = None
        self.foot = None
        
        self.lookAtHleper = None
        self.thighRotHelper = None
        self.calfRotHelper = None
        
        self.thighRotRootHelper = None
        self.calfRotRootHelper = None
        
        self.thighTwistBones = []
        self.calfTwistBones = []
        self.thighTwistHelpers = []
        self.calfTwistHelpers = []
        
        self.middleBones = []
        
        self.liftScale = 0.1
        
        self.thighRotScriptExpression = (
            "localLimbTm = limb.transform * inverse limbParent.transform\n"
            "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "axis = [0,0,1]\n"
            "\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat -q.angle proj\n"
            "twist = normalize twist\n"
            "\n"
            "twist\n"
        )
        self.calfRotScriptExpression = (
            "localLimbTm = limb.transform * inverse limbParent.transform\n"
            "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "axis = [0,0,1]\n"
            "\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat q.angle proj\n"
            "twist = normalize twist\n"
            "\n"
            "twist\n"
        )
            
    
    def create_lookat_helper(self, inPelvis, inThigh, inFoot):
        if not rt.isValidNode(inPelvis) or not rt.isValidNode(inThigh) or not rt.isValidNode(inFoot):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = inThigh.name.islower()
        
        # 서비스 인스턴스 설정 또는 생성
        self.pelvis = inPelvis
        self.thigh = inThigh
        self.foot = inFoot
        
        lookAtHelperName = self.name.replace_name_part("Type", inThigh.name, self.name.get_name_part_value_by_description("Type", "LookAt"))
        lookAtHelperName = self.name.add_suffix_to_real_name(lookAtHelperName, filteringChar + "Lift")
        if isLowerName:
            lookAtHelperName = lookAtHelperName.lower()
            
        lookAtHelper = self.helper.create_point(lookAtHelperName)
        lookAtHelper.transform = inThigh.transform
        lookAtHelper.parent = inThigh
        lookAtConst = self.const.assign_lookat(lookAtHelper, inFoot)
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inThigh
        lookAtConst.lookat_vector_length = 0.0
        
        self.lookAtHleper = lookAtHelper
        
    def create_rot_root_heleprs(self, inThigh, inCalf, inFoot):
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf) or not rt.isValidNode(inFoot):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = inThigh.name.islower()
        
        # 서비스 인스턴스 설정 또는 생성
        self.thigh = inThigh
        self.calf = inCalf
        self.foot = inFoot
        
        thighRotRootHelperName = self.name.replace_name_part("Type", inThigh.name, self.name.get_name_part_value_by_description("Type", "Dummy"))
        calfRotRootHelperName = self.name.replace_name_part("Type", inCalf.name, self.name.get_name_part_value_by_description("Type", "Dummy"))
        thighRotRootHelperName = self.name.add_suffix_to_real_name(thighRotRootHelperName, filteringChar + "Lift")
        calfRotRootHelperName = self.name.add_suffix_to_real_name(calfRotRootHelperName, filteringChar + "Lift")
        if isLowerName:
            thighRotRootHelperName = thighRotRootHelperName.lower()
            calfRotRootHelperName = calfRotRootHelperName.lower()
        
        thighRotRootHelper = self.helper.create_point(thighRotRootHelperName, crossToggle=False, boxToggle=True)
        thighRotRootHelper.transform = inThigh.transform
        thighRotRootHelper.parent = inThigh
        
        calfRotRootHelper = self.helper.create_point(calfRotRootHelperName, crossToggle=False, boxToggle=True)
        calfRotRootHelper.transform = inCalf.transform
        calfRotRootHelper.position = inFoot.position
        calfRotRootHelper.parent = inCalf
        
        self.thighRotRootHelper = thighRotRootHelper
        self.calfRotRootHelper = calfRotRootHelper

    def create_rot_helper(self, inThigh, inCalf, inFoot):
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = inThigh.name.islower()
        
        # 서비스 인스턴스 설정 또는 생성
        self.thigh = inThigh
        self.calf = inCalf
        
        thighRotHelperName = self.name.replace_name_part("Type", inThigh.name, self.name.get_name_part_value_by_description("Type", "Rotation"))
        calfRotHelperName = self.name.replace_name_part("Type", inCalf.name, self.name.get_name_part_value_by_description("Type", "Rotation"))
        thighRotHelperName = self.name.add_suffix_to_real_name(thighRotHelperName, filteringChar + "Lift")
        calfRotHelperName = self.name.add_suffix_to_real_name(calfRotHelperName, filteringChar + "Lift")
        if isLowerName:
            thighRotHelperName = thighRotHelperName.lower()
            calfRotHelperName = calfRotHelperName.lower()
        
        thighRotHelper = self.helper.create_point(thighRotHelperName)
        thighRotHelper.transform = inThigh.transform
        thighRotHelper.parent = inThigh
        
        calfRotHelper = self.helper.create_point(calfRotHelperName)
        calfRotHelper.transform = inCalf.transform
        calfRotHelper.position = inFoot.position
        calfRotHelper.parent = inCalf
        
        self.thighRotHelper = thighRotHelper
        self.calfRotHelper = calfRotHelper
    
    def assign_thigh_rot_constraint(self):
        localRotRefTm = self.lookAtHleper.transform * rt.inverse(self.thighRotRootHelper.transform)
        
        rotListConst = self.const.assign_rot_list(self.thighRotHelper)
        rotScriptConst = rt.Rotation_Script()
        rt.setPropertyController(rotListConst, "Available", rotScriptConst)
        rotListConst.setActive(rotListConst.count)
        
        rotScriptConst.addConstant("localRotRefTm", localRotRefTm)
        rotScriptConst.addNode("limb", self.lookAtHleper)
        rotScriptConst.addNode("limbParent", self.thighRotRootHelper)
        rotScriptConst.setExpression(self.thighRotScriptExpression)
        
        self.const.set_rot_controllers_weight_in_list(self.calfRotHelper, 1, self.liftScale * 100.0)
        
    def assign_calf_rot_constraint(self):
        localRotRefTm = self.lookAtHleper.transform * rt.inverse(self.thighRotRootHelper.transform)
        
        rotListConst = self.const.assign_rot_list(self.calfRotHelper)
        rotScriptConst = rt.Rotation_Script()
        rt.setPropertyController(rotListConst, "Available", rotScriptConst)
        rotListConst.setActive(rotListConst.count)
        
        rotScriptConst.addConstant("localRotRefTm", localRotRefTm)
        rotScriptConst.addNode("limb", self.lookAtHleper)
        rotScriptConst.addNode("limbParent", self.thighRotRootHelper)
        rotScriptConst.setExpression(self.calfRotScriptExpression)
        
        self.const.set_rot_controllers_weight_in_list(self.calfRotHelper, 1, self.liftScale * 100.0)
        
    def create_middle_bone(self, inThigh, inCalf, inKneePopScale=1.0, inKneeBackScale=1.0):
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf):
            return False
        
        facingDirVec = inCalf.transform.position - inThigh.transform.position
        inObjXAxisVec = inCalf.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        self.thigh = inThigh
        self.calf = inCalf
        
        transScales = []
        if distanceDir > 0:
            transScales.append(inKneePopScale)
            transScales.append(inKneeBackScale)
        else:
            transScales.append(inKneeBackScale)
            transScales.append(inKneePopScale)
        
        result = self.volumeBone.create_bones(self.calf, self.thigh, inVolumeSize=5.0, inRotAxises=["NegZ", "NegZ"], inTransAxises=["PosY", "NegY"], inTransScales=transScales)

