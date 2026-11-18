# -*- coding: utf-8 -*-
"""PyJalLib 정렬 에이전트 인터페이스 — 노드들의 회전을 기준 노드에 맞추는 정렬을 에이전트가 이름으로 실행한다.

함수 목록:
    align_rotation_to_last — 목록의 노드들을 마지막 노드의 회전에 맞춘다(위치 유지, 스케일 1로 초기화) [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib.max를 import할 수 있어야 한다.
    노드는 이름(str)·handle(int)·NodeRef(dict)로 지정한다(``agentSupport.resolve_node`` 규칙).
    현재 선택에 의존하지 않는다. 기준 노드는 목록의 마지막 항목이다.
    pymxs와 Header는 함수 안에서만 지연 획득하므로 이 모듈 import는 장면을 바꾸지 않는다.
"""

from pyjallib.max import agentSupport as ags

#: 스케일·행렬 비교 허용 오차
_TOLERANCE = 1e-4


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _service():
    """Header의 Align 서비스를 지연 획득한다(명세 C-1·J-14)."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().align


def _handle(inNode) -> int:
    """노드 handle(``inode.handle``)."""
    return int(inNode.inode.handle)


def _transform_rows(inNode) -> list:
    """노드 월드 변환을 ``[[x, y, z] × 4]``로 읽는다."""
    return ags.to_json(inNode.transform)


def _rows_differ(inBefore: list, inAfter: list) -> bool:
    """두 행렬(4행 리스트)이 허용 오차보다 다른지 판정한다."""
    for rowBefore, rowAfter in zip(inBefore, inAfter):
        for valueBefore, valueAfter in zip(rowBefore, rowAfter):
            if abs(valueBefore - valueAfter) > _TOLERANCE:
                return True
    return False


def _scale_is_one(inNode) -> bool:
    """노드 스케일이 [1, 1, 1]인지 판정한다."""
    scale = ags.to_json(inNode.scale)
    return all(abs(value - 1.0) <= _TOLERANCE for value in scale)


def _resolve_unique(inNodes, inArgName: str) -> list:
    """노드 목록을 해석하고 중복 노드를 거절한다."""
    nodes = ags.resolve_nodes(inNodes)
    firstIndex = {}
    duplicates = []
    for index, node in enumerate(nodes):
        handle = _handle(node)
        if handle in firstIndex:
            duplicates.append({"index": index, "handle": handle, "firstIndex": firstIndex[handle]})
        else:
            firstIndex[handle] = index
    if duplicates:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}에 같은 노드가 두 번 이상 있다",
            {"argument": inArgName, "duplicates": duplicates},
        )
    return nodes


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def align_rotation_to_last(inNodes: list) -> dict:
    """목록의 노드들을 마지막 노드의 회전에 맞춘다. 각 노드의 위치는 유지한다.

    원본이 변환 행렬을 통째로 대입하므로 **처리한 노드의 스케일이 1로 초기화된다.**
    마지막(기준) 노드도 원본이 같은 방식으로 다시 대입하므로, 기준 노드의 스케일이 1이
    아니었다면 기준 노드도 바뀐다(이 경우 modified에 포함한다). 스케일이 1이 아니던
    노드는 warnings에 적는다. 현재 선택은 쓰지 않는다.

    Args:
        inNodes: 노드 목록(이름·handle·NodeRef). 2개 이상이며 마지막 항목이 기준 노드다

    Returns:
        readback dict. modified는 마지막을 뺀 노드(+변환이 실제로 바뀐 기준 노드),
        details는 ``{"target": NodeRef}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(노드 2개 미만·중복 노드), NODE_NOT_FOUND,
            NODE_AMBIGUOUS, OPERATION_FAILED(원본 실행 실패. ``details["applied"]``에 변환이
            바뀐 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import align; result = align.align_rotation_to_last(["Helper_A", "Helper_B", "Bip001 Pelvis"])
    """
    if not isinstance(inNodes, (list, tuple)) or len(inNodes) < 2:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inNodes에는 노드가 2개 이상 있어야 한다(마지막이 기준 노드)",
            {"argument": "inNodes", "count": len(inNodes) if isinstance(inNodes, (list, tuple)) else None},
        )
    nodes = _resolve_unique(inNodes, "inNodes")
    target = nodes[-1]

    warnings = []
    before = {}
    for node in nodes:
        before[_handle(node)] = _transform_rows(node)
        if not _scale_is_one(node):
            warnings.append(f"'{node.name}'의 스케일이 1이 아니었으나 1로 초기화된다")

    try:
        _service().align_to_last_rot(list(nodes))
    except Exception as error:  # noqa: BLE001 - C-3 변환
        applied = []
        for node in nodes:
            try:
                if _rows_differ(before[_handle(node)], _transform_rows(node)):
                    applied.append(ags.node_ref(node))
            except Exception:  # noqa: BLE001 - 적용 여부 확인 실패는 목록에서 뺀다
                pass
        code = ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED
        raise ags.AgentApiError(
            code,
            f"마지막 노드 회전 정렬에 실패했다: {error}",
            {"exception": repr(error), "applied": applied},
        ) from error

    modified = list(nodes[:-1])
    if _rows_differ(before[_handle(target)], _transform_rows(target)):
        modified.append(target)

    return ags.readback(modified=modified, details={"target": ags.node_ref(target)}, warnings=warnings)
