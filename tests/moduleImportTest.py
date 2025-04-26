import sys
import os
import importlib
import pkgutil

# 현재 스크립트의 디렉토리 path 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = os.path.abspath(os.path.join(current_dir, "..", "src"))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib

def test_import_modules():
    """pyjallib의 모든 모듈을 임포트해보는 테스트 함수"""
    print("PyJalLib 모듈 임포트 테스트 시작...")
    
    
    # 성공적으로 임포트된 모듈 수
    imported_count = 0
    # 임포트 실패한 모듈 목록
    failed_imports = []
    
    # pyjallib 패키지 내의 모든 모듈을 검색하고 임포트 시도
    for importer, modname, ispkg in pkgutil.walk_packages(pyjallib.__path__, prefix="pyjallib."):
        print(f"임포트 시도: {modname}")
        try:
            importlib.import_module(modname)
            imported_count += 1
            print(f"  성공: {modname}")
        except ImportError as e:
            failed_imports.append((modname, str(e)))
            print(f"  실패: {modname} - {e}")
    
    # 결과 출력
    print("\n== 임포트 테스트 결과 ==")
    print(f"성공적으로 임포트된 모듈: {imported_count}개")
    
    if failed_imports:
        print("\n임포트 실패한 모듈:")
        for module, error in failed_imports:
            print(f"- {module}: {error}")
    else:
        print("\n모든 모듈이 성공적으로 임포트되었습니다!")
        
    pyjallib.reload_jallib_modules()

if __name__ == "__main__":
    test_import_modules()