# -*- coding: utf-8 -*-
"""본 에이전트 인터페이스 — 에이전트가 Nub 본을 만들고 스킨 본을 판정·연결·설정하며 본을 계층 순으로 정렬한다.

함수 목록:
    create_nub_bone — 원점에 Nub 본(BoneGeometry)을 만든다 [scene]
    link_skin_bone — 스킨 본을 Link_Constraint로 원본 본에 연결한다 [scene]
    is_skin_bone — 노드마다 스킨 본(사용자 프로퍼티 IsSkinBone)인지 판정한다 [none]
    set_skin_bone_property — 노드들의 스킨 본 표시(IsSkinBone)를 기록한다 [scene]
    get_skin_bone_ori_bone — 스킨 본마다 원본 본(사용자 프로퍼티 OriBone)을 읽는다 [none]
    set_skin_bone_parent — 스킨 본의 부모를 지정하고 Parent 프로퍼티에 기록한다 [scene]
    sort_bones_by_hierarchy — 본들을 계층 깊이 순(루트에 가까운 순)으로 정렬한다 [none]
    create_skin_bones — 원본 본들로 스킨 본을 만들고 원본 계층대로 잇는다 [scene]
    create_skin_bones_from_biped — Biped 노드들로 스킨 본을 만든다(원본 그대로, 트위스트 포함) [scene]
    is_bip_skin_bone — 스킨 본마다 원본이 Biped 계열인지 판정한다 [none]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.
    노드 인자는 이름(str)·handle(int)·NodeRef(dict)로 받고 ``agentSupport``로 해석한다.
    create_skin_bones_from_biped의 결과(링크된 Biped 스킨 본)가 ``ue5Skeleton`` 함수들의 입력이다.

호출 예:
    from pyjallib.max.agentapi import bone; result = bone.sort_bones_by_hierarchy(["Bip001 Spine", "Bip001 Pelvis"])
"""

from pyjallib.max import agentSupport as ags
from pyjallib.max.agentapi import _scene

#: create_nub_bone이 받는 boneScaleType 값
_BONE_SCALE_TYPES = ("none", "scale", "squash")


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


def _handle(inNode) -> int:
    """노드 동일성 비교용 노드 handle."""
    return int(inNode.inode.handle)


def _original_error(inError: Exception, inAction: str, inDetails: dict | None = None) -> ags.AgentApiError:
    """원본 메서드 예외를 AgentApiError로 바꾼다.

    ValueError는 INVALID_ARGUMENT, 그 밖은 OPERATION_FAILED. ``details.exception``에 repr을 담는다.
    """
    code = ags.INVALID_ARGUMENT if isinstance(inError, ValueError) else ags.OPERATION_FAILED
    details = dict(inDetails or {})
    details["exception"] = repr(inError)
    return ags.AgentApiError(code, f"{inAction} 중 원본 처리가 실패했다: {inError}", details)


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


def _is_number(inValue) -> bool:
    """int·float 숫자인지 판정한다(bool 제외)."""
    return isinstance(inValue, (int, float)) and not isinstance(inValue, bool)


def _user_prop_text(inRt, inNode, inKey: str) -> str | None:
    """사용자 프로퍼티 값을 문자열로 읽는다. 없으면 None."""
    value = inRt.getUserProp(inNode, inRt.Name(inKey))
    if value is None:
        return None
    return str(value)


def _user_prop_is_true(inValue) -> bool:
    """getUserProp 값이 참(true)인지 판정한다. 문자열로 돌아와도 처리한다."""
    if isinstance(inValue, bool):
        return inValue
    if isinstance(inValue, str):
        return inValue.strip().lower() == "true"
    return False


