"""
P4 Python API 버전 및 동작 확인

문제가 있는 환경과 정상 환경의 P4 API 차이를 확인합니다.
"""

import sys
from pathlib import Path

print("=" * 80)
print("P4 Python API 버전 및 동작 확인")
print("=" * 80)

# P4 모듈 정보
try:
    from P4 import P4, P4Exception
    print("\n[P4 모듈 정보]")
    print(f"✓ P4 모듈 import 성공")
    
    # 버전 정보
    if hasattr(P4, '__version__'):
        print(f"  P4.__version__: {P4.__version__}")
    else:
        print(f"  P4.__version__: (없음)")
    
    # API 식별 정보
    try:
        from P4 import P4API
        identify = P4API.identify()
        print(f"  P4API.identify(): {identify}")
    except:
        print(f"  P4API.identify(): (실패)")
    
except ImportError as e:
    print(f"✗ P4 모듈 import 실패: {e}")
    sys.exit(1)

# Python 환경
print("\n[Python 환경]")
print(f"  Python 버전: {sys.version}")
print(f"  Python 실행 파일: {sys.executable}")
print(f"  플랫폼: {sys.platform}")

# 3ds Max 감지
try:
    from pymxs import runtime as rt
    print(f"  3ds Max 버전: {rt.maxVersion()[0]}")
    print(f"  실행 환경: 3ds Max 내부")
except:
    print(f"  실행 환경: 독립 Python")

# P4 객체 내부 속성 확인
print("\n[P4 객체 속성 확인]")
p4 = P4()
print(f"  P4 객체 타입: {type(p4)}")
print(f"  P4 객체 속성 목록: {[attr for attr in dir(p4) if not attr.startswith('_')]}")

# save_change 메서드 확인
print("\n[save_change 메서드 확인]")
if hasattr(p4, 'save_change'):
    print(f"  ✓ save_change 메서드 존재")
    print(f"  save_change 타입: {type(p4.save_change)}")
    
    # 메서드 시그니처 확인 (가능한 경우)
    import inspect
    try:
        sig = inspect.signature(p4.save_change)
        print(f"  save_change 시그니처: {sig}")
    except:
        print(f"  save_change 시그니처: (확인 불가)")
else:
    print(f"  ✗ save_change 메서드 없음!")

# P4 오류/경고 속성 확인
print("\n[P4 오류/경고 속성 확인]")
print(f"  errors 속성 타입: {type(p4.errors)}")
print(f"  warnings 속성 타입: {type(p4.warnings)}")

# errors와 warnings가 쓰기 가능한지 확인
print("\n[속성 쓰기 가능 여부 확인]")
try:
    original_errors = p4.errors
    p4.errors = []
    p4.errors = original_errors
    print(f"  ✓ p4.errors 쓰기 가능")
except AttributeError as e:
    print(f"  ✗ p4.errors 쓰기 불가: {e}")

try:
    original_warnings = p4.warnings
    p4.warnings = []
    p4.warnings = original_warnings
    print(f"  ✓ p4.warnings 쓰기 가능")
except AttributeError as e:
    print(f"  ✗ p4.warnings 쓰기 불가: {e}")

# exception_level 확인
print("\n[exception_level 확인]")
if hasattr(p4, 'exception_level'):
    print(f"  ✓ exception_level 존재")
    print(f"  현재 값: {p4.exception_level}")
    try:
        p4.exception_level = 1
        print(f"  ✓ exception_level 설정 가능")
    except Exception as e:
        print(f"  ✗ exception_level 설정 실패: {e}")
else:
    print(f"  ✗ exception_level 없음")

print("\n" + "=" * 80)
print("확인 완료")
print("=" * 80)

