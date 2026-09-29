#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **4차** - 정리 대상이 매테리얼 쪽에 있는가.

**왜 4차가 있는가.** 실기 판정에서 마스터가 "세 툴 전부 변화가 없다, 링크가 깨진
텍스쳐를 쓰는 **매테리얼**을 정리해야 할 것 같다"고 지적했다. 1~3차는 **노드**를 축으로
셌고, 그 결과 프로덕션 13씬에서 삭제 대상 0건이 나왔다. 3차가 남긴 미해결 조각 -
누락 애셋 55건 중 **49건(89%)이 어떤 보유자도 찾지 못한 unmatched** - 이 지적과 같은
곳을 가리킬 가능성이 크다.

이 프로브가 답할 것:

    M1  깨진 텍스쳐를 참조하는 **매테리얼**이 몇 개인가, 어떤 클래스인가
    M2  그 매테리얼이 **노드에 할당돼 있는가**(할당 / 씬 라이브러리에만 / 머티리얼 에디터)
    M3  unmatched 애셋의 정체 - 그 경로 문자열을 **씬 어디가** 들고 있는가
        (애님 트리 전수 재귀로 추적. 3차는 클래스 3종 + 머티리얼 2출처만 훑었다)
    M4  노드에 할당된 매테리얼의 깨진 슬롯 수 - MeshValidator의 기존 4-state가
        **잡아야 하는데 못 잡고 있는** 것이 있는가

**아무것도 바꾸지 않는다.** 씬은 로드만 하고 `setSaveRequired(False)`로 닫는다.

실행:
    uv run python tests/_run_probe.py _probe_material_cleanup.py 1800

결과:
    tests/logs/probe_material_cleanup.json
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
RESULT_PATH = LOG_DIR / "probe_material_cleanup.json"

#: 실태를 볼 씬. 대형 캐릭터 + 애니메이션 + 공유 에셋을 섞는다. 1~3차가 소품에
#: 치우쳤던 것을 교정한다.
TARGET_SCENES = (
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default/SK_JeongHuiwon_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Main/HanMyeongoh/MeshB/Default/SK_HanMyeongoh_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Main/YuSangah/MeshB/Default/SK_YuSangah_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Main/LeeHyeonseong/MeshB/Default/SK_LeeHyeonseong_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Shared/Human/Male/Mesh/BangCheolSoo/SK_HumanM_Sh_LongTeeShorts.max",
)

SECTION_BUDGET = 1200.0

reporter = TestReporter("ProbeMaterialCleanup", LOG_DIR)

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
            "error": traceback.format_exc(limit=3),
        }


def _norm(inPath):
    """경로를 비교용으로 정규화한다.

    Args:
        inPath: 원본 경로

    Returns:
        str: 소문자 + 정방향 슬래시
    """
    return str(inPath or "").replace("\\", "/").lower()


def _missing_asset_paths():
    """`AssetManager`로 해석 실패한 애셋 경로를 모은다.

    Returns:
        dict: `{정규화 경로: {"fileName", "assetType"}}`
    """
    assetMan = getattr(rt, "AssetManager", None)
    if assetMan is None:
        return {}
    countProbe = _try("GetNumAssets", lambda: int(assetMan.GetNumAssets()))
    if not countProbe["ok"]:
        return {}

    missing = {}
    for index in range(1, (countProbe["value"] or 0) + 1):
        userProbe = _try("GetAssetByIndex", lambda i=index: assetMan.GetAssetByIndex(i))
        assetUser = userProbe["value"]
        if assetUser is None:
            continue
        fullProbe = _try("GetFullFilePath", lambda a=assetUser: str(a.GetFullFilePath()))
        if fullProbe["ok"] and fullProbe["value"]:
            continue
        nameProbe = _try("GetFileName", lambda a=assetUser: str(a.GetFileName()))
        typeProbe = _try("GetType", lambda a=assetUser: str(a.GetType()))
        fileName = nameProbe["value"] if nameProbe["ok"] else ""
        missing[_norm(fileName)] = {
            "fileName": fileName,
            "assetType": typeProbe["value"] if typeProbe["ok"] else None,
        }
    return missing


def _node_material_map():
    """노드에 할당된 매테리얼의 핸들 집합을 만든다.

    Multi/Sub-Object의 서브 매테리얼까지 내려간다 - 서브가 깨진 텍스쳐를 물고 있는데
    최상위만 보면 "할당 안 됨"으로 오판한다.

    Returns:
        dict: `{매테리얼 핸들: [노드 이름, ...]}`
    """
    assigned = {}

    def _walk_material(inMaterial, inNodeName, inDepth=0):
        """매테리얼과 그 서브 매테리얼을 훑어 할당 표에 넣는다."""
        if inMaterial is None or inDepth > 6:
            return
        handleProbe = _try("handle", lambda m=inMaterial: int(rt.getHandleByAnim(m)))
        if not handleProbe["ok"]:
            return
        assigned.setdefault(handleProbe["value"], []).append(inNodeName)

        countProbe = _try("numSubs", lambda m=inMaterial: int(rt.getNumSubMtls(m)))
        for index in range(1, (countProbe["value"] or 0) + 1):
            subProbe = _try("getSubMtl", lambda m=inMaterial, i=index: rt.getSubMtl(m, i))
            if subProbe["ok"] and subProbe["value"] is not None:
                _walk_material(subProbe["value"], inNodeName, inDepth + 1)

    for node in rt.objects:
        materialProbe = _try("node.material", lambda n=node: n.material)
        if materialProbe["ok"] and materialProbe["value"] is not None:
            _walk_material(materialProbe["value"], str(node.name))
    return assigned


