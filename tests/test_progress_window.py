# -*- coding: utf-8 -*-
"""ProgressWindow 위젯 테스트.

다단계 진행 상황 표시 모달리스 QDialog의 생성, 상태 전이
(start/complete/fail/skip), 텍스트 변경, 인덱스 가드를 검증한다.

테스트 유형: Type A (Console, pytest)
실행: uv run pytest tests/test_progress_window.py -v

검증 항목:
    TC01: 생성 - 단계 수에 맞게 라벨 초기화
    TC02: 초기 상태 - 모든 단계가 WAITING
    TC03: start_step() - 진행중 스타일
    TC04: complete_step() - 완료 스타일
    TC05: fail_step() - 실패 스타일
    TC06: update_step_text() - 단계 텍스트 변경
    TC07: show_progress() / close_progress() - 표시 상태
    TC08: 범위 초과 인덱스 - 예외 없이 무시
    TC09: 상태 전이 start -> complete
    TC10: 상태 전이 start -> fail
    TC11: skip_step() - 생략 스타일/아이콘/접미사
    TC12: 상태 전이 start -> skip
    TC13: skip_step() 범위 초과 및 중복 호출 가드
"""

import pytest
from PySide2 import QtWidgets

from pyjallib.max.ui.progressWindow import ProgressWindow


