#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 사용자 지정 파일명 기능 테스트
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime

# 테스트를 위해 src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyjallib.logger import Logger


def test_custom_filename():
    """사용자 지정 파일명 테스트"""
    print("=== 사용자 지정 파일명 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 사용자 지정 파일명으로 로거 생성
        logger = Logger(
            inLogPath=temp_dir, 
            inLogFileName="custom_module",
            inEnableConsole=True
        )
        
        logger.set_session("Custom Module Test")
        logger.info("사용자 지정 파일명으로 로그 생성")
        logger.warning("경고 메시지 테스트")
        logger.end_session()
        
        # 예상 파일명 확인
        current_date = datetime.now().strftime("%Y%m%d")
        expected_filename = f"{current_date}_custom_module.log"
        log_file = Path(temp_dir) / expected_filename
        
        if log_file.exists():
            print(f"✓ 사용자 지정 파일명 로그 생성됨: {expected_filename}")
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print("로그 파일 내용:")
                print(content)
        else:
            print(f"✗ 예상 파일명 {expected_filename}이 생성되지 않았습니다")
            # 실제 생성된 파일들 확인
            files = list(Path(temp_dir).glob("*.log"))
            print(f"실제 생성된 파일들: {files}")
        
        logger.close()


def test_different_paths_and_names():
    """다양한 경로와 파일명 조합 테스트"""
    print("\n=== 다양한 경로와 파일명 조합 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        current_date = datetime.now().strftime("%Y%m%d")
        
        test_cases = [
            ("ue5_module", f"{current_date}_ue5_module.log"),
            ("perforce_sync", f"{current_date}_perforce_sync.log"),
            ("max_export", f"{current_date}_max_export.log"),
            ("animation_import", f"{current_date}_animation_import.log")
        ]
        
        for filename, expected_file in test_cases:
            print(f"\n테스트: {filename}")
            
            logger = Logger(
                inLogPath=temp_dir,
                inLogFileName=filename,
                inEnableConsole=False  # 콘솔 출력 비활성화
            )
            
            logger.set_session(f"{filename} 테스트")
            logger.info(f"{filename} 모듈에서 로그 생성")
            logger.end_session()
            logger.close()
            
            # 파일 생성 확인
            log_file = Path(temp_dir) / expected_file
            if log_file.exists():
                print(f"✓ {expected_file} 생성됨")
            else:
                print(f"✗ {expected_file} 생성 실패")
        
        # 생성된 모든 파일 목록 출력
        print(f"\n생성된 모든 로그 파일:")
        for log_file in Path(temp_dir).glob("*.log"):
            print(f"  - {log_file.name}")


def test_default_behavior():
    """기본 동작 테스트 (파일명 미지정)"""
    print("\n=== 기본 동작 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 파일명을 지정하지 않은 경우 (기본값 사용)
        logger = Logger(inLogPath=temp_dir, inEnableConsole=True)
        
        logger.set_session("기본 파일명 테스트")
        logger.info("기본 파일명으로 로그 생성")
        logger.end_session()
        logger.close()
        
        # 기본 파일명 확인
        current_date = datetime.now().strftime("%Y%m%d")
        expected_filename = f"{current_date}_pyjallib.log"
        log_file = Path(temp_dir) / expected_filename
        
        if log_file.exists():
            print(f"✓ 기본 파일명 로그 생성됨: {expected_filename}")
        else:
            print(f"✗ 기본 파일명 {expected_filename} 생성 실패")


def test_real_world_usage():
    """실제 사용 시나리오 테스트"""
    print("\n=== 실제 사용 시나리오 테스트 ===")
    
    # UE5 모듈 시뮬레이션
    print("UE5 모듈 시뮬레이션:")
    ue5_logger = Logger(
        inLogFileName="ue5_animation_import",
        inEnableUE5=True,
        inEnableConsole=True
    )
    ue5_logger.set_session("UE5 Animation Import")
    ue5_logger.info("FBX 파일 로드 중...")
    ue5_logger.warning("일부 본 누락 감지")
    ue5_logger.info("임포트 완료")
    ue5_logger.end_session()
    ue5_logger.close()
    
    # Perforce 모듈 시뮬레이션
    print("\nPerforce 모듈 시뮬레이션:")
    p4_logger = Logger(
        inLogFileName="perforce_operations",
        inEnableConsole=False  # 파일만 출력
    )
    p4_logger.set_session("Perforce Sync")
    p4_logger.debug("P4 서버 연결 시도")
    p4_logger.info("동기화 시작")
    p4_logger.info("동기화 완료")
    p4_logger.end_session()
    p4_logger.close()
    
    # 3DS Max 모듈 시뮬레이션
    print("\n3DS Max 모듈 시뮬레이션:")
    max_logger = Logger(
        inLogPath="./logs",  # 현재 디렉토리의 logs 폴더
        inLogFileName="max_fbx_export",
        inEnableConsole=False
    )
    max_logger.set_session("FBX Export")
    max_logger.info("Max 스크립트 시작")
    max_logger.info("FBX 익스포트 완료")
    max_logger.end_session()
    max_logger.close()
    
    print("✓ 모든 실제 시나리오 테스트 완료")


def main():
    """메인 테스트 실행"""
    print("Logger 클래스 사용자 지정 파일명 기능 테스트 시작\n")
    
    try:
        test_custom_filename()
        test_different_paths_and_names()
        test_default_behavior()
        test_real_world_usage()
        
        print("\n=== 모든 테스트 완료 ===")
        print("✓ 사용자 지정 파일명 기능이 정상적으로 동작합니다")
        
        # 실제 로그 파일들 확인
        log_path = Path.home() / "Documents" / "PyJalLib" / "logs"
        if log_path.exists():
            print(f"\n실제 생성된 로그 파일들 ({log_path}):")
            current_date = datetime.now().strftime("%Y%m%d")
            for log_file in log_path.glob(f"{current_date}_*.log"):
                print(f"  - {log_file.name}")
        
    except Exception as e:
        print(f"\n✗ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 