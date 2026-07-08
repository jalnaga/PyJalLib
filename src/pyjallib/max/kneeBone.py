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

from .boneChain import BoneChain

class KneeBone:
    """다리 리깅을 위한 자동 무릎 본(AutoKnee) 시스템을 생성하는 클래스.

    LookAt·회전 헬퍼와 스크립트 제약으로 무릎 굽힘에 따른 리프트 회전, 볼륨 중간 본, 트위스트 리프트 본을 구성한다.
    """

    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, volumeBoneService=None):
        """KneeBone 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            volumeBoneService (VolumeBone | None): 볼륨 본 서비스. None이면 새로 생성한다.
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
        
        self.thighTwistBones = []
        self.calfTwistBones = []
        self.thighTwistHelpers = []
        self.calfTwistHelpers = []
        
        self.middleBones = []
        self.middleHelper = None
        
        self.liftScale = 0.05
        
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
        """무릎 시스템의 기반이 되는 LookAt 헬퍼를 생성한다.

        헬퍼는 대퇴골 위치에 생성되어 발을 바라보도록 제약되며,
        무릎 회전의 기반 방향을 결정하는 역할을 한다.

        Args:
            inThigh (rt.Node): 대퇴골 본
            inFoot (rt.Node): 발 본

        Returns:
            None | False: 유효하지 않은 노드가 있으면 False. 성공 시 반환값 없음.
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inFoot):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = self.name.get_name("RealName", inThigh.name)[0].islower()
        
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
        """무릎 회전의 기준이 되는 회전 루트 헬퍼를 생성한다.

        대퇴골 위치에 박스 형태 헬퍼를 만들어 비틀림 계산의 기준점으로 사용한다.

        Args:
            inThigh (rt.Node): 대퇴골 본
            inCalf (rt.Node): 종아리뼈 본
            inFoot (rt.Node): 발 본

        Returns:
            None | False: 유효하지 않은 노드가 있으면 False. 성공 시 반환값 없음.
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf) or not rt.isValidNode(inFoot):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = self.name.get_name("RealName", inThigh.name)[0].islower()
        
        # 서비스 인스턴스 설정 또는 생성
        self.thigh = inThigh
        self.calf = inCalf
        self.foot = inFoot
        
        thighRotRootHelperName = self.name.replace_name_part("Type", inThigh.name, self.name.get_name_part_value_by_description("Type", "Dummy"))
        thighRotRootHelperName = self.name.add_suffix_to_real_name(thighRotRootHelperName, filteringChar + "Lift")
        if isLowerName:
            thighRotRootHelperName = thighRotRootHelperName.lower()
        
        thighRotRootHelper = self.helper.create_point(thighRotRootHelperName, crossToggle=False, boxToggle=True)
        thighRotRootHelper.transform = inThigh.transform
        thighRotRootHelper.parent = inThigh
        
        self.thighRotRootHelper = thighRotRootHelper

    def create_rot_helper(self, inThigh, inCalf, inFoot):
        """대퇴골과 종아리뼈의 회전을 제어하는 헬퍼들을 생성한다.

        이 헬퍼들은 무릎 움직임에 따른 비틀림 효과를 구현하는 데 사용된다.

        Args:
            inThigh (rt.Node): 대퇴골 본
            inCalf (rt.Node): 종아리뼈 본
            inFoot (rt.Node): 발 본. 종아리 회전 헬퍼의 위치 기준이 된다.

        Returns:
            None | False: 대퇴골 또는 종아리뼈가 유효하지 않으면 False. 성공 시 반환값 없음.
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = self.name.get_name("RealName", inThigh.name)[0].islower()
        
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
        """대퇴골 회전 헬퍼에 스크립트 기반 회전 제약을 할당한다.

        LookAt 헬퍼와 대퇴골 회전 루트 헬퍼 사이의 관계를 기반으로 비틀림 회전을 계산한다.

        Args:
            inLiftScale (float): 회전 영향력 스케일 (0.0~1.0)
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
        """종아리뼈 회전 헬퍼에 스크립트 기반 회전 제약을 할당한다.

        LookAt 헬퍼와 대퇴골 회전 루트 헬퍼 사이의 관계를 기반으로 비틀림 회전을 계산한다.

        Args:
            inLiftScale (float): 회전 영향력 스케일 (0.0~1.0)
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
        
    def create_middle_bone(self, inThigh, inCalf, inKneeVolumeSize=5.0, inKneePopScale=0.1, inKneeBackScale=1.5):
        """무릎이 구부러질 때 앞(Pop)·뒤(Back)로 움직이는 볼륨 중간 본을 생성한다.

        VolumeBone 서비스로 볼륨 본을 만든 뒤 무릎 이름 규칙으로 이름을 바꾼다.

        Args:
            inThigh (rt.Node): 대퇴골 본
            inCalf (rt.Node): 종아리뼈 본
            inKneeVolumeSize (float): 무릎 볼륨 크기
            inKneePopScale (float): 무릎 앞쪽 돌출 스케일
            inKneeBackScale (float): 무릎 뒤쪽 돌출 스케일

        Returns:
            BoneChain | None: 생성된 무릎 볼륨 본 체인. 유효하지 않은 노드가 있으면 None
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf):
            return None
        
        filteringChar = self.name.get_filtering_char(inCalf.name)
        kneeName = self.name.replace_name_part("RealName", inCalf.name, "Knee")
        kneeRootName = self.name.replace_name_part("RealName", kneeName, "Knee" + filteringChar + "Root")
        kneeRootDumName = self.name.replace_name_part("Type", kneeRootName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        kneeFwdName = self.name.replace_name_part("FrontBack", kneeName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        kneeBckName = self.name.replace_name_part("FrontBack", kneeName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        
        if self.name.get_name("RealName", inCalf.name)[0].islower():
            kneeName = kneeName.lower()
            kneeRootName = kneeRootName.lower()
            kneeRootDumName = kneeRootDumName.lower()
            kneeFwdName = kneeFwdName.lower()
            kneeBckName = kneeBckName.lower()
        
        facingDirVec = inCalf.transform.position - inThigh.transform.position
        inObjXAxisVec = inCalf.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        self.thigh = inThigh
        self.calf = inCalf
        
        transScales = []
        transAxisNames = ["PosY", "NegY"]
        if distanceDir > 0:
            transScales.append(inKneePopScale)
            transScales.append(inKneeBackScale)
            transAxisNames = ["PosY", "NegY"]
        else:
            transScales.append(inKneeBackScale)
            transScales.append(inKneePopScale)
            transAxisNames = ["NegY", "PosY"]
        
        result = self.volumeBone.create_bones(self.calf, self.thigh, inVolumeSize=inKneeVolumeSize, inRotAxises=["Z", "Z"], inTransAxises=["PosY", "NegY"], inTransScales=transScales)
        
        for item in result.bones:
            if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = kneeRootName
            elif rt.matchPattern(item.name.lower(), pattern="*"+transAxisNames[0].lower()+"*"):
                item.name = kneeFwdName
            elif rt.matchPattern(item.name.lower(), pattern="*"+transAxisNames[1].lower()+"*"):
                item.name = kneeBckName
        
        for item in result.helpers:
            if rt.matchPattern(item.name.lower(), pattern="*root*"):
                item.name = kneeRootDumName
        
        # 결과 저장 - 기존 확장 방식에서 직접 할당으로 변경
        if result.bones:
            self.middleBones = result.bones
            self.middleHelper = result.helpers[0]
        
        return result
    
    def create_twist_bones(self, inThigh, inCalf):
        """대퇴골·종아리뼈의 기존 비틀림 본에 대응하는 리프트 본과 헬퍼를 생성한다.

        자식 중 이름에 "twist"가 포함된 본을 찾아 각각 리프트 본을 만들고,
        회전 헬퍼에 연결된 헬퍼로 위치 제약을 설정한다.

        Args:
            inThigh (rt.Node): 대퇴골 본
            inCalf (rt.Node): 종아리뼈 본

        Returns:
            None | False: 노드가 유효하지 않거나 자식 본이 없으면 False. 성공 시 반환값 없음.
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf):
            return False
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLowerName = self.name.get_name("RealName", inThigh.name)[0].islower()
        
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
            liftTwistBone.name = self.name.replace_name_part("Index", liftTwistBone.name, self.name.get_name("Index", item.name))
            
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
            liftTwistBone.name = self.name.replace_name_part("Index", liftTwistBone.name, self.name.get_name("Index", item.name))
            
            rt.setProperty(liftTwistBone, "transform", item.transform)
            liftTwistBone.parent = item
            
            liftTwistHelper = self.helper.create_point(liftTwistHelperName)
            liftTwistHelper.name = self.name.replace_name_part("Type", liftTwistHelper.name, self.name.get_name_part_value_by_description("Type", "Position"))
            
            rt.setProperty(liftTwistHelper, "transform", item.transform)
            liftTwistHelper.parent = self.calfRotHelper
            
            liftTwistBonePosConst = self.const.assign_pos_const(liftTwistBone, liftTwistHelper)
            
            self.calfTwistBones.append(liftTwistBone)
            self.calfTwistHelpers.append(liftTwistHelper)
            
    def create_bone(self, inThigh, inCalf, inFoot, inLiftScale=0.05, inKneeVolumeSize=5.0, inKneePopScale=0.1, inKneeBackScale=1.5):
        """자동 무릎 본 시스템의 모든 요소를 생성한다.

        LookAt 헬퍼, 회전 루트 헬퍼, 회전 헬퍼 생성과 회전 제약 할당,
        볼륨 중간 본과 비틀림 리프트 본 생성을 순차적으로 실행한다.

        Args:
            inThigh (rt.Node): 대퇴골 본
            inCalf (rt.Node): 종아리뼈 본
            inFoot (rt.Node): 발 본
            inLiftScale (float): 회전 영향력 스케일 (0.0~1.0)
            inKneeVolumeSize (float): 무릎 볼륨 크기
            inKneePopScale (float): 무릎 앞쪽 돌출 스케일
            inKneeBackScale (float): 무릎 뒤쪽 돌출 스케일

        Returns:
            BoneChain | None: 생성된 자동 무릎 본 체인. 유효하지 않은 노드가 있으면 None
        """
        if not rt.isValidNode(inThigh) or not rt.isValidNode(inCalf) or not rt.isValidNode(inFoot):
            return None
        
        self.create_lookat_helper(inThigh, inFoot)
        self.create_rot_root_heleprs(inThigh, inCalf, inFoot)
        self.create_rot_helper(inThigh, inCalf, inFoot)
        self.assign_thigh_rot_constraint(inLiftScale=inLiftScale)
        self.assign_calf_rot_constraint(inLiftScale=inLiftScale)
        self.create_middle_bone(inThigh, inCalf, inKneeVolumeSize=inKneeVolumeSize, inKneePopScale=inKneePopScale, inKneeBackScale=inKneeBackScale)
        self.create_twist_bones(inThigh, inCalf)
        
        # 모든 생성된 본들을 개별적으로 수집
        all_bones = []
        
        # 대퇴부 트위스트 본 추가
        for bone in self.thighTwistBones:
            all_bones.append(bone)
            
        # 종아리 트위스트 본 추가
        for bone in self.calfTwistBones:
            all_bones.append(bone)
            
        # 중간 본 추가
        for bone in self.middleBones:
            all_bones.append(bone)
        
        # 모든 헬퍼 수집
        all_helpers = [self.lookAtHleper, self.thighRotHelper, self.calfRotHelper, 
                      self.thighRotRootHelper, self.middleHelper]
                      
        # 트위스트 헬퍼 추가
        for helper in self.thighTwistHelpers:
            all_helpers.append(helper)
            
        for helper in self.calfTwistHelpers:
            all_helpers.append(helper)
        
        if self.bone.is_skin_bone(inThigh) or self.bone.is_skin_bone(inCalf) or self.bone.is_skin_bone(inFoot):
            for item in all_bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in all_helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 BoneChain 형태로 준비
        result = {
            "Bones": all_bones,
            "Helpers": all_helpers,
            "SourceBones": [inThigh, inCalf, inFoot],
            "Parameters": [inLiftScale, inKneeVolumeSize, inKneePopScale, inKneeBackScale]
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 자동 무릎 본을 재생성한다.

        기존 설정을 복원하거나 저장된 데이터에서 무릎 셋업을 재생성할 때 사용한다.

        Args:
            inBoneChain (BoneChain): 자동 무릎 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 BoneChain. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
            
        # 기존 객체 삭제
        inBoneChain.delete()
            
        # BoneChain에서 필요한 정보 추출
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        # 필수 소스 본 확인
        if len(sourceBones) < 3 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or not rt.isValidNode(sourceBones[2]):
            return None
            
        # 파라미터 가져오기 (또는 기본값 사용)
        liftScale = parameters[0] if len(parameters) > 0 else 0.05
        kneeVolumeSize = parameters[1] if len(parameters) > 1 else 5.0
        kneePopScale = parameters[2] if len(parameters) > 2 else 0.1
        kneeBackScale = parameters[3] if len(parameters) > 3 else 1.5
        
        # 무릎 본 생성
        inThigh = sourceBones[0]
        inCalf = sourceBones[1]
        inFoot = sourceBones[2]
        
        # 새로운 자동 무릎 본 생성
        return self.create_bone(inThigh, inCalf, inFoot, liftScale, kneeVolumeSize, kneePopScale, kneeBackScale)
    
    def reset(self):
        """클래스의 작업 데이터를 초기 상태로 되돌린다.

        서비스가 아닌 클래스 자체의 작업 데이터만 초기화한다.

        Returns:
            KneeBone: 메서드 체이닝을 위한 자기 자신
        """
        self.thigh = None
        self.calf = None
        self.foot = None
        
        self.lookAtHleper = None
        self.thighRotHelper = None
        self.calfRotHelper = None
        
        self.thighRotRootHelper = None
        
        self.thighTwistBones = []
        self.calfTwistBones = []
        self.thighTwistHelpers = []
        self.calfTwistHelpers = []
        
        self.middleBones = []
        
        self.liftScale = 0.05
        
        return self







