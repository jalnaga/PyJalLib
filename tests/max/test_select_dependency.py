#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Select 서비스 - dependency 수집 기능 테스트 스크립트 (Type C 헤드레스 실행).

pyjallib.max.select.Select 클래스의 dependency 관련 메서드를 검증한다:
- get_all_dependencies_optimized()
- get_dependents()
- collect_addon_helpers()  (정서 기반으로 재구현됨)
- select_dependencies()

``collect_addon_helpers()``는 더 이상 라이브러리가 아는 레이어 접두로 수집하지 않고,
호출부가 주입한 정서(``NodeCollectPolicy``)의 규칙으로 수집한다. 인터페이스가 의도적으로
바뀌었으므로 이 스위트는 **셋업을 정서 주입 형태로 고쳤다** - 판정 기준을 낮춘 것이
아니라, 정서 미주입(확장 없음)과 정서 주입(확장 발동) 두 갈래를 모두 단정한다.

3ds Max 내부에서 실행되며, TestReporter를 통해 결과를 로그에 기록한다.

테스트 유형: Type C (3dsmaxbatch.exe 헤드레스 실행 + 로그 분석)
실행 방법:
    uv run python tests/run_max_tests.py
로그 파일: tests/logs/test_SelectDependency.log
"""

import sys
import importlib.util
from pathlib import Path

# -- 경로 설정 -----------------------------------------------------------------
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

from pymxs import runtime as rt  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402

# 3ds Max 기동 시 pyjallib이 사전 캐시되므로, 수정된 소스를 importlib로 강제 로드
# (pymxs_pitfalls.md 섹션 8 패턴)


def _force_load(inModuleName, inRelativePath):
    """워크스페이스 소스 파일을 importlib로 강제 로드해 sys.modules에 등록한다.

    ``select.py``가 ``nodeCollectResolver``를 상대 import하므로 **의존 모듈을 먼저
    등록해야 한다.** 등록하지 않으면 상대 import가 선캐시된 배포본 패키지 경로를 뒤져
    신규 모듈을 찾지 못한다.

    Args:
        inModuleName (str): sys.modules에 등록할 모듈 이름
        inRelativePath (str): src 아래 상대 경로

    Returns:
        로드된 모듈 객체
    """
    modulePath = Path(_srcPath) / inRelativePath
    moduleSpec = importlib.util.spec_from_file_location(inModuleName, modulePath)
    module = importlib.util.module_from_spec(moduleSpec)
    sys.modules[inModuleName] = module
    moduleSpec.loader.exec_module(module)
    return module


_policyMod = _force_load(
    "pyjallib.max.nodeCollectPolicy", "pyjallib/max/nodeCollectPolicy.py"
)
_resolverMod = _force_load(
    "pyjallib.max.nodeCollectResolver", "pyjallib/max/nodeCollectResolver.py"
)
_selectMod = _force_load("pyjallib.max.select", "pyjallib/max/select.py")

Select = _selectMod.Select
build_policy = _resolverMod.build_policy
RULE_ALL_OR_NOTHING = _policyMod.RULE_ALL_OR_NOTHING

from pyjallib.max.name import Name  # noqa: E402
from pyjallib.max.bone import Bone  # noqa: E402
from pyjallib.max.layer import Layer  # noqa: E402

# -- TestReporter 초기화 -------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
reporter = TestReporter("SelectDependency", LOG_DIR)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _make_select_service(inPolicy=None):
    """Select 서비스 인스턴스를 생성하여 반환한다.

    Args:
        inPolicy: 주입할 노드 수집 확장 정서. None이면 규칙 발동 없음
    """
    nameService = Name()
    boneService = Bone(nameService=nameService)
    layerService = Layer()
    return Select(
        nameService=nameService,
        boneService=boneService,
        layerService=layerService,
        inCollectPolicy=inPolicy,
    )


# ============================================================
# TC01: Select 인스턴스 생성
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()
    reporter.assert_test(
        sel is not None,
        "TC01 Select 인스턴스 생성",
        "Select() 반환값이 None"
    )
except Exception as e:
    reporter.error("TC01 Select 인스턴스 생성", str(e))


# ============================================================
# TC02: get_all_dependencies_optimized - 단순 본 체인
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    # 3단계 본 체인 생성: grandBone -> parentBone -> childBone
    grandBone = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    grandBone.name = "grandBone"

    parentBone = rt.BoneSys.createBone(
        rt.Point3(10, 0, 0), rt.Point3(20, 0, 0), rt.Point3(0, 0, 1)
    )
    parentBone.name = "parentBone"
    parentBone.parent = grandBone

    childBone = rt.BoneSys.createBone(
        rt.Point3(20, 0, 0), rt.Point3(30, 0, 0), rt.Point3(0, 0, 1)
    )
    childBone.name = "childBone"
    childBone.parent = parentBone

    # childBone 입력 -> 부모 체인이 수집되어야 함
    deps, visited = sel.get_all_dependencies_optimized([childBone])

    # childBone 자신 + parentBone + grandBone 이 모두 수집되어야 함
    depNames = [n.name for n in deps]
    reporter.assert_test(
        len(deps) >= 1,
        "TC02 get_all_dependencies_optimized 반환 비어있지 않음",
        f"수집된 노드 수: {len(deps)}, 이름: {depNames}"
    )
    reporter.assert_test(
        visited is not None,
        "TC02-b visited set 반환",
        "visited가 None"
    )
    reporter.assert_test(
        "childBone" in depNames,
        "TC02-c childBone 자신이 결과에 포함",
        f"결과: {depNames}"
    )
    reporter.assert_test(
        "parentBone" in depNames,
        "TC02-d parentBone이 부모 체인으로 수집",
        f"결과: {depNames}"
    )
    reporter.assert_test(
        "grandBone" in depNames,
        "TC02-e grandBone이 부모 체인으로 수집",
        f"결과: {depNames}"
    )
except Exception as e:
    reporter.error("TC02 get_all_dependencies_optimized 본 체인", str(e))


# ============================================================
# TC03: get_all_dependencies_optimized - visited 재사용
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    bone1 = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    bone1.name = "bone1"

    bone2 = rt.BoneSys.createBone(
        rt.Point3(10, 0, 0), rt.Point3(20, 0, 0), rt.Point3(0, 0, 1)
    )
    bone2.name = "bone2"
    bone2.parent = bone1

    # 1차 호출
    deps1, visited1 = sel.get_all_dependencies_optimized([bone2])
    countAfter1st = len(visited1)

    # 2차 호출 - visited 재사용하면 이미 방문한 노드를 다시 추가하지 않아야 함
    deps2, visited2 = sel.get_all_dependencies_optimized(deps1, visited1)

    reporter.assert_test(
        visited1 is visited2,
        "TC03 visited set 동일 객체 재사용",
        "visited set이 다른 객체로 교체됨"
    )
    reporter.assert_test(
        len(visited2) >= countAfter1st,
        "TC03-b 2차 호출 후 visited 크기가 줄지 않음",
        f"1차 후={countAfter1st}, 2차 후={len(visited2)}"
    )
except Exception as e:
    reporter.error("TC03 get_all_dependencies_optimized visited 재사용", str(e))


# ============================================================
# TC04: get_all_dependencies_optimized - 빈 입력
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    deps, visited = sel.get_all_dependencies_optimized([])

    reporter.assert_test(
        isinstance(deps, list),
        "TC04 빈 입력 - 결과가 리스트",
        f"반환 타입: {type(deps)}"
    )
    reporter.assert_test(
        len(deps) == 0,
        "TC04-b 빈 입력 - 결과 빈 리스트",
        f"결과 길이: {len(deps)}"
    )
except Exception as e:
    reporter.error("TC04 get_all_dependencies_optimized 빈 입력", str(e))


# ============================================================
# TC05: get_all_dependencies_optimized - Skin 모디파이어 메시
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    # 본 생성
    skinBone = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(20, 0, 0), rt.Point3(0, 0, 1)
    )
    skinBone.name = "SkinBone"

    # 메시 생성
    mesh = rt.Box(
        pos=rt.Point3(0, 0, 0),
        length=10,
        width=10,
        height=10,
        name="SkinMesh"
    )

    # Skin 모디파이어 추가 및 본 바인딩
    skinMod = rt.Skin()
    rt.addModifier(mesh, skinMod)
    rt.select(mesh)
    rt.modPanel.setCurrentObject(skinMod)
    rt.skinOps.addBone(skinMod, skinBone, 0)

    # 메시를 입력으로 dependency 수집
    deps, visited = sel.get_all_dependencies_optimized([mesh])
    depNames = [n.name for n in deps]

    reporter.assert_test(
        len(deps) >= 1,
        "TC05 Skin 메시 - 결과 비어있지 않음",
        f"결과 노드 수: {len(deps)}, 이름: {depNames}"
    )
    reporter.assert_test(
        "SkinMesh" in depNames,
        "TC05-b SkinMesh 자신이 포함",
        f"결과: {depNames}"
    )
except Exception as e:
    reporter.error("TC05 get_all_dependencies_optimized Skin 모디파이어", str(e))


# ============================================================
# TC06: get_dependents - 자식 노드 수집
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    # 부모-자식 계층 생성
    parentPoint = rt.Point(name="parentPoint", pos=rt.Point3(0, 0, 0))
    child1 = rt.Point(name="child1Point", pos=rt.Point3(10, 0, 0))
    child2 = rt.Point(name="child2Point", pos=rt.Point3(20, 0, 0))
    grandChild = rt.Point(name="grandChildPoint", pos=rt.Point3(30, 0, 0))

    child1.parent = parentPoint
    child2.parent = parentPoint
    grandChild.parent = child1

    dependents = sel.get_dependents([parentPoint])
    depNames = [n.name for n in dependents]

    reporter.assert_test(
        isinstance(dependents, list),
        "TC06 get_dependents 반환 타입 리스트",
        f"반환 타입: {type(dependents)}"
    )
    reporter.assert_test(
        "child1Point" in depNames,
        "TC06-b child1이 dependents에 포함",
        f"결과: {depNames}"
    )
    reporter.assert_test(
        "child2Point" in depNames,
        "TC06-c child2가 dependents에 포함",
        f"결과: {depNames}"
    )
    reporter.assert_test(
        "grandChildPoint" in depNames,
        "TC06-d grandChild가 재귀적으로 포함",
        f"결과: {depNames}"
    )
except Exception as e:
    reporter.error("TC06 get_dependents 자식 노드", str(e))


# ============================================================
# TC07: get_dependents - 빈 입력
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    dependents = sel.get_dependents([])

    reporter.assert_test(
        isinstance(dependents, list),
        "TC07 get_dependents 빈 입력 - 리스트 반환",
        f"반환 타입: {type(dependents)}"
    )
    reporter.assert_test(
        len(dependents) == 0,
        "TC07-b get_dependents 빈 입력 - 빈 결과",
        f"결과 길이: {len(dependents)}"
    )
except Exception as e:
    reporter.error("TC07 get_dependents 빈 입력", str(e))


# ============================================================
# TC08: collect_addon_helpers - 정서 미주입이면 확장 없음
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()
    layerService = Layer()

    # 규칙 대상이 될 만한 레이어가 씬에 있어도, 정서가 없으면 발동하지 않는다.
    addonBone = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    addonBone.name = "tc08AddonBone"
    addonHelperNode = rt.Point(name="tc08AddonHelper", pos=rt.Point3(0, 0, 0))
    layerService.create_layer_from_array(
        [addonBone, addonHelperNode], "Tc08_AddOn_Face"
    )

    addonHelpers = sel.collect_addon_helpers([addonBone])

    reporter.assert_test(
        isinstance(addonHelpers, set),
        "TC08 collect_addon_helpers 반환 타입 set",
        f"반환 타입: {type(addonHelpers)}"
    )
    reporter.assert_test(
        len(addonHelpers) == 0,
        "TC08-b 정서 미주입 -> 규칙 대상 레이어가 있어도 빈 set",
        f"결과 크기: {len(addonHelpers)}"
    )
except Exception as e:
    reporter.error("TC08 collect_addon_helpers 정서 미주입", str(e))


# ============================================================
# TC08b: collect_addon_helpers - 정서 주입이면 규칙이 발동한다
# ============================================================
try:
    _reset_scene()
    layerService = Layer()

    addonBone = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    addonBone.name = "tc08bAddonBone"
    helperInLayer = rt.Point(name="tc08bHelperInLayer", pos=rt.Point3(0, 0, 0))
    helperOther = rt.Point(name="tc08bHelperOther", pos=rt.Point3(30, 0, 0))
    layerService.create_layer_from_array(
        [addonBone, helperInLayer], "Tc08b_AddOn_Face"
    )
    layerService.create_layer_from_array([helperOther], "Tc08b_Other")

    sel = _make_select_service(
        build_policy(
            inAllOrNothingLayers=["Tc08b_AddOn_*"],
            inAllOrNothingAddSuperClass="Helper",
        )
    )
    addonHelpers = sel.collect_addon_helpers([addonBone])
    addonHelperNames = sorted(str(n.name) for n in addonHelpers)

    reporter.assert_test(
        addonHelperNames == ["tc08bHelperInLayer"],
        "TC08b 정서 주입 -> 본이 판정을 발동시키고 같은 레이어 Helper만 수집",
        f"결과: {addonHelperNames}"
    )

    collectedNodes, byRule = sel.collect_by_rule([addonBone])
    reporter.assert_test(
        len(byRule.get(RULE_ALL_OR_NOTHING, [])) == 1,
        "TC08b-b collect_by_rule이 규칙별 집계를 돌려준다",
        f"byRule: {{k: len(v) for k, v in byRule.items()}} -> "
        f"{ {ruleKey: len(handles) for ruleKey, handles in byRule.items()} }"
    )
except Exception as e:
    reporter.error("TC08b collect_addon_helpers 정서 주입", str(e))


# ============================================================
# TC09: collect_addon_helpers - 빈 입력
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    addonHelpers = sel.collect_addon_helpers([])

    reporter.assert_test(
        isinstance(addonHelpers, set),
        "TC09 collect_addon_helpers 빈 입력 - set 반환",
        f"반환 타입: {type(addonHelpers)}"
    )
    reporter.assert_test(
        len(addonHelpers) == 0,
        "TC09-b collect_addon_helpers 빈 입력 - 빈 set",
        f"결과 크기: {len(addonHelpers)}"
    )
except Exception as e:
    reporter.error("TC09 collect_addon_helpers 빈 입력", str(e))


# ============================================================
# TC10: select_dependencies - 전체 플로우
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    # 본 체인 생성
    rootBone = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    rootBone.name = "rootBone"

    midBone = rt.BoneSys.createBone(
        rt.Point3(10, 0, 0), rt.Point3(20, 0, 0), rt.Point3(0, 0, 1)
    )
    midBone.name = "midBone"
    midBone.parent = rootBone

    tipBone = rt.BoneSys.createBone(
        rt.Point3(20, 0, 0), rt.Point3(30, 0, 0), rt.Point3(0, 0, 1)
    )
    tipBone.name = "tipBone"
    tipBone.parent = midBone

    result = sel.select_dependencies([tipBone])

    reporter.assert_test(
        isinstance(result, dict),
        "TC10 select_dependencies 반환 타입 dict",
        f"반환 타입: {type(result)}"
    )
    reporter.assert_test(
        "nodes" in result and "stats" in result,
        "TC10-b nodes 및 stats 키 존재",
        f"키 목록: {list(result.keys())}"
    )

    nodes = result["nodes"]
    stats = result["stats"]
    nodeNames = [n.name for n in nodes if hasattr(n, "name")]

    reporter.assert_test(
        isinstance(nodes, list),
        "TC10-c nodes가 리스트",
        f"nodes 타입: {type(nodes)}"
    )
    reporter.assert_test(
        len(nodes) >= 1,
        "TC10-d nodes 비어있지 않음",
        f"nodes 길이: {len(nodes)}"
    )
    reporter.assert_test(
        "total_count" in stats,
        "TC10-e stats에 total_count 존재",
        f"stats 키: {list(stats.keys())}"
    )
    reporter.assert_test(
        stats["total_count"] == len(nodes),
        "TC10-f total_count와 nodes 길이 일치",
        f"total_count={stats['total_count']}, nodes 길이={len(nodes)}"
    )
    reporter.assert_test(
        "tipBone" in nodeNames,
        "TC10-g tipBone이 결과에 포함",
        f"결과 노드: {nodeNames}"
    )
except Exception as e:
    reporter.error("TC10 select_dependencies 전체 플로우", str(e))


# ============================================================
# TC11: select_dependencies - 빈 입력
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    result = sel.select_dependencies([])

    reporter.assert_test(
        isinstance(result, dict),
        "TC11 select_dependencies 빈 입력 - dict 반환",
        f"반환 타입: {type(result)}"
    )
    reporter.assert_test(
        "nodes" in result,
        "TC11-b nodes 키 존재",
        f"키 목록: {list(result.keys())}"
    )
    reporter.assert_test(
        isinstance(result["nodes"], list),
        "TC11-c nodes가 리스트",
        f"nodes 타입: {type(result['nodes'])}"
    )
except Exception as e:
    reporter.error("TC11 select_dependencies 빈 입력", str(e))


# ============================================================
# TC12: select_dependencies - stats 구조 검증
# ============================================================
try:
    _reset_scene()
    sel = _make_select_service()

    singleBone = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    singleBone.name = "singleBone"

    result = sel.select_dependencies([singleBone])
    stats = result["stats"]

    expectedKeys = [
        "selected_count",
        "dependents_count",
        "dependencies_1st_count",
        "dependencies_2nd_count",
        "addon_helpers_count",
        "collected_by_rule",
        "total_count",
        "time_dependents_ms",
        "time_dependencies_1st_ms",
        "time_dependencies_2nd_ms",
        "time_total_ms",
    ]
    missingKeys = [k for k in expectedKeys if k not in stats]

    reporter.assert_test(
        len(missingKeys) == 0,
        "TC12 stats에 필수 키 모두 존재",
        f"누락된 키: {missingKeys}"
    )
    reporter.assert_test(
        stats["selected_count"] == 1,
        "TC12-b selected_count가 1",
        f"selected_count={stats['selected_count']}"
    )
    reporter.assert_test(
        stats["time_total_ms"] >= 0,
        "TC12-c time_total_ms가 0 이상",
        f"time_total_ms={stats['time_total_ms']}"
    )
except Exception as e:
    reporter.error("TC12 select_dependencies stats 구조", str(e))


# ============================================================
# 결과 요약
# ============================================================
reporter.summary()
reporter.close()
