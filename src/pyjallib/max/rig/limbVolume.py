#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""팔다리 관절 볼륨 본의 공통 본체 - `_LimbVolumePart`.

`Elbow`·`Wrist`·`Ankle`·`Inguinal`은 `VolumeBone`을 상속해 같은 8단계를 밟는다.
네 파일이 155줄 안팎에서 서로 120~159줄씩 달랐지만, 실제로 다른 것은
**표로 적을 수 있는 값**과 **훅 세 개**뿐이었다(2026-09-21 소스 대조).

## 공통 8단계

1. 입력 노드 유효성 검사
2. 이름 생성 (Root·RootDum·방향별 이름)
3. 소문자 전파
4. 방향 결정 (`facingDirVec`와 대상의 X축 내적 부호)
5. 축·스케일 계획 조립 (`_build_axis_plan` 훅)
6. `VolumeBone.create_bones()` 호출
7. 생성된 본·헬퍼 개명 (`_rename_rules` 훅) + 개명 직후 후처리 (`_postprocess_bone` 훅)
8. 스킨 본 표시 -> 결과 조립

## 표로 흡수한 차이

`REAL_NAME`(RealName 치환값) · `NAME_SOURCE_INDEX`(이름 기준 노드) ·
`DIRECTION_SOURCE`(방향 계산에 쓰는 두 노드) · `VOLUME_SOURCE`(부모에게 넘길 obj/parent) ·
`STRIP_NAME_PARTS`(이름에서 떼어낼 부분) · `DIRECTION_NAME_KEYS`(방향별 이름 키).

## 훅으로 남긴 차이

- `_build_axis_plan`: `distanceDir < 0`일 때의 뒤집기가 **넷 다 다르다.**
  elbow·ankle은 스케일과 이름을 함께 스왑, wrist는 이름만 쌍 단위 스왑,
  inguinal은 스왑이 아니라 축 자체를 `Neg` 접두로 재작성한다.
- `_rename_rules`: ankle만 축 이름이 아니라 `*pos*`/`*neg*`로 매칭한다.
- `_postprocess_bone`: inguinal만 위치 스크립트에 조건절을 주입한다.

## 결과 `Parameters`가 자기 것이 된다

