# -*- coding: utf-8 -*-
"""파일 조작 - checkout/add/delete/move/revert 배치와 단건 위임.

`Perforce`의 Mixin이다 - `pyjallib/perforce.py`(1,671줄)를 서브패키지로 분해하면서
(2026-09-18 ExportToolsRefactor Phase 10) 메서드를 **본문 무변경으로 이동**만 했다(`P4()` 생성 호출만
패키지 이름 조회로 바꿈 - 아래 주석). 인스턴스 속성(`port`/`user`/`workspace_name`/`charset`/
`exception_level`)과 `_normalize_path(s)`는 `core.Perforce`에 있다. 특성화 Type A(`tests/perforce/`)가 계약을 고정한다.
"""

from P4 import P4Exception
from typing import List, Optional, Tuple

# 연결 객체 생성은 `pyjallib.perforce.P4`(패키지 이름)를 **호출 시점에** 조회한다.
# 소비처·테스트가 `patch("pyjallib.perforce.P4", ...)`로 대역을 꽂는 주입점을 분해 전과 같게 유지하기 위해서다
# (모듈 전역 `P4`를 쓰면 패키지 속성을 바꿔도 이 모듈에는 닿지 않는다).
from pyjallib import perforce as _perforcePackage


class _FileOpsMixin:
    """파일 조작 - checkout/add/delete/move/revert 배치와 단건 위임."""

    def checkout_files(self, file_paths: List[str], change_list_number: int) -> bool:
        """
        파일들을 체크아웃

        Args:
            file_paths: 체크아웃할 파일 경로 리스트
            change_list_number: 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")
        
        if not file_paths:
            return False

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)
            print(f"Normalized: {normalized}")

            # 다른 CL에 이미 열린 파일은 대상 CL로 이어받는다 (자기 클라이언트의 오픈만 해당)
            opened_actions = self._takeover_opened_files(p4, normalized, change_list_number)

            # 아직 열려 있지 않은 파일만 체크아웃 실행.
            # delete로 열린 파일에 체크아웃(edit) 의도가 오면 삭제 마크가 남지 않도록
            # revert -k(로컬 파일 유지)로 되돌린 후 edit로 다시 연다.
            to_edit = []
            for filePath in normalized:
                action = opened_actions.get(self._comparable_path(filePath))
                if action is None:
                    to_edit.append(filePath)
                elif action in ("delete", "move/delete"):
                    p4.run("revert", "-k", filePath)
                    print(f"delete로 열려있던 파일을 edit로 전환: {filePath}")
                    to_edit.append(filePath)
            if to_edit:
                p4.run("edit", "-c", str(change_list_number), *to_edit)
            return True
        except P4Exception as e:
            print(f"체크아웃 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def add_files(self, file_paths: List[str], change_list_number: int) -> bool:
        """
        파일들을 추가

        Args:
            file_paths: 추가할 파일 경로 리스트
            change_list_number: 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")
        
        if not file_paths:
            return False

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 다른 CL에 이미 열린 파일은 대상 CL로 이어받는다 (자기 클라이언트의 오픈만 해당)
            opened_actions = self._takeover_opened_files(p4, normalized, change_list_number)

            # 이미 열린 파일은 reopen으로 대상 CL에 들어갔으므로 add를 생략하고,
            # 아직 열려 있지 않은 파일만 추가 실행
            to_add = []
            for filePath in normalized:
                action = opened_actions.get(self._comparable_path(filePath))
                if action is None:
                    to_add.append(filePath)
                elif action not in ("add", "edit", "move/add"):
                    print(f"add 요청 파일이 '{action}' 액션으로 열려있어 add를 생략함: {filePath}")
            if to_add:
                p4.run("add", "-c", str(change_list_number), *to_add)
            return True
        except P4Exception as e:
            print(f"파일 추가 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def delete_files(self, file_paths: List[str], change_list_number: int) -> bool:
        """
        파일들을 삭제 마킹

        Args:
            file_paths: 삭제할 파일 경로 리스트
            change_list_number: 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")
        
        if not file_paths:
            return False

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 다른 CL에 이미 열린 파일은 대상 CL로 이어받는다 (자기 클라이언트의 오픈만 해당)
            opened_actions = self._takeover_opened_files(p4, normalized, change_list_number)

            # 오픈 액션별 분기: delete로 열린 파일은 그대로 두고,
            # edit로 열린 파일은 revert -k(로컬 유지)로 되돌린 후 delete로 다시 연다.
            # add로 열린 파일은 depot에 리비전이 없어 delete가 불가하므로 add만 취소한다.
            to_delete = []
            for filePath in normalized:
                action = opened_actions.get(self._comparable_path(filePath))
                if action is None:
                    to_delete.append(filePath)
                elif action in ("delete", "move/delete"):
                    continue
                elif action in ("add", "move/add"):
                    p4.run("revert", "-k", filePath)
                    print(f"add로 열려있던 파일의 add를 취소함 (depot 미존재로 delete 생략): {filePath}")
                else:
                    p4.run("revert", "-k", filePath)
                    to_delete.append(filePath)

            # 삭제 실행
            if to_delete:
                p4.run("delete", "-c", str(change_list_number), *to_delete)
            return True
        except P4Exception as e:
            print(f"파일 삭제 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def move_files(self, source_target_pairs: List[Tuple[str, str]], change_list_number: int) -> bool:
        """
        파일들을 새 경로로 이동/개명 (p4 edit → p4 move, 이력 보존)

        각 (source, target) 쌍에 대해 source를 지정 체인지리스트로 edit한 뒤 move한다.
        p4 move는 depot 경로와 워크스페이스의 실제 파일을 함께 이동하므로 별도의
        파일시스템 조작이 필요 없다(add/delete와 달리 rename 이력이 보존된다).
        원본이 자기 클라이언트의 다른 CL에 이미 열려 있으면 대상 CL로 이어받는다(reopen).

        Args:
            source_target_pairs: (원본 경로, 대상 경로) 튜플 리스트
            change_list_number: 체인지리스트 번호

        Returns:
            bool: 성공 여부

        Raises:
            ValueError: source_target_pairs가 리스트가 아닌 경우
            P4Exception: 이동에 실패한 경우
        """
        if not isinstance(source_target_pairs, list):
            raise ValueError("source_target_pairs must be a list")

        if not source_target_pairs:
            return False

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            sources = [self._normalize_path(src) for src, _dst in source_target_pairs]

            # 다른 CL에 이미 열린 원본은 대상 CL로 이어받는다 (자기 클라이언트의 오픈만 해당)
            opened_actions = self._takeover_opened_files(p4, sources, change_list_number)

            # 각 쌍에 대해 edit 후 move (move는 원본이 edit/add 상태여야 함)
            # 이미 열린 원본은 재-edit를 생략하고 바로 move한다
            for src, dst in source_target_pairs:
                normSource = self._normalize_path(src)
                normTarget = self._normalize_path(dst)
                if self._comparable_path(normSource) not in opened_actions:
                    p4.run("edit", "-c", str(change_list_number), normSource)
                p4.run("move", "-c", str(change_list_number), normSource, normTarget)
            return True
        except P4Exception as e:
            print(f"파일 이동 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def revert_files(self, change_list_number: int, file_paths: Optional[List[str]] = None) -> bool:
        """
        파일들을 리버트

        Args:
            change_list_number: 체인지리스트 번호
            file_paths: 리버트할 파일 경로 리스트 (None이면 체인지리스트의 모든 파일)

        Returns:
            bool: 성공 여부
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            if file_paths:
                if not isinstance(file_paths, list):
                    raise ValueError("file_paths must be a list or None")
                normalized = self._normalize_paths(file_paths)
                p4.run("revert", "-c", str(change_list_number), *normalized)
            else:
                # 모든 파일 리버트
                p4.run("revert", "-c", str(change_list_number), "//...")

            return True
        except P4Exception as e:
            print(f"파일 리버트 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def checkout_file(self, file_path: str, change_list_number: int) -> bool:
        """단일 파일 체크아웃 (배치 메서드 위임)"""
        return self.checkout_files([file_path], change_list_number)

    def add_file(self, file_path: str, change_list_number: int) -> bool:
        """단일 파일 추가 (배치 메서드 위임)"""
        return self.add_files([file_path], change_list_number)

    def delete_file(self, file_path: str, change_list_number: int) -> bool:
        """단일 파일 삭제 (배치 메서드 위임)"""
        return self.delete_files([file_path], change_list_number)

    def revert_file(self, file_path: str, change_list_number: int) -> bool:
        """단일 파일 리버트 (배치 메서드 위임)"""
        return self.revert_files(change_list_number, [file_path])
