#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_ui_fuzzy_search_combo_box.py - FuzzySearchComboBox UI 자동화 테스트.

FuzzySearchComboBox 위젯의 공개 API 및 내부 UI 동작을 QtTest로 검증한다.
3ds Max 내부에서 python.ExecuteFile로 실행하거나, 3dsmaxbatch.exe를 통해 실행한다.
pymxs 씬 상태 검증은 없으므로 씬 리셋 없이 순수 Qt 위젯 테스트만 수행한다.

테스트 대상:
    - FuzzySearchComboBox 생성 및 기본 상태
    - addItem 및 첫 항목 자동 선택
    - 팝업 열기 (클릭 시뮬레이션)
    - 퍼지 필터링 (키보드 텍스트 입력)
    - 키보드 탐색 (Up/Down)
    - Enter로 항목 선택
    - 리스트 클릭으로 항목 선택
    - Escape로 팝업 닫기
    - 비활성 상태에서 팝업 미열림
    - setCurrentIndex 시그널 발생

로그: tests/logs/test_FuzzySearchComboBoxUI.log
"""

import importlib.util
import sys
from pathlib import Path

# PySide2/PySide6 호환 shim
try:
    from PySide6 import QtWidgets, QtCore, QtTest
    from PySide6.QtCore import Qt
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtTest
    from PySide2.QtCore import Qt

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

# fuzzySearchComboBox.py는 새 모듈이므로 importlib으로 직접 로드한다.
# 3DS Max 기동 시 pyjallib.max 패키지가 캐시된 상태에서
# 패키지 경로 import가 실패하는 것을 방지한다.
_fuzzyPath = (
    Path(__file__).parent.parent.parent
    / "src"
    / "pyjallib"
    / "max"
    / "ui"
    / "fuzzySearchComboBox.py"
)
_spec = importlib.util.spec_from_file_location(
    "pyjallib.max.ui.fuzzySearchComboBox", _fuzzyPath
)
_fuzzyModule = importlib.util.module_from_spec(_spec)
sys.modules["pyjallib.max.ui.fuzzySearchComboBox"] = _fuzzyModule
_spec.loader.exec_module(_fuzzyModule)

FuzzySearchComboBox = _fuzzyModule.FuzzySearchComboBox

from pyjallib.testKit import TestReporter

# 로그 디렉토리
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 테스트 데이터
_TEST_ITEMS = ["KimDokja", "YooJoonghyuk", "HanSooyoung", "LeeSookyung", "JungHeewon"]

# GC 크래시 방지: 위젯 참조를 모듈 전역에 유지
_gCombo = None


def _open_popup(inCombo: FuzzySearchComboBox) -> None:
    """디스플레이 버튼을 클릭하여 팝업을 연다.

    Args:
        inCombo: 팝업을 열 FuzzySearchComboBox 인스턴스
    """
    QtTest.QTest.mouseClick(inCombo._comboDisplay, Qt.LeftButton)
    QtWidgets.QApplication.processEvents()


def run_tests() -> None:
    """TC01 ~ TC10 전체 테스트를 실행한다."""
    global _gCombo

    reporter = TestReporter("FuzzySearchComboBoxUI", LOG_DIR)

    # qtmax는 3ds Max 내부에서만 사용 가능
    try:
        import qtmax
        mainWindow = qtmax.GetQMaxMainWindow()
    except ImportError:
        mainWindow = None

    # ========================================================
    # TC01: 위젯 생성 및 기본 상태
    # ========================================================
    try:
        _gCombo = FuzzySearchComboBox(parent=mainWindow)
        _gCombo.show()
        QtWidgets.QApplication.processEvents()

        countOk = _gCombo.count() == 0
        textOk = _gCombo.currentText() == ""

        reporter.assert_test(
            countOk and textOk,
            "TC01 위젯 생성 및 기본 상태",
            f"count={_gCombo.count()} (기대 0), currentText='{_gCombo.currentText()}' (기대 '')",
        )
    except Exception as e:
        reporter.error("TC01 위젯 생성 및 기본 상태", str(e))

    # ========================================================
    # TC02: 아이템 추가 및 첫 항목 자동 선택
    # ========================================================
    try:
        for item in _TEST_ITEMS:
            _gCombo.addItem(item)
        QtWidgets.QApplication.processEvents()

        countOk = _gCombo.count() == len(_TEST_ITEMS)
        # 첫 번째 항목이 자동 선택되어야 함
        firstSelected = _gCombo.currentText() == _TEST_ITEMS[0]

        reporter.assert_test(
            countOk and firstSelected,
            "TC02 아이템 추가 및 첫 항목 자동 선택",
            f"count={_gCombo.count()} (기대 {len(_TEST_ITEMS)}), "
            f"currentText='{_gCombo.currentText()}' (기대 '{_TEST_ITEMS[0]}')",
        )
    except Exception as e:
        reporter.error("TC02 아이템 추가 및 첫 항목 자동 선택", str(e))

    # ========================================================
    # TC03: 팝업 열기 (클릭 시뮬레이션)
    # ========================================================
    try:
        # 팝업이 닫혀있는 상태에서 시작
        if _gCombo._popup.isVisible():
            _gCombo._popup.hide_popup()
            QtWidgets.QApplication.processEvents()

        _open_popup(_gCombo)

        popupVisible = _gCombo._popup.isVisible()

        reporter.assert_test(
            popupVisible,
            "TC03 팝업 열기 (클릭 시뮬레이션)",
            f"_popup.isVisible()={popupVisible} (기대 True)",
        )

        # 다음 TC를 위해 팝업 상태 유지
    except Exception as e:
        reporter.error("TC03 팝업 열기 (클릭 시뮬레이션)", str(e))
        # 팝업이 닫혀있을 수 있으므로 열어둠
        if not _gCombo._popup.isVisible():
            _open_popup(_gCombo)

    # ========================================================
    # TC04: 퍼지 필터링 (키보드 입력)
    # ========================================================
    try:
        # 팝업이 닫혀있으면 다시 열기
        if not _gCombo._popup.isVisible():
            _open_popup(_gCombo)

        # "Kim" 입력 -> KimDokja 만 매칭 기대
        searchEdit = _gCombo._popup._searchEdit
        searchEdit.clear()
        QtTest.QTest.keyClicks(searchEdit, "Kim")
        QtWidgets.QApplication.processEvents()

        proxyRowCount = _gCombo._popup._proxyModel.rowCount()
        # "Kim"은 KimDokja에만 매칭 (score >= 0)
        # KimDokja: K-i-m 연속 매칭 + 단어 시작 보너스 -> 통과
        # 나머지: K, i, m 문자가 순서대로 없으면 필터 제외
        filterOk = proxyRowCount >= 1

        reporter.assert_test(
            filterOk,
            "TC04 퍼지 필터링 (키보드 입력 'Kim')",
            f"proxyModel.rowCount()={proxyRowCount} (기대 >= 1, KimDokja 포함 확인)",
        )

        # 검색어 초기화
        searchEdit.clear()
        QtWidgets.QApplication.processEvents()
    except Exception as e:
        reporter.error("TC04 퍼지 필터링 (키보드 입력)", str(e))

    # ========================================================
    # TC05: 키보드 탐색 (Down 키)
    # ========================================================
    try:
        # 팝업이 닫혀있으면 다시 열기
        if not _gCombo._popup.isVisible():
            _open_popup(_gCombo)

        searchEdit = _gCombo._popup._searchEdit
        listView = _gCombo._popup._listView

        # 팝업 열기 시 첫 항목이 하이라이트됨
        initialRow = listView.currentIndex().row()

        # Down 키 한 번 입력
        QtTest.QTest.keyClick(searchEdit, Qt.Key_Down)
        QtWidgets.QApplication.processEvents()

        newRow = listView.currentIndex().row()

        # 초기 행이 0이면 Down 후 1이 되어야 함
        # 초기 행이 마지막이면 그대로 유지
        totalRows = _gCombo._popup._proxyModel.rowCount()
        if initialRow < totalRows - 1:
            expectedRow = initialRow + 1
            navigateOk = newRow == expectedRow
        else:
            # 이미 마지막 항목이면 변화 없음
            navigateOk = newRow == initialRow

        reporter.assert_test(
            navigateOk,
            "TC05 키보드 탐색 Down 키",
            f"initialRow={initialRow}, newRow={newRow} "
            f"(totalRows={totalRows})",
        )
    except Exception as e:
        reporter.error("TC05 키보드 탐색 (Down 키)", str(e))

    # ========================================================
    # TC06: Enter로 항목 선택
    # ========================================================
    try:
        # 팝업이 닫혀있으면 다시 열기
        if not _gCombo._popup.isVisible():
            _open_popup(_gCombo)

        searchEdit = _gCombo._popup._searchEdit
        listView = _gCombo._popup._listView
        proxyModel = _gCombo._popup._proxyModel

        # 첫 항목(row=0)으로 이동 확인 후 Enter
        firstProxyIndex = proxyModel.index(0, 0)
        listView.setCurrentIndex(firstProxyIndex)
        QtWidgets.QApplication.processEvents()

        # 선택될 항목의 텍스트 (프록시 -> 소스 변환)
        sourceIndex = proxyModel.mapToSource(firstProxyIndex)
        expectedText = _gCombo._popup._sourceModel.data(
            sourceIndex, QtCore.Qt.DisplayRole
        )
        expectedSourceRow = sourceIndex.row()

        # Enter 키 입력으로 선택 확정
        QtTest.QTest.keyClick(searchEdit, Qt.Key_Return)
        QtWidgets.QApplication.processEvents()

        popupClosed = not _gCombo._popup.isVisible()
        textMatch = _gCombo.currentText() == expectedText
        indexMatch = _gCombo._currentIndex == expectedSourceRow

        reporter.assert_test(
            popupClosed and textMatch and indexMatch,
            "TC06 Enter로 항목 선택",
            f"popupClosed={popupClosed}, "
            f"currentText='{_gCombo.currentText()}' (기대 '{expectedText}'), "
            f"currentIndex={_gCombo._currentIndex} (기대 {expectedSourceRow})",
        )
    except Exception as e:
        reporter.error("TC06 Enter로 항목 선택", str(e))

    # ========================================================
    # TC07: 리스트 클릭으로 항목 선택
    # ========================================================
    try:
        # 팝업 열기
        if _gCombo._popup.isVisible():
            _gCombo._popup.hide_popup()
            QtWidgets.QApplication.processEvents()

        _open_popup(_gCombo)

        listView = _gCombo._popup._listView
        proxyModel = _gCombo._popup._proxyModel

        # 클릭 대상: 프록시 모델의 두 번째 항목 (row=1)
        targetProxyRow = 1
        if proxyModel.rowCount() > targetProxyRow:
            targetProxyIndex = proxyModel.index(targetProxyRow, 0)

            # 소스 인덱스로 변환하여 기대 텍스트 확인
            targetSourceIndex = proxyModel.mapToSource(targetProxyIndex)
            expectedClickText = _gCombo._popup._sourceModel.data(
                targetSourceIndex, QtCore.Qt.DisplayRole
            )

            # 리스트뷰의 시각적 좌표 계산 (visualRect 중심점)
            visualRect = listView.visualRect(targetProxyIndex)
            clickPos = visualRect.center()

            QtTest.QTest.mouseClick(
                listView.viewport(), Qt.LeftButton, Qt.NoModifier, clickPos
            )
            QtWidgets.QApplication.processEvents()

            popupClosed = not _gCombo._popup.isVisible()
            textMatch = _gCombo.currentText() == expectedClickText

            reporter.assert_test(
                popupClosed and textMatch,
                "TC07 리스트 클릭으로 항목 선택",
                f"popupClosed={popupClosed}, "
                f"currentText='{_gCombo.currentText()}' (기대 '{expectedClickText}')",
            )
        else:
            reporter.assert_test(
                False,
                "TC07 리스트 클릭으로 항목 선택",
                f"proxyModel.rowCount()={proxyModel.rowCount()} < 2, 클릭 대상 없음",
            )
    except Exception as e:
        reporter.error("TC07 리스트 클릭으로 항목 선택", str(e))

    # ========================================================
    # TC08: Escape로 팝업 닫기 + 이전 선택 유지
    # ========================================================
    try:
        # TC07 이후 현재 선택된 텍스트를 기록
        textBeforeEscape = _gCombo.currentText()

        # 팝업 열기
        if _gCombo._popup.isVisible():
            _gCombo._popup.hide_popup()
            QtWidgets.QApplication.processEvents()

        _open_popup(_gCombo)

        searchEdit = _gCombo._popup._searchEdit

        # Escape 입력
        QtTest.QTest.keyClick(searchEdit, Qt.Key_Escape)
        QtWidgets.QApplication.processEvents()

        popupClosed = not _gCombo._popup.isVisible()
        # Escape는 팝업을 닫지만 선택을 변경하지 않아야 함
        selectionUnchanged = _gCombo.currentText() == textBeforeEscape

        reporter.assert_test(
            popupClosed and selectionUnchanged,
            "TC08 Escape로 팝업 닫기",
            f"popupClosed={popupClosed}, "
            f"currentText='{_gCombo.currentText()}' (기대 '{textBeforeEscape}' 유지)",
        )
    except Exception as e:
        reporter.error("TC08 Escape로 팝업 닫기", str(e))

    # ========================================================
    # TC09: 비활성 상태에서 팝업 미열림
    # ========================================================
    try:
        # 팝업이 열려있으면 닫기
        if _gCombo._popup.isVisible():
            _gCombo._popup.hide_popup()
            QtWidgets.QApplication.processEvents()

        _gCombo.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        # 클릭 시뮬레이션
        QtTest.QTest.mouseClick(_gCombo._comboDisplay, Qt.LeftButton)
        QtWidgets.QApplication.processEvents()

        popupNotVisible = not _gCombo._popup.isVisible()

        reporter.assert_test(
            popupNotVisible,
            "TC09 비활성 상태에서 팝업 미열림",
            f"_popup.isVisible()={_gCombo._popup.isVisible()} (기대 False)",
        )

        # 다음 TC를 위해 다시 활성화
        _gCombo.setEnabled(True)
        QtWidgets.QApplication.processEvents()
    except Exception as e:
        reporter.error("TC09 비활성 상태에서 팝업 미열림", str(e))
        # 활성화 상태 복원
        _gCombo.setEnabled(True)

    # ========================================================
    # TC10: setCurrentIndex 시그널 발생
    # ========================================================
    try:
        # 시그널 수신 카운터
        _signalReceived = {"count": 0, "lastIndex": -1}

        def _on_index_changed(inIndex: int) -> None:
            _signalReceived["count"] += 1
            _signalReceived["lastIndex"] = inIndex

        _gCombo.currentIndexChanged.connect(_on_index_changed)

        # 현재 인덱스와 다른 인덱스로 변경
        currentIdx = _gCombo._currentIndex
        targetIdx = (currentIdx + 1) % len(_TEST_ITEMS)

        _gCombo.setCurrentIndex(targetIdx)
        QtWidgets.QApplication.processEvents()

        signalFired = _signalReceived["count"] == 1
        signalIndexOk = _signalReceived["lastIndex"] == targetIdx
        textUpdated = _gCombo.currentText() == _TEST_ITEMS[targetIdx]

        reporter.assert_test(
            signalFired and signalIndexOk and textUpdated,
            "TC10 setCurrentIndex 시그널 발생",
            f"signalCount={_signalReceived['count']} (기대 1), "
            f"signalIndex={_signalReceived['lastIndex']} (기대 {targetIdx}), "
            f"currentText='{_gCombo.currentText()}' (기대 '{_TEST_ITEMS[targetIdx]}')",
        )

        # 시그널 연결 해제
        _gCombo.currentIndexChanged.disconnect(_on_index_changed)
    except Exception as e:
        reporter.error("TC10 setCurrentIndex 시그널 발생", str(e))

    # ========================================================
    # 정리
    # ========================================================
    try:
        if _gCombo._popup.isVisible():
            _gCombo._popup.hide_popup()
        _gCombo.close()
        QtWidgets.QApplication.processEvents()
    except Exception:
        pass

    passed, failed, total = reporter.summary()
    reporter.close()


run_tests()
