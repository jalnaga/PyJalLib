# -*- coding: utf-8 -*-
"""agentapi 공용 지원 모듈 — 모든 agentapi가 같은 방식으로 노드를 해석하고 결과를 JSON으로 돌려주게 한다.

각 툴·라이브러리의 ``agentapi`` 모듈이 공유하는 오류 형식, 노드 해석, JSON 변환,
readback 생성을 한곳에 둔다. agentapi 함수는 이 모듈만 써서 이름→노드 해석과
결과 직렬화를 처리한다.

함수 목록:
    AgentApiError — agentapi 실패를 알리는 예외. ``str(exc)``는 ``"<CODE>: <message>"`` [none]
    resolve_node — 이름·handle·NodeRef dict 하나를 장면 노드 하나로 해석한다 [none]
    resolve_nodes — 여러 입력을 순서대로 해석하고 실패를 모두 모아 한 번에 보고한다 [none]
    node_ref — 노드를 NodeRef dict ``{"name", "handle", "class"}``로 바꾼다 [none]
    to_json — Point3·Matrix3·Name·Color·노드 등을 재귀적으로 JSON 기본형으로 바꾼다 [none]
    readback — 장면 변경 결과 dict(created·modified·deleted·details·warnings)를 만든다 [none]
    report_progress — 장시간 함수의 진행 단계를 진행 파일에 원자적으로 기록한다(MCP가 정체를 감시한다) [file]
    progress_path — 진행 파일 경로 ``%LOCALAPPDATA%\\PyJal3DSMCP\\agentapi-progress\\<pid>.json``을 돌려준다 [none]

공통 오류 코드 상수:
    NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT, PRECONDITION_FAILED, OPERATION_FAILED

사전 조건:
    오류 형식·readback(dict 항목)·기본형 to_json·입력 형 검사는 pymxs 없이 동작한다.
    노드 해석과 pymxs 값 변환은 3ds Max의 Python에서만 동작한다. pymxs는 필요한
    함수 안에서만 지연 import하며, 이 모듈은 UI(PySide2 등)를 import하지 않는다.
    진행 신호(report_progress·progress_path)는 pymxs 없이 동작한다. import만으로는
    진행 폴더·로그 파일을 만들지 않는다(폴더는 첫 기록 때, Logger는 첫 경고 때 만든다).

handle 규약:
    handle은 노드 handle(``node.inode.handle``)이다. handle 조회는
    ``rt.maxOps.getNodeByHandle``을 쓴다. 장면 루트 노드는 해석 대상이 아니다.
"""

import json
import os
import tempfile
import threading
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# 공통 오류 코드
# ---------------------------------------------------------------------------

#: 이름·handle에 해당하는 장면 노드가 없다
NODE_NOT_FOUND = "NODE_NOT_FOUND"
#: 같은 이름의 장면 노드가 여러 개다(후보 handle은 details["handles"])
NODE_AMBIGUOUS = "NODE_AMBIGUOUS"
#: 인자 형이나 값이 허용 범위를 벗어났다
INVALID_ARGUMENT = "INVALID_ARGUMENT"
#: 장면·UI 상태 등 사전 조건이 맞지 않는다
PRECONDITION_FAILED = "PRECONDITION_FAILED"
#: 내부 처리가 실패했다(원래 예외나 실패 사유는 details)
OPERATION_FAILED = "OPERATION_FAILED"


class AgentApiError(Exception):
    """agentapi 함수의 실패를 알리는 예외.

    ``str(exc)``는 ``"<code>: <message>"`` 형식이라 traceback 마지막 줄만으로
    실패를 분류할 수 있다.

    Attributes:
        code: 오류 코드(공통 코드 상수 또는 ``<TOOL>_`` 접두 고유 코드)
        message: 사람이 읽는 설명
        details: 분류·복구에 필요한 추가 정보. 없으면 빈 dict
    """

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        """예외를 만든다.

        Args:
            code: 오류 코드
            message: 사람이 읽는 설명
            details: 추가 정보. None이면 빈 dict로 둔다
        """
        self.code = code
        self.message = message
        self.details = {} if details is None else details
        super().__init__(code, message, self.details)

    def __str__(self) -> str:
        """``"<code>: <message>"`` 문자열을 돌려준다."""
        return f"{self.code}: {self.message}"


