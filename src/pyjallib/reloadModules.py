#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pyjallib 패키지와 모든 하위 모듈을 다시 로드합니다.
"""

import sys
import importlib


def reload_modules():
    """
    pyjallib 패키지와 모든 하위 모듈을 다시 로드합니다.
    
    이 함수는 sys.modules에서 'pyjallib'로 시작하는 모든 모듈을 찾아
    importlib.reload()를 사용하여 다시 로드합니다.
    테스트 실행 전에 호출하여 최신 코드가 테스트에 적용되도록 합니다.
    """
    reloaded_modules = []
    
    # JalLib 모듈을 찾아 재로드
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('pyjallib') and module_name not in reloaded_modules:
            try:
                module = sys.modules[module_name]
                importlib.reload(module)
                reloaded_modules.append(module_name)
                print(f"{module_name} 모듈이 다시 로드 되었습니다.")
            except Exception as e:
                print(f"모듈 리로드 중 오류 발생 - {module_name}: {e}")
    
    return reloaded_modules