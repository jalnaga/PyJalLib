#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NodeCollectResolver 어댑터 단독 스모크 (Type C 헤드레스 실행).

Phase 2의 어댑터는 pymxs 의존이라 콘솔 pytest로 검증할 수 없다. 그래서 어댑터
단위를 여기서 종결한다 - 서비스 배선을 거치지 않고 ``NodeCollectResolver``를 직접
만들어, 레이어 패턴 해석(대소문자 무시)과 수퍼클래스 필터가 실제 씬에서 동작하는지
확인한다. 서비스 통합 검증은 다른 층이므로 별 스위트(``test_node_collect_policy_max``)에
둔다.

테스트 유형: Type C (3dsmaxbatch.exe 헤드레스 실행 + 로그 분석)
실행 방법:
    uv run python tests/run_max_tests.py
로그 파일: tests/logs/test_NodeCollectResolver.log
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


# 엔진을 먼저 등록해야 어댑터의 from-import가 강제 로드본을 집는다.
_policyMod = _force_load(
    "pyjallib.max.nodeCollectPolicy", "pyjallib/max/nodeCollectPolicy.py"
)
_resolverMod = _force_load(
    "pyjallib.max.nodeCollectResolver", "pyjallib/max/nodeCollectResolver.py"
)

NodeCollectResolver = _resolverMod.NodeCollectResolver
build_policy = _resolverMod.build_policy
ADD_KEY = _policyMod.ADD_KEY
TRIGGER_KEY = _policyMod.TRIGGER_KEY
RULE_ALL_OR_NOTHING = _policyMod.RULE_ALL_OR_NOTHING
RULE_MANDATORY = _policyMod.RULE_MANDATORY
RULE_PARENT_CHAIN = _policyMod.RULE_PARENT_CHAIN

from pyjallib.max.layer import Layer  # noqa: E402

# -- TestReporter 초기화 -------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
reporter = TestReporter("NodeCollectResolver", LOG_DIR)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _make_resolver():
    """NodeCollectResolver 인스턴스를 만든다."""
    return NodeCollectResolver(layerService=Layer())


def _make_bone(inName, inStartX):
    """이름을 지정한 본을 만든다."""
    bone = rt.BoneSys.createBone(
        rt.Point3(inStartX, 0, 0),
        rt.Point3(inStartX + 10, 0, 0),
        rt.Point3(0, 0, 1),
    )
    bone.name = inName
    return bone


def _handles(inNodes):
    """노드 리스트를 핸들 집합으로 바꾼다."""
    return {int(rt.getHandleByAnim(node)) for node in inNodes}


def _names(inNodes):
    """노드 리스트를 이름 리스트로 바꾼다."""
    return sorted(str(node.name) for node in inNodes)


# ============================================================
# TC00: 라이브러리 로드 출처 어서션
# ============================================================
try:
    expectedSrc = Path(_srcPath).resolve()
    policyFile = Path(_policyMod.__file__).resolve()
    resolverFile = Path(_resolverMod.__file__).resolve()

    reporter.assert_test(
        expectedSrc in policyFile.parents,
        "TC00 nodeCollectPolicy가 워크스페이스 소스에서 로드됨",
        f"기대 경로 하위: {expectedSrc} / 실제: {policyFile}"
    )
    reporter.assert_test(
        expectedSrc in resolverFile.parents,
        "TC00-b nodeCollectResolver가 워크스페이스 소스에서 로드됨",
        f"기대 경로 하위: {expectedSrc} / 실제: {resolverFile}"
    )
    reporter.assert_test(
        sys.modules["pyjallib.max.nodeCollectPolicy"] is _policyMod,
        "TC00-c 어댑터가 참조하는 엔진이 강제 로드본과 동일 객체",
        "sys.modules 등록본이 강제 로드본과 다름"
    )
except Exception as e:
    reporter.error("TC00 로드 출처 어서션", str(e))


# ============================================================
# TC01: 정서 없음 / 빈 정서 -> resolve()가 None
# ============================================================
try:
    _reset_scene()
    resolver = _make_resolver()

    reporter.assert_test(
        resolver.resolve(None) is None,
        "TC01 정서 None -> resolve() None",
        "None 정서인데 None이 아닌 값 반환"
    )
    reporter.assert_test(
        resolver.resolve(build_policy()) is None,
        "TC01-b 빈 정서 -> resolve() None",
        "빈 정서인데 None이 아닌 값 반환"
    )
    reporter.assert_test(
        resolver.resolve(
            build_policy(inParentChainBoundaryLayers=["Anything_*"])
        ) is None,
        "TC01-c 경계만 지정한 정서 -> resolve() None (경계는 규칙이 아니다)",
        "경계만 있는 정서가 확장 대상으로 취급됨"
    )
