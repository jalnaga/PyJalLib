#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
관절 부피 유지 본(Volume preserve Bone) 모듈 - 3ds Max용 관절의 부피를 유지하기 위해 추가되는 중간본들을 위한 모듈
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint

class VolumeBone:  # Updated class name to match the new file name
    """
    관절 부피 유지 본(Volume preserve Bone) 클래스
    3ds Max에서 관절의 부피를 유지하기 위해 추가되는 중간본들을 위한 클래스
    """
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constService: 제약 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        
        self.rootBone = None
        self.rotHelper = None
        self.limb = None
        self.limbParent = None
        
        self.posScriptExpression = (
            "localLimbTm = limb.transform * inverse limbParent.transform\n"
            "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat q.angle proj\n"
            "twist = normalize twist\n"
            "saturatedTwist = amin (twist.angle/180.0) 1.0\n"
            "\n"
            "trAxis * saturatedTwist * volumeSize * transScale\n"
        )
    
    def create_root_bone(self, inObj, inParent, inRotScale=0.5):
        if rt.isValidNode(inObj) == False or rt.isValidNode(inParent) == False:
            return False
        
        if rt.isValidNode(self.rootBone) and rt.isValidNode(self.rotHelper):
            return self.rootBone
        
        rootBoneName = inObj.name
        filteringChar = self.name._get_filtering_char(rootBoneName)
        rootBoneName = self.name.add_suffix_to_real_name(rootBoneName, filteringChar+"Root")
        
        rootBone = self.bone.create_nub_bone(rootBoneName, 2)
        rootBone.name = self.name.remove_name_part("Nub", rootBone.name)
        if rootBone.name[0].islower():
            rootBone.name = rootBone.name.lower()
            rootBoneName = rootBoneName.lower()
            
        rt.setProperty(rootBone, "transform", inObj.transform)
        rootBone.parent = inObj
        
        rotHelper = self.helper.create_point(rootBoneName)
        rotHelper.name = self.name.replace_name_part("Type", rotHelper.name, self.name.get_name_part_value_by_description("Type", "Dummy"))
        rt.setProperty(rotHelper, "transform", inObj.transform)
        rotHelper.parent = inParent
        
        oriConst = self.const.assign_rot_const_multi(rootBone, [inObj, rotHelper])
        oriConst.setWeight(1, inRotScale * 100.0)
        oriConst.setWeight(2, (1.0 - inRotScale) * 100.0)
        
        self.rootBone = rootBone
        self.rotHelper = rotHelper
        self.limb = inObj
        self.limbParent = inParent
        
        return self.rootBone
    
    def create_bone(self, inObj, inParent, inRotScale=0.5, inVolumeSize=5.0, inRotAxis="Z", inTransAxis="PosY", inTransScale=1.0, useRootBone=True, inRootBone=None):
        if rt.isValidNode(inObj) == False or rt.isValidNode(inParent) == False:
            return False
        
        if useRootBone:
            if rt.isValidNode(self.rootBone) == False and rt.isValidNode(self.rotHelper) == False:
                return False
            self.rootBone = inRootBone if inRootBone else self.create_root_bone(inObj, inParent, inRotScale)
        else:
            self.create_root_bone(inObj, inParent, inRotScale)
        
        self.limb = inObj
        self.limbParent = inParent
        
        volBoneName = inObj.name
        filteringChar = self.name._get_filtering_char(volBoneName)
        volBoneName = self.name.add_suffix_to_real_name(volBoneName, filteringChar + "Vol" + filteringChar + inRotAxis + filteringChar+ inTransAxis)
        
        volBone = self.bone.create_nub_bone(volBoneName, 2)
        volBone.name = self.name.remove_name_part("Nub", volBone.name)
        if volBone.name[0].islower():
            volBone.name = volBone.name.lower()
            volBoneName = volBoneName.lower()
        rt.setProperty(volBone, "transform", self.rootBone.transform)
        
        volBoneTrDir = rt.Point3(0.0, 0.0, 0.0)
        if inTransAxis == "PosX":
            volBoneTrDir = rt.Point3(1.0, 0.0, 0.0)
        elif inTransAxis == "NegX":
            volBoneTrDir = rt.Point3(-1.0, 0.0, 0.0)
        elif inTransAxis == "PosY":
            volBoneTrDir = rt.Point3(0.0, 1.0, 0.0)
        elif inTransAxis == "NegY":
            volBoneTrDir = rt.Point3(0.0, -1.0, 0.0)
        elif inTransAxis == "PosZ":
            volBoneTrDir = rt.Point3(0.0, 0.0, 1.0)
        elif inTransAxis == "NegZ":
            volBoneTrDir = rt.Point3(0.0, 0.0, -1.0)
        
        self.anim.move_local(volBone, volBoneTrDir[0]*inVolumeSize, volBoneTrDir[1]*inVolumeSize, volBoneTrDir[2]*inVolumeSize)
        volBone.parent = self.rootBone
        
        rotAxis = rt.Point3(0.0, 0.0, 0.0)
        if inRotAxis == "X":
            rotAxis = rt.Point3(1.0, 0.0, 0.0)
        elif inRotAxis == "Y":
            rotAxis = rt.Point3(0.0, 1.0, 0.0)
        elif inRotAxis == "Z":
            rotAxis = rt.Point3(0.0, 0.0, 1.0)
        
        localRotRefTm = self.limb.transform * rt.inverse(self.limbParent.transform)
        volBonePosConst = self.const.assign_pos_script_controller(volBone)
        volBonePosConst.addNode("limb", self.limb)
        volBonePosConst.addNode("limbParent", self.limbParent)
        volBonePosConst.addConstant("axis", rotAxis)
        volBonePosConst.addConstant("transScale", rt.Float(inTransScale))
        volBonePosConst.addConstant("volumeSize", rt.Float(inVolumeSize))
        volBonePosConst.addConstant("localRotRefTm", localRotRefTm)
        volBonePosConst.addConstant("trAxis", volBoneTrDir)
        volBonePosConst.setExpression(self.posScriptExpression)
        volBonePosConst.update()
        
        return True
    
    def create_bones(self, inObj, inParent, inRotScale=0.5, inVolumeSize=5.0, inRotAxises=["Z"], inTransAxises=["PosY"], inTransScales=[1.0]):
        """
        여러 개의 부피 유지 본을 생성합니다.
        
        Args:
            inObj: 본을 생성할 객체
            inParent: 부모 객체
            inRotScale: 회전 비율
            inVolumeSize: 부피 크기
            inRotAxises: 회전 축 리스트
            inTransAxises: 변환 축 리스트
            inTransScales: 변환 비율 리스트
        
        Returns:
            bool: 성공 여부
        """
        if rt.isValidNode(inObj) == False or rt.isValidNode(inParent) == False:
            return False
        
        if len(inRotAxises) != len(inTransAxises) or len(inRotAxises) != len(inTransScales):
            return False
        
        rootBone = self.create_root_bone(inObj, inParent, inRotScale=inRotScale)
        
        for i in range(len(inRotAxises)):
            self.create_bone(inObj, inParent, inRotScale, inVolumeSize, inRotAxises[i], inTransAxises[i], inTransScales[i], useRootBone=True, inRootBone=rootBone)
        
        return True
        