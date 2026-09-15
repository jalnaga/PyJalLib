#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skin 가중치 이전 프리미티브 테스트 - 3ds Max 환경에서 실행 (Type C).

``pyjallib.max.skin.Skin``의 ``activate_skin`` / ``get_bone_table`` / ``get_vertex_weights`` /
``transfer_bone_weights`` 와 legacy ``transfert_skin_data`` 래퍼를 합성 스킨 박스로 검증한다.
판정은 가중치 보존 항등식이다 - 대상 본 새 가중치 == 기존 + Σ이전, 원본 본 0, 버텍스 합 1,
제거 본 ∩ 본 목록 = ∅. 포즈·형상 축은 두지 않는다(라이브러리 단위는 가중치 항등식이 정확한 판정).

합성 씬(박스 본, 레이어 규약 없음):

    root(0,0,0) > spine(0,0,10) > head(0,0,20)
    spine > upperarm(10,0,15) > twist(15,0,15)
    extra(20,0,15) 독립
    head > jaw(0,5,20)
    Body  [spine, upperarm, twist, extra]   가중치 규칙 body_weight_rule
    Face  [head, jaw]                       face_weight_rule
    Hair  [jaw]                             hair_weight_rule  → head가 addBone 경로

가중치는 버텍스 인덱스 규칙으로 결정적으로 준다(위치 무의존). 픽스처가 만들려던 조건은
TC01이 먼저 단정한다.

기대 TC 수: 15 (TC00~TC14, TC당 assert 1건)

실행 방법:
    uv run python tests/run_max_tests.py test_skin.py

로그 파일: tests/logs/test_Skin.log
"""

import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# pyjallib 소스 경로 추가 + 배포본 선점 퍼지.
# 3ds Max는 기동 시 배포본 pyjallib을 sys.modules에 선점하므로, 경로만 앞에 넣으면 캐시
# 히트로 배포본이 검증된다(`processes/worktree_workflow.md`). 퍼지 후 import해야 이 체크아웃의
# 소스가 로드되고, TC00이 그것을 단정한다.
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)
for _moduleName in [name for name in list(sys.modules) if name.split(".")[0] == "pyjallib"]:
    del sys.modules[_moduleName]

from pymxs import runtime as rt

import pyjallib
from pyjallib.testKit import TestReporter
from pyjallib.max.skin import Skin

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Skin", LOG_DIR)

WEIGHT_TOLERANCE = 1e-5
SUM_TOLERANCE = 1e-4

skin = Skin()


# ---- 픽스처 -------------------------------------------------------------------


def _bone(inName: str, inPos: Tuple[float, float, float], inParent: Any) -> Any:
    node = rt.Box(name=inName, width=1.0, length=1.0, height=2.0)
    node.pos = rt.Point3(*inPos)
    if inParent is not None:
        node.parent = inParent
    return node


def _skinned_box(inName: str, inPos: Tuple[float, float, float], inBones: List[Any]) -> Tuple[Any, Any]:
    box = rt.Box(
        name=inName, width=10.0, length=4.0, height=4.0, widthsegs=3, lengthsegs=1, heightsegs=1
    )
    box.pos = rt.Point3(*inPos)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    for bone in inBones:
        rt.skinOps.addBone(skinMod, bone, 1)
    skinMod.enableDQ = False
    rt.completeRedraw()
    return box, skinMod


def _set_weights(inBox: Any, inSkinMod: Any, inRule: Callable[[int], Dict[str, float]]) -> None:
    """``inRule(vertIndex) -> {boneName: weight}``로 전 버텍스 가중치를 쓴다."""
    skin.activate_skin(inBox, inSkinMod)
    table = skin.get_bone_table(inSkinMod)
    idByName = {entry["name"]: boneId for boneId, entry in table.items()}
    for v in range(1, int(rt.skinOps.GetNumberVertices(inSkinMod)) + 1):
        weights = inRule(v)
        ids = [idByName[name] for name in weights]
        ws = [weights[name] for name in weights]
        rt.skinOps.ReplaceVertexWeights(inSkinMod, v, ids, ws)


def body_weight_rule(inVertIndex: int) -> Dict[str, float]:
    remainder = inVertIndex % 3
    if remainder == 0:
        return {"spine": 1.0}
    if remainder == 1:
        return {"upperarm": 0.5, "twist": 0.5}
    return {"twist": 0.7, "extra": 0.3}


def face_weight_rule(inVertIndex: int) -> Dict[str, float]:
    if inVertIndex % 2 == 1:
        return {"jaw": 0.6, "head": 0.4}
    return {"head": 1.0}


def hair_weight_rule(inVertIndex: int) -> Dict[str, float]:
    return {"jaw": 1.0}


def build_scene() -> Dict[str, Any]:
    """합성 씬을 새로 짓고 ``{이름: 노드}`` + ``{"<Mesh>Skin": Skin 모디파이어}``를 돌려준다."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    nodes: Dict[str, Any] = {}
    nodes["root"] = _bone("root", (0, 0, 0), None)
    nodes["spine"] = _bone("spine", (0, 0, 10), nodes["root"])
    nodes["head"] = _bone("head", (0, 0, 20), nodes["spine"])
    nodes["upperarm"] = _bone("upperarm", (10, 0, 15), nodes["spine"])
    nodes["twist"] = _bone("twist", (15, 0, 15), nodes["upperarm"])
    nodes["extra"] = _bone("extra", (20, 0, 15), None)
    nodes["jaw"] = _bone("jaw", (0, 5, 20), nodes["head"])

    body, bodySkin = _skinned_box(
        "Body", (15, 0, 15), [nodes["spine"], nodes["upperarm"], nodes["twist"], nodes["extra"]]
    )
    face, faceSkin = _skinned_box("Face", (0, 5, 20), [nodes["head"], nodes["jaw"]])
    hair, hairSkin = _skinned_box("Hair", (0, 8, 22), [nodes["jaw"]])
    _set_weights(body, bodySkin, body_weight_rule)
    _set_weights(face, faceSkin, face_weight_rule)
    _set_weights(hair, hairSkin, hair_weight_rule)
    nodes["Body"], nodes["Face"], nodes["Hair"] = body, face, hair
    nodes["BodySkin"], nodes["FaceSkin"], nodes["HairSkin"] = bodySkin, faceSkin, hairSkin

    rt.clearSelection()
    return nodes


