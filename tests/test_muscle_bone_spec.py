# -*- coding: utf-8 -*-
"""근육 본 파트(`MuscleBone`·`MuscleBoneChain`)의 공개 계약 단정 (Type A).

근육 본 파트(2026-11-10 추가)의 공개 API를 콘솔에서 고정한다. Max 동작은
`tests/max/test_muscle_bone.py`(Type C)와 `tests/run_muscle_bone_roundtrip.py`(UE5 왕복)가 본다.

고정하는 것:

- 모듈 `pyjallib.max.rig.muscleBone`에 두 클래스가 있고 `_RigPartBase`를 상속한다.
- `SOURCE_SPEC`·`PARAM_SPEC`이 **정확히** 아래 표와 같다(이름·순서·기본값).
- `create_bones` 시그니처가 표와 1:1·동순이다(소스 인자는 기본값 없음).
- `rig` 패키지가 두 클래스를 re-export한다(같은 객체).
- `header.py`가 `self.muscleBone`·`self.muscleBoneChain`을 다른 파트와 같은 공통 서비스
  다섯(name, anim, helper, bone, constraint) 순서로 만든다(AST 대조 - Header 싱글톤은
  콘솔에서 만들지 않는다).
- 서비스 필수 주입(`None`이면 `ValueError`)이 상속으로 유지된다.

**import는 각 테스트 안에서 한다.** 구현 전에는 모듈이 없어 수집 단계에서 파일 전체가
죽으면 다른 단정의 판정까지 잃는다.

pymxs는 `tests/conftest.py`가 세션 전역에 mock으로 등록한다.
"""

import ast
import importlib
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_HEADER_PATH = Path(__file__).parent.parent / "src" / "pyjallib" / "max" / "header.py"

#: 정본 표. 사양의 리터럴을 그대로 옮긴다. 구현 상수를 빌리지 않는다.
EXPECTED_SPECS = {
    "MuscleBone": {
        "SOURCE_SPEC": ("inStartObj", "inEndObj"),
        "PARAM_SPEC": (
            ("inName", ""),
            ("inBoneSize", 2.0),
            ("inSquashExponent", 1.0),
        ),
    },
    "MuscleBoneChain": {
        "SOURCE_SPEC": ("inSpline",),
        "PARAM_SPEC": (
            ("inName", ""),
            ("inLinkNum", 2),
            ("inBoneSize", 2.0),
            ("inSquashExponent", 1.0),
        ),
    },
}

#: Header 속성 이름 -> 클래스 이름.
EXPECTED_HEADER_ATTRS = {
    "muscleBone": "MuscleBone",
    "muscleBoneChain": "MuscleBoneChain",
}

#: 다른 파트와 같은 공통 서비스 주입 순서(`header.py`의 릭 파트 배선 주석).
EXPECTED_SERVICE_ARGS = ["name", "anim", "helper", "bone", "constraint"]


def _load_module():
    """구현 모듈을 import한다. 없으면 그 테스트만 실패한다."""
    return importlib.import_module("pyjallib.max.rig.muscleBone")


