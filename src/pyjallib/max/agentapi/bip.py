# -*- coding: utf-8 -*-
"""Biped 에이전트 인터페이스 — 에이전트가 Biped COM·그룹을 조회하고 BIP 파일을 불러오거나 저장하고 피규어 모드를 바꾼다.

함수 목록:
    get_biped_coms — 장면의 모든 Biped COM을 돌려준다 [none]
    get_biped_group_nodes — Biped 노드의 신체 부위 그룹별 노드를 돌려준다 [none]
    is_biped_object — 노드마다 Biped 관련 객체(BipSlave·Footsteps·COM)인지 판정한다 [none]
    load_bip_file — Biped COM에 BIP 파일을 불러온다(애니메이션 구간이 바뀔 수 있음) [scene]
    save_bip_file — Biped COM의 애니메이션을 BIP 파일로 저장한다(선택 시 레이어 병합) [scene, file]
    set_biped_figure_mode — Biped COM의 피규어 모드를 켜거나 끈다 [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    파일 입출력·피규어 모드 함수는 Biped의 COM(Center of Mass) 노드를 받는다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 예:
    from pyjallib.max.agentapi import bip; result = bip.get_biped_coms()
"""

import os

from pyjallib.max import agentSupport as ags

#: ``Bip.get_all_grouped_nodes``가 쓰는 그룹 이름(bip.py의 NODE_CATEGORIES 값과 같은 순서)
_BIPED_GROUP_NAMES = (
    "lArm",
    "rArm",
    "lFingers",
    "rFingers",
    "lLeg",
    "rLeg",
    "lToes",
    "rToes",
    "spine",
    "tail",
    "head",
    "pelvis",
    "neck",
    "pony1",
    "pony2",
    "prop1",
    "prop2",
    "prop3",
)


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


def _call_original(inOperation: str, inFunc, *args, **kwargs):
    """원본 메서드를 부르고 예외를 계약 코드로 바꾼다(명세 C-3).

    ``AgentApiError``는 그대로 통과시키고, ``ValueError``는 INVALID_ARGUMENT, 그 밖의 예외는
    OPERATION_FAILED로 감싼다. 원인 예외는 ``details["exception"]``과 예외 체인에 남긴다.
    """
    try:
        return inFunc(*args, **kwargs)
    except ags.AgentApiError:
        raise
    except ValueError as error:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, f"{inOperation}: 원본이 인자를 거절했다: {error}", {"exception": repr(error)}
        ) from error
    except Exception as error:  # noqa: BLE001 - pymxs 예외 등은 모두 OPERATION_FAILED로 보고한다
        raise ags.AgentApiError(
            ags.OPERATION_FAILED, f"{inOperation} 중 원본 처리가 실패했다: {error}", {"exception": repr(error)}
        ) from error


