#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 (Phase 0 / PyJalLib MissingAsset 사이클).

PRD `.ai_planning/active/PyJalLib/active_prd.md` §4의 미확정 10건(P0-1~P0-10)을
**한 실행**으로 닫는다. 3dsmaxbatch 왕복이 비싸므로 섹션을 한 파일에 몰아 넣고
(`max/max_test_pattern.md` §프로브 설계 4원칙 제2원칙) 섹션마다 즉시 JSON을 flush해
뒤 섹션이 죽어도 앞 결과가 남게 한다.

섹션:
    A  `rt.ATSOps` / `rt.AssetManager` / `rt.objXRefMgr` 노출·헤드레스 동작·byref 수신,
       `IsFileMissing`/`GetFileAssetType`/`GetFileStatus` 반환 형태 (P0-1~P0-3).
       **폴백(`getClassInstances` 자체 열거)을 같은 섹션에 동봉**한다 - 반대로 나와도
       Max 재기동 없이 갈아탄다.
    B  ATS 열거 ∆ 클래스 인스턴스 열거의 **차집합 양방향** (P0-4)
    C  Missing 플러그인 객체 판정 축 3종 덤프 (P0-5)
    D  애셋 → 의존 노드 역추적 호출 형태 비교 (P0-6)
    E  지오메트리 판별 축 **분포표** - 노드 종류별 (P0-7)
    F  삭제·undo·멱등 (P0-8). 프로덕션 씬은 **임시 사본에서만**
    G  씬 전체 스윕 비용 - 씬 로드 시간과 함께 (P0-9)
    H  프로덕션 실기 씬 실태 - 건수·지오메트리 비율·종류 분포 (P0-10)

**판정 축은 결과 JSON 단독이다.** `3dsmaxbatch.exe`는 정상 완주해도 종료 코드
`4294967166`을 낸다(`patterns/subprocess_verdict_axis.md`).

실행:
    uv run python tests/_run_probe.py _probe_missing_asset.py 1800

결과:
    tests/logs/probe_missing_asset.json
