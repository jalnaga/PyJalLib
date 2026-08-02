# -*- coding: utf-8 -*-
"""pyjallib 소스에 특정 프로젝트(ORV) 레이어 문자열이 없음을 단정하는 Type A 가드.

pyjallib은 오픈소스 범용 라이브러리다. 어떤 프로젝트에서 쓰든 특정 리그 규약의
레이어 이름을 전제해서는 안 된다. 이 가드가 이관 작업의 목적을 직접 검증한다 -
"규칙 엔진으로 옮겼다"는 말이 아니라 문자열이 실제로 0건인지를 본다.

함께 단정하는 것이 하나 더 있다. 삭제된 Deep 메서드 3종이 되살아나지 않았는지다.
그 메서드들은 호출부가 0건이라 검증 수단이 없는데도 특정 프로젝트의 레이어
와일드카드를 들고 있었다. 다시 들어오면 여기서 걸린다.
"""

import re
from pathlib import Path

import pytest

# 검사 대상 소스 루트. tests/ 는 검사하지 않는다 - 테스트는 규약 씬을 합성하기
# 위해 프로젝트풍 레이어 이름을 쓸 수 있고, 그것이 라이브러리 오염은 아니다.
_SRC_ROOT = Path(__file__).parent.parent / "src" / "pyjallib"

# 라이브러리에 있어서는 안 되는 프로젝트 레이어 문자열과 검사 시 대소문자 구분 여부.
#
# ``Skinbone``만 대소문자를 구분한다. 무시하면 일반 용어인 ``skinBone`` /
# ``SkinBone`` 변수(스킨 본을 다루는 코드 전반에 쓰인다)가 전부 걸려 가드가
# 무의미해진다. 반면 ORV 레이어 규약은 ``Skinbone``(대문자 S + 소문자 b)로 쓰므로
# 대소문자 구분이 정확한 판별자가 된다. 나머지 셋은 형태가 고유해 무시해도 안전하다.
_FORBIDDEN_LAYER_LITERALS = (
    ("Rig_AddOn", re.IGNORECASE),
    ("Bip_AddOn", re.IGNORECASE),
    ("*AddOn*", re.IGNORECASE),
    ("Skinbone", 0),
)

# 예외는 두지 않는다. 라이브러리 전체가 검사 대상이다.
#
# 이 목록이 한때 `max/skeleton.py`를 담고 있었다. PRD가 식별하지 못한 4번째 지점으로,
# `Skeleton.get_all_dependencies(inObjs, inAddonLayerName="Rig_AddOn")`의 기본 인자값에
# ORV 레이어 접두가 박혀 있었다. 마스터 판정(2026-07-31)에 따라 기본값을 None으로 바꿔
# 애드온 병합 대상을 호출부가 지정하도록 했고, 예외가 필요 없어졌다.
_PENDING_EXCEPTION_PATHS = frozenset()

# 삭제된 공개 메서드. 이름이 다시 정의되면 실패한다.
_DELETED_METHOD_NAMES = (
    "get_all_related",
    "get_deep_dependencies",
    "get_deep_dependents",
)


def _iter_source_files():
    """검사 대상 파이썬 소스 파일을 순회한다.

    Yields:
        Path: ``src/pyjallib`` 아래의 ``.py`` 파일 경로
    """
    for sourcePath in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in sourcePath.parts:
            continue
        if sourcePath.relative_to(_SRC_ROOT).as_posix() in _PENDING_EXCEPTION_PATHS:
            continue
        yield sourcePath


