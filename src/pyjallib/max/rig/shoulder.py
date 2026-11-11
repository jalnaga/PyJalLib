#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
어깨 모듈
자동으로 어깨 본을 생성.
"""

from pymxs import runtime as rt

from .boneChain import BoneChain
from .rigPart import _RigPartBase


class Shoulder(_RigPartBase):
    """자동 어깨 본을 생성하는 클래스.

    쇄골-상완 사이에 LookAt 헬퍼와 상완 트위스트 가중치 기반 회전 제약으로 움직이는 어깨 본 셋업을 구성한다.
    """

    PARAM_SPEC = (("inTwistWeight", 0.7),)

    SOURCE_SPEC = ("inClavicle", "inUpperArm", "inAutoClavicle", "inUpperArmTwist")

    WORK_DEFAULTS = {
        "boneSize": 2.0,
        "genBones": [],
        "genHelpers": [],
        "clavicle": None,
        "upperArm": None,
        "autoClavicle": None,
        "upperArmTwist": None,
        "twistWeight": 0.7,
    }

    #: 어깨 LookAt 타겟의 위치 스크립트. 쇄골 길이만큼 팔 방향으로 밀어낸다.
    shoulderLookAtTargetPosConstExpression = """local clavicleDistance = distance clavicle upperArm
local xPos = clavicleDistance * distanceDir
[xPos, 0.0, 0.0]
"""

    def __init__(
        self,
        inNameService,
        inAnimService,
        inHelperService,
        inBoneService,
        inConstService,
        inBipService,
    ):
        """어깨 본 서비스를 초기화한다.

        Args:
            inNameService: 이름 처리 서비스
            inAnimService: 애니메이션 서비스
            inHelperService: 헬퍼 객체 서비스
            inBoneService: 뼈대 서비스
            inConstService: 제약 서비스
            inBipService: Biped 서비스
        """
        super().__init__(
            inNameService, inAnimService, inHelperService, inBoneService, inConstService
        )
        self.bip = inBipService

    def create_bones(self, inClavicle, inUpperArm, inAutoClavicle, inUpperArmTwist, inTwistWeight: float = 0.7):
        """어깨 본과 보조 헬퍼들을 생성한다.

        쇄골-상완 방향을 기준으로 LookAt 타겟·회전 헬퍼를 구성하고,
        LookAt 헬퍼와 상완 트위스트 본에 가중치를 나눠 어깨 본의 회전을 제어한다.

        Args:
            inClavicle (rt.Node): 쇄골 본
            inUpperArm (rt.Node): 상완 본
            inAutoClavicle (rt.Node): 자동 쇄골 본. 생성되는 어깨 본의 부모가 된다.
            inUpperArmTwist (rt.Node): 상완 트위스트 본
            inTwistWeight (float): 트위스트 회전 가중치 (0.0~1.0)

        Returns:
            BoneChain | None: 생성된 어깨 본 체인. 입력 노드가 유효하지 않으면 None
        """
        if not self.validate_source_nodes(inClavicle, inUpperArm, inAutoClavicle, inUpperArmTwist):
            return None
        
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        facingDirVec = inUpperArm.transform.position - inClavicle.transform.position
        inObjXAxisVec = inClavicle.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        clavicleLength *= distanceDir
        
        genBones = []
        genHelpers = []
        
        # 자동 쇄골 이름 생성 및 뼈대 생성
        shoulderName = self.name.replace_name_part("RealName", inClavicle.name, "Shoulder")
        if self.name.get_name("RealName", inClavicle.name)[0].islower():
            shoulderName = shoulderName.lower()
            
        shoulderBone = self.bone.create_nub_bone(shoulderName, self.boneSize)
        shoulderBone.name = self.name.remove_name_part("Nub", shoulderBone.name)
        shoulderBone.transform = inUpperArm.transform
        shoulderBone.parent = inAutoClavicle
        genBones.append(shoulderBone)
        
        # 어깨 타겟 포인트 생성
        shoulderLookAtTarget = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "Target")))
        shoulderLookAtTarget.transform = inUpperArm.transform
        shoulderLookAtTarget.parent = inUpperArm
        shoulderLookAtTargetPosConst = self.const.assign_pos_script_controller(shoulderLookAtTarget)
        shoulderLookAtTargetPosConst.addConstant("distanceDir", distanceDir)
        shoulderLookAtTargetPosConst.addNode("clavicle", inClavicle)
        shoulderLookAtTargetPosConst.addNode("upperArm", inUpperArm)
        shoulderLookAtTargetPosConst.setExpression(self.shoulderLookAtTargetPosConstExpression)
        genHelpers.append(shoulderLookAtTarget)
        
        # 어깨 회전 헬퍼 포인트 생성
        shoulderLookAtHelper = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "LookAt")))
        shoulderLookAtHelper.transform = inClavicle.transform
        shoulderLookAtHelper.parent = inClavicle
        self.const.assign_pos_const(shoulderLookAtHelper, inClavicle)
        
        lookAtConst = self.const.assign_lookat(shoulderLookAtHelper, shoulderLookAtTarget)
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inClavicle
        lookAtConst.lookat_vector_length = 0.0
        if distanceDir < 0:
            lookAtConst.target_axisFlip = True
        genHelpers.append(shoulderLookAtHelper)
        
        # 어깨 최종 회전 헬퍼 포인트 생성
        shoulderRotHelper = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "Rotation")))
        shoulderRotHelper.transform = inUpperArm.transform
        shoulderRotHelper.parent = inUpperArm
        self.const.assign_pos_const(shoulderRotHelper, inUpperArm)
        
        shoulderRotHelperRotConst = self.const.assign_rot_const_multi(shoulderRotHelper, [shoulderLookAtHelper, inUpperArmTwist])
        shoulderRotHelperRotConst.setWeight(1, 100.0-(inTwistWeight*100.0))
        shoulderRotHelperRotConst.setWeight(2, inTwistWeight*100.0)
        genHelpers.append(shoulderRotHelper)
        
        # 어깨 최종 회전 오프셋 헬퍼 포인트 생성
        shoulderRotOffsetHelepr = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "Dummy")))
        shoulderRotOffsetHelepr.transform = inUpperArm.transform
        shoulderRotOffsetHelepr.parent = shoulderRotHelper
        genHelpers.append(shoulderRotOffsetHelepr)
        
        # 어깨 본 회전 설정
        self.const.assign_rot_const(shoulderBone, shoulderRotOffsetHelepr)
        
        if self.bone.is_skin_bone(inClavicle) or self.bone.is_skin_bone(inUpperArm) or self.bone.is_skin_bone(inAutoClavicle) or self.bone.is_skin_bone(inUpperArmTwist):
            for item in genBones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in genHelpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        self.genBones = genBones
        self.genHelpers = genHelpers
        self.clavicle = inClavicle
        self.upperArm = inUpperArm
        self.autoClavicle = inAutoClavicle
        self.upperArmTwist = inUpperArmTwist
        self.twistWeight = inTwistWeight
        
        result = self.build_result(
            genBones,
            genHelpers,
            [inClavicle, inUpperArm, inAutoClavicle, inUpperArmTwist],
            {"inTwistWeight": inTwistWeight},
        )
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
