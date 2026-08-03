# -*- coding: utf-8 -*-
"""legacy 임포터 순수화(서밋 제거 + 연 파일 목록 반환) 단위 테스트 (unreal mock).

임포터가 `unreal.SourceControl.check_in_files`로 자동 서밋을 하면 바깥 툴의
체인지리스트 계층이 무력화된다(이미 서밋되어 CL이 비고 삭제됨). 수정 후
임포터는 **임포트 + 체크아웃까지만** 수행하고, 연 파일의 로컬 절대경로를
결과 딕셔너리의 `OpenedFiles`로 보고해야 한다.

inUnreal 모듈은 언리얼 에디터 전용(플랫 import + unreal 의존)이므로
`unreal`을 sys.modules에 mock으로 등록하고 inUnreal 디렉토리를 sys.path에
추가해 콘솔에서 분기만 검증한다 (실제 임포트 동작은 UE5 헤드레스 담당).
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
    "legacySkeletalMeshImporter",
    "legacyStaticMeshImporter",
)

_CONTENT_DIR = "C:/proj/Content"
_CONTENT_ROOT_PREFIX = "C:/proj/Content/Omni"
_FBX_ROOT_PREFIX = "C:/DevStorage/Omni"
_FBX_FILE = "C:/DevStorage/Omni/Char/Anim/A_Test.fbx"
_ASSET_FULL_PATH = "/Game/Omni/Char/Anim/A_Test"
_SKELETON_CONTENT_PATH = "/Game/Omni/Char/Rig/SK_Test"
_DEP_PATH = "/Game/Omni/Char/Rig/SK_Test"


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


class _FakeStaticMesh:
    """isinstance 분기용 fake unreal.StaticMesh."""


class _FakeAnimSequence:
    """isinstance 분기용 fake unreal.AnimSequence."""


class _FakeAsset:
    """load_asset이 돌려주는 최소 에셋 (시스템 경로 해석용 식별자만 보유)."""

    def __init__(self, inContentPath):
        self.contentPath = inContentPath


class _FakeAssetData:
    """find_asset_data 반환값 - 스켈레톤 해석과 의존성 조회에 모두 쓰인다."""

    def __init__(self, inContentPath, inAsset):
        self.package_name = inContentPath
        self.asset_name = PurePosixPath(inContentPath).name
        self._asset = inAsset

    def is_valid(self):
        return True

    def get_asset(self):
        return self._asset


_WORKSPACE_ROOT = "C:/ws"


def _system_path_of(inAsset):
    """fake 에셋의 Content 경로를 로컬 절대경로로 바꾼다 (워크스페이스 루트 접두)."""
    if isinstance(inAsset, _FakeAsset):
        return f"{_WORKSPACE_ROOT}{inAsset.contentPath}.uasset"
    return ""


_EXPECTED_OPENED_FILES = [
    f"{_WORKSPACE_ROOT}{_ASSET_FULL_PATH}.uasset",
    f"{_WORKSPACE_ROOT}{_DEP_PATH}.uasset",
]


def _configure_unreal_mock(inUnrealMock, inImportedObjects, inDependencies):
    """임포트 성공 경로를 통과시키는 최소 unreal mock 설정을 적용한다.

    Args:
        inUnrealMock: sys.modules에 등록된 unreal MagicMock
        inImportedObjects: import task가 돌려줄 임포트 결과 객체 리스트
        inDependencies: get_dependencies가 돌려줄 dirty dep Content 경로 리스트
    """
    # isinstance 분기 대상은 실제 클래스여야 한다 (MagicMock은 type이 아님)
    inUnrealMock.Skeleton = _FakeSkeleton
    inUnrealMock.SkeletalMesh = _FakeSkeletalMesh
    inUnrealMock.StaticMesh = _FakeStaticMesh
    inUnrealMock.AnimSequence = _FakeAnimSequence

    paths = inUnrealMock.Paths
    paths.convert_relative_path_to_full.side_effect = lambda p: p
    paths.project_content_dir.side_effect = lambda: _CONTENT_DIR
    paths.get_path.side_effect = lambda p: str(PurePosixPath(p).parent)
    paths.get_base_filename.side_effect = lambda p: PurePosixPath(p).stem
    paths.normalize_directory_name.side_effect = lambda p: p
    paths.directory_exists.side_effect = lambda p: True
    paths.file_exists.side_effect = lambda p: False

    editor = inUnrealMock.EditorAssetLibrary
    editor.does_asset_exist.side_effect = lambda p: False
    editor.make_directory.side_effect = lambda p: True
    editor.save_asset.side_effect = lambda p, only_if_is_dirty=False: True
    editor.load_asset.side_effect = lambda p: _FakeAsset(p)
    editor.find_asset_data.side_effect = lambda p: _FakeAssetData(p, _FakeSkeleton())

    inUnrealMock.SystemLibrary.get_system_path.side_effect = _system_path_of

    registry = MagicMock()
    registry.get_dependencies.side_effect = lambda *args, **kwargs: list(inDependencies)
    inUnrealMock.AssetRegistryHelpers.get_asset_registry.return_value = registry

    task = MagicMock()
    task.get_objects.return_value = list(inImportedObjects)
    task.imported_object_paths = [_ASSET_FULL_PATH]
    inUnrealMock.AssetImportTask.return_value = task

    return task


@pytest.fixture()
def inunreal_modules():
    """unreal mock + sys.path 주입으로 inUnreal 모듈들을 로드한다 (종료 시 원상 복구)."""
    savedModules = {name: sys.modules.get(name) for name in _MODULE_NAMES}
    for name in _MODULE_NAMES:
        sys.modules.pop(name, None)

    unrealMock = MagicMock()
    sys.modules["unreal"] = unrealMock
    sys.path.insert(0, _INUNREAL_DIR)
    try:
        modules = {
            "animation": importlib.import_module("legacyAnimationImporter"),
            "skeletalMesh": importlib.import_module("legacySkeletalMeshImporter"),
            "staticMesh": importlib.import_module("legacyStaticMeshImporter"),
        }
        yield modules, unrealMock
    finally:
        sys.path.remove(_INUNREAL_DIR)
        for name, original in savedModules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


# ============================================================================
# 애니메이션 임포터 (단수)
# ============================================================================

def test_import_animation_does_not_check_in(inunreal_modules):
    """임포터는 자동 서밋을 하지 않는다 (check_in_files 비호출 회귀 감시)."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeAnimSequence()], [_DEP_PATH])

    importer = modules["animation"].LegacyAnimationImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    importer.import_animation(_FBX_FILE, inSkeletonContentPath=_SKELETON_CONTENT_PATH)

    unrealMock.SourceControl.check_in_files.assert_not_called()


