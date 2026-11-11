#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
자동 쇄골(AutoClavicle) 모듈 - 3ds Max용 자동화된 쇄골 기능 제공
원본 MAXScript의 autoclavicle.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

from .boneChain import BoneChain
from .rigPart import _RigPartBase


class AutoClavicle(_RigPartBase):
    """자동 쇄골 본을 생성하는 클래스.

    상완의 움직임에 따라 LookAt 헬퍼로 자동 회전하는 쇄골 본 셋업을 구성한다.
    """

    PARAM_SPEC = (("inLiftScale", 0.8),)

    SOURCE_SPEC = ("inClavicle", "inUpperArm")

    WORK_DEFAULTS = {
        "boneSize": 2.0,
        "genBones": [],
        "genHelpers": [],
        "clavicle": None,
        "upperArm": None,
        "liftScale": 0.8,
    }

    #: 상완 회전 타겟의 위치 스크립트. 쇄골 길이 절반만큼 들어올림 비율로 민다.
    rotTargetUpperArmPosConstExpression = """local clavicleDistance = distance clavicle upperArm
local xPos = (clavicleDistance/2.0) * distanceDir * liftScale
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
        """자동 쇄골 본 서비스를 초기화한다.

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

    def create_bones(self, inClavicle, inUpperArm, inLiftScale: float = 0.8):
        """자동 쇄골 본과 보조 헬퍼들을 생성한다.

        쇄골·상완에 타겟 헬퍼를 배치하고 LookAt 제약으로 회전하는
        자동 쇄골 본을 쇄골의 자식으로 구성한다.

        Args:
            inClavicle: 쇄골 본
            inUpperArm: 상완 본
            inLiftScale: 상완 타겟의 들어올림 스케일

        Returns:
            BoneChain | None: 생성된 자동 쇄골 본 체인. 입력 노드가 유효하지 않으면 None
        """
        if not self.validate_source_nodes(inClavicle, inUpperArm):
            return None
        
        # 리스트 초기화
        genBones = []
        genHelpers = []
        
        # 쇄골과 상완 사이의 거리 계산
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        facingDirVec = inUpperArm.transform.position - inClavicle.transform.position
        inObjXAxisVec = inClavicle.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        clavicleLength *= distanceDir
        
        # 자동 쇄골 이름 생성 및 뼈대 생성
        autoClavicleName = self.name.replace_name_part("RealName", inClavicle.name, "Auto" + self.name._get_filtering_char(inClavicle.name) + "Clavicle")
        if self.name.get_name("RealName", inClavicle.name)[0].islower():
            autoClavicleName = autoClavicleName.lower()
        
        autoClavicleBone = self.bone.create_nub_bone(autoClavicleName, 2)
        autoClavicleBone.name = self.name.remove_name_part("Nub", autoClavicleBone.name)
        autoClavicleBone.transform = inClavicle.transform
        autoClavicleBone.parent = inClavicle
        self.const.assign_pos_const_multi(autoClavicleBone, [inClavicle, inUpperArm])
        genBones.append(autoClavicleBone)
        
        # 타겟 헬퍼 포인트 생성 (쇄골과 상완용)
        rotTargetClavicle = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target")))
        rotTargetClavicle.name = self.name.replace_name_part("Index", rotTargetClavicle.name, "0")
        rotTargetClavicle.transform = inClavicle.transform
        rotTargetClavicle.parent = inClavicle
        self.const.assign_pos_const(rotTargetClavicle, inUpperArm)
        genHelpers.append(rotTargetClavicle)
        
        rotTargetUpperArm = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target")))
        rotTargetUpperArm.name = self.name.add_suffix_to_real_name(rotTargetUpperArm.name, self.name._get_filtering_char(inClavicle.name) + "arm")
        rotTargetUpperArm.transform = inUpperArm.transform
        rotTargetUpperArm.parent = inUpperArm
        rotTargetUpperArmPosConst = self.const.assign_pos_script_controller(rotTargetUpperArm)
        rotTargetUpperArmPosConst.addConstant("distanceDir", distanceDir)
        rotTargetUpperArmPosConst.addConstant("liftScale", inLiftScale)
        rotTargetUpperArmPosConst.addNode("clavicle", inClavicle)
        rotTargetUpperArmPosConst.addNode("upperArm", inUpperArm)
        rotTargetUpperArmPosConst.setExpression(self.rotTargetUpperArmPosConstExpression)
        genHelpers.append(rotTargetUpperArm)
        
        # 회전 헬퍼 포인트 생성
        autoClavicleRotHelper = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Rotation")))
        autoClavicleRotHelper.transform = autoClavicleBone.transform
        autoClavicleRotHelper.parent = inClavicle
        self.const.assign_pos_const_multi(autoClavicleRotHelper, [inClavicle, inUpperArm])
        
        lookAtConst = self.const.assign_lookat_multi(autoClavicleRotHelper, [rotTargetClavicle, rotTargetUpperArm])
        
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inClavicle
        lookAtConst.lookat_vector_length = 0.0
        if distanceDir < 0:
            lookAtConst.target_axisFlip = True
        
        genHelpers.append(autoClavicleRotHelper)
        
        # ik 헬퍼 포인트 생성
        ikGoal = self.helper.create_point(autoClavicleName, boxToggle=False, crossToggle=True)
        ikGoal.transform = inClavicle.transform
        self.anim.move_local(ikGoal, clavicleLength, 0.0, 0.0)
        ikGoal.name = self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target"))
        ikGoal.name = self.name.replace_name_part("Index", ikGoal.name, "1")
        
        ikGoal.parent = autoClavicleRotHelper
        
        autClavicleLookAtConst = self.const.assign_lookat(autoClavicleBone, ikGoal)
        if clavicleLength < 0:
            autClavicleLookAtConst.target_axisFlip = True
        autClavicleLookAtConst.upnode_world = False
        autClavicleLookAtConst.pickUpNode = inClavicle
        autClavicleLookAtConst.lookat_vector_length = 0.0
        genHelpers.append(ikGoal)
        
        if self.bone.is_skin_bone(inClavicle) or self.bone.is_skin_bone(inUpperArm):
            for item in genBones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in genHelpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 멤버 변수에 저장
        self.genBones = genBones
        self.genHelpers = genHelpers
        self.clavicle = inClavicle
        self.upperArm = inUpperArm
        self.liftScale = inLiftScale
        
        result = self.build_result(
            genBones, genHelpers, [inClavicle, inUpperArm], {"inLiftScale": inLiftScale}
        )
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
