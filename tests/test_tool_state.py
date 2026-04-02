# -*- coding: utf-8 -*-
"""ToolState 단위 테스트 (Type A - Console pytest).

pymxs 없이 PySide2만으로 ToolState의 핵심 기능을 검증한다.
_settingsPath를 직접 설정하여 pymxs 의존성을 우회한다.
"""

import json
import os

import pytest
from PySide2 import QtCore, QtWidgets

from pyjallib.max.ui.toolState import ToolState
from pyjallib.max.ui.Container import Container


# ==============================================================================
# QApplication fixture
# ==============================================================================

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


@pytest.fixture
def tool_state(qapp):
    """기본 ToolState 인스턴스를 생성한다.

    Args:
        qapp: QApplication fixture

    Returns:
        ToolState 인스턴스
    """
    return ToolState("TestTool")


@pytest.fixture
def window(qapp):
    """테스트용 QWidget 윈도우를 생성한다.

    Args:
        qapp: QApplication fixture

    Returns:
        QWidget 인스턴스
    """
    w = QtWidgets.QWidget()
    w.resize(400, 300)
    w.move(100, 100)
    return w


@pytest.fixture
def container(qapp):
    """테스트용 Container 위젯을 생성한다.

    Args:
        qapp: QApplication fixture

    Returns:
        Container 인스턴스
    """
    return Container("TestGroup")


# ==============================================================================
# TC01~TC03: 기본 초기화
# ==============================================================================

class TestInit:
    """ToolState 초기화 관련 테스트."""

    def test_tool_name_stored(self, tool_state):
        """TC01: ToolState 생성 시 _toolName이 올바르게 저장된다."""
        assert tool_state._toolName == "TestTool"

    def test_windows_empty_on_init(self, tool_state):
        """TC02: ToolState 생성 시 _windows가 빈 딕셔너리다."""
        assert tool_state._windows == {}

    def test_containers_empty_on_init(self, tool_state):
        """TC02: ToolState 생성 시 _containers가 빈 딕셔너리다."""
        assert tool_state._containers == {}

    def test_get_settings_path_without_pymxs(self, tool_state):
        """TC03: pymxs 없는 환경에서 _get_settings_path()가 빈 문자열을 반환한다."""
        # _settingsPath가 None이고 pymxs가 없으면 빈 문자열 반환
        result = tool_state._get_settings_path()
        assert result == ""

    def test_get_settings_path_with_explicit_path(self, tool_state, tmp_path):
        """TC03 변형: _settingsPath를 직접 설정하면 그 값을 반환한다."""
        expectedPath = str(tmp_path / "test_setting.json")
        tool_state._settingsPath = expectedPath
        result = tool_state._get_settings_path()
        assert result == expectedPath


# ==============================================================================
# TC04~TC05: 윈도우 등록
# ==============================================================================

class TestRegisterWindow:
    """register_window() 관련 테스트."""

    def test_window_stored_in_windows(self, tool_state, window):
        """TC04: register_window() 후 _windows에 윈도우가 저장된다."""
        tool_state.register_window(window, "main")
        assert "main" in tool_state._windows
        assert tool_state._windows["main"] is window

    def test_containers_key_created_for_window(self, tool_state, window):
        """TC05: register_window() 후 _containers에 해당 윈도우 키가 생성된다."""
        tool_state.register_window(window, "main")
        assert "main" in tool_state._containers
        assert tool_state._containers["main"] == {}


# ==============================================================================
# TC06~TC07: Container 등록
# ==============================================================================

class TestRegisterContainer:
    """register_container() 관련 테스트."""

    def test_container_stored_in_window(self, tool_state, window, container):
        """TC06: register_container() 후 해당 윈도우에 Container가 저장된다."""
        tool_state.register_window(window, "main")
        tool_state.register_container(container, "settings", "main")
        assert "settings" in tool_state._containers["main"]
        assert tool_state._containers["main"]["settings"] is container

    def test_register_container_unknown_window_ignored(self, tool_state, container):
        """TC07: 미등록 윈도우에 register_container() 호출 시 에러 없이 무시된다."""
        # 에러가 발생하지 않아야 함
        tool_state.register_container(container, "settings", "nonexistent")
        # "nonexistent" 키가 생기지 않아야 함
        assert "nonexistent" not in tool_state._containers


# ==============================================================================
# TC08~TC10: 상태 수집 (_collect_state)
# ==============================================================================