def _ambiguity_warning(inNodeName: str, inContext: str) -> str | None:
    """같은 이름 노드가 여러 개면 경고 문구를 돌려준다."""
    try:
        ags.resolve_node(inNodeName)
    except ags.AgentApiError as error:
        if error.code == ags.NODE_AMBIGUOUS:
            return (
                f"{inContext}: 이름 '{inNodeName}'인 노드가 {len(error.details.get('handles', []))}개다"
                f"(handles={error.details.get('handles')}). 이름으로 다시 해석하면 NODE_AMBIGUOUS가 된다"
            )
    return None


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def create_nub_bone(inName: str, inSize: float, inBoneScaleType: str = "none") -> dict:
    """원점에 Nub 본(BoneGeometry)을 만든다.

    원본은 이름에서 Index·Nub 파트를 지운 뒤 ``gen_unique_name``으로 번호를 붙인다. 그래서
    실제 이름은 요청한 이름과 다를 수 있고 ``details.actualName``에 실제 이름을 돌려준다.
    ``gen_unique_name``은 진짜 고유 이름을 보장하지 않으므로 같은 이름 노드가 생기면
    warnings에 적는다.

    Args:
        inName: 본 이름(비어 있지 않은 문자열)
        inSize: 본 크기(폭·높이·길이). 0보다 커야 한다
        inBoneScaleType: 본 스케일 타입. "none" | "scale" | "squash"

    Returns:
        readback dict. created에 생성된 본(장면 handle 차이 기준),
        details에 ``{"requestedName": str, "actualName": str}``.

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 이름, inSize<=0, 허용 밖 inBoneScaleType),
            OPERATION_FAILED(원본 예외 — 화면 갱신 잠김을 풀기 위해 enableSceneRedraw를 1회 호출한다)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bone; result = bone.create_nub_bone("Bip001 Head Nub", 2.0)
    """
    if not isinstance(inName, str) or inName == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, "inName은 비어 있지 않은 문자열이어야 한다", {"argument": "inName", "input": repr(inName)}
        )
    if not _is_number(inSize) or inSize <= 0:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, "inSize는 0보다 큰 숫자여야 한다", {"argument": "inSize", "input": repr(inSize)}
        )
    if not isinstance(inBoneScaleType, str) or inBoneScaleType not in _BONE_SCALE_TYPES:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"inBoneScaleType은 {list(_BONE_SCALE_TYPES)} 중 하나여야 한다",
            {"argument": "inBoneScaleType", "input": repr(inBoneScaleType), "valid": list(_BONE_SCALE_TYPES)},
        )

    header = _header()
    rt = _runtime()
    before = _scene.snapshot_handles()
    try:
        nubBone = header.bone.create_nub_bone(inName, float(inSize), rt.Name(inBoneScaleType))
    except Exception as error:  # noqa: BLE001 - 원본 예외를 계약 오류로 바꾼다
        try:
            rt.enableSceneRedraw()
        except Exception:  # noqa: BLE001 - 잠김 해제 실패는 원래 오류를 가리지 않는다
            pass
        raise _original_error(error, "Nub 본 생성", {"requestedName": inName}) from error

    created = _scene.created_since(before)
    if nubBone is None or not rt.isValidNode(nubBone):
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "원본이 유효한 본을 돌려주지 않았다",
            {"requestedName": inName, "originalReturn": repr(nubBone), "created": [ags.node_ref(n) for n in created]},
        )

    actualName = str(nubBone.name)
    warnings = []
    duplicate = _ambiguity_warning(actualName, "생성한 본")
    if duplicate:
        warnings.append(duplicate)
    return ags.readback(
        created=created,
        details={"requestedName": inName, "actualName": actualName},
        warnings=warnings,
    )


