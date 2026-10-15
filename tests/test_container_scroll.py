# -*- coding: utf-8 -*-
"""Container 기본 스크롤 단위 테스트 (Type A - Console pytest + 실제 PySide2).

왜: 스크롤이 없는 Container는 컨텐츠 최소 높이를 창 최소 높이로 그대로 전파한다
(2026-10-14 MeshValidator - 슬롯 29개가 창을 1080p 작업 영역 밖으로 밀었다). 기본 스크롤을
켜되, 공간이 충분하면 외형이 지금과 같아야 하고(L3·L4), 외부가 읽는 접힘 계약
(`contentWidget.isHidden()`, L2)이 유지되어야 한다.

창은 `WA_DontShowOnScreen`으로 화면에 띄우지 않고 표시 상태만 만든다 - 레이아웃 활성화와
스크롤바 범위 계산은 표시된 위젯에서만 일어난다.
"""

import pytest
from PySide2 import QtCore, QtWidgets

from pyjallib.max.ui.Container import Container

#: 컨텐츠 항목 수. 항목 높이 30px 기준으로 Qt 기본 QScrollArea.sizeHint 상한(글꼴 약 24줄)을
#: 넘도록 잡는다 - 크기 규칙이 빠지면 "공간이 충분해도 잘린다"가 실제로 드러나야 한다.
_ITEM_COUNT = 30
_ITEM_HEIGHT = 30


