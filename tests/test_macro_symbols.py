# -*- coding: utf-8 -*-
"""매크로가 쓰는 `jal.*` 심볼의 정적 대조와 릭 패키지 위생 가드 (Type A).

## 왜 매크로를 지키는가

`pyjallib/max/macro/` 5개는 워크스페이스의 어느 프로젝트 `src/`에서도 import되지 않아
**정적 스캔으로는 소비처가 0으로 보인다.** 그러나 startupscript의 MaxScript가 이 경로의
파이썬 매크로를 직접 부른다(마스터 확인, 2026-09-21) - **프로덕션 소비처다.**

import 그래프에 나타나지 않으므로 심볼이 사라져도 아무 테스트도 깨지지 않고, 리거가
3ds Max에서 매크로를 누를 때 처음 드러난다. 그래서 **AST로 정적 대조**한다.

릭 계열 재구성이 매크로에 닿지 않는다는 것이 PRD Q5의 실측 전제였다. 이 테스트가 그
전제를 상시 가드로 바꾼다.

## 위생 가드

재구성한 `rig/` 안에서만 검사한다. 코어 모듈의 `print()`·bare `except:`는 별도 사이클이다
(PRD S3).

pymxs는 `tests/conftest.py`가 세션 전역에 mock으로 등록한다.
"""

import ast
import re
from pathlib import Path

import pytest

_SRC = Path(__file__).parent.parent / "src" / "pyjallib" / "max"
_MACRO_DIR = _SRC / "macro"
_RIG_DIR = _SRC / "rig"
_HEADER_PATH = _SRC / "header.py"

#: `jal.<속성>.<메서드>` 꼴 호출을 뽑는 패턴.
_JAL_CALL = re.compile(r"\bjal\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)")


def _macro_files():
    """매크로 파일 목록을 돌려준다.

    Returns:
        list[Path]: `macro/` 아래 `.py` 파일
    """
    return sorted(p for p in _MACRO_DIR.glob("*.py") if p.name != "__init__.py")


def _collect_jal_usages():
    """매크로가 쓰는 `(속성, 메서드)` 쌍을 전부 모은다.

    Returns:
        dict[tuple[str, str], list[str]]: (속성, 메서드) -> 쓰는 파일 이름들
    """
    usages = {}
    for path in _macro_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for attrName, methodName in _JAL_CALL.findall(text):
            usages.setdefault((attrName, methodName), []).append(path.name)
    return usages


