#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **3차** - "의존 노드 0개"의 정체를 가른다.

2차가 프로덕션 13씬에서 누락 애셋 534건 중 **503건(94%)이 의존 노드 0개**라고 보고했다.
그 0이 두 가지 중 무엇인지에 따라 Phase 2 스캐너의 설계가 갈린다.

- **진짜 고아**: 텍스쳐 객체는 씬에 있는데 그것을 참조하는 노드가 없다.
  -> 노드 기반 계획에 기여할 것이 없다. 스캐너는 지금 형태로 맞다.
- **열거 누락**: `AssetManager`는 아는데 `getClassInstances`로는 안 보이는 애셋이 있다.
  -> 스캐너가 대상을 조용히 빠뜨리고 있다. 열거 경로를 바꿔야 한다.

**둘 다 "0"으로 보인다**(`testing/debug_process.md` 원칙 22 - "실측 0건"이 "안전 확인"인지
"검사 불가"인지 구분해 기록한다). 그래서 이번에는 **매칭 여부를 따로 센다**.

    N1  애셋 경로가 텍스쳐 객체 맵에 **키로 존재하는가**(matched) vs 아예 없는가(unmatched)
    N2  `ATSOps.GetFileClients`를 MAXScript 워커로 불러 **독립 출처로 교차 확인**
    N3  unmatched 애셋의 정체 - 어떤 클래스가 그 경로를 들고 있는지 전수 역탐색

실행:
    uv run python tests/_run_probe.py _probe_missing_asset_3.py 1800

결과:
    tests/logs/probe_missing_asset_3.json
