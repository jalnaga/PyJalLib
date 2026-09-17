# -*- coding: utf-8 -*-
"""소스 컨트롤 경로 정규화(`pathUtils.to_package_path`) Type A 단위 테스트.

2026-09-17 실측: 애니메이션 임포트 후 체크아웃이 전건 실패하고 CL이 생성되지
않았다. 원인은 `LegacyAnimationImporter`가 `task.imported_object_paths`가 주는
**오브젝트 경로**(`/Game/A/B.B`)를 그대로 소스 컨트롤에 넘긴 것이다. 엔진은 그
문자열을 패키지 파일명으로 변환하지 못하고 절대경로화해 클라이언트 루트 밖을
조회한 뒤 실패를 돌려줬다(`Path 'D:/Game/...' is not under client's root 'D:\\root'`
-> `Could not determine revision control state of file`).

여기서 단정하는 것:
    1. `to_package_path`가 오브젝트 경로·패키지 경로·`.uasset` 절대경로를 모두
       패키지 경로로 정규화한다
    2. `.` 절단이 **마지막 세그먼트에 한정**된다 (폴더 이름에 `.`이 있어도 안전)
    3. 진입점이 소스 컨트롤에 **패키지 경로로** 호출한다 (`call_args` 단정)
    4. 정규화가 실패 보고를 삼키지 않는다 - 반환 `False`(배타 락 등 진짜 실패)는
       여전히 `failed`에 남는다 (0.3.4가 세운 계약 보존)
    5. 실패 항목의 `contentPath`는 **정규화 전 입력 원본**이다 (호출자 대조용)

테스트 격리:
    `tests/ue5/conftest.py`가 `unreal`을 MagicMock으로 주입한다. 각 테스트는 그
    mock을 새로 갈아 끼우고 fixture가 원복한다(`test_checkout_result_report.py`와
    같은 패턴 - 전역 mock을 공유하면 호출 기록이 누적되어 단정이 오염된다).
"""

import sys
from unittest.mock import MagicMock

import pytest

from pyjallib.ue5.inUnreal import pathUtils


# 2026-09-17 로그에 실제로 찍힌 실패 경로. 합성 문자열 대신 이것을 쓴다.
FAILED_OBJECT_PATH = (
    "/Game/Omni/Characters/Villain/CheonInHo/AnimationB/Movie/CutScene/GumhoStation/"
    "A_Mv_CheonInHo_Vl_0040_CS_GHSt.A_Mv_CheonInHo_Vl_0040_CS_GHSt"
)
FAILED_PACKAGE_PATH = (
    "/Game/Omni/Characters/Villain/CheonInHo/AnimationB/Movie/CutScene/GumhoStation/"
    "A_Mv_CheonInHo_Vl_0040_CS_GHSt"
)

CONTENT_DIR = "D:/root/Omni/Content"


# ============================================================================
# 공통 fixture
# ============================================================================

@pytest.fixture()
def unreal_mock():
    """`pathUtils`가 보는 `unreal`을 이 테스트 전용 mock으로 갈아 끼운다.

    `absolute_path_to_content_path()`가 `unreal.Paths`를 실제로 쓰므로,
    MagicMock 기본 반환값(MagicMock) 대신 **문자열**을 돌려주도록 배선한다.
    배선하지 않으면 `Path(MagicMock)`에서 TypeError가 난다.

    Yields:
        MagicMock: `pathUtils.unreal`로 주입된 mock.
    """
    savedModule = sys.modules.get("unreal")
    savedAttr = pathUtils.unreal

    freshMock = MagicMock()
    freshMock.SourceControl.last_error_msg.return_value = "테스트 기본 사유"
    freshMock.Paths.project_content_dir.return_value = CONTENT_DIR
    freshMock.Paths.convert_relative_path_to_full.return_value = CONTENT_DIR
    freshMock.Paths.normalize_directory_name.side_effect = lambda inPath: inPath

    sys.modules["unreal"] = freshMock
    pathUtils.unreal = freshMock
    try:
        yield freshMock
    finally:
        pathUtils.unreal = savedAttr
        if savedModule is None:
            sys.modules.pop("unreal", None)
        else:
            sys.modules["unreal"] = savedModule


