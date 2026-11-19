# -*- coding: utf-8 -*-
"""FBX 에이전트 인터페이스 — 에이전트가 지정한 노드를 FBX로 내보내고 FBX 파일을 장면으로 가져온다.

함수 목록:
    export_fbx — 지정한 노드를 선택해 FBX 파일로 내보낸다(선택·익스포터 옵션은 바뀐 채 남음) [scene, file]
    import_fbx — FBX 파일을 현재 장면으로 가져온다(애니메이션 구간이 바뀔 수 있음) [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 하고 FBX 익스포터·임포터
    플러그인이 있어야 한다. 대화상자 없이(noPrompt) 실행한다.
    export_fbx는 내보낼 노드를 선택한 채 남기고, FBX 익스포터 전역 설정을 원본이 지정한 값으로
    바꾼 채 남긴다(호출 전 상태로 되돌리지 않는다).
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 예:
    from pyjallib.max.agentapi import fbx; result = fbx.export_fbx(["Bip001", "Body_Mesh"], "D:/Export/Hero.fbx")
"""

import os

from pyjallib.max import agentSupport as ags

#: import_fbx가 받는 가져오기 모드
_IMPORT_MODES = ("add_and_update_animation", "update_animation")

#: import_fbx가 받는 업 축
_UP_AXES = ("Z", "Y")


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


