# -*- coding: utf-8 -*-
"""verify_asset_saved 저장 검증 분기 단위 테스트 (unreal mock).

UE5 임포트에서 임포트 태스크의 저장이 파일 잠금 등으로 실패해도 파이썬
예외가 나지 않아 툴이 성공으로 오판하는 silent 실패를 막는 검증 메서드다.
inUnreal 모듈은 언리얼 에디터 전용(플랫 import + unreal 의존)이므로,
unreal을 sys.modules에 mock으로 등록하고 inUnreal 디렉토리를 sys.path에
추가해 콘솔에서 분기만 검증한다 (실제 저장 동작은 UE5 헤드레스 스모크 담당).
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_INUNREAL_DIR = str(
    Path(__file__).resolve().parents[1] / "src" / "pyjallib" / "ue5" / "inUnreal"
)
_MODULE_NAMES = ("unreal", "legacyBaseImporter", "legacyImporterSettings")


@pytest.fixture()
def legacy_base_importer_module():
    """unreal mock + sys.path 주입으로 legacyBaseImporter를 로드한다 (종료 시 원상 복구)."""
    savedModules = {name: sys.modules.get(name) for name in _MODULE_NAMES}
    for name in _MODULE_NAMES:
        sys.modules.pop(name, None)

    unrealMock = MagicMock()
    sys.modules["unreal"] = unrealMock
    sys.path.insert(0, _INUNREAL_DIR)
    try:
        module = importlib.import_module("legacyBaseImporter")
        yield module, unrealMock
    finally:
        sys.path.remove(_INUNREAL_DIR)
        for name, original in savedModules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _make_probe(inModule):
    """설정 로드 없이 verify_asset_saved만 쓰는 최소 구현체를 만든다."""

    class _Probe(inModule.LegacyBaseImporter):
        def __init__(self):
            pass

        @property
        def asset_type(self):
            return "Probe"

        def create_import_task(self, inFbxFile, inDestinationPath):
            return None

    return _Probe()


def test_verify_asset_saved_passes_when_save_succeeds(legacy_base_importer_module):
    """save_asset이 True면 예외 없이 통과하고 only_if_is_dirty=True로 호출된다."""
    module, unrealMock = legacy_base_importer_module
    unrealMock.EditorAssetLibrary.save_asset.return_value = True

    probe = _make_probe(module)
    probe.verify_asset_saved("/Game/Test/A_Test_Anim")

    unrealMock.EditorAssetLibrary.save_asset.assert_called_once_with(
        "/Game/Test/A_Test_Anim", only_if_is_dirty=True
    )


def test_verify_asset_saved_raises_when_save_fails(legacy_base_importer_module):
    """save_asset이 False면(디스크 미반영) ValueError로 실패를 전파한다."""
    module, unrealMock = legacy_base_importer_module
    unrealMock.EditorAssetLibrary.save_asset.return_value = False

    probe = _make_probe(module)
    with pytest.raises(ValueError, match="에셋 저장 실패"):
        probe.verify_asset_saved("/Game/Test/A_Test_Anim")