# ---------------------------------------------------------------------------
# 내부 보조 — 순수 Python
# ---------------------------------------------------------------------------


def _type_name(inValue) -> str:
    """오류 상세에 쓸 값의 형 이름."""
    return type(inValue).__name__


def _is_handle_value(inValue) -> bool:
    """handle로 받을 수 있는 정수인지 판정한다(bool은 int 하위 클래스라 제외한다)."""
    return isinstance(inValue, int) and not isinstance(inValue, bool)


def _parse_node_input(inValue) -> tuple:
    """노드 입력의 형을 검사하고 해석 방식을 정한다. pymxs에 접근하지 않는다.

    Args:
        inValue: resolve_node에 들어온 입력

    Returns:
        ``(이름 또는 None, handle 또는 None)``. 둘 중 하나 이상은 None이 아니다.

    Raises:
        AgentApiError: INVALID_ARGUMENT — 허용하지 않는 형이거나 빈 이름일 때
    """
    if isinstance(inValue, str):
        if inValue == "":
            raise AgentApiError(INVALID_ARGUMENT, "노드 이름이 빈 문자열이다", {"input": inValue})
        return inValue, None

    if _is_handle_value(inValue):
        return None, inValue

    if isinstance(inValue, dict):
        name = inValue.get("name")
        handle = inValue.get("handle")
        if name is None and handle is None:
            raise AgentApiError(
                INVALID_ARGUMENT,
                "NodeRef dict에는 name 또는 handle이 있어야 한다",
                {"keys": sorted(str(key) for key in inValue)},
            )
        if name is not None and (not isinstance(name, str) or name == ""):
            raise AgentApiError(
                INVALID_ARGUMENT,
                "NodeRef의 name은 비어 있지 않은 문자열이어야 한다",
                {"name": repr(name), "type": _type_name(name)},
            )
        if handle is not None and not _is_handle_value(handle):
            raise AgentApiError(
                INVALID_ARGUMENT,
                "NodeRef의 handle은 정수여야 한다",
                {"handle": repr(handle), "type": _type_name(handle)},
            )
        return name, handle

    raise AgentApiError(
        INVALID_ARGUMENT,
        f"노드는 이름(str)·handle(int)·NodeRef(dict)로 지정해야 한다: {_type_name(inValue)}",
        {"type": _type_name(inValue), "input": repr(inValue)},
    )


def _json_key(inKey) -> str:
    """dict 키를 JSON 키(str)로 바꾼다."""
    return inKey if isinstance(inKey, str) else str(inKey)


def _require_iterable(inValue, inArgName: str) -> None:
    """readback 목록 인자가 항목 목록인지 확인한다(문자열을 글자 단위로 도는 실수를 막는다).

    Raises:
        AgentApiError: INVALID_ARGUMENT — 문자열·dict·순회 불가 값일 때
    """
    if isinstance(inValue, (str, bytes, dict)):
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"readback의 {inArgName}는 항목 목록이어야 한다: {_type_name(inValue)}",
            {"argument": inArgName, "type": _type_name(inValue)},
        )
    try:
        iter(inValue)
    except TypeError:
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"readback의 {inArgName}는 항목 목록이어야 한다: {_type_name(inValue)}",
            {"argument": inArgName, "type": _type_name(inValue)},
        ) from None


# ---------------------------------------------------------------------------
# 내부 보조 — pymxs (함수 안에서만 import)
# ---------------------------------------------------------------------------


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _node_handle(inNode) -> int:
    """노드 handle(``inode.handle``)을 int로 돌려준다."""
    return int(inNode.inode.handle)


