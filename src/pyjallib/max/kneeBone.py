#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
자동 무릎 본(AutoKnee) 모듈 - 3ds Max용 자동화된 무릎 본 기능 제공
원본 MAXScript의 autoKnee.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
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
    
    이 클래스는 IK 시스템 기반의 다리 리깅을 자동화하며, 무릎 관절 회전, 비틀림 본 및 
    중간 본을 생성하여 자연스러운 무릎 움직임을 구현합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, volumeBoneService=None):
        """
        KneeBone 클래스 초기화
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            volumeBoneService: 볼륨 본 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.volumeBone = volumeBoneService if volumeBoneService else VolumeBone(nameService=self.name, animService=self.anim, constraintService=self.const, boneService=self.bone, helperService=self.helper)
        
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
        
        self.liftScale = 0.025
        
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
            
    
    def create_lookat_helper(self, inThigh, inFoot):
        """
        무릎 시스템을 위한 LookAt 헬퍼 객체를 생성합니다.
        
        이 헬퍼는 대퇴골(Thigh)에 위치하면서 발(Foot)을 바라보도록 제약됩니다.
        무릎 회전의 기반이 되는 방향을 결정하는 역할을 합니다.
        
        Args:
            inThigh: 대퇴골 본 객체
            inFoot: 발 본 객체
            
        Returns:
            bool: 헬퍼 생성 성공 여부
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inFoot):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = inThigh.name.islower()
        
        # 서비스 인스턴스 설정 또는 생성
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
        """
        무릎 회전의 기준이 되는 루트 헬퍼 객체들을 생성합니다.
        
        대퇴골과 종아리뼈에 각각 위치하며, 비틀림 계산을 위한 기준점 역할을 합니다.
        
        Args:
            inThigh: 대퇴골 본 객체
            inCalf: 종아리뼈 본 객체
            inFoot: 발 본 객체
            
        Returns:
            bool: 헬퍼 생성 성공 여부
        """
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
        """
        대퇴골과 종아리뼈의 회전을 제어하는 헬퍼 객체들을 생성합니다.
        
        이 헬퍼들은 실제 무릎 움직임에 따른 비틀림 효과를 구현하는 데 사용됩니다.
        
        Args:
            inThigh: 대퇴골 본 객체
            inCalf: 종아리뼈 본 객체
            inFoot: 발 본 객체
            
        Returns:
            bool: 헬퍼 생성 성공 여부
        """
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
        calfRotHelper.position = inFoot.transform.position
        calfRotHelper.parent = inCalf
        
        self.thighRotHelper = thighRotHelper
        self.calfRotHelper = calfRotHelper
    
    def assign_thigh_rot_constraint(self, inLiftScale=0.1):
        """
        대퇴골 회전 헬퍼에 스크립트 기반 회전 제약을 할당합니다.
        
        LookAt 헬퍼와 대퇴골 회전 루트 헬퍼 사이의 관계를 기반으로 비틀림 회전을 계산합니다.
        
        Args:
            inLiftScale: 회전 영향력 스케일 (0.0~1.0)
        """
        self.liftScale = inLiftScale
        localRotRefTm = self.lookAtHleper.transform * rt.inverse(self.thighRotRootHelper.transform)
        
        rotListConst = self.const.assign_rot_list(self.thighRotHelper)
        rotScriptConst = rt.Rotation_Script()
        rt.setPropertyController(rotListConst, "Available", rotScriptConst)
        rotListConst.setActive(rotListConst.count)
        
        rotScriptConst.addConstant("localRotRefTm", localRotRefTm)
        rotScriptConst.addNode("limb", self.lookAtHleper)
        rotScriptConst.addNode("limbParent", self.thighRotRootHelper)
        rotScriptConst.setExpression(self.thighRotScriptExpression)
        
        self.const.set_rot_controllers_weight_in_list(self.thighRotHelper, 1, self.liftScale * 100.0)
        
    def assign_calf_rot_constraint(self, inLiftScale=0.1):
        """
        종아리뼈 회전 헬퍼에 스크립트 기반 회전 제약을 할당합니다.
        
        LookAt 헬퍼와 대퇴골 회전 루트 헬퍼 사이의 관계를 기반으로 비틀림 회전을 계산합니다.
        
        Args:
            inLiftScale: 회전 영향력 스케일 (0.0~1.0)
        """
        self.liftScale = inLiftScale
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
        """
        무릎 중간 본을 생성합니다.
        
        이 본들은 무릎이 구부러질 때 앞(Pop)과 뒤(Back)로 움직이는 볼륨감 있는 본들입니다.
        무릎 관절의 시각적 품질을 향상시킵니다.
        
        Args:
            inThigh: 대퇴골 본 객체
            inCalf: 종아리뼈 본 객체
            inKneePopScale: 무릎 앞쪽 돌출 스케일 (1.0이 기본값)
            inKneeBackScale: 무릎 뒤쪽 돌출 스케일 (1.0이 기본값)
            
        Returns:
            bool: 중간 본 생성 성공 여부
        """
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
        
        result = self.volumeBone.create_bones(self.calf, self.thigh, inVolumeSize=5.0, inRotAxises=["Z", "Z"], inTransAxises=["PosY", "NegY"], inTransScales=transScales)
        
        calfName = self.name.get_name_part("RealName", inCalf.name)
        isLower = calfName[0].islower()
        replaceName = "Knee"
        if isLower:
            replaceName = replaceName.lower()
        
        for item in result["Bones"]:
            item.name.replace(calfName, replaceName)
        
        result["rootBone"].name.replace(calfName, replaceName)
        result["RotHelper"].name.replace(calfName, replaceName)
        
        # 결과 저장
        if result and "Bones" in result:
            self.middleBones.extend(result["Bones"])
        
        return result
    
    def create_twist_bones(self, inThigh, inCalf):
        """
        대퇴골과 종아리뼈에 연결된 비틀림 본들에 대한 리프팅 본과 헬퍼를 생성합니다.
        
        기존 비틀림 본들을 찾아 각각에 대응하는 리프팅 본과 헬퍼를 생성하여 
        무릎 구부림에 따라 자연스럽게 회전하도록 제약을 설정합니다.
        
        Args:
            inThigh: 대퇴골 본 객체
            inCalf: 종아리뼈 본 객체
            
        Returns:
            bool: 비틀림 본 생성 성공 여부
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = inThigh.name.islower()
        
        # 서비스 인스턴스 설정 또는 생성
        self.thigh = inThigh
        self.calf = inCalf
        
        oriThighTwistBones = []
        oriClafTwistBones = []
        thighChildren = inThigh.children
        calfChildren = inCalf.children
        
        if len(thighChildren) < 1 or len(calfChildren) < 1:
            return False
        
        for item in thighChildren:
            testName = item.name.lower()
            if testName.find("twist") != -1:
                oriThighTwistBones.append(item)
    
        for item in calfChildren:
            testName = item.name.lower()
            if testName.find("twist") != -1:
                oriClafTwistBones.append(item)
        
        for item in oriThighTwistBones:
            liftTwistBoneName = self.name.add_suffix_to_real_name(item.name, filteringChar + "Lift")
            liftTwistHelperName = self.name.add_suffix_to_real_name(item.name, filteringChar + "Lift")
            if isLowerName:
                liftTwistBoneName = liftTwistBoneName.lower()
                liftTwistHelperName = liftTwistHelperName.lower()
            
            liftTwistBone = self.bone.create_nub_bone(liftTwistBoneName, 2)
            liftTwistBone.name = self.name.remove_name_part("Nub", liftTwistBone.name)
            liftTwistBone.name = self.name.replace_name_part("Index", liftTwistBone.name, self.name.get_name("Index", oriThighTwistBones.name))
            
            rt.setProperty(liftTwistBone, "transform", item.transform)
            liftTwistBone.parent = item
            
            liftTwistHelper = self.helper.create_point(liftTwistHelperName)
            liftTwistHelper.name = self.name.replace_name_part("Type", liftTwistHelper.name, self.name.get_name_part_value_by_description("Type", "Position"))
            
            rt.setProperty(liftTwistHelper, "transform", item.transform)
            liftTwistHelper.parent = self.thighRotHelper
            
            liftTwistBonePosConst = self.const.assign_pos_const(liftTwistBone, liftTwistHelper)
            
            self.thighTwistBones.append(liftTwistBone)
            self.thighTwistHelpers.append(liftTwistHelper)
        
        for item in oriClafTwistBones:
            liftTwistBoneName = self.name.add_suffix_to_real_name(item.name, filteringChar + "Lift")
            liftTwistHelperName = self.name.add_suffix_to_real_name(item.name, filteringChar + "Lift")
            if isLowerName:
                liftTwistBoneName = liftTwistBoneName.lower()
                liftTwistHelperName = liftTwistHelperName.lower()
            
            liftTwistBone = self.bone.create_nub_bone(liftTwistBoneName, 2)
            liftTwistBone.name = self.name.remove_name_part("Nub", liftTwistBone.name)
            liftTwistBone.name = self.name.replace_name_part("Index", liftTwistBone.name, self.name.get_name("Index", oriClafTwistBones.name))
            
            rt.setProperty(liftTwistBone, "transform", item.transform)
            liftTwistBone.parent = item
            
            liftTwistHelper = self.helper.create_point(liftTwistHelperName)
            liftTwistHelper.name = self.name.replace_name_part("Type", liftTwistHelper.name, self.name.get_name_part_value_by_description("Type", "Position"))
            
            rt.setProperty(liftTwistHelper, "transform", item.transform)
            liftTwistHelper.parent = self.calfRotHelper
            
            liftTwistBonePosConst = self.const.assign_pos_const(liftTwistBone, liftTwistHelper)
            
            self.calfTwistBones.append(liftTwistBone)
            self.calfTwistHelpers.append(liftTwistHelper)
            
    def create_bone(self, inThigh, inCalf, inFoot, inLiftScale=0.05, inKneePopScale=1.0, inKneeBackScale=1.0):
        """
        자동 무릎 본 시스템의 모든 요소를 생성하는 주요 메서드입니다.
        
        이 메서드는 다음 단계들을 순차적으로 실행합니다:
        1. LookAt 헬퍼 생성
        2. 회전 루트 헬퍼 생성
        3. 회전 헬퍼 생성
        4. 대퇴골과 종아리뼈 회전 제약 설정
        5. 무릎 중간 본 생성
        6. 비틀림 본 생성 및 제약 설정
        
        Args:
            inThigh: 대퇴골 본 객체
            inCalf: 종아리뼈 본 객체
            inFoot: 발 본 객체
            inLiftScale: 회전 영향력 스케일 (0.0~1.0)
            inKneePopScale: 무릎 앞쪽 돌출 스케일 (1.0이 기본값)
            inKneeBackScale: 무릎 뒤쪽 돌출 스케일 (1.0이 기본값)
            
        Returns:
            bool: 자동 무릎 본 시스템 생성 성공 여부
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf) or not rt.isValidNode(inFoot):
            return False
        
        self.create_lookat_helper(inThigh, inFoot)
        self.create_rot_root_heleprs(inThigh, inCalf, inFoot)
        self.create_rot_helper(inThigh, inCalf, inFoot)
        self.assign_thigh_rot_constraint(inLiftScale=inLiftScale)
        self.assign_calf_rot_constraint(inLiftScale=inLiftScale)
        self.create_middle_bone(inThigh, inCalf, inKneePopScale=inKneePopScale, inKneeBackScale=inKneeBackScale)
        self.create_twist_bones(inThigh, inCalf)
        
        # 결과를 딕셔너리 형태로 준비
        result = {
            "Thigh": inThigh,
            "Calf": inCalf, 
            "Foot": inFoot,
            "LookAtHelper": self.lookAtHleper,
            "ThighRotHelper": self.thighRotHelper,
            "CalfRotHelper": self.calfRotHelper,
            "ThighRotRootHelper": self.thighRotRootHelper,
            "CalfRotRootHelper": self.calfRotRootHelper,
            "ThighTwistBones": self.thighTwistBones,
            "CalfTwistBones": self.calfTwistBones,
            "ThighTwistHelpers": self.thighTwistHelpers,
            "CalfTwistHelpers": self.calfTwistHelpers,
            "MiddleBones": self.middleBones,
            "LiftScale": inLiftScale,
            "KneePopScale": inKneePopScale,
            "KneeBackScale": inKneeBackScale
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return result
    
    def reset(self):
        """
        클래스의 주요 컴포넌트들을 초기화합니다.
        서비스가 아닌 클래스 자체의 작업 데이터를 초기화하는 함수입니다.
        
        Returns:
            self: 메소드 체이닝을 위한 자기 자신 반환
        """
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
        
        self.liftScale = 0.025
        
        return self







