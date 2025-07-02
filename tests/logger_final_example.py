#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 최종 사용법 예제
사용자 지정 파일명 기능을 포함한 완전한 사용법 시연
"""

import sys
from pathlib import Path

# 테스트를 위해 src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyjallib.logger import Logger


def main():
    """최종 사용법 예제"""
    print("=== Logger 클래스 최종 사용법 예제 ===\n")
    
    # 1. 기본 사용법 (기본 파일명)
    print("1. 기본 사용법:")
    basic_logger = Logger()
    basic_logger.set_session("기본 사용법 테스트")
    basic_logger.info("기본 파일명으로 로그 생성: 20250702_pyjallib.log")
    basic_logger.end_session()
    basic_logger.close()
    
    # 2. 사용자 지정 파일명
    print("\n2. 사용자 지정 파일명:")
    custom_logger = Logger(inLogFileName="my_custom_module")
    custom_logger.set_session("사용자 지정 파일명 테스트")
    custom_logger.info("사용자 지정 파일명으로 로그 생성: 20250702_my_custom_module.log")
    custom_logger.end_session()
    custom_logger.close()
    
    # 3. 사용자 지정 경로 + 파일명
    print("\n3. 사용자 지정 경로와 파일명:")
    path_logger = Logger(
        inLogPath="./logs",
        inLogFileName="project_specific"
    )
    path_logger.set_session("경로와 파일명 지정 테스트")
    path_logger.info("지정된 경로에 사용자 파일명으로 로그 생성")
    path_logger.end_session()
    path_logger.close()
    
    # 4. UE5 모듈 시뮬레이션
    print("\n4. UE5 모듈 시뮬레이션:")
    ue5_logger = Logger(
        inLogFileName="ue5_mesh_import",
        inEnableUE5=True,
        inEnableConsole=True
    )
    ue5_logger.set_session("UE5 Mesh Import")
    ue5_logger.info("UE5에서 메시 임포트 시작")
    ue5_logger.warning("일부 머티리얼 누락")
    ue5_logger.info("임포트 완료")
    ue5_logger.end_session()
    ue5_logger.close()
    
    # 5. Perforce 모듈 시뮬레이션
    print("\n5. Perforce 모듈 시뮬레이션:")
    p4_logger = Logger(
        inLogFileName="perforce_daily_sync",
        inEnableConsole=False  # 파일만 출력
    )
    p4_logger.set_session("Daily Sync")
    p4_logger.debug("P4 연결 확인")
    p4_logger.info("일일 동기화 시작")
    p4_logger.info("동기화 완료 - 42개 파일 업데이트")
    p4_logger.end_session()
    p4_logger.close()
    
    # 6. 여러 세션을 하나의 로거로 처리
    print("\n6. 여러 세션을 하나의 로거로 처리:")
    multi_logger = Logger(inLogFileName="batch_processing")
    
    # 첫 번째 작업
    multi_logger.set_session("데이터 준비")
    multi_logger.info("데이터 파일 로드")
    multi_logger.info("데이터 검증 완료")
    multi_logger.end_session()
    
    # 두 번째 작업 (자동으로 이전 세션 종료)
    multi_logger.set_session("데이터 처리")
    multi_logger.info("데이터 변환 시작")
    multi_logger.warning("일부 데이터 누락 감지")
    multi_logger.info("데이터 처리 완료")
    multi_logger.end_session()
    
    # 세 번째 작업
    multi_logger.set_session("결과 저장")
    multi_logger.info("결과 파일 생성")
    multi_logger.info("모든 작업 완료")
    multi_logger.end_session()
    multi_logger.close()
    
    print("\n=== 생성된 로그 파일들 확인 ===")
    
    # 생성된 로그 파일들 확인
    from datetime import datetime
    current_date = datetime.now().strftime("%Y%m%d")
    
    log_paths = [
        Path.home() / "Documents" / "PyJalLib" / "logs",
        Path("./logs")
    ]
    
    for log_path in log_paths:
        if log_path.exists():
            print(f"\n📁 {log_path}:")
            for log_file in log_path.glob(f"{current_date}_*.log"):
                print(f"  📄 {log_file.name} ({log_file.stat().st_size} bytes)")
    
    print("\n✅ 모든 예제 완료!")
    print("💡 각 모듈별로 고유한 파일명을 사용하여 로그를 분리 관리할 수 있습니다.")


if __name__ == "__main__":
    main() 