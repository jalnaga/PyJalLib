# -*- coding: utf-8 -*-
"""UE5 스켈레톤 에이전트 인터페이스 — 에이전트가 Biped 스킨 본을 UE5 스켈레톤 규칙으로 회전·이름 변경하고 스파인·목·너클 본을 더한다.

함수 목록:
    rotate_biped_skin_bones_to_ue5 — Biped 스킨 본을 그룹별 고정 각도로 로컬 회전한다(한 번만 호출) [scene]
    rename_biped_skin_bones_to_ue5 — Biped 스킨 본 이름을 UE5 이름 규칙으로 바꾼다 [scene]
    add_ue5_spine_skin_bones — 스파인 스킨 본을 UE5 기준 개수(5)까지 더하고 목·쇄골을 다시 잇는다 [scene]
    add_ue5_neck_skin_bones — 목 스킨 본을 UE5 기준 개수(2)까지 더하고 머리를 다시 잇는다 [scene]
    create_ue5_knuckle_skin_bones — 엄지를 뺀 손가락마다 너클(Metacarpal) 스킨 본을 만든다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    입력은 ``bone.create_skin_bones_from_biped``(원본 ``create_skin_bone_from_bip``)로 만든 **링크된
    Biped 스킨 본**이다(사용자 프로퍼티 ``OriBone``이 Biped 노드를 가리킨다). Biped 스킨 본이 아닌
    입력은 원본이 조용히 건너뛰므로 warnings에 적고, 대상이 하나도 없으면 PRECONDITION_FAILED다.
    원본은 첫 Biped 스킨 본의 Biped를 기준으로 그룹을 찾는다 — 한 번에 Biped 하나의 스킨 본만 넘긴다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 순서(PyJalMaxRiggingTool ``func/bip.py``의 실제 순서):
    1. ``bone.create_skin_bones_from_biped`` — 스킨 본 생성
    2. ``rotate_biped_skin_bones_to_ue5`` — 회전. **한 번만** 부른다(원본이 멱등이 아니라 다시 부르면
       회전이 누적된다). 새 스파인·목 본은 기존 본의 변환을 복사하므로 회전을 먼저 한다
    3. ``add_ue5_spine_skin_bones`` → ``add_ue5_neck_skin_bones`` → ``create_ue5_knuckle_skin_bones``
       — 각각 **한 번만** 부른다. 원본은 Biped의 스파인·목 개수로 판정하므로 다시 부르면 본이 중복
       생성된다. 입력은 1의 스킨 본을 계층 순(생성 순) 그대로 넘긴다
    4. ``rename_biped_skin_bones_to_ue5`` — 이름 변경은 마지막에 한다. 원본 스파인·목 추가는 스킨 본
       이름의 번호로 새 본 개수를 정하므로 이름을 바꾼 뒤에 부르면 본이 과다 생성될 수 있다

호출 예:
    from pyjallib.max.agentapi import ue5Skeleton; result = ue5Skeleton.rotate_biped_skin_bones_to_ue5(["b_Pelvis", "b_Spine"])
"""

from pyjallib.max import agentSupport as ags
from pyjallib.max.agentapi import _scene


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


def _handle(inNode) -> int:
    """노드 동일성 비교용 노드 handle."""
    return int(inNode.inode.handle)


def _original_error(inError: Exception, inAction: str, inDetails: dict | None = None) -> ags.AgentApiError:
    """원본 메서드 예외를 AgentApiError로 바꾼다(명세 C-3).

    ValueError는 INVALID_ARGUMENT, 그 밖은 OPERATION_FAILED. ``details.exception``에 repr을 담는다.
    """
    code = ags.INVALID_ARGUMENT if isinstance(inError, ValueError) else ags.OPERATION_FAILED
    details = dict(inDetails or {})
    details["exception"] = repr(inError)
    return ags.AgentApiError(code, f"{inAction} 중 원본 처리가 실패했다: {inError}", details)


def _call(inAction: str, inFunc, *args, **kwargs):
    """원본 조회 메서드를 부르고 예외를 계약 코드로 바꾼다."""
    try:
        return inFunc(*args, **kwargs)
    except ags.AgentApiError:
        raise
    except Exception as error:  # noqa: BLE001 - C-3
        raise _original_error(error, inAction) from error