def _load_class(inClassName: str):
    """구현 모듈에서 클래스를 꺼낸다."""
    return getattr(_load_module(), inClassName)


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_class_exists_and_inherits_rig_part_base(className):
    """모듈에 클래스가 있고 `_RigPartBase`를 상속하는지 확인한다."""
    from pyjallib.max.rig.rigPart import _RigPartBase

    cls = _load_class(className)
    assert inspect.isclass(cls), f"{className}이 클래스가 아니다: {cls!r}"
    assert issubclass(cls, _RigPartBase), f"{className}이 _RigPartBase를 상속하지 않는다"


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_source_spec_exact(className):
    """`SOURCE_SPEC`이 정본 표와 정확히 같은지 확인한다."""
    cls = _load_class(className)
    expected = EXPECTED_SPECS[className]["SOURCE_SPEC"]
    assert tuple(cls.SOURCE_SPEC) == expected, (
        f"{className}.SOURCE_SPEC {cls.SOURCE_SPEC!r} != 기대 {expected!r}"
    )


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_param_spec_exact(className):
    """`PARAM_SPEC`이 정본 표와 이름·순서·기본값까지 같은지 확인한다."""
    cls = _load_class(className)
    expected = EXPECTED_SPECS[className]["PARAM_SPEC"]
    actual = tuple((name, default) for name, default in cls.PARAM_SPEC)
    assert actual == expected, f"{className}.PARAM_SPEC {actual!r} != 기대 {expected!r}"
    # 0 == False 류의 동치로 통과하지 않도록 타입까지 본다(inLinkNum은 정수, 나머지 크기는 실수).
    actualTypes = tuple(type(default) for _, default in cls.PARAM_SPEC)
    expectedTypes = tuple(type(default) for _, default in expected)
    assert actualTypes == expectedTypes, (
        f"{className}.PARAM_SPEC 기본값 타입 {actualTypes} != 기대 {expectedTypes}"
    )


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_create_bones_signature_exact(className):
    """`create_bones` 시그니처가 SOURCE_SPEC + PARAM_SPEC과 1:1·동순인지 확인한다."""
    cls = _load_class(className)
    spec = EXPECTED_SPECS[className]
    signature = inspect.signature(cls.create_bones)
    params = [p for name, p in signature.parameters.items() if name != "self"]

    expectedNames = list(spec["SOURCE_SPEC"]) + [name for name, _ in spec["PARAM_SPEC"]]
    assert [p.name for p in params] == expectedNames, (
        f"{className}.create_bones 인자 {[p.name for p in params]} != 기대 {expectedNames}"
    )

    sourceCount = len(spec["SOURCE_SPEC"])
    for param in params[:sourceCount]:
        assert param.default is inspect.Parameter.empty, (
            f"{className}: 소스 인자 {param.name}에 기본값이 있다"
        )
    for param, (name, default) in zip(params[sourceCount:], spec["PARAM_SPEC"]):
        assert param.default == default and type(param.default) is type(default), (
            f"{className}: {name} 기본값 {param.default!r} != 기대 {default!r}"
        )
        assert param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ), f"{className}: {name}을 키워드로 넘길 수 없다(create_bones_from_chain이 이름으로 넘긴다)"


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_create_bones_is_overridden(className):
    """`create_bones`를 기반 클래스의 미구현 본문 그대로 두지 않았는지 확인한다."""
    from pyjallib.max.rig.rigPart import _RigPartBase

    cls = _load_class(className)
    assert cls.create_bones is not _RigPartBase.create_bones, (
        f"{className}.create_bones가 _RigPartBase의 NotImplementedError 본문이다"
    )


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_rig_package_reexports_same_class(className):
    """`pyjallib.max.rig`가 같은 클래스 객체를 re-export하고 `__all__`에 올리는지 확인한다."""
    from pyjallib.max import rig

    cls = _load_class(className)
    assert className in rig.__all__, f"rig.__all__에 {className}이 없다"
    assert getattr(rig, className, None) is cls, (
        f"rig.{className}이 muscleBone 모듈의 클래스와 다른 객체다"
    )


@pytest.mark.parametrize("className", sorted(EXPECTED_SPECS))
def test_services_are_required(className):
    """서비스 다섯을 받으면 생성되고, 하나라도 None이면 `ValueError`인지 확인한다."""
    cls = _load_class(className)
    services = [MagicMock(name=f"svc{i}") for i in range(5)]
    part = cls(*services)
    assert part.name is services[0] and part.const is services[4]

    for index in range(5):
        broken = list(services)
        broken[index] = None
        with pytest.raises(ValueError):
            cls(*broken)


