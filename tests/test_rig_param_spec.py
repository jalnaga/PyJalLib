# -*- coding: utf-8 -*-
"""릭 파트의 `PARAM_SPEC` 규약 전수 단정 (Type A).

`pyjallib.max.rig`의 파트들은 파라미터의 정본을 `PARAM_SPEC` 표 하나로 갖는다.
그 표는 세 곳에서 동시에 쓰인다.

- `_RigPartBase.create_bones_from_chain()`이 dict에서 키워드 인자를 만들 때
- `build_result()`가 결과의 `Parameters`를 채울 때
- 툴(`PyJalMaxRiggingTool`)의 `partSpecs.py`가 UI 위젯 표를 만들 때

**표와 시그니처가 어긋나면 위 셋이 조용히 갈린다.** 전 구현이 정확히 그 상태였다 -
`VolumeBone`이 저장한 `Parameters` 레이아웃과 `Elbow`가 읽는 레이아웃이 달라서,
라이브러리를 직접 쓰는 재생성이 `Unable to convert: "NegY" to type: Float`로 죽었다
(2026-09-21 실측). 이 테스트가 그 어긋남을 **구조적으로** 막는다.

pymxs는 `tests/conftest.py`가 세션 전역에 mock으로 등록한다.
"""

import inspect

import pytest

from pyjallib.max import rig

#: 시험할 릭 파트 클래스 이름. `rig.__all__`에서 값 객체와 비공개 기반 클래스를 뺀다.
PART_CLASS_NAMES = tuple(
    name for name in rig.__all__ if not name.startswith("_") and name != "BoneChain"
)

#: PRD가 세는 릭 파트 수(14 클래스). 표가 줄거나 늘면 여기가 먼저 깨진다.
EXPECTED_PART_COUNT = 14


def _part_classes():
    """시험 대상 클래스를 (이름, 클래스) 쌍으로 돌려준다.

    Returns:
        list[tuple[str, type]]: 파트 이름과 클래스
    """
    return [(name, getattr(rig, name)) for name in PART_CLASS_NAMES]


def _create_bones_parameters(inClass):
    """`create_bones`의 파라미터를 `self`를 뺀 순서대로 돌려준다.

    Args:
        inClass: 릭 파트 클래스

    Returns:
        list[inspect.Parameter]: 파라미터 목록
    """
    signature = inspect.signature(inClass.create_bones)
    return [p for name, p in signature.parameters.items() if name != "self"]