def _resolve_inputs(inSkinBones) -> list:
    """입력 목록을 해석한다. 빈 목록·같은 노드 중복은 거절한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT, NODE_NOT_FOUND, NODE_AMBIGUOUS
    """
    if isinstance(inSkinBones, (list, tuple)) and len(inSkinBones) == 0:
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, "inSkinBones가 비어 있다", {"argument": "inSkinBones"})
    nodes = ags.resolve_nodes(inSkinBones)
    seen = set()
    duplicates = []
    for node in nodes:
        if _handle(node) in seen:
            duplicates.append(ags.node_ref(node))
        seen.add(_handle(node))
    if duplicates:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inSkinBones에 같은 노드가 두 번 이상 있다",
            {"argument": "inSkinBones", "duplicates": duplicates},
        )
    return nodes


def _split_biped_skin_bones(inHeader, inNodes: list) -> tuple:
    """입력을 원본 판정(``is_bip_skin_bone``)으로 Biped 스킨 본과 나머지로 나눈다.

    Returns:
        ``(Biped 스킨 본 list, 걸러진 입력 list)`` — 입력 순서 유지
    """
    bipSkinBones = []
    filtered = []
    for node in inNodes:
        if _call("Biped 스킨 본 판정", inHeader.bone.is_bip_skin_bone, node):
            bipSkinBones.append(node)
        else:
            filtered.append(node)
    return bipSkinBones, filtered


def _require_targets(inAction: str, inNodes: list, inBipSkinBones: list) -> None:
    """Biped 스킨 본이 하나도 없으면 PRECONDITION_FAILED.

    Raises:
        AgentApiError: PRECONDITION_FAILED
    """
    if not inBipSkinBones:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"{inAction}: 입력에 Biped 스킨 본(OriBone이 Biped 노드인 스킨 본)이 하나도 없다",
            {"inputs": [ags.node_ref(node) for node in inNodes]},
        )


def _filtered_warnings(inFiltered: list) -> list:
    """원본이 건너뛰는 입력의 warnings 문구."""
    return [f"입력 '{node.name}'은 Biped 스킨 본이 아니어서 원본이 건너뛰었다" for node in inFiltered]


def _ori_handle(inHeader, inRt, inSkinBone):
    """스킨 본의 원본 본 handle(원본 ``get_skin_bone_ori_bone``으로 평가). 못 찾으면 None."""
    ori = _call("원본 본 조회", inHeader.bone.get_skin_bone_ori_bone, inSkinBone)
    if ori is None or not inRt.isValidNode(ori):
        return None
    return _handle(ori)


def _skin_for(inOriHandles: list, inBipNode):
    """원본 본이 inBipNode인 첫 스킨 본(입력 순서). 없으면 None."""
    if inBipNode is None:
        return None
    target = _handle(inBipNode)
    for skinBone, oriHandle in inOriHandles:
        if oriHandle == target:
            return skinBone
    return None


def _ori_handle_map(inHeader, inRt, inBipSkinBones: list) -> list:
    """``[(스킨 본, 원본 본 handle 또는 None)]``(입력 순서 유지)."""
    return [(skinBone, _ori_handle(inHeader, inRt, skinBone)) for skinBone in inBipSkinBones]


def _first_ori_bone(inHeader, inBipSkinBones: list):
    """원본이 기준으로 삼는 첫 Biped 스킨 본의 원본 Biped 노드."""
    return _call("원본 본 조회", inHeader.bone.get_skin_bone_ori_bone, inBipSkinBones[0])


def _group(inHeader, inBipNode, inGroupName: str) -> list:
    """원본 ``get_grouped_nodes``로 Biped 그룹 노드 목록을 읽는다."""
    return list(_call("Biped 그룹 조회", inHeader.bip.get_grouped_nodes, inBipNode, inGroupName) or [])


def _parents(inNodes: list) -> dict:
    """``{handle: 부모 handle 또는 None}``."""
    return {_handle(node): (_handle(node.parent) if node.parent is not None else None) for node in inNodes}


