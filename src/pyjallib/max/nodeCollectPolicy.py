#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
노드 수집 확장 규칙 엔진 (순수 모듈).

의존성 탐색은 "지금 실제로 참조되는 것"만 찾는다. 그런데 익스포트나 선택에서
필요한 집합은 그것보다 넓을 때가 많다 - 스킨 가중치가 0이라 참조가 끊긴 본,
레이어 단위로 함께 가야 하는 부속 노드, 부모가 살아 있을 때만 의미가 있는
소켓 따위다. 이 모듈은 그 확장을 규칙 3종으로 기술한다.

- 규칙 1 (무조건 포함): 대상 레이어의 노드를 항상 넣는다
- 규칙 2 (전부-또는-전무): 대상 레이어의 노드를 하나라도 쓰면 그 레이어 전체를
  넣는다. **레이어별로 독립 판정한다**
- 규칙 3 (부모 조건부): 그 노드의 부모가 집합에 있을 때만 넣는다

무엇이 대상인가는 이 모듈이 알지 못한다. 호출부가 :class:`NodeCollectPolicy`로
기술하고, 씬 접근은 ``nodeCollectResolver`` 어댑터가 담당한다. pyjallib은 범용
오픈소스 라이브러리이므로 특정 프로젝트의 레이어 이름을 알고 있어서는 안 된다.

이 모듈은 ``pymxs``에 의존하지 않는다. 규칙 판단을 순수하게 분리해야 콘솔
pytest(Type A)로 규칙 전체를 검증할 수 있다 - 규칙 한 줄 고칠 때마다 3ds Max를
띄우는 비용을 없애는 것이 분리의 목적이다. 클래스 판정(수퍼클래스 필터)도 같은
이유로 어댑터에 남기고, 엔진은 이미 걸러진 핸들 집합만 받는다.

