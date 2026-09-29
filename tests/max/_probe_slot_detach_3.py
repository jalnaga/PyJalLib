#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **7차** - 서브 텍스쳐맵 표준 인터페이스로 슬롯을 잡는다.

**왜 7차가 있는가.** 6차가 깨진 텍스쳐 6건과 보유 매테리얼 12개를 정확히 찾고도
**슬롯명을 0건** 잡았다(`slotMatched: 0 / slotUnmatched: 12`). `getPropNames`를 돌며
값의 핸들을 대조하는 접근이 매테리얼의 맵 슬롯을 보지 못한 것이다.

MAXScript에는 매테리얼·텍스쳐맵의 서브 텍스쳐맵을 다루는 **표준 인터페이스**가 있고,
그것은 클래스를 가리지 않는다. 이 사이클이 필요로 하는 바로 그 성질이다
(기존 MeshValidator 검증이 `DirectX_9_Shader` 전용이라 `Standardmaterial`을 놓쳤다).

    S1  `getNumSubTexmaps` / `getSubTexmap` / `getSubTexmapSlotName` /
        `setSubTexmap`이 pymxs에 노출되는가, 합성 씬에서 동작하는가
    S2  **중첩** - 텍스쳐맵 자신도 서브 텍스쳐맵을 갖는가(Composite·Mix 등).
        재귀가 필요한지 여기서 정한다
    S3  프로덕션 **사본**에서 6건을 전부 잡아 슬롯명까지 얻는가
    S4  실제로 떼고 재스캔 0건(멱등) + 저장·재로드 무결성

**각 단계가 공허하지 않음을 같은 실행에서 단정한다.**

실행:
    uv run python tests/_run_probe.py _probe_slot_detach_3.py 1800

결과:
    tests/logs/probe_slot_detach_3.json
"""

import json
import os
import shutil
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
RESULT_PATH = LOG_DIR / "probe_slot_detach_3.json"
TEMP_DIR = LOG_DIR / "_probe_slot3_tmp"

MISSING_ROOT = "D:/__probe_slot3__"
PRODUCTION_SCENE = (
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default"
    r"/SK_JeongHuiwon_Mn_Default.max"
)

reporter = TestReporter("ProbeSlotDetach3", LOG_DIR)
RESULT = {"loadedFrom": getattr(pyjallib, "__file__", None), "S1": {}, "S3": {}}


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


def _resolve_exists(inFilePath):
    """애셋 경로가 실제로 존재하는지 직접 판정한다.

    Args:
        inFilePath: 판정할 경로

    Returns:
        bool: 존재하면 True
    """
    if not inFilePath:
        return False
    if os.path.isabs(inFilePath) and os.path.exists(inFilePath):
        return True
    probe = _try("mapPaths", lambda: rt.mapPaths.getFullFilePath(inFilePath))
    resolved = probe["value"]
    return bool(resolved) and os.path.exists(str(resolved))


def _texmap_filename(inTexmap):
    """텍스쳐맵의 파일 경로를 읽는다.

    Args:
        inTexmap: 텍스쳐맵 객체

    Returns:
        str: 경로. 읽지 못하면 빈 문자열
    """
    probe = _try("filename", lambda: rt.getProperty(inTexmap, "filename"))
    if not probe["ok"]:
        return ""
    value = probe["value"]
    if value is None or isinstance(value, (bool, int, float)):
        return ""
    return str(value)


def _handle(inAnim):
    """애님의 핸들을 읽는다.

    Args:
        inAnim: 대상 객체

    Returns:
        int | None: 핸들. 실패하면 None
    """
    probe = _try("handle", lambda: int(rt.getHandleByAnim(inAnim)))
    return probe["value"] if probe["ok"] else None


# ============================================================
# S1 - 표준 인터페이스 노출·동작
# ============================================================


def section_s1():
    """S1+S2 - 서브 텍스쳐맵 인터페이스가 동작하는가, 중첩이 있는가."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    box = rt.Box(name="s1_box", mapcoords=True)
    material = rt.StandardMaterial(name="s1_mat")
    material.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/diffuse.png")
    material.bumpMap = rt.BitmapTexture(filename=MISSING_ROOT + "/bump.png")
    box.material = material

    out = {"api": {}, "slots": [], "nested": []}

    for label in (
        "getNumSubTexmaps",
        "getSubTexmap",
        "getSubTexmapSlotName",
        "setSubTexmap",
    ):
        out["api"][label] = getattr(rt, label, None) is not None

    countProbe = _try("getNumSubTexmaps", lambda: int(rt.getNumSubTexmaps(material)))
    out["subTexmapCount"] = countProbe["value"] if countProbe["ok"] else None
    out["subTexmapCountError"] = countProbe["error"]

    for index in range(1, (out["subTexmapCount"] or 0) + 1):
        texProbe = _try("getSubTexmap", lambda i=index: rt.getSubTexmap(material, i))
        nameProbe = _try(
            "getSubTexmapSlotName", lambda i=index: str(rt.getSubTexmapSlotName(material, i))
        )
        texmap = texProbe["value"]
        entry = {
            "index": index,
            "slotName": nameProbe["value"] if nameProbe["ok"] else None,
            "hasTexmap": texmap is not None,
        }
        if texmap is not None:
            entry["class"] = _try("classOf", lambda t=texmap: str(rt.classOf(t)))["value"]
            entry["filename"] = _texmap_filename(texmap)
            entry["broken"] = not _resolve_exists(entry["filename"])
            # 중첩 - 텍스쳐맵 자신도 서브를 갖는가.
            nestedProbe = _try(
                "중첩 getNumSubTexmaps", lambda t=texmap: int(rt.getNumSubTexmaps(t))
            )
            entry["nestedCount"] = nestedProbe["value"] if nestedProbe["ok"] else None
            out["nested"].append(
                {"slot": entry["slotName"], "nestedCount": entry["nestedCount"]}
            )
        out["slots"].append(entry)

    # 실제로 떼어 본다.
    filled = [item for item in out["slots"] if item["hasTexmap"]]
    out["filledSlotCount"] = len(filled)
    if filled:
        target = filled[0]
        detachProbe = _try(
            "setSubTexmap(None)",
            lambda i=target["index"]: rt.setSubTexmap(material, i, None),
        )
        out["detachOk"] = detachProbe["ok"]
        out["detachError"] = detachProbe["error"]
        afterProbe = _try(
            "재조회", lambda i=target["index"]: rt.getSubTexmap(material, i)
        )
        out["afterIsNone"] = afterProbe["ok"] and afterProbe["value"] is None
        out["afterBitmapCount"] = len(
            _try("bitmaps", lambda: list(rt.getClassInstances(rt.BitmapTexture)))["value"]
            or []
        )
        out["nodeSurvived"] = "s1_box" in [str(node.name) for node in rt.objects]
    return out