def _reparented(inNodes: list, inBefore: dict, inRt) -> list:
    """호출 전후 부모가 바뀐 노드(입력 순서)."""
    changed = []
    for node in inNodes:
        if not inRt.isValidNode(node):
            continue
        parent = _handle(node.parent) if node.parent is not None else None
        if inBefore.get(_handle(node)) != parent:
            changed.append(node)
    return changed


def _transform_key(inNode) -> tuple:
    """노드 변환 행렬 비교값."""
    tm = inNode.transform
    return tuple(float(value) for row in (tm.row1, tm.row2, tm.row3, tm.row4) for value in row)


def _missing_error(inAction: str, inMissing: list) -> ags.AgentApiError:
    """필수 입력 누락 PRECONDITION_FAILED(``details.missing``)."""
    return ags.AgentApiError(
        ags.PRECONDITION_FAILED,
        f"{inAction}: 원본이 쓰는 스킨 본이 입력에 없다: {', '.join(inMissing)}",
        {"missing": inMissing},
    )


def _run_add_bones(inAction: str, inFunc, inNodes: list, inExtraDetails: dict, inWarnings: list) -> dict:
    """본을 더하는 원본(U3·U4·U5)을 부르고 readback을 만든다.

    created는 장면 handle 차이, modified는 입력 중 부모가 바뀐 노드다.
    """
    rt = _runtime()
    parentsBefore = _parents(inNodes)
    before = _scene.snapshot_handles()
    try:
        returned = inFunc(list(inNodes))
    except Exception as error:  # noqa: BLE001 - C-3, 부분 적용을 숨기지 않는다
        raise _original_error(
            error,
            inAction,
            {
                "created": [ags.node_ref(node) for node in _scene.created_since(before)],
                "applied": [ags.node_ref(node) for node in _reparented(inNodes, parentsBefore, rt)],
            },
        ) from error
    created = _scene.created_since(before)
    modified = _reparented(inNodes, parentsBefore, rt)
    warnings = list(inWarnings)
    if returned is not None:
        # 원본 create_knuckles_skin_bones는 반환문이 없어 None이다 — 그때는 장면 차이만 쓴다
        returnedNodes = [node for node in returned if node is not None and rt.isValidNode(node)]
        createdHandles = {_handle(node) for node in created}
        if len(returnedNodes) != len(created) or any(_handle(node) not in createdHandles for node in returnedNodes):
            warnings.append(
                f"원본이 돌려준 새 본({len(returnedNodes)}개)과 장면에 실제로 생긴 노드({len(created)}개)가 다르다"
            )
    details = {"added": len(created)}
    details.update(inExtraDetails)
    return ags.readback(created=created, modified=modified, details=details, warnings=warnings)


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def rotate_biped_skin_bones_to_ue5(inSkinBones: list) -> dict:
    """Biped 스킨 본을 UE5 축 방향에 맞게 Biped 그룹별 고정 각도로 로컬 회전한다(자식은 그대로).

    원본 ``rotate_bip_skin_bones``를 그대로 부른다. 각도는 원본 표(``bipRotDict``)를 따른다
    (예: pelvis·spine·neck·head [180, 0, 0], rArm [0, 0, 180], lArm [0, 0, 0]). **원본은 멱등이 아니다
    — 같은 본에 다시 부르면 회전이 누적되므로 한 번만 호출한다.** 원본 본이 같은 스킨 본이 여럿이면
    원본은 입력 순서상 첫 스킨 본만 회전한다. Biped 스킨 본이 아닌 입력과 회전 표 그룹에 없는 본은
    warnings에 적는다.

    Args:
        inSkinBones: Biped 스킨 본 목록(이름·handle·NodeRef). 비어 있으면 안 되고 중복이 없어야 한다

    Returns:
        readback dict. ``modified``=변환이 실제로 바뀐 본, ``details={"rotations": [{"node": NodeRef,
        "group": str, "angles": [x, y, z]}]}`` — 원본이 회전 대상으로 삼은 본마다(각도 0 포함)

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(대상 0개 — Biped 스킨 본이 하나도 없음), OPERATION_FAILED(원본 예외 —
            ``details["applied"]``에 이미 회전한 본)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import ue5Skeleton; result = ue5Skeleton.rotate_biped_skin_bones_to_ue5(["b_Pelvis", "b_Spine", "b_L_Thigh"])
    """
    nodes = _resolve_inputs(inSkinBones)
    header = _header()
    rt = _runtime()
    bipSkinBones, filtered = _split_biped_skin_bones(header, nodes)
    _require_targets("UE5 회전", nodes, bipSkinBones)

    ue5 = header.ue5Skeleton
    oriHandles = _ori_handle_map(header, rt, bipSkinBones)
    groups = _call("Biped 그룹 조회", header.bip.get_all_grouped_nodes, _first_ori_bone(header, bipSkinBones))
    rotTable = dict(ue5.bipRotDict)

    # 원본이 회전 대상으로 삼는 본(그룹 순회·원본 본마다 첫 스킨 본)을 읽기만 한다
    planned = []
    plannedHandles = set()
    for groupName, groupNodes in (groups or {}).items():
        if groupName not in rotTable:
            continue
        for bipNode in groupNodes or []:
            skinBone = _skin_for(oriHandles, bipNode)
            if skinBone is not None and _handle(skinBone) not in plannedHandles:
                plannedHandles.add(_handle(skinBone))
                planned.append((skinBone, groupName, list(rotTable[groupName])))

    transformsBefore = {_handle(node): _transform_key(node) for node in bipSkinBones}
    try:
        ue5.rotate_bip_skin_bones(list(nodes))
    except Exception as error:  # noqa: BLE001 - C-3, 부분 적용을 숨기지 않는다
        applied = [ags.node_ref(node) for node in bipSkinBones if _transform_key(node) != transformsBefore[_handle(node)]]
        raise _original_error(error, "UE5 회전", {"applied": applied}) from error

    modified = [node for node in bipSkinBones if _transform_key(node) != transformsBefore[_handle(node)]]
    warnings = _filtered_warnings(filtered)
    for node in bipSkinBones:
        if _handle(node) not in plannedHandles:
            warnings.append(f"Biped 스킨 본 '{node.name}'은 원본 회전 표의 그룹에 속하지 않아 회전하지 않았다")

    return ags.readback(
        modified=modified,
        details={
            "rotations": [
                {"node": ags.node_ref(skinBone), "group": str(groupName), "angles": angles}
                for skinBone, groupName, angles in planned
            ]
        },
        warnings=warnings,
    )