def link_skin_bone(inSkinBone: str | int | dict, inSourceBone: str | int | dict) -> dict:
    """스킨 본을 Link_Constraint로 원본 본에 연결한다.

    원본은 두 본 모두에 현재 트랜스폼을 사용자 프로퍼티(WorldSpaceMatrix 등)로 기록하고,
    스킨 본의 Scale 컨트롤러를 교체한 뒤 트랜스폼 컨트롤러를 Link_Constraint로 바꾼다.
    호출 뒤 스킨 본 컨트롤러가 실제로 Link_Constraint인지 확인한다.

    Args:
        inSkinBone: 스킨 본(이름·handle·NodeRef)
        inSourceBone: 연결할 원본 본(이름·handle·NodeRef)

    Returns:
        readback dict. modified에 ``[스킨 본, 원본 본]``,
        details에 ``{"controller": 호출 뒤 스킨 본 컨트롤러 클래스 이름}``.

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(두 인자가 같은 노드),
            OPERATION_FAILED(원본 예외, 또는 호출 뒤 컨트롤러가 Link_Constraint가 아님)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bone; result = bone.link_skin_bone("b_Spine", "Bip001 Spine")
    """
    skinBone, sourceBone = ags.resolve_nodes([inSkinBone, inSourceBone])
    if _handle(skinBone) == _handle(sourceBone):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "스킨 본과 원본 본이 같은 노드다",
            {"node": ags.node_ref(skinBone)},
        )

    header = _header()
    rt = _runtime()
    try:
        header.bone.link_skin_bone(skinBone, sourceBone)
    except Exception as error:  # noqa: BLE001
        raise _original_error(
            error, "스킨 본 링크", {"skinBone": ags.node_ref(skinBone), "sourceBone": ags.node_ref(sourceBone)}
        ) from error

    controllerName = str(rt.classOf(skinBone.controller))
    if controllerName != "Link_Constraint":
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"호출 뒤 스킨 본 컨트롤러가 Link_Constraint가 아니다: {controllerName}",
            {"skinBone": ags.node_ref(skinBone), "controller": controllerName},
        )
    return ags.readback(modified=[skinBone, sourceBone], details={"controller": controllerName})


def is_skin_bone(inNodes: list) -> dict:
    """노드마다 스킨 본(사용자 프로퍼티 ``IsSkinBone``가 true)인지 판정한다.

    Args:
        inNodes: 판정할 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"results": [{"node": NodeRef, "isSkinBone": bool}]}`` — 입력 순서

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bone; result = bone.is_skin_bone(["b_Spine", "Bip001 Spine"])
    """
    nodes = ags.resolve_nodes(inNodes)
    header = _header()
    results = []
    for node in nodes:
        try:
            value = bool(header.bone.is_skin_bone(node))
        except Exception as error:  # noqa: BLE001
            raise _original_error(error, "스킨 본 판정", {"node": ags.node_ref(node)}) from error
        results.append({"node": ags.node_ref(node), "isSkinBone": value})
    return {"results": results}


def set_skin_bone_property(inNodes: list, inIsSkinBone: bool = True) -> dict:
    """노드들의 사용자 프로퍼티 ``IsSkinBone``에 스킨 본 여부를 기록한다.

    모든 노드를 먼저 해석한 뒤 적용한다. 적용 뒤 프로퍼티를 다시 읽어 확인한다.

    Args:
        inNodes: 대상 노드 목록(이름·handle·NodeRef)
        inIsSkinBone: 기록할 값

    Returns:
        readback dict. modified에 프로퍼티를 기록한 노드(입력 순서),
        details에 ``{"isSkinBone": bool}``.

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(inIsSkinBone이 bool이 아님),
            OPERATION_FAILED(원본 예외 또는 다시 읽은 값 불일치 — details.applied에 이미 바뀐 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bone; result = bone.set_skin_bone_property(["b_Spine"], True)
    """
    _require_bool(inIsSkinBone, "inIsSkinBone")
    nodes = ags.resolve_nodes(inNodes)
    header = _header()
    rt = _runtime()

    applied = []
    for node in nodes:
        try:
            header.bone.set_skin_bone_property(node, inIsSkinBone)
        except Exception as error:  # noqa: BLE001
            raise _original_error(
                error, "스킨 본 프로퍼티 기록", {"node": ags.node_ref(node), "applied": applied}
            ) from error
        stored = rt.getUserProp(node, rt.Name("IsSkinBone"))
        if _user_prop_is_true(stored) != inIsSkinBone:
            raise ags.AgentApiError(
                ags.OPERATION_FAILED,
                "기록 뒤 다시 읽은 IsSkinBone 값이 요청과 다르다",
                {"node": ags.node_ref(node), "stored": repr(stored), "applied": applied},
            )
        applied.append(ags.node_ref(node))
    return ags.readback(modified=applied, details={"isSkinBone": inIsSkinBone})


