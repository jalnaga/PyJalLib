# -*- coding: utf-8 -*-
"""이름 에이전트 인터페이스 — 에이전트가 pyjallib 이름 규칙으로 이름을 분해·조합하고 이름 설정을 조회한다.

함수 목록:
    parse_name — 이름을 namePart별 값 dict로 분해한다 [none]
    combine_name — namePart 값 dict를 설정 순서대로 조합해 이름을 만든다 [none]
    get_name_index — 이름의 Index 파트를 정수로 읽는다 [none]
    get_naming_config_path — 로드된 이름 설정 파일 경로와 존재 여부를 읽는다 [none]
    get_name_separator — 이름에 쓰인 구분자(공백·밑줄·없음)를 읽는다 [none]
    get_name_parts — 이름 설정의 namePart 정의 목록을 순서와 함께 읽는다 [none]

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    이름 규칙은 Header의 이름 서비스(``3DSMaxNamingConfig.json`` 또는 ``update_name_config``로
    바꾼 설정)를 쓴다. 장면은 건드리지 않는다.
    이 모듈은 import할 때 pymxs·header를 불러오지 않는다.

호출 예:
    from pyjallib.max.agentapi import name; result = name.parse_name("Bip001 L UpperArm")
"""

import os

from pyjallib.max import agentSupport as ags

#: combine_name이 받는 구분자(원본 구분자 판별 규칙과 같은 집합)
_SEPARATORS = (" ", "_", "")


# ---------------------------------------------------------------------------
# 내부 보조
# ---------------------------------------------------------------------------


def _name_service():
    """Header의 이름 서비스를 함수 안에서 지연 획득한다."""
    from pyjallib.max.header import get_pyjallibmaxheader

    return get_pyjallibmaxheader().name


def _original_error(inError: Exception, inAction: str, inDetails: dict | None = None) -> ags.AgentApiError:
    """원본 메서드 예외를 AgentApiError로 바꾼다."""
    code = ags.INVALID_ARGUMENT if isinstance(inError, ValueError) else ags.OPERATION_FAILED
    details = dict(inDetails or {})
    details["exception"] = repr(inError)
    return ags.AgentApiError(code, f"{inAction} 중 원본 처리가 실패했다: {inError}", details)


def _require_str(inValue, inArgName: str, inAllowEmpty: bool = True) -> None:
    """문자열 인자인지 확인한다.

    Raises:
        AgentApiError: INVALID_ARGUMENT
    """
    if not isinstance(inValue, str):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"{inArgName}는 문자열이어야 한다: {type(inValue).__name__}",
            {"argument": inArgName, "type": type(inValue).__name__},
        )
    if not inAllowEmpty and inValue == "":
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, f"{inArgName}는 빈 문자열일 수 없다", {"argument": inArgName}
        )


# ---------------------------------------------------------------------------
# 에이전트 함수
# ---------------------------------------------------------------------------


def parse_name(inName: str) -> dict:
    """이름을 namePart별 값으로 분해한다.

    Args:
        inName: 분해할 이름(비어 있지 않은 문자열)

    Returns:
        ``{"name": str, "parts": {namePart 이름: 값}}``. 값이 없는 파트는 빈 문자열이다.

    Raises:
        AgentApiError: INVALID_ARGUMENT(문자열이 아니거나 빈 문자열)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import name; result = name.parse_name("Bip001 L UpperArm")
    """
    _require_str(inName, "inName", inAllowEmpty=False)
    service = _name_service()
    try:
        parts = service.convert_to_dictionary(inName)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "이름 분해", {"name": inName}) from error
    return {"name": inName, "parts": {str(key): ("" if value is None else str(value)) for key, value in parts.items()}}


