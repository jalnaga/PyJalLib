# -*- coding: utf-8 -*-
"""`inUnreal/materialSlots.py`의 **모듈 로드 경로**만 콘솔에서 검증한다.

어댑터의 쓰기 경로(3단 쓰기·되읽기·저장 가드)는 여기서 검증하지 않는다 - `unreal` mock은
구조체 사본을 흉내 내지 않으므로 그 판정은 Type C(`tests/ue5/ue5_test_material_slots.py`)가
한다. 여기서 보는 것은 순수 결정 모듈을 **두 로드 방식 모두에서** 찾는가이다.

- 패키지 import(`pyjallib.ue5.inUnreal.materialSlots`) -> 상대 import로 패키지 모듈을 쓴다.
- UE5 legacy 템플릿식 평면 로드(`inUnreal` 폴더가 `sys.path`에 있고 패키지 문맥 없음)
  -> 형제 폴더의 `materialSlotRules.py`를 경로로 로드한다. 배포본이 실제로 이 방식으로 돈다.

`unreal`은 `tests/ue5/conftest.py`가 MagicMock으로 주입한다.
"""

import importlib.util
import sys
from pathlib import Path

import pyjallib.ue5.materialSlotRules as packageRules

_SRC_UE5 = Path(packageRules.__file__).resolve().parent
_ADAPTER_PATH = _SRC_UE5 / "inUnreal" / "materialSlots.py"


def test_package_import_uses_package_rules_module() -> None:
    from pyjallib.ue5.inUnreal import materialSlots

    assert materialSlots.materialSlotRules is packageRules


def test_flat_load_resolves_sibling_rules_file(monkeypatch) -> None:
    # 평면 로드 직전 상태: 패키지 문맥 없음 + 평면 이름의 규칙 모듈이 아직 없음
    monkeypatch.delitem(sys.modules, "materialSlotRules", raising=False)
    spec = importlib.util.spec_from_file_location("materialSlots_flat", _ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    loadedRules = module.materialSlotRules
    assert loadedRules is not packageRules, "평면 로드가 패키지 모듈을 집었다면 이 테스트는 평면 경로를 안 탔다"
    assert Path(loadedRules.__file__).resolve() == _SRC_UE5 / "materialSlotRules.py"
    assert sys.modules["materialSlotRules"] is loadedRules
    assert loadedRules.decide_slots(["Body"], inRenameTable={"Body": "Skin_Body"})[0].targetName == "Skin_Body"


def test_flat_load_does_not_put_ue5_dir_on_sys_path(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "materialSlotRules", raising=False)
    before = list(sys.path)
    spec = importlib.util.spec_from_file_location("materialSlots_flat2", _ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert sys.path == before
    assert str(_SRC_UE5) not in sys.path