# ---- 스냅샷 / 판정 헬퍼 -----------------------------------------------------------


def handle_of(inNode: Any) -> int:
    return int(rt.getHandleByAnim(inNode))


def bone_names(inNode: Any, inSkinMod: Any) -> List[str]:
    """Skin의 본 이름(정렬). 선택을 바꾸므로 보관·복원한다."""
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        return sorted(e["name"] for e in skin.get_bone_table(inSkinMod).values())
    finally:
        _restore(saved)


def weights_by_name(inNode: Any, inSkinMod: Any) -> Dict[int, Dict[str, float]]:
    """``{v: {본 이름: w}}`` (w > 0만). 선택을 바꾸므로 보관·복원한다."""
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        table = skin.get_bone_table(inSkinMod)
        raw = skin.get_vertex_weights(inSkinMod)
    finally:
        _restore(saved)
    return {
        v: {table[boneId]["name"]: w for boneId, w in entries if w > 0.0}
        for v, entries in raw.items()
    }


def _restore(inSaved: List[Any]) -> None:
    valid = [n for n in inSaved if rt.isValidNode(n)]
    if valid:
        rt.select(rt.Array(*valid))
    else:
        rt.clearSelection()


def expected_weights(
    inWeights: Dict[int, Dict[str, float]], inTransfer: Dict[str, str], inVerts: Optional[List[int]] = None
) -> Dict[int, Dict[str, float]]:
    """``{원본 본: 대상 본}``으로 합산한 기대 결과. ``inVerts``가 있으면 그 버텍스만 합산한다."""
    expected: Dict[int, Dict[str, float]] = {}
    for v, byName in inWeights.items():
        if inVerts is not None and v not in inVerts:
            expected[v] = dict(byName)
            continue
        merged: Dict[str, float] = {}
        for name, w in byName.items():
            target = inTransfer.get(name, name)
            merged[target] = merged.get(target, 0.0) + w
        expected[v] = merged
    return expected


