# -*- coding: utf-8 -*-
"""`Perforce.collect_opened_files_into_change_list` Type A (P4 서버 없이 mock).

**이관 이력 (2026-09-18 ExportToolsRefactor Phase 1):** 세 툴이 각자 들고 있던
"이동 결과 해석 → 조건부 서밋" 코드(BatchAnimExporter `p4Changelist.py`,
NewAnimExporter `UE5ImportService.move_assets_to_new_changelist`, MeshValidator
`ue5P4Manager._manage_p4_changelist`)를 pyjallib 신규 메서드로 합쳤다. 여기의 4경로는
BatchAnimExporter `tests/test_p4changelist_move.py`의 서밋 관련 케이스
(`test_submit_is_called_when_requested` / `test_submit_is_skipped_when_not_requested` /
`test_partial_move_blocks_submit` / `test_empty_changelist_submit_is_reported_as_failure`)
를 라이브러리 계약 형태로 재명세한 것이다. 개발 모드·prefix 같은 ORV 해석은 orvlib
층(Phase 2)에 남으므로 여기에는 없다.

신규 메서드는 기존 메서드(`move_opened_files_to_new_change_list` / `submit_change_list`)를
호출만 하므로 그 둘을 mock으로 대체해 오케스트레이션만 단정한다. 기존 메서드의
P4 수준 동작은 `test_perforce_move_opened_files.py`(12건)가 그대로 덮는다.
"""

from unittest.mock import patch

import pytest

from P4 import P4Exception
from pyjallib.perforce import OpenedFilesCollectResult, Perforce

_LOCAL_A = r"C:\ws\proj\A.uasset"
_LOCAL_B = r"C:\ws\proj\B.uasset"
_NEW_CL = 4242
_DESCRIPTION = "[TA 김동석] Import Batch Animation Files"


def _make_wrap():
    """workspace가 설정된 Perforce 래퍼를 만든다."""
    p4wrap = Perforce("server:1666", "Dev")
    p4wrap.workspace_name = "ws"
    return p4wrap


def _move_result(inSucceeded, inMissing=None, inChangelist=_NEW_CL, inMoved=None):
    """`move_opened_files_to_new_change_list`의 반환 dict를 만든다."""
    missing = list(inMissing or [])
    moved = (2 - len(missing)) if inMoved is None else inMoved
    return {
        "succeeded": inSucceeded,
        "changelist": inChangelist,
        "movedCount": moved,
        "missingPaths": missing,
    }


# ============================================================================
# 경로 ① 전량 이동 + 서밋
# ============================================================================

def test_full_move_with_submit_submits_and_reports():
    """전량 이동 후 `inShouldSubmit=True`면 `submit_change_list`가 그 CL로 호출된다."""
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      return_value=_move_result(True)) as mockMove, \
         patch.object(Perforce, "submit_change_list", return_value=True) as mockSubmit:
        result = p4wrap.collect_opened_files_into_change_list(
            _DESCRIPTION, [_LOCAL_A, _LOCAL_B], inShouldSubmit=True
        )

    mockMove.assert_called_once_with(_DESCRIPTION, [_LOCAL_A, _LOCAL_B])
    mockSubmit.assert_called_once_with(_NEW_CL)
    assert isinstance(result, OpenedFilesCollectResult)
    assert result.succeeded is True
    assert result.submitted is True
    assert result.changelist == _NEW_CL
    assert result.movedCount == 2
    assert result.missingPaths == []
    assert str(_NEW_CL) in result.message


# ============================================================================
# 경로 ② 전량 이동 + 서밋 안 함 (pending 유지)
# ============================================================================

def test_full_move_without_submit_keeps_changelist_pending():
    """기본값(`inShouldSubmit=False`)이면 서밋을 부르지 않고 CL 번호만 돌려준다.

    MeshValidator의 "서밋 없음(사람 검수)" 정책이 이 경로다.
    """
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      return_value=_move_result(True)), \
         patch.object(Perforce, "submit_change_list") as mockSubmit:
        result = p4wrap.collect_opened_files_into_change_list(
            _DESCRIPTION, [_LOCAL_A, _LOCAL_B]
        )

    mockSubmit.assert_not_called()
    assert result.succeeded is True
    assert result.submitted is False
    assert result.changelist == _NEW_CL
    assert "pending" in result.message


# ============================================================================
# 경로 ③ 부분 누락 → 서밋 중단·CL 유지
# ============================================================================