def rename_biped_skin_bones_to_ue5(inSkinBones: list) -> dict:
    """Biped 스킨 본(몸통·팔다리·손가락·발가락) 이름을 UE5 이름 규칙으로 바꾼다.

    원본 ``convert_bip_skin_bone_name_to_ue5``를 그대로 부른다(예: L UpperArm → ``b_L_Upperarm``,
    Spine → ``b_Spine_01``, L Finger1 → ``b_L_Index_01``). 원본은 손가락 첫 마디의 부모가 너클
    (Metacarpal) 본이면 **입력에 없는 그 너클 본의 이름도 바꾼다.** 결과는 호출 전후 장면 노드 이름을
    비교해 실제로 이름이 바뀐 노드로 돌려준다. 이름이 바뀌지 않은 입력, Biped 스킨 본이 아닌 입력,
    바뀐 뒤 같은 이름이 된 노드는 warnings에 적는다. 다른 스킨 본의 ``OriBone``·``Parent`` 프로퍼티는
    이름 문자열이라 이름이 바뀐 본을 가리키던 참조는 끊길 수 있다(원본 동작).

    Args:
        inSkinBones: Biped 스킨 본 목록(이름·handle·NodeRef). 비어 있으면 안 되고 중복이 없어야 한다

    Returns:
        readback dict. ``modified``=이름이 실제로 바뀐 노드, ``details={"renamed": [{"handle": int,
        "before": str, "after": str}]}`` (handle 오름차순)

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(대상 0개 — Biped 스킨 본이 하나도 없음), OPERATION_FAILED(원본 예외 —
            ``details["renamed"]``에 이미 바뀐 이름)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import ue5Skeleton; result = ue5Skeleton.rename_biped_skin_bones_to_ue5(["b_Pelvis", "b_Spine", "b_L_UpperArm"])
    """
    nodes = _resolve_inputs(inSkinBones)
    header = _header()
    rt = _runtime()
    bipSkinBones, filtered = _split_biped_skin_bones(header, nodes)
    _require_targets("UE5 이름 변경", nodes, bipSkinBones)

    def _scene_names() -> dict:
        return {_handle(node): str(node.name) for node in rt.objects if rt.isValidNode(node)}

    def _renamed(inBefore: dict) -> list:
        after = _scene_names()
        return [
            {"handle": handle, "before": inBefore[handle], "after": after[handle]}
            for handle in sorted(inBefore)
            if handle in after and after[handle] != inBefore[handle]
        ]

    namesBefore = _scene_names()
    try:
        header.ue5Skeleton.convert_bip_skin_bone_name_to_ue5(list(nodes))
    except Exception as error:  # noqa: BLE001 - C-3, 부분 적용을 숨기지 않는다
        raise _original_error(error, "UE5 이름 변경", {"renamed": _renamed(namesBefore)}) from error

    renamed = _renamed(namesBefore)
    renamedHandles = {entry["handle"] for entry in renamed}
    modified = [rt.maxOps.getNodeByHandle(entry["handle"]) for entry in renamed]

    warnings = _filtered_warnings(filtered)
    for node in bipSkinBones:
        if _handle(node) not in renamedHandles:
            warnings.append(f"Biped 스킨 본 '{node.name}'은 이름이 바뀌지 않았다(이미 UE5 이름이거나 변환 규칙 밖)")
    afterNames = {}
    for node in rt.objects:
        if rt.isValidNode(node):
            afterNames.setdefault(str(node.name).lower(), []).append(_handle(node))
    for entry in renamed:
        sameName = afterNames.get(entry["after"].lower(), [])
        if len(sameName) > 1:
            warnings.append(f"바뀐 이름 '{entry['after']}'인 노드가 장면에 {len(sameName)}개다(이름 중복)")

    return ags.readback(modified=modified, details={"renamed": renamed}, warnings=warnings)