def _texmap_records(inMissingPaths, inAssignedMaterials):
    """깨진 텍스쳐맵과 그것을 참조하는 매테리얼을 모은다.

    Args:
        inMissingPaths: `_missing_asset_paths()` 결과
        inAssignedMaterials: `_node_material_map()` 결과

    Returns:
        dict: 집계와 표본
    """
    records = []
    materialCounter = Counter()
    placementCounter = Counter()
    seenMaterials = {}

    for className in ("BitmapTexture", "VRayHDRI"):
        klass = getattr(rt, className, None)
        if klass is None:
            continue
        instancesProbe = _try("getClassInstances", lambda k=klass: list(rt.getClassInstances(k)))
        for texmap in instancesProbe["value"] or []:
            pathProbe = _try("filename", lambda t=texmap: rt.getProperty(t, "filename"))
            if not pathProbe["ok"]:
                continue
            value = pathProbe["value"]
            if value is None or isinstance(value, (bool, int, float)):
                continue
            key = _norm(str(value))
            if key not in inMissingPaths:
                continue

            # 이 텍스쳐맵을 참조하는 것들 - 매테리얼이 대부분이다.
            dependentsProbe = _try(
                "refs.dependents", lambda t=texmap: list(rt.refs.dependents(t))
            )
            materials = []
            for dependent in dependentsProbe["value"] or []:
                superProbe = _try("superClassOf", lambda d=dependent: str(rt.superClassOf(d)))
                if superProbe["value"] != "material":
                    continue
                handleProbe = _try("handle", lambda d=dependent: int(rt.getHandleByAnim(d)))
                if not handleProbe["ok"]:
                    continue
                handle = handleProbe["value"]
                nameProbe = _try("name", lambda d=dependent: str(d.name))
                classProbe = _try("classOf", lambda d=dependent: str(rt.classOf(d)))
                assignedNodes = inAssignedMaterials.get(handle, [])
                placement = "assigned" if assignedNodes else "unassigned"
                seenMaterials[handle] = {
                    "name": nameProbe["value"] if nameProbe["ok"] else "",
                    "class": classProbe["value"] if classProbe["ok"] else "",
                    "placement": placement,
                    "nodeCount": len(assignedNodes),
                }
                materials.append(handle)

            nodesProbe = _try(
                "dependentNodes", lambda t=texmap: list(rt.refs.dependentNodes(t))
            )
            records.append({
                "className": className,
                "path": str(value),
                "materialHandles": materials,
                "nodeCount": len(nodesProbe["value"] or []),
            })

    for handle, info in seenMaterials.items():
        materialCounter[info["class"]] += 1
        placementCounter[info["placement"]] += 1

    return {
        "brokenTexmapCount": len(records),
        "materialCount": len(seenMaterials),
        "materialByClass": dict(sorted(materialCounter.items())),
        "materialByPlacement": dict(sorted(placementCounter.items())),
        "materialSamples": [
            dict(info, handle=handle) for handle, info in list(seenMaterials.items())[:15]
        ],
        "texmapSamples": records[:15],
        "texmapWithNoMaterial": len([r for r in records if not r["materialHandles"]]),
        "texmapWithNoNode": len([r for r in records if r["nodeCount"] == 0]),
        "matchedPaths": {_norm(r["path"]) for r in records},
    }


