#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **5차** - 깨진 텍스쳐맵을 슬롯에서 뗄 수 있는가 (Phase 7-0).

실기 판정이 "정리 대상은 노드가 아니라 매테리얼 슬롯"으로 축을 옮겼다(PRD §4-B).
그 축이 **실제로 동작하는지**를 코드화 전에 실측한다 - 실패 형태를 추측해 넣지 않는다.

섹션:
    A  `Standardmaterial`의 맵 슬롯을 떼는 pymxs 형태 (후보를 `_try`로 전부 비교)
    B  뗀 뒤 `getClassInstances(BitmapTexture)`·`AssetManager`에서 사라지는가 (멱등)
    C  `Multi/Sub-Object` 서브 매테리얼 안의 슬롯도 뗄 수 있는가
    D  `DirectX_9_Shader`의 텍스쳐 **파라미터**를 떼는 형태 - Standard와 다를 수 있다
    E  **프로덕션 씬 임시 사본**에서 실제로 떼어내고 멱등·저장 무결성 확인

**프로덕션 원본은 절대 건드리지 않는다.** `shutil.copyfile` 사본에서만 뗀다.

실행:
    uv run python tests/_run_probe.py _probe_slot_detach.py 1800

결과:
    tests/logs/probe_slot_detach.json
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
RESULT_PATH = LOG_DIR / "probe_slot_detach.json"
TEMP_DIR = LOG_DIR / "_probe_slot_tmp"

MISSING_ROOT = "D:/__probe_slot_detach__"

#: 4차 프로브에서 깨진 텍스쳐맵 6건이 확인된 씬. 사본으로만 연다.
PRODUCTION_SCENE = (
    r"E:/DevStorage_root/DevStorage/Characters/Main/JeongHuiwon/MeshB/Default"
    r"/SK_JeongHuiwon_Mn_Default.max"
)

reporter = TestReporter("ProbeSlotDetach", LOG_DIR)

RESULT = {
    "loadedFrom": getattr(pyjallib, "__file__", None),
    "A": {},
    "B": {},
    "C": {},
    "D": {},
    "E": {},
}


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


def _bitmap_count():
    """씬의 `BitmapTexture` 인스턴스 수를 센다.

    Returns:
        int: 인스턴스 수. 조회 실패 시 -1
    """
    probe = _try("getClassInstances", lambda: list(rt.getClassInstances(rt.BitmapTexture)))
    return len(probe["value"]) if probe["ok"] else -1


def _missing_asset_names():
    """`AssetManager`로 해석 실패한 애셋 이름 집합을 돌려준다.

    Returns:
        set[str]: 정규화된 경로 집합
    """
    assetMan = getattr(rt, "AssetManager", None)
    if assetMan is None:
        return set()
    countProbe = _try("GetNumAssets", lambda: int(assetMan.GetNumAssets()))
    if not countProbe["ok"]:
        return set()

    missing = set()
    for index in range(1, (countProbe["value"] or 0) + 1):
        userProbe = _try("GetAssetByIndex", lambda i=index: assetMan.GetAssetByIndex(i))
        assetUser = userProbe["value"]
        if assetUser is None:
            continue
        fullProbe = _try("GetFullFilePath", lambda a=assetUser: str(a.GetFullFilePath()))
        if fullProbe["ok"] and fullProbe["value"]:
            continue
        nameProbe = _try("GetFileName", lambda a=assetUser: str(a.GetFileName()))
        if nameProbe["ok"]:
            missing.add(_norm(nameProbe["value"]))
    return missing


def _build_standard_scene():
    """Standard 매테리얼에 깨진 맵 2개를 물린 씬을 만든다.

    Returns:
        dict: 사전 어서션 값
    """
    rt.resetMaxFile(rt.Name("noPrompt"))
    box = rt.Box(name="slot_box", mapcoords=True)
    material = rt.StandardMaterial(name="slot_mat")
    material.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/diffuse.png")
    material.bumpMap = rt.BitmapTexture(filename=MISSING_ROOT + "/bump.png")
    box.material = material
    return {
        "missingRootAbsent": not os.path.exists(MISSING_ROOT),
        "bitmapCount": _bitmap_count(),
        "missingAssets": sorted(_missing_asset_names()),
    }


# ============================================================
# 섹션 A - Standard 슬롯을 떼는 형태
# ============================================================


