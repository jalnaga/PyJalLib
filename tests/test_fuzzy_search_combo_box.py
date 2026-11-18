# -*- coding: utf-8 -*-
"""FuzzySearchComboBox 클래스 API 및 시그널 테스트."""

import pytest
from PySide2 import QtWidgets
from pyjallib.max.ui.fuzzySearchComboBox import FuzzySearchComboBox


@pytest.fixture(scope="session")
def qapp():
    """세션 범위 QApplication 인스턴스. 이미 존재하면 재사용한다."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def combo(qapp):
    """각 테스트마다 새 FuzzySearchComboBox 인스턴스를 반환한다."""
    return FuzzySearchComboBox()


# =============================================================================
# API 테스트
# =============================================================================


def test_add_item_increases_count(combo):
    """addItem 호출 후 count가 증가한다."""
    assert combo.count() == 0
    combo.addItem("KimDokja")
    assert combo.count() == 1
    combo.addItem("YooJoonghyuk")
    assert combo.count() == 2


def test_first_add_item_auto_selects(combo):
    """첫 addItem 후 해당 텍스트가 자동 선택된다."""
    combo.addItem("KimDokja")
    assert combo.currentText() == "KimDokja"


def test_find_text_success(combo):
    """findText가 존재하는 텍스트의 인덱스를 반환한다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")
    assert combo.findText("YooJoonghyuk") == 1


def test_find_text_failure(combo):
    """findText가 존재하지 않는 텍스트에 대해 -1을 반환한다."""
    combo.addItem("KimDokja")
    assert combo.findText("HanSooyoung") == -1


def test_set_current_index_updates_text(combo):
    """setCurrentIndex 후 currentText가 해당 인덱스의 텍스트로 변경된다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")
    combo.addItem("HanSooyoung")

    combo.setCurrentIndex(2)
    assert combo.currentText() == "HanSooyoung"


def test_set_current_index_out_of_range_ignored(combo):
    """setCurrentIndex에 범위 밖 값을 전달하면 무시된다."""
    combo.addItem("KimDokja")
    # 첫 항목 자동 선택 상태에서 범위 밖 인덱스 시도
    combo.setCurrentIndex(99)
    assert combo.currentText() == "KimDokja"

    combo.setCurrentIndex(-1)
    assert combo.currentText() == "KimDokja"


def test_clear_resets_state(combo):
    """clear 후 count == 0, currentText == "" 가 된다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")

    combo.clear()
    assert combo.count() == 0
    assert combo.currentText() == ""


# =============================================================================
# 시그널 테스트
# =============================================================================


def test_set_current_index_emits_signal(combo):
    """setCurrentIndex 시 currentIndexChanged 시그널이 발생한다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")
    # 첫 항목이 이미 index 0으로 선택됨 -> index 1로 변경
    received = []
    combo.currentIndexChanged.connect(lambda idx: received.append(idx))

    combo.setCurrentIndex(1)
    assert received == [1]


def test_set_current_index_same_index_no_signal(combo):
    """setCurrentIndex에 동일 인덱스를 전달하면 시그널이 발생하지 않는다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")
    combo.setCurrentIndex(1)  # index 1로 먼저 변경

    received = []
    combo.currentIndexChanged.connect(lambda idx: received.append(idx))

    combo.setCurrentIndex(1)  # 동일 인덱스 재설정
    assert received == []


def test_block_signals_suppresses_signal(combo):
    """blockSignals(True) 시 시그널이 발생하지 않는다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")

    received = []
    combo.currentIndexChanged.connect(lambda idx: received.append(idx))

    combo.blockSignals(True)
    combo.setCurrentIndex(1)
    combo.blockSignals(False)

    assert received == []


def test_set_current_index_after_clear_no_signal(combo):
    """clear 후 setCurrentIndex를 호출해도 범위 밖이므로 시그널이 발생하지 않는다."""
    combo.addItem("KimDokja")
    combo.addItem("YooJoonghyuk")
    combo.clear()

    received = []
    combo.currentIndexChanged.connect(lambda idx: received.append(idx))

    combo.setCurrentIndex(0)  # clear 후 항목 없음 -> 범위 밖 -> 무시
    assert received == []
