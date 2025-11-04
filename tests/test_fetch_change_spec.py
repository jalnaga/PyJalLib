"""
fetch_change()가 반환하는 spec 구조 비교

정상 환경과 문제 환경에서 fetch_change() 결과를 비교합니다.
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
print("fetch_change() 반환 값 분석")
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

# 순수 P4 객체로 테스트
p4 = P4()
p4.client = workspace

try:
    p4.connect()
    print(f"[OK] P4 연결 성공\n")
except Exception as e:
    print(f"[FAIL] P4 연결 실패: {e}")
    sys.exit(1)

print("=" * 80)
print("fetch_change() 결과 분석")
print("=" * 80)

try:
    spec = p4.fetch_change()
    
    print(f"\n1. 기본 정보:")
    print(f"   - 타입: {type(spec)}")
    print(f"   - 타입 이름: {type(spec).__name__}")
    print(f"   - 타입 모듈: {type(spec).__module__}")
    
    print(f"\n2. 내용:")
    print(f"   spec = {spec}")
    
    print(f"\n3. 속성 및 메서드:")
    attrs = [attr for attr in dir(spec) if not attr.startswith('_')]
    print(f"   속성 목록: {attrs[:20]}")  # 처음 20개만
    
    print(f"\n4. Dict 형태로 변환 가능 여부:")
    try:
        if isinstance(spec, dict):
            print(f"   [OK] 이미 dict 타입")
            print(f"   - Keys: {list(spec.keys())}")
            print(f"   - Values 샘플:")
            for key, value in list(spec.items())[:5]:
                print(f"     {key}: {repr(value)}")
        else:
            print(f"   [INFO] dict가 아님")
            # dict로 변환 시도
            spec_dict = dict(spec)
            print(f"   [OK] dict()로 변환 성공")
            print(f"   - Keys: {list(spec_dict.keys())}")
    except Exception as e:
        print(f"   [FAIL] 변환 실패: {e}")
    
    print(f"\n5. 주요 필드 확인:")
    key_fields = ["Change", "Description", "Status", "Client", "User", "Files"]
    for field in key_fields:
        try:
            value = spec.get(field) if hasattr(spec, 'get') else spec[field] if field in spec else "N/A"
            print(f"   - {field}: {repr(value)}")
        except:
            print(f"   - {field}: (접근 불가)")
    
    print(f"\n6. Description 설정 테스트:")
    original_desc = spec.get("Description") if hasattr(spec, 'get') else spec.get("Description", "N/A")
    print(f"   - 원본 Description: {repr(original_desc)}")
    
    test_desc = "[Test] Description 설정 테스트"
    spec["Description"] = test_desc
    
    new_desc = spec.get("Description") if hasattr(spec, 'get') else spec["Description"]
    print(f"   - 새 Description: {repr(new_desc)}")
    print(f"   - 설정 성공: {new_desc == test_desc}")
    
    print(f"\n7. save_change() 호출 테스트:")
    print(f"   - spec 인자 타입: {type(spec)}")
    print(f"   - spec 인자 내용: {spec}")
    
    try:
        result = p4.save_change(spec)
        print(f"   [OK] save_change() 성공!")
        print(f"   - 결과: {result}")
        
        # Change 번호 추출 및 삭제
        if result and len(result) > 0:
            try:
                change_num = int(str(result[0]).split()[1])
                print(f"   - 생성된 Change: {change_num}")
                p4.run("change", "-d", str(change_num))
                print(f"   - (삭제 완료)")
            except Exception as e:
                print(f"   - (삭제 실패: {e})")
                
    except P4Exception as e:
        print(f"   [FAIL] save_change() 실패!")
        print(f"   - P4Exception: {e}")
        print(f"   - p4.errors: {p4.errors}")
        print(f"   - p4.warnings: {p4.warnings}")
        
        # 에러 발생 시 추가 디버깅
        print(f"\n   [추가 디버깅]")
        print(f"   - P4 연결 상태: {p4.connected()}")
        print(f"   - spec이 비었는지: {len(spec) if hasattr(spec, '__len__') else 'N/A'}")
        
except Exception as e:
    print(f"\n[ERROR] 예외 발생: {e}")
    import traceback
    traceback.print_exc()

finally:
    p4.disconnect()
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


