#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""손목 볼륨 본.

손목의 앞/뒤(FB)와 안/바깥(IO) 방향으로 볼륨 본 **4개**를 만든다. 네 limb 파트 중
유일하게 볼륨 본이 4개이고, 이동 축을 축 문자(`"Y"`)로 받아 `Pos`/`Neg` 접두를
코드가 붙인다.
"""

from typing import Optional

from .boneChain import BoneChain
from .limbVolume import _LimbVolumePart


class Wrist(_LimbVolumePart):
    """손목 볼륨 본을 생성하는 클래스."""

    REAL_NAME = "Wrist"
    SOURCE_SPEC = ("inHand", "inForeArm")
    NAME_SOURCE_INDEX = 1
    DIRECTION_SOURCE = (0, 1)
    VOLUME_SOURCE = (0, 1)
    DIRECTION_NAME_KEYS = (
        ("fwd", "FrontBack", "Forward"),
        ("bck", "FrontBack", "Backward"),
        ("in", "InOut", "In"),
        ("out", "InOut", "Out"),
    )
    RENAME_KEY_ORDER = ("bck", "fwd", "in", "out")

    PARAM_SPEC = (
        ("inRotScale", 0.5),
        ("inVolumeSize", 4.0),
        ("inFBRotAxis", "Y"),
        ("inIORotAxis", "Z"),
        ("inFBTransAxis", "Z"),
        ("inIOTransAxis", "Y"),
        ("inFBTransScale", 1.0),
        ("inIOTransScale", 1.0),
    )

    def _build_axis_plan(self, inParameters: dict, inDistanceDir: float) -> dict:
        """손목의 축·스케일 계획을 조립한다.

        이동 축을 축 문자로 받아 `Pos`/`Neg` 접두를 여기서 붙인다. 손이 반대 방향을
        보면 **이름 매핑만 쌍 단위로 뒤집고 스케일은 그대로 둔다** - elbow·ankle이
        스케일까지 뒤집는 것과 다르다(현행 동작 그대로 옮긴다).

        Args:
            inParameters: `PARAM_SPEC` 기준 파라미터
            inDistanceDir: 방향 부호

        Returns:
            dict: `rotAxises`·`transAxises`·`transScales`·`transAxisNames`
        """
        fbRotAxis = inParameters["inFBRotAxis"]
        ioRotAxis = inParameters["inIORotAxis"]
        fbTransAxis = inParameters["inFBTransAxis"]
        ioTransAxis = inParameters["inIOTransAxis"]
        fbScale = inParameters["inFBTransScale"]
        ioScale = inParameters["inIOTransScale"]

        transAxises = [
            "Pos" + fbTransAxis,
            "Neg" + fbTransAxis,
            "Pos" + ioTransAxis,
            "Neg" + ioTransAxis,
        ]
        transAxisNames = list(transAxises)
        if inDistanceDir < 0:
            transAxisNames = [transAxises[1], transAxises[0], transAxises[3], transAxises[2]]

        return {
            "rotAxises": [fbRotAxis, fbRotAxis, ioRotAxis, ioRotAxis],
            "transAxises": transAxises,
            "transScales": [fbScale, fbScale, ioScale, ioScale],
            "transAxisNames": transAxisNames,
        }

    def create_bones(
        self,
        inHand,
        inForeArm,
        inRotScale: float = 0.5,
        inVolumeSize: float = 4.0,
        inFBRotAxis: str = "Y",
        inIORotAxis: str = "Z",
        inFBTransAxis: str = "Z",
        inIOTransAxis: str = "Y",
        inFBTransScale: float = 1.0,
        inIOTransScale: float = 1.0,
    ) -> Optional[BoneChain]:
        """손목 볼륨 본들을 생성한다.

        Args:
            inHand: 손 본. 볼륨 본의 기준 객체가 된다.
            inForeArm: 전완 본. 볼륨 본의 부모 기준이자 이름 기준이 된다.
            inRotScale: 회전 반영 비율
            inVolumeSize: 볼륨 본 크기
            inFBRotAxis: 앞/뒤 방향 회전 감지 축 ("X", "Y", "Z")
            inIORotAxis: 안/바깥 방향 회전 감지 축 ("X", "Y", "Z")
            inFBTransAxis: 앞/뒤 방향 본 이동 축. "Pos"/"Neg" 접두사가 자동으로 붙는다.
            inIOTransAxis: 안/바깥 방향 본 이동 축. "Pos"/"Neg" 접두사가 자동으로 붙는다.
            inFBTransScale: 앞/뒤 방향 본 이동 스케일
            inIOTransScale: 안/바깥 방향 본 이동 스케일

        Returns:
            BoneChain | None: 생성된 손목 본 체인. 실패하면 None
        """
        return self.create_limb_volume(
            [inHand, inForeArm],
            {
                "inRotScale": inRotScale,
                "inVolumeSize": inVolumeSize,
                "inFBRotAxis": inFBRotAxis,
                "inIORotAxis": inIORotAxis,
                "inFBTransAxis": inFBTransAxis,
                "inIOTransAxis": inIOTransAxis,
                "inFBTransScale": inFBTransScale,
                "inIOTransScale": inIOTransScale,
            },
        )
