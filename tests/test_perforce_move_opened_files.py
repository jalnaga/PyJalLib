# -*- coding: utf-8 -*-
"""`Perforce.move_opened_files_to_new_change_list` 단위 테스트 (P4 서버 없이 mock).

이 메서드는 "이미 열린 파일들을 새 체인지리스트로 모은다"는 계약만 갖는다.
따라서 `p4 reopen` 단독으로 동작해야 하고(3연타·sync -k·reconcile 금지),
"예외 안 났다"를 성공으로 삼지 않도록 `p4 opened -c` 사후 대조를 거쳐야 한다.
서밋은 이 메서드의 책임이 아니다.
"""

from unittest.mock import MagicMock, patch

import pytest

from P4 import P4Exception
from pyjallib.perforce import Perforce

_LOCAL_A = r"C:\ws\proj\A.uasset"
_LOCAL_B = r"C:\ws\proj\B.uasset"
_DEPOT_A = "//depot/proj/A.uasset"
_DEPOT_B = "//depot/proj/B.uasset"

_NEW_CL = 4242
_DESCRIPTION = "[TA 김동석] Import Batch Animation Files"


def _make_wrap():
    """workspace가 설정된 Perforce 래퍼를 만든다."""
    p4wrap = Perforce("server:1666", "Dev")
    p4wrap.workspace_name = "ws"
    return p4wrap


def _where_entry(inDepotFile, inLocalPath):
    """`p4 where` 결과 엔트리 딕셔너리를 만든다."""
    return {
        "depotFile": inDepotFile,
        "clientFile": f"//ws{inDepotFile[7:]}",
        "path": inLocalPath,
    }


def _opened_entry(inDepotFile, inChange):
    """`p4 opened -c` 결과 엔트리 딕셔너리를 만든다."""
    return {
        "depotFile": inDepotFile,
        "clientFile": f"//ws{inDepotFile[7:]}",
        "change": str(inChange),
        "action": "edit",
    }


def _make_p4_mock(inOpenedInClResult, inWhereResult, inReopenError=None):
    """CL 생성 -> reopen -> 사후 대조 흐름을 제어하는 P4 mock을 만든다.

    Args:
        inOpenedInClResult: `p4 opened -c <CL>` 반환값 (리스트) 또는 P4Exception
        inWhereResult: `p4 where` 반환값 (리스트)
        inReopenError: `p4 reopen` 호출 시 던질 예외 (None이면 정상)

    Returns:
        MagicMock: P4 mock
    """
    mock_p4 = MagicMock()
    mock_p4.connected.return_value = True
    mock_p4.save_change.return_value = [f"Change {_NEW_CL} created."]

    def _run(command, *args):
        if command == "change" and args and args[0] == "-o":
            return [{"Change": "new", "Description": "", "Files": ["//depot/other/X"]}]
        if command == "reopen":
            if inReopenError is not None and args and args[1] != "default":
                raise inReopenError
            return []
        if command == "opened":
            if isinstance(inOpenedInClResult, Exception):
                raise inOpenedInClResult
            return inOpenedInClResult
        if command == "where":
            return inWhereResult
        return []

    mock_p4.run.side_effect = _run
    return mock_p4


def _calls_of(mock_p4, inCommand):
    """run 호출 중 첫 인자가 inCommand인 호출 목록을 반환한다."""
    return [c for c in mock_p4.run.call_args_list if c.args and c.args[0] == inCommand]


# ============================================================================
# 정상 이동
# ============================================================================

def test_all_opened_files_are_moved_to_new_changelist():
    """전량이 새 CL에서 확인되면 succeeded=True와 이동 수를 반환한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    normB = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[_opened_entry(_DEPOT_A, _NEW_CL), _opened_entry(_DEPOT_B, _NEW_CL)],
        inWhereResult=[_where_entry(_DEPOT_A, normA), _where_entry(_DEPOT_B, normB)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_opened_files_to_new_change_list(
            _DESCRIPTION, [_LOCAL_A, _LOCAL_B]
        )

    assert result == {
        'succeeded': True,
        'changelist': _NEW_CL,
        'movedCount': 2,
        'missingPaths': [],
    }
    mock_p4.run.assert_any_call("reopen", "-c", str(_NEW_CL), normA, normB)


def test_move_uses_reopen_only_without_brute_force_commands():
    """reopen 단독으로 끝난다 (edit/add/sync/reconcile 금지 - 계약이 '열린 파일')."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[_opened_entry(_DEPOT_A, _NEW_CL)],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A])

    assert _calls_of(mock_p4, "edit") == []
    assert _calls_of(mock_p4, "add") == []
    assert _calls_of(mock_p4, "sync") == []
    assert _calls_of(mock_p4, "reconcile") == []


