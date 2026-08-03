# -*- coding: utf-8 -*-
"""죽은 legacy 임포트 경로가 제거된 상태를 단정하는 회귀 테스트.

제거 근거 (2026-08-03 전수 조사):
    - `LegacySkeletonImporter`: 사용처 0 + `self.naming`(미정의 속성) 참조로
      호출 즉시 `AttributeError`. 한 번도 실행된 적 없는 경로였다.
    - `LegacySkeletalMeshImporter`: 사용처 0. 동작은 하지만 아무도 부르지 않았다.
    - legacy skeleton / skeletalMesh / staticMesh 템플릿과 그 프로세서 메서드:
      호출부 0 (워크스페이스 툴 4개 + 배포 ORVTools 트리 모두).
      staticMesh는 클래스만 살아 있다 - MeshValidator가 자체 생성 스크립트에서
      직접 import하므로 템플릿 경유 경로는 쓰이지 않는다.

이 테스트는 "지웠다"를 고정한다. 되살릴 이유가 생기면 이 테스트를 먼저 지우게
되므로, 부활이 의도적 결정으로 드러난다.
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyjallib.ue5 import templates as _templatesPkg
from pyjallib.ue5.templateProcessor import TemplateProcessor

_INUNREAL_DIR = str(
    Path(__file__).resolve().parents[1] / "src" / "pyjallib" / "ue5" / "inUnreal"
)


# ============================================================================
# 임포터 모듈 부재
# ============================================================================

@pytest.mark.parametrize(
    "moduleName", ["legacySkeletonImporter", "legacySkeletalMeshImporter"]
)
def test_dead_importer_modules_are_gone(moduleName):
    """죽은 임포터 모듈 파일이 남아 있지 않다."""
    assert not (Path(_INUNREAL_DIR) / f"{moduleName}.py").exists()


def test_surviving_importers_are_still_loadable():
    """살아 있는 임포터(Animation / StaticMesh)는 여전히 로드된다.

    제거 과정에서 플랫 import 사슬(`legacyBaseImporter` -> `pathUtils` 등)을
    깨뜨리지 않았는지 확인한다.
    """
    savedModules = {
        name: sys.modules.get(name)
        for name in (
            "unreal",
            "pathUtils",
            "legacyBaseImporter",
            "legacyImporterSettings",
            "legacyAnimationImporter",
            "legacyStaticMeshImporter",
        )
    }
    for name in savedModules:
        sys.modules.pop(name, None)

    sys.modules["unreal"] = MagicMock()
    sys.path.insert(0, _INUNREAL_DIR)
    try:
        animModule = importlib.import_module("legacyAnimationImporter")
        staticModule = importlib.import_module("legacyStaticMeshImporter")
        assert hasattr(animModule, "LegacyAnimationImporter")
        assert hasattr(staticModule, "LegacyStaticMeshImporter")
    finally:
        sys.path.remove(_INUNREAL_DIR)
        for name, original in savedModules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


# ============================================================================
# 템플릿 / 프로세서 메서드 부재
# ============================================================================

@pytest.mark.parametrize(
    "templateFileName",
    [
        "legacySkeletonImportTemplate.py",
        "legacySkeletalMeshImportTemplate.py",
        "legacyStaticMeshImportTemplate.py",
    ],
)
def test_dead_template_files_are_gone(templateFileName):
    """죽은 템플릿 파일이 남아 있지 않다."""
    templatesDir = Path(_templatesPkg.__file__).parent
    assert not (templatesDir / templateFileName).exists()


@pytest.mark.parametrize(
    "constantName",
    [
        "LEGACY_SKELETON_IMPORT_TEMPLATE",
        "LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE",
        "LEGACY_STATIC_MESH_IMPORT_TEMPLATE",
    ],
)
def test_dead_template_constants_are_gone(constantName):
    """죽은 템플릿 이름 상수가 제거되었다."""
    assert not hasattr(_templatesPkg, constantName)


@pytest.mark.parametrize(
    "methodName",
    [
        "process_legacy_skeleton_import_template",
        "process_legacy_skeletal_mesh_import_template",
        "process_legacy_static_mesh_import_template",
    ],
)
def test_dead_processor_methods_are_gone(methodName):
    """죽은 프로세서 메서드가 제거되었다."""
    assert not hasattr(TemplateProcessor, methodName)


@pytest.mark.parametrize(
    "assetType", ["skeleton", "skeletal_mesh", "static_mesh"]
)
def test_legacy_combination_is_rejected_by_unified_entry_point(assetType):
    """통합 진입점에서 legacy 조합이 더 이상 해석되지 않는다."""
    processor = TemplateProcessor()
    with pytest.raises(ValueError):
        processor._get_template_name(assetType, "legacy")


def test_surviving_legacy_combinations_still_resolve():
    """살아 있는 legacy 조합(animation / batch_animation)은 그대로 동작한다."""
    processor = TemplateProcessor()
    assert processor._get_template_name("animation", "legacy") == "legacyAnimImport"
    assert (
        processor._get_template_name("batch_animation", "legacy")
        == "legacyBatchAnimImport"
    )


def test_interchange_skeleton_combinations_are_untouched():
    """interchange 쪽 skeleton / skeletal_mesh 조합은 제거 대상이 아니다."""
    processor = TemplateProcessor()
    assert processor._get_template_name("skeleton", "interchange") == "interchangeSkeletonImport"
    assert (
        processor._get_template_name("skeletal_mesh", "interchange")
        == "interchangeSkeletalMeshImport"
    )


# ============================================================================
# 임포트 설정 프리셋
# ============================================================================

def test_dead_preset_methods_are_gone():
    """죽은 임포터의 프리셋 옵션 메서드가 함께 제거되었다."""
    savedModules = {
        name: sys.modules.get(name) for name in ("unreal", "legacyImporterSettings")
    }
    for name in savedModules:
        sys.modules.pop(name, None)

    sys.modules["unreal"] = MagicMock()
    sys.path.insert(0, _INUNREAL_DIR)
    try:
        module = importlib.import_module("legacyImporterSettings")
        settingsClass = module.LegacyImporterSettings
        assert not hasattr(settingsClass, "set_options_for_skeleton_import")
        assert not hasattr(settingsClass, "set_options_for_skeletal_mesh_import")
        # 살아 있는 프리셋은 유지
        assert hasattr(settingsClass, "set_options_for_static_mesh_import")
        assert hasattr(settingsClass, "set_options_for_animation_import")
    finally:
        sys.path.remove(_INUNREAL_DIR)
        for name, original in savedModules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