def test_partial_move_blocks_submit_and_keeps_changelist():
    """일부가 대상 CL에서 확인되지 않으면 서밋을 요청했어도 부르지 않는다 (부분 제출 방지)."""
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      return_value=_move_result(False, inMissing=[_LOCAL_B])), \
         patch.object(Perforce, "submit_change_list") as mockSubmit:
        result = p4wrap.collect_opened_files_into_change_list(
            _DESCRIPTION, [_LOCAL_A, _LOCAL_B], inShouldSubmit=True
        )

    mockSubmit.assert_not_called()
    assert result.succeeded is False
    assert result.submitted is False
    assert result.changelist == _NEW_CL  # CL은 삭제하지 않고 유지 - 진단용
    assert result.missingPaths == [_LOCAL_B]
    assert result.movedCount == 1
    assert str(_NEW_CL) in result.message
    assert "중단" in result.message


# ============================================================================
# 경로 ④ 서밋이 False (빈 CL 삭제)
# ============================================================================

def test_empty_changelist_submit_is_reported_not_raised():
    """`submit_change_list`가 False(내용 변경 없음 → 빈 CL 삭제)를 돌려주면 이동 성공·서밋 False로 보고한다.

    이것은 오류가 아니라 정상 경로다(`submit_change_list` 독스트링). 호출자가
    "서밋했다고 믿었는데 depot에 없다"를 진단할 수 있게 메시지에 사유를 남긴다.
    """
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      return_value=_move_result(True)), \
         patch.object(Perforce, "submit_change_list", return_value=False):
        result = p4wrap.collect_opened_files_into_change_list(
            _DESCRIPTION, [_LOCAL_A, _LOCAL_B], inShouldSubmit=True
        )

    assert result.succeeded is True
    assert result.submitted is False
    assert "빈 체인지리스트" in result.message


# ============================================================================
# 입력 검증 · 빈 목록 · 예외 전파
# ============================================================================

def test_empty_file_list_makes_no_changelist():
    """빈 목록은 기존 메서드가 CL을 만들지 않고 `changelist=None`을 돌려주며, 그대로 실패 보고한다."""
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      return_value=_move_result(False, inChangelist=None, inMoved=0)), \
         patch.object(Perforce, "submit_change_list") as mockSubmit:
        result = p4wrap.collect_opened_files_into_change_list(_DESCRIPTION, [], inShouldSubmit=True)

    mockSubmit.assert_not_called()
    assert result.succeeded is False
    assert result.changelist is None
    assert result.movedCount == 0
    assert "비어" in result.message


@pytest.mark.parametrize("badDescription", ["", "   ", None])
def test_empty_description_is_rejected_before_touching_p4(badDescription):
    """빈 description은 P4를 건드리기 전에 ValueError다 (이름 없는 CL은 검수 불가)."""
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list") as mockMove:
        with pytest.raises(ValueError):
            p4wrap.collect_opened_files_into_change_list(badDescription, [_LOCAL_A])

    mockMove.assert_not_called()


def test_move_p4exception_propagates():
    """이동 중 P4Exception은 삼키지 않고 전파한다 (롤백은 기존 메서드가 이미 마쳤다)."""
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      side_effect=P4Exception("reopen failed")):
        with pytest.raises(P4Exception):
            p4wrap.collect_opened_files_into_change_list(_DESCRIPTION, [_LOCAL_A])


def test_submit_p4exception_propagates():
    """서밋 중 P4Exception도 전파한다 - CL은 pending으로 남아 있어 호출자가 구분 보고한다."""
    p4wrap = _make_wrap()

    with patch.object(Perforce, "move_opened_files_to_new_change_list",
                      return_value=_move_result(True)), \
         patch.object(Perforce, "submit_change_list",
                      side_effect=P4Exception("submit failed")):
        with pytest.raises(P4Exception):
            p4wrap.collect_opened_files_into_change_list(
                _DESCRIPTION, [_LOCAL_A, _LOCAL_B], inShouldSubmit=True
            )


def test_existing_move_method_is_untouched_by_new_method():
    """신규 메서드 추가가 기존 메서드의 시그니처를 바꾸지 않았다 (호환 유지 → fan-out 아님)."""
    import inspect

    params = list(inspect.signature(Perforce.move_opened_files_to_new_change_list).parameters)
    assert params == ["self", "inDescription", "inFilePaths"]

    submitParams = list(inspect.signature(Perforce.submit_change_list).parameters)
    assert submitParams == ["self", "change_list_number", "auto_revert_unchanged"]
