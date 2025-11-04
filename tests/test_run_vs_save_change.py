"""
p4.run("change", "-i", input=spec) vs p4.save_change(spec) 비교

문제 환경에서 두 방법의 동작 차이를 확인합니다.
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
print("run() vs save_change() 비교 테스트")
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

def test_method(method_name: str, test_func):
    """테스트 메서드를 실행하고 결과를 출력합니다."""
    print("=" * 80)
    print(f"테스트: {method_name}")
    print("=" * 80)
    
    p4 = P4()
    p4.client = workspace
    
    try:
        p4.connect()
        print(f"[OK] P4 연결 성공")
        print(f"  연결 상태 (연결 후): {p4.connected()}\n")
        
        # Spec 가져오기
        spec = p4.fetch_change()
        spec["Description"] = f"[Test] {method_name}"
        
        print(f"Spec 준비:")
        print(f"  - Description: {spec['Description']}")
        print(f"  - 연결 상태 (spec 준비 후): {p4.connected()}\n")
        
        # 테스트 함수 실행
        result = test_func(p4, spec)
        
        print(f"\n결과:")
        print(f"  [OK] 성공!")
        print(f"  - 반환값: {result}")
        print(f"  - 연결 상태 (실행 후): {p4.connected()}")
        
        # Change 번호 추출 및 삭제
        if result and len(result) > 0:
            try:
                change_num = int(str(result[0]).split()[1])
                print(f"  - 생성된 Change: {change_num}")
                
                if p4.connected():
                    p4.run("change", "-d", str(change_num))
                    print(f"  - (삭제 완료)")
                else:
                    print(f"  - (연결이 끊겨서 삭제 불가)")
            except Exception as e:
                print(f"  - (삭제 실패: {e})")
        
        return True
        
    except P4Exception as e:
        print(f"\n결과:")
        print(f"  [FAIL] 실패!")
        print(f"  - P4Exception: {e}")
        print(f"  - 연결 상태 (실패 후): {p4.connected()}")
        print(f"  - p4.errors: {p4.errors}")
        print(f"  - p4.warnings: {p4.warnings}")
        return False
        
    except Exception as e:
        print(f"\n결과:")
        print(f"  [ERROR] 예외 발생!")
        print(f"  - Exception: {e}")
        print(f"  - 연결 상태 (예외 후): {p4.connected()}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            if p4.connected():
                p4.disconnect()
        except:
            pass

# 테스트 1: save_change()
def test_save_change(p4, spec):
    return p4.save_change(spec)

# 테스트 2: run("change", "-i", input=spec)
def test_run_with_input_param(p4, spec):
    return p4.run("change", "-i", input=spec)

# 테스트 3: run("change", "-i") with p4.input
def test_run_with_input_attr(p4, spec):
    p4.input = spec
    return p4.run("change", "-i")

# 테스트 실행
print("\n")
result1 = test_method("p4.save_change(spec)", test_save_change)
print("\n")
result2 = test_method('p4.run("change", "-i", input=spec)', test_run_with_input_param)
print("\n")
result3 = test_method('p4.input = spec; p4.run("change", "-i")', test_run_with_input_attr)

# 요약
print("\n")
print("=" * 80)
print("테스트 요약")
print("=" * 80)

result1_text = "[OK] 성공" if result1 else "[FAIL] 실패"
result2_text = "[OK] 성공" if result2 else "[FAIL] 실패"
result3_text = "[OK] 성공" if result3 else "[FAIL] 실패"

print(f"1. p4.save_change(spec)                    : {result1_text}")
print(f'2. p4.run("change", "-i", input=spec)      : {result2_text}')
print(f'3. p4.input = spec; p4.run("change", "-i") : {result3_text}')
print("=" * 80)

if not result1 and (result2 or result3):
    print("\n[OK] 해결책 확인: run() 방식이 save_change()보다 안정적입니다!")
elif result1:
    print("\n[INFO] 이 환경에서는 save_change()가 정상 작동합니다.")
else:
    print("\n[ERROR] 모든 방법이 실패했습니다. 추가 조사가 필요합니다.")

