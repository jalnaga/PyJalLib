# -*- coding: utf-8 -*-
"""PyJalLib 애니메이션 에이전트 인터페이스 — 트랜스폼 베이크·키 삭제·변환 저장/복원·평균 변환·로컬 이동을 에이전트가 이름으로 실행한다.

함수 목록:
    bake_world_transforms — 소스 노드의 월드 트랜스폼을 대상 노드에 프레임 단위로 베이크한다 [scene]
    delete_keys_in_range — 노드들의 위치·회전·스케일 키를 프레임 구간에서 지운다 [scene]
    match_anim_transform — 노드의 애니메이션 변환을 대상 노드의 키 시점에 맞춰 복사한다 [scene]
    save_xform — 노드의 현재 월드·부모 공간 행렬을 사용자 프로퍼티에 기록한다 [scene]
    set_xform — save_xform으로 기록한 행렬을 노드에 다시 적용한다 [scene]
    get_average_position_transform — 노드들의 평균 위치 변환 행렬을 계산한다 [none]
    get_average_rotation_transform — 노드들의 평균 회전 변환 행렬을 계산한다 [none]
    move_local — 노드들을 각자의 로컬 축 기준으로 이동한다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib.max를 import할 수 있어야 한다.
    노드는 이름(str)·handle(int)·NodeRef(dict)로 지정한다(``agentSupport.resolve_node`` 규칙).
    pymxs와 Header는 함수 안에서만 지연 획득하므로 이 모듈 import는 장면을 바꾸지 않는다.
"""

from pyjallib.max import agentSupport as ags

#: MAXScript 경로 문자열(``$'이름'``)에 넣으면 오동작하는 문자(명세 J-13)
_PATH_FORBIDDEN_CHARS = ("'", "*", "?", "\\")