class TestCollectState:
    """_collect_state() 관련 테스트."""

    def test_collect_state_single_window_single_container(self, qapp, tmp_path):
        """TC08: 단일 윈도우 + 단일 Container 상태를 올바르게 수집한다."""
        state = ToolState("SingleWin")
        w = QtWidgets.QWidget()
        w.resize(500, 400)
        w.move(50, 60)
        c = Container("Group1")

        state.register_window(w, "main")
        state.register_container(c, "grp1", "main")

        data = state._collect_state()

        assert data["tool_name"] == "SingleWin"
        assert data["version"] == 1
        assert "main" in data["windows"]
        assert "grp1" in data["windows"]["main"]["containers"]

    def test_collect_state_multi_window_multi_container(self, qapp):
        """TC09: 멀티 윈도우 + 멀티 Container 상태를 올바르게 수집한다."""
        state = ToolState("MultiWin")
        w1 = QtWidgets.QWidget()
        w2 = QtWidgets.QWidget()
        c1 = Container("Group1")
        c2 = Container("Group2")
        c3 = Container("Group3")

        state.register_window(w1, "win1")
        state.register_window(w2, "win2")
        state.register_container(c1, "grp1", "win1")
        state.register_container(c2, "grp2", "win1")
        state.register_container(c3, "grp3", "win2")

        data = state._collect_state()

        assert "win1" in data["windows"]
        assert "win2" in data["windows"]
        assert "grp1" in data["windows"]["win1"]["containers"]
        assert "grp2" in data["windows"]["win1"]["containers"]
        assert "grp3" in data["windows"]["win2"]["containers"]

    def test_collect_state_container_expanded(self, qapp):
        """TC10: expanded Container의 상태가 True로 수집된다."""
        state = ToolState("ExpandedTest")
        w = QtWidgets.QWidget()
        c = Container("Group1")
        c.expand()  # 명시적으로 expand

        state.register_window(w, "main")
        state.register_container(c, "grp", "main")

        data = state._collect_state()
        assert data["windows"]["main"]["containers"]["grp"]["expanded"] is True

    def test_collect_state_container_collapsed(self, qapp):
        """TC10: collapsed Container의 상태가 False로 수집된다."""
        state = ToolState("CollapsedTest")
        w = QtWidgets.QWidget()
        c = Container("Group1")
        c.collapse()  # 접기

        state.register_window(w, "main")
        state.register_container(c, "grp", "main")

        data = state._collect_state()
        assert data["windows"]["main"]["containers"]["grp"]["expanded"] is False


# ==============================================================================
# TC11~TC13: JSON 저장/로드
# ==============================================================================