def _find_by_name(inRt, inName: str):
    """대소문자까지 정확히 같은 이름의 장면 노드 하나를 찾는다.

    Max의 이름 조회는 대소문자를 무시하므로 후보를 모은 뒤 Python에서 정확히 비교한다.

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS
    """
    try:
        candidates = list(inRt.getNodeByName(inName, all=True))
    except Exception:  # noqa: BLE001 - all: 키워드를 받지 않는 환경이면 전체 순회로 대신한다
        candidates = list(inRt.objects)

    matches = [node for node in candidates if inRt.isValidNode(node) and node.name == inName]
    if not matches:
        raise AgentApiError(NODE_NOT_FOUND, f"이름이 '{inName}'인 노드가 없다", {"name": inName})
    if len(matches) > 1:
        handles = [_node_handle(node) for node in matches]
        raise AgentApiError(
            NODE_AMBIGUOUS,
            f"이름이 '{inName}'인 노드가 {len(matches)}개다. handle로 지정해야 한다",
            {"name": inName, "handles": handles},
        )
    return matches[0]


def _find_by_handle(inRt, inHandle: int):
    """노드 handle로 장면 노드를 찾는다.

    Raises:
        AgentApiError: NODE_NOT_FOUND
    """
    try:
        node = inRt.maxOps.getNodeByHandle(inHandle)
    except Exception:  # noqa: BLE001 - 범위를 벗어난 정수 등은 "없음"으로 본다
        node = None
    if node is None or not inRt.isValidNode(node):
        raise AgentApiError(NODE_NOT_FOUND, f"handle {inHandle}인 노드가 없다", {"handle": inHandle})
    return node


def _max_value_to_json(inValue):
    """pymxs 값(노드·Point·Matrix3 등)을 JSON 기본형으로 바꾼다. 모르는 값은 str이다."""
    try:
        import pymxs
    except ImportError:
        return str(inValue)

    wrapperType = getattr(pymxs, "MXSWrapperBase", None)
    if not isinstance(wrapperType, type) or not isinstance(inValue, wrapperType):
        return str(inValue)

    rt = pymxs.runtime
    try:
        if rt.isValidNode(inValue):
            return node_ref(inValue)
        valueClass = rt.classOf(inValue)
        if valueClass == rt.Point3:
            return [float(inValue.x), float(inValue.y), float(inValue.z)]
        if valueClass == rt.Point2:
            return [float(inValue.x), float(inValue.y)]
        if valueClass == rt.Point4 or valueClass == rt.Quat:
            return [float(inValue.x), float(inValue.y), float(inValue.z), float(inValue.w)]
        if valueClass == rt.Color:
            return [float(inValue.r), float(inValue.g), float(inValue.b), float(inValue.a)]
        if valueClass == rt.Matrix3:
            rows = (inValue.row1, inValue.row2, inValue.row3, inValue.row4)
            return [[float(row.x), float(row.y), float(row.z)] for row in rows]
        if valueClass == rt.Name:
            return str(inValue)
        if valueClass == rt.Array:
            return [to_json(item) for item in inValue]
    except AgentApiError:
        raise
    except Exception:  # noqa: BLE001 - 판별 중 실패한 값(삭제된 노드 등)은 문자열로 남긴다
        pass
    return str(inValue)


# ---------------------------------------------------------------------------
# 공개 함수
# ---------------------------------------------------------------------------