def _require_optional_frame(inValue, inArgName: str) -> None:
    """None 또는 정수 프레임 인자인지 확인한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if inValue is not None and (not isinstance(inValue, int) or isinstance(inValue, bool)):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 None 또는 정수 프레임이어야 한다",
            {"argument": inArgName, "input": repr(inValue)},
        )


def _require_fbx_path(inFilePath, inMustExist: bool) -> str:
    """FBX 파일 경로 인자를 확인하고 절대 경로로 돌려준다.

    Raises:
        AgentApiError: INVALID_ARGUMENT — 문자열이 아님·빈 경로·확장자가 ``.fbx``가 아님·
            폴더 경로·(inMustExist일 때) 파일 없음. ``details["kind"]="file"``
    """
    if not isinstance(inFilePath, str) or inFilePath.strip() == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inFilePath는 비어 있지 않은 문자열이어야 한다",
            {"argument": "inFilePath", "input": repr(inFilePath), "kind": "file"},
        )
    path = os.path.abspath(inFilePath)
    if os.path.splitext(path)[1].lower() != ".fbx":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, f"FBX 파일 확장자는 .fbx여야 한다: {path}", {"file": path, "kind": "file"}
        )
    if os.path.isdir(path):
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, f"파일이 아니라 폴더 경로다: {path}", {"file": path, "kind": "file"})
    if inMustExist and not os.path.isfile(path):
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, f"FBX 파일이 없다: {path}", {"file": path, "kind": "file"})
    return path


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


def export_fbx(
    inNodes: list,
    inFilePath: str,
    inOverwrite: bool = False,
    inMatchAnimRange: bool = True,
    inStartFrame: int | None = None,
    inEndFrame: int | None = None,
    inSmoothingGroups: bool = True,
) -> dict:
    """지정한 노드를 선택해 FBX 파일로 내보낸다.

    원본 ``export_selection``(애니메이션 베이크·스킨·모프 포함, Z 업, FBX 2020)은 현재 선택을
    내보내므로, 이 함수는 노드를 선택한 뒤 원본을 부른다. **선택은 내보낸 노드로 바뀐 채 남는다**
    (호출 전 선택으로 되돌리지 않는다). **원본은 FBX 익스포터 전역 설정을 리셋한 뒤 툴 값으로
    덮어쓰며, 이 설정은 바뀐 채 남는다** — 이후 사용자가 GUI로 FBX를 내보낼 때 그 값이 쓰인다
    (``details["exporterOptionsChanged"]``). 의존 노드(스킨 본 등)는 자동으로 넣지 않는다 —
    필요하면 ``dependent.collect_export_related_nodes``로 모은 목록을 넘긴다. 상위 폴더가 없으면
    만든다(``details["createdDirs"]``). 선택한 뒤 일부 노드가 선택되지 않았으면(숨김·동결 등)
    원본을 부르지 않고 거절한다(선택은 이미 바뀐 상태다).

    Args:
        inNodes: 내보낼 노드 목록(이름·handle·NodeRef). 비어 있으면 안 된다
        inFilePath: 저장할 ``.fbx`` 파일 경로(절대 경로 권장)
        inOverwrite: 같은 경로에 파일이 있으면 덮어쓴다. False면 거절한다
        inMatchAnimRange: True면 베이크 구간을 지정한다(아래 프레임, 없으면 장면 animationRange)
        inStartFrame: 베이크 시작 프레임. None이면 장면 animationRange 시작
        inEndFrame: 베이크 끝 프레임. None이면 장면 animationRange 끝
        inSmoothingGroups: 스무딩 그룹을 내보낸다

    Returns:
        readback dict. ``details={"file", "bytes", "overwritten", "exported": [NodeRef],
        "range": [시작, 끝] | None(inMatchAnimRange=False), "createdDirs": [str],
        "exporterOptionsChanged": True(FBX 익스포터 설정이 툴 값으로 바뀐 채 남음)}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(빈 목록·확장자가 .fbx가 아님·폴더 경로·시작 > 끝·인자 형 오류),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, PRECONDITION_FAILED(기존 파일이 있는데 inOverwrite=False,
            일부 노드가 선택되지 않음 — ``details["notSelected"]``),
            OPERATION_FAILED(원본이 False 반환·파일 미생성·갱신 안 됨·원본 예외)

    Side effects: scene, file
    Undo: no

    Example:
        from pyjallib.max.agentapi import fbx; result = fbx.export_fbx(["Bip001", "Body_Mesh"], "D:/Export/Hero.fbx", inStartFrame=0, inEndFrame=30)
    """
    if isinstance(inNodes, (list, tuple)) and len(inNodes) == 0:
        raise ags.AgentApiError(ags.INVALID_ARGUMENT, "inNodes가 비어 있다", {"argument": "inNodes"})
    path = _require_fbx_path(inFilePath, inMustExist=False)
    for argName, argValue in (
        ("inOverwrite", inOverwrite),
        ("inMatchAnimRange", inMatchAnimRange),
        ("inSmoothingGroups", inSmoothingGroups),
    ):
        _require_bool(argValue, argName)
    _require_optional_frame(inStartFrame, "inStartFrame")
    _require_optional_frame(inEndFrame, "inEndFrame")
    if inStartFrame is not None and inEndFrame is not None and inStartFrame > inEndFrame:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"inStartFrame({inStartFrame})이 inEndFrame({inEndFrame})보다 크다",
            {"inStartFrame": inStartFrame, "inEndFrame": inEndFrame},
        )

    resolved = ags.resolve_nodes(inNodes)
    nodes = []
    refs = []
    for node in resolved:
        ref = ags.node_ref(node)
        if any(item["handle"] == ref["handle"] for item in refs):
            continue
        nodes.append(node)
        refs.append(ref)

    beforeStat = _file_stat(path)
    if beforeStat is not None and not inOverwrite:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"파일이 이미 있다. 덮어쓰려면 inOverwrite=True로 호출해야 한다: {path}",
            {"file": path},
        )

    rt = _runtime()
    fbxService = _header().fbx

    exportRange = None
    if inMatchAnimRange:
        sceneRange = _animation_range(rt)
        exportRange = [
            inStartFrame if inStartFrame is not None else sceneRange[0],
            inEndFrame if inEndFrame is not None else sceneRange[1],
        ]
        if exportRange[0] > exportRange[1]:
            raise ags.AgentApiError(
                ags.INVALID_ARGUMENT,
                f"베이크 구간 시작({exportRange[0]})이 끝({exportRange[1]})보다 크다",
                {"range": exportRange, "sceneRange": sceneRange},
            )

    missingDirs = _missing_dirs(path)
    # 원본 export_selection의 사용법: 내보낼 노드를 선택한 뒤 부른다(선택은 되돌리지 않는다)
    rt.select(rt.Array(*nodes))
    selectedHandles = {ags.node_ref(item)["handle"] for item in rt.getCurrentSelection()}
    notSelected = [ref for ref in refs if ref["handle"] not in selectedHandles]
    if notSelected:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"내보낼 노드 {len(notSelected)}개를 선택하지 못했다(숨김·동결 등)",
            {"notSelected": notSelected},
        )
    result = _call_original(
        "FBX 내보내기",
        fbxService.export_selection,
        path,
        inMatchAnimRange=inMatchAnimRange,
        inStartFrame=inStartFrame,
        inEndFrame=inEndFrame,
        inSmoothingGroups=inSmoothingGroups,
    )

    createdDirs = [item for item in missingDirs if os.path.isdir(item)]
    if not result:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "원본이 FBX 내보내기 실패를 돌려줬다(선택 없음·익스포터 없음·내보내기 실패)",
            {"file": path, "originalReturn": ags.to_json(result), "createdDirs": createdDirs},
        )
    fileBytes = _verify_written(path, beforeStat, "FBX 내보내기", result)

    return ags.readback(
        details={
            "file": path,
            "bytes": fileBytes,
            "overwritten": beforeStat is not None,
            "exported": refs,
            "range": exportRange,
            "createdDirs": createdDirs,
            "exporterOptionsChanged": True,
        },
    )


def import_fbx(inFilePath: str, inImportMode: str = "add_and_update_animation", inUpAxis: str = "Z") -> dict:
    """FBX 파일을 대화상자 없이 현재 장면으로 가져온다.

    가져오기 모드: ``"add_and_update_animation"``(새 노드 추가 + 이름이 같은 노드의 애니메이션 갱신),
    ``"update_animation"``(이름이 같은 기존 노드의 애니메이션만 갱신). 장면 animationRange를 파일에
    맞춰 바꿀 수 있다(``details``의 전후 구간). FBX 임포터 전역 옵션은 원본이 리셋·덮어쓴다.
    ``created``는 호출 전후 장면 노드 비교로 만든다. 애니메이션이 갱신된 기존 노드는 추적하지 않는다.

    Args:
        inFilePath: 가져올 ``.fbx`` 파일 경로(절대 경로 권장)
        inImportMode: ``"add_and_update_animation"`` 또는 ``"update_animation"``
        inUpAxis: ``"Z"`` 또는 ``"Y"``

    Returns:
        readback dict. ``created``=새로 생긴 노드, ``details={"file", "mode", "upAxis",
        "animationRangeBefore", "animationRangeAfter"}``(구간은 ``[시작, 끝]`` 프레임)

    Raises:
        AgentApiError: INVALID_ARGUMENT(파일 없음·확장자가 .fbx가 아님 — ``details["kind"]="file"``,
            모르는 모드·축 — ``details["valid"]``), OPERATION_FAILED(원본이 False 반환·원본 예외)

    Side effects: scene
    Undo: no

    Example:
        from pyjallib.max.agentapi import fbx; result = fbx.import_fbx("D:/Anim/Walk.fbx", "update_animation")
    """
    path = _require_fbx_path(inFilePath, inMustExist=True)
    if not isinstance(inImportMode, str) or inImportMode not in _IMPORT_MODES:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"모르는 가져오기 모드다: {inImportMode!r}",
            {"argument": "inImportMode", "input": repr(inImportMode), "valid": list(_IMPORT_MODES)},
        )
    if not isinstance(inUpAxis, str) or inUpAxis not in _UP_AXES:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"모르는 업 축이다: {inUpAxis!r}",
            {"argument": "inUpAxis", "input": repr(inUpAxis), "valid": list(_UP_AXES)},
        )

    rt = _runtime()
    fbxService = _header().fbx
    from pyjallib.max.agentapi import _scene

    rangeBefore = _animation_range(rt)
    handlesBefore = _scene.snapshot_handles()
    result = _call_original("FBX 가져오기", fbxService.import_fbx, path, inImportMode=inImportMode, inUpAxis=inUpAxis)
    created = _scene.created_since(handlesBefore)
    rangeAfter = _animation_range(rt)

    if not result:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            "원본이 FBX 가져오기 실패를 돌려줬다(파일 없음·임포터 없음·가져오기 실패)",
            {
                "file": path,
                "originalReturn": ags.to_json(result),
                "created": [ags.node_ref(item) for item in created],
            },
        )

    warnings = ["이름이 같은 기존 노드의 애니메이션 갱신은 modified로 추적하지 않는다"]
    if rangeAfter != rangeBefore:
        warnings.append(f"장면 animationRange가 {rangeBefore}에서 {rangeAfter}로 바뀌었다")

    return ags.readback(
        created=created,
        details={
            "file": path,
            "mode": inImportMode,
            "upAxis": inUpAxis,
            "animationRangeBefore": rangeBefore,
            "animationRangeAfter": rangeAfter,
        },
        warnings=warnings,
    )
