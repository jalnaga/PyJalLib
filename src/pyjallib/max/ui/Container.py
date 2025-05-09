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
        if self.expand_ico.isNull() or self.collapse_ico.isNull():
            # Create fallback icons programmatically
            self.expand_ico = self._create_arrow_icon("down")
            self.collapse_ico = self._create_arrow_icon("right")

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        stacked = QtWidgets.QStackedLayout(self)
        stacked.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        background = QtWidgets.QLabel()
        background.setStyleSheet("QLabel{ background-color: rgb(81, 81, 81); border-radius:2px}")

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)

        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(self.expand_ico)
        layout.addWidget(self.icon)
        layout.setContentsMargins(11, 0, 11, 0)

        font = QtGui.QFont()
        font.setBold(True)
        label = QtWidgets.QLabel(name)
        label.setFont(font)

        layout.addWidget(label)
        layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

        stacked.addWidget(widget)
        stacked.addWidget(background)
        background.setMinimumHeight(layout.sizeHint().height() * 1.5)

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

        # Set the pen and brush
        pen = QtGui.QPen(QtGui.QColor(200, 200, 200))
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200)))

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
        if color_background:
            self._content_widget.setStyleSheet('''
                .QWidget{
                    background-color: rgb(81, 81, 81); 
                }
            ''')
        header = Header(name, self._content_widget)
        layout.addWidget(header)
        layout.addWidget(self._content_widget)

        # assign header methods to instance attributes so they can be called outside of this class
        self.collapse = header.collapse
        self.expand = header.expand
        self.toggle = header.mousePressEvent

    @property
    def contentWidget(self):
        """Getter for the content widget

        Returns: Content widget
        """
        return self._content_widget
