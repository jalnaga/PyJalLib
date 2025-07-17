"""
P4Python을 사용하는 Perforce 모듈.

이 모듈은 P4Python을 사용하여 Perforce 서버와 상호작용하는 기능을 제공합니다.
주요 기능:
- 워크스페이스 연결
- 체인지리스트 관리 (생성, 조회, 편집, 제출, 되돌리기)
- 파일 작업 (체크아웃, 추가, 삭제)
- 파일 동기화 및 업데이트 확인
"""

from P4 import P4, P4Exception
import os
from .exceptions import PerforceError, ValidationError


class Perforce:
    """P4Python을 사용하여 Perforce 작업을 수행하는 클래스."""

    def __init__(self):
        """Perforce 인스턴스를 초기화합니다."""
        self.p4 = P4()
        self.connected = False
        self.workspaceRoot = r""

    def _is_connected(self) -> bool:
        """Perforce 서버 연결 상태를 확인합니다.

        Returns:
            bool: 연결되어 있으면 True, 아니면 False
        """
        if not self.connected:
            return False
        return True
    
    def _ensure_connected(self) -> None:
        """Perforce 서버 연결 상태를 확인하고 연결되지 않은 경우 예외를 발생시킵니다.
        
        Raises:
            PerforceError: 연결되지 않은 상태인 경우
        """
        if not self.connected:
            error_message = "Perforce 서버에 연결되지 않았습니다."
            raise PerforceError(error_message)

    def connect(self, workspace_name: str) -> bool:
        """지정된 워크스페이스에 연결합니다.

        Args:
            workspace_name (str): 연결할 워크스페이스 이름

        Returns:
            bool: 연결 성공 시 True, 실패 시 False
        """
        try:
            self.p4.client = workspace_name
            self.p4.connect()
            self.connected = True
            
            # 워크스페이스 루트 경로 가져오기
            try:
                client_info = self.p4.run_client("-o", workspace_name)[0]
                root_path = client_info.get("Root", "")
                
                # Windows 경로 형식으로 변환 (슬래시를 백슬래시로)
                root_path = os.path.normpath(root_path)
                
                self.workspaceRoot = root_path
            except (IndexError, KeyError):
                self.workspaceRoot = ""
                
            return True
        except P4Exception as e:
            self.connected = False
            error_message = f"'{workspace_name}' 워크스페이스 연결 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def get_pending_change_list(self) -> list:
        """워크스페이스의 Pending된 체인지 리스트를 가져옵니다.

        Returns:
            list: 체인지 리스트 정보 딕셔너리들의 리스트
        """
        self._ensure_connected()
        try:
            pending_changes = self.p4.run_changes("-s", "pending", "-u", self.p4.user, "-c", self.p4.client)
            change_numbers = [int(cl['change']) for cl in pending_changes]
            
            # 각 체인지 리스트 번호에 대한 상세 정보 가져오기
            change_list_info = []
            for change_number in change_numbers:
                cl_info = self.get_change_list_by_number(change_number)
                if cl_info:
                    change_list_info.append(cl_info)
            
            return change_list_info
        except P4Exception as e:
            error_message = f"Pending 체인지 리스트 조회 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def create_change_list(self, description: str) -> dict:
        """새로운 체인지 리스트를 생성합니다.

        Args:
            description (str): 체인지 리스트 설명

        Returns:
            dict: 생성된 체인지 리스트 정보. 실패 시 빈 딕셔너리
        """
        self._ensure_connected()
        try:
            change_spec = self.p4.fetch_change()
            change_spec["Description"] = description
            result = self.p4.save_change(change_spec)
            created_change_number = int(result[0].split()[1])
            return self.get_change_list_by_number(created_change_number)
        except P4Exception as e:
            error_message = f"체인지 리스트 생성 실패 ('{description}') 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)
        except (IndexError, ValueError) as e:
            error_message = f"체인지 리스트 번호 파싱 오류: {e}"
            raise PerforceError(error_message)

    def get_change_list_by_number(self, change_list_number: int) -> dict:
        """체인지 리스트 번호로 체인지 리스트를 가져옵니다.

        Args:
            change_list_number (int): 체인지 리스트 번호

        Returns:
            dict: 체인지 리스트 정보. 실패 시 빈 딕셔너리
        """
        self._ensure_connected()
        try:
            cl_info = self.p4.fetch_change(change_list_number)
            if cl_info:
                return cl_info
            else:
                error_message = f"체인지 리스트 {change_list_number}를 찾을 수 없습니다."
                raise PerforceError(error_message)
        except P4Exception as e:
            error_message = f"체인지 리스트 {change_list_number} 정보 조회 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def get_change_list_by_description(self, description: str) -> dict:
        """체인지 리스트 설명으로 체인지 리스트를 가져옵니다.

        Args:
            description (str): 체인지 리스트 설명

        Returns:
            dict: 체인지 리스트 정보 (일치하는 첫 번째 체인지 리스트)
        """
        self._ensure_connected()
        try:
            pending_changes = self.p4.run_changes("-l", "-s", "pending", "-u", self.p4.user, "-c", self.p4.client)
            for cl in pending_changes:
                cl_desc = cl.get('Description', b'').decode('utf-8', 'replace').strip()
                if cl_desc == description.strip():
                    return self.get_change_list_by_number(int(cl['change']))
            return {}
        except P4Exception as e:
            error_message = f"설명으로 체인지 리스트 조회 실패 ('{description}') 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def get_change_list_by_description_pattern(self, description_pattern: str, exact_match: bool = False) -> list:
        """설명 패턴과 일치하는 Pending 체인지 리스트들을 가져옵니다.

        Args:
            description_pattern (str): 검색할 설명 패턴
            exact_match (bool, optional): True면 정확히 일치하는 설명만, 
                                        False면 패턴이 포함된 설명도 포함. 기본값 False

        Returns:
            list: 패턴과 일치하는 체인지 리스트 정보들의 리스트
        """
        self._ensure_connected()
        try:
            pending_changes = self.p4.run_changes("-l", "-s", "pending", "-u", self.p4.user, "-c", self.p4.client)
            matching_changes = []
            
            for cl in pending_changes:
                cl_desc = cl.get('Description', b'').decode('utf-8', 'replace').strip()
                
                # 패턴 매칭 로직
                is_match = False
                if exact_match:
                    # 정확한 일치
                    is_match = (cl_desc == description_pattern.strip())
                else:
                    # 패턴이 포함되어 있는지 확인 (대소문자 구분 없음)
                    is_match = (description_pattern.lower().strip() in cl_desc.lower())
                
                if is_match:
                    change_number = int(cl['change'])
                    change_info = self.get_change_list_by_number(change_number)
                    if change_info:
                        matching_changes.append(change_info)
            
            return matching_changes
        except P4Exception as e:
            error_message = f"설명 패턴으로 체인지 리스트 조회 실패 ('{description_pattern}') 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def disconnect(self):
        """Perforce 서버와의 연결을 해제합니다."""
        if self.connected:
            try:
                self.p4.disconnect()
                self.connected = False
            except P4Exception as e:
                error_message = f"Perforce 서버 연결 해제 중 P4Exception 발생: {e}"
                raise PerforceError(error_message)

    def __del__(self):
        """객체가 소멸될 때 자동으로 연결을 해제합니다."""
        self.disconnect()

    def check_files_checked_out(self, file_paths: list) -> dict:
        """파일들의 체크아웃 상태를 확인합니다.

        Args:
            file_paths (list): 확인할 파일 경로 리스트

        Returns:
            dict: 파일별 체크아웃 상태 정보
                 {
                     'file_path': {
                         'is_checked_out': bool,
                         'change_list': int or None,
                         'action': str or None,
                         'user': str or None,
                         'workspace': str or None
                     }
                 }
        """
        self._ensure_connected()
        if not file_paths:
            return {}
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 is_file_checked_out() 메서드를 사용하세요."
            raise ValidationError(error_msg)
        
        result = {}
        try:
            # 각 파일의 상태 확인
            for file_path in file_paths:
                file_status = {
                    'is_checked_out': False,
                    'change_list': None,
                    'action': None,
                    'user': None,
                    'workspace': None
                }
                
                try:
                    # p4 opened 명령으로 파일이 열려있는지 확인
                    opened_files = self.p4.run_opened(file_path)
                    
                    if opened_files:
                        # 파일이 체크아웃되어 있음
                        file_info = opened_files[0]
                        file_status['is_checked_out'] = True
                        file_status['change_list'] = int(file_info.get('change', 0))
                        file_status['action'] = file_info.get('action', '')
                        file_status['user'] = file_info.get('user', '')
                        file_status['workspace'] = file_info.get('client', '')
                        
                except P4Exception as e:
                    # 파일이 perforce에 없거나 접근할 수 없는 경우
                    if not any("not opened" in err.lower() or "no such file" in err.lower() 
                               for err in self.p4.errors):
                        error_message = f"파일 '{file_path}' 체크아웃 상태 확인 중 P4Exception 발생: {e}"
                        raise PerforceError(error_message)
                
                result[file_path] = file_status
            
            return result
            
        except P4Exception as e:
            error_message = f"파일들 체크아웃 상태 확인 ({file_paths}) 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def is_file_checked_out(self, file_path: str) -> bool:
        """단일 파일의 체크아웃 상태를 간단히 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            bool: 체크아웃되어 있으면 True, 아니면 False
        """
        result = self.check_files_checked_out([file_path])
        return result.get(file_path, {}).get('is_checked_out', False)

    def is_file_in_pending_changelist(self, file_path: str, change_list_number: int) -> bool:
        """특정 파일이 지정된 pending 체인지 리스트에 있는지 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로
            change_list_number (int): 확인할 체인지 리스트 번호

        Returns:
            bool: 파일이 해당 체인지 리스트에 있으면 True, 아니면 False
        """
        self._ensure_connected()
        try:
            # 해당 체인지 리스트의 파일들 가져오기
            opened_files = self.p4.run_opened("-c", change_list_number)
            
            # 파일 경로 정규화
            normalized_file_path = os.path.normpath(file_path)
            
            for file_info in opened_files:
                client_file = file_info.get('clientFile', '')
                normalized_client_file = os.path.normpath(client_file)
                
                if normalized_client_file == normalized_file_path:
                    return True
            
            return False
            
        except P4Exception as e:
            error_message = f"파일 '{file_path}' 체인지 리스트 {change_list_number} 포함 여부 확인 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def edit_change_list(self, change_list_number: int, description: str = None, add_file_paths: list = None, remove_file_paths: list = None) -> dict:
        """체인지 리스트를 편집합니다.

        Args:
            change_list_number (int): 체인지 리스트 번호
            description (str, optional): 변경할 설명
            add_file_paths (list, optional): 추가할 파일 경로 리스트
            remove_file_paths (list, optional): 제거할 파일 경로 리스트

        Returns:
            dict: 업데이트된 체인지 리스트 정보
        """
        self._ensure_connected()
        try:
            if description is not None:
                change_spec = self.p4.fetch_change(change_list_number)
                current_description = change_spec.get('Description', '').strip()
                if current_description != description.strip():
                    change_spec['Description'] = description
                    self.p4.save_change(change_spec)

            if add_file_paths:
                for file_path in add_file_paths:
                    try:
                        self.p4.run_reopen("-c", change_list_number, file_path)
                    except P4Exception as e_reopen:
                        error_message = f"파일 '{file_path}'을 CL {change_list_number}로 이동 중 P4Exception 발생: {e_reopen}"
                        raise PerforceError(error_message)

            if remove_file_paths:
                for file_path in remove_file_paths:
                    try:
                        self.p4.run_revert("-c", change_list_number, file_path)
                    except P4Exception as e_revert:
                        error_message = f"파일 '{file_path}'을 CL {change_list_number}에서 제거(revert) 중 P4Exception 발생: {e_revert}"
                        raise PerforceError(error_message)

            return self.get_change_list_by_number(change_list_number)

        except P4Exception as e:
            error_message = f"체인지 리스트 {change_list_number} 편집 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def _file_op(self, command: str, file_path: str, change_list_number: int, op_name: str) -> bool:
        """파일 작업을 수행하는 내부 헬퍼 함수입니다.

        Args:
            command (str): 실행할 명령어 (edit/add/delete)
            file_path (str): 대상 파일 경로
            change_list_number (int): 체인지 리스트 번호
            op_name (str): 작업 이름 (로깅용)

        Returns:
            bool: 작업 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        try:
            if command == "edit":
                self.p4.run_edit("-c", change_list_number, file_path)
            elif command == "add":
                self.p4.run_add("-c", change_list_number, file_path)
            elif command == "delete":
                self.p4.run_delete("-c", change_list_number, file_path)
            else:
                error_message = f"지원되지 않는 파일 작업: {command}"
                raise ValidationError(error_message)
            return True
        except P4Exception as e:
            error_message = f"파일 '{file_path}' {op_name} (CL: {change_list_number}) 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def checkout_file(self, file_path: str, change_list_number: int) -> bool:
        """파일을 체크아웃합니다.

        Args:
            file_path (str): 체크아웃할 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 체크아웃 성공 시 True, 실패 시 False
        """
        return self._file_op("edit", file_path, change_list_number, "체크아웃")
        
    def checkout_files(self, file_paths: list, change_list_number: int) -> bool:
        """여러 파일을 한 번에 체크아웃합니다.
        
        Args:
            file_paths (list): 체크아웃할 파일 경로 리스트
            change_list_number (int): 체인지 리스트 번호
            
        Returns:
            bool: 모든 파일 체크아웃 성공 시 True, 하나라도 실패 시 False
        """
        if not file_paths:
            return True
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 checkout_file() 메서드를 사용하세요."
            raise ValidationError(error_msg)
            
        all_success = True
        for file_path in file_paths:
            success = self.checkout_file(file_path, change_list_number)
            if not success:
                all_success = False
                
        return all_success

    def add_file(self, file_path: str, change_list_number: int) -> bool:
        """파일을 추가합니다.

        Args:
            file_path (str): 추가할 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 추가 성공 시 True, 실패 시 False
        """
        return self._file_op("add", file_path, change_list_number, "추가")
        
    def add_files(self, file_paths: list, change_list_number: int) -> bool:
        """여러 파일을 한 번에 추가합니다.
        
        Args:
            file_paths (list): 추가할 파일 경로 리스트
            change_list_number (int): 체인지 리스트 번호
            
        Returns:
            bool: 모든 파일 추가 성공 시 True, 하나라도 실패 시 False
        """
        if not file_paths:
            return True
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 add_file() 메서드를 사용하세요."
            raise ValidationError(error_msg)
            
        all_success = True
        for file_path in file_paths:
            success = self.add_file(file_path, change_list_number)
            if not success:
                all_success = False
                
        return all_success

    def delete_file(self, file_path: str, change_list_number: int) -> bool:
        """파일을 삭제합니다.

        Args:
            file_path (str): 삭제할 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 삭제 성공 시 True, 실패 시 False
        """
        return self._file_op("delete", file_path, change_list_number, "삭제")
        
    def delete_files(self, file_paths: list, change_list_number: int) -> bool:
        """여러 파일을 한 번에 삭제합니다.
        
        Args:
            file_paths (list): 삭제할 파일 경로 리스트
            change_list_number (int): 체인지 리스트 번호
            
        Returns:
            bool: 모든 파일 삭제 성공 시 True, 하나라도 실패 시 False
        """
        if not file_paths:
            return True
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 delete_file() 메서드를 사용하세요."
            raise ValidationError(error_msg)
            
        all_success = True
        for file_path in file_paths:
            success = self.delete_file(file_path, change_list_number)
            if not success:
                all_success = False
                
        return all_success

    def submit_change_list(self, change_list_number: int, auto_revert_unchanged: bool = True) -> bool:
        """체인지 리스트를 제출합니다.

        Args:
            change_list_number (int): 제출할 체인지 리스트 번호
            auto_revert_unchanged (bool, optional): 제출 후 변경사항이 없는 체크아웃된 파일들을 
                                                  자동으로 리버트할지 여부. 기본값 True

        Returns:
            bool: 제출 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        
        submit_success = False
        try:
            self.p4.run_submit("-c", change_list_number)
            submit_success = True
        except P4Exception as e:
            if any("nothing to submit" in err.lower() for err in self.p4.errors):
                error_message = f"체인지 리스트 {change_list_number}에 제출할 파일이 없습니다."
            else:
                error_message = f"체인지 리스트 {change_list_number} 제출 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)
        
        # 제출 성공 시 후속 작업 실행
        try:
            # 제출 후 변경사항이 없는 체크아웃된 파일들을 자동으로 리버트
            if auto_revert_unchanged:
                self._auto_revert_unchanged_files(change_list_number)
                self._auto_revert_unchanged_files_in_default_changelist()
            
            # 빈 체인지 리스트 삭제
            self.delete_empty_change_list(change_list_number)
        except Exception as e:
            error_message = f"체인지 리스트 {change_list_number} 제출 후 후속 작업 중 오류 발생: {e}"
            raise PerforceError(error_message)
        
        return submit_success

    def _auto_revert_unchanged_files(self, change_list_number: int) -> None:
        """제출 후 변경사항이 없는 체크아웃된 파일들을 자동으로 리버트합니다.

        Args:
            change_list_number (int): 체인지 리스트 번호
        """
        try:
            # 체인지 리스트에서 체크아웃된 파일들 가져오기
            opened_files = self.p4.run_opened("-c", change_list_number)
            
            if not opened_files:
                return
            
            unchanged_files = []
            for file_info in opened_files:
                file_path = file_info.get('clientFile', '')
                action = file_info.get('action', '')
                
                # edit 액션의 파일만 확인 (add, delete는 변경사항이 있음)
                if action == 'edit':
                    try:
                        # p4 diff 명령으로 파일의 변경사항 확인
                        diff_result = self.p4.run_diff("-sa", file_path)
                        
                        # diff 결과가 비어있으면 변경사항이 없음
                        if not diff_result:
                            unchanged_files.append(file_path)
                            
                    except P4Exception:
                        # diff 명령 실패 시에도 리버트 대상으로 추가 (안전하게 처리)
                        unchanged_files.append(file_path)
            
            # 변경사항이 없는 파일들을 리버트
            if unchanged_files:
                for file_path in unchanged_files:
                    try:
                        self.p4.run_revert("-c", change_list_number, file_path)
                    except P4Exception:
                        pass  # 개별 파일 리버트 실패는 무시
                
        except P4Exception:
            pass  # 자동 리버트 실패는 무시

    def _auto_revert_unchanged_files_in_default_changelist(self) -> None:
        """default change list에서 변경사항이 없는 체크아웃된 파일들을 자동으로 리버트합니다."""
        try:
            # get_default_change_list를 사용해서 default change list의 파일들 가져오기
            default_cl_info = self.get_default_change_list()
            
            if not default_cl_info or not default_cl_info.get('Files'):
                return
            
            files_list = default_cl_info.get('Files', [])
            unchanged_files = []
            
            for file_path in files_list:
                try:
                    # p4 diff 명령으로 파일의 변경사항 확인
                    diff_result = self.p4.run_diff("-sa", file_path)
                    
                    # diff 결과가 비어있으면 변경사항이 없음
                    if not diff_result:
                        unchanged_files.append(file_path)
                        
                except P4Exception:
                    # diff 명령 실패 시에도 리버트 대상으로 추가 (안전하게 처리)
                    unchanged_files.append(file_path)
            
            # 변경사항이 없는 파일들을 리버트
            if unchanged_files:
                for file_path in unchanged_files:
                    try:
                        self.p4.run_revert(file_path)
                    except P4Exception:
                        pass  # 개별 파일 리버트 실패는 무시
                
        except P4Exception:
            pass  # 자동 리버트 실패는 무시

    def revert_change_list(self, change_list_number: int) -> bool:
        """체인지 리스트를 되돌리고 삭제합니다.

        체인지 리스트 내 모든 파일을 되돌린 후 빈 체인지 리스트를 삭제합니다.

        Args:
            change_list_number (int): 되돌릴 체인지 리스트 번호

        Returns:
            bool: 되돌리기 및 삭제 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        try:
            # 체인지 리스트의 모든 파일 되돌리기
            self.p4.run_revert("-c", change_list_number, "//...")
            
            # 빈 체인지 리스트 삭제
            try:
                self.p4.run_change("-d", change_list_number)
            except P4Exception as e_delete:
                error_message = f"체인지 리스트 {change_list_number} 삭제 중 P4Exception 발생: {e_delete}"
                raise PerforceError(error_message)
                
            return True
        except P4Exception as e:
            error_message = f"체인지 리스트 {change_list_number} 전체 되돌리기 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)
    
    def delete_empty_change_list(self, change_list_number: int) -> bool:
        """빈 체인지 리스트를 삭제합니다.

        Args:
            change_list_number (int): 삭제할 체인지 리스트 번호

        Returns:
            bool: 삭제 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        try:
            # 체인지 리스트 정보 가져오기
            change_spec = self.p4.fetch_change(change_list_number)
            
            # 파일이 있는지 확인
            if change_spec and change_spec.get('Files') and len(change_spec['Files']) > 0:
                error_message = f"체인지 리스트 {change_list_number}에 파일이 {len(change_spec['Files'])}개 있어 삭제할 수 없습니다."
                raise PerforceError(error_message)
            
            # 빈 체인지 리스트 삭제
            self.p4.run_change("-d", change_list_number)
            return True
        except P4Exception as e:
            error_message = f"체인지 리스트 {change_list_number} 삭제 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def revert_file(self, file_path: str, change_list_number: int) -> bool:
        """체인지 리스트에서 특정 파일을 되돌립니다.

        Args:
            file_path (str): 되돌릴 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 되돌리기 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        try:
            self.p4.run_revert("-c", change_list_number, file_path)
            return True
        except P4Exception as e:
            error_message = f"파일 '{file_path}'를 체인지 리스트 {change_list_number}에서 되돌리기 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def revert_files(self, change_list_number: int, file_paths: list) -> bool:
        """체인지 리스트 내의 특정 파일들을 되돌립니다.

        Args:
            change_list_number (int): 체인지 리스트 번호
            file_paths (list): 되돌릴 파일 경로 리스트

        Returns:
            bool: 모든 파일 되돌리기 성공 시 True, 하나라도 실패 시 False
        """
        self._ensure_connected()
        if not file_paths:
            return True
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 revert_file() 메서드를 사용하세요."
            raise ValidationError(error_msg)
            
        all_success = True
        for file_path in file_paths:
            success = self.revert_file(file_path, change_list_number)
            if not success:
                all_success = False
                
        return all_success

    def check_update_required(self, file_paths: list) -> bool:
        """파일이나 폴더의 업데이트 필요 여부를 확인합니다.

        Args:
            file_paths (list): 확인할 파일 또는 폴더 경로 리스트. 
                              폴더 경로는 자동으로 재귀적으로 처리됩니다.

        Returns:
            bool: 업데이트가 필요한 파일이 있으면 True, 없으면 False
        """
        self._ensure_connected()
        if not file_paths:
            return False
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요: ['{file_paths}']"
            raise ValidationError(error_msg)
        
        # 폴더 경로에 재귀적 와일드카드 패턴을 추가
        processed_paths = []
        for path in file_paths:
            if os.path.isdir(path):
                # 폴더 경로에 '...'(재귀) 패턴을 추가
                processed_paths.append(os.path.join(path, '...'))
            else:
                processed_paths.append(path)
        
        try:
            sync_preview_results = self.p4.run_sync("-n", processed_paths)
            needs_update = False
            for result in sync_preview_results:
                if isinstance(result, dict):
                    if 'up-to-date' not in result.get('how', '') and \
                       'no such file(s)' not in result.get('depotFile', ''):
                        if result.get('how') and 'syncing' in result.get('how'):
                            needs_update = True
                            break
                        elif result.get('action') and result.get('action') not in ['checked', 'exists']:
                            needs_update = True
                            break
                elif isinstance(result, str):
                    if "up-to-date" not in result and "no such file(s)" not in result:
                        needs_update = True
                        break
            
            return needs_update
        except P4Exception as e:
            # "up-to-date" 메시지는 정상적인 응답이므로 에러로 처리하지 않음
            exception_str = str(e)
            error_messages = [str(err) for err in self.p4.errors]
            warning_messages = [str(warn) for warn in self.p4.warnings]
            
            # P4Exception 자체 메시지나 에러/경고 메시지에서 "up-to-date" 확인
            if ("up-to-date" in exception_str or 
                any("up-to-date" in msg for msg in error_messages) or
                any("up-to-date" in msg for msg in warning_messages)):
                return False
            else:
                error_message = f"파일/폴더 업데이트 필요 여부 확인 ({processed_paths}) 중 P4Exception 발생: {e}"
                raise PerforceError(error_message)

    def is_file_in_perforce(self, file_path: str) -> bool:
        """파일이 Perforce에 속하는지 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            bool: 파일이 Perforce에 속하면 True, 아니면 False
        """
        self._ensure_connected()
        try:
            # p4 files 명령으로 파일 정보 조회
            file_info = self.p4.run_files(file_path)
            
            # 파일 정보가 있고, 'no such file(s)' 오류가 없는 경우
            if file_info and not any("no such file(s)" in str(err).lower() for err in self.p4.errors):
                return True
            else:
                return False
                
        except P4Exception as e:
            # 파일이 존재하지 않는 경우는 일반적인 상황이므로 False 반환
            if any("no such file(s)" in err.lower() for err in self.p4.errors):
                return False
            else:
                error_message = f"파일 '{file_path}' Perforce 존재 여부 확인 중 P4Exception 발생: {e}"
                raise PerforceError(error_message)

    def sync_files(self, file_paths: list) -> bool:
        """파일이나 폴더를 동기화합니다.

        Args:
            file_paths (list): 동기화할 파일 또는 폴더 경로 리스트.
                              폴더 경로는 자동으로 재귀적으로 처리됩니다.

        Returns:
            bool: 동기화 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        if not file_paths:
            return True
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요: ['{file_paths}']"
            raise ValidationError(error_msg)
        
        # 폴더 경로에 재귀적 와일드카드 패턴을 추가
        processed_paths = []
        for path in file_paths:
            if os.path.isdir(path):
                # 폴더 경로에 '...'(재귀) 패턴을 추가
                processed_paths.append(os.path.join(path, '...'))
            else:
                processed_paths.append(path)
        
        try:
            self.p4.run_sync(processed_paths)
            return True
        except P4Exception as e:
            # "file(s) up-to-date" 메시지는 정상적인 상황이므로 에러로 처리하지 않음
            error_str = str(e)
            if "file(s) up-to-date" in error_str:
                # 파일이 이미 최신 상태인 경우 성공으로 처리
                return True
            else:
                # 실제 에러인 경우에만 PerforceError 발생
                error_message = f"파일/폴더 싱크 실패 ({processed_paths}) 중 P4Exception 발생: {e}"
                raise PerforceError(error_message)

    def get_default_change_list(self) -> dict:
        """default change list의 정보를 가져옵니다.

        Returns:
            dict: get_change_list_by_number와 동일한 형태의 딕셔너리
        """
        self._ensure_connected()
        try:
            opened_files = self.p4.run_opened("-c", "default")
            files_list = [f.get('clientFile', '') for f in opened_files]
            result = {
                'Change': 'default',
                'Description': 'Default change',
                'User': getattr(self.p4, 'user', ''),
                'Client': getattr(self.p4, 'client', ''),
                'Status': 'pending',
                'Files': files_list
            }
            return result
        except P4Exception as e:
            error_message = f"default change list 정보 조회 실패 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def check_files_checked_out_all_users(self, file_paths: list) -> dict:
        """파일들의 체크아웃 상태를 모든 사용자/워크스페이스에서 확인합니다.

        Args:
            file_paths (list): 확인할 파일 경로 리스트

        Returns:
            dict: 파일별 체크아웃 상태 정보
                 {
                     'file_path': {
                         'is_checked_out': bool,
                         'change_list': int or None,
                         'action': str or None,
                         'user': str or None,
                         'client': str or None
                     }
                 }
        """
        self._ensure_connected()
        if not file_paths:
            return {}
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 get_file_checkout_info_all_users() 메서드를 사용하세요."
            raise ValidationError(error_msg)
        
        result = {}
        try:
            # 각 파일의 상태 확인
            for file_path in file_paths:
                file_status = {
                    'is_checked_out': False,
                    'change_list': None,
                    'action': None,
                    'user': None,
                    'client': None
                }
                
                try:
                    # p4 opened -a 명령으로 모든 사용자의 파일 체크아웃 상태 확인
                    opened_files = self.p4.run_opened("-a", file_path)
                    
                    if opened_files:
                        # 파일이 체크아웃되어 있음 (첫 번째 결과 사용)
                        file_info = opened_files[0]
                        file_status['is_checked_out'] = True
                        file_status['change_list'] = int(file_info.get('change', 0))
                        file_status['action'] = file_info.get('action', '')
                        file_status['user'] = file_info.get('user', '')
                        file_status['client'] = file_info.get('client', '')
                        
                except P4Exception as e:
                    # 파일이 perforce에 없거나 접근할 수 없는 경우
                    if not any("not opened" in err.lower() or "no such file" in err.lower() 
                               for err in self.p4.errors):
                        error_message = f"파일 '{file_path}' 체크아웃 상태 확인 (모든 사용자) 중 P4Exception 발생: {e}"
                        raise PerforceError(error_message)
                
                result[file_path] = file_status
            
            return result
            
        except P4Exception as e:
            error_message = f"파일들 체크아웃 상태 확인 - 모든 사용자 ({file_paths}) 중 P4Exception 발생: {e}"
            raise PerforceError(error_message)

    def is_file_checked_out_by_others(self, file_path: str) -> bool:
        """단일 파일이 다른 사용자/워크스페이스에 의해 체크아웃되어 있는지 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            bool: 다른 사용자에 의해 체크아웃되어 있으면 True, 아니면 False
        """
        result = self.check_files_checked_out_all_users([file_path])
        file_status = result.get(file_path, {})
        
        if not file_status.get('is_checked_out', False):
            return False
        
        # 현재 사용자와 클라이언트가 아닌 경우 다른 사용자로 간주
        current_user = self.p4.user
        current_client = self.p4.client
        
        file_user = file_status.get('user', '')
        file_client = file_status.get('client', '')
        
        return (file_user != current_user) or (file_client != current_client)

    def get_file_checkout_info_all_users(self, file_path: str) -> dict:
        """단일 파일의 상세 체크아웃 정보를 모든 사용자에서 가져옵니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            dict: 체크아웃 정보 또는 빈 딕셔너리
                 {
                     'is_checked_out': bool,
                     'change_list': int or None,
                     'action': str or None,
                     'user': str or None,
                     'client': str or None,
                     'is_checked_out_by_current_user': bool,
                     'is_checked_out_by_others': bool
                 }
        """
        result = self.check_files_checked_out_all_users([file_path])
        file_status = result.get(file_path, {})
        
        if file_status.get('is_checked_out', False):
            # 현재 사용자와 클라이언트인지 확인
            current_user = self.p4.user
            current_client = self.p4.client
            
            file_user = file_status.get('user', '')
            file_client = file_status.get('client', '')
            
            is_current_user = (file_user == current_user) and (file_client == current_client)
            
            file_status['is_checked_out_by_current_user'] = is_current_user
            file_status['is_checked_out_by_others'] = not is_current_user
        else:
            file_status['is_checked_out_by_current_user'] = False
            file_status['is_checked_out_by_others'] = False
        
        return file_status

    def get_files_checked_out_by_others(self, file_paths: list) -> list:
        """파일 목록에서 다른 사용자/워크스페이스에 의해 체크아웃된 파일들을 찾습니다.

        Args:
            file_paths (list): 확인할 파일 경로 리스트

        Returns:
            list: 다른 사용자에 의해 체크아웃된 파일 정보 리스트
                  [
                      {
                          'file_path': str,
                          'user': str,
                          'client': str,
                          'change_list': int,
                          'action': str
                      }
                  ]
        """
        if not file_paths:
            return []
        
        # 타입 검증: 리스트가 아닌 경우 에러 발생
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 is_file_checked_out_by_others() 메서드를 사용하세요."
            raise ValidationError(error_msg)
        
        result = self.check_files_checked_out_all_users(file_paths)
        files_by_others = []
        
        current_user = self.p4.user
        current_client = self.p4.client
        
        for file_path, status in result.items():
            if status.get('is_checked_out', False):
                file_user = status.get('user', '')
                file_client = status.get('client', '')
                
                # 다른 사용자/클라이언트에 의해 체크아웃된 경우
                if (file_user != current_user) or (file_client != current_client):
                    files_by_others.append({
                        'file_path': file_path,
                        'user': file_user,
                        'client': file_client,
                        'change_list': status.get('change_list'),
                        'action': status.get('action', '')
                    })
        
        return files_by_others 