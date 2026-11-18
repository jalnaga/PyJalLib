#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""발목 볼륨 본.

발목이 굽을 때 앞뒤로 밀리는 볼륨 본 2개를 만든다. 축 계획은 팔꿈치와 같은 규칙이고,
**개명 매칭만 다르다** - 축 이름이 아니라 `Pos`/`Neg` 의미로 앞뒤를 가른다.
"""

from typing import Optional

from .boneChain import BoneChain
from .limbVolume import _LimbVolumePart


class Ankle(_LimbVolumePart):
    """발목 볼륨 본을 생성하는 클래스."""

    REAL_NAME = "Ankle"
    SOURCE_SPEC = ("inFoot", "inCalf")
    NAME_SOURCE_INDEX = 1
    DIRECTION_SOURCE = (0, 1)
    VOLUME_SOURCE = (0, 1)
    DIRECTION_NAME_KEYS = (
        ("fwd", "FrontBack", "Forward"),
        ("bck", "FrontBack", "Backward"),
    )

    PARAM_SPEC = (
        ("inRotScale", 0.5),
        ("inVolumeSize", 4.0),
        ("inRotAxis", "Z"),
        ("inAnkleTransAxis", "PosY"),
        ("inInnerAnkleTransAxis", "NegY"),
        ("inAnkleTransScale", 1.5),
        ("inInnerAnkleTransScale", 1.0),
    )

    def _build_axis_plan(self, inParameters: dict, inDistanceDir: float) -> dict:
        """발목의 축·스케일 계획을 조립한다(팔꿈치와 같은 뒤집기 규칙).

        Args:
            inParameters: `PARAM_SPEC` 기준 파라미터
            inDistanceDir: 방향 부호

        Returns:
            dict: `rotAxises`·`transAxises`·`transScales`·`transAxisNames`
        """
        rotAxis = inParameters["inRotAxis"]
        outerAxis = inParameters["inAnkleTransAxis"]
        innerAxis = inParameters["inInnerAnkleTransAxis"]
        outerScale = inParameters["inAnkleTransScale"]
        innerScale = inParameters["inInnerAnkleTransScale"]

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

    def _rename_rules(self, inNames: dict, inPlan: dict) -> list:
        """축 이름이 아니라 `Pos`/`Neg` 의미로 앞뒤를 가른다.

        네 파트 중 발목만 이 규칙을 쓴다(전 구현의 주석: "축 이름의 의미(Pos=앞,
        Neg=뒤)를 기준으로 이름 매핑"). 이동 축을 둘 다 `Pos*`로 주면 두 본이 같은
        규칙에 걸리지만, 그것이 현행 동작이므로 그대로 둔다.

        Args:
            inNames: `build_part_names()`의 결과
            inPlan: `_build_axis_plan()`의 결과

        Returns:
            list: `(매칭 패턴, 새 이름, 후처리 키)` 목록
        """
        return [("*pos*", inNames["fwd"], "fwd"), ("*neg*", inNames["bck"], "bck")]

    def create_bones(
        self,
        inFoot,
        inCalf,
        inRotScale: float = 0.5,
        inVolumeSize: float = 4.0,
        inRotAxis: str = "Z",
        inAnkleTransAxis: str = "PosY",
        inInnerAnkleTransAxis: str = "NegY",
        inAnkleTransScale: float = 1.5,
        inInnerAnkleTransScale: float = 1.0,
    ) -> Optional[BoneChain]:
        """발목 볼륨 본들을 생성한다.

        Args:
            inFoot: 발 본. 볼륨 본의 기준 객체가 된다.
            inCalf: 종아리 본. 볼륨 본의 부모 기준이자 이름 기준이 된다.
            inRotScale: 회전 반영 비율
            inVolumeSize: 볼륨 본 크기
            inRotAxis: 회전 감지 축 ("X", "Y", "Z")
            inAnkleTransAxis: 발목(앞쪽) 본 이동 축
            inInnerAnkleTransAxis: 안쪽 발목(뒤쪽) 본 이동 축
            inAnkleTransScale: 발목 본 이동 스케일
            inInnerAnkleTransScale: 안쪽 발목 본 이동 스케일

        Returns:
            BoneChain | None: 생성된 발목 본 체인. 실패하면 None
        """
        return self.create_limb_volume(
            [inFoot, inCalf],
            {
                "inRotScale": inRotScale,
                "inVolumeSize": inVolumeSize,
                "inRotAxis": inRotAxis,
                "inAnkleTransAxis": inAnkleTransAxis,
                "inInnerAnkleTransAxis": inInnerAnkleTransAxis,
                "inAnkleTransScale": inAnkleTransScale,
                "inInnerAnkleTransScale": inInnerAnkleTransScale,
            },
        )
