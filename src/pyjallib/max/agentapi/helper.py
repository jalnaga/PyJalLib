# -*- coding: utf-8 -*-
"""PyJalLib 헬퍼 에이전트 인터페이스 — 리깅용 빈 포인트 헬퍼 생성을 에이전트가 이름으로 실행한다.

함수 목록:
    create_empty_point — 크기 0·프리즈된 빈 Point 헬퍼를 원점에 만든다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib.max를 import할 수 있어야 한다.
    pymxs와 Header는 함수 안에서만 지연 획득하므로 이 모듈 import는 장면을 바꾸지 않는다.
"""

from pyjallib.max import agentSupport as ags


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _service():
    """Header의 Helper 서비스를 지연 획득한다."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().helper


def _handle(inNode) -> int:
    """노드 handle(``inode.handle``)."""
    return int(inNode.inode.handle)


def _nodes_named(inRt, inName: str) -> list:
    """이름이 대소문자까지 정확히 같은 장면 노드 목록."""
    return [node for node in inRt.objects if inRt.isValidNode(node) and str(node.name) == inName]


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def create_empty_point(inName: str) -> dict:
    """크기 0이고 십자·박스 표시가 꺼진 빈 Point 헬퍼를 원점에 만들고 프리즈한다.

    이름을 고유하게 바꾸지 않는다. 같은 이름의 노드가 이미 있으면 그대로 만들고 warnings에
    적는다(이후 그 이름으로 노드를 지정하면 NODE_AMBIGUOUS가 된다 — handle로 지정한다).
    created는 호출 전후 장면 노드 차이로 만든다.

    Args:
        inName: 만들 헬퍼 이름(빈 문자열 불가)

    Returns:
        readback dict. created는 새 Point 헬퍼, details는
        ``{"requestedName": str, "actualName": str, "frozen": bool}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(문자열이 아님·빈 이름), OPERATION_FAILED(원본 실행 실패,
            생성된 노드를 확인하지 못함)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import helper; result = helper.create_empty_point("Dum_Root")
    """
    if not isinstance(inName, str) or inName == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inName은 비어 있지 않은 문자열이어야 한다",
            {"argument": "inName", "value": repr(inName)},
        )

    from pyjallib.max.agentapi import _scene

    rt = _runtime()
    warnings = []
    existing = _nodes_named(rt, inName)
    if existing:
        warnings.append(
            f"이름이 '{inName}'인 노드가 이미 {len(existing)}개 있다. 이름으로 지정하면 NODE_AMBIGUOUS가 된다"
        )

    before = _scene.snapshot_handles()
    try:
        point = _service().create_empty_point(inName)
    except Exception as error:  # noqa: BLE001 변환
        code = ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED
        raise ags.AgentApiError(
            code,
            f"빈 포인트 헬퍼 생성에 실패했다: {error}",
            {"exception": repr(error), "requestedName": inName},
        ) from error

    if point is None or not rt.isValidNode(point):
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "원본이 유효한 포인트 헬퍼를 돌려주지 않았다",
            {"requestedName": inName, "originalReturn": repr(point)},
        )

    created = _scene.created_since(before)
    if _handle(point) not in {_handle(node) for node in created}:
        created.append(point)
        warnings.append("생성된 헬퍼가 장면 노드 차이에 잡히지 않아 원본 반환값으로 보충했다")

    actualName = str(point.name)
    if actualName != inName:
        warnings.append(f"요청한 이름 '{inName}'과 실제 이름 '{actualName}'이 다르다")

    return ags.readback(
        created=created,
        details={
            "requestedName": inName,
            "actualName": actualName,
            "frozen": bool(point.isFrozen),
        },
        warnings=warnings,
    )