"""

import json
import os
import shutil
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

# pyjallib 소스 경로 선주입 + 배포본 선점 퍼지 (다른 pyjallib import보다 앞).
sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

import pymxs  # noqa: E402
from pymxs import runtime as rt  # noqa: E402

import pyjallib  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = LOG_DIR / "probe_missing_asset.json"
STATIC_RESULT_PATH = LOG_DIR / "probe_missing_asset_static.json"
TEMP_DIR = LOG_DIR / "_probe_tmp"

#: 존재하지 않는 디렉토리. 합성 씬의 누락 애셋이 여기를 가리킨다.
MISSING_ROOT = "D:/__pyjallib_missing_probe__"

#: 비트맵 접근 예외에서 경로를 뽑는 마커. strict가 실측된 형태고 loose는 버전 차이 대비.
STRICT_BITMAP_MARKER = "Error opening bitmap: "
LOOSE_BITMAP_MARKER = "bitmap: "

#: 섹션 H의 씬 로드 예산(초). 넘으면 남은 씬을 건너뛰고 건너뛴 사실을 남긴다.
SECTION_H_BUDGET = 900.0

reporter = TestReporter("ProbeMissingAsset", LOG_DIR)

RESULT = {
    "loadedFrom": getattr(pyjallib, "__file__", None),
    "maxVersion": None,
    "A": {},
    "B": {},
    "C": {},
    "D": {},
    "E": {},
    "F": {},
    "G": {},
    "H": {},
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


def _members(inObject):
    """객체의 공개 멤버 이름 목록을 돌려준다.

    Args:
        inObject: 조사할 객체

    Returns:
        list[str] | None: 멤버 이름 목록. 조회에 실패하면 None
    """
    try:
        return sorted(name for name in dir(inObject) if not name.startswith("_"))
    except Exception:
        return None


def _mxs_name(inValue):
    """MAXScript 값의 클래스 이름을 문자열로 돌려준다.

    Args:
        inValue: 대상 값

    Returns:
        str | None: 클래스 이름. 조회 실패 시 None
    """
    try:
        return str(rt.classOf(inValue))
    except Exception:
        return None


def _extract_missing_bitmap_path(inErrorMessage):
    """비트맵 접근 예외 메시지에서 경로를 뽑는다.

    마커를 못 찾으면 빈 문자열이 아니라 **메시지 전문을 보존**한다(fail-loud).

    Args:
        inErrorMessage: 예외 메시지

    Returns:
        str: 뽑아낸 경로, 또는 메시지 전문
    """
    message = str(inErrorMessage)
    for marker in (STRICT_BITMAP_MARKER, LOOSE_BITMAP_MARKER):
        index = message.find(marker)
        if index >= 0:
            return message[index + len(marker):].strip()
    return message.strip()


def _probe_filename(inObject, inPropName="filename"):
    """객체의 파일 프로퍼티를 읽되 **두 예외 채널을 분리해** 돌려준다.

    `accessError`(접근 예외 = 애셋이 물려 있다)와 `notTexture`(값이 애셋이 아님)를
    합치면 bool 파라미터가 누락으로 새어나간다
    (`patterns/texture_extraction_pattern.md` §10).

    Args:
        inObject: 대상 객체
        inPropName: 읽을 프로퍼티 이름. 기본값 "filename"

    Returns:
        dict: `{"channel", "filename", "raw"}`.
            channel은 accessError / none / notTexture / value 중 하나
    """
    try:
        value = rt.getProperty(inObject, inPropName)
    except Exception as exc:
        return {
            "channel": "accessError",
            "filename": _extract_missing_bitmap_path(exc),
            "raw": str(exc)[:400],
        }

    if value is None:
        return {"channel": "none", "filename": None, "raw": None}
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return {"channel": "notTexture", "filename": None, "raw": repr(value)[:120]}

    text = str(value)
    if not text:
        # 경로가 비어 있어도 "애셋이 물려 있다"는 판정은 유지된다(실측 선례).
        return {"channel": "value", "filename": "", "raw": None}
    return {"channel": "value", "filename": text, "raw": None}


# ============================================================
# 잠정 스캐너 - 섹션 B/F/G/H가 공유한다.
# Phase 2의 프로덕션 구현이 아니라 **측정 도구**다.
# ============================================================

#: 외부 파일을 물 수 있는 클래스와 그 파일 프로퍼티 이름.
ASSET_CLASS_SPECS = (
    ("BitmapTexture", "filename"),
    ("DirectX_9_Shader", "effectfile"),
    ("VRayHDRI", "HDRIMapName"),
    ("Substance_Output", "filename"),
)


def _asset_class_instances():
    """씬의 애셋 보유 객체를 클래스별로 열거한다.

    Returns:
        dict: `{클래스명: {"available": bool, "instances": list, "error": str | None}}`
    """
    found = {}
    for className, propName in ASSET_CLASS_SPECS:
        klass = getattr(rt, className, None)
        if klass is None:
            found[className] = {
                "available": False,
                "propName": propName,
                "instances": [],
                "error": "클래스가 rt에 없음",
            }
            continue
        probe = _try(f"getClassInstances({className})", lambda k=klass: list(rt.getClassInstances(k)))
        found[className] = {
            "available": True,
            "propName": propName,
            "instances": probe["value"] or [],
            "error": probe["error"],
        }
    return found


def _scan_missing_files():
    """클래스 인스턴스 열거 경로로 누락 외부 파일을 찾는다(폴백 경로).

    Returns:
        dict: `{"assets": [...], "byChannel": {...}, "errors": [...]}`
    """
    assets = []
    channelCounts = Counter()
    errors = []

    for className, info in _asset_class_instances().items():
        if info["error"]:
            errors.append({"className": className, "error": info["error"]})
        for instance in info["instances"]:
            probe = _probe_filename(instance, info["propName"])
            channelCounts[f"{className}:{probe['channel']}"] += 1

            if probe["channel"] == "notTexture" or probe["channel"] == "none":
                continue

            filePath = probe["filename"]
            if probe["channel"] == "accessError":
                # 접근 예외 = 애셋이 물려 있다. 경로를 못 뽑아도 누락으로 센다.
                assets.append({
                    "kind": "file",
                    "className": className,
                    "path": filePath,
                    "why": "accessError",
                    "object": instance,
                })
                continue

            if not filePath:
                continue
            if _resolve_exists(filePath):
                continue
            assets.append({
                "kind": "file",
                "className": className,
                "path": filePath,
                "why": "notFound",
                "object": instance,
            })

    return {"assets": assets, "byChannel": dict(channelCounts), "errors": errors}


def _resolve_exists(inFilePath):
    """애셋 경로가 실제로 존재하는지 판정한다.

    절대 경로면 그대로 보고, 상대 경로·맨 파일명이면 Max의 애셋 탐색에 맡긴다
    (`rt.mapPaths.getFullFilePath`). 해석에 실패하면 부재로 본다.

    Args:
        inFilePath: 판정할 경로

    Returns:
        bool: 존재하면 True
    """
    if not inFilePath:
        return False
    if os.path.isabs(inFilePath) and os.path.exists(inFilePath):
        return True

    probe = _try(
        "mapPaths.getFullFilePath",
        lambda: rt.mapPaths.getFullFilePath(inFilePath),
    )
    resolved = probe["value"]
    if resolved:
        return os.path.exists(str(resolved))
    return False


def _scan_missing_plugins():
    """로드되지 않은 플러그인 객체(Missing 계열)를 열거한다.

    판정 축은 섹션 C가 확정한다. 여기서는 **클래스 이름이 "Missing"으로 시작**하는
    것을 후보로 잡고 세 축을 함께 기록한다.

    Returns:
        list[dict]: 후보 노드 정보 목록
    """
    found = []
    for node in rt.objects:
        axes = _node_axes(node)
        names = [
            axes.get("classOfNode") or "",
            axes.get("classOfBaseObject") or "",
        ]
        if any(name.lower().startswith("missing") for name in names):
            found.append(axes)
    return found


def _node_axes(inNode):
    """노드의 판정 축 4종을 함께 덤프한다.

    한 축만 찍으면 그 축이 기대와 다를 때 다시 Max를 띄워야 한다.

    Args:
        inNode: 대상 노드

    Returns:
        dict: 이름·핸들과 네 축의 값
    """
    axes = {
        "name": None,
        "handle": None,
        "classOfNode": None,
        "classOfBaseObject": None,
        "superClassOfNode": None,
        "superClassOfBaseObject": None,
        "isGeometry": None,
        "errors": [],
    }
    for key, getter in (
        ("name", lambda: str(inNode.name)),
        ("handle", lambda: int(rt.getHandleByAnim(inNode))),
        ("classOfNode", lambda: str(rt.classOf(inNode))),
        ("classOfBaseObject", lambda: str(rt.classOf(inNode.baseObject))),
        ("superClassOfNode", lambda: str(rt.superClassOf(inNode))),
        ("superClassOfBaseObject", lambda: str(rt.superClassOf(inNode.baseObject))),
        ("isGeometry", lambda: bool(rt.superClassOf(inNode) == rt.GeometryClass)),
    ):
        try:
            axes[key] = getter()
        except Exception as exc:
            axes["errors"].append(f"{key}: {exc}")
    return axes


# ============================================================
# 섹션 A - ATS / AssetManager / objXRefMgr 노출과 반환 형태 (P0-1~P0-3)
# ============================================================


def _build_synthetic_scene():
    """누락 애셋을 물린 합성 씬을 만든다.

    구성:
        probe_geo_missing   Box + StandardMaterial(diffuseMap = 없는 비트맵)  -> 지오메트리
        probe_geo_ok        Box, 맵 없음                                      -> 지오메트리 대조군
        probe_light_missing OmniLight + projectorMap(없는 비트맵)             -> 비지오메트리
        probe_helper_plain  Point 헬퍼, 애셋 없음                             -> 비지오메트리 대조군

    Returns:
        dict: 생성 결과와 **사전 어서션** 값.
            테스트가 만들려던 조건이 실제로 만들어졌는지 먼저 단정한다
            (`max/max_test_pattern.md`).
    """
    _reset_scene()
    built = {"steps": [], "assertions": {}}

    geoMissing = rt.Box(name="probe_geo_missing", mapcoords=True)
    material = rt.StandardMaterial(name="probe_mat_missing")
    diffuseTexture = rt.BitmapTexture(filename=MISSING_ROOT + "/missing_diffuse.png")
    material.diffuseMap = diffuseTexture
    geoMissing.material = material
    built["steps"].append(_try("geoMissing", lambda: str(geoMissing.name)))

    geoOk = rt.Box(name="probe_geo_ok", mapcoords=True)
    built["steps"].append(_try("geoOk", lambda: str(geoOk.name)))

    light = rt.OmniLight(name="probe_light_missing")
    projectorTexture = rt.BitmapTexture(filename=MISSING_ROOT + "/missing_projector.png")
    built["steps"].append(_try("light.projector=True", lambda: setattr(light, "projector", True)))
    built["steps"].append(
        _try("light.projectorMap", lambda: setattr(light, "projectorMap", projectorTexture))
    )

    helper = rt.Point(name="probe_helper_plain")
    built["steps"].append(_try("helper", lambda: str(helper.name)))

    # 사전 어서션 - 만들려던 조건이 실제로 만들어졌는가.
    built["assertions"] = {
        "missingRootAbsent": not os.path.exists(MISSING_ROOT),
        "bitmapInstances": len(_try(
            "getClassInstances(BitmapTexture)",
            lambda: list(rt.getClassInstances(rt.BitmapTexture)),
        )["value"] or []),
        "geoMissingIsGeometry": bool(rt.superClassOf(geoMissing) == rt.GeometryClass),
        "lightIsGeometry": bool(rt.superClassOf(light) == rt.GeometryClass),
        "helperIsGeometry": bool(rt.superClassOf(helper) == rt.GeometryClass),
        "nodeCount": len(list(rt.objects)),
    }
    return built


def section_a():
    """A - ATSOps / AssetManager / objXRefMgr 실측 (P0-1~P0-3)."""
    out = {}
    out["scene"] = _build_synthetic_scene()

    # --- ATSOps ---
    atsOps = getattr(rt, "ATSOps", None)
    out["ATSOps"] = {
        "exposed": atsOps is not None,
        "members": _members(atsOps) if atsOps is not None else None,
        "calls": [],
    }
    if atsOps is not None:
        out["ATSOps"]["calls"] = [
            _try("Refresh()", lambda: atsOps.Refresh()),
            _try("GetNumFiles()", lambda: atsOps.GetNumFiles()),
            _try("GetFiles() 무인자", lambda: atsOps.GetFiles()),
            _try("GetFiles(byref)", lambda: atsOps.GetFiles(pymxs.byref(None))),
            _try(
                "MAXScript 워커 경유",
                lambda: rt.execute("(local f = #(); ATSOps.GetFiles &f; f)"),
            ),
            _try(
                "IsFileMissing(없는 경로)",
                lambda: atsOps.IsFileMissing(MISSING_ROOT + "/missing_diffuse.png"),
            ),
            _try(
                "GetFileAssetType(없는 경로)",
                lambda: atsOps.GetFileAssetType(MISSING_ROOT + "/missing_diffuse.png"),
            ),
            _try(
                "GetFileStatus(없는 경로)",
                lambda: atsOps.GetFileStatus(MISSING_ROOT + "/missing_diffuse.png"),
            ),
            _try(
                "GetFileClients(byref)",
                lambda: atsOps.GetFileClients(
                    MISSING_ROOT + "/missing_diffuse.png", pymxs.byref(None)
                ),
            ),
        ]

    # --- AssetManager ---
    assetMan = getattr(rt, "AssetManager", None)
    out["AssetManager"] = {
        "exposed": assetMan is not None,
        "members": _members(assetMan) if assetMan is not None else None,
        "calls": [],
        "assets": [],
    }
    if assetMan is not None:
        numProbe = _try("GetNumAssets()", lambda: assetMan.GetNumAssets())
        out["AssetManager"]["calls"].append(numProbe)
        count = numProbe["value"] if numProbe["ok"] else 0
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        for index in range(1, min(count, 40) + 1):
            entry = {"index": index}
            userProbe = _try(
                f"GetAssetByIndex({index})", lambda i=index: assetMan.GetAssetByIndex(i)
            )
            entry["getAssetByIndex"] = {"ok": userProbe["ok"], "error": userProbe["error"]}
            assetUser = userProbe["value"]
            if assetUser is not None:
                entry["members"] = _members(assetUser) if index == 1 else None
                for label, getter in (
                    ("GetFileName", lambda a=assetUser: str(a.GetFileName())),
                    ("GetFullFilePath", lambda a=assetUser: str(a.GetFullFilePath())),
                    ("GetType", lambda a=assetUser: str(a.GetType())),
                ):
                    probe = _try(label, getter)
                    entry[label] = probe["value"] if probe["ok"] else f"ERR: {probe['error']}"
            out["AssetManager"]["assets"].append(entry)

    # --- objXRefMgr ---
    xrefMgr = getattr(rt, "objXRefMgr", None)
    out["objXRefMgr"] = {
        "exposed": xrefMgr is not None,
        "members": _members(xrefMgr) if xrefMgr is not None else None,
        "calls": [],
    }
    if xrefMgr is not None:
        out["objXRefMgr"]["calls"] = [
            _try("recordCount", lambda: xrefMgr.recordCount),
            _try("UpdateAllRecords()", lambda: xrefMgr.UpdateAllRecords()),
        ]

    # --- 폴백: 클래스 인스턴스 자체 열거 (같은 실행에 동봉) ---
    out["fallback"] = _try("클래스 인스턴스 자체 열거", lambda: {
        "scan": {
            key: value
            for key, value in _scan_missing_files().items()
            if key != "assets"
        },
        "assetPaths": [item["path"] for item in _scan_missing_files()["assets"]],
    })
    return out


# ============================================================
# 섹션 B - ATS 열거 ∆ 클래스 인스턴스 열거 차집합 양방향 (P0-4)
# ============================================================


def _ats_file_set():
    """ATS/AssetManager 경로로 얻은 애셋 경로 집합을 돌려준다.

    Returns:
        dict: `{"source", "paths", "error"}`
    """
    assetMan = getattr(rt, "AssetManager", None)
    if assetMan is not None:
        probe = _try("AssetManager 전량", lambda: [
            str(assetMan.GetAssetByIndex(index).GetFileName())
            for index in range(1, int(assetMan.GetNumAssets()) + 1)
        ])
        if probe["ok"]:
            return {"source": "AssetManager", "paths": probe["value"], "error": None}
        atsError = probe["error"]
    else:
        atsError = "AssetManager 미노출"

    atsOps = getattr(rt, "ATSOps", None)
    if atsOps is not None:
        probe = _try(
            "ATSOps 워커",
            lambda: rt.execute("(local f = #(); ATSOps.GetFiles &f; f)"),
        )
        if probe["ok"] and probe["value"] is not None:
            return {
                "source": "ATSOps",
                "paths": [str(item) for item in probe["value"]],
                "error": None,
            }
        atsError = f"{atsError} / ATSOps: {probe['error']}"

    return {"source": None, "paths": [], "error": atsError}


def section_b():
    """B - 두 열거 경로의 차집합을 **양방향**으로 덤프한다 (P0-4)."""
    # 합성 씬 위에서 잰다(섹션 A가 이미 만들어 뒀다).
    atsInfo = _ats_file_set()
    classScan = _scan_missing_files()

    atsPaths = {str(item).lower().replace("\\", "/") for item in atsInfo["paths"] if item}
    classPaths = set()
    for className, info in _asset_class_instances().items():
        for instance in info["instances"]:
            probe = _probe_filename(instance, info["propName"])
            if probe["channel"] == "value" and probe["filename"]:
                classPaths.add(probe["filename"].lower().replace("\\", "/"))

    return {
        "atsSource": atsInfo["source"],
        "atsError": atsInfo["error"],
        "atsCount": len(atsPaths),
        "classCount": len(classPaths),
        "onlyInAts": sorted(atsPaths - classPaths),
        "onlyInClass": sorted(classPaths - atsPaths),
        "intersection": sorted(atsPaths & classPaths),
        "classScanChannels": classScan["byChannel"],
        "classScanMissing": [item["path"] for item in classScan["assets"]],
    }


# ============================================================
# 섹션 C - Missing 플러그인 객체 판정 축 (P0-5)
# ============================================================


def _build_missing_xref_scene():
    """참조 원본이 사라진 XRef 노드를 가진 씬을 만든다.

    원본 `.max`를 만들어 XRef로 물린 뒤 **원본을 rename**해 미해결 상태를 만든다.
    삭제가 아니라 rename이므로 되돌릴 수 있다.

    Returns:
        dict: 단계별 `_try` 결과와 최종 노드 축 덤프
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    sourcePath = TEMP_DIR / "probe_xref_src.max"
    scenePath = TEMP_DIR / "probe_xref_scene.max"
    movedPath = TEMP_DIR / "probe_xref_src.max.moved"

    out = {"steps": [], "nodes": [], "xrefRecords": []}

    _reset_scene()
    rt.Box(name="xrefSourceBox", mapcoords=True)
    out["steps"].append(_try("원본 저장", lambda: bool(rt.saveMaxFile(str(sourcePath)))))

    _reset_scene()
    added = _try(
        "xrefs.addNewXRefObject",
        lambda: rt.xrefs.addNewXRefObject(str(sourcePath), "xrefSourceBox"),
    )
    out["steps"].append({"label": added["label"], "ok": added["ok"], "error": added["error"]})
    if not added["ok"]:
        out["steps"].append(
            _try(
                "objXRefMgr.AddXRefItemsFromFile",
                lambda: rt.objXRefMgr.AddXRefItemsFromFile(str(sourcePath)),
            )
        )

    out["steps"].append(_try("XRef 씬 저장", lambda: bool(rt.saveMaxFile(str(scenePath)))))

    _reset_scene()
    # 원본을 옮겨 미해결 상태를 만든다(삭제가 아니라 rename).
    out["steps"].append(_try(
        "원본 rename",
        lambda: (
            movedPath.exists() and movedPath.unlink(),
            os.rename(str(sourcePath), str(movedPath)),
            True,
        )[-1],
    ))
    out["steps"].append(_try("XRef 씬 로드", lambda: bool(rt.loadMaxFile(str(scenePath)))))
    out["steps"].append(_try("setSaveRequired(False)", lambda: rt.setSaveRequired(False)))

    out["nodes"] = [_node_axes(node) for node in rt.objects]

    xrefMgr = getattr(rt, "objXRefMgr", None)
    if xrefMgr is not None:
        countProbe = _try("recordCount", lambda: int(xrefMgr.recordCount))
        out["recordCount"] = countProbe["value"] if countProbe["ok"] else countProbe["error"]
        if countProbe["ok"]:
            for index in range(1, (countProbe["value"] or 0) + 1):
                recordProbe = _try(f"GetRecord({index})", lambda i=index: xrefMgr.GetRecord(i))
                record = recordProbe["value"]
                entry = {"index": index, "ok": recordProbe["ok"], "error": recordProbe["error"]}
                if record is not None:
                    entry["members"] = _members(record) if index == 1 else None
                    for label, getter in (
                        ("srcFileName", lambda r=record: str(r.srcFileName)),
                        ("unresolved", lambda r=record: bool(r.unresolved)),
                        ("empty", lambda r=record: bool(r.empty)),
                    ):
                        probe = _try(label, getter)
                        entry[label] = probe["value"] if probe["ok"] else f"ERR: {probe['error']}"
                out["xrefRecords"].append(entry)
    return out


