# -*- coding: utf-8 -*-
"""PyJalLib 레이어 에이전트 인터페이스 — 레이어 조회·검색·노드 이동·부모 레이어 지정을 에이전트가 이름으로 실행한다.

함수 목록:
    get_layer_nodes — 이름이 정확히 같은 레이어에 속한 노드를 읽는다 [none]
    find_layers — 와일드카드 패턴과 일치하는 레이어 이름을 찾는다 [none]
    create_layer_from_nodes — 레이어를 만들거나 재사용해 노드들을 그 레이어로 옮긴다 [scene]
    set_parent_layer — 레이어의 부모 레이어를 지정한다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib.max를 import할 수 있어야 한다.
    레이어는 이름으로 지정한다(대소문자까지 정확히 일치). 없는 레이어는
    INVALID_ARGUMENT(``details["kind"] == "layer"``)다. 기본 레이어 이름은 ``"0"``이다.
    노드는 이름(str)·handle(int)·NodeRef(dict)로 지정한다(``agentSupport.resolve_node`` 규칙).
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
    """Header의 Layer 서비스를 지연 획득한다(명세 C-1·J-14)."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().layer


def _handle(inNode) -> int:
    """노드 handle(``inode.handle``)."""
    return int(inNode.inode.handle)


def _require_name(inValue, inArgName: str) -> str:
    """비어 있지 않은 문자열 인자를 검사한다."""
    if not isinstance(inValue, str) or inValue == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 비어 있지 않은 문자열이어야 한다",
            {"argument": inArgName, "value": repr(inValue)},
        )
    return inValue


def _layer_index(inService, inLayerName: str) -> int:
    """이름이 정확히 같은 레이어 번호. 없으면 INVALID_ARGUMENT(kind="layer")."""
    index = inService.get_layer_number(inLayerName)
    if index is False:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"이름이 '{inLayerName}'인 레이어가 없다",
            {"kind": "layer", "layer": inLayerName},
        )
    return int(index)


def _parent_name(inLayer) -> str | None:
    """레이어의 부모 레이어 이름. 없으면 None."""
    parent = inLayer.getParent()
    if parent is None:
        return None
    return str(parent.name)


def _resolve_unique(inNodes, inArgName: str) -> list:
    """노드 목록을 해석하고 빈 목록·중복 노드를 거절한다."""
    nodes = ags.resolve_nodes(inNodes)
    if not nodes:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, f"{inArgName}가 비어 있다", {"argument": inArgName}
        )
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


def get_layer_nodes(inLayerName: str, inLimit: int = 1000) -> dict:
    """이름이 정확히 같은 레이어에 속한 노드를 읽는다(하위 레이어는 포함하지 않는다).

    원본은 없는 레이어와 빈 레이어를 똑같이 빈 목록으로 돌려주므로, 이 함수는 레이어
    존재를 먼저 확인하고 없으면 INVALID_ARGUMENT로 거절한다.

    Args:
        inLayerName: 레이어 이름(대소문자까지 정확히 일치)
        inLimit: 돌려줄 노드 수 상한(1 이상)

    Returns:
        ``{"layer": str, "nodes": [NodeRef], "count": int, "truncated": bool}``.
        count는 레이어의 전체 노드 수, nodes는 그중 앞 inLimit개다.

    Raises:
        AgentApiError: INVALID_ARGUMENT(이름 형·빈 이름·inLimit 범위, 레이어 없음 —
            ``details["kind"] == "layer"``), OPERATION_FAILED(원본 실행 실패)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import layer; result = layer.get_layer_nodes("Bip_IK")
    """
    _require_name(inLayerName, "inLayerName")
    if isinstance(inLimit, bool) or not isinstance(inLimit, int) or inLimit < 1:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inLimit은 1 이상의 정수여야 한다",
            {"argument": "inLimit", "value": repr(inLimit)},
        )

    service = _service()
    index = _layer_index(service, inLayerName)
    try:
        nodes = list(service.get_nodes_from_layer(index))
    except Exception as error:  # noqa: BLE001 - C-3 변환
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"레이어 '{inLayerName}'의 노드 조회에 실패했다: {error}",
            {"exception": repr(error), "layer": inLayerName},
        ) from error

    return {
        "layer": inLayerName,
        "nodes": [ags.node_ref(node) for node in nodes[:inLimit]],
        "count": len(nodes),
        "truncated": len(nodes) > inLimit,
    }