def section_a():
    """A - 맵 슬롯을 떼는 pymxs 형태를 후보별로 비교한다."""
    out = {"before": _build_standard_scene(), "attempts": []}

    # 후보를 하나씩 **독립된 씬**에서 시도한다 - 앞 시도가 성공하면 뒤 시도의
    # 전제가 사라져 무엇이 통했는지 말할 수 없게 된다.
    candidates = (
        (
            "setattr None",
            lambda m: setattr(m, "diffuseMap", None),
        ),
        (
            "rt.setProperty(mat, 'diffuseMap', None)",
            lambda m: rt.setProperty(m, "diffuseMap", None),
        ),
        (
            "rt.setProperty(mat, 'diffuseMap', rt.undefined)",
            lambda m: rt.setProperty(m, "diffuseMap", rt.undefined),
        ),
        (
            "MAXScript 워커 (meditMaterials 경유 불가 - execute로 직접)",
            lambda m: rt.execute(
                "(local ms = (getClassInstances StandardMaterial); "
                "if ms.count > 0 do ms[1].diffuseMap = undefined; true)"
            ),
        ),
    )

    for label, action in candidates:
        _build_standard_scene()
        materialProbe = _try(
            "매테리얼 조회", lambda: list(rt.getClassInstances(rt.StandardMaterial))[0]
        )
        if not materialProbe["ok"]:
            out["attempts"].append({"label": label, "ok": False, "error": "매테리얼 조회 실패"})
            continue
        material = materialProbe["value"]

        actionProbe = _try(label, lambda m=material, a=action: a(m))
        afterProbe = _try(
            "diffuseMap 재조회", lambda m=material: rt.getProperty(m, "diffuseMap")
        )
        out["attempts"].append({
            "label": label,
            "ok": actionProbe["ok"],
            "error": actionProbe["error"],
            "diffuseMapAfter": repr(afterProbe["value"]) if afterProbe["ok"] else None,
            "diffuseMapIsNone": afterProbe["ok"] and afterProbe["value"] is None,
            "bitmapCountAfter": _bitmap_count(),
            "missingAfter": sorted(_missing_asset_names()),
        })

    # `rt.undefined` 자체가 노출되는지도 남긴다.
    out["hasRtUndefined"] = _try("rt.undefined", lambda: repr(rt.undefined))
    return out


# ============================================================
# 섹션 B - 뗀 뒤 멱등
# ============================================================


def section_b():
    """B - 슬롯을 뗀 뒤 텍스쳐와 누락 애셋이 실제로 사라지는가."""
    before = _build_standard_scene()
    material = list(rt.getClassInstances(rt.StandardMaterial))[0]

    detach = _try("diffuseMap 분리", lambda: rt.setProperty(material, "diffuseMap", None))
    afterOne = {
        "bitmapCount": _bitmap_count(),
        "missingAssets": sorted(_missing_asset_names()),
    }

    detachBump = _try("bumpMap 분리", lambda: rt.setProperty(material, "bumpMap", None))
    afterBoth = {
        "bitmapCount": _bitmap_count(),
        "missingAssets": sorted(_missing_asset_names()),
    }

    # ATS 갱신이 필요한지 - 애셋 테이블이 캐시라면 Refresh 후 달라진다.
    refresh = _try("ATSOps.Refresh", lambda: rt.ATSOps.Refresh())
    afterRefresh = {
        "bitmapCount": _bitmap_count(),
        "missingAssets": sorted(_missing_asset_names()),
    }

    # 두 번 떼도 무해한가.
    detachAgain = _try(
        "diffuseMap 재분리", lambda: rt.setProperty(material, "diffuseMap", None)
    )

    return {
        "before": before,
        "detachOk": detach["ok"],
        "detachError": detach["error"],
        "afterOne": afterOne,
        "detachBumpOk": detachBump["ok"],
        "afterBoth": afterBoth,
        "refreshOk": refresh["ok"],
        "afterRefresh": afterRefresh,
        "detachAgainOk": detachAgain["ok"],
        "detachAgainError": detachAgain["error"],
        "nodeSurvived": "slot_box" in [str(node.name) for node in rt.objects],
    }


# ============================================================
# 섹션 C - Multi/Sub-Object 서브 매테리얼
# ============================================================