def test_new_changelist_does_not_inherit_default_changelist_files():
    """새 CL 스펙에서 Files 필드를 제거해 default CL 파일이 딸려오지 않게 한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[_opened_entry(_DEPOT_A, _NEW_CL)],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A])

    savedSpec = mock_p4.save_change.call_args.args[0]
    assert savedSpec["Description"] == _DESCRIPTION
    assert "Files" not in savedSpec


def test_submit_is_never_called():
    """서밋은 이 메서드의 책임이 아니다 (회귀 감시)."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[_opened_entry(_DEPOT_A, _NEW_CL)],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A])

    assert _calls_of(mock_p4, "submit") == []


# ============================================================================
# 일부 미열림 검출 (사후 대조)
# ============================================================================

def test_partially_moved_files_are_reported_as_missing():
    """대상 CL에서 확인되지 않은 입력은 missingPaths로 보고하고 succeeded=False."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    normB = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[_opened_entry(_DEPOT_A, _NEW_CL)],
        inWhereResult=[_where_entry(_DEPOT_A, normA), _where_entry(_DEPOT_B, normB)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_opened_files_to_new_change_list(
            _DESCRIPTION, [_LOCAL_A, _LOCAL_B]
        )

    assert result['succeeded'] is False
    assert result['movedCount'] == 1
    assert result['missingPaths'] == [normB]


def test_nothing_moved_is_not_reported_as_success():
    """사후 대조가 비면(전량 미이동) 성공으로 판정하지 않는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=P4Exception("file(s) not opened on this client."),
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A])

    assert result['succeeded'] is False
    assert result['movedCount'] == 0
    assert result['missingPaths'] == [normA]
    # CL은 유지한다 (원인 진단용) - 삭제하지 않는다
    deleteCalls = [c for c in _calls_of(mock_p4, "change") if c.args[1] == "-d"]
    assert deleteCalls == []


def test_partial_move_keeps_changelist_for_diagnosis():
    """부분 이동은 예외가 아니므로 CL을 삭제하지 않는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    normB = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[_opened_entry(_DEPOT_A, _NEW_CL)],
        inWhereResult=[_where_entry(_DEPOT_A, normA), _where_entry(_DEPOT_B, normB)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A, _LOCAL_B])

    deleteCalls = [c for c in _calls_of(mock_p4, "change") if c.args[1] == "-d"]
    assert deleteCalls == []


# ============================================================================
# 실패 롤백
# ============================================================================

def test_reopen_failure_rolls_back_to_default_and_deletes_changelist():
    """reopen 실패 시 default로 되돌리고 빈 CL을 삭제한 뒤 예외를 전파한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
        inReopenError=P4Exception("Change 4242 unknown."),
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        with pytest.raises(P4Exception):
            p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A])

    mock_p4.run.assert_any_call("reopen", "-c", "default", normA)
    mock_p4.run.assert_any_call("change", "-d", str(_NEW_CL))


def test_rollback_never_reverts_file_contents():
    """롤백은 '이동'만 되돌린다 - 임포트 결과가 사라지지 않도록 revert 금지."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedInClResult=[],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
        inReopenError=P4Exception("Change 4242 unknown."),
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        with pytest.raises(P4Exception):
            p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [_LOCAL_A])

    assert _calls_of(mock_p4, "revert") == []


# ============================================================================
# 입력 방어
# ============================================================================

def test_empty_file_list_does_not_create_changelist():
    """빈 목록이면 CL을 만들지 않고 실패로 보고한다."""
    p4wrap = _make_wrap()
    mock_p4 = _make_p4_mock(inOpenedInClResult=[], inWhereResult=[])

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, [])

    assert result == {
        'succeeded': False,
        'changelist': None,
        'movedCount': 0,
        'missingPaths': [],
    }
    mock_p4.run.assert_not_called()


def test_non_list_input_raises_value_error():
    """리스트가 아닌 입력은 ValueError로 즉시 막는다 (모듈 관례)."""
    p4wrap = _make_wrap()

    with pytest.raises(ValueError):
        p4wrap.move_opened_files_to_new_change_list(_DESCRIPTION, _LOCAL_A)