def resolve_node(inName):
    """이름·handle·NodeRef dict 하나를 장면 노드 하나로 해석한다.

    - ``str``: 이름이 대소문자까지 정확히 같은 노드. 없으면 NODE_NOT_FOUND,
      여러 개면 NODE_AMBIGUOUS(``details["handles"]``에 후보 handle 목록).
    - ``int``: 노드 handle. 없으면 NODE_NOT_FOUND.
    - ``dict``(NodeRef): ``handle``이 있으면 handle로 찾고, ``name``도 있으면 이름이
      일치하는지 확인한다(불일치는 NODE_NOT_FOUND, details에 요청 이름과 실제 이름).
      ``name``만 있으면 이름으로 찾는다.

    형 검사는 pymxs에 접근하기 전에 끝난다.

    Args:
        inName: 노드 이름(str), 노드 handle(int), 또는 NodeRef dict

    Returns:
        해석한 pymxs 노드

    Raises:
        AgentApiError: INVALID_ARGUMENT(bool·float·None·빈 문자열·그 밖의 형,
            name·handle이 없는 dict), NODE_NOT_FOUND, NODE_AMBIGUOUS

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max import agentSupport as ags; node = ags.resolve_node("Bip001 Pelvis")
    """
    name, handle = _parse_node_input(inName)
    rt = _runtime()

    if handle is None:
        return _find_by_name(rt, name)

    node = _find_by_handle(rt, handle)
    if name is not None and node.name != name:
        raise AgentApiError(
            NODE_NOT_FOUND,
            f"handle {handle}의 노드 이름은 '{node.name}'이고 요청한 이름 '{name}'과 다르다",
            {"name": name, "handle": handle, "actualName": str(node.name)},
        )
    return node


