#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 **8차** - 배포본이 프로덕션 씬 표본에서 무엇을 찾는가.

**왜 8차가 있는가.** 실기 재판정에서 "딱히 경고창이 나오지 않는다"는 보고가 나왔다.
배포 자체는 정상임을 확인했고(파일 존재·심볼 노출·진입점 배선), 코드 경로도
`_on_validation_clicked`가 맨 앞에서 `run_missing_asset_step()`을 부른다.

그렇다면 남은 가설은 **그 씬에 조치할 것이 없었다**는 것이다. 이 프로브가 그 가설을
수치로 확인한다 - 프로덕션 씬 표본에서 조치 가능한 건이 있는 씬이 몇 개인지 센다.

**배포본을 그대로 쓴다.** 워크스페이스 경로를 넣지 않는다 - Max가 기동 시 올려 둔
배포본 `pyjallib`이 곧 마스터가 툴에서 만나는 그 코드다. `sys.path`를 건드리면
무엇을 측정했는지 말할 수 없게 된다.

**씬은 읽기 전용으로만 연다.** 아무것도 바꾸지 않고, 로드 직후
`setSaveRequired(False)`로 저장 요구를 끈다 - 프로덕션 원본을 건드리지 않기 위함이다.

실행:
    uv run python tests/_run_probe.py _probe_scene_survey.py 3600

결과:
    tests/logs/probe_scene_survey.json
"""

import json
import time
import traceback
from pathlib import Path

from pymxs import runtime as rt  # noqa: E402

import pyjallib  # noqa: E402
from pyjallib.max.missingAssetResolver import MissingAsset  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402

#: 배포처 pyjallib 루트. 로드 출처가 여기가 아니면 측정이 무의미하다.
DEPLOY_PYJALLIB = Path(
    r"E:/DevStorage_root/DevStorage/ExtPythonPackage/.venv/Lib/site-packages/pyjallib"
)

#: 표본을 뽑을 캐릭터 루트.
CHARACTER_ROOT = Path(r"E:/DevStorage_root/DevStorage/Characters/Main")

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = LOG_DIR / "probe_scene_survey.json"

reporter = TestReporter("ProbeSceneSurvey", LOG_DIR)

RESULT = {
    "loadedFrom": getattr(pyjallib, "__file__", None),
    "deployed": None,
    "scenes": [],
    "totals": {},
}


def _flush():
    """지금까지의 결과를 JSON으로 덮어쓴다."""
    RESULT_PATH.write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _collect_scenes():
    """표본으로 쓸 씬 경로 목록을 만든다.

    Returns:
        list[Path]: 씬 경로 목록
    """
    scenes = []
    for path in sorted(CHARACTER_ROOT.glob("*/MeshB/*/*.max")):
        # BaseSkeleton은 메쉬가 없는 스켈레톤 전용 씬이라 매테리얼 표본이 아니다.
        if "BaseSkeleton" in path.parts:
            continue
        scenes.append(path)
    return scenes


def _scan_current_scene():
    """현재 열린 씬을 검사해 계획 수치를 돌려준다.

    Returns:
        dict: 슬롯·삭제·보고 수치와 표본 라벨
    """
    started = time.time()
    plan = MissingAsset().build_purge_plan()

    detachSlots = plan.get("detachSlots") or []
    deleteNodes = plan.get("deleteNodes") or []
    reportNodes = plan.get("reportNodes") or []

    return {
        "slotCount": len(detachSlots),
        "deleteCount": len(deleteNodes),
        "reportCount": len(reportNodes),
        "actionable": len(detachSlots) + len(deleteNodes),
        "slotLabels": [
            f"{slot.get('ownerName')}.{slot.get('displayName')}"
            for slot in detachSlots[:20]
        ],
        "deleteNames": [str(node.get("name")) for node in deleteNodes[:20]],
        "reportNames": [str(node.get("name")) for node in reportNodes[:20]],
        "elapsed": round(time.time() - started, 3),
    }


# ============================================================
# S0: 로드 출처가 배포본인가
# ============================================================
try:
    loaded = Path(str(pyjallib.__file__)).resolve().parent
    isDeployed = loaded == DEPLOY_PYJALLIB.resolve()
    RESULT["deployed"] = isDeployed
    reporter.assert_test(
        isDeployed,
        "S0 배포본 pyjallib이 로드됐다",
        f"loaded={loaded}, expected={DEPLOY_PYJALLIB}",
    )
except Exception:
    reporter.error("S0 배포본 pyjallib이 로드됐다", traceback.format_exc(limit=4))

_flush()


# ============================================================
# S1: 표본 씬을 하나씩 열어 검사한다
# ============================================================
scenes = _collect_scenes()
RESULT["totals"]["sceneCandidates"] = len(scenes)
_flush()

for scenePath in scenes:
    record = {"scene": str(scenePath), "ok": False}
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        loadedOk = rt.loadMaxFile(str(scenePath), quiet=True)
        # 아무것도 바꾸지 않았음을 Max에게도 알린다 - 프로덕션 원본 보호.
        rt.setSaveRequired(False)

        if not loadedOk:
            record["error"] = "loadMaxFile가 False를 돌려줬다"
        else:
            record.update(_scan_current_scene())
            record["nodeCount"] = len(list(rt.objects))
            record["ok"] = True
    except Exception:
        record["error"] = traceback.format_exc(limit=4)

    RESULT["scenes"].append(record)
    _flush()

rt.resetMaxFile(rt.Name("noPrompt"))
rt.setSaveRequired(False)


# ============================================================
# S2: 집계 - 조치 가능한 씬이 몇 개인가
# ============================================================
try:
    scanned = [item for item in RESULT["scenes"] if item.get("ok")]
    actionable = [item for item in scanned if item.get("actionable", 0) > 0]
    withReport = [item for item in scanned if item.get("reportCount", 0) > 0]

    RESULT["totals"].update(
        {
            "scanned": len(scanned),
            "failed": len(RESULT["scenes"]) - len(scanned),
            "actionableScenes": len(actionable),
            "reportOnlyScenes": len(withReport) - len(
                [item for item in withReport if item.get("actionable", 0) > 0]
            ),
            "actionableSceneNames": [
                Path(item["scene"]).name for item in actionable
            ],
            "totalSlots": sum(item.get("slotCount", 0) for item in scanned),
            "totalDeletes": sum(item.get("deleteCount", 0) for item in scanned),
        }
    )
    _flush()

    # **공허하지 않음을 단정한다** - 씬을 하나도 못 열었으면 "0건"은 의미가 없다.
    reporter.assert_test(
        len(scanned) > 0,
        "S2 표본 씬을 실제로 열어 검사했다",
        f"scanned={len(scanned)}, failed={RESULT['totals']['failed']}",
    )
    reporter.assert_test(
        True,
        "S2 집계 완료",
        f"totals={RESULT['totals']}",
    )
except Exception:
    reporter.error("S2 집계", traceback.format_exc(limit=4))

_flush()
reporter.summary()
reporter.close()
