#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""팔꿈치 볼륨 본.

팔꿈치가 굽을 때 바깥쪽·안쪽으로 밀리는 볼륨 본 2개를 만든다.
공통 8단계는 `_LimbVolumePart`에 있고, 이 파일은 **표와 축 계획**만 갖는다.
"""

from typing import Optional

from .boneChain import BoneChain
from .limbVolume import _LimbVolumePart


class Elbow(_LimbVolumePart):
    """팔꿈치 볼륨 본을 생성하는 클래스."""

    REAL_NAME = "Elbow"
    SOURCE_SPEC = ("inForeArm", "inUpperArm")
    NAME_SOURCE_INDEX = 1
    DIRECTION_SOURCE = (0, 1)
    VOLUME_SOURCE = (0, 1)
    DIRECTION_NAME_KEYS = (
        ("fwd", "FrontBack", "Forward"),
        ("bck", "FrontBack", "Backward"),
    )
    RENAME_KEY_ORDER = ("bck", "fwd")

    PARAM_SPEC = (
        ("inRotScale", 0.5),
        ("inVolumeSize", 4.0),
        ("inRotAxis", "Z"),
        ("inElbowTransAxis", "PosY"),
        ("inInnerElbowTransAxis", "NegY"),
        ("inElbowTransScale", 0.25),
        ("inInnerElbowTransScale", 1.0),
    )

    def _build_axis_plan(self, inParameters: dict, inDistanceDir: float) -> dict:
        """팔꿈치의 축·스케일 계획을 조립한다.

        볼륨 본이 2개이므로 같은 회전축을 두 번 쓴다. 팔이 반대 방향을 보면
        **스케일과 이름 매핑을 함께 뒤집는다**(ankle과 같은 규칙).

        Args:
            inParameters: `PARAM_SPEC` 기준 파라미터
            inDistanceDir: 방향 부호

        Returns:
            dict: `rotAxises`·`transAxises`·`transScales`·`transAxisNames`
        """
        rotAxis = inParameters["inRotAxis"]
        outerAxis = inParameters["inElbowTransAxis"]
        innerAxis = inParameters["inInnerElbowTransAxis"]
        outerScale = inParameters["inElbowTransScale"]
        innerScale = inParameters["inInnerElbowTransScale"]

        transScales = [outerScale, innerScale]
        transAxisNames = [outerAxis, innerAxis]
        if inDistanceDir < 0:
            transScales = [innerScale, outerScale]
            transAxisNames = [innerAxis, outerAxis]

        return {
            "rotAxises": [rotAxis, rotAxis],
            "transAxises": [outerAxis, innerAxis],
            "transScales": transScales,
            "transAxisNames": transAxisNames,
        }

    def create_bones(
        self,
        inForeArm,
        inUpperArm,
        inRotScale: float = 0.5,
        inVolumeSize: float = 4.0,
        inRotAxis: str = "Z",
        inElbowTransAxis: str = "PosY",
        inInnerElbowTransAxis: str = "NegY",
        inElbowTransScale: float = 0.25,
        inInnerElbowTransScale: float = 1.0,
    ) -> Optional[BoneChain]:
        """팔꿈치 볼륨 본들을 생성한다.

        Args:
            inForeArm: 전완 본. 볼륨 본의 기준 객체가 된다.
            inUpperArm: 상완 본. 볼륨 본의 부모 기준이자 이름 기준이 된다.
            inRotScale: 회전 반영 비율
            inVolumeSize: 볼륨 본 크기
            inRotAxis: 회전 감지 축 ("X", "Y", "Z")
            inElbowTransAxis: 팔꿈치(뒤쪽) 본 이동 축 (예: "PosY")
            inInnerElbowTransAxis: 안쪽 팔꿈치(앞쪽) 본 이동 축 (예: "NegY")
            inElbowTransScale: 팔꿈치 본 이동 스케일
            inInnerElbowTransScale: 안쪽 팔꿈치 본 이동 스케일

        Returns:
            BoneChain | None: 생성된 팔꿈치 본 체인. 실패하면 None
        """
        return self.create_limb_volume(
            [inForeArm, inUpperArm],
            {
                "inRotScale": inRotScale,
                "inVolumeSize": inVolumeSize,
                "inRotAxis": inRotAxis,
                "inElbowTransAxis": inElbowTransAxis,
                "inInnerElbowTransAxis": inInnerElbowTransAxis,
                "inElbowTransScale": inElbowTransScale,
                "inInnerElbowTransScale": inInnerElbowTransScale,
            },
        )
