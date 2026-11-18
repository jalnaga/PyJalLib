#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고간 부 본 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공
"""

from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain
from .rigPart import _RigPartBase

class GroinBone(_RigPartBase):
    """골반과 좌우 허벅지 트위스트 본을 기반으로 고간 부 본을 생성하는 클래스.

    헬퍼 3개와 가중치 회전 제약으로 고간 본이 골반·허벅지 회전을 따라가도록 구성한다.
    """

    PARAM_SPEC = (
        ("inPelvisWeight", 40.0),
        ("inThighWeight", 60.0),
    )

    SOURCE_SPEC = ("inPelvis", "inLThighTwist", "inRThighTwist")

    WORK_DEFAULTS = {
        "pelvis": None,
        "lThighTwist": None,
        "rThighTwist": None,
        "bones": [],
        "helpers": [],
        "pelvisWeight": 40.0,
        "thighWeight": 60.0,
    }

    def create_bones(
        self,
        inPelvis,
        inLThighTwist,
        inRThighTwist,
        inPelvisWeight: float = 40.0,
        inThighWeight: float = 60.0,
    ) -> Optional[BoneChain]:
        """골반과 좌우 허벅지 트위스트 본을 기반으로 고간 부 본을 생성한다.

        Args:
            inPelvis (rt.Node): 골반 본
            inLThighTwist (rt.Node): 왼쪽 허벅지 트위스트 본
            inRThighTwist (rt.Node): 오른쪽 허벅지 트위스트 본
            inPelvisWeight (float): 골반 회전 가중치
            inThighWeight (float): 허벅지 회전 가중치. 좌우에 절반씩 분배된다.

        Returns:
            BoneChain | None: 생성된 고간 부 본 체인. 유효하지 않은 노드가 있으면 None
        """
        # 전에는 여기서 `rt.messageBox`를 띄웠다. 라이브러리가 UI를 띄우면 헤드리스에서
        # 판정할 수 없고 사유도 사라진다 - 사유는 Logger로 가고 반환은 None으로 통일한다.
        if not self.validate_source_nodes(inPelvis, inLThighTwist, inRThighTwist):
            return None
        
        groinName = "Groin"
        if self.name.get_name("RealName", inPelvis.name)[0].islower():
            groinName = groinName.lower()
        
        groinBaseName = self.name.replace_name_part("RealName", inLThighTwist.name, groinName)
        
        pelvisHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelperName = self.name.replace_name_part("Index", pelvisHelperName, "0")
        pelvisHelperName = self.name.remove_name_part("Side", pelvisHelperName)
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        pelvisHelper.transform = inPelvis.transform
        self.anim.rotate_local(pelvisHelper, 0.0, 0.0, -180.0)
        pelvisHelper.parent = inPelvis
        self.helper.set_shape_to_box(pelvisHelper)
        
        lThighTwistHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        lThighTwistHelperName = self.name.replace_name_part("Side", lThighTwistHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        lThighTwistHelperName = self.name.replace_name_part("Index", lThighTwistHelperName, "0")
        lThighTwistHelper = self.helper.create_point(lThighTwistHelperName)
        lThighTwistHelper.transform = pelvisHelper.transform
        lThighTwistHelper.position = inLThighTwist.transform.position
        lThighTwistHelper.parent = inLThighTwist
        self.helper.set_shape_to_box(lThighTwistHelper)
        
        rThighTwistHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        rThighTwistHelperName = self.name.replace_name_part("Side", rThighTwistHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        rThighTwistHelperName = self.name.replace_name_part("Index", rThighTwistHelperName, "0")
        rThighTwistHelper = self.helper.create_point(rThighTwistHelperName)
        rThighTwistHelper.transform = pelvisHelper.transform
        rThighTwistHelper.position = inRThighTwist.transform.position
        rThighTwistHelper.parent = inRThighTwist
        self.helper.set_shape_to_box(rThighTwistHelper)
        
        groinBoneName = self.name.replace_name_part("Index", groinBaseName, "0")
        groinBoneName = self.name.remove_name_part("Side", groinBoneName)
        groinBone = self.bone.create_nub_bone(groinBoneName, 2)
        groinBone.name = groinBoneName
        groinBone.transform = pelvisHelper.transform
        groinBone.parent = inPelvis
        
        self.const.assign_rot_const_multi(groinBone, [pelvisHelper, lThighTwistHelper, rThighTwistHelper])
        rotConst = self.const.get_rot_list_controller(groinBone)[1]
        rotConst.setWeight(1, inPelvisWeight)
        rotConst.setWeight(2, inThighWeight/2.0)
        rotConst.setWeight(3, inThighWeight/2.0)
        
        if self.bone.is_skin_bone(inPelvis) or self.bone.is_skin_bone(inLThighTwist) or self.bone.is_skin_bone(inRThighTwist):
            for item in self.bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in self.helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 멤버 변수에 저장
        self.pelvis = inPelvis
        self.lThighTwist = inLThighTwist
        self.rThighTwist = inRThighTwist
        self.bones = [groinBone]
        self.helpers = [pelvisHelper, lThighTwistHelper, rThighTwistHelper]
        self.pelvisWeight = inPelvisWeight
        self.thighWeight = inThighWeight
        
        result = self.build_result(
            [groinBone],
            [pelvisHelper, lThighTwistHelper, rThighTwistHelper],
            [inPelvis, inLThighTwist, inRThighTwist],
            {"inPelvisWeight": inPelvisWeight, "inThighWeight": inThighWeight},
        )
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        rt.redrawViews()
        
        # BoneChain 객체 반환
        return BoneChain.from_result(result)