def get_skin_bone_ori_bone(inNodes: list) -> dict:
    """스킨 본마다 사용자 프로퍼티 ``OriBone``이 가리키는 원본 본을 읽는다.

    원본은 프로퍼티 문자열(``$'이름'``)을 MAXScript로 평가해 노드를 찾는다. 같은 이름 노드가
    여럿이면 그중 첫 노드가 나온다(그 경우 warnings). 평가가 실패하거나 프로퍼티는 있는데
    노드가 잡히지 않으면 해당 항목의 ``oriBone``을 None으로 두고 warnings에 적는다(조회 함수라
    전체를 실패로 만들지 않는다).

    Args:
        inNodes: 스킨 본 목록(이름·handle·NodeRef)

    Returns:
        ``{"results": [{"node": NodeRef, "oriBone": NodeRef | None, "rawProperty": str | None}],
        "warnings": [str]}`` — 입력 순서

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bone; result = bone.get_skin_bone_ori_bone(["b_Spine"])
    """
    nodes = ags.resolve_nodes(inNodes)
    header = _header()
    rt = _runtime()

    results = []
    warnings = []
    for node in nodes:
        nodeRef = ags.node_ref(node)
        rawProperty = _user_prop_text(rt, node, "OriBone")
        oriRef = None
        try:
            oriBone = header.bone.get_skin_bone_ori_bone(node)
        except Exception as error:  # noqa: BLE001 - 항목 단위 실패는 warnings로 남긴다
            warnings.append(f"'{nodeRef['name']}': OriBone 평가가 실패했다({error!r}), rawProperty={rawProperty!r}")
            oriBone = None
        if oriBone is not None and rt.isValidNode(oriBone):
            oriRef = ags.node_ref(oriBone)
            duplicate = _ambiguity_warning(oriRef["name"], f"'{nodeRef['name']}'의 OriBone")
            if duplicate:
                warnings.append(duplicate + " — 원본은 그중 첫 노드를 돌려줬다")
        elif rawProperty not in (None, "", "undefined"):
            warnings.append(f"'{nodeRef['name']}': OriBone 프로퍼티({rawProperty!r})가 있지만 노드를 찾지 못했다")
        results.append({"node": nodeRef, "oriBone": oriRef, "rawProperty": rawProperty})
    return {"results": results, "warnings": warnings}


def set_skin_bone_parent(inSkinBone: str | int | dict, inParentBone: str | int | dict | None = None) -> dict:
    """스킨 본의 부모를 지정하고 사용자 프로퍼티 ``Parent``에 ``$'부모 이름'``을 기록한다.

    ``inParentBone``이 None이면 부모를 바꾸지 않고 현재 부모 이름만 기록한다(부모가 없으면
    ``undefined``). 부모 이름 문자열로 기록하므로 이후 이름이 바뀌면 참조가 끊길 수 있다.

    Args:
        inSkinBone: 스킨 본(이름·handle·NodeRef)
        inParentBone: 새 부모(이름·handle·NodeRef) 또는 None

    Returns:
        readback dict. modified에 ``[스킨 본]``, details에
        ``{"parent": 호출 뒤 실제 부모 NodeRef | None, "parentProperty": 기록된 프로퍼티 문자열}``.

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(자기 자신이나 자손을 부모로 지정),
            OPERATION_FAILED(원본 예외, 또는 호출 뒤 부모가 요청과 다름)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bone; result = bone.set_skin_bone_parent("b_Spine1", "b_Spine")
    """
    if inParentBone is None:
        skinBone = ags.resolve_node(inSkinBone)
        parentBone = None
    else:
        skinBone, parentBone = ags.resolve_nodes([inSkinBone, inParentBone])
        skinHandle = _handle(skinBone)
        cursor = parentBone
        while cursor is not None:
            if _handle(cursor) == skinHandle:
                raise ags.AgentApiError(
                    ags.INVALID_ARGUMENT,
                    "자기 자신이나 자손을 부모로 지정할 수 없다",
                    {"skinBone": ags.node_ref(skinBone), "parent": ags.node_ref(parentBone)},
                )
            cursor = cursor.parent

    header = _header()
    rt = _runtime()
    try:
        header.bone.set_skin_bone_parent(skinBone, parentBone)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "스킨 본 부모 지정", {"skinBone": ags.node_ref(skinBone)}) from error

    actualParent = skinBone.parent
    if parentBone is not None and (actualParent is None or _handle(actualParent) != _handle(parentBone)):
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "호출 뒤 스킨 본의 부모가 요청한 노드가 아니다",
            {
                "skinBone": ags.node_ref(skinBone),
                "requestedParent": ags.node_ref(parentBone),
                "actualParent": None if actualParent is None else ags.node_ref(actualParent),
            },
        )
    parentProperty = _user_prop_text(rt, skinBone, "Parent")
    return ags.readback(
        modified=[skinBone],
        details={
            "parent": None if actualParent is None else ags.node_ref(actualParent),
            "parentProperty": "undefined" if parentProperty is None else parentProperty,
        },
    )


