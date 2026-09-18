# -*- coding: utf-8 -*-
"""`pyjallib.ue5.importVerdict` Type A - UE5 임포트 결과 판정 진리표.

**이관 이력 (2026-09-18 ExportToolsRefactor Phase 1):** 원 위치는 MeshValidator
`tests/test_import_verdict.py`(17건, 2026-09-17 ImportVerdict 사이클)다. 판정 모듈이
세 툴 공용으로 pyjallib에 승격되면서 테스트도 같이 옮겼다 - **사양 불변**이며,
`importlib`로 툴 파일을 격리 로드하던 방식이 pyjallib 직접 import로 바뀐 것만 다르다.
여기에 애님 툴 두 벌(BatchAnimExporter `test_import_verdict.py`
`test_script_error_marker_overrides_success_json` / NewAnimExporter 동명)이 갖던
stdout 에러 마커 게이트 케이스를 `inScriptErrorDetected` 입력 형태로 더했다.

판정 축은 결과 JSON 단독이고 종료 코드는 진단 정보다(모듈 docstring).
"""

import json
import os
from pathlib import Path

import pytest

from pyjallib.ue5 import importVerdict as _judge

_MESH_UASSET = r"D:\root\Omni\Content\Omni\Char\Mesh\SM_Test.uasset"
_CRASH_RETURN_CODE = 3221225477  # 0xC0000005 - 2026-09-17 실측 종료 코드
_STARTED_AT = 1_000_000.0


def _write_result(inTmpPath, inPayload, inMtime=None):
    """결과 JSON을 쓰고 mtime을 지정한다.

    Args:
        inTmpPath: pytest `tmp_path`.
        inPayload: JSON으로 기록할 딕셔너리.
        inMtime: 설정할 수정 시각(epoch 초). None이면 기본 신선한 값.

    Returns:
        str: 기록한 파일 경로.
    """
    resultPath = Path(inTmpPath) / "importResult.json"
    resultPath.write_text(json.dumps(inPayload), encoding="utf-8")
    mtime = _STARTED_AT + 10.0 if inMtime is None else inMtime
    os.utime(resultPath, (mtime, mtime))
    return str(resultPath)


def _fresh_success_readout(inFailedFiles=None):
    """신선한 성공 readout을 만든다 (순수 판정 함수 단독 검증용)."""
    return _judge.ImportResultReadout(
        exists=True,
        readable=True,
        mtime=_STARTED_AT + 10.0,
        success=True,
        error=None,
        openedFiles=[_MESH_UASSET],
        failedFiles=list(inFailedFiles or []),
    )


# ============================================================================
# 진리표 - stdout 에러 마커 (1순위 게이트, 애님 툴 두 벌에서 흡수)
# ============================================================================

def test_script_error_marker_overrides_fresh_success_json():
    """마커가 검출되면 결과 JSON이 신선한 성공이어도 실패다 (silent 실패 게이트).

    원 위치: BatchAnimExporter/NewAnimExporter `test_script_error_marker_overrides_success_json`.
    애님 툴은 판정 함수 안에서 stdout을 직접 검사했고, 여기서는 검출 결과를 입력으로
    받는다(`headlessRunner.detect_import_script_error`가 검출 담당).
    """
    verdict = _judge.judge_import_outcome(
        0, _fresh_success_readout(), _STARTED_AT, inScriptErrorDetected=True
    )

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_SCRIPT_ERROR
    assert verdict.openedFiles == []
    assert "0" in verdict.detail


def test_script_error_default_is_false_and_does_not_change_verdict():
    """마커 인자를 생략하면(기본 False) 기존 진리표와 같은 판정이다 (하위호환)."""
    verdict = _judge.judge_import_outcome(0, _fresh_success_readout(), _STARTED_AT)

    assert verdict.success is True
    assert verdict.reasonCode == _judge.REASON_OK


# ============================================================================
# 진리표 - 결과 JSON이 없거나 못 읽는 경우 (종료 코드와 무관하게 실패)
# ============================================================================