def resolve_nodes(inNames) -> list:
    """여러 노드 입력을 입력 순서대로 해석한다. 실패는 모두 모아 예외 하나로 보고한다.

    Args:
        inNames: resolve_node가 받는 입력의 list 또는 tuple

    Returns:
        입력 순서와 같은 순서의 pymxs 노드 list

    Raises:
        AgentApiError: inNames가 list/tuple이 아니면 INVALID_ARGUMENT. 항목 실패가 있으면
            입력 순서상 첫 실패의 코드로 던지고, ``details["failures"]``에
            ``{"index", "input", "code", "message", "details"}`` 목록을 담는다.

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max import agentSupport as ags; nodes = ags.resolve_nodes(["Bip001 Pelvis", "Bip001 Spine"])
    """
    if not isinstance(inNames, (list, tuple)):
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"노드 목록은 list 또는 tuple이어야 한다: {_type_name(inNames)}",
            {"type": _type_name(inNames)},
        )

    nodes = []
    failures = []
    for index, value in enumerate(inNames):
        try:
            nodes.append(resolve_node(value))
        except AgentApiError as error:
            failures.append(
                {
                    "index": index,
                    "input": value,
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            )

    if failures:
        first = failures[0]
        raise AgentApiError(
            first["code"],
            f"노드 {len(inNames)}개 중 {len(failures)}개를 해석하지 못했다. "
            f"첫 실패 index {first['index']}: {first['message']}",
            {"failures": failures},
        )
    return nodes


def node_ref(inNode) -> dict:
    """노드를 NodeRef dict로 바꾼다.

    Args:
        inNode: pymxs 장면 노드

    Returns:
        ``{"name": str, "handle": int, "class": str}``. handle은 노드 handle,
        class는 ``str(rt.classOf(node))``다.

    Raises:
        AgentApiError: INVALID_ARGUMENT — 유효한 장면 노드가 아닐 때(삭제된 노드 포함)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max import agentSupport as ags; result = ags.node_ref(ags.resolve_node("Box001"))
    """
    rt = _runtime()
    if not rt.isValidNode(inNode):
        raise AgentApiError(
            INVALID_ARGUMENT,
            "유효한 장면 노드가 아니다",
            {"type": _type_name(inNode), "input": str(inNode)},
        )
    return {
        "name": str(inNode.name),
        "handle": _node_handle(inNode),
        "class": str(rt.classOf(inNode)),
    }


def to_json(inValue):
    """값을 ``json.dumps`` 가능한 형태로 재귀 변환한다.

    변환 규칙:
        - None·bool·int·float·str: 그대로
        - list·tuple: list (항목 재귀 변환)
        - dict: dict (키는 str, 값 재귀 변환)
        - 노드: NodeRef
        - rt.Name: 이름 문자열
        - Point2: ``[x, y]`` / Point3: ``[x, y, z]`` / Point4·Quat: ``[x, y, z, w]``
        - Color: ``[r, g, b, a]``
        - Matrix3: ``[row1, row2, row3, row4]`` (각 행 ``[x, y, z]``)
        - MAXScript Array: list (항목 재귀 변환)
        - 그 밖의 값: ``str(value)``

    기본형·list·tuple·dict만 있으면 pymxs에 접근하지 않는다.

    Args:
        inValue: 변환할 값

    Returns:
        JSON 기본형으로 이루어진 값

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max import agentSupport as ags; result = ags.to_json({"pos": ags.resolve_node("Box001").pos})
    """
    if inValue is None or isinstance(inValue, (bool, int, float, str)):
        return inValue
    if isinstance(inValue, (list, tuple)):
        return [to_json(item) for item in inValue]
    if isinstance(inValue, dict):
        return {_json_key(key): to_json(item) for key, item in inValue.items()}
    return _max_value_to_json(inValue)


def readback(created=(), modified=(), deleted=(), details=None, warnings=()) -> dict:
    """장면·파일을 바꾸는 agentapi 함수의 반환 dict(readback)를 만든다.

    Args:
        created: 생성한 노드 또는 NodeRef dict 목록
        modified: 수정한 노드 또는 NodeRef dict 목록
        deleted: 삭제한 노드 이름 목록
        details: 함수별 추가 정보 dict. None이면 빈 dict. to_json을 거친다
        warnings: 부분 적용·건너뛴 항목 설명 목록

    Returns:
        ``{"created": [NodeRef], "modified": [NodeRef], "deleted": [str],
        "details": dict, "warnings": [str]}``. 키 5개가 항상 있다.

    Raises:
        AgentApiError: INVALID_ARGUMENT — 목록 인자가 문자열·dict 등 항목 목록이 아니거나,
            created·modified 항목이 노드도 dict도 아니거나, details가 dict가 아닐 때

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max import agentSupport as ags; result = ags.readback(modified=[ags.resolve_node("Box001")])
    """
    for argName, argValue in (
        ("created", created),
        ("modified", modified),
        ("deleted", deleted),
        ("warnings", warnings),
    ):
        _require_iterable(argValue, argName)
    if details is not None and not isinstance(details, dict):
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"readback의 details는 dict여야 한다: {_type_name(details)}",
            {"argument": "details", "type": _type_name(details)},
        )

    def _ref_item(inItem):
        """created·modified 항목: dict는 그대로(JSON 정리만), 노드는 NodeRef."""
        if isinstance(inItem, dict):
            return to_json(inItem)
        return node_ref(inItem)

    return {
        "created": [_ref_item(item) for item in created],
        "modified": [_ref_item(item) for item in modified],
        "deleted": [item if isinstance(item, str) else str(item) for item in deleted],
        "details": {} if details is None else to_json(details),
        "warnings": [item if isinstance(item, str) else str(item) for item in warnings],
    }


# ---------------------------------------------------------------------------
# 진행 신호 (agentapi 2차 G6 — PyJal3DSMCP가 진행 파일의 정체를 감시한다)
# ---------------------------------------------------------------------------

#: 진행 파일 형식 버전
_PROGRESS_SCHEMA_VERSION = 1
#: 진행 파일 상위 폴더(LOCALAPPDATA 기준). PyJal3DSMCP와 맞춘 계약 경로다
_PROGRESS_SUBDIR = ("PyJal3DSMCP", "agentapi-progress")
#: 진행 쓰기 실패 경고를 남길 pyjallib Logger 파일 이름
_PROGRESS_LOG_NAME = "pyjallib_agentProgress"