def add_ue5_spine_skin_bones(inSkinBones: list) -> dict:
    """스파인 스킨 본을 UE5 기준 개수(5개)까지 더하고 목·양 쇄골 스킨 본을 마지막 새 스파인 아래로 옮긴다.

    원본 ``match_spine_skin_bone_numbers_to_ue5``를 그대로 부른다. 원본은 **입력 순서상 마지막 스파인
    스킨 본**과 목 스킨 본 사이를 나눠 새 본을 만들고, 새 본 개수는 Biped 스파인 수와 마지막 스파인
    스킨 본 이름의 번호로 정한다 — 스킨 본을 생성 순(계층 순)으로, 이름 변경 전에 넘긴다. **한 번만
    호출한다**(원본은 Biped 스파인 수로 판정하므로 다시 부르면 본이 중복 생성된다). Biped 스파인이
    이미 5개 이상이면 오류가 아니라 ``added: 0``·``reason: "already_enough"``다. 새 본의 ``OriBone``은
    마지막 Biped 스파인이다.

    Args:
        inSkinBones: 같은 Biped의 스킨 본 목록(이름·handle·NodeRef). 스파인·목·양 쇄골 스킨 본이 있어야 한다

    Returns:
        readback dict. ``created``=새 스파인 스킨 본(장면 handle 차이), ``modified``=부모가 바뀐 입력
        (목·좌우 쇄골 스킨 본), ``details={"added": int, "reason": "already_enough"(이미 충분할 때만)}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(대상 0개, 입력에 스파인·목·쇄골 스킨 본 누락 — ``details["missing"]``),
            OPERATION_FAILED(원본 예외 — ``details["created"]``·``details["applied"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import ue5Skeleton; result = ue5Skeleton.add_ue5_spine_skin_bones(["b_Pelvis", "b_Spine", "b_Spine1", "b_Neck", "b_L_Clavicle", "b_R_Clavicle"])
    """
    nodes = _resolve_inputs(inSkinBones)
    header = _header()
    rt = _runtime()
    bipSkinBones, filtered = _split_biped_skin_bones(header, nodes)
    _require_targets("UE5 스파인 추가", nodes, bipSkinBones)

    ue5 = header.ue5Skeleton
    firstOri = _first_ori_bone(header, bipSkinBones)
    spines = _group(header, firstOri, "spine")
    alreadyEnough = len(spines) >= int(ue5.ue5SpineNum)
    if not alreadyEnough:
        # (나) 사전 검사: 원본이 입력에서 찾는 스킨 본이 없으면 원본이 IndexError·AttributeError로 죽는다
        oriHandles = _ori_handle_map(header, rt, bipSkinBones)
        spineHandles = {_handle(node) for node in spines}
        missing = []
        if not any(handle in spineHandles for _skin, handle in oriHandles):
            missing.append("스파인(" + ", ".join(str(node.name) for node in spines) + ")")
        for groupName, label in (("neck", "목"), ("lArm", "왼쪽 쇄골"), ("rArm", "오른쪽 쇄골")):
            groupNodes = _group(header, firstOri, groupName)
            if not groupNodes:
                missing.append(f"{label}(Biped 그룹 '{groupName}'이 비었다)")
            elif _skin_for(oriHandles, groupNodes[0]) is None:
                missing.append(str(groupNodes[0].name))
        if missing:
            raise _missing_error("UE5 스파인 추가", missing)

    extra = {"reason": "already_enough"} if alreadyEnough else {}
    return _run_add_bones(
        "UE5 스파인 추가", ue5.match_spine_skin_bone_numbers_to_ue5, nodes, extra, _filtered_warnings(filtered)
    )


