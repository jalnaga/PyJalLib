# -*- coding: utf-8 -*-
"""스킨 에이전트 인터페이스 — 에이전트가 Skin 모디파이어를 조회하고 스킨 파일을 불러오거나 저장하고 스킨을 최적화한다.

함수 목록:
    get_skin_modifiers — 노드마다 Skin 모디파이어 유무와 스택 위치·본 수를 돌려준다 [none]
    load_skin — .skin 파일을 읽어 노드에 새 Skin을 만들고 가중치를 적용한다 [scene]
    optimize_skin — Skin의 0 가중치와 쓰지 않는 본을 제거한다 [scene]
    save_skin — Modify 패널에 열린 노드의 Skin을 .skin 파일로 저장한다 [file]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    Skin 스택 위치(stackIndex)는 모디파이어 스택 맨 위가 1이다.
    이 모듈의 함수는 선택·Modify 패널을 직접 바꾸지 않고, 원본이 바꾼 선택·패널은 되돌리지 않는다.
    load_skin: 원본이 대상 노드를 선택하고 Command 패널을 Modify로 바꾼 채 남긴다.
    optimize_skin: 입력 노드가 모두 현재 선택에 있어야 한다. 원본이 Command 패널을 Modify로 바꾸고
    끝에 입력 노드 전체를 선택한 채 남긴다.
    save_skin: 저장할 노드의 Skin이 Modify 패널의 현재 객체로 열려 있어야 한다(원본은 패널에 열린
    Skin을 저장한다). 선택·패널은 바꾸지 않는다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 예:
    from pyjallib.max.agentapi import skin; result = skin.get_skin_modifiers(["Body_Mesh"])
"""

import os

from pyjallib.max import agentSupport as ags

#: optimize_skin의 버텍스당 본 제한 허용 범위
_BONE_LIMIT_RANGE = (1, 20)


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


def _call_original(inOperation: str, inFunc, *args, **kwargs):
    """원본 메서드를 부르고 예외를 계약 코드로 바꾼다.

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


def _is_int(inValue) -> bool:
    """bool을 뺀 정수인지 판정한다."""
    return isinstance(inValue, int) and not isinstance(inValue, bool)


def _require_skin_path(inFilePath, inMustExist: bool) -> str:
    """.skin 파일 경로 인자를 확인하고 절대 경로로 돌려준다.

    Raises:
        AgentApiError: INVALID_ARGUMENT — 문자열이 아님·빈 경로·확장자가 ``.skin``이 아님·
            폴더 경로·(inMustExist일 때) 파일 없음. ``details["kind"]="file"``
    """
    if not isinstance(inFilePath, str) or inFilePath.strip() == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inFilePath는 비어 있지 않은 문자열이어야 한다",
            {"argument": "inFilePath", "input": repr(inFilePath), "kind": "file"},
        )
    path = os.path.abspath(inFilePath)
    if os.path.splitext(path)[1].lower() != ".skin":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, f"스킨 파일 확장자는 .skin이어야 한다: {path}", {"file": path, "kind": "file"}
        )
    if os.path.isdir(path):
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, f"파일이 아니라 폴더 경로다: {path}", {"file": path, "kind": "file"})
    if inMustExist and not os.path.isfile(path):
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, f"스킨 파일이 없다: {path}", {"file": path, "kind": "file"})
    return path


def _skin_entries(inRt, inNode) -> list:
    """노드의 Skin 모디파이어를 ``[(stackIndex, 모디파이어)]``로 돌려준다(맨 위 = 1).

    원본 ``Skin.get_skin_mod``와 같은 판정(``classOf == Skin``)·같은 순서다.
    """
    modifiers = inNode.modifiers
    entries = []
    for index in range(len(modifiers)):
        modifier = modifiers[index]
        if inRt.classOf(modifier) == inRt.Skin:
            entries.append((index + 1, modifier))
    return entries


def _bone_count(inRt, inSkinMod) -> int:
    """Skin의 본 수(``skinOps.GetNumberBones``)."""
    return int(inRt.skinOps.GetNumberBones(inSkinMod))


def _try_bone_count(inRt, inSkinMod, inLabel: str, inWarnings: list):
    """선택·패널을 바꾸지 않고 Skin 본 수를 읽는다. 못 읽으면 None을 돌려주고 warnings에 적는다."""
    try:
        return _bone_count(inRt, inSkinMod)
    except Exception as error:  # noqa: BLE001 - readback 실패는 결과를 막지 않는다
        inWarnings.append(f"{inLabel}의 Skin 본 수를 읽지 못했다: {error}")
        return None


def _anim_handle(inRt, inAnim):
    """모디파이어 등 애니메이터블의 anim handle(동일성 비교용). 못 읽으면 None."""
    try:
        return int(inRt.getHandleByAnim(inAnim))
    except Exception:  # noqa: BLE001
        return None


def _selected_handles(inRt) -> set:
    """현재 선택 노드의 handle 집합(읽기만 한다)."""
    return {int(node.inode.handle) for node in inRt.getCurrentSelection() if inRt.isValidNode(node)}


def _file_stat(inPath: str):
    """파일의 ``(mtime_ns, size)``. 없으면 None."""
    try:
        stat = os.stat(inPath)
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _verify_written(inPath: str, inBeforeStat, inOperation: str, inOriginalReturn) -> int:
    """출력 파일이 실제로 생기거나 갱신됐는지 확인하고 크기를 돌려준다.

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


