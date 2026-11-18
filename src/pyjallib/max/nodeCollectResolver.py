#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
노드 수집 확장 규칙의 pymxs 어댑터.

``nodeCollectPolicy``의 규칙 엔진은 순수 모듈이라 씬을 모른다. 이 모듈이 그
사이를 잇는다 - 정서(:class:`NodeCollectPolicy`)에 적힌 **레이어 패턴**을 씬의
**노드 핸들 집합과 부모 맵**으로 해석해 엔진에 넘기고, 엔진이 돌려준 핸들을 다시
pymxs 노드로 복원한다.

역할 분담이 이렇게 갈리는 이유는 검증 비용이다. 규칙 판단은 순수하게 분리해야
콘솔 pytest(Type A)로 전체를 검증할 수 있고, 씬 접근과 클래스 판정은 원리적으로
3ds Max 안에서만 확인된다(Type C). 그래서 **클래스 필터도 엔진이 아니라 여기서**
적용한다 - 수퍼클래스 조회가 pymxs이므로 엔진에 들어가면 Type A 검증이 깨진다.

레이어 이름 해석은 대소문자를 무시한다. 3ds Max 레이어 이름은 대소문자를
구분하지 않지만 ``Layer.get_layer_number()``는 ``==`` 비교라 구분하므로,
``rt.matchPattern`` 기반의 ``get_layer_by_namepattern()``으로 씬의 실제 이름을
먼저 해석한 뒤 그 이름으로만 노드를 조회한다. 해석은 ``resolve()`` 최상단에서
패턴마다 한 번씩만 수행하고, 이후 내부 메서드는 해석된 실제 이름만 받는다 -
같은 패턴을 여러 번 해석하면 미해석 경고가 중복으로 쌓인다.
"""

from typing import Optional

from pymxs import runtime as rt

from pyjallib.logger import Logger
from pyjallib.max.nodeCollectPolicy import (
    ADD_KEY,
    ALL_RULE_KEYS,
    RULE_ALL_OR_NOTHING,
    RULE_MANDATORY,
    RULE_PARENT_CHAIN,
    RULE_PARENT_CONDITIONAL,
    TRIGGER_KEY,
    NodeCollectPolicy,
    expand_node_set,
)

# 로그에 규칙을 사람이 읽는 이름으로 남긴다. 키 순서가 곧 로그 출력 순서다.
_RULE_DISPLAY_NAMES = {
    RULE_MANDATORY: "무조건 포함",
    RULE_ALL_OR_NOTHING: "전부-또는-전무",
    RULE_PARENT_CONDITIONAL: "부모 조건부",
    RULE_PARENT_CHAIN: "부모 체인",
}

# 모듈 단일 지연 Logger. Logger는 생성 시 같은 로그 파일에 핸들러를 새로 부착하므로
# 인스턴스마다 만들면 긴 DCC 세션에서 파일 핸들이 누수되고 롤오버가 충돌한다.
_logger: Optional[Logger] = None


def _get_logger() -> Logger:
    """모듈 단일 Logger를 지연 생성해 반환한다.

    임포트 시점에 만들지 않는 이유는, 규칙을 쓰지 않는 프로젝트에서 이 모듈이
    임포트만 되어도 로그 파일이 생기는 것을 막기 위함이다.

    Returns:
        Logger: 모듈 전역 Logger 인스턴스
    """
    global _logger
    if _logger is None:
        _logger = Logger(inLogFileName="pyjallib_nodeCollect", inEnableConsole=False)
    return _logger


class NodeCollectResolver:
    """정서의 레이어 패턴을 씬 핸들로 해석해 규칙 엔진을 구동하는 어댑터.

    ``Dependent``와 ``Select``가 이 클래스를 공유한다. 두 서비스가 같은 수집
    로직을 각자 들고 있던 것이 서로 어긋난 원인이었으므로, 확장 경로를 하나로
    접는다. 서비스 간 위임(``Select`` -> ``Dependent``)을 쓰지 않는 이유는
    ``header``의 생성 순서에 의존이 생기기 때문이다 - 독립 클래스면 순서 의존이
    없다.

    Attributes:
        layerService (Layer): 레이어 조회에 쓰는 Layer 서비스 인스턴스
    """

    def __init__(self, layerService):
        """NodeCollectResolver를 초기화한다.

        Args:
            layerService (Layer): Layer 서비스 인스턴스. 레이어 이름 해석과 노드
                조회를 전담한다
        """
        self.layerService = layerService

    # ------------------------------------------------------------------ #
    #  레이어 해석 / 씬 환원
    # ------------------------------------------------------------------ #

    def _resolve_layer_names(self, inLayerPatterns) -> list:
        """레이어 패턴을 씬에 실제로 존재하는 레이어 이름으로 해석한다.

        해석되지 않는 패턴은 조용히 넘기지 않고 WARNING을 남긴다. 규약이 바뀐
        씬에서 규칙이 발동하지 않는 것이 로그로 드러나야 한다. 마이그레이션은 이
        라이브러리의 소관이 아니므로 보고만 한다.

        Args:
            inLayerPatterns (list[str] | None): 레이어 이름 또는 와일드카드 패턴 리스트

        Returns:
            list[str]: 씬에 존재하는 실제 레이어 이름 리스트 (중복 제거, 입력 순서 유지)
        """
        resolvedNames = []
        seenNames = set()

        for layerPattern in inLayerPatterns or []:
            matchedNames = self.layerService.get_layer_by_namepattern(layerPattern)
            if not matchedNames:
                _get_logger().warning(
                    f"노드 수집 규칙 대상 레이어 '{layerPattern}'을(를) 씬에서 찾을 수 "
                    f"없습니다. 해당 규칙은 이 씬에서 발동하지 않습니다."
                )
                continue

            for matchedName in matchedNames:
                if matchedName in seenNames:
                    continue
                seenNames.add(matchedName)
                resolvedNames.append(matchedName)

        return resolvedNames

    def _collect_layer_handles(self, inLayerNames, inSuperClass=None) -> dict:
        """레이어별 소속 노드의 핸들 집합을 수집한다.

        비재귀 조회(``get_nodes_by_layername()``)만 사용한다. 재귀 조회를 쓰면
        자식 레이어가 부모 레이어의 규칙에 휩쓸려, 자식 레이어에 따로 걸어 둔
        규칙(부모 조건부 등)이 무의미해진다.

        Args:
            inLayerNames (list[str]): **해석이 끝난** 실제 레이어 이름 리스트
            inSuperClass: 수퍼클래스 필터(예: ``rt.Helper``). None이면 필터 없음

        Returns:
            dict[str, set[int]]: ``{레이어 이름: 노드 핸들 집합}``.
                빈 레이어는 빈 집합으로 남는다
        """
        handlesByLayer = {}
        getHandleByAnim = rt.getHandleByAnim
        superClassOf = rt.superClassOf

        for layerName in inLayerNames:
            layerNodes = self.layerService.get_nodes_by_layername(layerName) or []
            handlesByLayer[layerName] = {
                int(getHandleByAnim(node))
                for node in layerNodes
                if inSuperClass is None or superClassOf(node) == inSuperClass
            }

        return handlesByLayer

    def _build_scene_graph(self, inGraphLayerNames, inBoundaryLayerNames) -> dict:
        """규칙에 관여하는 레이어 전체의 노드로 핸들 그래프를 구성한다.

        규칙 엔진은 순수 모듈이라 pymxs 노드를 다루지 않으므로, 씬을 핸들과 부모
        맵으로 환원해 넘긴다. 핸들을 식별자로 쓰는 이유는 pymxs 노드 래퍼가 같은
        노드라도 조회 경로에 따라 다른 객체가 되어 집합 원소로 쓸 수 없기 때문이다.

        그래프 범위가 경계 레이어보다 넓은 것이 중요하다. 부모 조건부 규칙은
        부모 맵에서 자기 부모를 찾지 못하면 아예 발동하지 않고, 엔진이 돌려준
        핸들도 ``nodeByHandle``에 없으면 노드로 복원되지 않는다. 그래서 규칙 대상
        레이어를 모두 그래프에 넣고 **경계 판정에만** 경계 레이어를 쓴다. 경계를
        지정하지 않은 정서(부모 체인 확장을 원하지 않는 경우)에서도 규칙 1~3이
        정상 동작해야 하기 때문이다.

        Args:
            inGraphLayerNames (list[str]): 그래프에 담을 실제 레이어 이름 (규칙 대상 + 경계)
            inBoundaryLayerNames (list[str]): 부모 체인 추적을 허용하는 실제 경계 레이어 이름

        Returns:
            dict: ``{"nodeByHandle": {핸들: 노드},
                "parentByHandle": {핸들: 부모 핸들 | None},
                "boundaryHandles": 핸들 집합}``
        """
        getHandleByAnim = rt.getHandleByAnim
        nodeByHandle = {}
        handlesByLayer = {}

        for layerName in inGraphLayerNames:
            layerNodes = self.layerService.get_nodes_by_layername(layerName) or []
            layerHandles = set()
            for node in layerNodes:
                nodeHandle = int(getHandleByAnim(node))
                nodeByHandle[nodeHandle] = node
                layerHandles.add(nodeHandle)
            handlesByLayer[layerName] = layerHandles

        parentByHandle = {}
        for nodeHandle, node in nodeByHandle.items():
            parentNode = node.parent
            parentByHandle[nodeHandle] = (
                None if parentNode is None else int(getHandleByAnim(parentNode))
            )

        boundaryHandles = set()
        for layerName in inBoundaryLayerNames:
            boundaryHandles |= handlesByLayer.get(layerName, set())

        return {
            "nodeByHandle": nodeByHandle,
            "parentByHandle": parentByHandle,
            "boundaryHandles": boundaryHandles,
        }

    def _resolve_super_class(self, inSuperClassName):
        """수퍼클래스 이름 문자열을 pymxs 수퍼클래스 값으로 해석한다.

        정서는 순수 모듈 소속이라 pymxs 값을 담을 수 없어 이름 문자열을 든다.
        해석은 여기서 한다.

        Args:
            inSuperClassName (str | None): 수퍼클래스 이름(예: ``"Helper"``).
                None이면 필터 없음

        Returns:
            pymxs 수퍼클래스 값. 이름이 None이거나 해석 실패면 None
        """
        if inSuperClassName is None:
            return None

        # pymxs 런타임은 미정의 전역에 대해 AttributeError를 내거나 undefined를
        # 돌려준다. 둘 다 "필터 없음"으로 접어야 undefined와의 비교가 모든 노드를
        # 걸러내는 사고를 막을 수 있다.
        try:
            superClass = getattr(rt, inSuperClassName, None)
        except Exception:
            superClass = None

        if superClass is None or superClass == rt.undefined:
            _get_logger().error(
                f"수퍼클래스 '{inSuperClassName}'을(를) 3ds Max 런타임에서 찾을 수 "
                f"없습니다. 전부-또는-전무 규칙의 클래스 필터를 적용하지 않습니다."
            )
            return None

        return superClass

    # ------------------------------------------------------------------ #
    #  공개 API
    # ------------------------------------------------------------------ #

    def resolve(self, inPolicy) -> Optional[dict]:
        """정서를 규칙 엔진 입력(핸들 집합과 부모 맵)으로 해석한다.

        규칙 2만 레이어별 dict로 유지한다. 판정이 레이어마다 독립이어야 한
        레이어를 쓴 것이 다른 레이어를 끌고 들어오지 않기 때문이다. 규칙 1과 3은
        판정 단위가 노드 하나이므로 합집합으로 충분하다.

        규칙 2의 ``{trigger, add}`` 쌍에서 **판정에는 클래스 필터를 걸지 않는다.**
        의존성에 걸리는 것은 보통 본이므로 판정에도 필터를 걸면 규칙이 발동하지
        않는다. 필터가 없으면 두 집합이 같아진다.

        Args:
            inPolicy (NodeCollectPolicy | None): 해석할 정서

        Returns:
            dict | None: ``{"mandatoryHandles": set, "allOrNothingByLayer": dict,
                "parentConditionalHandles": set, "parentByHandle": dict,
                "boundaryHandles": set, "nodeByHandle": dict}``.
                정서가 비었거나 씬 조회에 실패하면 None
        """
        if inPolicy is None or inPolicy.is_empty():
            return None

        try:
            # 패턴 해석은 여기서 한 번씩만 한다. 아래 헬퍼들은 실제 이름만 받는다.
            mandatoryNames = self._resolve_layer_names(inPolicy.mandatoryLayers)
            allOrNothingNames = self._resolve_layer_names(inPolicy.allOrNothingLayers)
            parentConditionalNames = self._resolve_layer_names(
                inPolicy.parentConditionalLayers
            )
            boundaryNames = self._resolve_layer_names(
                inPolicy.parentChainBoundaryLayers
            )

            graphLayerNames = self._merge_layer_names(
                mandatoryNames, allOrNothingNames, parentConditionalNames, boundaryNames
            )
            sceneGraph = self._build_scene_graph(graphLayerNames, boundaryNames)

            mandatoryByLayer = self._collect_layer_handles(mandatoryNames)
            parentConditionalByLayer = self._collect_layer_handles(
                parentConditionalNames
            )

            addSuperClass = self._resolve_super_class(
                inPolicy.allOrNothingAddSuperClass
            )
            triggerByLayer = self._collect_layer_handles(allOrNothingNames)
            addByLayer = (
                triggerByLayer
                if addSuperClass is None
                else self._collect_layer_handles(
                    allOrNothingNames, inSuperClass=addSuperClass
                )
            )
        except Exception as e:
            _get_logger().error(
                f"노드 수집 규칙 재료 수집 실패 - {e}. 규칙 확장 없이 의존성 탐색 "
                f"결과만 사용합니다."
            )
            return None

        allOrNothingByLayer = {
            layerName: {
                TRIGGER_KEY: triggerHandles,
                ADD_KEY: addByLayer.get(layerName, set()),
            }
            for layerName, triggerHandles in triggerByLayer.items()
        }

        resolved = {
            "mandatoryHandles": self._union_handles(mandatoryByLayer),
            "allOrNothingByLayer": allOrNothingByLayer,
            "parentConditionalHandles": self._union_handles(parentConditionalByLayer),
        }
        resolved.update(sceneGraph)
        return resolved

    @staticmethod
    def _merge_layer_names(*inNameLists) -> list:
        """여러 레이어 이름 리스트를 순서를 지키며 하나로 합친다.

        Args:
            *inNameLists (list[str]): 합칠 레이어 이름 리스트들

        Returns:
            list[str]: 중복이 제거된 레이어 이름 리스트
        """
        mergedNames = []
        seenNames = set()

        for nameList in inNameLists:
            for layerName in nameList:
                if layerName in seenNames:
                    continue
                seenNames.add(layerName)
                mergedNames.append(layerName)

        return mergedNames

    @staticmethod
    def _union_handles(inHandlesByLayer) -> set:
        """레이어별 핸들 집합을 하나로 합친다.

        Args:
            inHandlesByLayer (dict[str, set[int]]): 레이어별 핸들 집합

        Returns:
            set[int]: 합집합. 입력이 비면 빈 집합
        """
        unionHandles = set()
        for handles in inHandlesByLayer.values():
            unionHandles |= handles
        return unionHandles

    def expand(self, inNodes, inPolicy) -> list:
        """의존성 탐색 결과 노드 리스트에 규칙 확장을 적용해 반환한다.

        확장 중 예외가 나면 원본 리스트를 그대로 반환한다. 확장 실패로 수집 자체가
        무너지는 것보다 확장 없이 나가는 편이 낫다.

        Args:
            inNodes (list[rt.Node]): 의존성 탐색으로 얻은 노드 리스트
            inPolicy (NodeCollectPolicy | None): 적용할 정서. None이면 원본 그대로

        Returns:
            list[rt.Node]: 확장된 노드 리스트. 원본 노드가 앞에 오고 추가된 노드가
                뒤에 붙는다
        """
        resolved = self.resolve(inPolicy)
        if resolved is None:
            return list(inNodes)

        addedNodes, _ = self.collect_additions(inNodes, resolved)
        return list(inNodes) + addedNodes

    def collect_additions(self, inNodes, inResolved) -> tuple:
        """규칙 확장으로 **추가되는** 노드만 산출한다.

        ``expand()``와 달리 원본을 앞에 붙이지 않는다. 호출부가 기존 결과와 다른
        방식으로 결합하거나(집합 합집합) 규칙별 집계를 통계에 반영해야 할 때 쓴다.

        Args:
            inNodes (list[rt.Node]): 의존성 탐색으로 얻은 노드 리스트
            inResolved (dict): ``resolve()`` 결과

        Returns:
            tuple[list, dict]: ``([추가된 노드], {규칙키: [추가된 핸들]})``.
                확장 실패 시 ``([], 규칙키마다 빈 리스트인 dict)``
        """
        emptyByRule = {ruleKey: [] for ruleKey in ALL_RULE_KEYS}
        if inResolved is None:
            return [], emptyByRule

        nodeByHandle = inResolved["nodeByHandle"]
        getHandleByAnim = rt.getHandleByAnim

        try:
            baseHandles = {int(getHandleByAnim(node)) for node in inNodes}
            expanded = expand_node_set(
                inBaseIds=baseHandles,
                inMandatoryIds=inResolved["mandatoryHandles"],
                inAllOrNothingIdsByLayer=inResolved["allOrNothingByLayer"],
                inParentConditionalIds=inResolved["parentConditionalHandles"],
                inParentMap=inResolved["parentByHandle"],
                inParentChainBoundaryIds=inResolved["boundaryHandles"],
            )
        except Exception as e:
            _get_logger().error(
                f"노드 수집 규칙 확장 실패 - {e}. 의존성 탐색 결과를 그대로 "
                f"사용합니다."
            )
            return [], emptyByRule

        byRule = expanded["byRule"]
        self._log_expand_result(byRule, nodeByHandle)

        addedNodes = []
        missingHandles = []

        for addedHandles in byRule.values():
            for nodeHandle in addedHandles:
                if nodeHandle in nodeByHandle:
                    addedNodes.append(nodeByHandle[nodeHandle])
                else:
                    missingHandles.append(nodeHandle)

        # 규칙 대상 레이어와 경계 레이어가 모두 그래프에 들어 있으므로 여기에
        # 걸리는 것은 없어야 한다. 걸린다면 그래프 수집과 규칙 대상 수집이 서로
        # 다른 씬 상태를 본 것이므로 조용히 넘기지 않는다.
        if missingHandles:
            _get_logger().warning(
                f"규칙으로 추가된 핸들 {len(missingHandles)}개를 노드로 복원하지 "
                f"못했습니다(그래프 수집과 규칙 대상 수집이 다른 씬 상태를 본 "
                f"신호): {missingHandles}"
            )

        return addedNodes, byRule

    @staticmethod
    def _log_expand_result(inByRule, inNodeByHandle) -> None:
        """규칙별 추가 내역을 로그로 남긴다.

        어떤 노드가 왜 수집에 들어갔는지 추적할 수 있어야 한다. 개수는 INFO로,
        노드 이름은 DEBUG로 남긴다.

        Args:
            inByRule (dict[str, list[int]]): ``{규칙 키: [추가된 핸들]}``
            inNodeByHandle (dict[int, Any]): ``{핸들: 노드}``. 핸들을 이름으로
                되돌리는 데 사용
        """
        totalCount = sum(len(addedHandles) for addedHandles in inByRule.values())
        if totalCount == 0:
            _get_logger().info("노드 수집 규칙 확장: 추가된 노드 없음")
            return

        countTexts = [
            f"{_RULE_DISPLAY_NAMES[ruleKey]} {len(inByRule[ruleKey])}개"
            for ruleKey in _RULE_DISPLAY_NAMES
            if ruleKey in inByRule
        ]
        _get_logger().info(
            f"노드 수집 규칙 확장: 총 {totalCount}개 추가 ({', '.join(countTexts)})"
        )

        for ruleKey, addedHandles in inByRule.items():
            if not addedHandles:
                continue
            addedNames = [
                str(inNodeByHandle[nodeHandle].name)
                for nodeHandle in addedHandles
                if nodeHandle in inNodeByHandle
            ]
            _get_logger().debug(
                f"{_RULE_DISPLAY_NAMES[ruleKey]}로 추가된 노드 "
                f"{len(addedNames)}개: {', '.join(addedNames)}"
            )


def build_policy(
    inMandatoryLayers=None,
    inAllOrNothingLayers=None,
    inAllOrNothingAddSuperClass=None,
    inParentConditionalLayers=None,
    inParentChainBoundaryLayers=None,
) -> NodeCollectPolicy:
    """호출부 대면 정서 생성 헬퍼.

    ``NodeCollectPolicy``를 직접 만드는 것과 결과가 같지만, 이 워크스페이스의 인자
    규약(``in`` 접두)에 맞춘 진입점을 제공해 호출부가 dataclass 필드 이름을 외우지
    않아도 되게 한다.

    Args:
        inMandatoryLayers (list[str] | None): 규칙 1 대상 레이어 패턴
        inAllOrNothingLayers (list[str] | None): 규칙 2 대상 레이어 패턴
        inAllOrNothingAddSuperClass (str | None): 규칙 2 추가 집합의 수퍼클래스
            이름(예: ``"Helper"``)
        inParentConditionalLayers (list[str] | None): 규칙 3 대상 레이어 패턴
        inParentChainBoundaryLayers (list[str] | None): 부모 체인 경계 레이어 패턴

    Returns:
        NodeCollectPolicy: 조립된 정서
    """
    return NodeCollectPolicy(
        mandatoryLayers=list(inMandatoryLayers or []),
        allOrNothingLayers=list(inAllOrNothingLayers or []),
        allOrNothingAddSuperClass=inAllOrNothingAddSuperClass,
        parentConditionalLayers=list(inParentConditionalLayers or []),
        parentChainBoundaryLayers=list(inParentChainBoundaryLayers or []),
    )