def _arrange_checkout(inUnrealMock, inCheckoutResults):
    """체크아웃 반환값과 에셋 로드·시스템 경로 해석을 배선한다.

    배선 키는 **소스 컨트롤에 실제로 넘어간 경로**다. 정규화가 제대로 되면
    패키지 경로로 조회되고, 안 되면 오브젝트 경로로 조회되어 기본값을 탄다.

    Args:
        inUnrealMock: `unreal_mock` fixture 값.
        inCheckoutResults: 경로 -> `check_out_or_add_file` 반환값(bool).

    Returns:
        None
    """
    def _checkOut(inContentPath, silent=False):
        return inCheckoutResults.get(inContentPath, True)

    inUnrealMock.SourceControl.check_out_or_add_file.side_effect = _checkOut
    inUnrealMock.EditorAssetLibrary.load_asset.side_effect = (
        lambda inContentPath: f"asset:{inContentPath}"
    )
    inUnrealMock.SystemLibrary.get_system_path.side_effect = (
        lambda inAssetObj: f"C:/ws{str(inAssetObj).replace('asset:', '')}.uasset"
    )


def _checkout_call_paths(inUnrealMock):
    """`check_out_or_add_file`에 넘어간 경로들을 호출 순서대로 모은다.

    Args:
        inUnrealMock: `unreal_mock` fixture 값.

    Returns:
        list[str]: 호출 인자 경로 리스트.
    """
    return [
        call.args[0]
        for call in inUnrealMock.SourceControl.check_out_or_add_file.call_args_list
    ]


# ============================================================================
# to_package_path - 형식 정규화
# ============================================================================

def test_object_path_becomes_package_path(unreal_mock):
    """오브젝트 경로의 `.에셋이름`이 떨어져 패키지 경로가 된다 (실측 경로)."""
    assert pathUtils.to_package_path(FAILED_OBJECT_PATH) == FAILED_PACKAGE_PATH


def test_package_path_is_unchanged(unreal_mock):
    """이미 패키지 경로면 그대로 돌려준다 (기존 호출부 무변화 보장)."""
    assert pathUtils.to_package_path(FAILED_PACKAGE_PATH) == FAILED_PACKAGE_PATH


def test_uasset_absolute_path_becomes_package_path(unreal_mock):
    """`.uasset` 절대경로는 Content 경로 변환을 거쳐 패키지 경로가 된다."""
    absolutePath = f"{CONTENT_DIR}/Omni/Characters/Hero/SK_Hero.uasset"

    assert pathUtils.to_package_path(absolutePath) == "/Game/Omni/Characters/Hero/SK_Hero"


def test_backslash_absolute_path_becomes_package_path(unreal_mock):
    """역슬래시 절대경로도 같은 결과를 낸다 (Windows 경로 입력)."""
    absolutePath = r"D:\root\Omni\Content\Omni\Characters\Hero\SK_Hero.uasset"

    assert pathUtils.to_package_path(absolutePath) == "/Game/Omni/Characters/Hero/SK_Hero"


def test_dot_in_folder_name_is_not_cut(unreal_mock):
    """`.`이 폴더 이름에 있으면 자르지 않는다 - 절단은 마지막 세그먼트 한정.

    경로 중간을 자르면 전혀 다른 에셋을 가리키게 되므로, 정규화가
    결함을 새로 만드는 경로다(PRD R2).
    """
    objectPath = "/Game/Omni/v1.2/Char/A_Test.A_Test"

    assert pathUtils.to_package_path(objectPath) == "/Game/Omni/v1.2/Char/A_Test"


def test_dotted_folder_package_path_is_unchanged(unreal_mock):
    """폴더에 `.`이 있고 에셋 쪽엔 없으면 아무것도 자르지 않는다."""
    packagePath = "/Game/Omni/v1.2/Char/A_Test"

    assert pathUtils.to_package_path(packagePath) == packagePath


@pytest.mark.parametrize("emptyValue", ["", None])
def test_empty_input_returns_none(unreal_mock, emptyValue):
    """빈 입력은 None이다 (호출부가 실패로 다룰 수 있어야 한다)."""
    assert pathUtils.to_package_path(emptyValue) is None


def test_unconvertible_absolute_path_returns_none(unreal_mock):
    """Content 디렉토리 밖의 절대경로는 None이다 (조용히 통과시키지 않는다)."""
    assert pathUtils.to_package_path("E:/DevStorage/Anim/A.fbx") is None


# ============================================================================
# 진입점 - 소스 컨트롤에 패키지 경로로 넘어가는가
# ============================================================================

def test_object_path_is_checked_out_as_package_path(unreal_mock):
    """오브젝트 경로를 넣어도 소스 컨트롤에는 패키지 경로로 호출된다.

    이 단정이 결함의 직접 회귀 가드다 - 수정 전에는 오브젝트 경로가 그대로
    넘어가 `False`를 받았고, 연 파일이 0개가 되어 CL이 생성되지 않았다.
    """
    _arrange_checkout(unreal_mock, {})

    result = pathUtils.open_for_source_control_checked([FAILED_OBJECT_PATH])

    assert _checkout_call_paths(unreal_mock) == [FAILED_PACKAGE_PATH]
    assert result["opened"] == [f"C:/ws{FAILED_PACKAGE_PATH}.uasset"]
    assert result["failed"] == []


