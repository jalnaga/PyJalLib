# -*- coding: utf-8 -*-
"""PyJalLib 커스텀 어트리뷰트 에이전트 인터페이스 — 노드에 붙은 커스텀 어트리뷰트 정의 제거를 에이전트가 이름으로 실행한다.

함수 목록:
    remove_attribute_def — 노드 baseObject에서 이름이 일치하는 커스텀 어트리뷰트 정의를 지운다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib.max를 import할 수 있어야 한다.
    노드는 이름(str)·handle(int)·NodeRef(dict)로 지정한다(``agentSupport.resolve_node`` 규칙).
    대상은 노드의 baseObject에 붙은 정의뿐이다. 모디파이어에 붙은 정의는 다루지 않는다.
    pymxs와 Header는 함수 안에서만 지연 획득하므로 이 모듈 import는 장면을 바꾸지 않는다.
"""

from pyjallib.max import agentSupport as ags


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _service():
    """Header의 Attribute 서비스를 지연 획득한다(명세 C-1·J-14)."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().attribute


def _def_names(inService, inNode) -> list:
    """노드 baseObject에 붙은 커스텀 어트리뷰트 정의 이름 목록."""
    try:
        return [str(attrDef.name) for attrDef in inService.get_all_attribute_defs(inNode)]
    except Exception:  # noqa: BLE001 - 진단용 목록이라 실패하면 비운다
        return []


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def remove_attribute_def(inNode: str | int | dict, inDefName: str) -> dict:
    """노드 baseObject에서 이름이 ``inDefName``인 커스텀 어트리뷰트 정의를 지운다.

    정의가 없으면 장면을 바꾸지 않고 INVALID_ARGUMENT(``details["kind"] == "attributeDef"``,
    ``details["available"]``에 현재 정의 이름)로 거절한다. 원본은 같은 이름의 정의 중
    첫 번째만 지우므로, 지운 뒤에도 같은 이름이 남아 있으면 warnings에 적는다.

    Args:
        inNode: 대상 노드(이름·handle·NodeRef)
        inDefName: 지울 커스텀 어트리뷰트 정의 이름

    Returns:
        readback dict. modified는 ``[inNode]``, details는 ``{"defName": str}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(inDefName 형·빈 이름, 정의 없음), NODE_NOT_FOUND,
            NODE_AMBIGUOUS, OPERATION_FAILED(원본이 False를 돌려줌 또는 실행 실패)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import attribute; result = attribute.remove_attribute_def("Ctrl_Face", "FacialData")
    """
    if not isinstance(inDefName, str) or inDefName == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inDefName은 비어 있지 않은 문자열이어야 한다",
            {"argument": "inDefName", "value": repr(inDefName)},
        )

    node = ags.resolve_node(inNode)
    service = _service()

    if not service.has_attribute_def(node, inDefName):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"'{node.name}'에 커스텀 어트리뷰트 정의 '{inDefName}'이 없다",
            {
                "kind": "attributeDef",
                "node": ags.node_ref(node),
                "defName": inDefName,
                "available": _def_names(service, node),
            },
        )

    try:
        result = service.remove_attribute_def(node, inDefName)
    except Exception as error:  # noqa: BLE001 - C-3 변환
        code = ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED
        raise ags.AgentApiError(
            code,
            f"'{node.name}'의 커스텀 어트리뷰트 정의 '{inDefName}' 제거에 실패했다: {error}",
            {"exception": repr(error), "node": ags.node_ref(node), "defName": inDefName},
        ) from error
    if result is False:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"'{node.name}'의 커스텀 어트리뷰트 정의 '{inDefName}' 제거에 실패했다",
            {"originalReturn": False, "node": ags.node_ref(node), "defName": inDefName},
        )

    warnings = []
    if service.has_attribute_def(node, inDefName):
        warnings.append(
            f"같은 이름의 정의 '{inDefName}'이 아직 남아 있다(원본은 첫 정의 하나만 지운다)"
        )

    return ags.readback(modified=[node], details={"defName": inDefName}, warnings=warnings)
