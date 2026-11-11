#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
겨드랑이 본(Armpit) 모듈 - 3ds Max용 겨드랑이 본 기능 제공
어깨본에서 링크되어 몸통본을 바라보면서 어깨의 높이 변화에 따라 몸통 바깥면을 따라 움직이는 본을 만드는 모듈
"""

from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain
from .rigPart import _RigPartBase


class Armpit(_RigPartBase):
    """겨드랑이 본을 생성하는 클래스.

    어깨 본에 링크된 LookAt 헬퍼가 몸통을 바라보게 하여, 어깨 높이 변화에 따라 몸통 바깥면을 따라 움직이는 본 셋업을 구성한다.
    """

    PARAM_SPEC = (("inSpineLengthScale", 0.67),)

    SOURCE_SPEC = ("inShoulder", "inSpine", "inNeck")

    WORK_DEFAULTS = {
        "boneSize": 2.0,
        "shoulder": None,
        "neck": None,
        "spine": None,
        "genBones": [],
        "genHelpers": [],
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
        """겨드랑이 본 서비스를 초기화한다.

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


    def create_bones(
        self, inShoulder, inSpine, inNeck, inSpineLengthScale: float = 0.67
    ) -> Optional[BoneChain]:
        """겨드랑이 본과 보조 헬퍼들을 생성한다.

        어깨에 링크된 LookAt 헬퍼가 몸통쪽 타겟을 바라보게 하고,
        그 아래 위치 헬퍼를 따라가는 겨드랑이 본을 몸통의 자식으로 구성한다.

        Args:
            inShoulder (rt.Node): 어깨 본
            inSpine (rt.Node): 몸통 본
            inNeck (rt.Node): 목 본
            inSpineLengthScale (float): 몸통 길이 비율. 헬퍼 배치 거리 계산에 사용한다.

        Returns:
            BoneChain | None: 생성된 겨드랑이 본 체인. 입력 노드가 유효하지 않으면 None
        """
        if not self.validate_source_nodes(inShoulder, inSpine, inNeck):
            return None
        
        genBones = []
        genHelpers = []
        
        self.shoulder = inShoulder
        self.spine = inSpine
        self.neck = inNeck
        
        # 몸통 길이 계산
        spineLength = rt.distance(self.spine, self.neck) * inSpineLengthScale
        
        # 겨드랑이 본 이름 생성
        armpitName = self.name.replace_name_part("RealName", self.shoulder.name, "Armpit")
        if self.name.get_name("RealName", self.shoulder.name)[0].islower():
            armpitName = armpitName.lower()
        
        # 겨드랑이 룩엣 헬퍼 생성
        armpitLookAtName = self.name.replace_name_part("Type", armpitName, self.name.get_name_part_value_by_description("Type", "LookAt"))
        armpitLookAtHelper = self.helper.create_point(armpitLookAtName)
        self.helper.set_shape_to_axis(armpitLookAtHelper)
        armpitLookAtHelper.transform = self.shoulder.transform
        
        tempTarget = self.helper.create_point("Temp")
        tempTarget.transform = self.shoulder.transform
        rt.move(tempTarget, rt.Point3(0.0, 0.0, -spineLength))
        
        armpitLookAtConst = self.const.assign_lookat(armpitLookAtHelper, tempTarget)
        armpitLookAtConst.upnode_world = False
        armpitLookAtConst.pickUpNode = self.spine
        armpitLookAtConst.lookat_vector_length = 0.0
        
        self.const.collapse(armpitLookAtHelper)
        rt.delete(tempTarget)
        
        armpitLookAtTargetName = self.name.replace_name_part("Type", armpitName, self.name.get_name_part_value_by_description("Type", "Target"))
        armpitLookAtTarget = self.helper.create_point(armpitLookAtTargetName)
        self.helper.set_shape_to_cross(armpitLookAtTarget)
        armpitLookAtTarget.transform = armpitLookAtHelper.transform
        self.anim.move_local(armpitLookAtTarget, spineLength, 0.0, 0.0)
        rt.select([armpitLookAtTarget, self.spine])
        self.align.align_to_last_rot([armpitLookAtTarget, self.spine])
        
        armpitLookAtHelper.parent = self.shoulder
        armpitLookAtTarget.parent = self.spine
        
        armpitLookAtConst = self.const.assign_lookat(armpitLookAtHelper, armpitLookAtTarget)
        armpitLookAtConst.upnode_world = False
        armpitLookAtConst.pickUpNode = self.spine
        armpitLookAtConst.lookat_vector_length = 0.0
        
        armpitPosHelperName = self.name.replace_name_part("Type", armpitName, self.name.get_name_part_value_by_description("Type", "Position"))
        armpitPosHelper = self.helper.create_point(armpitPosHelperName)
        self.helper.set_shape_to_box(armpitPosHelper)
        armpitPosHelper.transform = armpitLookAtTarget.transform
        
        armpitPosHelper.parent = armpitLookAtHelper
        
        genHelpers.append(armpitLookAtHelper)
        genHelpers.append(armpitLookAtTarget)
        genHelpers.append(armpitPosHelper)
        
        # 겨드랑이 본 생성
        armpitBone = self.bone.create_nub_bone(armpitName, self.boneSize)
        armpitBone.name = armpitName
        armpitBone.transform = armpitPosHelper.transform
        armpitBone.parent = self.spine
        self.const.assign_pos_const(armpitBone, armpitPosHelper)
        
        genBones.append(armpitBone)
        
        self.genBones = genBones
        self.genHelpers = genHelpers
        
        result = self.build_result(
            genBones,
            genHelpers,
            [self.shoulder, self.spine, self.neck],
            {"inSpineLengthScale": inSpineLengthScale},
        )
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