except Exception as e:
    reporter.error("TC01 빈 정서 resolve", str(e))


# ============================================================
# TC02: 레이어 패턴 대소문자 무시 해석
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    # 씬 레이어 이름은 소문자로 만든다. 정서의 패턴은 대문자로 준다.
    lowerBone = _make_bone("lowerCaseLayerBone", 0)
    layerService.create_layer_from_array([lowerBone], "nodecollect_addon_face")

    resolved = resolver.resolve(
        build_policy(inMandatoryLayers=["NodeCollect_AddOn_*"])
    )

    reporter.assert_test(
        resolved is not None,
        "TC02 대소문자 다른 패턴이 해석됨",
        "resolve()가 None을 반환 (패턴 해석 실패)"
    )
    if resolved is not None:
        reporter.assert_test(
            _handles([lowerBone]) == resolved["mandatoryHandles"],
            "TC02-b 소문자 레이어의 노드가 규칙 1 대상으로 수집",
            f"기대: {_handles([lowerBone])} / 실제: {resolved['mandatoryHandles']}"
        )
except Exception as e:
    reporter.error("TC02 대소문자 무시 해석", str(e))


# ============================================================
# TC03: 미해석 레이어는 규칙 미발동 (조용히 넘기지 않고 WARNING)
# ============================================================
try:
    _reset_scene()
    resolver = _make_resolver()
    strayBone = _make_bone("strayBone", 0)

    resolved = resolver.resolve(
        build_policy(inMandatoryLayers=["NoSuchLayer_*"])
    )

    reporter.assert_test(
        resolved is not None,
        "TC03 미해석 레이어에도 resolve()는 dict 반환",
        "미해석 레이어에서 None 반환 (규칙 없음과 구분되지 않음)"
    )
    if resolved is not None:
        reporter.assert_test(
            len(resolved["mandatoryHandles"]) == 0,
            "TC03-b 미해석 레이어 -> 규칙 대상 0개",
            f"대상 수: {len(resolved['mandatoryHandles'])}"
        )
        addedNodes, byRule = resolver.collect_additions([strayBone], resolved)
        reporter.assert_test(
            len(addedNodes) == 0,
            "TC03-c 미해석 레이어 -> 추가 노드 0개",
            f"추가된 노드: {_names(addedNodes)}"
        )
except Exception as e:
    reporter.error("TC03 미해석 레이어", str(e))


# ============================================================
# TC04: 규칙 2의 수퍼클래스 필터 - trigger는 전부, add는 Helper만
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    addonBone = _make_bone("addonBone", 0)
    addonHelper1 = rt.Point(name="addonHelper1", pos=rt.Point3(0, 0, 0))
    addonHelper2 = rt.Point(name="addonHelper2", pos=rt.Point3(10, 0, 0))
    layerService.create_layer_from_array(
        [addonBone, addonHelper1, addonHelper2], "Rig_AddOn_Face"
    )

    resolved = resolver.resolve(
        build_policy(
            inAllOrNothingLayers=["Rig_AddOn_*"],
            inAllOrNothingAddSuperClass="Helper",
        )
    )

    reporter.assert_test(
        resolved is not None,
        "TC04 규칙 2 정서 해석 성공",
        "resolve()가 None 반환"
    )
    if resolved is not None:
        layerEntries = resolved["allOrNothingByLayer"]
        reporter.assert_test(
            len(layerEntries) == 1,
            "TC04-b 레이어 1개가 규칙 2 항목으로 해석",
            f"항목 수: {len(layerEntries)}, 키: {list(layerEntries.keys())}"
        )
        entry = list(layerEntries.values())[0] if layerEntries else {}
        triggerHandles = entry.get(TRIGGER_KEY, set())
        addHandles = entry.get(ADD_KEY, set())

        reporter.assert_test(
            triggerHandles == _handles([addonBone, addonHelper1, addonHelper2]),
            "TC04-c trigger 집합에는 필터가 걸리지 않는다 (본 포함)",
            f"기대 3개 / 실제 {len(triggerHandles)}개"
        )
        reporter.assert_test(
            addHandles == _handles([addonHelper1, addonHelper2]),
            "TC04-d add 집합에는 Helper만 남는다",
            f"기대 2개 / 실제 {len(addHandles)}개"
        )
        reporter.assert_test(
            _handles([addonBone]).isdisjoint(addHandles),
            "TC04-e add 집합에 본이 들어가지 않는다",
            f"본 핸들이 add에 포함됨: {addHandles}"
        )
except Exception as e:
    reporter.error("TC04 수퍼클래스 필터", str(e))