@pytest.mark.parametrize(
    "forbiddenLiteral,patternFlags",
    _FORBIDDEN_LAYER_LITERALS,
    ids=[literal for literal, _ in _FORBIDDEN_LAYER_LITERALS],
)
def test_no_project_layer_literal_in_library(forbiddenLiteral, patternFlags):
    """pyjallib 소스에 프로젝트 레이어 문자열이 없어야 한다."""
    literalPattern = re.compile(re.escape(forbiddenLiteral), patternFlags)
    offendingLocations = []

    for sourcePath in _iter_source_files():
        sourceText = sourcePath.read_text(encoding="utf-8")
        for lineNumber, lineText in enumerate(sourceText.splitlines(), start=1):
            if literalPattern.search(lineText):
                relativePath = sourcePath.relative_to(_SRC_ROOT.parent.parent)
                offendingLocations.append(
                    f"{relativePath}:{lineNumber}: {lineText.strip()}"
                )

    assert not offendingLocations, (
        f"프로젝트 레이어 문자열 '{forbiddenLiteral}'이 라이브러리에 남아 있습니다. "
        f"수집 대상은 호출부가 정서로 기술해야 합니다.\n"
        + "\n".join(offendingLocations)
    )


@pytest.mark.parametrize("deletedMethodName", _DELETED_METHOD_NAMES)
def test_deleted_deep_method_is_not_redefined(deletedMethodName):
    """삭제된 Deep 메서드가 다시 정의되지 않아야 한다.

    ``get_all_related_to_export``는 남아 있는 메서드이므로, 단어 경계를 두어
    접두가 같은 이름에 걸리지 않게 한다.
    """
    definitionPattern = re.compile(rf"def\s+{re.escape(deletedMethodName)}\s*\(")
    offendingLocations = []

    for sourcePath in _iter_source_files():
        sourceText = sourcePath.read_text(encoding="utf-8")
        for lineNumber, lineText in enumerate(sourceText.splitlines(), start=1):
            if definitionPattern.search(lineText):
                relativePath = sourcePath.relative_to(_SRC_ROOT.parent.parent)
                offendingLocations.append(f"{relativePath}:{lineNumber}")

    assert not offendingLocations, (
        f"삭제된 메서드 '{deletedMethodName}'이 다시 정의되었습니다. "
        f"포괄적 의존성 탐색이 다시 필요하면 정서 기반으로 새로 설계합니다.\n"
        + "\n".join(offendingLocations)
    )


def test_dependent_class_has_no_deleted_methods():
    """``Dependent`` 클래스에 삭제된 메서드 3종이 없어야 한다.

    소스 텍스트 검사와 별개로 실제 클래스 속성을 본다. 다른 모듈에서 몽키패치로
    붙는 경로까지 막는다.
    """
    from pyjallib.max.dependent import Dependent

    stillPresent = [
        methodName
        for methodName in _DELETED_METHOD_NAMES
        if hasattr(Dependent, methodName)
    ]

    assert not stillPresent, f"Dependent에 삭제 대상 메서드가 남아 있습니다: {stillPresent}"


def test_dependent_keeps_public_surface():
    """삭제 대상이 아닌 공개 메서드는 그대로 있어야 한다.

    삭제 범위가 넘치지 않았음을 반대 방향에서 단정한다.
    """
    from pyjallib.max.dependent import Dependent

    expectedMethodNames = (
        "get_all_dependencies",
        "get_dependents",
        "collect_addon_helpers",
        "get_all_related_to_export",
    )
    missingMethods = [
        methodName
        for methodName in expectedMethodNames
        if not hasattr(Dependent, methodName)
    ]

    assert not missingMethods, f"공개 메서드가 사라졌습니다: {missingMethods}"


def test_select_keeps_public_surface():
    """``Select``의 dependency 관련 공개 메서드가 유지되어야 한다."""
    from pyjallib.max.select import Select

    expectedMethodNames = (
        "get_all_dependencies_optimized",
        "get_dependents",
        "collect_addon_helpers",
        "select_dependencies",
    )
    missingMethods = [
        methodName
        for methodName in expectedMethodNames
        if not hasattr(Select, methodName)
    ]

    assert not missingMethods, f"공개 메서드가 사라졌습니다: {missingMethods}"


def test_header_exposes_policy_configuration():
    """``Header``에 정서 배선 메서드가 있어야 한다."""
    from pyjallib.max.header import Header

    assert hasattr(Header, "configure_node_collect_policy")