def get_skin_modifiers(inNodes: list) -> dict:
    """노드마다 Skin 모디파이어가 있는지와 각 Skin의 스택 위치·이름·본 수·켜짐 여부를 돌려준다.

    선택·Modify 패널을 바꾸지 않는다. 본 수는 Skin을 Modify 패널에 띄우지 않고 읽은 값이며,
    읽지 못하면 ``boneCount``를 None으로 두고 warnings에 적는다.

    Args:
        inNodes: 조회할 노드 목록(이름·handle·NodeRef)

    Returns:
        ``{"results": [{"node": NodeRef, "hasSkin": bool, "modifiers": [{"stackIndex": int(맨 위 = 1),
        "name": str, "boneCount": int | None, "enabled": bool}]}], "warnings": [str]}`` — 입력 순서

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT, OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import skin; result = skin.get_skin_modifiers(["Body_Mesh", "Head_Mesh"])
    """
    nodes = ags.resolve_nodes(inNodes)
    rt = _runtime()
    skinService = _header().skin

    results = []
    warnings = []
    for node in nodes:
        ref = ags.node_ref(node)
        hasSkin = bool(_call_original("Skin 유무 확인", skinService.has_skin, node))
        skinMods = list(_call_original("Skin 모디파이어 조회", skinService.get_skin_mod, node))
        entries = _call_original("모디파이어 스택 조회", _skin_entries, rt, node)
        if len(entries) != len(skinMods):
            warnings.append(
                f"'{ref['name']}': 원본 Skin 목록({len(skinMods)}개)과 스택 조회({len(entries)}개)가 다르다"
            )

        modifiers = []
        for stackIndex, modifier in entries:
            try:
                boneCount = _bone_count(rt, modifier)
            except Exception as error:  # noqa: BLE001 - 본 수를 못 읽어도 나머지 정보는 돌려준다
                boneCount = None
                warnings.append(f"'{ref['name']}' 스택 {stackIndex}의 Skin 본 수를 읽지 못했다: {error}")
            modifiers.append(
                {
                    "stackIndex": stackIndex,
                    "name": str(modifier.name),
                    "boneCount": boneCount,
                    "enabled": bool(modifier.enabled),
                }
            )
        results.append({"node": ref, "hasSkin": hasSkin, "modifiers": modifiers})
    return {"results": results, "warnings": warnings}