# ============================================================
# TC05: 필터 미지정이면 trigger == add
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    plainBone = _make_bone("plainBone", 0)
    plainHelper = rt.Point(name="plainHelper", pos=rt.Point3(0, 0, 0))
    layerService.create_layer_from_array([plainBone, plainHelper], "Plain_AddOn")

    resolved = resolver.resolve(build_policy(inAllOrNothingLayers=["Plain_AddOn"]))

    if resolved is None:
        reporter.assert_test(False, "TC05 필터 미지정 정서 해석", "resolve()가 None")
    else:
        entry = list(resolved["allOrNothingByLayer"].values())[0]
        reporter.assert_test(
            entry[TRIGGER_KEY] == entry[ADD_KEY],
            "TC05 필터 미지정 -> trigger와 add가 같은 집합",
            f"trigger={entry[TRIGGER_KEY]} / add={entry[ADD_KEY]}"
        )
        reporter.assert_test(
            entry[ADD_KEY] == _handles([plainBone, plainHelper]),
            "TC05-b 필터 미지정 -> 레이어 전체가 추가 대상",
            f"기대 2개 / 실제 {len(entry[ADD_KEY])}개"
        )
except Exception as e:
    reporter.error("TC05 필터 미지정", str(e))


# ============================================================
# TC06: 비재귀 조회 - 자식 레이어가 부모 레이어 규칙에 휩쓸리지 않는다
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    parentLayerBone = _make_bone("parentLayerBone", 0)
    childLayerBone = _make_bone("childLayerBone", 20)
    layerService.create_layer_from_array([parentLayerBone], "Collect_Parent")
    layerService.create_layer_from_array([childLayerBone], "Collect_Child")
    layerService.set_parent_layer("Collect_Child", "Collect_Parent")

    resolved = resolver.resolve(build_policy(inMandatoryLayers=["Collect_Parent"]))

    if resolved is None:
        reporter.assert_test(False, "TC06 비재귀 조회 정서 해석", "resolve()가 None")
    else:
        reporter.assert_test(
            resolved["mandatoryHandles"] == _handles([parentLayerBone]),
            "TC06 비재귀 조회 - 자식 레이어 노드가 포함되지 않는다",
            f"기대 1개(parentLayerBone) / 실제 {len(resolved['mandatoryHandles'])}개"
        )
except Exception as e:
    reporter.error("TC06 비재귀 조회", str(e))


# ============================================================
# TC07: expand() - AddOn Helper 동작 재현 (본이 발동, Helper만 추가)
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    triggerBone = _make_bone("triggerBone", 0)
    helperA = rt.Point(name="helperA", pos=rt.Point3(0, 0, 0))
    helperB = rt.Point(name="helperB", pos=rt.Point3(10, 0, 0))
    layerService.create_layer_from_array(
        [triggerBone, helperA, helperB], "Rig_AddOn_Arm"
    )

    policy = build_policy(
        inAllOrNothingLayers=["Rig_AddOn_*"],
        inAllOrNothingAddSuperClass="Helper",
    )
    expandedNodes = resolver.expand([triggerBone], policy)

    reporter.assert_test(
        _names(expandedNodes) == ["helperA", "helperB", "triggerBone"],
        "TC07 본이 규칙 2를 발동시키고 Helper 2개가 추가된다",
        f"결과: {_names(expandedNodes)}"
    )
    reporter.assert_test(
        expandedNodes[0] is triggerBone,
        "TC07-b 원본 노드가 앞에 유지된다",
        f"첫 노드: {expandedNodes[0].name if expandedNodes else None}"
    )
except Exception as e:
    reporter.error("TC07 expand AddOn Helper 재현", str(e))


# ============================================================
# TC08: expand() - 판정 집합과 겹치지 않으면 발동하지 않는다
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    outsideBone = _make_bone("outsideBone", 40)
    addonBone = _make_bone("insideAddonBone", 0)
    addonHelper = rt.Point(name="insideAddonHelper", pos=rt.Point3(0, 0, 0))
    layerService.create_layer_from_array(
        [addonBone, addonHelper], "Rig_AddOn_Leg"
    )

    policy = build_policy(
        inAllOrNothingLayers=["Rig_AddOn_*"],
        inAllOrNothingAddSuperClass="Helper",
    )
    expandedNodes = resolver.expand([outsideBone], policy)

    reporter.assert_test(
        _names(expandedNodes) == ["outsideBone"],
        "TC08 판정 교집합이 없으면 확장이 없다",
        f"결과: {_names(expandedNodes)}"
    )
except Exception as e:
    reporter.error("TC08 판정 미발동", str(e))


