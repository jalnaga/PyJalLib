#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
진행 상황 표시 창 모듈

작업 진행 단계를 시각적으로 표시하는 모달리스 QDialog입니다.
익스포트/임포트/검증 등 다단계 작업의 진행 상태를 사용자에게 피드백합니다.
"""

from typing import List

from PySide2 import QtWidgets, QtCore

try:
    from pymxs import runtime as rt

    HAS_PYMXS = True
except ImportError:
    HAS_PYMXS = False


class ProgressWindow(QtWidgets.QDialog):
    """진행 상황 표시 창

    다단계 작업의 진행 상태를 단계별로 표시합니다.
    각 단계는 대기/진행중/완료/실패/생략 상태를 가집니다.
    WA_DeleteOnClose 사용 금지 (pymxs_pitfalls_advanced 섹션 11 참조).
    """

    # 상태별 스타일 상수
    _STYLE_WAITING = "color: #888888;"
    _STYLE_RUNNING = "color: #2196F3; font-weight: bold;"
    _STYLE_COMPLETE = "color: #4CAF50;"
    _STYLE_FAILED = "color: #F44336;"
    _STYLE_SKIPPED = "color: #666666; font-style: italic;"

    # 상태별 아이콘 텍스트
    _ICON_WAITING = "  "
    _ICON_RUNNING = ">>>"
    _ICON_COMPLETE = " V "
    _ICON_FAILED = " X "
    _ICON_SKIPPED = " - "

    # 생략 단계임을 라벨에 명시하는 접미사.
    # 대기(회색)와 생략(회색)은 색만으로 구분되지 않으므로, 텍스트로 못을 박아
    # 건너뛴 단계가 "멈춘 것처럼" 보이지 않게 한다.
    _SUFFIX_SKIPPED = " (생략)"

    def __init__(self, inSteps: List[str], parent=None):
        """ProgressWindow 초기화

        Args:
            inSteps: 단계 목록 (예: ["P4 동기화", "MAX 파일 저장", ...])
            parent: 부모 위젯. None이면 3ds Max HWND 기반 위젯 사용.
        """
        # 부모가 없으면 3ds Max 윈도우를 부모로 설정
        if parent is None and HAS_PYMXS:
            try:
                parent = QtWidgets.QWidget.find(rt.windows.getMAXHWND())
            except Exception:
                pass

        super(ProgressWindow, self).__init__(parent)

        self._steps = list(inSteps)
        self._stepLabels: List[QtWidgets.QLabel] = []
        self._iconLabels: List[QtWidgets.QLabel] = []

        self._init_window_flags()
        self._init_ui()

    def _init_window_flags(self):
        """윈도우 플래그 설정

        최상위 윈도우, 닫기 버튼 없음, 모달리스 설정.
        WA_DeleteOnClose 사용 금지.
        """
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setWindowTitle("진행 상황")
        self.setMinimumWidth(300)

    def _init_ui(self):
        """UI 레이아웃 구성

        각 단계별 QHBoxLayout (상태 아이콘 QLabel + 단계명 QLabel)을 생성합니다.
        """
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(12, 12, 12, 12)
        mainLayout.setSpacing(6)

        for stepText in self._steps:
            stepLayout = QtWidgets.QHBoxLayout()
            stepLayout.setSpacing(8)

            # 상태 아이콘 라벨
            iconLabel = QtWidgets.QLabel(self._ICON_WAITING)
            iconLabel.setFixedWidth(30)
            iconLabel.setAlignment(QtCore.Qt.AlignCenter)
            iconLabel.setStyleSheet(self._STYLE_WAITING)
            stepLayout.addWidget(iconLabel)
            self._iconLabels.append(iconLabel)

            # 단계명 라벨
            stepLabel = QtWidgets.QLabel(stepText)
            stepLabel.setStyleSheet(self._STYLE_WAITING)
            stepLayout.addWidget(stepLabel, stretch=1)
            self._stepLabels.append(stepLabel)

            mainLayout.addLayout(stepLayout)

    def start_step(self, inIndex: int):
        """해당 단계를 '진행중' 스타일로 변경합니다.

        Args:
            inIndex: 단계 인덱스 (0부터 시작)
        """
        if not self._is_valid_index(inIndex):
            return

        self._iconLabels[inIndex].setText(self._ICON_RUNNING)
        self._iconLabels[inIndex].setStyleSheet(self._STYLE_RUNNING)
        self._stepLabels[inIndex].setStyleSheet(self._STYLE_RUNNING)
        QtWidgets.QApplication.processEvents()

    def complete_step(self, inIndex: int):
        """해당 단계를 '완료' 스타일로 변경합니다.

        Args:
            inIndex: 단계 인덱스 (0부터 시작)
        """
        if not self._is_valid_index(inIndex):
            return

        self._iconLabels[inIndex].setText(self._ICON_COMPLETE)
        self._iconLabels[inIndex].setStyleSheet(self._STYLE_COMPLETE)
        self._stepLabels[inIndex].setStyleSheet(self._STYLE_COMPLETE)
        QtWidgets.QApplication.processEvents()

    def fail_step(self, inIndex: int):
        """해당 단계를 '실패' 스타일로 변경합니다.

        Args:
            inIndex: 단계 인덱스 (0부터 시작)
        """
        if not self._is_valid_index(inIndex):
            return

        self._iconLabels[inIndex].setText(self._ICON_FAILED)
        self._iconLabels[inIndex].setStyleSheet(self._STYLE_FAILED)
        self._stepLabels[inIndex].setStyleSheet(self._STYLE_FAILED)
        QtWidgets.QApplication.processEvents()

    def skip_step(self, inIndex: int):
        """해당 단계를 '생략' 스타일로 변경합니다.

        조건에 따라 수행하지 않은 단계에 사용합니다(예: 경량 모드의 엔진 임포트,
        제출 모드의 미선택 파일 정리). 대기 상태로 남겨두면 작업이 멈춘 것처럼
        보이므로, 아이콘과 접미사로 건너뛰었음을 명시합니다.

        Args:
            inIndex: 단계 인덱스 (0부터 시작)
        """
        if not self._is_valid_index(inIndex):
            return

        self._iconLabels[inIndex].setText(self._ICON_SKIPPED)
        self._iconLabels[inIndex].setStyleSheet(self._STYLE_SKIPPED)

        # 접미사 중복 부착 방지 (같은 단계에 skip_step이 두 번 와도 안전)
        currentText = self._stepLabels[inIndex].text()
        if not currentText.endswith(self._SUFFIX_SKIPPED):
            self._stepLabels[inIndex].setText(currentText + self._SUFFIX_SKIPPED)
        self._stepLabels[inIndex].setStyleSheet(self._STYLE_SKIPPED)
        QtWidgets.QApplication.processEvents()

    def show_progress(self):
        """모달리스로 진행 상황 창을 표시합니다."""
        self.show()
        QtWidgets.QApplication.processEvents()

    def close_progress(self):
        """진행 상황 창을 안전하게 닫습니다."""
        self.close()

    def update_step_text(self, inIndex: int, inText: str):
        """단계 텍스트를 동적으로 변경합니다.

        Args:
            inIndex: 단계 인덱스 (0부터 시작)
            inText: 새 텍스트 (예: "FBX 익스포트 (2/5)")
        """
        if not self._is_valid_index(inIndex):
            return

        self._stepLabels[inIndex].setText(inText)
        QtWidgets.QApplication.processEvents()

    def _is_valid_index(self, inIndex: int) -> bool:
        """인덱스 유효성 검증

        Args:
            inIndex: 검증할 인덱스

        Returns:
            유효하면 True, 아니면 False
        """
        return 0 <= inIndex < len(self._steps)