@pytest.fixture(scope="session")
def qapp():
    """세션 범위 QApplication 인스턴스. 이미 존재하면 재사용한다."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def win(qapp):
    """기본 3단계 ProgressWindow 인스턴스를 반환한다."""
    return ProgressWindow(["P4 동기화", "MAX 파일 저장", "텍스쳐 추출"], parent=None)


def _make_window(inSteps):
    """지정한 단계 목록으로 ProgressWindow를 생성한다.

    Args:
        inSteps: 단계 목록

    Returns:
        ProgressWindow 인스턴스
    """
    return ProgressWindow(inSteps, parent=None)


# =============================================================================
# TC01: 생성 - 단계 수에 맞게 라벨 초기화
# =============================================================================


def test_step_label_count_matches_input(qapp):
    """단계 수만큼 _stepLabels와 _iconLabels가 생성된다."""
    window = _make_window(["단계1", "단계2", "단계3", "단계4"])

    assert len(window._stepLabels) == 4
    assert len(window._iconLabels) == 4


def test_single_step(qapp):
    """단일 단계도 정상 생성된다."""
    window = _make_window(["단일 단계"])

    assert len(window._stepLabels) == 1
    assert len(window._iconLabels) == 1


def test_empty_steps(qapp):
    """빈 단계 목록도 예외 없이 생성된다."""
    window = _make_window([])

    assert len(window._stepLabels) == 0
    assert len(window._iconLabels) == 0


# =============================================================================
# TC02: 초기 상태 - 모든 단계가 WAITING
# =============================================================================


def test_initial_icon_text_is_waiting(win):
    """초기 아이콘 텍스트는 _ICON_WAITING이다."""
    for iconLabel in win._iconLabels:
        assert iconLabel.text() == ProgressWindow._ICON_WAITING


def test_initial_style_is_waiting(win):
    """초기 스타일은 _STYLE_WAITING이다."""
    for iconLabel in win._iconLabels:
        assert iconLabel.styleSheet() == ProgressWindow._STYLE_WAITING

    for stepLabel in win._stepLabels:
        assert stepLabel.styleSheet() == ProgressWindow._STYLE_WAITING


def test_initial_step_text_matches_input(qapp):
    """초기 단계 텍스트는 입력 단계 목록과 일치한다."""
    steps = ["P4 동기화", "MAX 파일 저장", "텍스쳐 추출"]
    window = _make_window(steps)

    for i, stepLabel in enumerate(window._stepLabels):
        assert stepLabel.text() == steps[i]


# =============================================================================
# TC03: start_step() - 진행중 스타일
# =============================================================================


def test_start_step_changes_icon_text(win):
    """start_step() 후 아이콘 텍스트가 _ICON_RUNNING으로 바뀐다."""
    win.start_step(0)

    assert win._iconLabels[0].text() == ProgressWindow._ICON_RUNNING


def test_start_step_changes_styles(win):
    """start_step() 후 아이콘·라벨 스타일이 _STYLE_RUNNING으로 바뀐다."""
    win.start_step(1)

    assert win._iconLabels[1].styleSheet() == ProgressWindow._STYLE_RUNNING
    assert win._stepLabels[1].styleSheet() == ProgressWindow._STYLE_RUNNING


def test_start_step_does_not_affect_other_steps(win):
    """start_step(0)은 다른 단계의 WAITING 상태를 유지한다."""
    win.start_step(0)

    assert win._iconLabels[1].styleSheet() == ProgressWindow._STYLE_WAITING
    assert win._iconLabels[2].styleSheet() == ProgressWindow._STYLE_WAITING


# =============================================================================
# TC04: complete_step() - 완료 스타일
# =============================================================================


def test_complete_step_changes_icon_text(win):
    """complete_step() 후 아이콘 텍스트가 _ICON_COMPLETE로 바뀐다."""
    win.complete_step(0)

    assert win._iconLabels[0].text() == ProgressWindow._ICON_COMPLETE


def test_complete_step_changes_styles(win):
    """complete_step() 후 아이콘·라벨 스타일이 _STYLE_COMPLETE로 바뀐다."""
    win.complete_step(0)

    assert win._iconLabels[0].styleSheet() == ProgressWindow._STYLE_COMPLETE
    assert win._stepLabels[0].styleSheet() == ProgressWindow._STYLE_COMPLETE


# =============================================================================
# TC05: fail_step() - 실패 스타일
# =============================================================================


def test_fail_step_changes_icon_text(win):
    """fail_step() 후 아이콘 텍스트가 _ICON_FAILED로 바뀐다."""
    win.fail_step(1)

    assert win._iconLabels[1].text() == ProgressWindow._ICON_FAILED


def test_fail_step_changes_styles(win):
    """fail_step() 후 아이콘·라벨 스타일이 _STYLE_FAILED로 바뀐다."""
    win.fail_step(1)

    assert win._iconLabels[1].styleSheet() == ProgressWindow._STYLE_FAILED
    assert win._stepLabels[1].styleSheet() == ProgressWindow._STYLE_FAILED


# =============================================================================
# TC06: update_step_text() - 단계 텍스트 변경
# =============================================================================


def test_update_step_text_changes_label(win):
    """update_step_text() 후 단계 라벨 텍스트가 바뀐다."""
    win.update_step_text(0, "FBX 익스포트 (2/5)")

    assert win._stepLabels[0].text() == "FBX 익스포트 (2/5)"


def test_update_step_text_does_not_change_other_labels(win):
    """한 단계의 텍스트 변경은 다른 단계에 영향을 주지 않는다."""
    win.update_step_text(1, "새 텍스트")

    assert win._stepLabels[0].text() == "P4 동기화"
    assert win._stepLabels[2].text() == "텍스쳐 추출"


# =============================================================================
# TC07: show_progress() / close_progress() - 표시 상태
# =============================================================================


def test_show_progress_makes_window_visible(win):
    """show_progress() 후 창이 보이는 상태가 된다."""
    win.show_progress()

    assert win.isVisible() is True


def test_close_progress_hides_window(win):
    """close_progress() 후 창이 숨겨진다."""
    win.show_progress()
    win.close_progress()

    assert win.isVisible() is False


# =============================================================================
# TC08: 범위 초과 인덱스 - 예외 없이 무시
# =============================================================================


@pytest.mark.parametrize("inIndex", [-1, -5, 3, 99])
def test_out_of_range_index_ignored(win, inIndex):
    """범위 밖 인덱스는 모든 상태 변경 메서드에서 예외 없이 무시된다."""
    win.start_step(inIndex)
    win.complete_step(inIndex)
    win.fail_step(inIndex)
    win.update_step_text(inIndex, "텍스트")

    # 유효 단계들은 초기 상태를 유지해야 한다
    for iconLabel in win._iconLabels:
        assert iconLabel.styleSheet() == ProgressWindow._STYLE_WAITING


# =============================================================================
# TC09: 상태 전이 start -> complete
# =============================================================================


def test_start_then_complete_overrides_style(win):
    """start_step() 후 complete_step()이 스타일을 COMPLETE로 교체한다."""
    win.start_step(0)
    assert win._iconLabels[0].styleSheet() == ProgressWindow._STYLE_RUNNING

    win.complete_step(0)
    assert win._iconLabels[0].text() == ProgressWindow._ICON_COMPLETE
    assert win._iconLabels[0].styleSheet() == ProgressWindow._STYLE_COMPLETE
    assert win._stepLabels[0].styleSheet() == ProgressWindow._STYLE_COMPLETE


# =============================================================================
# TC10: 상태 전이 start -> fail
# =============================================================================


def test_start_then_fail_overrides_style(win):
    """start_step() 후 fail_step()이 스타일을 FAILED로 교체한다."""
    win.start_step(2)
    assert win._iconLabels[2].styleSheet() == ProgressWindow._STYLE_RUNNING

    win.fail_step(2)
    assert win._iconLabels[2].text() == ProgressWindow._ICON_FAILED
    assert win._iconLabels[2].styleSheet() == ProgressWindow._STYLE_FAILED
    assert win._stepLabels[2].styleSheet() == ProgressWindow._STYLE_FAILED


# =============================================================================
# TC11: skip_step() - 생략 스타일/아이콘/접미사
# =============================================================================


def test_skip_step_changes_icon_text(win):
    """skip_step() 후 아이콘 텍스트가 _ICON_SKIPPED로 바뀐다."""
    win.skip_step(1)

    assert win._iconLabels[1].text() == ProgressWindow._ICON_SKIPPED


def test_skip_step_changes_styles(win):
    """skip_step() 후 아이콘·라벨 스타일이 _STYLE_SKIPPED로 바뀐다."""
    win.skip_step(1)

    assert win._iconLabels[1].styleSheet() == ProgressWindow._STYLE_SKIPPED
    assert win._stepLabels[1].styleSheet() == ProgressWindow._STYLE_SKIPPED


def test_skip_step_appends_suffix(win):
    """skip_step() 후 라벨 텍스트에 생략 접미사가 붙는다.

    대기(회색)와 생략(회색)은 색만으로 구분되지 않으므로 텍스트로 구분한다.
    """
    win.skip_step(1)

    assert win._stepLabels[1].text() == "MAX 파일 저장" + ProgressWindow._SUFFIX_SKIPPED


def test_skip_step_does_not_affect_other_steps(win):
    """skip_step(1)은 다른 단계의 텍스트·상태를 바꾸지 않는다."""
    win.skip_step(1)

    assert win._stepLabels[0].text() == "P4 동기화"
    assert win._stepLabels[2].text() == "텍스쳐 추출"
    assert win._iconLabels[0].styleSheet() == ProgressWindow._STYLE_WAITING
    assert win._iconLabels[2].styleSheet() == ProgressWindow._STYLE_WAITING


# =============================================================================
# TC12: 상태 전이 start -> skip
# =============================================================================


def test_start_then_skip_overrides_style(win):
    """start_step() 후 skip_step()이 RUNNING 스타일을 SKIPPED로 교체한다."""
    win.start_step(0)
    assert win._iconLabels[0].styleSheet() == ProgressWindow._STYLE_RUNNING

    win.skip_step(0)
    assert win._iconLabels[0].text() == ProgressWindow._ICON_SKIPPED
    assert win._iconLabels[0].styleSheet() == ProgressWindow._STYLE_SKIPPED
    assert win._stepLabels[0].styleSheet() == ProgressWindow._STYLE_SKIPPED


# =============================================================================
# TC13: skip_step() 범위 초과 및 중복 호출 가드
# =============================================================================


@pytest.mark.parametrize("inIndex", [-1, 3, 99])
def test_skip_step_out_of_range_ignored(win, inIndex):
    """skip_step()도 범위 밖 인덱스를 예외 없이 무시한다."""
    win.skip_step(inIndex)

    for stepLabel in win._stepLabels:
        assert not stepLabel.text().endswith(ProgressWindow._SUFFIX_SKIPPED)


def test_skip_step_twice_does_not_duplicate_suffix(win):
    """skip_step()을 같은 단계에 두 번 호출해도 접미사가 중복되지 않는다."""
    win.skip_step(2)
    win.skip_step(2)

    assert win._stepLabels[2].text() == "텍스쳐 추출" + ProgressWindow._SUFFIX_SKIPPED
