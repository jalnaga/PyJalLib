#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`MissingAsset` 어댑터 테스트 (Type C, 3dsmaxbatch 헤드레스).

순수 엔진의 분류 규칙은 콘솔 pytest가 전수로 덮는다(`tests/test_missing_asset_policy.py`).
여기서 검증하는 것은 **씬 접근 자체의 정확성**이다 - 누락을 실제로 찾아내는가,
지오메트리를 실제로 지키는가, 두 번 실행해도 무해한가.

이 사이클의 핵심 안전 축은 하나다: **지오메트리 노드는 삭제되지 않는다.** 그래서
TC05가 "지오메트리가 남아 있다"를 단정하는 데 그치지 않고, TC06이 **지오메트리를
삭제하는 구현이었다면 TC05가 실패함**을 같은 실행에서 보인다(`testing/discriminating_power.md`).

기대 TC 수: 19 (TC00~TC18)

실행:
    uv run python tests/run_max_tests.py test_missing_asset.py
"""

import os
import sys
from pathlib import Path

# pyjallib 소스 경로 선주입 + 배포본 선점 퍼지 (다른 pyjallib import보다 앞).
sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt  # noqa: E402

import pyjallib  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402
from pyjallib.max.missingAssetPolicy import REASON_GEOMETRY  # noqa: E402
from pyjallib.max.missingAssetResolver import MissingAsset, is_geometry_node  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("MissingAsset", LOG_DIR)

#: 존재하지 않는 디렉토리. 픽스처의 누락 애셋이 여기를 가리킨다.
MISSING_ROOT = "D:/__pyjallib_missing_asset_test__"

#: Max 설치본에 딸려 오는 실재 맵. "해석되는 애셋"의 대조군으로 쓴다.
INSTALLED_MAP = r"C:/Program Files/Autodesk/3ds Max 2024/maps/uvwunwrap/UV_Checker.png"


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _build_fixture():
    """누락 애셋을 물린 합성 씬을 만든다.

    구성:
        fixture_geo_missing   Box + 없는 비트맵           -> 지오메트리 (보고 대상)
        fixture_geo_ok        Box + **실재하는** 비트맵    -> 대조군 (계획에 들어오면 안 됨)
        fixture_light_missing OmniLight + 없는 projectorMap -> 비지오메트리 (삭제 대상)
        fixture_helper_plain  Point 헬퍼, 애셋 없음        -> 대조군

    Returns:
        dict: 사전 어서션 값. **테스트가 만들려던 조건이 실제로 만들어졌는지**를
            본 판정 앞에서 먼저 단정하기 위한 재료다
    """
    _reset_scene()

    geoMissing = rt.Box(name="fixture_geo_missing", mapcoords=True)
    missingMaterial = rt.StandardMaterial(name="fixture_mat_missing")
    missingMaterial.diffuseMap = rt.BitmapTexture(
        filename=MISSING_ROOT + "/fixture_diffuse.png"
    )
    geoMissing.material = missingMaterial

    geoOk = rt.Box(name="fixture_geo_ok", mapcoords=True)
    okMaterial = rt.StandardMaterial(name="fixture_mat_ok")
    okMaterial.diffuseMap = rt.BitmapTexture(filename=INSTALLED_MAP)
    geoOk.material = okMaterial

    light = rt.OmniLight(name="fixture_light_missing")
    light.projector = True
    light.projectorMap = rt.BitmapTexture(
        filename=MISSING_ROOT + "/fixture_projector.png"
    )

    rt.Point(name="fixture_helper_plain")

    return {
        "missingRootAbsent": not os.path.exists(MISSING_ROOT),
        "installedMapExists": os.path.exists(INSTALLED_MAP),
        "nodeCount": len(list(rt.objects)),
        "geoMissingIsGeometry": is_geometry_node(geoMissing),
        "lightIsGeometry": is_geometry_node(light),
    }


def _node_names(inNodes):
    """노드 레코드 목록에서 이름만 뽑는다.

    Args:
        inNodes: 노드 레코드 목록

    Returns:
        list[str]: 이름 목록
    """
    return [record["name"] for record in inNodes]


def _scene_node_names():
    """씬에 실제로 남아 있는 노드 이름 목록을 돌려준다.

    Returns:
        list[str]: 노드 이름 목록
    """
    return [str(node.name) for node in rt.objects]


# ============================================================
# TC00: 로드 출처
# ============================================================
try:
    reporter.assert_test(
        assert_loaded_from_checkout(pyjallib),
        "TC00 pyjallib 로드 출처가 검증 대상인가",
        f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
    )
except Exception as e:
    reporter.error("TC00 pyjallib 로드 출처가 검증 대상인가", str(e))


# ============================================================
# TC01: 픽스처 사전 어서션 - 만들려던 조건이 실제로 만들어졌는가
# ============================================================
try:
    assertions = _build_fixture()
    reporter.assert_test(
        assertions["missingRootAbsent"] is True
        and assertions["installedMapExists"] is True
        and assertions["nodeCount"] == 4
        and assertions["geoMissingIsGeometry"] is True
        and assertions["lightIsGeometry"] is False,
        "TC01 픽스처 사전 어서션",
        f"{assertions}",
    )
except Exception as e:
    reporter.error("TC01 픽스처 사전 어서션", str(e))


# ============================================================
# TC02: 스캔 - 누락 애셋을 찾아내는가
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    plan = service.build_purge_plan()

    missingPaths = [asset["path"].lower() for asset in plan["assets"]]
    foundDiffuse = any("fixture_diffuse.png" in path for path in missingPaths)
    foundProjector = any("fixture_projector.png" in path for path in missingPaths)

    reporter.assert_test(
        foundDiffuse and foundProjector,
        "TC02 누락 애셋 2건을 찾는다",
        f"assets={missingPaths}",
    )
except Exception as e:
    reporter.error("TC02 누락 애셋 2건을 찾는다", str(e))


# ============================================================
# TC03: 해석되는 애셋은 계획에 들어오지 않는다 (오탐 없음)
# ============================================================
try:
    _build_fixture()
    plan = MissingAsset().build_purge_plan()

    missingPaths = [asset["path"].lower() for asset in plan["assets"]]
    reporter.assert_test(
        not any("uv_checker" in path for path in missingPaths),
        "TC03 해석되는 애셋은 누락으로 잡히지 않는다",
        f"assets={missingPaths}",
    )
except Exception as e:
    reporter.error("TC03 해석되는 애셋은 누락으로 잡히지 않는다", str(e))


# ============================================================
# TC04: 분류 - 라이트는 삭제, 메쉬는 보고
# ============================================================
try:
    _build_fixture()
    plan = MissingAsset().build_purge_plan()

    deleteNames = _node_names(plan["deleteNodes"])
    reportNames = _node_names(plan["reportNodes"])

    reporter.assert_test(
        deleteNames == ["fixture_light_missing"]
        and reportNames == ["fixture_geo_missing"]
        and plan["reportNodes"][0]["reason"] == REASON_GEOMETRY
        and plan["empty"] is False,
        "TC04 비지오메트리는 삭제·지오메트리는 보고로 분류된다",
        f"delete={deleteNames}, report={reportNames}",
    )
except Exception as e:
    reporter.error("TC04 비지오메트리는 삭제·지오메트리는 보고로 분류된다", str(e))


# ============================================================
# TC05: 적용 - 삭제되고, **지오메트리는 남는다** (핵심 안전 축)
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    plan = service.build_purge_plan()
    result = service.apply_purge_plan(plan)

    remaining = _scene_node_names()
    reporter.assert_test(
        result["deleted"] == ["fixture_light_missing"]
        and result["failed"] == []
        and "fixture_light_missing" not in remaining
        and "fixture_geo_missing" in remaining
        and "fixture_geo_ok" in remaining
        and "fixture_helper_plain" in remaining,
        "TC05 비지오메트리만 삭제되고 지오메트리는 남는다",
        f"result={result}, remaining={remaining}",
    )
except Exception as e:
    reporter.error("TC05 비지오메트리만 삭제되고 지오메트리는 남는다", str(e))


# ============================================================
# TC06: 판별력 - 지오메트리를 지우는 구현이었다면 TC05가 실패한다
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    plan = service.build_purge_plan()

    # 계획을 일부러 뒤집는다 - 보고 대상(지오메트리)을 삭제 목록에 넣는다.
    # 어댑터는 삭제 직전에 **다시 확인**하므로 이것을 거부해야 한다.
    brokenPlan = dict(plan)
    brokenPlan["deleteNodes"] = list(plan["deleteNodes"]) + list(plan["reportNodes"])
    result = service.apply_purge_plan(brokenPlan)

    remaining = _scene_node_names()
    reporter.assert_test(
        "fixture_geo_missing" in remaining
        and any(item["name"] == "fixture_geo_missing" for item in result["failed"]),
        "TC06 계획이 지오메트리를 지목해도 어댑터가 거부한다",
        f"result={result}, remaining={remaining}",
    )
except Exception as e:
    reporter.error("TC06 계획이 지오메트리를 지목해도 어댑터가 거부한다", str(e))


# ============================================================
# TC07: 멱등 - 두 번째 계획은 삭제할 것이 없다
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    service.apply_purge_plan(service.build_purge_plan())
    secondPlan = service.build_purge_plan()

    # **사양이 바뀌었다(2026-09-29).** 슬롯 분리가 들어오면서, 메쉬가 물고 있던 깨진
    # 텍스쳐는 슬롯에서 떼어져 **보고 대상 자체가 사라진다.** 실기 판정에서 "잡았는데
    # 지우지 않았다고만 하고 끝"이던 것이 정확히 이 지점이었고, 그것이 해소된 것이
    # 이번 변경의 목적이다. 옛 기대(지오메트리 보고가 남는다)는 그 개선의 반대다.
    reporter.assert_test(
        secondPlan["empty"] is True
        and secondPlan["actionable"] == 0
        and secondPlan["deleteNodes"] == []
        and secondPlan["detachSlots"] == []
        and secondPlan["reportNodes"] == [],
        "TC07 정리 후 두 번째 계획은 할 일이 없다(멱등 - 보고까지 해소된다)",
        f"empty={secondPlan['empty']}, actionable={secondPlan['actionable']}, "
        f"delete={_node_names(secondPlan['deleteNodes'])}, "
        f"report={_node_names(secondPlan['reportNodes'])}",
    )
except Exception as e:
    reporter.error("TC07 두 번째 계획은 삭제 대상이 없다(멱등)", str(e))


# ============================================================
# TC08: 두 번 적용해도 무해하다
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    service.apply_purge_plan(service.build_purge_plan())
    beforeSecond = _scene_node_names()
    secondResult = service.apply_purge_plan(service.build_purge_plan())

    reporter.assert_test(
        secondResult["deleted"] == []
        and secondResult["failed"] == []
        and _scene_node_names() == beforeSecond,
        "TC08 두 번 적용해도 씬이 더 바뀌지 않는다",
        f"secondResult={secondResult}",
    )
except Exception as e:
    reporter.error("TC08 두 번 적용해도 씬이 더 바뀌지 않는다", str(e))


# ============================================================
# TC09: 깨끗한 씬 - 계획이 비어 있다
# ============================================================
try:
    _reset_scene()
    rt.Box(name="clean_box", mapcoords=True)
    plan = MissingAsset().build_purge_plan()

    reporter.assert_test(
        plan["empty"] is True and plan["hasFindings"] is False,
        "TC09 누락이 없는 씬은 계획이 비어 있다",
        f"empty={plan['empty']}, hasFindings={plan['hasFindings']}, "
        f"assets={[asset['path'] for asset in plan['assets']]}",
    )
except Exception as e:
    reporter.error("TC09 누락이 없는 씬은 계획이 비어 있다", str(e))


# ============================================================
# TC10: build_purge_plan은 씬을 바꾸지 않는다 ("확인 후 삭제"의 근거)
# ============================================================
try:
    _build_fixture()
    before = _scene_node_names()
    service = MissingAsset()
    service.build_purge_plan()
    service.build_purge_plan()

    reporter.assert_test(
        _scene_node_names() == before,
        "TC10 계획 수립은 씬을 바꾸지 않는다",
        f"before={before}, after={_scene_node_names()}",
    )
except Exception as e:
    reporter.error("TC10 계획 수립은 씬을 바꾸지 않는다", str(e))


# ============================================================
# TC11: 요약 문구가 지오메트리를 지키는 사실을 말한다
# ============================================================
try:
    _build_fixture()
    service = MissingAsset()
    summary = service.build_plan_summary(service.build_purge_plan())

    reporter.assert_test(
        summary.startswith("정리할 수 있는 것:")
        and "fixture_light_missing" in summary
        and "fixture_mat_missing" in summary
        and "매테리얼과 메쉬는 그대로 둡니다" in summary,
        "TC11 요약 문구가 자기완결형이고 조치 가능한 것으로 시작한다",
        f"summary={summary}",
    )
except Exception as e:
    reporter.error("TC11 요약 문구가 자기완결형이다", str(e))


# ============================================================
# 슬롯 분리 축 (2026-09-29 실기 판정으로 추가)
# ============================================================


def _build_slot_fixture():
    """깨진 텍스쳐를 **매테리얼 슬롯**에 물린 씬을 만든다.

    노드 축 픽스처와 다르다 - 여기서는 메쉬에 붙은 매테리얼의 슬롯이 깨진 상태를
    만든다. 프로덕션에서 실제로 발견된 형태가 이것이다(1씬 12슬롯).

    Returns:
        dict: 사전 어서션 값
    """
    _reset_scene()

    geoA = rt.Box(name="slot_geo_a", mapcoords=True)
    matA = rt.StandardMaterial(name="slot_mat_a")
    matA.diffuseMap = rt.BitmapTexture(filename=MISSING_ROOT + "/slot_diffuse.png")
    matA.bumpMap = rt.BitmapTexture(filename=MISSING_ROOT + "/slot_bump.png")
    geoA.material = matA

    geoB = rt.Box(name="slot_geo_b", mapcoords=True)
    matB = rt.StandardMaterial(name="slot_mat_b")
    matB.diffuseMap = rt.BitmapTexture(filename=INSTALLED_MAP)
    geoB.material = matB

    return {
        "missingRootAbsent": not os.path.exists(MISSING_ROOT),
        "installedMapExists": os.path.exists(INSTALLED_MAP),
        "nodeCount": len(list(rt.objects)),
        "bitmapCount": len(list(rt.getClassInstances(rt.BitmapTexture))),
    }


def _slot_labels(inPlan):
    """계획의 슬롯을 ``매테리얼.슬롯`` 라벨로 뽑는다.

    Args:
        inPlan: 계획 dict

    Returns:
        list[str]: 라벨 목록
    """
    return [
        f"{slot['ownerName']}.{slot['displayName']}" for slot in inPlan["detachSlots"]
    ]


# ============================================================
# TC12: 깨진 슬롯을 찾는다 - 클래스를 가리지 않는다
# ============================================================
try:
    assertions = _build_slot_fixture()
    plan = MissingAsset().build_purge_plan()

    reporter.assert_test(
        assertions["missingRootAbsent"] is True
        and assertions["bitmapCount"] == 3
        and sorted(_slot_labels(plan))
        == ["slot_mat_a.Bump", "slot_mat_a.Diffuse Color"],
        "TC12 깨진 텍스쳐 슬롯 2개를 찾는다",
        f"assertions={assertions}, slots={_slot_labels(plan)}",
    )
except Exception as e:
    reporter.error("TC12 깨진 텍스쳐 슬롯 2개를 찾는다", str(e))


# ============================================================
# TC13: 해석되는 텍스쳐의 슬롯은 잡지 않는다 (오탐 없음)
# ============================================================
try:
    _build_slot_fixture()
    plan = MissingAsset().build_purge_plan()

    reporter.assert_test(
        not any("slot_mat_b" in label for label in _slot_labels(plan)),
        "TC13 해석되는 텍스쳐의 슬롯은 잡지 않는다",
        f"slots={_slot_labels(plan)}",
    )
except Exception as e:
    reporter.error("TC13 해석되는 텍스쳐의 슬롯은 잡지 않는다", str(e))


# ============================================================
# TC14: 적용 - 슬롯이 떼어지고 **메쉬와 매테리얼은 남는다**
# ============================================================
try:
    _build_slot_fixture()
    service = MissingAsset()
    result = service.apply_purge_plan(service.build_purge_plan())

    remaining = _scene_node_names()
    materialNames = [str(mat.name) for mat in rt.sceneMaterials]
    reporter.assert_test(
        len(result["detached"]) == 2
        and result["failed"] == []
        and "slot_geo_a" in remaining
        and "slot_geo_b" in remaining
        and "slot_mat_a" in materialNames,
        "TC14 슬롯만 떼어지고 메쉬·매테리얼은 남는다",
        f"result={result}, remaining={remaining}, materials={materialNames}",
    )
except Exception as e:
    reporter.error("TC14 슬롯만 떼어지고 메쉬·매테리얼은 남는다", str(e))


# ============================================================
# TC15: 뗀 슬롯이 실제로 비었는가 - 텍스쳐맵이 사라진다
# ============================================================
try:
    _build_slot_fixture()
    service = MissingAsset()
    service.apply_purge_plan(service.build_purge_plan())

    material = rt.getNodeByName("slot_geo_a").material
    reporter.assert_test(
        rt.getProperty(material, "diffuseMap") is None
        and rt.getProperty(material, "bumpMap") is None
        and len(list(rt.getClassInstances(rt.BitmapTexture))) == 1,
        "TC15 뗀 슬롯이 실제로 비고 텍스쳐맵이 사라진다",
        f"bitmaps={len(list(rt.getClassInstances(rt.BitmapTexture)))}",
    )
except Exception as e:
    reporter.error("TC15 뗀 슬롯이 실제로 비고 텍스쳐맵이 사라진다", str(e))


# ============================================================
# TC16: 멱등 - 두 번째 계획은 뗄 것이 없다
# ============================================================
try:
    _build_slot_fixture()
    service = MissingAsset()
    service.apply_purge_plan(service.build_purge_plan())
    secondPlan = service.build_purge_plan()

    reporter.assert_test(
        secondPlan["detachSlots"] == []
        and secondPlan["empty"] is True
        and secondPlan["actionable"] == 0,
        "TC16 정리 후 두 번째 계획은 뗄 것이 없다(멱등)",
        f"slots={_slot_labels(secondPlan)}, empty={secondPlan['empty']}",
    )
except Exception as e:
    reporter.error("TC16 정리 후 두 번째 계획은 뗄 것이 없다(멱등)", str(e))


# ============================================================
# TC17: 판별력 - AssetManager 축이었다면 TC16이 실패한다
# ============================================================
try:
    _build_slot_fixture()
    service = MissingAsset()
    service.apply_purge_plan(service.build_purge_plan())

    # 슬롯을 다 뗀 **뒤에도** AssetManager는 누락을 계속 보고한다. 이 축으로
    # 멱등을 판정했다면 TC16이 영원히 실패한다 - 부재 판정을 직접 판정으로
    # 되돌린 이유가 이것이고, 그 사실을 여기서 못 박는다.
    assetMan = rt.AssetManager
    stillReported = 0
    for index in range(1, int(assetMan.GetNumAssets()) + 1):
        assetUser = assetMan.GetAssetByIndex(index)
        if assetUser is None:
            continue
        if not str(assetUser.GetFullFilePath()):
            stillReported += 1

    reporter.assert_test(
        stillReported > 0 and service.build_purge_plan()["actionable"] == 0,
        "TC17 AssetManager는 정리 후에도 누락을 보고한다(직접 판정이 필요한 이유)",
        f"assetManager가 여전히 보고={stillReported}건, 계획 actionable=0",
    )
except Exception as e:
    reporter.error(
        "TC17 AssetManager는 정리 후에도 누락을 보고한다(직접 판정이 필요한 이유)", str(e)
    )


# ============================================================
# TC18: 두 축이 한 번에 적용된다 - 슬롯 분리 + 노드 삭제
# ============================================================
try:
    _build_slot_fixture()
    light = rt.OmniLight(name="slot_light_missing")
    light.projector = True
    light.projectorMap = rt.BitmapTexture(filename=MISSING_ROOT + "/slot_proj.png")

    service = MissingAsset()
    plan = service.build_purge_plan()
    result = service.apply_purge_plan(plan)
    remaining = _scene_node_names()

    reporter.assert_test(
        len(result["detached"]) >= 2
        and result["deleted"] == ["slot_light_missing"]
        and result["failed"] == []
        and "slot_light_missing" not in remaining
        and "slot_geo_a" in remaining,
        "TC18 슬롯 분리와 노드 삭제가 한 번에 적용된다",
        f"result={result}, remaining={remaining}",
    )
except Exception as e:
    reporter.error("TC18 슬롯 분리와 노드 삭제가 한 번에 적용된다", str(e))

reporter.summary()
reporter.close()
