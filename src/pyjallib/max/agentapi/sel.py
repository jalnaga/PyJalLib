# -*- coding: utf-8 -*-
"""선택 에이전트 인터페이스 — 에이전트가 노드들의 의존 노드(컨트롤러·스킨·부모 체인)를 선택 없이 모은다.

함수 목록:
    collect_dependencies — 노드들의 의존 노드를 모아 handle 순으로 돌려준다(선택하지 않음) [none]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    결과는 Header 전역 노드 수집 정서(``Header.configure_node_collect_policy``)에 따라 달라진다.
    반환의 ``collectPolicyActive``가 그 상태를 알려 준다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 예:
    from pyjallib.max.agentapi import sel; result = sel.collect_dependencies(["Body_Mesh"])
"""

from pyjallib.max import agentSupport as ags


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _header():
    """pyjallib Max 헤더를 함수 안에서 지연 획득한다(명세 C-1·J-14)."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader()


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _require_limit(inLimit) -> None:
    """목록 상한 인자를 확인한다(0 이상 정수).

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inLimit, int) or isinstance(inLimit, bool) or inLimit < 0:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, "inLimit은 0 이상의 정수여야 한다", {"argument": "inLimit", "input": repr(inLimit)}
        )


def _unique_nodes_by_handle(inRt, inNodes) -> tuple:
    """유효한 노드만 handle 기준으로 중복 제거해 handle 오름차순으로 정렬한다.

    Returns:
        ``(노드 list, 버린 비노드 항목 수)``
    """
    byHandle = {}
    dropped = 0
    for node in inNodes:
        if node is None or not inRt.isValidNode(node):
            dropped += 1
            continue
        byHandle.setdefault(int(node.inode.handle), node)
    return [byHandle[handle] for handle in sorted(byHandle)], dropped


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def collect_dependencies(inNodes: list, inLimit: int = 1000) -> dict:
    """노드들의 의존 노드(컨트롤러·스킨이 참조하는 노드와 부모 체인)를 모은다.

    원본 ``select_dependencies``는 이름과 달리 선택하지 않으며, 이 함수도 선택을 바꾸지 않는다.
    원본 결과는 집합 합집합이라 순서가 정해지지 않으므로 handle 오름차순으로 정렬하고
    같은 노드(handle)는 한 번만 담는다. 입력 노드 자신도 결과에 들어간다.

    Args:
        inNodes: 시작 노드 목록(이름·handle·NodeRef). 비어 있으면 안 된다
        inLimit: 돌려줄 노드 수 상한(0 이상)

    Returns:
        ``{"nodes": [NodeRef](handle 오름차순, 최대 inLimit개), "count": 전체 노드 수,
        "truncated": bool, "stats": 원본 단계별 통계 dict, "collectPolicyActive": bool,
        "warnings": [str]}``

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(빈 목록, inLimit 오류),
            OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import sel; result = sel.collect_dependencies(["Body_Mesh"], inLimit=500)
    """
    _require_limit(inLimit)
    if isinstance(inNodes, (list, tuple)) and len(inNodes) == 0:
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, "inNodes가 비어 있다", {"argument": "inNodes"})
    nodes = ags.resolve_nodes(inNodes)

    header = _header()
    rt = _runtime()
    try:
        result = header.sel.select_dependencies(nodes)
    except Exception as error:  # noqa: BLE001
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"의존 노드 수집 중 원본 처리가 실패했다: {error}",
            {"exception": repr(error), "inputs": [ags.node_ref(node) for node in nodes]},
        ) from error

    collected, dropped = _unique_nodes_by_handle(rt, result.get("nodes", []))
    warnings = []
    if dropped:
        warnings.append(f"유효한 장면 노드가 아닌 항목 {dropped}개를 결과에서 뺐다")
    total = len(collected)
    return {
        "nodes": [ags.node_ref(node) for node in collected[:inLimit]],
        "count": total,
        "truncated": total > inLimit,
        "stats": ags.to_json(result.get("stats", {})),
        "collectPolicyActive": header.sel.collectPolicy is not None,
        "warnings": warnings,
    }
