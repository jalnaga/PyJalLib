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
from pathlib import Path
from .exceptions import PerforceError, ValidationError
from .perforceCore import P4Adapter, PerforceService


class Perforce:
    """P4Python을 사용하여 Perforce 작업을 수행하는 클래스."""

    def __init__(self):
        """Perforce 인스턴스를 초기화합니다."""
        # 코어 서비스 구성
        self._adapter = P4Adapter()
        self._service = PerforceService(self._adapter, in_auto_revert_unchanged=True)
        # 레거시 호환: p4 핸들 노출 유지
        self.p4 = self._adapter.p4
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
        """Perforce 서버 연결 상태를 확인하고 연결되지 않은 경우 예외를 발생시킵니다."""
        if not self._service.is_connected:
            raise PerforceError("Perforce 서버에 연결되지 않았습니다.")

    def connect(self, workspace_name: str) -> bool:
        """지정된 워크스페이스에 연결합니다.

        Args:
            workspace_name (str): 연결할 워크스페이스 이름

        Returns:
            bool: 연결 성공 시 True, 실패 시 False
        """
        try:
            self._service.connect(workspace_name)
            self.connected = True
            self.workspaceRoot = self._adapter.workspaceRoot or ""
            return True
        except PerforceError as e:
            self.connected = False
            raise

    def get_pending_change_list(self) -> list:
        """워크스페이스의 Pending된 체인지 리스트를 가져옵니다.

        Returns:
            list: 체인지 리스트 정보 딕셔너리들의 리스트
        """
        self._ensure_connected()
        try:
            dtos = self._service.get_pending_changelists()
            return [dto.to_dict() for dto in dtos]
        except PerforceError:
            raise

    def create_change_list(self, description: str) -> dict:
        """새로운 체인지 리스트를 생성합니다.

        Args:
            description (str): 체인지 리스트 설명

        Returns:
            dict: 생성된 체인지 리스트 정보. 실패 시 빈 딕셔너리
        """
        self._ensure_connected()
        dto = self._service.create_changelist(description)
        return dto.to_dict()

    def get_change_list_by_number(self, change_list_number: int) -> dict:
        """체인지 리스트 번호로 체인지 리스트를 가져옵니다.

        Args:
            change_list_number (int): 체인지 리스트 번호

        Returns:
            dict: 체인지 리스트 정보. 실패 시 빈 딕셔너리
        """
        self._ensure_connected()
        dto = self._service.get_changelist_by_number(change_list_number)
        return dto.to_dict()

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
            normalized_file_path = str(Path(file_path).resolve())
            
            for file_info in opened_files:
                client_file = file_info.get('clientFile', '')
                normalized_client_file = str(Path(client_file).resolve())
                
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
        dto = self._service.edit_changelist(change_list_number, description, add_file_paths, remove_file_paths)
        return dto.to_dict()

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
        if command == "edit":
            self._service.checkout([file_path], change_list_number)
        elif command == "add":
            self._service.add([file_path], change_list_number)
        elif command == "delete":
            self._service.delete([file_path], change_list_number)
        else:
            error_message = f"지원되지 않는 파일 작업: {command}"
            raise ValidationError(error_message)
        return True

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
        self._service.submit_changelist(change_list_number, auto_revert_unchanged)
        
        # 제출 후 체인지리스트가 여전히 pending 상태로 남아있는 경우만 삭제 시도
        try:
            cl_info = self._service.get_changelist_by_number(change_list_number)
            # pending 상태이고 파일이 없으면 빈 체인지리스트이므로 삭제
            if cl_info.status == "pending" and not cl_info.files:
                self.delete_empty_change_list(change_list_number)
        except PerforceError:
            # 체인지리스트를 찾을 수 없으면 이미 제출되었거나 삭제된 것이므로 무시
            pass
        
        return True

    

    def revert_change_list(self, change_list_number: int) -> bool:
        """체인지 리스트를 되돌리고 삭제합니다.

        체인지 리스트 내 모든 파일을 되돌린 후 빈 체인지 리스트를 삭제합니다.

        Args:
            change_list_number (int): 되돌릴 체인지 리스트 번호

        Returns:
            bool: 되돌리기 및 삭제 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        self._service.revert_changelist(change_list_number)
        return True
    
    def delete_empty_change_list(self, change_list_number: int) -> bool:
        """빈 체인지 리스트를 삭제합니다.

        Args:
            change_list_number (int): 삭제할 체인지 리스트 번호

        Returns:
            bool: 삭제 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        self._service.delete_empty_changelist(change_list_number)
        return True

    def revert_file(self, file_path: str, change_list_number: int) -> bool:
        """체인지 리스트에서 특정 파일을 되돌립니다.

        Args:
            file_path (str): 되돌릴 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 되돌리기 성공 시 True, 실패 시 False
        """
        self._ensure_connected()
        self._service.revert([file_path], change_list_number)
        return True

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
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 revert_file() 메서드를 사용하세요."
            raise ValidationError(error_msg)
        self._service.revert(file_paths, change_list_number)
        return True

    def check_update_required(self, file_paths: list) -> bool:
        """파일이나 폴더의 업데이트 필요 여부를 확인합니다.

        Args:
            file_paths (list): 확인할 파일 또는 폴더 경로 리스트. 
                              폴더 경로는 자동으로 재귀적으로 처리됩니다.

        Returns:
            bool: 업데이트가 필요한 파일이 있으면 True, 없으면 False
        """
        self._ensure_connected()
        return self._service.check_update_required(file_paths)

    def is_file_in_perforce(self, file_path: str) -> bool:
        """파일이 Perforce에 속하는지 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            bool: 파일이 Perforce에 속하면 True, 아니면 False
        """
        self._ensure_connected()
        res = self._service.is_in_perforce([file_path])
        # 어떤 키로 들어오든 하나라도 True이면 True 처리
        return any(res.values())

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
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 경로도 리스트로 감싸서 전달하세요: ['{file_paths}']"
            raise ValidationError(error_msg)
        self._service.sync(file_paths)
        return True

    def get_default_change_list(self) -> dict:
        """default change list의 정보를 가져옵니다.

        Returns:
            dict: get_change_list_by_number와 동일한 형태의 딕셔너리
        """
        self._ensure_connected()
        dto = self._service.get_default_changelist()
        return dto.to_dict()

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
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 get_file_checkout_info_all_users() 메서드를 사용하세요."
            raise ValidationError(error_msg)
        status = self._service.get_checkout_status(file_paths, in_scope="all")
        result = {}
        for path in file_paths:
            norm = str(Path(path).resolve())
            fi = status.get(norm)
            if fi and fi.isCheckedOut:
                result[path] = {
                    'is_checked_out': True,
                    'change_list': fi.changeList,
                    'action': fi.action or '',
                    'user': fi.user or '',
                    'client': fi.client or '',
                }
            else:
                result[path] = {
                    'is_checked_out': False,
                    'change_list': None,
                    'action': None,
                    'user': None,
                    'client': None,
                }
        return result

    def is_file_checked_out_by_others(self, file_path: str) -> bool:
        """단일 파일이 다른 사용자/워크스페이스에 의해 체크아웃되어 있는지 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            bool: 다른 사용자에 의해 체크아웃되어 있으면 True, 아니면 False
        """
        status = self._service.get_checkout_status([file_path], in_scope="all")
        norm = str(Path(file_path).resolve())
        fi = status.get(norm)
        return bool(fi and fi.isCheckedOut and fi.isOthers)

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
        status = self._service.get_checkout_status([file_path], in_scope="all")
        norm = str(Path(file_path).resolve())
        fi = status.get(norm)
        if not fi:
            return {
                'is_checked_out': False,
                'change_list': None,
                'action': None,
                'user': None,
                'client': None,
                'is_checked_out_by_current_user': False,
                'is_checked_out_by_others': False,
            }
        return {
            'is_checked_out': fi.isCheckedOut,
            'change_list': fi.changeList,
            'action': fi.action,
            'user': fi.user,
            'client': fi.client,
            'is_checked_out_by_current_user': fi.isCurrentUser,
            'is_checked_out_by_others': fi.isOthers,
        }

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
        
        if not file_paths:
            return []
        if not isinstance(file_paths, list):
            error_msg = f"file_paths는 리스트여야 합니다. 전달된 타입: {type(file_paths).__name__}. 단일 파일은 is_file_checked_out_by_others() 메서드를 사용하세요."
            raise ValidationError(error_msg)
        status = self._service.get_checkout_status(file_paths, in_scope="all")
        files_by_others = []
        for path in file_paths:
            norm = str(Path(path).resolve())
            fi = status.get(norm)
            if fi and fi.isCheckedOut and fi.isOthers:
                files_by_others.append({
                    'file_path': path,
                    'user': fi.user or '',
                    'client': fi.client or '',
                    'change_list': fi.changeList,
                    'action': fi.action or '',
                })
        return files_by_others 