def section_c():
    """C - Missing 플러그인 객체 판정 축 3종을 노드별로 함께 덤프한다 (P0-5)."""
    out = {}

    # Missing 계열 클래스가 rt에 노출되는지.
    out["classProbe"] = [
        _try(f"rt.{name}", lambda n=name: str(rt.execute(n)))
        for name in (
            "Missing_GeomObject",
            "Missing_Helper",
            "Missing_Light",
            "Missing_Camera",
            "Missing_Shape",
            "Missing_Modifier",
            "Missing_Material",
            "Missing_Texmap",
        )
    ]

    # 합성 씬에는 Missing 플러그인 객체를 만들 수 없다 - XRef 미해결로 대체 관측하고,
    # 진짜 Missing 객체는 섹션 H의 프로덕션 씬에서 센다.
    out["syntheticNote"] = (
        "Missing 플러그인 객체는 합성으로 만들 수 없다(플러그인 DLL 부재가 전제). "
        "XRef 미해결로 대체 관측하고 실태는 섹션 H가 센다."
    )
    out["xrefScene"] = _build_missing_xref_scene()
    out["missingPluginCandidates"] = _scan_missing_plugins()
    return out


# ============================================================
# 섹션 D - 애셋 → 의존 노드 역추적 호출 형태 (P0-6)
# ============================================================

