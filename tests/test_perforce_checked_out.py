# -*- coding: utf-8 -*-
"""`Perforce.check_files_checked_out` 열림 판정 단위 테스트 (P4 서버 없이 mock).

과거 구현은 `p4 opened`가 돌려주는 `clientFile`(클라이언트 문법
`//워크스페이스명/...`)을 로컬 절대경로와 대조해 **어떤 경우에도 매칭되지 않고
전부 False**를 돌려줬다. 수정 후에는 `depotFile` + `p4 where` 매핑으로
로컬 절대경로를 복원해 판정해야 한다.

격리 방식은 기존 P4 단위 테스트(`test_perforce_takeover.py`)와 동일하게
`pyjallib.perforce.P4`를 패치한다. P4Python은 선언된 의존이라 실제로 import
가능하므로, sys.modules 통째 주입 대신 생성자만 가로채는 쪽이 부작용이 없다.
"""

from unittest.mock import MagicMock, patch

from P4 import P4Exception
from pyjallib.perforce import Perforce

_LOCAL_A = r"C:\ws\proj\A.uasset"
_LOCAL_B = r"C:\ws\proj\B.uasset"
_DEPOT_A = "//depot/proj/A.uasset"
_DEPOT_B = "//depot/proj/B.uasset"

# p4 opened가 돌려주는 클라이언트 문법 경로 (로컬 절대경로가 아니다)
_CLIENT_A = "//ws/proj/A.uasset"


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


def _opened_entry(inDepotFile, inClientFile, inChange, inAction="edit"):
    """`p4 opened` 결과 엔트리 딕셔너리를 만든다 (clientFile은 클라이언트 문법)."""
    return {
        "depotFile": inDepotFile,
        "clientFile": inClientFile,
        "change": inChange,
        "action": inAction,
    }


def _where_entry(inDepotFile, inLocalPath):
    """`p4 where` 결과 엔트리 딕셔너리를 만든다."""
    return {
        "depotFile": inDepotFile,
        "clientFile": f"//ws{inDepotFile[7:]}",
        "path": inLocalPath,
    }


# ============================================================================
# 판정 4종: 열림 / 미열림 / 타 CL 열림 / 미존재
# ============================================================================

def test_opened_in_default_changelist_is_reported_as_checked_out():
    """default CL에 열린 파일은 True로 판정한다 (clientFile 대조 없이 depotFile 기준)."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, _CLIENT_A, "default")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result == {normA: True}


def test_unopened_file_is_reported_as_not_checked_out():
    """열려 있지 않은 파일('not opened' 예외)은 False로 판정한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=P4Exception("file(s) not opened on this client."),
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result == {normA: False}


def test_opened_in_other_numbered_changelist_is_reported_as_checked_out():
    """다른 숫자 CL에 열려 있어도 '열림'이므로 True로 판정한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, _CLIENT_A, "12345")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result == {normA: True}


def test_file_missing_from_depot_is_reported_as_not_checked_out():
    """depot에 없는 파일은 opened 결과가 비어 False로 판정한다 (where도 unmap)."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[],
        inWhereResult=[{"depotFile": _DEPOT_A, "unmap": ""}],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result == {normA: False}


# ============================================================================
# 혼합 / 회귀 감시
# ============================================================================

def test_mixed_opened_and_unopened_files_are_judged_independently():
    """열린 파일만 True가 되고 나머지는 False로 남는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    normB = p4wrap._normalize_path(_LOCAL_B)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, _CLIENT_A, "default")],
        inWhereResult=[_where_entry(_DEPOT_A, normA), _where_entry(_DEPOT_B, normB)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A, _LOCAL_B])

    assert result == {normA: True, normB: False}


def test_client_syntax_path_alone_never_produces_false_negative():
    """clientFile만 클라이언트 문법이어도 depotFile 매핑으로 정확히 판정한다.

    회귀 감시: clientFile을 `Path().resolve()`로 정규화해 대조하던 구현은
    이 케이스에서 False를 돌려줬다(실제로 열린 파일을 '미열림'으로 오탐).
    """
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, _CLIENT_A, "default")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result[normA] is True
    # 오탐 방지의 근거: clientFile을 로컬 경로로 오해하지 않았는지 확인
    assert p4wrap._normalize_path(_CLIENT_A) != normA


def test_case_and_separator_differences_are_absorbed_in_matching():
    """where가 돌려준 경로의 구분자/대소문자가 달라도 같은 파일로 매칭한다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_A, _CLIENT_A, "default")],
        inWhereResult=[_where_entry(_DEPOT_A, normA.replace("\\", "/").lower())],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result == {normA: True}


def test_unmappable_opened_entry_is_excluded_instead_of_mismatched():
    """where 매핑이 없는 열린 파일은 다른 입력에 잘못 귀속되지 않는다."""
    p4wrap = _make_wrap()
    normA = p4wrap._normalize_path(_LOCAL_A)
    mock_p4 = _make_p4_mock(
        inOpenedResult=[_opened_entry(_DEPOT_B, "//ws/proj/B.uasset", "default")],
        inWhereResult=[_where_entry(_DEPOT_A, normA)],
    )

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.check_files_checked_out([_LOCAL_A])

    assert result == {normA: False}
