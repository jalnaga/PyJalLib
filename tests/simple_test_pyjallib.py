"""
pyjallib 라이브러리 사용 테스트

pyjallib의 Perforce 클래스를 사용하여 체인지리스트 생성을 테스트합니다.
orvlib에서 워크스페이스를 자동으로 감지합니다.

실행 방법:
    # 3ds Max에서
    exec(open(r"D:\path\to\PyJalLib\tests\simple_test_pyjallib.py").read())
    
    # 명령줄에서
    python tests\simple_test_pyjallib.py
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

# PyJalLib 경로 추가
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# ============================================================================
# 설정
# ============================================================================
DESCRIPTION = "PyJalLib Test - " + datetime.now().strftime("%Y%m%d_%H%M%S")
# ============================================================================

print("=" * 80)
print("pyjallib 라이브러리 사용 테스트")
print("=" * 80)
print(f"설명: {DESCRIPTION}")
print("")

# orvlib에서 워크스페이스 자동 감지
workspace_name = None
print("orvlib에서 워크스페이스 자동 감지 시도 중...")

try:
    from orvlib.p4Sync import P4Sync
    orvP4 = P4Sync()
    
    # devStorageP4 시도
    if hasattr(orvP4, 'devStorageP4') and orvP4.devStorageP4:
        if hasattr(orvP4.devStorageP4, 'p4'):
            workspace_name = orvP4.devStorageP4.p4.client
            print(f"✓ devStorageP4에서 워크스페이스 감지: {workspace_name}")
    
    # omniP4 시도
    if not workspace_name and hasattr(orvP4, 'omniP4') and orvP4.omniP4:
        if hasattr(orvP4.omniP4, 'p4'):
            workspace_name = orvP4.omniP4.p4.client
            print(f"✓ omniP4에서 워크스페이스 감지: {workspace_name}")
    
    if not workspace_name:
        print("✗ orvlib에서 워크스페이스를 찾을 수 없습니다")
        sys.exit(1)
        
except ImportError as e:
    print(f"✗ orvlib를 찾을 수 없습니다: {e}")
    print("  orvlib가 설치되어 있고 경로가 올바른지 확인하세요")
    sys.exit(1)
except Exception as e:
    print(f"✗ orvlib 초기화 실패: {e}")
    print(traceback.format_exc())
    sys.exit(1)

print("")

# pyjallib import
try:
    from pyjallib.perforce import Perforce
    from pyjallib.exceptions import PerforceError
    print("✓ pyjallib 모듈 import 성공")
except ImportError as e:
    print(f"✗ pyjallib 모듈 import 실패: {e}")
    print(traceback.format_exc())
    sys.exit(1)

print("")

# Perforce 객체 생성
try:
    p4_instance = Perforce()
    print("✓ Perforce 객체 생성 성공")
except Exception as e:
    print(f"✗ Perforce 객체 생성 실패: {e}")
    print(traceback.format_exc())
    sys.exit(1)

# 연결
try:
    p4_instance.connect(workspace_name)
    print(f"✓ Perforce 연결 성공")
    print(f"  - 워크스페이스 루트: {p4_instance.workspaceRoot}")
    print(f"  - 연결 상태: {p4_instance.connected}")
except Exception as e:
    print(f"✗ Perforce 연결 실패: {e}")
    print(traceback.format_exc())
    sys.exit(1)

print("")

# 체인지리스트 생성 (핵심 테스트)
print("체인지리스트 생성 시도 중...")
print(f"  방법: p4_instance.create_change_list(description)")
print("")

try:
    result = p4_instance.create_change_list(DESCRIPTION)
    print("=" * 80)
    print("✓✓✓ 성공! ✓✓✓")
    print("=" * 80)
    print(f"결과 타입: {type(result).__name__}")
    print(f"결과: {result}")
    
    # 체인지 번호 추출
    if isinstance(result, dict) and "Change" in result:
        change_num = result["Change"]
        print(f"생성된 체인지 번호: {change_num}")
        
except PerforceError as e:
    print("=" * 80)
    print("✗✗✗ 실패 (PerforceError) ✗✗✗")
    print("=" * 80)
    print(f"에러 타입: PerforceError")
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
        p4_instance.disconnect()
        print("")
        print("Perforce 연결 해제 완료")
    except:
        pass

print("=" * 80)
print("테스트 종료")
print("=" * 80)

