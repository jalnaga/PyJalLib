#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""릭 파트 특성화 회귀 스위트 (Type C).

`pyjallib.max.rig`의 릭 파트가 **재구성 전과 같은 결과를 내는지**를 판정한다.
기준값은 `tests/fixtures/rig_parts_baseline.json`이고, 그것은 재구성 **전** 코드를
헤드리스 Biped 위에서 돌려 얻은 스냅샷이다(Phase 0 프로브, 두 번 독립 실행에서
51/51 재현 확인).

## 무엇을 대조하는가

파트마다 두 국면:

- `create`: 툴 기본 파라미터로 생성
- `modify`: 생성한 체인을 `create_bones_from_chain()`으로 재생성 (툴의 modify 경로)

노드마다 이름·부모 이름·클래스·컨트롤러 클래스·userProp을 본다. 핸들과 위치 수치는
보지 않는다 - 우연을 굳히면 무의미한 빨강이 난다.

## 왜 `jal.<attr>`가 아니라 `rig` 패키지에서 직접 만드는가

`Header`는 코어 서비스까지 전부 물고 오는 싱글톤이라, 실패했을 때 릭 파트 문제인지
헤더 배선 문제인지 가려지지 않는다. 이 스위트는 **릭 패키지만** 시험하고, `Header`의
속성 배선은 Type A(`tests/test_macro_symbols.py`)가 정적으로 대조한다.
서비스 인스턴스는 `Header`에서 빌려 와 프로덕션과 같은 구성을 쓴다.

## 아직 옮기지 않은 파트

