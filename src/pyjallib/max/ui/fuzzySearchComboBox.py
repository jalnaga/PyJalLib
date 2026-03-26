# -*- coding: utf-8 -*-
"""
FuzzySearchComboBox - QWidget 기반 커스텀 퍼지 검색 콤보박스 위젯.

QComboBox를 상속하지 않고 QWidget 기반 커스텀 위젯 + Qt.Popup 플래그 팝업으로
퍼지 검색 콤보박스를 구현한다. 3ds Max 환경에서 QComboBox의 showPopup/hidePopup
연쇄 호출 문제를 회피하기 위한 설계이다.

아키텍처::

    FuzzySearchComboBox (QWidget) -- 공개 API, QComboBox 호환 인터페이스
      |-- _ComboDisplay (QPushButton) -- QStylePainter로 네이티브 콤보박스 외관 렌더링
      +-- _FuzzyPopup (QFrame, Qt.Popup) -- 팝업 윈도우
            |-- QLineEdit -- 검색 입력
            |-- QListView -- 필터링된 결과 표시
            +-- _FuzzyFilterProxyModel (QSortFilterProxyModel) + QStandardItemModel
"""

from PySide2 import QtWidgets, QtCore, QtGui


# =============================================================================
# Phase 1: 퍼지 매칭 알고리즘
# =============================================================================


def _fuzzy_score(inPattern: str, inText: str) -> int:
    """퍼지 매칭 스코어를 계산한다.

    패턴의 모든 문자가 텍스트에 순서대로 존재하면 매칭 성공.
    연속 매칭과 단어 시작점 매칭에 보너스를 부여한다.

    Args:
        inPattern: 검색 패턴 문자열
        inText: 매칭 대상 텍스트

    Returns:
        매칭 스코어. 매칭 실패 시 -1, 빈 패턴은 0.
    """
    if not inPattern:
        return 0

    patternLower = inPattern.lower()
    textLower = inText.lower()

    score = 0
    patternIdx = 0
    prevMatchIdx = -2  # -2로 초기화하여 첫 매칭에서 연속 보너스 방지

    for textIdx in range(len(textLower)):
        if patternIdx >= len(patternLower):
            break

        if textLower[textIdx] == patternLower[patternIdx]:
            # 기본 매칭 점수
            score += 1

            # 연속 매칭 보너스: 이전 매칭 위치 바로 다음에 매칭되면
            if textIdx == prevMatchIdx + 1:
                score += 6

            # 단어 시작점 보너스: 대문자이거나 _/- 바로 뒤 문자
            if _is_word_start(inText, textIdx):
                score += 10

            prevMatchIdx = textIdx
            patternIdx += 1

    # 패턴의 모든 문자가 매칭되지 않으면 실패
    if patternIdx < len(patternLower):
        return -1

    return score


def _is_word_start(inText: str, inIdx: int) -> bool:
    """해당 인덱스의 문자가 단어 시작점인지 판별한다.

    단어 시작점 조건:
    - 첫 번째 문자
    - 대문자이면서 이전 문자가 소문자인 경우 (camelCase 경계)
    - '_' 또는 '-' 바로 뒤의 문자

    Args:
        inText: 전체 텍스트
        inIdx: 판별 대상 인덱스

    Returns:
        단어 시작점이면 True
    """
    if inIdx == 0:
        return True

    currentChar = inText[inIdx]
    prevChar = inText[inIdx - 1]

    # 대문자이면서 이전 문자가 소문자 (camelCase 경계)
    if currentChar.isupper() and prevChar.islower():
        return True

    # '_' 또는 '-' 바로 뒤의 문자
    if prevChar in ("_", "-"):
        return True

    return False


# =============================================================================
# Phase 2: _FuzzyFilterProxyModel
# =============================================================================


