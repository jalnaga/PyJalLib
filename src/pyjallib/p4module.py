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
logger.setLevel(logging.DEBUG)
# 사용자 문서 폴더 내 로그 파일 저장
log_path = os.path.join(Path.home() / "Documents", 'p4module.log')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class P4Module:
    """P4Python을 사용하여 Perforce 작업을 수행하는 클래스."""

    def __init__(self):
        """P4Module 인스턴스를 초기화합니다."""
        self.p4 = P4()
        self.connected = False
        logger.info("P4Module 인스턴스 생성됨")

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

    def add_file(self, file_path: str, change_list_number: int) -> bool:
        """파일을 추가합니다.

        Args:
            file_path (str): 추가할 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 추가 성공 시 True, 실패 시 False
        """
        return self._file_op("add", file_path, change_list_number, "추가")

    def delete_file(self, file_path: str, change_list_number: int) -> bool:
        """파일을 삭제합니다.

        Args:
            file_path (str): 삭제할 파일 경로
            change_list_number (int): 체인지 리스트 번호

        Returns:
            bool: 삭제 성공 시 True, 실패 시 False
        """
        return self._file_op("delete", file_path, change_list_number, "삭제")

    def submit_change_list(self, change_list_number: int) -> bool:
        """체인지 리스트를 제출합니다.

        Args:
            change_list_number (int): 제출할 체인지 리스트 번호

        Returns:
            bool: 제출 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
        logger.info(f"체인지 리스트 {change_list_number} 제출 시도...")
        try:
            self.p4.run_submit("-c", change_list_number)
            logger.info(f"체인지 리스트 {change_list_number} 제출 성공.")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number} 제출")
            if any("nothing to submit" in err.lower() for err in self.p4.errors):
                logger.warning(f"체인지 리스트 {change_list_number}에 제출할 파일이 없습니다.")
            return False

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

    def revert_files(self, change_list_number: int, file_paths: list) -> bool:
        """체인지 리스트 내의 특정 파일들을 되돌립니다.

        Args:
            change_list_number (int): 체인지 리스트 번호
            file_paths (list): 되돌릴 파일 경로 리스트

        Returns:
            bool: 되돌리기 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
        if not file_paths:
            logger.warning("되돌릴 파일 목록이 비어있습니다.")
            return True
            
        logger.info(f"체인지 리스트 {change_list_number}에서 {len(file_paths)}개 파일 되돌리기 시도...")
        try:
            for file_path in file_paths:
                self.p4.run_revert("-c", change_list_number, file_path)
                logger.info(f"파일 '{file_path}'를 체인지 리스트 {change_list_number}에서 되돌리기 성공.")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"체인지 리스트 {change_list_number}에서 파일 되돌리기")
            return False

    def check_update_required(self, file_paths: list) -> bool:
        """파일들의 업데이트 필요 여부를 확인합니다.

        Args:
            file_paths (list): 확인할 파일 경로 리스트

        Returns:
            bool: 업데이트가 필요한 파일이 있으면 True, 없으면 False
        """
        if not self._is_connected():
            return False
        if not file_paths:
            logger.debug("업데이트 필요 여부 확인할 파일 목록이 비어있습니다.")
            return False
        logger.debug(f"파일 업데이트 필요 여부 확인 중 (파일 {len(file_paths)}개): {file_paths}")
        try:
            sync_preview_results = self.p4.run_sync("-n", file_paths)
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
                logger.info(f"지정된 파일 중 업데이트가 필요한 파일이 있습니다.")
            else:
                logger.info(f"지정된 모든 파일이 최신 상태입니다.")
            return needs_update
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일 업데이트 필요 여부 확인 ({file_paths})")
            return False

    def sync_files(self, file_paths: list) -> bool:
        """파일들을 동기화합니다.

        Args:
            file_paths (list): 동기화할 파일 경로 리스트

        Returns:
            bool: 동기화 성공 시 True, 실패 시 False
        """
        if not self._is_connected():
            return False
        if not file_paths:
            logger.debug("싱크할 파일 목록이 비어있습니다.")
            return True
        logger.info(f"파일 싱크 시도 (파일 {len(file_paths)}개): {file_paths}")
        try:
            self.p4.run_sync(file_paths)
            logger.info(f"파일 싱크 완료: {file_paths}")
            return True
        except P4Exception as e:
            self._handle_p4_exception(e, f"파일 싱크 ({file_paths})")
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
