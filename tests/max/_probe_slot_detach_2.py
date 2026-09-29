#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **6차** - 슬롯명 역추적을 실증한다 (Phase 7-0 계속).

**왜 6차가 있는가.** 5차 섹션 D/E가 프로덕션 씬에서 슬롯 레코드 **0건**을 보고했다.
같은 씬에서 4차는 깨진 텍스쳐맵 6건 / 매테리얼 12개를 찾았으므로 모집단이 아니라
**질문이 틀렸다** - 5차는 `getClassInstances(rt.material)`로 시작했는데 `rt.material`은
클래스가 아니라 **수퍼클래스**라 빈 결과가 나온 것으로 보인다
(`max/max_test_pattern.md` 5원칙: 프로브가 0건을 보고하면 워커보다 판정 기준을 먼저 의심한다).

5차가 확정한 것은 다시 재지 않는다. 6차는 다음만 다룬다.

    N1  `getClassInstances`에 수퍼클래스를 넘기면 무엇이 나오는가 (5차 0건의 원인 확정)
    N2  **부재 판정을 AssetManager가 아니라 직접 판정으로** 했을 때의 프로덕션 실태.
        5차 §B가 AssetManager 테이블은 정리 후에도 안 줄어드는 것을 보였으므로,
        멱등을 만들려면 축을 옮겨야 한다
    N3  텍스쳐맵 -> `refs.dependents` -> 매테리얼 -> **슬롯명** 역추적 (4차가 실증한 경로)
    N4  프로덕션 **사본**에서 그 슬롯을 실제로 떼고 재스캔 0건(멱등)·저장 무결성 확인

**각 단계가 공허하지 않음을 같은 실행에서 단정한다.** 5차가 그것을 빼서 0건을 실태로
오독할 뻔했다.

실행:
    uv run python tests/_run_probe.py _probe_slot_detach_2.py 1800

결과:
    tests/logs/probe_slot_detach_2.json
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
RESULT_PATH = LOG_DIR / "probe_slot_detach_2.json"
TEMP_DIR = LOG_DIR / "_probe_slot2_tmp"

PRODUCTION_SCENE = (
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default"
    r"/SK_JeongHuiwon_Mn_Default.max"
)

reporter = TestReporter("ProbeSlotDetach2", LOG_DIR)

RESULT = {"loadedFrom": getattr(pyjallib, "__file__", None), "N1": {}, "N2": {}}


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


def _resolve_exists(inFilePath):
    """애셋 경로가 실제로 존재하는지 **직접** 판정한다.

    `AssetManager`에 묻지 않는다 - 5차 실측에서 그 테이블은 슬롯을 뗀 뒤에도
    갱신되지 않아 멱등을 만들지 못했다.

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
# N1 - getClassInstances에 수퍼클래스를 넘기면 무엇이 나오는가
# ============================================================


def section_n1():
    """N1 - 5차가 0건을 본 원인을 확정한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    box = rt.Box(name="n1_box", mapcoords=True)
    material = rt.StandardMaterial(name="n1_mat")
    material.diffuseMap = rt.BitmapTexture(filename="D:/__n1_missing__/x.png")
    box.material = material

    out = {"fixtureBitmapCount": len(rt.getClassInstances(rt.BitmapTexture))}

    for label, getter in (
        ("getClassInstances(rt.material) - 수퍼클래스", lambda: rt.material),
        ("getClassInstances(rt.StandardMaterial) - 클래스", lambda: rt.StandardMaterial),
        ("getClassInstances(rt.BitmapTexture) - 클래스", lambda: rt.BitmapTexture),
        ("getClassInstances(rt.textureMap) - 수퍼클래스", lambda: rt.textureMap),
    ):
        klassProbe = _try(label, getter)
        if not klassProbe["ok"] or klassProbe["value"] is None:
            out[label] = {"available": False, "error": klassProbe["error"]}
            continue
        countProbe = _try(
            "count", lambda k=klassProbe["value"]: len(list(rt.getClassInstances(k)))
        )
        out[label] = {
            "available": True,
            "count": countProbe["value"] if countProbe["ok"] else None,
            "error": countProbe["error"],
        }

    # sceneMaterials로 매테리얼을 얻는 경로도 함께 본다.
    out["sceneMaterials"] = _try(
        "sceneMaterials count", lambda: len(list(rt.sceneMaterials))
    )
    return out


# ============================================================
# N2~N4 - 프로덕션 사본에서 역추적 → 분리 → 멱등
# ============================================================