def load_skin(
    inNode: str | int | dict,
    inFilePath: str,
    inKeepSkin: bool = False,
    inLoadBindPose: bool = False,
    inInsertBefore: int | None = None,
) -> dict:
    """``.skin`` 파일을 읽어 노드에 새 Skin 모디파이어를 만들고 본·가중치를 적용한다.

    **주의: 파일의 각 줄을 MAXScript로 실행한다.** 신뢰하는 ``.skin`` 파일(``save_skin``으로 만든
    파일 등)만 넘긴다. 파일에 적힌 본이 장면에 없으면 같은 이름의 Dummy를 만들어 대신 쓴다
    (``created``와 warnings). ``inKeepSkin=False``면 노드의 기존 Skin을 모두 지운다.
    **원본은 대상 노드를 선택하고 Command 패널을 Modify로 바꿔 새 Skin을 현재 객체로 둔 채
    남긴다**(호출 전 선택으로 되돌리지 않는다).

    Args:
        inNode: Skin을 적용할 지오메트리 노드(이름·handle·NodeRef)
        inFilePath: 읽을 ``.skin`` 파일 경로(절대 경로 권장)
        inKeepSkin: True면 기존 Skin을 남기고 새 Skin 이름을 ``Skin_<파일 이름>``으로 둔다
        inLoadBindPose: True면 바인드 포즈 파일도 읽어 적용한다(``details["bindPoseFile"]``의 경로)
        inInsertBefore: 새 Skin을 넣을 위치(``addModifier``의 ``before:`` — 0 = 맨 위, N = 위에서
            N번째 모디파이어 아래). None이면 ``inKeepSkin``이면 1, 아니면 0

    Returns:
        readback dict. ``created``=새로 생긴 노드(대체 Dummy), ``modified=[inNode]``,
        ``details={"file", "removedSkinModifiers": int, "missingBones": [str], "bindPoseFile": str | None,
        "vertexCount": int}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(파일 없음·읽을 수 없음·확장자가 .skin이 아님,
            ``details["kind"]="file"``; inInsertBefore가 음수·스택 범위 밖; bool 인자 형 오류),
            NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(지오메트리가 아님·버텍스 수를 읽을 수 없음·파일 줄 수 - 1과 버텍스 수가
            다름 — ``details["expected"]``·``details["actual"]``),
            OPERATION_FAILED(새 Skin이 생기지 않음·원본 예외)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import skin; result = skin.load_skin("Body_Mesh", "D:/Skin/Body_Mesh.skin")
    """
    path = _require_skin_path(inFilePath, inMustExist=True)
    _require_bool(inKeepSkin, "inKeepSkin")
    _require_bool(inLoadBindPose, "inLoadBindPose")
    if inInsertBefore is not None and (not _is_int(inInsertBefore) or inInsertBefore < 0):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inInsertBefore는 None 또는 0 이상의 정수여야 한다",
            {"argument": "inInsertBefore", "input": repr(inInsertBefore)},
        )

    node = ags.resolve_node(inNode)
    rt = _runtime()
    skinService = _header().skin
    from pyjallib.max.agentapi import _scene

    ref = ags.node_ref(node)
    if rt.superClassOf(node) != rt.GeometryClass:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED, f"'{ref['name']}'은 지오메트리가 아니다", {"node": ref, "class": ref["class"]}
        )
    try:
        vertexCount = int(node.verts.count)
    except Exception as error:  # noqa: BLE001 - 원본이 쓰는 verts.count를 못 읽으면 적용할 수 없다
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"'{ref['name']}'의 버텍스 수를 읽을 수 없다(Editable Mesh/Poly 계열이어야 한다)",
            {"node": ref, "exception": repr(error)},
        ) from error

    # 원본과 같은 방식(기본 인코딩, 줄 단위)으로 줄 수를 센다 — 원본은 불일치를 빈 목록으로 삼킨다
    try:
        with open(path, "r") as file:
            lineCount = sum(1 for _line in file)
    except Exception as error:  # noqa: BLE001
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"스킨 파일을 읽을 수 없다: {path}",
            {"file": path, "kind": "file", "exception": repr(error)},
        ) from error
    if vertexCount == 0 or lineCount - 1 != vertexCount:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"스킨 파일의 버텍스 수({lineCount - 1})가 '{ref['name']}'의 버텍스 수({vertexCount})와 다르다",
            {"node": ref, "file": path, "expected": vertexCount, "actual": lineCount - 1},
        )

    entriesBefore = _call_original("모디파이어 스택 조회", _skin_entries, rt, node)
    skinCountBefore = len(entriesBefore)
    removedCount = 0 if inKeepSkin else skinCountBefore
    if inInsertBefore is not None:
        remaining = len(node.modifiers) - removedCount
        if inInsertBefore > remaining:
            raise ags.AgentApiError(
                ags.INVALID_ARGUMENT,
                f"inInsertBefore({inInsertBefore})가 남는 모디파이어 수({remaining})보다 크다",
                {"argument": "inInsertBefore", "input": inInsertBefore, "max": remaining},
            )

    handlesBefore = _scene.snapshot_handles()
    missing = _call_original(
        "스킨 파일 불러오기",
        skinService.load_skin,
        node,
        path,
        load_bind_pose=inLoadBindPose,
        keep_skin=inKeepSkin,
        insert_before=inInsertBefore,
    )
    created = _scene.created_since(handlesBefore)

    skinCountAfter = len(_call_original("모디파이어 스택 조회", _skin_entries, rt, node))
    expectedCount = (skinCountBefore if inKeepSkin else 0) + 1
    if skinCountAfter != expectedCount:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "스킨 파일을 불러온 뒤 새 Skin 모디파이어가 확인되지 않았다",
            {
                "node": ref,
                "file": path,
                "skinModifiersBefore": skinCountBefore,
                "skinModifiersAfter": skinCountAfter,
                "expected": expectedCount,
                "originalReturn": ags.to_json(list(missing) if missing else []),
                "created": [ags.node_ref(item) for item in created],
            },
        )

    missingBones = [str(item.name) for item in (missing or []) if rt.isValidNode(item)]
    warnings = [f"장면에 없는 본 '{name}'을 같은 이름의 Dummy로 만들어 대신 썼다" for name in missingBones]

    bindPoseFile = None
    if inLoadBindPose:
        # 원본 load_skin이 찾는 경로 규칙(splitext + "bp")을 그대로 보고한다
        bindPoseFile = os.path.splitext(path)[0] + "bp"
        if not os.path.isfile(bindPoseFile):
            warnings.append(
                f"바인드 포즈 파일이 없어 바인드 포즈를 적용하지 않았다: {bindPoseFile} "
                "(save_skin이 쓰는 경로 규칙과 다를 수 있다)"
            )

    return ags.readback(
        created=created,
        modified=[node],
        details={
            "file": path,
            "removedSkinModifiers": removedCount,
            "missingBones": missingBones,
            "bindPoseFile": bindPoseFile,
            "vertexCount": vertexCount,
        },
        warnings=warnings,
    )