_XFORM_SPACES = ("World", "Parent")


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _service():
    """Header의 Anim 서비스를 지연 획득한다(명세 C-1·J-14)."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().anim


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


def _require_int(inValue, inArgName: str) -> int:
    """정수 인자를 검사한다(bool 제외)."""
    if isinstance(inValue, bool) or not isinstance(inValue, int):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 정수여야 한다: {type(inValue).__name__}",
            {"argument": inArgName, "value": repr(inValue)},
        )
    return inValue


def _require_bool(inValue, inArgName: str) -> bool:
    """bool 인자를 검사한다."""
    if not isinstance(inValue, bool):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 bool이어야 한다: {type(inValue).__name__}",
            {"argument": inArgName, "value": repr(inValue)},
        )
    return inValue


def _require_range(inStart: int, inEnd: int) -> None:
    """시작 프레임이 끝 프레임보다 크면 거절한다."""
    if inStart > inEnd:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"구간이 뒤집혀 있다: start={inStart}, end={inEnd}",
            {"start": inStart, "end": inEnd},
        )


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


def _user_prop(inRt, inNode, inKey: str):
    """사용자 프로퍼티 문자열. 없으면 None."""
    value = inRt.getUserProp(inNode, inRt.Name(inKey))
    if value is None:
        return None
    return str(value)


def _descendants(inNode) -> list:
    """노드의 모든 자손(깊이 우선)."""
    result = []
    stack = list(inNode.children)
    while stack:
        child = stack.pop(0)
        result.append(child)
        stack.extend(list(child.children))
    return result


def _ancestor_handles(inNode) -> list:
    """노드의 조상 handle 목록(가까운 순)."""
    handles = []
    parent = inNode.parent
    while parent is not None:
        handles.append(_handle(parent))
        parent = parent.parent
    return handles


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def bake_world_transforms(
    inSourceNodes: list,
    inTargetNodes: list,
    inStartFrame: int,
    inEndFrame: int,
    inTargetStartFrame: int = 0,
    inClearTargetKeys: bool = False,
) -> dict:
    """소스 노드들의 월드 트랜스폼을 대상 노드들에 프레임마다 베이크한다.

    소스 프레임 ``k``의 월드 트랜스폼을 대상 프레임
    ``inTargetStartFrame + (k - inStartFrame)``에 키로 기록한다(구간 이동 가능).
    대상들이 부모-자식 관계면 부모를 먼저 적용해야 한다. 목록에서 자식이 부모보다
    앞에 있으면 순서는 바꾸지 않고 warnings에 적는다.
    원본이 MAXScript ``with undo off``로 키를 기록하므로 Undo로 되돌릴 수 없다.

    Args:
        inSourceNodes: 월드 트랜스폼을 읽을 소스 노드 목록(이름·handle·NodeRef)
        inTargetNodes: 기록 대상 노드 목록. 소스와 같은 순서로 1:1 대응한다
        inStartFrame: 소스 구간 시작 프레임
        inEndFrame: 소스 구간 끝 프레임(포함)
        inTargetStartFrame: inStartFrame에 대응하는 대상 프레임
        inClearTargetKeys: True면 기록 전에 대상 구간의 기존 키를 지운다

    Returns:
        readback dict. modified는 대상 노드, details는
        ``{"sourceRange": [s, e], "targetRange": [ts, ts+e-s], "clearedTargetKeys": bool}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(프레임 형·뒤집힌 구간·빈 목록·중복 노드·개수 불일치),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, OPERATION_FAILED(원본 실행 실패)

    Side effects: scene
    Undo: no

    Example:
        from pyjallib.max.agentapi import anim; result = anim.bake_world_transforms(["Bip001 Pelvis"], ["Root_Helper"], 0, 30)
    """
    _require_int(inStartFrame, "inStartFrame")
    _require_int(inEndFrame, "inEndFrame")
    _require_int(inTargetStartFrame, "inTargetStartFrame")
    _require_bool(inClearTargetKeys, "inClearTargetKeys")
    _require_range(inStartFrame, inEndFrame)

    sources = _resolve_unique(inSourceNodes, "inSourceNodes")
    targets = _resolve_unique(inTargetNodes, "inTargetNodes")
    if len(sources) != len(targets):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"소스와 대상 노드 수가 다르다: 소스 {len(sources)}개, 대상 {len(targets)}개",
            {"sourceCount": len(sources), "targetCount": len(targets)},
        )

    warnings = []
    targetIndex = {_handle(node): index for index, node in enumerate(targets)}
    for index, node in enumerate(targets):
        for ancestorHandle in _ancestor_handles(node):
            ancestorIndex = targetIndex.get(ancestorHandle)
            if ancestorIndex is not None and ancestorIndex > index:
                warnings.append(
                    f"대상 '{node.name}'(index {index})이 조상 '{targets[ancestorIndex].name}'"
                    f"(index {ancestorIndex})보다 먼저 적용된다. 부모를 먼저 두어야 결과가 맞는다"
                )
                break

    try:
        _service().bake_world_transforms(
            sources,
            targets,
            inStartFrame,
            inEndFrame,
            inTargetStartFrame=inTargetStartFrame,
            inClearTargetKeys=inClearTargetKeys,
        )
    except Exception as error:  # noqa: BLE001 - C-3 변환
        raise _to_agent_error(error, "월드 트랜스폼 베이크에 실패했다") from error

    targetEnd = inTargetStartFrame + (inEndFrame - inStartFrame)
    return ags.readback(
        modified=targets,
        details={
            "sourceRange": [inStartFrame, inEndFrame],
            "targetRange": [inTargetStartFrame, targetEnd],
            "clearedTargetKeys": inClearTargetKeys,
        },
        warnings=warnings,
    )


def delete_keys_in_range(inNodes: list, inStartFrame: int, inEndFrame: int) -> dict:
    """노드들의 위치·회전·스케일 컨트롤러 키를 프레임 구간에서 지운다.

    원본이 MAXScript 경로 ``$'이름'``으로 노드를 가리키므로, 이름에 ``'`` ``*`` ``?`` ``\\``가
    있거나 대소문자만 다른 동명 노드가 있으면 장면을 바꾸기 전에 거절한다.
    모든 사전 검사를 통과한 뒤 노드 순서대로 적용한다.

    Args:
        inNodes: 키를 지울 노드 목록(이름·handle·NodeRef)
        inStartFrame: 구간 시작 프레임
        inEndFrame: 구간 끝 프레임(포함)

    Returns:
        readback dict. modified는 처리한 노드, details는 ``{"range": [s, e]}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(프레임 형·뒤집힌 구간·빈 목록·중복 노드·이름 금지 문자),
            NODE_NOT_FOUND, NODE_AMBIGUOUS(대소문자만 다른 동명 노드 포함),
            OPERATION_FAILED(원본이 실패를 삼키고 False를 돌려줌 — 리스너 출력 참조.
            ``details["applied"]``에 이미 처리한 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import anim; result = anim.delete_keys_in_range(["Box001"], 10, 20)
    """
    _require_int(inStartFrame, "inStartFrame")
    _require_int(inEndFrame, "inEndFrame")
    _require_range(inStartFrame, inEndFrame)

    nodes = _resolve_unique(inNodes, "inNodes")
    rt = _runtime()
    for node in nodes:
        _check_path_safe(rt, node)

    service = _service()
    applied = []
    for node in nodes:
        try:
            result = service.delete_keys_in_range(node, inStartFrame, inEndFrame)
        except Exception as error:  # noqa: BLE001 - C-3·C-11 변환
            raise _to_agent_error(
                error,
                f"'{node.name}'의 키 삭제에 실패했다",
                {"node": ags.node_ref(node), "applied": applied},
            ) from error
        if result is False:
            raise ags.AgentApiError(
                ags.OPERATION_FAILED,
                f"'{node.name}'의 키 삭제에 실패했다(원본이 예외를 삼킴 — 리스너 출력 참조)",
                {
                    "node": ags.node_ref(node),
                    "originalReturn": False,
                    "reason": "원본이 예외를 삼키고 False를 돌려줬다. 리스너 출력을 참조한다",
                    "applied": applied,
                },
            )
        applied.append(ags.node_ref(node))

    return ags.readback(modified=nodes, details={"range": [inStartFrame, inEndFrame]})


def match_anim_transform(
    inNode: str | int | dict,
    inTarget: str | int | dict,
    inStartFrame: int | None = None,
    inEndFrame: int | None = None,
) -> dict:
    """노드의 애니메이션 변환을 대상 노드의 위치·회전·스케일 키 시점에 맞춰 복사한다.

    구간 안의 기존 키를 지운 뒤, 대상 노드의 키 시점과 구간 양끝에 대상의 월드 변환을
    키로 기록한다. 상태 표시줄 진행 표시가 잠시 나타날 수 있다(대화상자 아님).
    원본이 내부 베이크를 MAXScript ``with undo off``로 실행하므로 Undo로 되돌릴 수 없다.

    Args:
        inNode: 변환을 받을 노드(이름·handle·NodeRef)
        inTarget: 기준이 되는 대상 노드(이름·handle·NodeRef)
        inStartFrame: 시작 프레임. None이면 장면 animationRange 시작
        inEndFrame: 끝 프레임. None이면 장면 animationRange 끝

    Returns:
        readback dict. modified는 ``[inNode]``, details는
        ``{"range": [s, e], "target": NodeRef}``(None으로 받은 값은 실제 사용한 값으로 채운다).

    Raises:
        AgentApiError: INVALID_ARGUMENT(같은 노드·프레임 형·뒤집힌 구간), NODE_NOT_FOUND,
            NODE_AMBIGUOUS, OPERATION_FAILED(원본 실행 실패)

    Side effects: scene
    Undo: no

    Example:
        from pyjallib.max.agentapi import anim; result = anim.match_anim_transform("Helper_Root", "Bip001", 0, 100)
    """
    if inStartFrame is not None:
        _require_int(inStartFrame, "inStartFrame")
    if inEndFrame is not None:
        _require_int(inEndFrame, "inEndFrame")

    node = ags.resolve_node(inNode)
    target = ags.resolve_node(inTarget)
    if _handle(node) == _handle(target):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inNode와 inTarget이 같은 노드다",
            {"node": ags.node_ref(node)},
        )

    rt = _runtime()
    startFrame = int(rt.animationRange.start) if inStartFrame is None else inStartFrame
    endFrame = int(rt.animationRange.end) if inEndFrame is None else inEndFrame
    _require_range(startFrame, endFrame)

    try:
        _service().match_anim_transform(node, target, startFrame, endFrame)
    except Exception as error:  # noqa: BLE001 - C-3 변환
        raise _to_agent_error(
            error,
            f"'{node.name}'의 애니메이션 변환 일치에 실패했다",
            {"node": ags.node_ref(node), "target": ags.node_ref(target)},
        ) from error

    return ags.readback(
        modified=[node],
        details={"range": [startFrame, endFrame], "target": ags.node_ref(target)},
    )


def save_xform(inNodes: list) -> dict:
    """노드들의 현재 월드 행렬(``WorldSpaceMatrix``)과, 부모가 있으면 부모 공간 행렬(``ParentSpaceMatrix``)을 사용자 프로퍼티에 기록한다.

    행렬은 ``str(Matrix3)`` 문자열로 저장되어 정밀도가 깎일 수 있다. 부모가 없는 노드에
    예전 ``ParentSpaceMatrix``가 남아 있으면 지우지 않고 warnings에 적는다.

    Args:
        inNodes: 기록할 노드 목록(이름·handle·NodeRef)

    Returns:
        readback dict. modified는 기록한 노드, details는
        ``{"saved": [{"node": NodeRef, "world": True, "parent": bool}]}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            OPERATION_FAILED(원본 실행 실패 또는 기록 확인 실패. ``details["applied"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import anim; result = anim.save_xform(["Bone_L_Arm"])
    """
    nodes = _resolve_unique(inNodes, "inNodes")
    rt = _runtime()
    service = _service()

    saved = []
    warnings = []
    applied = []
    for node in nodes:
        try:
            service.save_xform(node)
        except Exception as error:  # noqa: BLE001 - C-3·C-11 변환
            raise _to_agent_error(
                error,
                f"'{node.name}'의 변환 기록에 실패했다",
                {"node": ags.node_ref(node), "applied": applied},
            ) from error
        if _user_prop(rt, node, "WorldSpaceMatrix") is None:
            raise ags.AgentApiError(
                ags.OPERATION_FAILED,
                f"'{node.name}'에 WorldSpaceMatrix가 기록되지 않았다",
                {"node": ags.node_ref(node), "applied": applied},
            )
        hasParent = node.parent is not None
        if not hasParent and _user_prop(rt, node, "ParentSpaceMatrix") is not None:
            warnings.append(
                f"'{node.name}'은 부모가 없지만 예전 ParentSpaceMatrix가 남아 있다"
                "(set_xform Parent는 부모가 없어 쓸 수 없다)"
            )
        applied.append(ags.node_ref(node))
        saved.append({"node": ags.node_ref(node), "world": True, "parent": hasParent})

    return ags.readback(modified=nodes, details={"saved": saved}, warnings=warnings)


def set_xform(inNodes: list, inSpace: str = "World") -> dict:
    """save_xform으로 기록한 행렬을 노드들에 다시 적용한다.

    ``"World"``는 ``WorldSpaceMatrix``를 그대로, ``"Parent"``는 ``ParentSpaceMatrix``를 현재
    부모 변환에 곱해 적용한다. **원본은 프로퍼티 문자열을 형식 검사 없이 MAXScript로 실행한다**
    (``rt.execute``). 이 함수는 문자열 형식을 검사하지 않으므로, 프로퍼티에 행렬이 아닌
    MAXScript가 들어 있으면 그대로 실행된다 — 신뢰하는 장면(``save_xform``으로 기록한 노드)에만
    쓴다. 프로퍼티가 없거나 ``"Parent"``인데 부모가 없는 노드는 원본을 부르기 전에 거절하며,
    모든 노드의 사전 검사를 통과한 뒤에 적용한다.

    Args:
        inNodes: 적용할 노드 목록(이름·handle·NodeRef)
        inSpace: ``"World"`` 또는 ``"Parent"``

    Returns:
        readback dict. modified는 적용한 노드, details는 ``{"space": str}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(inSpace 값·빈 목록·중복 노드), NODE_NOT_FOUND,
            NODE_AMBIGUOUS, PRECONDITION_FAILED(프로퍼티 없음·Parent인데 부모 없음.
            ``details["problems"]``), OPERATION_FAILED(원본 실행 실패 — 프로퍼티 문자열 평가 오류 포함.
            ``details["applied"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import anim; result = anim.set_xform(["Bone_L_Arm"], "World")
    """
    if inSpace not in _XFORM_SPACES:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"inSpace는 {list(_XFORM_SPACES)} 중 하나여야 한다: {inSpace!r}",
            {"argument": "inSpace", "value": repr(inSpace), "valid": list(_XFORM_SPACES)},
        )

    nodes = _resolve_unique(inNodes, "inNodes")
    rt = _runtime()
    propKey = "WorldSpaceMatrix" if inSpace == "World" else "ParentSpaceMatrix"

    problems = []
    for node in nodes:
        if inSpace == "Parent" and node.parent is None:
            problems.append({"node": ags.node_ref(node), "reason": "부모가 없다"})
            continue
        if _user_prop(rt, node, propKey) is None:
            problems.append({"node": ags.node_ref(node), "reason": f"{propKey} 프로퍼티가 없다"})
    if problems:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"노드 {len(problems)}개가 {inSpace} 공간 적용 조건을 만족하지 않는다",
            {"space": inSpace, "problems": problems},
        )

    service = _service()
    applied = []
    for node in nodes:
        try:
            service.set_xform(node, space=inSpace)
        except Exception as error:  # noqa: BLE001 - C-3·C-11 변환
            raise _to_agent_error(
                error,
                f"'{node.name}'에 기록한 변환 적용에 실패했다",
                {"node": ags.node_ref(node), "applied": applied},
            ) from error
        applied.append(ags.node_ref(node))

    return ags.readback(modified=nodes, details={"space": inSpace})


def get_average_position_transform(inNodes: list) -> dict:
    """노드들의 평균 위치를 담은 변환 행렬을 계산한다(장면에 남는 변화 없음).

    원본은 임시 Point에 Position_Constraint를 걸어 계산한 뒤 임시 노드를 지운다.

    Args:
        inNodes: 평균을 낼 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"transform": [[x, y, z] × 4], "position": [x, y, z]}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            OPERATION_FAILED(원본 실행 실패)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import anim; result = anim.get_average_position_transform(["Bip001 L Hand", "Bip001 R Hand"])
    """
    nodes = _resolve_unique(inNodes, "inNodes")
    try:
        transform = _service().create_average_pos_transform(nodes)
        return {
            "transform": ags.to_json(transform),
            "position": ags.to_json(transform.row4),
        }
    except Exception as error:  # noqa: BLE001 - C-3 변환
        raise _to_agent_error(error, "평균 위치 계산에 실패했다") from error


def get_average_rotation_transform(inNodes: list) -> dict:
    """노드들의 평균 회전을 담은 변환 행렬을 계산한다(장면에 남는 변화 없음).

    원본은 임시 Point에 Orientation_Constraint를 걸어 계산한 뒤 임시 노드를 지운다.

    Args:
        inNodes: 평균을 낼 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"transform": [[x, y, z] × 4], "rotationQuat": [x, y, z, w]}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            OPERATION_FAILED(원본 실행 실패)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import anim; result = anim.get_average_rotation_transform(["Bip001 L Hand", "Bip001 R Hand"])
    """
    nodes = _resolve_unique(inNodes, "inNodes")
    try:
        transform = _service().create_average_rot_transform(nodes)
        return {
            "transform": ags.to_json(transform),
            "rotationQuat": ags.to_json(transform.rotationPart),
        }
    except Exception as error:  # noqa: BLE001 - C-3 변환
        raise _to_agent_error(error, "평균 회전 계산에 실패했다") from error


def move_local(inNodes: list, inOffset: list, inDontAffectChildren: bool = False) -> dict:
    """노드들을 각자의 로컬 축 기준으로 ``inOffset``만큼 이동한다.

    ``inDontAffectChildren``이 False면 자식도 함께 움직인다(readback modified에 포함).
    True면 이동하는 동안 자식 링크를 잠시 끊었다가 되돌려 자식은 제자리에 둔다.
    Auto Key가 켜져 있으면 현재 프레임에 키가 생길 수 있어 warnings에 적는다.

    Args:
        inNodes: 이동할 노드 목록(이름·handle·NodeRef)
        inOffset: 로컬 축 이동량 ``[x, y, z]``
        inDontAffectChildren: True면 자식을 움직이지 않는다

    Returns:
        readback dict. modified는 이동한 노드(+함께 움직인 자손), details는
        ``{"offset": [x, y, z], "dontAffectChildren": bool, "affectedChildren": [NodeRef]}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(inOffset 길이≠3·숫자 아님·빈 목록·중복 노드),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, OPERATION_FAILED(원본 실행 실패. ``details["applied"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import anim; result = anim.move_local(["Box001"], [0.0, 0.0, 10.0])
    """
    if (
        not isinstance(inOffset, (list, tuple))
        or len(inOffset) != 3
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in inOffset)
    ):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inOffset은 숫자 3개짜리 목록 [x, y, z]여야 한다",
            {"argument": "inOffset", "value": repr(inOffset)},
        )
    _require_bool(inDontAffectChildren, "inDontAffectChildren")
    offset = [float(value) for value in inOffset]

    nodes = _resolve_unique(inNodes, "inNodes")
    rt = _runtime()

    warnings = []
    if bool(rt.animButtonState):
        warnings.append("Auto Key가 켜져 있어 현재 프레임에 트랜스폼 키가 생길 수 있다")

    nodeHandles = {_handle(node) for node in nodes}
    affectedChildren = []
    if not inDontAffectChildren:
        seen = set(nodeHandles)
        for node in nodes:
            for child in _descendants(node):
                childHandle = _handle(child)
                if childHandle not in seen:
                    seen.add(childHandle)
                    affectedChildren.append(child)
        for node in nodes:
            if any(handle in nodeHandles for handle in _ancestor_handles(node)):
                warnings.append(
                    f"'{node.name}'은 조상과 함께 목록에 있어 조상의 이동까지 더해 움직인다"
                )

    service = _service()
    applied = []
    for node in nodes:
        try:
            service.move_local(node, offset[0], offset[1], offset[2], dontAffectChildren=inDontAffectChildren)
        except Exception as error:  # noqa: BLE001 - C-3·C-11 변환
            raise _to_agent_error(
                error,
                f"'{node.name}'의 로컬 이동에 실패했다",
                {"node": ags.node_ref(node), "applied": applied},
            ) from error
        applied.append(ags.node_ref(node))

    return ags.readback(
        modified=list(nodes) + affectedChildren,
        details={
            "offset": offset,
            "dontAffectChildren": inDontAffectChildren,
            "affectedChildren": [ags.node_ref(child) for child in affectedChildren],
        },
        warnings=warnings,
    )