#: seq 증가를 직렬화한다(같은 프로세스의 여러 스레드가 불러도 seq가 겹치지 않는다)
_progressLock = threading.Lock()
#: 이 프로세스에서 마지막으로 발급한 seq
_progressSeq = 0
#: 모듈 단일 지연 Logger. import 때 만들지 않는다(로그 파일이 import만으로 생기지 않게)
_progressLogger = None


def _progress_root() -> str:
    """진행 파일 상위 폴더 경로. LOCALAPPDATA를 호출 시점에 읽는다.

    LOCALAPPDATA가 없으면 Windows 기본 위치(``~/AppData/Local``)로 둔다.
    """
    localAppData = os.environ.get("LOCALAPPDATA")
    if not localAppData:
        localAppData = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(localAppData, *_PROGRESS_SUBDIR)


def _next_progress_seq() -> int:
    """프로세스 안에서 증가하는 다음 seq를 발급한다."""
    global _progressSeq
    with _progressLock:
        _progressSeq += 1
        return _progressSeq


def _progress_warn(inMessage: str) -> None:
    """진행 쓰기 실패를 pyjallib Logger 경고로 남긴다. 경고 자체의 실패도 삼킨다."""
    global _progressLogger
    try:
        if _progressLogger is None:
            from pyjallib.logger import Logger

            _progressLogger = Logger(inLogFileName=_PROGRESS_LOG_NAME, inEnableConsole=False)
        _progressLogger.warning(inMessage)
    except Exception:  # noqa: BLE001 - 진행 신호는 보고 수단이라 로그 실패로 작업을 막지 않는다
        pass


