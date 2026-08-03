# -*- coding: utf-8 -*-
"""legacy 임포트 템플릿의 결과 JSON 핸드오프 배선 단위 테스트.

UE5 헤드레스는 별도 프로세스라 반환값을 직접 받을 수 없다. 템플릿이 임포트
결과(성공 여부, 연 파일 절대경로)를 JSON으로 남기고 툴이 회수하는 구조이며,
`inResultJsonPath`는 **선택 키**다 - 누락하면 빈 문자열로 채워져 템플릿이
기록을 생략하므로 구 호출부와 하위호환된다.

여기서는 TemplateProcessor의 치환 결과(생성된 스크립트 텍스트)만 검증한다.
실제 기록 동작은 unreal 의존이라 헤드레스(Type C) 담당이고, 순수 계산부인
`collect_opened_files`만 unreal mock으로 따로 확인한다.
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyjallib.ue5.templateProcessor import TemplateProcessor

_INUNREAL_DIR = str(
    Path(__file__).resolve().parents[1] / "src" / "pyjallib" / "ue5" / "inUnreal"
)

_RESULT_JSON_PATH = r"E:/DevStorage_root/DevStorage/Temp/animImportResult.json"

_BASE_ANIM_DATA = {
    "inExtPackagePath": r"E:/ExtPythonPackage/site-packages",
    "inFbxPath": r"E:/DevStorage_root/DevStorage/Char/Anim/A_Test.fbx",
    "inDestinationPath": "/Game/Omni/Char/Anim",
    "inSkeletonPath": "/Game/Omni/Char/Rig/SK_Test",
}


@pytest.fixture()
def processor():
    """TemplateProcessor 인스턴스를 만든다."""
    return TemplateProcessor()


def _render(inProcessor, inMethodName, inTemplateData, inTmpPath):
    """지정한 처리 메서드로 템플릿을 렌더링하고 결과 텍스트를 반환한다."""
    outputPath = str(Path(inTmpPath) / "renderedScript.py")
    return getattr(inProcessor, inMethodName)(
        inTemplateData=dict(inTemplateData), inOutputPath=outputPath
    )


# ============================================================================
# 결과 JSON 경로 배선
# ============================================================================

def test_animation_template_embeds_result_json_path(processor, tmp_path):
    """결과 JSON 경로를 주면 템플릿에 그대로 치환된다."""
    data = dict(_BASE_ANIM_DATA, inResultJsonPath=_RESULT_JSON_PATH)
    rendered = _render(
        processor, "process_legacy_animation_import_template", data, tmp_path
    )

    assert f"resultJsonPath = r'{_RESULT_JSON_PATH}'" in rendered
    assert "write_import_result(resultJsonPath, importResults, inSuccess=True)" in rendered


def test_batch_animation_template_embeds_result_json_path(processor, tmp_path):
    """배치 템플릿도 동일하게 결과 JSON 경로를 배선한다."""
    data = {
        "inExtPackagePath": _BASE_ANIM_DATA["inExtPackagePath"],
        "inFbxPaths": TemplateProcessor.format_list_for_template(
            [_BASE_ANIM_DATA["inFbxPath"]]
        ),
        "inDestinationPath": _BASE_ANIM_DATA["inDestinationPath"],
        "inSkeletonPath": _BASE_ANIM_DATA["inSkeletonPath"],
        "inResultJsonPath": _RESULT_JSON_PATH,
    }
    rendered = _render(
        processor, "process_legacy_batch_anim_import_template", data, tmp_path
    )

    assert f"resultJsonPath = r'{_RESULT_JSON_PATH}'" in rendered
    assert "importResults.append(result)" in rendered


def test_missing_result_json_path_falls_back_to_empty_string(processor, tmp_path):
    """키를 누락하면 빈 문자열로 채워 기록을 생략한다 (하위호환).

    치환되지 않은 `{inResultJsonPath}` 자리표시자가 그대로 남으면 템플릿이
    존재하지 않는 경로에 기록을 시도하게 되므로, 기본값 주입이 필수다.
    """
    rendered = _render(
        processor, "process_legacy_animation_import_template", _BASE_ANIM_DATA, tmp_path
    )

    assert "resultJsonPath = r''" in rendered
    assert "{inResultJsonPath}" not in rendered


def test_unified_entry_point_also_defaults_result_json_path(processor, tmp_path):
    """통합 진입점(process_import_template)에서도 선택 키 기본값이 채워진다."""
    outputPath = str(Path(tmp_path) / "unifiedScript.py")
    rendered = processor.process_import_template(
        "animation", "legacy", dict(_BASE_ANIM_DATA), outputPath
    )

    assert "resultJsonPath = r''" in rendered
    assert "{inResultJsonPath}" not in rendered


@pytest.mark.parametrize(
    "methodName,templateData",
    [
        (
            "process_legacy_skeletal_mesh_import_template",
            _BASE_ANIM_DATA,
        ),
        (
            "process_legacy_skeleton_import_template",
            {
                "inExtPackagePath": _BASE_ANIM_DATA["inExtPackagePath"],
                "inFbxPath": _BASE_ANIM_DATA["inFbxPath"],
                "inDestinationPath": _BASE_ANIM_DATA["inDestinationPath"],
            },
        ),
        (
            "process_legacy_static_mesh_import_template",
            {
                "inExtPackagePath": _BASE_ANIM_DATA["inExtPackagePath"],
                "inFbxPath": _BASE_ANIM_DATA["inFbxPath"],
                "inDestinationPath": _BASE_ANIM_DATA["inDestinationPath"],
            },
        ),
    ],
)
def test_sibling_templates_are_aligned(processor, tmp_path, methodName, templateData):
    """형제 템플릿 3종도 같은 결과 JSON 구조로 정렬되어 있다."""
    data = dict(templateData, inResultJsonPath=_RESULT_JSON_PATH)
    rendered = _render(processor, methodName, data, tmp_path)

    assert "from importResultWriter import write_import_result" in rendered
    assert f"resultJsonPath = r'{_RESULT_JSON_PATH}'" in rendered
    assert "write_import_result(resultJsonPath, importResults, inSuccess=True)" in rendered


def test_templates_record_partial_result_before_reraising(processor, tmp_path):
    """실패 시에도 그 시점까지의 결과를 남기고 예외를 전파한다."""
    data = dict(_BASE_ANIM_DATA, inResultJsonPath=_RESULT_JSON_PATH)
    rendered = _render(
        processor, "process_legacy_animation_import_template", data, tmp_path
    )

    assert "inSuccess=False, inError=str(e)" in rendered
    assert "\n    raise\n" in rendered


# ============================================================================
# 연 파일 합집합 (순수 계산부)
# ============================================================================

@pytest.fixture()
def import_result_writer():
    """unreal mock + sys.path 주입으로 importResultWriter를 로드한다."""
    savedModules = {
        name: sys.modules.get(name) for name in ("unreal", "importResultWriter")
    }
    for name in savedModules:
        sys.modules.pop(name, None)

    sys.modules["unreal"] = MagicMock()
    sys.path.insert(0, _INUNREAL_DIR)
    try:
        yield importlib.import_module("importResultWriter")
    finally:
        sys.path.remove(_INUNREAL_DIR)
        for name, original in savedModules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_collect_opened_files_merges_and_dedupes_in_order(import_result_writer):
    """여러 결과의 연 파일을 순서 보존으로 합치고 중복(공유 스켈레톤)을 제거한다."""
    results = [
        {"OpenedFiles": ["C:/ws/A.uasset", "C:/ws/SK.uasset"]},
        {"OpenedFiles": ["C:/ws/B.uasset", "C:/ws/SK.uasset"]},
    ]

    merged = import_result_writer.collect_opened_files(results)

    assert merged == ["C:/ws/A.uasset", "C:/ws/SK.uasset", "C:/ws/B.uasset"]


def test_collect_opened_files_tolerates_missing_key(import_result_writer):
    """OpenedFiles 키가 없는 결과가 섞여도 예외 없이 건너뛴다."""
    results = [{"Success": True}, {"OpenedFiles": ["C:/ws/A.uasset"]}, None]

    merged = import_result_writer.collect_opened_files(results)

    assert merged == ["C:/ws/A.uasset"]


def test_write_import_result_skips_when_path_is_empty(import_result_writer, tmp_path):
    """결과 경로가 비면 파일을 만들지 않고 False를 반환한다 (하위호환 경로)."""
    assert import_result_writer.write_import_result("", [{"OpenedFiles": []}]) is False
    assert list(Path(tmp_path).iterdir()) == []


def test_write_import_result_writes_payload(import_result_writer, tmp_path):
    """성공 경로에서 success/error/results/openedFiles를 기록한다."""
    import json

    outPath = Path(tmp_path) / "nested" / "result.json"
    results = [{"Name": "A_Test", "Success": True, "OpenedFiles": ["C:/ws/A.uasset"]}]

    assert import_result_writer.write_import_result(str(outPath), results) is True

    payload = json.loads(outPath.read_text(encoding="utf-8"))
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["openedFiles"] == ["C:/ws/A.uasset"]
    assert payload["results"] == results