def find_layers(inPattern: str) -> dict:
    """와일드카드 패턴(``*``, ``?``, 대소문자 무시)과 일치하는 레이어 이름을 레이어 번호 순으로 찾는다.

    Args:
        inPattern: 레이어 이름 패턴(예: ``"Bip_*"``)

    Returns:
        ``{"layers": [str]}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(문자열이 아님·빈 패턴), OPERATION_FAILED(원본 실행 실패)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import layer; result = layer.find_layers("Bip_*")
    """
    _require_name(inPattern, "inPattern")
    try:
        names = _service().get_layer_by_namepattern(inPattern)
    except Exception as error:  # noqa: BLE001 - C-3 변환
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"레이어 패턴 검색에 실패했다: {error}",
            {"exception": repr(error), "pattern": inPattern},
        ) from error
    return {"layers": [str(name) for name in names]}


def create_layer_from_nodes(inLayerName: str, inNodes: list) -> dict:
    """이름이 ``inLayerName``인 레이어를 만들거나(없을 때) 재사용하고, 노드들을 그 레이어로 옮긴다.

    레이어 존재 판정은 원본(``get_layer_number``, 대소문자 구분)을 그대로 따른다. 대소문자만 다른
    이름의 레이어가 이미 있으면 원본은 "없음"으로 보고 새 레이어를 만드는데, Max 레이어 이름은
    대소문자를 무시하므로 새 레이어의 이름 지정이 실패해 노드가 다른 이름의 새 레이어로 옮겨질 수
    있다(이 함수는 거절하지 않는다). 호출 뒤 각 노드의 레이어를 다시 읽어, ``inLayerName``으로
    옮겨지지 않은 노드는 warnings에 실제 레이어 이름과 함께 적는다. 레이어가 바뀌지 않은 노드(이미
    그 레이어에 있던 노드)는 modified에서 뺀다.

    Args:
        inLayerName: 레이어 이름
        inNodes: 옮길 노드 목록(이름·handle·NodeRef)

    Returns:
        readback dict. modified는 소속 레이어가 실제로 바뀐 노드(``inLayerName``이 아닌 레이어로
        옮겨진 노드도 포함 — warnings 참조), details는
        ``{"layer": str, "layerCreated": bool(원본 판정 기준으로 레이어가 없었는지),
        "previousLayers": {handle 문자열: 이전 레이어 이름}}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(이름 형·빈 이름·빈 목록·중복 노드), NODE_NOT_FOUND,
            NODE_AMBIGUOUS, OPERATION_FAILED(원본 실행 실패)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import layer; result = layer.create_layer_from_nodes("Helpers", ["Dum_Root", "Dum_IK"])
    """
    _require_name(inLayerName, "inLayerName")
    nodes = _resolve_unique(inNodes, "inNodes")
    service = _service()

    layerCreated = service.get_layer_number(inLayerName) is False

    previousLayers = {str(_handle(node)): str(node.layer.name) for node in nodes}

    try:
        service.create_layer_from_array(list(nodes), inLayerName)
    except Exception as error:  # noqa: BLE001 - C-3 변환
        code = ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED
        raise ags.AgentApiError(
            code,
            f"레이어 '{inLayerName}' 생성·노드 이동에 실패했다: {error}",
            {"exception": repr(error), "layer": inLayerName},
        ) from error

    modified = []
    warnings = []
    for node in nodes:
        currentLayer = str(node.layer.name)
        if currentLayer != previousLayers[str(_handle(node))]:
            modified.append(node)
        if currentLayer != inLayerName:
            warnings.append(f"'{node.name}'이 레이어 '{inLayerName}'로 옮겨지지 않았다(현재 '{currentLayer}')")

    return ags.readback(
        modified=modified,
        details={
            "layer": inLayerName,
            "layerCreated": layerCreated,
            "previousLayers": previousLayers,
        },
        warnings=warnings,
    )