전 구현에서 elbow·wrist·ankle은 부모가 만든 `BoneChain`을 **그대로 반환**했다. 그래서
`Parameters`에 `VolumeBone` 레이아웃이 담겼는데 자기 `create_bones_from_chain`은 다른
레이아웃으로 읽어, 재생성이 `Unable to convert: "NegY" to type: Float`로 죽었다.
이제 네 파트 모두 **자기 `PARAM_SPEC` 이름으로** 결과를 조립하므로 어긋날 수 없다.
"""

from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain
from .volumeBone import VolumeBone


class _LimbVolumePart(VolumeBone):
    """팔다리 관절 볼륨 본 파트의 공통 본체."""

    #: `RealName` 부분을 이 값으로 치환해 파트 이름을 만든다.
    REAL_NAME = ""

    #: 이름 생성의 기준이 되는 소스 노드의 인덱스(`SOURCE_SPEC` 기준).
    NAME_SOURCE_INDEX = 1

    #: 방향 벡터를 만들 (끝점, 시작점) 인덱스. `vec = source[끝].pos - source[시작].pos`
    DIRECTION_SOURCE = (0, 1)

    #: 방향 벡터와 내적할 X축을 제공하는 노드의 인덱스. inguinal만 벡터의 끝점과 다르다
    #: (벡터는 calf - thighTwist인데 X축은 thighTwist의 것을 쓴다).
    DIRECTION_AXIS_INDEX = 0

    #: `VolumeBone.create_bones()`에 넘길 (inObj, inParent) 인덱스.
    VOLUME_SOURCE = (0, 1)

    #: 파트 이름에서 떼어낼 name part들. inguinal만 Nub·Index를 뗀다.
    STRIP_NAME_PARTS = ()

    #: 방향별 이름 키와 그 생성 규칙. `(키, name part, description)`.
    DIRECTION_NAME_KEYS = ()

    # ------------------------------------------------------------------
    # 2·3단계 - 이름
    # ------------------------------------------------------------------

    def build_part_names(self, inSourceNodes: list) -> dict:
        """파트의 모든 이름을 만들고 소문자를 전파한다.

        Args:
            inSourceNodes: `SOURCE_SPEC` 순서의 소스 노드

        Returns:
            dict: `base`·`root`·`rootDum` + `DIRECTION_NAME_KEYS`의 키
        """
        referenceName = inSourceNodes[self.NAME_SOURCE_INDEX].name
        filteringChar = self.filtering_char(referenceName)

        baseName = self.name.replace_name_part("RealName", referenceName, self.REAL_NAME)
        for partName in self.STRIP_NAME_PARTS:
            baseName = self.name.remove_name_part(partName, baseName)

        rootName = self.name.replace_name_part(
            "RealName", baseName, self.REAL_NAME + filteringChar + "Root"
        )

        names = {"base": baseName, "root": rootName, "rootDum": self.dummy_name(rootName)}
        for key, namePart, description in self.DIRECTION_NAME_KEYS:
            names[key] = self.name.replace_name_part(
                namePart,
                baseName,
                self.name.get_name_part_value_by_description(namePart, description),
            )

        return self.propagate_lower_case(referenceName, names)

    # ------------------------------------------------------------------
    # 4단계 - 방향
    # ------------------------------------------------------------------

    def facing_direction(self, inSourceNodes: list) -> float:
        """팔다리가 향하는 방향의 부호를 돌려준다.

        Args:
            inSourceNodes: `SOURCE_SPEC` 순서의 소스 노드

        Returns:
            float: 같은 방향이면 1.0, 반대면 -1.0
        """
        endNode = inSourceNodes[self.DIRECTION_SOURCE[0]]
        startNode = inSourceNodes[self.DIRECTION_SOURCE[1]]
        facingDirVec = endNode.transform.position - startNode.transform.position
        objXAxisVec = inSourceNodes[self.DIRECTION_AXIS_INDEX].objectTransform.row1
        return 1.0 if rt.dot(objXAxisVec, facingDirVec) > 0 else -1.0

    # ------------------------------------------------------------------
    # 훅
    # ------------------------------------------------------------------

    def _build_axis_plan(self, inParameters: dict, inDistanceDir: float) -> dict:
        """축·스케일 계획을 조립한다. 하위 클래스가 구현한다.

        Args:
            inParameters: `PARAM_SPEC` 기준으로 채워진 파라미터
            inDistanceDir: `facing_direction()`의 결과

        Returns:
            dict: `rotAxises`·`transAxises`·`transScales`·`transAxisNames`

        Raises:
            NotImplementedError: 하위 클래스가 구현하지 않았으면
        """
        raise NotImplementedError(f"{type(self).__name__}._build_axis_plan()가 구현되지 않았다")

    def _rename_rules(self, inNames: dict, inPlan: dict) -> list:
        """볼륨 본 개명 규칙을 순서대로 돌려준다.

        기본 구현은 축 이름(`transAxisNames`)으로 매칭하고, `DIRECTION_NAME_KEYS`의
        순서를 그대로 쓴다. ankle만 이 규칙을 갈아끼운다.

        Args:
            inNames: `build_part_names()`의 결과
            inPlan: `_build_axis_plan()`의 결과

        Returns:
            list: `(매칭 패턴, 새 이름, 후처리 키)` 목록
        """
        rules = []
        for index, axisName in enumerate(inPlan["transAxisNames"]):
            key = self.RENAME_KEY_ORDER[index]
            rules.append(("*" + axisName.lower() + "*", inNames[key], key))
        return rules

    #: `_rename_rules` 기본 구현이 축 순서에 대응시킬 이름 키.
    RENAME_KEY_ORDER = ()

    def _postprocess_bone(self, inBone, inRenameKey: str) -> None:
        """개명 직후 본 하나에 후처리를 건다. 기본은 아무것도 하지 않는다.

        Args:
            inBone: 방금 개명한 본
            inRenameKey: 그 본에 적용된 이름 키
        """
        return None

    # ------------------------------------------------------------------
    # 공통 본체
    # ------------------------------------------------------------------

    def create_limb_volume(
        self, inSourceNodes: list, inParameters: dict
    ) -> Optional[BoneChain]:
        """팔다리 관절 볼륨 본을 만든다 - 8단계 공통 본체.

        Args:
            inSourceNodes: `SOURCE_SPEC` 순서의 소스 노드
            inParameters: `PARAM_SPEC` 기준 파라미터 dict

        Returns:
            BoneChain | None: 생성된 체인. 실패하면 None
        """
        if not self.validate_source_nodes(*inSourceNodes):
            return None

        names = self.build_part_names(inSourceNodes)
        plan = self._build_axis_plan(inParameters, self.facing_direction(inSourceNodes))

        volumeChain = super().create_bones(
            inSourceNodes[self.VOLUME_SOURCE[0]],
            inSourceNodes[self.VOLUME_SOURCE[1]],
            inParameters["inRotScale"],
            inParameters["inVolumeSize"],
            plan["rotAxises"],
            plan["transAxises"],
            plan["transScales"],
        )
        if volumeChain is None:
            return None

        renameRules = [("*root*", names["root"], "root")] + self._rename_rules(names, plan)
        for bone in volumeChain.bones:
            for pattern, newName, renameKey in renameRules:
                if rt.matchPattern(bone.name.lower(), pattern=pattern):
                    bone.name = newName
                    self._postprocess_bone(bone, renameKey)
                    break

        for helper in volumeChain.helpers:
            if rt.matchPattern(helper.name.lower(), pattern="*root*"):
                helper.name = names["rootDum"]

        self.tag_as_skin_bones(volumeChain.bones + volumeChain.helpers, inSourceNodes)

        rt.redrawViews()

        return BoneChain.from_result(
            self.build_result(
                volumeChain.bones, volumeChain.helpers, list(inSourceNodes), inParameters
            )
        )
