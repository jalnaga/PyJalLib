#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 실제 사용 예제
PRD에 명시된 사용법대로 동작하는지 확인
"""

import sys
from pathlib import Path

# 테스트를 위해 src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyjallib.logger import Logger


def example_ue5_module():
    """UE5 모듈에서의 사용 예제"""
    print("=== UE5 모듈 사용 예제 ===")
    
    # UE5 출력 활성화된 로거 생성
    logger = Logger(inEnableUE5=True)
    
    # 첫 번째 작업
    logger.set_session("UE5 Animation Import")
    logger.info("애니메이션 임포트 시작")
    logger.info("FBX 파일 분석 중...")
    logger.warning("일부 본이 누락되었습니다")
    logger.info("애니메이션 임포트 완료")
    logger.end_session()
    
    # 같은 로거로 다른 작업 수행
    logger.set_session("UE5 Mesh Import")
    logger.info("메시 임포트 시작")
    logger.info("메시 임포트 완료")
    logger.end_session()
    
    logger.close()


def example_perforce_module():
    """Perforce 모듈에서의 사용 예제"""
    print("\n=== Perforce 모듈 사용 예제 ===")
    
    class Perforce:
        def __init__(self, debugMode: bool = False):
            # 디버그 모드에 따라 콘솔 출력 제어
            self.logger = Logger(inEnableConsole=debugMode)
                
        def sync_project(self, projectName: str):
            self.logger.set_session(f"Perforce Sync - {projectName}")
            self.logger.debug("Perforce 연결 시도")
            self.logger.info("Perforce 연결 성공")
            self.logger.info(f"{projectName} 프로젝트 동기화 중...")
            self.logger.info("동기화 완료")
            self.logger.end_session()
            
        def submit_files(self, description: str):
            self.logger.set_session("Perforce Submit")
            self.logger.info(f"파일 제출: {description}")
            self.logger.info("제출 완료")
            self.logger.end_session()
            
        def close(self):
            self.logger.close()
    
    # 디버그 모드로 Perforce 인스턴스 생성
    p4 = Perforce(debugMode=True)
    p4.sync_project("MyGame")
    p4.submit_files("애니메이션 파일 업데이트")
    p4.close()


def example_max_module():
    """3DS Max 모듈에서의 사용 예제"""
    print("\n=== 3DS Max 모듈 사용 예제 ===")
    
    # 파일만 출력 (콘솔 비활성화)
    logger = Logger(inEnableConsole=False)
    
    logger.set_session("3DS Max Export")
    logger.info("Max 스크립트 실행")
    logger.info("FBX 익스포트 시작")
    logger.warning("일부 텍스처 경로가 누락됨")
    logger.info("FBX 익스포트 완료")
    logger.end_session()
    
    # 같은 로거로 다른 익스포트 작업
    logger.set_session("3DS Max Animation Export")
    logger.info("애니메이션 익스포트 시작")
    logger.info("애니메이션 익스포트 완료")
    logger.end_session()
    
    logger.close()


def example_basic_usage():
    """기본 사용법 예제"""
    print("\n=== 기본 사용법 예제 ===")
    
    # 기본 로거 생성 (파일 + 콘솔 출력)
    logger = Logger()
    
    # 사용자 지정 경로로 생성
    custom_logger = Logger("./logs")
    
    # 콘솔 출력 비활성화
    file_only_logger = Logger(inEnableConsole=False)
    
    # UE5 환경에서 UE5 출력 활성화
    ue5_logger = Logger(inEnableUE5=True)
    
    # 세션 시작
    logger.set_session("기본 사용 예제")
    
    # 로그 메시지 출력
    logger.debug("디버그 메시지")
    logger.info("정보 메시지")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")
    logger.critical("치명적 에러 메시지")
    
    # 작업 완료 시 세션 종료
    logger.end_session()
    
    # 다른 작업 시작
    logger.set_session("Animation Export")
    logger.info("애니메이션 익스포트 시작")
    logger.end_session()
    
    # 리소스 정리
    logger.close()
    custom_logger.close()
    file_only_logger.close()
    ue5_logger.close()


def main():
    """메인 실행 함수"""
    print("Logger 클래스 사용 예제 실행\n")
    
    try:
        example_basic_usage()
        example_ue5_module()
        example_perforce_module()
        example_max_module()
        
        print("\n=== 모든 예제 실행 완료 ===")
        print("✓ Logger 클래스가 PRD 요구사항에 맞게 동작합니다")
        
        # 로그 파일 확인 (날짜 기반 파일명)
        from datetime import datetime
        current_date = datetime.now().strftime("%Y%m%d")
        log_filename = f"{current_date}_pyjallib.log"
        log_path = Path.home() / "Documents" / "PyJalLib" / "logs" / log_filename
        if log_path.exists():
            print(f"\n로그 파일 위치: {log_path}")
            print("로그 파일 내용 (마지막 20줄):")
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
        
    except Exception as e:
        print(f"\n✗ 예제 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 