def test_import_animation_reports_opened_files(inunreal_modules):
    """결과 딕셔너리에 임포트 결과 + dirty dep의 로컬 절대경로가 담긴다."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeAnimSequence()], [_DEP_PATH])

    importer = modules["animation"].LegacyAnimationImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    result = importer.import_animation(
        _FBX_FILE, inSkeletonContentPath=_SKELETON_CONTENT_PATH
    )

    assert result["Success"] is True
    assert result["OpenedFiles"] == _EXPECTED_OPENED_FILES


def test_import_animation_checks_out_imported_asset_and_deps(inunreal_modules):
    """임포트 결과와 dirty dep 모두 체크아웃(열기) 대상이다."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeAnimSequence()], [_DEP_PATH])

    importer = modules["animation"].LegacyAnimationImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    importer.import_animation(_FBX_FILE, inSkeletonContentPath=_SKELETON_CONTENT_PATH)

    checkedOut = [
        call.args[0]
        for call in unrealMock.SourceControl.check_out_or_add_file.call_args_list
    ]
    assert _ASSET_FULL_PATH in checkedOut
    assert _DEP_PATH in checkedOut


def test_import_animation_skeleton_swap_path_reports_opened_files(inunreal_modules):
    """스켈레톤 스왑 경로도 서밋 없이 연 파일 목록을 반환한다."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeAnimSequence()], [_DEP_PATH])

    importer = modules["animation"].LegacyAnimationImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    # 스왑 판정을 True로 강제하고, consolidate 본체는 단위 테스트 범위 밖이라 스텁한다
    importer._needs_skeleton_swap = lambda assetFullPath, targetSkeleton: True
    importer._swap_skeleton_via_consolidate = (
        lambda inFbxFile, assetFullPath, inFbxSkeletonPath=None, inSkeletonContentPath=None: True
    )

    result = importer.import_animation(
        _FBX_FILE, inSkeletonContentPath=_SKELETON_CONTENT_PATH
    )

    unrealMock.SourceControl.check_in_files.assert_not_called()
    assert result["OpenedFiles"] == _EXPECTED_OPENED_FILES


def test_legacy_animation_importer_has_no_plural_import_method(inunreal_modules):
    """죽은 복수형 `import_animations`는 제거되었다 (사용처 0 확증 후 삭제)."""
    modules, _unrealMock = inunreal_modules
    assert not hasattr(
        modules["animation"].LegacyAnimationImporter, "import_animations"
    )


# ============================================================================
# 형제 임포터 (SkeletalMesh / StaticMesh)
# ============================================================================

def test_import_skeletal_mesh_does_not_check_in_and_reports_opened_files(
    inunreal_modules,
):
    """스켈레탈 메시 임포터도 서밋 없이 연 파일 목록을 반환한다."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeSkeletalMesh()], [_DEP_PATH])

    importer = modules["skeletalMesh"].LegacySkeletalMeshImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    result = importer.import_skeletal_mesh(
        _FBX_FILE, inSkeletonContentPath=_SKELETON_CONTENT_PATH
    )

    unrealMock.SourceControl.check_in_files.assert_not_called()
    assert result["OpenedFiles"] == _EXPECTED_OPENED_FILES