def _collect_slot_records():
    """깨진 텍스쳐맵을 물고 있는 (매테리얼, 슬롯) 쌍을 모은다.

    **텍스쳐맵에서 시작해 `refs.dependents`로 매테리얼을 찾고**, 그 매테리얼의
    프로퍼티 중 그 텍스쳐맵과 **같은 객체**를 가리키는 것을 슬롯으로 잡는다.
    4차가 실증한 방향이다 - 매테리얼 쪽에서 전수로 내려가면 클래스 열거에서 막힌다.

    Returns:
        dict: 레코드와 **공허하지 않음을 보이는 진단 수치**
    """
    diagnostics = {
        "bitmapInstances": 0,
        "withFilename": 0,
        "brokenTexmaps": 0,
        "dependentMaterials": 0,
        "slotMatched": 0,
        "slotUnmatched": 0,
    }
    records = []

    instancesProbe = _try(
        "getClassInstances(BitmapTexture)",
        lambda: list(rt.getClassInstances(rt.BitmapTexture)),
    )
    instances = instancesProbe["value"] or []
    diagnostics["bitmapInstances"] = len(instances)

    for texmap in instances:
        fileName = _texmap_filename(texmap)
        if not fileName:
            continue
        diagnostics["withFilename"] += 1
        if _resolve_exists(fileName):
            continue
        diagnostics["brokenTexmaps"] += 1

        texHandle = _handle(texmap)
        dependentsProbe = _try(
            "refs.dependents", lambda t=texmap: list(rt.refs.dependents(t))
        )
        for dependent in dependentsProbe["value"] or []:
            superProbe = _try("superClassOf", lambda d=dependent: str(rt.superClassOf(d)))
            if superProbe["value"] != "material":
                continue
            diagnostics["dependentMaterials"] += 1

            classProbe = _try("classOf", lambda d=dependent: str(rt.classOf(d)))
            nameProbe = _try("name", lambda d=dependent: str(d.name))
            namesProbe = _try(
                "getPropNames", lambda d=dependent: [str(n) for n in rt.getPropNames(d)]
            )

            matchedSlot = None
            for propName in namesProbe["value"] or []:
                valueProbe = _try(
                    "getProperty", lambda d=dependent, n=propName: rt.getProperty(d, n)
                )
                if not valueProbe["ok"]:
                    continue
                value = valueProbe["value"]
                if value is None or isinstance(value, (bool, int, float, str)):
                    continue
                if _handle(value) == texHandle:
                    matchedSlot = propName
                    break

            if matchedSlot is None:
                diagnostics["slotUnmatched"] += 1
                continue
            diagnostics["slotMatched"] += 1
            records.append({
                "materialHandle": _handle(dependent),
                "materialName": nameProbe["value"] if nameProbe["ok"] else "",
                "materialClass": classProbe["value"] if classProbe["ok"] else "",
                "slotName": matchedSlot,
                "path": fileName,
                "texmapHandle": texHandle,
            })

    return {"records": records, "diagnostics": diagnostics}


def section_n2():
    """N2~N4 - 프로덕션 사본에서 역추적·분리·멱등을 한 번에 본다."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    copyPath = TEMP_DIR / "slot2_copy.max"
    savePath = TEMP_DIR / "slot2_saved.max"

    out = {"sourceScene": PRODUCTION_SCENE}
    copyProbe = _try("사본 생성", lambda: shutil.copyfile(PRODUCTION_SCENE, str(copyPath)))
    out["copyOk"] = copyProbe["ok"]
    if not copyProbe["ok"]:
        out["copyError"] = copyProbe["error"]
        return out

    rt.resetMaxFile(rt.Name("noPrompt"))
    loadStart = time.time()
    loadProbe = _try("loadMaxFile", lambda: bool(rt.loadMaxFile(str(copyPath))))
    out["loadSeconds"] = round(time.time() - loadStart, 2)
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
    out["slotByClass"] = dict(
        Counter(item["materialClass"] for item in scan["records"])
    )
    out["slotSamples"] = scan["records"][:15]

    # 실제로 뗀다 - 사본이므로 안전하다. 핸들로 매테리얼을 복원한다.
    detached = []
    failed = []
    for record in scan["records"]:
        materialProbe = _try(
            "getAnimByHandle", lambda h=record["materialHandle"]: rt.getAnimByHandle(h)
        )
        material = materialProbe["value"]
        if material is None:
            failed.append({"record": record, "why": "핸들로 매테리얼 복원 실패"})
            continue
        detachProbe = _try(
            "슬롯 분리",
            lambda m=material, n=record["slotName"]: rt.setProperty(m, n, None),
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

    # 저장 → 재로드로 씬 무결성을 확인한다.
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

for _key, _func in (("N1", section_n1), ("N2", section_n2)):
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
