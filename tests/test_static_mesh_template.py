# -*- coding: utf-8 -*-
"""Legacy Static Mesh 임포트 템플릿 Type A - 부활한 템플릿의 산출물 사양.

**이관 이력 (2026-09-18 ExportToolsRefactor Phase 1, Q5):** MeshValidator가 pyjallib에
Static Mesh 템플릿이 없어 자체 문자열 템플릿(`func/ue5ImportScript.py` 175줄)을 들고
있었다. 그 본문을 `templates/legacyStaticMeshImportTemplate.py`로 이식하고
`TemplateProcessor.process_legacy_static_mesh_import_template`을 더했다. 여기의
생성 스크립트 문자열 검사 5건은 MeshValidator `tests/test_ue5_p4_handoff.py`의
`generated_script` 계열을 **템플릿 산출물에 대해 재적용**한 것이다(사양 불변).

TemplateProcessor의 치환 결과(생성된 스크립트 텍스트)만 검증한다. 실제 임포트
동작은 unreal 의존이라 실기(Phase 3 MeshValidator 임포트 1회)가 담당한다.
"""

import ast
from pathlib import Path

import pytest

from pyjallib.ue5 import templates as _templatesPkg
from pyjallib.ue5.templateProcessor import TemplateProcessor

_EXT_PACKAGE_PATH = r"E:/Ext/.venv/Lib/site-packages"
_PARENT_MATERIAL = "/Game/Omni/Common/M_Parent"
_RESULT_JSON_PATH = r"E:/DevStorage_root/DevStorage/Temp/meshImportResult.json"

# MeshValidator `_build_slots_data_code`가 내는 형태의 슬롯 리터럴(1슬롯·텍스처 1·MI 1)
_SLOTS_DATA = """slots = [
    {
        'slotName': r'Body',
        'fbxPath': r'E:/DevStorage_root/DevStorage/Char/Mesh/SM_Test.fbx',
        'meshDestPath': r'/Game/Omni/Char/Mesh',
        'assetName': r'SM_Test',
        'textures': [
            {'sourcePath': r'E:/DevStorage_root/DevStorage/Char/Texture/T_Test.tga', 'destPath': r'/Game/Omni/Char/Texture', 'assetName': r'T_Test'},
        ],
        'materialDestPath': r'/Game/Omni/Char/Material',
        'materialNames': ['MI_Test'],
    },
]"""

_BASE_DATA = {
    "inExtPackagePath": _EXT_PACKAGE_PATH,
    "inSlotsData": _SLOTS_DATA,
    "inParentMaterialContentPath": _PARENT_MATERIAL,
}


@pytest.fixture()
def processor():
    """TemplateProcessor 인스턴스를 만든다."""
    return TemplateProcessor()


def _render(inProcessor, inTemplateData, inTmpPath):
    """Static Mesh 템플릿을 렌더링하고 결과 텍스트를 반환한다."""
    outputPath = str(Path(inTmpPath) / "renderedStaticMeshScript.py")
    return inProcessor.process_legacy_static_mesh_import_template(
        inTemplateData=dict(inTemplateData), inOutputPath=outputPath
    )


@pytest.fixture()
def generated_script(processor, tmp_path):
    """결과 JSON 경로를 포함한 표준 데이터로 렌더링한 스크립트 텍스트."""
    data = dict(_BASE_DATA, inResultJsonPath=_RESULT_JSON_PATH)
    return _render(processor, data, tmp_path)


# ============================================================================
# MeshValidator 생성 스크립트 검사 5건 재적용
# ============================================================================

def test_generated_script_checks_out_all_asset_kinds(generated_script):
    """메시·텍스쳐·머티리얼 모두 소스 컨트롤에 열고 경로를 수집한다.

    원 위치: MeshValidator `test_generated_script_checks_out_all_asset_kinds`.
    텍스쳐·머티리얼 각각에 수집 호출이 배선되어 있어야 한다.
    """
    assert (
        "from pathUtils import ensure_directory_exists, checkout_or_add_file, "
        "open_for_source_control_checked" in generated_script
    )
    assert generated_script.count("open_for_source_control_checked([") >= 2


def test_generated_script_collects_failed_files(generated_script):
    """체크아웃 실패분을 `FailedFiles`로 결과에 실어 보낸다.

    원 위치: MeshValidator `test_generated_script_collects_failed_files`. 실패분을
    연 파일 목록에서 빼기만 하고 보고하지 않으면 무증상이 된다.
    """
    assert generated_script.count("'FailedFiles': scResult['failed']") >= 2
    assert generated_script.count("'OpenedFiles': scResult['opened']") >= 2


def test_generated_script_no_longer_skips_source_control(generated_script):
    """StaticMesh 임포트에서 inSkipSourceControl=True를 쓰지 않는다.

    원 위치: MeshValidator `test_generated_script_no_longer_skips_source_control`.
    """
    assert "inSkipSourceControl=True" not in generated_script


def test_generated_script_writes_result_json(generated_script):
    """연 파일 목록을 결과 JSON으로 남기도록 배선되어 있다.

    원 위치: MeshValidator `test_generated_script_writes_result_json`.
    """
    assert "from importResultWriter import write_import_result" in generated_script
    assert f"resultJsonPath = r'{_RESULT_JSON_PATH}'" in generated_script
    assert "write_import_result(" in generated_script


