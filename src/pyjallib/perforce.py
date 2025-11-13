"""
Perforce 모듈 - 단순화된 버전
P4Python을 사용하여 Perforce 작업을 수행하는 단일 클래스
"""

from P4 import P4, P4Exception
from pathlib import Path
from typing import List, Optional, Dict, Union


class Perforce:
    """
    Perforce 작업을 위한 단순화된 클래스
    각 메서드는 독립적으로 P4 인스턴스를 생성하고 연결/실행/종료합니다.
    """

    def __init__(self):
        """Perforce 객체 초기화"""
        self.workspace_name = None
        self.workspaceRoot = None

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
        p4 = P4()
        p4.client = workspace_name
        try:
            p4.connect()
            client_spec = p4.fetch_client(workspace_name)
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

    # ============================================================================
    # 체인지리스트 생성/관리
    # ============================================================================

    def create_change_list(self, description: str) -> Dict:
        """
        새 체인지리스트 생성

        Args:
            description: 체인지리스트 설명

        Returns:
            Dict: 생성된 체인지리스트 정보 {'id', 'description', 'status', 'user', 'client'}
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            # 새 체인지 스펙 가져오기
            change_spec = p4.run("change", "-o")[0]
            change_spec["Description"] = description

            # 저장
            result = p4.save_change(change_spec)[0]

            # 생성된 번호 파싱 ("Change 12345 created")
            cl_number = int(result.split()[1])

            # 상세정보 조회
            cl_info = p4.fetch_change(cl_number)

            return {
                'id': cl_number,
                'description': cl_info.get('Description', '').strip(),
                'status': cl_info.get('Status', ''),
                'user': cl_info.get('User', ''),
                'client': cl_info.get('Client', '')
            }
        except P4Exception as e:
            print(f"체인지리스트 생성 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def delete_empty_change_list(self, change_list_number: int) -> bool:
        """
        빈 체인지리스트 삭제

        Args:
            change_list_number: 삭제할 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            # 체인지리스트 삭제
            p4.run("change", "-d", str(change_list_number))
            return True
        except P4Exception as e:
            print(f"체인지리스트 삭제 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def submit_change_list(self, change_list_number: int, auto_revert_unchanged: bool = True) -> bool:
        """
        체인지리스트 제출

        Args:
            change_list_number: 제출할 체인지리스트 번호
            auto_revert_unchanged: 변경되지 않은 파일 자동 리버트 여부

        Returns:
            bool: 제출 성공 여부 (False인 경우 빈 체인지리스트로 삭제됨)
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            # 1. 변경 없는 파일 리버트
            if auto_revert_unchanged:
                try:
                    p4.run("revert", "-a", "-c", str(change_list_number))
                except P4Exception:
                    # 리버트 실패는 무시 (파일이 없을 수 있음)
                    pass

            # 2. 제출할 파일 확인
            opened = p4.run("opened", "-c", str(change_list_number))
            if not opened:
                # 빈 체인지리스트 삭제
                p4.run("change", "-d", str(change_list_number))
                return False

            # 3. 제출
            p4.run("submit", "-c", str(change_list_number))
            return True
        except P4Exception as e:
            print(f"체인지리스트 제출 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def revert_change_list(self, change_list_number: int) -> bool:
        """
        체인지리스트의 모든 파일 리버트 및 체인지리스트 삭제

        Args:
            change_list_number: 리버트할 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            # 1. 파일 리버트
            try:
                p4.run("revert", "-c", str(change_list_number), "//...")
            except P4Exception:
                # 리버트할 파일이 없을 수 있음
                pass

            # 2. 빈 체인지리스트 삭제
            p4.run("change", "-d", str(change_list_number))
            return True
        except P4Exception as e:
            print(f"체인지리스트 리버트 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def edit_change_list(self, change_list_number: int, description: Optional[str] = None,
                        add_file_paths: Optional[List[str]] = None,
                        remove_file_paths: Optional[List[str]] = None) -> Dict:
        """
        체인지리스트 수정

        Args:
            change_list_number: 수정할 체인지리스트 번호
            description: 새 설명 (None이면 변경하지 않음)
            add_file_paths: 추가할 파일 경로 리스트
            remove_file_paths: 제거할 파일 경로 리스트

        Returns:
            Dict: 수정된 체인지리스트 정보
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            # Description 변경
            if description is not None:
                change_spec = p4.fetch_change(change_list_number)
                change_spec["Description"] = description
                p4.save_change(change_spec)

            # 파일 추가 (reopen)
            if add_file_paths:
                normalized = self._normalize_paths(add_file_paths)
                p4.run("reopen", "-c", str(change_list_number), *normalized)

            # 파일 제거 (default CL로 reopen)
            if remove_file_paths:
                normalized = self._normalize_paths(remove_file_paths)
                p4.run("reopen", "-c", "default", *normalized)

            # 수정된 정보 반환
            cl_info = p4.fetch_change(change_list_number)
            return {
                'id': change_list_number,
                'description': cl_info.get('Description', '').strip(),
                'status': cl_info.get('Status', ''),
                'user': cl_info.get('User', ''),
                'client': cl_info.get('Client', '')
            }
        except P4Exception as e:
            print(f"체인지리스트 수정 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    # ============================================================================
    # 체인지리스트 조회
    # ============================================================================

    def get_pending_change_list(self) -> List[Dict]:
        """
        대기 중인 체인지리스트 목록 조회

        Returns:
            List[Dict]: 체인지리스트 정보 리스트
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name

            # 대기 중인 체인지리스트 조회 (설명 포함)
            changes = p4.run("changes", "-l", "-s", "pending", "-u", user, "-c", client)

            result = []
            for change in changes:
                result.append({
                    'id': int(change.get('change', 0)),
                    'description': change.get('desc', '').strip(),
                    'status': change.get('status', ''),
                    'user': change.get('user', ''),
                    'client': change.get('client', '')
                })

            return result
        except P4Exception as e:
            print(f"체인지리스트 조회 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_change_list_by_number(self, change_list_number: int) -> Dict:
        """
        번호로 체인지리스트 조회

        Args:
            change_list_number: 조회할 체인지리스트 번호

        Returns:
            Dict: 체인지리스트 정보
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            cl_info = p4.fetch_change(change_list_number)

            return {
                'id': change_list_number,
                'description': cl_info.get('Description', '').strip(),
                'status': cl_info.get('Status', ''),
                'user': cl_info.get('User', ''),
                'client': cl_info.get('Client', '')
            }
        except P4Exception as e:
            print(f"체인지리스트 조회 실패 (번호: {change_list_number}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_change_list_by_description(self, description: str) -> Dict:
        """
        설명으로 체인지리스트 조회 (정확히 일치하는 첫 번째 항목)

        Args:
            description: 찾을 설명

        Returns:
            Dict: 체인지리스트 정보 (없으면 빈 딕셔너리)
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name

            changes = p4.run("changes", "-l", "-s", "pending", "-u", user, "-c", client)

            for change in changes:
                desc = change.get('desc', '').strip()
                if desc == description:
                    return {
                        'id': int(change.get('change', 0)),
                        'description': desc,
                        'status': change.get('status', ''),
                        'user': change.get('user', ''),
                        'client': change.get('client', '')
                    }

            return {}
        except P4Exception as e:
            print(f"체인지리스트 조회 실패 (설명: {description}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_change_list_by_description_pattern(self, description_pattern: str,
                                               exact_match: bool = False) -> List[Dict]:
        """
        설명 패턴으로 체인지리스트 검색

        Args:
            description_pattern: 검색할 패턴
            exact_match: True면 정확히 일치, False면 부분 일치

        Returns:
            List[Dict]: 매칭되는 체인지리스트 리스트
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name

            changes = p4.run("changes", "-l", "-s", "pending", "-u", user, "-c", client)

            result = []
            for change in changes:
                desc = change.get('desc', '').strip()

                if exact_match:
                    if desc == description_pattern:
                        result.append({
                            'id': int(change.get('change', 0)),
                            'description': desc,
                            'status': change.get('status', ''),
                            'user': change.get('user', ''),
                            'client': change.get('client', '')
                        })
                else:
                    if description_pattern in desc:
                        result.append({
                            'id': int(change.get('change', 0)),
                            'description': desc,
                            'status': change.get('status', ''),
                            'user': change.get('user', ''),
                            'client': change.get('client', '')
                        })

            return result
        except P4Exception as e:
            print(f"체인지리스트 검색 실패 (패턴: {description_pattern}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_default_change_list(self) -> Dict:
        """
        기본 체인지리스트 정보 반환

        Returns:
            Dict: 기본 체인지리스트 정보 (id는 'default')
        """
        return {
            'id': 'default',
            'description': 'Default Change',
            'status': 'pending',
            'user': '',
            'client': self.workspace_name or ''
        }

    # ============================================================================
    # 파일 작업 (배치)
    # ============================================================================

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

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 다른 체인지리스트에 이미 열려있는지 체크
            try:
                opened = p4.run("opened", *normalized)
                for file_info in opened:
                    existing_cl = file_info.get('change')
                    if existing_cl != str(change_list_number) and existing_cl != 'default':
                        depotFile = file_info.get('depotFile', 'unknown')
                        print(f"파일이 다른 체인지리스트에 열려있음: {depotFile} (CL: {existing_cl})")
                        raise P4Exception(f"파일이 체인지리스트 {existing_cl}에 이미 열려있습니다")
            except P4Exception as e:
                # 파일이 열려있지 않으면 에러가 발생할 수 있음 (정상)
                if "not opened" not in str(e):
                    raise

            # 체크아웃 실행
            p4.run("edit", "-c", str(change_list_number), *normalized)
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

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 다른 체인지리스트에 이미 열려있는지 체크
            try:
                opened = p4.run("opened", *normalized)
                for file_info in opened:
                    existing_cl = file_info.get('change')
                    if existing_cl != str(change_list_number) and existing_cl != 'default':
                        depotFile = file_info.get('depotFile', 'unknown')
                        print(f"파일이 다른 체인지리스트에 열려있음: {depotFile} (CL: {existing_cl})")
                        raise P4Exception(f"파일이 체인지리스트 {existing_cl}에 이미 열려있습니다")
            except P4Exception as e:
                # 파일이 열려있지 않으면 에러가 발생할 수 있음 (정상)
                if "not opened" not in str(e):
                    raise

            # 추가 실행
            p4.run("add", "-c", str(change_list_number), *normalized)
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

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 다른 체인지리스트에 이미 열려있는지 체크
            try:
                opened = p4.run("opened", *normalized)
                for file_info in opened:
                    existing_cl = file_info.get('change')
                    if existing_cl != str(change_list_number) and existing_cl != 'default':
                        depotFile = file_info.get('depotFile', 'unknown')
                        print(f"파일이 다른 체인지리스트에 열려있음: {depotFile} (CL: {existing_cl})")
                        raise P4Exception(f"파일이 체인지리스트 {existing_cl}에 이미 열려있습니다")
            except P4Exception as e:
                # 파일이 열려있지 않으면 에러가 발생할 수 있음 (정상)
                if "not opened" not in str(e):
                    raise

            # 삭제 실행
            p4.run("delete", "-c", str(change_list_number), *normalized)
            return True
        except P4Exception as e:
            print(f"파일 삭제 실패: {e}")
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
        p4 = P4()
        p4.client = self.workspace_name
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

    # ============================================================================
    # 파일 작업 (단일 파일 - 배치 메서드 위임)
    # ============================================================================

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

    # ============================================================================
    # 파일 상태 조회
    # ============================================================================

    def is_file_checked_out(self, file_path: str) -> bool:
        """
        파일이 현재 사용자에 의해 체크아웃되었는지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: 체크아웃 여부
        """
        p4 = P4()
        p4.client = self.workspace_name
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
        여러 파일의 체크아웃 상태 확인

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            Dict[str, bool]: 파일 경로별 체크아웃 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)
            result = {path: False for path in normalized}

            try:
                opened = p4.run("opened", *normalized)
                for file_info in opened:
                    client_file = file_info.get('clientFile', '')
                    if client_file:
                        # 경로 정규화 후 매칭
                        norm_client = self._normalize_path(client_file)
                        if norm_client in result:
                            result[norm_client] = True
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

    def is_file_checked_out_by_others(self, file_path: str) -> bool:
        """
        파일이 다른 사용자에 의해 체크아웃되었는지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: 다른 사용자가 체크아웃한 경우 True
        """
        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            current_user = p4.user
            normalized = self._normalize_path(file_path)

            # 모든 사용자의 열린 파일 확인
            opened = p4.run("opened", "-a", normalized)

            for file_info in opened:
                user = file_info.get('user', '')
                if user and user != current_user:
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

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            current_user = p4.user
            normalized = self._normalize_paths(file_paths)
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
                    client_file = file_info.get('clientFile', '')
                    if client_file:
                        norm_client = self._normalize_path(client_file)
                        if norm_client in result:
                            user = file_info.get('user', '')
                            result[norm_client]['checked_out'] = True
                            result[norm_client]['user'] = user
                            result[norm_client]['client'] = file_info.get('client', '')

                            if user == current_user:
                                result[norm_client]['by_current_user'] = True
                            else:
                                result[norm_client]['by_others'] = True
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
        p4 = P4()
        p4.client = self.workspace_name
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

    # ============================================================================
    # 싱크 작업
    # ============================================================================

    def is_file_in_perforce(self, file_path: str) -> bool:
        """
        파일이 Perforce에 존재하는지 확인

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: Perforce에 존재 여부
        """
        p4 = P4()
        p4.client = self.workspace_name
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

    def check_update_required(self, file_paths: List[str]) -> bool:
        """
        파일들의 싱크 필요 여부 확인

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            bool: 싱크가 필요하면 True
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 프리뷰 모드로 싱크 확인
            sync_result = p4.run("sync", "-n", *normalized)

            # 결과가 있으면 싱크 필요
            return len(sync_result) > 0
        except P4Exception as e:
            print(f"싱크 확인 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def sync_files(self, file_paths: List[str]) -> bool:
        """
        파일들을 싱크

        Args:
            file_paths: 싱크할 파일 경로 리스트

        Returns:
            bool: 성공 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = P4()
        p4.client = self.workspace_name
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 싱크 실행
            p4.run("sync", *normalized)
            return True
        except P4Exception as e:
            print(f"싱크 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()