class TestSave:
    """save() 관련 테스트."""

    def test_save_creates_json_file(self, qapp, tmp_path):
        """TC11: save() 후 JSON 파일이 생성된다."""
        state = ToolState("SaveTest")
        settingsPath = str(tmp_path / "SaveTest_setting.json")
        state._settingsPath = settingsPath

        w = QtWidgets.QWidget()
        state.register_window(w, "main")

        state.save()

        assert os.path.isfile(settingsPath)

    def test_save_json_content_structure(self, qapp, tmp_path):
        """TC12: save() 후 JSON 파일의 구조, tool_name, version이 올바르다."""
        state = ToolState("StructureTest")
        settingsPath = str(tmp_path / "StructureTest_setting.json")
        state._settingsPath = settingsPath

        w = QtWidgets.QWidget()
        state.register_window(w, "main")

        state.save()

        with open(settingsPath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["tool_name"] == "StructureTest"
        assert data["version"] == 1
        assert "windows" in data
        assert "main" in data["windows"]
        assert "geometry" in data["windows"]["main"]
        assert "containers" in data["windows"]["main"]

    def test_save_without_settings_path_ignored(self, qapp):
        """TC13: _settingsPath 미설정 시 save() 호출이 에러 없이 무시된다."""
        state = ToolState("NoPathTest")
        w = QtWidgets.QWidget()
        state.register_window(w, "main")

        # 에러가 발생하지 않아야 함
        state.save()


# ==============================================================================
# TC14~TC17: 상태 복원
# ==============================================================================

class TestRestore:
    """restore() 관련 테스트."""

    def test_restore_window_geometry(self, qapp, tmp_path):
        """TC14: restore() 후 윈도우 geometry가 복원된다."""
        # 먼저 상태 저장
        state = ToolState("GeoRestore")
        settingsPath = str(tmp_path / "GeoRestore_setting.json")
        state._settingsPath = settingsPath

        w = QtWidgets.QWidget()
        w.move(200, 150)
        w.resize(600, 500)
        state.register_window(w, "main")
        state.save()

        # 새 윈도우와 ToolState로 복원
        state2 = ToolState("GeoRestore")
        state2._settingsPath = settingsPath
        w2 = QtWidgets.QWidget()
        w2.move(0, 0)
        w2.resize(100, 100)
        state2.register_window(w2, "main")
        state2.restore()

        assert w2.width() == 600
        assert w2.height() == 500

    def test_restore_container_expand_collapse(self, qapp, tmp_path):
        """TC15: restore() 후 Container expand/collapse 상태가 복원된다."""
        # 상태 저장 (하나는 expanded, 하나는 collapsed)
        state = ToolState("ContainerRestore")
        settingsPath = str(tmp_path / "ContainerRestore_setting.json")
        state._settingsPath = settingsPath

        w = QtWidgets.QWidget()
        cExpanded = Container("Expanded")
        cCollapsed = Container("Collapsed")
        cExpanded.expand()
        cCollapsed.collapse()

        state.register_window(w, "main")
        state.register_container(cExpanded, "exp", "main")
        state.register_container(cCollapsed, "col", "main")
        state.save()

        # 새 상태로 복원
        state2 = ToolState("ContainerRestore")
        state2._settingsPath = settingsPath
        w2 = QtWidgets.QWidget()
        cExp2 = Container("Expanded")
        cCol2 = Container("Collapsed")
        # 초기 상태를 반전시켜 복원이 실제로 동작하는지 확인
        cExp2.collapse()
        cCol2.expand()

        state2.register_window(w2, "main")
        state2.register_container(cExp2, "exp", "main")
        state2.register_container(cCol2, "col", "main")
        state2.restore()

        # isVisible()은 부모가 show()된 경우에만 True이므로
        # 명시적 hidden 상태를 나타내는 not isHidden()으로 검증한다.
        assert not cExp2.contentWidget.isHidden()
        assert cCol2.contentWidget.isHidden()

    def test_restore_no_file_ignored(self, qapp, tmp_path):
        """TC16: 파일이 없을 때 restore()가 에러 없이 무시된다."""
        state = ToolState("NoFileRestore")
        settingsPath = str(tmp_path / "nonexistent.json")
        state._settingsPath = settingsPath

        w = QtWidgets.QWidget()
        state.register_window(w, "main")

        # 에러가 발생하지 않아야 함
        state.restore()

    def test_restore_unknown_window_data_ignored(self, qapp, tmp_path):
        """TC17: JSON에 등록되지 않은 윈도우 데이터가 있어도 에러 없이 무시된다."""
        # 미등록 윈도우 데이터가 포함된 JSON 직접 작성
        settingsPath = str(tmp_path / "UnknownWin_setting.json")
        fakeData = {
            "tool_name": "UnknownWin",
            "version": 1,
            "windows": {
                "ghost_window": {
                    "geometry": {"x": 100, "y": 100, "width": 400, "height": 300},
                    "containers": {
                        "ghost_container": {"expanded": True}
                    }
                }
            }
        }
        with open(settingsPath, "w", encoding="utf-8") as f:
            json.dump(fakeData, f)

        state = ToolState("UnknownWin")
        state._settingsPath = settingsPath
        w = QtWidgets.QWidget()
        state.register_window(w, "real_window")

        # 에러가 발생하지 않아야 함
        state.restore()


# ==============================================================================
# TC18: 멀티 윈도우 독립 저장/복원
# ==============================================================================

class TestMultiWindow:
    """멀티 윈도우 시나리오 테스트."""

    def test_two_windows_independent_save_restore(self, qapp, tmp_path):
        """TC18: 2개 윈도우 각각의 상태가 독립적으로 저장/복원된다."""
        state = ToolState("MultiWindowTest")
        settingsPath = str(tmp_path / "MultiWindowTest_setting.json")
        state._settingsPath = settingsPath

        w1 = QtWidgets.QWidget()
        w2 = QtWidgets.QWidget()
        w1.move(10, 20)
        w1.resize(300, 200)
        w2.move(400, 300)
        w2.resize(500, 400)

        state.register_window(w1, "win1")
        state.register_window(w2, "win2")
        state.save()

        # 새 상태로 복원
        state2 = ToolState("MultiWindowTest")
        state2._settingsPath = settingsPath
        nw1 = QtWidgets.QWidget()
        nw2 = QtWidgets.QWidget()
        nw1.resize(100, 100)
        nw2.resize(100, 100)

        state2.register_window(nw1, "win1")
        state2.register_window(nw2, "win2")
        state2.restore()

        assert nw1.width() == 300
        assert nw1.height() == 200
        assert nw2.width() == 500
        assert nw2.height() == 400


# ==============================================================================
# TC19~TC20: 자동 저장 (eventFilter)
# ==============================================================================

class TestEventFilter:
    """eventFilter() 자동 저장 관련 테스트."""

    def test_close_event_triggers_save(self, qapp, tmp_path, monkeypatch):
        """TC19: 등록된 윈도우에 Close 이벤트 발생 시 save()가 호출된다."""
        state = ToolState("AutoSaveTest")
        settingsPath = str(tmp_path / "AutoSaveTest_setting.json")
        state._settingsPath = settingsPath

        saveCalled = []

        def _mock_save():
            saveCalled.append(True)

        monkeypatch.setattr(state, "save", _mock_save)

        w = QtWidgets.QWidget()
        state.register_window(w, "main")

        # Close 이벤트 직접 전달
        closeEvent = QtCore.QEvent(QtCore.QEvent.Close)
        state.eventFilter(w, closeEvent)

        assert len(saveCalled) == 1

    def test_close_event_unregistered_object_no_save(self, qapp, monkeypatch):
        """TC20: 미등록 객체의 Close 이벤트는 save()를 호출하지 않는다."""
        state = ToolState("NoAutoSaveTest")

        saveCalled = []

        def _mock_save():
            saveCalled.append(True)

        monkeypatch.setattr(state, "save", _mock_save)

        # 등록되지 않은 객체
        outsideWidget = QtWidgets.QWidget()

        closeEvent = QtCore.QEvent(QtCore.QEvent.Close)
        state.eventFilter(outsideWidget, closeEvent)

        assert len(saveCalled) == 0

    def test_event_filter_returns_false(self, qapp):
        """eventFilter()는 항상 False를 반환하여 이벤트를 소비하지 않는다."""
        state = ToolState("ReturnFalseTest")
        w = QtWidgets.QWidget()
        state.register_window(w, "main")

        closeEvent = QtCore.QEvent(QtCore.QEvent.Close)
        result = state.eventFilter(w, closeEvent)

        assert result is False


# ==============================================================================
# TC21~TC25: 커스텀 데이터 (Task 1-5)
# ==============================================================================

class TestCustomData:
    """custom_data 저장/복원 관련 테스트."""

    def test_set_and_get_custom_value_roundtrip(self, tool_state):
        """TC21: set_custom_value() 후 get_custom_value()로 같은 값을 반환한다."""
        tool_state.set_custom_value("mode", "export")
        tool_state.set_custom_value("count", 42)
        tool_state.set_custom_value("flag", True)

        assert tool_state.get_custom_value("mode") == "export"
        assert tool_state.get_custom_value("count") == 42
        assert tool_state.get_custom_value("flag") is True

    def test_collect_state_includes_custom_data(self, tool_state):
        """TC22: _collect_state()에 custom_data가 포함된다."""
        tool_state.set_custom_value("selectedIndex", 3)
        tool_state.set_custom_value("lastPath", "/some/path")

        data = tool_state._collect_state()

        assert "custom_data" in data
        assert data["custom_data"]["selectedIndex"] == 3
        assert data["custom_data"]["lastPath"] == "/some/path"

    def test_apply_state_restores_custom_data(self, tool_state):
        """TC23: _apply_state()로 custom_data가 복원된다."""
        stateData = {
            "tool_name": "TestTool",
            "version": 1,
            "windows": {},
            "custom_data": {
                "preset": "high_quality",
                "frameRange": [0, 100]
            }
        }

        tool_state._apply_state(stateData)

        assert tool_state.get_custom_value("preset") == "high_quality"
        assert tool_state.get_custom_value("frameRange") == [0, 100]

    def test_apply_state_without_custom_data_key_returns_empty_dict(self, tool_state):
        """TC24: custom_data 키 없는 기존 JSON 로드 시 _customData가 빈 딕셔너리 (하위 호환)."""
        legacyStateData = {
            "tool_name": "TestTool",
            "version": 1,
            "windows": {}
            # custom_data 키 없음
        }

        tool_state._apply_state(legacyStateData)

        assert tool_state._customData == {}

    def test_get_custom_value_returns_default_when_key_missing(self, tool_state):
        """TC25: get_custom_value()에 존재하지 않는 키를 조회하면 기본값을 반환한다."""
        # 기본값 None
        assert tool_state.get_custom_value("nonexistent") is None

        # 명시적 기본값
        assert tool_state.get_custom_value("nonexistent", "fallback") == "fallback"
        assert tool_state.get_custom_value("missing_int", 0) == 0
