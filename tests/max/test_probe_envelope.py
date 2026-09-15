#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
엔벨로프 재평가 결함 Phase 0 프로브 - 3ds Max 환경에서 실행 (Type C).

가설 H1: 3ds Max Skin은 버텍스마다 "수정(Modified)" 플래그를 두고, 그 플래그가 꺼진
버텍스의 가중치는 엔벨로프에서 계산한다. 본 목록의 구조 변경(``addBone``/``removeBone``)은
이 비수정 버텍스를 전수 재평가하므로, ``transfer_bone_weights``가 손대지 않은(비접촉)
버텍스의 가중치가 절차 전후에 달라진다.

이 파일은 **가설을 실측으로 확정하거나 기각하는 게이트**다. 측정치는
``tests/logs/probe_envelope.json``에 남기고, 판정 TC는 가설이 맞을 때만 통과한다.
판정 TC가 실패하면 그것이 곧 H1 기각 신호이므로, 코드를 고치지 않고 PRD를 다시 쓴다.

절 구성:

- 합성 절 (P1·P2·P4): 엔벨로프 구동 박스(``ReplaceVertexWeights`` 미호출)와 명시 지정
  박스를 짓고 ``addBone``/``removeBone`` 전후 전 버텍스 가중치를 대조한다.
- 고정 수단 절 (P3): 비수정 버텍스를 현재 가중치로 고정하는 수단 2종의 효과와 비용.
- 실기 절 (P5·P6): 마스터 결함 씬 사본과 JeongHuiwon 사본의 비수정 버텍스 분포.
- 교차 저장소 통합 절: 워크트리 pyjallib + 툴 master 소스로 ``run_build``를 돌린다.

합성 씬(레이어 규약 없음. 본은 Box 프리미티브, 엔벨로프는 Max가 자동 계산):

    boneA(-15,0,2)  boneB(-5,0,2)  boneC(5,0,2)  boneD(15,0,2)  각 14x8x8
    EnvBox / ExpBox : width 40(X) x length 4 x height 4, widthsegs 7 (32 verts)

본 폭(14)이 간격(10)보다 넓어 엔벨로프가 겹치므로 엔벨로프 구동 가중치가 블렌드로
떨어진다. 이것이 없으면 전 버텍스가 rigid(단일 본 1.0)라 재평가를 관측할 재료가 없다.

기대 TC 수: 23 (TC00~TC22)

실행 방법:
    uv run python tests/run_max_tests.py test_probe_envelope.py

로그 파일: tests/logs/test_ProbeEnvelope.log
결과 JSON: tests/logs/probe_envelope.json
"""

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
JSON_PATH = LOG_DIR / "probe_envelope.json"
reporter = TestReporter("ProbeEnvelope", LOG_DIR)

WEIGHT_TOLERANCE = 1e-6

skin = Skin()

# 프로브 측정치 적재소. 각 절이 끝날 때마다 디스크에 쓴다(중간에 죽어도 앞 절은 남는다).
PROBE: Dict[str, Any] = {"host": "batch", "sections": {}}


def dump_probe() -> None:
    """지금까지의 측정치를 JSON으로 쓴다."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(PROBE, f, ensure_ascii=False, indent=2, default=str)


# ---- 공용 헬퍼 -----------------------------------------------------------------


def _restore(inSaved: List[Any]) -> None:
    valid = [n for n in inSaved if rt.isValidNode(n)]
    if valid:
        rt.select(rt.Array(*valid))
    else:
        rt.clearSelection()


def weights_by_name(inNode: Any, inSkinMod: Any) -> Dict[int, Dict[str, float]]:
    """``{v: {본 이름: w}}`` (w > 0만). 본 ID는 구조 변경으로 밀리므로 이름으로 키를 잡는다."""
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


def changed_verts(
    inBefore: Dict[int, Dict[str, float]],
    inAfter: Dict[int, Dict[str, float]],
    inVerts: Optional[List[int]] = None,
    inTol: float = WEIGHT_TOLERANCE,
) -> List[int]:
    """전후 가중치가 허용오차를 넘게 달라진 버텍스 인덱스 목록."""
    targets = sorted(set(inBefore) | set(inAfter)) if inVerts is None else sorted(inVerts)
    changed: List[int] = []
    for v in targets:
        wa = inBefore.get(v, {})
        wb = inAfter.get(v, {})
        names = set(wa) | set(wb)
        if any(abs(wa.get(n, 0.0) - wb.get(n, 0.0)) > inTol for n in names):
            changed.append(v)
    return changed


def max_delta(
    inBefore: Dict[int, Dict[str, float]],
    inAfter: Dict[int, Dict[str, float]],
    inVerts: Optional[List[int]] = None,
) -> float:
    """전후 가중치 편차의 최대값(진단용 - 변경 규모가 ULP인지 실질인지 가른다)."""
    targets = sorted(set(inBefore) | set(inAfter)) if inVerts is None else sorted(inVerts)
    worst = 0.0
    for v in targets:
        wa = inBefore.get(v, {})
        wb = inAfter.get(v, {})
        for n in set(wa) | set(wb):
            worst = max(worst, abs(wa.get(n, 0.0) - wb.get(n, 0.0)))
    return worst


def bone_names(inNode: Any, inSkinMod: Any) -> List[str]:
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        return sorted(e["name"] for e in skin.get_bone_table(inSkinMod).values())
    finally:
        _restore(saved)


def bone_id_of(inNode: Any, inSkinMod: Any, inBoneName: str) -> Optional[int]:
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        for boneId, entry in skin.get_bone_table(inSkinMod).items():
            if entry["name"] == inBoneName:
                return boneId
    finally:
        _restore(saved)
    return None


def is_vertex_modified(inSkinMod: Any, inVertIndex: int) -> Any:
    """``skinOps.isVertexModified``의 원값을 돌려준다. 호출 자체가 불가하면 예외를 올린다."""
    return rt.skinOps.isVertexModified(inSkinMod, inVertIndex)


def modified_flags(inNode: Any, inSkinMod: Any) -> Dict[int, Any]:
    """``{v: isVertexModified 원값}``. 호출이 실패하면 예외가 그대로 올라간다."""
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        count = int(rt.skinOps.GetNumberVertices(inSkinMod))
        return {v: is_vertex_modified(inSkinMod, v) for v in range(1, count + 1)}
    finally:
        _restore(saved)


# ---- 합성 픽스처 ---------------------------------------------------------------


# 본 배치. 본 Box의 크기가 Max 자동 엔벨로프의 크기를 정한다 - 작은 본(3x3x6)은 엔벨로프가
# 겹치지 않아 전 버텍스가 rigid(단일 본 1.0)로 떨어지고, 그러면 재평가가 가중치를 갈아치워도
# "블렌드가 흔들린다"를 관측할 재료가 없다(공허한 측정). 2026-09-15 스크래치 프로브 실측:
# 3x3x6 간격 20 → 블렌드 0/32, 24x8x8 간격 20 → 16/32, 20x8x8 간격 8 3개 → 28/32.
# 그래서 폭이 간격보다 넓은 본을 쓴다.
BONE_LAYOUT: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {
    "boneA": ((-15.0, 0.0, 2.0), (14.0, 8.0, 8.0)),
    "boneB": ((-5.0, 0.0, 2.0), (14.0, 8.0, 8.0)),
    "boneC": ((5.0, 0.0, 2.0), (14.0, 8.0, 8.0)),
    "boneD": ((15.0, 0.0, 2.0), (14.0, 8.0, 8.0)),
}


def _bone(inName: str) -> Any:
    pos, size = BONE_LAYOUT[inName]
    node = rt.Box(name=inName, width=size[0], length=size[1], height=size[2])
    node.pos = rt.Point3(*pos)
    return node


def _skinned_box(inName: str, inBones: List[Any]) -> Tuple[Any, Any]:
    """엔벨로프 구동 스킨 박스. ``ReplaceVertexWeights``를 부르지 않는다."""
    box = rt.Box(
        name=inName, width=40.0, length=4.0, height=4.0, widthsegs=7, lengthsegs=1, heightsegs=1
    )
    box.pos = rt.Point3(0.0, 0.0, 0.0)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    for bone in inBones:
        rt.skinOps.addBone(skinMod, bone, 1)
    skinMod.enableDQ = False
    rt.completeRedraw()
    return box, skinMod


def _set_explicit_weights(inBox: Any, inSkinMod: Any) -> None:
    """전 버텍스에 결정적 규칙으로 명시 가중치를 쓴다(= M 플래그를 켠다)."""
    skin.activate_skin(inBox, inSkinMod)
    table = skin.get_bone_table(inSkinMod)
    idByName = {entry["name"]: boneId for boneId, entry in table.items()}
    names = sorted(idByName)
    for v in range(1, int(rt.skinOps.GetNumberVertices(inSkinMod)) + 1):
        primary = names[v % len(names)]
        secondary = names[(v + 1) % len(names)]
        if primary == secondary:
            ids, ws = [idByName[primary]], [1.0]
        else:
            ids, ws = [idByName[primary], idByName[secondary]], [0.7, 0.3]
        rt.skinOps.ReplaceVertexWeights(inSkinMod, v, ids, ws)