def sort_bones_by_hierarchy(inNodes: list) -> dict:
    """이름으로 받은 본들을 계층 깊이 순(루트에 가까운 순)으로 정렬한다.

    같은 깊이끼리는 입력 순서를 유지한다(안정 정렬).

    Args:
        inNodes: 정렬할 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"nodes": [NodeRef, ...]}`` — 정렬된 순서

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bone; result = bone.sort_bones_by_hierarchy(["Bip001 Spine", "Bip001 Pelvis"])
    """
    nodes = ags.resolve_nodes(inNodes)
    header = _header()
    try:
        ordered = header.bone.sort_bones_as_hierarchy(nodes)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "계층 순 정렬") from error
    return {"nodes": [ags.node_ref(node) for node in ordered]}


def is_bip_skin_bone(inNodes: list) -> dict:
    """스킨 본마다 원본 본(OriBone)의 컨트롤러가 Biped 계열인지 판정한다.

    스킨 본이 아니거나 원본 본을 찾지 못하면 False다. 원본 본 평가가 실패하면 False로 두고
    warnings에 적는다.

    Args:
        inNodes: 판정할 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"results": [{"node": NodeRef, "isBipSkinBone": bool}], "warnings": [str]}`` — 입력 순서

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bone; result = bone.is_bip_skin_bone(["b_Spine"])
    """
    nodes = ags.resolve_nodes(inNodes)
    header = _header()
    results = []
    warnings = []
    for node in nodes:
        nodeRef = ags.node_ref(node)
        try:
            value = bool(header.bone.is_bip_skin_bone(node))
        except Exception as error:  # noqa: BLE001 - 항목 단위 실패는 warnings로 남긴다
            warnings.append(f"'{nodeRef['name']}': 판정 중 원본 처리가 실패해 False로 두었다({error!r})")
            value = False
        results.append({"node": nodeRef, "isBipSkinBone": value})
    return {"results": results, "warnings": warnings}


# ---------------------------------------------------------------------------
# 스킨 본 생성 공통 보조
# ---------------------------------------------------------------------------


