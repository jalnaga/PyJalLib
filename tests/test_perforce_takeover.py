# -*- coding: utf-8 -*-
"""Perforce 배치 메서드의 "내 pending CL 이어받기(reopen)" 단위 테스트 (P4 서버 없이 mock).

과거에는 파일이 자기 클라이언트의 다른 CL에 열려 있으면 P4Exception을 던져
재익스포트가 중단됐다. 수정 후에는 `p4 reopen -c 대상CL`로 이어받고 흐름을
계속해야 한다. 이 테스트는 checkout_files/add_files/delete_files/move_files가
오픈 상태별로 올바른 p4 명령을 호출하는지 검증한다.
"""

from unittest.mock import MagicMock, patch

import pytest

from P4 import P4Exception
from pyjallib.perforce import Perforce

_LOCAL_A = r"C:\ws\proj\A.max"
_LOCAL_B = r"C:\ws\proj\B.fbx"
_DEPOT_A = "//depot/proj/A.max"
_DEPOT_B = "//depot/proj/B.fbx"


def _make_wrap():
    """workspace가 설정된 Perforce 래퍼를 만든다."""
    p4wrap = Perforce("server:1666", "Dev")
    p4wrap.workspace_name = "ws"
    return p4wrap


def _make_p4_mock(inOpenedResult, inWhereResult):
    """opened/where 결과를 지정한 P4 인스턴스 mock을 만든다.

    Args:
        inOpenedResult: `p4 opened` 반환값 (리스트) 또는 P4Exception 인스턴스
        inWhereResult: `p4 where` 반환값 (리스트)

    Returns:
        MagicMock: run()이 명령별로 분기하는 P4 mock
    """
    mock_p4 = MagicMock()
    mock_p4.connected.return_value = True

    def _run(command, *args):
        if command == "opened":
            if isinstance(inOpenedResult, Exception):
                raise inOpenedResult
            return inOpenedResult
        if command == "where":
            return inWhereResult
        return []

    mock_p4.run.side_effect = _run
    return mock_p4


def _opened_entry(inDepotFile, inChange, inAction="edit"):
    """`p4 opened` 결과 엔트리 딕셔너리를 만든다."""
    return {"depotFile": inDepotFile, "change": inChange, "action": inAction}


def _where_entry(inDepotFile, inLocalPath):
    """`p4 where` 결과 엔트리 딕셔너리를 만든다."""
    return {"depotFile": inDepotFile, "clientFile": f"//ws{inDepotFile[7:]}", "path": inLocalPath}


def _calls_of(mock_p4, inCommand):
    """run 호출 중 첫 인자가 inCommand인 호출 목록을 반환한다."""
    return [c for c in mock_p4.run.call_args_list if c.args and c.args[0] == inCommand]


# ============================================================================
# 3.1 헬퍼 분기: 다른 CL 열림 / default 열림 / 미열림
# ============================================================================

def test_checkout_takes_over_file_opened_in_other_changelist():
    """다른 숫자 CL에 열린 파일은 reopen으로 대상 CL로 이어받고 재-edit는 생략한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.checkout_files([_LOCAL_A], 42)

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "42", _DEPOT_A)
    assert _calls_of(mock_p4, "edit") == []


def test_checkout_takes_over_file_opened_in_default_changelist():
    """default CL에 열린 파일도 reopen으로 대상 CL로 이동한다 (기존 p4 edit 잔류 결함 해소)."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "default", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.checkout_files([_LOCAL_A], 42)

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "42", _DEPOT_A)


def test_checkout_unopened_files_keeps_existing_edit_flow():
    """열려 있지 않은 파일('not opened' 예외)은 기존대로 edit만 실행하고 reopen하지 않는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=P4Exception("file(s) not opened on this client."),
        inWhereResult=[],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.checkout_files([_LOCAL_A], 42)

    assert result is True
    mock_p4.run.assert_any_call("edit", "-c", "42", normA)
    assert _calls_of(mock_p4, "reopen") == []


def test_checkout_file_already_in_target_changelist_skips_reopen():
    """이미 대상 CL에 열린 파일은 reopen도 재-edit도 하지 않는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "42", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.checkout_files([_LOCAL_A], 42)

    assert result is True
    assert _calls_of(mock_p4, "reopen") == []
    assert _calls_of(mock_p4, "edit") == []


