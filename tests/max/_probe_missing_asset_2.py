#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **2차** - 1차가 틀린 것을 재고 실태를 다시 센다.

**왜 2차가 있는가.** 1차(`_probe_missing_asset.py`)는 애셋 열거를
`getClassInstances(BitmapTexture)`로 했다. 그 경로는 프로덕션 씬에서 **누락을 한 건도
못 찾았다**(8씬 전량 0건). 모집단이 깨끗해서가 아니라 **질문이 틀렸다** - 이 워크스페이스의
프로덕션 머티리얼은 `DirectX_9_Shader`이고 텍스쳐가 셰이더 **파라미터** 안에 있어
`BitmapTexture` 인스턴스로 열거되지 않는다(1차 결과 `byChannel`에 `BitmapTexture`가
0건, `DirectX_9_Shader:value` 1건만 찍힌 것이 그 지문이다).

1차 JSON을 지우지 않는 이유가 이것이다 - **왜 그 열거 경로를 쓰면 안 되는지**가 거기
남아 있다(`max/max_test_pattern.md` §6원칙, 프로브 한정 규율).

1차가 **확정한** 것은 다시 재지 않는다. 2차는 다음만 다룬다.

    A2  `AssetManager` 기반 열거 - 누락 판정 축(`GetFullFilePath()` 공백)의 실증,
        오탐 원인(미저장 씬 self-xref / Max 설치본 기본 맵) 분리 (P0-3 재측정)
    E2  `Missing_*` 클래스의 `superClassOf` - **인스턴스 없이** R2를 닫는다 (P0-5/P0-7)
    H2  프로덕션 실태 재측정 - 교정된 스캐너로, **누락 후보가 많은 순** 표본 (P0-9/P0-10)

실행:
    uv run python tests/_run_probe.py _probe_missing_asset_2.py 1800

결과:
    tests/logs/probe_missing_asset_2.json
