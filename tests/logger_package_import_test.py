#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 패키지 레벨 import 테스트
"""

import sys
from pathlib import Path

# 테스트를 위해 src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_package_level_import():
    """패키지 레벨에서 Logger import 테스트"""
    print("=== 패키지 레벨 Logger import 테스트 ===")
    
    try:
        # 패키지 레벨에서 직접 import
        from pyjallib import Logger
        print("✓ 패키지 레벨에서 Logger import 성공")
        
        # Logger 인스턴스 생성 테스트
        logger = Logger(inLogFileName="package_import_test")
        logger.set_session("패키지 Import 테스트")
        logger.info("패키지 레벨에서 Logger를 성공적으로 import했습니다")
        logger.end_session()
        logger.close()
        
        print("✓ Logger 인스턴스 생성 및 사용 성공")
        
    except ImportError as e:
        print(f"✗ 패키지 레벨 import 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ Logger 사용 중 오류: {e}")
        return False
    
    return True


def test_direct_module_import():
    """직접 모듈 import 테스트 (기존 방식)"""
    print("\n=== 직접 모듈 import 테스트 ===")
    
    try:
        # 직접 모듈에서 import
        from pyjallib.logger import Logger
        print("✓ 직접 모듈에서 Logger import 성공")
        
        # Logger 인스턴스 생성 테스트
        logger = Logger(inLogFileName="direct_import_test")
        logger.set_session("직접 Import 테스트")
        logger.info("직접 모듈에서 Logger를 성공적으로 import했습니다")
        logger.end_session()
        logger.close()
        
        print("✓ Logger 인스턴스 생성 및 사용 성공")
        
    except ImportError as e:
        print(f"✗ 직접 모듈 import 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ Logger 사용 중 오류: {e}")
        return False
    
    return True


def test_other_imports():
    """다른 클래스들과 함께 import 테스트"""
    print("\n=== 다른 클래스들과 함께 import 테스트 ===")
    
    try:
        # 여러 클래스를 함께 import
        from pyjallib import Logger, Naming, Perforce, NamePart
        print("✓ 여러 클래스를 함께 import 성공")
        
        # 각 클래스가 정상적으로 import되었는지 확인
        classes = [
            ("Logger", Logger),
            ("Naming", Naming),
            ("Perforce", Perforce),
            ("NamePart", NamePart)
        ]
        
        for class_name, class_obj in classes:
            if class_obj is not None:
                print(f"  ✓ {class_name} 클래스 사용 가능")
            else:
                print(f"  ✗ {class_name} 클래스 import 실패")
                
    except ImportError as e:
        print(f"✗ 다중 클래스 import 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ 다중 클래스 테스트 중 오류: {e}")
        return False
    
    return True


def main():
    """메인 테스트 실행"""
    print("Logger 클래스 패키지 import 테스트 시작\n")
    
    results = []
    
    # 각 테스트 실행
    results.append(test_package_level_import())
    results.append(test_direct_module_import())
    results.append(test_other_imports())
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    if all(results):
        print("✅ 모든 import 테스트 성공!")
        print("💡 이제 다음과 같이 사용할 수 있습니다:")
        print("   from pyjallib import Logger")
        print("   logger = Logger(inLogFileName='my_module')")
    else:
        print("❌ 일부 테스트 실패")
        failed_tests = []
        test_names = ["패키지 레벨 import", "직접 모듈 import", "다중 클래스 import"]
        for i, result in enumerate(results):
            if not result:
                failed_tests.append(test_names[i])
        print(f"실패한 테스트: {', '.join(failed_tests)}")


if __name__ == "__main__":
    main() 