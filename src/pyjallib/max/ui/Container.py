"""
PySide2 Collapsible Widget/ frameLayout

Origianlly created by: aronamao
on GitHub: https://github.com/aronamao/PySide2-Collapsible-Widget
"""


from PySide2 import QtWidgets, QtGui, QtCore


class Header(QtWidgets.QWidget):
    """Header class for collapsible group"""

    def __init__(self, name, content_widget):
        """Header Class Constructor to initialize the object.

        Args:
            name (str): Name for the header
            content_widget (QtWidgets.QWidget): Widget containing child elements
        """
        super(Header, self).__init__()
        self.content = content_widget

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
        self.content.setVisible(True)
        self.icon.setPixmap(self.expand_ico)

    def collapse(self):
        self.content.setVisible(False)
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
    def __init__(self, name, color_background=True):
        """Container Class Constructor to initialize the object

        Args:
            name (str): Name for the header
            color_background (bool): whether or not to color the background lighter like in maya
        """
        super(Container, self).__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)
        self._content_widget = QtWidgets.QWidget()
        self._color_background: bool = color_background
        if self._color_background:
            self._update_content_style()
        self._header = Header(name, self._content_widget)
        layout.addWidget(self._header)
        layout.addWidget(self._content_widget)

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