def _header_assignments():
    """`header.py`의 `self.<속성> = <클래스>(...)`를 AST로 읽는다.

    Returns:
        dict[str, ast.Call]: 속성 이름 -> 생성 호출
    """
    tree = ast.parse(_HEADER_PATH.read_text(encoding="utf-8"))
    calls = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                calls[target.attr] = node.value
    return calls


def _header_imports():
    """`header.py`의 `from .<모듈> import <이름>`을 AST로 읽는다.

    Returns:
        dict[str, str]: 이름 -> 모듈(점 표기, `max` 기준 상대)
    """
    tree = ast.parse(_HEADER_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                mapping[alias.asname or alias.name] = node.module
    return mapping


def test_header_reads_existing_parts():
    """AST 대조가 공허하지 않은지 - 기존 파트 배선이 실제로 읽히는지 먼저 확인한다."""
    calls = _header_assignments()
    assert "twistBone" in calls and "groinBone" in calls, (
        f"header.py 배선을 읽지 못했다: {sorted(calls)}"
    )
    imports = _header_imports()
    assert imports.get("TwistBone") == "rig.twistBone", f"import 대조 실패: {imports}"


@pytest.mark.parametrize("attrName", sorted(EXPECTED_HEADER_ATTRS))
def test_header_wires_muscle_parts(attrName):
    """`Header`가 근육 본 파트를 공통 서비스 다섯으로 만들어 `jal.<속성>`에 두는지 확인한다."""
    className = EXPECTED_HEADER_ATTRS[attrName]
    calls = _header_assignments()
    call = calls.get(attrName)
    assert call is not None, f"header.py에 self.{attrName} 배선이 없다"
    assert isinstance(call.func, ast.Name) and call.func.id == className, (
        f"self.{attrName}이 {className}(...)로 만들어지지 않는다: {ast.dump(call.func)}"
    )
    args = [
        arg.attr
        if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name) and arg.value.id == "self"
        else ast.dump(arg)
        for arg in call.args
    ]
    assert args == EXPECTED_SERVICE_ARGS and not call.keywords, (
        f"self.{attrName}의 서비스 주입 {args} (키워드 {[k.arg for k in call.keywords]}) != "
        f"기대 {EXPECTED_SERVICE_ARGS}"
    )

    imports = _header_imports()
    assert imports.get(className) == "rig.muscleBone", (
        f"header.py가 {className}을 rig.muscleBone에서 import하지 않는다: {imports.get(className)}"
    )


# ---------------------------------------------------------------------------
# 이름 규칙(사용자 예)과 naming 설정의 Type "Ctrl"
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).parent.parent / "src" / "pyjallib" / "max" / "ConfigFiles"
#: Type "Ctrl"을 더한 두 설정 파일
_CONFIG_FILES = ("3DSMaxNamingConfig.json", "Default_3DSMaxNamingConfig.json")
#: 변경 전 Type 값과 설명 - "기존 값·순서는 유지"의 기준
_ORIGINAL_TYPE_VALUES = ["Dum", "P", "Exp", "IK", "T", "Rot", "Pos", "Lat", "UpN"]
_ORIGINAL_TYPE_DESCRIPTIONS = [
    "Dummy", "Parent", "ExposeTM", "IK", "Target", "Rotation", "Position", "LookAt", "UpNode",
]

#: 사용자 예(소스 "Bip001 L Upper Arm")의 리터럴 -> 기대 파트 분해
USER_EXAMPLE_NAMES = {
    "Bip001 L Upper ArmMuscle 00": {"Base": "Bip001", "Type": "", "Side": "L", "RealName": "Upper ArmMuscle", "Index": "00"},
    "Bip001 L Upper ArmMuscle 01": {"Base": "Bip001", "Type": "", "Side": "L", "RealName": "Upper ArmMuscle", "Index": "01"},
    "Bip001 L Upper ArmMuscleNub 00": {"Base": "Bip001", "Type": "", "Side": "L", "RealName": "Upper ArmMuscleNub", "Index": "00"},
    "Bip001 Dum L Upper ArmMuscle 01": {"Base": "Bip001", "Type": "Dum", "Side": "L", "RealName": "Upper ArmMuscle", "Index": "01"},
    "Bip001 Dum L Upper ArmMuscleRoot 00": {"Base": "Bip001", "Type": "Dum", "Side": "L", "RealName": "Upper ArmMuscleRoot", "Index": "00"},
    "Bip001 Ctrl L Upper ArmMuscle 02": {"Base": "Bip001", "Type": "Ctrl", "Side": "L", "RealName": "Upper ArmMuscle", "Index": "02"},
}


