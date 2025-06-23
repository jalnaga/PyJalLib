"""
P4Python을 사용하는 Perforce 모듈.

이 모듈은 P4Python을 사용하여 Perforce 서버와 상호작용하는 기능을 제공합니다.
주요 기능:
- 워크스페이스 연결
- 체인지리스트 관리 (생성, 조회, 편집, 제출, 되돌리기)
- 파일 작업 (체크아웃, 추가, 삭제)
- 파일 동기화 및 업데이트 확인
"""

import logging
from P4 import P4, P4Exception
import os
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)

# 기본 로그 레벨은 ERROR로 설정 (디버그 모드는 생성자에서 설정)
logger.setLevel(logging.ERROR)

# 사용자 문서 폴더 내 로그 파일 저장
log_path = os.path.join(Path.home() / "Documents", 'Perforce.log')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.ERROR)  # 기본적으로 ERROR 레벨만 기록
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class Perforce:
    """P4Python을 사용하여 Perforce 작업을 수행하는 클래스."""

    def __init__(self, debug_mode: bool = False):
        """Perforce 인스턴스를 초기화합니다.
        
        Args:
            debug_mode (bool): True로 설정하면 DEBUG 레벨 로그를 활성화합니다. 
                             기본값은 False (ERROR 레벨만 기록)
        """
        # 디버그 모드에 따라 로그 레벨 설정
        if debug_mode:
            logger.setLevel(logging.DEBUG)
            file_handler.setLevel(logging.DEBUG)
            logger.debug("디버그 모드가 활성화되었습니다.")
        
        self.p4 = P4()
        self.connected = False
        self.workspaceRoot = r""
        logger.info("Perforce 인스턴스 생성됨")

    def _is_connected(self) -> bool:
        """Perforce 서버 연결 상태를 확인합니다.

        Returns:
            bool: 연결되어 있으면 True, 아니면 False
        """
        if not self.connected:
            logger.warning("Perforce 서버에 연결되지 않았습니다.")
            return False
        return True

    def _handle_p4_exception(self, e: P4Exception, context_msg: str = "") -> None:
        """P4Exception을 처리하고 로깅합니다.

        Args:
            e (P4Exception): 발생한 예외
            context_msg (str, optional): 예외가 발생한 컨텍스트 설명
        """
        logger.error(f"{context_msg} 중 P4Exception 발생: {e}")
        for err in self.p4.errors:
            logger.error(f"  P4 Error: {err}")
        for warn in self.p4.warnings:
            logger.warning(f"  P4 Warning: {warn}")

    def connect(self, workspace_name: str) -> bool:
        """지정된 워크스페이스에 연결합니다.

        Args:
            workspace_name (str): 연결할 워크스페이스 이름

        Returns:
            bool: 연결 성공 시 True, 실패 시 False
        """
        logger.info(f"'{workspace_name}' 워크스페이스에 연결 시도 중...")
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
                logger.info(f"워크스페이스 루트 절대 경로: {self.workspaceRoot}")
            except (IndexError, KeyError) as e:
                logger.error(f"워크스페이스 루트 경로 가져오기 실패: {e}")
                self.workspaceRoot = ""
                
            logger.info(f"'{workspace_name}' 워크스페이스에 성공적으로 연결됨 (User: {self.p4.user}, Port: {self.p4.port})")
            return True
        except P4Exception as e:
            self.connected = False
            self._handle_p4_exception(e, f"'{workspace_name}' 워크스페이스 연결")
            return False

    def get_pending_change_list(self) -> list:
        """워크스페이스의 Pending된 체인지 리스트를 가져옵니다.

        Returns:
            list: 체인지 리스트 정보 딕셔너리들의 리스트
        """
        if not self._is_connected():
            return []
        logger.debug("Pending 체인지 리스트 조회 중...")
        try:
            pending_changes = self.p4.run_changes("-s", "pending", "-u", self.p4.user, "-c", self.p4.client)
            change_numbers = [int(cl['change']) for cl in pending_changes]
            
            # 각 체인지 리스트 번호에 대한 상세 정보 가져오기
            change_list_info = []
            for change_number in change_numbers:
                cl_info = self.get_change_list_by_number(change_number)
                if cl_info:
                    change_list_info.append(cl_info)
            
            logger.info(f"Pending 체인지 리스트 {len(change_list_info)}개 조회 완료")
            return change_list_info
        except P4Exception as e:
            self._handle_p4_exception(e, "Pending 체인지 리스트 조회")
            return []

    def create_change_list(self, description: str) -> dict:
        """새로운 체인지 리스트를 생성합니다.

        Args:
            description (str): 체인지 리스트 설명

        Returns:
            dict: 생성된 체인지 리스트 정보. 실패 시 빈 딕셔너리
        """
        if not self._is_connected():
            return {}
        logger.info(f"새 체인지 리스트 생성 시도: '{description}'")
        try:
            change_spec = self.p4.fetch_change()
            change_spec["Description"] = description
            result = self.p4.save_change(change_spec)
            created_change_number = int(result[0].split()[1])
            logger.info(f"체인지 리스트 {created_change_number} 생성 완료: '{description}'")
            return self.get_change_list_by_number(created_change_number)
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 생성 ('{description}')")
            return {}
        except (IndexError, ValueError) as e:
            logger.error(f"체인지 리스트 번호 파싱 오류: {e}")
            return {}

    def get_change_list_by_number(self, change_list_number: int) -> dict:
        """체인지 리스트 번호로 체인지 리스트를 가져옵니다.

        Args:
            change_list_number (int): 체인지 리스트 번호

        Returns:
            dict: 체인지 리스트 정보. 실패 시 빈 딕셔너리
        """
        if not self._is_connected():
            return {}
        logger.debug(f"체인지 리스트 {change_list_number} 정보 조회 중...")
        try:
            cl_info = self.p4.fetch_change(change_list_number)
            if cl_info:
                logger.info(f"체인지 리스트 {change_list_number} 정보 조회 완료.")
                return cl_info
            else:
                logger.warning(f"체인지 리스트 {change_list_number}를 찾을 수 없습니다.")
                return {}
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 정보 조회")
            return {}

    def get_change_list_by_description(self, description: str) -> dict:
        """체인지 리스트 설명으로 체인지 리스트를 가져옵니다.

        Args:
            description (str): 체인지 리스트 설명

        Returns:
            dict: 체인지 리스트 정보 (일치하는 첫 번째 체인지 리스트)
        """
        if not self._is_connected():
            return {}
        logger.debug(f"설명으로 체인지 리스트 조회 중: '{description}'")
        try:
            pending_changes = self.p4.run_changes("-l", "-s", "pending", "-u", self.p4.user, "-c", self.p4.client)
            for cl in pending_changes:
                cl_desc = cl.get('Description', b'').decode('utf-8', 'replace').strip()
                if cl_desc == description.strip():
                    logger.info(f"설명 '{description}'에 해당하는 체인지 리스트 {cl['change']} 조회 완료.")
                    return self.get_change_list_by_number(int(cl['change']))
            logger.info(f"설명 '{description}'에 해당하는 Pending 체인지 리스트를 찾을 수 없습니다.")
            return {}
        except P4Exception as e:
            self._handle_p4_exception(e, f"설명으로 체인지 리스트 조회 ('{description}')")
            return {}

    def get_change_list_by_description_pattern(self, description_pattern: str, exact_match: bool = False) -> list:
        """설명 패턴과 일치하는 Pending 체인지 리스트들을 가져옵니다.

        Args:
            description_pattern (str): 검색할 설명 패턴
            exact_match (bool, optional): True면 정확히 일치하는 설명만, 
                                        False면 패턴이 포함된 설명도 포함. 기본값 False

        Returns:
            list: 패턴과 일치하는 체인지 리스트 정보들의 리스트
        """
        if not self._is_connected():
            return []
        
        search_type = "정확히 일치" if exact_match else "패턴 포함"
        logger.debug(f"설명 패턴으로 체인지 리스트 조회 중 ({search_type}): '{description_pattern}'")
        
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
                        logger.info(f"패턴 '{description_pattern}'에 매칭되는 체인지 리스트 {change_number} 발견: '{cl_desc}'")
            
            if matching_changes:
                logger.info(f"패턴 '{description_pattern}'에 매칭되는 체인지 리스트 {len(matching_changes)}개 조회 완료.")
            else:
                logger.info(f"패턴 '{description_pattern}'에 매칭되는 Pending 체인지 리스트를 찾을 수 없습니다.")
            
            return matching_changes
        except P4Exception as e:
            self._handle_p4_exception(e, f"설명 패턴으로 체인지 리스트 조회 ('{description_pattern}')")
            return []

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
        if not self._is_connected():
            return {}
        if not file_paths:
            logger.debug("체크아웃 상태 확인할 파일 목록이 비어있습니다.")
            return {}
        
        logger.debug(f"파일 체크아웃 상태 확인 중 (파일 {len(file_paths)}개)")
        
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
                        
                        logger.debug(f"파일 '{file_path}' 체크아웃됨: CL {file_status['change_list']}, "
                                   f"액션: {file_status['action']}, 사용자: {file_status['user']}, "
                                   f"워크스페이스: {file_status['workspace']}")
                    else:
                        # 파일이 체크아웃되지 않음
                        logger.debug(f"파일 '{file_path}' 체크아웃되지 않음")
                        
                except P4Exception as e:
                    # 파일이 perforce에 없거나 접근할 수 없는 경우
                    if any("not opened" in err.lower() or "no such file" in err.lower() 
                           for err in self.p4.errors):
                        logger.debug(f"파일 '{file_path}' 체크아웃되지 않음 (perforce에 없거나 접근 불가)")
                    else:
                        self._handle_p4_exception(e, f"파일 '{file_path}' 체크아웃 상태 확인")
                
                result[file_path] = file_status
            
            checked_out_count = sum(1 for status in result.values() if status['is_checked_out'])
            logger.info(f"파일 체크아웃 상태 확인 완료: 전체 {len(file_paths)}개 중 {checked_out_count}개 체크아웃됨")
            
            return result
            
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일들 체크아웃 상태 확인 ({file_paths})")
            return {}

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
        if not self._is_connected():
            return False
        
        logger.debug(f"파일 '{file_path}'가 체인지 리스트 {change_list_number}에 있는지 확인 중...")
        
        try:
            # 해당 체인지 리스트의 파일들 가져오기
            opened_files = self.p4.run_opened("-c", change_list_number)
            
            # 파일 경로 정규화
            normalized_file_path = os.path.normpath(file_path)
            
            for file_info in opened_files:
                client_file = file_info.get('clientFile', '')
                normalized_client_file = os.path.normpath(client_file)
                
                if normalized_client_file == normalized_file_path:
                    logger.debug(f"파일 '{file_path}'가 체인지 리스트 {change_list_number}에서 발견됨 "
                               f"(액션: {file_info.get('action', '')})")
                    return True
            
            logger.debug(f"파일 '{file_path}'가 체인지 리스트 {change_list_number}에 없음")
            return False
            
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일 '{file_path}' 체인지 리스트 {change_list_number} 포함 여부 확인")
            return False

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
        if not self._is_connected():
            return {}
        logger.info(f"체인지 리스트 {change_list_number} 편집 시도...")
        try:
            if description is not None:
                change_spec = self.p4.fetch_change(change_list_number)
                current_description = change_spec.get('Description', '').strip()
                if current_description != description.strip():
                    change_spec['Description'] = description
                    self.p4.save_change(change_spec)
                    logger.info(f"체인지 리스트 {change_list_number} 설명 변경 완료: '{description}'")

            if add_file_paths:
                for file_path in add_file_paths:
                    try:
                        self.p4.run_reopen("-c", change_list_number, file_path)
                        logger.info(f"파일 '{file_path}'를 체인지 리스트 {change_list_number}로 이동 완료.")
                    except P4Exception as e_reopen:
                        self._handle_p4_exception(e_reopen, f"파일 '{file_path}'을 CL {change_list_number}로 이동")

            if remove_file_paths:
                for file_path in remove_file_paths:
                    try:
                        self.p4.run_revert("-c", change_list_number, file_path)
                        logger.info(f"파일 '{file_path}'를 체인지 리스트 {change_list_number}에서 제거(revert) 완료.")
                    except P4Exception as e_revert:
                        self._handle_p4_exception(e_revert, f"파일 '{file_path}'을 CL {change_list_number}에서 제거(revert)")

            return self.get_change_list_by_number(change_list_number)

        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 편집")
            return self.get_change_list_by_number(change_list_number)

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
        if not self._is_connected():
            return False
        logger.info(f"파일 '{file_path}'에 대한 '{op_name}' 작업 시도 (CL: {change_list_number})...")
        try:
            if command == "edit":
                self.p4.run_edit("-c", change_list_number, file_path)
            elif command == "add":
                self.p4.run_add("-c", change_list_number, file_path)
            elif command == "delete":
                self.p4.run_delete("-c", change_list_number, file_path)
            else:
                logger.error(f"지원되지 않는 파일 작업: {command}")
                return False
            logger.info(f"파일 '{file_path}'에 대한 '{op_name}' 작업 성공 (CL: {change_list_number}).")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일 '{file_path}' {op_name} (CL: {change_list_number})")
            return False

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
            logger.debug("체크아웃할 파일 목록이 비어있습니다.")
            return True
            
        logger.info(f"체인지 리스트 {change_list_number}에 {len(file_paths)}개 파일 체크아웃 시도...")
        
        all_success = True
        for file_path in file_paths:
            success = self.checkout_file(file_path, change_list_number)
            if not success:
                all_success = False
                logger.warning(f"파일 '{file_path}' 체크아웃 실패")
                
        if all_success:
            logger.info(f"모든 파일({len(file_paths)}개)을 체인지 리스트 {change_list_number}에 성공적으로 체크아웃했습니다.")
        else:
            logger.warning(f"일부 파일을 체인지 리스트 {change_list_number}에 체크아웃하지 못했습니다.")
            
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
            logger.debug("추가할 파일 목록이 비어있습니다.")
            return True
            
        logger.info(f"체인지 리스트 {change_list_number}에 {len(file_paths)}개 파일 추가 시도...")
        
        all_success = True
        for file_path in file_paths:
            success = self.add_file(file_path, change_list_number)
            if not success:
                all_success = False
                logger.warning(f"파일 '{file_path}' 추가 실패")
                
        if all_success:
            logger.info(f"모든 파일({len(file_paths)}개)을 체인지 리스트 {change_list_number}에 성공적으로 추가했습니다.")
        else:
            logger.warning(f"일부 파일을 체인지 리스트 {change_list_number}에 추가하지 못했습니다.")
            
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
            logger.debug("삭제할 파일 목록이 비어있습니다.")
            return True
            
        logger.info(f"체인지 리스트 {change_list_number}에서 {len(file_paths)}개 파일 삭제 시도...")
        
        all_success = True
        for file_path in file_paths:
            success = self.delete_file(file_path, change_list_number)
            if not success:
                all_success = False
                logger.warning(f"파일 '{file_path}' 삭제 실패")
                
        if all_success:
            logger.info(f"모든 파일({len(file_paths)}개)을 체인지 리스트 {change_list_number}에서 성공적으로 삭제했습니다.")
        else:
            logger.warning(f"일부 파일을 체인지 리스트 {change_list_number}에서 삭제하지 못했습니다.")
            
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
        if not self._is_connected():
            return False
        logger.info(f"체인지 리스트 {change_list_number} 제출 시도...")
        try:
            self.p4.run_submit("-c", change_list_number)
            logger.info(f"체인지 리스트 {change_list_number} 제출 성공.")
            
            # 제출 후 변경사항이 없는 체크아웃된 파일들을 자동으로 리버트
            if auto_revert_unchanged:
                self._auto_revert_unchanged_files(change_list_number)
            
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 제출")
            if any("nothing to submit" in err.lower() for err in self.p4.errors):
                logger.warning(f"체인지 리스트 {change_list_number}에 제출할 파일이 없습니다.")
            return False

    def _auto_revert_unchanged_files(self, change_list_number: int) -> None:
        """제출 후 변경사항이 없는 체크아웃된 파일들을 자동으로 리버트합니다.

        Args:
            change_list_number (int): 체인지 리스트 번호
        """
        logger.debug(f"체인지 리스트 {change_list_number}에서 변경사항이 없는 파일들 자동 리버트 시도...")
        try:
            # 체인지 리스트에서 체크아웃된 파일들 가져오기
            opened_files = self.p4.run_opened("-c", change_list_number)
            
            if not opened_files:
                logger.debug(f"체인지 리스트 {change_list_number}에 체크아웃된 파일이 없습니다.")
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
                            logger.debug(f"파일 '{file_path}'에 변경사항이 없어 리버트 대상으로 추가")
                        else:
                            logger.debug(f"파일 '{file_path}'에 변경사항이 있어 리버트하지 않음")
                            
                    except P4Exception as e:
                        # diff 명령 실패 시에도 리버트 대상으로 추가 (안전하게 처리)
                        unchanged_files.append(file_path)
                        logger.debug(f"파일 '{file_path}' diff 확인 실패, 리버트 대상으로 추가: {e}")
                else:
                    logger.debug(f"파일 '{file_path}'는 {action} 액션이므로 리버트하지 않음")
            
            # 변경사항이 없는 파일들을 리버트
            if unchanged_files:
                logger.info(f"체인지 리스트 {change_list_number}에서 변경사항이 없는 파일 {len(unchanged_files)}개 자동 리버트 시도...")
                for file_path in unchanged_files:
                    try:
                        self.p4.run_revert("-c", change_list_number, file_path)
                        logger.info(f"파일 '{file_path}' 자동 리버트 완료")
                    except P4Exception as e:
                        self._handle_p4_exception(e, f"파일 '{file_path}' 자동 리버트")
                logger.info(f"체인지 리스트 {change_list_number}에서 변경사항이 없는 파일 {len(unchanged_files)}개 자동 리버트 완료")
            else:
                logger.debug(f"체인지 리스트 {change_list_number}에서 변경사항이 없는 파일이 없습니다.")
            
            # default change list에서도 변경사항이 없는 파일들 처리
            self._auto_revert_unchanged_files_in_default_changelist()
                
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 자동 리버트 처리")

    def _auto_revert_unchanged_files_in_default_changelist(self) -> None:
        """default change list에서 변경사항이 없는 체크아웃된 파일들을 자동으로 리버트합니다."""
        logger.debug("default change list에서 변경사항이 없는 파일들 자동 리버트 시도...")
        try:
            # default change list에서 체크아웃된 파일들 가져오기
            opened_files = self.p4.run_opened("-c", "default")
            
            if not opened_files:
                logger.debug("default change list에 체크아웃된 파일이 없습니다.")
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
                            logger.debug(f"default change list의 파일 '{file_path}'에 변경사항이 없어 리버트 대상으로 추가")
                        else:
                            logger.debug(f"default change list의 파일 '{file_path}'에 변경사항이 있어 리버트하지 않음")
                            
                    except P4Exception as e:
                        # diff 명령 실패 시에도 리버트 대상으로 추가 (안전하게 처리)
                        unchanged_files.append(file_path)
                        logger.debug(f"default change list의 파일 '{file_path}' diff 확인 실패, 리버트 대상으로 추가: {e}")
                else:
                    logger.debug(f"default change list의 파일 '{file_path}'는 {action} 액션이므로 리버트하지 않음")
            
            # 변경사항이 없는 파일들을 리버트
            if unchanged_files:
                logger.info(f"default change list에서 변경사항이 없는 파일 {len(unchanged_files)}개 자동 리버트 시도...")
                for file_path in unchanged_files:
                    try:
                        self.p4.run_revert(file_path)
                        logger.info(f"default change list의 파일 '{file_path}' 자동 리버트 완료")
                    except P4Exception as e:
                        self._handle_p4_exception(e, f"default change list의 파일 '{file_path}' 자동 리버트")
                logger.info(f"default change list에서 변경사항이 없는 파일 {len(unchanged_files)}개 자동 리버트 완료")
            else:
                logger.debug("default change list에서 변경사항이 없는 파일이 없습니다.")
                
        except P4Exception as e:
            self._handle_p4_exception(e, "default change list 자동 리버트 처리")

    def revert_change_list(self, change_list_number: int) -> bool:
        """체인지 리스트를 되돌리고 삭제합니다.

        체인지 리스트 내 모든 파일을 되돌린 후 빈 체인지 리스트를 삭제합니다.

        Args:
            change_list_number (int): 되돌릴 체인지 리스트 번호

        Returns:
            bool: 되돌리기 및 삭제 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
        logger.info(f"체인지 리스트 {change_list_number} 전체 되돌리기 및 삭제 시도...")
        try:
            # 체인지 리스트의 모든 파일 되돌리기
            self.p4.run_revert("-c", change_list_number, "//...")
            logger.info(f"체인지 리스트 {change_list_number} 전체 되돌리기 성공.")
            
            # 빈 체인지 리스트 삭제
            try:
                self.p4.run_change("-d", change_list_number)
                logger.info(f"체인지 리스트 {change_list_number} 삭제 완료.")
            except P4Exception as e_delete:
                self._handle_p4_exception(e_delete, f"체인지 리스트 {change_list_number} 삭제")
                logger.warning(f"파일 되돌리기는 성공했으나 체인지 리스트 {change_list_number} 삭제에 실패했습니다.")
                return False
                
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 전체 되돌리기")
            return False
    
    def delete_empty_change_list(self, change_list_number: int) -> bool:
        """빈 체인지 리스트를 삭제합니다.

        Args:
            change_list_number (int): 삭제할 체인지 리스트 번호

        Returns:
            bool: 삭제 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
        
        logger.info(f"체인지 리스트 {change_list_number} 삭제 시도 중...")
        try:
            # 체인지 리스트 정보 가져오기
            change_spec = self.p4.fetch_change(change_list_number)
            
            # 파일이 있는지 확인
            if change_spec and change_spec.get('Files') and len(change_spec['Files']) > 0:
                logger.warning(f"체인지 리스트 {change_list_number}에 파일이 {len(change_spec['Files'])}개 있어 삭제할 수 없습니다.")
                return False
            
            # 빈 체인지 리스트 삭제
            self.p4.run_change("-d", change_list_number)
            logger.info(f"빈 체인지 리스트 {change_list_number} 삭제 완료.")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 삭제")
            return False

    def revert_file(self, file_path: str, change_list_number: int) -> bool:
        """체인지 리스트에서 특정 파일을 되돌립니다.

        Args:
            file_path (str): 되돌릴 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 되돌리기 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
            
        logger.info(f"파일 '{file_path}'을 체인지 리스트 {change_list_number}에서 되돌리기 시도...")
        try:
            self.p4.run_revert("-c", change_list_number, file_path)
            logger.info(f"파일 '{file_path}'를 체인지 리스트 {change_list_number}에서 되돌리기 성공.")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일 '{file_path}'를 체인지 리스트 {change_list_number}에서 되돌리기")
            return False

    def revert_files(self, change_list_number: int, file_paths: list) -> bool:
        """체인지 리스트 내의 특정 파일들을 되돌립니다.

        Args:
            change_list_number (int): 체인지 리스트 번호
            file_paths (list): 되돌릴 파일 경로 리스트

        Returns:
            bool: 모든 파일 되돌리기 성공 시 True, 하나라도 실패 시 False
        """
        if not self._is_connected():
            return False
        if not file_paths:
            logger.warning("되돌릴 파일 목록이 비어있습니다.")
            return True
            
        logger.info(f"체인지 리스트 {change_list_number}에서 {len(file_paths)}개 파일 되돌리기 시도...")
        
        all_success = True
        for file_path in file_paths:
            success = self.revert_file(file_path, change_list_number)
            if not success:
                all_success = False
                logger.warning(f"파일 '{file_path}' 되돌리기 실패")
                
        if all_success:
            logger.info(f"모든 파일({len(file_paths)}개)을 체인지 리스트 {change_list_number}에서 성공적으로 되돌렸습니다.")
        else:
            logger.warning(f"일부 파일을 체인지 리스트 {change_list_number}에서 되돌리지 못했습니다.")
            
        return all_success

    def check_update_required(self, file_paths: list) -> bool:
        """파일이나 폴더의 업데이트 필요 여부를 확인합니다.

        Args:
            file_paths (list): 확인할 파일 또는 폴더 경로 리스트. 
                              폴더 경로는 자동으로 재귀적으로 처리됩니다.

        Returns:
            bool: 업데이트가 필요한 파일이 있으면 True, 없으면 False
        """
        if not self._is_connected():
            return False
        if not file_paths:
            logger.debug("업데이트 필요 여부 확인할 파일/폴더 목록이 비어있습니다.")
            return False
        
        # 폴더 경로에 재귀적 와일드카드 패턴을 추가
        processed_paths = []
        for path in file_paths:
            if os.path.isdir(path):
                # 폴더 경로에 '...'(재귀) 패턴을 추가
                processed_paths.append(os.path.join(path, '...'))
                logger.debug(f"폴더 경로를 재귀 패턴으로 변환: {path} -> {os.path.join(path, '...')}")
            else:
                processed_paths.append(path)
        
        logger.debug(f"파일/폴더 업데이트 필요 여부 확인 중 (항목 {len(processed_paths)}개): {processed_paths}")
        try:
            sync_preview_results = self.p4.run_sync("-n", processed_paths)
            needs_update = False
            for result in sync_preview_results:
                if isinstance(result, dict):
                    if 'up-to-date' not in result.get('how', '') and \
                       'no such file(s)' not in result.get('depotFile', ''):
                        if result.get('how') and 'syncing' in result.get('how'):
                            needs_update = True
                            logger.info(f"파일 '{result.get('clientFile', result.get('depotFile'))}' 업데이트 필요: {result.get('how')}")
                            break
                        elif result.get('action') and result.get('action') not in ['checked', 'exists']:
                            needs_update = True
                            logger.info(f"파일 '{result.get('clientFile', result.get('depotFile'))}' 업데이트 필요 (action: {result.get('action')})")
                            break
                elif isinstance(result, str):
                    if "up-to-date" not in result and "no such file(s)" not in result:
                        needs_update = True
                        logger.info(f"파일 업데이트 필요 (문자열 결과): {result}")
                        break
            
            if needs_update:
                logger.info(f"지정된 파일/폴더 중 업데이트가 필요한 파일이 있습니다.")
            else:
                logger.info(f"지정된 모든 파일/폴더가 최신 상태입니다.")
            return needs_update
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일/폴더 업데이트 필요 여부 확인 ({processed_paths})")
            return False

    def is_file_in_perforce(self, file_path: str) -> bool:
        """파일이 Perforce에 속하는지 확인합니다.

        Args:
            file_path (str): 확인할 파일 경로

        Returns:
            bool: 파일이 Perforce에 속하면 True, 아니면 False
        """
        if not self._is_connected():
            return False
            
        logger.debug(f"파일 '{file_path}'가 Perforce에 속하는지 확인 중...")
        try:
            # p4 files 명령으로 파일 정보 조회
            file_info = self.p4.run_files(file_path)
            
            # 파일 정보가 있고, 'no such file(s)' 오류가 없는 경우
            if file_info and not any("no such file(s)" in str(err).lower() for err in self.p4.errors):
                logger.info(f"파일 '{file_path}'가 Perforce에 존재합니다.")
                return True
            else:
                logger.info(f"파일 '{file_path}'가 Perforce에 존재하지 않습니다.")
                return False
                
        except P4Exception as e:
            # 파일이 존재하지 않는 경우는 일반적인 상황이므로 경고 레벨로 로깅
            if any("no such file(s)" in err.lower() for err in self.p4.errors):
                logger.info(f"파일 '{file_path}'가 Perforce에 존재하지 않습니다.")
                return False
            else:
                self._handle_p4_exception(e, f"파일 '{file_path}' Perforce 존재 여부 확인")
                return False

    def sync_files(self, file_paths: list) -> bool:
        """파일이나 폴더를 동기화합니다.

        Args:
            file_paths (list): 동기화할 파일 또는 폴더 경로 리스트.
                             폴더 경로는 자동으로 재귀적으로 처리됩니다.

        Returns:
            bool: 동기화 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
        if not file_paths:
            logger.debug("싱크할 파일/폴더 목록이 비어있습니다.")
            return True
        
        # 폴더 경로에 재귀적 와일드카드 패턴을 추가
        processed_paths = []
        for path in file_paths:
            if os.path.isdir(path):
                # 폴더 경로에 '...'(재귀) 패턴을 추가
                processed_paths.append(os.path.join(path, '...'))
                logger.debug(f"폴더 경로를 재귀 패턴으로 변환: {path} -> {os.path.join(path, '...')}")
            else:
                processed_paths.append(path)
        
        logger.info(f"파일/폴더 싱크 시도 (항목 {len(processed_paths)}개): {processed_paths}")
        try:
            self.p4.run_sync(processed_paths)
            logger.info(f"파일/폴더 싱크 완료: {processed_paths}")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일/폴더 싱크 ({processed_paths})")
            return False

    def disconnect(self):
        """Perforce 서버와의 연결을 해제합니다."""
        if self.connected:
            try:
                self.p4.disconnect()
                self.connected = False
                logger.info("Perforce 서버 연결 해제 완료.")
            except P4Exception as e:
                self._handle_p4_exception(e, "Perforce 서버 연결 해제")
        else:
            logger.debug("Perforce 서버에 이미 연결되지 않은 상태입니다.")

    def __del__(self):
        """객체가 소멸될 때 자동으로 연결을 해제합니다."""
        self.disconnect()

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
        if not self._is_connected():
            return {}
        if not file_paths:
            logger.debug("체크아웃 상태 확인할 파일 목록이 비어있습니다.")
            return {}
        
        logger.debug(f"파일 체크아웃 상태 확인 중 - 모든 사용자 (파일 {len(file_paths)}개)")
        
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
                        
                        logger.debug(f"파일 '{file_path}' 체크아웃됨: CL {file_status['change_list']}, "
                                   f"액션: {file_status['action']}, 사용자: {file_status['user']}, "
                                   f"클라이언트: {file_status['client']}")
                    else:
                        # 파일이 체크아웃되지 않음
                        logger.debug(f"파일 '{file_path}' 체크아웃되지 않음 (모든 사용자)")
                        
                except P4Exception as e:
                    # 파일이 perforce에 없거나 접근할 수 없는 경우
                    if any("not opened" in err.lower() or "no such file" in err.lower() 
                           for err in self.p4.errors):
                        logger.debug(f"파일 '{file_path}' 체크아웃되지 않음 (perforce에 없거나 접근 불가)")
                    else:
                        self._handle_p4_exception(e, f"파일 '{file_path}' 체크아웃 상태 확인 (모든 사용자)")
                
                result[file_path] = file_status
            
            checked_out_count = sum(1 for status in result.values() if status['is_checked_out'])
            logger.info(f"파일 체크아웃 상태 확인 완료 (모든 사용자): 전체 {len(file_paths)}개 중 {checked_out_count}개 체크아웃됨")
            
            return result
            
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일들 체크아웃 상태 확인 - 모든 사용자 ({file_paths})")
            return {}

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
        
        logger.info(f"다른 사용자에 의해 체크아웃된 파일: {len(files_by_others)}개")
        return files_by_others
