#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""배포 검증 프로브 - **배포본**의 누락 애셋 기능이 실제로 동작하는가.

`processes/p4_deploy.md` §배포는 "복사했다"로 끝나지 않는다 - 프로브로 닫는다.
세 축을 단정한다.

1. **로드 출처** - `__file__`이 배포본을 가리키는가
2. **의존 완결성** - 새 코드가 배포되지 않은 모듈을 참조하지 않는가
3. **진입점 배선** - 세 툴이 그 기능을 **실제로 물고 있는가**(파일만 배포되고 안 불리는 상태 배제)

**워크스페이스 경로를 일절 넣지 않는다.** 프로덕션과 같은 조건으로 배포본을 그대로
import한다 - `sys.path`를 조작하면 무엇을 검증했는지 말할 수 없게 된다.

기대 TC 수: 12 (TC01~TC12)

실행:
    uv run python tests/_run_probe.py _probe_deploy_missing_asset.py 900
"""

import sys
import traceback
from pathlib import Path

from pymxs import runtime as rt  # noqa: E402

#: 배포처 루트. `.p4deploy.json`이 선언한 값과 같아야 한다.
DEPLOY_PYJALLIB = Path(
    r"E:/DevStorage_root/DevStorage/ExtPythonPackage/.venv/Lib/site-packages/pyjallib"
)
DEPLOY_TOOLS = Path(r"E:/DevStorage_root/DevStorage/Tools/Max/ORVTools/Tools")
DEPLOY_VALIDATOR = DEPLOY_TOOLS / "ORV_Char_Model/MeshValidator"
DEPLOY_EXPORTER = DEPLOY_TOOLS / "ORV_Char_Model/MeshNameSelector"
DEPLOY_BUILDER = DEPLOY_TOOLS / "ORV_Char_Rigging/BaseSkeletonBuilder"

MISSING_ROOT = "D:/__deploy_probe_missing_asset__"

# 배포본 pyjallib은 Max가 기동 시 이미 올려 두므로 경로 조작이 필요 없다.
# 툴 패키지는 런처가 넣는 경로를 그대로 흉내낸다 - 그 외 경로는 넣지 않는다.
for _toolRoot in (DEPLOY_VALIDATOR, DEPLOY_EXPORTER, DEPLOY_BUILDER):
    _path = str(_toolRoot)
    if _path not in sys.path:
        sys.path.append(_path)

from pyjallib.testKit import TestReporter  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
reporter = TestReporter("DeployMissingAsset", LOG_DIR)


def _under(inModule, inRoot) -> bool:
    """모듈이 지정한 루트 아래에서 로드됐는지 판정한다.

    Args:
        inModule: 검사할 모듈
        inRoot: 기대 루트 경로

    Returns:
        bool: 루트 아래면 True
    """
    moduleFile = getattr(inModule, "__file__", None)
    if not moduleFile:
        return False
    return str(Path(moduleFile).resolve()).lower().startswith(
        str(Path(inRoot).resolve()).lower()
    )


def _build_fixture():
    """누락 애셋을 물린 합성 씬을 만든다.

    Returns:
        dict: 사전 어서션 값
    """
    rt.resetMaxFile(rt.Name("noPrompt"))

    geoMissing = rt.Box(name="deploy_geo_missing", mapcoords=True)
    material = rt.StandardMaterial(name="deploy_mat")
    material.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/d.png")
    material.bumpMap = rt.BitmapTexture(filename=MISSING_ROOT + "/b.png")
    geoMissing.material = material

    light = rt.OmniLight(name="deploy_light_missing")
    light.projector = True
    light.projectorMap = rt.BitmapTexture(filename=MISSING_ROOT + "/p.png")

    rt.Box(name="deploy_geo_clean", mapcoords=True)
    return {"nodeCount": len(list(rt.objects))}


# ============================================================
# 축 1: 로드 출처
# ============================================================
try:
    import pyjallib
    from pyjallib.max import missingAssetPolicy, missingAssetResolver

    reporter.assert_test(
        _under(pyjallib, DEPLOY_PYJALLIB.parent)
        and _under(missingAssetPolicy, DEPLOY_PYJALLIB)
        and _under(missingAssetResolver, DEPLOY_PYJALLIB),
        "TC01 pyjallib 신규 모듈이 배포본에서 로드된다",
        f"pyjallib={pyjallib.__file__}, policy={missingAssetPolicy.__file__}, "
        f"resolver={missingAssetResolver.__file__}",
    )
except Exception:
    reporter.error("TC01 pyjallib 신규 모듈이 배포본에서 로드된다", traceback.format_exc(limit=4))


# ============================================================
# 축 2: 의존 완결성 - 신규 심볼이 전부 노출되는가
# ============================================================
try:
    from pyjallib.max import MissingAsset as FacadeFromPackage
    from pyjallib.max.missingAssetPolicy import (
        ASSET_KIND_FILE,
        ASSET_KIND_PLUGIN,
        REASON_GEOMETRY,
        REASON_UNKNOWN,
        build_plan_summary,
        build_purge_plan,
    )
    from pyjallib.max.missingAssetPolicy import (
        build_purge_confirm_summary,
        build_purge_detail_text,
    )
    from pyjallib.max.missingAssetResolver import (
        MissingAsset,
        collect_broken_slots,
        is_geometry_node,
    )
    from pyjallib.max.ui.scrollableConfirmDialog import show_scrollable_confirm

    symbols = {
        "패키지 재노출": FacadeFromPackage is MissingAsset,
        "build_purge_plan": callable(build_purge_plan),
        "build_plan_summary": callable(build_plan_summary),
        "build_purge_detail_text": callable(build_purge_detail_text),
        "build_purge_confirm_summary": callable(build_purge_confirm_summary),
        "collect_broken_slots": callable(collect_broken_slots),
        "show_scrollable_confirm": callable(show_scrollable_confirm),
        "is_geometry_node": callable(is_geometry_node),
        "상수 4종": {ASSET_KIND_FILE, ASSET_KIND_PLUGIN, REASON_GEOMETRY, REASON_UNKNOWN}
        == {"file", "plugin", "geometry", "unknown"},
    }
    reporter.assert_test(
        all(symbols.values()),
        "TC02 pyjallib 신규 심볼이 전부 노출된다",
        f"{symbols}",
    )
except Exception:
    reporter.error("TC02 pyjallib 신규 심볼이 전부 노출된다", traceback.format_exc(limit=4))


# ============================================================
# 축 2 (계속): 배포본이 실제로 동작하는가 - 합성 씬 왕복
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    plan = service.build_purge_plan()
    deleteNames = [node["name"] for node in plan["deleteNodes"]]
    reportNames = [node["name"] for node in plan["reportNodes"]]

    slotLabels = [
        slot["ownerName"] + "." + str(slot["displayName"])
        for slot in plan["detachSlots"]
    ]
    reporter.assert_test(
        deleteNames == ["deploy_light_missing"]
        and len(slotLabels) == 2
        and all("deploy_mat" in label for label in slotLabels),
        "TC03 배포본이 깨진 슬롯과 잔재 노드를 함께 찾는다",
        f"slots={slotLabels}, delete={deleteNames}, report={reportNames}",
    )
except Exception:
    reporter.error("TC03 배포본이 누락 애셋을 찾고 분류한다", traceback.format_exc(limit=4))

try:
    _build_fixture()
    service = MissingAsset()
    result = service.apply_purge_plan(service.build_purge_plan())
    remaining = [str(node.name) for node in rt.objects]

    reporter.assert_test(
        len(result["detached"]) == 2
        and result["deleted"] == ["deploy_light_missing"]
        and result["failed"] == []
        and "deploy_geo_missing" in remaining
        and "deploy_geo_clean" in remaining,
        "TC04 배포본이 슬롯을 떼고 잔재만 지우며 메쉬를 지킨다",
        f"result={result}, remaining={remaining}",
    )
except Exception:
    reporter.error(
        "TC04 배포본이 비지오메트리만 지우고 지오메트리를 지킨다",
        traceback.format_exc(limit=4),
    )


# ============================================================
# 축 3: 진입점 배선 - 세 툴이 그 기능을 실제로 물고 있는가
# ============================================================
try:
    from meshvalidator.func import missingAsset as validatorStep

    reporter.assert_test(
        _under(validatorStep, DEPLOY_VALIDATOR)
        and callable(validatorStep.build_missing_asset_errors)
        and callable(validatorStep.build_node_slot_errors)
        and callable(validatorStep.has_actionable)
        and {"geometry", "unknown"}.issubset(set(validatorStep.REASON_LABELS)),
        "TC05 MeshValidator 순수 스텝이 배포본에서 로드되고 사유 키가 맞다",
        f"file={getattr(validatorStep, '__file__', None)}, "
        f"labels={sorted(validatorStep.REASON_LABELS)}",
    )
except Exception:
    reporter.error(
        "TC05 MeshValidator 순수 스텝이 배포본에서 로드되고 사유 키가 맞다",
        traceback.format_exc(limit=4),
    )

try:
    from meshvalidator.ui import slot as validatorSlot

    reporter.assert_test(
        _under(validatorSlot, DEPLOY_VALIDATOR)
        and hasattr(validatorSlot.RolloutSlot, "run_missing_asset_step")
        and hasattr(validatorSlot.RolloutSlot, "collect_node_missing_asset_errors"),
        "TC06 MeshValidator UI가 검사 스텝과 Pick 스텝을 둘 다 물고 있다",
        f"file={getattr(validatorSlot, '__file__', None)}",
    )
except Exception:
    reporter.error(
        "TC06 MeshValidator UI가 검사 스텝과 Pick 스텝을 둘 다 물고 있다",
        traceback.format_exc(limit=4),
    )

try:
    import inspect

    from meshnameselector.func.saveLoad import MeshSaveLoadService

    signature = inspect.signature(MeshSaveLoadService.save_file)
    reporter.assert_test(
        _under(sys.modules["meshnameselector.func.saveLoad"], DEPLOY_EXPORTER)
        and hasattr(MeshSaveLoadService, "run_missing_asset_step")
        and "inConfirmPurge" in signature.parameters
        and signature.parameters["inConfirmPurge"].default is None,
        "TC07 MeshNameSelector가 저장 전 스텝과 확인 콜백을 물고 있다",
        f"file={sys.modules['meshnameselector.func.saveLoad'].__file__}, "
        f"params={list(signature.parameters)}",
    )
except Exception:
    reporter.error(
        "TC07 MeshNameSelector가 저장 전 스텝과 확인 콜백을 물고 있다",
        traceback.format_exc(limit=4),
    )

try:
    from baseskeletonbuilder.func import gates as builderGates
    from baseskeletonbuilder.func import missingAssetStep as builderStep

    reporter.assert_test(
        _under(builderGates, DEPLOY_BUILDER)
        and _under(builderStep, DEPLOY_BUILDER)
        and builderGates.KIND_MISSING_ASSET == "missingAsset"
        and callable(builderStep.purge_missing_assets)
        and callable(builderStep.build_confirm_detail),
        "TC08 BaseSkeletonBuilder 게이트 사유와 정리 스텝이 배포됐다",
        f"gates={getattr(builderGates, '__file__', None)}, "
        f"step={getattr(builderStep, '__file__', None)}",
    )
except Exception:
    reporter.error(
        "TC08 BaseSkeletonBuilder 게이트 사유와 정리 스텝이 배포됐다",
        traceback.format_exc(limit=4),
    )

try:
    from baseskeletonbuilder.func import buildService as builderService

    planSignature = inspect.signature(builderService.plan_scene)
    reporter.assert_test(
        hasattr(builderService.SceneOps, "purge_missing_assets")
        and "inConfirmPurge" in planSignature.parameters
        and planSignature.parameters["inConfirmPurge"].default is None,
        "TC09 BaseSkeletonBuilder가 정리를 수확 앞에 물고 있다",
        f"params={list(planSignature.parameters)}",
    )
except Exception:
    reporter.error(
        "TC09 BaseSkeletonBuilder가 정리를 수확 앞에 물고 있다",
        traceback.format_exc(limit=4),
    )


# ============================================================
# 배포본 게이트가 실제로 사유를 만드는가 (기능 왕복)
# ============================================================
try:
    _build_fixture()
    summary = builderStep.purge_missing_assets()
    reasons = builderGates.evaluate_preconditions([], {"noop": False}, None, summary)

    reporter.assert_test(
        summary["blockCount"] == 1
        and summary["slotCount"] == 2
        and [reason["kind"] for reason in reasons]
        == [builderGates.KIND_MISSING_ASSET],
        "TC10 배포본 게이트가 잔재 노드를 차단한다",
        f"summary={summary}",
    )
except Exception:
    reporter.error(
        "TC10 배포본 게이트가 잔재 노드를 차단한다", traceback.format_exc(limit=4)
    )


# ============================================================
# TC11: 깨진 슬롯만으로는 **차단하지 않는다** (과차단 회귀 가드)
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    slotBox = rt.Box(name="deploy_slot_only", mapcoords=True)
    slotMat = rt.StandardMaterial(name="deploy_slot_mat")
    slotMat.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/s.png")
    slotBox.material = slotMat

    summary = builderStep.purge_missing_assets()
    reasons = builderGates.evaluate_preconditions([], {"noop": False}, None, summary)

    reporter.assert_test(
        summary["slotCount"] == 1 and summary["blockCount"] == 0 and reasons == [],
        "TC11 깨진 슬롯만으로는 변환을 차단하지 않는다",
        f"summary={summary}, reasons={reasons}",
    )
except Exception:
    reporter.error(
        "TC11 깨진 슬롯만으로는 변환을 차단하지 않는다", traceback.format_exc(limit=4)
    )


# ============================================================
# TC12: 배포본 다이얼로그 문구가 만들어진다
# ============================================================
try:
    _build_fixture()
    plan = MissingAsset().build_purge_plan()
    summaryText = build_purge_confirm_summary(plan)
    detailText = build_purge_detail_text(plan)

    reporter.assert_test(
        "진행하시겠습니까?" in summaryText
        and "[정리]" in detailText
        and "메쉬와 매테리얼은 그대로 둡니다" in summaryText,
        "TC12 배포본이 확인 다이얼로그 문구를 만든다",
        f"detailLines={len(detailText.splitlines())}",
    )
except Exception:
    reporter.error(
        "TC12 배포본이 확인 다이얼로그 문구를 만든다", traceback.format_exc(limit=4)
    )


reporter.summary()
reporter.close()