#: 섹션 D가 확정한 역추적 호출 형태. G/H가 그대로 쓴다.
_DEPENDENT_FORM = None


def _dependent_forms(inAsset):
    """`refs.dependentNodes` 키워드 인자 조합을 전부 시도한다.

    Args:
        inAsset: 역추적 기점이 될 애셋 객체

    Returns:
        list[dict]: 조합별 결과
    """
    forms = (
        ("무인자", lambda: rt.refs.dependentNodes(inAsset)),
        ("firstOnly=False", lambda: rt.refs.dependentNodes(inAsset, firstOnly=False)),
        (
            "firstOnly=False, baseObjectOnly=False",
            lambda: rt.refs.dependentNodes(inAsset, firstOnly=False, baseObjectOnly=False),
        ),
        (
            "firstOnly=False, immediateOnly=False",
            lambda: rt.refs.dependentNodes(inAsset, firstOnly=False, immediateOnly=False),
        ),
        (
            "firstOnly=False, baseObjectOnly=False, immediateOnly=False",
            lambda: rt.refs.dependentNodes(
                inAsset, firstOnly=False, baseObjectOnly=False, immediateOnly=False
            ),
        ),
        ("refs.dependents", lambda: rt.refs.dependents(inAsset)),
    )

    results = []
    for label, getter in forms:
        probe = _try(label, getter)
        entry = {"label": label, "ok": probe["ok"], "error": probe["error"]}
        if probe["ok"]:
            value = probe["value"]
            try:
                names = [str(item.name) for item in value]
            except Exception:
                names = [str(value)]
            entry["count"] = len(names)
            entry["names"] = names[:20]
        results.append(entry)
    return results