def section_c():
    """C - 서브 매테리얼 안의 슬롯도 뗄 수 있는가."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    box = rt.Box(name="multi_box", mapcoords=True)

    multiProbe = _try("MultiMaterial 생성", lambda: rt.MultiMaterial(numsubs=2))
    if not multiProbe["ok"]:
        return {"fatal": "MultiMaterial 생성 실패", "error": multiProbe["error"]}
    multi = multiProbe["value"]

    subMaterial = rt.StandardMaterial(name="multi_sub")
    subMaterial.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/sub.png")
    setSub = _try("setSubMtl", lambda: rt.setSubMtl(multi, 1, subMaterial))
    box.material = multi

    before = {
        "bitmapCount": _bitmap_count(),
        "missingAssets": sorted(_missing_asset_names()),
        "numSubMtls": _try("getNumSubMtls", lambda: int(rt.getNumSubMtls(multi)))["value"],
    }

    # 서브를 다시 꺼내 슬롯을 뗀다 - 계획이 핸들로 매테리얼을 복원하므로
    # 꺼내는 경로가 실제로 같은 객체를 주는지도 함께 본다.
    fetched = _try("getSubMtl(1)", lambda: rt.getSubMtl(multi, 1))
    sameObject = _try(
        "핸들 동일",
        lambda: int(rt.getHandleByAnim(fetched["value"]))
        == int(rt.getHandleByAnim(subMaterial)),
    )
    detach = _try(
        "서브 diffuseMap 분리",
        lambda: rt.setProperty(fetched["value"], "diffuseMap", None),
    )

    return {
        "setSubOk": setSub["ok"],
        "before": before,
        "fetchedOk": fetched["ok"],
        "sameObject": sameObject["value"],
        "detachOk": detach["ok"],
        "detachError": detach["error"],
        "afterBitmapCount": _bitmap_count(),
        "afterMissing": sorted(_missing_asset_names()),
        "nodeSurvived": "multi_box" in [str(node.name) for node in rt.objects],
    }


# ============================================================
# 섹션 D + E - 프로덕션 사본에서 DX9 포함 실측
# ============================================================


def _material_slot_records():
    """씬에서 깨진 텍스쳐맵을 물고 있는 (매테리얼, 슬롯) 쌍을 모은다.

    매테리얼 클래스를 가리지 않는다 - Standard와 DX9 둘 다 본다. 기존
    MeshValidator 검증이 DX9 전용이었던 것이 실기 미검출의 원인이었다.

    Returns:
        list[dict]: 슬롯 레코드
    """
    missing = _missing_asset_names()
    records = []

    materialsProbe = _try(
        "getClassInstances(material)", lambda: list(rt.getClassInstances(rt.material))
    )
    for material in materialsProbe["value"] or []:
        namesProbe = _try(
            "getPropNames", lambda m=material: [str(n) for n in rt.getPropNames(m)]
        )
        classProbe = _try("classOf", lambda m=material: str(rt.classOf(m)))
        for propName in namesProbe["value"] or []:
            valueProbe = _try(
                "getProperty", lambda m=material, n=propName: rt.getProperty(m, n)
            )
            if not valueProbe["ok"]:
                continue
            value = valueProbe["value"]
            if value is None or isinstance(value, (bool, int, float, str)):
                continue
            fileProbe = _try(
                "filename", lambda v=value: rt.getProperty(v, "filename")
            )
            if not fileProbe["ok"] or not fileProbe["value"]:
                continue
            key = _norm(str(fileProbe["value"]))
            if key not in missing:
                continue
            nameProbe = _try("material.name", lambda m=material: str(m.name))
            records.append({
                "materialName": nameProbe["value"] if nameProbe["ok"] else "",
                "materialClass": classProbe["value"] if classProbe["ok"] else "",
                "slotName": propName,
                "path": str(fileProbe["value"]),
            })
    return records


def section_de():
    """D+E - 프로덕션 **사본**에서 슬롯 레코드를 모으고 실제로 떼어낸다."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    copyPath = TEMP_DIR / "probe_slot_copy.max"

    out = {"sourceScene": PRODUCTION_SCENE, "copyPath": str(copyPath)}

    copyProbe = _try(
        "사본 생성", lambda: shutil.copyfile(PRODUCTION_SCENE, str(copyPath))
    )
    out["copyOk"] = copyProbe["ok"]
    if not copyProbe["ok"]:
        out["copyError"] = copyProbe["error"]
        return out

    rt.resetMaxFile(rt.Name("noPrompt"))
    loadStart = time.time()
    loadProbe = _try("loadMaxFile(사본)", lambda: bool(rt.loadMaxFile(str(copyPath))))
    out["loadSeconds"] = round(time.time() - loadStart, 2)
    if not loadProbe["ok"] or loadProbe["value"] is not True:
        out["loadError"] = loadProbe["error"] or "loadMaxFile이 True를 돌려주지 않음"
        return out
    _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))

    scanStart = time.time()
    records = _material_slot_records()
    out["scanSeconds"] = round(time.time() - scanStart, 2)
    out["slotRecordCount"] = len(records)
    out["slotByClass"] = dict(Counter(item["materialClass"] for item in records))
    out["slotSamples"] = records[:15]
    out["beforeMissingCount"] = len(_missing_asset_names())
    out["beforeBitmapCount"] = _bitmap_count()
    out["beforeNodeCount"] = len(list(rt.objects))

    # 실제로 떼어낸다 - 사본이므로 안전하다.
    detached = []
    failed = []
    materialsByName = {}
    for material in _try(
        "getClassInstances(material)", lambda: list(rt.getClassInstances(rt.material))
    )["value"] or []:
        nameProbe = _try("name", lambda m=material: str(m.name))
        if nameProbe["ok"]:
            materialsByName.setdefault(nameProbe["value"], []).append(material)

    for record in records:
        candidates = materialsByName.get(record["materialName"], [])
        if not candidates:
            failed.append({"record": record, "why": "매테리얼을 못 찾음"})
            continue
        probe = _try(
            "슬롯 분리",
            lambda m=candidates[0], n=record["slotName"]: rt.setProperty(m, n, None),
        )
        if probe["ok"]:
            detached.append(record)
        else:
            failed.append({"record": record, "why": probe["error"]})

    out["detachedCount"] = len(detached)
    out["failedCount"] = len(failed)
    out["failedSamples"] = failed[:5]

    _try("ATSOps.Refresh", lambda: rt.ATSOps.Refresh())
    out["afterMissingCount"] = len(_missing_asset_names())
    out["afterBitmapCount"] = _bitmap_count()
    out["afterNodeCount"] = len(list(rt.objects))
    out["afterSlotRecordCount"] = len(_material_slot_records())

    # 저장 무결성 - 사본에 저장해 보고 다시 열린다면 씬이 깨지지 않은 것이다.
    savePath = TEMP_DIR / "probe_slot_saved.max"
    out["saveOk"] = _try("saveMaxFile", lambda: bool(rt.saveMaxFile(str(savePath))))["ok"]
    if out["saveOk"]:
        rt.resetMaxFile(rt.Name("noPrompt"))
        reload = _try("재로드", lambda: bool(rt.loadMaxFile(str(savePath))))
        out["reloadOk"] = reload["ok"] and reload["value"] is True
        out["reloadNodeCount"] = len(list(rt.objects)) if out["reloadOk"] else None
        out["reloadSlotRecordCount"] = (
            len(_material_slot_records()) if out["reloadOk"] else None
        )
        _try("setSaveRequired(False)", lambda: rt.setSaveRequired(False))
    return out


# ============================================================
# 실행
# ============================================================

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)

for _key, _func in (("A", section_a), ("B", section_b), ("C", section_c), ("DE", section_de)):
    _started = time.time()
    try:
        _target = "D" if _key == "DE" else _key
        RESULT[_target] = _func()
        RESULT[_target]["elapsedSeconds"] = round(time.time() - _started, 2)
        reporter.assert_test(
            True, f"TC-{_key} 섹션 완주", f"{round(time.time() - _started, 2)}초"
        )
    except Exception:
        _target = "D" if _key == "DE" else _key
        RESULT[_target] = {"fatal": traceback.format_exc(limit=8)}
        reporter.error(f"TC-{_key} 섹션 완주", traceback.format_exc(limit=4))
    _flush()

_try("임시 디렉토리 정리", lambda: shutil.rmtree(str(TEMP_DIR), ignore_errors=True))
_flush()
reporter.summary()
reporter.close()
