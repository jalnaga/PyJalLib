# -*- coding: utf-8 -*-
"""PyJalLib 제약 에이전트 인터페이스 — 노드의 트랜스폼 컨트롤러를 기본형으로 되돌리는 작업을 에이전트가 이름으로 실행한다.

함수 목록:
    collapse_transform_controllers — 비 Biped 노드의 위치·회전·스케일 컨트롤러를 기본형으로 바꾸고 현재 변환만 남긴다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib.max를 import할 수 있어야 한다.
    노드는 이름(str)·handle(int)·NodeRef(dict)로 지정한다(``agentSupport.resolve_node`` 규칙).
    pymxs와 Header는 함수 안에서만 지연 획득하므로 이 모듈 import는 장면을 바꾸지 않는다.
"""

from pyjallib.max import agentSupport as ags

#: MAXScript 경로 문자열(``$'이름'``)에 넣으면 오동작하는 문자(명세 J-13)
_PATH_FORBIDDEN_CHARS = ("'", "*", "?", "\\")


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _service():
    """Header의 Constraint 서비스를 지연 획득한다(명세 C-1·J-14)."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().constraint


def _handle(inNode) -> int:
    """노드 handle(``inode.handle``)."""
    return int(inNode.inode.handle)


def _to_agent_error(inError: Exception, inMessage: str, inDetails: dict | None = None):
    """원본 예외를 AgentApiError로 바꾼다(명세 C-3). ValueError는 INVALID_ARGUMENT, 그 밖은 OPERATION_FAILED."""
    if isinstance(inError, ags.AgentApiError):
        return inError
    code = ags.INVALID_ARGUMENT if isinstance(inError, ValueError) else ags.OPERATION_FAILED
    details = dict(inDetails or {})
    details["exception"] = repr(inError)
    return ags.AgentApiError(code, f"{inMessage}: {inError}", details)


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


def _check_path_safe(inRt, inNode) -> None:
    """``$'이름'`` 경로로 노드를 가리키는 원본을 부르기 전에 이름을 검사한다.

    금지 문자(J-13)가 있으면 INVALID_ARGUMENT. MAXScript 경로는 대소문자를 무시하므로
    대소문자만 다른 동명 노드가 있으면 다른 노드가 바뀔 수 있어 NODE_AMBIGUOUS로 거절한다.
    """
    name = str(inNode.name)
    forbidden = [char for char in _PATH_FORBIDDEN_CHARS if char in name]
    if forbidden:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"노드 이름 '{name}'에 MAXScript 경로에서 쓸 수 없는 문자가 있다",
            {"node": ags.node_ref(inNode), "forbiddenChars": forbidden},
        )
    lowered = name.lower()
    sameNames = [
        node for node in inRt.objects if inRt.isValidNode(node) and str(node.name).lower() == lowered
    ]
    if len(sameNames) > 1:
        raise ags.AgentApiError(
            ags.NODE_AMBIGUOUS,
            f"'{name}'과 대소문자만 다른 이름의 노드가 있어 MAXScript 경로가 다른 노드를 가리킬 수 있다",
            {"name": name, "handles": sorted(_handle(node) for node in sameNames)},
        )


def _controllers_collapsed(inRt, inNode) -> bool:
    """위치·회전·스케일 컨트롤러가 Position_XYZ·Euler_XYZ·Bezier_Scale인지 확인한다."""
    transformController = inNode.controller
    expected = (
        ("Position", inRt.Position_XYZ),
        ("Rotation", inRt.Euler_XYZ),
        ("Scale", inRt.Bezier_Scale),
    )
    for propName, controllerClass in expected:
        controller = inRt.getPropertyController(transformController, propName)
        if controller is None or inRt.classOf(controller) != controllerClass:
            return False
    return True


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def collapse_transform_controllers(inNodes: list) -> dict:
    """비 Biped 노드의 위치·회전·스케일 컨트롤러를 기본형으로 바꾸고 현재 시간의 변환만 남긴다.

    **애니메이션 키가 사라진다.** 위치는 Position_XYZ, 회전은 Euler_XYZ, 스케일은
    Bezier_Scale로 교체하고, 호출 시점(현재 프레임)의 월드 변환을 다시 대입한다.
    제약·리스트 컨트롤러도 함께 사라진다. Biped_Object는 처리하지 않고 warnings에 적는다.
    원본이 MAXScript 경로 ``$'이름'``으로 노드를 가리키므로, 이름에 ``'`` ``*`` ``?`` ``\\``가
    있거나 대소문자만 다른 동명 노드가 있으면 장면을 바꾸기 전에 거절한다.
    모든 사전 검사를 통과한 뒤 노드 순서대로 적용한다.

    Args:
        inNodes: 처리할 노드 목록(이름·handle·NodeRef)

    Returns:
        readback dict. modified는 실제로 처리한 노드, details는
        ``{"time": 현재 프레임, "skipped": [NodeRef]}``(건너뛴 Biped_Object).

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드·이름 금지 문자), NODE_NOT_FOUND,
            NODE_AMBIGUOUS(대소문자만 다른 동명 노드 포함), OPERATION_FAILED(원본 실행 실패.
            ``details["applied"]``에 이미 처리한 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import constraint; result = constraint.collapse_transform_controllers(["Helper_IK"])
    """
    nodes = _resolve_unique(inNodes, "inNodes")
    rt = _runtime()

    targets = []
    skipped = []
    warnings = []
    for node in nodes:
        if rt.classOf(node) == rt.Biped_Object:
            skipped.append(node)
            warnings.append(f"'{node.name}'은 Biped_Object라 건너뛰었다")
            continue
        _check_path_safe(rt, node)
        targets.append(node)

    service = _service()
    currentFrame = int(rt.currentTime)
    applied = []
    for node in targets:
        try:
            service.collapse(node)
        except Exception as error:  # noqa: BLE001 - C-3·C-11 변환
            raise _to_agent_error(
                error,
                f"'{node.name}'의 컨트롤러 초기화에 실패했다",
                {"node": ags.node_ref(node), "applied": applied},
            ) from error
        applied.append(ags.node_ref(node))
        try:
            collapsed = _controllers_collapsed(rt, node)
        except Exception:  # noqa: BLE001 - 확인 실패는 경고로만 남긴다
            collapsed = False
        if not collapsed:
            warnings.append(
                f"'{node.name}'의 위치·회전·스케일 컨트롤러가 기본형으로 바뀐 것을 확인하지 못했다"
            )

    return ags.readback(
        modified=targets,
        details={"time": currentFrame, "skipped": [ags.node_ref(node) for node in skipped]},
        warnings=warnings,
    )
