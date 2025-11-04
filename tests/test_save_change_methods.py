"""
save_change 다양한 호출 방식 테스트

문제가 있는 환경에서 어떤 방식이 작동하는지 확인합니다.
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
print("save_change 다양한 호출 방식 테스트")
print("=" * 80)

# P4Sync 초기화
try:
    p4Sync = P4Sync()
    workspace = p4Sync.devStorageP4.p4.client if hasattr(p4Sync.devStorageP4, 'p4') else None
    
    if not workspace:
        # Perforce 객체 직접 접근
        if hasattr(p4Sync.devStorageP4, '_service'):
            workspace = p4Sync.devStorageP4._service.adapter.p4.client
    
    print(f"워크스페이스: {workspace}")
except Exception as e:
    print(f"P4Sync 초기화 실패: {e}")
    sys.exit(1)

# 순수 P4 객체로 테스트
p4 = P4()
p4.client = workspace

try:
    p4.connect()
    print(f"✓ P4 연결 성공")
except Exception as e:
    print(f"✗ P4 연결 실패: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("테스트 시작")
print("=" * 80)

# 테스트 Description
description = "[Test] save_change 방식 테스트"

# 방법 1: save_change() 직접 호출 (현재 방식)
print("\n[방법 1] p4.save_change(spec)")
print("-" * 80)
try:
    spec = p4.fetch_change()
    spec["Description"] = description + " - Method 1"
    
    print(f"spec 타입: {type(spec)}")
    print(f"spec 내용: {spec}")
    
    result = p4.save_change(spec)
    
    print(f"✓ 성공!")
    print(f"결과: {result}")
    
    # Change 번호 추출
    if result and len(result) > 0:
        try:
            change_num = int(str(result[0]).split()[1])
            print(f"생성된 Change: {change_num}")
            
            # 삭제
            p4.run("change", "-d", str(change_num))
            print(f"(삭제 완료)")
        except:
            pass
            
except P4Exception as e:
    print(f"✗ P4Exception 발생!")
    print(f"에러 메시지: {e}")
    print(f"p4.errors: {p4.errors}")
    print(f"p4.warnings: {p4.warnings}")
except Exception as e:
    print(f"✗ 기타 예외 발생!")
    print(f"에러 타입: {type(e).__name__}")
    print(f"에러 메시지: {e}")

# 방법 2: p4.input 속성 사용
print("\n[방법 2] p4.input = spec; p4.run('change', '-i')")
print("-" * 80)
try:
    spec = p4.fetch_change()
    spec["Description"] = description + " - Method 2"
    
    p4.input = spec
    result = p4.run("change", "-i")
    
    print(f"✓ 성공!")
    print(f"결과: {result}")
    
    # Change 번호 추출 및 삭제
    if result and len(result) > 0:
        try:
            change_num = int(str(result[0]).split()[1])
            print(f"생성된 Change: {change_num}")
            p4.run("change", "-d", str(change_num))
            print(f"(삭제 완료)")
        except:
            pass
            
except P4Exception as e:
    print(f"✗ P4Exception 발생!")
    print(f"에러 메시지: {e}")
    print(f"p4.errors: {p4.errors}")
    print(f"p4.warnings: {p4.warnings}")
except Exception as e:
    print(f"✗ 기타 예외 발생!")
    print(f"에러 타입: {type(e).__name__}")
    print(f"에러 메시지: {e}")

# 방법 3: run() with input 파라미터
print("\n[방법 3] p4.run('change', '-i', input=spec)")
print("-" * 80)
try:
    spec = p4.fetch_change()
    spec["Description"] = description + " - Method 3"
    
    result = p4.run("change", "-i", input=spec)
    
    print(f"✓ 성공!")
    print(f"결과: {result}")
    
    # Change 번호 추출 및 삭제
    if result and len(result) > 0:
        try:
            change_num = int(str(result[0]).split()[1])
            print(f"생성된 Change: {change_num}")
            p4.run("change", "-d", str(change_num))
            print(f"(삭제 완료)")
        except:
            pass
            
except P4Exception as e:
    print(f"✗ P4Exception 발생!")
    print(f"에러 메시지: {e}")
    print(f"p4.errors: {p4.errors}")
    print(f"p4.warnings: {p4.warnings}")
except Exception as e:
    print(f"✗ 기타 예외 발생!")
    print(f"에러 타입: {type(e).__name__}")
    print(f"에러 메시지: {e}")

# 방법 4: pyjallib 사용
print("\n[방법 4] pyjallib.perforce.create_change_list()")
print("-" * 80)
try:
    result = p4Sync.devStorageP4.create_change_list(description + " - Method 4 (pyjallib)")
    
    print(f"✓ 성공!")
    print(f"결과: {result}")
    
    change_num = result.get("Change")
    if change_num:
        print(f"생성된 Change: {change_num}")
        p4Sync.devStorageP4.delete_empty_change_list(int(change_num))
        print(f"(삭제 완료)")
        
except Exception as e:
    print(f"✗ 예외 발생!")
    print(f"에러 타입: {type(e).__name__}")
    print(f"에러 메시지: {e}")
    import traceback
    traceback.print_exc()

# 연결 해제
p4.disconnect()
print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)


