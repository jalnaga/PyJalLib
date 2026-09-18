# -*- coding: utf-8 -*-
"""파일 상태 조회 - 열림·타인 체크아웃·CL 소속·depot 존재.

`Perforce`의 Mixin이다 - `pyjallib/perforce.py`(1,671줄)를 서브패키지로 분해하면서
(2026-09-18 ExportToolsRefactor Phase 10) 메서드를 **본문 무변경으로 이동**만 했다(`P4()` 생성 호출만
패키지 이름 조회로 바꿈 - 아래 주석). 인스턴스 속성(`port`/`user`/`workspace_name`/`charset`/
`exception_level`)과 `_normalize_path(s)`는 `core.Perforce`에 있다. 특성화 Type A(`tests/perforce/`)가 계약을 고정한다.
"""

from P4 import P4Exception
from typing import List, Dict

# 연결 객체 생성은 `pyjallib.perforce.P4`(패키지 이름)를 **호출 시점에** 조회한다.
# 소비처·테스트가 `patch("pyjallib.perforce.P4", ...)`로 대역을 꽂는 주입점을 분해 전과 같게 유지하기 위해서다
# (모듈 전역 `P4`를 쓰면 패키지 속성을 바꿔도 이 모듈에는 닿지 않는다).
from pyjallib import perforce as _perforcePackage