def test_part_count_matches_prd():
    """릭 파트 클래스 수가 PRD의 14와 같은지 확인한다."""
    assert len(PART_CLASS_NAMES) == EXPECTED_PART_COUNT, (
        f"릭 파트 수가 다르다. 기대 {EXPECTED_PART_COUNT}, 실제 {len(PART_CLASS_NAMES)}: "
        f"{PART_CLASS_NAMES}"
    )


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_param_spec_is_declared(partName, partClass):
    """모든 파트가 비어 있지 않은 `PARAM_SPEC`과 `SOURCE_SPEC`을 선언하는지 확인한다."""
    assert partClass.PARAM_SPEC, f"{partName}: PARAM_SPEC이 비어 있다"
    assert partClass.SOURCE_SPEC, f"{partName}: SOURCE_SPEC이 비어 있다"


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_param_spec_names_are_unique(partName, partClass):
    """`PARAM_SPEC`에 같은 파라미터 이름이 두 번 나오지 않는지 확인한다."""
    names = [name for name, _ in partClass.PARAM_SPEC]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    assert not duplicated, f"{partName}: PARAM_SPEC에 중복된 이름이 있다: {duplicated}"


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_param_spec_names_use_in_prefix(partName, partClass):
    """파라미터 이름이 `in` 접두 규약(`rules/code-style.md`)을 따르는지 확인한다."""
    offenders = [
        name
        for name, _ in partClass.PARAM_SPEC
        if not (name.startswith("in") and len(name) > 2 and name[2].isupper())
    ]
    assert not offenders, f"{partName}: `in` 접두 규약을 벗어난 파라미터: {offenders}"


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_source_spec_matches_leading_parameters(partName, partClass):
    """`SOURCE_SPEC`이 `create_bones`의 **앞쪽 위치 인자**와 1:1·동순인지 확인한다.

    `create_bones_from_chain()`이 `sourceBones`를 이 순서로 풀어 넘기므로,
    어긋나면 소스 본이 뒤바뀐 채 릭이 만들어진다.
    """
    parameters = _create_bones_parameters(partClass)
    sourceCount = len(partClass.SOURCE_SPEC)
    actual = tuple(p.name for p in parameters[:sourceCount])
    assert actual == tuple(partClass.SOURCE_SPEC), (
        f"{partName}: SOURCE_SPEC {partClass.SOURCE_SPEC} != "
        f"create_bones의 앞쪽 인자 {actual}"
    )

    for parameter in parameters[:sourceCount]:
        assert parameter.default is inspect.Parameter.empty, (
            f"{partName}: 소스 본 파라미터 {parameter.name}에 기본값이 있다 - "
            "소스 본은 필수여야 한다"
        )


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_param_spec_matches_signature(partName, partClass):
    """`PARAM_SPEC`이 `create_bones`의 키워드 파라미터와 1:1·동순인지 확인한다."""
    parameters = _create_bones_parameters(partClass)
    keywordParams = parameters[len(partClass.SOURCE_SPEC):]

    specNames = tuple(name for name, _ in partClass.PARAM_SPEC)
    signatureNames = tuple(p.name for p in keywordParams)

    assert specNames == signatureNames, (
        f"{partName}: PARAM_SPEC {specNames} != create_bones 키워드 인자 {signatureNames}"
    )


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_param_spec_defaults_match_signature(partName, partClass):
    """`PARAM_SPEC`의 기본값이 `create_bones`의 기본값과 같은지 확인한다.

    **가변 기본값은 예외다.** 리스트·dict를 시그니처 기본값으로 두면 호출 사이에
    공유돼 오염되므로(파이썬의 고전적 함정), 그런 파라미터는 시그니처에 `None`을 두고
    함수 안에서 표의 값으로 대체한다. 이 경우만 `None`을 허용하고, 스칼라 기본값에는
    그대로 일치를 요구한다.
    """
    parameters = _create_bones_parameters(partClass)
    keywordParams = {p.name: p for p in parameters[len(partClass.SOURCE_SPEC):]}

    mismatched = []
    for name, default in partClass.PARAM_SPEC:
        parameter = keywordParams.get(name)
        if parameter is None:
            mismatched.append(f"{name}: 시그니처에 없음")
            continue
        if isinstance(default, (list, dict)) and parameter.default is None:
            continue
        if parameter.default != default:
            mismatched.append(f"{name}: 표 {default!r} vs 시그니처 {parameter.default!r}")

    assert not mismatched, f"{partName}: 기본값 불일치 - {mismatched}"


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_mutable_defaults_are_none_in_signature(partName, partClass):
    """가변 기본값은 시그니처에서 반드시 `None`이어야 한다.

    위 테스트가 허용하는 예외를 **반대 방향으로** 못박는다. 리스트를 시그니처
    기본값으로 직접 두면 호출 사이에 공유된다.
    """
    parameters = _create_bones_parameters(partClass)
    keywordParams = {p.name: p for p in parameters[len(partClass.SOURCE_SPEC):]}

    offenders = [
        name
        for name, parameter in keywordParams.items()
        if isinstance(parameter.default, (list, dict, set))
    ]
    assert not offenders, (
        f"{partName}: 가변 객체가 시그니처 기본값으로 쓰였다: {offenders}. "
        "None을 기본값으로 두고 함수 안에서 PARAM_SPEC의 값으로 대체한다."
    )


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_default_parameters_copies_mutable_defaults(partName, partClass):
    """`default_parameters()`가 리스트 기본값을 복제해 돌려주는지 확인한다.

    표를 그대로 돌려주면 호출부의 수정이 클래스 전역 기본값을 오염시킨다.
    """
    first = partClass.default_parameters()
    second = partClass.default_parameters()
    for name, value in first.items():
        if isinstance(value, (list, dict)):
            assert value is not second[name], (
                f"{partName}: {name}의 기본값이 복제되지 않고 공유된다"
            )


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_resolve_parameters_fills_defaults_and_drops_unknown(partName, partClass):
    """`resolve_parameters()`가 빠진 값을 채우고 모르는 키를 버리는지 확인한다."""
    resolved = partClass.resolve_parameters({"완전히모르는키": 1})
    assert set(resolved) == set(partClass.param_names()), (
        f"{partName}: resolve_parameters의 키 집합이 PARAM_SPEC과 다르다"
    )
    assert "완전히모르는키" not in resolved, f"{partName}: 모르는 키가 남았다"


@pytest.mark.parametrize("partName, partClass", _part_classes())
def test_work_defaults_cover_reset(partName, partClass):
    """`WORK_DEFAULTS`가 비어 있지 않은지 확인한다.

    비어 있으면 `reset()`이 아무것도 되돌리지 않아 앞 실행의 작업 데이터가 남는다.
    """
    assert partClass.WORK_DEFAULTS, f"{partName}: WORK_DEFAULTS가 비어 있다"
