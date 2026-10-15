"""
PySide2 Collapsible Widget/ frameLayout

Origianlly created by: aronamao
on GitHub: https://github.com/aronamao/PySide2-Collapsible-Widget
"""


from PySide2 import QtWidgets, QtGui, QtCore


class Header(QtWidgets.QWidget):
    """Header class for collapsible group"""

    def __init__(self, name, content_widget, inFrameWidget=None):
        """Header Class Constructor to initialize the object.

        Args:
            name (str): Name for the header
            content_widget (QtWidgets.QWidget): Widget containing child elements
            inFrameWidget: 컨텐츠를 감싸는 위젯(스크롤 영역). 있으면 컨텐츠와 함께 접고 편다.
                기본값 None(컨텐츠만 접고 편다).
        """
        super(Header, self).__init__()
        self.content = content_widget
        self._frameWidget = inFrameWidget

        # Try to load icons from resources, use fallback if not available
        self.expand_ico = QtGui.QPixmap(":teDownArrow.png")
        self.collapse_ico = QtGui.QPixmap(":teRightArrow.png")

        # Check if icons were loaded properly (not empty)
        self._using_fallback_icons: bool = False
        if self.expand_ico.isNull() or self.collapse_ico.isNull():
            # Create fallback icons programmatically
            self._using_fallback_icons = True
            self.expand_ico = self._create_arrow_icon("down")
            self.collapse_ico = self._create_arrow_icon("right")

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        stacked = QtWidgets.QStackedLayout(self)
        stacked.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        self._background = QtWidgets.QLabel()

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)

        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(self.expand_ico)
        layout.addWidget(self.icon)
        layout.setContentsMargins(11, 0, 11, 0)

        font = QtGui.QFont()
        font.setBold(True)
        self._titleLabel = QtWidgets.QLabel(name)
        self._titleLabel.setFont(font)

        layout.addWidget(self._titleLabel)
        layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

        stacked.addWidget(widget)
        stacked.addWidget(self._background)
        self._background.setMinimumHeight(layout.sizeHint().height() * 1.5)

        self._update_background_style()

    def _update_background_style(self) -> None:
        """팔레트 기반으로 Header 배경 스타일을 갱신한다.

        QPalette.Window 색상을 가져와 lighter(115)를 적용하여
        테마 전환에 자동 대응한다.
        """
        baseColor = self.palette().color(QtGui.QPalette.Window)
        bgColor = baseColor.lighter(115)
        self._background.setStyleSheet(
            f"QLabel{{ background-color: rgb({bgColor.red()}, {bgColor.green()}, {bgColor.blue()}); border-radius:2px}}"
        )

    def changeEvent(self, inEvent: QtCore.QEvent) -> None:
        """팔레트 변경 이벤트를 감지하여 스타일을 갱신한다.

        Args:
            inEvent: 위젯 변경 이벤트
        """
        if inEvent.type() == QtCore.QEvent.PaletteChange:
            self._update_background_style()
            if self._using_fallback_icons:
                self.expand_ico = self._create_arrow_icon("down")
                self.collapse_ico = self._create_arrow_icon("right")
                # 현재 표시 상태에 맞는 아이콘으로 갱신
                if self.content.isVisible():
                    self.icon.setPixmap(self.expand_ico)
                else:
                    self.icon.setPixmap(self.collapse_ico)
        super().changeEvent(inEvent)

    def mousePressEvent(self, *args):
        """Handle mouse events, call the function to toggle groups"""
        self.expand() if not self.content.isVisible() else self.collapse()

    def expand(self):
        # 컨텐츠 자신의 숨김 플래그가 접힘 상태의 정본이다(ToolState 등이 isHidden()을 읽는다).
        # 감싸는 스크롤 영역은 그 상태를 따라간다.
        self.content.setVisible(True)
        if self._frameWidget is not None:
            self._frameWidget.setVisible(True)
        self.icon.setPixmap(self.expand_ico)

    def collapse(self):
        self.content.setVisible(False)
        if self._frameWidget is not None:
            self._frameWidget.setVisible(False)
        self.icon.setPixmap(self.collapse_ico)

    def _create_arrow_icon(self, direction):
        """Create a fallback arrow icon when resource icons are not available.

        Args:
            direction (str): Direction of the arrow ('down' or 'right')

        Returns:
            QtGui.QPixmap: Created arrow icon
        """
        # Create a pixmap for the arrow
        pixmap = QtGui.QPixmap(16, 16)
        pixmap.fill(QtGui.QColor(0, 0, 0, 0))  # Transparent background

        # Create a painter to draw the arrow
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # 팔레트 기반 텍스트 색상 사용 (테마 대응)
        textColor = self.palette().color(QtGui.QPalette.WindowText)
        pen = QtGui.QPen(textColor)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(textColor))

        # Draw the arrow based on direction
        if direction == "down":
            points = [QtCore.QPoint(4, 6), QtCore.QPoint(12, 6), QtCore.QPoint(8, 10)]
        else:  # right arrow
            points = [QtCore.QPoint(6, 4), QtCore.QPoint(6, 12), QtCore.QPoint(10, 8)]

        painter.drawPolygon(points)
        painter.end()

        return pixmap


