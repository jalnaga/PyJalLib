#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
실기 씬 호환성 검사 - 현행 하드코딩 로직과 신 규칙 엔진의 결과 집합 일치 확인.

이관이 **동작 보존**인지를 합성 씬이 아닌 실기 씬으로 증명한다. 같은 씬·같은 시작
노드에 대해 두 경로의 결과 핸들 집합을 각각 산출해 비교한다.

1. **현행 로직 재현:** 이관 전 ``collect_addon_helpers``의 구현을 이 파일 안에서
   그대로 재현한다(``_legacy_collect_addon_helpers``). 삭제된 코드를 라이브러리에
   남겨 두지 않고도 비교 기준을 확보하기 위함이다 - 기준이 라이브러리에 있으면
   "제거했다"는 주장과 어긋난다.
2. **신 엔진:** ``Rig_AddOn_*`` 상당 정서를 주입한 ``Dependent.collect_addon_helpers``.

불일치가 나오면 양방향 차집합을 **노드 이름으로** 보고한다. 개수만 보고하면 어느
노드가 어긋났는지 알 수 없어 원인에 도달할 수 없다.

씬 경로는 환경변수 ``PYJALLIB_COMPAT_SCENE``로 받는다. 미지정이면 씬 없이 판정할 수
없으므로 SKIP 사유를 로그에 남기고 검사 블록을 건너뛴다 - 실패로 만들지 않는다(씬
제공은 마스터의 결정 사항이고, 실패로 올리면 다른 스위트의 회귀 신호를 가린다).
시작 노드는 ``PYJALLIB_COMPAT_START_NODES``로 이름을 지정할 수 있고, 미지정이면 씬에
저장된 선택 -> 씬 전체 지오메트리 순으로 폴백한다.

테스트 유형: Type C (3dsmaxbatch.exe 헤드레스 실행 + 로그 분석)
실행 방법:
    set PYJALLIB_COMPAT_SCENE=<씬 경로>
    uv run python tests/run_max_tests.py
