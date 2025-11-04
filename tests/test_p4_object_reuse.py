"""
P4 객체 재사용 시 save_change() 문제 분석

새 P4 객체 vs 재사용 P4 객체의 차이점을 비교합니다.
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
print("P4 객체 재사용 문제 분석")
print("=" * 80)

# P4Sync 초기화
try:
    p4Sync = P4Sync()
    workspace = p4Sync.devStorageP4._service.adapter.p4.client
    print(f"워크스페이스: {workspace}\n")
except Exception as e:
    print(f"P4Sync 초기화 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def analyze_p4_state(p4, label):
    """P4 객체의 상태를 분석합니다."""
    print(f"\n[{label}]")
    print(f"  - 객체 ID: {id(p4)}")
    print(f"  - connected(): {p4.connected()}")
    print(f"  - client: {p4.client}")
    print(f"  - user: {p4.user}")
    print(f"  - port: {p4.port}")
    
    # 내부 상태 확인
    if hasattr(p4, 'input'):
        input_value = getattr(p4, 'input', None)
        if input_value:
            print(f"  - input 속성: {type(input_value)} (있음)")
        else:
            print(f"  - input 속성: None")
    
    # errors/warnings
    print(f"  - errors: {p4.errors}")
    print(f"  - warnings: {p4.warnings}")

# 테스트 1: 새로운 P4 객체로 체인지리스트 생성
print("=" * 80)
print("테스트 1: 새 P4 객체 (매번 생성)")
print("=" * 80)

for i in range(3):
    print(f"\n[시도 #{i+1}]")
    p4_new = P4()
    p4_new.client = workspace
    
    try:
        p4_new.connect()
        analyze_p4_state(p4_new, "연결 직후")
        
        spec = p4_new.fetch_change()
        spec["Description"] = f"[Test New] Attempt {i+1}"
        analyze_p4_state(p4_new, "fetch_change() 후")
        
        result = p4_new.save_change(spec)
        analyze_p4_state(p4_new, "save_change() 성공 후")
        
        print(f"  [OK] 성공: {result}")
        
        # 삭제
        if result and len(result) > 0:
            change_num = int(str(result[0]).split()[1])
            p4_new.run("change", "-d", str(change_num))
            print(f"  (Change {change_num} 삭제)")
            
    except P4Exception as e:
        analyze_p4_state(p4_new, "save_change() 실패 후")
        print(f"  [FAIL] 에러: {e}")
        
    finally:
        try:
            if p4_new.connected():
                p4_new.disconnect()
        except:
            pass

# 테스트 2: 재사용 P4 객체로 체인지리스트 생성
print("\n" + "=" * 80)
print("테스트 2: 재사용 P4 객체 (한 번만 생성)")
print("=" * 80)

p4_reuse = P4()
p4_reuse.client = workspace

try:
    p4_reuse.connect()
    analyze_p4_state(p4_reuse, "초기 연결")
    
    for i in range(3):
        print(f"\n[시도 #{i+1}]")
        
        try:
            analyze_p4_state(p4_reuse, f"시도 {i+1} 시작")
            
            spec = p4_reuse.fetch_change()
            analyze_p4_state(p4_reuse, "fetch_change() 후")
            
            spec["Description"] = f"[Test Reuse] Attempt {i+1}"
            
            result = p4_reuse.save_change(spec)
            analyze_p4_state(p4_reuse, "save_change() 성공 후")
            
            print(f"  [OK] 성공: {result}")
            
            # 삭제
            if result and len(result) > 0:
                change_num = int(str(result[0]).split()[1])
                p4_reuse.run("change", "-d", str(change_num))
                print(f"  (Change {change_num} 삭제)")
                
        except P4Exception as e:
            analyze_p4_state(p4_reuse, f"save_change() 실패 후 (시도 {i+1})")
            print(f"  [FAIL] 에러: {e}")
            print(f"  계속 진행...")
            
finally:
    try:
        if p4_reuse.connected():
            p4_reuse.disconnect()
    except:
        pass

# 테스트 3: pyjallib의 Perforce 객체로 체인지리스트 생성 (실제 툴 방식)
print("\n" + "=" * 80)
print("테스트 3: pyjallib Perforce 객체 (실제 툴 방식)")
print("=" * 80)

p4_pyjallib = p4Sync.devStorageP4._service.adapter.p4
print(f"pyjallib P4 객체 ID: {id(p4_pyjallib)}")

for i in range(3):
    print(f"\n[시도 #{i+1}]")
    
    try:
        analyze_p4_state(p4_pyjallib, f"시도 {i+1} 시작")
        
        result = p4Sync.devStorageP4.create_change_list(f"[Test PyJalLib] Attempt {i+1}")
        
        analyze_p4_state(p4_pyjallib, "create_change_list() 성공 후")
        print(f"  [OK] 성공: Change {result['Change']}")
        
        # 삭제
        p4_pyjallib.run("change", "-d", str(result["Change"]))
        print(f"  (Change {result['Change']} 삭제)")
        
    except Exception as e:
        analyze_p4_state(p4_pyjallib, f"create_change_list() 실패 후 (시도 {i+1})")
        print(f"  [FAIL] 에러: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n  계속 진행...")

print("\n" + "=" * 80)
print("분석 완료")
print("=" * 80)
print("\n주의사항:")
print("- 테스트 1에서 모두 성공하고 테스트 2/3에서 실패하면: P4 객체 재사용 문제")
print("- 특히 'connected()' 값이 False로 변하는 시점을 확인하세요")
print("- 'input' 속성이나 errors/warnings 변화도 주목하세요")