노드 식별자는 3ds Max 노드 핸들(정수)을 쓴다. pymxs 노드 래퍼는 같은 노드라도
조회 경로에 따라 서로 다른 객체가 되어 ``set`` 원소로 쓸 수 없기 때문이다.
"""

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

# 규칙별 추가 내역 키. 로깅이 이 키로 규칙별 집계를 그대로 꺼내 쓴다.
RULE_MANDATORY = "mandatory"
RULE_ALL_OR_NOTHING = "allOrNothing"
RULE_PARENT_CONDITIONAL = "parentConditional"

# 위 세 규칙이 노드를 넣을 때 딸려 들어온 부모 노드. 규칙이 직접 지목한 것과
# 구분해 집계해야 "왜 이 노드가 들어갔는가"가 로그에서 드러난다.
RULE_PARENT_CHAIN = "parentChain"

ALL_RULE_KEYS = (
    RULE_MANDATORY,
    RULE_ALL_OR_NOTHING,
    RULE_PARENT_CONDITIONAL,
    RULE_PARENT_CHAIN,
)

# 규칙 2 항목의 두 집합 키. 판정 집합과 추가 집합이 다를 수 있다는 것이
# 이 규칙의 핵심이므로 키를 상수로 고정해 오타를 막는다.
TRIGGER_KEY = "trigger"
ADD_KEY = "add"


@dataclass
class NodeCollectPolicy:
    """노드 수집 확장 규칙을 레이어 패턴으로 기술한 정서(policy).

    전부 기본값이 빈 값이다. 즉 **정서를 만들기만 하고 아무것도 채우지 않으면
    규칙이 하나도 발동하지 않는다.** 라이브러리 기본값 자리에 특정 프로젝트의
    레이어 이름을 남기면 그것을 제거한 것이 아니므로, "규칙 없음"이 기본이어야
    한다.

    레이어 이름은 ``rt.matchPattern`` 와일드카드를 쓸 수 있다(예:
    ``"Prop_Attach_*"``). 해석은 어댑터가 대소문자 무시로 수행한다.

    Attributes:
        mandatoryLayers: 규칙 1 대상 레이어 패턴. 이 레이어의 노드는 의존성과
            무관하게 항상 들어간다
        allOrNothingLayers: 규칙 2 대상 레이어 패턴. 레이어별로 독립 판정한다
        allOrNothingAddSuperClass: 규칙 2의 **추가 집합에만** 걸리는 수퍼클래스
            이름(예: ``"Helper"``). None이면 필터 없음(판정 집합 = 추가 집합).
            판정에는 걸지 않는다 - 의존성에 걸리는 것은 보통 본이므로 판정에도
            Helper 필터를 걸면 규칙이 발동하지 않는다
        parentConditionalLayers: 규칙 3 대상 레이어 패턴. 부모가 결과 집합에
            있을 때만 들어간다
        parentChainBoundaryLayers: 부모 체인 추적을 허용하는 경계 레이어 패턴.
            비어 있으면 부모 체인 확장이 일어나지 않는다
    """

    mandatoryLayers: list[str] = field(default_factory=list)
    allOrNothingLayers: list[str] = field(default_factory=list)
    allOrNothingAddSuperClass: Optional[str] = None
    parentConditionalLayers: list[str] = field(default_factory=list)
    parentChainBoundaryLayers: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """규칙 대상 레이어가 하나도 없는지 판정합니다.

        경계 레이어(``parentChainBoundaryLayers``)만 지정된 정서는 확장할 대상이
        없으므로 비어 있는 것으로 본다 - 경계는 규칙이 아니라 규칙의 작용 범위다.

        Returns:
            규칙 1~3 대상이 전부 비었으면 True
        """
        return not (
            self.mandatoryLayers
            or self.allOrNothingLayers
            or self.parentConditionalLayers
        )


def _add_with_parent_chain(
    inTargetIds: Iterable[int],
    inResult: set[int],
    inParentMap: dict[int, Optional[int]],
    inParentChainBoundaryIds: set[int],
) -> dict[str, list[int]]:
    """대상 핸들을 결과 집합에 넣고, 부모 방향으로 연결된 노드까지 함께 넣습니다.

    ``inResult``를 제자리에서 변경합니다. 부모 추적은 ``inParentChainBoundaryIds``
    안에 머무는 동안만 계속하고, 그 밖으로 나가면 중단합니다. 수집 대상이 아닌
    노드를 결과에 끌고 들어가지 않기 위함입니다.

    이미 결과 집합에 있는 부모를 만나면 즉시 중단합니다. 모든 추가가 이 함수를
    거치므로, 결과 집합에 들어 있는 핸들은 자신의 부모 체인 추적을 이미 마친
    상태라는 불변식이 성립하기 때문입니다.

    세 규칙 모두 이 함수를 통과시키는 이유는, 계층이 예상 밖으로 바뀌었을 때
    부모 없는 고아 노드가 조용히 결과에 들어가는 것을 막기 위함입니다.

    Args:
        inTargetIds: 결과 집합에 넣을 노드 핸들들
        inResult: 수집 대상 핸들 집합. 제자리에서 변경됨
        inParentMap: ``{핸들: 부모 핸들}``. 부모가 없으면 값이 None
        inParentChainBoundaryIds: 부모 추적을 허용하는 경계 핸들 집합

    Returns:
        ``{"direct": [규칙이 직접 지목해 추가된 핸들],
        "chain": [부모 추적으로 딸려 추가된 핸들]}``.
        이미 집합에 있던 핸들은 어느 쪽에도 포함되지 않습니다.
    """
    directIds: list[int] = []
    chainIds: list[int] = []

    for targetId in inTargetIds:
        if targetId in inResult:
            continue

        inResult.add(targetId)
        directIds.append(targetId)

        currentId = targetId
        while True:
            parentId = inParentMap.get(currentId)
            if parentId is None:
                break
            if parentId not in inParentChainBoundaryIds:
                break
            if parentId in inResult:
                break

            inResult.add(parentId)
            chainIds.append(parentId)
            currentId = parentId

    return {"direct": directIds, "chain": chainIds}


def expand_node_set(
    inBaseIds: set[int],
    inMandatoryIds: Optional[set[int]] = None,
    inAllOrNothingIdsByLayer: Optional[dict[str, dict[str, set[int]]]] = None,
    inParentConditionalIds: Optional[set[int]] = None,
    inParentMap: Optional[dict[int, Optional[int]]] = None,
    inParentChainBoundaryIds: Optional[set[int]] = None,
) -> dict[str, Any]:
    """의존성 탐색으로 얻은 핸들 집합에 규칙 1~3을 적용해 확장합니다.

    규칙 1 -> 2 -> 3 순서로 한 번씩 적용합니다. 각 규칙의 추가가 결과 집합에
    즉시 반영되므로 뒤 규칙은 앞 규칙의 결과를 보고 판정합니다. 예를 들어 규칙
    2가 노드를 넣으면서 딸려 온 부모에 조건부 노드가 매달려 있으면 규칙 3이
    그것을 잡습니다.

    규칙 3은 새로 추가된 노드에 다시 조건부 노드가 매달려 있을 수 있으므로 더
    이상 추가할 것이 없을 때까지 반복합니다. 대상 집합이 유한하고 매 반복마다
    결과가 최소 1개 늘어나므로 반드시 종료합니다.

    모든 규칙 인자가 생략 가능합니다. 전부 생략하면 ``inBaseIds`` 사본이 그대로
    반환됩니다 - **정서 없음 = 확장 없음**이 라이브러리로서 옳은 기본값입니다.

    입력 집합은 변경하지 않습니다. ``inBaseIds``를 복사해 작업합니다.

    Args:
        inBaseIds: 의존성 탐색으로 얻은 기준 핸들 집합
        inMandatoryIds: 규칙 1 대상 핸들 집합
        inAllOrNothingIdsByLayer: 규칙 2 대상. ``{레이어명: {"trigger": 판정
            핸들 집합, "add": 추가 핸들 집합}}``. 레이어별로 독립 판정하기 위해
            dict로 받는다. ``trigger``와 ``add``가 다를 수 있는 것이 이 규칙의
            핵심이다 - 본이 걸려서 발동하고 Helper만 들어오는 경우가 그것이다
        inParentConditionalIds: 규칙 3 대상 핸들 집합
        inParentMap: ``{핸들: 부모 핸들}``. 부모가 없으면 값이 None
        inParentChainBoundaryIds: 부모 추적을 허용하는 경계 핸들 집합

    Returns:
        ``{"result": 확장된 핸들 집합,
        "byRule": {규칙키: [그 규칙으로 추가된 핸들 리스트]}}``.
        ``byRule``은 항상 4개 키를 모두 가지며, 추가가 없으면 빈 리스트입니다.
    """
    mandatoryIds = inMandatoryIds if inMandatoryIds is not None else set()
    allOrNothingIdsByLayer = (
        inAllOrNothingIdsByLayer if inAllOrNothingIdsByLayer is not None else {}
    )
    parentConditionalIds = (
        inParentConditionalIds if inParentConditionalIds is not None else set()
    )
    parentMap = inParentMap if inParentMap is not None else {}
    parentChainBoundaryIds = (
        inParentChainBoundaryIds if inParentChainBoundaryIds is not None else set()
    )

    resultIds = set(inBaseIds)
    byRule: dict[str, list[int]] = {ruleKey: [] for ruleKey in ALL_RULE_KEYS}

    def applyRule(inRuleKey: str, inTargetIds: Iterable[int]) -> None:
        """대상 핸들을 결과 집합에 추가하고 규칙별 내역에 기록한다."""
        addedIds = _add_with_parent_chain(
            inTargetIds, resultIds, parentMap, parentChainBoundaryIds
        )
        byRule[inRuleKey].extend(addedIds["direct"])
        byRule[RULE_PARENT_CHAIN].extend(addedIds["chain"])

    # 규칙 1 - 무조건 포함. 의존성 탐색 결과와 무관하다.
    applyRule(RULE_MANDATORY, sorted(mandatoryIds))

    # 규칙 2 - 전부-또는-전무. 레이어를 하나라도 쓰면 그 레이어 전체.
    # 판정을 레이어별로 분리해야 한 레이어를 쓴 것이 다른 레이어를 끌고
    # 들어오지 않는다.
    for layerName in sorted(allOrNothingIdsByLayer.keys()):
        layerEntry = allOrNothingIdsByLayer[layerName]
        triggerIds = layerEntry.get(TRIGGER_KEY) or set()
        if not (triggerIds & resultIds):
            continue
        applyRule(RULE_ALL_OR_NOTHING, sorted(layerEntry.get(ADD_KEY) or set()))

    # 규칙 3 - 부모 조건부. 부모 핸들로 역인덱스를 만들어 두면 매 반복이
    # 조건부 노드 전체 순회가 아니라 부모 조회로 끝난다.
    conditionalIdsByParent: dict[int, list[int]] = {}
    for nodeId in sorted(parentConditionalIds):
        parentId = parentMap.get(nodeId)
        if parentId is None:
            # 부모가 없으면 발동 조건 자체가 성립하지 않는다.
            continue
        conditionalIdsByParent.setdefault(parentId, []).append(nodeId)

    while True:
        pendingIds = sorted(
            nodeId
            for parentId, nodeIds in conditionalIdsByParent.items()
            if parentId in resultIds
            for nodeId in nodeIds
            if nodeId not in resultIds
        )
        if not pendingIds:
            break
        applyRule(RULE_PARENT_CONDITIONAL, pendingIds)

    return {"result": resultIds, "byRule": byRule}