def set_parent_layer(inLayerName: str, inParentName: str) -> dict:
    """레이어 ``inLayerName``의 부모 레이어를 ``inParentName``으로 지정한다.

    두 레이어가 모두 있어야 한다. 자기 자신·자기 하위 레이어를 부모로 지정하거나 기본
    레이어 ``"0"``을 자식으로 지정하면 장면을 바꾸기 전에 거절한다. 레이어는 노드가 아니므로
    modified는 비운다.

    Args:
        inLayerName: 자식 레이어 이름
        inParentName: 부모 레이어 이름

    Returns:
        readback dict. details는 ``{"layer": str, "parent": str, "previousParent": str | None}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(이름 형·빈 이름, 레이어 없음 — ``details["kind"] == "layer"``,
            같은 레이어·순환·기본 레이어를 자식으로 지정), OPERATION_FAILED(원본이 False를
            돌려줌·실행 실패·부모가 바뀌지 않음)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import layer; result = layer.set_parent_layer("Bip_IK", "Rig")
    """
    _require_name(inLayerName, "inLayerName")
    _require_name(inParentName, "inParentName")
    if inLayerName == inParentName:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "자식 레이어와 부모 레이어가 같다",
            {"kind": "layer", "layer": inLayerName, "parent": inParentName},
        )

    rt = _runtime()
    service = _service()
    missing = [
        name for name in (inLayerName, inParentName) if service.get_layer_number(name) is False
    ]
    if missing:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"레이어가 없다: {missing}",
            {"kind": "layer", "missing": missing},
        )

    childIndex = _layer_index(service, inLayerName)
    parentIndex = _layer_index(service, inParentName)
    if childIndex == 0:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "기본 레이어 '0'은 다른 레이어의 자식이 될 수 없다",
            {"kind": "layer", "layer": inLayerName},
        )

    childLayer = rt.LayerManager.getLayer(childIndex)
    parentLayer = rt.LayerManager.getLayer(parentIndex)

    ancestor = parentLayer
    while ancestor is not None:
        if str(ancestor.name) == inLayerName:
            raise ags.AgentApiError(
                ags.INVALID_ARGUMENT,
                f"'{inParentName}'은 '{inLayerName}'의 하위 레이어라 부모로 지정하면 순환이 생긴다",
                {"kind": "layer", "layer": inLayerName, "parent": inParentName},
            )
        ancestor = ancestor.getParent()

    previousParent = _parent_name(childLayer)

    try:
        result = service.set_parent_layer(inLayerName, inParentName)
    except Exception as error:  # noqa: BLE001 - C-3 변환
        code = ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED
        raise ags.AgentApiError(
            code,
            f"레이어 '{inLayerName}'의 부모 지정에 실패했다: {error}",
            {"exception": repr(error), "layer": inLayerName, "parent": inParentName},
        ) from error
    if result is False:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"레이어 '{inLayerName}'의 부모 지정에 실패했다",
            {"originalReturn": False, "layer": inLayerName, "parent": inParentName},
        )

    currentParent = _parent_name(rt.LayerManager.getLayer(_layer_index(service, inLayerName)))
    if currentParent != inParentName:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"레이어 '{inLayerName}'의 부모가 '{inParentName}'로 바뀌지 않았다(현재 {currentParent!r})",
            {"layer": inLayerName, "parent": inParentName, "actualParent": currentParent},
        )

    return ags.readback(
        details={"layer": inLayerName, "parent": inParentName, "previousParent": previousParent}
    )
