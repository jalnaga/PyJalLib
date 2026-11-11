#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
가슴 본(Chest) 모듈 - 3ds Max용 가슴 본 기능 제공
해부학적인 척추 위치에서 대흉근 쪽을 바라보는 헬퍼를 사용해서, 어깨 움직임에 따라 늘어나거나 수축하는 대흉근용 본을 만든다.
"""

from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain
from .rigPart import _RigPartBase


class Chest(_RigPartBase):
    """대흉근용 가슴 본을 생성하는 클래스.

    척추 위치의 LookAt 헬퍼가 대흉근 쪽을 바라보게 하여, 어깨 움직임에 따라 늘어나거나 수축하는 가슴 본 셋업을 구성한다.
    """

    PARAM_SPEC = (
        ("inSpineHeightScale", 0.33),
        ("inSpinePushScale", 0.5),
        ("inFrontWeight", 60.0),
        ("inShoulderWeight", 40.0),
        ("inChestMusclePushScale", 1.0),
        ("inChestMuscleHeightScale", 0.15),
        ("inShoulderPushScale", 0.25),
    )

    SOURCE_SPEC = ("inSpine", "inNeck", "inAutoClavicle", "inUpperArm")

    WORK_DEFAULTS = {
        "boneSize": 2.0,
        "genBones": [],
        "genHelpers": [],
        "pelvis": None,
        "spine": None,
        "neck": None,
        "autoClavicle": None,
        "upperArm": None,
    }

    def __init__(
        self,
        inNameService,
        inAnimService,
        inHelperService,
        inBoneService,
        inConstService,
        inAlignService,
    ):
        """가슴 본 서비스를 초기화한다.

        Args:
            inNameService: 이름 처리 서비스
            inAnimService: 애니메이션 서비스
            inHelperService: 헬퍼 객체 서비스
            inBoneService: 뼈대 서비스
            inConstService: 제약 서비스
            inAlignService: 정렬 서비스
        """
        super().__init__(
            inNameService, inAnimService, inHelperService, inBoneService, inConstService
        )
        self.align = inAlignService


    def create_bones(self, inSpine: rt.Object, inNeck: rt.Object, inAutoClavicle: rt.Object, inUpperArm: rt.Object,
                     inSpineHeightScale: float = 0.33, inSpinePushScale: float = 0.5,
                     inFrontWeight: float = 60.0, inShoulderWeight: float = 40.0,
                     inChestMusclePushScale: float = 1.0, inChestMuscleHeightScale: float = 0.15,
                     inShoulderPushScale: float = 0.25) -> Optional[BoneChain]:
        """가슴(대흉근) 본과 보조 헬퍼들을 생성한다.

        척추 뒤쪽의 LookAt 헬퍼가 앞쪽 타겟과 어깨 타겟을 가중치로 바라보게 하고,
        그 아래 대흉근 헬퍼를 향하는 몸통쪽(In)·어깨쪽(Out) 본 2개를 구성한다.

        Args:
            inSpine (rt.Node): 몸통 본
            inNeck (rt.Node): 목 본
            inAutoClavicle (rt.Node): 자동 쇄골 본
            inUpperArm (rt.Node): 상완 본
            inSpineHeightScale (float): 척추 높이 비율
            inSpinePushScale (float): 척추 앞뒤 밀림 비율
            inFrontWeight (float): 가슴쪽 LookAt 웨이트
            inShoulderWeight (float): 어깨쪽 LookAt 웨이트
            inChestMusclePushScale (float): 대흉근 X축 밀림 비율
            inChestMuscleHeightScale (float): 대흉근 높이 비율
            inShoulderPushScale (float): 어깨 밀림 비율

        Returns:
            BoneChain | None: 생성된 가슴 본 체인. 입력 노드가 유효하지 않으면 None
        """
        
        if not self.validate_source_nodes(inSpine, inNeck, inAutoClavicle, inUpperArm):
            return None
        
        self.spine = inSpine
        self.neck = inNeck
        self.autoClavicle = inAutoClavicle
        self.upperArm = inUpperArm
        
        genBones = []
        genHelpers = []
        
        chestName = self.name.replace_name_part("RealName", self.upperArm.name, "Chest")
        if self.name.get_name("RealName", self.upperArm.name)[0].islower():
            chestName = chestName.lower()
        
        # 몸통 길이 계산
        spineLength = rt.distance(self.spine, self.neck)
        
        # 몸통의 정면이 로컬 +Y 방향인지 -Y 방향인지 결정
        spineZAxisVec = self.spine.objectTransform.row3
        spineFacingDir = rt.normalize(self.neck.transform.position - self.spine.transform.position)
        spineFwdVec = rt.cross(spineZAxisVec, spineFacingDir)
        fwdDir = 1.0 if rt.dot(spineFwdVec, rt.normalize(self.spine.objectTransform.row2)) < 0.0 else -1.0
        
        # 뒤쪽 척추 룩엣 헬퍼 생성
        chestBackLookAtHelperName = self.name.replace_name_part("Type", chestName, self.name.get_name_part_value_by_description("Type", "LookAt"))
        chestBackLookAtHelper = self.helper.create_point(chestBackLookAtHelperName)
        self.helper.set_shape_to_axis(chestBackLookAtHelper)
        chestBackLookAtHelper.transform = self.spine.transform
        self.anim.move_local(chestBackLookAtHelper, spineLength*inSpineHeightScale, -fwdDir*spineLength*inSpinePushScale, 0.0)
        chestBackLookAtHelper.parent = self.spine
        
        # 앞쪽 갈비펴 타겟 헬퍼 생성
        chestFrontTargetHelperName = self.name.replace_name_part("Type", chestName, self.name.get_name_part_value_by_description("Type", "Target"))
        chestFrontTargetHelperName = self.name.replace_name_part("FrontBack", chestFrontTargetHelperName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        chestFrontTargetHelper = self.helper.create_point(chestFrontTargetHelperName)
        self.helper.set_shape_to_cross(chestFrontTargetHelper)
        chestFrontTargetHelper.transform  = self.spine.transform
        self.anim.move_local(chestFrontTargetHelper, spineLength*inSpineHeightScale, fwdDir*spineLength*inSpinePushScale, 0.0)
        chestFrontTargetHelper.parent = self.spine
        
        # 어깨 타겟 헬퍼 생성
        chestShoulderTargetHelperName = self.name.add_suffix_to_real_name(chestName, "Shoulder")
        if self.name.get_name("RealName", self.upperArm.name)[0].islower():
            chestShoulderTargetHelperName = chestShoulderTargetHelperName.lower()
        chestShoulderTargetHelperName = self.name.replace_name_part("Type", chestShoulderTargetHelperName, self.name.get_name_part_value_by_description("Type", "Target"))
        chestShoulderTargetHelper = self.helper.create_point(chestShoulderTargetHelperName)
        self.helper.set_shape_to_cross(chestShoulderTargetHelper)
        chestShoulderTargetHelper.transform = self.upperArm.transform
        chestShoulderTargetHelper.parent = self.autoClavicle
        
        # 뒤쪽 척추 룩엣 헬퍼에 룩엣 컨스트레인 설정
        chestBackLookAtConst = self.const.assign_lookat_multi(chestBackLookAtHelper, [chestFrontTargetHelper, chestShoulderTargetHelper])
        chestBackLookAtConst.upnode_world = False
        chestBackLookAtConst.pickUpNode = self.spine
        chestBackLookAtConst.lookat_vector_length = 0.0
        chestBackLookAtConst.SetWeight(1, inFrontWeight)
        chestBackLookAtConst.SetWeight(2, inShoulderWeight)
        
        # 갈비뼈 위를 흐르는 대흉근 헬퍼 생성
        chestFrontMuscleHelperName = self.name.replace_name_part("Type", chestName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        chestFrontMuscleHelper = self.helper.create_point(chestFrontMuscleHelperName)
        self.helper.set_shape_to_box(chestFrontMuscleHelper)
        chestFrontMuscleHelper.transform = chestBackLookAtHelper.transform
        self.anim.move_local(chestFrontMuscleHelper, spineLength*inChestMusclePushScale, -spineLength*inChestMuscleHeightScale, 0.0)
        chestFrontMuscleHelper.parent = chestBackLookAtHelper
        
        # 몸통쪽 대흉근 본 생성
        chestInBoneName = self.name.replace_name_part("InOut", chestName, self.name.get_name_part_value_by_description("InOut", "In"))
        chestInBone = self.bone.create_nub_bone(chestInBoneName, self.boneSize)
        chestInBone.transform = chestFrontTargetHelper.transform
        chestInBone.parent = self.spine
        chestInBoneLookAtConst = self.const.assign_lookat(chestInBone, chestFrontMuscleHelper)
        chestInBoneLookAtConst.upnode_world = False
        chestInBoneLookAtConst.pickUpNode = self.spine
        chestInBoneLookAtConst.lookat_vector_length = 0.0
        chestInBoneLookAtConst.StoUP_axis = 1
        chestInBoneLookAtConst.upnode_axis = 1
        
        # 어깨쪽 대흉근 본 생성
        chestOutBoneName = self.name.replace_name_part("InOut", chestName, self.name.get_name_part_value_by_description("InOut", "Out"))
        chestOutBone = self.bone.create_nub_bone(chestOutBoneName, self.boneSize)
        chestOutBone.transform = self.upperArm.transform
        
        upperArmZAxisVec = self.upperArm.objectTransform.row3
        upperArmFacingDir = rt.normalize(self.upperArm.transform.position - self.autoClavicle.transform.position)
        upperArmFwdVec = rt.cross(upperArmZAxisVec, upperArmFacingDir)
        fwdDir = 1.0 if rt.dot(upperArmFwdVec, rt.normalize(self.upperArm.objectTransform.row2)) < 0.0 else -1.0
        self.anim.move_local(chestOutBone, 0.0, fwdDir*spineLength*inShoulderPushScale, 0.0)
        
        chestOutBone.parent = self.autoClavicle
        chestOutBoneLookAtConst = self.const.assign_lookat(chestOutBone, chestFrontMuscleHelper)
        chestOutBoneLookAtConst.upnode_world = False
        chestOutBoneLookAtConst.pickUpNode = self.autoClavicle
        chestOutBoneLookAtConst.lookat_vector_length = 0.0
        chestOutBoneLookAtConst.StoUP_axis = 1
        chestOutBoneLookAtConst.upnode_axis = 1
        
        genBones.append(chestInBone)
        genBones.append(chestOutBone)
        genHelpers.append(chestBackLookAtHelper)
        genHelpers.append(chestFrontTargetHelper)
        genHelpers.append(chestShoulderTargetHelper)
        genHelpers.append(chestFrontMuscleHelper)
        
        self.genBones = genBones
        self.genHelpers = genHelpers
        
        result = self.build_result(
            genBones,
            genHelpers,
            [self.spine, self.neck, self.autoClavicle, self.upperArm],
            {
                "inSpineHeightScale": inSpineHeightScale,
                "inSpinePushScale": inSpinePushScale,
                "inFrontWeight": inFrontWeight,
                "inShoulderWeight": inShoulderWeight,
                "inChestMusclePushScale": inChestMusclePushScale,
                "inChestMuscleHeightScale": inChestMuscleHeightScale,
                "inShoulderPushScale": inShoulderPushScale,
            },
        )

        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
