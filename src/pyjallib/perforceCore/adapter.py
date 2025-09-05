"""P4Python 어댑터.

P4 호출을 캡슐화하고, 예외/경로 정규화를 담당합니다.
"""

from typing import List, Union, Any, Dict, Optional
from pathlib import Path

from P4 import P4, P4Exception

from ..exceptions import PerforceError


class P4Adapter:
    """P4Python 호출을 래핑하는 어댑터 클래스."""

    def __init__(self) -> None:
        """어댑터를 초기화합니다."""
        self.p4 = P4()
        # 경고성 메시지를 예외로 올리지 않도록 설정
        try:
            self.p4.exception_level = 1
        except Exception:
            # 일부 환경에서 속성이 없을 수 있음
            pass
        self.connected: bool = False
        self.workspaceRoot: str = ""

    # ------------------------
    # 연결 관리
    # ------------------------
    def connect(self, in_client_name: str) -> None:
        """클라이언트(워크스페이스)에 연결합니다."""
        try:
            self.p4.client = in_client_name
            self.p4.connect()
            self.connected = True
            # 워크스페이스 루트 캐싱
            try:
                client_info = self.p4.run_client("-o", in_client_name)[0]
                root_path = client_info.get("Root", "")
                self.workspaceRoot = str(Path(root_path).resolve())
            except Exception:
                self.workspaceRoot = ""
        except P4Exception as e:
            self.connected = False
            raise PerforceError(f"'{in_client_name}' 워크스페이스 연결 실패: {e}")

    def disconnect(self) -> None:
        """서버 연결을 해제합니다."""
        if not self.connected:
            return
        try:
            self.p4.disconnect()
            self.connected = False
        except P4Exception as e:
            raise PerforceError(f"Perforce 서버 연결 해제 실패: {e}")

    # ------------------------
    # 유틸리티
    # ------------------------
    def _normalize_win_path(self, in_path: Union[str, Path]) -> str:
        """Windows 절대경로 형태로 정규화합니다."""
        return str(Path(in_path).resolve())

    def _normalize_multiple(self, in_paths: Union[str, Path, List[Union[str, Path]]]) -> List[str]:
        if isinstance(in_paths, (str, Path)):
            return [self._normalize_win_path(in_paths)]
        return [self._normalize_win_path(p) for p in in_paths]

    # ------------------------
    # 파일/체인지리스트 메소드
    # ------------------------
    def run_edit(self, in_paths: List[Union[str, Path]], in_changelist_id: Union[int, str]) -> Any:
        paths = self._normalize_multiple(in_paths)
        return self.p4.run_edit("-c", in_changelist_id, *paths)

    def run_add(self, in_paths: List[Union[str, Path]], in_changelist_id: Union[int, str]) -> Any:
        paths = self._normalize_multiple(in_paths)
        return self.p4.run_add("-c", in_changelist_id, *paths)

    def run_delete(self, in_paths: List[Union[str, Path]], in_changelist_id: Union[int, str]) -> Any:
        paths = self._normalize_multiple(in_paths)
        return self.p4.run_delete("-c", in_changelist_id, *paths)

    def run_reopen(self, in_paths: List[Union[str, Path]], in_changelist_id: Union[int, str]) -> Any:
        paths = self._normalize_multiple(in_paths)
        return self.p4.run_reopen("-c", in_changelist_id, *paths)

    def run_revert(
        self,
        in_paths_or_filter: Union[str, Path, List[Union[str, Path]]],
        in_changelist_id: Optional[Union[int, str]] = None,
        in_only_unchanged: bool = False,
    ) -> Any:
        paths = self._normalize_multiple(in_paths_or_filter)
        args: List[Any] = []
        if in_only_unchanged:
            args.append("-a")
        if in_changelist_id is not None:
            args.extend(["-c", in_changelist_id])
        return self.p4.run_revert(*args, *paths)

    def run_opened(
        self,
        in_paths_or_filter: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
        in_all_users: bool = False,
        in_changelist_id: Optional[Union[int, str]] = None,
    ) -> Any:
        args: List[Any] = []
        if in_all_users:
            args.append("-a")
        if in_changelist_id is not None:
            args.extend(["-c", in_changelist_id])
        if in_paths_or_filter is None:
            return self.p4.run_opened(*args)
        paths = self._normalize_multiple(in_paths_or_filter)
        return self.p4.run_opened(*args, *paths)

    def run_files(self, in_path_or_paths: Union[str, Path, List[Union[str, Path]]]) -> Any:
        paths = self._normalize_multiple(in_path_or_paths)
        return self.p4.run_files(*paths)

    def run_sync(self, in_paths_or_dirs: List[Union[str, Path]], in_preview: bool = False) -> Any:
        paths = self._normalize_multiple(in_paths_or_dirs)
        args: List[Any] = []
        if in_preview:
            args.append("-n")
        return self.p4.run_sync(*args, *paths)

    def run_change_fetch(self, in_changelist_id: Union[int, str]) -> Dict[str, Any]:
        return self.p4.fetch_change(in_changelist_id)

    def run_change_create(self) -> Dict[str, Any]:
        return self.p4.fetch_change()

    def run_change_save(self, in_change_spec: Dict[str, Any]) -> Any:
        return self.p4.save_change(in_change_spec)

    def run_change_delete(self, in_changelist_id: Union[int, str]) -> Any:
        return self.p4.run_change("-d", in_changelist_id)

    def run_submit(self, in_changelist_id: Union[int, str]) -> Any:
        return self.p4.run_submit("-c", in_changelist_id)

    def run_where(self, in_path_or_paths: Union[str, Path, List[Union[str, Path]]]) -> Any:
        paths = self._normalize_multiple(in_path_or_paths)
        return self.p4.run_where(*paths)

    def run_changes(self, *args: Any) -> Any:
        return self.p4.run_changes(*args)