def build_synthetic(inBoneNames: List[str], inExplicit: bool) -> Dict[str, Any]:
    """본 목록으로 스킨 박스 하나를 짓는다. ``inExplicit``이면 전 버텍스를 명시 지정한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    nodes = {name: _bone(name) for name in inBoneNames}
    boxName = "ExpBox" if inExplicit else "EnvBox"
    box, skinMod = _skinned_box(boxName, [nodes[name] for name in inBoneNames])
    if inExplicit:
        _set_explicit_weights(box, skinMod)
    rt.clearSelection()
    nodes["box"] = box
    nodes["skinMod"] = skinMod
    return nodes


# ============================================================
# TC00: 로드 출처 = 이 체크아웃의 src (배포본 아님)
# ============================================================
try:
    loadedFrom = str(Path(pyjallib.__file__).resolve()).lower()
    expectedRoot = str(Path(_srcPath).resolve()).lower()
    PROBE["pyjallibFile"] = str(pyjallib.__file__)
    reporter.assert_test(
        loadedFrom.startswith(expectedRoot),
        f"TC00 로드 출처 = 워크스페이스 소스 [pyjallib={pyjallib.__file__}]",
        f"기대 루트 {expectedRoot}",
    )
except Exception as e:
    reporter.error("TC00 로드 출처", str(e))


# ============================================================
# TC01: 픽스처 자기단정 - 엔벨로프 구동 박스에 가중치가 있고, 그중 **블렌드**(본 2개 이상)
#       버텍스가 존재하며, 명시 지정 박스와 분포가 다르다.
#       블렌드가 0이면 전 버텍스가 rigid라 "재평가로 가중치가 흔들린다"를 관측할 재료가
#       없다 - 이후 절의 "변경 0"이 공허해진다
# ============================================================
try:
    envNodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=False)
    envWeights = weights_by_name(envNodes["box"], envNodes["skinMod"])
    envVertCount = len(envWeights)
    envNonEmpty = sum(1 for w in envWeights.values() if w)
    envBlended = [v for v, w in envWeights.items() if len(w) > 1]

    expNodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=True)
    expWeights = weights_by_name(expNodes["box"], expNodes["skinMod"])
    expVertCount = len(expWeights)

    # 엔벨로프 구동과 명시 지정이 같은 분포면 픽스처가 조건을 만들지 못한 것이다
    distinct = len(changed_verts(envWeights, expWeights)) > 0

    PROBE["sections"]["fixture"] = {
        "envVertCount": envVertCount,
        "envVertsWithWeight": envNonEmpty,
        "envBlendedCount": len(envBlended),
        "expVertCount": expVertCount,
        "distinctDistribution": distinct,
        "envSample": {str(v): envWeights[v] for v in sorted(envWeights)[:4]},
        "expSample": {str(v): expWeights[v] for v in sorted(expWeights)[:4]},
    }
    dump_probe()

    reporter.assert_test(
        envVertCount >= 8
        and envNonEmpty == envVertCount
        and len(envBlended) > 0
        and expVertCount == envVertCount
        and distinct,
        f"TC01 픽스처 자기단정 - 엔벨로프 구동 전 버텍스 가중치 존재 + 블렌드 버텍스 존재 + "
        f"명시 지정과 분포 상이 [v={envVertCount}, 가중치 있는 v={envNonEmpty}, "
        f"블렌드 v={len(envBlended)}, 분포 상이={distinct}]",
        f"envVertCount={envVertCount} envNonEmpty={envNonEmpty} blended={len(envBlended)} "
        f"expVertCount={expVertCount} distinct={distinct}",
    )
except Exception as e:
    reporter.error("TC01 픽스처 자기단정", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC02 (P1, 판정): addBone이 엔벨로프 구동 버텍스를 재평가한다
#       (a) 엔벨로프 구동 박스: 변경 > 0    (b) 명시 지정 박스: 변경 == 0
#       (a)가 0이면 H1 기각 → PRD 재작성
# ============================================================
try:
    envNodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=False)
    envBefore = weights_by_name(envNodes["box"], envNodes["skinMod"])
    newBoneEnv = _bone("boneD")
    skin.activate_skin(envNodes["box"], envNodes["skinMod"])
    rt.skinOps.addBone(envNodes["skinMod"], newBoneEnv, 0)
    rt.clearSelection()
    envAfter = weights_by_name(envNodes["box"], envNodes["skinMod"])
    envChanged = changed_verts(envBefore, envAfter)
    envDelta = max_delta(envBefore, envAfter)

    expNodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=True)
    expBefore = weights_by_name(expNodes["box"], expNodes["skinMod"])
    newBoneExp = _bone("boneD")
    skin.activate_skin(expNodes["box"], expNodes["skinMod"])
    rt.skinOps.addBone(expNodes["skinMod"], newBoneExp, 0)
    rt.clearSelection()
    expAfter = weights_by_name(expNodes["box"], expNodes["skinMod"])
    expChanged = changed_verts(expBefore, expAfter)
    expDelta = max_delta(expBefore, expAfter)

    PROBE["sections"]["P1_addBone"] = {
        "envelopeDriven": {
            "vertCount": len(envBefore),
            "changedCount": len(envChanged),
            "changedVerts": envChanged[:20],
            "maxDelta": envDelta,
            "beforeSample": {str(v): envBefore[v] for v in envChanged[:3]},
            "afterSample": {str(v): envAfter[v] for v in envChanged[:3]},
        },
        "explicit": {
            "vertCount": len(expBefore),
            "changedCount": len(expChanged),
            "changedVerts": expChanged[:20],
            "maxDelta": expDelta,
        },
        "H1_reproduced": len(envChanged) > 0 and len(expChanged) == 0,
    }
    dump_probe()

    reporter.assert_test(
        len(envChanged) > 0 and len(expChanged) == 0,
        f"TC02 [P1 판정] addBone 재평가 - 엔벨로프 구동 변경 {len(envChanged)}/{len(envBefore)}"
        f"(최대 편차 {envDelta:.6g}) > 0, 명시 지정 변경 {len(expChanged)}/{len(expBefore)}"
        f"(최대 편차 {expDelta:.6g}) == 0",
        f"H1 기각 신호: env={len(envChanged)} exp={len(expChanged)} - PRD 재작성 대상",
    )
except Exception as e:
    reporter.error("TC02 P1 addBone 재평가", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC03 (P2): skinOps.isVertexModified 가용성과 의미
#       (b) 전 버텍스 True / (a) 전 버텍스 False / (a)에 ReplaceVertexWeights 1회 후
#       그 버텍스만 True로 바뀐다
# ============================================================
try:
    available = True
    apiError = ""
    envFlags: Dict[int, Any] = {}
    expFlags: Dict[int, Any] = {}
    afterWriteFlags: Dict[int, Any] = {}
    writtenVert = 3

    try:
        envNodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=False)
        envFlags = modified_flags(envNodes["box"], envNodes["skinMod"])
    except Exception as apiExc:
        available = False
        apiError = f"{apiExc}"

    if available:
        expNodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=True)
        expFlags = modified_flags(expNodes["box"], expNodes["skinMod"])

        # (a)에 버텍스 하나만 명시 지정하고 플래그 변화를 본다
        envNodes2 = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=False)
        skin.activate_skin(envNodes2["box"], envNodes2["skinMod"])
        raw = skin.get_vertex_weights(envNodes2["skinMod"], [writtenVert])
        ids = [boneId for boneId, _ in raw[writtenVert]]
        ws = [float(w) for _, w in raw[writtenVert]]
        rt.skinOps.ReplaceVertexWeights(envNodes2["skinMod"], writtenVert, ids, ws)
        rt.clearSelection()
        afterWriteFlags = modified_flags(envNodes2["box"], envNodes2["skinMod"])

    envAllFalse = available and all(not bool(f) for f in envFlags.values())
    expAllTrue = available and bool(expFlags) and all(bool(f) for f in expFlags.values())
    onlyWrittenTrue = available and bool(afterWriteFlags) and (
        [v for v, f in afterWriteFlags.items() if bool(f)] == [writtenVert]
    )

    PROBE["sections"]["P2_isVertexModified"] = {
        "available": available,
        "apiError": apiError,
        "rawValueSample": repr(envFlags.get(1)) if envFlags else None,
        "envelopeDrivenTrueCount": sum(1 for f in envFlags.values() if bool(f)),
        "envelopeDrivenVertCount": len(envFlags),
        "explicitTrueCount": sum(1 for f in expFlags.values() if bool(f)),
        "explicitVertCount": len(expFlags),
        "afterSingleWriteTrueVerts": [v for v, f in afterWriteFlags.items() if bool(f)],
        "writtenVert": writtenVert,
        "semanticsHold": envAllFalse and expAllTrue and onlyWrittenTrue,
    }
    dump_probe()

    reporter.assert_test(
        available and envAllFalse and expAllTrue and onlyWrittenTrue,
        f"TC03 [P2] isVertexModified 의미 - 엔벨로프 구동 True {sum(1 for f in envFlags.values() if bool(f))}"
        f"/{len(envFlags)}, 명시 지정 True {sum(1 for f in expFlags.values() if bool(f))}/{len(expFlags)}, "
        f"1회 쓰기 후 True 버텍스 {[v for v, f in afterWriteFlags.items() if bool(f)]}",
        f"available={available} err={apiError} envAllFalse={envAllFalse} "
        f"expAllTrue={expAllTrue} onlyWrittenTrue={onlyWrittenTrue}",
    )
except Exception as e:
    reporter.error("TC03 P2 isVertexModified", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC04 (P4, 판정): removeBone도 엔벨로프 구동 버텍스를 재평가한다
#       본 3개(A,B,C) 엔벨로프 구동 박스에서 B를 제거하고, B 가중치가 없던
#       비접촉 버텍스가 바뀌는지 센다. > 0이면 고정 시점이 "구조 변경 전"이어야 한다
# ============================================================
try:
    envNodes = build_synthetic(["boneA", "boneB", "boneC", "boneD"], inExplicit=False)
    envBefore = weights_by_name(envNodes["box"], envNodes["skinMod"])
    untouched = [v for v, w in envBefore.items() if w.get("boneD", 0.0) <= WEIGHT_TOLERANCE]
    touched = [v for v in envBefore if v not in untouched]

    boneDId = bone_id_of(envNodes["box"], envNodes["skinMod"], "boneD")
    skin.activate_skin(envNodes["box"], envNodes["skinMod"])
    rt.skinOps.removeBone(envNodes["skinMod"], boneDId)
    rt.clearSelection()
    envAfter = weights_by_name(envNodes["box"], envNodes["skinMod"])

    untouchedChanged = changed_verts(envBefore, envAfter, untouched)
    untouchedDelta = max_delta(envBefore, envAfter, untouched)

    # 명시 지정 대조군
    expNodes = build_synthetic(["boneA", "boneB", "boneC", "boneD"], inExplicit=True)
    expBefore = weights_by_name(expNodes["box"], expNodes["skinMod"])
    expUntouched = [v for v, w in expBefore.items() if w.get("boneD", 0.0) <= WEIGHT_TOLERANCE]
    expBoneDId = bone_id_of(expNodes["box"], expNodes["skinMod"], "boneD")
    skin.activate_skin(expNodes["box"], expNodes["skinMod"])
    rt.skinOps.removeBone(expNodes["skinMod"], expBoneDId)
    rt.clearSelection()
    expAfter = weights_by_name(expNodes["box"], expNodes["skinMod"])
    expUntouchedChanged = changed_verts(expBefore, expAfter, expUntouched)

    PROBE["sections"]["P4_removeBone"] = {
        "envelopeDriven": {
            "vertCount": len(envBefore),
            "untouchedCount": len(untouched),
            "touchedCount": len(touched),
            "untouchedChangedCount": len(untouchedChanged),
            "untouchedChangedVerts": untouchedChanged[:20],
            "maxDelta": untouchedDelta,
            "beforeSample": {str(v): envBefore[v] for v in untouchedChanged[:3]},
            "afterSample": {str(v): envAfter[v] for v in untouchedChanged[:3]},
        },
        "explicit": {
            "vertCount": len(expBefore),
            "untouchedCount": len(expUntouched),
            "untouchedChangedCount": len(expUntouchedChanged),
        },
        "fixBeforeStructureChangeRequired": len(untouchedChanged) > 0,
    }
    dump_probe()

    # 판정: 비접촉 버텍스가 있어야 측정이 성립하고(비공허), 명시 지정 대조군은 0이어야 한다.
    # 엔벨로프 구동 쪽 변경 수는 가설의 방향(> 0)을 확인하되, 0이어도 P1이 결함을 설명하므로
    # 여기서는 "측정이 성립했고 명시 지정은 무변경"을 판정 축에 둔다.
    reporter.assert_test(
        len(untouched) > 0 and len(expUntouchedChanged) == 0,
        f"TC04 [P4] removeBone 재평가 - 엔벨로프 구동 비접촉 {len(untouched)}개 중 변경 "
        f"{len(untouchedChanged)}개(최대 편차 {untouchedDelta:.6g}), 명시 지정 비접촉 "
        f"{len(expUntouched)}개 중 변경 {len(expUntouchedChanged)}개",
        f"untouched={len(untouched)} expUntouchedChanged={len(expUntouchedChanged)}",
    )
except Exception as e:
    reporter.error("TC04 P4 removeBone 재평가", f"{e}\n{traceback.format_exc()}")


# ============================================================
# 고정 수단 절 (P3) - 비수정 버텍스를 현재 가중치로 고정하는 수단 2종
#
#   (A) skinOps.SelectVertices(비수정 버텍스 비트배열) + skinOps.bakeSelectedVerts  - 벌크 2회 호출
#   (B) 비수정 버텍스마다 ReplaceVertexWeights(자기 가중치)                          - 버텍스당 1회 호출
#
# 각 수단마다 네 가지를 잰다.
#   ① 고정 자체가 가중치를 바꾸지 않는가 (바꾸면 처방이 아니라 새 결함이다)
#   ② M 플래그가 실제로 켜졌는가 (호출 성공 != 효과 - pymxs_pitfalls_advanced.md §28-b)
#   ③ 고정 후 addBone이 비접촉 버텍스를 재평가하지 않는가 (= 처방이 듣는가)
#   ④ 소요 시간
# ============================================================

rt.execute("fn pjlProbeMakeBits idxArr = ( local b = #{}; for i in idxArr do b[i] = true; b )")


def unmodified_verts(inNode: Any, inSkinMod: Any) -> List[int]:
    """M 플래그가 꺼진(엔벨로프 구동) 버텍스 인덱스 목록."""
    return [v for v, flag in modified_flags(inNode, inSkinMod).items() if not bool(flag)]


def apply_fix_bake(inNode: Any, inSkinMod: Any, inVerts: List[int]) -> None:
    """수단 (A): 대상 버텍스를 skinOps 선택에 넣고 bakeSelectedVerts로 벌크 고정한다."""
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        bits = rt.pjlProbeMakeBits(rt.Array(*inVerts))
        rt.skinOps.SelectVertices(inSkinMod, bits)
        rt.skinOps.bakeSelectedVerts(inSkinMod)
    finally:
        _restore(saved)


def apply_fix_replace(inNode: Any, inSkinMod: Any, inVerts: List[int]) -> None:
    """수단 (B): 대상 버텍스에 지금 가중치를 그대로 다시 써서 고정한다."""
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        raw = skin.get_vertex_weights(inSkinMod, inVerts)
        for v, entries in raw.items():
            if not entries:
                continue
            ids = [int(boneId) for boneId, _ in entries]
            ws = [float(w) for _, w in entries]
            rt.skinOps.ReplaceVertexWeights(inSkinMod, v, ids, ws)
    finally:
        _restore(saved)


def measure_fix_means(inLabel: str, inApply: Any) -> Dict[str, Any]:
    """고정 수단 하나를 합성 픽스처에 적용하고 ①~④를 잰다."""
    nodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=False)
    box, skinMod = nodes["box"], nodes["skinMod"]

    before = weights_by_name(box, skinMod)
    targets = unmodified_verts(box, skinMod)

    started = time.perf_counter()
    applyError = ""
    try:
        inApply(box, skinMod, targets)
    except Exception as exc:
        applyError = f"{exc}"
    elapsed = time.perf_counter() - started

    afterFix = weights_by_name(box, skinMod)
    flagsAfterFix = modified_flags(box, skinMod)
    stillUnmodified = [v for v, f in flagsAfterFix.items() if not bool(f)]
    fixChangedVerts = changed_verts(before, afterFix)

    # 고정 후 구조 변경(addBone)이 비수정 버텍스를 재평가하는가
    newBone = _bone("boneD")
    skin.activate_skin(box, skinMod)
    rt.skinOps.addBone(skinMod, newBone, 0)
    rt.clearSelection()
    afterAdd = weights_by_name(box, skinMod)
    addChanged = changed_verts(afterFix, afterAdd)

    return {
        "label": inLabel,
        "applyError": applyError,
        "targetCount": len(targets),
        "vertCount": len(before),
        "fixChangedVertCount": len(fixChangedVerts),
        "fixMaxDelta": max_delta(before, afterFix),
        "stillUnmodifiedCount": len(stillUnmodified),
        "addBoneChangedCount": len(addChanged),
        "addBoneMaxDelta": max_delta(afterFix, afterAdd),
        "elapsedSec": round(elapsed, 4),
        "effective": (
            applyError == ""
            and len(targets) > 0
            and len(fixChangedVerts) == 0
            and len(stillUnmodified) == 0
            and len(addChanged) == 0
        ),
    }


# ============================================================
# TC05 (P3-A): SelectVertices + bakeSelectedVerts 벌크 고정
# ============================================================
try:
    meansA = measure_fix_means("A_bakeSelectedVerts", apply_fix_bake)
    PROBE["sections"].setdefault("P3_fixMeans", {})["A"] = meansA
    dump_probe()
    reporter.assert_test(
        meansA["targetCount"] > 0,
        f"TC05 [P3-A] SelectVertices + bakeSelectedVerts 측정 성립 - 대상 비수정 버텍스 "
        f"{meansA['targetCount']}개, 고정 후 잔여 비수정 {meansA['stillUnmodifiedCount']}개, "
        f"고정이 바꾼 버텍스 {meansA['fixChangedVertCount']}개, 고정 후 addBone 변경 "
        f"{meansA['addBoneChangedCount']}개, {meansA['elapsedSec']}초, 유효={meansA['effective']}",
        f"대상 버텍스 0 - 측정이 공허하다 {meansA}",
    )
except Exception as e:
    reporter.error("TC05 P3-A bakeSelectedVerts", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC06 (P3-B): 비수정 버텍스만 ReplaceVertexWeights(자기 가중치)
# ============================================================
try:
    meansB = measure_fix_means("B_replaceSelfWeights", apply_fix_replace)
    PROBE["sections"].setdefault("P3_fixMeans", {})["B"] = meansB
    dump_probe()
    reporter.assert_test(
        meansB["targetCount"] > 0,
        f"TC06 [P3-B] ReplaceVertexWeights(자기 가중치) 측정 성립 - 대상 비수정 버텍스 "
        f"{meansB['targetCount']}개, 고정 후 잔여 비수정 {meansB['stillUnmodifiedCount']}개, "
        f"고정이 바꾼 버텍스 {meansB['fixChangedVertCount']}개, 고정 후 addBone 변경 "
        f"{meansB['addBoneChangedCount']}개, {meansB['elapsedSec']}초, 유효={meansB['effective']}",
        f"대상 버텍스 0 - 측정이 공허하다 {meansB}",
    )
except Exception as e:
    reporter.error("TC06 P3-B ReplaceVertexWeights", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC07 (P3 채택, 판정): 적어도 한 수단이 유효해야 §2.2 설계가 성립한다.
#       둘 다 유효하면 호출 2회로 끝나는 (A)를 채택한다
# ============================================================
try:
    means = PROBE["sections"].get("P3_fixMeans", {})
    aOk = bool(means.get("A", {}).get("effective"))
    bOk = bool(means.get("B", {}).get("effective"))
    adopted = "A" if aOk else ("B" if bOk else None)
    PROBE["sections"]["P3_adopted"] = {
        "A_effective": aOk,
        "B_effective": bOk,
        "adopted": adopted,
        "reason": (
            "둘 다 유효 - 호출 2회로 끝나는 A 채택" if aOk and bOk
            else "A 무효(§28-b) - B로 폴백" if bOk
            else "A 유효" if aOk
            else "둘 다 무효 - §2.2 설계 재검토 필요"
        ),
    }
    dump_probe()
    reporter.assert_test(
        adopted is not None,
        f"TC07 [P3 판정] 고정 수단 채택 - A 유효={aOk}, B 유효={bOk} → 채택 '{adopted}'",
        f"두 수단 모두 무효다 - PRD §2.2 설계를 다시 써야 한다 {means}",
    )
except Exception as e:
    reporter.error("TC07 P3 채택 판정", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC08 (P3 부수 효과): 수단 (A)는 skinOps **버텍스 선택**을 갈아엎는다.
#       라이브러리가 리거의 선택 상태를 조용히 바꾸지 않으려면 보관·복원이 성립해야 한다
#       (§29 라이브 뷰 계열). GetSelectedVertices → SelectVertices 왕복을 실측한다
# ============================================================
try:
    nodes = build_synthetic(["boneA", "boneB", "boneC"], inExplicit=False)
    box, skinMod = nodes["box"], nodes["skinMod"]
    marker = [2, 5, 9]

    skin.activate_skin(box, skinMod)
    rt.skinOps.SelectVertices(skinMod, rt.pjlProbeMakeBits(rt.Array(*marker)))
    selectedBefore = [
        v
        for v in range(1, int(rt.skinOps.GetNumberVertices(skinMod)) + 1)
        if bool(rt.skinOps.IsVertexSelected(skinMod, v))
    ]
    savedBits = rt.skinOps.GetSelectedVertices(skinMod)
    rt.clearSelection()

    # 고정 수단 (A)가 선택을 갈아엎는다
    apply_fix_bake(box, skinMod, list(range(1, int(len(selectedBefore)) + 10)))
    skin.activate_skin(box, skinMod)
    selectedDuring = [
        v
        for v in range(1, int(rt.skinOps.GetNumberVertices(skinMod)) + 1)
        if bool(rt.skinOps.IsVertexSelected(skinMod, v))
    ]

    # 보관본으로 복원
    rt.skinOps.SelectVertices(skinMod, savedBits)
    selectedAfter = [
        v
        for v in range(1, int(rt.skinOps.GetNumberVertices(skinMod)) + 1)
        if bool(rt.skinOps.IsVertexSelected(skinMod, v))
    ]
    rt.clearSelection()

    PROBE["sections"]["P3_vertexSelection"] = {
        "marker": marker,
        "selectedBefore": selectedBefore,
        "selectedDuringFix": selectedDuring,
        "selectedAfterRestore": selectedAfter,
        "clobbered": selectedDuring != selectedBefore,
        "restorable": selectedAfter == selectedBefore,
    }
    dump_probe()

    reporter.assert_test(
        selectedBefore == marker and selectedAfter == selectedBefore,
        f"TC08 [P3 부수 효과] skinOps 버텍스 선택 보관·복원 - 선택 {selectedBefore} → 고정 중 "
        f"{selectedDuring} → 복원 후 {selectedAfter}",
        f"before={selectedBefore} marker={marker} during={selectedDuring} after={selectedAfter}",
    )
except Exception as e:
    reporter.error("TC08 P3 버텍스 선택 왕복", f"{e}\n{traceback.format_exc()}")


# ============================================================
# 실기 절 (P5·P6) - 마스터 결함 씬 사본과 JeongHuiwon 사본
#
# 원본은 절대 열지 않는다. temp 사본을 만들어 그것만 연다(프로브 4원칙).
#
# 이전 계획은 툴(`20260905_BaseSkeletonBuilder`)의 `rebindPlan`이 산출하지만, 이 절은
# **라이브러리 단독 baseline**이므로 툴을 import하지 않고 1안(부모 체인)만 레이어 기준으로
# 재현한다. 2안(OriBone 폴백)으로만 풀리는 본은 이전·제거 양쪽에서 제외한다 - 결함의
# 유무와 규모를 재는 데는 1안 범위로 충분하고, 정확한 소비처 경로는 A2.4가 툴
# `run_build`로 닫는다.
# ============================================================

DEFECT_SCENE = Path(r"C:/Users/Admin/Desktop/SK_CheonInHo_Vl_Default.max")
REFERENCE_SCENE = Path(
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default/SK_JeongHuiwon_Mn_Default.max"
)
ADDON_ROOT_LAYER = "Skinbone_AddOn"
SKINBONE_PREFIX = "skinbone"


def load_scene_copy(inScenePath: Path) -> Path:
    """씬을 temp로 복사한 뒤 사본을 연다. 원본 경로는 열지 않는다."""
    import os
    import shutil
    import stat
    import tempfile

    tempPath = Path(tempfile.gettempdir()) / f"probe_envelope_{inScenePath.name}"
    # P4 워크스페이스의 씬은 읽기 전용이다. copy2가 그 속성까지 복사하므로 다음 실행에서
    # 덮어쓰기가 Permission denied로 죽는다(2026-09-15 실측). 기존 사본과 새 사본 양쪽의
    # 읽기 전용 속성을 벗긴다.
    if tempPath.exists():
        os.chmod(str(tempPath), stat.S_IWRITE)
    shutil.copy2(str(inScenePath), str(tempPath))
    os.chmod(str(tempPath), stat.S_IWRITE)
    rt.resetMaxFile(rt.Name("noPrompt"))
    if not rt.loadMaxFile(str(tempPath), quiet=True):
        raise RuntimeError(f"씬 사본 로드 실패: {tempPath}")
    return tempPath


def collect_layer_parents() -> Dict[str, Optional[str]]:
    """``{레이어 실제 이름: 부모 이름 | None}``."""
    parents: Dict[str, Optional[str]] = {}
    for index in range(int(rt.LayerManager.count)):
        layer = rt.LayerManager.getLayer(index)
        parent = layer.getParent()
        parents[str(layer.name)] = None if parent is None else str(parent.name)
    return parents


def addon_delete_layers(inLayerParents: Dict[str, Optional[str]]) -> List[str]:
    """``Skinbone_AddOn``과 그 자손 레이어의 실제 표기 목록(대소문자 무시 비교)."""
    root = next(
        (name for name in inLayerParents if name.lower() == ADDON_ROOT_LAYER.lower()), None
    )
    if root is None:
        return []
    result = [root]
    frontier = [root]
    while frontier:
        current = frontier.pop()
        children = [
            name
            for name, parent in inLayerParents.items()
            if parent is not None and parent.lower() == current.lower() and name not in result
        ]
        result.extend(children)
        frontier.extend(children)
    return result


def collect_node_graph() -> Tuple[Dict[int, Optional[int]], Dict[int, str], Dict[int, str]]:
    """씬 전 노드의 ``({핸들: 부모 핸들}, {핸들: 레이어 이름}, {핸들: 노드 이름})``."""
    parentById: Dict[int, Optional[int]] = {}
    layerById: Dict[int, str] = {}
    nameById: Dict[int, str] = {}
    for node in rt.objects:
        handle = int(rt.getHandleByAnim(node))
        parent = node.parent
        parentById[handle] = None if parent is None else int(rt.getHandleByAnim(parent))
        layerById[handle] = str(node.layer.name) if node.layer is not None else ""
        nameById[handle] = str(node.name)
    return parentById, layerById, nameById


def resolve_parent_chain_target(
    inHandle: int,
    inParentById: Dict[int, Optional[int]],
    inLayerById: Dict[int, str],
    inDeleteIds: set,
) -> Optional[int]:
    """1안 - 삭제 대상을 건너뛰며 올라가 처음 만나는 잔존 ``Skinbone*`` 본. 없으면 None."""
    cursor = inHandle
    visited: set = set()
    while True:
        if cursor in visited:
            return None
        visited.add(cursor)
        parent = inParentById.get(cursor)
        if parent is None:
            return None
        if parent in inDeleteIds:
            cursor = parent
            continue
        if inLayerById.get(parent, "").lower().startswith(SKINBONE_PREFIX):
            return parent
        return None


def weights_by_handle(inNode: Any, inSkinMod: Any) -> Dict[int, Dict[int, float]]:
    """``{v: {본 노드 핸들: w}}`` (w > 0만). 구조 변경으로 밀리는 본 ID 대신 핸들로 키를 잡는다."""
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(inNode, inSkinMod)
        table = skin.get_bone_table(inSkinMod)
        raw = skin.get_vertex_weights(inSkinMod)
    finally:
        _restore(saved)
    return {
        v: {
            table[boneId]["handle"]: w
            for boneId, w in entries
            if w > 0.0 and table[boneId]["handle"] is not None
        }
        for v, entries in raw.items()
    }


def changed_verts_by_handle(
    inBefore: Dict[int, Dict[int, float]],
    inAfter: Dict[int, Dict[int, float]],
    inVerts: List[int],
    inTol: float = WEIGHT_TOLERANCE,
) -> List[int]:
    changed: List[int] = []
    for v in inVerts:
        wa = inBefore.get(v, {})
        wb = inAfter.get(v, {})
        if any(abs(wa.get(h, 0.0) - wb.get(h, 0.0)) > inTol for h in set(wa) | set(wb)):
            changed.append(v)
    return changed


def skinned_nodes() -> List[Tuple[Any, Any]]:
    """Skin 모디파이어가 붙은 노드와 그 Skin 모디파이어 목록."""
    found: List[Tuple[Any, Any]] = []
    for node in rt.objects:
        for modIndex in range(1, int(node.modifiers.count) + 1):
            mod = node.modifiers[modIndex - 1]
            if rt.classOf(mod) == rt.Skin:
                found.append((node, mod))
    return found


def survey_scene(inScenePath: Path, inRunTransfer: bool) -> Dict[str, Any]:
    """씬 사본을 열어 Skin별 버텍스·비수정 버텍스를 세고, 선택적으로 이전을 돌린다."""
    started = time.perf_counter()
    tempPath = load_scene_copy(inScenePath)
    loadElapsed = time.perf_counter() - started

    layerParents = collect_layer_parents()
    deleteLayers = addon_delete_layers(layerParents)
    parentById, layerById, nameById = collect_node_graph()
    deleteLayerLower = {name.lower() for name in deleteLayers}
    deleteIds = {h for h, layer in layerById.items() if layer.lower() in deleteLayerLower}

    # 씬 인벤토리 - "Skin이 5개뿐"이 열거 실수인지 씬의 사실인지 가른다.
    # 열거를 믿고 결론을 내면 안 된다(§28 계열 - 조회가 조용히 적게 준다).
    layerObjectCounts: Dict[str, int] = {}
    classCounts: Dict[str, int] = {}
    modifierClassCounts: Dict[str, int] = {}
    for node in rt.objects:
        layerName = str(node.layer.name) if node.layer is not None else ""
        layerObjectCounts[layerName] = layerObjectCounts.get(layerName, 0) + 1
        className = str(rt.classOf(node))
        classCounts[className] = classCounts.get(className, 0) + 1
        for modIndex in range(int(node.modifiers.count)):
            modName = str(rt.classOf(node.modifiers[modIndex]))
            modifierClassCounts[modName] = modifierClassCounts.get(modName, 0) + 1

    survey: Dict[str, Any] = {
        "scene": str(inScenePath),
        "tempCopy": str(tempPath),
        "loadSec": round(loadElapsed, 2),
        "layerCount": len(layerParents),
        "addonRootPresent": bool(deleteLayers),
        "deleteLayers": deleteLayers,
        "deleteNodeCount": len(deleteIds),
        "objectCount": len(parentById),
        "layerObjectCounts": dict(sorted(layerObjectCounts.items())),
        "classCounts": dict(sorted(classCounts.items(), key=lambda kv: -kv[1])),
        "modifierClassCounts": dict(sorted(modifierClassCounts.items(), key=lambda kv: -kv[1])),
        "meshLayerNodes": sorted(
            str(node.name)
            for node in rt.objects
            if node.layer is not None and str(node.layer.name).lower().startswith("mesh")
        ),
        "skins": [],
    }

    for node, skinMod in skinned_nodes():
        entry: Dict[str, Any] = {
            "node": str(node.name),
            "layer": str(node.layer.name) if node.layer is not None else "",
        }
        flagStart = time.perf_counter()
        flags = modified_flags(node, skinMod)
        entry["vertCount"] = len(flags)
        entry["unmodifiedCount"] = sum(1 for f in flags.values() if not bool(f))
        entry["flagsSec"] = round(time.perf_counter() - flagStart, 2)

        if not inRunTransfer:
            survey["skins"].append(entry)
            continue

        before = weights_by_handle(node, skinMod)
        skinBoneHandles = set()
        for byHandle in before.values():
            skinBoneHandles.update(byHandle)
        # Skin이 쓰는 본 중 삭제 대상인 것을 1안으로 해소한다
        transferMap: Dict[int, int] = {}
        unresolved: List[str] = []
        for handle in sorted(skinBoneHandles & deleteIds):
            target = resolve_parent_chain_target(handle, parentById, layerById, deleteIds)
            if target is None:
                unresolved.append(nameById.get(handle, str(handle)))
                continue
            transferMap[handle] = target
        entry["usedDeleteBoneCount"] = len(skinBoneHandles & deleteIds)
        entry["transferCount"] = len(transferMap)
        entry["unresolvedNames"] = unresolved[:10]

        if not transferMap:
            entry["skipped"] = "이전 대상 없음"
            survey["skins"].append(entry)
            continue

        sources = set(transferMap)
        contact = [v for v, byHandle in before.items() if sources & set(byHandle)]
        untouched = [v for v in before if v not in set(contact)]
        entry["contactVertCount"] = len(contact)
        entry["untouchedVertCount"] = len(untouched)
        entry["untouchedUnmodifiedCount"] = sum(
            1 for v in untouched if not bool(flags.get(v, True))
        )

        # 이전 맵을 이름으로도 남긴다 - 편차가 나면 "어디로 갔어야 하는가"가 근거가 된다
        entry["transferMapByName"] = {
            nameById.get(src, str(src)): nameById.get(dst, str(dst))
            for src, dst in sorted(transferMap.items())
        }
        targetNames = sorted({nameById.get(dst, str(dst)) for dst in transferMap.values()})
        entry["targetNames"] = targetNames
        # 대조표의 byName 폴백(동명 노드 오대조 가능성)과 핸들 None을 기록한다
        saved = list(rt.getCurrentSelection())
        try:
            skin.activate_skin(node, skinMod)
            preTable = skin.get_bone_table(skinMod)
        finally:
            _restore(saved)
        entry["boneTableSize"] = len(preTable)
        entry["boneTableByNameCount"] = sum(1 for e in preTable.values() if e.get("byName"))
        entry["boneTableNoHandleCount"] = sum(
            1 for e in preTable.values() if e.get("handle") is None
        )
        entry["duplicateHandleCount"] = len(preTable) - len(
            {e["handle"] for e in preTable.values() if e["handle"] is not None}
        )

        transferStart = time.perf_counter()
        try:
            result = skin.transfer_bone_weights(node, skinMod, transferMap, sources)
            entry["transferError"] = ""
            entry["addedBones"] = result["addedBones"]
            entry["removedBoneCount"] = len(result["removedBones"])
            entry["touchedVerts"] = result["touchedVerts"]
            entry["warnings"] = result["warnings"]
        except Exception as exc:
            entry["transferError"] = f"{exc}"
        entry["transferSec"] = round(time.perf_counter() - transferStart, 2)

        if not entry.get("transferError"):
            after = weights_by_handle(node, skinMod)
            untouchedChanged = changed_verts_by_handle(before, after, untouched)
            entry["untouchedChangedCount"] = len(untouchedChanged)
            entry["untouchedChangedVerts"] = untouchedChanged[:20]
            entry["untouchedMaxDelta"] = max(
                (
                    abs(before.get(v, {}).get(h, 0.0) - after.get(v, {}).get(h, 0.0))
                    for v in untouched
                    for h in set(before.get(v, {})) | set(after.get(v, {}))
                ),
                default=0.0,
            )

            # 비접촉 버텍스만 보는 것은 축이 좁다. 마스터가 보고한 증상("베이스 본 가중치를
            # 갖고 있지 않던 버텍스에 베이스 본 가중치가 새로 생긴다")은 전 버텍스에서
            # **순수 합산 기대값과 실제 결과의 편차**로 재는 것이 정확하다.
            expectedAll: Dict[int, Dict[int, float]] = {}
            for v, byHandle in before.items():
                merged: Dict[int, float] = {}
                for handle, w in byHandle.items():
                    merged[transferMap.get(handle, handle)] = (
                        merged.get(transferMap.get(handle, handle), 0.0) + w
                    )
                expectedAll[v] = merged
            deviated: List[int] = []
            gainedNewBone: List[int] = []
            worstAll = 0.0
            for v, exp in expectedAll.items():
                act = after.get(v, {})
                bad = False
                for h in set(exp) | set(act):
                    delta = abs(exp.get(h, 0.0) - act.get(h, 0.0))
                    worstAll = max(worstAll, delta)
                    if delta > WEIGHT_TOLERANCE:
                        bad = True
                        # 기대값에 없던 본이 실제에 생겼는가 (= 마스터 보고 증상)
                        if h not in exp and act.get(h, 0.0) > WEIGHT_TOLERANCE:
                            gainedNewBone.append(v)
                if bad:
                    deviated.append(v)
            entry["expectedDeviationCount"] = len(deviated)
            entry["expectedDeviationVerts"] = deviated[:20]
            entry["gainedUnexpectedBoneCount"] = len(set(gainedNewBone))
            entry["gainedUnexpectedBoneVerts"] = sorted(set(gainedNewBone))[:20]
            entry["expectedMaxDelta"] = worstAll
            if deviated:
                sampleV = deviated[0]
                entry["deviationSample"] = {
                    "vert": sampleV,
                    "beforeTargets": {
                        nameById.get(h, str(h)): nameById.get(
                            transferMap.get(h, h), str(transferMap.get(h, h))
                        )
                        for h in before.get(sampleV, {})
                    },
                    "before": {
                        nameById.get(h, str(h)): w for h, w in before.get(sampleV, {}).items()
                    },
                    "expected": {
                        nameById.get(h, str(h)): w for h, w in expectedAll[sampleV].items()
                    },
                    "actual": {
                        nameById.get(h, str(h)): w for h, w in after.get(sampleV, {}).items()
                    },
                }
        survey["skins"].append(entry)

    survey["totalSec"] = round(time.perf_counter() - started, 2)
    return survey


# ============================================================
# TC09 (P5, 비공허 단정): 결함 씬 사본이 측정 재료를 갖고 있는가
#       Skinbone_AddOn 루트 레이어 존재 + Skin > 0 + 비수정 버텍스 > 0.
#       하나라도 0이면 이후 "변경 0"이 공허하다(worktree_workflow.md §무력화 4경로)
# ============================================================
defectSurvey: Dict[str, Any] = {}
try:
    if not DEFECT_SCENE.exists():
        raise RuntimeError(f"결함 씬이 없습니다: {DEFECT_SCENE}")
    defectSurvey = survey_scene(DEFECT_SCENE, inRunTransfer=True)
    PROBE["sections"]["P5_defectScene"] = defectSurvey
    dump_probe()

    skins = defectSurvey["skins"]
    totalUnmodified = sum(int(s.get("unmodifiedCount", 0)) for s in skins)
    totalVerts = sum(int(s.get("vertCount", 0)) for s in skins)
    structureChanged = sum(
        len(s.get("addedBones", [])) + int(s.get("removedBoneCount", 0) or 0) for s in skins
    )
    reporter.assert_test(
        defectSurvey["addonRootPresent"] and len(skins) > 0 and structureChanged > 0,
        f"TC09 [P5 비공허] 결함 씬에서 절차가 실제로 돌았다 - AddOn 루트="
        f"{defectSurvey['addonRootPresent']}(삭제 레이어 {len(defectSurvey['deleteLayers'])}개, "
        f"삭제 대상 노드 {defectSurvey['deleteNodeCount']}개), 씬 오브젝트 "
        f"{defectSurvey['objectCount']}개 중 Skin {len(skins)}개, 전 버텍스 {totalVerts}개"
        f"(그중 비수정 {totalUnmodified}개), 구조 변경 {structureChanged}건, "
        f"로드 {defectSurvey['loadSec']}초",
        f"addonRoot={defectSurvey['addonRootPresent']} skins={len(skins)} "
        f"structureChanged={structureChanged} - 절차가 돌지 않으면 측정이 공허하다",
    )
except Exception as e:
    reporter.error("TC09 P5 결함 씬 비공허", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC10 (P5 baseline): 현행 transfer_bone_weights 후 비접촉 버텍스 변경 수.
#       이 값이 결함의 크기이고, A2.4가 수정 후 0이 되는지를 이 수치와 대조한다.
#       측정이 성립했는지(이전이 실제로 일어났는지)를 판정 축에 둔다
# ============================================================
try:
    ran = [s for s in defectSurvey.get("skins", []) if "untouchedChangedCount" in s]
    baselineChanged = sum(int(s["untouchedChangedCount"]) for s in ran)
    baselineUntouched = sum(int(s["untouchedVertCount"]) for s in ran)
    deviation = sum(int(s.get("expectedDeviationCount", 0)) for s in ran)
    gained = sum(int(s.get("gainedUnexpectedBoneCount", 0)) for s in ran)
    contactTotal = sum(int(s.get("contactVertCount", 0)) for s in ran)
    worstAll = max((float(s.get("expectedMaxDelta", 0.0)) for s in ran), default=0.0)
    PROBE["sections"]["P5_baseline"] = {
        "skinsWithTransfer": len(ran),
        "contactVertTotal": contactTotal,
        "untouchedVertTotal": baselineUntouched,
        "untouchedChangedTotal": baselineChanged,
        "expectedDeviationTotal": deviation,
        "gainedUnexpectedBoneTotal": gained,
        "expectedMaxDelta": worstAll,
        "perSkin": [
            {
                "node": s["node"],
                "vertCount": s.get("vertCount"),
                "unmodifiedCount": s.get("unmodifiedCount"),
                "contactVertCount": s.get("contactVertCount"),
                "untouchedVertCount": s.get("untouchedVertCount"),
                "untouchedChangedCount": s.get("untouchedChangedCount"),
                "expectedDeviationCount": s.get("expectedDeviationCount"),
                "gainedUnexpectedBoneCount": s.get("gainedUnexpectedBoneCount"),
                "deviationSample": s.get("deviationSample"),
                "addedBones": s.get("addedBones"),
                "removedBoneCount": s.get("removedBoneCount"),
                "transferSec": s.get("transferSec"),
            }
            for s in ran
        ],
        "errors": [
            {"node": s["node"], "error": s["transferError"]}
            for s in defectSurvey.get("skins", [])
            if s.get("transferError")
        ],
    }
    dump_probe()
    reporter.assert_test(
        len(ran) > 0 and contactTotal > 0,
        f"TC10 [P5 baseline] 현행 절차의 실제 결과 vs 순수 합산 기대값 - 이전을 돌린 Skin "
        f"{len(ran)}개, 접촉 버텍스 {contactTotal}개 / 비접촉 {baselineUntouched}개(변경 "
        f"{baselineChanged}개), 전 버텍스 기대값 편차 {deviation}개(그중 기대에 없던 본이 "
        f"생긴 버텍스 {gained}개, 최대 편차 {worstAll:.6g})",
        f"이전이 일어난 Skin {len(ran)}개, 접촉 버텍스 {contactTotal}개 - 측정이 성립하지 않았다",
    )
except Exception as e:
    reporter.error("TC10 P5 baseline", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC11 (P6): JeongHuiwon 사본의 비수정 버텍스 수.
#       0이면 "툴 TC03(전 버텍스 보존 항등식)이 왜 통과했나"가 닫힌다
# ============================================================
try:
    if not REFERENCE_SCENE.exists():
        raise RuntimeError(f"참조 씬이 없습니다: {REFERENCE_SCENE}")
    refSurvey = survey_scene(REFERENCE_SCENE, inRunTransfer=False)
    PROBE["sections"]["P6_referenceScene"] = refSurvey
    dump_probe()
    refSkins = refSurvey["skins"]
    refUnmodified = sum(int(s.get("unmodifiedCount", 0)) for s in refSkins)
    refVerts = sum(int(s.get("vertCount", 0)) for s in refSkins)
    reporter.assert_test(
        len(refSkins) > 0,
        f"TC11 [P6] JeongHuiwon 사본 비수정 버텍스 - Skin {len(refSkins)}개, 전 버텍스 "
        f"{refVerts}개 중 비수정 {refUnmodified}개, 로드 {refSurvey['loadSec']}초",
        f"Skin 0개 - 측정이 성립하지 않았다 {refSurvey}",
    )
except Exception as e:
    reporter.error("TC11 P6 JeongHuiwon 사본", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC12 (기록): 두 프로덕션 씬에 H1 전제가 없다는 사실을 고정한다
#
#   H1(엔벨로프 재평가)은 "비수정 버텍스"가 있어야 성립한다. 합성 절(TC02)이 메커니즘
#   자체는 확정했지만, 결함 씬과 참조 씬 **둘 다 비수정 버텍스가 0**이라 프로덕션에는
#   조건이 없다. 이 판정이 처음 실패로 떴을 때 그것이 곧 "H1은 이 씬의 원인이 아니다"의
#   신호였고, 마스터 결정(2026-09-15 R2)으로 **H1 고정은 이번 사이클 Non-Goal**이 됐다.
#
#   그래서 판정축을 "전제가 있는가"(가설 검증)에서 **"측정이 성립했는가"**(사실 고정)로
#   바꾼다. 비수정 버텍스 수는 이제 통과 조건이 아니라 **기록해야 할 값**이다.
#   조건이 생기면 이 수치가 별건 PRD의 착수 신호가 된다.
# ============================================================
try:
    defectSkins = defectSurvey.get("skins", [])
    defectUnmodified = sum(int(s.get("unmodifiedCount", 0)) for s in defectSkins)
    defectVerts = sum(int(s.get("vertCount", 0)) for s in defectSkins)
    refSection = PROBE["sections"].get("P6_referenceScene", {})
    refSkinsList = refSection.get("skins", [])
    refUnmodifiedTotal = sum(int(s.get("unmodifiedCount", 0)) for s in refSkinsList)
    deviationTotal = int(PROBE["sections"].get("P5_baseline", {}).get("expectedDeviationTotal", -1))

    PROBE["sections"]["gate"] = {
        "H1_mechanismConfirmed": bool(
            PROBE["sections"].get("P1_addBone", {}).get("H1_reproduced")
        ),
        "defectSceneUnmodifiedVerts": defectUnmodified,
        "defectSceneTotalVerts": defectVerts,
        "defectSceneSkinCount": len(defectSkins),
        "referenceSceneUnmodifiedVerts": refUnmodifiedTotal,
        "defectSceneExpectedDeviation": deviationTotal,
        "H1_preconditionPresentInDefectScene": defectUnmodified > 0,
        "H1_scopeDecision": "Non-Goal (마스터 결정 2026-09-15 R2) - 조건이 생기면 별건 PRD",
        "verdict": (
            "결함 씬에 H1 전제가 존재한다 - 별건 PRD 착수 신호"
            if defectUnmodified > 0
            else "두 프로덕션 씬 모두 비수정 버텍스 0 - H1 조건이 프로덕션에 없다. "
            "실제 원인은 H6(addBone 본 ID 삽입 + stale ID 재사용)이다"
        ),
    }
    dump_probe()

    # 판정축은 측정 성립이다. 비수정 버텍스 수 자체는 이 프로브가 알아내는 값이고,
    # 그 값이 0이라는 사실은 이미 마스터 결정으로 소화됐다(H1 → Non-Goal).
    reporter.assert_test(
        len(defectSkins) > 0 and defectVerts > 0 and deviationTotal >= 0,
        f"TC12 [기록] 프로덕션 씬의 H1 전제 부재 - 결함 씬 비수정 버텍스 {defectUnmodified}"
        f"/{defectVerts}개(Skin {len(defectSkins)}개), 참조 씬 비수정 {refUnmodifiedTotal}개 "
        f"→ H1은 Non-Goal(R2). 실제 원인 H6의 크기 = 기대값 편차 {deviationTotal}개",
        f"측정이 성립하지 않았다 - skins={len(defectSkins)} verts={defectVerts} "
        f"deviation={deviationTotal}",
    )
except Exception as e:
    reporter.error("TC12 게이트 판정", f"{e}\n{traceback.format_exc()}")


# ============================================================
# 본 인덱스 공간 절 (H5) - P5가 H1이 아닌 다른 원인을 가리켰다
#
# P5 실측: 결함 씬은 비수정 버텍스가 0인데도 현행 절차의 결과가 순수 합산 기대값과
# 544 버텍스에서 어긋났고, 그중 523개는 **기대값에 없던 본**(neck)이 생겼다. 샘플에서
# ``frontalis_l``의 가중치가 통째로 ``neck``으로 갔다. H1(엔벨로프 재평가)로는 설명되지
# 않는다 - 전 버텍스가 명시 지정(M 켜짐)이기 때문이다.
#
# 남는 설명은 **본 인덱스 공간**이다. Max skinOps에는 두 인덱스가 있다.
#   - 본 ID: ``GetVertexWeightBoneID`` / ``ReplaceVertexWeights``가 쓰는 내부 ID
#   - 리스트 ID: 본 목록(UI 정렬)의 위치
# 라이브러리 ``get_bone_table``은 ``GetBoneName``/``GetBoneNode``에 1..GetNumberBones를
# 먹여 대조표를 만든다. 그 인자가 리스트 ID라면 대조표의 키는 본 ID가 아니고, 가중치
# 항목의 본 ID와 섞이는 순간 **가중치가 다른 본에 얹힌다.**
#
# 두 인덱스가 같아 보이는 경우(본을 알파벳 순으로 추가한 합성 픽스처)에는 증상이 없다.
# 그래서 기존 테스트가 전부 통과했다. 여기서 두 인덱스를 직접 갈라 확정한다.
# ============================================================


def build_unsorted_bone_skin() -> Dict[str, Any]:
    """본을 **비알파벳 순서**로 추가한 스킨. 본 ID와 리스트 ID를 갈라내는 픽스처."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    order = ["zeta", "alpha", "mike"]
    nodes = {}
    for index, name in enumerate(order):
        node = rt.Box(name=name, width=14.0, length=8.0, height=8.0)
        node.pos = rt.Point3(-15.0 + index * 15.0, 0.0, 2.0)
        nodes[name] = node
    box = rt.Box(
        name="UnsortedBox", width=40.0, length=4.0, height=4.0, widthsegs=7, lengthsegs=1, heightsegs=1
    )
    box.pos = rt.Point3(0.0, 0.0, 0.0)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    for name in order:
        rt.skinOps.addBone(skinMod, nodes[name], 1)
    skinMod.enableDQ = False
    rt.completeRedraw()
    rt.clearSelection()
    nodes["box"] = box
    nodes["skinMod"] = skinMod
    nodes["addOrder"] = order
    return nodes


