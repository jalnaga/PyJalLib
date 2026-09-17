# -*- coding: utf-8 -*-
"""`pathUtils`의 체크아웃 성공/실패 갈라 보고 Type A 단위 테스트.

2026-09-17 실측: UE5 안에서 `p4 add` 8건이 전부 배타 락으로 실패했는데
`open_for_source_control()`이 8건 모두를 "연 파일"로 보고했다. 그 목록이
에디터 밖 `p4 reopen`의 입력이라, 열리지 않은 파일을 옮기려다 부분 실패가
난다. 원인은 `unreal.SourceControl.check_out_or_add_file()`의 **bool 반환을
받지 않은 것**이다(엔진 `SourceControlHelpers.h`: "true if succeeded, false
if failed and can call LastErrorMsg()").

여기서 단정하는 것:
    1. 전건 성공 / 전건 실패 / 혼재 입력에서 `opened`·`failed`가 정확히 갈린다
    2. 실패 사유가 `last_error_msg()` 값으로 실린다
    3. 에셋 로드 실패·시스템 경로 해석 실패도 같은 `failed`로 합류한다
       (지금까지는 경고만 남기고 목록에서 조용히 사라졌다)
    4. 하위호환 - `open_for_source_control`은 여전히 `list[str]`이고 성공분만 담는다

테스트 격리:
    `tests/ue5/conftest.py`가 `unreal`을 MagicMock으로 주입한다. 각 테스트는
    그 mock의 반환값을 케이스별로 재설정하고 fixture가 원복한다.
"""

import sys
from unittest.mock import MagicMock

import pytest

from pyjallib.ue5.inUnreal import pathUtils


# ============================================================================
# 공통 fixture
# ============================================================================

@pytest.fixture()
def unreal_mock():
    """`pathUtils`가 보는 `unreal`을 이 테스트 전용 mock으로 갈아 끼운다.

    conftest가 주입한 전역 mock을 테스트끼리 공유하면 호출 기록이 누적되어
    단정이 서로 오염된다. 매 테스트마다 새 mock을 넣고 원복한다.

    Yields:
        MagicMock: `pathUtils.unreal`로 주입된 mock.
    """
    savedModule = sys.modules.get("unreal")
    savedAttr = pathUtils.unreal

    freshMock = MagicMock()
    freshMock.SourceControl.last_error_msg.return_value = "테스트 기본 사유"
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


def _arrange_checkout(inUnrealMock, inCheckoutResults, inSystemPathByAsset=None):
    """체크아웃 반환값과 시스템 경로 해석을 경로별로 배선한다.

    Args:
        inUnrealMock: `unreal_mock` fixture 값.
        inCheckoutResults: Content 경로 -> `check_out_or_add_file` 반환값(bool).
        inSystemPathByAsset: 로드된 에셋 객체 -> 절대경로. None이면
            Content 경로에서 기계적으로 만든 경로를 쓴다.

    Returns:
        None
    """
    def _checkOut(inContentPath, silent=False):
        return inCheckoutResults.get(inContentPath, True)

    inUnrealMock.SourceControl.check_out_or_add_file.side_effect = _checkOut

    def _loadAsset(inContentPath):
        return f"asset:{inContentPath}"

    inUnrealMock.EditorAssetLibrary.load_asset.side_effect = _loadAsset

    def _systemPath(inAssetObj):
        if inSystemPathByAsset is not None:
            return inSystemPathByAsset.get(inAssetObj, "")
        contentPath = str(inAssetObj).replace("asset:", "")
        return f"C:/ws{contentPath}.uasset"

    inUnrealMock.SystemLibrary.get_system_path.side_effect = _systemPath


# ============================================================================
# 체크아웃 성공/실패 분리
# ============================================================================

def test_all_checkouts_succeed_fills_opened_only(unreal_mock):
    """전건 성공이면 `opened`에 전부 들어가고 `failed`는 비어 있다."""
    paths = ["/Game/A", "/Game/B"]
    _arrange_checkout(unreal_mock, {})

    result = pathUtils.open_for_source_control_checked(paths)

    assert result["opened"] == ["C:/ws/Game/A.uasset", "C:/ws/Game/B.uasset"]
    assert result["failed"] == []


def test_all_checkouts_fail_fills_failed_only(unreal_mock):
    """전건 실패면 `opened`가 비고 실패 경로가 전부 `failed`에 담긴다.

    2026-09-17 실측 사고의 직접 회귀 가드다 - 이 조건에서 예전 구현은
    8건 모두를 "연 파일"로 보고했다.
    """
    paths = ["/Game/A", "/Game/B"]
    unreal_mock.SourceControl.last_error_msg.return_value = (
        "can't add exclusive file already opened"
    )
    _arrange_checkout(unreal_mock, {"/Game/A": False, "/Game/B": False})

    result = pathUtils.open_for_source_control_checked(paths)

    assert result["opened"] == []
    assert [entry["contentPath"] for entry in result["failed"]] == ["/Game/A", "/Game/B"]


