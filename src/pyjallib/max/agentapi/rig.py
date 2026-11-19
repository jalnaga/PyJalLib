# -*- coding: utf-8 -*-
"""릭 에이전트 인터페이스 — 에이전트가 트위스트 본·볼륨 본 체인을 만들고 체인 정보로 다시 만든다.

함수 목록:
    create_twist_bones — 두 본 사이에 트위스트 본 체인을 만든다 [scene]
    rebuild_twist_bones — 트위스트 체인을 지우고 같은 소스·파라미터로 다시 만든다(inConfirm 필요) [scene]
    create_volume_bones — 관절에 볼륨 본 체인(루트 본·볼륨 본·회전 헬퍼)을 만든다 [scene]
    rebuild_volume_bones — 볼륨 체인을 지우고 같은 소스·파라미터로 다시 만든다(inConfirm 필요) [scene]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    체인은 장면에 저장되지 않는 값이므로 생성 함수가 돌려준 ``details["chain"]`` dict로 표현한다:
    ``{"part": "TwistBone" | "VolumeBone", "bones": [NodeRef], "helpers": [NodeRef],
    "sourceBones": [NodeRef], "parameters": {원본 PARAM_SPEC 키: 값}}``. 재생성 함수는 이 dict를 받는다.
    ``parameters`` 키는 원본 철자(``inRotAxises``·``inTransAxises``)이고, ``create_volume_bones``의
    인자 ``inRotAxes``·``inTransAxes``가 그 키로 옮겨진다.
    원본의 실패 사유는 콘솔이 꺼진 로그 파일 ``pyjallib_rig``에만 남는다(OPERATION_FAILED의
    ``details["log"]``).
    이 모듈은 import할 때 pymxs·header를 불러오지 않고 장면을 바꾸지 않는다.

호출 예:
    from pyjallib.max.agentapi import rig; result = rig.create_twist_bones("Bip001 L UpperArm", "Bip001 L Forearm", 4, "Upper")
"""

from pyjallib.max import agentSupport as ags
from pyjallib.max.agentapi import _scene

#: 트위스트 타입(원본 TwistBone._TWIST_MODES 키)
_TWIST_TYPES = ("Upper", "Lower")

#: 체인 dict 필수 키
_CHAIN_KEYS = ("part", "bones", "helpers", "sourceBones", "parameters")

#: 원본 실패 사유가 남는 로그 파일 이름(rig/boneChain.py)
_RIG_LOG = "pyjallib_rig"


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


def _is_int(inValue) -> bool:
    """bool을 뺀 정수인지."""
    return isinstance(inValue, int) and not isinstance(inValue, bool)


def _is_number(inValue) -> bool:
    """bool을 뺀 int·float인지."""
    return isinstance(inValue, (int, float)) and not isinstance(inValue, bool)


def _invalid(inMessage: str, inDetails: dict) -> ags.AgentApiError:
    """INVALID_ARGUMENT 오류."""
    return ags.AgentApiError(ags.INVALID_ARGUMENT, inMessage, inDetails)


def _require_bool(inValue, inArgName: str) -> None:
    """bool 인자인지 확인한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inValue, bool):
        raise _invalid(f"{inArgName}는 bool이어야 한다: {type(inValue).__name__}", {"argument": inArgName})


def _check_twist_parameters(inTwistNum, inTwistType) -> None:
    """트위스트 파라미터 값 검사.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not _is_int(inTwistNum) or inTwistNum < 1:
        raise _invalid("inTwistNum은 1 이상의 정수여야 한다", {"argument": "inTwistNum", "input": repr(inTwistNum)})
    if not isinstance(inTwistType, str) or inTwistType not in _TWIST_TYPES:
        raise _invalid(
            f"inTwistType은 {list(_TWIST_TYPES)} 중 하나여야 한다: {inTwistType!r}",
            {"argument": "inTwistType", "input": repr(inTwistType), "valid": list(_TWIST_TYPES)},
        )