def _best_dependent_nodes(inAsset):
    """가장 넓게 잡는 역추적 형태로 의존 노드를 돌려준다.

    섹션 D가 확정한 형태를 쓰고, 실패하면 다음 형태로 내려간다.

    Args:
        inAsset: 애셋 객체

    Returns:
        list: 의존 노드 목록. 전부 실패하면 빈 목록
    """
    attempts = (
        lambda: rt.refs.dependentNodes(inAsset, firstOnly=False, baseObjectOnly=False),
        lambda: rt.refs.dependentNodes(inAsset, firstOnly=False),
        lambda: rt.refs.dependentNodes(inAsset),
    )
    for attempt in attempts:
        try:
            return list(attempt())
        except Exception:
            continue
    return []


def section_d():
    """D - 역추적 호출 형태를 `_try`로 전부 비교한다 (P0-6)."""
    # 합성 씬을 다시 세워 기점을 확보한다(섹션 C가 씬을 XRef 씬으로 바꿨다).
    scene = _build_synthetic_scene()

    out = {"sceneAssertions": scene["assertions"], "byAsset": []}
    for texture in rt.getClassInstances(rt.BitmapTexture):
        fileProbe = _probe_filename(texture, "filename")
        out["byAsset"].append({
            "className": _mxs_name(texture),
            "filename": fileProbe["filename"],
            "forms": _dependent_forms(texture),
        })

    # 머티리얼을 기점으로도 재본다(비트맵 -> 머티리얼 -> 노드 2단 경유 여부).
    materials = _try("getClassInstances(StandardMaterial)", lambda: list(
        rt.getClassInstances(rt.StandardMaterial)
    ))
    out["byMaterial"] = []
    for material in materials["value"] or []:
        out["byMaterial"].append({
            "className": _mxs_name(material),
            "forms": _dependent_forms(material),
        })
    return out


