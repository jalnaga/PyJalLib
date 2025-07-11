#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
변경된 PyJalLib Perforce 모듈 사용 예제
예외 처리 방식으로 전환된 후의 사용 패턴을 보여줍니다.
"""

from pyjallib.logger import Logger
from pyjallib.perforce import Perforce
from pyjallib.exceptions import PerforceError, ValidationError


def main():
    """메인 함수 - Perforce 작업 예제"""
    
    # 로거 초기화
    logger = Logger(inLogFileName="perforce_example")
    logger.set_session("Perforce 작업 예제")
    
    try:
        # Perforce 인스턴스 생성
        p4 = Perforce()
        
        # 워크스페이스 연결
        logger.info("워크스페이스 연결 시도...")
        p4.connect("my_workspace")
        logger.info("워크스페이스 연결 성공")
        
        # 체인지리스트 생성
        logger.info("새 체인지리스트 생성...")
        change_list = p4.create_change_list("예제 작업용 체인지리스트")
        change_number = int(change_list['Change'])
        logger.info(f"체인지리스트 생성 성공: {change_number}")
        
        # 파일 체크아웃
        test_file = "test_file.txt"
        logger.info(f"파일 체크아웃: {test_file}")
        p4.checkout_file(test_file, change_number)
        logger.info("파일 체크아웃 성공")
        
        # 여러 파일 체크아웃
        test_files = ["file1.txt", "file2.txt", "file3.txt"]
        logger.info(f"여러 파일 체크아웃: {test_files}")
        p4.checkout_files(test_files, change_number)
        logger.info("여러 파일 체크아웃 성공")
        
        # Pending 체인지리스트 조회
        logger.info("Pending 체인지리스트 조회...")
        pending_lists = p4.get_pending_change_list()
        logger.info(f"Pending 체인지리스트 {len(pending_lists)}개 발견")
        
        logger.info("모든 작업 완료")
        
    except ValidationError as e:
        # 입력값 검증 실패
        logger.log_pyjallib_error(e, "입력값 검증 실패")
        
    except PerforceError as e:
        # Perforce 작업 실패
        logger.log_pyjallib_error(e, "Perforce 작업 실패")
        
    except Exception as e:
        # 예상치 못한 에러
        logger.log_exception(e, "예상치 못한 에러 발생")
        
    finally:
        # 세션 종료
        logger.end_session()
        logger.close()


def example_error_handling():
    """에러 처리 예제"""
    
    logger = Logger(inLogFileName="error_example")
    logger.set_session("에러 처리 예제")
    
    try:
        p4 = Perforce()
        
        # 잘못된 워크스페이스 이름으로 연결 시도
        p4.connect("")  # ValidationError 발생
        
    except ValidationError as e:
        # 함수명이 자동으로 포함된 에러 메시지 로깅
        logger.error(f"입력값 오류: {e}")
        
    try:
        p4 = Perforce()
        
        # 잘못된 체인지리스트 번호로 조회 시도
        p4.get_change_list_by_number(-1)  # ValidationError 발생
        
    except ValidationError as e:
        # 커스텀 메시지와 함께 로깅
        logger.log_pyjallib_error(e, "체인지리스트 조회 실패")
        
    logger.end_session()
    logger.close()


if __name__ == "__main__":
    print("=== 기본 사용 예제 ===")
    main()
    
    print("\n=== 에러 처리 예제 ===")
    example_error_handling()
    
    print("\n예제 실행 완료. 로그 파일을 확인하세요.") 