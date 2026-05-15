# -*- coding: utf-8 -*-
"""pytest conftest.py - UE5 테스트 공통 설정.

`pyjallib.ue5.inUnreal` 하위 모듈은 모듈 최상단에서 `unreal` 및
UE5 에디터 전용 모듈(`legacyImporterSettings` 등)을 import한다.
콘솔(Type A) pytest 환경에는 해당 모듈이 존재하지 않으므로
collect 단계에서 ImportError로 실패한다.

이 conftest는 ue5 테스트 디렉토리 범위로 한정하여 필요한 모듈을
`sys.modules`에 MagicMock으로 미리 주입한다. 최상위 `tests/conftest.py`
(pymxs mock 전용)는 건드리지 않으며 다른 테스트에 영향을 주지 않는다.
"""

import sys
from unittest.mock import MagicMock

# UE5 인-에디터 전용 모듈을 mock으로 등록한다.
# legacyBaseImporter.py는 모듈 최상단에서 다음을 import:
#   - import unreal
#   - from legacyImporterSettings import LegacyImporterSettings
_UE5_MOCK_MODULES = [
    "unreal",
    "legacyImporterSettings",
]

for _modName in _UE5_MOCK_MODULES:
    if _modName not in sys.modules:
        sys.modules[_modName] = MagicMock()

# `from legacyImporterSettings import LegacyImporterSettings` 형태로 import되므로
# 모듈 mock의 `LegacyImporterSettings` 속성이 반드시 존재해야 한다.
# MagicMock은 임의 속성을 자동 생성하지만, 명시적으로 노출하여 의도를 분명히 한다.
sys.modules["legacyImporterSettings"].LegacyImporterSettings = MagicMock()