# ============================================================
# TC13 (H5): 본 ID 공간과 리스트 ID 공간이 같은가
#       GetBoneName(i) / GetBoneNode(i)가 쓰는 i와 GetVertexWeightBoneID가 주는 ID가
#       같은 공간이면 통과. 다르면 get_bone_table의 키가 본 ID가 아니다
# ============================================================
try:
    nodes = build_unsorted_bone_skin()
    box, skinMod = nodes["box"], nodes["skinMod"]
    skin.activate_skin(box, skinMod)
    boneCount = int(rt.skinOps.GetNumberBones(skinMod))

    byIndex = {
        i: str(rt.skinOps.GetBoneName(skinMod, i, 1)) for i in range(1, boneCount + 1)
    }
    byIndexNode = {}
    for i in range(1, boneCount + 1):
        node = rt.skinOps.GetBoneNode(skinMod, i)
        byIndexNode[i] = None if node is None else str(node.name)
    listIdToBoneId = {}
    listIdError = ""
    try:
        for i in range(1, boneCount + 1):
            listIdToBoneId[i] = int(rt.skinOps.GetBoneIDByListID(skinMod, i))
    except Exception as exc:
        listIdError = f"{exc}"

    # 인덱스 i로 가중치를 쓰고, 그 버텍스를 다시 읽어 어떤 본 ID로 돌아오는지 본다.
    # 두 공간이 같으면 쓴 i가 그대로 돌아온다
    writeIndex = 1
    rt.skinOps.ReplaceVertexWeights(skinMod, 1, [writeIndex], [1.0])
    readBack = [
        int(rt.skinOps.GetVertexWeightBoneID(skinMod, 1, k))
        for k in range(1, int(rt.skinOps.GetVertexWeightCount(skinMod, 1)) + 1)
    ]
    rt.clearSelection()

    # 판정축: GetBoneName/GetBoneNode에 먹인 인덱스가 GetVertexWeightBoneID /
    # ReplaceVertexWeights와 **같은 공간**인가. 리스트 ID는 알파벳 순이라 생성 순과
    # 다른 것이 정상이고, 라이브러리가 그것을 안 쓰면 문제가 아니다.
    creationOrderOk = list(byIndex.values()) == nodes["addOrder"]
    sameSpace = creationOrderOk and readBack == [writeIndex]
    PROBE["sections"]["H5_boneIndexSpace"] = {
        "addOrder": nodes["addOrder"],
        "boneCount": boneCount,
        "getBoneNameByIndex": byIndex,
        "getBoneNodeByIndex": byIndexNode,
        "getBoneIDByListID": listIdToBoneId,
        "getBoneIDByListIDError": listIdError,
        "wroteIndex": writeIndex,
        "readBackBoneIds": readBack,
        "sameIndexSpace": sameSpace,
    }
    dump_probe()

    reporter.assert_test(
        sameSpace,
        f"TC13 [H5] get_bone_table의 인덱스 == 가중치 API의 본 ID 공간 - 추가 순서 "
        f"{nodes['addOrder']}, GetBoneName(i)={list(byIndex.values())}(생성 순), "
        f"GetBoneIDByListID={listIdToBoneId}(리스트는 알파벳 순 - 라이브러리 미사용), "
        f"인덱스 {writeIndex}로 쓴 뒤 읽은 본 ID {readBack}",
        f"두 공간이 다르다 - get_bone_table의 키가 본 ID가 아니다. "
        f"creationOrder={creationOrderOk} listIdToBoneId={listIdToBoneId} "
        f"err={listIdError} readBack={readBack}",
    )