def _volume_parameter_values(inParameters: dict) -> dict:
    """볼륨 파라미터(원본 철자 키, None은 원본 기본값으로 채움)를 검사하고 원본에 넘길 값으로 돌려준다.

    원본 ``VolumeBone.create_bones``와 같이 None인 축 목록은 원본 PARAM_SPEC 기본값으로 채운 뒤,
    축 목록 길이와 등록 축(원본 공개 함수 ``invalid_axes``)을 본을 만들기 전에 검사한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    from pyjallib.max.rig.volumeBone import VolumeBone, invalid_axes

    defaults = VolumeBone.default_parameters()
    values = {}
    for key in ("inRotScale", "inVolumeSize"):
        value = inParameters.get(key, defaults[key])
        if not _is_number(value):
            raise _invalid(f"{key}는 숫자여야 한다", {"argument": key, "input": repr(value)})
        values[key] = float(value)
    for key, itemCheck, label in (
        ("inRotAxises", lambda item: isinstance(item, str), "문자열"),
        ("inTransAxises", lambda item: isinstance(item, str), "문자열"),
        ("inTransScales", _is_number, "숫자"),
    ):
        value = inParameters.get(key)
        if value is None:
            value = defaults[key]
        if not isinstance(value, (list, tuple)) or not all(itemCheck(item) for item in value):
            raise _invalid(f"{key}는 {label} 목록이어야 한다", {"argument": key, "input": repr(value)})
        values[key] = [float(item) for item in value] if key == "inTransScales" else list(value)

    lengths = {key: len(values[key]) for key in ("inRotAxises", "inTransAxises", "inTransScales")}
    if len(set(lengths.values())) != 1 or lengths["inRotAxises"] == 0:
        raise _invalid("회전 축·이동 축·이동 스케일 목록의 길이가 같아야 하고 비어 있으면 안 된다", {"lengths": lengths})
    invalid = invalid_axes(values["inRotAxises"], values["inTransAxises"])
    if invalid:
        raise _invalid(
            f"미등록 축이 있다: {invalid}",
            {"invalid": invalid, "validRotAxes": ["X", "Y", "Z"], "validTransAxes": ["PosX", "NegX", "PosY", "NegY", "PosZ", "NegZ"]},
        )
    return values


def _resolve_pair(inFirst, inSecond, inSecondArg: str) -> tuple:
    """노드 두 개를 해석하고 같은 노드면 거절한다.

    Raises:
        AgentApiError: NODE_NOT_FOUND, NODE_AMBIGUOUS, INVALID_ARGUMENT
    """
    first, second = ags.resolve_nodes([inFirst, inSecond])
    if _handle(first) == _handle(second):
        raise _invalid(
            f"inNode와 {inSecondArg}가 같은 노드다", {"node": ags.node_ref(first), "argument": inSecondArg}
        )
    return first, second


def _chain_dict(inPart: str, inChain) -> dict:
    """원본 ``BoneChain``을 체인 dict로 바꾼다."""
    rt = _runtime()

    def _refs(inNodes) -> list:
        return [ags.node_ref(node) for node in inNodes if node is not None and rt.isValidNode(node)]

    return {
        "part": inPart,
        "bones": _refs(inChain.bones),
        "helpers": _refs(inChain.helpers),
        "sourceBones": _refs(inChain.sourceBones),
        "parameters": ags.to_json(dict(inChain.parameters)),
    }


def _chain_warnings(inChain, inCreated: list) -> list:
    """체인 노드와 장면 차이가 어긋나면 warnings."""
    rt = _runtime()
    chainHandles = {_handle(node) for node in list(inChain.bones) + list(inChain.helpers) if node is not None and rt.isValidNode(node)}
    createdHandles = {_handle(node) for node in inCreated}
    warnings = []
    outside = [node for node in inCreated if _handle(node) not in chainHandles]
    if outside:
        warnings.append(
            f"원본이 체인 밖의 노드 {len(outside)}개를 만들고 남겼다: " + ", ".join(f"'{node.name}'" for node in outside)
        )
    if chainHandles - createdHandles:
        warnings.append(f"체인 노드 {len(chainHandles - createdHandles)}개가 이번 호출로 생긴 노드가 아니다")
    return warnings


def _create_chain(inPart: str, inAction: str, inCall, inDetails: dict) -> dict:
    """원본 생성 메서드(``create_bones``)를 부르고 readback을 만든다.

    Raises:
        AgentApiError: OPERATION_FAILED(원본 예외·None 반환)
    """
    before = _scene.snapshot_handles()
    try:
        chain = inCall()
    except Exception as error:  # noqa: BLE001
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED,
            f"{inAction} 중 원본 처리가 실패했다: {error}",
            dict(inDetails, exception=repr(error), created=[ags.node_ref(node) for node in _scene.created_since(before)]),
        ) from error
    created = _scene.created_since(before)
    if chain is None:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"{inAction}: 원본이 실패(None)를 돌려줬다(사유는 로그 파일 '{_RIG_LOG}')",
            dict(inDetails, log=_RIG_LOG, originalReturn=None, created=[ags.node_ref(node) for node in created]),
        )
    return ags.readback(
        created=created,
        details={"chain": _chain_dict(inPart, chain)},
        warnings=_chain_warnings(chain, created),
    )


def _rebuild_chain(inChain, inConfirm, inPart: str, inServiceName: str) -> dict:
    """체인 dict 형식을 검사·해석하고 원본 ``create_bones_from_chain``을 그대로 부른다.

    체인 dict 형식·필수 키·part·PARAM_SPEC 밖 키, 체인 노드와 inConfirm을 검사한다. 원본이 체인을 지운 뒤 실패하는 경로(빈 체인·소스 수·파라미터 값·소스가 삭제 대상에 포함)는
    막지 않는다.

    Raises:
        AgentApiError: INVALID_ARGUMENT, NODE_NOT_FOUND, NODE_AMBIGUOUS, PRECONDITION_FAILED, OPERATION_FAILED
    """
    _require_bool(inConfirm, "inConfirm")
    if not isinstance(inChain, dict):
        raise _invalid("inChain은 체인 dict여야 한다", {"argument": "inChain", "type": type(inChain).__name__})
    missingKeys = [key for key in _CHAIN_KEYS if key not in inChain]
    if missingKeys:
        raise _invalid(f"inChain에 필수 키가 없다: {missingKeys}", {"argument": "inChain", "missing": missingKeys})
    if inChain["part"] != inPart:
        raise _invalid(
            f"inChain의 part가 '{inPart}'가 아니다: {inChain['part']!r}",
            {"argument": "inChain", "part": repr(inChain["part"]), "expected": inPart},
        )
    for key in ("bones", "helpers", "sourceBones"):
        if not isinstance(inChain[key], (list, tuple)):
            raise _invalid(f"inChain['{key}']는 NodeRef 목록이어야 한다", {"argument": "inChain", "key": key})
    parameters = inChain["parameters"]
    if not isinstance(parameters, dict):
        raise _invalid("inChain['parameters']는 dict여야 한다", {"argument": "inChain", "key": "parameters"})

    header = _header()
    service = getattr(header, inServiceName)
    specNames = list(service.param_names())
    unknown = [key for key in parameters if key not in specNames]
    if unknown:
        raise _invalid(
            f"inChain['parameters']에 원본 PARAM_SPEC 밖 키가 있다: {unknown}",
            {"argument": "inChain", "unknown": unknown, "valid": specNames},
        )

    # 체인 노드는 모두 해석돼야 한다
    bones = ags.resolve_nodes(list(inChain["bones"]))
    helpers = ags.resolve_nodes(list(inChain["helpers"]))
    sources = ags.resolve_nodes(list(inChain["sourceBones"]))
    toDelete = bones + helpers
    toDeleteRefs = [ags.node_ref(node) for node in toDelete]

    if not inConfirm:
        raise ags.AgentApiError(
            ags.PRECONDITION_FAILED,
            f"재생성은 체인 노드 {len(toDelete)}개를 지운다. 지워도 되면 inConfirm=True로 다시 호출한다",
            {"toDelete": toDeleteRefs, "toDeleteNames": [ref["name"] for ref in toDeleteRefs]},
        )

    from pyjallib.max.rig.boneChain import BoneChain

    rt = _runtime()
    boneChain = BoneChain.from_result(
        {"Bones": bones, "Helpers": helpers, "SourceBones": sources, "Parameters": dict(parameters)}
    )

    def _deleted_names() -> list:
        return [ref["name"] for node, ref in zip(toDelete, toDeleteRefs) if not rt.isValidNode(node)]

    before = _scene.snapshot_handles()
    try:
        newChain = service.create_bones_from_chain(boneChain)
    except Exception as error:  # noqa: BLE001 - 지운 노드·부분 생성을 숨기지 않는다
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT if isinstance(error, ValueError) else ags.OPERATION_FAILED,
            f"{inPart} 재생성 중 원본 처리가 실패했다: {error}",
            {
                "exception": repr(error),
                "deleted": _deleted_names(),
                "created": [ags.node_ref(node) for node in _scene.created_since(before)],
            },
        ) from error
    created = _scene.created_since(before)
    deleted = _deleted_names()
    if newChain is None:
        raise ags.AgentApiError(
            ags.OPERATION_FAILED,
            f"{inPart} 재생성: 원본이 실패(None)를 돌려줬다(사유는 로그 파일 '{_RIG_LOG}')",
            {
                "log": _RIG_LOG,
                "originalReturn": None,
                "deleted": deleted,
                "created": [ags.node_ref(node) for node in created],
            },
        )

    warnings = _chain_warnings(newChain, created)
    notDeleted = [ref["name"] for node, ref in zip(toDelete, toDeleteRefs) if rt.isValidNode(node)]
    if notDeleted:
        warnings.append(f"원본이 옛 체인 노드 {len(notDeleted)}개를 지우지 않았다: {notDeleted}")
    return ags.readback(
        created=created,
        deleted=deleted,
        details={"chain": _chain_dict(inPart, newChain)},
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def create_twist_bones(
    inNode: str | int | dict, inChild: str | int | dict, inTwistNum: int = 4, inTwistType: str = "Upper"
) -> dict:
    """두 본 사이에 트위스트 본 체인을 만든다(원본 ``TwistBone.create_bones``).

    ``"Upper"``는 부모 쪽이 도는 상완·대퇴부용, ``"Lower"``는 자식 쪽이 도는 전완·하퇴부용이다.
    소스 중 하나라도 스킨 본이면 원본이 생성 본도 스킨 본으로 표시한다. ``"Upper"``는 inNode의 부모를
    쓰므로 부모가 없는 본이면 원본이 예외로 실패한다(OPERATION_FAILED, ``details["exception"]``).

    Args:
        inNode: 트위스트 본을 붙일 본(상완·전완·대퇴부·하퇴부. 이름·handle·NodeRef)
        inChild: inNode의 자식 본(이름·handle·NodeRef). inNode와 달라야 한다
        inTwistNum: 만들 트위스트 본 수(1 이상)
        inTwistType: ``"Upper"`` 또는 ``"Lower"``

    Returns:
        readback dict. ``created``=새 노드(장면 handle 차이), ``details={"chain": 체인 dict}``
        (``parameters``는 ``{"inTwistNum", "inTwistType"}``, 트위스트 체인은 ``helpers``가 비었다)

    Raises:
        AgentApiError: INVALID_ARGUMENT(inTwistType이 Upper·Lower가 아님, inTwistNum < 1, 같은 노드),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, OPERATION_FAILED(원본 예외 — ``details["exception"]``,
            원본이 None 반환 — ``details["log"]="pyjallib_rig"``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import rig; result = rig.create_twist_bones("Bip001 L UpperArm", "Bip001 L Forearm", 4, "Upper")
    """
    _check_twist_parameters(inTwistNum, inTwistType)
    node, child = _resolve_pair(inNode, inChild, "inChild")
    twistService = _header().twistBone
    return _create_chain(
        "TwistBone",
        "트위스트 본 생성",
        lambda: twistService.create_bones(node, child, inTwistNum=inTwistNum, inTwistType=inTwistType),
        {"sources": [ags.node_ref(node), ags.node_ref(child)]},
    )


def rebuild_twist_bones(inChain: dict, inConfirm: bool = False) -> dict:
    """트위스트 체인의 본을 지우고 같은 소스 본·파라미터로 다시 만든다(원본 ``create_bones_from_chain``).

    **원본은 체인의 bones·helpers 노드를 삭제한 뒤 다시 만든다.** 그래서 ``inConfirm=True``일 때만
    진행하고, ``inConfirm=False``(기본)면 장면을 바꾸지 않고 PRECONDITION_FAILED로 삭제 예정 노드
    (``details["toDelete"]``)를 알려 준다. 체인 dict는 ``create_twist_bones``·``rebuild_twist_bones``가
    돌려준 ``details["chain"]``을 그대로 넘긴다. 체인 노드는 모두 장면에서 해석돼야 한다. 파라미터 값은
    검사하지 않고 원본에 그대로 넘긴다. **경고: 원본은 옛 노드를 먼저 지우므로, 그 뒤 원본이 실패(None
    반환·예외)하면 옛 체인 노드는 사라진 채 새 노드가 만들어지지 않는다**(OPERATION_FAILED의
    ``details["deleted"]``). bones가 빈 체인·소스 수가 맞지 않는 체인은 원본이 None을 돌려준다.

    Args:
        inChain: 체인 dict(``part="TwistBone"``, bones·helpers·sourceBones NodeRef 목록, parameters)
        inConfirm: True여야 옛 체인 노드를 지우고 다시 만든다. False면 삭제 예정 노드만 알려 준다

    Returns:
        readback dict. ``created``=새 노드, ``deleted``=지운 옛 노드 이름, ``details={"chain": 새 체인 dict}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(체인 형식 — dict 아님·필수 키 누락·part가 TwistBone이 아님·
            원본 PARAM_SPEC 밖 parameters 키, inConfirm이 bool이 아님),
            NODE_NOT_FOUND·NODE_AMBIGUOUS(체인 노드 해석 실패), PRECONDITION_FAILED(inConfirm=False —
            ``details["toDelete"]``), OPERATION_FAILED(원본 None 반환 — ``details["log"]="pyjallib_rig"``,
            원본 예외 — ``details["exception"]``. 둘 다 ``details["deleted"]``에 원본이 이미 지운 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import rig; result = rig.rebuild_twist_bones(chain, inConfirm=True)
    """
    return _rebuild_chain(inChain, inConfirm, "TwistBone", "twistBone")


def create_volume_bones(
    inNode: str | int | dict,
    inParent: str | int | dict,
    inRotScale: float = 0.5,
    inVolumeSize: float = 5.0,
    inRotAxes: list | None = None,
    inTransAxes: list | None = None,
    inTransScales: list | None = None,
) -> dict:
    """관절에 볼륨 본 체인(루트 본 1 + 축마다 볼륨 본 1 + 회전 헬퍼 1)을 만든다(원본 ``VolumeBone.create_bones``).

    관절이 굽을 때 줄어드는 부피를 보정하는 본이다. 루트 본은 관절 회전을 inRotScale만큼 따라가고
    볼륨 본은 굽힘 각도에 비례해 지정 축으로 밀려난다. 인자 ``inRotAxes``·``inTransAxes``는 원본
    인자 ``inRotAxises``·``inTransAxises``로 넘기며 체인 ``parameters``에는 원본 철자 키로 남는다.
    None인 축 목록은 원본 기본값(``["Z"]``·``["PosY"]``·``[1.0]``)이다. 축 목록 길이와 등록 축은
    본을 만들기 전에 검사한다. 소스 중 하나라도 스킨 본이면 원본이 생성 노드도 스킨 본으로 표시한다.

    Args:
        inNode: 볼륨 본을 붙일 관절 본(이름·handle·NodeRef)
        inParent: 관절 본의 부모(이름·handle·NodeRef). inNode와 달라야 한다
        inRotScale: 루트 본이 관절 회전을 따라가는 비율
        inVolumeSize: 볼륨 본이 밀려나는 크기
        inRotAxes: 회전 감지 축 목록(``"X"``·``"Y"``·``"Z"``). None이면 ``["Z"]``
        inTransAxes: 이동 축 목록(``"PosX"``~``"NegZ"``). None이면 ``["PosY"]``
        inTransScales: 이동 스케일 목록(숫자). None이면 ``[1.0]``. 세 목록의 길이가 같아야 한다

    Returns:
        readback dict. ``created``=새 노드(장면 handle 차이), ``details={"chain": 체인 dict}``
        (``bones``=루트 본+볼륨 본, ``helpers``=회전 헬퍼, ``parameters``는 원본 PARAM_SPEC 키)

    Raises:
        AgentApiError: INVALID_ARGUMENT(축 목록 길이 불일치·미등록 축·숫자 아님·같은 노드),
            NODE_NOT_FOUND, NODE_AMBIGUOUS, OPERATION_FAILED(원본 예외 — ``details["exception"]``,
            원본이 None 반환 — ``details["log"]="pyjallib_rig"``)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import rig; result = rig.create_volume_bones("Bip001 L Forearm", "Bip001 L UpperArm", inRotAxes=["Z"], inTransAxes=["PosY"], inTransScales=[1.0])
    """
    values = _volume_parameter_values(
        {
            "inRotScale": inRotScale,
            "inVolumeSize": inVolumeSize,
            "inRotAxises": inRotAxes,
            "inTransAxises": inTransAxes,
            "inTransScales": inTransScales,
        }
    )
    node, parent = _resolve_pair(inNode, inParent, "inParent")
    volumeService = _header().volumeBone
    return _create_chain(
        "VolumeBone",
        "볼륨 본 생성",
        lambda: volumeService.create_bones(node, parent, **values),
        {"sources": [ags.node_ref(node), ags.node_ref(parent)]},
    )


def rebuild_volume_bones(inChain: dict, inConfirm: bool = False) -> dict:
    """볼륨 체인의 본·헬퍼를 지우고 같은 소스 본·파라미터로 다시 만든다(원본 ``create_bones_from_chain``).

    **원본은 체인의 bones·helpers 노드(루트 본·볼륨 본·회전 헬퍼)를 삭제한 뒤 다시 만든다.** 그래서
    ``inConfirm=True``일 때만 진행하고, ``inConfirm=False``(기본)면 장면을 바꾸지 않고
    PRECONDITION_FAILED로 삭제 예정 노드(``details["toDelete"]``)를 알려 준다. 체인 dict는
    ``create_volume_bones``·``rebuild_volume_bones``가 돌려준 ``details["chain"]``을 그대로 넘긴다
    (``parameters`` 키는 원본 철자 ``inRotAxises``·``inTransAxises``). 체인 노드는 모두 장면에서
    해석돼야 한다. 파라미터 값(축 목록 길이·미등록 축 등)은 검사하지 않고 원본에 그대로 넘긴다.
    **경고: 원본은 옛 노드를 먼저 지우므로, 그 뒤 원본이 실패(None 반환·예외 — 예: 축 목록 길이
    불일치·미등록 축)하면 옛 체인 노드는 사라진 채 새 노드가 만들어지지 않는다**(OPERATION_FAILED의
    ``details["deleted"]``). bones가 빈 체인·소스 수가 맞지 않는 체인은 원본이 None을 돌려준다.

    Args:
        inChain: 체인 dict(``part="VolumeBone"``, bones·helpers·sourceBones NodeRef 목록, parameters)
        inConfirm: True여야 옛 체인 노드를 지우고 다시 만든다. False면 삭제 예정 노드만 알려 준다

    Returns:
        readback dict. ``created``=새 노드, ``deleted``=지운 옛 노드 이름, ``details={"chain": 새 체인 dict}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(체인 형식 — dict 아님·필수 키 누락·part가 VolumeBone이 아님·
            원본 PARAM_SPEC 밖 parameters 키, inConfirm이 bool이 아님),
            NODE_NOT_FOUND·NODE_AMBIGUOUS(체인 노드 해석 실패), PRECONDITION_FAILED(inConfirm=False —
            ``details["toDelete"]``), OPERATION_FAILED(원본 None 반환 — ``details["log"]="pyjallib_rig"``,
            원본 예외 — ``details["exception"]``. 둘 다 ``details["deleted"]``에 원본이 이미 지운 노드)

    Side effects: scene
    Undo: yes

    Example:
        from pyjallib.max.agentapi import rig; result = rig.rebuild_volume_bones(chain, inConfirm=True)
    """
    return _rebuild_chain(inChain, inConfirm, "VolumeBone", "volumeBone")
