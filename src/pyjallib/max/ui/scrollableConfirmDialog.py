#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""요약 + 스크롤 상세 + 예/아니오 확인 다이얼로그.

`QMessageBox.question`은 본문이 길어지면 창이 화면 밖으로 자라고 스크롤도 되지 않는다.
정리 대상이 수십 건인 경우가 실재하므로(프로덕션 실측 1씬 12슬롯, 씬당 누락 후보 최대
72건) **목록을 스크롤로 보여 주면서 예/아니오를 받는 창**이 따로 필요하다.

비가역 동작을 묻는 자리에 쓰인다. 그래서 **기본 버튼이 '아니오'**다 - 엔터를 잘못
눌러 지워지는 경로를 만들지 않는다.

**거부는 "건너뛰기"가 아니라 "중단"이다**(2026-09-29 마스터 지시 3차). 호출부는 False를
받으면 그 작업 전체를 멈춰야 한다. 그래서 기본 거부 라벨이 `취소 (중단)`이다 - 그냥
"취소"이면 사용자가 정리만 건너뛰는 것으로 읽는다.

.. code-block:: python

    from pyjallib.max.ui.scrollableConfirmDialog import show_scrollable_confirm

    if show_scrollable_confirm(self, "누락 애셋 정리", summary, detailText):
        service.apply_purge_plan(plan)
"""

from PySide2 import QtCore, QtWidgets


class ScrollableConfirmDialog(QtWidgets.QDialog):
    """요약 라벨 + 스크롤 상세 영역 + 예/아니오 버튼의 확인 다이얼로그."""

    def __init__(
        self,
        inTitle: str,
        inSummary: str,
        inDetailText: str,
        inYesLabel: str = "정리",
        inNoLabel: str = "취소 (중단)",
        parent=None,
    ):
        """ScrollableConfirmDialog 초기화.

        Args:
            inTitle: 창 제목
            inSummary: 상단 요약 문구(짧게 유지 - 상세는 스크롤 영역이 갖는다)
            inDetailText: 스크롤 영역에 표시할 전체 목록
            inYesLabel: 승인 버튼 문구. 기본값 "정리"
            inNoLabel: 거부 버튼 문구. 기본값 "취소 (중단)"
            parent: 부모 위젯
        """
        super(ScrollableConfirmDialog, self).__init__(parent)
        self.setWindowTitle(inTitle)
        # QDialog 기본 플래그가 켜는 타이틀바 "?" 버튼을 없앤다 - 연결된 도움말이
        # 없어 눌러도 아무 일이 일어나지 않는다.
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        mainLayout = QtWidgets.QVBoxLayout(self)

        headerLayout = QtWidgets.QHBoxLayout()
        iconLabel = QtWidgets.QLabel()
        try:
            # 위젯의 `self.style()`이 아니라 앱 레벨 스타일을 쓴다 - PySide2에서
            # 위젯 스타일은 이미 삭제된 C++ 래퍼일 수 있다.
            appStyle = QtWidgets.QApplication.style()
            if appStyle is not None:
                iconLabel.setPixmap(
                    appStyle.standardIcon(
                        QtWidgets.QStyle.SP_MessageBoxWarning
                    ).pixmap(32, 32)
                )
        except Exception:
            # 스타일 객체가 없는 환경(헤드레스 배치)에서는 아이콘을 생략한다.
            pass
        iconLabel.setFixedSize(36, 36)
        headerLayout.addWidget(iconLabel)

        summaryLabel = QtWidgets.QLabel(inSummary)
        summaryLabel.setWordWrap(True)
        headerLayout.addWidget(summaryLabel, 1)
        mainLayout.addLayout(headerLayout)

        self._detailEdit = QtWidgets.QPlainTextEdit()
        self._detailEdit.setPlainText(inDetailText)
        self._detailEdit.setReadOnly(True)
        self._detailEdit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        mainLayout.addWidget(self._detailEdit, 1)

        buttonBox = QtWidgets.QDialogButtonBox()
        self._yesButton = buttonBox.addButton(
            inYesLabel, QtWidgets.QDialogButtonBox.AcceptRole
        )
        self._noButton = buttonBox.addButton(
            inNoLabel, QtWidgets.QDialogButtonBox.RejectRole
        )
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(buttonBox)

        # **기본 버튼은 거부 쪽**이다. 이 창은 비가역 동작을 묻는 자리이므로
        # 엔터를 잘못 눌러 진행되는 경로를 만들지 않는다.
        self._noButton.setDefault(True)
        self._noButton.setAutoDefault(True)
        self._yesButton.setAutoDefault(False)

        self.setMinimumSize(480, 300)
        self.resize(640, 460)


def show_scrollable_confirm(
    inParent,
    inTitle: str,
    inSummary: str,
    inDetailText: str,
    inYesLabel: str = "정리",
    inNoLabel: str = "취소 (중단)",
) -> bool:
    """확인 다이얼로그를 모달로 띄우고 승인 여부를 돌려준다.

    Args:
        inParent: 부모 위젯
        inTitle: 창 제목
        inSummary: 상단 요약 문구
        inDetailText: 스크롤 영역 전체 목록
        inYesLabel: 승인 버튼 문구
        inNoLabel: 거부 버튼 문구

    Returns:
        승인하면 True, 거부하거나 창을 닫으면 False
    """
    dialog = ScrollableConfirmDialog(
        inTitle, inSummary, inDetailText, inYesLabel, inNoLabel, parent=inParent
    )
    return dialog.exec_() == QtWidgets.QDialog.Accepted
