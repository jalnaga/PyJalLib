"""
Perforce 모듈 - 단순화된 버전
P4Python을 사용하여 Perforce 작업을 수행하는 단일 클래스
"""

from P4 import P4, P4Exception
from pathlib import Path
from typing import List, Optional, Dict, Union, Tuple


class Perforce:
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
        p4 = P4()
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
        p4 = P4()
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # 새 체인지 스펙 가져오기
            change_spec = p4.run("change", "-o")[0]
            change_spec["Description"] = description

            # Default CL 파일이 새 CL로 이동하지 않도록 Files 필드 제거
            if "Files" in change_spec:
                del change_spec["Files"]

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

    def delete_change_list(self, change_list_number: int) -> bool:
        """
        체인지리스트 삭제 (파일이 있으면 리버트 후 삭제)

        Args:
            change_list_number: 삭제할 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        p4 = P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # 1. 체인지리스트의 파일 리버트
            try:
                p4.run("revert", "-c", str(change_list_number), "//...")
                print(f"체인지리스트 {change_list_number}의 파일 리버트 완료")
            except P4Exception:
                # 리버트할 파일이 없을 수 있음
                pass

            # 2. 체인지리스트 삭제
            p4.run("change", "-d", str(change_list_number))
            print(f"체인지리스트 {change_list_number} 삭제 완료")
            return True
        except P4Exception as e:
            print(f"체인지리스트 삭제 실패 (CL {change_list_number}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def delete_empty_change_list(self) -> List[int]:
        """
        현재 클라이언트의 모든 빈 펜딩 체인지리스트 삭제

        Returns:
            List[int]: 삭제된 체인지리스트 번호 리스트
        """
        p4 = P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name
            deleted_cls = []

            # 대기 중인 체인지리스트 조회
            changes = p4.run("changes", "-s", "pending", "-u", user, "-c", client)

            for change in changes:
                cl_number = int(change.get('change', 0))
                if cl_number == 0:
                    continue

                # 체인지리스트에 파일이 있는지 확인
                try:
                    opened = p4.run("opened", "-c", str(cl_number))
                    # 파일이 있으면 건너뛰기
                    if opened:
                        continue
                except P4Exception:
                    # 파일이 없으면 에러 발생 (정상 - 빈 CL)
                    pass

                # 빈 체인지리스트 삭제 시도
                try:
                    p4.run("change", "-d", str(cl_number))
                    deleted_cls.append(cl_number)
                    print(f"빈 체인지리스트 삭제: {cl_number}")
                except P4Exception as e:
                    # 삭제 실패는 경고만 출력하고 계속 진행
                    print(f"체인지리스트 삭제 실패 (CL {cl_number}): {e}")

            return deleted_cls
        except P4Exception as e:
            print(f"빈 체인지리스트 삭제 작업 실패: {e}")
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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

    @staticmethod
    def _comparable_path(path: str) -> str:
        """경로 비교용 키를 만든다 (구분자/대소문자 차이 흡수).

        Args:
            path: 비교할 경로 문자열

        Returns:
            str: 슬래시 통일 + 소문자화된 비교 키
        """
        return str(path).replace("\\", "/").lower()

    def _takeover_opened_files(self, p4: P4, file_paths: List[str], change_list_number: Union[int, str]) -> Dict[str, str]:
        """대상 체인지리스트가 아닌 곳에 열려 있는 파일들을 대상 CL로 이어받는다.

        `p4 opened`(-a 미사용)는 현재 워크스페이스의 오픈만 반환하므로, 여기서
        잡히는 파일은 전부 자기 클라이언트의 pending CL(또는 default)에 열린
        파일이다. 안전하게 이어받을 수 있으므로 예외를 던지는 대신
        `p4 reopen -c`로 대상 CL로 이동시킨다. (p4 edit/add의 -c 플래그는 이미
        열린 파일을 다른 CL로 이동시키지 않으므로 reopen이 필요하다.)

        Args:
            p4: 연결된 P4 인스턴스
            file_paths: 정규화된 로컬 파일 경로 리스트
            change_list_number: 대상 체인지리스트 번호 (숫자 또는 "default")

        Returns:
            Dict[str, str]: {비교용 경로 키(_comparable_path): 오픈 액션} 딕셔너리.
                현재 열려 있는 파일만 포함된다(이어받은 파일 + 이미 대상 CL에
                있던 파일). 열려 있지 않은 파일은 포함되지 않는다.
        """
        target_cl = str(change_list_number)

        # 현재 워크스페이스에서 열린 파일 조회
        try:
            opened = p4.run("opened", *file_paths)
        except P4Exception as e:
            # 파일이 열려있지 않으면 에러가 발생할 수 있음 (정상)
            if "not opened" in str(e):
                return {}
            raise

        if not opened:
            return {}

        # opened 출력은 depot/client 문법이므로 로컬 경로 매핑을 만든다
        depot_to_local = {}
        try:
            for mapping in p4.run("where", *file_paths):
                if isinstance(mapping, dict) and "unmap" not in mapping and mapping.get("depotFile"):
                    depot_to_local[mapping["depotFile"]] = mapping.get("path", "")
        except P4Exception as e:
            print(f"p4 where 매핑 실패 (열린 파일 식별이 depot 경로 기준으로 동작): {e}")

        opened_actions: Dict[str, str] = {}
        reopen_targets = []
        source_changelists = set()
        for file_info in opened:
            if not isinstance(file_info, dict):
                continue
            depot_file = file_info.get("depotFile", "")
            local_file = depot_to_local.get(depot_file, depot_file)
            opened_actions[self._comparable_path(local_file)] = file_info.get("action", "")

            existing_cl = file_info.get("change", "")
            if existing_cl != target_cl:
                reopen_targets.append(depot_file)
                if existing_cl and existing_cl != "default":
                    source_changelists.add(existing_cl)
                print(f"파일이 체인지리스트 {existing_cl}에 열려있어 {target_cl}(으)로 이어받음(reopen): {depot_file}")

        if reopen_targets:
            p4.run("reopen", "-c", target_cl, *reopen_targets)
            self._delete_emptied_changelists(p4, source_changelists)

        return opened_actions

    def _delete_emptied_changelists(self, p4: P4, changelist_numbers: Union[set, List[str]]) -> None:
        """이어받기로 파일이 빠져나가 비게 된 pending CL들을 삭제한다.

        고아 빈 CL이 누적되는 것을 막는 정리 단계다. 조회/삭제 실패는
        본 작업에 영향을 주지 않도록 경고만 남기고 계속한다
        (셸브 파일이 있는 CL 등은 p4가 삭제를 거부한다).

        Args:
            p4: 연결된 P4 인스턴스
            changelist_numbers: 파일이 빠져나간 원본 CL 번호 목록 (default 제외)
        """
        for changelist in changelist_numbers:
            try:
                remaining = p4.run("opened", "-c", str(changelist))
                if remaining:
                    continue
                p4.run("change", "-d", str(changelist))
                print(f"이어받기로 비게 된 체인지리스트 삭제: {changelist}")
            except P4Exception as e:
                print(f"체인지리스트 {changelist} 정리 실패 (무시하고 계속): {e}")

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

        p4 = P4()
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

        p4 = P4()
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

        p4 = P4()
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

        p4 = P4()
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
        p4 = P4()
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
        여러 파일의 체크아웃 상태 확인

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            Dict[str, bool]: 파일 경로별 체크아웃 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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

        p4 = P4()
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
        p4 = P4()
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
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
