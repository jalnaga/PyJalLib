"""
P4 Python 직접 사용 테스트

순수 P4 Python API만 사용하여 체인지리스트 생성을 테스트합니다.
워크스페이스 이름을 직접 입력해야 합니다.

실행 방법:
    # 3ds Max에서
    exec(open(r"D:\path\to\PyJalLib\tests\simple_test_p4_direct.py").read())
    
    # 명령줄에서
    python tests\simple_test_p4_direct.py
"""

import sys
import traceback
from datetime import datetime

# ============================================================================
# 설정: 여기에 워크스페이스 이름을 입력하세요
# ============================================================================
WORKSPACE_NAME = "Kwangsoo_DevStorage"  # ← 여기를 수정하세요!
DESCRIPTION = "P4 Direct Test - " + datetime.now().strftime("%Y%m%d_%H%M%S")
# ============================================================================

print("=" * 80)
print("P4 Python 직접 사용 테스트")
print("=" * 80)
print(f"워크스페이스: {WORKSPACE_NAME}")
print(f"설명: {DESCRIPTION}")
print("")

# P4 가져오기
try:
    from P4 import P4, P4Exception
    print("✓ P4 모듈 import 성공")
except ImportError as e:
    print(f"✗ P4 모듈 import 실패: {e}")
    sys.exit(1)

# P4 객체 생성 및 연결
try:
    p4 = P4()
    p4.client = WORKSPACE_NAME
    p4.connect()
    print(f"✓ P4 연결 성공")
    print(f"  - 서버: {p4.port}")
    print(f"  - 사용자: {p4.user}")
    print(f"  - 클라이언트: {p4.client}")
except Exception as e:
    print(f"✗ P4 연결 실패: {e}")
    print(traceback.format_exc())
    sys.exit(1)

print("")

# 체인지 스펙 생성
try:
    spec = p4.fetch_change()
    print(f"✓ fetch_change() 성공")
    print(f"  - 스펙 타입: {type(spec).__name__}")
    print(f"  - 필드: {list(spec.keys())}")
except Exception as e:
    print(f"✗ fetch_change() 실패: {e}")
    print(traceback.format_exc())
    p4.disconnect()
    sys.exit(1)

print("")

# Description 설정
spec["Description"] = DESCRIPTION

# 체인지리스트 저장 (핵심 테스트)
print("체인지리스트 저장 시도 중...")
print(f"  방법: p4.save_change(spec)")
print("")

try:
    result = p4.save_change(spec)
    print("=" * 80)
    print("✓✓✓ 성공! ✓✓✓")
    print("=" * 80)
    print(f"결과: {result}")
    
    # 체인지 번호 추출 시도
    try:
        if result and len(result) > 0:
            # "Change 12345 created" 형식에서 번호 추출
            change_num = str(result[0]).split()[1]
            print(f"생성된 체인지 번호: {change_num}")
    except:
        pass
        
except P4Exception as e:
    print("=" * 80)
    print("✗✗✗ 실패 (P4Exception) ✗✗✗")
    print("=" * 80)
    print(f"에러 타입: P4Exception")
    print(f"에러 메시지: {e}")
    print("")
    print("전체 스택 트레이스:")
    print("-" * 80)
    print(traceback.format_exc())
    
except Exception as e:
    print("=" * 80)
    print("✗✗✗ 실패 (기타 예외) ✗✗✗")
    print("=" * 80)
    print(f"에러 타입: {type(e).__name__}")
    print(f"에러 메시지: {e}")
    print("")
    print("전체 스택 트레이스:")
    print("-" * 80)
    print(traceback.format_exc())

finally:
    # 연결 해제
    try:
        p4.disconnect()
        print("")
        print("P4 연결 해제 완료")
    except:
        pass

print("=" * 80)
print("테스트 종료")
print("=" * 80)