class _ContentScrollArea(QtWidgets.QScrollArea):
    """Container 컨텐츠를 감싸는 세로 스크롤 영역(비공개).

    공간이 충분하면 스크롤이 없던 때와 같은 크기를 요구하고, 창을 줄일 때만 세로로 줄어들며
    스크롤바를 띄운다.

    왜 크기 규칙을 직접 정하는가: Qt 기본 `QScrollArea.sizeHint()`는 글꼴 높이 약 24줄에서
    잘리므로, 그대로 두면 긴 롤아웃은 공간이 남아도 스크롤바가 생겨 외형이 바뀐다.
    기본 `minimumSizeHint()`는 반대로 컨텐츠 최소 폭을 무시해, 가로 스크롤이 꺼진 상태에서
    컨텐츠 오른쪽이 잘린다.
    """

    #: 세로 최소 높이 상한(줄 수). 컨텐츠가 이보다 작으면 컨텐츠 최소 높이를 그대로 쓴다.
    _MIN_VISIBLE_LINES = 3

    def __init__(self, inContentWidget: QtWidgets.QWidget):
        """스크롤 영역을 만들고 컨텐츠 위젯을 넣는다.

        Args:
            inContentWidget: 스크롤될 컨텐츠 위젯(Container.contentWidget)
        """
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        # QScrollArea 기본 정책(Expanding)은 컨텐츠와 무관하게 부모 레이아웃의 남는 공간을 가져간다.
        # 스크롤이 없던 때의 컨텐츠(맨 QWidget)와 같은 Preferred에서 시작하고, 세로는
        # _sync_vertical_policy가 컨텐츠의 확장 여부를 따라가게 한다.
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setWidget(inContentWidget)
        # setWidget이 컨텐츠의 autoFillBackground를 켜므로 끈다 - 켜 두면 color_background가
        # 꺼진 Container가 부모 배경 대신 Window 색을 칠한다. 뷰포트도 칠하지 않는다.
        inContentWidget.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.setAutoFillBackground(False)
        # 스크롤바가 나타나고 사라질 때 최소 폭(스크롤바 폭 포함 여부)이 바뀐다.
        self.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)
        self._sync_vertical_policy()

    def _sync_vertical_policy(self) -> None:
        """컨텐츠의 세로 확장 여부를 이 스크롤 영역의 세로 정책으로 옮긴다.

        판정은 Qt `QWidgetItem::expandingDirections()`와 같다 - 컨텐츠 세로 정책에 ExpandFlag가
        있거나, GrowFlag가 있고 컨텐츠 레이아웃이 세로로 확장하면 Expanding, 아니면 Preferred.
        정책이 실제로 바뀔 때만 설정해 레이아웃 요청이 한 번에 수렴하게 한다.

        왜 필요한가(2026-10-15 PyJalFacialBuilder Bone 탭): Qt는 위젯의 레이아웃이 확장하면 그
        위젯도 확장하는 것으로 보아 리스트 같은 확장 위젯의 "늘어나고 싶음"을 바깥 레이아웃까지
        올린다. QScrollArea는 컨텐츠를 레이아웃이 아니라 setWidget으로 소유하므로 이 전파가
        끊긴다. 그러면 펼친 리스트 롤아웃이 접힌 롤아웃의 자리를 가져가지 못하고, 남는 공간이
        모든 롤아웃에 균등 분배되어 접힌 헤더가 빈 공간 한가운데 뜬다. 스크롤이 없던 때와 같은
        분배를 되살리기 위해 전파를 직접 잇는다. 접힌 Container는 이 위젯이 숨겨져 레이아웃이
        빈 항목으로 보므로 따로 처리하지 않는다.
        """
        content = self.widget()
        if content is None:
            return
        contentPolicy = int(content.sizePolicy().verticalPolicy())
        isExpanding = bool(contentPolicy & int(QtWidgets.QSizePolicy.ExpandFlag))
        contentLayout = content.layout()
        if (
            not isExpanding
            and contentLayout is not None
            and contentPolicy & int(QtWidgets.QSizePolicy.GrowFlag)
        ):
            isExpanding = bool(contentLayout.expandingDirections() & QtCore.Qt.Vertical)
        targetPolicy = QtWidgets.QSizePolicy.Expanding if isExpanding else QtWidgets.QSizePolicy.Preferred
        policy = self.sizePolicy()
        if policy.verticalPolicy() == targetPolicy:
            return
        policy.setVerticalPolicy(targetPolicy)
        self.setSizePolicy(policy)

    def showEvent(self, inEvent: QtGui.QShowEvent) -> None:
        """표시 시점에 세로 정책을 컨텐츠에 맞춘다.

        Args:
            inEvent: 표시 이벤트
        """
        self._sync_vertical_policy()
        super().showEvent(inEvent)

    def _on_scroll_range_changed(self, inMin: int, inMax: int) -> None:
        """세로 스크롤 범위 변경 시 크기 힌트를 다시 계산하게 한다.

        Args:
            inMin: 스크롤바 최솟값
            inMax: 스크롤바 최댓값
        """
        self.updateGeometry()

    def _scroll_bar_width(self) -> int:
        """세로 스크롤바가 필요한 상태면 그 폭을, 아니면 0을 돌려준다.

        Returns:
            크기 힌트에 더할 스크롤바 폭(px)
        """
        bar = self.verticalScrollBar()
        if bar.maximum() > bar.minimum():
            return bar.sizeHint().width()
        return 0

    def sizeHint(self) -> QtCore.QSize:
        """컨텐츠 전체 sizeHint를 그대로 요구한다(잘림 없음).

        Returns:
            컨텐츠 sizeHint(+스크롤바가 보이면 그 폭)
        """
        content = self.widget()
        if content is None:
            return super().sizeHint()
        hint = content.sizeHint().expandedTo(content.minimumSizeHint())
        return QtCore.QSize(hint.width() + self._scroll_bar_width(), hint.height())

    def minimumSizeHint(self) -> QtCore.QSize:
        """가로는 컨텐츠 최소 폭을 전파하고, 세로만 작게 둔다.

        Returns:
            (컨텐츠 최소 폭 + 보이는 스크롤바 폭, min(컨텐츠 최소 높이, 3줄))
        """
        content = self.widget()
        if content is None:
            return super().minimumSizeHint()
        contentMin = content.minimumSizeHint()
        lineLimit = self.fontMetrics().lineSpacing() * self._MIN_VISIBLE_LINES
        height = min(max(contentMin.height(), 0), lineLimit)
        return QtCore.QSize(max(contentMin.width(), 0) + self._scroll_bar_width(), height)

    def event(self, inEvent: QtCore.QEvent) -> bool:
        """컨텐츠 레이아웃 변경을 바깥 레이아웃으로 전파한다.

        컨텐츠의 updateGeometry는 부모(뷰포트)에 LayoutRequest를 보내고 뷰포트는 그것을 이
        위젯으로 넘긴다. QScrollArea는 스크롤바만 갱신하므로, 컨텐츠 크기에 의존하는 이 위젯의
        크기 힌트를 무효화해 바깥 레이아웃(창 최소 크기 포함)이 따라오게 한다. 컨텐츠의 세로
        확장 여부도 이때 다시 맞춘다(확장 위젯 추가·하위 롤아웃 접힘 등).

        Args:
            inEvent: 위젯 이벤트

        Returns:
            이벤트 처리 여부
        """
        if inEvent.type() == QtCore.QEvent.LayoutRequest:
            self._sync_vertical_policy()
            self.updateGeometry()
        return super().event(inEvent)


