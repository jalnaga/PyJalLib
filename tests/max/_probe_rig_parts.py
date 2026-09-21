#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""릭 파트 계열 특성화 프로브 (Phase 0 / RiggingToolRefactor).

> **이 스크립트는 재구성 *전* API를 겨냥한다.** 파트 표가 `create_bone`(단수)과
> positional 파라미터를 쓰는데, 재구성 후에는 진입점이 `create_bones(**params)` 하나로
> 통일됐다. 그래서 **현행 코드에서는 돌지 않는 것이 정상**이고, 러너의 `TEST_SCRIPTS`에
> 등록하지 않는다(파일명의 `_` 접두가 그 표시다 - `max/max_test_pattern.md`).
>
> 남겨 두는 이유는 하나다 - `tests/fixtures/rig_parts_baseline.json`이 **어떻게**
> 만들어졌는지가 이 파일에 있다. 재캡처가 필요하면 재구성 전 체크아웃(master의 detached
> 워크트리)에서 이 스크립트를 돌리고 `tests/make_rig_baseline.py`로 굳힌다.
>
> **살아 있는 회귀 스위트는 `tests/max/test_rig_parts.py`다.**

`pyjallib.max`의 릭 파트 14종은 자동 테스트가 0건이었다. 재구성 전에 **현행 동작을
스냅샷으로 굳혀** 리팩토링의 안전망으로 쓴다. 3dsmaxbatch 왕복이 비싸므로
(`max/max_test_pattern.md` §프로브 설계 4원칙) P1~P4를 한 실행에 몰아 넣는다.

섹션:
    P1  헤드리스에서 `rt.biped.createNew`로 Biped를 만들고 소스 본을 해석할 수 있는가
    P1B `create_skin_bone_from_bip`이 헤드리스에서 도는가 (대체 픽스처 후보)
    P2  14 파트를 툴 기본 파라미터로 생성하고 스냅샷을 찍는다  <- 특성화 baseline
    P3  재생성(modify)과 삭제가 멱등한가. 툴 경로와 직접 경로를 **따로** 잰다
    P4  `rt.messageBox`가 헤드리스에서 어떻게 동작하는가

결과는 `tests/logs/probe_rig_parts.json`에 **섹션마다 즉시** 기록한다. P4가 블로킹해도
앞 섹션이 살아남고, 실패한 섹션만 골라 재실행할 수 있다.

실행:
    uv run python tests/run_max_tests.py test_probe_rig_parts.py