def weights_equal(
    inA: Dict[int, Dict[str, float]], inB: Dict[int, Dict[str, float]], inTol: float = WEIGHT_TOLERANCE
) -> Tuple[bool, str]:
    if set(inA) != set(inB):
        return False, f"버텍스 집합 불일치 {len(inA)} vs {len(inB)}"
    for v in inA:
        a = {k: w for k, w in inA[v].items() if w > inTol}
        b = {k: w for k, w in inB[v].items() if w > inTol}
        if set(a) != set(b):
            return False, f"v{v} 본 집합 {sorted(a)} vs {sorted(b)}"
        for name in a:
            if abs(a[name] - b[name]) > inTol:
                return False, f"v{v} {name} {a[name]} vs {b[name]}"
    return True, ""


def weight_sums_ok(inWeights: Dict[int, Dict[str, float]], inTol: float = SUM_TOLERANCE) -> Tuple[bool, str]:
    for v, byName in inWeights.items():
        total = sum(byName.values())
        if abs(total - 1.0) > inTol:
            return False, f"v{v} 합 {total}"
    return True, ""


def rule_weights(inRule: Callable[[int], Dict[str, float]], inCount: int) -> Dict[int, Dict[str, float]]:
    return {v: inRule(v) for v in range(1, inCount + 1)}


# ============================================================
# TC00: 로드 출처 = 이 체크아웃의 src (배포본 아님)
# ============================================================
try:
    loadedFrom = str(Path(pyjallib.__file__).resolve()).lower()
    expectedRoot = str(Path(_srcPath).resolve()).lower()
    reporter.assert_test(
        loadedFrom.startswith(expectedRoot),
        f"TC00 로드 출처 = 워크스페이스 소스 [pyjallib={pyjallib.__file__}]",
        f"기대 루트 {expectedRoot}",
    )
except Exception as e:
    reporter.error("TC00 로드 출처", str(e))


# ============================================================
# TC01: 픽스처 자기단정 - 본 목록 + 규칙대로 가중치가 들어갔는가
# ============================================================
try:
    nodes = build_scene()
    bodyCount = int(rt.skinOps.GetNumberVertices(nodes["BodySkin"]))
    bodyOk, bodyMsg = weights_equal(
        weights_by_name(nodes["Body"], nodes["BodySkin"]), rule_weights(body_weight_rule, bodyCount)
    )
    faceCount = int(rt.skinOps.GetNumberVertices(nodes["FaceSkin"]))
    faceOk, faceMsg = weights_equal(
        weights_by_name(nodes["Face"], nodes["FaceSkin"]), rule_weights(face_weight_rule, faceCount)
    )
    hairCount = int(rt.skinOps.GetNumberVertices(nodes["HairSkin"]))
    hairOk, hairMsg = weights_equal(
        weights_by_name(nodes["Hair"], nodes["HairSkin"]), rule_weights(hair_weight_rule, hairCount)
    )
    bonesOk = (
        bone_names(nodes["Body"], nodes["BodySkin"]) == ["extra", "spine", "twist", "upperarm"]
        and bone_names(nodes["Face"], nodes["FaceSkin"]) == ["head", "jaw"]
        and bone_names(nodes["Hair"], nodes["HairSkin"]) == ["jaw"]
    )
    reporter.assert_test(
        bodyOk and faceOk and hairOk and bonesOk and bodyCount >= 6,
        f"TC01 픽스처 자기단정 - 본 목록 + 규칙 가중치 [Body v={bodyCount}, Face v={faceCount}, Hair v={hairCount}]",
        f"body={bodyMsg} face={faceMsg} hair={hairMsg} bones={bonesOk}",
    )
