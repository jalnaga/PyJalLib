#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고간 부 본 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint

class GroinBone:
    """
    고간 부 본 관련 기능을 위한 클래스
    3DS Max에서 고간 부 본을 생성하고 관리하는 기능을 제공합니다.
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            twistBoneService: 트위스트 본 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
    
    def create_bone(self, inPelvis, inLThighTwist, inRThighTwist, inPelvisWeight=40.0, inThighWeight=60.0):
        """
        고간 부 본을 생성하는 메소드.
        
        Args:
            inPelvis: Biped 객체
            inPelvisWeight: 골반 가중치 (기본값: 40.0)
            inThighWeight: 허벅지 가중치 (기본값: 60.0)
        
        Returns:
            성공 여부 (Boolean)
        """
        returnVal = {
            "pelvis": None,
            "lThighTwist": None,
            "rThighTwist": None,
            "Bones": [],
            "Helpers": [],
            "pelvisWeight": inPelvisWeight,
            "thighWeight": inThighWeight
        }
        if rt.isValidNode(inPelvis) == False or rt.isValidNode(inLThighTwist) == False or rt.isValidNode(inRThighTwist) == False:
            rt.messageBox("There is no valid node.")
            return False
        
        groinBaseName = self.name.add_suffix_to_real_name(inPelvis.name, self.name._get_filtering_char(inPelvis.name) + "Groin")
        
        pelvisHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelperName = self.name.replace_name_part("Index", pelvisHelperName, "00")
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        pelvisHelper.transform = inPelvis.transform
        self.const.assign_rot_const_multi(pelvisHelper, [inLThighTwist, inRThighTwist])
        self.const.collapse(pelvisHelper)
        pelvisHelper.parent = inPelvis
        self.helper.set_shape_to_box(pelvisHelper)
        self.genHelpers.append(pelvisHelper)
        
        groinBoneName = self.name.replace_name_part("Index", groinBaseName, "00")
        groinBones = self.bone.create_simple_bone(3.0, groinBoneName, size=2)
        groinBones[0].transform = pelvisHelper.transform
        groinBones[0].parent = inPelvis
        for groinBone in groinBones:
            self.genBones.append(groinBone)
        
        self.const.assign_rot_const_multi(groinBones[0], [pelvisHelper, inLThighTwist, inRThighTwist])
        rotConst = self.const.get_rot_list_controller(groinBones[0])[1]
        rotConst.setWeight(1, inPelvisWeight)
        rotConst.setWeight(2, inThighWeight/2.0)
        rotConst.setWeight(3, inThighWeight/2.0)
        
        returnVal["pelvis"] = inPelvis
        returnVal["lThighTwist"] = inLThighTwist
        returnVal["rThighTwist"] = inRThighTwist
        returnVal["Bones"] = groinBones
        returnVal["Helpers"] = [pelvisHelper]
        returnVal["pelvisWeight"] = inPelvisWeight
        returnVal["thighWeight"] = inThighWeight
        
        return returnVal