class _FileStatusMixin:
    """파일 상태 조회 - 열림·타인 체크아웃·CL 소속·depot 존재."""

    def is_file_checked_out(self, file_path: str) -> bool:
        """
        파일이 현재 사용자에 의해 체크아웃되었는지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: 체크아웃 여부
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_path(file_path)
            opened = p4.run("opened", normalized)

            return len(opened) > 0
        except P4Exception:
            # 파일이 열려있지 않으면 에러 발생
            return False
        finally:
            if p4.connected():
                p4.disconnect()

    def check_files_checked_out(self, file_paths: List[str]) -> Dict[str, bool]:
        """
        여러 파일의 체크아웃 상태 확인 (현재 클라이언트 기준)

        `p4 opened`의 `clientFile`은 클라이언트 문법(`//워크스페이스명/...`)이라
        로컬 절대경로와 대조하면 어떤 경우에도 매칭되지 않는다(전부 False 오탐).
        따라서 `depotFile`을 키로 `p4 where` 매핑을 거쳐 로컬 절대경로로 되돌린 뒤
        구분자/대소문자를 흡수하는 비교 키(`_comparable_path`)로 대조한다.

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            Dict[str, bool]: 정규화된 파일 경로별 체크아웃 여부.
                열려 있어도 대상이 다른 체인지리스트면 True다(열림 여부만 본다).
                특정 CL 소속까지 확인하려면 `is_file_in_pending_changelist`를 쓴다.
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)
            result = {path: False for path in normalized}
            # 비교 키 -> 결과 딕셔너리 키 매핑 (구분자/대소문자 차이 흡수)
            comparable_to_key = {self._comparable_path(path): path for path in normalized}

            try:
                opened = p4.run("opened", *normalized)
            except P4Exception:
                # 파일이 하나도 열려있지 않으면 에러 발생 (정상)
                opened = []

            if opened:
                depot_to_local = self._map_depot_to_local(p4, normalized)
                for file_info in opened:
                    if not isinstance(file_info, dict):
                        continue
                    depot_file = file_info.get('depotFile', '')
                    local_file = depot_to_local.get(depot_file, '')
                    if not local_file:
                        print(f"열린 파일의 로컬 경로 매핑 실패 (판정 제외): {depot_file}")
                        continue
                    matched_key = comparable_to_key.get(self._comparable_path(local_file))
                    if matched_key is not None:
                        result[matched_key] = True

            return result
        except P4Exception as e:
            print(f"파일 상태 확인 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def is_file_checked_out_by_others(self, file_path: str) -> bool:
        """
        파일이 다른 사용자에 의해 체크아웃되었는지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: 다른 사용자가 체크아웃한 경우 True
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            current_user = p4.user
            current_client = self.workspace_name
            normalized = self._normalize_path(file_path)

            # 모든 사용자의 열린 파일 확인
            opened = p4.run("opened", "-a", normalized)

            for file_info in opened:
                user = file_info.get('user', '')
                client = file_info.get('client', '')

                # 다른 워크스페이스(클라이언트)에서 체크아웃한 경우
                if client and client != current_client:
                    return True
                # 같은 클라이언트지만 다른 사용자인 경우 (거의 없지만 체크)
                if user and user != current_user and client == current_client:
                    return True

            return False
        except P4Exception:
            # 파일이 열려있지 않으면 에러 발생
            return False
        finally:
            if p4.connected():
                p4.disconnect()

    def check_files_checked_out_all_users(self, file_paths: List[str]) -> Dict[str, Dict]:
        """
        여러 파일의 모든 사용자 체크아웃 상태 확인

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            Dict[str, Dict]: 파일 경로별 상태 정보
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            current_user = p4.user
            current_client = self.workspace_name
            normalized = self._normalize_paths(file_paths)

            # 로컬 경로 -> depot 경로 매핑 생성
            path_to_depot = {}
            for path in normalized:
                try:
                    where_result = p4.run("where", path)
                    if where_result:
                        depot_file = where_result[0].get('depotFile', '')
                        if depot_file:
                            path_to_depot[depot_file] = path
                except P4Exception:
                    # 파일이 Perforce에 없으면 무시
                    pass

            result = {}
            for path in normalized:
                result[path] = {
                    'checked_out': False,
                    'by_current_user': False,
                    'by_others': False,
                    'user': None,
                    'client': None
                }

            try:
                opened = p4.run("opened", "-a", *normalized)
                for file_info in opened:
                    depot_file = file_info.get('depotFile', '')
                    if depot_file and depot_file in path_to_depot:
                        local_path = path_to_depot[depot_file]
                        user = file_info.get('user', '')
                        client = file_info.get('client', '')

                        result[local_path]['checked_out'] = True
                        result[local_path]['user'] = user
                        result[local_path]['client'] = client

                        # 다른 워크스페이스(클라이언트)에서 체크아웃한 경우
                        if client != current_client:
                            result[local_path]['by_others'] = True
                        elif user == current_user:
                            result[local_path]['by_current_user'] = True
                        else:
                            # 같은 클라이언트지만 다른 사용자 (드문 경우)
                            result[local_path]['by_others'] = True
            except P4Exception:
                # 파일이 하나도 열려있지 않으면 에러 발생
                pass

            return result
        except P4Exception as e:
            print(f"파일 상태 확인 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_file_checkout_info_all_users(self, file_path: str) -> Dict:
        """
        파일의 체크아웃 정보 조회 (모든 사용자)

        Args:
            file_path: 확인할 파일 경로

        Returns:
            Dict: 체크아웃 정보
        """
        result = self.check_files_checked_out_all_users([file_path])
        normalized = self._normalize_path(file_path)
        return result.get(normalized, {})

    def get_files_checked_out_by_others(self, file_paths: List[str]) -> List[Dict]:
        """
        다른 사용자가 체크아웃한 파일 목록 조회

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            List[Dict]: 다른 사용자가 체크아웃한 파일 정보 리스트
        """
        all_status = self.check_files_checked_out_all_users(file_paths)

        result = []
        for path, info in all_status.items():
            if info['by_others']:
                result.append({
                    'path': path,
                    'user': info['user'],
                    'client': info['client']
                })

        return result

    def is_file_in_pending_changelist(self, file_path: str, change_list_number: int) -> bool:
        """
        파일이 특정 체인지리스트에 있는지 확인

        Args:
            file_path: 확인할 파일 경로
            change_list_number: 체인지리스트 번호

        Returns:
            bool: 체인지리스트에 포함 여부
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_path(file_path)

            try:
                opened = p4.run("opened", "-c", str(change_list_number), normalized)
                return len(opened) > 0
            except P4Exception:
                return False
        except P4Exception as e:
            print(f"파일 상태 확인 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def is_file_in_perforce(self, file_path: str) -> bool:
        """
        파일이 Perforce에 존재하는지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: Perforce에 존재 여부
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_path(file_path)
            files = p4.run("files", normalized)

            return len(files) > 0
        except P4Exception:
            # 파일이 없으면 에러 발생
            return False
        finally:
            if p4.connected():
                p4.disconnect()
