"""Perforce 서비스 계층.

유스케이스(체인지리스트/파일/동기화/조회)를 캡슐화하고
어댑터를 통해 P4Python을 호출합니다.
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from .adapter import P4Adapter
from .dtos import ChangeListInfo, FileInfo
from ..exceptions import PerforceError, ValidationError
from P4 import P4Exception


class PerforceService:
    """Perforce 작업을 수행하는 서비스."""

    def __init__(self, in_adapter: P4Adapter, in_auto_revert_unchanged: bool = True) -> None:
        self.adapter = in_adapter
        self.autoRevertUnchanged = in_auto_revert_unchanged

    # ------------------------
    # 연결/가드
    # ------------------------
    @property
    def is_connected(self) -> bool:
        return self.adapter.connected

    def require_connected(self) -> None:
        if not self.is_connected:
            raise PerforceError("Perforce 서버에 연결되지 않았습니다.")

    def connect(self, in_workspace_name: str) -> None:
        self.adapter.connect(in_workspace_name)

    def disconnect(self) -> None:
        self.adapter.disconnect()

    # ------------------------
    # 체인지리스트
    # ------------------------
    def get_pending_changelists(self) -> List[ChangeListInfo]:
        self.require_connected()
        try:
            pending = self.adapter.run_changes("-s", "pending", "-u", self.adapter.p4.user, "-c", self.adapter.p4.client)
            result: List[ChangeListInfo] = []
            for cl in pending:
                cl_num = int(cl.get("change", 0))
                fetched = self.adapter.run_change_fetch(cl_num)
                result.append(
                    ChangeListInfo(
                        id=fetched.get("Change"),
                        description=fetched.get("Description", ""),
                        status=fetched.get("Status", "pending"),
                        user=fetched.get("User", self.adapter.p4.user),
                        client=fetched.get("Client", self.adapter.p4.client),
                        files=fetched.get("Files", []) or [],
                    )
                )
            return result
        except P4Exception as e:
            raise PerforceError(f"Pending 체인지 리스트 조회 실패: {e}")

    def create_changelist(self, in_description: str) -> ChangeListInfo:
        self.require_connected()
        try:
            spec = self.adapter.run_change_create()
            spec["Description"] = in_description
            saved = self.adapter.run_change_save(spec)
            created_id = None
            try:
                created_id = int(str(saved[0]).split()[1])
            except Exception:
                raise PerforceError("체인지 리스트 생성 번호 파싱 실패")
            fetched = self.adapter.run_change_fetch(created_id)
            return ChangeListInfo(
                id=fetched.get("Change"),
                description=fetched.get("Description", ""),
                status=fetched.get("Status", "pending"),
                user=fetched.get("User", self.adapter.p4.user),
                client=fetched.get("Client", self.adapter.p4.client),
                files=fetched.get("Files", []) or [],
            )
        except P4Exception as e:
            raise PerforceError(f"체인지 리스트 생성 실패: {e}")

    def get_changelist_by_number(self, in_changelist_id: int) -> ChangeListInfo:
        self.require_connected()
        try:
            fetched = self.adapter.run_change_fetch(in_changelist_id)
            if not fetched:
                raise PerforceError(f"체인지 리스트 {in_changelist_id}를 찾을 수 없습니다.")
            return ChangeListInfo(
                id=fetched.get("Change"),
                description=fetched.get("Description", ""),
                status=fetched.get("Status", "pending"),
                user=fetched.get("User", self.adapter.p4.user),
                client=fetched.get("Client", self.adapter.p4.client),
                files=fetched.get("Files", []) or [],
            )
        except P4Exception as e:
            raise PerforceError(f"체인지 리스트 조회 실패: {e}")

    def edit_changelist(
        self,
        in_changelist_id: int,
        in_description: Optional[str] = None,
        in_add_paths: Optional[List[str]] = None,
        in_remove_paths: Optional[List[str]] = None,
    ) -> ChangeListInfo:
        self.require_connected()
        try:
            if in_description is not None:
                spec = self.adapter.run_change_fetch(in_changelist_id)
                if (spec.get("Description", "").strip() or "") != (in_description or "").strip():
                    spec["Description"] = in_description
                    self.adapter.run_change_save(spec)

            if in_add_paths:
                self.adapter.run_reopen(in_add_paths, in_changelist_id)

            if in_remove_paths:
                self.adapter.run_revert(in_remove_paths, in_changelist_id)

            return self.get_changelist_by_number(in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"체인지 리스트 편집 실패: {e}")

    def submit_changelist(self, in_changelist_id: int, in_auto_revert_unchanged: Optional[bool] = None) -> None:
        self.require_connected()
        try:
            auto_flag = self.autoRevertUnchanged if in_auto_revert_unchanged is None else in_auto_revert_unchanged
            if auto_flag:
                # 제출 전에 변경사항 없는 파일들을 먼저 리버트
                try:
                    self.adapter.run_revert(["//..."], in_changelist_id, in_only_unchanged=True)
                except P4Exception:
                    # revert -a 실패는 무시 (파일이 없거나 이미 정리된 경우)
                    pass
            
            # 실제 변경된 파일들만 제출
            self.adapter.run_submit(in_changelist_id)
            
            # 제출 후에도 default CL 정리 (제출 과정에서 default로 이동한 변경되지 않은 파일들 처리)
            if auto_flag:
                try:
                    self.adapter.run_revert(["//..."], None, in_only_unchanged=True)
                except P4Exception:
                    # revert -a 실패는 무시
                    pass
        except P4Exception as e:
            raise PerforceError(f"체인지 리스트 제출 실패: {e}")

    def revert_changelist(self, in_changelist_id: int) -> None:
        self.require_connected()
        try:
            self.adapter.run_revert(["//..."], in_changelist_id)
            self.adapter.run_change_delete(in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"체인지 리스트 되돌리기 실패: {e}")

    def delete_empty_changelist(self, in_changelist_id: int) -> None:
        self.require_connected()
        try:
            spec = self.adapter.run_change_fetch(in_changelist_id)
            files = spec.get("Files") or []
            if files:
                raise PerforceError(f"체인지 리스트 {in_changelist_id}에 파일이 {len(files)}개 있어 삭제할 수 없습니다.")
            self.adapter.run_change_delete(in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"체인지 리스트 삭제 실패: {e}")

    def get_default_changelist(self) -> ChangeListInfo:
        self.require_connected()
        try:
            opened = self.adapter.run_opened(in_changelist_id="default")
            files_list = [f.get("clientFile", "") for f in opened]
        except P4Exception as e:
            raise PerforceError(f"default change list 조회 실패: {e}")
        return ChangeListInfo(
            id="default",
            description="Default change",
            status="pending",
            user=self.adapter.p4.user,
            client=self.adapter.p4.client,
            files=files_list,
        )

    # ------------------------
    # 파일 상태/체크아웃
    # ------------------------
    def is_in_perforce(self, in_paths: List[str]) -> Dict[str, bool]:
        self.require_connected()
        if not isinstance(in_paths, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        result: Dict[str, bool] = {}
        if not in_paths:
            return result
        try:
            files_info = self.adapter.run_files(in_paths)
        except P4Exception as e:
            raise PerforceError(f"Perforce 포함 여부 확인 실패: {e}")
        found_set = set()
        for item in files_info:
            depot_file = item.get("depotFile") or item.get("clientFile") or ""
            # where로 clientFile 매핑을 얻을 수 있지만, 여기서는 간단히 Path 정규화만 수행
            try:
                client_file = item.get("clientFile") or ""
                if client_file:
                    found_set.add(str(Path(client_file).resolve()))
            except Exception:
                pass
        for p in in_paths:
            result[str(Path(p).resolve())] = str(Path(p).resolve()) in found_set or bool(files_info)
        return result

    def _parse_opened_entry(self, in_entry: Dict[str, Any]) -> FileInfo:
        user = in_entry.get("user", "")
        client = in_entry.get("client", "")
        action = in_entry.get("action", "")
        change = in_entry.get("change")
        change_int = None
        try:
            change_int = int(change) if change is not None else None
        except Exception:
            change_int = None
        client_file = in_entry.get("clientFile", "")
        is_current = (user == self.adapter.p4.user) and (client == self.adapter.p4.client)
        return FileInfo(
            path=client_file,
            inPerforce=True,
            isCheckedOut=True,
            changeList=change_int,
            action=action,
            user=user,
            client=client,
            isCurrentUser=is_current,
            isOthers=not is_current,
        )

    def get_checkout_status(self, in_paths: List[str], in_scope: str = "current") -> Dict[str, FileInfo]:
        self.require_connected()
        if not isinstance(in_paths, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        result: Dict[str, FileInfo] = {}
        if not in_paths:
            return result
        all_users = in_scope == "all"
        for p in in_paths:
            result[str(Path(p).resolve())] = FileInfo(
                path=str(Path(p).resolve()),
                inPerforce=False,
                isCheckedOut=False,
            )
        try:
            opened = self.adapter.run_opened(in_paths, in_all_users=all_users)
        except P4Exception as e:
            raise PerforceError(f"체크아웃 상태 조회 실패: {e}")
        if opened:
            # 여러 항목 중 첫 항목 우선 적용
            by_path: Dict[str, FileInfo] = {}
            for entry in opened:
                fi = self._parse_opened_entry(entry)
                norm = str(Path(fi.path).resolve()) if fi.path else ""
                if norm:
                    by_path.setdefault(norm, fi)
            result.update(by_path)
        return result

    # ------------------------
    # 파일 작업(배치)
    # ------------------------
    def checkout(self, in_paths: List[str], in_changelist_id: Union[int, str]) -> None:
        self.require_connected()
        if not in_paths:
            return
        if not isinstance(in_paths, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        try:
            self.adapter.run_edit(in_paths, in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"파일 체크아웃 실패: {e}")

    def add(self, in_paths: List[str], in_changelist_id: Union[int, str]) -> None:
        self.require_connected()
        if not in_paths:
            return
        if not isinstance(in_paths, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        try:
            self.adapter.run_add(in_paths, in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"파일 추가 실패: {e}")

    def delete(self, in_paths: List[str], in_changelist_id: Union[int, str]) -> None:
        self.require_connected()
        if not in_paths:
            return
        if not isinstance(in_paths, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        try:
            self.adapter.run_delete(in_paths, in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"파일 삭제 실패: {e}")

    def revert(self, in_paths: List[str], in_changelist_id: Optional[Union[int, str]] = None) -> None:
        self.require_connected()
        if not in_paths:
            return
        if not isinstance(in_paths, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        try:
            self.adapter.run_revert(in_paths, in_changelist_id)
        except P4Exception as e:
            raise PerforceError(f"파일 되돌리기 실패: {e}")

    # ------------------------
    # 동기화/프리뷰
    # ------------------------
    def check_update_required(self, in_paths_or_dirs: List[str]) -> bool:
        self.require_connected()
        if not in_paths_or_dirs:
            return False
        if not isinstance(in_paths_or_dirs, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths_or_dirs).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        processed: List[str] = []
        for p in in_paths_or_dirs:
            pth = Path(p)
            if pth.exists() and pth.is_dir():
                processed.append(str(pth / "..."))
            elif pth.exists() and pth.is_file():
                processed.append(str(pth))
            else:
                raise PerforceError(f"파일 또는 폴더가 존재하지 않습니다. 경로: {p}")
        try:
            preview = self.adapter.run_sync(processed, in_preview=True)
        except P4Exception as e:
            # up-to-date류 메시지는 호출자에서 중립 처리 가능
            # 여기서는 예외 문자열 확인 없이 상위로 래핑
            raise PerforceError(f"업데이트 필요 여부 확인 실패: {e}")
        for r in preview:
            if isinstance(r, dict):
                how = r.get("how", "")
                action = r.get("action", "")
                if (how and "syncing" in how) or (action and action not in ["checked", "exists"]):
                    return True
            elif isinstance(r, str):
                if "up-to-date" not in r and "no such file(s)" not in r:
                    return True
        return False

    def sync(self, in_paths_or_dirs: List[str]) -> None:
        self.require_connected()
        if not in_paths_or_dirs:
            return
        if not isinstance(in_paths_or_dirs, list):
            raise ValidationError(
                f"paths는 리스트여야 합니다. 전달된 타입: {type(in_paths_or_dirs).__name__}. 단일 경로도 리스트로 감싸서 전달하세요."
            )
        processed: List[str] = []
        for p in in_paths_or_dirs:
            pth = Path(p)
            if pth.exists() and pth.is_dir():
                processed.append(str(pth / "..."))
            elif pth.exists() and pth.is_file():
                processed.append(str(pth))
            else:
                raise PerforceError(f"파일 또는 폴더가 존재하지 않습니다. 경로: {p}")
        try:
            self.adapter.run_sync(processed, in_preview=False)
        except P4Exception as e:
            raise PerforceError(f"파일/폴더 동기화 실패: {e}")