def _trace_unmatched(inMissingPaths, inMatchedPaths):
    """어떤 텍스쳐맵에도 안 잡힌 누락 애셋의 정체를 추적한다.

    씬의 애님 트리를 전수 재귀해 **문자열 프로퍼티**를 훑는다. 3차는 클래스 3종과
    머티리얼 2출처만 봤으므로, 그 밖에 있는 보유자를 여기서 찾는다.

    Args:
        inMissingPaths: 누락 애셋 경로 표
        inMatchedPaths: 텍스쳐맵에서 이미 찾은 경로 집합

    Returns:
        dict: unmatched 집계와 보유자 클래스 분포
    """
    unmatched = [key for key in inMissingPaths if key not in inMatchedPaths]
    holders = Counter()
    found = set()
    visited = set()

    def _walk(inAnim, inDepth=0):
        """애님 트리를 재귀로 훑으며 문자열 프로퍼티에서 경로를 찾는다."""
        if inDepth > 8:
            return
        handleProbe = _try("handle", lambda a=inAnim: int(rt.getHandleByAnim(a)))
        if handleProbe["ok"]:
            if handleProbe["value"] in visited:
                return
            visited.add(handleProbe["value"])

        namesProbe = _try("getPropNames", lambda a=inAnim: [str(n) for n in rt.getPropNames(a)])
        for propName in namesProbe["value"] or []:
            valueProbe = _try("getProperty", lambda a=inAnim, n=propName: rt.getProperty(a, n))
            if not valueProbe["ok"]:
                continue
            value = valueProbe["value"]
            if not isinstance(value, str):
                continue
            key = _norm(value)
            if key in inMissingPaths and key not in inMatchedPaths:
                found.add(key)
                classProbe = _try("classOf", lambda a=inAnim: str(rt.classOf(a)))
                holders[f"{classProbe['value']}.{propName}"] += 1

        countProbe = _try("numSubs", lambda a=inAnim: int(rt.getNumSubs(a)))
        for index in range(1, (countProbe["value"] or 0) + 1):
            subProbe = _try("getSubAnim", lambda a=inAnim, i=index: rt.getSubAnim(a, i))
            if subProbe["ok"] and subProbe["value"] is not None:
                _walk(subProbe["value"], inDepth + 1)

    for source in ("rootScene", "sceneMaterials", "meditMaterials"):
        collectionProbe = _try(source, lambda s=source: getattr(rt, s))
        value = collectionProbe["value"]
        if value is None:
            continue
        if source == "rootScene":
            _walk(value)
        else:
            listProbe = _try("list", lambda v=value: list(v))
            for item in listProbe["value"] or []:
                _walk(item)

    return {
        "unmatchedCount": len(unmatched),
        "tracedCount": len(found),
        "stillUnknownCount": len(unmatched) - len(found),
        "holderByClassProp": dict(sorted(holders.items(), key=lambda kv: -kv[1])[:15]),
        "unmatchedSamples": [inMissingPaths[key]["fileName"] for key in unmatched[:10]],
    }


def _sweep(inScenePath):
    """씬 하나를 열어 매테리얼 축으로 실태를 잰다. 씬을 바꾸지 않는다.

    Args:
        inScenePath: 열 `.max` 경로

    Returns:
        dict: 계측 결과
    """
    record = {"path": inScenePath, "ok": False, "error": None}

    rt.resetMaxFile(rt.Name("noPrompt"))
    loadStart = time.time()
    loadProbe = _try("loadMaxFile", lambda: bool(rt.loadMaxFile(inScenePath)))
    record["loadSeconds"] = round(time.time() - loadStart, 2)
    if not loadProbe["ok"] or loadProbe["value"] is not True:
        record["error"] = loadProbe["error"] or "loadMaxFile이 True를 돌려주지 않음"
        return record
    _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))

    sweepStart = time.time()
    missingPaths = _missing_asset_paths()
    assignedMaterials = _node_material_map()
    texmapInfo = _texmap_records(missingPaths, assignedMaterials)
    traceInfo = _trace_unmatched(missingPaths, texmapInfo.pop("matchedPaths"))
    record["sweepSeconds"] = round(time.time() - sweepStart, 2)

    record["ok"] = True
    record["nodeCount"] = len(list(rt.objects))
    record["missingAssetCount"] = len(missingPaths)
    record["missingByType"] = dict(
        sorted(Counter(item["assetType"] for item in missingPaths.values()).items())
    )
    record["assignedMaterialCount"] = len(assignedMaterials)
    record.update(texmapInfo)
    record["unmatchedTrace"] = traceInfo
    return record


reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

_deadline = time.time() + SECTION_BUDGET
for _scenePath in TARGET_SCENES:
    if time.time() > _deadline:
        RESULT["scenes"].append({"path": _scenePath, "skipped": "예산 초과"})
        continue
    try:
        RESULT["scenes"].append(_sweep(_scenePath))
        reporter.assert_test(True, f"TC {Path(_scenePath).name} 스윕", "")
    except Exception:
        RESULT["scenes"].append({"path": _scenePath, "fatal": traceback.format_exc(limit=6)})
        reporter.error(f"TC {Path(_scenePath).name} 스윕", traceback.format_exc(limit=4))
    _flush()

_swept = [item for item in RESULT["scenes"] if item.get("ok")]
RESULT["summary"] = {
    "sceneCount": len(_swept),
    "missingAssetTotal": sum(item.get("missingAssetCount", 0) for item in _swept),
    "brokenTexmapTotal": sum(item.get("brokenTexmapCount", 0) for item in _swept),
    "materialTotal": sum(item.get("materialCount", 0) for item in _swept),
    "texmapWithNoMaterialTotal": sum(item.get("texmapWithNoMaterial", 0) for item in _swept),
    "texmapWithNoNodeTotal": sum(item.get("texmapWithNoNode", 0) for item in _swept),
    "unmatchedTotal": sum(
        (item.get("unmatchedTrace") or {}).get("unmatchedCount", 0) for item in _swept
    ),
    "tracedTotal": sum(
        (item.get("unmatchedTrace") or {}).get("tracedCount", 0) for item in _swept
    ),
    "stillUnknownTotal": sum(
        (item.get("unmatchedTrace") or {}).get("stillUnknownCount", 0) for item in _swept
    ),
    "sweepSecondsTotal": round(sum(item.get("sweepSeconds", 0) for item in _swept), 2),
}
_flush()
reporter.summary()
reporter.close()
