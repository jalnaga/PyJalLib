#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""관절 부피 유지 본(Volume preserve Bone).

관절이 회전할 때 줄어드는 부피를 보정하는 보조 본을 만든다. 루트 본이 관절 회전을
가중치만큼 따라가고, 볼륨 본은 굽힘 각도에 비례해 지정 축으로 밀려난다.

`Elbow`·`Wrist`·`Ankle`·`Inguinal`이 이 클래스를 상속해 파트별 이름 규칙과 축 계획을
얹는다(`limbVolume.py`).
"""

from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain, _get_logger
from .rigPart import _RigPartBase

#: 이동 축 이름 -> 로컬 방향 벡터 성분. 전 구현의 `if/elif` 6단을 대체한다.
_TRANS_AXIS_VECTORS = {
    "PosX": (1.0, 0.0, 0.0),
    "NegX": (-1.0, 0.0, 0.0),
    "PosY": (0.0, 1.0, 0.0),
    "NegY": (0.0, -1.0, 0.0),
    "PosZ": (0.0, 0.0, 1.0),
    "NegZ": (0.0, 0.0, -1.0),
}

#: 회전 감지 축 이름 -> 축 벡터 성분.
_ROT_AXIS_VECTORS = {
    "X": (1.0, 0.0, 0.0),
    "Y": (0.0, 1.0, 0.0),
    "Z": (0.0, 0.0, 1.0),
}

def invalid_axes(inRotAxises: list, inTransAxises: list) -> list:
    """두 축 표에 없는 축 값을 찾아 돌려준다.

    전에는 미등록 축이 `.get(..., (0, 0, 0))`으로 **영벡터**가 되어, 생성은 성공하는데
    볼륨 본이 루트에 붙어 움직이지 않았다. 툴이 `"PosY"` 대신 `"Y"`를 넘기던 결함이
    이 폴백 뒤에서 조용히 출하됐다(2026-10-08 Inguinal). 허용 값은 두 표의 키 그 자체다 -
    별도 목록을 두면 표와 갈라진다.

    Args:
        inRotAxises: 회전 감지 축 리스트
        inTransAxises: 이동 축 리스트

    Returns:
        list: `"rot=<값>"`/`"trans=<값>"` 형식의 잘못된 값 목록. 모두 유효하면 빈 리스트
    """
    invalid = [f"rot={axis!r}" for axis in inRotAxises if axis not in _ROT_AXIS_VECTORS]
    invalid += [f"trans={axis!r}" for axis in inTransAxises if axis not in _TRANS_AXIS_VECTORS]
    return invalid


def _warn_invalid_axes(inOwner: str, inInvalid: list) -> None:
    """미등록 축 거절 사유를 경고로 남긴다.

    Args:
        inOwner: 호출한 클래스 이름
        inInvalid: `invalid_axes()`의 결과
    """
    _get_logger().warning(
        f"{inOwner}: 미등록 축이라 볼륨 본을 만들지 않는다 {inInvalid} "
        f"(회전 축 {sorted(_ROT_AXIS_VECTORS)}, 이동 축 {sorted(_TRANS_AXIS_VECTORS)})"
    )


#: 볼륨 본의 위치 스크립트 컨트롤러 표현식.
#: 관절의 로컬 회전을 기준 자세와 비교해 twist 성분만 뽑고, 그 비율만큼 축 방향으로 민다.
POS_SCRIPT_EXPRESSION = (
    "localLimbTm = limb.transform * inverse limbParent.transform\n"
    "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
    "\n"
    "q = localDeltaTm.rotation\n"
    "\n"
    "eulerRot = (quatToEuler q order:5)\n"
    "swizzledRot = (eulerAngles eulerRot.y eulerRot.z eulerRot.x)\n"
    "saturatedTwist = abs ((swizzledRot.x*axis.x + swizzledRot.y*axis.y + swizzledRot.z*axis.z)/180.0)\n"
    "\n"
    "trAxis * saturatedTwist * volumeSize * transScale\n"
)


class VolumeBone(_RigPartBase):
    """관절 회전 시 부피 감소를 보정하는 볼륨 본 시스템을 생성·관리하는 클래스."""

    PARAM_SPEC = (
        ("inRotScale", 0.5),
        ("inVolumeSize", 5.0),
        ("inRotAxises", ["Z"]),
        ("inTransAxises", ["PosY"]),
        ("inTransScales", [1.0]),
    )

    SOURCE_SPEC = ("inObj", "inParent")

    WORK_DEFAULTS = {
        "rootBone": None,
        "rotHelper": None,
        "limb": None,
        "limbParent": None,
        "bones": [],
        "rotAxises": [],
        "transAxises": [],
        "transScales": [],
        "volumeSize": 5.0,
        "rotScale": 0.5,
    }

    #: 전 구현이 인스턴스 속성으로 들고 있던 표현식. 상수이므로 클래스에 둔다.
    posScriptExpression = POS_SCRIPT_EXPRESSION

    # ------------------------------------------------------------------
    # 구성 요소
    # ------------------------------------------------------------------

    def create_root_bone(self, inObj, inParent, inRotScale: float = 0.5):
        """볼륨 본들의 부모가 되는 루트 본과 회전 헬퍼를 생성한다.

        루트 본의 회전은 대상 관절과 회전 헬퍼에 가중치 회전 제약으로 연결된다.
        이미 유효한 루트 본과 회전 헬퍼가 있으면 기존 루트 본을 그대로 반환한다.

        Args:
            inObj: 볼륨 본을 붙일 대상 관절
            inParent: 대상 관절의 부모
            inRotScale: 대상 관절 회전을 따라가는 비율 (0.0~1.0)

        Returns:
            생성된(또는 기존) 루트 본. 유효하지 않은 노드가 있으면 None
        """
        if not self.validate_source_nodes(inObj, inParent):
            return None

        if rt.isValidNode(self.rootBone) and rt.isValidNode(self.rotHelper):
            return self.rootBone

        filteringChar = self.filtering_char(inObj.name)
        rootBoneName = self.name.add_suffix_to_real_name(
            inObj.name, filteringChar + "Vol" + filteringChar + "Root"
        )

        rootBone = self.bone.create_nub_bone(rootBoneName, 2)
        rootBone.name = self.name.remove_name_part("Nub", rootBone.name)
        if self.is_lower_case_name(rootBone.name):
            rootBone.name = rootBone.name.lower()
            rootBoneName = rootBoneName.lower()

        rt.setProperty(rootBone, "transform", inObj.transform)
        rootBone.parent = inObj

        rotHelper = self.helper.create_point(rootBoneName)
        rotHelper.name = self.dummy_name(rotHelper.name)
        rt.setProperty(rotHelper, "transform", inObj.transform)
        rotHelper.parent = inParent
        self.const.assign_pos_const(rotHelper, inObj)

        oriConst = self.const.assign_rot_const_multi(rootBone, [inObj, rotHelper])
        oriConst.setWeight(1, inRotScale * 100.0)
        oriConst.setWeight(2, (1.0 - inRotScale) * 100.0)

        self.rootBone = rootBone
        self.rotHelper = rotHelper
        self.limb = inObj
        self.limbParent = inParent

        return self.rootBone

    def volume_bone_name(self, inObjName: str, inRotAxis: str, inTransAxis: str) -> str:
        """볼륨 본 하나의 이름을 만든다(Nub 부분 제거 전).

        Args:
            inObjName: 대상 관절 이름
            inRotAxis: 회전 감지 축
            inTransAxis: 이동 축

        Returns:
            str: 볼륨 본 이름
        """
        filteringChar = self.filtering_char(inObjName)
        return self.name.add_suffix_to_real_name(
            inObjName,
            filteringChar + "Vol" + filteringChar + inRotAxis + filteringChar + inTransAxis,
        )

    def create_bone(
        self,
        inObj,
        inParent,
        inRotScale: float = 0.5,
        inVolumeSize: float = 5.0,
        inRotAxis: str = "Z",
        inTransAxis: str = "PosY",
        inTransScale: float = 1.0,
        inUseRootBone: bool = True,
        inRootBone=None,
    ) -> bool:
        """단일 볼륨 본을 생성하고 위치 스크립트 컨트롤러를 할당한다.

        Args:
            inObj: 볼륨 본을 붙일 대상 관절
            inParent: 대상 관절의 부모
            inRotScale: 루트 본 생성 시 사용하는 회전 반영 비율
            inVolumeSize: 볼륨 크기(이동 거리)
            inRotAxis: 굽힘을 측정할 회전 축 ("X", "Y", "Z")
            inTransAxis: 본이 밀려나는 이동 축 ("PosX"~"NegZ")
            inTransScale: 이동 스케일
            inUseRootBone: True면 기존 루트 본(또는 `inRootBone`)을 쓴다.
            inRootBone: 사용할 루트 본. None이면 새로 생성한다.

        Returns:
            bool: 성공하면 True. 노드가 유효하지 않거나, 쓸 루트 본이 없거나,
                축이 미등록 값이면 False
        """
        if not self.validate_source_nodes(inObj, inParent):
            return False

        invalid = invalid_axes([inRotAxis], [inTransAxis])
        if invalid:
            _warn_invalid_axes(type(self).__name__, invalid)
            return False

        if inUseRootBone:
            if not rt.isValidNode(self.rootBone) and not rt.isValidNode(self.rotHelper):
                return False
            self.rootBone = inRootBone if inRootBone else self.create_root_bone(inObj, inParent, inRotScale)
        else:
            self.create_root_bone(inObj, inParent, inRotScale)

        self.limb = inObj
        self.limbParent = inParent

        volBoneName = self.volume_bone_name(inObj.name, inRotAxis, inTransAxis)
        volBoneIndex = self.name.get_name("Index", volBoneName)

        volBone = self.bone.create_nub_bone(volBoneName, 2)
        volBone.name = self.name.remove_name_part("Nub", volBone.name)
        volBone.name = self.name.replace_name_part("Index", volBone.name, volBoneIndex)

        if self.is_lower_case_name(volBone.name):
            volBone.name = volBone.name.lower()
        rt.setProperty(volBone, "transform", self.rootBone.transform)

        transDirection = _TRANS_AXIS_VECTORS.get(inTransAxis, (0.0, 0.0, 0.0))
        volBoneTrDir = rt.Point3(*transDirection)
        self.anim.move_local(
            volBone,
            transDirection[0] * inVolumeSize,
            transDirection[1] * inVolumeSize,
            transDirection[2] * inVolumeSize,
        )
        volBone.parent = self.rootBone

        rotAxis = rt.Point3(*_ROT_AXIS_VECTORS.get(inRotAxis, (0.0, 0.0, 0.0)))

        localRotRefTm = self.limb.transform * rt.inverse(self.rotHelper.transform)
        volBonePosConst = self.const.assign_pos_script_controller(volBone)
        volBonePosConst.addNode("limb", self.limb)
        volBonePosConst.addNode("limbParent", self.rotHelper)
        volBonePosConst.addConstant("axis", rotAxis)
        volBonePosConst.addConstant("transScale", rt.Float(inTransScale))
        volBonePosConst.addConstant("volumeSize", rt.Float(inVolumeSize))
        volBonePosConst.addConstant("localRotRefTm", localRotRefTm)
        volBonePosConst.addConstant("trAxis", volBoneTrDir)
        volBonePosConst.setExpression(self.posScriptExpression)
        volBonePosConst.update()

        return True

    # ------------------------------------------------------------------
    # 진입점
    # ------------------------------------------------------------------

    def create_volume_bones(
        self,
        inObj,
        inParent,
        inRotScale: float,
        inVolumeSize: float,
        inRotAxises: list,
        inTransAxises: list,
        inTransScales: list,
    ) -> Optional[dict]:
        """루트 본과 볼륨 본들을 만들고 생성 결과를 돌려준다.

        `create_bones()`와 파트 서브클래스가 함께 쓰는 공통 본체다. 서브클래스는
        이것으로 본을 만든 뒤 자기 이름 규칙으로 개명하고 자기 `Parameters`를 붙인다.

        Args:
            inObj: 볼륨 본을 붙일 대상 관절
            inParent: 대상 관절의 부모
            inRotScale: 회전 반영 비율
            inVolumeSize: 볼륨 크기
            inRotAxises: 회전 축 리스트
            inTransAxises: 이동 축 리스트
            inTransScales: 이동 스케일 리스트

        Returns:
            dict | None: `{"rootBone", "volumeBones", "rotHelper"}`.
                노드가 유효하지 않거나, 축 리스트 길이가 다르거나, 미등록 축이 있거나,
                루트 본 생성에 실패하면 None. 축 검사는 **본을 하나도 만들기 전에** 하므로
                거절된 호출은 씬에 아무것도 남기지 않는다.
        """
        if not self.validate_source_nodes(inObj, inParent):
            return None

        if len(inRotAxises) != len(inTransAxises) or len(inRotAxises) != len(inTransScales):
            _get_logger().warning(
                f"{type(self).__name__}: 축 리스트 길이가 다르다 "
                f"(rot {len(inRotAxises)}, trans {len(inTransAxises)}, scale {len(inTransScales)})"
            )
            return None

        invalid = invalid_axes(inRotAxises, inTransAxises)
        if invalid:
            _warn_invalid_axes(type(self).__name__, invalid)
            return None

        rootBone = self.create_root_bone(inObj, inParent, inRotScale=inRotScale)
        if not rootBone:
            return None

        volumeBones = []
        for index in range(len(inRotAxises)):
            self.create_bone(
                inObj,
                inParent,
                inRotScale,
                inVolumeSize,
                inRotAxises[index],
                inTransAxises[index],
                inTransScales[index],
                inUseRootBone=True,
                inRootBone=rootBone,
            )

            # 방금 만든 본을 이름으로 되찾는다. `create_bone`이 노드를 돌려주지 않는
            # 전 구현의 형태를 그대로 둔다 - 동작 불변이 이 사이클의 기준이다.
            volBoneName = self.volume_bone_name(inObj.name, inRotAxises[index], inTransAxises[index])
            if self.is_lower_case_name(volBoneName):
                volBoneName = volBoneName.lower()
            volBone = self.find_node(self.name.remove_name_part("Nub", volBoneName))
            if volBone is not None:
                volumeBones.append(volBone)

        return {"rootBone": rootBone, "volumeBones": volumeBones, "rotHelper": self.rotHelper}

    def create_bones(
        self,
        inObj,
        inParent,
        inRotScale: float = 0.5,
        inVolumeSize: float = 5.0,
        inRotAxises: Optional[list] = None,
        inTransAxises: Optional[list] = None,
        inTransScales: Optional[list] = None,
    ) -> Optional[BoneChain]:
        """루트 본과 여러 개의 볼륨 본을 생성한다.

        Args:
            inObj: 볼륨 본을 붙일 대상 관절
            inParent: 대상 관절의 부모
            inRotScale: 회전 반영 비율
            inVolumeSize: 볼륨 크기
            inRotAxises: 회전 축 리스트 ("X", "Y", "Z")
            inTransAxises: 이동 축 리스트 ("PosX"~"NegZ")
            inTransScales: 이동 스케일 리스트

        Returns:
            BoneChain | None: 생성된 볼륨 본 체인. 실패하면 None
        """
        rotAxises = list(inRotAxises) if inRotAxises is not None else ["Z"]
        transAxises = list(inTransAxises) if inTransAxises is not None else ["PosY"]
        transScales = list(inTransScales) if inTransScales is not None else [1.0]

        built = self.create_volume_bones(
            inObj, inParent, inRotScale, inVolumeSize, rotAxises, transAxises, transScales
        )
        if built is None:
            return None

        allBones = [built["rootBone"]] + built["volumeBones"]
        rotHelper = built["rotHelper"]

        self.tag_as_skin_bones(allBones + [rotHelper], [inObj, inParent])

        result = self.build_result(
            allBones,
            [rotHelper],
            [inObj, inParent],
            {
                "inRotScale": inRotScale,
                "inVolumeSize": inVolumeSize,
                "inRotAxises": rotAxises,
                "inTransAxises": transAxises,
                "inTransScales": transScales,
            },
        )

        self.reset()
        rt.redrawViews()

        return BoneChain.from_result(result)