# ============================================================
# 섹션 E - 지오메트리 판별 축 분포표 (P0-7)
# ============================================================


def section_e():
    """E - 노드 종류별 판정 축 **분포표**를 낸다 (P0-7).

    통과·실패 이진이 아니라 분포로 낸다 - "요구는 충족하지만 절반만 좋다"가
    사라지지 않게.
    """
    out = {"synthetic": [], "xref": [], "distribution": {}}

    _build_synthetic_scene()
    out["synthetic"] = [_node_axes(node) for node in rt.objects]

    xrefScene = _build_missing_xref_scene()
    out["xref"] = xrefScene["nodes"]

    distribution = Counter()
    for axes in out["synthetic"] + out["xref"]:
        key = (
            f"{axes.get('superClassOfNode')} | "
            f"{axes.get('classOfNode')} | "
            f"isGeometry={axes.get('isGeometry')}"
        )
        distribution[key] += 1
    out["distribution"] = dict(sorted(distribution.items()))
    out["geometryClassName"] = _try("GeometryClass", lambda: str(rt.GeometryClass))
    return out


# ============================================================
# 섹션 F - 삭제·undo·멱등 (P0-8)
# ============================================================


def section_f():
    """F - `pymxs.undo(True)` 안의 `rt.delete` 반환·예외 형태와 멱등성 (P0-8)."""
    out = {}

    scene = _build_synthetic_scene()
    out["sceneAssertions"] = scene["assertions"]

    beforeScan = _scan_missing_files()
    beforeNodes = []
    for asset in beforeScan["assets"]:
        for node in _best_dependent_nodes(asset["object"]):
            beforeNodes.append(_node_axes(node))
    out["beforeAssetCount"] = len(beforeScan["assets"])
    out["beforeDependentNodes"] = beforeNodes

    deleteTargets = [axes for axes in beforeNodes if axes.get("isGeometry") is False]
    keepTargets = [axes for axes in beforeNodes if axes.get("isGeometry") is not False]
    out["deleteTargetNames"] = [axes["name"] for axes in deleteTargets]
    out["keepTargetNames"] = [axes["name"] for axes in keepTargets]

    # 삭제 - undo 컨텍스트 안에서. 반환값을 확인해 실패를 기록한다.
    deleteResults = []
    try:
        with pymxs.undo(True):
            for axes in deleteTargets:
                node = rt.getNodeByName(axes["name"])
                if node is None:
                    deleteResults.append({"name": axes["name"], "returned": None, "error": "노드 없음"})
                    continue
                probe = _try(f"delete({axes['name']})", lambda n=node: rt.delete(n))
                deleteResults.append({
                    "name": axes["name"],
                    "returned": repr(probe["value"]),
                    "returnedType": type(probe["value"]).__name__,
                    "error": probe["error"],
                })
    except Exception:
        out["undoContextError"] = traceback.format_exc(limit=4)
    out["deleteResults"] = deleteResults

    out["afterNodeNames"] = [str(node.name) for node in rt.objects]
    afterScan = _scan_missing_files()
    out["afterAssetCount"] = len(afterScan["assets"])
    out["afterAssetPaths"] = [item["path"] for item in afterScan["assets"]]

    # 멱등 - 두 번째 계획이 비었는가(비지오메트리 기준).
    secondNodes = []
    for asset in afterScan["assets"]:
        for node in _best_dependent_nodes(asset["object"]):
            secondNodes.append(_node_axes(node))
    out["secondPlanDeleteTargets"] = [
        axes["name"] for axes in secondNodes if axes.get("isGeometry") is False
    ]
    out["secondPlanReportTargets"] = [
        axes["name"] for axes in secondNodes if axes.get("isGeometry") is not False
    ]

    # undo 동작 확인 - 헤드리스에서 되돌아오는가.
    out["undo"] = _try("max undo", lambda: rt.execute("max undo"))
    out["afterUndoNodeNames"] = _try("undo 후 노드", lambda: [str(node.name) for node in rt.objects])
    return out