def add_ue5_neck_skin_bones(inSkinBones: list) -> dict:
    """목 스킨 본을 UE5 기준 개수(2개)까지 더하고 머리 스킨 본을 마지막 새 목 아래로 옮긴다.

    원본 ``match_neck_skin_bone_numbers_to_ue5``를 그대로 부른다. 원본은 **입력 순서상 마지막 목 스킨
    본**과 머리 스킨 본 사이를 나눠 새 본을 만들고, 새 본 개수는 Biped 목 수와 마지막 목 스킨 본 이름의
    번호로 정한다 — 스킨 본을 생성 순(계층 순)으로, 이름 변경 전에 넘긴다. **한 번만 호출한다**(다시
    부르면 본이 중복 생성된다). Biped 목이 이미 2개 이상이면 오류가 아니라 ``added: 0``·
    ``reason: "already_enough"``다. 새 본의 ``OriBone``은 마지막 Biped 목이다.

    Args:
        inSkinBones: 같은 Biped의 스킨 본 목록(이름·handle·NodeRef). 목·머리 스킨 본이 있어야 한다

    Returns:
        readback dict. ``created``=새 목 스킨 본(장면 handle 차이), ``modified``=부모가 바뀐 입력
        (머리 스킨 본), ``details={"added": int, "reason": "already_enough"(이미 충분할 때만)}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(대상 0개, 입력에 목·머리 스킨 본 누락 — ``details["missing"]``),
            OPERATION_FAILED(원본 예외 — ``details["created"]``·``details["applied"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import ue5Skeleton; result = ue5Skeleton.add_ue5_neck_skin_bones(["b_Neck", "b_Head"])
    """
    nodes = _resolve_inputs(inSkinBones)
    header = _header()
    rt = _runtime()
    bipSkinBones, filtered = _split_biped_skin_bones(header, nodes)
    _require_targets("UE5 목 추가", nodes, bipSkinBones)

    ue5 = header.ue5Skeleton
    firstOri = _first_ori_bone(header, bipSkinBones)
    necks = _group(header, firstOri, "neck")
    alreadyEnough = len(necks) >= int(ue5.ue5NeckNum)
    if not alreadyEnough:
        # (나) 사전 검사: 원본이 입력에서 찾는 스킨 본이 없으면 원본이 IndexError·AttributeError로 죽는다
        oriHandles = _ori_handle_map(header, rt, bipSkinBones)
        neckHandles = {_handle(node) for node in necks}
        missing = []
        if not any(handle in neckHandles for _skin, handle in oriHandles):
            missing.append("목(" + ", ".join(str(node.name) for node in necks) + ")")
        heads = _group(header, firstOri, "head")
        if not heads:
            missing.append("머리(Biped 그룹 'head'가 비었다)")
        elif _skin_for(oriHandles, heads[0]) is None:
            missing.append(str(heads[0].name))
        if missing:
            raise _missing_error("UE5 목 추가", missing)

    extra = {"reason": "already_enough"} if alreadyEnough else {}
    return _run_add_bones(
        "UE5 목 추가", ue5.match_neck_skin_bone_numbers_to_ue5, nodes, extra, _filtered_warnings(filtered)
    )


