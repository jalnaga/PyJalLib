# -*- coding: utf-8 -*-
"""legacy 애니메이션 임포트의 0 커브 옵션 단위 테스트 (unreal mock).

`do_not_import_curve_with_zero`가 True면 클립 전 구간이 0인 커브(그 클립에서
쓰이지 않은 모프 채널 등)가 AnimSequence에서 통째로 누락되어, 커브 집합이
클립마다 달라진다. 엔진 쪽에서 커브 이름으로 조회·블렌딩하는 소비 코드가
"있는 클립/없는 클립"을 구분해야 하므로 이 값을 False로 고정한다.

값이 박혀 있는 지점이 둘(`legacyAnimationImporter`의 실제 임포트 경로와
`legacyImporterSettings`의 Animation 프리셋)이라, 두 지점이 갈리면 즉시
실패하도록 같은 축으로 함께 단정한다.

inUnreal 모듈은 언리얼 에디터 전용(플랫 import + unreal 의존)이므로
`unreal`을 sys.modules에 mock으로 등록하고 inUnreal 디렉토리를 sys.path에
추가해 콘솔에서 옵션 설정만 검증한다 (실제 임포트 동작은 UE5가 담당).
"""

import importlib
import sys
from pathlib import Path, PurePosixPath
from unittest.mock import MagicMock

import pytest

_INUNREAL_DIR = str(
    Path(__file__).resolve().parents[1] / "src" / "pyjallib" / "ue5" / "inUnreal"
)
_MODULE_NAMES = (
    "unreal",
    "pathUtils",
    "legacyBaseImporter",
    "legacyImporterSettings",
    "legacyAnimationImporter",
)

_CURVE_OPTION_KEY = "do_not_import_curve_with_zero"

_CONTENT_ROOT_PREFIX = "C:/proj/Content/Omni"
_FBX_ROOT_PREFIX = "C:/DevStorage/Omni"
_FBX_FILE = "C:/DevStorage/Omni/Char/Anim/A_Test.fbx"
_DESTINATION_PATH = "/Game/Omni/Char/Anim"
_SKELETON_CONTENT_PATH = "/Game/Omni/Char/Rig/SK_Test"


class _FakeSkeleton:
    """isinstance 분기용 fake unreal.Skeleton."""

    def get_name(self):
        return "SK_Test"

    def get_path_name(self):
        return _SKELETON_CONTENT_PATH


class _FakeSkeletalMesh:
    """isinstance 분기용 fake unreal.SkeletalMesh."""

    def __init__(self):
        self.skeleton = _FakeSkeleton()

    def get_editor_property(self, inKey):
        return self.skeleton if inKey == "skeleton" else None


class _FakeAssetData:
    """find_asset_data 반환값 - 스켈레톤 해석에만 쓰인다."""

    def __init__(self, inContentPath, inAsset):
        self.package_name = inContentPath
        self.asset_name = PurePosixPath(inContentPath).name
        self._asset = inAsset

    def is_valid(self):
        return True

    def get_asset(self):
        return self._asset


@pytest.fixture()
def inunreal_modules():
    """unreal mock + sys.path 주입으로 inUnreal 모듈들을 로드한다 (종료 시 원상 복구)."""
    savedModules = {name: sys.modules.get(name) for name in _MODULE_NAMES}
    for name in _MODULE_NAMES:
        sys.modules.pop(name, None)

    unrealMock = MagicMock()
    unrealMock.Skeleton = _FakeSkeleton
    unrealMock.SkeletalMesh = _FakeSkeletalMesh
    unrealMock.EditorAssetLibrary.find_asset_data.side_effect = (
        lambda p: _FakeAssetData(p, _FakeSkeleton())
    )
    sys.modules["unreal"] = unrealMock
    sys.path.insert(0, _INUNREAL_DIR)
    try:
        modules = {
            "animation": importlib.import_module("legacyAnimationImporter"),
            "settings": importlib.import_module("legacyImporterSettings"),
        }
        yield modules, unrealMock
    finally:
        sys.path.remove(_INUNREAL_DIR)
        for name, original in savedModules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _collect_curve_option_values(inImportOptions):
    """anim_sequence_import_data에 설정된 0 커브 옵션 값들을 호출 순서대로 모은다.

    Args:
        inImportOptions: set_editor_property 호출을 기록한 FbxImportUI mock

    Returns:
        설정된 값 리스트. 한 번도 설정하지 않았으면 빈 리스트.
    """
    calls = inImportOptions.anim_sequence_import_data.set_editor_property.call_args_list
    return [call.args[1] for call in calls if call.args and call.args[0] == _CURVE_OPTION_KEY]


def test_import_task_does_not_drop_zero_curves(inunreal_modules):
    """실제 임포트 경로가 0 커브 옵션을 False로 설정한다 (True 설정 0회)."""
    modules, unrealMock = inunreal_modules

    importer = modules["animation"].LegacyAnimationImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    importer.create_import_task(
        _FBX_FILE, _DESTINATION_PATH, inSkeletonContentPath=_SKELETON_CONTENT_PATH
    )

    values = _collect_curve_option_values(unrealMock.FbxImportUI.return_value)
    assert values == [False]


def test_animation_preset_matches_import_task(inunreal_modules):
    """Animation 프리셋도 같은 값을 쓴다 (두 지점이 갈리면 실패)."""
    modules, unrealMock = inunreal_modules

    settings = modules["settings"].LegacyImporterSettings(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX,
        inFbxRootPrefix=_FBX_ROOT_PREFIX,
        inPresetName="Animation",
    )
    settings.set_options_for_animation_import()

    values = _collect_curve_option_values(unrealMock.FbxImportUI.return_value)
    assert values == [False]
