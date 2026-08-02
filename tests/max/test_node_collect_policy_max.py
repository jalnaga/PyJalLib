#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
노드 수집 확장 규칙의 서비스 통합 검증 (Type C 헤드레스 실행).

어댑터 단독 동작은 ``test_node_collect_resolver.py``가 검증한다. 이 스위트는 그
위층 - ``Dependent`` / ``Select`` / ``header`` 배선을 거쳐 규칙이 실제 수집 결과를
바꾸는지, 그리고 **정서를 주입하지 않으면 확장이 일어나지 않는지**를 본다. 후자가
이번 이관의 기본값 계약이므로 반드시 단정한다.

합성 씬을 쓴다. 규칙 3종 대상 레이어와 Helper·본이 섞인 레이어, 경계 밖 부모
노드를 만들어 규칙별 발동 차이를 갈라 본다.

테스트 유형: Type C (3dsmaxbatch.exe 헤드레스 실행 + 로그 분석)
실행 방법:
    uv run python tests/run_max_tests.py
로그 파일: tests/logs/test_NodeCollectPolicyMax.log
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


def _force_load(inModuleName, inRelativePath):
    """워크스페이스 소스 파일을 importlib로 강제 로드해 sys.modules에 등록한다.

    3ds Max 기동 시 배포본 pyjallib이 선캐시되므로, 그냥 import하면 워크트리 소스가
    아니라 배포본을 검증하게 된다(pymxs_pitfalls.md 섹션 8 패턴). 의존 모듈을 먼저
    등록해야 뒤에 로드되는 모듈의 ``from ... import``가 강제 로드본을 집는다.

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


# 로드 순서가 곧 의존 순서다. 엔진 -> 어댑터 -> 두 서비스.
_policyMod = _force_load(
    "pyjallib.max.nodeCollectPolicy", "pyjallib/max/nodeCollectPolicy.py"
)
_resolverMod = _force_load(
    "pyjallib.max.nodeCollectResolver", "pyjallib/max/nodeCollectResolver.py"
)
_dependentMod = _force_load("pyjallib.max.dependent", "pyjallib/max/dependent.py")
_selectMod = _force_load("pyjallib.max.select", "pyjallib/max/select.py")
# header도 강제 로드해야 신규 배선 메서드가 잡힌다. 위 두 서비스를 먼저 등록했으므로
# header의 상대 import가 강제 로드본을 집는다.
_headerMod = _force_load("pyjallib.max.header", "pyjallib/max/header.py")

Dependent = _dependentMod.Dependent
Select = _selectMod.Select
build_policy = _resolverMod.build_policy
RULE_ALL_OR_NOTHING = _policyMod.RULE_ALL_OR_NOTHING
RULE_MANDATORY = _policyMod.RULE_MANDATORY
RULE_PARENT_CHAIN = _policyMod.RULE_PARENT_CHAIN
RULE_PARENT_CONDITIONAL = _policyMod.RULE_PARENT_CONDITIONAL

from pyjallib.max.name import Name  # noqa: E402
from pyjallib.max.bone import Bone  # noqa: E402
from pyjallib.max.layer import Layer  # noqa: E402

# -- TestReporter 초기화 -------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
reporter = TestReporter("NodeCollectPolicyMax", LOG_DIR)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _make_bone(inName, inStartX):
    """이름을 지정한 본을 만든다."""
    bone = rt.BoneSys.createBone(
        rt.Point3(inStartX, 0, 0),
        rt.Point3(inStartX + 10, 0, 0),
        rt.Point3(0, 0, 1),
    )
    bone.name = inName
    return bone


def _names(inNodes):
    """노드 리스트를 정렬된 이름 리스트로 바꾼다."""
    return sorted(str(node.name) for node in inNodes if hasattr(node, "name"))


def _build_fixture_scene():
    """규칙 3종을 모두 갈라 볼 수 있는 합성 씬을 만든다.

    구성 의도:
        - ``Fx_Base``: 의존성 탐색의 시작점이 되는 본 체인. 규칙 대상이 아니다
        - ``Fx_Mandatory``: 규칙 1 대상. 의존성과 무관하게 항상 들어와야 한다
        - ``Fx_AddOn_Face``: 규칙 2 대상이고 **본과 Helper가 섞여 있다.** 판정은
          본으로 걸리고 추가는 Helper만이어야 한다
        - ``Fx_AddOn_Arm``: 규칙 2 대상이지만 판정에 걸리지 않는다. 레이어별 독립
          판정을 확인하는 대조군
        - ``Fx_Socket``: 규칙 3 대상. 부모가 집합에 들어올 때만 따라와야 한다
        - ``Fx_Boundary``: 부모 체인 경계. ``Fx_Outside``는 경계 밖이라 끌려오면 안 된다
        - ``fxSlotMesh``: ``fxFaceBone``에 스키닝된 메쉬

    ``fxSlotMesh``가 필요한 이유는 서비스 진입점(``select_dependencies`` /
    ``get_all_related_to_export``)이 규칙을 **2차 탐색 결과에만** 적용하기 때문이다.
    1·2차 탐색은 visited를 공유하므로, 순수 부모 계층만 있는 씬에서는 1차에서 전부
    방문되어 2차 결과가 비고 규칙이 발동할 여지가 없다. 실제 리그에서 규칙이 발동하는
    경로는 스킨/컨트롤러 의존으로 노드가 2차에 처음 등장하는 경로이므로(1차 탐색은
    스킨 의존 노드를 결과에 담되 방문 처리하지 않는다), 픽스처가 그 구조를 갖춰야
    서비스 통합을 실제로 검증한다. 규칙 입력을 2차 결과로 두는 것은 이관 전 동작이며,
    이번 스코프는 수집 결과의 확장만 다룬다.

    Returns:
        dict: 이름으로 노드를 꺼낼 수 있는 딕셔너리
    """
    layerService = Layer()

    # 경계 밖 루트 - 부모 체인이 여기까지 올라오면 실패다.
    outsideRoot = _make_bone("fxOutsideRoot", 0)
    layerService.create_layer_from_array([outsideRoot], "Fx_Outside")

    # 경계 레이어 - 규칙이 노드를 넣을 때 이 안에서만 부모를 끌어온다.
    boundaryRoot = _make_bone("fxBoundaryRoot", 10)
    boundaryMid = _make_bone("fxBoundaryMid", 20)
    boundaryRoot.parent = outsideRoot
    boundaryMid.parent = boundaryRoot
    layerService.create_layer_from_array([boundaryRoot, boundaryMid], "Fx_Boundary")

    # 의존성 탐색 시작점.
    baseBone = _make_bone("fxBaseBone", 30)
    baseBone.parent = boundaryMid
    layerService.create_layer_from_array([baseBone], "Fx_Base")

    # 규칙 1 대상 - 경계 안에 부모를 둔다(부모 체인 확장을 함께 확인).
    mandatoryBone = _make_bone("fxMandatoryBone", 40)
    mandatoryBone.parent = boundaryMid
    layerService.create_layer_from_array([mandatoryBone], "Fx_Mandatory")

    # 규칙 2 대상 (발동) - 본과 Helper가 섞여 있다.
    faceBone = _make_bone("fxFaceBone", 50)
    faceBone.parent = baseBone
    faceHelperA = rt.Point(name="fxFaceHelperA", pos=rt.Point3(50, 0, 0))
    faceHelperB = rt.Point(name="fxFaceHelperB", pos=rt.Point3(60, 0, 0))
    layerService.create_layer_from_array(
        [faceBone, faceHelperA, faceHelperB], "Fx_AddOn_Face"
    )

    # 규칙 2 대상 (미발동) - 대조군.
    armBone = _make_bone("fxArmBone", 70)
    armHelper = rt.Point(name="fxArmHelper", pos=rt.Point3(70, 0, 0))
    layerService.create_layer_from_array([armBone, armHelper], "Fx_AddOn_Arm")

    # 규칙 3 대상 - 하나는 규칙 2가 끌어온 부모에, 하나는 아무 데도 안 붙는다.
    socketOnFaceHelper = rt.Point(
        name="fxSocketOnFaceHelper", pos=rt.Point3(50, 10, 0)
    )
    socketOnFaceHelper.parent = faceHelperA
    socketOrphan = rt.Point(name="fxSocketOrphan", pos=rt.Point3(90, 0, 0))
    socketOrphan.parent = armHelper
    layerService.create_layer_from_array(
        [socketOnFaceHelper, socketOrphan], "Fx_Socket"
    )

    # 스킨 의존으로 faceBone을 2차 탐색에 처음 등장시키는 메쉬.
    # 1차 탐색은 스킨 의존 노드를 결과에 담기만 하고 방문 처리하지 않으므로,
    # 그 노드가 2차 탐색에서 처음 처리되어 규칙 판정 대상이 된다.
    slotMesh = rt.Box(
        pos=rt.Point3(110, 0, 0), length=10, width=10, height=10, name="fxSlotMesh"
    )
    skinModifier = rt.Skin()
    rt.addModifier(slotMesh, skinModifier)
    rt.select(slotMesh)
    rt.modPanel.setCurrentObject(skinModifier)
    rt.skinOps.addBone(skinModifier, faceBone, 0)
    layerService.create_layer_from_array([slotMesh], "Fx_Mesh")

    return {
        "layerService": layerService,
        "slotMesh": slotMesh,
        "outsideRoot": outsideRoot,
        "boundaryRoot": boundaryRoot,
        "boundaryMid": boundaryMid,
        "baseBone": baseBone,
        "mandatoryBone": mandatoryBone,
        "faceBone": faceBone,
        "faceHelperA": faceHelperA,
        "faceHelperB": faceHelperB,
        "armBone": armBone,
        "armHelper": armHelper,
        "socketOnFaceHelper": socketOnFaceHelper,
        "socketOrphan": socketOrphan,
    }


def _make_select(inLayerService, inPolicy=None):
    """Select 서비스를 만든다."""
    nameService = Name()
    return Select(
        nameService=nameService,
        boneService=Bone(nameService=nameService),
        layerService=inLayerService,
        inCollectPolicy=inPolicy,
    )


# 규칙 2를 발동시키는 정서. 판정은 레이어 전체, 추가는 Helper만.
def _all_or_nothing_policy():
    """규칙 2 단독 정서를 만든다."""
    return build_policy(
        inAllOrNothingLayers=["Fx_AddOn_*"],
        inAllOrNothingAddSuperClass="Helper",
    )


# ============================================================
# TC00: 라이브러리 로드 출처 어서션
# ============================================================
try:
    expectedSrc = Path(_srcPath).resolve()
    loadedFiles = {
        "nodeCollectPolicy": Path(_policyMod.__file__).resolve(),
        "nodeCollectResolver": Path(_resolverMod.__file__).resolve(),
        "dependent": Path(_dependentMod.__file__).resolve(),
        "select": Path(_selectMod.__file__).resolve(),
    }

    for moduleLabel, loadedFile in loadedFiles.items():
        reporter.assert_test(
            expectedSrc in loadedFile.parents,
            f"TC00 {moduleLabel}가 워크스페이스 소스에서 로드됨",
            f"기대 경로 하위: {expectedSrc} / 실제: {loadedFile}"
        )

    # 배포본이 선캐시되면 삭제된 Deep 메서드가 살아 있다. 로드 출처의 2차 증거다.
    reporter.assert_test(
        not hasattr(Dependent, "get_all_related"),
        "TC00-e 로드된 Dependent에 삭제된 get_all_related가 없음",
        "배포본이 로드된 신호 (Deep 메서드가 살아 있다)"
    )
except Exception as e:
    reporter.error("TC00 로드 출처 어서션", str(e))


# ============================================================
# TC01: 정서 미주입 = 확장 없음 (Dependent)
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    dependent = Dependent(layerService=fixture["layerService"])
    noPolicyResult = dependent.get_all_related_to_export([fixture["baseBone"]])
    noPolicyNames = _names(noPolicyResult)

    reporter.assert_test(
        dependent.collectPolicy is None,
        "TC01 정서 미주입 상태 확인",
        f"collectPolicy={dependent.collectPolicy}"
    )
    reporter.assert_test(
        dependent.collect_addon_helpers(noPolicyResult) == set(),
        "TC01-b 정서 미주입 -> collect_addon_helpers()가 빈 set",
        "정서가 없는데 확장 노드가 반환됨"
    )
    reporter.assert_test(
        "fxFaceHelperA" not in noPolicyNames and "fxFaceHelperB" not in noPolicyNames,
        "TC01-c 정서 미주입 -> AddOn 레이어 Helper가 들어오지 않는다",
        f"결과: {noPolicyNames}"
    )
    reporter.assert_test(
        "fxMandatoryBone" not in noPolicyNames,
        "TC01-d 정서 미주입 -> 규칙 1 대상도 들어오지 않는다",
        f"결과: {noPolicyNames}"
    )
except Exception as e:
    reporter.error("TC01 정서 미주입 확장 없음", str(e))


# ============================================================
# TC02: 정서 미주입 = 순수 의존성 결과와 동일 (Select)
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    sel = _make_select(fixture["layerService"])
    result = sel.select_dependencies([fixture["baseBone"]])
    stats = result["stats"]

    reporter.assert_test(
        stats["addon_helpers_count"] == 0,
        "TC02 정서 미주입 -> addon_helpers_count가 0",
        f"addon_helpers_count={stats['addon_helpers_count']}"
    )
    reporter.assert_test(
        stats["collected_by_rule"] == {},
        "TC02-b 정서 미주입 -> collected_by_rule이 빈 dict",
        f"collected_by_rule={stats['collected_by_rule']}"
    )
    reporter.assert_test(
        stats["total_count"] == len(result["nodes"]),
        "TC02-c total_count와 nodes 길이 일치",
        f"total_count={stats['total_count']} / nodes={len(result['nodes'])}"
    )
except Exception as e:
    reporter.error("TC02 정서 미주입 Select", str(e))


# ============================================================
# TC03: 규칙 1 단독 - 무조건 포함 + 경계 안 부모 체인
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    policy = build_policy(
        inMandatoryLayers=["Fx_Mandatory"],
        inParentChainBoundaryLayers=["Fx_Boundary"],
    )
    dependent = Dependent(
        layerService=fixture["layerService"], inCollectPolicy=policy
    )
    addedNodes = dependent.collect_addon_helpers([fixture["baseBone"]])
    addedNames = _names(addedNodes)

    reporter.assert_test(
        "fxMandatoryBone" in addedNames,
        "TC03 규칙 1 - 의존성과 무관하게 대상이 들어온다",
        f"추가: {addedNames}"
    )
    reporter.assert_test(
        "fxBoundaryMid" in addedNames and "fxBoundaryRoot" in addedNames,
        "TC03-b 경계 안 부모가 체인으로 딸려 들어온다",
        f"추가: {addedNames}"
    )
    reporter.assert_test(
        "fxOutsideRoot" not in addedNames,
        "TC03-c 경계 밖 부모는 끌려오지 않는다",
        f"추가: {addedNames}"
    )
    reporter.assert_test(
        "fxFaceHelperA" not in addedNames,
        "TC03-d 규칙 1 단독 -> 규칙 2 대상은 들어오지 않는다",
        f"추가: {addedNames}"
    )
except Exception as e:
    reporter.error("TC03 규칙 1 단독", str(e))


# ============================================================
# TC04: 규칙 2 단독 - 전부-또는-전무 + Helper 필터 + 레이어 독립 판정
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    dependent = Dependent(
        layerService=fixture["layerService"],
        inCollectPolicy=_all_or_nothing_policy(),
    )
    # 판정에는 Face 레이어의 본이 걸린다(Helper가 아니다).
    addedNames = _names(dependent.collect_addon_helpers([fixture["faceBone"]]))

    reporter.assert_test(
        "fxFaceHelperA" in addedNames and "fxFaceHelperB" in addedNames,
        "TC04 규칙 2 - 본이 판정을 발동시키고 Helper가 추가된다",
        f"추가: {addedNames}"
    )
    reporter.assert_test(
        "fxArmHelper" not in addedNames,
        "TC04-b 레이어별 독립 판정 - 걸리지 않은 레이어는 확장되지 않는다",
        f"추가: {addedNames}"
    )
    reporter.assert_test(
        "fxArmBone" not in addedNames,
        "TC04-c 미발동 레이어의 본도 들어오지 않는다",
        f"추가: {addedNames}"
    )
except Exception as e:
    reporter.error("TC04 규칙 2 단독", str(e))


# ============================================================
# TC05: 규칙 3 단독 - 부모 조건부
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    policy = build_policy(inParentConditionalLayers=["Fx_Socket"])
    dependent = Dependent(
        layerService=fixture["layerService"], inCollectPolicy=policy
    )

    # faceHelperA가 집합에 있으면 그 자식 소켓이 따라온다.
    addedWithParent = _names(
        dependent.collect_addon_helpers([fixture["faceHelperA"]])
    )
    # 아무 부모도 없는 상태면 소켓이 따라오지 않는다.
    addedWithoutParent = _names(
        dependent.collect_addon_helpers([fixture["baseBone"]])
    )

    reporter.assert_test(
        addedWithParent == ["fxSocketOnFaceHelper"],
        "TC05 규칙 3 - 부모가 집합에 있으면 조건부 노드가 따라온다",
        f"추가: {addedWithParent}"
    )
    reporter.assert_test(
        addedWithoutParent == [],
        "TC05-b 규칙 3 - 부모가 없으면 발동하지 않는다",
        f"추가: {addedWithoutParent}"
    )
except Exception as e:
    reporter.error("TC05 규칙 3 단독", str(e))


# ============================================================
# TC06: 규칙 3종 동시 - 규칙 2가 끌어온 노드에 규칙 3이 걸리는 경로
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    policy = build_policy(
        inMandatoryLayers=["Fx_Mandatory"],
        inAllOrNothingLayers=["Fx_AddOn_*"],
        inAllOrNothingAddSuperClass="Helper",
        inParentConditionalLayers=["Fx_Socket"],
        inParentChainBoundaryLayers=["Fx_Boundary"],
    )
    sel = _make_select(fixture["layerService"], policy)
    collectedNodes, byRule = sel.collect_by_rule([fixture["faceBone"]])
    collectedNames = _names(collectedNodes)

    reporter.assert_test(
        "fxMandatoryBone" in collectedNames,
        "TC06 규칙 1이 발동",
        f"추가: {collectedNames}"
    )
    reporter.assert_test(
        "fxFaceHelperA" in collectedNames and "fxFaceHelperB" in collectedNames,
        "TC06-b 규칙 2가 발동 (Helper만)",
        f"추가: {collectedNames}"
    )
    reporter.assert_test(
        "fxSocketOnFaceHelper" in collectedNames,
        "TC06-c 규칙 2가 끌어온 Helper에 규칙 3이 걸린다 (규칙 간 상호작용)",
        f"추가: {collectedNames}"
    )
    reporter.assert_test(
        "fxSocketOrphan" not in collectedNames,
        "TC06-d 미발동 레이어에 매달린 조건부 노드는 들어오지 않는다",
        f"추가: {collectedNames}"
    )
    reporter.assert_test(
        "fxOutsideRoot" not in collectedNames,
        "TC06-e 경계 밖 부모는 여전히 제외된다",
        f"추가: {collectedNames}"
    )
    reporter.assert_test(
        len(byRule.get(RULE_MANDATORY, [])) >= 1
        and len(byRule.get(RULE_ALL_OR_NOTHING, [])) >= 1
        and len(byRule.get(RULE_PARENT_CONDITIONAL, [])) >= 1
        and len(byRule.get(RULE_PARENT_CHAIN, [])) >= 1,
        "TC06-f byRule에 네 규칙 모두 기여가 기록된다",
        f"byRule 집계: "
        f"{ {ruleKey: len(handles) for ruleKey, handles in byRule.items()} }"
    )
except Exception as e:
    reporter.error("TC06 규칙 3종 동시", str(e))


# ============================================================
# TC07: select_dependencies() stats에 규칙별 집계가 실린다
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    sel = _make_select(fixture["layerService"], _all_or_nothing_policy())
    # 메쉬에서 출발하면 faceBone이 스킨 의존으로 2차 탐색에 등장해 규칙 2가 걸린다.
    result = sel.select_dependencies([fixture["slotMesh"]])
    stats = result["stats"]
    nodeNames = _names(result["nodes"])

    reporter.assert_test(
        stats["addon_helpers_count"] >= 2,
        "TC07 addon_helpers_count가 규칙 확장분을 센다 (하위 호환 키)",
        f"addon_helpers_count={stats['addon_helpers_count']}"
    )
    reporter.assert_test(
        stats["collected_by_rule"].get(RULE_ALL_OR_NOTHING, 0) >= 2,
        "TC07-b collected_by_rule에 규칙 2 기여가 기록된다",
        f"collected_by_rule={stats['collected_by_rule']}"
    )
    reporter.assert_test(
        "fxFaceHelperA" in nodeNames and "fxFaceHelperB" in nodeNames,
        "TC07-c 최종 nodes에 규칙 확장분이 결합된다",
        f"nodes: {nodeNames}"
    )
    reporter.assert_test(
        stats["total_count"] == len(result["nodes"]),
        "TC07-d total_count와 nodes 길이 일치",
        f"total_count={stats['total_count']} / nodes={len(result['nodes'])}"
    )
except Exception as e:
    reporter.error("TC07 select_dependencies stats", str(e))


# ============================================================
# TC08: get_all_related_to_export()에 규칙 확장이 실린다
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    dependent = Dependent(
        layerService=fixture["layerService"],
        inCollectPolicy=_all_or_nothing_policy(),
    )
    exportNames = _names(
        dependent.get_all_related_to_export([fixture["slotMesh"]])
    )

    reporter.assert_test(
        "fxSlotMesh" in exportNames and "fxFaceBone" in exportNames,
        "TC08 시작 노드와 스킨 의존 노드가 결과에 포함",
        f"결과: {exportNames}"
    )
    reporter.assert_test(
        "fxFaceHelperA" in exportNames and "fxFaceHelperB" in exportNames,
        "TC08-b 규칙 확장분이 익스포트 결과에 결합된다",
        f"결과: {exportNames}"
    )
    reporter.assert_test(
        len(exportNames) == len(set(exportNames)),
        "TC08-c 결과에 중복이 없다",
        f"결과: {exportNames}"
    )
except Exception as e:
    reporter.error("TC08 get_all_related_to_export 확장", str(e))


# ============================================================
# TC09: header.configure_node_collect_policy()가 양쪽에 배선한다
# ============================================================
try:
    _reset_scene()

    jal = _headerMod.get_pyjallibmaxheader()

    policy = _all_or_nothing_policy()
    jal.configure_node_collect_policy(policy)

    reporter.assert_test(
        jal.dependent.collectPolicy is policy,
        "TC09 dependent에 정서가 배선된다",
        f"dependent.collectPolicy={getattr(jal.dependent, 'collectPolicy', 'MISSING')}"
    )
    reporter.assert_test(
        jal.sel.collectPolicy is policy,
        "TC09-b sel에 같은 정서가 함께 배선된다 (한쪽 누락 방지)",
        f"sel.collectPolicy={getattr(jal.sel, 'collectPolicy', 'MISSING')}"
    )
    reporter.assert_test(
        jal.dependent.collectPolicy is jal.sel.collectPolicy,
        "TC09-c 두 서비스가 같은 정서 객체를 공유한다",
        "두 서비스의 정서가 다른 객체"
    )

    # None을 주면 규칙이 해제된다.
    jal.configure_node_collect_policy(None)
    reporter.assert_test(
        jal.dependent.collectPolicy is None and jal.sel.collectPolicy is None,
        "TC09-d None 배선으로 규칙을 해제할 수 있다",
        f"dependent={jal.dependent.collectPolicy} / sel={jal.sel.collectPolicy}"
    )
except Exception as e:
    reporter.error("TC09 header 배선", str(e))


# ============================================================
# TC10: 미해석 레이어 정서 - 확장 없이 정상 종료
# ============================================================
try:
    _reset_scene()
    fixture = _build_fixture_scene()

    policy = build_policy(
        inMandatoryLayers=["NoSuchLayer_A"],
        inAllOrNothingLayers=["NoSuchLayer_B_*"],
        inParentConditionalLayers=["NoSuchLayer_C"],
        inParentChainBoundaryLayers=["NoSuchLayer_D"],
    )
    dependent = Dependent(
        layerService=fixture["layerService"], inCollectPolicy=policy
    )
    addedNames = _names(dependent.collect_addon_helpers([fixture["baseBone"]]))
    exportNames = _names(dependent.get_all_related_to_export([fixture["baseBone"]]))

    reporter.assert_test(
        addedNames == [],
        "TC10 미해석 레이어 정서 -> 확장 0개",
        f"추가: {addedNames}"
    )
    reporter.assert_test(
        "fxBaseBone" in exportNames,
        "TC10-b 미해석 레이어에도 의존성 탐색은 정상 동작한다",
        f"결과: {exportNames}"
    )
except Exception as e:
    reporter.error("TC10 미해석 레이어 정서", str(e))


# ============================================================
# 결과 요약
# ============================================================
reporter.summary()
reporter.close()
