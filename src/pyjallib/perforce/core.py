# -*- coding: utf-8 -*-
"""Perforce 래퍼 본체 - Mixin 조립 + 생성자·연결·경로 정규화.

`pyjallib/perforce.py`(1,671줄)를 2026-09-18 ExportToolsRefactor Phase 10에서 책임 축별 Mixin
서브패키지로 분해했다. 메서드 본문은 무변경 이동이고(`P4()` 생성 호출만 패키지 이름 조회로),
연결 객체 생성의 공통화(`_new_p4()`)는 하지 않았다. 외부 import 경로는 패키지 `__init__`이 유지한다.
"""

from P4 import P4Exception
from pathlib import Path
from typing import List, Union

# 연결 객체 생성은 `pyjallib.perforce.P4`(패키지 이름)를 **호출 시점에** 조회한다.
# 소비처·테스트가 `patch("pyjallib.perforce.P4", ...)`로 대역을 꽂는 주입점을 분해 전과 같게 유지하기 위해서다
# (모듈 전역 `P4`를 쓰면 패키지 속성을 바꿔도 이 모듈에는 닿지 않는다).
from pyjallib import perforce as _perforcePackage
from pyjallib.perforce.openedMove import OpenedFilesCollectResult  # noqa: F401 - 재노출
from pyjallib.perforce.changeList import _ChangeListMixin
from pyjallib.perforce.fileOps import _FileOpsMixin
from pyjallib.perforce.fileStatus import _FileStatusMixin
from pyjallib.perforce.openedMove import _OpenedMoveMixin
from pyjallib.perforce.sync import _SyncMixin


class Perforce(_ChangeListMixin, _FileOpsMixin, _FileStatusMixin, _OpenedMoveMixin, _SyncMixin):
    """
    Perforce 작업을 위한 단순화된 클래스
    각 메서드는 독립적으로 P4 인스턴스를 생성하고 연결/실행/종료합니다.
    """

    def __init__(self, port: str, user: str):
        """
        Perforce 객체 초기화

        Args:
            port: Perforce 서버 주소 (예: "localhost:1666")
            user: Perforce 사용자 이름
        """
        self.port = port
        self.user = user
        self.workspace_name = None
        self.workspaceRoot = None
        self.charset = "utf8"
        self.exception_level = 1

    def connect(self, workspace_name: str) -> bool:
        """
        워크스페이스 이름 저장

        Args:
            workspace_name: Perforce 워크스페이스 이름

        Returns:
            bool: 성공 여부
        """
        self.workspace_name = workspace_name

        # 워크스페이스 루트 경로 가져오기
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()
            client_spec = p4.run("client", "-o", workspace_name)[0]
            self.workspaceRoot = client_spec.get('Root', '')
            return True
        except P4Exception as e:
            print(f"워크스페이스 연결 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def disconnect(self) -> None:
        """저장된 워크스페이스 정보 초기화"""
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()
            p4.disconnect()
        except P4Exception:
            # 연결 실패해도 무시하고 정리 진행
            pass
        finally:
            # Instance 변수 초기화
            self.workspace_name = None
            self.workspaceRoot = None

    def _normalize_path(self, path: Union[str, Path]) -> str:
        """
        경로를 Windows 절대경로로 정규화

        Args:
            path: 정규화할 경로

        Returns:
            str: 정규화된 절대경로
        """
        return str(Path(path).resolve())

    def _normalize_paths(self, paths: Union[str, Path, List[Union[str, Path]]]) -> List[str]:
        """
        경로 리스트를 정규화

        Args:
            paths: 정규화할 경로 또는 경로 리스트

        Returns:
            List[str]: 정규화된 경로 리스트
        """
        if isinstance(paths, (str, Path)):
            return [self._normalize_path(paths)]
        return [self._normalize_path(p) for p in paths]
