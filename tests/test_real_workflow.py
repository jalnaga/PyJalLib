"""
실제 툴의 워크플로우를 재현하는 테스트

AnimNameSelector.py에서 발생하는 정확한 시퀀스를 재현합니다.
"""

import sys
from pathlib import Path

# PyJalLib 경로 추가
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# orvlib 경로 추가
orvlib_path = Path("d:/Work/00_Scripting/orvlib/src")
if str(orvlib_path) not in sys.path:
    sys.path.insert(0, str(orvlib_path))

from pyjallib.perforce import Perforce
from orvlib.p4Sync import P4Sync

print("=" * 80)
print("실제 툴 워크플로우 재현 테스트")
print("=" * 80)

# 1. P4Sync 초기화 (툴 시작 시 한 번)
print("\n[1단계] P4Sync 초기화 (툴 시작)")
try:
    p4Sync = P4Sync()
    print(f"✓ P4Sync 초기화 성공")
    print(f"  - devStorageP4 타입: {type(p4Sync.devStorageP4)}")
    print(f"  - devStorageP4 객체 ID: {id(p4Sync.devStorageP4)}")
    print(f"  - devStorageP4.connected: {p4Sync.devStorageP4.connected}")
    
    if hasattr(p4Sync.devStorageP4, '_service') and hasattr(p4Sync.devStorageP4._service, 'adapter'):
        print(f"  - 내부 P4 객체 ID: {id(p4Sync.devStorageP4._service.adapter.p4)}")
except Exception as e:
    print(f"✗ P4Sync 초기화 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. 필수 파일 동기화 (툴 시작 시)
print("\n[2단계] 필수 파일 동기화")
try:
    # 실제 툴은 sync_all_required_files()를 호출하지만,
    # 테스트에서는 건너뛰거나 간단한 sync만 수행
    print("  (동기화 건너뜀)")
except Exception as e:
    print(f"✗ 동기화 실패: {e}")

# 3. 여러 번의 저장 작업 시뮬레이션
print("\n[3단계] 여러 번의 저장 작업 시뮬레이션")
print("-" * 80)

test_files = [
    "test_anim_01",
    "test_anim_02",
    "test_anim_03",
]

for i, filename in enumerate(test_files, 1):
    print(f"\n저장 시도 #{i}: {filename}")
    print("-" * 40)
    
    # AnimNameSelector.py의 403번 라인과 동일한 호출
    description = p4Sync.prefix + " Save Anim File\n- " + filename
    
    print(f"Description: {repr(description)}")
    print(f"devStorageP4 객체 ID: {id(p4Sync.devStorageP4)}")
    
    try:
        # 실제 툴과 동일한 호출 방식
        result = p4Sync.devStorageP4.create_change_list(description)
        change_num = result.get("Change")
        
        print(f"✓ 체인지리스트 생성 성공: Change #{change_num}")
        
        # 생성된 체인지리스트 삭제 (cleanup)
        try:
            p4Sync.devStorageP4.delete_empty_change_list(int(change_num))
            print(f"  (삭제 완료)")
        except Exception as e:
            print(f"  (삭제 실패: {e})")
            
    except Exception as e:
        print(f"✗ 체인지리스트 생성 실패!")
        print(f"  에러 타입: {type(e).__name__}")
        print(f"  에러 메시지: {e}")
        print("\n전체 스택 트레이스:")
        print("-" * 80)
        import traceback
        traceback.print_exc()
        print("-" * 80)
        
        # 첫 실패 후에도 계속 시도
        print("\n⚠️  실패했지만 다음 시도를 계속합니다 (실제 환경 재현)...")

# 4. P4 객체 상태 출력
print("\n" + "=" * 80)
print("[최종 상태 확인]")
print("=" * 80)
print(f"devStorageP4 연결 상태: {p4Sync.devStorageP4.connected}")

if hasattr(p4Sync.devStorageP4, '_service') and hasattr(p4Sync.devStorageP4._service, 'adapter'):
    adapter = p4Sync.devStorageP4._service.adapter
    print(f"P4 객체 연결 상태: {adapter.p4.connected()}")
    print(f"P4 포트: {adapter.p4.port}")
    print(f"P4 사용자: {adapter.p4.user}")
    print(f"P4 클라이언트: {adapter.p4.client}")

# 5. Cleanup
print("\n[정리]")
try:
    p4Sync.devStorageP4.disconnect()
    p4Sync.omniP4.disconnect()
    print("✓ P4 연결 해제 완료")
except Exception as e:
    print(f"연결 해제 중 오류 (무시): {e}")

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)