`pyjallib.max.rig`에 클래스가 없으면 그 파트는 SKIP하고 사유를 남긴다. Phase 1이
끝나면 SKIP은 0이어야 하고, TC00-A가 그것을 단정한다.
"""

import json
import sys
from pathlib import Path

# pyjallib 소스 경로 선주입 + 배포본 선점 퍼지.
sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt  # noqa: E402
import pyjallib  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402
from pyjallib.max.header import get_pyjallibmaxheader  # noqa: E402
from pyjallib.max import rig  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
BASELINE_PATH = Path(__file__).parent.parent / "fixtures" / "rig_parts_baseline.json"

reporter = TestReporter("RigParts", LOG_DIR)

# 스냅샷에서 볼 축. baseline 픽스처를 만든 `tests/make_rig_baseline.py`와 같아야 한다.
NODE_KEYS = (
    "name",
    "parent",
    "class",
    "superClass",
    "transformController",
    "posController",
    "rotController",
    "scaleController",
    "userProps",
)

# ------------------------------------------------------------------
# 파트 표 - 프로브(`test_probe_rig_parts.py`)와 같은 픽스처·같은 순서.
# `params`는 툴 `func_<part>`의 기본값이고, 새 dict 파라미터 이름으로 적는다.
# `produces`는 뒤 파트가 소스로 쓰는 산출물의 논리 키다.
# ------------------------------------------------------------------
PART_TABLE = [
    {
        "key": "twistUpperArm",
        "cls": "TwistBone",
        "sources": ["lUpperArm", "lForeArm"],
        "params": {"inTwistNum": 4, "inTwistType": "Upper"},
        "produces": "lUpperArmTwist",
    },
    {
        "key": "twistLowerArm",
        "cls": "TwistBone",
        "sources": ["lForeArm", "lHand"],
        "params": {"inTwistNum": 4, "inTwistType": "Lower"},
    },
    {
        "key": "twistUpperLegL",
        "cls": "TwistBone",
        "sources": ["lThigh", "lCalf"],
        "params": {"inTwistNum": 4, "inTwistType": "Upper"},
        "produces": "lThighTwist",
    },
    {
        "key": "twistUpperLegR",
        "cls": "TwistBone",
        "sources": ["rThigh", "rCalf"],
        "params": {"inTwistNum": 4, "inTwistType": "Upper"},
        "produces": "rThighTwist",
    },
    {
        "key": "autoClavicle",
        "cls": "AutoClavicle",
        "sources": ["lClavicle", "lUpperArm"],
        "params": {"inLiftScale": 0.8},
        "produces": "lAutoClavicle",
    },
    {
        "key": "shoulder",
        "cls": "Shoulder",
        "sources": ["lClavicle", "lUpperArm", "lAutoClavicle", "lUpperArmTwist"],
        "params": {"inTwistWeight": 0.7},
        "produces": "lShoulder",
    },
    {
        "key": "chest",
        "cls": "Chest",
        "sources": ["spine", "neck", "lAutoClavicle", "lUpperArm"],
        "params": {
            "inSpineHeightScale": 0.33,
            "inSpinePushScale": 0.5,
            "inFrontWeight": 60.0,
            "inShoulderWeight": 40.0,
            "inChestMusclePushScale": 1.0,
            "inChestMuscleHeightScale": 0.15,
            "inShoulderPushScale": 0.25,
        },
    },
    {
        "key": "armpit",
        "cls": "Armpit",
        "sources": ["lShoulder", "spine", "neck"],
        "params": {"inSpineLengthScale": 0.67},
    },
    {
        "key": "elbow",
        "cls": "Elbow",
        "sources": ["lForeArm", "lUpperArm"],
        "params": {
            "inRotScale": 0.5,
            "inVolumeSize": 4.0,
            "inRotAxis": "Z",
            "inElbowTransAxis": "PosY",
            "inInnerElbowTransAxis": "NegY",
            "inElbowTransScale": 0.25,
            "inInnerElbowTransScale": 1.0,
        },
    },
    {
        "key": "wrist",
        "cls": "Wrist",
        "sources": ["lHand", "lForeArm"],
        "params": {
            "inRotScale": 0.5,
            "inVolumeSize": 4.0,
            "inFBRotAxis": "Y",
            "inIORotAxis": "Z",
            "inFBTransAxis": "Z",
            "inIOTransAxis": "Y",
            "inFBTransScale": 1.0,
            "inIOTransScale": 1.0,
        },
    },
    {
        "key": "knee",
        "cls": "KneeBone",
        "sources": ["lThigh", "lCalf", "lFoot"],
        "params": {
            "inLiftScale": 0.05,
            "inKneeVolumeSize": 5.0,
            "inKneePopScale": 0.1,
            "inKneeBackScale": 1.5,
        },
    },
    {
        "key": "ankle",
        "cls": "Ankle",
        "sources": ["lFoot", "lCalf"],
        "params": {
            "inRotScale": 0.5,
            "inVolumeSize": 4.0,
            "inRotAxis": "Z",
            "inAnkleTransAxis": "PosY",
            "inInnerAnkleTransAxis": "NegY",
            "inAnkleTransScale": 1.5,
            "inInnerAnkleTransScale": 1.0,
        },
    },
    {
        "key": "hip",
        "cls": "Hip",
        "sources": ["pelvis", "lThigh", "lThighTwist", "lCalf"],
        "params": {"inPushAmount": 5.0, "inPelvisWeight": 60.0, "inThighWeight": 40.0},
    },
    {
        "key": "inguinal",
        "cls": "Inguinal",
        "sources": ["lThighTwist", "pelvis", "lCalf"],
        "params": {
            "inRotScale": 0.5,
            "inVolumeSize": 6.0,
            "inFwdRotAxis": "Z",
            "inOutRotAxis": "Y",
            "inFwdTransAxis": "PosY",
            "inOutTransAxis": "PosZ",
            "inFwdTransScale": 2.0,
            "inOutTransScale": 2.0,
        },
    },
    {
        "key": "groin",
        "cls": "GroinBone",
        "sources": ["pelvis", "lThighTwist", "rThighTwist"],
        "params": {"inPelvisWeight": 40.0, "inThighWeight": 60.0},
    },
    {
        "key": "jacketPanel",
        "cls": "JacketPanel",
        "sources": ["lClavicle", "lUpperArm", "rClavicle", "rUpperArm", "spine", "neck"],
        "params": {
            "inWidthScale": 1.65,
            "inForwardScale": 0.5,
            "inBackwardScale": 0.5,
            "inHeightScale": 0.67,
            "inFrontCenterPushScale": 1.1,
            "inBackCenterPushScale": 1.1,
        },
    },
    {
        "key": "volumePreserve",
        "cls": "VolumeBone",
        "sources": ["lForeArm", "lUpperArm"],
        "params": {
            "inRotScale": 0.5,
            "inVolumeSize": 5.0,
            "inRotAxises": ["Z"],
            "inTransAxises": ["PosY"],
            "inTransScales": [1.0],
        },
    },
]

# `rt.biped.getNode`의 link 인덱스.
_ARM_LINKS = {"Clavicle": 1, "UpperArm": 2, "ForeArm": 3, "Hand": 4}
_LEG_LINKS = {"Thigh": 1, "Calf": 2, "Foot": 3}


# ------------------------------------------------------------------
# 픽스처
# ------------------------------------------------------------------


def build_biped_sources() -> dict:
    """헤드리스에서 Biped를 만들고 릭 파트가 쓰는 소스 본을 해석한다.

    Returns:
        dict: 논리 키 -> 노드
    """
    rt.resetMaxFile(rt.Name("noPrompt"))
    com = rt.biped.createNew(100.0, 100.0, rt.Point3(0.0, 0.0, 0.0))

    def _get(inKeyName, inLink):
        node = rt.biped.getNode(com, rt.Name(inKeyName), link=inLink)
        return node if rt.isValidNode(node) else None

    nodes = {}
    for sidePrefix, armKey in (("l", "lArm"), ("r", "rArm")):
        for partName, link in _ARM_LINKS.items():
            node = _get(armKey, link)
            if node is not None:
                nodes[sidePrefix + partName] = node
    for sidePrefix, legKey in (("l", "lLeg"), ("r", "rLeg")):
        for partName, link in _LEG_LINKS.items():
            node = _get(legKey, link)
            if node is not None:
                nodes[sidePrefix + partName] = node
    for logicalName, keyName in (("pelvis", "pelvis"), ("neck", "neck")):
        node = _get(keyName, 1)
        if node is not None:
            nodes[logicalName] = node
    spine = _get("spine", 1)
    if spine is not None:
        nodes["spine"] = spine
    return nodes


# ------------------------------------------------------------------
# 스냅샷
# ------------------------------------------------------------------


def _controller_class(inNode, inSubAnimName):
    """노드의 지정 서브애님 컨트롤러 클래스 이름을 돌려준다.

    Args:
        inNode: 대상 노드
        inSubAnimName: "Position" | "Rotation" | "Scale"

    Returns:
        str | None: 컨트롤러 클래스 이름. 접근에 실패하면 None
    """
    try:
        controller = rt.getPropertyController(inNode.controller, inSubAnimName)
        return None if controller is None else str(rt.classOf(controller))
    except Exception:
        return None


def snapshot_node(inNode) -> dict:
    """노드 하나의 특성화 스냅샷을 만든다.

    Args:
        inNode: 대상 노드

    Returns:
        dict: `NODE_KEYS`의 축만 담은 dict
    """
    if not rt.isValidNode(inNode):
        return {key: None for key in NODE_KEYS}

    parent = inNode.parent
    try:
        userProps = str(rt.getUserPropBuffer(inNode))
    except Exception:
        userProps = None

    return {
        "name": str(inNode.name),
        "parent": str(parent.name) if parent is not None else None,
        "class": str(rt.classOf(inNode)),
        "superClass": str(rt.superClassOf(inNode)),
        "transformController": str(rt.classOf(inNode.controller)),
        "posController": _controller_class(inNode, "Position"),
        "rotController": _controller_class(inNode, "Rotation"),
        "scaleController": _controller_class(inNode, "Scale"),
        "userProps": userProps,
    }


def snapshot_chain(inChain) -> dict:
    """BoneChain의 특성화 스냅샷을 만든다.

    Args:
        inChain: BoneChain 인스턴스

    Returns:
        dict: `bones`·`helpers`·`sourceBones`
    """
    return {
        "bones": [snapshot_node(item) for item in inChain.bones],
        "helpers": [snapshot_node(item) for item in inChain.helpers],
        "sourceBones": [
            str(item.name) if rt.isValidNode(item) else None for item in inChain.sourceBones
        ],
    }


def describe_difference(inExpected: dict, inActual: dict) -> str:
    """두 스냅샷의 첫 차이들을 사람이 읽을 수 있게 적는다.

    Args:
        inExpected: baseline 스냅샷
        inActual: 이번 실행의 스냅샷

    Returns:
        str: 차이 설명. 같으면 빈 문자열
    """
    if inExpected == inActual:
        return ""

    lines = []
    for group in ("bones", "helpers"):
        expectedNodes = inExpected.get(group) or []
        actualNodes = inActual.get(group) or []
        if len(expectedNodes) != len(actualNodes):
            lines.append(f"{group} 개수: 기대 {len(expectedNodes)}, 실제 {len(actualNodes)}")
        for index, (expectedNode, actualNode) in enumerate(zip(expectedNodes, actualNodes)):
            for key in NODE_KEYS:
                if expectedNode.get(key) != actualNode.get(key):
                    lines.append(
                        f"{group}[{index}].{key}: "
                        f"기대 {expectedNode.get(key)!r}, 실제 {actualNode.get(key)!r}"
                    )
    if inExpected.get("sourceBones") != inActual.get("sourceBones"):
        lines.append(
            f"sourceBones: 기대 {inExpected.get('sourceBones')}, 실제 {inActual.get('sourceBones')}"
        )
    return " | ".join(lines[:8])


# ------------------------------------------------------------------
# TC00: 전제
# ------------------------------------------------------------------

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

_baselineExists = BASELINE_PATH.exists()
reporter.assert_test(
    _baselineExists,
    "TC00-B baseline 픽스처가 있는가",
    f"경로={BASELINE_PATH}",
)

BASELINE = json.loads(BASELINE_PATH.read_text(encoding="utf-8")) if _baselineExists else {}

_missingClasses = [spec["key"] for spec in PART_TABLE if not hasattr(rig, spec["cls"])]
reporter.assert_test(
    not _missingClasses,
    f"TC00-A 표의 파트 클래스가 rig 패키지에 전부 있는가 (미구현 {len(_missingClasses)})",
    f"미구현: {_missingClasses}",
)

jal = get_pyjallibmaxheader()

#: 릭 파트에 주입할 서비스. 프로덕션(`Header`)과 같은 인스턴스를 빌려 쓴다.
SERVICES = (jal.name, jal.anim, jal.helper, jal.bone, jal.constraint)

#: 추가 서비스가 필요한 파트. 클래스 이름 -> 뒤에 붙일 서비스 튜플.
EXTRA_SERVICES = {
    "TwistBone": (jal.bip,),
    "AutoClavicle": (jal.bip,),
    "Shoulder": (jal.bip,),
    "Armpit": (jal.align,),
    "Chest": (jal.align,),
    "JacketPanel": (jal.align,),
    "KneeBone": (jal.volumeBone,),
}


def make_part(inClassName):
    """릭 파트 인스턴스를 만든다.

    Args:
        inClassName: `pyjallib.max.rig`의 클래스 이름

    Returns:
        릭 파트 인스턴스
    """
    partClass = getattr(rig, inClassName)
    return partClass(*SERVICES, *EXTRA_SERVICES.get(inClassName, ()))


def pick_produced(inChain):
    """파트 산출 체인에서 후속 파트가 소스로 쓸 본을 고른다.

    Args:
        inChain: 생성된 BoneChain

    Returns:
        첫 유효 본. 없으면 None
    """
    for item in inChain.bones:
        if rt.isValidNode(item):
            return item
    return None


# ------------------------------------------------------------------
# TC01~: 파트별 create / modify 대조
# ------------------------------------------------------------------


def run_tests():
    """14 파트(twist 4변형 포함)를 baseline과 대조한다."""
    sources = build_biped_sources()
    ctx = dict(sources)
    chains = {}
    parts = {}

    # --- Pass A: 생성 + create 대조 ---
    for spec in PART_TABLE:
        key = spec["key"]
        label = f"create {key}"

        if not hasattr(rig, spec["cls"]):
            # 아직 옮기지 않은 파트. TC00-A가 이미 미구현 목록으로 실패를 내므로
            # 여기서 또 실패를 세지 않는다(같은 사실이 TC 수만 부풀린다).
            continue

        missing = [name for name in spec["sources"] if name not in ctx]
        if missing:
            reporter.error(f"TC create/{key}", f"소스 본 미해석: {missing}")
            continue

        try:
            part = make_part(spec["cls"])
            parts[key] = part
            chain = part.create_bones(*[ctx[name] for name in spec["sources"]], **spec["params"])
        except Exception as error:
            reporter.error(f"TC create/{key}", f"{label} 중 예외: {error}")
            continue

        if chain is None:
            reporter.assert_test(False, f"TC create/{key}", "create_bones가 None을 반환했다")
            continue

        chains[key] = chain
        if spec.get("produces"):
            produced = pick_produced(chain)
            if produced is not None:
                ctx[spec["produces"]] = produced

        expected = (BASELINE.get(key) or {}).get("create")
        actual = snapshot_chain(chain)
        if expected is None:
            reporter.error(f"TC create/{key}", "baseline에 create 스냅샷이 없다")
            continue
        reporter.assert_test(
            expected == actual,
            f"TC create/{key} 스냅샷이 baseline과 같은가",
            describe_difference(expected, actual),
        )

    # --- Pass B: 재생성 + modify 대조 (역순 - 의존하는 쪽이 먼저 끝난다) ---
    for spec in reversed(PART_TABLE):
        key = spec["key"]
        chain = chains.get(key)
        if chain is None:
            continue

        try:
            regenerated = parts[key].create_bones_from_chain(chain)
        except Exception as error:
            reporter.error(f"TC modify/{key}", f"재생성 중 예외: {error}")
            continue

        if regenerated is None:
            reporter.assert_test(
                False, f"TC modify/{key}", "create_bones_from_chain이 None을 반환했다"
            )
            continue

        expected = (BASELINE.get(key) or {}).get("modify")
        actual = snapshot_chain(regenerated)
        if expected is None:
            reporter.error(f"TC modify/{key}", "baseline에 modify 스냅샷이 없다")
            continue
        reporter.assert_test(
            expected == actual,
            f"TC modify/{key} 스냅샷이 baseline과 같은가",
            describe_difference(expected, actual),
        )

        # 삭제까지 확인하고 씬에서 치운다.
        deleted = regenerated.delete()
        remaining = sum(1 for item in regenerated.bones if rt.isValidNode(item))
        reporter.assert_test(
            deleted and remaining == 0,
            f"TC delete/{key} 삭제 후 잔여 본이 없는가",
            f"delete={deleted}, 잔여={remaining}",
        )


if _baselineExists:
    run_tests()

reporter.summary()
reporter.close()