def test_mixed_checkout_splits_lists_exactly(unreal_mock):
    """성공·실패가 섞이면 두 목록이 서로소로 정확히 갈리고 순서를 보존한다."""
    paths = ["/Game/A", "/Game/B", "/Game/C"]
    _arrange_checkout(unreal_mock, {"/Game/B": False})

    result = pathUtils.open_for_source_control_checked(paths)

    assert result["opened"] == ["C:/ws/Game/A.uasset", "C:/ws/Game/C.uasset"]
    assert [entry["contentPath"] for entry in result["failed"]] == ["/Game/B"]


def test_failure_reason_comes_from_last_error_msg(unreal_mock):
    """실패 사유는 `last_error_msg()`의 값으로 실린다 (개수만 남기지 않는다)."""
    unreal_mock.SourceControl.last_error_msg.return_value = (
        "also opened by Dev@Dev_kimwoong_omni"
    )
    _arrange_checkout(unreal_mock, {"/Game/A": False})

    result = pathUtils.open_for_source_control_checked(["/Game/A"])

    assert result["failed"][0]["reason"] == "also opened by Dev@Dev_kimwoong_omni"


def test_failure_reason_survives_last_error_msg_raising(unreal_mock):
    """사유 조회가 터져도 실패 사실은 보고된다 (보고 경로가 사유에 종속되지 않는다)."""
    unreal_mock.SourceControl.last_error_msg.side_effect = RuntimeError("노출 없음")
    _arrange_checkout(unreal_mock, {"/Game/A": False})

    result = pathUtils.open_for_source_control_checked(["/Game/A"])

    assert result["opened"] == []
    assert result["failed"][0]["contentPath"] == "/Game/A"
    assert "조회 불가" in result["failed"][0]["reason"]


# ============================================================================
# 로드 실패·경로 해석 실패의 합류
# ============================================================================

def test_asset_load_failure_joins_failed_list(unreal_mock):
    """에셋 로드 실패는 경고로 사라지지 않고 `failed`에 합류한다."""
    _arrange_checkout(unreal_mock, {})
    unreal_mock.EditorAssetLibrary.load_asset.side_effect = (
        lambda inContentPath: None if inContentPath == "/Game/B" else f"asset:{inContentPath}"
    )

    result = pathUtils.open_for_source_control_checked(["/Game/A", "/Game/B"])

    assert result["opened"] == ["C:/ws/Game/A.uasset"]
    assert result["failed"] == [{"contentPath": "/Game/B", "reason": "에셋 로드 실패"}]


def test_system_path_failure_joins_failed_list(unreal_mock):
    """시스템 경로 해석 실패도 `failed`에 합류한다."""
    _arrange_checkout(
        unreal_mock, {}, inSystemPathByAsset={"asset:/Game/A": "C:/ws/Game/A.uasset",
                                              "asset:/Game/B": ""}
    )

    result = pathUtils.open_for_source_control_checked(["/Game/A", "/Game/B"])

    assert result["opened"] == ["C:/ws/Game/A.uasset"]
    assert result["failed"] == [{"contentPath": "/Game/B", "reason": "시스템 경로 해석 실패"}]


def test_empty_input_returns_both_lists_empty(unreal_mock):
    """빈 입력에서도 두 키가 항상 존재한다 (호출부가 `.get` 없이 쓸 수 있다)."""
    _arrange_checkout(unreal_mock, {})

    result = pathUtils.open_for_source_control_checked([])

    assert result == {"opened": [], "failed": []}


# ============================================================================
# 하위호환 - 기존 래퍼 (1.8)
# ============================================================================

def test_legacy_wrapper_still_returns_flat_list(unreal_mock):
    """`open_for_source_control`은 여전히 `list[str]`을 돌려준다 (시그니처 불변)."""
    _arrange_checkout(unreal_mock, {})

    opened = pathUtils.open_for_source_control(["/Game/A", "/Game/B"])

    assert isinstance(opened, list)
    assert all(isinstance(item, str) for item in opened)
    assert opened == ["C:/ws/Game/A.uasset", "C:/ws/Game/B.uasset"]


def test_legacy_wrapper_drops_failed_paths(unreal_mock):
    """래퍼 결과에는 체크아웃 실패분이 담기지 않는다 (더 정확해지는 방향의 변경)."""
    _arrange_checkout(unreal_mock, {"/Game/B": False})

    opened = pathUtils.open_for_source_control(["/Game/A", "/Game/B"])

    assert opened == ["C:/ws/Game/A.uasset"]
