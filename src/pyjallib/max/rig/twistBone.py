#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""트위스트 본 - 팔·다리의 비틀림 회전을 여러 본에 분산한다.

상완/대퇴부처럼 **부모 쪽이 도는** 상부(Upper)와 전완/하퇴부처럼 **자식 쪽이 도는**
하부(Lower)를 같은 골격으로 만든다. 둘의 차이는 표로 적을 수 있다(아래 `_TWIST_MODES`).

전 구현은 `create_upper_limb_bones` / `create_lower_limb_bones` 두 진입점을 두고
**본체를 통째로 복제**했다(각 100줄, 서로 다른 곳은 6군데). 이제 진입점은
`create_bones(inObj, inChild, inTwistNum, inTwistType)` 하나이고, `inTwistType`이
표를 고른다. `BoneChain.parameters`가 이미 `[twistNum, "Upper"]`로 타입을 담고 있었으므로
계약이 늘어나는 것도 아니다.
"""

from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain, _get_logger
from .rigPart import _RigPartBase

#: 상부용 회전 표현식. 관절의 로컬 회전에서 X축 twist 성분만 뽑아 **역으로** 돌린다.
UPPER_TWIST_EXPRESSION = (
    "localTm = limb.transform * (inverse limbParent.transform)\n"
    "tm = localTm * inverse(localRefTm)\n"
    "\n"
    "q = tm.rotation\n"
    "\n"
    "axis = [1,0,0]\n"
    "proj = (dot q.axis axis) * axis\n"
    "twist = quat q.angle proj\n"
    "twist = normalize twist\n"
    "--swing = tm.rotation * (inverse twist)\n"
    "\n"
    "inverse twist\n"
)

#: 하부용 회전 표현식. 상부와 같되 마지막 줄이 `twist`다(역으로 돌리지 않는다).
LOWER_TWIST_EXPRESSION = (
    "localTm = limb.transform * (inverse limbParent.transform)\n"
    "tm = localTm * inverse(localRefTm)\n"
    "\n"
    "q = tm.rotation\n"
    "\n"
    "axis = [1,0,0]\n"
    "proj = (dot q.axis axis) * axis\n"
    "twist = quat q.angle proj\n"
    "twist = normalize twist\n"
    "--swing = tm.rotation * (inverse twist)\n"
    "\n"
    "twist\n"
)


class TwistBone(_RigPartBase):
    """팔·다리의 트위스트 본 체인을 생성하는 클래스."""

    PARAM_SPEC = (
        ("inTwistNum", 4),
        ("inTwistType", "Upper"),
    )

    SOURCE_SPEC = ("inObj", "inChild")

    WORK_DEFAULTS = {
        "limb": None,
        "child": None,
        "twistNum": 0,
        "bones": [],
        "twistType": "",
    }

    #: 전 구현이 인스턴스 속성으로 들고 있던 표현식. 상수이므로 클래스에 둔다.
    upperTwistBoneExpression = UPPER_TWIST_EXPRESSION
    lowerTwistBoneExpression = LOWER_TWIST_EXPRESSION

    def __init__(
        self,
        inNameService,
        inAnimService,
        inHelperService,
        inBoneService,
        inConstService,
        inBipService,
    ):
        """트위스트 본 서비스를 초기화한다.

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

    # ------------------------------------------------------------------
    # 내부 조립
    # ------------------------------------------------------------------

    def _twist_bone_base_name(self, inObj) -> str:
        """트위스트 본들의 기준 이름을 만든다.

        Args:
            inObj: 이름 기준이 되는 노드

        Returns:
            str: `RealName`에 Twist 접미가 붙은 이름
        """
        boneName = self.name.add_suffix_to_real_name(
            inObj.name, self.filtering_char(inObj.name) + "Twist"
        )
        return boneName.lower() if self.is_lower_case_name(inObj.name) else boneName

    def _create_indexed_bone(self, inBaseName: str, inIndex: int, inTransformSource, inParent):
        """번호가 붙은 트위스트 본 하나를 만들고 부모에 붙인다.

        Args:
            inBaseName: `_twist_bone_base_name()`의 결과
            inIndex: 본 번호 (1부터)
            inTransformSource: 트랜스폼을 가져올 노드
            inParent: 부모가 될 노드

        Returns:
            생성된 본
        """
        bone = self.bone.create_nub_bone(inBaseName, 2)
        bone.name = self.name.replace_name_part("Index", inBaseName, str(inIndex))
        bone.name = self.name.remove_name_part("Nub", bone.name)
        bone.transform = inTransformSource.transform
        bone.parent = inParent
        return bone

    def _assign_twist_rotation(self, inBone, inLocalRefTm, inLimb, inExpression: str, inWeight: float) -> None:
        """본에 트위스트 회전 스크립트 컨트롤러를 붙인다.

        Args:
            inBone: 대상 본
            inLocalRefTm: 기준 자세 행렬
            inLimb: 회전을 읽어 올 관절
            inExpression: 상부용/하부용 회전 표현식
            inWeight: 회전 리스트의 가중치
        """
        rotListController = self.const.assign_rot_list(inBone)
        rotController = rt.Rotation_Script()
        rotController.addConstant("localRefTm", inLocalRefTm)
        rotController.addNode("limb", inLimb)
        rotController.addNode("limbParent", inLimb.parent)
        rotController.setExpression(inExpression)
        rotController.update()

        rt.setPropertyController(rotListController, "Available", rotController)
        rotListController.delete(1)
        rotListController.setActive(rotListController.count)
        rotListController.weight[0] = inWeight

    # ------------------------------------------------------------------
    # 타입별 본체
    # ------------------------------------------------------------------

    def _create_upper_bones(self, inObj, inChild, inTwistNum: int) -> list:
        """상부(상완·대퇴부)의 트위스트 본들을 만든다.

        첫 본이 회전을 100% 받고, 중간 본들이 가중치를 나눠 받는다. 위치는 중간·마지막
        본만 부모-자식 사이를 보간한다.

        Args:
            inObj: 트위스트 본의 부모 객체
            inChild: 자식 객체
            inTwistNum: 생성할 본 개수

        Returns:
            list: 생성된 본들 (번호 순)
        """
        limb = inObj
        boneName = self._twist_bone_base_name(inObj)
        localRefTm = limb.transform * rt.inverse(limb.parent.transform)

        firstBone = self._create_indexed_bone(boneName, 1, limb, limb)
        self._assign_twist_rotation(
            firstBone, localRefTm, limb, self.upperTwistBoneExpression, 100.0
        )
        bones = [firstBone]

        if inTwistNum <= 1:
            return bones

        weightVal = 100.0 / (inTwistNum - 1)
        posWeightVal = 100.0 / inTwistNum

        lastBone = self._create_indexed_bone(boneName, inTwistNum, limb, limb)
        lastBonePosConst = self.const.assign_pos_const_multi(lastBone, [limb, inChild])
        lastBonePosConst.setWeight(1, 100.0 - (posWeightVal * (inTwistNum - 1)))
        lastBonePosConst.setWeight(2, posWeightVal * (inTwistNum - 1))

        for index in range(1, inTwistNum - 1):
            extraBone = self._create_indexed_bone(boneName, index + 1, limb, limb)
            extraBonePosConst = self.const.assign_pos_const_multi(extraBone, [limb, inChild])
            extraBonePosConst.setWeight(1, 100.0 - (posWeightVal * index))
            extraBonePosConst.setWeight(2, posWeightVal * index)
            self._assign_twist_rotation(
                extraBone,
                localRefTm,
                limb,
                self.upperTwistBoneExpression,
                weightVal * (inTwistNum - 1 - index),
            )
            bones.append(extraBone)

        bones.append(lastBone)
        return bones

    def _create_lower_bones(self, inObj, inChild, inTwistNum: int) -> list:
        """하부(전완·하퇴부)의 트위스트 본들을 만든다.

        회전을 읽어 오는 관절이 **자식**(`inChild`)이라는 점이 상부와 가장 크게 다르다.
        첫 본도 위치 제약을 받고, 마지막 본은 위치 제약 없이 부모에 붙는다.

        Args:
            inObj: 트위스트 본의 부모 객체
            inChild: 자식 객체. 회전의 출처다.
            inTwistNum: 생성할 본 개수

        Returns:
            list: 생성된 본들 (번호 순)
        """
        limb = inChild
        posWeightVal = 100.0 / inTwistNum
        boneName = self._twist_bone_base_name(inObj)

        firstBone = self._create_indexed_bone(boneName, 1, inObj, inObj)
        firstBonePosConst = self.const.assign_pos_const_multi(firstBone, [limb, inObj])
        firstBonePosConst.setWeight(1, posWeightVal * (inTwistNum - 1))
        firstBonePosConst.setWeight(2, 100.0 - (posWeightVal * (inTwistNum - 1)))

        localRefTm = limb.transform * rt.inverse(limb.parent.transform)
        self._assign_twist_rotation(
            firstBone, localRefTm, limb, self.lowerTwistBoneExpression, 100.0
        )
        bones = [firstBone]

        if inTwistNum <= 1:
            return bones

        weightVal = 100.0 / (inTwistNum - 1)

        lastBone = self._create_indexed_bone(boneName, inTwistNum, inObj, inObj)

        for index in range(1, inTwistNum - 1):
            extraBone = self._create_indexed_bone(boneName, index + 1, inObj, inObj)
            extraBonePosConst = self.const.assign_pos_const_multi(extraBone, [limb, inObj])
            extraBonePosConst.setWeight(1, 100.0 - (posWeightVal * (index + 1)))
            extraBonePosConst.setWeight(2, posWeightVal * (index + 1))
            self._assign_twist_rotation(
                extraBone,
                localRefTm,
                limb,
                self.lowerTwistBoneExpression,
                weightVal * (inTwistNum - 1 - index),
            )
            bones.append(extraBone)

        bones.append(lastBone)
        return bones

    #: 트위스트 타입 -> 본체 메서드 이름.
    _TWIST_MODES = {
        "Upper": "_create_upper_bones",
        "Lower": "_create_lower_bones",
    }

    # ------------------------------------------------------------------
    # 진입점
    # ------------------------------------------------------------------

    def create_bones(
        self, inObj, inChild, inTwistNum: int = 4, inTwistType: str = "Upper"
    ) -> Optional[BoneChain]:
        """트위스트 본 체인을 생성한다.

        Args:
            inObj: 트위스트 본의 부모 객체 (상완·전완·대퇴부·하퇴부)
            inChild: 자식 객체
            inTwistNum: 생성할 트위스트 본의 개수
            inTwistType: `"Upper"`(부모가 도는 쪽) 또는 `"Lower"`(자식이 도는 쪽)

        Returns:
            BoneChain | None: 생성된 트위스트 본 체인. 실패하면 None
        """
        if not self.validate_source_nodes(inObj, inChild):
            return None

        modeMethod = self._TWIST_MODES.get(inTwistType)
        if modeMethod is None:
            _get_logger().warning(
                f"TwistBone: 알 수 없는 트위스트 타입 {inTwistType!r} "
                f"(가능: {sorted(self._TWIST_MODES)})"
            )
            return None

        bones = getattr(self, modeMethod)(inObj, inChild, inTwistNum)

        self.tag_as_skin_bones(bones, [inObj, inChild])

        result = self.build_result(
            bones, [], [inObj, inChild], {"inTwistNum": inTwistNum, "inTwistType": inTwistType}
        )

        self.reset()

        return BoneChain.from_result(result)

    def create_upper_limb_bones(self, inObj, inChild, inTwistNum: int = 4) -> Optional[BoneChain]:
        """상부 트위스트 본을 생성한다. `create_bones(..., inTwistType="Upper")`와 같다.

        **과도기 별칭이다.** 툴이 아직 이 이름으로 부르고 있어 남겨 둔다
        (`PyJalMaxRiggingTool`의 `func_twist.py`). 툴이 `create_bones`로 옮기면
        (RiggingToolRefactor Phase 3) 이 메서드와 `create_lower_limb_bones`를 함께 삭제한다.
        사용처는 그 하나뿐이다.


        Args:
            inObj: 트위스트 본의 부모 객체
            inChild: 자식 객체
            inTwistNum: 생성할 트위스트 본의 개수

        Returns:
            BoneChain | None: 생성된 트위스트 본 체인
        """
        return self.create_bones(inObj, inChild, inTwistNum, "Upper")

    def create_lower_limb_bones(self, inObj, inChild, inTwistNum: int = 4) -> Optional[BoneChain]:
        """하부 트위스트 본을 생성한다. `create_bones(..., inTwistType="Lower")`와 같다.

        `create_upper_limb_bones`와 같은 과도기 별칭이다. 함께 삭제한다.


        Args:
            inObj: 트위스트 본의 부모 객체
            inChild: 자식 객체
            inTwistNum: 생성할 트위스트 본의 개수

        Returns:
            BoneChain | None: 생성된 트위스트 본 체인
        """
        return self.create_bones(inObj, inChild, inTwistNum, "Lower")
