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
from .bip import Bip


class AutoClavicle:
    """
    자동 쇄골(AutoClavicle) 관련 기능을 제공하는 클래스.
    MAXScript의 _AutoClavicleBone 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, bipService=None):
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
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim)
        
        self.boneSize = 2.0
    
    def create_bones(self, inClavicle, inUpperArm, liftScale=0.8):
        """
        자동 쇄골 뼈를 생성하고 설정합니다.
        
        Args:
            inClavicle: 쇄골 뼈 객체
            inUpperArm: 상완 뼈 객체
            liftScale: 들어올림 스케일 (기본값: 0.8)
            
        Returns:
            생성된 자동 쇄골 뼈대 배열 또는 AutoClavicleChain 클래스에 전달할 수 있는 딕셔너리
        """
        if not rt.isValidNode(inClavicle) or not rt.isValidNode(inUpperArm):
            return False
        
        # 리스트 초기화
        genBones = []
        genHelpers = []
        
        # 쇄골과 상완 사이의 거리 계산
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        
        # 임시 헬퍼 포인트 생성
        tempHelperA = rt.Point()
        tempHelperB = rt.Point()
        tempHelperA.transform = inClavicle.transform
        tempHelperB.transform = inClavicle.transform
        self.anim.move_local(tempHelperB, clavicleLength/2.0, 0.0, 0.0)
        
        # 자동 쇄골 이름 생성 및 뼈대 생성
        autoClavicleName = self.name.replace_name_part("RealName", inClavicle.name, "Auto" + self.name._get_filtering_char(inClavicle.name) + "Clavicle")
        if inClavicle.name[0].islower():
            autoClavicleName = autoClavicleName.lower()
        
        autoClavicleBones = self.bone.create_bone(
            [tempHelperA, tempHelperB], 
            autoClavicleName, 
            end=True, 
            delPoint=True, 
            parent=False, 
            size=self.boneSize
        )
        autoClavicleBones[0].transform = inClavicle.transform
        self.anim.move_local(autoClavicleBones[0], clavicleLength/2.0, 0.0, 0.0)
        autoClavicleBones[0].parent = inClavicle
        genBones.extend(autoClavicleBones)
        
        # LookAt 설정
        ikGoal = self.helper.create_point(autoClavicleName, boxToggle=False, crossToggle=True)
        ikGoal.transform = autoClavicleBones[1].transform
        ikGoal.name = self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target"))
        autClavicleLookAtConst = self.const.assign_lookat(autoClavicleBones[0], ikGoal)
        autClavicleLookAtConst.upnode_world = False
        autClavicleLookAtConst.pickUpNode = inClavicle
        autClavicleLookAtConst.lookat_vector_length = 0.0
        genHelpers.append(ikGoal)
        
        # 회전 헬퍼 포인트 생성
        autoClavicleRotHelper = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Rotation")))
        autoClavicleRotHelper.transform = autoClavicleBones[0].transform
        autoClavicleRotHelper.parent = inClavicle
        genHelpers.append(autoClavicleRotHelper)
        
        # 타겟 헬퍼 포인트 생성 (쇄골과 상완용)
        rotTargetClavicle = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target")))
        rotTargetClavicle.transform = inClavicle.transform
        self.anim.move_local(rotTargetClavicle, clavicleLength, 0.0, 0.0)
        genHelpers.append(rotTargetClavicle)
        
        rotTargetUpperArm = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target")))
        rotTargetUpperArm.name = self.name.add_suffix_to_real_name(rotTargetUpperArm.name, self.name._get_filtering_char(inClavicle.name) + "upper")
        rotTargetUpperArm.transform = inUpperArm.transform
        self.anim.move_local(rotTargetUpperArm, (clavicleLength/2.0)*liftScale, 0.0, 0.0)
        genHelpers.append(rotTargetUpperArm)
        
        # 부모 설정
        rotTargetClavicle.parent = inClavicle
        rotTargetUpperArm.parent = inUpperArm
        
        # LookAt 제약 설정
        lookAtConst = self.const.assign_lookat_multi(autoClavicleRotHelper, [rotTargetClavicle, rotTargetUpperArm])
        
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inClavicle
        lookAtConst.lookat_vector_length = 0.0
        
        ikGoal.parent = autoClavicleRotHelper
        
        # 결과를 멤버 변수에 저장
        self.genBones = genBones
        
        # AutoClavicleChain에 전달할 수 있는 딕셔너리 형태로 결과 반환
        result = {
            "Bones": genBones,
            "Helpers": self.helpers,
            "Clavicle": inClavicle,
            "UpperArm": inUpperArm,
            "LiftScale": liftScale
        }
        
        result["Bones"] = genBones
        result["Helpers"] = genHelpers
        result["Clavicle"] = inClavicle
        result["UpperArm"] = inUpperArm
        result["LiftScale"] = liftScale
        
        return result