"""

import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt  # noqa: E402

import pyjallib  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = LOG_DIR / "probe_missing_asset_3.json"

#: 2차에서 실태가 가장 선명했던 씬들. 큰 캐릭터 씬과 애니메이션 씬을 함께 본다.
TARGET_SCENES = (
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default/SK_JeongHuiwon_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Main/HanMyeongoh/MeshB/Default/SK_HanMyeongoh_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Shared/Human/Male/Mesh/BangCheolSoo/SK_HumanM_Sh_LongTeeShorts.max",
)

reporter = TestReporter("ProbeMissingAsset3", LOG_DIR)

RESULT = {"loadedFrom": getattr(pyjallib, "__file__", None), "scenes": [], "summary": {}}


def _flush():
    """지금까지의 결과를 JSON으로 덮어쓴다."""
    RESULT_PATH.write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _try(inLabel, inFunc):
    """함수를 실행하고 성공/실패를 함께 기록한다.

    Args:
        inLabel: 기록용 라벨
        inFunc: 인자 없는 호출 가능 객체

    Returns:
        dict: `{"label", "ok", "value", "error"}`
    """
    try:
        return {"label": inLabel, "ok": True, "value": inFunc(), "error": None}
    except Exception:
        return {
            "label": inLabel,
            "ok": False,
            "value": None,
            "error": traceback.format_exc(limit=4),
        }


def _norm(inPath):
    """경로를 비교용으로 정규화한다.

    Args:
        inPath: 원본 경로

    Returns:
        str: 소문자 + 정방향 슬래시
    """
    return str(inPath or "").replace("\\", "/").lower()


def _missing_assets():
    """`AssetManager`로 누락 애셋(해석 실패)을 열거한다.

    Returns:
        list[dict]: `{"fileName", "assetType"}` 목록
    """
    assetMan = getattr(rt, "AssetManager", None)
    if assetMan is None:
        return []
    countProbe = _try("GetNumAssets", lambda: int(assetMan.GetNumAssets()))
    if not countProbe["ok"]:
        return []

    missing = []
    for index in range(1, (countProbe["value"] or 0) + 1):
        userProbe = _try("GetAssetByIndex", lambda i=index: assetMan.GetAssetByIndex(i))
        assetUser = userProbe["value"]
        if assetUser is None:
            continue
        nameProbe = _try("GetFileName", lambda a=assetUser: str(a.GetFileName()))
        fullProbe = _try("GetFullFilePath", lambda a=assetUser: str(a.GetFullFilePath()))
        typeProbe = _try("GetType", lambda a=assetUser: str(a.GetType()))
        if fullProbe["ok"] and fullProbe["value"]:
            continue
        missing.append({
            "fileName": nameProbe["value"] if nameProbe["ok"] else None,
            "assetType": typeProbe["value"] if typeProbe["ok"] else None,
        })
    return missing


def _path_holder_map():
    """씬의 **모든** 객체를 훑어 "경로 문자열 -> 그것을 들고 있는 객체들"을 만든다.

    2차는 `BitmapTexture` 등 **정해진 클래스만** 훑었다. 그 표본으로는 "열거 누락"을
    "고아"와 구분할 수 없다. 여기서는 클래스를 고정하지 않고 씬의 애님 트리를 훑는다.

    Returns:
        dict: `{정규화 경로: [{"className", "propName", "dependentNodeNames"}]}`
    """
    holders = {}

    def _record(inObject, inPropName, inValue):
        """경로 문자열 하나를 소유자와 함께 기록한다."""
        text = str(inValue or "")
        if not text or len(text) < 4:
            return
        key = _norm(text)
        nodesProbe = _try("dependentNodes", lambda o=inObject: list(rt.refs.dependentNodes(o)))
        nodes = nodesProbe["value"] or []
        holders.setdefault(key, []).append({
            "className": str(rt.classOf(inObject)),
            "propName": inPropName,
            "dependentNodeCount": len(nodes),
            "dependentNodeNames": [str(node.name) for node in nodes][:5],
            "dependentIsGeometry": [
                bool(rt.superClassOf(node) == rt.GeometryClass) for node in nodes
            ][:5],
        })

    # 씬의 모든 애님(머티리얼·텍스쳐·모디파이어 포함)을 훑는다.
    visited = set()

    def _walk(inAnim, inDepth=0):
        """애님 트리를 재귀로 훑으며 문자열 프로퍼티를 기록한다."""
        if inDepth > 6:
            return
        try:
            handle = int(rt.getHandleByAnim(inAnim))
        except Exception:
            handle = None
        if handle is not None:
            if handle in visited:
                return
            visited.add(handle)

        namesProbe = _try("getPropNames", lambda a=inAnim: [str(n) for n in rt.getPropNames(a)])
        for propName in namesProbe["value"] or []:
            valueProbe = _try("getProperty", lambda a=inAnim, n=propName: rt.getProperty(a, n))
            if not valueProbe["ok"]:
                continue
            value = valueProbe["value"]
            if isinstance(value, str) and ("/" in value or "\\" in value or "." in value):
                _record(inAnim, propName, value)

        countProbe = _try("numSubs", lambda a=inAnim: int(rt.getNumSubs(a)))
        for index in range(1, (countProbe["value"] or 0) + 1):
            subProbe = _try("getSubAnim", lambda a=inAnim, i=index: rt.getSubAnim(a, i))
            if subProbe["ok"] and subProbe["value"] is not None:
                _walk(subProbe["value"], inDepth + 1)

    for klassName in ("BitmapTexture", "DirectX_9_Shader", "VRayHDRI", "Bitmaptexture"):
        klass = getattr(rt, klassName, None)
        if klass is None:
            continue
        instancesProbe = _try("getClassInstances", lambda k=klass: list(rt.getClassInstances(k)))
        for instance in instancesProbe["value"] or []:
            _walk(instance)

    # 씬 머티리얼도 기점에 넣는다(노드에 붙지 않은 것까지 잡기 위해).
    for source in ("sceneMaterials", "meditMaterials"):
        collectionProbe = _try(source, lambda s=source: list(getattr(rt, s)))
        for material in collectionProbe["value"] or []:
            _walk(material)

    return holders


def _sweep(inScenePath):
    """씬 하나에서 matched / unmatched를 갈라 센다.

    Args:
        inScenePath: 열 `.max` 경로

    Returns:
        dict: 계측 결과
    """
    record = {"path": inScenePath, "ok": False}

    rt.resetMaxFile(rt.Name("noPrompt"))
    loadStart = time.time()
    loadProbe = _try("loadMaxFile", lambda: bool(rt.loadMaxFile(inScenePath)))
    record["loadSeconds"] = round(time.time() - loadStart, 2)
    if not loadProbe["ok"] or loadProbe["value"] is not True:
        record["error"] = loadProbe["error"] or "loadMaxFile이 True를 돌려주지 않음"
        return record
    _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))

    sweepStart = time.time()
    missing = _missing_assets()
    holders = _path_holder_map()
    record["sweepSeconds"] = round(time.time() - sweepStart, 2)
    record["ok"] = True

    matched = []
    unmatchedNames = []
    withNodes = 0
    for asset in missing:
        key = _norm(asset["fileName"])
        entries = holders.get(key)
        if not entries:
            unmatchedNames.append(asset["fileName"])
            continue
        nodeCount = sum(entry["dependentNodeCount"] for entry in entries)
        if nodeCount > 0:
            withNodes += 1
        matched.append({
            "fileName": asset["fileName"],
            "assetType": asset["assetType"],
            "holders": entries[:3],
            "nodeCount": nodeCount,
        })

    record["missingTotal"] = len(missing)
    record["matchedCount"] = len(matched)
    record["unmatchedCount"] = len(unmatchedNames)
    record["matchedWithNodesCount"] = withNodes
    record["matchedOrphanCount"] = len(matched) - withNodes
    record["holderClassCounts"] = dict(
        Counter(
            entry["className"]
            for item in matched
            for entry in item["holders"]
        )
    )
    record["unmatchedSamples"] = unmatchedNames[:15]
    record["matchedSamples"] = matched[:15]

    # N2 - ATSOps.GetFileClients 교차 확인(독립 출처).
    if missing:
        target = missing[0]["fileName"].replace("\\", "\\\\")
        record["atsClientsCrossCheck"] = _try(
            "ATSOps.GetFileClients 워커",
            lambda: str(
                rt.execute(
                    f'(local c = #(); ATSOps.GetFileClients "{target}" &c; c as string)'
                )
            ),
        )
    return record


reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

for scenePath in TARGET_SCENES:
    try:
        RESULT["scenes"].append(_sweep(scenePath))
        reporter.assert_test(True, f"TC {Path(scenePath).name} 스윕", "")
    except Exception:
        RESULT["scenes"].append({"path": scenePath, "fatal": traceback.format_exc(limit=6)})
        reporter.error(f"TC {Path(scenePath).name} 스윕", traceback.format_exc(limit=4))
    _flush()

swept = [item for item in RESULT["scenes"] if item.get("ok")]
RESULT["summary"] = {
    "sceneCount": len(swept),
    "missingTotal": sum(item.get("missingTotal", 0) for item in swept),
    "matchedTotal": sum(item.get("matchedCount", 0) for item in swept),
    "unmatchedTotal": sum(item.get("unmatchedCount", 0) for item in swept),
    "matchedWithNodesTotal": sum(item.get("matchedWithNodesCount", 0) for item in swept),
    "matchedOrphanTotal": sum(item.get("matchedOrphanCount", 0) for item in swept),
    "sweepSecondsTotal": round(sum(item.get("sweepSeconds", 0) for item in swept), 2),
    "loadSecondsTotal": round(sum(item.get("loadSeconds", 0) for item in swept), 2),
}
_flush()
reporter.summary()
reporter.close()