def _require_progress_text(inValue, inArgName: str) -> None:
    """operation·step이 비어 있지 않은 문자열인지 확인한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inValue, str) or inValue == "":
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"report_progress의 {inArgName}는 비어 있지 않은 문자열이어야 한다: {_type_name(inValue)}",
            {"argument": inArgName, "type": _type_name(inValue), "input": repr(inValue)},
        )


def _write_progress_file(inTargetPath: str, inPayload: bytes) -> None:
    """임시 파일에 전부 쓴 뒤 ``os.replace``로 대상을 교체한다.

    판독자는 교체 전의 완전한 파일이나 교체 후의 완전한 파일만 본다. 실패하면 임시 파일을
    지우고 원래 예외를 그대로 올린다(호출자가 경고로 바꾼다).
    """
    targetDir = os.path.dirname(inTargetPath)
    os.makedirs(targetDir, exist_ok=True)
    baseName = os.path.basename(inTargetPath)
    fd, tempPath = tempfile.mkstemp(prefix=f"{baseName}.", suffix=".tmp", dir=targetDir)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(inPayload)
        os.replace(tempPath, inTargetPath)
    except BaseException:
        try:
            os.remove(tempPath)
        except OSError:
            pass
        raise


def progress_path(inPid: int | None = None) -> str:
    """진행 파일 경로를 돌려준다.

    경로는 ``%LOCALAPPDATA%\\PyJal3DSMCP\\agentapi-progress\\<pid>.json``이다. LOCALAPPDATA는
    호출할 때 읽는다. 폴더를 만들거나 파일에 접근하지 않는다.

    Args:
        inPid: 프로세스 ID. None이면 현재 프로세스(3ds Max)의 PID

    Returns:
        진행 파일 절대 경로 문자열

    Raises:
        AgentApiError: INVALID_ARGUMENT — inPid가 None도 정수도 아닐 때(bool 포함)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max import agentSupport as ags; result = {"path": ags.progress_path()}
    """
    if inPid is None:
        pid = os.getpid()
    elif _is_handle_value(inPid):
        pid = inPid
    else:
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"progress_path의 inPid는 정수 또는 None이어야 한다: {_type_name(inPid)}",
            {"argument": "inPid", "type": _type_name(inPid), "input": repr(inPid)},
        )
    return os.path.abspath(os.path.join(_progress_root(), f"{pid}.json"))


def report_progress(inOperation: str, inStep: str, inDetail: dict | None = None) -> None:
    """장시간 agentapi 함수의 진행 단계를 현재 프로세스의 진행 파일에 기록한다.

    파일 내용은 JSON 객체 ``{"schema_version": 1, "pid", "operation", "step", "detail",
    "seq", "updated_at"}``다. seq는 프로세스 안에서 호출마다 증가하고, updated_at은 UTC
    ISO 8601(``+00:00``)이다. 임시 파일에 쓴 뒤 ``os.replace``로 교체하므로 읽는 쪽은
    깨진 JSON을 보지 않는다. 진행 폴더는 첫 호출 때 만든다.

    래퍼는 시작(``start``), 항목 사이, 긴 원본 호출 직전·직후, 끝(``done``/``failed``)에
    부른다. PyJal3DSMCP는 실행 중 이 파일의 updated_at이 오래 바뀌지 않으면 "진행 없음"을
    보고한다(Max 호출은 중단하지 않는다).

    쓰기 실패(폴더 생성·파일 쓰기·교체 실패)는 예외를 올리지 않고 pyjallib Logger 경고만
    남긴다. 진행 신호는 보고 수단이지 작업의 일부가 아니다. 다음 호출은 다시 쓴다.

    Args:
        inOperation: 에이전트 함수 이름(비어 있지 않은 문자열)
        inStep: 짧은 단계 이름(비어 있지 않은 문자열). 예 ``start``·``item``·``done``
        inDetail: JSON 직렬화 가능한 dict. 예 ``{"index": 3, "total": 20}``.
            None이면 빈 dict로 기록한다

    Returns:
        None

    Raises:
        AgentApiError: INVALID_ARGUMENT — operation·step이 비어 있지 않은 문자열이 아니거나,
            inDetail이 dict가 아니거나 JSON으로 직렬화할 수 없을 때. 이때 진행 파일은
            바뀌지 않는다

    Side effects: file
    Undo: no

    Example:
        from pyjallib.max import agentSupport as ags; ags.report_progress("run_batch_export", "item", {"index": 3, "total": 20})
    """
    _require_progress_text(inOperation, "inOperation")
    _require_progress_text(inStep, "inStep")
    if inDetail is None:
        detail = {}
    elif isinstance(inDetail, dict):
        detail = inDetail
    else:
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"report_progress의 inDetail은 dict 또는 None이어야 한다: {_type_name(inDetail)}",
            {"argument": "inDetail", "type": _type_name(inDetail)},
        )

    # detail은 seq를 발급하기 전에 직렬화해 본다. 거절한 호출은 seq·파일을 건드리지 않는다.
    try:
        json.dumps(detail, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise AgentApiError(
            INVALID_ARGUMENT,
            f"report_progress의 inDetail을 JSON으로 직렬화할 수 없다: {error}",
            {"argument": "inDetail", "error": f"{type(error).__name__}: {error}"},
        ) from None

    record = {
        "schema_version": _PROGRESS_SCHEMA_VERSION,
        "pid": os.getpid(),
        "operation": inOperation,
        "step": inStep,
        "detail": detail,
        "seq": _next_progress_seq(),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
    payload = json.dumps(record, ensure_ascii=False).encode("utf-8")

    targetPath = progress_path()
    try:
        _write_progress_file(targetPath, payload)
    except Exception as error:  # noqa: BLE001 - 쓰기 실패는 작업을 막지 않는다(경고만)
        _progress_warn(
            f"agentapi 진행 파일을 쓰지 못했다(operation={inOperation}, step={inStep}, "
            f"seq={record['seq']}): {targetPath}: {type(error).__name__}: {error}"
        )