"""

import json
import sys
import traceback
from pathlib import Path

# pyjallib 소스 경로 선주입 + 배포본 선점 퍼지.
sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt  # noqa: E402
import pyjallib  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402
from pyjallib.max.header import get_pyjallibmaxheader  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = LOG_DIR / "probe_rig_parts.json"

reporter = TestReporter("ProbeRigParts", LOG_DIR)

# 섹션별 결과. 매 섹션 종료 시 디스크에 쓴다.
RESULT = {
    "loadedFrom": getattr(pyjallib, "__file__", None),
    "P1": {},
    "P1B": {},
    "P2": {},
    "P3": {},
    "P4": {},
}


def _flush():
    """지금까지의 결과를 JSON으로 덮어쓴다.

    섹션이 블로킹·크래시로 죽어도 앞 섹션 결과는 디스크에 남는다.
    """
    RESULT_PATH.write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _try(inLabel, inFunc):
    """함수를 실행하고 성공/실패를 함께 기록한다.

    실패도 정보다 - 예외를 삼키지 않고 문자열로 남겨 한 번의 Max 실행에서
    최대한 많은 판별을 끝낸다.

    Args:
        inLabel: 기록용 라벨
        inFunc: 인자 없는 호출 가능 객체

    Returns:
        dict: `{"ok": bool, "value": Any, "error": str | None}`
    """
    try:
        return {"ok": True, "value": inFunc(), "error": None}
    except Exception:
        return {"ok": False, "value": None, "error": traceback.format_exc(limit=6)}


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _scene_node_signature() -> dict:
    """씬 전체의 노드 수와 이름별 개수를 찍는다.

    재생성 전후로 이 값이 달라지면 이름 기반 수집이 노드를 놓쳤다는 뜻이다.

    Returns:
        dict: `total`(노드 수)과 `duplicated`(2개 이상인 이름 -> 개수)
    """
    counts = {}
    for item in rt.objects:
        name = str(item.name)
        counts[name] = counts.get(name, 0) + 1
    return {
        "total": sum(counts.values()),
        "duplicated": {name: count for name, count in counts.items() if count > 1},
    }


# ============================================================
# 스냅샷 - R2에 따라 이름·부모·클래스·컨트롤러·userProp만 담는다.
# 핸들과 위치 수치는 넣지 않는다(우연을 굳혀 무의미한 빨강을 만든다).
# ============================================================


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
        if controller is None:
            return None
        return str(rt.classOf(controller))
    except Exception:
        return None


def _snapshot_node(inNode):
    """노드 하나의 특성화 스냅샷을 만든다.

    Args:
        inNode: 대상 노드

    Returns:
        dict: 이름·부모 이름·클래스·컨트롤러 클래스·userProp 버퍼
    """
    if not rt.isValidNode(inNode):
        return {"name": None, "valid": False}

    parent = inNode.parent
    snapshot = {
        "name": str(inNode.name),
        "valid": True,
        "parent": str(parent.name) if parent is not None else None,
        "class": str(rt.classOf(inNode)),
        "superClass": str(rt.superClassOf(inNode)),
        "transformController": str(rt.classOf(inNode.controller)),
        "posController": _controller_class(inNode, "Position"),
        "rotController": _controller_class(inNode, "Rotation"),
        "scaleController": _controller_class(inNode, "Scale"),
    }
    try:
        snapshot["userProps"] = str(rt.getUserPropBuffer(inNode))
    except Exception:
        snapshot["userProps"] = None
    return snapshot


def _jsonable_parameter(inValue):
    """`BoneChain.parameters` 항목을 JSON으로 담을 수 있게 만든다.

    Args:
        inValue: 파라미터 값

    Returns:
        float | str: 수치는 그대로, 그 외는 문자열
    """
    if isinstance(inValue, bool):
        return inValue
    if isinstance(inValue, (int, float)):
        return inValue
    return str(inValue)


def _snapshot_chain(inChain):
    """BoneChain 전체의 특성화 스냅샷을 만든다.

    Args:
        inChain: BoneChain 인스턴스 또는 그 외 반환값

    Returns:
        dict: 본·헬퍼 스냅샷, 소스본 이름, 파라미터
    """
    if inChain is None:
        return {"chain": None, "returned": "None"}
    if inChain is False:
        return {"chain": None, "returned": "False"}
    if not hasattr(inChain, "bones"):
        return {"chain": None, "returned": str(type(inChain))}

    return {
        "returned": "BoneChain",
        "bones": [_snapshot_node(item) for item in inChain.bones],
        "helpers": [_snapshot_node(item) for item in inChain.helpers],
        "sourceBones": [
            str(item.name) if rt.isValidNode(item) else None
            for item in inChain.sourceBones
        ],
        "parameters": [_jsonable_parameter(item) for item in inChain.parameters],
    }


# ============================================================
# TC00: 로드 출처
# ============================================================
reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

jal = get_pyjallibmaxheader()


# ============================================================
# P1: 헤드리스 Biped 생성 + 소스 본 해석
# ============================================================

# `rt.biped.getNode`의 link 인덱스. 이름 매칭보다 안정적이다.
_ARM_LINKS = {"clavicle": 1, "upperArm": 2, "foreArm": 3, "hand": 4}
_LEG_LINKS = {"thigh": 1, "calf": 2, "foot": 3, "toe": 4}


def _resolve_biped_nodes(inCom):
    """Biped COM에서 릭 파트가 요구하는 소스 본들을 해석한다.

    Args:
        inCom: `rt.biped.createNew`가 돌려준 Biped 컨트롤 노드

    Returns:
        dict: 논리 키 -> 노드. 해석에 실패한 키는 담지 않는다.
    """
    nodes = {}

    def _get(inKeyName, inLink):
        try:
            node = rt.biped.getNode(inCom, rt.Name(inKeyName), link=inLink)
            return node if rt.isValidNode(node) else None
        except Exception:
            return None

    for side, armKey in (("l", "lArm"), ("r", "rArm")):
        for partName, link in _ARM_LINKS.items():
            node = _get(armKey, link)
            if node is not None:
                nodes[side + partName[0].upper() + partName[1:]] = node

    for side, legKey in (("l", "lLeg"), ("r", "rLeg")):
        for partName, link in _LEG_LINKS.items():
            node = _get(legKey, link)
            if node is not None:
                nodes[side + partName[0].upper() + partName[1:]] = node

    for logicalName, keyName in (("pelvis", "pelvis"), ("neck", "neck"), ("head", "head")):
        node = _get(keyName, 1)
        if node is not None:
            nodes[logicalName] = node

    spine = _get("spine", 1)
    if spine is not None:
        nodes["spine"] = spine
    spineTop = _get("spine", 4) or _get("spine", 3) or _get("spine", 2) or spine
    if spineTop is not None:
        nodes["spineTop"] = spineTop

    return nodes


def _build_biped():
    """헤드리스에서 Biped를 새로 만들고 소스 본을 해석한다.

    Returns:
        tuple[Any, dict]: (COM 노드, 논리 키 -> 노드 매핑)
    """
    _reset_scene()
    com = rt.biped.createNew(100.0, 100.0, rt.Point3(0.0, 0.0, 0.0))
    return com, _resolve_biped_nodes(com)


_p1 = _try("P1 biped 생성", _build_biped)
RESULT["P1"]["created"] = _p1["ok"]
RESULT["P1"]["error"] = _p1["error"]

BIPED_COM = None
SRC = {}
if _p1["ok"] and _p1["value"] is not None:
    BIPED_COM, SRC = _p1["value"]
    RESULT["P1"]["comName"] = str(BIPED_COM.name) if rt.isValidNode(BIPED_COM) else None
    RESULT["P1"]["resolved"] = {key: str(node.name) for key, node in SRC.items()}
    RESULT["P1"]["sceneNodeNames"] = sorted(str(item.name) for item in rt.objects)
    RESULT["P1"]["filteringChar"] = _try(
        "filtering char",
        lambda: jal.name.get_filtering_char(SRC["lUpperArm"].name) if "lUpperArm" in SRC else None,
    )["value"]

reporter.assert_test(
    _p1["ok"] and bool(SRC),
    "P1 헤드리스 Biped 생성 + 소스 본 해석",
    f"error={_p1['error']}, resolved={len(SRC)}",
)
_flush()


# ============================================================
# P1B: 스킨 본 생성 경로가 헤드리스에서 도는가 (대체 픽스처 후보)
# ============================================================
def _probe_skin_bones():
    """Biped에서 스킨 본을 뽑아 본다.

    Returns:
        dict: 생성된 스킨 본 개수와 앞 10개 이름
    """
    com, _ = _build_biped()
    bipNodes = jal.bip.get_nodes(com)
    skinBones = jal.bone.create_skin_bone_from_bip(
        bipNodes, inSkipNub=True, inMesh=False, inLink=True
    )
    names = [str(item.name) for item in skinBones] if skinBones else []
    return {"count": len(names), "sample": names[:10]}


_p1b = _try("P1B 스킨 본 생성", _probe_skin_bones)
RESULT["P1B"] = {"ok": _p1b["ok"], "value": _p1b["value"], "error": _p1b["error"]}
reporter.assert_test(
    _p1b["ok"],
    "P1B create_skin_bone_from_bip 헤드리스 동작",
    f"error={_p1b['error']}",
)
_flush()


# ============================================================
# P2/P3: 14 파트 생성 - 툴(func_*)의 기본 파라미터를 그대로 쓴다.
# ============================================================

# 파트 표. `sources`는 논리 키(SRC 또는 앞 파트가 만든 산출물)를 가리킨다.
# `args`는 툴 func_<part>의 기본값 그대로이고, `modifyParams`는 툴
# modify_chain이 `bone_chain.parameters`에 다시 써 넣는 리스트다
# (툴 경로에서는 이 값이 직접 경로의 파라미터 레이아웃을 덮어쓴다).
PART_TABLE = [
    {
        "key": "twistUpperArm",
        "attr": "twistBone",
        "method": "create_upper_limb_bones",
        "sources": ["lUpperArm", "lForeArm"],
        "args": [4],
        "modifyParams": [4, "Upper"],
        "produces": "lUpperArmTwist",
    },
    {
        "key": "twistLowerArm",
        "attr": "twistBone",
        "method": "create_lower_limb_bones",
        "sources": ["lForeArm", "lHand"],
        "args": [4],
        "modifyParams": [4, "Lower"],
    },
    {
        "key": "twistUpperLegL",
        "attr": "twistBone",
        "method": "create_upper_limb_bones",
        "sources": ["lThigh", "lCalf"],
        "args": [4],
        "modifyParams": [4, "Upper"],
        "produces": "lThighTwist",
    },
    {
        "key": "twistUpperLegR",
        "attr": "twistBone",
        "method": "create_upper_limb_bones",
        "sources": ["rThigh", "rCalf"],
        "args": [4],
        "modifyParams": [4, "Upper"],
        "produces": "rThighTwist",
    },
    {
        "key": "autoClavicle",
        "attr": "autoClavicle",
        "method": "create_bones",
        "sources": ["lClavicle", "lUpperArm"],
        "args": [0.8],
        "modifyParams": [0.8],
        "produces": "lAutoClavicle",
    },
    {
        "key": "shoulder",
        "attr": "shoulder",
        "method": "create_bones",
        "sources": ["lClavicle", "lUpperArm", "lAutoClavicle", "lUpperArmTwist"],
        "args": [0.7],
        "modifyParams": [0.7],
        "produces": "lShoulder",
    },
    {
        "key": "chest",
        "attr": "chest",
        "method": "create_bones",
        "sources": ["spine", "neck", "lAutoClavicle", "lUpperArm"],
        "args": [0.33, 0.5, 60.0, 40.0, 1.0, 0.15, 0.25],
        "modifyParams": [0.33, 0.5, 60.0, 40.0, 1.0, 0.15, 0.25],
    },
    {
        "key": "armpit",
        "attr": "armpit",
        "method": "create_bones",
        "sources": ["lShoulder", "spine", "neck"],
        "args": [0.67],
        "modifyParams": [0.67],
    },
    {
        "key": "elbow",
        "attr": "elbow",
        "method": "create_bones",
        "sources": ["lForeArm", "lUpperArm"],
        "args": [0.5, 4.0, "Z", "PosY", "NegY", 0.25, 1.0],
        "modifyParams": [0.5, 4.0, "Z", "PosY", "NegY", 0.25, 1.0],
    },
    {
        "key": "wrist",
        "attr": "wrist",
        "method": "create_bones",
        "sources": ["lHand", "lForeArm"],
        "args": [0.5, 4.0, "Y", "Z", "Z", "Y", 1.0, 1.0],
        "modifyParams": [0.5, 4.0, "Y", "Z", "Z", "Y", 1.0, 1.0],
    },
    {
        "key": "knee",
        "attr": "kneeBone",
        "method": "create_bone",
        "sources": ["lThigh", "lCalf", "lFoot"],
        "args": [0.05, 5.0, 0.1, 1.5],
        "modifyParams": [0.05, 5.0, 0.1, 1.5],
    },
    {
        "key": "ankle",
        "attr": "ankle",
        "method": "create_bones",
        "sources": ["lFoot", "lCalf"],
        "args": [0.5, 4.0, "Z", "PosY", "NegY", 1.5, 1.0],
        "modifyParams": [0.5, 4.0, "Z", "PosY", "NegY", 1.5, 1.0],
    },
    {
        "key": "hip",
        "attr": "hip",
        "method": "create_bone",
        "sources": ["pelvis", "lThigh", "lThighTwist", "lCalf"],
        "args": [5.0, 60.0, 40.0],
        "modifyParams": [5.0, 60.0, 40.0],
    },
    {
        "key": "inguinal",
        "attr": "inguinal",
        "method": "create_bones",
        "sources": ["lThighTwist", "pelvis", "lCalf"],
        "args": [0.5, 6.0, "Z", "Y", "PosY", "PosZ", 2.0, 2.0],
        "modifyParams": [0.5, 6.0, "Z", "Y", "PosY", "PosZ", 2.0, 2.0],
    },
    {
        "key": "groin",
        "attr": "groinBone",
        "method": "create_bone",
        "sources": ["pelvis", "lThighTwist", "rThighTwist"],
        "args": [],
        "kwargs": {"inPelvisWeight": 40.0, "inThighWeight": 60.0},
        "modifyParams": [40.0, 60.0],
    },
    {
        "key": "jacketPanel",
        "attr": "jacketPanel",
        "method": "create_bones",
        "sources": ["lClavicle", "lUpperArm", "rClavicle", "rUpperArm", "spine", "neck"],
        "args": [1.65, 0.5, 0.5, 0.67, 1.1, 1.1],
        "modifyParams": [1.65, 0.5, 0.5, 0.67, 1.1, 1.1],
    },
    {
        "key": "volumePreserve",
        "attr": "volumeBone",
        "method": "create_bones",
        "sources": ["lForeArm", "lUpperArm"],
        "args": [0.5, 5.0, ["Z"], ["PosY"], [1.0]],
        "modifyParams": [0.5, 5.0, "Z", "PosY", 1.0],
    },
]


def _pick_produced(inChain):
    """파트 산출 체인에서 후속 파트가 소스로 쓸 본을 고른다.

    툴에서는 리거가 화면에서 고르지만, 프로브는 체인의 첫 본을 쓴다.

    Args:
        inChain: 생성된 BoneChain

    Returns:
        Any | None: 첫 유효 본. 없으면 None
    """
    if inChain is None or inChain is False or not hasattr(inChain, "bones"):
        return None
    for item in inChain.bones:
        if rt.isValidNode(item):
            return item
    return None


def _run_part_pass():
    """14 파트를 생성(P2)한 뒤 재생성·삭제(P3)를 잰다.

    **패스를 둘로 나눈다.** 파트 사이에 의존이 있어서다 - twist -> hip/inguinal/groin,
    autoClavicle -> shoulder/chest, shoulder -> armpit. 1차 실행에서 생성 직후 삭제까지
    한 번에 돌렸더니, twist·autoClavicle 체인을 지운 뒤 그것을 소스로 쓰는 5개 파트가
    `False`를 받았다(프로브 자신의 설계 결함이지 라이브러리 결함이 아니다).

    - **Pass A (P2):** 의존 순서대로 전부 생성만 하고 스냅샷을 찍는다. 삭제하지 않는다.
    - **Pass B (P3):** 같은 씬에서 **역순으로** 재생성·삭제를 잰다. 의존하는 쪽이 먼저
      끝나므로, 나중에 의존 대상이 지워져도 이미 측정이 끝나 있다.

    Pass B는 파트마다 다섯 단계를 밟는다. 2차 실행에서 직접 경로가 던진 예외가 체인을
    비워 버려 뒤이은 툴 경로가 "빈 체인이라 None"을 측정했기 때문에, **측정마다 깨끗한
    체인에서 시작**하도록 재생성을 사이에 끼웠다.

    1. 직접 경로 재생성 (진단 - 파라미터 레이아웃 계약)
    2. 잔여 정리
    3. 같은 인자로 재생성 (create 자체의 멱등성)
    4. 툴 경로 재생성 (**프로덕션 계약. modify의 특성화 기준값**)
    5. 삭제
    """
    _, src = _build_biped()
    ctx = dict(src)
    chains = {}
    calls = {}

    # --- Pass A: 생성만 ---
    for spec in PART_TABLE:
        key = spec["key"]
        entry = {"sources": spec["sources"]}

        missing = [name for name in spec["sources"] if name not in ctx]
        if missing:
            entry["skipped"] = f"소스 본 미해석: {missing}"
            RESULT["P2"][key] = entry
            _flush()
            continue

        service = getattr(jal, spec["attr"])
        method = getattr(service, spec["method"])
        callArgs = [ctx[name] for name in spec["sources"]] + list(spec.get("args", []))
        callKwargs = dict(spec.get("kwargs", {}))
        calls[key] = (service, method, callArgs, callKwargs)

        created = _try(f"{key} create", lambda: method(*callArgs, **callKwargs))
        entry["create"] = {
            "ok": created["ok"],
            "error": created["error"],
            "snapshot": _snapshot_chain(created["value"]) if created["ok"] else None,
        }
        RESULT["P2"][key] = entry
        _flush()

        chain = created["value"] if created["ok"] else None
        if chain is not None and chain is not False and hasattr(chain, "bones"):
            chains[key] = chain
            if spec.get("produces"):
                produced = _pick_produced(chain)
                if produced is not None:
                    ctx[spec["produces"]] = produced

    # --- Pass B: 재생성·삭제 (역순) ---
    for spec in reversed(PART_TABLE):
        key = spec["key"]
        chain = chains.get(key)
        p3 = {}

        if chain is None:
            p3["skipped"] = "생성 실패로 재생성을 재지 않음"
            RESULT["P3"][key] = p3
            _flush()
            continue

        service, method, callArgs, callKwargs = calls[key]
        hasRegen = hasattr(service, "create_bones_from_chain")

        # **순서가 곧 측정의 타당성이다.** 프로덕션 경로(툴 경로)를 맨 먼저 잰다.
        #
        # 3차 실행은 진단(직접 경로)을 먼저 돌렸는데, elbow·wrist·ankle에서 그것이
        # `Unable to convert: "NegY" to type: Float`로 **중간에 죽으면서 씬에 반쯤
        # 만든 노드를 남겼다.** wrist는 볼륨 본 넷이 이름이 같아(D-2) 뒤이은 툴 경로의
        # 이름 기반 수집이 그 잔여를 집었고, 결과적으로 `parent=None`인 본이 baseline에
        # 굳었다. 구 구현을 단독으로 돌리면 그런 본은 나오지 않는다(2026-09-21
        # `_probe_wrist_parent.py`로 master 체크아웃에서 확증).
        #
        # 그래서 진단은 **맨 뒤로** 보내고, 그마저 버릴 체인에서만 돌린다.
        p3["parametersAfterCreate"] = [_jsonable_parameter(item) for item in chain.parameters]

        # --- ① 툴 경로 (프로덕션 계약 - 이것이 modify의 특성화 기준값이다) ---
        # 씬 노드 수를 앞뒤로 찍는다. 재생성은 지운 만큼 다시 만들므로 수가 같아야
        # 한다. 늘거나 줄면 이름 기반 수집이 무언가를 놓쳤다는 뜻이고, 그 잔여가
        # 다음 수집에 섞여 들어간다(D-2 중복 이름의 귀결).
        p3["sceneNodesBeforeModify"] = _scene_node_signature()

        target = chain
        if hasRegen:
            chain.parameters = list(spec["modifyParams"])
            toolPath = _try(f"{key} tool regen", lambda: service.create_bones_from_chain(chain))
            p3["toolPath"] = {
                "ok": toolPath["ok"],
                "error": toolPath["error"],
                "snapshot": _snapshot_chain(toolPath["value"]) if toolPath["ok"] else None,
            }
            if toolPath["ok"] and toolPath["value"] is not None and hasattr(toolPath["value"], "bones"):
                target = toolPath["value"]

        p3["sceneNodesAfterModify"] = _scene_node_signature()

        # --- ② 삭제 ---
        deleted = _try(f"{key} delete", lambda: target.delete())
        p3["delete"] = {
            "ok": deleted["ok"],
            "returned": _jsonable_parameter(deleted["value"]),
            "error": deleted["error"],
            "remainingValidBones": sum(1 for item in target.bones if rt.isValidNode(item)),
        }

        # --- ③ 직접 경로 (진단, 버릴 체인에서만) ---
        # `parameters`를 생성 시점 그대로 둔 채 재생성하면 어떻게 되는가.
        # 이것이 D-1(elbow·wrist·ankle의 레이아웃 어긋남)을 드러내는 축이다.
        # 여기서 무엇이 깨지든 위 ①·②의 기준값에 닿지 않는다 - 이미 측정이 끝났고
        # 이 단계의 산출물은 곧바로 버린다.
        if hasRegen:
            probeChain = _try(f"{key} recreate for direct probe", lambda: method(*callArgs, **callKwargs))
            fresh = probeChain["value"] if probeChain["ok"] else None
            if fresh is not None and fresh is not False and hasattr(fresh, "bones"):
                p3["recreate"] = {"ok": True, "snapshot": _snapshot_chain(fresh)}
                direct = _try(f"{key} direct regen", lambda: service.create_bones_from_chain(fresh))
                p3["direct"] = {
                    "ok": direct["ok"],
                    "error": direct["error"],
                    "snapshot": _snapshot_chain(direct["value"]) if direct["ok"] else None,
                }
                # 진단이 남긴 것을 이름에 기대지 않고 치운다. 실패했으면 씬에 반쯤
                # 만든 노드가 남을 수 있으나, 이 파트의 측정은 이미 끝났고 뒤 파트는
                # 역순이라 자기 소스만 본다.
                for candidate in (direct["value"], fresh):
                    if candidate is not None and candidate is not False and hasattr(candidate, "delete"):
                        _try(f"{key} direct cleanup", lambda: candidate.delete())
            else:
                p3["recreate"] = {"ok": False, "error": probeChain["error"]}

        RESULT["P3"][key] = p3
        _flush()


_p2 = _try("P2/P3 14 파트", _run_part_pass)
RESULT["P2"]["_runError"] = _p2["error"]
_flush()

_createdOk = sum(
    1
    for key, entry in RESULT["P2"].items()
    if isinstance(entry, dict) and entry.get("create", {}).get("ok")
)
reporter.assert_test(
    _p2["ok"],
    "P2 14 파트 생성 패스가 끝까지 돌았는가",
    f"error={_p2['error']}",
)
reporter.assert_test(
    _createdOk == len(PART_TABLE),
    f"P2 14 파트 전건 생성 (성공 {_createdOk}/{len(PART_TABLE)})",
    "생성 실패 파트는 결과 JSON의 create.error 참조",
)

# 툴 경로(modify)는 프로덕션 계약이다. 직접 경로와 달리 전건 성공해야 한다.
_toolOk = sum(
    1
    for entry in RESULT["P3"].values()
    if isinstance(entry, dict)
    and (entry.get("toolPath") or {}).get("ok")
    and ((entry.get("toolPath") or {}).get("snapshot") or {}).get("returned") == "BoneChain"
)
reporter.assert_test(
    _toolOk == len(PART_TABLE),
    f"P3 툴 경로 modify 전건 성공 (성공 {_toolOk}/{len(PART_TABLE)})",
    "툴 경로는 func_<part>.modify_chain이 parameters를 덮어쓴 뒤 재생성하는 프로덕션 경로다",
)

_deleteOk = sum(
    1
    for entry in RESULT["P3"].values()
    if isinstance(entry, dict) and (entry.get("delete") or {}).get("remainingValidBones") == 0
)
reporter.assert_test(
    _deleteOk == len(PART_TABLE),
    f"P3 삭제 후 잔여 본 0 (성공 {_deleteOk}/{len(PART_TABLE)})",
    "삭제가 씬에서 본을 실제로 없앴는지",
)
_flush()


# ============================================================
# P4: rt.messageBox 헤드리스 동작 - 블로킹 위험이 있어 맨 뒤에 둔다.
# ============================================================
_p4 = _try(
    "P4 messageBox",
    lambda: str(rt.messageBox("probe: headless messageBox", beep=False)),
)
RESULT["P4"] = {"ok": _p4["ok"], "returned": _p4["value"], "error": _p4["error"]}
reporter.assert_test(
    _p4["ok"],
    "P4 rt.messageBox가 헤드리스에서 반환되는가(블로킹하지 않는가)",
    f"error={_p4['error']}",
)
_flush()


reporter.summary()
reporter.close()
