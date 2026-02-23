# -*- coding: utf-8 -*-
"""pytest conftest.py - 공통 테스트 설정.

pymxs를 포함한 3ds Max 전용 모듈들을 mock 처리하여
콘솔 환경(Type A)에서도 테스트가 실행될 수 있도록 한다.
"""

import sys
from unittest.mock import MagicMock

# 3ds Max 전용 모듈을 sys.modules에 mock 등록
# pyjallib.max.__init__ 로드 시 pymxs import가 시도되므로
# 반드시 실제 import 전에 등록해야 한다.
_MAX_MOCK_MODULES = [
    "pymxs",
    "pymxs.runtime",
]

for _modName in _MAX_MOCK_MODULES:
    if _modName not in sys.modules:
        sys.modules[_modName] = MagicMock()

# toolState 모듈이 로드되면 _HAS_PYMXS를 False로 강제 설정한다.
# pymxs가 mock으로 등록되어 import가 성공하므로 _HAS_PYMXS=True가 되는 문제를 방지.
import importlib
import pyjallib.max.ui.toolState as _toolStateModule
_toolStateModule._HAS_PYMXS = False