# ============================================================
# 섹션 G/H - 프로덕션 씬 스윕 비용과 실태 (P0-9, P0-10)
# ============================================================


def _load_static_candidates():
    """정적 사전 정찰 결과에서 확정 대상 씬을 고른다.

    누락 후보가 있는 씬과 **없는 씬(대조군)**을 함께 고른다. 대조군이 없으면
    "전부 누락"이 스캐너 결함인지 실태인지 갈리지 않는다.

    Returns:
        dict: `{"withMissing": [...], "control": [...], "error": str | None}`
    """
    if not STATIC_RESULT_PATH.exists():
        return {"withMissing": [], "control": [], "error": "정적 스캔 결과 없음"}
    try:
        data = json.loads(STATIC_RESULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"withMissing": [], "control": [], "error": str(exc)}

    scenes = [item for item in data.get("scenes", []) if item.get("scannable")]
    withMissing = sorted(
        (item for item in scenes if item.get("absoluteMissing", 0) > 0),
        key=lambda item: item.get("sizeBytes", 0),
    )
    control = sorted(
        (item for item in scenes if item.get("absoluteMissing", 0) == 0),
        key=lambda item: item.get("sizeBytes", 0),
    )
    # 카테고리가 겹치지 않게 앞에서부터 고르되 작은 파일 우선(로드 비용).
    return {
        "withMissing": [item["path"] for item in withMissing[:6]],
        "control": [item["path"] for item in control[:2]],
        "error": None,
    }