except Exception as e:
    reporter.error("TC01 픽스처 자기단정", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC02: get_bone_table - GetBoneNode 핸들 == getNodeByName 핸들, byName 없음
# ============================================================
try:
    nodes = build_scene()
    skin.activate_skin(nodes["Body"], nodes["BodySkin"])
    table = skin.get_bone_table(nodes["BodySkin"])
    idsContiguous = sorted(table) == list(range(1, len(table) + 1))
    handlesMatch = all(
        entry["handle"] == handle_of(rt.getNodeByName(entry["name"])) for entry in table.values()
    )
    noByName = not any(entry["byName"] for entry in table.values())
    names = sorted(e["name"] for e in table.values())
    reporter.assert_test(
        idsContiguous and handlesMatch and noByName and names == ["extra", "spine", "twist", "upperarm"],
        f"TC02 get_bone_table - 본 ID 연속 + GetBoneNode 핸들 == getNodeByName 핸들 + byName 0 [{len(table)}본]",
        f"contiguous={idsContiguous} handles={handlesMatch} byName0={noByName} names={names}",
    )
except Exception as e:
    reporter.error("TC02 get_bone_table", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC03: get_vertex_weights 왕복 - 전 버텍스 / 부분 인덱스 / 사용 본 핸들
# ============================================================
try:
    nodes = build_scene()
    skin.activate_skin(nodes["Body"], nodes["BodySkin"])
    table = skin.get_bone_table(nodes["BodySkin"])
    allWeights = skin.get_vertex_weights(nodes["BodySkin"])
    count = int(rt.skinOps.GetNumberVertices(nodes["BodySkin"]))
    byName = {
        v: {table[b]["name"]: w for b, w in entries if w > 0.0} for v, entries in allWeights.items()
    }
    roundtripOk, roundtripMsg = weights_equal(byName, rule_weights(body_weight_rule, count))
    partial = skin.get_vertex_weights(nodes["BodySkin"], [1, 2])
    partialOk = set(partial) == {1, 2} and partial[1] == allWeights[1] and partial[2] == allWeights[2]
    usedHandles = skin.get_used_bone_handles(table, allWeights)
    expectedUsed = {handle_of(nodes[n]) for n in ("spine", "upperarm", "twist", "extra")}
    reporter.assert_test(
        roundtripOk and set(allWeights) == set(range(1, count + 1)) and partialOk and usedHandles == expectedUsed,
        f"TC03 get_vertex_weights 왕복 + 부분 인덱스 + get_used_bone_handles [v={count}]",
        f"roundtrip={roundtripMsg} partial={partialOk} used={usedHandles == expectedUsed}",
    )
except Exception as e:
    reporter.error("TC03 get_vertex_weights", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC04: transfer_bone_weights 다대일 - twist+extra → upperarm, 둘 제거. 보존 항등식
# ============================================================
try:
    nodes = build_scene()
    before = weights_by_name(nodes["Body"], nodes["BodySkin"])
    twistH, extraH, upperH = handle_of(nodes["twist"]), handle_of(nodes["extra"]), handle_of(nodes["upperarm"])
    result = skin.transfer_bone_weights(
        nodes["Body"], nodes["BodySkin"], {twistH: upperH, extraH: upperH}, {twistH, extraH}
    )
    after = weights_by_name(nodes["Body"], nodes["BodySkin"])
    expected = expected_weights(before, {"twist": "upperarm", "extra": "upperarm"})
    eqOk, eqMsg = weights_equal(after, expected)
    sumOk, sumMsg = weight_sums_ok(after)
    bonesAfter = bone_names(nodes["Body"], nodes["BodySkin"])
    noRemoved = not ({"twist", "extra"} & set(bonesAfter))
    touchedExpected = sum(1 for v, w in before.items() if "twist" in w or "extra" in w)
    twistVerts = sum(1 for w in before.values() if "twist" in w)
    twistSum = sum(w["twist"] for w in before.values() if "twist" in w)
    statsOk = (
        result["touchedVerts"] == touchedExpected
        and result["transferred"][twistH]["target"] == upperH
        and result["transferred"][twistH]["verts"] == twistVerts
        and abs(result["transferred"][twistH]["weightSum"] - twistSum) < WEIGHT_TOLERANCE
        and result["transferred"][extraH]["target"] == upperH
        and result["removedBones"] == ["extra", "twist"]
        and result["addedBones"] == []
        and result["warnings"] == []
    )
    reporter.assert_test(
        eqOk and sumOk and noRemoved and statsOk and bonesAfter == ["spine", "upperarm"],
        f"TC04 transfer 다대일 twist+extra→upperarm + 제거 - 보존 항등식 + 합 1 + 제거 본 ∩ 본 목록 ∅ [touched={result['touchedVerts']}]",
        f"eq={eqMsg} sum={sumMsg} bones={bonesAfter} stats={statsOk} result={result}",
    )
except Exception as e:
    reporter.error("TC04 transfer 다대일", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC05: addBone 경로 - Hair [jaw] → head (Skin에 없음) + bind pose 경고
# ============================================================
try:
    nodes = build_scene()
    before = weights_by_name(nodes["Hair"], nodes["HairSkin"])
    jawH, headH = handle_of(nodes["jaw"]), handle_of(nodes["head"])
    result = skin.transfer_bone_weights(nodes["Hair"], nodes["HairSkin"], {jawH: headH}, {jawH})
    after = weights_by_name(nodes["Hair"], nodes["HairSkin"])
    expected = expected_weights(before, {"jaw": "head"})
    eqOk, eqMsg = weights_equal(after, expected)
    sumOk, sumMsg = weight_sums_ok(after)
    bonesAfter = bone_names(nodes["Hair"], nodes["HairSkin"])
    warnOk = len(result["warnings"]) == 1 and "bind pose" in result["warnings"][0]
    reporter.assert_test(
        eqOk and sumOk and bonesAfter == ["head"] and result["addedBones"] == ["head"]
        and result["removedBones"] == ["jaw"] and warnOk and result["touchedVerts"] == len(before),
        f"TC05 addBone 경로 - jaw→head(Skin 부재) 추가 후 이전·제거 + bind pose 경고 [bones={bonesAfter}]",
        f"eq={eqMsg} sum={sumMsg} result={result}",
    )
except Exception as e:
    reporter.error("TC05 addBone 경로", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC06: inVertexIndices 부분 이전 + inRemoveHandles 빈 집합이면 본 잔존
# ============================================================
try:
    nodes = build_scene()
    before = weights_by_name(nodes["Body"], nodes["BodySkin"])
    twistH, upperH = handle_of(nodes["twist"]), handle_of(nodes["upperarm"])
    twistVerts = sorted(v for v, w in before.items() if "twist" in w)
    partialVerts = twistVerts[:2]
    result = skin.transfer_bone_weights(
        nodes["Body"], nodes["BodySkin"], {twistH: upperH}, set(), inVertexIndices=partialVerts
    )
    after = weights_by_name(nodes["Body"], nodes["BodySkin"])
    expected = expected_weights(before, {"twist": "upperarm"}, inVerts=partialVerts)
    eqOk, eqMsg = weights_equal(after, expected)
    sumOk, sumMsg = weight_sums_ok(after)
    bonesAfter = bone_names(nodes["Body"], nodes["BodySkin"])
    untouchedStillTwist = all("twist" in after[v] for v in twistVerts[2:])
    reporter.assert_test(
        eqOk and sumOk and len(partialVerts) == 2 and result["touchedVerts"] == 2
        and bonesAfter == ["extra", "spine", "twist", "upperarm"] and result["removedBones"] == []
        and untouchedStillTwist and len(twistVerts) > 2,
        f"TC06 inVertexIndices 부분 이전 {partialVerts} + inRemoveHandles 빈 집합 → twist 잔존, 나머지 버텍스 무변경",
        f"eq={eqMsg} sum={sumMsg} bones={bonesAfter} result={result} twistVerts={twistVerts}",
    )
except Exception as e:
    reporter.error("TC06 부분 이전", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC07: 이전 대상 없는 사용 본 → RuntimeError, 씬 무변경
# ============================================================
try:
    nodes = build_scene()
    before = weights_by_name(nodes["Body"], nodes["BodySkin"])
    bonesBefore = bone_names(nodes["Body"], nodes["BodySkin"])
    twistH = handle_of(nodes["twist"])
    raised = None
    try:
        skin.transfer_bone_weights(nodes["Body"], nodes["BodySkin"], {}, {twistH})
    except RuntimeError as err:
        raised = err
    after = weights_by_name(nodes["Body"], nodes["BodySkin"])
    bonesAfter = bone_names(nodes["Body"], nodes["BodySkin"])
    eqOk, eqMsg = weights_equal(after, before)
    reporter.assert_test(
        raised is not None and "twist" in str(raised) and eqOk and bonesAfter == bonesBefore,
        f"TC07 이전 대상 없는 사용 본(twist) → RuntimeError + 가중치·본 목록 무변경 [{raised}]",
        f"raised={raised!r} eq={eqMsg} bones {bonesBefore} → {bonesAfter}",
    )
except Exception as e:
    reporter.error("TC07 미해소 예외", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC08: 선택 보관·복원 - 호출 전/후 선택 집합 일치 (성공 경로 + 예외 경로)
# ============================================================
try:
    nodes = build_scene()
    rt.select(rt.Array(nodes["root"], nodes["spine"]))
    selBefore = sorted(handle_of(n) for n in rt.getCurrentSelection())
    twistH, upperH = handle_of(nodes["twist"]), handle_of(nodes["upperarm"])
    skin.transfer_bone_weights(nodes["Body"], nodes["BodySkin"], {twistH: upperH}, {twistH})
    selAfterOk = sorted(handle_of(n) for n in rt.getCurrentSelection())
    extraH = handle_of(nodes["extra"])
    try:
        skin.transfer_bone_weights(nodes["Body"], nodes["BodySkin"], {}, {extraH})
    except RuntimeError:
        pass
    selAfterErr = sorted(handle_of(n) for n in rt.getCurrentSelection())
    reporter.assert_test(
        len(selBefore) == 2 and selAfterOk == selBefore and selAfterErr == selBefore,
        f"TC08 선택 보관·복원 - 성공 경로·예외 경로 모두 호출 전 선택 집합 유지 [{selBefore}]",
        f"before={selBefore} afterOk={selAfterOk} afterErr={selAfterErr}",
    )
except Exception as e:
    reporter.error("TC08 선택 보관·복원", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC09: legacy transfert_skin_data - 본별 가중치 동일(0 == 부재), 원본 본 잔존
# ============================================================
try:
    nodes = build_scene()
    before = weights_by_name(nodes["Body"], nodes["BodySkin"])
    count = int(rt.skinOps.GetNumberVertices(nodes["BodySkin"]))
    skin.transfert_skin_data(nodes["Body"], nodes["twist"], nodes["upperarm"], list(range(1, count + 1)))
    after = weights_by_name(nodes["Body"], nodes["BodySkin"])
    expected = expected_weights(before, {"twist": "upperarm"})
    eqOk, eqMsg = weights_equal(after, expected)
    sumOk, sumMsg = weight_sums_ok(after)
    bonesAfter = bone_names(nodes["Body"], nodes["BodySkin"])
    reporter.assert_test(
        eqOk and sumOk and bonesAfter == ["extra", "spine", "twist", "upperarm"],
        "TC09 legacy transfert_skin_data(twist→upperarm) - 본별 가중치 == 기대 합산(0 == 부재) + twist 본 잔존",
        f"eq={eqMsg} sum={sumMsg} bones={bonesAfter}",
    )
except Exception as e:
    reporter.error("TC09 legacy 래퍼", f"{e}\n{traceback.format_exc()}")


# ============================================================
# 본 ID 밀림 픽스처 (TC10~TC14)
#
# `addBone`은 새 본을 항상 끝에 붙이지 않는다. 이전에 `removeBone`으로 비워 둔 슬롯이
# 있으면 **가장 낮은 빈 자리부터** 내주고 그 뒤 본의 ID를 한 칸씩 민다(2026-09-15 실측 -
# 프로덕션 Skin에서 새 본이 ID 1을 차지하며 258본이 밀렸다). 리거가 본을 붙였다 뗐다 한
# Skin에는 빈 슬롯이 흔하지만, 갓 만든 합성 Skin에는 없어서 TC01~TC09가 이 결함을 못 봤다.
#
# 여기서는 **빈 슬롯을 일부러 만들어** 그 조건을 세운다:
#   체인 chain00..chain13 → Skin에 dummySlot + chain01..chain13 → dummySlot을 removeBone
#   → 전 버텍스 명시 지정(엔벨로프 요인 배제) → chain01..chain06을 Skin 밖 chain00으로 이전
# 이전 시 chain00이 빈 슬롯을 채우며 ID가 밀린다.
# ============================================================

SHIFT_CHAIN_LEN = 14
SHIFT_SOURCE_COUNT = 6


def build_shift_scene() -> Dict[str, Any]:
    """본 ID가 밀리는 조건의 씬을 짓는다. ``{"box", "skinMod", "chain", "target", "sources"}``."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    chain: List[Any] = []
    for i in range(SHIFT_CHAIN_LEN):
        node = rt.Box(name=f"chain{i:02d}", width=4.0, length=4.0, height=6.0)
        node.pos = rt.Point3(0.0, 0.0, i * 6.0)
        if chain:
            node.parent = chain[-1]
        chain.append(node)
    dummy = rt.Box(name="dummySlot", width=4.0, length=4.0, height=6.0)
    dummy.pos = rt.Point3(30.0, 0.0, 0.0)

    box = rt.Box(
        name="ShiftBox", width=6.0, length=6.0, height=SHIFT_CHAIN_LEN * 6.0,
        widthsegs=1, lengthsegs=1, heightsegs=3,
    )
    box.pos = rt.Point3(0.0, 0.0, 0.0)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    # chain00은 Skin 밖에 둔다 - 이전 대상이므로 addBone 경로를 탄다
    for bone in [dummy] + chain[1:]:
        rt.skinOps.addBone(skinMod, bone, 1)
    skinMod.enableDQ = False
    rt.completeRedraw()

    # dummySlot을 빼서 앞쪽 슬롯을 비운다 - 이것이 밀림의 방아쇠다
    skin.activate_skin(box, skinMod)
    dummyId = next(
        (bid for bid, e in skin.get_bone_table(skinMod).items() if e["name"] == "dummySlot"), None
    )
    rt.skinOps.removeBone(skinMod, dummyId)

    # 슬롯이 빈 상태에서 전 버텍스를 명시 지정한다(M 플래그를 켜 엔벨로프 요인을 배제)
    table = skin.get_bone_table(skinMod)
    idByName = {e["name"]: bid for bid, e in table.items()}
    names = sorted(idByName)
    for v in range(1, int(rt.skinOps.GetNumberVertices(skinMod)) + 1):
        primary = names[v % len(names)]
        secondary = names[(v + 1) % len(names)]
        if primary == secondary:
            rt.skinOps.ReplaceVertexWeights(skinMod, v, [idByName[primary]], [1.0])
        else:
            rt.skinOps.ReplaceVertexWeights(
                skinMod, v, [idByName[primary], idByName[secondary]], [0.7, 0.3]
            )
    rt.clearSelection()

    return {
        "box": box,
        "skinMod": skinMod,
        "chain": chain,
        "target": chain[0],
        "sources": chain[1 : 1 + SHIFT_SOURCE_COUNT],
    }


def shift_transfer_map(inScene: Dict[str, Any]) -> Dict[int, int]:
    targetHandle = handle_of(inScene["target"])
    return {handle_of(bone): targetHandle for bone in inScene["sources"]}


# ============================================================
# TC10: 픽스처 자기단정 - 빈 슬롯이 있고, 이전 대상이 Skin 밖이며, 전 버텍스가 명시 지정이다
# ============================================================
try:
    scene = build_shift_scene()
    bonesBefore = bone_names(scene["box"], scene["skinMod"])
    before = weights_by_name(scene["box"], scene["skinMod"])
    targetInSkin = "chain00" in bonesBefore
    dummyGone = "dummySlot" not in bonesBefore
    allWeighted = all(w for w in before.values())
    sumOk, sumMsg = weight_sums_ok(before)
    reporter.assert_test(
        dummyGone and not targetInSkin and allWeighted and sumOk and len(before) >= 8
        and len(bonesBefore) == SHIFT_CHAIN_LEN - 1,
        f"TC10 밀림 픽스처 자기단정 - dummySlot 제거로 빈 슬롯 확보, 이전 대상 chain00은 Skin 밖, "
        f"전 버텍스 명시 지정 [본 {len(bonesBefore)}개, v={len(before)}]",
        f"dummyGone={dummyGone} targetOutside={not targetInSkin} allWeighted={allWeighted} "
        f"sum={sumMsg} bones={bonesBefore}",
    )
except Exception as e:
    reporter.error("TC10 밀림 픽스처", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC11: 밀림 경로에서 이전 결과가 핸들 기준 순수 합산 기대값과 일치한다 (판별력 TC)
#       수정 전 코드에서는 여기서 편차가 난다 - stale 본 ID로 가중치가 엉뚱한 본에 얹힌다
# ============================================================
try:
    scene = build_shift_scene()
    before = weights_by_name(scene["box"], scene["skinMod"])
    sourceNames = {str(b.name) for b in scene["sources"]}
    targetName = str(scene["target"].name)
    result = skin.transfer_bone_weights(
        scene["box"], scene["skinMod"], shift_transfer_map(scene), set(shift_transfer_map(scene))
    )
    after = weights_by_name(scene["box"], scene["skinMod"])
    expected = expected_weights(before, {name: targetName for name in sourceNames})
    eqOk, eqMsg = weights_equal(after, expected)
    sumOk, sumMsg = weight_sums_ok(after)
    bonesAfter = bone_names(scene["box"], scene["skinMod"])
    noSource = not (sourceNames & set(bonesAfter))
    reporter.assert_test(
        eqOk and sumOk and noSource and targetName in bonesAfter,
        # 신규 키는 메시지에서 .get으로 읽는다 - 판별력 확인(수정 전 코드) 때 KeyError로
        # 죽지 않고 **가중치 항등식 축에서** 실패해야 신호가 정확하다
        f"TC11 밀림 경로 보존 항등식 - chain01~chain06 → {targetName}, 결과 == 핸들 기준 "
        f"순수 합산 기대값 [touched={result['touchedVerts']}, added={result['addedBones']}, "
        f"shifted={result.get('boneIdsShifted')}]",
        f"eq={eqMsg} sum={sumMsg} bones={bonesAfter} result={result}",
    )
except Exception as e:
    reporter.error("TC11 밀림 경로 보존", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC12: boneIdsShifted == True + warnings에 밀림 줄이 있다
# ============================================================
try:
    scene = build_shift_scene()
    result = skin.transfer_bone_weights(
        scene["box"], scene["skinMod"], shift_transfer_map(scene), set(shift_transfer_map(scene))
    )
    shiftWarnings = [w for w in result["warnings"] if "본 ID를 밀었습니다" in w]
    reporter.assert_test(
        result["boneIdsShifted"] is True and len(shiftWarnings) == 1,
        f"TC12 밀림 탐지 - boneIdsShifted=True + 경고 1줄 [{shiftWarnings[:1]}]",
        f"boneIdsShifted={result['boneIdsShifted']} warnings={result['warnings']}",
    )
except Exception as e:
    reporter.error("TC12 밀림 탐지", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC13: verifiedVerts == 쓴 버텍스 수(touchedVerts)
# ============================================================
try:
    scene = build_shift_scene()
    result = skin.transfer_bone_weights(
        scene["box"], scene["skinMod"], shift_transfer_map(scene), set(shift_transfer_map(scene))
    )
    reporter.assert_test(
        result["verifiedVerts"] == result["touchedVerts"] and result["verifiedVerts"] > 0,
        f"TC13 사후 검증 범위 - verifiedVerts({result['verifiedVerts']}) == "
        f"touchedVerts({result['touchedVerts']}) > 0",
        f"result={result}",
    )
except Exception as e:
    reporter.error("TC13 사후 검증 범위", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC14: legacy transfert_skin_data 경로 - 구조 변경이 없으므로 boneIdsShifted == False
#       (대상 본이 이미 Skin에 있어 addBone이 일어나지 않는다 → 재조회도 생략된다)
# ============================================================
try:
    nodes = build_scene()
    count = int(rt.skinOps.GetNumberVertices(nodes["BodySkin"]))
    twistH, upperH = handle_of(nodes["twist"]), handle_of(nodes["upperarm"])
    result = skin.transfer_bone_weights(
        nodes["Body"], nodes["BodySkin"], {twistH: upperH}, set(),
        inVertexIndices=list(range(1, count + 1)),
    )
    bonesAfter = bone_names(nodes["Body"], nodes["BodySkin"])
    reporter.assert_test(
        result["boneIdsShifted"] is False and result["addedBones"] == []
        and result["verifiedVerts"] == result["touchedVerts"] and "twist" in bonesAfter,
        f"TC14 무구조변경 경로 - addBone 없음 → boneIdsShifted=False, 재조회 생략, "
        f"검증은 그대로 [verified={result['verifiedVerts']}]",
        f"result={result} bones={bonesAfter}",
    )
except Exception as e:
    reporter.error("TC14 무구조변경 경로", f"{e}\n{traceback.format_exc()}")


# ============================================================
# 결과 요약 및 정리
# ============================================================
passed, failed, total = reporter.summary()
reporter.close()
print(f"[test_skin] RESULT: {passed}/{total} passed, {failed} failed")