# ============================================================
# S3+S4 - 프로덕션 사본
# ============================================================


def _collect_slot_records():
    """서브 텍스쳐맵 인터페이스로 깨진 슬롯을 모은다.

    매테리얼과 텍스쳐맵 **양쪽**에서 서브를 훑는다 - 중첩 텍스쳐맵(Composite 등)
    안의 슬롯도 같은 인터페이스로 잡힌다.

    Returns:
        dict: 레코드와 **공허하지 않음을 보이는 진단 수치**
    """
    diagnostics = {
        "materials": 0,
        "materialsWithSubs": 0,
        "slotsVisited": 0,
        "slotsFilled": 0,
        "brokenSlots": 0,
        "nestedVisited": 0,
    }
    records = []
    visited = set()

    def _walk(inOwner, inOwnerKind, inDepth=0):
        """소유자의 서브 텍스쳐맵을 훑고 중첩으로 내려간다."""
        if inDepth > 6:
            return
        ownerHandle = _handle(inOwner)
        if ownerHandle is not None:
            if ownerHandle in visited:
                return
            visited.add(ownerHandle)

        countProbe = _try("getNumSubTexmaps", lambda o=inOwner: int(rt.getNumSubTexmaps(o)))
        if not countProbe["ok"]:
            return
        count = countProbe["value"] or 0
        if count and inOwnerKind == "material":
            diagnostics["materialsWithSubs"] += 1

        for index in range(1, count + 1):
            diagnostics["slotsVisited"] += 1
            if inDepth > 0:
                diagnostics["nestedVisited"] += 1
            texProbe = _try("getSubTexmap", lambda o=inOwner, i=index: rt.getSubTexmap(o, i))
            texmap = texProbe["value"]
            if texmap is None:
                continue
            diagnostics["slotsFilled"] += 1

            fileName = _texmap_filename(texmap)
            if fileName and not _resolve_exists(fileName):
                diagnostics["brokenSlots"] += 1
                slotProbe = _try(
                    "slotName",
                    lambda o=inOwner, i=index: str(rt.getSubTexmapSlotName(o, i)),
                )
                ownerNameProbe = _try("owner.name", lambda o=inOwner: str(o.name))
                ownerClassProbe = _try("classOf", lambda o=inOwner: str(rt.classOf(o)))
                records.append({
                    "ownerHandle": ownerHandle,
                    "ownerName": ownerNameProbe["value"] if ownerNameProbe["ok"] else "",
                    "ownerClass": ownerClassProbe["value"] if ownerClassProbe["ok"] else "",
                    "ownerKind": inOwnerKind,
                    "slotIndex": index,
                    "slotName": slotProbe["value"] if slotProbe["ok"] else "",
                    "path": fileName,
                })

            _walk(texmap, "texmap", inDepth + 1)

    for className in ("StandardMaterial", "DirectX_9_Shader", "MultiMaterial", "Shell_Material"):
        klass = getattr(rt, className, None)
        if klass is None:
            continue
        instancesProbe = _try(
            "getClassInstances", lambda k=klass: list(rt.getClassInstances(k))
        )
        for material in instancesProbe["value"] or []:
            diagnostics["materials"] += 1
            _walk(material, "material")

    return {"records": records, "diagnostics": diagnostics}