class Container(QtWidgets.QWidget):
    """Class for creating a collapsible group similar to how it is implement in Maya

        Examples:
            Simple example of how to add a Container to a QVBoxLayout and attach a QGridLayout

            >>> layout = QtWidgets.QVBoxLayout()
            >>> container = Container("Group")
            >>> layout.addWidget(container)
            >>> content_layout = QtWidgets.QGridLayout(container.contentWidget)
            >>> content_layout.addWidget(QtWidgets.QPushButton("Button"))
    """
    def __init__(self, name, color_background=True, inScrollable: bool = True):
        """Container Class Constructor to initialize the object

        Args:
            name (str): Name for the header
            color_background (bool): whether or not to color the background lighter like in maya
            inScrollable: 컨텐츠를 세로 스크롤 영역에 넣는다. 기본값 True.
                켜져 있으면 공간이 충분할 때는 외형이 같고, 창을 줄일 때만 스크롤바가 생긴다.
                False면 스크롤 영역 없이 Header + 컨텐츠만 쌓는다(구 동작). 스크롤되는 롤아웃
                안에 다시 넣는 하위 롤아웃처럼 이중 스크롤을 피해야 할 때 끈다.

        Note:
            스크롤이 기본인 이유(2026-10-14 MeshValidator): 스크롤이 없으면 컨텐츠 최소 높이가 그대로
            창 최소 높이로 전파된다. 슬롯 29개짜리 롤아웃이 창 최소 높이를 1080p 작업 영역 밖으로
            밀어, 창을 줄일 수도 아래 항목에 닿을 수도 없었다.
        """
        super(Container, self).__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)
        self._content_widget = QtWidgets.QWidget()
        self._color_background: bool = color_background
        if self._color_background:
            self._update_content_style()
        self._scrollArea = _ContentScrollArea(self._content_widget) if inScrollable else None
        self._header = Header(name, self._content_widget, self._scrollArea)
        layout.addWidget(self._header)
        layout.addWidget(self._scrollArea if self._scrollArea is not None else self._content_widget)

        # assign header methods to instance attributes so they can be called outside of this class
        self.collapse = self._header.collapse
        self.expand = self._header.expand
        self.toggle = self._header.mousePressEvent

    def _update_content_style(self) -> None:
        """팔레트 기반으로 컨텐츠 위젯 배경 스타일을 갱신한다.

        QPalette.Window 색상을 가져와 lighter(115)를 적용하여
        테마 전환에 자동 대응한다.
        """
        baseColor = self.palette().color(QtGui.QPalette.Window)
        bgColor = baseColor.lighter(115)
        self._content_widget.setStyleSheet(
            f".QWidget{{ background-color: rgb({bgColor.red()}, {bgColor.green()}, {bgColor.blue()}); }}"
        )

    def changeEvent(self, inEvent: QtCore.QEvent) -> None:
        """팔레트 변경 이벤트를 감지하여 컨텐츠 스타일을 갱신한다.

        Args:
            inEvent: 위젯 변경 이벤트
        """
        if inEvent.type() == QtCore.QEvent.PaletteChange:
            if self._color_background:
                self._update_content_style()
        super().changeEvent(inEvent)

    @property
    def contentWidget(self):
        """Getter for the content widget

        Returns: Content widget
        """
        return self._content_widget

    def title(self) -> str:
        """헤더에 표시된 제목 문자열을 반환한다.

        Returns:
            헤더 제목 문자열
        """
        return self._header._titleLabel.text()

    def set_title(self, inTitle: str) -> None:
        """헤더에 표시할 제목 문자열을 바꾼다.

        사용처가 헤더 내부 라벨을 직접 건드리지 않도록 공개 경로를 둔다
        (예: 접힌 롤아웃 제목에 할당 수를 표시).

        Args:
            inTitle: 새 제목 문자열
        """
        self._header._titleLabel.setText(inTitle)
