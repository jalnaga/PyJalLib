# -*- coding: utf-8 -*-
"""
ToolState - 툴 UI 상태 저장/복원 모듈.

3ds Max PySide2 툴의 UI 상태(윈도우 위치/크기, Container expand/collapse)를
JSON 파일로 저장하고 복원하는 기능을 제공한다.
"""

import json
import os
from typing import TYPE_CHECKING

from PySide2 import QtWidgets, QtCore

try:
    from pymxs import runtime as rt
    _HAS_PYMXS = True
except ImportError:
    _HAS_PYMXS = False

if TYPE_CHECKING:
    from pyjallib.max.ui.Container import Container


class ToolState(QtCore.QObject):
    """툴 UI 상태를 JSON으로 저장/복원하는 클래스.

    QObject를 상속하여 eventFilter를 통해 윈도우 Close 이벤트를 감지하고
    자동으로 상태를 저장한다.

    Examples:
        >>> state = ToolState("MyTool")
        >>> state.register_window(mainWindow, "main")
        >>> state.register_container(rollout1, "export_settings", inWindowName="main")
        >>> state.restore()
        >>> # 윈도우 닫힐 때 자동 저장 (eventFilter)
        >>> state.save()  # 수동 저장도 가능
    """

    def __init__(self, inToolName: str) -> None:
        """ToolState 인스턴스를 초기화한다.

        Args:
            inToolName: 툴 이름. 설정 파일명에 사용된다.
        """
        super().__init__()
        self._toolName: str = inToolName
        self._windows: dict[str, QtWidgets.QWidget] = {}
        self._containers: dict[str, dict[str, "Container"]] = {}
        self._settingsPath: str | None = None

    def _get_settings_path(self) -> str:
        """설정 파일 경로를 반환한다.

        pymxs가 사용 가능하면 3ds Max의 plugcfg 디렉토리를 기준으로 경로를 결정한다.
        pymxs가 없는 환경(테스트 등)에서는 빈 문자열을 반환한다.
        _settingsPath가 이미 외부에서 설정되어 있으면 그 값을 그대로 반환한다.

        Returns:
            설정 파일의 절대 경로. pymxs가 없으면 빈 문자열.
        """
        if self._settingsPath is not None:
            return self._settingsPath

        if _HAS_PYMXS:
            plugcfgDir = rt.getDir(rt.name("plugcfg"))
            self._settingsPath = os.path.join(str(plugcfgDir), f"{self._toolName}_setting.json")
            return self._settingsPath

        return ""

    def register_window(self, inWindow: QtWidgets.QWidget, inName: str) -> None:
        """윈도우를 상태 관리 대상으로 등록한다.

        등록된 윈도우는 Close 이벤트 시 자동으로 상태가 저장된다.

        Args:
            inWindow: 등록할 QWidget 또는 QDialog
            inName: 윈도우 식별 이름
        """
        self._windows[inName] = inWindow
        self._containers[inName] = {}
        inWindow.installEventFilter(self)

    def register_container(self, inContainer: "Container", inName: str, inWindowName: str) -> None:
        """Container를 지정된 윈도우에 연결 등록한다.

        등록되지 않은 윈도우 이름이 전달되면 경고 없이 무시한다.

        Args:
            inContainer: 등록할 Container 위젯
            inName: Container 식별 이름
            inWindowName: Container가 속할 윈도우 이름
        """
        if inWindowName not in self._containers:
            return
        self._containers[inWindowName][inName] = inContainer

    def _collect_state(self) -> dict:
        """등록된 모든 윈도우와 Container에서 현재 상태를 수집한다.

        삭제된 위젯에 접근할 경우 기본값(expanded=True)으로 처리한다.

        Returns:
            PRD에 정의된 JSON 구조 형태의 딕셔너리.
        """
        stateData: dict = {
            "tool_name": self._toolName,
            "version": 1,
            "windows": {}
        }

        for windowName, window in self._windows.items():
            windowState: dict = {
                "geometry": {
                    "x": window.x(),
                    "y": window.y(),
                    "width": window.width(),
                    "height": window.height()
                },
                "containers": {}
            }

            if windowName in self._containers:
                for containerName, container in self._containers[windowName].items():
                    try:
                        expanded = not container.contentWidget.isHidden()
                    except (RuntimeError, AttributeError):
                        expanded = True
                    windowState["containers"][containerName] = {
                        "expanded": expanded
                    }

            stateData["windows"][windowName] = windowState

        return stateData

    def save(self) -> None:
        """현재 UI 상태를 JSON 파일에 저장한다.

        _get_settings_path()가 빈 문자열을 반환하면 저장하지 않는다.
        파일 쓰기 실패 시 조용히 무시한다 (eventFilter에서 자동 호출되므로 예외 전파 방지).
        """
        settingsPath = self._get_settings_path()
        if not settingsPath:
            return

        stateData = self._collect_state()

        try:
            with open(settingsPath, "w", encoding="utf-8") as f:
                json.dump(stateData, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _apply_state(self, inStateData: dict) -> None:
        """저장된 상태 데이터를 등록된 윈도우와 Container에 적용한다.

        등록되지 않은 윈도우나 Container는 무시한다.

        Args:
            inStateData: JSON에서 로드한 상태 딕셔너리
        """
        windowsData = inStateData.get("windows", {})

        for windowName, windowState in windowsData.items():
            if windowName not in self._windows:
                continue

            window = self._windows[windowName]
            geometry = windowState.get("geometry", {})

            if "x" in geometry and "y" in geometry:
                window.move(geometry["x"], geometry["y"])
            if "width" in geometry and "height" in geometry:
                window.resize(geometry["width"], geometry["height"])

            containersData = windowState.get("containers", {})
            if windowName not in self._containers:
                continue

            for containerName, containerState in containersData.items():
                if containerName not in self._containers[windowName]:
                    continue

                container = self._containers[windowName][containerName]
                if containerState.get("expanded", True):
                    container.expand()
                else:
                    container.collapse()

    def restore(self) -> None:
        """JSON 파일에서 UI 상태를 읽어 복원한다.

        파일이 없거나 경로가 비어있으면 무시한다 (첫 실행 시 정상 동작).
        손상된 JSON이나 파일 읽기 실패 시에도 조용히 무시한다.
        """
        settingsPath = self._get_settings_path()
        if not settingsPath:
            return

        if not os.path.isfile(settingsPath):
            return

        try:
            with open(settingsPath, "r", encoding="utf-8") as f:
                stateData = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        self._apply_state(stateData)

    def eventFilter(self, inObj: QtCore.QObject, inEvent: QtCore.QEvent) -> bool:
        """이벤트 필터. 등록된 윈도우의 Close 이벤트를 감지하여 자동 저장한다.

        Args:
            inObj: 이벤트가 발생한 객체
            inEvent: 발생한 이벤트

        Returns:
            이벤트를 소비하지 않고 부모 클래스에 전달한다.
        """
        if inEvent.type() == QtCore.QEvent.Close:
            if inObj in self._windows.values():
                self.save()

        return super().eventFilter(inObj, inEvent)
