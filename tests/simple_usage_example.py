#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 간단한 사용법 예제
패키지 레벨 import를 사용한 실제 사용 시나리오
"""

import sys
from pathlib import Path

# 테스트를 위해 src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 🎯 패키지 레벨에서 직접 import!
from pyjallib import Logger


def main():
    """간단한 사용법 예제"""
    print("=== PyJalLib Logger 간단한 사용법 ===\n")
    
    # 1. 가장 간단한 사용법
    print("1. 기본 사용법:")
    logger = Logger()
    logger.set_session("Hello PyJalLib")
    logger.info("PyJalLib Logger가 정상적으로 동작합니다!")
    logger.end_session()
    logger.close()
    
    # 2. 모듈별 로그 파일
    print("\n2. 모듈별 로그 파일:")
    
    # UE5 모듈 시뮬레이션
    ue5_logger = Logger(inLogFileName="ue5_tools", inEnableUE5=True)
    ue5_logger.set_session("UE5 Tools")
    ue5_logger.info("UE5 도구 실행 중...")
    ue5_logger.end_session()
    ue5_logger.close()
    
    # Perforce 모듈 시뮬레이션
    p4_logger = Logger(inLogFileName="perforce_tools", inEnableConsole=False)
    p4_logger.set_session("Perforce Tools")
    p4_logger.info("Perforce 작업 실행 중...")
    p4_logger.end_session()
    p4_logger.close()
    
    print("\n✅ 완료!")
    print("📁 로그 파일들이 다음 위치에 생성되었습니다:")
    print("   Documents/PyJalLib/logs/")
    print("   - 20250702_pyjallib.log")
    print("   - 20250702_ue5_tools.log")
    print("   - 20250702_perforce_tools.log")
    
    print("\n💡 사용법:")
    print("   from pyjallib import Logger")
    print("   logger = Logger(inLogFileName='my_module')")
    print("   logger.set_session('작업명')")
    print("   logger.info('메시지')")
    print("   logger.end_session()")


if __name__ == "__main__":
    main() 