def _header_attribute_classes():
    """`header.py`의 `self.<속성> = <클래스>(...)` 배선을 AST로 읽는다.

    Returns:
        dict[str, str]: 속성 이름 -> 생성하는 클래스 이름
    """
    tree = ast.parse(_HEADER_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        callee = node.value.func
        if not isinstance(callee, ast.Name):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                mapping[target.attr] = callee.id
    return mapping


def _header_class_modules():
    """`header.py`의 `from .<모듈> import <클래스>`를 AST로 읽는다.

    Returns:
        dict[str, str]: 클래스 이름 -> 모듈 경로(점 표기, `max` 기준 상대)
    """
    tree = ast.parse(_HEADER_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                mapping[alias.name] = node.module
    return mapping


#: 이 대조가 뒤지는 소스 루트. 기반 클래스가 `max/` 밖에 있는 경우가 있다
#: (`max/name.py`의 `Name(Naming)`은 `pyjallib/naming.py`를 상속한다).
_SEARCH_ROOTS = (_SRC, _SRC.parent)


def _find_class_node(inClassName: str):
    """클래스 정의를 소스 트리에서 찾아 AST 노드를 돌려준다.

    Args:
        inClassName: 찾을 클래스 이름

    Returns:
        ast.ClassDef | None: 찾은 정의. 없으면 None
    """
    for root in _SEARCH_ROOTS:
        for path in sorted(root.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == inClassName:
                    return node
    return None


def _class_method_names(inClassName: str, inSeen=None):
    """클래스와 그 조상들의 메서드 이름을 모은다.

    이름으로 찾으므로 모듈 경로를 몰라도 되고, `max/` 밖의 기반 클래스
    (`pyjallib/naming.py`의 `Naming` 등)도 따라간다.

    Args:
        inClassName: 클래스 이름
        inSeen: 순환 상속 방지용 방문 집합

    Returns:
        set[str] | None: 메서드 이름 집합. 클래스를 못 찾으면 None
    """
    seen = set() if inSeen is None else inSeen
    if inClassName in seen:
        return set()
    seen.add(inClassName)

    node = _find_class_node(inClassName)
    if node is None:
        return None

    methods = {
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for base in node.bases:
        baseName = base.id if isinstance(base, ast.Name) else None
        if baseName is None:
            continue
        inherited = _class_method_names(baseName, seen)
        if inherited:
            methods |= inherited
    return methods


def test_macro_files_exist():
    """매크로 파일이 실제로 있는지 확인한다(가드가 공허해지지 않게)."""
    macros = _macro_files()
    assert len(macros) >= 5, f"매크로 파일이 부족하다: {[p.name for p in macros]}"


def test_macro_uses_jal_symbols():
    """매크로에서 `jal.*` 호출이 실제로 뽑히는지 확인한다.

    **부재 단정이 공허해지지 않도록 하는 대조군이다.** 정규식이 아무것도 못 뽑으면
    아래 대조 테스트가 전부 통과하지만 실제로는 아무것도 검증하지 않게 된다.
    """
    usages = _collect_jal_usages()
    assert len(usages) >= 40, f"매크로에서 뽑은 jal 심볼이 너무 적다: {len(usages)}"


def test_macro_attributes_exist_in_header():
    """매크로가 쓰는 `jal.<속성>`이 전부 `header.py`에 배선돼 있는지 확인한다."""
    attributes = _header_attribute_classes()
    missing = sorted(
        {
            attrName
            for (attrName, _), _ in _collect_jal_usages().items()
            if attrName not in attributes
        }
    )
    assert not missing, f"header.py에 없는 jal 속성을 매크로가 쓴다: {missing}"


#: **이미 깨져 있는 매크로 심볼**(master에서 실측, 2026-09-21). 이 사이클이 만든 것이
#: 아니고, `macro/`와 코어 `align`은 이 사이클의 Non-Goal이라 고치지 않는다.
#: 목록에 담아 두면 가드가 **새로 깨지는 것**은 여전히 잡는다.
#:
#: `jal_macro_align.jal_align_to_last_center()`가 `Align.align_to_last_sel_center()`를
#: 부르는데 그 메서드가 없다. `Align`에는 `align_to_last_sel`·`_pos`·`_rot`만 있다.
#: 리거가 3ds Max에서 그 매크로를 누르면 AttributeError가 난다.
#: -> 후속 사이클 후보: 메서드를 추가하거나 매크로에서 그 항목을 뺀다.
KNOWN_BROKEN_MACRO_SYMBOLS = {
    ("align", "align_to_last_sel_center"),
}


def test_macro_methods_exist_in_classes():
    """매크로가 쓰는 `jal.<속성>.<메서드>`가 해당 클래스에 정의돼 있는지 확인한다."""
    attributes = _header_attribute_classes()

    missing = []
    for (attrName, methodName), files in sorted(_collect_jal_usages().items()):
        if (attrName, methodName) in KNOWN_BROKEN_MACRO_SYMBOLS:
            continue
        className = attributes.get(attrName)
        if className is None:
            continue
        methods = _class_method_names(className)
        if methods is None:
            missing.append(f"{attrName}.{methodName}: 클래스 {className}을 못 찾음")
            continue
        if methodName not in methods:
            missing.append(f"{attrName}.{methodName} (쓰는 곳: {', '.join(sorted(set(files)))})")

    assert not missing, "매크로가 쓰는 심볼이 사라졌다:\n  " + "\n  ".join(missing)


def test_known_broken_macro_symbols_are_still_broken():
    """알려진 파손 목록이 **실제로 여전히 파손 상태인지** 확인한다.

    고쳐졌는데 목록에 남아 있으면 가드에 구멍이 생긴다(면제가 영구화된다).
    """
    attributes = _header_attribute_classes()
    fixed = []
    for attrName, methodName in sorted(KNOWN_BROKEN_MACRO_SYMBOLS):
        className = attributes.get(attrName)
        methods = _class_method_names(className) if className else None
        if methods and methodName in methods:
            fixed.append(f"{attrName}.{methodName}")
    assert not fixed, (
        f"이제 존재하는 심볼이 KNOWN_BROKEN에 남아 있다: {fixed}. 목록에서 지운다."
    )


def test_macro_does_not_use_rig_parts():
    """매크로가 릭 파트 계열을 쓰지 않는지 확인한다(PRD Q5의 실측 전제).

    이 전제가 깨지면 릭 계열 변경이 매크로에 닿는다는 뜻이고, 그때는 매크로도 함께
    고쳐야 한다. 가드가 그 시점을 알려 준다.
    """
    attributes = _header_attribute_classes()
    rigClassNames = {
        path.stem[0].upper() + path.stem[1:]
        for path in _RIG_DIR.glob("*.py")
        if path.name not in ("__init__.py", "rigPart.py", "limbVolume.py", "boneChain.py")
    }
    used = sorted(
        {
            attrName
            for (attrName, _), _ in _collect_jal_usages().items()
            if attributes.get(attrName) in rigClassNames
        }
    )
    assert not used, (
        f"매크로가 릭 파트를 쓴다: {used}. PRD Q5의 전제가 바뀌었으므로 "
        "릭 계열 변경 시 매크로도 함께 수정해야 한다."
    )


# ---------------------------------------------------------------------------
# rig/ 위생 가드
# ---------------------------------------------------------------------------


def _rig_files():
    """`rig/` 아래 `.py` 파일 목록을 돌려준다.

    Returns:
        list[Path]: 모듈 파일
    """
    return sorted(_RIG_DIR.glob("*.py"))


def test_rig_files_exist():
    """`rig/` 모듈이 실제로 있는지 확인한다(아래 부재 단정이 공허해지지 않게)."""
    assert len(_rig_files()) >= 15, f"rig 모듈이 부족하다: {[p.name for p in _rig_files()]}"


@pytest.mark.parametrize("path", _rig_files(), ids=lambda p: p.name)
def test_rig_has_no_print(path):
    """`rig/` 안에 `print(`가 없는지 확인한다. 로그는 pyjallib Logger로 남긴다."""
    text = path.read_text(encoding="utf-8")
    offenders = [
        f"{index}: {line.strip()}"
        for index, line in enumerate(text.splitlines(), start=1)
        if re.search(r"(?<![\w.])print\s*\(", line)
    ]
    assert not offenders, f"{path.name}에 print(가 있다:\n  " + "\n  ".join(offenders)


@pytest.mark.parametrize("path", _rig_files(), ids=lambda p: p.name)
def test_rig_has_no_bare_except(path):
    """`rig/` 안에 bare `except:`가 없는지 확인한다."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.type is None
    ]
    assert not offenders, f"{path.name}의 {offenders}번 줄에 bare except가 있다"


@pytest.mark.parametrize("path", _rig_files(), ids=lambda p: p.name)
def test_rig_has_no_messagebox(path):
    """`rig/` 안에 `rt.messageBox`가 없는지 확인한다.

    라이브러리가 UI를 띄우면 헤드리스에서 판정할 수 없고 실패 사유도 사라진다.
    사유는 Logger로 가고 반환은 `None`으로 통일한다.
    """
    # 호출만 본다 - 주석에서 이 규칙 자체를 설명할 때 이름이 나오기 때문이다.
    text = path.read_text(encoding="utf-8")
    offenders = [
        f"{index}: {line.strip()}"
        for index, line in enumerate(text.splitlines(), start=1)
        if re.search(r"messageBox\s*\(", line)
    ]
    assert not offenders, f"{path.name}에 messageBox 호출이 있다:\n  " + "\n  ".join(offenders)


def test_rig_entry_points_return_none_on_failure():
    """`create_bones`가 실패 경로에서 `False`를 돌려주지 않는지 확인한다.

    실패 반환이 `False`와 `None`으로 갈리면 호출부가 둘 다 검사해야 한다.
    `delete()`·`validate_source_nodes()`처럼 **참·거짓을 뜻하는 술어**는 대상이 아니다.
    """
    offenders = []
    for path in _rig_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "create_bones":
                continue
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Return)
                    and isinstance(sub.value, ast.Constant)
                    and sub.value.value is False
                ):
                    offenders.append(f"{path.name}:{sub.lineno}")
    assert not offenders, f"create_bones가 False를 반환한다: {offenders}"