def test_takeover_to_default_changelist_target():
    """대상 CL이 문자열 'default'여도(numbered CL -> default) reopen으로 이동한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "77", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.checkout_files([_LOCAL_A], "default")

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "default", _DEPOT_A)


def test_takeover_raises_on_unexpected_opened_error():
    """'not opened'가 아닌 opened 조회 실패는 그대로 예외를 전파한다."""
    p4wrap = _make_wrap()
    mock_p4 = _make_p4_mock(
        inOpenedResult=P4Exception("Connection reset by peer"),
        inWhereResult=[],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        with pytest.raises(P4Exception):
            p4wrap.checkout_files([_LOCAL_A], 42)


# ============================================================================
# 3.2 메서드별 분기: 혼합 케이스 / add / delete / move
# ============================================================================

def test_checkout_mixed_opened_and_unopened_files():
    """열린 파일은 이어받고, 안 열린 파일만 edit 인자로 넘긴다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    normB = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normA), _where_entry(_DEPOT_B, normB)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.checkout_files([_LOCAL_A, _LOCAL_B], 42)

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "42", _DEPOT_A)
    mock_p4.run.assert_any_call("edit", "-c", "42", normB)


def test_add_skips_already_opened_file_and_adds_new_one():
    """add로 이미 열린 파일은 reopen만 하고, 새 파일만 add한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    normB = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "add")],
        inWhereResult=[_where_entry(_DEPOT_A, normA), _where_entry(_DEPOT_B, normB)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.add_files([_LOCAL_A, _LOCAL_B], 42)

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "42", _DEPOT_A)
    mock_p4.run.assert_any_call("add", "-c", "42", normB)
    addCalls = _calls_of(mock_p4, "add")
    assert len(addCalls) == 1


def test_delete_skips_file_already_opened_for_delete():
    """delete로 이미 열린 파일은 reopen 후 재-delete하지 않는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "delete")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.delete_files([_LOCAL_A], 42)

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "42", _DEPOT_A)
    assert _calls_of(mock_p4, "delete") == []


def test_delete_converts_edit_opened_file_via_revert():
    """edit로 열린 파일의 delete 요청은 revert -k 후 delete로 다시 연다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.delete_files([_LOCAL_A], 42)

    assert result is True
    mock_p4.run.assert_any_call("revert", "-k", normA)
    mock_p4.run.assert_any_call("delete", "-c", "42", normA)


def test_delete_cancels_add_opened_file_without_delete():
    """add로 열린 파일의 delete 요청은 add만 취소하고 delete는 생략한다 (depot 미존재)."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "add")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.delete_files([_LOCAL_A], 42)

    assert result is True
    mock_p4.run.assert_any_call("revert", "-k", normA)
    assert _calls_of(mock_p4, "delete") == []


def test_move_skips_reedit_for_opened_source():
    """이미 열린 원본은 재-edit 없이 바로 move한다."""
    p4wrap = _make_wrap()
    normSrc = p4wrap._normalize_path(_LOCAL_A)
    normDst = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, "99", "edit")],
        inWhereResult=[_where_entry(_DEPOT_A, normSrc)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_files([(_LOCAL_A, _LOCAL_B)], 42)

    assert result is True
    mock_p4.run.assert_any_call("reopen", "-c", "42", _DEPOT_A)
    assert _calls_of(mock_p4, "edit") == []
    mock_p4.run.assert_any_call("move", "-c", "42", normSrc, normDst)


def test_comparable_path_absorbs_separator_and_case_differences():
    """경로 비교 키가 구분자/대소문자 차이를 흡수한다."""
    assert Perforce._comparable_path(r"C:\WS\Proj\A.max") == Perforce._comparable_path("c:/ws/proj/a.max")