def _require_bool(inValue, inArgName: str) -> None:
    """bool 인자인지 확인한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inValue, bool):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 bool이어야 한다: {type(inValue).__name__}",
            {"argument": inArgName, "input": repr(inValue)},
        )


def _require_bip_path(inFilePath, inMustExist: bool) -> str:
    """BIP 파일 경로 인자를 확인하고 절대 경로로 돌려준다.

    Raises:
        AgentApiError: INVALID_ARGUMENT — 문자열이 아님·빈 경로·확장자가 ``.bip``가 아님·
            폴더 경로·(inMustExist일 때) 파일 없음. ``details["kind"]="file"``
    """
    if not isinstance(inFilePath, str) or inFilePath.strip() == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inFilePath는 비어 있지 않은 문자열이어야 한다",
            {"argument": "inFilePath", "input": repr(inFilePath), "kind": "file"},
        )
    path = os.path.abspath(inFilePath)
    if os.path.splitext(path)[1].lower() != ".bip":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, f"BIP 파일 확장자는 .bip여야 한다: {path}", {"file": path, "kind": "file"}
        )
    if os.path.isdir(path):
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, f"파일이 아니라 폴더 경로다: {path}", {"file": path, "kind": "file"})
    if inMustExist and not os.path.isfile(path):
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, f"BIP 파일이 없다: {path}", {"file": path, "kind": "file"})
    return path


def _resolve_com(inBipedRoot):
    """인자를 노드로 해석하고 그 노드가 Biped COM인지 확인한다.

    Returns:
        COM 노드

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT,
            PRECONDITION_FAILED — COM이 아닐 때. ``details["com"]``에 그 노드가 속한 COM
            NodeRef(Biped 관련 객체가 아니면 None)
    """
    node = ags.resolve_node(inBipedRoot)
    rt = _runtime()
    bip = _header().bip

    isBiped = bool(_call_original("Biped 판정", bip.is_biped_object, node))
    comRef = None
    if isBiped:
        try:
            com = node.controller.rootNode
            if com is not None and rt.isValidNode(com):
                comRef = ags.node_ref(com)
        except Exception:  # noqa: BLE001 - rootNode가 없는 Biped 관련 객체는 COM 없음으로 본다
            comRef = None

    nodeRef = ags.node_ref(node)
    if comRef is None or comRef["handle"] != nodeRef["handle"]:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"'{nodeRef['name']}'은 Biped COM이 아니다. COM 노드를 지정해야 한다",
            {"node": nodeRef, "isBipedObject": isBiped, "com": comRef},
        )
    return node


def _animation_range(inRt) -> list:
    """현재 장면 animationRange를 ``[시작, 끝]`` 정수 프레임으로 돌려준다."""
    return [int(inRt.animationRange.start), int(inRt.animationRange.end)]


def _file_stat(inPath: str):
    """파일의 ``(mtime_ns, size)``. 없으면 None."""
    try:
        stat = os.stat(inPath)
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _missing_dirs(inPath: str) -> list:
    """파일 경로의 상위 폴더 중 아직 없는 폴더를 위에서부터 돌려준다."""
    missing = []
    current = os.path.dirname(inPath)
    while current and not os.path.exists(current):
        missing.append(current)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    missing.reverse()
    return missing


def _verify_written(inPath: str, inBeforeStat, inOperation: str, inOriginalReturn) -> int:
    """출력 파일이 실제로 생기거나 갱신됐는지 확인하고 크기를 돌려준다(명세 C-8).

    Raises:
        AgentApiError: OPERATION_FAILED — 파일이 없거나, 덮어쓰기인데 수정 시각·크기가 그대로일 때
    """
    afterStat = _file_stat(inPath)
    if afterStat is None:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"{inOperation} 후 파일이 생기지 않았다: {inPath}",
            {"file": inPath, "originalReturn": ags.to_json(inOriginalReturn)},
        )
    if inBeforeStat is not None and afterStat == inBeforeStat:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"{inOperation} 후 기존 파일이 갱신되지 않았다: {inPath}",
            {"file": inPath, "originalReturn": ags.to_json(inOriginalReturn)},
        )
    return int(afterStat[1])


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def get_biped_coms() -> dict:
    """장면에 있는 모든 Biped의 COM(Center of Mass) 노드를 돌려준다.

    같은 COM은 한 번만 담는다(handle 기준). 순서는 원본이 장면 노드를 훑은 순서다.

    Returns:
        ``{"coms": [NodeRef]}``. Biped가 없으면 빈 목록

    Raises:
        AgentApiError: OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bip; result = bip.get_biped_coms()
    """
    bip = _header().bip
    coms = _call_original("Biped COM 수집", bip.get_coms)
    refs = []
    seen = set()
    for com in coms:
        ref = ags.node_ref(com)
        if ref["handle"] in seen:
            continue
        seen.add(ref["handle"])
        refs.append(ref)
    return {"coms": refs}


def get_biped_group_nodes(inBipedNode: str | int | dict, inGroupName: str | None = None) -> dict:
    """Biped 노드가 속한 Biped의 신체 부위 그룹별 노드를 돌려준다.

    그룹 이름: lArm, rArm, lFingers, rFingers, lLeg, rLeg, lToes, rToes, spine, tail, head,
    pelvis, neck, pony1, pony2, prop1, prop2, prop3. 각 그룹의 노드는 링크 순서다.

    Args:
        inBipedNode: 기준 Biped 노드(이름·handle·NodeRef). COM이 아니어도 같은 Biped면 된다
        inGroupName: 그룹 이름. None이면 모든 그룹을 돌려준다

    Returns:
        inGroupName을 주면 ``{"group": str, "nodes": [NodeRef]}``,
        None이면 ``{"groups": {그룹 이름: [NodeRef]}}``

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(모르는 그룹 이름 —
            ``details["valid"]``에 허용 이름), PRECONDITION_FAILED(Biped_Object가 아님),
            OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bip; result = bip.get_biped_group_nodes("Bip001", "lArm")
    """
    if inGroupName is not None and (not isinstance(inGroupName, str) or inGroupName not in _BIPED_GROUP_NAMES):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"모르는 Biped 그룹 이름이다: {inGroupName!r}",
            {"argument": "inGroupName", "input": repr(inGroupName), "valid": list(_BIPED_GROUP_NAMES)},
        )

    node = ags.resolve_node(inBipedNode)
    rt = _runtime()
    if rt.classOf(node) != rt.Biped_Object:
        nodeRef = ags.node_ref(node)
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"'{nodeRef['name']}'은 Biped_Object가 아니다",
            {"node": nodeRef, "class": nodeRef["class"]},
        )

    bip = _header().bip
    if inGroupName is not None:
        nodes = _call_original("Biped 그룹 노드 조회", bip.get_grouped_nodes, node, inGroupName)
        return {"group": inGroupName, "nodes": [ags.node_ref(item) for item in nodes]}

    grouped = _call_original("Biped 그룹 노드 조회", bip.get_all_grouped_nodes, node)
    return {"groups": {str(group): [ags.node_ref(item) for item in items] for group, items in grouped.items()}}


def is_biped_object(inNodes: list) -> dict:
    """노드마다 Biped 관련 객체인지 판정한다.

    컨트롤러가 BipSlave_control(일반 Biped 본)·Footsteps·Vertical_Horizontal_Turn(COM)이면
    Biped 관련 객체다. 사용자가 Biped 아래에 붙인 일반 노드는 False다.

    Args:
        inNodes: 판정할 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"results": [{"node": NodeRef, "isBiped": bool}]}`` — 입력 순서

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT, OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import bip; result = bip.is_biped_object(["Bip001 Pelvis", "Box001"])
    """
    nodes = ags.resolve_nodes(inNodes)
    bip = _header().bip
    results = []
    for node in nodes:
        isBiped = bool(_call_original("Biped 판정", bip.is_biped_object, node))
        results.append({"node": ags.node_ref(node), "isBiped": isBiped})
    return {"results": results}


def load_bip_file(inBipedRoot: str | int | dict, inFilePath: str) -> dict:
    """Biped COM에 BIP 애니메이션 파일을 불러온다.

    불러오는 동안 피규어 모드를 끄고, 끝나면 피규어 모드가 꺼진 상태로 둔다. 원본은 불러온 키의
    마지막 시간으로 장면 animationRange를 ``0 ~ 마지막 키``로 바꾸고 sliderTime을 0으로 옮길 수
    있다. 바뀌었는지는 ``details``의 전후 구간으로 확인한다. 원본은 ``loadBipFile``의 성공 여부를
    돌려주지 않으므로, 불러오기 자체의 성공은 이 함수가 판정하지 않는다.

    Args:
        inBipedRoot: Biped COM 노드(이름·handle·NodeRef)
        inFilePath: 불러올 ``.bip`` 파일 경로(절대 경로 권장)

    Returns:
        readback dict. ``modified=[COM]``, ``details={"file", "animationRangeBefore",
        "animationRangeAfter", "sliderTime", "figureModeBefore", "figureModeAfter"}``
        (구간은 ``[시작, 끝]`` 프레임). 피규어 모드가 꺼졌거나 구간이 바뀌면 warnings에 적는다

    Raises:
        AgentApiError: INVALID_ARGUMENT(파일 없음·확장자가 .bip가 아님, ``details["kind"]="file"``),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, PRECONDITION_FAILED(COM이 아님 — ``details["com"]``에
            그 노드의 COM), OPERATION_FAILED(원본 예외)

    Side effects: scene
    Undo: no

    Example:
        from pyjallib.max.agentapi import bip; result = bip.load_bip_file("Bip001", "D:/Anim/Walk.bip")
    """
    path = _require_bip_path(inFilePath, inMustExist=True)
    com = _resolve_com(inBipedRoot)
    rt = _runtime()
    bip = _header().bip

    rangeBefore = _animation_range(rt)
    figureModeBefore = bool(com.controller.figureMode)

    _call_original("BIP 파일 불러오기", bip.load_bip_file, com, path)

    rangeAfter = _animation_range(rt)
    figureModeAfter = bool(com.controller.figureMode)
    warnings = []
    if figureModeBefore and not figureModeAfter:
        warnings.append("불러오기 전에 켜져 있던 피규어 모드가 꺼졌다")
    if rangeAfter != rangeBefore:
        warnings.append(f"장면 animationRange가 {rangeBefore}에서 {rangeAfter}로 바뀌었다")

    return ags.readback(
        modified=[com],
        details={
            "file": path,
            "animationRangeBefore": rangeBefore,
            "animationRangeAfter": rangeAfter,
            "sliderTime": int(rt.sliderTime),
            "figureModeBefore": figureModeBefore,
            "figureModeAfter": figureModeAfter,
        },
        warnings=warnings,
    )


def save_bip_file(
    inBipedRoot: str | int | dict,
    inFilePath: str,
    inOverwrite: bool = False,
    inBakeAllKeys: bool = True,
    inCollapseLayers: bool = False,
    inUseAnimationRangeOnly: bool = True,
) -> dict:
    """Biped COM의 애니메이션을 BIP 파일로 저장한다.

    상위 폴더가 없으면 만든다(``details["createdDirs"]``). ``inCollapseLayers=True``면 저장 전에
    **장면의 Biped 애니메이션 레이어를 모두 병합한다**(장면 변경, 되돌릴 수 없음). 기본값은
    병합하지 않는다.

    Args:
        inBipedRoot: Biped COM 노드(이름·handle·NodeRef)
        inFilePath: 저장할 ``.bip`` 파일 경로(절대 경로 권장)
        inOverwrite: 같은 경로에 파일이 있으면 덮어쓴다. False면 거절한다
        inBakeAllKeys: True면 매 프레임 키로 베이크해 저장한다(keyPerFrame)
        inCollapseLayers: True면 저장 전에 Biped 레이어를 병합한다
        inUseAnimationRangeOnly: True면 장면 animationRange를, False면 Biped 키 범위를 저장 구간으로 쓴다

    Returns:
        readback dict. 레이어를 실제로 병합했으면 ``modified=[COM]``.
        ``details={"file", "bytes", "overwritten", "range": [시작, 끝], "layersCollapsed": bool,
        "layerCountBefore": int, "createdDirs": [str]}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(확장자가 .bip가 아님·폴더 경로·bool 인자 형 오류),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, PRECONDITION_FAILED(COM이 아님, 기존 파일이 있는데
            inOverwrite=False), OPERATION_FAILED(원본이 False 반환·파일 미생성·갱신 안 됨·원본 예외)

    Side effects: scene, file
    Undo: no

    Example:
        from pyjallib.max.agentapi import bip; result = bip.save_bip_file("Bip001", "D:/Anim/Walk.bip", inOverwrite=True)
    """
    path = _require_bip_path(inFilePath, inMustExist=False)
    for argName, argValue in (
        ("inOverwrite", inOverwrite),
        ("inBakeAllKeys", inBakeAllKeys),
        ("inCollapseLayers", inCollapseLayers),
        ("inUseAnimationRangeOnly", inUseAnimationRangeOnly),
    ):
        _require_bool(argValue, argName)

    com = _resolve_com(inBipedRoot)
    beforeStat = _file_stat(path)
    if beforeStat is not None and not inOverwrite:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"파일이 이미 있다. 덮어쓰려면 inOverwrite=True로 호출해야 한다: {path}",
            {"file": path},
        )

    rt = _runtime()
    bip = _header().bip
    layerCountBefore = int(_call_original("Biped 레이어 수 조회", rt.biped.numLayers, com.controller))
    rangeBefore = _animation_range(rt)
    missingDirs = _missing_dirs(path)

    result = _call_original(
        "BIP 파일 저장",
        bip.save_bip_file,
        com,
        path,
        inBakeAllKeys=inBakeAllKeys,
        inCollapseLayers=inCollapseLayers,
        inUseAnimationRangeOnly=inUseAnimationRangeOnly,
    )
    createdDirs = [item for item in missingDirs if os.path.isdir(item)]
    if result is False:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "원본이 BIP 저장 실패(False)를 돌려줬다(Biped 아님 또는 폴더 생성 실패)",
            {"file": path, "originalReturn": False, "createdDirs": createdDirs},
        )
    fileBytes = _verify_written(path, beforeStat, "BIP 파일 저장", result)

    if inUseAnimationRangeOnly:
        savedRange = rangeBefore
    else:
        interval = _call_original(
            "Biped 키 범위 조회", bip.get_animation_range, _call_original("Biped 노드 조회", bip.get_nodes, com)
        )
        savedRange = [int(interval.start), int(interval.end)] if interval is not False else None

    layersCollapsed = bool(inCollapseLayers and layerCountBefore > 0)
    warnings = []
    if layersCollapsed:
        warnings.append(f"저장 전에 Biped 애니메이션 레이어 {layerCountBefore}개를 병합했다")

    return ags.readback(
        modified=[com] if layersCollapsed else [],
        details={
            "file": path,
            "bytes": fileBytes,
            "overwritten": beforeStat is not None,
            "range": savedRange,
            "layersCollapsed": layersCollapsed,
            "layerCountBefore": layerCountBefore,
            "createdDirs": createdDirs,
        },
        warnings=warnings,
    )


def set_biped_figure_mode(inBipedRoot: str | int | dict, inEnabled: bool) -> dict:
    """Biped COM의 피규어 모드를 켜거나 끈다.

    이미 원하는 상태면 장면을 바꾸지 않고 ``modified``를 비운다.

    Args:
        inBipedRoot: Biped COM 노드(이름·handle·NodeRef)
        inEnabled: True면 켜고 False면 끈다

    Returns:
        readback dict. 상태가 실제로 바뀌었으면 ``modified=[COM]``.
        ``details={"before": bool, "after": bool}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(inEnabled가 bool이 아님), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(COM이 아님), OPERATION_FAILED(원본 예외·적용 후 상태 불일치)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import bip; result = bip.set_biped_figure_mode("Bip001", True)
    """
    _require_bool(inEnabled, "inEnabled")
    com = _resolve_com(inBipedRoot)
    bip = _header().bip

    before = bool(com.controller.figureMode)
    if inEnabled:
        _call_original("피규어 모드 켜기", bip.turn_on_figure_mode, com)
    else:
        _call_original("피규어 모드 끄기", bip.turn_off_figure_mode, com)
    after = bool(com.controller.figureMode)

    if after != inEnabled:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"피규어 모드를 {inEnabled}로 바꾸지 못했다(현재 {after})",
            {"node": ags.node_ref(com), "before": before, "after": after},
        )
    return ags.readback(modified=[com] if after != before else [], details={"before": before, "after": after})
