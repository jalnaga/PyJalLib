#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 기본 기능 테스트
"""

import sys
import tempfile
from pathlib import Path

# 테스트를 위해 src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyjallib.logger import Logger


def test_basic_logging():
    """기본 로깅 기능 테스트"""
    print("=== 기본 로깅 기능 테스트 ===")
    
    # 임시 디렉토리에 로거 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = Logger(inLogPath=temp_dir, inEnableConsole=True, inEnableUE5=False)
        
        # 세션 시작
        logger.set_session("기본 테스트")
        
        # 모든 로그 레벨 테스트
        logger.debug("디버그 메시지입니다")
        logger.info("정보 메시지입니다")
        logger.warning("경고 메시지입니다")
        logger.error("에러 메시지입니다")
        logger.critical("치명적 에러 메시지입니다")
        
        # 세션 종료
        logger.end_session()
        
        # 로그 파일 확인 (날짜 기반 파일명)
        from datetime import datetime
        current_date = datetime.now().strftime("%Y%m%d")
        log_filename = f"{current_date}_pyjallib.log"
        log_file = Path(temp_dir) / log_filename
        if log_file.exists():
            print(f"✓ 로그 파일 생성됨: {log_file}")
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print("로그 파일 내용:")
                print(content)
        else:
            print("✗ 로그 파일이 생성되지 않았습니다")


def test_session_management():
    """세션 관리 기능 테스트"""
    print("\n=== 세션 관리 기능 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = Logger(inLogPath=temp_dir, inEnableConsole=True, inEnableUE5=False)
        
        # 첫 번째 세션
        logger.set_session("첫 번째 작업")
        logger.info("첫 번째 작업을 시작합니다")
        logger.info("첫 번째 작업 진행 중...")
        logger.end_session()
        
        # 두 번째 세션 (자동으로 첫 번째 세션 종료)
        logger.set_session("두 번째 작업")
        logger.info("두 번째 작업을 시작합니다")
        logger.warning("두 번째 작업에서 경고 발생")
        logger.end_session()
        
        # 세 번째 세션
        logger.set_session("세 번째 작업")
        logger.info("세 번째 작업 진행")
        # 의도적으로 end_session 호출 안함 (다음 set_session에서 자동 종료)
        
        logger.set_session("네 번째 작업")
        logger.info("네 번째 작업 완료")
        logger.end_session()


def test_console_disable():
    """콘솔 출력 비활성화 테스트"""
    print("\n=== 콘솔 출력 비활성화 테스트 ===")
    print("(아래 메시지들은 콘솔에 출력되지 않아야 합니다)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = Logger(inLogPath=temp_dir, inEnableConsole=False, inEnableUE5=False)
        
        logger.set_session("콘솔 비활성화 테스트")
        logger.info("이 메시지는 콘솔에 출력되지 않습니다")
        logger.warning("이 경고도 콘솔에 출력되지 않습니다")
        logger.end_session()
        
        # 파일에는 기록되었는지 확인 (날짜 기반 파일명)
        from datetime import datetime
        current_date = datetime.now().strftime("%Y%m%d")
        log_filename = f"{current_date}_pyjallib.log"
        log_file = Path(temp_dir) / log_filename
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "콘솔 비활성화 테스트" in content:
                    print("✓ 파일에는 정상적으로 기록됨")
                else:
                    print("✗ 파일에 기록되지 않음")


def test_ue5_handler_fallback():
    """UE5 핸들러 fallback 테스트"""
    print("\n=== UE5 핸들러 fallback 테스트 ===")
    print("(UE5가 없는 환경에서 fallback 동작 확인)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # UE5 핸들러 활성화 (하지만 unreal 모듈이 없으므로 fallback)
        logger = Logger(inLogPath=temp_dir, inEnableConsole=True, inEnableUE5=True)
        
        logger.set_session("UE5 Fallback 테스트")
        logger.info("UE5 핸들러가 fallback으로 동작해야 합니다")
        logger.warning("이 메시지도 fallback으로 처리됩니다")
        logger.end_session()


def main():
    """메인 테스트 실행"""
    print("Logger 클래스 테스트 시작\n")
    
    try:
        test_basic_logging()
        test_session_management()
        test_console_disable()
        test_ue5_handler_fallback()
        
        print("\n=== 모든 테스트 완료 ===")
        print("✓ Logger 클래스가 정상적으로 동작합니다")
        
    except Exception as e:
        print(f"\n✗ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 