로그 파일: tests/logs/test_AddonCompatRealScene.log
"""

import os
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
_dependentMod = _force_load("pyjallib.max.dependent", "pyjallib/max/dependent.py")

Dependent = _dependentMod.Dependent
build_policy = _resolverMod.build_policy

from pyjallib.max.layer import Layer  # noqa: E402

# -- TestReporter 초기화 -------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
reporter = TestReporter("AddonCompatRealScene", LOG_DIR)


def _log_info(inMessage):
    """판정이 아닌 관측 정보를 로그에 남긴다.

    ``TestReporter``에는 정보성 기록 API가 없고, ``assert_test(True, ...)``로 대신하면
    통과 개수가 부풀어 TC 집계가 흐려진다. 그래서 리포터의 로거에 직접 쓴다 - 이
    스위트의 판정은 집합 일치 하나이고, 나머지는 사람이 읽을 관측치다.

    Args:
        inMessage (str): 기록할 메시지
    """
    reporter._logger.info(f"INFO: {inMessage}")

SCENE_PATH_ENV = "PYJALLIB_COMPAT_SCENE"
# 시작 노드를 이름으로 지정할 수 있다. 미지정이면 씬에 저장된 선택을 쓴다.
START_NODES_ENV = "PYJALLIB_COMPAT_START_NODES"
# 비교에 쓸 레이어 접두를 바꿀 수 있다. 규약이 바뀐 씬에서 현행 접두가 아무것도
# 잡지 못하면 비교가 공허해지므로, 실제로 노드가 있는 접두로 바꿔 재측정해야 한다.
LAYER_PREFIX_ENV = "PYJALLIB_COMPAT_LAYER_PREFIX"

# 비교 기준이 되는 현행 판정 접두. 이관 전 라이브러리가 하드코딩하고 있던 값이다.
_LEGACY_LAYER_PREFIX = os.environ.get(LAYER_PREFIX_ENV, "").strip() or "Rig_AddOn_"

# 신 엔진에 줄 동등 정서. 접두 판정을 와일드카드 패턴으로 옮긴 것이다.
_EQUIVALENT_LAYER_PATTERN = _LEGACY_LAYER_PREFIX + "*"


def _legacy_collect_addon_helpers(inDeps, inLayerService):
    """이관 전 ``collect_addon_helpers`` 구현을 그대로 재현한다.

    비교 기준이므로 **의도적으로 원본 그대로 둔다.** 대소문자를 구분하는
    ``startswith``와 ``rt.superClassOf`` 비교까지 원본과 같아야 비교가 의미를 갖는다.

    Args:
        inDeps (list[rt.Node]): dependency 노드 리스트
        inLayerService (Layer): 레이어 서비스

    Returns:
        set[rt.Node]: 수집된 AddOn Helper 노드 set
    """
    addonHelper = set()
    processedLayers = set()
    helperClass = rt.helper
    superClassOf = rt.superClassOf

    for item in inDeps:
        layerName = item.layer.name
        if layerName.startswith(_LEGACY_LAYER_PREFIX) and layerName not in processedLayers:
            processedLayers.add(layerName)
            layerNodes = inLayerService.get_nodes_by_layername(layerName)
            for obj in layerNodes or []:
                if superClassOf(obj) == helperClass:
                    addonHelper.add(obj)

    return addonHelper


def _handle_set(inNodes):
    """노드 모음을 핸들 집합으로 바꾼다.

    pymxs 노드 래퍼는 같은 노드라도 조회 경로에 따라 다른 객체가 되므로, 집합 비교는
    반드시 핸들로 한다.

    Args:
        inNodes: 노드 모음

    Returns:
        set[int]: 노드 핸들 집합
    """
    return {int(rt.getHandleByAnim(node)) for node in inNodes}


def _describe_handles(inHandles):
    """핸들 집합을 노드 이름 리스트로 바꾼다.

    차집합 보고에 쓴다. 개수만 보고하면 원인에 도달할 수 없으므로 이름을 낸다.

    Args:
        inHandles (set[int]): 노드 핸들 집합

    Returns:
        list[str]: 정렬된 노드 이름 리스트 (복원 실패는 핸들 번호로 표기)
    """
    describedNames = []
    for nodeHandle in sorted(inHandles):
        try:
            node = rt.getAnimByHandle(nodeHandle)
        except Exception:
            node = None
        if node is not None and rt.isValidNode(node):
            describedNames.append(str(node.name))
        else:
            describedNames.append(f"<복원 실패 handle={nodeHandle}>")
    return describedNames


def _resolve_start_nodes():
    """비교에 쓸 시작 노드를 결정한다.

    환경변수로 이름을 받으면 그것을, 없으면 씬에 저장된 선택을, 그것도 없으면
    모든 지오메트리를 쓴다. 실기 씬의 익스포트 대상이 보통 스키닝된 메쉬이므로
    지오메트리 폴백이 현실적이다.

    Returns:
        tuple[list, str]: (시작 노드 리스트, 결정 근거 설명)
    """
    nameText = os.environ.get(START_NODES_ENV, "").strip()
    if nameText:
        requestedNames = [part.strip() for part in nameText.split(",") if part.strip()]
        foundNodes = []
        missingNames = []
        for nodeName in requestedNames:
            node = rt.getNodeByName(nodeName)
            if node is None:
                missingNames.append(nodeName)
            else:
                foundNodes.append(node)
        reason = f"환경변수 {START_NODES_ENV} 지정 ({len(foundNodes)}개 확인"
        if missingNames:
            reason += f", 미발견: {missingNames}"
        reason += ")"
        return foundNodes, reason

    selectedNodes = list(rt.selection)
    if selectedNodes:
        return selectedNodes, f"씬에 저장된 선택 {len(selectedNodes)}개"

    geometryNodes = list(rt.geometry)
    return geometryNodes, f"폴백: 씬의 전체 지오메트리 {len(geometryNodes)}개"


# ============================================================
# TC00: 씬 제공 여부 확인
# ============================================================
scenePathText = os.environ.get(SCENE_PATH_ENV, "").strip()
scenePath = Path(scenePathText) if scenePathText else None

# 씬이 없으면 이후 블록을 전부 건너뛴다. sys.exit()로 빠져나가지 않는 이유는
# 3dsmaxbatch 안에서 조기 종료가 로그 마커를 남기지 못하고 배치 종료 코드를
# 흐리기 때문이다.
sceneReady = False

if scenePath is None:
    _log_info(
        f"실기 씬이 제공되지 않았습니다({SCENE_PATH_ENV} 미설정). 호환성 검사를 "
        f"건너뜁니다 - 합성 씬 검증(NodeCollectPolicyMax)까지가 이번 실행의 근거입니다."
    )
else:
    try:
        sceneReady = scenePath.exists()
        reporter.assert_test(
            sceneReady,
            f"TC00 실기 씬 파일 존재 ({scenePath.name})",
            f"경로를 찾을 수 없습니다: {scenePath}"
        )
    except Exception as e:
        reporter.error("TC00 실기 씬 존재 확인", str(e))


# ============================================================
# TC01: 씬 로드 + 시작 노드 결정
# ============================================================
startNodes = []
if sceneReady:
    try:
        loaded = rt.loadMaxFile(str(scenePath), useFileUnits=True, quiet=True)
        reporter.assert_test(
            loaded is True,
            "TC01 실기 씬 로드",
            f"loadMaxFile 반환값: {loaded}"
        )

        startNodes, startReason = _resolve_start_nodes()
        _log_info(f"시작 노드 결정 근거: {startReason}")
        reporter.assert_test(
            len(startNodes) > 0,
            "TC01-b 시작 노드가 1개 이상 결정됨",
            f"시작 노드 0개 ({startReason})"
        )
    except Exception as e:
        reporter.error("TC01 씬 로드 및 시작 노드 결정", str(e))


# ============================================================
# TC02: 두 경로의 결과 집합 일치
# ============================================================


def _compare_collect_paths():
    """현행 로직과 신 엔진의 결과 핸들 집합을 비교해 판정한다.

    두 경로에 **같은 입력**을 준다. 의존성 탐색은 한 번만 돌려 결과를 공유한다 -
    두 번 돌리면 그 사이 씬 상태 변화가 개입할 여지가 생겨 비교가 오염된다.

    Returns:
        Layer | None: 비교에 쓴 Layer 서비스. 비교를 수행하지 못하면 None
    """
    if not startNodes:
        reporter.error("TC02 결과 집합 비교", "시작 노드가 없어 비교를 수행할 수 없습니다")
        return None

    layerService = Layer()

    dependent = Dependent(layerService=layerService)
    visited = set()
    dependsOn, visited = dependent.get_all_dependencies(startNodes, visited)
    allDeps, visited = dependent.get_all_dependencies(dependsOn, visited)

    _log_info(
        f"의존성 탐색 결과: 1차 {len(dependsOn)}개 / 2차 {len(allDeps)}개 "
        f"(규칙 판정 입력은 2차 결과)"
    )

    # 비교가 성립하는지 먼저 단정한다. 규칙 입력이 비었거나 대상 레이어가 없으면
    # 두 경로 모두 빈 집합을 돌려주고 "일치"가 나오는데, 그것은 동작 보존의 근거가
    # 아니라 **아무것도 검증하지 못한 상태**다. 공허한 통과가 통과로 읽히지 않도록
    # 유효성을 별도 TC로 판정한다.
    targetLayerNames = layerService.get_layer_by_namepattern(
        _EQUIVALENT_LAYER_PATTERN
    ) or []
    populatedLayerNames = [
        layerName
        for layerName in targetLayerNames
        if layerService.get_nodes_by_layername(layerName)
    ]

    reporter.assert_test(
        len(allDeps) > 0,
        f"TC02-pre 규칙 판정 입력(2차 탐색 결과)이 비어 있지 않음 - {len(allDeps)}개",
        "2차 탐색 결과가 0개다. 시작 노드가 씬 전체에 가까우면 1차에서 모두 방문되어 "
        f"2차가 비고 규칙이 구조적으로 발동할 수 없다. {START_NODES_ENV}로 익스포트 "
        "대상 메쉬만 지정해 재측정할 것"
    )
    reporter.assert_test(
        len(populatedLayerNames) > 0,
        f"TC02-pre2 '{_EQUIVALENT_LAYER_PATTERN}' 대상 레이어에 노드가 있음 - "
        f"{len(populatedLayerNames)}개 레이어",
        f"패턴에 걸리는 레이어 {len(targetLayerNames)}개 중 노드가 있는 레이어가 "
        f"0개다. 이 접두로는 양쪽 모두 빈 집합이 나와 비교가 공허하다. "
        f"{LAYER_PREFIX_ENV}로 실제 노드가 있는 접두를 지정해 재측정할 것. "
        f"패턴 매치 레이어: {targetLayerNames}"
    )

    legacyHandles = _handle_set(
        _legacy_collect_addon_helpers(allDeps, layerService)
    )

    dependent.collectPolicy = build_policy(
        inAllOrNothingLayers=[_EQUIVALENT_LAYER_PATTERN],
        inAllOrNothingAddSuperClass="Helper",
    )
    engineHandles = _handle_set(dependent.collect_addon_helpers(allDeps))

    _log_info(
        f"현행 로직 결과 {len(legacyHandles)}개 / 신 엔진 결과 {len(engineHandles)}개"
    )

    onlyLegacy = legacyHandles - engineHandles
    onlyEngine = engineHandles - legacyHandles

    if onlyLegacy:
        _log_info(
            f"현행에만 있는 노드 {len(onlyLegacy)}개: {_describe_handles(onlyLegacy)}"
        )
    if onlyEngine:
        _log_info(
            f"신 엔진에만 있는 노드 {len(onlyEngine)}개: {_describe_handles(onlyEngine)}"
        )

    reporter.assert_test(
        legacyHandles == engineHandles,
        f"TC02 결과 집합 일치 (현행 {len(legacyHandles)}개 = "
        f"신 엔진 {len(engineHandles)}개)",
        f"현행에만: {_describe_handles(onlyLegacy)} / "
        f"신 엔진에만: {_describe_handles(onlyEngine)}"
    )
    return layerService


def _report_case_mismatched_layers(inLayerService):
    """현행 startswith가 놓치는 대소문자 불일치 레이어 현황을 기록한다.

    신 엔진은 대소문자를 무시해 레이어를 해석한다. 실기 씬에 ``rig_addon_*`` 같은
    표기가 있으면 현행 ``startswith``는 놓치고 신 엔진은 잡는다. 회귀가 아니라
    개선이지만, 차이가 있었다면 로그로 드러나야 판정이 근거를 갖는다.

    Args:
        inLayerService (Layer): 레이어 서비스
    """
    allAddonLayerNames = inLayerService.get_layer_by_namepattern(
        _EQUIVALENT_LAYER_PATTERN
    ) or []
    caseMismatchedNames = [
        layerName
        for layerName in allAddonLayerNames
        if not layerName.startswith(_LEGACY_LAYER_PREFIX)
    ]

    _log_info(
        f"씬의 '{_EQUIVALENT_LAYER_PATTERN}' 레이어 {len(allAddonLayerNames)}개, "
        f"그 중 현행 startswith가 놓치는 대소문자 불일치 "
        f"{len(caseMismatchedNames)}개: {caseMismatchedNames}"
    )


if sceneReady:
    try:
        comparedLayerService = _compare_collect_paths()
        if comparedLayerService is not None:
            _report_case_mismatched_layers(comparedLayerService)
    except Exception as e:
        reporter.error("TC02 결과 집합 비교", str(e))


# ============================================================
# 결과 요약
# ============================================================
reporter.summary()
reporter.close()