def optimize_skin(
    inNodes: list,
    inAllSkinModifiers: bool = False,
    inBoneLimit: int = 8,
    inSkinTolerance: float = 0.01,
) -> dict:
    """현재 선택된 노드들의 Skin에서 허용 오차 이하 가중치와 쓰지 않는 본을 제거한다.

    원본 ``optimize_skin_process``는 넘긴 노드가 선택돼 있다고 가정한다(Modify 패널에 모디파이어를
    띄우고 출력에 선택을 쓴다). 그래서 **입력 노드가 모두 현재 선택에 있어야 하며**, 하나라도
    선택에 없으면 원본을 부르지 않고 거절한다. 이 함수는 선택·Modify 패널을 바꾸지 않고, 원본을
    입력 노드 목록으로 한 번 부른다. **원본은 Command 패널을 Modify로 바꾸고, 끝에 입력 노드
    전체를 선택한 채 남긴다**(입력 밖의 노드는 선택에서 빠진다). Skin의 ``bone_Limit``을
    inBoneLimit으로 바꾸고 Dual Quaternion을 끈다. Skin이 없는 노드는 원본이 건너뛰며 warnings에
    적는다. 노드마다 처리 전후 본 수를 선택·패널을 바꾸지 않고 읽어 돌려준다(읽지 못하면 None과
    warnings).

    Args:
        inNodes: 대상 노드 목록(이름·handle·NodeRef). 모두 현재 선택에 있어야 한다
        inAllSkinModifiers: True면 노드의 모든 Skin을, False면 맨 위 Skin 하나만 처리한다
        inBoneLimit: 버텍스당 본 제한(1~20)
        inSkinTolerance: 이 값 이하 가중치를 0으로 지운다(0 이상)

    Returns:
        readback dict. ``modified``=Skin이 있어 처리 대상이 된 노드, ``details={"perNode": [{"node",
        "boneCountBefore", "boneCountAfter", "modifiers": [{"stackIndex", "boneCountBefore",
        "boneCountAfter"}]}]}`` (노드 단위 본 수는 처리한 Skin들의 합, 하나라도 못 읽으면 None)

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT(inBoneLimit이 1~20 밖,
            inSkinTolerance가 음수·숫자가 아님, bool 인자 형 오류), PRECONDITION_FAILED(입력 노드 중
            현재 선택에 없는 노드가 있음 — ``details["notSelected"]``, 어느 노드에도 Skin이 없음),
            OPERATION_FAILED(원본 예외 — 원본을 한 번 부르므로 일부 노드가 이미 처리됐을 수 있다.
            ``details["nodes"]``에 처리 대상 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import skin; result = skin.optimize_skin(["Body_Mesh"], inBoneLimit=4)
    """
    _require_bool(inAllSkinModifiers, "inAllSkinModifiers")
    if not _is_int(inBoneLimit) or not (_BONE_LIMIT_RANGE[0] <= inBoneLimit <= _BONE_LIMIT_RANGE[1]):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"inBoneLimit은 {_BONE_LIMIT_RANGE[0]}~{_BONE_LIMIT_RANGE[1]} 정수여야 한다",
            {"argument": "inBoneLimit", "input": repr(inBoneLimit), "range": list(_BONE_LIMIT_RANGE)},
        )
    if (
        isinstance(inSkinTolerance, bool)
        or not isinstance(inSkinTolerance, (int, float))
        or inSkinTolerance < 0
    ):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inSkinTolerance는 0 이상의 숫자여야 한다",
            {"argument": "inSkinTolerance", "input": repr(inSkinTolerance)},
        )

    nodes = ags.resolve_nodes(inNodes)
    rt = _runtime()
    skinService = _header().skin

    uniqueNodes = []
    seen = set()
    for node in nodes:
        handle = ags.node_ref(node)["handle"]
        if handle in seen:
            continue
        seen.add(handle)
        uniqueNodes.append(node)

    # (나) 사전 검사: 원본은 넘긴 노드가 선택돼 있다고 가정한다 — 선택은 바꾸지 않고 확인만 한다
    selectedHandles = _selected_handles(rt)
    notSelected = [ags.node_ref(node) for node in uniqueNodes if ags.node_ref(node)["handle"] not in selectedHandles]
    if notSelected:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"입력 노드 {len(notSelected)}개가 현재 선택에 없다. 원본은 대상 노드가 선택돼 있다고 가정한다",
            {"notSelected": notSelected},
        )

    warnings = []
    targets = []
    for node in uniqueNodes:
        ref = ags.node_ref(node)
        entries = _call_original("모디파이어 스택 조회", _skin_entries, rt, node)
        if not entries:
            warnings.append(f"'{ref['name']}'에 Skin이 없어 원본이 건너뛴다")
            continue
        targets.append((node, ref, entries if inAllSkinModifiers else entries[:1]))
    if not targets:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            "입력 노드 중 Skin 모디파이어가 있는 노드가 없다",
            {"nodes": [ags.node_ref(node) for node in uniqueNodes]},
        )

    countsBefore = {
        ref["handle"]: [
            _try_bone_count(rt, modifier, f"'{ref['name']}' 스택 {stackIndex}(처리 전)", warnings)
            for stackIndex, modifier in chosen
        ]
        for _node, ref, chosen in targets
    }

    try:
        skinService.optimize_skin_process(
            list(uniqueNodes),
            optim_all_skin_mod=inAllSkinModifiers,
            bone_limit=inBoneLimit,
            skin_tolerance=float(inSkinTolerance),
        )
    except Exception as error:  # noqa: BLE001 - 원본을 한 번 부르므로 부분 적용 여부는 알 수 없다
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"스킨 최적화 중 원본 처리가 실패했다(일부 노드가 이미 처리됐을 수 있다): {error}",
            {"exception": repr(error), "nodes": [ref for _node, ref, _chosen in targets]},
        ) from error

    perNode = []
    for _node, ref, chosen in targets:
        before = countsBefore[ref["handle"]]
        after = [
            _try_bone_count(rt, modifier, f"'{ref['name']}' 스택 {stackIndex}(처리 후)", warnings)
            for stackIndex, modifier in chosen
        ]
        perNode.append(
            {
                "node": ref,
                "boneCountBefore": None if None in before else sum(before),
                "boneCountAfter": None if None in after else sum(after),
                "modifiers": [
                    {"stackIndex": stackIndex, "boneCountBefore": countBefore, "boneCountAfter": countAfter}
                    for (stackIndex, _modifier), countBefore, countAfter in zip(chosen, before, after)
                ],
            }
        )

    return ags.readback(
        modified=[node for node, _ref, _chosen in targets], details={"perNode": perNode}, warnings=warnings
    )