def _type_part(inFileName: str) -> dict:
    import json

    data = json.loads((_CONFIG_DIR / inFileName).read_text(encoding="utf-8"))
    parts = [p for p in data["nameParts"] if p["name"] == "Type"]
    assert len(parts) == 1, f"{inFileName}: Type 파트가 하나가 아니다"
    return parts[0]


@pytest.mark.parametrize("fileName", _CONFIG_FILES)
def test_config_type_has_ctrl_control(fileName):
    """Type 파트에 값 "Ctrl"·설명 "Control"이 같은 위치로 있고, 병렬 배열 길이가 맞는다."""
    part = _type_part(fileName)
    values, descriptions = part["predefinedValues"], part["descriptions"]
    assert "Ctrl" in values, f"{fileName}: Type 값에 Ctrl이 없다: {values}"
    index = values.index("Ctrl")
    assert descriptions[index] == "Control", f"{fileName}: Ctrl의 설명이 Control이 아니다: {descriptions}"
    lengths = {key: len(part[key]) for key in ("predefinedValues", "descriptions", "koreanDescriptions", "weights")
               if key in part}
    assert len(set(lengths.values())) == 1, f"{fileName}: Type 병렬 배열 길이가 다르다: {lengths}"


@pytest.mark.parametrize("fileName", _CONFIG_FILES)
def test_config_type_keeps_existing_values_and_order(fileName):
    """기존 Type 값·설명이 모두 남고 서로의 순서가 유지된다(Ctrl 추가만 허용)."""
    part = _type_part(fileName)
    pairs = list(zip(part["predefinedValues"], part["descriptions"]))
    kept = [pair for pair in pairs if pair[0] != "Ctrl"]
    assert kept == list(zip(_ORIGINAL_TYPE_VALUES, _ORIGINAL_TYPE_DESCRIPTIONS)), (
        f"{fileName}: 기존 Type 값·순서가 바뀌었다: {pairs}"
    )


@pytest.mark.parametrize("fileName", _CONFIG_FILES)
def test_user_example_names_decompose_by_rule(fileName):
    """사용자 예 리터럴을 Name 서비스(그 설정)가 Base·Type·Side·RealName·Index로 규칙대로 분해한다.

    Type "Ctrl"이 설정에 없으면 Ctrl 이름이 Type ""로 읽혀 실패한다(판별력).
    """
    from pyjallib.max.name import Name

    name = Name(configPath=str(_CONFIG_DIR / fileName))
    actual = {
        literal: {part: name.get_name(part, literal) for part in ("Base", "Type", "Side", "RealName", "Index")}
        for literal in USER_EXAMPLE_NAMES
    }
    assert actual == USER_EXAMPLE_NAMES


def test_user_example_source_realname():
    """전제: 소스 "Bip001 L Upper Arm"의 RealName이 "Upper Arm"(공백 포함)으로 분해된다."""
    from pyjallib.max.name import Name

    name = Name(configPath=str(_CONFIG_DIR / _CONFIG_FILES[0]))
    assert name.get_name("RealName", "Bip001 L Upper Arm") == "Upper Arm"
    assert name.get_name("Side", "Bip001 L Upper Arm") == "L"
    assert name.get_name("Base", "Bip001 L Upper Arm") == "Bip001"
