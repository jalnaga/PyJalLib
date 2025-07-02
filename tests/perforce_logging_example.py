#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Perforce 클래스와 PyJalLib Logger를 함께 사용하는 예제

이 예제는 Perforce 클래스에서 발생하는 에러와 경고 정보를 
PyJalLib의 Logger를 통해 로깅하는 방법을 보여줍니다.
"""

import sys
import os
from pathlib import Path

# PyJalLib 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyjallib.perforce import Perforce
from pyjallib.logger import Logger


class PerforceWithLogging:
    """로깅 기능이 포함된 Perforce 래퍼 클래스"""
    
    def __init__(self, inLogFileName: str = "perforce_operations"):
        """
        Args:
            inLogFileName (str): 로그 파일명 (확장자 제외)
        """
        self.p4 = Perforce()
        self.logger = Logger(inLogFileName=inLogFileName, inEnableConsole=True)
        self.logger.info("Perforce 로깅 래퍼 초기화 완료")
        
    def connect(self, workspace_name: str) -> bool:
        """워크스페이스에 연결하고 결과를 로깅합니다."""
        self.logger.info(f"'{workspace_name}' 워크스페이스 연결 시도 중...")
        
        success = self.p4.connect(workspace_name)
        
        if success:
            self.logger.info(f"'{workspace_name}' 워크스페이스 연결 성공")
            self.logger.info(f"워크스페이스 루트: {self.p4.workspaceRoot}")
        else:
            error_msg = self.p4.get_last_error()
            warnings = self.p4.get_last_warnings()
            
            self.logger.error(f"워크스페이스 연결 실패: {error_msg}")
            for warning in warnings:
                self.logger.warning(f"경고: {warning}")
                
        return success
    
    def create_change_list(self, description: str) -> dict:
        """체인지 리스트를 생성하고 결과를 로깅합니다."""
        self.logger.info(f"체인지 리스트 생성 시도: '{description}'")
        
        result = self.p4.create_change_list(description)
        
        if result:
            change_number = result.get('Change', 'Unknown')
            self.logger.info(f"체인지 리스트 {change_number} 생성 성공: '{description}'")
        else:
            error_msg = self.p4.get_last_error()
            warnings = self.p4.get_last_warnings()
            
            self.logger.error(f"체인지 리스트 생성 실패: {error_msg}")
            for warning in warnings:
                self.logger.warning(f"경고: {warning}")
                
        return result
    
    def checkout_files(self, file_paths: list, change_list_number: int) -> bool:
        """파일들을 체크아웃하고 결과를 로깅합니다."""
        self.logger.info(f"파일 체크아웃 시도: {len(file_paths)}개 파일, CL {change_list_number}")
        self.logger.debug(f"체크아웃 대상 파일들: {file_paths}")
        
        success = self.p4.checkout_files(file_paths, change_list_number)
        
        if success:
            self.logger.info(f"모든 파일({len(file_paths)}개) 체크아웃 성공")
        else:
            error_msg = self.p4.get_last_error()
            warnings = self.p4.get_last_warnings()
            
            self.logger.error(f"파일 체크아웃 실패: {error_msg}")
            for warning in warnings:
                self.logger.warning(f"경고: {warning}")
                
        return success
    
    def submit_change_list(self, change_list_number: int) -> bool:
        """체인지 리스트를 제출하고 결과를 로깅합니다."""
        self.logger.info(f"체인지 리스트 {change_list_number} 제출 시도...")
        
        success = self.p4.submit_change_list(change_list_number)
        
        if success:
            self.logger.info(f"체인지 리스트 {change_list_number} 제출 성공")
        else:
            error_msg = self.p4.get_last_error()
            warnings = self.p4.get_last_warnings()
            
            self.logger.error(f"체인지 리스트 제출 실패: {error_msg}")
            for warning in warnings:
                self.logger.warning(f"경고: {warning}")
                
        return success
    
    def check_files_status(self, file_paths: list) -> dict:
        """파일들의 체크아웃 상태를 확인하고 결과를 로깅합니다."""
        self.logger.info(f"파일 상태 확인 시도: {len(file_paths)}개 파일")
        
        result = self.p4.check_files_checked_out(file_paths)
        
        if result:
            checked_out_count = sum(1 for status in result.values() if status.get('is_checked_out', False))
            self.logger.info(f"파일 상태 확인 완료: 전체 {len(file_paths)}개 중 {checked_out_count}개 체크아웃됨")
            
            # 체크아웃된 파일들 상세 로깅
            for file_path, status in result.items():
                if status.get('is_checked_out', False):
                    self.logger.debug(f"체크아웃됨: {file_path} (CL: {status.get('change_list')}, 사용자: {status.get('user')})")
        else:
            error_msg = self.p4.get_last_error()
            warnings = self.p4.get_last_warnings()
            
            self.logger.error(f"파일 상태 확인 실패: {error_msg}")
            for warning in warnings:
                self.logger.warning(f"경고: {warning}")
                
        return result
    
    def close(self):
        """리소스 정리"""
        self.logger.info("Perforce 연결 종료 및 로깅 세션 종료")
        self.p4.disconnect()
        self.logger.close()


def main():
    """메인 실행 함수 - 사용 예제"""
    
    # Perforce 로깅 래퍼 생성
    p4_logger = PerforceWithLogging("perforce_example")
    
    try:
        # 로깅 세션 시작
        p4_logger.logger.set_session("Perforce 작업 예제")
        
        # 1. 워크스페이스 연결 시도
        workspace_name = "my_workspace"
        if not p4_logger.connect(workspace_name):
            p4_logger.logger.critical("워크스페이스 연결 실패로 인해 작업을 중단합니다.")
            return
        
        # 2. 체인지 리스트 생성
        description = "테스트용 체인지 리스트"
        change_list = p4_logger.create_change_list(description)
        
        if change_list:
            change_number = int(change_list.get('Change', 0))
            
            # 3. 파일 체크아웃 시도
            test_files = [
                "//depot/project/test1.txt",
                "//depot/project/test2.txt"
            ]
            
            p4_logger.checkout_files(test_files, change_number)
            
            # 4. 파일 상태 확인
            p4_logger.check_files_status(test_files)
            
            # 5. 체인지 리스트 제출 (실제로는 파일이 없어서 실패할 가능성 높음)
            p4_logger.submit_change_list(change_number)
        
    except Exception as e:
        p4_logger.logger.critical(f"예상치 못한 오류 발생: {e}")
        
    finally:
        # 로깅 세션 종료 및 리소스 정리
        p4_logger.logger.end_session()
        p4_logger.close()


def demonstrate_error_handling():
    """에러 처리 시연을 위한 함수"""
    
    p4_logger = PerforceWithLogging("perforce_error_demo")
    
    try:
        p4_logger.logger.set_session("에러 처리 시연")
        
        # 존재하지 않는 워크스페이스에 연결 시도 (의도적 실패)
        p4_logger.logger.info("의도적으로 잘못된 워크스페이스에 연결을 시도합니다...")
        invalid_workspace = "nonexistent_workspace_12345"
        p4_logger.connect(invalid_workspace)
        
        # 연결되지 않은 상태에서 작업 시도 (의도적 실패)
        p4_logger.logger.info("연결되지 않은 상태에서 체인지 리스트 생성을 시도합니다...")
        p4_logger.create_change_list("실패할 체인지 리스트")
        
        # 잘못된 타입으로 메서드 호출 (의도적 실패)
        p4_logger.logger.info("잘못된 타입으로 파일 체크아웃을 시도합니다...")
        try:
            p4_logger.p4.checkout_files("단일_파일_경로", 123)  # 리스트가 아닌 문자열 전달
        except TypeError as e:
            p4_logger.logger.error(f"타입 에러 발생: {e}")
            
    finally:
        p4_logger.logger.end_session()
        p4_logger.close()


if __name__ == "__main__":
    print("=== Perforce 로깅 예제 실행 ===")
    print("1. 기본 사용 예제")
    main()
    
    print("\n" + "="*50)
    print("2. 에러 처리 시연")
    demonstrate_error_handling()
    
    print("\n로그 파일은 Documents/PyJalLib/logs/ 폴더에 저장됩니다.") 