class _FuzzyFilterProxyModel(QtCore.QSortFilterProxyModel):
    """퍼지 매칭 기반 필터 및 정렬 프록시 모델.

    QSortFilterProxyModel을 상속하여 _fuzzy_score 함수를 기반으로
    항목 필터링 및 스코어 정렬을 수행한다.
    """

    def __init__(self, inParent: QtCore.QObject = None):
        """초기화.

        Args:
            inParent: 부모 QObject
        """
        super().__init__(inParent)
        self._filterPattern: str = ""
        self._scoreCache: dict = {}
        self.setDynamicSortFilter(True)

    def set_filter_pattern(self, inPattern: str) -> None:
        """필터 패턴을 설정하고 필터를 갱신한다.

        Args:
            inPattern: 퍼지 검색 패턴
        """
        self._filterPattern = inPattern
        self._scoreCache.clear()
        self.invalidateFilter()
        if inPattern:
            self.sort(0, QtCore.Qt.DescendingOrder)
        else:
            self.sort(0, QtCore.Qt.AscendingOrder)

    def _get_score(self, inText: str) -> int:
        """텍스트의 스코어를 캐시에서 조회하거나 계산한다.

        Args:
            inText: 스코어 계산 대상 텍스트

        Returns:
            퍼지 매칭 스코어
        """
        if inText not in self._scoreCache:
            self._scoreCache[inText] = _fuzzy_score(self._filterPattern, inText)
        return self._scoreCache[inText]

    def filterAcceptsRow(
        self, inSourceRow: int, inSourceParent: QtCore.QModelIndex
    ) -> bool:
        """소스 모델의 행이 필터를 통과하는지 결정한다.

        Args:
            inSourceRow: 소스 모델의 행 인덱스
            inSourceParent: 소스 모델의 부모 인덱스

        Returns:
            _fuzzy_score >= 0이면 True
        """
        if not self._filterPattern:
            return True

        sourceModel = self.sourceModel()
        if sourceModel is None:
            return False

        index = sourceModel.index(inSourceRow, 0, inSourceParent)
        text = sourceModel.data(index, QtCore.Qt.DisplayRole)
        if text is None:
            return False

        return self._get_score(text) >= 0

    def lessThan(self, inLeft: QtCore.QModelIndex, inRight: QtCore.QModelIndex) -> bool:
        """정렬 비교 함수. 스코어가 높은 항목이 상위에 오도록 한다.

        DescendingOrder로 정렬하므로, lessThan에서 스코어가 낮은 쪽이 True를 반환하면
        스코어가 높은 쪽이 상단에 배치된다.

        Args:
            inLeft: 왼쪽 인덱스
            inRight: 오른쪽 인덱스

        Returns:
            왼쪽 스코어가 오른쪽보다 낮으면 True
        """
        if not self._filterPattern:
            return super().lessThan(inLeft, inRight)

        leftText = self.sourceModel().data(inLeft, QtCore.Qt.DisplayRole)
        rightText = self.sourceModel().data(inRight, QtCore.Qt.DisplayRole)

        leftScore = self._get_score(leftText) if leftText else -1
        rightScore = self._get_score(rightText) if rightText else -1

        return leftScore < rightScore


# =============================================================================
# Phase 3: _ComboDisplay
# =============================================================================


class _ComboDisplay(QtWidgets.QPushButton):
    """네이티브 콤보박스 외관을 렌더링하는 디스플레이 버튼.

    QStylePainter와 QStyleOptionComboBox를 사용하여
    시스템 테마에 맞는 콤보박스 외관을 그린다.
    """

    def __init__(self, inParent: QtWidgets.QWidget = None):
        """초기화.

        Args:
            inParent: 부모 위젯
        """
        super().__init__(inParent)
        self._displayText: str = ""
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def set_display_text(self, inText: str) -> None:
        """디스플레이 텍스트를 설정하고 다시 그린다.

        Args:
            inText: 표시할 텍스트
        """
        self._displayText = inText
        self.update()

    def display_text(self) -> str:
        """현재 디스플레이 텍스트를 반환한다.

        Returns:
            현재 표시 중인 텍스트
        """
        return self._displayText

    def paintEvent(self, inEvent: QtCore.QEvent) -> None:
        """네이티브 콤보박스 스타일로 렌더링한다.

        Args:
            inEvent: 페인트 이벤트
        """
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionComboBox()

        # 기본 상태 설정
        option.initFrom(self)
        option.currentText = self._displayText
        option.editable = False

        # 상태 플래그 설정
        if self.isEnabled():
            option.state |= QtWidgets.QStyle.State_Enabled
        if self.hasFocus():
            option.state |= QtWidgets.QStyle.State_HasFocus
        if self.isDown():
            option.state |= QtWidgets.QStyle.State_Sunken

        # 콤보박스 프레임(드롭다운 화살표 포함) 그리기
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, option)
        # 콤보박스 텍스트 영역에 현재 텍스트 그리기
        painter.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, option)

    def sizeHint(self) -> QtCore.QSize:
        """적절한 기본 크기를 반환한다.

        Returns:
            권장 크기
        """
        fontMetrics = self.fontMetrics()
        textWidth = (
            fontMetrics.horizontalAdvance(self._displayText)
            if self._displayText
            else 50
        )
        # 드롭다운 화살표 공간 + 여백 추가
        return QtCore.QSize(max(textWidth + 40, 100), fontMetrics.height() + 10)


# =============================================================================
# Phase 4: _FuzzyPopup
# =============================================================================


