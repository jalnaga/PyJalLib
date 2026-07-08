#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hip 모듈 - 3ds Max용 Hip 관련 기능 제공
원본 MAXScript의 hip.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint

from .boneChain import BoneChain


class Hip:
    """골반과 허벅지 사이에 배치되는 Hip 보조 본을 생성하는 클래스.

    헬퍼와 스크립트 제약을 이용해 허벅지 회전에 따라 밀려나는 Hip 본 셋업을 구성한다.
    """

    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None):
        """Hip 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.const = constraintService if constraintService else Constraint(nameService=self.name, helperService=self.helper)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim, helperService=self.helper, constraintService=self.const)
        
        # 기본 속성 초기화
        self.pelvisWeight = 0.4
        self.thighWeight = 0.6
        self.pushAmount = 20
        
        self.pelvis = None
        self.thigh = None
        self.thighTwist = None
        self.calf = None
        
        self.pelvisHelper = None
        self.thighHelper = None
        self.thighTwistHelper = None
        self.thighRotHelper = None
        self.thighPosHelper = None
        self.thighRotRootHelper = None
        
        self.helpers = []
        self.bones = []
        
        self.posScriptExpression = (
            "localLimbTm = limb.transform * inverse limbParent.transform\n"
            "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "eulerRot = (quatToEuler q order:5)\n"
            "swizzledRot = (eulerAngles eulerRot.y eulerRot.z eulerRot.x)\n"
            "\n"
            "axis = [0,0,1]\n"
            "\n"
            "saturatedTwistZ = (swizzledRot.x*axis.x + swizzledRot.y*axis.y + swizzledRot.z*axis.z)/180.0\n"
            "pushScaleY = (amax 0.0 saturatedTwistZ)\n"
            "\n"
            "axis = [0,1,0]\n"
            "saturatedTwistY = (swizzledRot.x*axis.x + swizzledRot.y*axis.y + swizzledRot.z*axis.z)/180.0\n"
            "pushScaleZ = amax 0.0 saturatedTwistY\n"
            "\n"
            "\n"
            "[0, pushAmount * pushScaleY, -pushAmount * 0.1 * pushScaleZ]\n"
        )
        
    def reset(self):
        """클래스의 작업 데이터를 초기 상태로 되돌린다.

        서비스가 아닌 클래스 자체의 작업 데이터만 초기화한다.

        Returns:
            Hip: 메서드 체이닝을 위한 자기 자신
        """
        self.pelvisWeight = 0.4
        self.thighWeight = 0.6
        self.pushAmount = 20
        
        self.pelvis = None
        self.thigh = None
        self.thighTwist = None
        self.calf = None
        
        self.pelvisHelper = None
        self.thighHelper = None
        self.thighTwistHelper = None
        self.thighRotHelper = None
        self.thighPosHelper = None
        self.thighRotRootHelper = None
        
        self.helpers = []
        self.bones = []
        
        return self
    
    def create_helper(self, inPelvis, inThigh, inThighTwist):
        """Hip 셋업에 필요한 헬퍼 포인트들을 생성한다.

        골반·허벅지 트위스트·회전·위치·회전 루트 헬퍼를 생성해 멤버 변수와
        helpers 리스트에 저장한다.

        Args:
            inPelvis (rt.Node): 골반 본
            inThigh (rt.Node): 허벅지 본
            inThighTwist (rt.Node): 허벅지 트위스트 본

        Returns:
            None | False: 유효하지 않은 노드가 있으면 False. 성공 시 반환값 없음.
        """
        if not rt.isValidNode(inPelvis) or not rt.isValidNode(inThigh) or not rt.isValidNode(inThighTwist):
            return False
        
        self.pelvis = inPelvis
        self.thigh = inThigh
        self.thighTwist = inThighTwist
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLower = self.name.get_name("RealName", inThigh.name)[0].islower()
        
        pelvisHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_realName(inPelvis.name)+filteringChar+"Hip")
        pelvisHelperName = self.name.replace_name_part("Type", pelvisHelperName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        rt.setProperty(pelvisHelper, "transform", inThigh.transform)
        pelvisHelper.parent = inPelvis
        
        tihgTwistHeleprName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_realName(inThighTwist.name)+filteringChar+"Hip")
        tihgTwistHeleprName = self.name.replace_name_part("Type", tihgTwistHeleprName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        thighTwistHelper = self.helper.create_point(tihgTwistHeleprName)
        rt.setProperty(thighTwistHelper, "transform", inThighTwist.transform)
        thighTwistHelper.parent = inThighTwist
        
        tihghRotHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_realName(inThigh.name)+filteringChar+"Hip")
        tihghRotHelperName = self.name.replace_name_part("Type", tihghRotHelperName, self.name.get_name_part_value_by_description("Type", "Rotation"))
        thighRotHelper = self.helper.create_point(tihghRotHelperName)
        rt.setProperty(thighRotHelper, "transform", inThighTwist.transform)
        thighRotHelper.parent = inThigh
        
        thighPosHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_realName(inThigh.name)+filteringChar+"Hip")
        thighPosHelperName = self.name.replace_name_part("Type", thighPosHelperName, self.name.get_name_part_value_by_description("Type", "Position"))
        thighPosHelper = self.helper.create_point(thighPosHelperName)
        rt.setProperty(thighPosHelper, "transform", inThighTwist.transform)
        thighPosHelper.parent = thighRotHelper
        
        thighRotRootHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_realName(inThigh.name)+filteringChar+"Hip")
        thighRotRootHelperName = self.name.replace_name_part("Type", thighRotRootHelperName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        thighRotRootHelper = self.helper.create_point(thighRotRootHelperName)
        rt.setProperty(thighRotRootHelper, "transform", thighRotHelper.transform)
        thighRotRootHelper.parent = inThighTwist
        
        if isLower:
            pelvisHelper.name = pelvisHelper.name.lower()
            thighTwistHelper.name = thighTwistHelper.name.lower()
            thighRotHelper.name = thighRotHelper.name.lower()
            thighPosHelper.name = thighPosHelper.name.lower()
            thighRotRootHelper.name = thighRotRootHelper.name.lower()
            
        self.pelvisHelper = pelvisHelper
        self.thighTwistHelper = thighTwistHelper
        self.thighRotHelper = thighRotHelper
        self.thighPosHelper = thighPosHelper
        self.thighRotRootHelper = thighRotRootHelper
        
        self.helpers.append(pelvisHelper)
        self.helpers.append(thighTwistHelper)
        self.helpers.append(thighRotHelper)
        self.helpers.append(thighPosHelper)
        self.helpers.append(thighRotRootHelper)
    
    def assing_constraint(self, inCalf, inPelvisWeight=60.0, inThighWeight=40.0, inPushAmount=5.0):
        """Hip 헬퍼들에 회전 제약과 위치 스크립트 컨트롤러를 할당한다.

        회전 헬퍼에는 골반·허벅지 트위스트 헬퍼 가중치 회전 제약을,
        위치 헬퍼에는 허벅지 회전량에 따라 밀려나는 위치 스크립트를 적용한다.

        Args:
            inCalf (rt.Node): 종아리 본. 밀림 방향 판별에 사용된다.
            inPelvisWeight (float): 골반 회전 가중치
            inThighWeight (float): 허벅지 회전 가중치
            inPushAmount (float): 밀림 크기
        """
        self.calf = inCalf
        self.pelvisWeight = inPelvisWeight
        self.thighWeight = inThighWeight
        self.pushAmount = rt.Float(inPushAmount)
        
        facingDirVec = self.calf.transform.position - self.thigh.transform.position
        inObjXAxisVec = self.thigh.objectTransform.row1
        distanceDir = -1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else 1.0
        
        rotConst = self.const.assign_rot_const_multi(self.thighRotHelper, [self.pelvisHelper, self.thighTwistHelper])
        rotConst.setWeight(1, self.pelvisWeight)
        rotConst.setWeight(2, self.thighWeight)
        
        localRotRefTm = self.thighRotHelper.transform * rt.inverse(self.thighRotRootHelper.transform)
        posConst = self.const.assign_pos_script_controller(self.thighPosHelper)
        posConst.addNode("limb", self.thighRotHelper)
        posConst.addNode("limbParent", self.thighRotRootHelper)
        posConst.addConstant("localRotRefTm", localRotRefTm)
        posConst.addConstant("pushAmount", self.pushAmount*distanceDir)
        posConst.setExpression(self.posScriptExpression)
        posConst.update()
        
    def create_bone(self, inPelvis, inThigh, inThighTwist, inCalf, pushAmount=5.0, inPelvisWeight=60.0, inThighWeight=40.0):
        """헬퍼와 제약을 구성하고 Hip 본을 생성한다.

        Args:
            inPelvis (rt.Node): 골반 본
            inThigh (rt.Node): 허벅지 본
            inThighTwist (rt.Node): 허벅지 트위스트 본
            inCalf (rt.Node): 종아리 본
            pushAmount (float): 밀림 크기
            inPelvisWeight (float): 골반 회전 가중치
            inThighWeight (float): 허벅지 회전 가중치

        Returns:
            BoneChain | False: 생성된 Hip 본 체인. 유효하지 않은 노드가 있으면 False
        """
        if not rt.isValidNode(inPelvis) or not rt.isValidNode(inThigh) or not rt.isValidNode(inThighTwist):
            return False
        
        self.create_helper(inPelvis, inThigh, inThighTwist)
        self.assing_constraint(inCalf, inPelvisWeight, inThighWeight, inPushAmount=pushAmount)
        
        isLower = self.name.get_name("RealName", inThigh.name)[0].islower()
        hipBoneName = self.name.replace_name_part("RealName", inThigh.name, "Hip")
        hipBone = self.bone.create_nub_bone(hipBoneName, 2)
        hipBone.name = self.name.remove_name_part("Nub", hipBone.name)
        if isLower:
            hipBone.name = hipBone.name.lower()
        
        rt.setProperty(hipBone, "transform", inThighTwist.transform)
        hipBone.parent = inPelvis
        
        self.const.assign_rot_const(hipBone, self.thighRotHelper)
        self.const.assign_pos_const(hipBone, self.thighPosHelper)
        
        self.bones.append(hipBone)
        
        if self.bone.is_skin_bone(inPelvis) or self.bone.is_skin_bone(inThigh) or self.bone.is_skin_bone(inThighTwist) or self.bone.is_skin_bone(inCalf):
            for item in self.bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in self.helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 딕셔너리 형태로 준비
        result = {
            "Bones": self.bones,
            "Helpers": self.helpers,
            "SourceBones": [inPelvis, inThigh, inThighTwist, inCalf],
            "Parameters": [pushAmount, inPelvisWeight, inThighWeight]
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 Hip 본을 재생성한다.

        기존 설정을 복원하거나 저장된 데이터에서 Hip 셋업을 재생성할 때 사용한다.

        Args:
            inBoneChain (BoneChain): Hip 정보를 포함한 BoneChain 객체

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
        if len(sourceBones) < 4 or not all(rt.isValidNode(bone) for bone in sourceBones[:4]):
            return None
            
        # 파라미터 가져오기 (또는 기본값 사용)
        pushAmount = parameters[0] if len(parameters) > 0 else 5.0
        pelvisWeight = parameters[1] if len(parameters) > 1 else 0.6
        thighWeight = parameters[2] if len(parameters) > 2 else 0.4
        
        # Hip 생성
        inPelvis = sourceBones[0]
        inThigh = sourceBones[1]
        inThighTwist = sourceBones[2]
        inCalf = sourceBones[3]
        
        # 새로운 Hip 생성
        return self.create_bone(inPelvis, inThigh, inThighTwist, inCalf, pushAmount, pelvisWeight, thighWeight)

