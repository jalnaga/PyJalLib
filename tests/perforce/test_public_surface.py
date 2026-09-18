# -*- coding: utf-8 -*-
"""`pyjallib.perforce` 공개 표면 불변 가드 (ExportToolsRefactor Phase 10.13).

서브패키지 분해 뒤에도 (1) `from pyjallib.perforce import Perforce, P4Exception, OpenedFilesCollectResult`가
동작하고, (2) `Perforce`의 메서드 이름 집합이 분해 전 스냅샷과 같고, (3) 특성화가 공개 메서드 34개
전부를 최소 1건씩 부르는지 목록으로 대조한다.
"""

import ast
import inspect
from pathlib import Path

import pyjallib
import pyjallib.perforce as perforcePackage
from pyjallib.perforce import OpenedFilesCollectResult, P4Exception, Perforce

# 분해 전(0.3.7, perforce.py 1671줄) `Perforce` 메서드 스냅샷 - 공개 34 + 비공개 8
PUBLIC_METHODS = {
    "connect", "disconnect",
    "create_change_list", "delete_change_list", "delete_empty_change_list", "submit_change_list",
    "revert_change_list", "edit_change_list",
    "move_opened_files_to_new_change_list", "collect_opened_files_into_change_list",
    "get_pending_change_list", "get_change_list_by_number", "get_change_list_by_description",
    "get_change_list_by_description_pattern", "get_default_change_list",
    "checkout_files", "add_files", "delete_files", "move_files", "revert_files",
    "checkout_file", "add_file", "delete_file", "revert_file",
    "is_file_checked_out", "check_files_checked_out", "is_file_checked_out_by_others",
    "check_files_checked_out_all_users", "get_file_checkout_info_all_users", "get_files_checked_out_by_others",
    "is_file_in_pending_changelist", "is_file_in_perforce",
    "check_update_required", "sync_files",
}
PRIVATE_METHODS = {
    "_normalize_path", "_normalize_paths", "_comparable_path", "_map_depot_to_local",
    "_takeover_opened_files", "_delete_emptied_changelists",
    "_collect_comparable_paths_in_change_list", "_rollback_change_list_move",
}


def _methods(inCls):
    return {name for name, member in inspect.getmembers(inCls) if inspect.isroutine(member) and not name.startswith("__")}


def test_public_imports_are_stable():
    assert perforcePackage.Perforce is Perforce
    assert pyjallib.Perforce is Perforce
    assert issubclass(P4Exception, Exception)
    assert callable(perforcePackage.P4), "패키지 이름 `pyjallib.perforce.P4`는 테스트 대역 주입점이다"
    assert OpenedFilesCollectResult.__dataclass_fields__.keys() == {"succeeded", "changelist", "movedCount", "missingPaths", "submitted", "message"}


def test_method_set_matches_snapshot():
    assert len(PUBLIC_METHODS) == 34
    assert _methods(Perforce) == PUBLIC_METHODS | PRIVATE_METHODS


def test_every_public_method_is_characterized():
    """특성화 테스트 소스에서 `.<메서드>(` 호출을 찾아 34개 전부가 덮이는지 본다."""
    testDir = Path(__file__).parent
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in testDir.glob("test_char_*.py"))
    uncovered = sorted(name for name in PUBLIC_METHODS | PRIVATE_METHODS if f".{name}(" not in corpus)
    assert uncovered == [], uncovered


def test_no_print_to_logger_conversion_happened():
    """이 Phase의 금지 사항: `print()` → `Logger` 전환은 동작 변경이라 하지 않는다."""
    sourceFiles = [Path(perforcePackage.__file__)]
    packageDir = Path(perforcePackage.__file__).parent
    if Path(perforcePackage.__file__).name == "__init__.py":
        sourceFiles = list(packageDir.glob("*.py"))
    text = "\n".join(p.read_text(encoding="utf-8") for p in sourceFiles)
    tree = ast.parse(text)
    printCalls = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print")
    assert printCalls >= 40, printCalls
    assert "get_logger" not in text and "Logger(" not in text