class _FuzzyPopup(QtWidgets.QFrame):
    """퍼지 검색 팝업 윈도우.

    QLineEdit(검색 입력)와 QListView(필터링된 결과 표시)를 포함하는
    Qt.Popup 플래그 기반 팝업 윈도우이다.
    """

    # 소스 모델 인덱스와 텍스트를 전달하는 시그널
    item_selected = QtCore.Signal(int, str)

    def __init__(self, inParent: QtWidgets.QWidget = None):
        """초기화.

        Args:
            inParent: 부모 위젯 (일반적으로 None으로 독립 윈도우 생성)
        """
        super().__init__(inParent)
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)

        self._ownerWidget: QtWidgets.QWidget = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """내부 UI 위젯을 구성한다."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # 검색 입력
        self._searchEdit = QtWidgets.QLineEdit(self)
        self._searchEdit.setPlaceholderText("Type to search...")
        layout.addWidget(self._searchEdit)

        # 결과 리스트
        self._listView = QtWidgets.QListView(self)
        self._listView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._listView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        layout.addWidget(self._listView)

        # 모델 설정
        self._sourceModel = QtGui.QStandardItemModel(self)
        self._proxyModel = _FuzzyFilterProxyModel(self)
        self._proxyModel.setSourceModel(self._sourceModel)
        self._listView.setModel(self._proxyModel)

        # 이벤트 필터 설치 (키보드 탐색용)
        self._searchEdit.installEventFilter(self)

    def _setup_connections(self) -> None:
        """시그널/슬롯을 연결한다."""
        # 검색어 변경 -> 필터 패턴 설정
        self._searchEdit.textChanged.connect(self._on_search_text_changed)

        # 리스트뷰 클릭 -> 항목 선택
        self._listView.clicked.connect(self._on_list_clicked)

    def _on_search_text_changed(self, inText: str) -> None:
        """검색어 변경 시 필터를 갱신하고 첫 항목을 하이라이트한다.

        Args:
            inText: 변경된 검색 텍스트
        """
        self._proxyModel.set_filter_pattern(inText)
        self._highlight_first_item()

    def _highlight_first_item(self) -> None:
        """프록시 모델의 첫 번째 항목을 하이라이트한다."""
        if self._proxyModel.rowCount() > 0:
            firstIndex = self._proxyModel.index(0, 0)
            self._listView.setCurrentIndex(firstIndex)

    def _on_list_clicked(self, inProxyIndex: QtCore.QModelIndex) -> None:
        """리스트뷰 항목 클릭 시 선택을 확정한다.

        Args:
            inProxyIndex: 클릭된 프록시 모델 인덱스
        """
        self._confirm_selection(inProxyIndex)

    def _confirm_selection(self, inProxyIndex: QtCore.QModelIndex) -> None:
        """선택을 확정하고 시그널을 발행한다.

        프록시 인덱스를 소스 인덱스로 변환하여 원본 항목의 인덱스와 텍스트를 전달한다.

        Args:
            inProxyIndex: 프록시 모델 인덱스
        """
        if not inProxyIndex.isValid():
            return

        sourceIndex = self._proxyModel.mapToSource(inProxyIndex)
        sourceRow = sourceIndex.row()
        text = self._sourceModel.data(sourceIndex, QtCore.Qt.DisplayRole)

        self.item_selected.emit(sourceRow, text)
        self.hide_popup()

    def eventFilter(self, inObj: QtCore.QObject, inEvent: QtCore.QEvent) -> bool:
        """QLineEdit의 키보드 이벤트를 가로채 리스트 탐색을 처리한다.

        Args:
            inObj: 이벤트 발생 객체
            inEvent: 이벤트

        Returns:
            이벤트 처리 여부
        """
        if inObj is not self._searchEdit:
            return super().eventFilter(inObj, inEvent)

        if inEvent.type() != QtCore.QEvent.KeyPress:
            return super().eventFilter(inObj, inEvent)

        key = inEvent.key()

        if key == QtCore.Qt.Key_Down:
            self._move_highlight(1)
            return True

        if key == QtCore.Qt.Key_Up:
            self._move_highlight(-1)
            return True

        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            currentIndex = self._listView.currentIndex()
            if currentIndex.isValid():
                self._confirm_selection(currentIndex)
            return True

        return super().eventFilter(inObj, inEvent)

    def _move_highlight(self, inDelta: int) -> None:
        """리스트뷰의 하이라이트를 이동한다.

        Args:
            inDelta: 이동 방향 (양수: 아래, 음수: 위)
        """
        rowCount = self._proxyModel.rowCount()
        if rowCount == 0:
            return

        currentIndex = self._listView.currentIndex()
        if not currentIndex.isValid():
            newRow = 0
        else:
            newRow = currentIndex.row() + inDelta
            newRow = max(0, min(newRow, rowCount - 1))

        newIndex = self._proxyModel.index(newRow, 0)
        self._listView.setCurrentIndex(newIndex)

    def show_popup(self, inGlobalPos: QtCore.QPoint, inWidth: int) -> None:
        """팝업을 지정된 위치에 표시한다.

        Args:
            inGlobalPos: 팝업 표시 위치 (글로벌 좌표, 위젯 하단 좌측)
            inWidth: 팝업 너비
        """
        # 필터 초기화
        self._searchEdit.clear()
        self._proxyModel.set_filter_pattern("")

        # 크기 계산
        rowCount = self._sourceModel.rowCount()
        rowHeight = self._listView.sizeHintForRow(0) if rowCount > 0 else 20
        listHeight = min(300, max(rowCount * rowHeight, rowHeight))
        # 검색 입력 높이 + 여백
        searchHeight = self._searchEdit.sizeHint().height()
        totalHeight = listHeight + searchHeight + 10

        self.setFixedSize(inWidth, totalHeight)

        # 화면 경계 확인
        popupPos = QtCore.QPoint(inGlobalPos)
        screen = QtWidgets.QApplication.screenAt(inGlobalPos)
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            screenGeometry = screen.availableGeometry()

            # 화면 하단 초과 시 위젯 위에 표시
            if popupPos.y() + totalHeight > screenGeometry.bottom():
                if self._ownerWidget is not None:
                    popupPos.setY(
                        inGlobalPos.y() - totalHeight - self._ownerWidget.height()
                    )
                else:
                    popupPos.setY(inGlobalPos.y() - totalHeight)

            # 화면 우측 초과 시 좌측으로 이동
            if popupPos.x() + inWidth > screenGeometry.right():
                popupPos.setX(screenGeometry.right() - inWidth)

        self.move(popupPos)
        self.show()
        self._searchEdit.setFocus()
        self._highlight_first_item()

    def hide_popup(self) -> None:
        """팝업을 숨기고 검색어를 초기화한다."""
        self._searchEdit.clear()
        self.hide()

    def set_items(self, inItems: list) -> None:
        """소스 모델의 아이템을 설정한다.

        Args:
            inItems: 문자열 아이템 리스트
        """
        self._sourceModel.clear()
        for itemText in inItems:
            item = QtGui.QStandardItem(itemText)
            self._sourceModel.appendRow(item)

    def add_item(self, inText: str) -> None:
        """소스 모델에 아이템을 하나 추가한다.

        Args:
            inText: 추가할 아이템 텍스트
        """
        item = QtGui.QStandardItem(inText)
        self._sourceModel.appendRow(item)

    def clear_items(self) -> None:
        """소스 모델의 모든 아이템을 제거한다."""
        self._sourceModel.clear()

    def set_owner_widget(self, inWidget: QtWidgets.QWidget) -> None:
        """팝업의 소유자 위젯을 설정한다.

        화면 경계 판정 시 소유자 위젯의 높이를 사용한다.

        Args:
            inWidget: 소유자 위젯
        """
        self._ownerWidget = inWidget


# =============================================================================
# Phase 5: FuzzySearchComboBox 통합
# =============================================================================


class FuzzySearchComboBox(QtWidgets.QWidget):
    """QWidget 기반 커스텀 퍼지 검색 콤보박스.

    QComboBox를 상속하지 않고, QPushButton 디스플레이와 Qt.Popup 팝업을 조합하여
    퍼지 검색 기능이 포함된 콤보박스를 제공한다.

    QComboBox 호환 API를 제공하여 기존 QComboBox 사용처에서 drop-in replacement가 가능하다.

    사용 예시::

        combo = FuzzySearchComboBox()
        combo.addItem("KimDokja")
        combo.addItem("YooJoonghyuk")
        combo.currentIndexChanged.connect(on_changed)
    """

    # QComboBox 호환 시그널
    currentIndexChanged = QtCore.Signal(int)

    def __init__(self, inParent: QtWidgets.QWidget = None):
        """초기화.

        Args:
            inParent: 부모 위젯
        """
        super().__init__(inParent)

        self._items: list = []
        self._currentIndex: int = -1
        self._currentText: str = ""

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """내부 UI를 구성한다."""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._comboDisplay = _ComboDisplay(self)
        layout.addWidget(self._comboDisplay, 1)

        # 팝업은 독립 윈도우로 생성
        self._popup = _FuzzyPopup(None)
        self._popup.set_owner_widget(self)

    def _setup_connections(self) -> None:
        """시그널/슬롯을 연결한다."""
        self._comboDisplay.clicked.connect(self._on_display_clicked)
        self._popup.item_selected.connect(self._on_item_selected)

    def _on_display_clicked(self) -> None:
        """디스플레이 버튼 클릭 시 팝업을 연다."""
        if not self.isEnabled():
            return

        # 위젯 하단 좌측의 글로벌 좌표 계산
        globalPos = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        self._popup.show_popup(globalPos, self.width())

    def _on_item_selected(self, inSourceIndex: int, inText: str) -> None:
        """팝업에서 항목이 선택되었을 때의 슬롯.

        Args:
            inSourceIndex: 소스 모델의 행 인덱스
            inText: 선택된 텍스트
        """
        if inSourceIndex < 0 or inSourceIndex >= len(self._items):
            return

        oldIndex = self._currentIndex
        self._currentIndex = inSourceIndex
        self._currentText = inText
        self._comboDisplay.set_display_text(inText)

        if oldIndex != inSourceIndex:
            self.currentIndexChanged.emit(inSourceIndex)

    # =========================================================================
    # QComboBox 호환 API
    # =========================================================================

    def addItem(self, inText: str) -> None:
        """아이템을 추가한다.

        첫 번째 항목 추가 시 자동으로 선택된다 (시그널 미발생).

        Args:
            inText: 추가할 아이템 텍스트
        """
        self._items.append(inText)
        self._popup.add_item(inText)

        # 첫 항목 추가 시 자동 선택 (시그널 미발생)
        if len(self._items) == 1 and self._currentIndex == -1:
            self._currentIndex = 0
            self._currentText = inText
            self._comboDisplay.set_display_text(inText)

    def addItems(self, inTexts: list) -> None:
        """여러 아이템을 일괄 추가한다.

        Args:
            inTexts: 추가할 아이템 텍스트 리스트
        """
        for text in inTexts:
            self.addItem(text)

    def clear(self) -> None:
        """모든 아이템을 제거하고 상태를 초기화한다."""
        self._items.clear()
        self._currentIndex = -1
        self._currentText = ""
        self._comboDisplay.set_display_text("")
        self._popup.clear_items()

    def currentText(self) -> str:
        """현재 선택된 텍스트를 반환한다.

        Returns:
            현재 선택 텍스트. 선택 없으면 빈 문자열.
        """
        return self._currentText

    def setCurrentIndex(self, inIndex: int) -> None:
        """인덱스로 항목을 선택한다.

        범위를 벗어나면 무시한다. 실제로 인덱스가 변경될 때만
        currentIndexChanged 시그널을 발생시킨다.

        Args:
            inIndex: 선택할 아이템 인덱스
        """
        if inIndex < 0 or inIndex >= len(self._items):
            return

        oldIndex = self._currentIndex
        self._currentIndex = inIndex
        self._currentText = self._items[inIndex]
        self._comboDisplay.set_display_text(self._currentText)

        if oldIndex != inIndex:
            self.currentIndexChanged.emit(inIndex)

    def findText(self, inText: str) -> int:
        """텍스트와 일치하는 아이템의 인덱스를 검색한다.

        Args:
            inText: 검색할 텍스트

        Returns:
            일치하는 아이템의 인덱스. 없으면 -1.
        """
        for i, item in enumerate(self._items):
            if item == inText:
                return i
        return -1

    def itemText(self, inIndex: int) -> str:
        """지정된 인덱스의 아이템 텍스트를 반환한다.

        Args:
            inIndex: 아이템 인덱스

        Returns:
            해당 인덱스의 텍스트. 범위 밖이면 빈 문자열.
        """
        if inIndex < 0 or inIndex >= len(self._items):
            return ""
        return self._items[inIndex]

    def count(self) -> int:
        """아이템 수를 반환한다.

        Returns:
            현재 아이템 수
        """
        return len(self._items)

    def setEnabled(self, inEnabled: bool) -> None:
        """위젯과 디스플레이 버튼의 활성화 상태를 설정한다.

        비활성 상태에서는 팝업이 열리지 않는다.

        Args:
            inEnabled: 활성화 여부
        """
        super().setEnabled(inEnabled)
        self._comboDisplay.setEnabled(inEnabled)

    def closeEvent(self, inEvent: QtCore.QEvent) -> None:
        """위젯이 닫힐 때 팝업을 정리한다.

        Args:
            inEvent: 클로즈 이벤트
        """
        self._popup.close()
        self._popup.deleteLater()
        super().closeEvent(inEvent)