@pytest.mark.parametrize("returnCode", [0, _CRASH_RETURN_CODE, None])
def test_missing_result_is_failure_regardless_of_return_code(returnCode):
    """결과 JSON이 없으면 종료 코드가 0이어도(또는 기동 실패 None이어도) 실패다."""
    readout = _judge.ImportResultReadout(exists=False, readable=False,
                                         readError="임포트 결과 JSON이 없습니다")

    verdict = _judge.judge_import_outcome(returnCode, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_NO_RESULT
    assert str(returnCode) in verdict.detail


@pytest.mark.parametrize("returnCode", [0, _CRASH_RETURN_CODE])
def test_unreadable_result_is_failure_regardless_of_return_code(returnCode):
    """JSON이 파손됐으면 실패다 - 결과 기록 *도중* 크래시한 경우를 덮는다."""
    readout = _judge.ImportResultReadout(
        exists=True, readable=False, mtime=_STARTED_AT + 10.0,
        readError="임포트 결과 JSON 읽기 실패 (broken.json): ..."
    )

    verdict = _judge.judge_import_outcome(returnCode, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_UNREADABLE
    assert "읽기 실패" in verdict.detail


# ============================================================================
# 진리표 - 신선도 게이트
# ============================================================================

@pytest.mark.parametrize("returnCode", [0, _CRASH_RETURN_CODE])
def test_stale_success_json_is_never_success(returnCode):
    """mtime이 기동 시각보다 이르면 어떤 종료 코드에서도 성공이 아니다.

    실행 전 결과 JSON 삭제는 실패해도 경고만 남기고 진행하므로 보증이 아니다.
    이 게이트가 "낡은 성공을 이번 성공으로 오인"하는 통로를 막는다.
    """
    readout = _judge.ImportResultReadout(
        exists=True, readable=True, mtime=_STARTED_AT - 600.0,
        success=True, openedFiles=[_MESH_UASSET]
    )

    verdict = _judge.judge_import_outcome(returnCode, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_STALE


def test_result_written_exactly_at_start_epoch_is_fresh():
    """기동 시각과 mtime이 같으면 신선한 것으로 본다 (경계값)."""
    readout = _judge.ImportResultReadout(
        exists=True, readable=True, mtime=_STARTED_AT,
        success=True, openedFiles=[_MESH_UASSET]
    )

    verdict = _judge.judge_import_outcome(0, readout, _STARTED_AT)

    assert verdict.success is True


def test_mtime_slightly_before_start_epoch_is_still_fresh():
    """mtime이 기동 시각보다 미세하게 앞서도 신선한 것으로 본다.

    Windows FILETIME → `st_mtime` double 반올림 때문에 방금 쓴 파일의 mtime이
    직전에 찍은 epoch보다 앞설 수 있다(실측: 50회 중 11회). 엄격 비교면 신선한
    결과가 `STALE`로 오판되어 성공을 실패로 판정하는 증상이 다른 통로로 재발한다.
    """
    readout = _judge.ImportResultReadout(
        exists=True, readable=True, mtime=_STARTED_AT - 1e-6,
        success=True, openedFiles=[_MESH_UASSET]
    )

    verdict = _judge.judge_import_outcome(0, readout, _STARTED_AT)

    assert verdict.success is True


def test_tolerance_is_far_below_a_real_run_gap():
    """허용 오차를 넘어선 과거 결과는 여전히 `STALE`이다 (게이트가 무뎌지지 않는다)."""
    justOutside = _STARTED_AT - _judge.FRESHNESS_TOLERANCE_SECONDS - 0.1
    readout = _judge.ImportResultReadout(
        exists=True, readable=True, mtime=justOutside,
        success=True, openedFiles=[_MESH_UASSET]
    )

    verdict = _judge.judge_import_outcome(0, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_STALE


def test_missing_mtime_is_not_success():
    """mtime을 알 수 없으면 신선도를 보증할 수 없으므로 성공으로 보지 않는다."""
    readout = _judge.ImportResultReadout(
        exists=True, readable=True, mtime=None, success=True
    )

    verdict = _judge.judge_import_outcome(0, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_STALE


# ============================================================================
# 진리표 - JSON이 실패를 보고한 경우
# ============================================================================

@pytest.mark.parametrize("returnCode", [0, _CRASH_RETURN_CODE])
def test_json_reporting_failure_is_failure(returnCode):
    """`success: false`면 실패이고 상세에 JSON의 error가 실린다."""
    readout = _judge.ImportResultReadout(
        exists=True, readable=True, mtime=_STARTED_AT + 10.0,
        success=False, error="Texture 3 성공/4 실패"
    )

    verdict = _judge.judge_import_outcome(returnCode, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_IMPORT_FAILED
    assert "Texture 3 성공/4 실패" in verdict.detail


# ============================================================================
# 진리표 - 성공 (종료 코드 0 / ≠0)
# ============================================================================

def test_clean_exit_with_success_json_is_success():
    """종료 코드 0 + 신선한 성공 JSON이면 성공이고 크래시 표시가 없다."""
    verdict = _judge.judge_import_outcome(0, _fresh_success_readout(), _STARTED_AT)

    assert verdict.success is True
    assert verdict.reasonCode == _judge.REASON_OK
    assert verdict.crashedAtExit is False
    assert verdict.openedFiles == [_MESH_UASSET]


def test_crash_at_exit_with_success_json_is_success():
    """**2026-09-17 결함의 직접 회귀 가드** - 종료 코드가 0이 아니어도 성공이다.

    UE5는 전건 임포트하고 결과 JSON까지 쓴 뒤 종료 중 크래시했다(3221225477).
    이 케이스가 실패로 뒤집히면 결함이 재발한 것이다.
    """
    verdict = _judge.judge_import_outcome(
        _CRASH_RETURN_CODE, _fresh_success_readout(), _STARTED_AT
    )

    assert verdict.success is True
    assert verdict.reasonCode == _judge.REASON_OK


def test_crash_at_exit_is_flagged_with_return_code_in_detail():
    """성공이면서 종료 코드가 0이 아니면 `crashedAtExit`이 참이고 상세에 코드가 실린다."""
    verdict = _judge.judge_import_outcome(
        _CRASH_RETURN_CODE, _fresh_success_readout(), _STARTED_AT
    )

    assert verdict.crashedAtExit is True
    assert str(_CRASH_RETURN_CODE) in verdict.detail


def test_failed_files_ride_along_without_flipping_verdict():
    """체크아웃 실패는 판정과 직교한다 - 성공 판정을 뒤집지 않고 그대로 실린다."""
    failedFiles = [{"contentPath": "/Game/Omni/Char/Mesh/SM_Test",
                    "reason": "can't add exclusive file already opened"}]

    verdict = _judge.judge_import_outcome(
        0, _fresh_success_readout(failedFiles), _STARTED_AT
    )

    assert verdict.success is True
    assert verdict.failedFiles == failedFiles


# ============================================================================
# 수집 함수 - 실제 파일 왕복 (판정 진리표와 배선이 맞물리는지)
# ============================================================================

def test_collect_readout_carries_failed_files(tmp_path):
    """결과 JSON의 `failedFiles`를 회수한다."""
    failedFiles = [{"contentPath": "/Game/A", "reason": "exclusive"}]
    resultPath = _write_result(tmp_path, {
        "success": True, "error": None,
        "openedFiles": [_MESH_UASSET], "failedFiles": failedFiles,
    })

    readout = _judge.collect_result_readout(resultPath)

    assert readout.failedFiles == failedFiles


def test_collect_readout_tolerates_legacy_json_without_failed_files(tmp_path):
    """`failedFiles` 키가 없는 구 JSON은 빈 리스트로 회수한다 (하위호환)."""
    resultPath = _write_result(tmp_path, {
        "success": True, "error": None, "openedFiles": [_MESH_UASSET],
    })

    readout = _judge.collect_result_readout(resultPath)

    assert readout.failedFiles == []
    assert readout.openedFiles == [_MESH_UASSET]


def test_collect_readout_records_mtime_for_freshness_gate(tmp_path):
    """회수 시 mtime을 함께 담아 판정이 신선도를 볼 수 있게 한다."""
    resultPath = _write_result(tmp_path, {"success": True, "openedFiles": []},
                               inMtime=_STARTED_AT + 42.0)

    readout = _judge.collect_result_readout(resultPath)

    assert readout.mtime == pytest.approx(_STARTED_AT + 42.0)


def test_collect_readout_accepts_path_object(tmp_path):
    """`Path` 객체도 받는다 - 애님 툴 `read_import_result`는 Path를 넘겼다(호환)."""
    resultPath = _write_result(tmp_path, {"success": True, "openedFiles": [_MESH_UASSET]})

    readout = _judge.collect_result_readout(Path(resultPath))

    assert readout.readable is True
    assert readout.openedFiles == [_MESH_UASSET]


def test_stale_file_on_disk_is_judged_stale_end_to_end(tmp_path):
    """디스크의 낡은 성공 JSON이 수집→판정을 거쳐 `STALE`로 떨어진다."""
    resultPath = _write_result(tmp_path, {"success": True, "openedFiles": [_MESH_UASSET]},
                               inMtime=_STARTED_AT - 600.0)

    readout = _judge.collect_result_readout(resultPath)
    verdict = _judge.judge_import_outcome(0, readout, _STARTED_AT)

    assert verdict.success is False
    assert verdict.reasonCode == _judge.REASON_STALE


def test_missing_file_on_disk_is_recorded_as_absent(tmp_path):
    """없는 파일은 `exists=False`로 기록되고 연 파일은 빈 리스트다.

    원 위치: BatchAnimExporter `test_import_result_handoff.py::test_missing_result_file_is_a_failure`
    / NewAnimExporter `test_move_assets_changelist.py` 동명 - `read_import_result`가
    `(False, [], 사유)`를 돌려주던 것을 readout 형태로 재명세.
    """
    readout = _judge.collect_result_readout(str(Path(tmp_path) / "missing.json"))

    assert readout.exists is False
    assert readout.readable is False
    assert readout.openedFiles == []
    assert "없습니다" in readout.readError


def test_corrupt_file_on_disk_is_recorded_as_unreadable(tmp_path):
    """파손 JSON은 `exists=True, readable=False`로 기록된다.

    원 위치: BatchAnimExporter `test_corrupt_result_file_is_a_failure` / MeshValidator
    `test_ue5_p4_handoff.py::test_result_readout_corrupt_file_is_recorded_as_unreadable`.
    """
    resultPath = Path(tmp_path) / "broken.json"
    resultPath.write_text("{not json", encoding="utf-8")

    readout = _judge.collect_result_readout(str(resultPath))

    assert readout.exists is True
    assert readout.readable is False
    assert readout.openedFiles == []
    assert "읽기 실패" in readout.readError


def test_failed_import_result_propagates_error(tmp_path):
    """`success: false` JSON의 error 문자열이 readout에 그대로 실린다.

    원 위치: BatchAnimExporter `test_failed_import_result_propagates_error`.
    """
    resultPath = _write_result(tmp_path, {
        "success": False, "error": "스켈레톤을 찾을 수 없음", "openedFiles": [],
    })

    readout = _judge.collect_result_readout(resultPath)

    assert readout.readable is True
    assert readout.success is False
    assert readout.error == "스켈레톤을 찾을 수 없음"


def test_non_dict_json_is_unreadable(tmp_path):
    """JSON이 딕셔너리가 아니면 읽기 실패로 처리한다 (형식 방어)."""
    resultPath = Path(tmp_path) / "list.json"
    resultPath.write_text("[1, 2, 3]", encoding="utf-8")

    readout = _judge.collect_result_readout(str(resultPath))

    assert readout.readable is False


# ============================================================================
# 패키지 공개 심볼
# ============================================================================

def test_symbols_are_re_exported_from_ue5_package():
    """`pyjallib.ue5`에서 판정 심볼을 바로 import할 수 있다 (툴 배선 경로)."""
    from pyjallib import ue5

    assert ue5.judge_import_outcome is _judge.judge_import_outcome
    assert ue5.collect_result_readout is _judge.collect_result_readout
    assert ue5.ImportVerdict is _judge.ImportVerdict
    assert ue5.REASON_SCRIPT_ERROR == "SCRIPT_ERROR"