@pytest.fixture(scope="session")
def qapp():
    """세션 범위 QApplication 인스턴스를 생성한다.

    Returns:
        QApplication 인스턴스
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _fill_content(inContainer: Container, inCount: int = _ITEM_COUNT) -> list:
    """Container 컨텐츠에 고정 높이 버튼을 쌓는다.

    Args:
        inContainer: 대상 Container
        inCount: 버튼 수

    Returns:
        만든 버튼 리스트
    """
    layout = QtWidgets.QVBoxLayout(inContainer.contentWidget)
    buttons = []
    for index in range(inCount):
        button = QtWidgets.QPushButton(f"Item {index}")
        button.setMinimumHeight(_ITEM_HEIGHT)
        layout.addWidget(button)
        buttons.append(button)
    return buttons


def _make_window(inContainer: QtWidgets.QWidget, inWidth: int, inHeight: int) -> QtWidgets.QWidget:
    """Container 하나 + 하단 stretch를 담은 창을 화면 밖 표시 상태로 만든다.

    Args:
        inContainer: 창에 넣을 위젯
        inWidth: 창 폭
        inHeight: 창 높이

    Returns:
        표시된 창
    """
    window = QtWidgets.QWidget()
    window.setAttribute(QtCore.Qt.WA_DontShowOnScreen)
    layout = QtWidgets.QVBoxLayout(window)
    layout.addWidget(inContainer)
    layout.addStretch(1)
    window.resize(inWidth, inHeight)
    window.show()
    _settle()
    return window


def _settle() -> None:
    """보류된 레이아웃 요청을 모두 처리한다(스크롤 영역은 이벤트를 두 단계로 전파한다)."""
    for _ in range(5):
        QtWidgets.QApplication.processEvents()


def _scroll_area(inContainer: Container):
    """Container 직계 자식 스크롤 영역을 찾는다.

    Args:
        inContainer: 대상 Container

    Returns:
        QScrollArea 또는 None
    """
    return inContainer.findChild(
        QtWidgets.QScrollArea, options=QtCore.Qt.FindDirectChildrenOnly
    )


# ==============================================================================
# 위젯 트리 / 기본값 (1.5 ①②)
# ==============================================================================


class TestStructure:
    """스크롤 켜짐/꺼짐 위젯 트리."""

    def test_default_is_scrollable(self, qapp):
        """기본값은 스크롤 켜짐 - 스크롤 영역이 있고 contentWidget이 그 위젯이다."""
        container = Container("Group")
        area = _scroll_area(container)
        assert area is not None
        assert area.widget() is container.contentWidget
        assert area.widgetResizable() is True
        assert area.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarAlwaysOff
        assert area.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarAsNeeded
        assert area.frameShape() == QtWidgets.QFrame.NoFrame

    def test_scroll_off_has_old_tree(self, qapp):
        """꺼짐이면 스크롤 영역이 없고 contentWidget이 Container 직계 자식이다(구 동작)."""
        container = Container("Group", inScrollable=False)
        assert container.findChildren(QtWidgets.QScrollArea) == []
        assert container.contentWidget.parentWidget() is container

    def test_color_background_positional_arg_kept(self, qapp):
        """기존 위치 인자(name, color_background)가 그대로 동작한다."""
        container = Container("Group", False)
        assert container._color_background is False
        assert _scroll_area(container) is not None

    def test_scroll_area_does_not_paint_background(self, qapp):
        """스크롤 영역·뷰포트·컨텐츠가 배경을 칠하지 않는다(color_background 배경이 그대로 보인다)."""
        container = Container("Group", color_background=False)
        area = _scroll_area(container)
        assert area.autoFillBackground() is False
        assert area.viewport().autoFillBackground() is False
        assert container.contentWidget.autoFillBackground() is False

    def test_scroll_area_size_policy_is_preferred(self, qapp):
        """확장하지 않는 컨텐츠면 스크롤 영역은 Preferred - 부모 레이아웃의 남는 공간을 가져가지 않는다.

        0.5.4에서는 컨텐츠와 무관하게 "항상 Preferred"를 지켰다. 0.5.5부터는 확장하지 않는
        컨텐츠(버튼만)에서만 성립하고, 확장 컨텐츠(리스트)는 Expanding으로 남는 공간을 가져가는
        것이 사양이다(스크롤이 없던 때와 같은 분배) - 그쪽은 TestExpandPropagation이 지킨다.
        """
        container = Container("Group")
        _fill_content(container, 3)
        window = _make_window(container, 300, 400)
        policy = _scroll_area(container).sizePolicy()
        assert policy.horizontalPolicy() == QtWidgets.QSizePolicy.Preferred
        assert policy.verticalPolicy() == QtWidgets.QSizePolicy.Preferred
        window.close()


# ==============================================================================
# 접기/펼치기 계약 (1.5 ③, L2)
# ==============================================================================


class TestCollapseContract:
    """contentWidget.isHidden()이 접힘 상태를 그대로 나타낸다."""

    def test_collapse_hides_content_widget(self, qapp):
        """collapse() 후 contentWidget.isHidden() is True, 스크롤 영역도 숨겨진다."""
        container = Container("Group")
        container.collapse()
        assert container.contentWidget.isHidden() is True
        assert _scroll_area(container).isHidden() is True

    def test_expand_shows_content_widget(self, qapp):
        """expand() 후 contentWidget.isHidden() is False, 스크롤 영역도 보인다."""
        container = Container("Group")
        container.collapse()
        container.expand()
        assert container.contentWidget.isHidden() is False
        assert _scroll_area(container).isHidden() is False

    def test_toggle_on_shown_window(self, qapp):
        """표시된 창에서 toggle()은 접고, 다시 toggle()하면 편다."""
        container = Container("Group")
        _fill_content(container, 3)
        window = _make_window(container, 300, 400)
        container.toggle()
        _settle()
        assert container.contentWidget.isHidden() is True
        container.toggle()
        _settle()
        assert container.contentWidget.isHidden() is False
        assert container.contentWidget.isVisible() is True
        window.close()

    def test_collapsed_height_equals_header_only(self, qapp):
        """접힌 켜짐 Container의 높이는 접힌 꺼짐 Container와 같다(헤더만)."""
        onContainer = Container("Group")
        offContainer = Container("Group", inScrollable=False)
        _fill_content(onContainer)
        _fill_content(offContainer)
        onContainer.collapse()
        offContainer.collapse()
        onWindow = _make_window(onContainer, 300, 600)
        offWindow = _make_window(offContainer, 300, 600)
        assert onContainer.height() == offContainer.height()
        onWindow.close()
        offWindow.close()


# ==============================================================================
# 제목 (1.5 ④)
# ==============================================================================


class TestTitle:
    """set_title() / title()."""

    def test_set_title_reflected(self, qapp):
        """set_title() 후 title()이 새 제목을 돌려준다."""
        container = Container("Attach")
        container.set_title("Attach (2/15)")
        assert container.title() == "Attach (2/15)"


# ==============================================================================
# 크기 규칙 (1.6, L3)
# ==============================================================================


class TestSizeRules:
    """공간이 충분하면 외형 무변화, 부족할 때만 세로 스크롤."""

    def test_enough_space_same_height_as_scroll_off(self, qapp):
        """① 공간이 충분하면 켜짐 높이 = 꺼짐 높이, 세로 스크롤바 없음."""
        onContainer = Container("Group")
        offContainer = Container("Group", inScrollable=False)
        _fill_content(onContainer)
        _fill_content(offContainer)
        onWindow = _make_window(onContainer, 400, 1600)
        offWindow = _make_window(offContainer, 400, 1600)

        assert onContainer.height() == offContainer.height()
        assert onContainer.contentWidget.height() == offContainer.contentWidget.height()
        assert _scroll_area(onContainer).verticalScrollBar().isVisible() is False
        onWindow.close()
        offWindow.close()

    def test_small_window_scrolls_and_min_height_shrinks(self, qapp):
        """② 컨텐츠보다 작은 창이면 창 최소 높이 < 컨텐츠 높이, 세로 스크롤바가 보인다."""
        container = Container("Group")
        _fill_content(container)
        contentHeight = container.contentWidget.sizeHint().height()
        window = _make_window(container, 400, 300)

        assert window.minimumSizeHint().height() < contentHeight
        assert window.height() < contentHeight
        bar = _scroll_area(container).verticalScrollBar()
        assert bar.isVisible() is True
        assert bar.maximum() > 0
        window.close()

    def test_scroll_off_min_height_follows_content(self, qapp):
        """② 대조: 꺼짐이면 창 최소 높이가 컨텐츠 높이 이상으로 전파된다(구 동작 = 문제의 원인)."""
        container = Container("Group", inScrollable=False)
        _fill_content(container)
        contentMin = container.contentWidget.minimumSizeHint().height()
        window = _make_window(container, 400, 300)
        assert window.minimumSizeHint().height() >= contentMin
        window.close()

    def test_min_width_same_as_scroll_off(self, qapp):
        """③ 공간이 충분하면 가로 최소 폭은 꺼짐과 같다."""
        onContainer = Container("Group")
        offContainer = Container("Group", inScrollable=False)
        for container in (onContainer, offContainer):
            layout = QtWidgets.QHBoxLayout(container.contentWidget)
            wide = QtWidgets.QPushButton("A fairly wide button label for min width")
            wide.setMinimumWidth(260)
            layout.addWidget(wide)
        onWindow = _make_window(onContainer, 500, 400)
        offWindow = _make_window(offContainer, 500, 400)
        assert onContainer.minimumSizeHint().width() == offContainer.minimumSizeHint().width()
        assert onWindow.minimumSizeHint().width() == offWindow.minimumSizeHint().width()
        onWindow.close()
        offWindow.close()

    def test_scrollbar_visible_keeps_content_min_width(self, qapp):
        """스크롤바가 보일 때 컨텐츠가 최소 폭 아래로 눌리지 않는다(가로 스크롤 없음 = 잘림 방지)."""
        container = Container("Group")
        buttons = _fill_content(container)
        for button in buttons:
            button.setMinimumWidth(240)
        window = _make_window(container, 100, 300)
        bar = _scroll_area(container).verticalScrollBar()
        assert bar.isVisible() is True
        assert container.contentWidget.width() >= container.contentWidget.minimumSizeHint().width()
        assert container.width() >= container.contentWidget.minimumSizeHint().width() + bar.width()
        window.close()

    def test_qt_default_scroll_area_would_clip(self, qapp):
        """④ 판별력: 크기 규칙 없는 Qt 기본 QScrollArea는 같은 컨텐츠의 높이를 잘라 요구한다.

        이 단정이 거짓이면(기본 sizeHint가 잘리지 않으면) ①은 크기 규칙의 유무를 가르지 못한다.
        """
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        for index in range(_ITEM_COUNT):
            button = QtWidgets.QPushButton(f"Item {index}")
            button.setMinimumHeight(_ITEM_HEIGHT)
            layout.addWidget(button)
        plain = QtWidgets.QScrollArea()
        plain.setFrameShape(QtWidgets.QFrame.NoFrame)
        plain.setWidgetResizable(True)
        plain.setWidget(content)
        assert plain.sizeHint().height() < content.sizeHint().height()

        container = Container("Group")
        _fill_content(container)
        area = _scroll_area(container)
        assert area.sizeHint().height() == container.contentWidget.sizeHint().height()


# ==============================================================================
# 컨텐츠 크기 변화 전파 (1.3 - 하위 롤아웃 접힘/펼침)
# ==============================================================================


class TestNestedResize:
    """스크롤 영역 안의 하위 롤아웃(스크롤 꺼짐)을 접고 펼 때 바깥 크기가 따라온다."""

    def test_nested_collapse_expand_propagates(self, qapp):
        """하위 롤아웃을 펼치면 바깥 Container가 커지고, 접으면 다시 줄어든다."""
        outer = Container("Outer")
        outerLayout = QtWidgets.QVBoxLayout(outer.contentWidget)
        head = QtWidgets.QPushButton("Head")
        outerLayout.addWidget(head)
        inner = Container("Inner", inScrollable=False)
        _fill_content(inner, 10)
        outerLayout.addWidget(inner)
        inner.collapse()

        window = _make_window(outer, 400, 1400)
        collapsedHeight = outer.height()
        bar = _scroll_area(outer).verticalScrollBar()

        inner.expand()
        _settle()
        expandedHeight = outer.height()
        assert expandedHeight > collapsedHeight + 10 * _ITEM_HEIGHT - 1
        assert bar.isVisible() is False

        inner.collapse()
        _settle()
        assert outer.height() == collapsedHeight
        window.close()


# ==============================================================================
# 세로 확장 전파 (0.5.5 - 접힌 롤아웃 자리를 펼친 리스트 롤아웃이 채운다)
# ==============================================================================

#: 리스트 롤아웃 스택 창 크기. 롤아웃 3개를 모두 펼쳐도 sizeHint 합보다 커서 공간 부족이 없다 -
#: 남는 공간의 분배만 비교한다.
_STACK_WIDTH = 400
_STACK_HEIGHT = 1200


def _fill_list_content(inContainer: Container) -> QtWidgets.QListWidget:
    """Container 컨텐츠에 버튼 1개 + 리스트(세로 확장 위젯)를 넣는다.

    Args:
        inContainer: 대상 Container

    Returns:
        만든 리스트 위젯
    """
    layout = QtWidgets.QVBoxLayout(inContainer.contentWidget)
    layout.addWidget(QtWidgets.QPushButton("Pick"))
    listWidget = QtWidgets.QListWidget()
    layout.addWidget(listWidget)
    return listWidget


def _make_stack_window(inContainers: list) -> QtWidgets.QWidget:
    """Container들을 stretch 없이 세로로 쌓은 창을 화면 밖 표시 상태로 만든다.

    PyJalFacialBuilder Bone 탭과 같은 배치다(롤아웃만 쌓고 stretch 없음).

    Args:
        inContainers: 쌓을 Container 리스트

    Returns:
        표시된 창
    """
    window = QtWidgets.QWidget()
    window.setAttribute(QtCore.Qt.WA_DontShowOnScreen)
    layout = QtWidgets.QVBoxLayout(window)
    for container in inContainers:
        layout.addWidget(container)
    window.resize(_STACK_WIDTH, _STACK_HEIGHT)
    window.show()
    _settle()
    return window


def _build_list_stack(inScrollable: bool) -> tuple:
    """리스트 롤아웃 3개 스택 창을 만든다.

    Args:
        inScrollable: Container 스크롤 켜짐 여부

    Returns:
        (창, Container 리스트)
    """
    containers = [Container(f"Group {index}", inScrollable=inScrollable) for index in range(3)]
    for container in containers:
        _fill_list_content(container)
    window = _make_stack_window(containers)
    return window, containers


def _geometries(inContainers: list) -> list:
    """Container들의 (y, 높이) 목록.

    Args:
        inContainers: Container 리스트

    Returns:
        [(y, height), ...]
    """
    return [(container.y(), container.height()) for container in inContainers]


class TestExpandPropagation:
    """리스트처럼 세로 확장하는 컨텐츠의 확장 여부가 스크롤 영역 바깥으로 전파된다."""

    def test_list_content_makes_scroll_area_expanding(self, qapp):
        """① 리스트를 담은 컨텐츠 -> 스크롤 영역 세로 Expanding, Container 레이아웃도 세로 확장."""
        container = Container("Group")
        _fill_list_content(container)
        window = _make_stack_window([container])
        area = _scroll_area(container)
        assert area.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert area.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Preferred
        assert bool(container.layout().expandingDirections() & QtCore.Qt.Vertical) is True
        window.close()

    def test_collapsed_space_goes_to_expanded_list(self, qapp):
        """② 회귀 시나리오: 아래 2개를 접으면 첫 롤아웃이 남는 공간을 갖고 헤더가 바로 아래 붙는다.

        정본은 스크롤 영역이 없던 0.5.4 이전 트리(inScrollable=False)의 배치다.
        """
        onWindow, onContainers = _build_list_stack(True)
        offWindow, offContainers = _build_list_stack(False)
        for containers in (onContainers, offContainers):
            containers[1].collapse()
            containers[2].collapse()
        _settle()

        assert _geometries(onContainers) == _geometries(offContainers)
        first, second, third = onContainers
        assert first.height() > first.sizeHint().height()
        spacing = onWindow.layout().spacing()
        assert second.y() == first.y() + first.height() + spacing
        assert third.y() == second.y() + second.height() + spacing
        assert second.height() == second.sizeHint().height()
        onWindow.close()
        offWindow.close()

    def test_expand_collapse_round_trip(self, qapp):
        """③ 다시 펼치면 스크롤 꺼짐과 같은 분배, 다시 접으면 ②의 배치로 돌아온다."""
        onWindow, onContainers = _build_list_stack(True)
        offWindow, offContainers = _build_list_stack(False)
        for containers in (onContainers, offContainers):
            containers[1].collapse()
            containers[2].collapse()
        _settle()
        collapsedGeometries = _geometries(onContainers)

        for containers in (onContainers, offContainers):
            containers[1].expand()
            containers[2].expand()
        _settle()
        assert _geometries(onContainers) == _geometries(offContainers)
        for container in onContainers:
            assert container.height() > container.sizeHint().height()

        onContainers[1].collapse()
        onContainers[2].collapse()
        _settle()
        assert _geometries(onContainers) == collapsedGeometries
        onWindow.close()
        offWindow.close()

    def test_non_expanding_content_keeps_size_hint(self, qapp):
        """④ 버튼만 있는 롤아웃은 리스트 롤아웃 옆에서 남는 공간을 가져가지 않는다(높이 = sizeHint)."""
        buttonContainer = Container("Buttons")
        _fill_content(buttonContainer, 3)
        listContainer = Container("List")
        _fill_list_content(listContainer)
        window = _make_stack_window([buttonContainer, listContainer])

        assert _scroll_area(buttonContainer).sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Preferred
        assert buttonContainer.height() == buttonContainer.sizeHint().height()
        assert listContainer.height() > listContainer.sizeHint().height()
        window.close()

    def test_nested_list_propagates_to_outer(self, qapp):
        """⑤ 스크롤 Container 안의 스크롤 꺼짐 하위 Container에 리스트가 있으면 바깥까지 전파된다."""
        outer = Container("Outer")
        outerLayout = QtWidgets.QVBoxLayout(outer.contentWidget)
        inner = Container("Inner", inScrollable=False)
        _fill_list_content(inner)
        outerLayout.addWidget(inner)
        window = _make_stack_window([outer])

        assert _scroll_area(outer).sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Expanding
        assert outer.height() > outer.sizeHint().height()
        window.close()

    def test_policy_follows_content_change(self, qapp):
        """⑥ 표시 후 리스트를 추가하면 Expanding으로, 그 리스트를 숨기면 Preferred로 따라온다."""
        container = Container("Group")
        _fill_content(container, 2)
        window = _make_stack_window([container])
        area = _scroll_area(container)
        assert area.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Preferred

        listWidget = QtWidgets.QListWidget()
        container.contentWidget.layout().addWidget(listWidget)
        _settle()
        assert area.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Expanding

        listWidget.hide()
        _settle()
        assert area.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Preferred
        window.close()

    def test_policy_is_fixed_point(self, qapp):
        """⑦ 정착 후 레이아웃 요청이 다시 와도 정책을 다시 설정하지 않는다(요청 순환 없음)."""
        container = Container("Group")
        _fill_list_content(container)
        window = _make_stack_window([container])
        area = _scroll_area(container)

        calls = []
        originalSetter = area.setSizePolicy

        def _counting_setter(*inArgs):
            calls.append(inArgs)
            originalSetter(*inArgs)

        area.setSizePolicy = _counting_setter
        for _ in range(3):
            QtWidgets.QApplication.sendEvent(area, QtCore.QEvent(QtCore.QEvent.LayoutRequest))
        _settle()
        assert calls == []
        assert area.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Expanding
        window.close()