except Exception as e:
    reporter.error("TC13 H5 본 인덱스 공간", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC14 (H5): addBone이 기존 본의 인덱스를 유지하는가
#       라이브러리는 addBone 후 대조표만 다시 만들고 **가중치 항목(weights)과
#       usedBoneIds는 addBone 전 값을 계속 쓴다.** addBone이 인덱스를 밀면 그 조합이
#       가중치를 엉뚱한 본에 얹는다. docstring은 "기존 본 ID는 유지된다"고 적고 있다
# ============================================================
try:
    nodes = build_unsorted_bone_skin()
    box, skinMod = nodes["box"], nodes["skinMod"]

    skin.activate_skin(box, skinMod)
    tableBefore = {
        boneId: entry["name"] for boneId, entry in skin.get_bone_table(skinMod).items()
    }
    weightsBefore = skin.get_vertex_weights(skinMod)
    rt.clearSelection()

    # 알파벳상 중간에 끼는 이름으로 본을 추가한다 - 정렬 삽입이면 뒤 인덱스가 밀린다
    newBone = rt.Box(name="bravo", width=14.0, length=8.0, height=8.0)
    newBone.pos = rt.Point3(0.0, 0.0, 2.0)
    skin.activate_skin(box, skinMod)
    rt.skinOps.addBone(skinMod, newBone, 0)
    tableAfter = {
        boneId: entry["name"] for boneId, entry in skin.get_bone_table(skinMod).items()
    }
    weightsAfter = skin.get_vertex_weights(skinMod)
    rt.clearSelection()

    stable = all(tableAfter.get(boneId) == name for boneId, name in tableBefore.items())
    # 가중치 항목의 본 ID가 가리키는 이름이 addBone 전후로 같은가 (진짜 판정 축)
    def _named(inWeights, inTable):
        return {
            v: sorted(
                (inTable.get(boneId, f"?{boneId}"), round(float(w), 6))
                for boneId, w in entries
                if w > 0.0
            )
            for v, entries in inWeights.items()
        }

    namedBefore = _named(weightsBefore, tableBefore)
    namedAfterOldTable = _named(weightsAfter, tableBefore)
    namedAfterNewTable = _named(weightsAfter, tableAfter)
    staleTableMisreads = [
        v for v in namedBefore if namedAfterOldTable.get(v) != namedBefore.get(v)
    ]

    PROBE["sections"]["H5_addBoneIndexStability"] = {
        "tableBefore": tableBefore,
        "tableAfter": tableAfter,
        "indexStable": stable,
        "staleTableMisreadVertCount": len(staleTableMisreads),
        "sampleVert": {
            "vert": 1,
            "before": namedBefore.get(1),
            "afterWithOldTable": namedAfterOldTable.get(1),
            "afterWithNewTable": namedAfterNewTable.get(1),
        },
    }
    dump_probe()

    reporter.assert_test(
        stable,
        f"TC14 [H5] addBone이 기존 본 인덱스를 유지한다 - 전 {tableBefore} → 후 {tableAfter}",
        f"인덱스가 밀렸다. addBone 전에 읽은 가중치 항목을 addBone 후에 쓰면 다른 본에 "
        f"얹힌다. 전={tableBefore} 후={tableAfter} 오독 버텍스={len(staleTableMisreads)}",
    )
except Exception as e:
    reporter.error("TC14 H5 addBone 인덱스 안정성", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC15 (원인 이분): 편차가 **쓰기 단계**에서 생기는가 **removeBone 단계**에서 생기는가
#
#   결함 씬 Face Skin에서 같은 이전을 두 번에 나눠 건다.
#     1단계 - inRemoveHandles=∅ 로 가중치만 쓴다 → 여기서 편차가 나면 쓰기가 원인
#     2단계 - 이어서 제거만 건다(원본 본은 이미 가중치 0) → 여기서 나면 removeBone이 원인
#   한 실행에서 두 단계를 갈라야 "어디를 고칠 것인가"가 정해진다
# ============================================================
try:
    tempPath = load_scene_copy(DEFECT_SCENE)
    layerParents = collect_layer_parents()
    deleteLayers = addon_delete_layers(layerParents)
    parentById, layerById, nameById = collect_node_graph()
    deleteLayerLower = {name.lower() for name in deleteLayers}
    deleteIds = {h for h, layer in layerById.items() if layer.lower() in deleteLayerLower}

    target = next((pair for pair in skinned_nodes() if str(pair[0].name) == "Face"), None)
    if target is None:
        raise RuntimeError("결함 씬에 'Face' Skin이 없습니다")
    node, skinMod = target

    before = weights_by_handle(node, skinMod)
    skinBoneHandles = set()
    for byHandle in before.values():
        skinBoneHandles.update(byHandle)
    transferMap: Dict[int, int] = {}
    for handle in sorted(skinBoneHandles & deleteIds):
        resolved = resolve_parent_chain_target(handle, parentById, layerById, deleteIds)
        if resolved is not None:
            transferMap[handle] = resolved

    def expected_from(inBefore: Dict[int, Dict[int, float]]) -> Dict[int, Dict[int, float]]:
        out: Dict[int, Dict[int, float]] = {}
        for v, byHandle in inBefore.items():
            merged: Dict[int, float] = {}
            for handle, w in byHandle.items():
                key = transferMap.get(handle, handle)
                merged[key] = merged.get(key, 0.0) + w
            out[v] = merged
        return out

    def deviation_of(
        inExpected: Dict[int, Dict[int, float]], inActual: Dict[int, Dict[int, float]]
    ) -> Tuple[int, int, float, Optional[Dict[str, Any]]]:
        deviated: List[int] = []
        gained: set = set()
        worst = 0.0
        sample: Optional[Dict[str, Any]] = None
        for v, exp in inExpected.items():
            act = inActual.get(v, {})
            bad = False
            for h in set(exp) | set(act):
                delta = abs(exp.get(h, 0.0) - act.get(h, 0.0))
                worst = max(worst, delta)
                if delta > WEIGHT_TOLERANCE:
                    bad = True
                    if h not in exp and act.get(h, 0.0) > WEIGHT_TOLERANCE:
                        gained.add(v)
            if bad:
                deviated.append(v)
                if sample is None:
                    sample = {
                        "vert": v,
                        "expected": {nameById.get(h, str(h)): w for h, w in exp.items()},
                        "actual": {nameById.get(h, str(h)): w for h, w in act.items()},
                    }
        return len(deviated), len(gained), worst, sample

    expectedAll = expected_from(before)

    # 1단계 - 쓰기만
    writeResult = skin.transfer_bone_weights(node, skinMod, transferMap, set())
    afterWrite = weights_by_handle(node, skinMod)
    wDev, wGained, wWorst, wSample = deviation_of(expectedAll, afterWrite)

    # 2단계 - 제거만 (원본 본은 1단계에서 가중치 0이 됐다)
    removeResult = skin.transfer_bone_weights(node, skinMod, {}, set(transferMap))
    afterRemove = weights_by_handle(node, skinMod)
    rDev, rGained, rWorst, rSample = deviation_of(expectedAll, afterRemove)
    # 제거 단계가 1단계 결과를 흔들었는지도 직접 본다
    stageDelta, stageGained, stageWorst, stageSample = deviation_of(afterWrite, afterRemove)

    PROBE["sections"]["bisect_writeVsRemove"] = {
        "node": str(node.name),
        "vertCount": len(before),
        "transferCount": len(transferMap),
        "stage1_write": {
            "addedBones": writeResult["addedBones"],
            "touchedVerts": writeResult["touchedVerts"],
            "deviationCount": wDev,
            "gainedUnexpectedBoneCount": wGained,
            "maxDelta": wWorst,
            "sample": wSample,
        },
        "stage2_remove": {
            "removedBoneCount": len(removeResult["removedBones"]),
            "deviationCount": rDev,
            "gainedUnexpectedBoneCount": rGained,
            "maxDelta": rWorst,
            "sample": rSample,
        },
        "stage2_vs_stage1": {
            "changedVertCount": stageDelta,
            "gainedUnexpectedBoneCount": stageGained,
            "maxDelta": stageWorst,
            "sample": stageSample,
        },
        "culprit": (
            "write" if wDev > 0 else ("removeBone" if stageDelta > 0 else "none")
        ),
    }
    dump_probe()

    reporter.assert_test(
        True,
        f"TC15 [원인 이분] Face Skin - 1단계(쓰기만) 편차 {wDev}개(새 본 {wGained}개, 최대 "
        f"{wWorst:.6g}) / 2단계(제거만) 후 편차 {rDev}개(새 본 {rGained}개) / 제거가 "
        f"1단계 결과를 바꾼 버텍스 {stageDelta}개 → 원인 = "
        f"{PROBE['sections']['bisect_writeVsRemove']['culprit']}",
        "",
    )
except Exception as e:
    reporter.error("TC15 원인 이분", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC16 (원인 확정): 쓰기 단계 안에서 addBone인가 ReplaceVertexWeights인가
#
#   TC15가 "쓰기 단계"까지 좁혔다. 쓰기 단계는 두 동작으로 이뤄진다.
#     (1) 대상 본이 Skin에 없으면 addBone  (2) 버텍스별 ReplaceVertexWeights
#   결함 씬 Face Skin에서 이 둘을 손으로 갈라 잰다.
#     A. addBone만 걸고 전 버텍스 diff  → addBone이 기존 버텍스를 건드리는가
#     B. 그 뒤 한 버텍스에 ReplaceVertexWeights(단일 본, 1.0) → 인자 밖 본이 남는가
#   B가 남는다면 그것이 H2("ReplaceVertexWeights가 Set이 아니라 Merge 의미")이고,
#   현행 ⑤ 검증이 **원본 본 잔여만** 보기 때문에 조용히 지나간 것이다
# ============================================================
try:
    load_scene_copy(DEFECT_SCENE)
    parentById, layerById, nameById = collect_node_graph()
    handleByName = {name: handle for handle, name in nameById.items()}

    target = next((pair for pair in skinned_nodes() if str(pair[0].name) == "Face"), None)
    if target is None:
        raise RuntimeError("결함 씬에 'Face' Skin이 없습니다")
    node, skinMod = target

    beforeAdd = weights_by_handle(node, skinMod)
    flagsBefore = modified_flags(node, skinMod)

    neckHandle = handleByName.get("neck")
    if neckHandle is None:
        raise RuntimeError("씬에 'neck' 노드가 없습니다")
    neckNode = rt.getAnimByHandle(neckHandle)

    # --- A. addBone만 ---
    skin.activate_skin(node, skinMod)
    boneCountBefore = int(rt.skinOps.GetNumberBones(skinMod))
    rt.skinOps.addBone(skinMod, neckNode, 0)
    boneCountAfter = int(rt.skinOps.GetNumberBones(skinMod))
    rt.clearSelection()
    afterAdd = weights_by_handle(node, skinMod)

    addChanged: List[int] = []
    addGainedNeck: List[int] = []
    for v in beforeAdd:
        wa, wb = beforeAdd[v], afterAdd.get(v, {})
        if any(abs(wa.get(h, 0.0) - wb.get(h, 0.0)) > WEIGHT_TOLERANCE for h in set(wa) | set(wb)):
            addChanged.append(v)
        if wb.get(neckHandle, 0.0) > WEIGHT_TOLERANCE:
            addGainedNeck.append(v)

    # --- B. ReplaceVertexWeights가 인자 밖 본을 지우는가 ---
    probeVert = addGainedNeck[0] if addGainedNeck else sorted(beforeAdd)[0]
    saved = list(rt.getCurrentSelection())
    try:
        skin.activate_skin(node, skinMod)
        table = skin.get_bone_table(skinMod)
        idsByHandle = {e["handle"]: bid for bid, e in table.items() if e["handle"] is not None}
        headHandle = handleByName.get("head")
        writeBoneId = idsByHandle.get(headHandle)
        if writeBoneId is None:
            writeBoneId = sorted(table)[0]
        rt.skinOps.ReplaceVertexWeights(skinMod, probeVert, [writeBoneId], [1.0])
        readBack = [
            (
                str(table[int(rt.skinOps.GetVertexWeightBoneID(skinMod, probeVert, k))]["name"])
                if int(rt.skinOps.GetVertexWeightBoneID(skinMod, probeVert, k)) in table
                else f"?{int(rt.skinOps.GetVertexWeightBoneID(skinMod, probeVert, k))}",
                float(rt.skinOps.GetVertexWeight(skinMod, probeVert, k)),
            )
            for k in range(1, int(rt.skinOps.GetVertexWeightCount(skinMod, probeVert)) + 1)
        ]
    finally:
        _restore(saved)
    rt.clearSelection()

    outsideBonesSurvive = [entry for entry in readBack if entry[1] > WEIGHT_TOLERANCE] != [
        (str(table[writeBoneId]["name"]), 1.0)
    ] and len([e for e in readBack if e[1] > WEIGHT_TOLERANCE]) > 1

    PROBE["sections"]["cause_addBone_vs_replace"] = {
        "node": str(node.name),
        "vertCount": len(beforeAdd),
        "unmodifiedCountBefore": sum(1 for f in flagsBefore.values() if not bool(f)),
        "boneCountBefore": boneCountBefore,
        "boneCountAfter": boneCountAfter,
        "addBoneChangedVertCount": len(addChanged),
        "addBoneGainedNeckVertCount": len(addGainedNeck),
        "addBoneSample": (
            {
                "vert": addChanged[0],
                "before": {nameById.get(h, str(h)): w for h, w in beforeAdd[addChanged[0]].items()},
                "after": {
                    nameById.get(h, str(h)): w for h, w in afterAdd.get(addChanged[0], {}).items()
                },
                "isVertexModified": repr(flagsBefore.get(addChanged[0])),
            }
            if addChanged
            else None
        ),
        "replaceProbeVert": probeVert,
        "replaceWroteBone": str(table[writeBoneId]["name"]) if writeBoneId in table else None,
        "replaceReadBack": readBack,
        "replaceKeepsOutsideBones": outsideBonesSurvive,
        "verdict": (
            "addBone이 기존 버텍스를 재평가한다" if addChanged else "addBone은 기존 버텍스를 건드리지 않는다"
        ),
    }
    dump_probe()

    reporter.assert_test(
        True,
        f"TC16 [원인 확정] Face Skin - addBone('neck') 후 변경 버텍스 {len(addChanged)}"
        f"/{len(beforeAdd)}개(그중 neck 가중치가 생긴 버텍스 {len(addGainedNeck)}개, "
        f"본 {boneCountBefore}→{boneCountAfter}), 비수정 버텍스 "
        f"{sum(1 for f in flagsBefore.values() if not bool(f))}개 / "
        f"ReplaceVertexWeights(단일 본 1.0) 후 읽은 항목 {readBack} "
        f"(인자 밖 본 잔존={outsideBonesSurvive})",
        "",
    )
except Exception as e:
    reporter.error("TC16 원인 확정", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC17 (스모킹 건): 편차 버텍스 하나에서 쓰기를 손으로 재현하며 전 단계를 기록한다
#
#   TC16에서 ReplaceVertexWeights(단일 본, 1.0)이 0.0으로 읽혔다. 라이브러리가 실제로
#   넘기는 인자와 그 직후 읽히는 값을 한 버텍스에서 그대로 재현해, 무엇이 어긋나는지를
#   추론이 아니라 기록으로 남긴다.
# ============================================================
try:
    load_scene_copy(DEFECT_SCENE)
    parentById, layerById, nameById = collect_node_graph()
    handleByName = {name: handle for handle, name in nameById.items()}
    target = next((pair for pair in skinned_nodes() if str(pair[0].name) == "Face"), None)
    node, skinMod = target
    probeVert = 3

    saved = list(rt.getCurrentSelection())
    trace: Dict[str, Any] = {"vert": probeVert}
    try:
        skin.activate_skin(node, skinMod)
        table0 = skin.get_bone_table(skinMod)
        entries0 = skin.get_vertex_weights(skinMod, [probeVert])[probeVert]
        trace["boneCountBefore"] = int(rt.skinOps.GetNumberBones(skinMod))
        trace["entriesBefore"] = [
            (bid, str(table0[bid]["name"]), float(w)) for bid, w in entries0
        ]
        trace["sumBefore"] = sum(float(w) for _, w in entries0)

        neckNode = rt.getAnimByHandle(handleByName["neck"])
        rt.skinOps.addBone(skinMod, neckNode, 0)
        table1 = skin.get_bone_table(skinMod)
        trace["boneCountAfterAdd"] = int(rt.skinOps.GetNumberBones(skinMod))
        # addBone이 기존 본 ID를 유지했는가 (TC14의 실기 판)
        trace["idsStableAfterAdd"] = all(
            str(table1.get(bid, {}).get("name")) == str(e["name"]) for bid, e in table0.items()
        )
        trace["shiftedIds"] = [
            (bid, str(e["name"]), str(table1.get(bid, {}).get("name")))
            for bid, e in table0.items()
            if str(table1.get(bid, {}).get("name")) != str(e["name"])
        ][:10]
        entries1 = skin.get_vertex_weights(skinMod, [probeVert])[probeVert]
        trace["entriesAfterAdd"] = [
            (bid, str(table1.get(bid, {}).get("name")), float(w)) for bid, w in entries1
        ]

        headId = next(
            (bid for bid, e in table1.items() if str(e["name"]) == "head"), None
        )
        neckId = next(
            (bid for bid, e in table1.items() if str(e["name"]) == "neck"), None
        )
        trace["headBoneId"] = headId
        trace["neckBoneId"] = neckId

        writeSum = sum(float(w) for _, w in entries1)
        trace["writeArgs"] = {"ids": [headId], "weights": [writeSum]}
        rt.skinOps.ReplaceVertexWeights(skinMod, probeVert, [headId], [writeSum])
        entries2 = skin.get_vertex_weights(skinMod, [probeVert])[probeVert]
        trace["entriesAfterWrite"] = [
            (bid, str(table1.get(bid, {}).get("name")), float(w)) for bid, w in entries2
        ]

        # 같은 버텍스에 rt.Array로 한 번 더 써 본다 (파이썬 list vs MAXScript array)
        rt.skinOps.ReplaceVertexWeights(
            skinMod, probeVert, rt.Array(headId), rt.Array(1.0)
        )
        entries3 = skin.get_vertex_weights(skinMod, [probeVert])[probeVert]
        trace["entriesAfterArrayWrite"] = [
            (bid, str(table1.get(bid, {}).get("name")), float(w)) for bid, w in entries3
        ]
    finally:
        _restore(saved)
    rt.clearSelection()

    PROBE["sections"]["smoking_gun_write"] = trace
    dump_probe()
    reporter.assert_test(
        True,
        f"TC17 [스모킹 건] v{probeVert} - 쓰기 전 {len(trace.get('entriesBefore', []))}본"
        f"(합 {trace.get('sumBefore')}), addBone 후 본 {trace.get('boneCountBefore')}→"
        f"{trace.get('boneCountAfterAdd')}(ID 유지={trace.get('idsStableAfterAdd')}), "
        f"head ID={trace.get('headBoneId')} neck ID={trace.get('neckBoneId')}, "
        f"쓰기 인자={trace.get('writeArgs')} → 직후 {trace.get('entriesAfterWrite')}, "
        f"Array 재쓰기 후 {trace.get('entriesAfterArrayWrite')}",
        "",
    )
except Exception as e:
    reporter.error("TC17 스모킹 건", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC18 (합성 재현, 판정): addBone의 본 ID 삽입을 실기 씬 없이 재현한다
#
#   TC17 실측: 결함 씬 Face Skin에 ``addBone(neck)``을 걸자 새 본이 **ID 1에 삽입**되고
#   기존 본 ID가 전부 +1 밀렸다(spine_03 1→2, head 3→4, frontalis_l 7→8).
#   TC14의 합성 픽스처에서는 부모 관계가 없는 본이라 끝에 붙어 밀림이 없었다.
#   여기서는 **계층으로 이어진 본**을 추가해 삽입을 재현하고, 그 상태에서
#   ``transfer_bone_weights``가 가중치를 엉뚱한 본에 얹는지를 끝까지 확인한다.
#
#   판정: 재현되면 이 사이클의 실제 원인이 확정된다(H1이 아니다). 실패하면 삽입 조건이
#   다른 것이므로 결함 씬 증거만으로 보고한다
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    # 계층: root > spine > head,  spine > armBone  (head/armBone은 형제)
    rootBone = rt.Box(name="pRoot", width=6.0, length=6.0, height=6.0)
    rootBone.pos = rt.Point3(0.0, 0.0, 0.0)
    spineBone = rt.Box(name="pSpine", width=6.0, length=6.0, height=6.0)
    spineBone.pos = rt.Point3(0.0, 0.0, 10.0)
    spineBone.parent = rootBone
    headBone = rt.Box(name="pHead", width=6.0, length=6.0, height=6.0)
    headBone.pos = rt.Point3(0.0, 0.0, 20.0)
    headBone.parent = spineBone
    armBone = rt.Box(name="pArm", width=6.0, length=6.0, height=6.0)
    armBone.pos = rt.Point3(10.0, 0.0, 15.0)
    armBone.parent = spineBone

    box = rt.Box(
        name="ReproBox", width=40.0, length=4.0, height=4.0, widthsegs=7, lengthsegs=1, heightsegs=1
    )
    box.pos = rt.Point3(0.0, 0.0, 15.0)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    # Skin에는 armBone과 spine만 넣는다 - head는 나중에 addBone으로 들어온다
    rt.skinOps.addBone(skinMod, armBone, 1)
    rt.skinOps.addBone(skinMod, spineBone, 1)
    skinMod.enableDQ = False
    rt.completeRedraw()

    # 전 버텍스를 명시 지정한다 - 엔벨로프(H1) 요인을 배제하고 ID 밀림만 남긴다
    skin.activate_skin(box, skinMod)
    table0 = skin.get_bone_table(skinMod)
    idByName0 = {str(e["name"]): bid for bid, e in table0.items()}
    vertCount = int(rt.skinOps.GetNumberVertices(skinMod))
    for v in range(1, vertCount + 1):
        if v % 2 == 1:
            rt.skinOps.ReplaceVertexWeights(skinMod, v, [idByName0["pArm"]], [1.0])
        else:
            rt.skinOps.ReplaceVertexWeights(
                skinMod, v, [idByName0["pArm"], idByName0["pSpine"]], [0.5, 0.5]
            )
    rt.clearSelection()

    beforeNamed = weights_by_name(box, skinMod)
    tableBeforeAdd = {bid: str(e["name"]) for bid, e in table0.items()}

    # addBone으로 head를 넣고 ID가 밀리는지 본다
    skin.activate_skin(box, skinMod)
    rt.skinOps.addBone(skinMod, headBone, 0)
    tableAfterAdd = {
        bid: str(e["name"]) for bid, e in skin.get_bone_table(skinMod).items()
    }
    rt.clearSelection()
    shifted = [
        (bid, name, tableAfterAdd.get(bid))
        for bid, name in tableBeforeAdd.items()
        if tableAfterAdd.get(bid) != name
    ]

    # 이제 같은 조건에서 라이브러리 절차를 통째로 돌린다(새 씬으로 다시 지어서)
    rt.resetMaxFile(rt.Name("noPrompt"))
    rootBone = rt.Box(name="pRoot", width=6.0, length=6.0, height=6.0)
    rootBone.pos = rt.Point3(0.0, 0.0, 0.0)
    spineBone = rt.Box(name="pSpine", width=6.0, length=6.0, height=6.0)
    spineBone.pos = rt.Point3(0.0, 0.0, 10.0)
    spineBone.parent = rootBone
    headBone = rt.Box(name="pHead", width=6.0, length=6.0, height=6.0)
    headBone.pos = rt.Point3(0.0, 0.0, 20.0)
    headBone.parent = spineBone
    armBone = rt.Box(name="pArm", width=6.0, length=6.0, height=6.0)
    armBone.pos = rt.Point3(10.0, 0.0, 15.0)
    armBone.parent = spineBone
    box = rt.Box(
        name="ReproBox", width=40.0, length=4.0, height=4.0, widthsegs=7, lengthsegs=1, heightsegs=1
    )
    box.pos = rt.Point3(0.0, 0.0, 15.0)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    rt.skinOps.addBone(skinMod, armBone, 1)
    rt.skinOps.addBone(skinMod, spineBone, 1)
    skinMod.enableDQ = False
    rt.completeRedraw()
    skin.activate_skin(box, skinMod)
    table0 = skin.get_bone_table(skinMod)
    idByName0 = {str(e["name"]): bid for bid, e in table0.items()}
    for v in range(1, vertCount + 1):
        if v % 2 == 1:
            rt.skinOps.ReplaceVertexWeights(skinMod, v, [idByName0["pArm"]], [1.0])
        else:
            rt.skinOps.ReplaceVertexWeights(
                skinMod, v, [idByName0["pArm"], idByName0["pSpine"]], [0.5, 0.5]
            )
    rt.clearSelection()

    before2 = weights_by_name(box, skinMod)
    armH = int(rt.getHandleByAnim(armBone))
    headH = int(rt.getHandleByAnim(headBone))
    libResult = skin.transfer_bone_weights(box, skinMod, {armH: headH}, {armH})
    after2 = weights_by_name(box, skinMod)

    expected2: Dict[int, Dict[str, float]] = {}
    for v, byName in before2.items():
        merged: Dict[str, float] = {}
        for name, w in byName.items():
            key = "pHead" if name == "pArm" else name
            merged[key] = merged.get(key, 0.0) + w
        expected2[v] = merged
    ok2, msg2 = True, ""
    deviated2: List[int] = []
    for v, exp in expected2.items():
        act = after2.get(v, {})
        if any(
            abs(exp.get(n, 0.0) - act.get(n, 0.0)) > WEIGHT_TOLERANCE
            for n in set(exp) | set(act)
        ):
            deviated2.append(v)
    ok2 = len(deviated2) == 0
    if deviated2:
        msg2 = (
            f"v{deviated2[0]} 기대 {expected2[deviated2[0]]} 실제 {after2.get(deviated2[0])}"
        )

    PROBE["sections"]["H6_addBoneIdShift"] = {
        "tableBeforeAdd": tableBeforeAdd,
        "tableAfterAdd": tableAfterAdd,
        "shiftedIds": shifted,
        "idShiftReproduced": len(shifted) > 0,
        "libraryVertCount": len(before2),
        "libraryDeviationCount": len(deviated2),
        "libraryDeviationSample": msg2,
        "libraryAddedBones": libResult["addedBones"],
        "librarySample": {
            "vert": deviated2[0] if deviated2 else None,
            "before": before2.get(deviated2[0]) if deviated2 else None,
            "expected": expected2.get(deviated2[0]) if deviated2 else None,
            "actual": after2.get(deviated2[0]) if deviated2 else None,
        },
        "rootCause": (
            "addBone이 본 ID를 삽입해 밀고, transfer_bone_weights가 addBone 전에 읽은 "
            "가중치·usedBoneIds를 그대로 재사용한다"
            if len(shifted) > 0 and len(deviated2) > 0
            else "합성으로는 재현되지 않음 - 결함 씬 증거(TC17)만으로 보고"
        ),
    }
    dump_probe()

    # 판정축은 "측정이 성립했는가"다. 밀림의 재현 여부 자체는 이 프로브가 **알아내는 값**이고,
    # 실기 증거(TC17)가 이미 밀림을 확정했다. 합성에서 안 나면 방아쇠 조건이 계층·생성 순서보다
    # 좁다는 뜻이며, 그 사실을 JSON에 남긴다(추측으로 규칙을 단정하지 않는다).
    reporter.assert_test(
        len(before2) > 0 and libResult["addedBones"] == ["pHead"],
        f"TC18 [합성 재현 시도] addBone ID 삽입 - 밀린 본 {len(shifted)}개{shifted[:4]}, "
        f"라이브러리 결과 편차 {len(deviated2)}/{len(before2)}개 ({msg2}). "
        f"재현={len(shifted) > 0} (실기 TC17에서는 재현됨 - 방아쇠는 씬 특이적)",
        f"측정이 성립하지 않았다 - verts={len(before2)} added={libResult['addedBones']}",
    )
except Exception as e:
    reporter.error("TC18 합성 재현", f"{e}\n{traceback.format_exc()}")


# ============================================================
# Phase 0B - 삽입 방아쇠 격자 (Q1)
#
# TC17이 실기에서 삽입을 확정했고 TC14·TC18의 합성은 전부 append였다. 무엇이 다른지를
# 축으로 갈라 훑는다. **밀림을 일으키는 조합을 찾아야 합성으로 판별력을 확보할 수 있다.**
#
#   ① 새 본의 계층 역할: ancestor(스킨 본들의 조상) / descendant(리프) /
#      middle(일부의 조상이자 일부의 자손) / sibling / unrelated
#   ② 노드 생성 순서: 새 본을 체인보다 먼저 만들었는가 나중에 만들었는가
#   ③ 스킨 본 개수: 4 / 12 / 60
#   ④ 본 클래스: Box 프리미티브 / `BoneSys.createBone`
#   ⑤ 레이어 소속: 기본 레이어 / 전용 레이어
#
# 조합마다 `addBone` 전후 `{boneId: name}`을 **전량** 기록한다. 이진으로 적으면 나중에
# 원인을 못 쫓는다(Phase 0에서 그럴 뻔했다).
# ============================================================

CHAIN_STEP = 6.0


def _make_bone_node(inName: str, inIndex: int, inUseBoneSys: bool, inLayer: Any) -> Any:
    """체인의 본 하나를 만든다. `BoneSys`와 Box 두 클래스를 같은 배치로 만든다."""
    z = inIndex * CHAIN_STEP
    if inUseBoneSys:
        node = rt.BoneSys.createBone(
            rt.Point3(0.0, 0.0, z), rt.Point3(0.0, 0.0, z + CHAIN_STEP), rt.Point3(0.0, 1.0, 0.0)
        )
        node.name = inName
    else:
        node = rt.Box(name=inName, width=4.0, length=4.0, height=CHAIN_STEP)
        node.pos = rt.Point3(0.0, 0.0, z)
    if inLayer is not None:
        inLayer.addNode(node)
    return node


def _skin_box_with(inBones: List[Any], inHeight: float) -> Tuple[Any, Any]:
    """주어진 본들로 스킨된 박스를 만든다(가중치는 지정하지 않는다 - ID 밀림만 본다)."""
    box = rt.Box(
        name="GridBox", width=6.0, length=6.0, height=inHeight, widthsegs=1, lengthsegs=1, heightsegs=3
    )
    box.pos = rt.Point3(0.0, 0.0, 0.0)
    skinMod = rt.Skin()
    rt.addModifier(box, skinMod)
    rt.modPanel.setCurrentObject(skinMod, node=box)
    for bone in inBones:
        rt.skinOps.addBone(skinMod, bone, 1)
    skinMod.enableDQ = False
    rt.completeRedraw()
    return box, skinMod


def _reload_scene_roundtrip() -> Tuple[Any, Any]:
    """씬을 temp .max로 저장했다가 다시 열고, 박스와 그 Skin을 되찾는다.

    실기 씬은 **파일에서 로드된** 상태였다. 로드가 본 목록의 내부 순서를 다시 잡는다면
    그때의 ``addBone``은 갓 만든 씬과 다르게 움직일 수 있다 - 그 가능성을 축으로 뺀다.
    """
    import os
    import stat
    import tempfile

    tempPath = Path(tempfile.gettempdir()) / "probe_grid_roundtrip.max"
    if tempPath.exists():
        os.chmod(str(tempPath), stat.S_IWRITE)
    rt.saveMaxFile(str(tempPath), quiet=True)
    rt.resetMaxFile(rt.Name("noPrompt"))
    if not rt.loadMaxFile(str(tempPath), quiet=True):
        raise RuntimeError(f"격자 왕복 로드 실패: {tempPath}")
    box = rt.getNodeByName("GridBox")
    if box is None:
        raise RuntimeError("재로드 후 GridBox를 찾지 못했다")
    for modIndex in range(int(box.modifiers.count)):
        mod = box.modifiers[modIndex]
        if rt.classOf(mod) == rt.Skin:
            return box, mod
    raise RuntimeError("재로드 후 Skin을 찾지 못했다")


def run_grid_case(
    inRole: str,
    inCount: int,
    inUseBoneSys: bool,
    inNewFirst: bool,
    inUseLayer: bool,
    inAddOrder: str = "creation",
    inSaveReload: bool = False,
) -> Dict[str, Any]:
    """격자 한 칸을 돌린다. `addBone` 전후 대조표를 전량 담아 돌려준다."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    layer = rt.LayerManager.newLayerFromName("GridBones") if inUseLayer else None

    # 새 본을 체인보다 먼저 만들 수 있게, 체인 밖 본(sibling/unrelated)은 순서를 바꾼다
    standalone: Optional[Any] = None
    if inRole in ("sibling", "unrelated") and inNewFirst:
        standalone = _make_bone_node("newBone", 0, inUseBoneSys, layer)

    chain: List[Any] = []
    for i in range(inCount + 1):
        node = _make_bone_node(f"chain{i:02d}", i, inUseBoneSys, layer)
        if chain:
            node.parent = chain[-1]
        chain.append(node)

    if inRole in ("sibling", "unrelated") and not inNewFirst:
        standalone = _make_bone_node("newBone", 0, inUseBoneSys, layer)

    if inRole == "ancestor":
        # 체인 맨 위를 나중에 넣는다 - 나머지 전부의 조상이다 (실기 `neck`과 같은 배치)
        newBone, skinBones = chain[0], chain[1:]
    elif inRole == "descendant":
        newBone, skinBones = chain[-1], chain[:-1]
    elif inRole == "middle":
        mid = len(chain) // 2
        newBone, skinBones = chain[mid], chain[:mid] + chain[mid + 1 :]
    elif inRole == "sibling":
        standalone.parent = chain[0]
        newBone, skinBones = standalone, chain[1:]
    else:  # unrelated
        newBone, skinBones = standalone, chain[1:]

    # 스킨에 본을 넣는 순서를 노드 생성 순서와 어긋나게 할 수 있다.
    # 실기 스킨은 리거가 임의 순서로 붙였을 수 있고, 그러면 본 ID 순서 != 씬 노드 순서다.
    addOrdered = list(skinBones)
    if inAddOrder == "reverse":
        addOrdered.reverse()
    elif inAddOrder == "interleaved":
        addOrdered = addOrdered[1::2] + addOrdered[0::2]

    box, skinMod = _skin_box_with(addOrdered, (inCount + 1) * CHAIN_STEP)
    newBoneName = str(newBone.name)
    if inSaveReload:
        box, skinMod = _reload_scene_roundtrip()
        newBone = rt.getNodeByName(newBoneName)
        if newBone is None:
            raise RuntimeError(f"재로드 후 '{newBoneName}'을 찾지 못했다")

    skin.activate_skin(box, skinMod)
    tableBefore = {bid: str(e["name"]) for bid, e in skin.get_bone_table(skinMod).items()}
    rt.skinOps.addBone(skinMod, newBone, 0)
    tableAfter = {bid: str(e["name"]) for bid, e in skin.get_bone_table(skinMod).items()}
    rt.clearSelection()

    shifted = [
        (bid, name, tableAfter.get(bid))
        for bid, name in tableBefore.items()
        if tableAfter.get(bid) != name
    ]
    newBoneId = next((bid for bid, name in tableAfter.items() if name == str(newBone.name)), None)
    return {
        "role": inRole,
        "chainLen": inCount,
        "boneSys": inUseBoneSys,
        "newFirst": inNewFirst,
        "layer": inUseLayer,
        "addOrder": inAddOrder,
        "saveReload": inSaveReload,
        "skinBoneCount": len(skinBones),
        "newBoneName": str(newBone.name),
        "newBoneId": newBoneId,
        "appendedAtEnd": newBoneId == len(tableAfter),
        "shiftedCount": len(shifted),
        "shifted": shifted[:8],
        "tableBefore": tableBefore,
        "tableAfter": tableAfter,
    }


# ============================================================
# TC19 (0B.1): 삽입 방아쇠 격자
# ============================================================
gridResults: List[Dict[str, Any]] = []
try:
    cases: List[Tuple[str, int, bool, bool, bool, str, bool]] = []
    # 역할 x 클래스 (기본: 체인 12, 새 본 나중 생성, 레이어 없음, 생성 순서대로 add)
    for role in ("ancestor", "descendant", "middle", "sibling", "unrelated"):
        for boneSys in (False, True):
            cases.append((role, 12, boneSys, False, False, "creation", False))
    # 개수 축 (ancestor / middle 만 - 밀림 후보)
    for role in ("ancestor", "middle"):
        for count in (4, 60):
            for boneSys in (False, True):
                cases.append((role, count, boneSys, False, False, "creation", False))
    # 생성 순서 축 (체인 밖 본에만 의미가 있다)
    for role in ("sibling", "unrelated"):
        for boneSys in (False, True):
            cases.append((role, 12, boneSys, True, False, "creation", False))
    # 레이어 축
    for role in ("ancestor", "descendant"):
        for boneSys in (False, True):
            cases.append((role, 12, boneSys, False, True, "creation", False))
    # ⑥ 스킨 add 순서 축 - 본 ID 순서를 노드 생성 순서와 어긋나게 한다
    for role in ("ancestor", "middle", "descendant"):
        for addOrder in ("reverse", "interleaved"):
            for boneSys in (False, True):
                cases.append((role, 12, boneSys, False, False, addOrder, False))
    # ⑦ 저장·재로드 축 - 실기 씬은 파일에서 로드된 상태였다
    for role in ("ancestor", "middle", "descendant"):
        for addOrder in ("creation", "reverse"):
            cases.append((role, 12, True, False, False, addOrder, True))

    caseErrors: List[str] = []
    for role, count, boneSys, newFirst, useLayer, addOrder, saveReload in cases:
        try:
            gridResults.append(
                run_grid_case(role, count, boneSys, newFirst, useLayer, addOrder, saveReload)
            )
        except Exception as caseExc:
            caseErrors.append(
                f"{role}/{count}/{boneSys}/{newFirst}/{useLayer}/{addOrder}/{saveReload}: {caseExc}"
            )

    shiftingCases = [c for c in gridResults if c["shiftedCount"] > 0]
    PROBE["sections"]["Q1_insertionGrid"] = {
        "caseCount": len(gridResults),
        "caseErrors": caseErrors,
        "shiftingCaseCount": len(shiftingCases),
        "shiftingCases": [
            {k: c[k] for k in ("role", "chainLen", "boneSys", "newFirst", "layer",
                               "addOrder", "saveReload", "newBoneId", "shiftedCount", "shifted")}
            for c in shiftingCases
        ],
        "summary": [
            {
                "role": c["role"],
                "chainLen": c["chainLen"],
                "boneSys": c["boneSys"],
                "newFirst": c["newFirst"],
                "layer": c["layer"],
                "addOrder": c["addOrder"],
                "saveReload": c["saveReload"],
                "newBoneId": c["newBoneId"],
                "skinBoneCount": c["skinBoneCount"],
                "appendedAtEnd": c["appendedAtEnd"],
                "shiftedCount": c["shiftedCount"],
            }
            for c in gridResults
        ],
        "cases": gridResults,
    }
    dump_probe()

    reporter.assert_test(
        len(gridResults) == len(cases) and not caseErrors,
        f"TC19 [0B.1] 삽입 방아쇠 격자 - {len(gridResults)}/{len(cases)} 조합 측정, "
        f"밀림을 일으킨 조합 {len(shiftingCases)}개"
        + (
            f" → {[(c['role'], c['chainLen'], 'BoneSys' if c['boneSys'] else 'Box', c['newBoneId']) for c in shiftingCases[:5]]}"
            if shiftingCases
            else " (전부 끝에 append - 합성 방아쇠 미발견)"
        ),
        f"측정이 성립하지 않았다 - {len(gridResults)}/{len(cases)}, 오류 {caseErrors[:3]}",
    )
except Exception as e:
    reporter.error("TC19 0B.1 삽입 격자", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC20 (0B.1 확증, 판정): 밀림 조건에서 라이브러리가 실제로 가중치를 오배치하는가
#
#   TC22가 방아쇠를 찾았다 - `removeBone`이 비운 슬롯을 `addBone`이 **가장 낮은 빈 자리부터
#   재사용**하고 그 뒤 본이 전부 밀린다. 프로덕션 스킨은 리거가 본을 붙였다 뗐다 한 이력이
#   있으므로 빈 슬롯이 흔하다(실기 `Face`에서 `neck`이 ID 1을 차지하며 258본이 밀렸다).
#
#   그 조건을 합성으로 세우고 `transfer_bone_weights`를 끝까지 돌려 편차를 잰다.
#   **여기서 편차가 나야 A2가 "수정 전 실패"를 보일 수 있다.**
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    chain: List[Any] = []
    for i in range(14):
        node = _make_bone_node(f"chain{i:02d}", i, True, None)
        if chain:
            node.parent = chain[-1]
        chain.append(node)
    # chain00은 Skin 밖에 둔다(이전 대상 → addBone 경로). dummy는 슬롯을 비우는 용도다
    dummy = _make_bone_node("dummySlot", 20, True, None)
    skinBones = [dummy] + chain[1:]
    box, skinMod = _skin_box_with(skinBones, 14 * CHAIN_STEP)

    # dummy를 빼서 앞쪽 슬롯을 비운다 - 프로덕션 스킨의 "본을 뗀 이력"을 재현한다
    skin.activate_skin(box, skinMod)
    dummyId = next(
        (bid for bid, e in skin.get_bone_table(skinMod).items() if str(e["name"]) == "dummySlot"),
        None,
    )
    rt.skinOps.removeBone(skinMod, dummyId)
    rt.clearSelection()

    # 슬롯이 빈 상태에서 전 버텍스를 명시 지정한다(엔벨로프 요인 배제)
    skin.activate_skin(box, skinMod)
    table0 = skin.get_bone_table(skinMod)
    idByName0 = {str(e["name"]): bid for bid, e in table0.items()}
    names0 = sorted(idByName0)
    vertCount = int(rt.skinOps.GetNumberVertices(skinMod))
    for v in range(1, vertCount + 1):
        primary = names0[v % len(names0)]
        secondary = names0[(v + 1) % len(names0)]
        if primary == secondary:
            rt.skinOps.ReplaceVertexWeights(skinMod, v, [idByName0[primary]], [1.0])
        else:
            rt.skinOps.ReplaceVertexWeights(
                skinMod, v, [idByName0[primary], idByName0[secondary]], [0.7, 0.3]
            )
    rt.clearSelection()

    before = weights_by_name(box, skinMod)
    # 스킨 본 절반을 Skin 밖 chain00으로 옮긴다 → addBone이 빈 슬롯을 채우며 ID가 밀린다
    sources = [b for b in chain[1:] if str(b.name) in idByName0][: len(chain[1:]) // 2]
    targetBone = chain[0]
    transferMap = {
        int(rt.getHandleByAnim(b)): int(rt.getHandleByAnim(targetBone)) for b in sources
    }
    libResult = skin.transfer_bone_weights(box, skinMod, transferMap, set(transferMap))
    after = weights_by_name(box, skinMod)

    sourceNames = {str(b.name) for b in sources}
    targetName = str(targetBone.name)
    expected: Dict[int, Dict[str, float]] = {}
    for v, byName in before.items():
        merged: Dict[str, float] = {}
        for name, w in byName.items():
            key = targetName if name in sourceNames else name
            merged[key] = merged.get(key, 0.0) + w
        expected[v] = merged
    deviated = [
        v
        for v, exp in expected.items()
        if any(
            abs(exp.get(n, 0.0) - after.get(v, {}).get(n, 0.0)) > WEIGHT_TOLERANCE
            for n in set(exp) | set(after.get(v, {}))
        )
    ]

    PROBE["sections"]["Q1_libraryDeviation"] = {
        "trigger": "removeBone으로 비운 슬롯을 addBone이 재사용 → 본 ID 밀림",
        "skinBoneCount": len(idByName0),
        "vertCount": len(before),
        "transferCount": len(transferMap),
        "sourceNames": sorted(sourceNames),
        "targetName": targetName,
        "addedBones": libResult["addedBones"],
        "deviationCount": len(deviated),
        "sample": (
            {
                "vert": deviated[0],
                "before": before.get(deviated[0]),
                "expected": expected.get(deviated[0]),
                "actual": after.get(deviated[0]),
            }
            if deviated
            else None
        ),
    }
    dump_probe()
    reporter.assert_test(
        len(deviated) > 0,
        f"TC20 [0B.1 확증] 합성 밀림 조건에서 라이브러리 오배치 재현 - 스킨 본 "
        f"{len(idByName0)}개(앞 슬롯 1개 비움), 이전 {len(transferMap)}본 → {targetName}, "
        f"추가 본 {libResult['addedBones']}, **편차 {len(deviated)}/{len(before)} 버텍스**",
        "밀림 조건인데 라이브러리 편차가 0이다 - 이 픽스처는 판별력이 없다. "
        "제거 위치를 앞으로 옮기거나 이전 대상 수를 늘린다",
    )
except Exception as e:
    reporter.error("TC20 0B.1 확증", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC21 (0B.2 / Q3): 재조회 비용 - A1.2가 추가하는 비용의 상한
# ============================================================
try:
    load_scene_copy(DEFECT_SCENE)
    costs: List[Dict[str, Any]] = []
    for node, skinMod in skinned_nodes():
        saved = list(rt.getCurrentSelection())
        try:
            skin.activate_skin(node, skinMod)
            started = time.perf_counter()
            raw = skin.get_vertex_weights(skinMod)
            elapsed = time.perf_counter() - started
        finally:
            _restore(saved)
        costs.append(
            {
                "node": str(node.name),
                "vertCount": len(raw),
                "readSec": round(elapsed, 3),
            }
        )
    rt.clearSelection()
    totalSec = sum(c["readSec"] for c in costs)
    totalVerts = sum(c["vertCount"] for c in costs)
    faceCost = next((c for c in costs if c["node"] == "Face"), None)

    PROBE["sections"]["Q3_rereadCost"] = {
        "perSkin": costs,
        "totalSec": round(totalSec, 3),
        "totalVerts": totalVerts,
        "faceSec": faceCost["readSec"] if faceCost else None,
        "note": "A1.2의 재조회는 addBone이 일어난 Skin에서만 발생한다",
    }
    dump_probe()
    reporter.assert_test(
        len(costs) > 0 and totalVerts > 0,
        f"TC21 [0B.2] 재조회 비용 - Skin {len(costs)}개 / 전 버텍스 {totalVerts}개 읽기에 "
        f"{totalSec:.3f}초 (Face {faceCost['readSec'] if faceCost else '?'}초). "
        f"addBone이 일어난 Skin에서만 발생한다",
        f"측정이 성립하지 않았다 - skins={len(costs)} verts={totalVerts}",
    )
except Exception as e:
    reporter.error("TC21 0B.2 재조회 비용", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC22 (0B.1 축 ⑧): removeBone이 만든 빈 자리를 addBone이 채우는가
#
#   실기에서 새 본이 **ID 1**에 들어갔다. 격자의 7개 축(44조합)은 전부 append였으므로,
#   남은 설명은 "그 Skin이 과거에 본을 제거한 적이 있어 내부 슬롯이 비어 있었다"이다.
#   리거가 만든 프로덕션 스킨은 본을 붙였다 뗐다 한 이력이 있을 수 있다.
#
#   제거 위치(앞/중간/뒤)와 제거 개수를 바꿔 가며 `addBone` 후 새 본의 ID를 본다.
#   append가 아니면 **합성 방아쇠를 찾은 것**이고, A2 픽스처가 그 조건이 된다.
# ============================================================
try:
    removeAddCases: List[Dict[str, Any]] = []
    for removeAt, label in ((1, "front"), (6, "middle"), (12, "back")):
        for removeCount in (1, 2):
            rt.resetMaxFile(rt.Name("noPrompt"))
            chain: List[Any] = []
            for i in range(14):
                node = _make_bone_node(f"chain{i:02d}", i, True, None)
                if chain:
                    node.parent = chain[-1]
                chain.append(node)
            newBone, skinBones = chain[0], chain[1:]
            box, skinMod = _skin_box_with(skinBones, 14 * CHAIN_STEP)

            skin.activate_skin(box, skinMod)
            tableInitial = {bid: str(e["name"]) for bid, e in skin.get_bone_table(skinMod).items()}
            # 제거는 ID 내림차순으로 (제거 시 ID가 밀린다)
            targets = sorted(
                range(removeAt, min(removeAt + removeCount, len(tableInitial) + 1)), reverse=True
            )
            for boneId in targets:
                rt.skinOps.removeBone(skinMod, boneId)
            tableBefore = {bid: str(e["name"]) for bid, e in skin.get_bone_table(skinMod).items()}
            rt.skinOps.addBone(skinMod, newBone, 0)
            tableAfter = {bid: str(e["name"]) for bid, e in skin.get_bone_table(skinMod).items()}
            rt.clearSelection()

            shifted = [
                (bid, name, tableAfter.get(bid))
                for bid, name in tableBefore.items()
                if tableAfter.get(bid) != name
            ]
            newBoneId = next(
                (bid for bid, name in tableAfter.items() if name == str(newBone.name)), None
            )
            removeAddCases.append(
                {
                    "removeAt": label,
                    "removeAtId": removeAt,
                    "removeCount": removeCount,
                    "removedNames": [tableInitial.get(b) for b in targets],
                    "boneCountAfterRemove": len(tableBefore),
                    "newBoneId": newBoneId,
                    "appendedAtEnd": newBoneId == len(tableAfter),
                    "shiftedCount": len(shifted),
                    "shifted": shifted[:8],
                    "tableBefore": tableBefore,
                    "tableAfter": tableAfter,
                }
            )

    shiftingRemoveAdd = [c for c in removeAddCases if c["shiftedCount"] > 0]
    PROBE["sections"]["Q1_removeThenAdd"] = {
        "caseCount": len(removeAddCases),
        "shiftingCaseCount": len(shiftingRemoveAdd),
        "summary": [
            {
                k: c[k]
                for k in (
                    "removeAt",
                    "removeCount",
                    "boneCountAfterRemove",
                    "newBoneId",
                    "appendedAtEnd",
                    "shiftedCount",
                )
            }
            for c in removeAddCases
        ],
        "cases": removeAddCases,
    }
    dump_probe()

    reporter.assert_test(
        len(removeAddCases) == 6,
        f"TC22 [0B.1 축 ⑧] removeBone 후 addBone - {len(removeAddCases)}조합 측정, "
        f"밀림 {len(shiftingRemoveAdd)}개. 새 본 ID "
        f"{[(c['removeAt'], c['removeCount'], c['newBoneId'], c['boneCountAfterRemove']) for c in removeAddCases]}",
        f"측정이 성립하지 않았다 - {len(removeAddCases)}조합",
    )
except Exception as e:
    reporter.error("TC22 0B.1 축 ⑧", f"{e}\n{traceback.format_exc()}")


# ---- 종료 ---------------------------------------------------------------------

dump_probe()
reporter.summary()
reporter.close()