def combine_name(inParts: dict, inSeparator: str = " ") -> dict:
    """namePart 값 dict를 이름 설정의 파트 순서대로 조합한다.

    원본은 설정에 없는 키를 조용히 무시하므로, 무시된 키를 ``unknownParts``로 알려 준다.
    ``Index`` 키가 있으면 원본 규칙대로 인덱스 자릿수를 채운다.

    Args:
        inParts: ``{namePart 이름: 값(str)}``
        inSeparator: 파트 사이 구분자. " " | "_" | ""

    Returns:
        ``{"name": str, "unknownParts": [설정에 없어 무시된 키]}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(inParts가 dict가 아님, 키·값이 문자열이 아님,
            허용 밖 구분자)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import name; result = name.combine_name({"Base": "Bip001", "Side": "L", "RealName": "UpperArm"})
    """
    if not isinstance(inParts, dict):
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            f"inParts는 dict여야 한다: {type(inParts).__name__}",
            {"argument": "inParts", "type": type(inParts).__name__},
        )
    badItems = [
        {"key": repr(key), "valueType": type(value).__name__}
        for key, value in inParts.items()
        if not isinstance(key, str) or not isinstance(value, str)
    ]
    if badItems:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT, "inParts의 키와 값은 모두 문자열이어야 한다", {"argument": "inParts", "invalid": badItems}
        )
    if not isinstance(inSeparator, str) or inSeparator not in _SEPARATORS:
        raise ags.AgentApiError(
            ags.INVALID_ARGUMENT,
            "inSeparator는 공백(' ')·밑줄('_')·빈 문자열('') 중 하나여야 한다",
            {"argument": "inSeparator", "input": repr(inSeparator), "valid": list(_SEPARATORS)},
        )

    service = _name_service()
    try:
        knownParts = [part.get_name() for part in service.get_name_parts()]
        combined = service.combine(dict(inParts), inSeparator)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "이름 조합", {"parts": dict(inParts)}) from error
    unknownParts = [key for key in inParts if key not in knownParts]
    return {"name": str(combined), "unknownParts": unknownParts}


def get_name_index(inName: str) -> dict:
    """이름의 Index 파트를 정수로 읽는다.

    원본은 인덱스가 없으면 ``False``를 돌려줘 인덱스 0과 구분이 흐리다. 이 함수는
    ``hasIndex``로 둘을 가른다.

    Args:
        inName: 대상 이름

    Returns:
        ``{"name": str, "hasIndex": bool, "index": int | None}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(문자열이 아님)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import name; result = name.get_name_index("Bip001 Finger03")
    """
    _require_str(inName, "inName")
    service = _name_service()
    try:
        value = service.get_index_as_digit(inName)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "이름 인덱스 읽기", {"name": inName}) from error
    if value is False or value is None or isinstance(value, bool):
        return {"name": inName, "hasIndex": False, "index": None}
    return {"name": inName, "hasIndex": True, "index": int(value)}


def get_naming_config_path() -> dict:
    """현재 이름 서비스가 로드한 설정 파일 경로와 존재 여부를 읽는다.

    Returns:
        ``{"path": str, "exists": bool}``. 로드된 경로가 없으면 path는 빈 문자열이고 exists는 False다.

    Raises:
        AgentApiError: OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import name; result = name.get_naming_config_path()
    """
    service = _name_service()
    try:
        path = service.get_config_path()
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "이름 설정 경로 읽기") from error
    path = "" if path is None else str(path)
    return {"path": path, "exists": bool(path) and os.path.isfile(path)}


def get_name_separator(inName: str) -> dict:
    """이름에 쓰인 구분자를 읽는다(공백이 있으면 공백, 아니면 밑줄, 둘 다 없으면 빈 문자열).

    Args:
        inName: 대상 이름

    Returns:
        ``{"name": str, "separator": " " | "_" | ""}``

    Raises:
        AgentApiError: INVALID_ARGUMENT(문자열이 아님)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import name; result = name.get_name_separator("b_L_UpperArm")
    """
    _require_str(inName, "inName")
    service = _name_service()
    try:
        separator = service.get_filtering_char(inName)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "구분자 읽기", {"name": inName}) from error
    return {"name": inName, "separator": str(separator)}


def get_name_parts() -> dict:
    """이름 설정의 namePart 정의 목록을 설정 순서와 함께 읽는다.

    원본이 돌려주는 내부 객체 대신 사본 dict를 돌려주므로 결과를 바꿔도 설정이 바뀌지 않는다.

    Returns:
        ``{"parts": [{"order": int(0부터), "name", "predefinedValues", "weights", "type",
        "descriptions", "koreanDescriptions", "isDirection"}]}``

    Raises:
        AgentApiError: OPERATION_FAILED(원본 예외)

    Side effects: none
    Undo: n/a

    Example:
        from pyjallib.max.agentapi import name; result = name.get_name_parts()
    """
    service = _name_service()
    try:
        parts = []
        for order, part in enumerate(service.get_name_parts()):
            item = {"order": order}
            item.update(part.to_dict())
            parts.append(item)
    except Exception as error:  # noqa: BLE001
        raise _original_error(error, "namePart 목록 읽기") from error
    return {"parts": ags.to_json(parts)}