def _require_skin_bone_args(inNodes, inSkipNub, inMesh, inLink, inSkinBoneBaseName) -> None:
    """스킨 본 생성에 필요한 공통 인자의 형을 검사한다. 노드 해석 전에 끝낸다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    _require_bool(inSkipNub, "inSkipNub")
    _require_bool(inMesh, "inMesh")
    _require_bool(inLink, "inLink")
    if inSkinBoneBaseName is not None and (not isinstance(inSkinBoneBaseName, str) or inSkinBoneBaseName.strip() == ""):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inSkinBoneBaseName은 None 또는 비어 있지 않은 문자열이어야 한다",
            {"argument": "inSkinBoneBaseName", "input": repr(inSkinBoneBaseName)},
        )
    if isinstance(inNodes, (list, tuple)) and len(inNodes) == 0:
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, "inNodes가 비어 있다", {"argument": "inNodes"})


def _resolve_distinct(inNodes) -> list:
    """노드 목록을 해석하고 같은 노드가 두 번 들어오면 거절한다.

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(중복 노드 — ``details["duplicates"]``)
    """
    nodes = ags.resolve_nodes(inNodes)
    seen = set()
    duplicates = []
    for node in nodes:
        handle = _handle(node)
        if handle in seen:
            duplicates.append(ags.node_ref(node))
        seen.add(handle)
    if duplicates:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, "inNodes에 같은 노드가 두 번 이상 있다", {"argument": "inNodes", "duplicates": duplicates}
        )
    return nodes


def _ori_bone_name(inRt, inSkinBone) -> str | None:
    """스킨 본의 ``OriBone`` 프로퍼티(``$'이름'``)에서 이름만 읽는다(평가하지 않는다)."""
    text = _user_prop_text(inRt, inSkinBone, "OriBone")
    if text is None:
        return None
    text = text.strip()
    if text.startswith("$'") and text.endswith("'") and len(text) >= 3:
        return text[2:-1]
    return None


def _pair_sources(inRt, inBoneService, inSkinBones: list, inSources: list, inLink: bool, inBaseName) -> tuple:
    """원본이 돌려준 스킨 본마다 원본 본(입력 노드)을 찾는다(읽기만 한다).

    inLink=True면 원본이 기록한 ``OriBone`` 프로퍼티의 이름으로, False면 원본의 스킨 본 이름 규칙
    (``gen_skin_bone_name``)으로 입력 노드와 맞춘다. 입력 중 이름이 하나로 맞는 노드만 짝으로 삼는다.

    Returns:
        ``([(원본 노드, 스킨 본)], [짝을 못 찾은 스킨 본])``
    """
    pairs = []
    unpaired = []
    used = set()
    for skinBone in inSkinBones:
        if inLink:
            key = _ori_bone_name(inRt, skinBone)
            candidates = [node for node in inSources if key is not None and str(node.name) == key]
        else:
            skinName = str(skinBone.name)
            candidates = [
                node
                for node in inSources
                if str(inBoneService.gen_skin_bone_name(str(node.name), inSkinBoneBaseName=inBaseName)) == skinName
            ]
        candidates = [node for node in candidates if _handle(node) not in used]
        if len(candidates) == 1:
            used.add(_handle(candidates[0]))
            pairs.append((candidates[0], skinBone))
        else:
            unpaired.append(skinBone)
    return pairs, unpaired


def _same_name_count(inRt, inName: str) -> int:
    """장면에서 이름이 같은(대소문자 무시 — Max 이름 조회 규칙) 노드 수."""
    lowered = inName.lower()
    return sum(1 for node in inRt.objects if inRt.isValidNode(node) and str(node.name).lower() == lowered)


def _run_skin_bone_creation(
    inOperation: str,
    inCall,
    inNodes: list,
    inLink: bool,
    inSkinBoneBaseName,
    inSkipReason: str,
) -> dict:
    """원본 스킨 본 생성 메서드를 부르고 readback을 만든다.

    Args:
        inOperation: 오류 문구에 쓸 작업 이름
        inCall: 원본 메서드를 부르는 인자 없는 callable(원본 반환을 그대로 돌려준다)
        inNodes: 해석한 입력 노드
        inLink: 원본에 넘긴 inLink
        inSkinBoneBaseName: 원본에 넘긴 inSkinBoneBaseName
        inSkipReason: 원본이 입력을 쓰지 않을 때 warnings에 적을 사유

    Raises:
        AgentApiError: PRECONDITION_FAILED(원본이 스킨 본을 하나도 만들지 않음), OPERATION_FAILED
    """
    rt = _runtime()
    boneService = _header().bone
    inputRefs = [ags.node_ref(node) for node in inNodes]

    before = _scene.snapshot_handles()
    try:
        returned = inCall()
    except Exception as error:  # noqa: BLE001 - 원본 예외, 부분 생성을 숨기지 않는다
        partial = [ags.node_ref(node) for node in _scene.created_since(before)]
        raise _original_error(error, inOperation, {"inputs": inputRefs, "created": partial}) from error
    created = _scene.created_since(before)

    skinBones = [node for node in (returned or []) if node is not None and rt.isValidNode(node)]
    if not skinBones:
        if created:
            raise ags.AgentApiError(
                ags.OPERATION_FAILED,
                f"{inOperation}: 원본이 스킨 본을 돌려주지 않았는데 장면에 노드가 생겼다",
                {"inputs": inputRefs, "created": [ags.node_ref(node) for node in created]},
            )
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"{inOperation}: 원본이 만들 대상이 없다(입력이 모두 원본 규칙으로 걸러졌다 — {inSkipReason})",
            {"inputs": inputRefs},
        )

    pairs, unpaired = _pair_sources(rt, boneService, skinBones, inNodes, inLink, inSkinBoneBaseName)
    skinHandles = {_handle(node) for node in skinBones}
    extra = [node for node in created if _handle(node) not in skinHandles]
    usedHandles = {_handle(source) for source, _skin in pairs}

    warnings = []
    for node in inNodes:
        if _handle(node) not in usedHandles:
            warnings.append(f"입력 '{node.name}'은 스킨 본의 원본으로 쓰이지 않았다({inSkipReason})")
    for skinBone in unpaired:
        warnings.append(f"스킨 본 '{skinBone.name}'의 원본 본을 입력에서 하나로 특정하지 못해 pairs에서 뺐다")
    if extra:
        warnings.append(
            f"원본이 스킨 본 밖의 노드 {len(extra)}개를 만들고 장면에 남겼다(inMesh=True 스냅샷 메시 등): "
            + ", ".join(f"'{node.name}'" for node in extra)
        )
    for skinBone in skinBones:
        count = _same_name_count(rt, str(skinBone.name))
        if count > 1:
            warnings.append(
                f"스킨 본 이름 '{skinBone.name}'인 노드가 장면에 {count}개다(이름 충돌 — 원본은 부모를 첫 일치 노드로 연결한다)"
            )
    notCreated = [node for node in skinBones if not any(_handle(item) == _handle(node) for item in created)]
    if notCreated:
        warnings.append(f"원본이 돌려준 스킨 본 중 {len(notCreated)}개는 이번 호출 전부터 있던 노드다")

    modified = [source for source, _skin in pairs] if inLink else []
    return ags.readback(
        created=created,
        modified=modified,
        details={
            "skinBones": [ags.node_ref(node) for node in skinBones],
            "pairs": [{"source": ags.node_ref(source), "skinBone": ags.node_ref(skin)} for source, skin in pairs],
            "extraCreated": [ags.node_ref(node) for node in extra],
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 스킨 본 생성
# ---------------------------------------------------------------------------


def create_skin_bones(
    inNodes: list,
    inSkipNub: bool = True,
    inMesh: bool = True,
    inLink: bool = True,
    inSkinBoneBaseName: str | None = None,
) -> dict:
    """원본 본들로 스킨 본을 만들고 원본 계층대로 부모를 잇는다.

    원본 ``create_skin_bones``를 그대로 부른다. 원본은 입력을 계층 순으로 정렬하고, 본마다 같은
    변환의 스킨 본(이름 Base = 스킨 본 Base, 기본 ``b``)을 만들어 사용자 프로퍼티
    ``IsSkinBone``·``Parent``를 기록한다. inLink=True면 ``OriBone``을 기록하고 Link_Constraint로
    원본 본에 연결한다(원본 본에도 ``WorldSpaceMatrix`` 등 사용자 프로퍼티가 기록된다). 부모는
    원본 본의 부모 이름으로 만든 스킨 본 이름을 ``getNodeByName``(첫 일치)으로 찾아 잇는다 — 같은
    이름 노드가 이미 있으면 다른 노드에 붙을 수 있다(warnings). **inMesh=True면 원본이 본마다
    스냅샷 메시를 만들고 붙이지도 지우지도 않아 장면에 남는다**(``details.extraCreated``·warnings).
    입력 중 스킨 본의 원본으로 쓰이지 않은 노드(inSkipNub=True의 끝 본 등)는 warnings에 적는다.

    Args:
        inNodes: 원본 본 목록(이름·handle·NodeRef). 비어 있으면 안 되고 같은 노드가 두 번 있으면 안 된다
        inSkipNub: True면 끝 본(부모는 있고 자식이 없는 BoneGeometry)을 건너뛴다
        inMesh: True면 원본 메시 스냅샷을 만들고 스킨 본에 Edit_Poly를 붙인다
        inLink: True면 스킨 본을 원본 본에 Link_Constraint로 연결하고 OriBone을 기록한다
        inSkinBoneBaseName: 스킨 본 이름의 Base 파트. None이면 이름 설정의 SkinBone 값

    Returns:
        readback dict. ``created``=이번 호출로 생긴 장면 노드 전부(스킨 본 + 부수 생성물, 장면 handle
        차이), ``modified``=inLink=True일 때 연결된 원본 본, ``details={"skinBones": [NodeRef](원본
        반환 순서), "pairs": [{"source": NodeRef, "skinBone": NodeRef}], "extraCreated": [NodeRef]}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드·bool 인자·inSkinBoneBaseName 형 오류),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, PRECONDITION_FAILED(대상 0개 — 입력이 모두 끝 본이라
            원본이 아무것도 만들지 않음), OPERATION_FAILED(원본 예외 — ``details["created"]``에 이미
            생긴 노드, ``details["exception"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bone; result = bone.create_skin_bones(["Bone_Arm", "Bone_Forearm"], inMesh=False)
    """
    _require_skin_bone_args(inNodes, inSkipNub, inMesh, inLink, inSkinBoneBaseName)
    nodes = _resolve_distinct(inNodes)
    boneService = _header().bone
    return _run_skin_bone_creation(
        "스킨 본 생성",
        lambda: boneService.create_skin_bones(
            list(nodes),
            inSkipNub=inSkipNub,
            inMesh=inMesh,
            inLink=inLink,
            inSkinBoneBaseName=inSkinBoneBaseName,
        ),
        nodes,
        inLink,
        inSkinBoneBaseName,
        "inSkipNub=True면 원본이 끝 본을 건너뛴다",
    )


def create_skin_bones_from_biped(
    inNodes: list,
    inSkipNub: bool = True,
    inMesh: bool = False,
    inLink: bool = True,
    inSkinBoneBaseName: str | None = None,
) -> dict:
    """Biped 노드들로 스킨 본을 만든다(원본 ``create_skin_bone_from_bip``을 그대로 부른다).

    원본은 입력에서 ``Biped_Object``가 아닌 노드와 COM(루트)을 빼고 나머지로 ``create_skin_bones``를
    부른다. 원본 docstring은 "Twist 제외"라고 하지만 **트위스트 필터가 동작하지 않아**(bone.py
    ``item.name.lower``를 호출하지 않고 넘김) **트위스트 Biped 본도 스킨 본이 만들어진다.** 이 함수는
    원본을 고치거나 따로 거르지 않는다 — 넘긴 Biped 본은 모두 스킨 본이 된다. 원본이 뺀 입력
    (비 Biped_Object·COM·끝 본)은 이름과 함께 warnings에 적는다. inMesh=True의 스냅샷 잔여물·이름
    충돌도 ``create_skin_bones``와 같이 보고한다.

    Args:
        inNodes: Biped 노드 목록(이름·handle·NodeRef). 비어 있으면 안 되고 같은 노드가 두 번 있으면 안 된다
        inSkipNub: True면 끝 본(BoneGeometry 끝 본)을 건너뛴다
        inMesh: True면 원본 메시 스냅샷을 만들고 스킨 본에 Edit_Poly를 붙인다
        inLink: True면 스킨 본을 원본 Biped 본에 Link_Constraint로 연결하고 OriBone을 기록한다
        inSkinBoneBaseName: 스킨 본 이름의 Base 파트. None이면 이름 설정의 SkinBone 값

    Returns:
        ``create_skin_bones``와 같은 readback dict(``details``의 skinBones·pairs·extraCreated)

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드·bool 인자·inSkinBoneBaseName 형 오류),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, PRECONDITION_FAILED(대상 Biped 노드 0개 — 원본이 입력을
            모두 걸러 아무것도 만들지 않음), OPERATION_FAILED(원본 예외 — ``details["created"]``·
            ``details["exception"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bone; result = bone.create_skin_bones_from_biped(["Bip001 Pelvis", "Bip001 Spine"])
    """
    _require_skin_bone_args(inNodes, inSkipNub, inMesh, inLink, inSkinBoneBaseName)
    nodes = _resolve_distinct(inNodes)
    boneService = _header().bone
    return _run_skin_bone_creation(
        "Biped 스킨 본 생성",
        lambda: boneService.create_skin_bone_from_bip(
            list(nodes),
            inSkipNub=inSkipNub,
            inMesh=inMesh,
            inLink=inLink,
            inSkinBoneBaseName=inSkinBoneBaseName,
        ),
        nodes,
        inLink,
        inSkinBoneBaseName,
        "원본이 Biped_Object가 아닌 노드·COM(루트)·inSkipNub=True의 끝 본을 뺀다",
    )