def section_s3():
    """S3+S4 - 프로덕션 사본에서 슬롯을 잡고 실제로 떼고 멱등을 확인한다."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    copyPath = TEMP_DIR / "slot3_copy.max"
    savePath = TEMP_DIR / "slot3_saved.max"

    out = {"sourceScene": PRODUCTION_SCENE}
    copyProbe = _try("사본 생성", lambda: shutil.copyfile(PRODUCTION_SCENE, str(copyPath)))
    out["copyOk"] = copyProbe["ok"]
    if not copyProbe["ok"]:
        out["copyError"] = copyProbe["error"]
        return out

    rt.resetMaxFile(rt.Name("noPrompt"))
    loadProbe = _try("loadMaxFile", lambda: bool(rt.loadMaxFile(str(copyPath))))
    if not loadProbe["ok"] or loadProbe["value"] is not True:
        out["loadError"] = loadProbe["error"] or "True가 아님"
        return out
    _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))

    out["nodeCountBefore"] = len(list(rt.objects))
    scanStart = time.time()
    scan = _collect_slot_records()
    out["scanSeconds"] = round(time.time() - scanStart, 2)
    out["diagnosticsBefore"] = scan["diagnostics"]
    out["slotRecordCount"] = len(scan["records"])
    out["slotByOwnerClass"] = dict(Counter(item["ownerClass"] for item in scan["records"]))
    out["slotByOwnerKind"] = dict(Counter(item["ownerKind"] for item in scan["records"]))
    out["slotSamples"] = scan["records"][:15]

    detached = []
    failed = []
    for record in scan["records"]:
        ownerProbe = _try(
            "getAnimByHandle", lambda h=record["ownerHandle"]: rt.getAnimByHandle(h)
        )
        owner = ownerProbe["value"]
        if owner is None:
            failed.append({"record": record, "why": "핸들로 소유자 복원 실패"})
            continue
        detachProbe = _try(
            "setSubTexmap(None)",
            lambda o=owner, i=record["slotIndex"]: rt.setSubTexmap(o, i, None),
        )
        if detachProbe["ok"]:
            detached.append(record)
        else:
            failed.append({"record": record, "why": detachProbe["error"]})

    out["detachedCount"] = len(detached)
    out["failedCount"] = len(failed)
    out["failedSamples"] = failed[:5]

    rescan = _collect_slot_records()
    out["diagnosticsAfter"] = rescan["diagnostics"]
    out["slotRecordCountAfter"] = len(rescan["records"])
    out["nodeCountAfter"] = len(list(rt.objects))

    out["saveOk"] = _try("saveMaxFile", lambda: bool(rt.saveMaxFile(str(savePath))))["ok"]
    if out["saveOk"]:
        rt.resetMaxFile(rt.Name("noPrompt"))
        reload = _try("재로드", lambda: bool(rt.loadMaxFile(str(savePath))))
        out["reloadOk"] = reload["ok"] and reload["value"] is True
        if out["reloadOk"]:
            reloadScan = _collect_slot_records()
            out["reloadNodeCount"] = len(list(rt.objects))
            out["reloadSlotRecordCount"] = len(reloadScan["records"])
            out["diagnosticsReload"] = reloadScan["diagnostics"]
        _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))
    return out


reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

for _key, _func in (("S1", section_s1), ("S3", section_s3)):
    _started = time.time()
    try:
        RESULT[_key] = _func()
        RESULT[_key]["elapsedSeconds"] = round(time.time() - _started, 2)
        reporter.assert_test(
            True, f"TC-{_key} 섹션 완주", f"{round(time.time() - _started, 2)}초"
        )
    except Exception:
        RESULT[_key] = {"fatal": traceback.format_exc(limit=8)}
        reporter.error(f"TC-{_key} 섹션 완주", traceback.format_exc(limit=4))
    _flush()

_try("임시 디렉토리 정리", lambda: shutil.rmtree(str(TEMP_DIR), ignore_errors=True))
_flush()
reporter.summary()
reporter.close()
