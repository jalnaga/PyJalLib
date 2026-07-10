# -*- coding: utf-8 -*-
"""Perforce.move_files 단위 테스트 (P4 서버 없이 mock).

실제 P4 서버 대신 pyjallib.perforce.P4를 mock으로 교체하여, move_files가
각 (source, target) 쌍에 대해 `p4 edit` 후 `p4 move`를 올바른 인자로 호출하는지 검증한다.
"""

from unittest.mock import MagicMock, patch

import pytest

from pyjallib.perforce import Perforce


def _make_p4_mock():
    """connected()=True, run()=[] 인 P4 인스턴스 mock을 만든다."""
    mock_p4 = MagicMock()
    mock_p4.connected.return_value = True
    mock_p4.run.return_value = []
    return mock_p4


def test_move_files_issues_edit_then_move():
    """각 쌍에 대해 edit → move를 지정 CL 인자로 호출한다."""
    p4wrap = Perforce("server:1666", "Dev")
    p4wrap.workspace_name = "ws"
    mock_p4 = _make_p4_mock()

    pairs = [(r"C:\old\SK_Old.max", r"C:\new\SK_New.max")]
    normSrc = p4wrap._normalize_path(pairs[0][0])
    normDst = p4wrap._normalize_path(pairs[0][1])

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_files(pairs, 42)

    assert result is True
    mock_p4.run.assert_any_call("edit", "-c", "42", normSrc)
    mock_p4.run.assert_any_call("move", "-c", "42", normSrc, normDst)
    mock_p4.disconnect.assert_called_once()


def test_move_files_multiple_pairs_all_moved():
    """여러 쌍이면 각각 edit+move가 호출된다."""
    p4wrap = Perforce("server:1666", "Dev")
    p4wrap.workspace_name = "ws"
    mock_p4 = _make_p4_mock()

    pairs = [
        (r"C:\a\X.max", r"C:\b\X2.max"),
        (r"C:\a\Y.fbx", r"C:\b\Y2.fbx"),
    ]

    with patch("pyjallib.perforce.P4", return_value=mock_p4):
        result = p4wrap.move_files(pairs, 7)

    assert result is True
    moveCalls = [c for c in mock_p4.run.call_args_list if c.args and c.args[0] == "move"]
    editCalls = [c for c in mock_p4.run.call_args_list if c.args and c.args[0] == "edit"]
    assert len(moveCalls) == 2
    assert len(editCalls) == 2


def test_move_files_empty_returns_false():
    """빈 리스트는 False를 반환하고 P4에 접속하지 않는다."""
    p4wrap = Perforce("server:1666", "Dev")
    with patch("pyjallib.perforce.P4") as mock_cls:
        result = p4wrap.move_files([], 1)
    assert result is False
    mock_cls.assert_not_called()


def test_move_files_non_list_raises():
    """리스트가 아니면 ValueError."""
    p4wrap = Perforce("server:1666", "Dev")
    with pytest.raises(ValueError):
        p4wrap.move_files("not-a-list", 1)