# ============================================================
# TC09: 부모 체인 경계 - 경계 레이어 안에서만 부모를 끌어온다
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    # 계층: outsideRoot(경계 밖) <- boundaryRoot <- boundaryMid <- mandatoryTip
    outsideRoot = _make_bone("outsideRoot", 0)
    boundaryRoot = _make_bone("boundaryRoot", 10)
    boundaryMid = _make_bone("boundaryMid", 20)
    mandatoryTip = _make_bone("mandatoryTip", 30)

    boundaryRoot.parent = outsideRoot
    boundaryMid.parent = boundaryRoot
    mandatoryTip.parent = boundaryMid

    layerService.create_layer_from_array([outsideRoot], "Chain_Outside")
    layerService.create_layer_from_array(
        [boundaryRoot, boundaryMid], "Chain_Boundary"
    )
    layerService.create_layer_from_array([mandatoryTip], "Chain_Mandatory")

    policy = build_policy(
        inMandatoryLayers=["Chain_Mandatory"],
        inParentChainBoundaryLayers=["Chain_Boundary"],
    )
    resolved = resolver.resolve(policy)
    addedNodes, byRule = resolver.collect_additions([], resolved)

    reporter.assert_test(
        _names(addedNodes) == ["boundaryMid", "boundaryRoot", "mandatoryTip"],
        "TC09 경계 안 부모만 딸려 들어온다 (outsideRoot 제외)",
        f"결과: {_names(addedNodes)}"
    )
    reporter.assert_test(
        len(byRule[RULE_MANDATORY]) == 1,
        "TC09-b 규칙 1이 직접 지목한 것은 1개",
        f"규칙 1 추가: {byRule[RULE_MANDATORY]}"
    )
    reporter.assert_test(
        len(byRule[RULE_PARENT_CHAIN]) == 2,
        "TC09-c 부모 체인으로 2개가 딸려 들어옴",
        f"부모 체인 추가: {byRule[RULE_PARENT_CHAIN]}"
    )
except Exception as e:
    reporter.error("TC09 부모 체인 경계", str(e))


# ============================================================
# TC10: 부모 조건부 규칙이 경계 미지정에서도 발동한다
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    baseBone = _make_bone("condBaseBone", 0)
    socketBone = _make_bone("condSocketBone", 10)
    orphanSocket = _make_bone("condOrphanSocket", 30)
    socketBone.parent = baseBone

    layerService.create_layer_from_array([baseBone], "Cond_Base")
    layerService.create_layer_from_array(
        [socketBone, orphanSocket], "Cond_Socket"
    )

    # 경계 레이어를 지정하지 않는다. 그래도 규칙 3은 부모 맵을 찾아 발동해야 한다.
    policy = build_policy(inParentConditionalLayers=["Cond_Socket"])
    expandedNodes = resolver.expand([baseBone], policy)

    reporter.assert_test(
        _names(expandedNodes) == ["condBaseBone", "condSocketBone"],
        "TC10 경계 미지정에서도 부모 조건부 규칙이 발동한다",
        f"결과: {_names(expandedNodes)}"
    )
    reporter.assert_test(
        "condOrphanSocket" not in _names(expandedNodes),
        "TC10-b 부모가 집합에 없는 조건부 노드는 들어오지 않는다",
        f"결과: {_names(expandedNodes)}"
    )
except Exception as e:
    reporter.error("TC10 부모 조건부 경계 미지정", str(e))


# ============================================================
# TC11: 해석 실패 수퍼클래스 이름 -> 필터 없이 진행
# ============================================================
try:
    _reset_scene()
    layerService = Layer()
    resolver = NodeCollectResolver(layerService=layerService)

    mixBone = _make_bone("mixBone", 0)
    mixHelper = rt.Point(name="mixHelper", pos=rt.Point3(0, 0, 0))
    layerService.create_layer_from_array([mixBone, mixHelper], "Mix_AddOn")

    policy = build_policy(
        inAllOrNothingLayers=["Mix_AddOn"],
        inAllOrNothingAddSuperClass="NoSuchSuperClassName",
    )
    resolved = resolver.resolve(policy)

    if resolved is None:
        reporter.assert_test(
            False, "TC11 해석 실패 수퍼클래스 - resolve 진행", "resolve()가 None"
        )
    else:
        entry = list(resolved["allOrNothingByLayer"].values())[0]
        reporter.assert_test(
            entry[ADD_KEY] == entry[TRIGGER_KEY],
            "TC11 수퍼클래스 해석 실패 -> 필터 없이 진행 (add == trigger)",
            f"trigger={entry[TRIGGER_KEY]} / add={entry[ADD_KEY]}"
        )
except Exception as e:
    reporter.error("TC11 수퍼클래스 해석 실패", str(e))


# ============================================================
# 결과 요약
# ============================================================
reporter.summary()
reporter.close()