def _sweep_scene(inScenePath):
    """씬 하나를 열어 스윕하고 비용·실태를 함께 잰다.

    원본은 저장하지 않는다(`setSaveRequired(False)`). 삭제는 하지 않는다.

    Args:
        inScenePath: 열 `.max` 경로

    Returns:
        dict: 로드 시간·스윕 시간과 분류 집계
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
    fileScan = _scan_missing_files()
    pluginNodes = _scan_missing_plugins()

    assetRecords = []
    deleteCount = 0
    reportCount = 0
    unknownCount = 0
    extensionCounter = Counter()
    for asset in fileScan["assets"]:
        nodes = [_node_axes(node) for node in _best_dependent_nodes(asset["object"])]
        for axes in nodes:
            if axes.get("isGeometry") is False:
                deleteCount += 1
            elif axes.get("isGeometry") is True:
                reportCount += 1
            else:
                unknownCount += 1
        extension = os.path.splitext(asset["path"] or "")[1].lower()
        extensionCounter[extension or "<없음>"] += 1
        assetRecords.append({
            "kind": asset["kind"],
            "className": asset["className"],
            "path": asset["path"],
            "why": asset["why"],
            "nodeCount": len(nodes),
            "nodeNames": [axes["name"] for axes in nodes][:10],
            "geometryFlags": [axes.get("isGeometry") for axes in nodes][:10],
        })

    record["sweepSeconds"] = round(time.time() - sweepStart, 2)
    record["ok"] = True
    record["missingFileCount"] = len(fileScan["assets"])
    record["missingPluginNodeCount"] = len(pluginNodes)
    record["missingPluginSamples"] = pluginNodes[:10]
    record["byChannel"] = fileScan["byChannel"]
    record["byExtension"] = dict(sorted(extensionCounter.items()))
    record["dependentDeleteCount"] = deleteCount
    record["dependentReportCount"] = reportCount
    record["dependentUnknownCount"] = unknownCount
    record["assets"] = assetRecords[:40]
    record["assetsTruncated"] = len(assetRecords) > 40
    return record


def section_gh():
    """G+H - 스윕 비용(P0-9)과 프로덕션 실태(P0-10)를 같은 로드로 잰다.

    씬 로드가 이 프로브에서 가장 비싼 단계이므로 두 섹션을 한 로드에 합친다.
    """
    candidates = _load_static_candidates()
    out = {
        "candidateError": candidates["error"],
        "withMissing": candidates["withMissing"],
        "control": candidates["control"],
        "scenes": [],
        "skipped": [],
        "budgetSeconds": SECTION_H_BUDGET,
    }

    deadline = time.time() + SECTION_H_BUDGET
    targets = [(path, "withMissing") for path in candidates["withMissing"]]
    targets += [(path, "control") for path in candidates["control"]]

    for scenePath, group in targets:
        if time.time() > deadline:
            out["skipped"].append({"path": scenePath, "group": group, "why": "예산 초과"})
            continue
        record = _sweep_scene(scenePath)
        record["group"] = group
        out["scenes"].append(record)
        _flush()

    swept = [item for item in out["scenes"] if item["ok"]]
    out["summary"] = {
        "sceneCount": len(swept),
        "loadSecondsTotal": round(sum(item.get("loadSeconds", 0) for item in swept), 2),
        "sweepSecondsTotal": round(sum(item.get("sweepSeconds", 0) for item in swept), 2),
        "sweepShareOfLoad": None,
        "missingFileTotal": sum(item.get("missingFileCount", 0) for item in swept),
        "missingPluginNodeTotal": sum(item.get("missingPluginNodeCount", 0) for item in swept),
        "dependentDeleteTotal": sum(item.get("dependentDeleteCount", 0) for item in swept),
        "dependentReportTotal": sum(item.get("dependentReportCount", 0) for item in swept),
        "dependentUnknownTotal": sum(item.get("dependentUnknownCount", 0) for item in swept),
        "scenesWithMissing": len([
            item for item in swept if item.get("missingFileCount", 0) > 0
        ]),
    }
    loadTotal = out["summary"]["loadSecondsTotal"]
    if loadTotal > 0:
        out["summary"]["sweepShareOfLoad"] = round(
            out["summary"]["sweepSecondsTotal"] / loadTotal, 4
        )
    return out


# ============================================================
# 실행
# ============================================================

RESULT["maxVersion"] = _try("maxVersion", lambda: [int(item) for item in rt.maxVersion()])

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

SECTIONS = (
    ("A", section_a),
    ("B", section_b),
    ("C", section_c),
    ("D", section_d),
    ("E", section_e),
    ("F", section_f),
    ("GH", section_gh),
)

for sectionKey, sectionFunc in SECTIONS:
    started = time.time()
    try:
        value = sectionFunc()
        target = "H" if sectionKey == "GH" else sectionKey
        RESULT[target] = value
        if sectionKey == "GH":
            RESULT["G"] = {
                "note": "섹션 H와 같은 로드에서 쟀다 - H.summary의 load/sweep 초를 본다",
                "summary": value.get("summary"),
            }
        RESULT[target]["elapsedSeconds"] = round(time.time() - started, 2)
        reporter.assert_test(
            True,
            f"TC-{sectionKey} 섹션 완주",
            f"{round(time.time() - started, 2)}초",
        )
    except Exception:
        target = "H" if sectionKey == "GH" else sectionKey
        RESULT[target] = {"fatal": traceback.format_exc(limit=8)}
        reporter.error(f"TC-{sectionKey} 섹션 완주", traceback.format_exc(limit=4))
    _flush()

# 임시 산출물 정리 - 실패해도 결과에 영향이 없다.
_try("임시 디렉토리 정리", lambda: shutil.rmtree(str(TEMP_DIR), ignore_errors=True))

_flush()
reporter.summary()
reporter.close()
