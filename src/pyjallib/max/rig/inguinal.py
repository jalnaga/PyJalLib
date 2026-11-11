#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""서혜부 볼륨 본.

다리가 앞으로 들리거나 바깥으로 벌어질 때 밀리는 볼륨 본 2개를 만든다.
네 limb 파트 중 유일하게 **소스 본이 3개**이고, 생성된 본의 위치 스크립트에
방향 조건절을 주입한다(한쪽 방향으로만 밀리게 한다).
"""

from typing import Optional

from .boneChain import BoneChain
from .limbVolume import _LimbVolumePart

#: 위치 스크립트에 주입할 조건절. 원래 표현식의 마지막 줄을 이것으로 바꾼다.
_BASE_EXPRESSION = "trAxis * saturatedTwist * volumeSize * transScale"

#: 이름 키 -> 주입할 조건. 앞쪽은 Z 회전이 양일 때만, 바깥쪽은 Y 회전이 음일 때만 민다.
_DIRECTION_CONDITIONS = {
    "fwd": "swizzledRot.z > 0",
    "out": "swizzledRot.y < 0",
}


class Inguinal(_LimbVolumePart):
    """서혜부 볼륨 본을 생성하는 클래스."""

    REAL_NAME = "Inguinal"
    SOURCE_SPEC = ("inThighTwist", "inPelvis", "inCalf")
    NAME_SOURCE_INDEX = 0
    #: 방향 벡터는 calf - thighTwist이고, 내적할 X축은 thighTwist의 것이다.
    DIRECTION_SOURCE = (2, 0)
    DIRECTION_AXIS_INDEX = 0
    VOLUME_SOURCE = (0, 1)
    #: 트위스트 본 이름에 붙은 Nub·Index를 떼고 파트 이름을 만든다.
    STRIP_NAME_PARTS = ("Nub", "Index")
    DIRECTION_NAME_KEYS = (
        ("fwd", "FrontBack", "Forward"),
        ("out", "InOut", "Out"),
    )
    RENAME_KEY_ORDER = ("fwd", "out")

    PARAM_SPEC = (
        ("inRotScale", 0.5),
        ("inVolumeSize", 10.0),
        ("inFwdRotAxis", "Z"),
        ("inOutRotAxis", "Y"),
        ("inFwdTransAxis", "PosY"),
        ("inOutTransAxis", "PosZ"),
        ("inFwdTransScale", 2.0),
        ("inOutTransScale", 2.5),
    )

    def _build_axis_plan(self, inParameters: dict, inDistanceDir: float) -> dict:
        """서혜부의 축·스케일 계획을 조립한다.

        다리가 반대 방향을 보면 **스왑이 아니라 축 자체를 `Neg` 접두로 재작성한다** -
        네 limb 파트 중 유일하게 `super()`에 넘기는 축 값 자체가 바뀐다.

        Args:
            inParameters: `PARAM_SPEC` 기준 파라미터
            inDistanceDir: 방향 부호

        Returns:
            dict: `rotAxises`·`transAxises`·`transScales`·`transAxisNames`
        """
        fwdTransAxis = inParameters["inFwdTransAxis"]
        outTransAxis = inParameters["inOutTransAxis"]

        transAxises = [fwdTransAxis, outTransAxis]
        if inDistanceDir < 0:
            transAxises = ["Neg" + fwdTransAxis[3:], "Neg" + outTransAxis[3:]]

        return {
            "rotAxises": [inParameters["inFwdRotAxis"], inParameters["inOutRotAxis"]],
            "transAxises": transAxises,
            "transScales": [inParameters["inFwdTransScale"], inParameters["inOutTransScale"]],
            "transAxisNames": list(transAxises),
        }

    def _postprocess_bone(self, inBone, inRenameKey: str) -> None:
        """볼륨 본의 위치 스크립트에 방향 조건절을 주입한다.

        해당 방향으로 굽었을 때만 밀리고 반대로는 움직이지 않게 만든다.

        Args:
            inBone: 방금 개명한 본
            inRenameKey: 그 본에 적용된 이름 키
        """
        condition = _DIRECTION_CONDITIONS.get(inRenameKey)
        if condition is None:
            return

        posScriptConst = self.const.get_pos_list_controller(inBone)[1]
        replacement = (
            f"result = {_BASE_EXPRESSION}\n"
            f"if {condition} then result\n"
            "else result * 0.0\n"
        )
        posScriptConst.setExpression(
            posScriptConst.script.replace(_BASE_EXPRESSION, replacement)
        )
        posScriptConst.update()

    def create_bones(
        self,
        inThighTwist,
        inPelvis,
        inCalf,
        inRotScale: float = 0.5,
        inVolumeSize: float = 10.0,
        inFwdRotAxis: str = "Z",
        inOutRotAxis: str = "Y",
        inFwdTransAxis: str = "PosY",
        inOutTransAxis: str = "PosZ",
        inFwdTransScale: float = 2.0,
        inOutTransScale: float = 2.5,
    ) -> Optional[BoneChain]:
        """서혜부 볼륨 본들을 생성한다.

        Args:
            inThighTwist: 허벅지 트위스트 본. 볼륨 본의 기준 객체이자 이름 기준이 된다.
            inPelvis: 골반 본. 볼륨 본의 부모 기준이 된다.
            inCalf: 종아리 본. 방향 판정에만 쓴다.
            inRotScale: 회전 반영 비율
            inVolumeSize: 볼륨 본 크기
            inFwdRotAxis: 앞쪽 방향 회전 감지 축
            inOutRotAxis: 바깥쪽 방향 회전 감지 축
            inFwdTransAxis: 앞쪽 본 이동 축
            inOutTransAxis: 바깥쪽 본 이동 축
            inFwdTransScale: 앞쪽 본 이동 스케일
            inOutTransScale: 바깥쪽 본 이동 스케일

        Returns:
            BoneChain | None: 생성된 서혜부 본 체인. 실패하면 None
        """
        return self.create_limb_volume(
            [inThighTwist, inPelvis, inCalf],
            {
                "inRotScale": inRotScale,
                "inVolumeSize": inVolumeSize,
                "inFwdRotAxis": inFwdRotAxis,
                "inOutRotAxis": inOutRotAxis,
                "inFwdTransAxis": inFwdTransAxis,
                "inOutTransAxis": inOutTransAxis,
                "inFwdTransScale": inFwdTransScale,
                "inOutTransScale": inOutTransScale,
            },
        )
