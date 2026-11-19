# -*- coding: utf-8 -*-
"""의존성 에이전트 인터페이스 — 에이전트가 노드 익스포트에 함께 필요한 관련 노드를 모은다.

함수 목록:
    collect_export_related_nodes — 익스포트 관련 노드(의존 노드·부모 체인·수집 규칙 확장분)를 모으고 원본이 결과를 선택한다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    결과는 Header 전역 노드 수집 정서(``Header.configure_node_collect_policy``)에 따라 달라진다.
    반환의 ``collectPolicyActive``가 그 상태를 알려 준다.
    원본은 결과가 비어 있지 않으면 결과 노드 전체를 선택한 채 남긴다(호출 전 선택은 되돌리지
    않는다). 선택이 바뀌므로 부작용을 scene으로 표기한다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 예:
    from pyjallib.max.agentapi import dependent; result = dependent.collect_export_related_nodes(["Body_Mesh"])
"""

from pyjallib.max import agentSupport as ags


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _header():
    """pyjallib Max 헤더를 함수 안에서 지연 획득한다."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader()


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _require_bool(inValue, inArgName: str) -> None:
    """bool 인자인지 확인한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inValue, bool):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 bool이어야 한다: {type(inValue).__name__}",
            {"argument": inArgName, "type": type(inValue).__name__},
        )


def _require_limit(inLimit) -> None:
    """목록 상한 인자를 확인한다(0 이상 정수).

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inLimit, int) or isinstance(inLimit, bool) or inLimit < 0:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, "inLimit은 0 이상의 정수여야 한다", {"argument": "inLimit", "input": repr(inLimit)}
        )


def _handle(inNode) -> int:
    """노드 handle."""
    return int(inNode.inode.handle)


def _valid_handles(inRt, inNodes) -> set:
    """유효한 노드의 handle 집합."""
    return {_handle(node) for node in inNodes if node is not None and inRt.isValidNode(node)}


def _current_selection(inRt) -> list:
    """현재 선택 노드 목록(읽기만 한다)."""
    return [node for node in inRt.selection if inRt.isValidNode(node)]


def _base_dependency_handles(inDependent, inRt, inNodes, inIncludeBiped: bool) -> set:
    """수집 규칙 확장 없이 얻는 의존 노드 handle 집합(원본과 같은 1차·2차 탐색)."""
    visited = set()
    dependsOn, visited = inDependent.get_all_dependencies(list(inNodes), visited, inIncludeBiped=inIncludeBiped)
    allDeps, visited = inDependent.get_all_dependencies(dependsOn, visited, inIncludeBiped=inIncludeBiped)
    return _valid_handles(inRt, list(inNodes) + list(dependsOn) + list(allDeps))


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def collect_export_related_nodes(
    inNodes: list, inIncludeBiped: bool = False, inLimit: int = 1000
) -> dict:
    """노드 익스포트에 함께 필요한 관련 노드를 모은다.

    컨트롤러·스킨이 참조하는 노드와 부모 체인을 두 번 따라가고, Header 전역 수집 정서가
    있으면 그 규칙의 확장분을 더한다. 결과는 handle 오름차순이며 같은 노드는 한 번만 담는다.
    원본은 수집 규칙 확장 중 예외를 삼키므로, 정서가 활성인데 확장분이 0개면 warnings에 적는다.
    **원본은 결과가 비어 있지 않으면 결과 노드 전체(상한과 무관)를 선택한 채 남긴다.** 호출 전
    선택은 되돌리지 않는다.

    Args:
        inNodes: 시작 노드 목록(이름·handle·NodeRef). 비어 있으면 안 된다
        inIncludeBiped: True면 Biped_Object도 탐색·포함한다
        inLimit: 돌려줄 노드 수 상한(0 이상). 원본이 남기는 선택에는 영향이 없다

    Returns:
        ``{"nodes": [NodeRef](handle 오름차순, 최대 inLimit개), "count": 전체 노드 수,
        "truncated": bool, "selected": 호출 뒤 선택이 결과 노드 전체와 일치하는지, "collectPolicyActive": bool,
        "warnings": [str]}``

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(빈 목록, bool·inLimit 형 오류),
            OPERATION_FAILED(원본 예외 — 선택은 원본이 남긴 상태 그대로다)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import dependent; result = dependent.collect_export_related_nodes(["Body_Mesh"])
    """
    _require_bool(inIncludeBiped, "inIncludeBiped")
    _require_limit(inLimit)
    if isinstance(inNodes, (list, tuple)) and len(inNodes) == 0:
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, "inNodes가 비어 있다", {"argument": "inNodes"})
    nodes = ags.resolve_nodes(inNodes)

    header = _header()
    rt = _runtime()
    dependentService = header.dependent

    try:
        related = dependentService.get_all_related_to_export(nodes, inIncludeBiped=inIncludeBiped)
    except Exception as error:  # noqa: BLE001
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"익스포트 관련 노드 수집 중 원본 처리가 실패했다: {error}",
            {"exception": repr(error), "inputs": [ags.node_ref(node) for node in nodes]},
        ) from error

    byHandle = {}
    dropped = 0
    for node in related or []:
        if node is None or not rt.isValidNode(node):
            dropped += 1
            continue
        byHandle.setdefault(_handle(node), node)
    collected = [byHandle[handle] for handle in sorted(byHandle)]

    warnings = []
    if dropped:
        warnings.append(f"유효한 장면 노드가 아닌 항목 {dropped}개를 결과에서 뺐다")

    policyActive = dependentService.collectPolicy is not None
    if policyActive:
        try:
            baseHandles = _base_dependency_handles(dependentService, rt, nodes, inIncludeBiped)
            extensionCount = len(set(byHandle) - baseHandles)
            if extensionCount == 0:
                warnings.append(
                    "수집 정서가 활성인데 규칙 확장분이 0개다. 원본은 확장 중 예외를 삼키므로 "
                    "규칙이 대상을 찾지 못했는지 실패했는지 구분할 수 없다(pyjallib 로그 참조)"
                )
        except Exception as error:  # noqa: BLE001 - 확장분 집계 실패는 결과를 막지 않는다
            warnings.append(f"규칙 확장분 집계에 실패했다({error!r})")

    # 원본이 남긴 선택을 읽기만 한다(되돌리지 않음)
    selectedHandles = _valid_handles(rt, _current_selection(rt))
    selected = bool(byHandle) and selectedHandles == set(byHandle)
    if byHandle and not selected:
        warnings.append(
            f"원본이 남긴 선택이 결과와 일치하지 않는다(선택 {len(selectedHandles)}개, 결과 {len(byHandle)}개)"
        )

    total = len(collected)
    return {
        "nodes": [ags.node_ref(node) for node in collected[:inLimit]],
        "count": total,
        "truncated": total > inLimit,
        "selected": selected,
        "collectPolicyActive": policyActive,
        "warnings": warnings,
    }