def test_import_static_mesh_does_not_check_in_and_reports_opened_files(
    inunreal_modules,
):
    """스태틱 메시 임포터도 서밋 없이 연 파일 목록을 반환한다."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeStaticMesh()], [_DEP_PATH])

    importer = modules["staticMesh"].LegacyStaticMeshImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    result = importer.import_static_mesh(_FBX_FILE)

    unrealMock.SourceControl.check_in_files.assert_not_called()
    assert result["OpenedFiles"] == _EXPECTED_OPENED_FILES


def test_import_static_mesh_skip_source_control_yields_empty_opened_files(
    inunreal_modules,
):
    """inSkipSourceControl=True이면 체크아웃을 건너뛰고 연 파일 목록이 비어 있다."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeStaticMesh()], [_DEP_PATH])

    importer = modules["staticMesh"].LegacyStaticMeshImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    result = importer.import_static_mesh(_FBX_FILE, inSkipSourceControl=True)

    unrealMock.SourceControl.check_in_files.assert_not_called()
    assert result["OpenedFiles"] == []


# ============================================================================
# 연 파일 목록 수집 헬퍼
# ============================================================================

def test_open_for_source_control_excludes_unresolvable_assets(inunreal_modules):
    """로드 실패/시스템 경로 해석 실패 항목은 목록에서 제외한다 (경고 후 계속)."""
    modules, unrealMock = inunreal_modules
    _configure_unreal_mock(unrealMock, [_FakeAnimSequence()], [])

    unrealMock.EditorAssetLibrary.load_asset.side_effect = (
        lambda p: None if p.endswith("Broken") else _FakeAsset(p)
    )

    importer = modules["animation"].LegacyAnimationImporter(
        inContentRootPrefix=_CONTENT_ROOT_PREFIX, inFbxRootPrefix=_FBX_ROOT_PREFIX
    )
    opened = importer.open_for_source_control(
        ["/Game/Omni/Char/Anim/A_Test", "/Game/Omni/Char/Anim/Broken"]
    )

    assert opened == [f"{_WORKSPACE_ROOT}{_ASSET_FULL_PATH}.uasset"]
    # 제외된 항목도 체크아웃 시도 자체는 수행한다 (열기는 임포터 책임)
    assert unrealMock.SourceControl.check_out_or_add_file.call_count == 2