def test_mixed_path_formats_all_reach_source_control(unreal_mock):
    """오브젝트 경로와 패키지 경로가 섞여 들어와도 전부 열린다.

    임포터는 `imported_object_paths`(오브젝트 경로)와 `get_dirty_deps()`가 주는
    패키지 이름을 **한 리스트로 합쳐** 넘긴다. 실제 입력 형태가 이것이다.
    """
    _arrange_checkout(unreal_mock, {})
    paths = [FAILED_OBJECT_PATH, "/Game/Omni/Characters/Hero/SKEL_Hero"]

    result = pathUtils.open_for_source_control_checked(paths)

    assert _checkout_call_paths(unreal_mock) == [
        FAILED_PACKAGE_PATH,
        "/Game/Omni/Characters/Hero/SKEL_Hero",
    ]
    assert len(result["opened"]) == 2
    assert result["failed"] == []


def test_single_entry_point_normalizes_too(unreal_mock):
    """단일 파일 진입점(`checkout_or_add_file`)도 패키지 경로로 조회한다."""
    unreal_mock.EditorAssetLibrary.does_asset_exist.return_value = True
    unreal_mock.SourceControl.check_out_or_add_file.return_value = True

    assert pathUtils.checkout_or_add_file(FAILED_OBJECT_PATH) is True

    unreal_mock.EditorAssetLibrary.does_asset_exist.assert_called_once_with(
        FAILED_PACKAGE_PATH
    )
    assert _checkout_call_paths(unreal_mock) == [FAILED_PACKAGE_PATH]


def test_unnormalizable_path_is_reported_as_failed(unreal_mock):
    """정규화 불가 경로는 조용히 빠지지 않고 `failed`에 사유와 함께 남는다."""
    result = pathUtils.open_for_source_control_checked(["E:/DevStorage/Anim/A.fbx"])

    assert result["opened"] == []
    assert result["failed"] == [
        {"contentPath": "E:/DevStorage/Anim/A.fbx", "reason": "패키지 경로로 정규화할 수 없음"}
    ]
    unreal_mock.SourceControl.check_out_or_add_file.assert_not_called()


# ============================================================================
# 0.3.4 계약 보존 - 정규화가 실패 보고를 삼키지 않는다
# ============================================================================

def test_real_checkout_failure_still_reported(unreal_mock):
    """반환 `False`(배타 락 등 진짜 실패)는 정규화와 무관하게 `failed`에 남는다.

    정규화가 "실패를 줄이는" 변경이지 "실패를 감추는" 변경이 아님을 못 박는다
    (PRD R1). 이 단정이 없으면 0.3.4가 세운 계약이 조용히 되돌아갈 수 있다.
    """
    unreal_mock.SourceControl.last_error_msg.return_value = (
        "can't add exclusive file already opened"
    )
    _arrange_checkout(unreal_mock, {FAILED_PACKAGE_PATH: False})

    result = pathUtils.open_for_source_control_checked([FAILED_OBJECT_PATH])

    assert result["opened"] == []
    assert len(result["failed"]) == 1
    assert result["failed"][0]["reason"] == "can't add exclusive file already opened"


def test_failed_entry_keeps_original_input_path(unreal_mock):
    """실패 항목의 `contentPath`는 정규화 전 입력 원본이다.

    호출자는 자기가 넘긴 문자열로 대조한다 - 정규화된 경로를 실으면 입력
    목록과 실패 목록을 맞출 수 없다.
    """
    _arrange_checkout(unreal_mock, {FAILED_PACKAGE_PATH: False})

    result = pathUtils.open_for_source_control_checked([FAILED_OBJECT_PATH])

    assert result["failed"][0]["contentPath"] == FAILED_OBJECT_PATH


def test_asset_load_failure_still_reported(unreal_mock):
    """에셋 로드 실패도 기존대로 `failed`로 합류한다 (정규화 뒤에도 유지)."""
    _arrange_checkout(unreal_mock, {})
    unreal_mock.EditorAssetLibrary.load_asset.side_effect = lambda inContentPath: None

    result = pathUtils.open_for_source_control_checked([FAILED_OBJECT_PATH])

    assert result["opened"] == []
    assert result["failed"] == [
        {"contentPath": FAILED_OBJECT_PATH, "reason": "에셋 로드 실패"}
    ]