"""

import json
import os
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
RESULT_PATH = LOG_DIR / "probe_missing_asset_2.json"
STATIC_RESULT_PATH = LOG_DIR / "probe_missing_asset_static.json"

MISSING_ROOT = "D:/__pyjallib_missing_probe__"

#: 섹션 H2의 씬 로드 예산(초).
SECTION_H2_BUDGET = 1200.0

#: 표본에 반드시 넣을 대형 실기 씬. 소품만 보면 실태를 오판한다(1차의 표본이
#: 노드 1~4개짜리 소품이었다 - 크기 오름차순으로 골라서 그렇게 됐다).
FORCED_SCENES = (
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default/SK_JeongHuiwon_Mn_Default.max",
    r"E:/DevStorage_root/DevStorage/Characters/Main/HanMyeongoh/MeshB/Default/SK_HanMyeongoh_Mn_Default.max",
)

reporter = TestReporter("ProbeMissingAsset2", LOG_DIR)

RESULT = {
    "loadedFrom": getattr(pyjallib, "__file__", None),
    "maxVersion": None,
    "A2": {},
    "E2": {},
    "H2": {},
}


def _flush():
    """지금까지의 결과를 JSON으로 덮어쓴다."""
    RESULT_PATH.write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
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
        value = inFunc()
    except Exception:
        return {
            "label": inLabel,
            "ok": False,
            "value": None,
            "error": traceback.format_exc(limit=4),
        }
    return {"label": inLabel, "ok": True, "value": value, "error": None}


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _node_axes(inNode):
    """노드의 판정 축을 함께 덤프한다.

    Args:
        inNode: 대상 노드

    Returns:
        dict: 이름·핸들과 판정 축들
    """
    axes = {
        "name": None,
        "handle": None,
        "classOfNode": None,
        "classOfBaseObject": None,
        "superClassOfNode": None,
        "isGeometry": None,
        "errors": [],
    }
    for key, getter in (
        ("name", lambda: str(inNode.name)),
        ("handle", lambda: int(rt.getHandleByAnim(inNode))),
        ("classOfNode", lambda: str(rt.classOf(inNode))),
        ("classOfBaseObject", lambda: str(rt.classOf(inNode.baseObject))),
        ("superClassOfNode", lambda: str(rt.superClassOf(inNode))),
        ("isGeometry", lambda: bool(rt.superClassOf(inNode) == rt.GeometryClass)),
    ):
        try:
            axes[key] = getter()
        except Exception as exc:
            axes["errors"].append(f"{key}: {exc}")
    return axes


# ============================================================
# 교정된 스캐너 - `AssetManager` 경유
# ============================================================


def _asset_entries():
    """`AssetManager`로 씬의 애셋을 전부 열거한다.

    1차 실측으로 확정된 축:

    - `AssetManager.GetNumAssets()` -> int
    - `AssetManager.GetAssetByIndex(i)` -> AssetUser (**1-based**)
    - `assetUser.GetFileName()` -> 선언된 경로
    - `assetUser.GetFullFilePath()` -> **해석된 절대 경로. 해석 실패 시 빈 문자열**
    - `assetUser.GetType()` -> "bitmap" | "xref" | ...

    `GetFullFilePath()`가 비었는지로 부재를 판정하면 Max 자신의 애셋 탐색(맵 경로·상대
    경로 해석)을 그대로 쓰게 된다. `os.path.exists` 자체 판정은 그 탐색을 재구현해야 해서
    **상대 경로에서 갈린다**(Q1의 답).

    Returns:
        list[dict]: 애셋별 레코드
    """
    assetMan = getattr(rt, "AssetManager", None)
    if assetMan is None:
        return []

    countProbe = _try("GetNumAssets", lambda: int(assetMan.GetNumAssets()))
    if not countProbe["ok"]:
        return []

    entries = []
    for index in range(1, (countProbe["value"] or 0) + 1):
        userProbe = _try(f"GetAssetByIndex({index})", lambda i=index: assetMan.GetAssetByIndex(i))
        assetUser = userProbe["value"]
        if assetUser is None:
            entries.append({"index": index, "error": userProbe["error"]})
            continue

        entry = {"index": index, "error": None, "assetUser": assetUser}
        for key, getter in (
            ("fileName", lambda a=assetUser: str(a.GetFileName())),
            ("fullFilePath", lambda a=assetUser: str(a.GetFullFilePath())),
            ("assetType", lambda a=assetUser: str(a.GetType())),
        ):
            probe = _try(key, getter)
            entry[key] = probe["value"] if probe["ok"] else None
            if not probe["ok"]:
                entry.setdefault("accessErrors", []).append(f"{key}: {probe['error']}")
        entries.append(entry)
    return entries


def _dependent_nodes(inAssetUser):
    """애셋에 의존하는 노드를 돌려준다.

    `AssetUser`는 참조 대상이 아니므로 `refs.dependentNodes`의 기점이 되지 못한다.
    그래서 애셋 파일명으로 되짚는 대신 **씬 전체를 한 번 훑어** 노드별 애셋 참조를
    모으는 경로를 쓴다(`_node_asset_map`).

    Args:
        inAssetUser: AssetManager가 돌려준 AssetUser

    Returns:
        list: 항상 빈 목록. 역추적은 `_node_asset_map`이 담당한다
    """
    return []


def _node_asset_map():
    """노드 -> 그 노드가 (간접적으로라도) 참조하는 애셋 파일 경로 집합을 만든다.

    `refs.dependentNodes`는 **참조 대상(ReferenceTarget)**을 기점으로 받는다. 1차에서
    확정했듯 비트맵 텍스쳐를 기점으로 주면 머티리얼을 건너뛰고 노드까지 닿는다. 그러나
    `AssetManager`가 돌려주는 `AssetUser`는 참조 대상이 아니라 **기록**이라 기점이 되지
    못한다. 그래서 반대 방향으로 간다 - 애셋을 물 수 있는 참조 대상을 클래스로 열거하고,
    각각에서 `dependentNodes`로 노드를 얻은 뒤 경로를 붙인다.

    Returns:
        dict: `{경로(소문자, 슬래시 통일): [노드, ...]}`
    """
    byPath = {}

    for className, propName in (
        ("BitmapTexture", "filename"),
        ("DirectX_9_Shader", "effectfile"),
        ("VRayHDRI", "HDRIMapName"),
    ):
        klass = getattr(rt, className, None)
        if klass is None:
            continue
        instancesProbe = _try(f"getClassInstances({className})", lambda k=klass: list(
            rt.getClassInstances(k)
        ))
        for instance in instancesProbe["value"] or []:
            pathProbe = _try("경로", lambda i=instance, p=propName: rt.getProperty(i, p))
            if not pathProbe["ok"]:
                continue
            value = pathProbe["value"]
            if value is None or isinstance(value, (bool, int, float)):
                continue
            text = str(value)
            if not text:
                continue
            nodesProbe = _try("dependentNodes", lambda i=instance: list(
                rt.refs.dependentNodes(i)
            ))
            byPath.setdefault(_norm_path(text), []).extend(nodesProbe["value"] or [])

        # DirectX_9_Shader는 텍스쳐를 **파라미터**로 갖는다. 이름은 후보를 좁히고
        # 값만이 판정한다 - 이름에 texture가 든 bool 파라미터가 실재한다.
        if className == "DirectX_9_Shader":
            for instance in instancesProbe["value"] or []:
                nodesProbe = _try("dependentNodes", lambda i=instance: list(
                    rt.refs.dependentNodes(i)
                ))
                nodes = nodesProbe["value"] or []
                namesProbe = _try("getPropNames", lambda i=instance: [
                    str(name) for name in rt.getPropNames(i)
                ])
                for propertyName in namesProbe["value"] or []:
                    if "texture" not in propertyName.lower():
                        continue
                    valueProbe = _try("슬롯", lambda i=instance, n=propertyName: rt.getProperty(i, n))
                    if not valueProbe["ok"]:
                        # 접근 예외 = 텍스쳐가 물려 있는데 못 열었다.
                        byPath.setdefault(
                            _norm_path(f"<accessError:{propertyName}>"), []
                        ).extend(nodes)
                        continue
                    slotValue = valueProbe["value"]
                    if slotValue is None or isinstance(slotValue, (bool, int, float)):
                        continue
                    fileProbe = _try("슬롯 filename", lambda v=slotValue: rt.getProperty(v, "filename"))
                    if not fileProbe["ok"] or not fileProbe["value"]:
                        continue
                    byPath.setdefault(_norm_path(str(fileProbe["value"])), []).extend(nodes)

    return byPath


def _norm_path(inPath):
    """경로를 비교용으로 정규화한다.

    Args:
        inPath: 원본 경로

    Returns:
        str: 소문자 + 정방향 슬래시
    """
    return str(inPath or "").replace("\\", "/").lower()


def _scan_scene():
    """씬을 스캔해 누락 애셋과 그 의존 노드를 모은다(교정판).

    Returns:
        dict: 애셋 레코드와 집계
    """
    entries = _asset_entries()
    nodeMap = _node_asset_map()

    missing = []
    resolved = 0
    orphan = 0
    typeCounter = Counter()

    for entry in entries:
        if entry.get("error"):
            continue
        fullPath = entry.get("fullFilePath") or ""
        fileName = entry.get("fileName") or ""
        assetType = entry.get("assetType") or "<없음>"

        if fullPath:
            resolved += 1
            continue

        nodes = nodeMap.get(_norm_path(fileName), [])
        typeCounter[assetType] += 1
        if not nodes:
            # 의존 노드가 하나도 없는 애셋. 미저장 씬의 self-xref("Untitled Scene")가
            # 여기에 걸린다 - 노드 기반 계획에는 기여할 것이 없다.
            orphan += 1

        missing.append({
            "fileName": fileName,
            "assetType": assetType,
            "nodes": [_node_axes(node) for node in nodes],
        })

    geometryCount = 0
    nonGeometryCount = 0
    unknownCount = 0
    seenHandles = set()
    for asset in missing:
        for axes in asset["nodes"]:
            handle = axes.get("handle")
            if handle in seenHandles:
                continue
            seenHandles.add(handle)
            if axes.get("isGeometry") is True:
                geometryCount += 1
            elif axes.get("isGeometry") is False:
                nonGeometryCount += 1
            else:
                unknownCount += 1

    return {
        "assetTotal": len(entries),
        "resolvedCount": resolved,
        "missingCount": len(missing),
        "orphanCount": orphan,
        "missingByType": dict(sorted(typeCounter.items())),
        "geometryNodeCount": geometryCount,
        "nonGeometryNodeCount": nonGeometryCount,
        "unknownNodeCount": unknownCount,
        "assets": missing,
    }


# ============================================================
# A2 - AssetManager 판정 축 실증
# ============================================================


def section_a2():
    """A2 - `GetFullFilePath()` 공백이 부재 축으로 성립하는지 실증한다."""
    _reset_scene()

    box = rt.Box(name="a2_geo_missing", mapcoords=True)
    material = rt.StandardMaterial(name="a2_mat")
    material.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/a2_missing.png")
    box.material = material

    okBox = rt.Box(name="a2_geo_ok", mapcoords=True)
    okMaterial = rt.StandardMaterial(name="a2_mat_ok")
    installedMap = str(
        Path(r"C:/Program Files/Autodesk/3ds Max 2024/maps/uvwunwrap/UV_Checker.png")
    )
    okMaterial.diffuseMap = rt.BitmapTexture(filename=installedMap)
    okBox.material = okMaterial

    light = rt.OmniLight(name="a2_light_missing")
    light.projector = True
    light.projectorMap = rt.BitmapTexture(filename=MISSING_ROOT + "/a2_projector.png")

    out = {
        "assertions": {
            "missingRootAbsent": not os.path.exists(MISSING_ROOT),
            "installedMapExists": os.path.exists(installedMap),
            "nodeCount": len(list(rt.objects)),
        },
        "entries": [],
    }

    for entry in _asset_entries():
        record = {key: value for key, value in entry.items() if key != "assetUser"}
        record["osExists"] = os.path.exists(entry.get("fileName") or "")
        record["fullPathEmpty"] = not (entry.get("fullFilePath") or "")
        out["entries"].append(record)

    # 판정 축 대조 - 두 축이 갈리는 지점이 있는가.
    disagreements = [
        item
        for item in out["entries"]
        if item.get("fullPathEmpty") is not (not item.get("osExists"))
    ]
    out["axisDisagreements"] = disagreements
    out["scan"] = {
        key: value for key, value in _scan_scene().items() if key != "assets"
    }
    out["scanAssets"] = _scan_scene()["assets"]

    # ATSOps 교차 확인 - 1차에서 byref 수신이 확정됐다.
    atsOps = getattr(rt, "ATSOps", None)
    out["atsCrossCheck"] = _try(
        "ATSOps.GetFiles(byref) 워커",
        lambda: str(rt.execute("(local f = #(); ATSOps.GetFiles &f; f as string)")),
    ) if atsOps is not None else {"ok": False, "error": "ATSOps 미노출"}
    return out


# ============================================================
# E2 - Missing_* 클래스의 수퍼클래스 (R2를 인스턴스 없이 닫는다)
# ============================================================


def section_e2():
    """E2 - `Missing_*` 클래스의 `superClassOf`를 직접 읽는다.

    Missing 플러그인 객체는 합성으로 만들 수 없다(플러그인 DLL 부재가 전제). 그러나
    **클래스 값 자체의 수퍼클래스**는 인스턴스 없이 읽을 수 있고, 그것이 곧 그 객체가
    `isGeometry` 축에서 어느 쪽으로 떨어질지를 말해 준다 - R2를 Max 재기동 없이 닫는다.
    """
    out = {"classes": [], "geometryClass": _try("GeometryClass", lambda: str(rt.GeometryClass))}
    for name in (
        "Missing_GeomObject",
        "Missing_Helper",
        "Missing_Light",
        "Missing_Camera",
        "Missing_Shape",
        "Missing_System",
        "Missing_Modifier",
        "Missing_Material",
        "Missing_Texmap",
        "Missing_Controller",
    ):
        classProbe = _try(f"rt.{name}", lambda n=name: rt.execute(n))
        entry = {"name": name, "exposed": classProbe["ok"] and classProbe["value"] is not None}
        if entry["exposed"]:
            klass = classProbe["value"]
            superProbe = _try("superClassOf", lambda k=klass: str(rt.superClassOf(k)))
            entry["superClassOf"] = superProbe["value"] if superProbe["ok"] else superProbe["error"]
            entry["isGeometryClass"] = _try(
                "== GeometryClass", lambda k=klass: bool(rt.superClassOf(k) == rt.GeometryClass)
            )["value"]
        out["classes"].append(entry)
    return out


# ============================================================
# H2 - 프로덕션 실태 재측정
# ============================================================


def _h2_targets():
    """표본을 고른다 - 누락 후보가 **많은 순**, 그리고 대형 실기 씬을 강제 포함.

    1차는 크기 오름차순으로 골라 노드 1~4개짜리 소품만 봤다. 그 표본으로는 실태를
    말할 수 없다.

    Returns:
        list[tuple]: `(경로, 그룹)` 목록
    """
    targets = [(path, "forced") for path in FORCED_SCENES if os.path.exists(path)]

    if not STATIC_RESULT_PATH.exists():
        return targets
    try:
        data = json.loads(STATIC_RESULT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return targets

    scenes = [item for item in data.get("scenes", []) if item.get("scannable")]
    withMissing = sorted(
        (item for item in scenes if item.get("absoluteMissing", 0) > 0),
        key=lambda item: item.get("absoluteMissing", 0),
        reverse=True,
    )
    control = sorted(
        (item for item in scenes if item.get("absoluteMissing", 0) == 0),
        key=lambda item: item.get("sizeBytes", 0),
        reverse=True,
    )
    targets += [(item["path"], "withMissing") for item in withMissing[:8]]
    targets += [(item["path"], "control") for item in control[:3]]
    return targets


def _sweep(inScenePath):
    """씬 하나를 열어 스윕 비용과 실태를 함께 잰다. 씬을 바꾸지 않는다.

    Args:
        inScenePath: 열 `.max` 경로

    Returns:
        dict: 계측 결과
    """
    record = {"path": inScenePath, "ok": False, "error": None}

    _reset_scene()
    loadStart = time.time()
    loadProbe = _try("loadMaxFile", lambda: bool(rt.loadMaxFile(inScenePath)))
    record["loadSeconds"] = round(time.time() - loadStart, 2)
    if not loadProbe["ok"] or loadProbe["value"] is not True:
        record["error"] = loadProbe["error"] or "loadMaxFile이 True를 돌려주지 않음"
        return record

    _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))
    record["nodeCount"] = len(list(rt.objects))

    sweepStart = time.time()
    scan = _scan_scene()
    record["sweepSeconds"] = round(time.time() - sweepStart, 2)
    record["ok"] = True

    record.update({
        key: value for key, value in scan.items() if key != "assets"
    })
    record["assetSamples"] = [
        {
            "fileName": asset["fileName"],
            "assetType": asset["assetType"],
            "nodeCount": len(asset["nodes"]),
            "nodeNames": [axes["name"] for axes in asset["nodes"]][:8],
            "geometryFlags": [axes["isGeometry"] for axes in asset["nodes"]][:8],
            "nodeClasses": [axes["classOfNode"] for axes in asset["nodes"]][:8],
        }
        for asset in scan["assets"][:25]
    ]
    record["assetSamplesTruncated"] = len(scan["assets"]) > 25

    # Missing 플러그인 객체 실태 - 클래스 이름이 Missing으로 시작하는 노드.
    pluginNodes = []
    for node in rt.objects:
        axes = _node_axes(node)
        names = [axes.get("classOfNode") or "", axes.get("classOfBaseObject") or ""]
        if any(name.lower().startswith("missing") for name in names):
            pluginNodes.append(axes)
    record["missingPluginNodeCount"] = len(pluginNodes)
    record["missingPluginSamples"] = pluginNodes[:10]
    return record


def section_h2():
    """H2 - 교정된 스캐너로 프로덕션 실태와 스윕 비용을 다시 잰다 (P0-9, P0-10)."""
    targets = _h2_targets()
    out = {"targets": [{"path": path, "group": group} for path, group in targets],
           "scenes": [], "skipped": [], "budgetSeconds": SECTION_H2_BUDGET}

    deadline = time.time() + SECTION_H2_BUDGET
    for scenePath, group in targets:
        if time.time() > deadline:
            out["skipped"].append({"path": scenePath, "group": group, "why": "예산 초과"})
            continue
        record = _sweep(scenePath)
        record["group"] = group
        out["scenes"].append(record)
        _flush()

    swept = [item for item in out["scenes"] if item["ok"]]
    loadTotal = round(sum(item.get("loadSeconds", 0) for item in swept), 2)
    sweepTotal = round(sum(item.get("sweepSeconds", 0) for item in swept), 2)

    typeCounter = Counter()
    for item in swept:
        for assetType, count in (item.get("missingByType") or {}).items():
            typeCounter[assetType] += count

    out["summary"] = {
        "sceneCount": len(swept),
        "loadSecondsTotal": loadTotal,
        "sweepSecondsTotal": sweepTotal,
        "sweepShareOfLoad": round(sweepTotal / loadTotal, 4) if loadTotal > 0 else None,
        "sweepSecondsMax": max((item.get("sweepSeconds", 0) for item in swept), default=0),
        "assetTotal": sum(item.get("assetTotal", 0) for item in swept),
        "missingTotal": sum(item.get("missingCount", 0) for item in swept),
        "orphanTotal": sum(item.get("orphanCount", 0) for item in swept),
        "missingByType": dict(sorted(typeCounter.items())),
        "geometryNodeTotal": sum(item.get("geometryNodeCount", 0) for item in swept),
        "nonGeometryNodeTotal": sum(item.get("nonGeometryNodeCount", 0) for item in swept),
        "unknownNodeTotal": sum(item.get("unknownNodeCount", 0) for item in swept),
        "missingPluginNodeTotal": sum(item.get("missingPluginNodeCount", 0) for item in swept),
        "scenesWithMissing": len([item for item in swept if item.get("missingCount", 0) > 0]),
    }
    return out


# ============================================================
# 실행
# ============================================================

RESULT["maxVersion"] = _try("maxVersion", lambda: [str(item) for item in rt.maxVersion()])

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

for sectionKey, sectionFunc in (("A2", section_a2), ("E2", section_e2), ("H2", section_h2)):
    started = time.time()
    try:
        RESULT[sectionKey] = sectionFunc()
        RESULT[sectionKey]["elapsedSeconds"] = round(time.time() - started, 2)
        reporter.assert_test(
            True, f"TC-{sectionKey} 섹션 완주", f"{round(time.time() - started, 2)}초"
        )
    except Exception:
        RESULT[sectionKey] = {"fatal": traceback.format_exc(limit=8)}
        reporter.error(f"TC-{sectionKey} 섹션 완주", traceback.format_exc(limit=4))
    _flush()

_flush()
reporter.summary()
reporter.close()