def save_skin(
    inNode: str | int | dict,
    inFilePath: str,
    inOverwrite: bool = False,
    inSaveBindPose: bool = False,
) -> dict:
    """Modify 패널에 열린 노드의 Skin을 ``.skin`` 파일(본 이름 목록 + 버텍스별 본 ID·가중치)로 저장한다.

    원본 ``save_skin``은 넘긴 노드와 무관하게 **Modify 패널의 현재 객체**를 저장한다. 그래서 현재
    Modify 패널 객체가 ``inNode``의 Skin 모디파이어가 아니면 원본을 부르지 않고 거절한다. 저장할
    Skin은 열린 패널이 정하므로(Skin이 여러 개면 패널에 연 그 Skin) 스택 위치 인자는 없다.
    이 함수는 선택·Modify 패널을 바꾸지 않는다. 상위 폴더는 만들지 않는다.
    ``inSaveBindPose=True``면 바인드 포즈를 ``<경로에서 'skin'을 뺀 것>bp``(예: ``a.skin`` →
    ``a.bp``)에 함께 저장한다.

    Args:
        inNode: Skin이 붙은 노드(이름·handle·NodeRef). 그 Skin이 Modify 패널에 열려 있어야 한다
        inFilePath: 저장할 ``.skin`` 파일 경로(절대 경로 권장)
        inOverwrite: 같은 경로에 파일(바인드 포즈 파일 포함)이 있으면 덮어쓴다. False면 거절한다
        inSaveBindPose: True면 바인드 포즈 파일도 저장한다

    Returns:
        readback dict. ``details={"file", "bytes", "overwritten", "boneCount", "vertexCount",
        "stackIndex": 패널에 열린 Skin의 스택 위치(맨 위 = 1), "bindPoseFile": str | None}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(확장자가 .skin이 아님·폴더 경로·상위 폴더 없음
            ``details["kind"]="directory"``, bool 인자 형 오류), NODE_NOT_FOUND, NODE_AMBIGUOUS,
            PRECONDITION_FAILED(Skin 없음, 현재 Modify 패널 객체가 그 노드의 Skin이 아님 —
            ``details["skinStackIndices"]``·``details["currentObject"]``, 열린 Skin에 본 0개,
            기존 파일이 있는데 inOverwrite=False), OPERATION_FAILED(원본이 None 반환·파일 미생성·원본 예외)

    Side effects: file
    Undo: no

    Example:
        from pyjallib.max.agentapi import skin; result = skin.save_skin("Body_Mesh", "D:/Skin/Body_Mesh.skin", inOverwrite=True)
    """
    path = _require_skin_path(inFilePath, inMustExist=False)
    _require_bool(inOverwrite, "inOverwrite")
    _require_bool(inSaveBindPose, "inSaveBindPose")
    parentDir = os.path.dirname(path)
    if parentDir and not os.path.isdir(parentDir):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"저장할 폴더가 없다: {parentDir}",
            {"file": path, "directory": parentDir, "kind": "directory"},
        )
    # 원본 save_skin의 바인드 포즈 경로 규칙(path[:-4] + "bp")
    bindPoseFile = path[:-4] + "bp" if inSaveBindPose else None

    node = ags.resolve_node(inNode)
    rt = _runtime()
    skinService = _header().skin
    ref = ags.node_ref(node)

    entries = _call_original("모디파이어 스택 조회", _skin_entries, rt, node)
    if not entries:
        raise ags.AgentApiError(ags.PRECONDITION_FAILED, f"'{ref['name']}'에 Skin이 없다", {"node": ref})
    validIndices = [stackIndex for stackIndex, _modifier in entries]

    # (나) 사전 검사: 원본은 패널의 현재 객체를 저장한다 — 패널은 바꾸지 않고 확인만 한다
    currentObject = _call_original("Modify 패널 현재 객체 조회", rt.modPanel.getCurrentObject)
    currentHandle = _anim_handle(rt, currentObject) if currentObject is not None else None
    stackIndex = None
    skinMod = None
    if currentHandle is not None:
        for entryIndex, modifier in entries:
            if _anim_handle(rt, modifier) == currentHandle:
                stackIndex, skinMod = entryIndex, modifier
                break
    if skinMod is None:
        currentInfo = None
        if currentObject is not None:
            try:
                currentInfo = {"class": str(rt.classOf(currentObject)), "name": str(currentObject.name)}
            except Exception:  # noqa: BLE001 - 진단 정보만 못 읽는다
                currentInfo = {"class": None, "name": None}
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"현재 Modify 패널 객체가 '{ref['name']}'의 Skin이 아니다. 원본은 패널에 열린 객체를 저장한다",
            {"node": ref, "skinStackIndices": validIndices, "currentObject": currentInfo},
        )

    boneCount = int(_call_original("Skin 본 수 조회", rt.skinOps.GetNumberBones, skinMod))
    if boneCount <= 0:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"'{ref['name']}' 스택 {stackIndex}의 Skin에 본이 없다",
            {"node": ref, "stackIndex": stackIndex},
        )
    vertexCount = int(_call_original("Skin 버텍스 수 조회", rt.skinOps.GetNumberVertices, skinMod))

    beforeStat = _file_stat(path)
    existing = [item for item in (path, bindPoseFile) if item is not None and os.path.exists(item)]
    if existing and not inOverwrite:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            "파일이 이미 있다. 덮어쓰려면 inOverwrite=True로 호출해야 한다",
            {"file": path, "existing": existing},
        )

    result = _call_original("스킨 파일 저장", skinService.save_skin, node, path, inSaveBindPose)
    if result is None:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "원본이 스킨 저장 실패(None)를 돌려줬다(리스너 출력 참조)",
            {"node": ref, "file": path, "originalReturn": None},
        )
    fileBytes = _verify_written(path, beforeStat, "스킨 파일 저장", result)

    warnings = []
    if bindPoseFile is not None and not os.path.isfile(bindPoseFile):
        warnings.append(f"바인드 포즈 파일이 생기지 않았다: {bindPoseFile}")

    return ags.readback(
        details={
            "file": path,
            "bytes": fileBytes,
            "overwritten": beforeStat is not None,
            "boneCount": boneCount,
            "vertexCount": vertexCount,
            "stackIndex": stackIndex,
            "bindPoseFile": bindPoseFile,
        },
        warnings=warnings,
    )
