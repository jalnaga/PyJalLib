"""
실제 툴 워크플로우 정밀 분석

AnimNameSelector의 실제 실행 흐름을 단계별로 재현하고 분석합니다.
"""

import sys
from pathlib import Path

# orvlib 경로 추가
orvlib_path = Path("d:/Work/00_Scripting/orvlib/src")
if str(orvlib_path) not in sys.path:
    sys.path.insert(0, str(orvlib_path))

try:
    from orvlib.p4Sync import P4Sync
    from P4 import P4, P4Exception
except ImportError as e:
    print(f"Import 실패: {e}")
    sys.exit(1)

print("=" * 80)
print("실제 툴 워크플로우 정밀 분석")
print("=" * 80)

def analyze_p4_detailed(p4, label):
    """P4 객체의 상세 상태를 분석합니다."""
    print(f"\n[{label}]")
    print(f"  객체 ID: {id(p4)}")
    print(f"  connected(): {p4.connected()}")
    
    # 모든 P4 설정 출력
    attrs_to_check = ['client', 'user', 'port', 'host', 'charset', 'exception_level']
    for attr in attrs_to_check:
        try:
            value = getattr(p4, attr, 'N/A')
            print(f"  {attr}: {value}")
        except:
            print(f"  {attr}: (접근 불가)")
    
    print(f"  errors: {p4.errors}")
    print(f"  warnings: {p4.warnings}")

print("\n1단계: P4Sync 초기화 전")
print("-" * 80)

# P4Sync 초기화
print("\n2단계: P4Sync 초기화 중...")
p4Sync = P4Sync()

print("\n3단계: P4Sync 초기화 후")
print("-" * 80)

# devStorageP4 상태 확인
devStorage = p4Sync.devStorageP4
p4_obj = devStorage._service.adapter.p4

analyze_p4_detailed(p4_obj, "P4Sync 초기화 직후")

# P4Sync가 어떤 작업을 했는지 확인
print(f"\nP4Sync가 실행한 명령들:")
print(f"  - omniP4 초기화됨: {p4Sync.omniP4 is not None}")
print(f"  - devStorageP4 초기화됨: {p4Sync.devStorageP4 is not None}")

# 이제 실제 툴처럼 체인지리스트 생성
print("\n" + "=" * 80)
print("4단계: 체인지리스트 생성 시도 (실제 툴 방식)")
print("=" * 80)

for i in range(3):
    print(f"\n[저장 시도 #{i+1}]")
    print("-" * 80)
    
    analyze_p4_detailed(p4_obj, f"시도 {i+1} 시작 전")
    
    # AnimNameSelector.save_file()과 동일한 방식
    description = f"[Animator Test] Save Anim File\n- test_anim_{i+1:02d}"
    print(f"\nDescription: {repr(description)}")
    
    try:
        # 실제 툴과 동일하게 호출
        result = devStorage.create_change_list(description)
        
        analyze_p4_detailed(p4_obj, f"시도 {i+1} 성공 후")
        print(f"\n[OK] Change {result['Change']} 생성 성공")
        
        # 삭제
        try:
            p4_obj.run("change", "-d", str(result["Change"]))
            print(f"(Change {result['Change']} 삭제)")
        except Exception as e:
            print(f"(삭제 실패: {e})")
            
    except Exception as e:
        analyze_p4_detailed(p4_obj, f"시도 {i+1} 실패 후")
        print(f"\n[FAIL] 에러 발생!")
        print(f"  에러 타입: {type(e).__name__}")
        print(f"  에러 메시지: {e}")
        
        import traceback
        print("\n전체 스택 트레이스:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)
        
        print("\n계속 진행...")

print("\n" + "=" * 80)
print("5단계: 최종 상태")
print("=" * 80)
analyze_p4_detailed(p4_obj, "모든 시도 완료 후")

print("\n" + "=" * 80)
print("분석 완료")
print("=" * 80)