def create_ue5_knuckle_skin_bones(inSkinBones: list) -> dict:
    """엄지를 뺀 손가락마다 손등 쪽 너클(Metacarpal) 스킨 본을 만들고 손가락 첫 마디를 그 아래로 옮긴다.

    원본 ``create_knuckles_skin_bones``를 그대로 부른다. 너클은 손 스킨 본과 손가락 첫 마디 사이 거리의
    80% 지점에 놓이고 같은 쪽 손 스킨 본의 자식이 된다. 너클의 ``OriBone``은 Biped 노드가 아니라
    **손 스킨 본**이다(원본 동작 — 너클은 Biped 스킨 본으로 판정되지 않는다). **한 번만 호출한다**
    (다시 부르면 너클이 중복 생성된다). Biped 손가락이 2개 미만이면 오류가 아니라 ``added: 0``·
    ``reason: "fewer_than_two_fingers"``다.

    Args:
        inSkinBones: 같은 Biped의 스킨 본 목록(이름·handle·NodeRef). 손가락 첫 마디가 있는 쪽의 손 스킨
            본이 있어야 한다

    Returns:
        readback dict. ``created``=새 너클 스킨 본(장면 handle 차이), ``modified``=부모가 바뀐 입력(손가락
        첫 마디), ``details={"added": int, "reason": "fewer_than_two_fingers"(손가락 2개 미만일 때만)}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·중복 노드), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(대상 0개, 손가락 첫 마디가 있는 쪽의 손 스킨 본 누락 —
            ``details["missing"]``), OPERATION_FAILED(원본 예외 — ``details["created"]``·``details["applied"]``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import ue5Skeleton; result = ue5Skeleton.create_ue5_knuckle_skin_bones(["b_L_Hand", "b_L_Finger1", "b_L_Finger2"])
    """
    nodes = _resolve_inputs(inSkinBones)
    header = _header()
    rt = _runtime()
    bipSkinBones, filtered = _split_biped_skin_bones(header, nodes)
    _require_targets("UE5 너클 생성", nodes, bipSkinBones)

    firstOri = _first_ori_bone(header, bipSkinBones)
    com = _call("Biped COM 조회", header.bip.get_com, firstOri)
    fingerNum = int(com.controller.fingers)
    fingerLinkNum = int(com.controller.fingerLinks)
    extra = {}
    if fingerNum < 2:
        extra = {"reason": "fewer_than_two_fingers"}
    else:
        # (나) 사전 검사: 손가락 첫 마디 스킨 본이 있는데 같은 쪽 손 스킨 본이 없으면 원본이 예외로 죽는다
        oriHandles = _ori_handle_map(header, rt, bipSkinBones)
        missing = []
        for side, armGroup, fingerGroup in (("왼쪽", "lArm", "lFingers"), ("오른쪽", "rArm", "rFingers")):
            firstLinks = []
            for fingerIndex in range(2, fingerNum + 1):
                linkIndex = (fingerIndex - 1) * fingerLinkNum + 1
                fingerNode = _call(
                    "Biped 손가락 조회", rt.biped.getNode, com.controller, rt.Name(fingerGroup), link=linkIndex
                )
                if fingerNode is not None:
                    firstLinks.append(_handle(fingerNode))
            if not any(handle in firstLinks for _skin, handle in oriHandles):
                continue
            arm = _group(header, firstOri, armGroup)
            if len(arm) < 4:
                missing.append(f"{side} 손(Biped 그룹 '{armGroup}'에 손 노드가 없다)")
            elif _skin_for(oriHandles, arm[3]) is None:
                missing.append(str(arm[3].name))
        if missing:
            raise _missing_error("UE5 너클 생성", missing)

    return _run_add_bones(
        "UE5 너클 생성", header.ue5Skeleton.create_knuckles_skin_bones, nodes, extra, _filtered_warnings(filtered)
    )