def test_generated_script_is_syntactically_valid(generated_script):
    """생성된 스크립트가 파싱 가능한 파이썬이어야 한다 (치환 오류 조기 검출).

    원 위치: MeshValidator `test_generated_script_is_syntactically_valid`. 원 템플릿은
    `str.format`용 `{{ }}` 이스케이프를 썼고 이식본은 `TemplateProcessor`의 단순
    치환이라 이스케이프를 풀었다 - 이 검사가 그 변환을 가장 먼저 잡는다.
    """
    ast.parse(generated_script)


# ============================================================================
# 템플릿 인자 배선 (MeshValidator 슬롯 데이터 → 템플릿 자리표시자)
# ============================================================================

def test_slots_data_is_embedded_verbatim(generated_script):
    """슬롯 리터럴 코드가 그대로 들어가고 자리표시자가 남지 않는다."""
    assert _SLOTS_DATA in generated_script
    assert "{inSlotsData}" not in generated_script
    assert "'slotName': r'Body'" in generated_script


def test_parent_material_path_is_embedded(generated_script):
    """Parent Material 경로가 `parentMaterialPath` 변수로 치환된다."""
    assert f"parentMaterialPath = r'{_PARENT_MATERIAL}'" in generated_script
    assert "{inParentMaterialContentPath}" not in generated_script


def test_ext_package_path_points_to_inunreal(generated_script):
    """외부 패키지 경로가 치환되고 inUnreal 모듈 경로 조립이 살아 있다."""
    assert f"extPackagePath = r'{_EXT_PACKAGE_PATH}'" in generated_script
    assert "/pyjallib/ue5/inUnreal" in generated_script
    assert "from legacyStaticMeshImporter import LegacyStaticMeshImporter" in generated_script


def test_pipeline_covers_mesh_texture_and_material_instance(generated_script):
    """Static Mesh → 텍스처 `AssetImportTask` → `MaterialInstanceConstantFactoryNew` 3단이 있다."""
    assert "importer.import_static_mesh(" in generated_script
    assert "unreal.AssetImportTask()" in generated_script
    assert "unreal.MaterialInstanceConstantFactoryNew()" in generated_script
    assert 'mi.set_editor_property("parent", parentMaterial)' in generated_script


def test_no_python_format_braces_remain(generated_script):
    """`str.format` 이스케이프 잔재(`{{`/`}}`)가 산출물에 없다."""
    assert "{{" not in generated_script
    assert "}}" not in generated_script


# ============================================================================
# TemplateProcessor 계약 - 필수 키 · 선택 키 기본값
# ============================================================================

@pytest.mark.parametrize(
    "missingKey", ["inExtPackagePath", "inSlotsData", "inParentMaterialContentPath"]
)
def test_missing_required_key_raises(processor, tmp_path, missingKey):
    """필수 키가 빠지면 ValueError다."""
    data = dict(_BASE_DATA)
    del data[missingKey]

    with pytest.raises(ValueError):
        _render(processor, data, tmp_path)


def test_result_json_path_defaults_to_empty_string(processor, tmp_path):
    """`inResultJsonPath`를 생략하면 빈 문자열로 치환되어 템플릿이 기록을 생략한다."""
    rendered = _render(processor, _BASE_DATA, tmp_path)

    assert "resultJsonPath = r''" in rendered
    assert "{inResultJsonPath}" not in rendered


def test_output_file_is_written(processor, tmp_path):
    """렌더링 결과가 지정 경로에 파일로 남는다(UE5가 이 파일을 실행한다)."""
    outputPath = Path(tmp_path) / "meshImportScript.py"

    rendered = processor.process_legacy_static_mesh_import_template(
        inTemplateData=dict(_BASE_DATA), inOutputPath=str(outputPath)
    )

    assert outputPath.exists()
    assert outputPath.read_text(encoding="utf-8") == rendered


# ============================================================================
# 부활 확인 - 상수·파일·통합 진입점
# ============================================================================

def test_template_constant_and_file_are_registered():
    """템플릿 이름 상수가 패키지에 있고 파일이 실존한다.

    `test_legacy_dead_paths_removed.py`가 고정하던 부재 단정을 이 테스트가 존재
    단정으로 뒤집는다 - 부활이 의도된 결정임을 드러내는 장치.
    """
    assert _templatesPkg.LEGACY_STATIC_MESH_IMPORT_TEMPLATE == "legacyStaticMeshImport"
    templatePath = Path(_templatesPkg.get_template_path(_templatesPkg.LEGACY_STATIC_MESH_IMPORT_TEMPLATE))

    assert templatePath.name == "legacyStaticMeshImportTemplate.py"
    assert templatePath.exists()
    assert "legacyStaticMeshImport" in _templatesPkg.get_available_templates()


def test_unified_entry_point_resolves_static_mesh_legacy(processor, tmp_path):
    """통합 진입점 `process_import_template('static_mesh', 'legacy', ...)`가 같은 산출물을 낸다."""
    assert processor._get_template_name("static_mesh", "legacy") == (
        _templatesPkg.LEGACY_STATIC_MESH_IMPORT_TEMPLATE
    )

    viaUnified = processor.process_import_template(
        "static_mesh", "legacy", dict(_BASE_DATA),
        str(Path(tmp_path) / "unified.py"),
    )
    viaDirect = _render(processor, _BASE_DATA, tmp_path)

    assert viaUnified == viaDirect


def test_static_mesh_interchange_is_still_absent(processor):
    """부활은 legacy 조합만이다 - Interchange Static Mesh는 여전히 없다(Non-Goal)."""
    with pytest.raises(ValueError):
        processor._get_template_name("static_mesh", "interchange")
