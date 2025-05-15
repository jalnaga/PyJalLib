#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# reloadModules 모듈

pyjallib 패키지와 모든 하위 모듈을 동적으로
다시 로드하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 메모리에 로드된 pyjallib 모듈 감지
- importlib.reload()를 사용한 모듈 재로드
- 모듈 리로드 결과 보고

## 사용 예시
```python
from pyjallib.reloadModules import reload_modules

# 모듈 테스트 전에 모든 모듈 재로드
reloaded = reload_modules()
print(f"{len(reloaded)}개 모듈이 재로드되었습니다.")
```
"""

import sys
import importlib


def reload_modules():
    """
    pyjallib 패키지와 모든 하위 모듈을 다시 로드합니다.
    
    현재 메모리에 로드된 모든 pyjallib 모듈을 찾아서 재로드합니다.
    코드 변경 후 테스트 실행 전에 호출하여 최신 코드가 반영되도록 합니다.
    
    ## 동작 방식
    1. sys.modules에서 'pyjallib'로 시작하는 모든 모듈을 찾습니다.
    2. importlib.reload()를 사용하여 각 모듈을 다시 로드합니다.
    3. 재로드된 모듈 이름을 콘솔에 출력합니다.
    4. 재로드된 모듈 이름 목록을 반환합니다.
    
    ## Returns
    - list: 재로드된 모듈 이름 목록
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