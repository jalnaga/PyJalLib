# -*- coding: utf-8 -*-
"""Perforce.move_files 단위 테스트 (P4 서버 없이 mock).

실제 P4 서버 대신 pyjallib.perforce.P4를 mock으로 교체하여, move_files가
각 (source, target) 쌍에 대해 `p4 edit` 후 `p4 move`를 올바른 인자로 호출하는지 검증한다.

단일 쌍·빈 리스트·비리스트 입력은 tests/perforce/test_char_fileops.py::TestMoveFiles가
호출 시퀀스까지 단정하므로 여기서는 다중 쌍만 본다(2026-11-05 테스트 정리에서 중복 제거).
"""

from unittest.mock import MagicMock, patch

from pyjallib.perforce import Perforce


def _make_p4_mock():
    """connected()=True, run()=[] 인 P4 인스턴스 mock을 만든다."""
    mock_p4 = MagicMock()
    mock_p4.connected.return_value = True
    mock_p4.run.return_value = []
    return mock_p4


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
