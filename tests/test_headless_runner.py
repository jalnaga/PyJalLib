# -*- coding: utf-8 -*-
"""`pyjallib.ue5.headlessRunner` Type A - UE5 헤드리스 실행기.

**이관 이력 (2026-09-18 ExportToolsRefactor Phase 1):** 원 위치는 NewAnimExporter
`tests/test_headless_polling.py`(12건) · `tests/test_ue5_import_failure.py`의 마커/디코딩/백업
(11건), BatchAnimExporter `tests/test_import_script_error_detection.py`(실패 stdout 실물
샘플 4건) · `tests/test_headless_polling.py`(11건, NewAnim과 동일 사양)다. 실행기가 세 툴
공용으로 pyjallib에 승격되면서 테스트도 같이 옮겼다 - **사양 불변**이며 달라진 것은:

- `importlib`로 툴 파일을 격리 로드하던 방식 → pyjallib 직접 import
- 상수 이름의 `_` 접두 제거(`_STDOUT_TAIL_SIZE` → `STDOUT_TAIL_SIZE`, 공개 심볼)
- `backup_import_script`가 DevStorage 루트 대신 **백업 디렉토리**를 직접 받는다
  (ORV 경로 규약은 라이브러리가 알 일이 아니다)
- 명령줄 빌더(`build_headless_command`)와 기동 실패 경로(`None` 반환)는 신규 단정

검증 축:
1. 대기 중 `inTickCallback`이 반복 호출되어 UI를 펌프할 수 있는가.
2. stdout을 PIPE 대신 임시 파일로 받아도 하류 판정(디코딩/마커/tail)이 동일한가.
3. 명령줄에 `-abslog`가 **항상** 포함되는가(세 툴 차이의 엄격 통일).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyjallib.ue5 import headlessRunner as _mod

# 2026-07-13 실제 실패 로그의 stdout tail 발췌 (returncode=0 이었음)
_REAL_FAILURE_STDOUT = (
    "을 수 없음: /Game/Omni/Characters/NormalMonster/Grol/MeshB/BaseSkeleton/"
    "SKEL_Grol_BaseSkeleton\n"
    "[2026.07.13-08.26.44:049][  5]LogEditorPythonExecuter: Error: "
    "Python script executed with errors\n"
    "[2026.07.13-08.26.44:079][  7]LogAnalytics: Warning: EventCache payload "
    "exceeded the maximum allowed size\n"
)

# 정상 임포트 시나리오의 stdout 발췌 (에러 마커 없음)
_SUCCESS_STDOUT = (
    "[2026.07.13-08.26.40:000][  5]LogPython: [LegacyAnimationImporter] "
    "스켈레톤 로드됨: SK_Grol_Nm_BaseSkeleton\n"
    "[2026.07.13-08.26.44:000][  7]LogAssetRegistry: Display: Asset registry "
    "cache written\n"
)


class _FakeProcess:
    """subprocess.Popen 대체 페이크.

    poll()이 지정 횟수만큼 None을 돌려준 뒤 returncode를 반환한다.
    """

    def __init__(self, inPollNoneCount: int, inReturncode: int):
        self._pollNoneCount = inPollNoneCount
        self._returncode = inReturncode
        self.returncode = None
        self.pollCallCount = 0

    def poll(self):
        """지정 횟수 동안 None(실행 중), 이후 returncode를 반환한다."""
        self.pollCallCount += 1
        if self.pollCallCount <= self._pollNoneCount:
            return None
        self.returncode = self._returncode
        return self._returncode


def _install_fake_popen(
    monkeypatch, inPollNoneCount: int, inReturncode: int, inPayload: bytes
):
    """headlessRunner의 subprocess.Popen을 페이크로 교체하고 인자 기록을 반환한다.

    Args:
        monkeypatch: pytest monkeypatch fixture
        inPollNoneCount: poll()이 None을 반환할 횟수 (= 대기 바퀴 수)
        inReturncode: 최종 returncode
        inPayload: stdout 파일에 쓸 바이트

    Returns:
        dict: Popen 호출 시 전달된 인자 기록
    """
    recorded = {}

    def _fakePopen(inCmd, **kwargs):
        recorded["cmd"] = inCmd
        recorded["kwargs"] = kwargs
        # 실제 자식이 그러하듯, 넘겨받은 파일 객체에 stdout을 쓴다
        kwargs["stdout"].write(inPayload)
        kwargs["stdout"].flush()
        return _FakeProcess(inPollNoneCount, inReturncode)

    monkeypatch.setattr(_mod.subprocess, "Popen", _fakePopen)
    # 폴링 대기가 테스트를 느리게 하지 않도록 sleep을 제거한다
    monkeypatch.setattr(_mod.time, "sleep", lambda _s: None)
    return recorded


@pytest.fixture()
def quiet_logger():
    """실행기가 파일 로그를 만들지 않도록 주입할 mock 로거."""
    return MagicMock()


# ============================================================================
# ① 폴링 루프가 대기 중 tickCallback을 반복 호출한다
# ============================================================================

class TestTickCallbackPump:
    """대기 중 UI 펌프 콜백 호출 검증."""

    def test_tick_callback_called_while_process_running(self, tmp_path, monkeypatch, quiet_logger):
        """poll()이 None인 동안 tickCallback이 매 바퀴 호출되어야 한다."""
        _install_fake_popen(monkeypatch, 5, 0, b"x")
        tickCount = {"n": 0}

        _mod.run_headless_with_pump(
            ["fake.exe"],
            tmp_path / "stdout.log",
            lambda: tickCount.__setitem__("n", tickCount["n"] + 1),
            quiet_logger,
        )

        assert tickCount["n"] == 5

    def test_no_tick_when_process_ends_immediately(self, tmp_path, monkeypatch, quiet_logger):
        """프로세스가 즉시 끝나면 tickCallback은 호출되지 않아야 한다."""
        _install_fake_popen(monkeypatch, 0, 0, b"x")
        tickCount = {"n": 0}

        _mod.run_headless_with_pump(
            ["fake.exe"],
            tmp_path / "stdout.log",
            lambda: tickCount.__setitem__("n", tickCount["n"] + 1),
            quiet_logger,
        )

        assert tickCount["n"] == 0

    def test_tick_exception_does_not_abort_wait(self, tmp_path, monkeypatch, quiet_logger):
        """tickCallback이 예외를 던져도 대기가 끝까지 진행되어야 한다.

        진행 표시는 부가 기능이고 임포트 완주가 본체다.
        """
        _install_fake_popen(monkeypatch, 3, 0, b"ok")

        def _raisingTick():
            raise RuntimeError("펌프 실패")

        returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", _raisingTick, quiet_logger
        )

        assert returncode == 0
        assert stdoutBytes == b"ok"
        assert quiet_logger.warning.called


# ============================================================================
# ② 파일로 받은 stdout이 기존 판정 로직과 동일한 결과를 낸다
# ============================================================================

class TestStdoutCaptureEquivalence:
    """PIPE -> 파일 전환 후 하류 판정 로직 불변 검증."""

    def test_stdout_bytes_round_trip_through_file(self, tmp_path, monkeypatch, quiet_logger):
        """파일에 쓴 stdout이 손실 없이 그대로 회수되어야 한다."""
        payload = "정상 임포트 로그 라인\n".encode("utf-8") * 100
        _install_fake_popen(monkeypatch, 2, 0, payload)

        returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", None, quiet_logger
        )

        assert returncode == 0
        assert stdoutBytes == payload

    def test_error_marker_detected_from_file_captured_stdout(
        self, tmp_path, monkeypatch, quiet_logger
    ):
        """파일로 받은 stdout에서도 silent 실패 마커가 감지되어야 한다.

        returncode=0 + 에러 마커 조합이 silent 실패의 지문이므로, 캡처
        경로를 바꾼 뒤에도 이 판정이 유지되어야 한다.
        """
        _install_fake_popen(monkeypatch, 1, 0, _REAL_FAILURE_STDOUT.encode("utf-8"))

        returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", None, quiet_logger
        )
        stdoutText = _mod.decode_process_stdout(stdoutBytes)

        assert returncode == 0
        assert _mod.detect_import_script_error(stdoutText) is True

    def test_cp949_stdout_decodes_through_fallback(self, tmp_path, monkeypatch, quiet_logger):
        """utf-8로 못 읽는 바이트도 decode_process_stdout 폴백을 탄다."""
        _install_fake_popen(monkeypatch, 1, 0, "한글 로그".encode("cp949"))

        _returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", None, quiet_logger
        )

        assert _mod.decode_process_stdout(stdoutBytes) == "한글 로그"

    def test_tail_available_from_large_stdout(self, tmp_path, monkeypatch, quiet_logger):
        """대용량 stdout에서도 마지막 ~2KB tail을 얻을 수 있어야 한다.

        파이프 버퍼(약 64KB)를 넘기는 크기를 실제로 통과시켜, 파일
        리다이렉트가 PIPE 데드락 없이 전량을 회수하는지 함께 확인한다.
        """
        payload = (b"A" * 100_000) + _REAL_FAILURE_STDOUT.encode("utf-8")
        _install_fake_popen(monkeypatch, 1, 0, payload)

        _returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", None, quiet_logger
        )
        stdoutText = _mod.decode_process_stdout(stdoutBytes)
        tail = _mod.stdout_tail(stdoutText)

        assert len(stdoutBytes) > 64 * 1024
        assert len(tail) == _mod.STDOUT_TAIL_SIZE
        assert _mod.detect_import_script_error(stdoutText) is True
        assert "LogEditorPythonExecuter: Error" in tail

    def test_nonzero_returncode_propagated(self, tmp_path, monkeypatch, quiet_logger):
        """0이 아닌 returncode가 그대로 전달되어야 한다."""
        _install_fake_popen(monkeypatch, 2, 3, b"")

        returncode, _stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", None, quiet_logger
        )

        assert returncode == 3

    def test_stdout_redirected_to_file_not_pipe(self, tmp_path, monkeypatch, quiet_logger):
        """Popen에 PIPE가 아니라 파일 객체가 stdout으로 전달되어야 한다.

        PIPE + 폴링 조합은 버퍼가 차면 자식이 블로킹해 영영 끝나지 않는다.
        이 회귀를 막는 가드다.
        """
        recorded = _install_fake_popen(monkeypatch, 1, 0, b"x")

        _mod.run_headless_with_pump(["fake.exe"], tmp_path / "stdout.log", None, quiet_logger)

        assert recorded["kwargs"]["stdout"] is not subprocess.PIPE
        assert hasattr(recorded["kwargs"]["stdout"], "write")
        assert recorded["kwargs"]["stderr"] == subprocess.STDOUT
        assert recorded["cmd"] == ["fake.exe"]


# ============================================================================
# ③ 하위호환 · 기동 실패
# ============================================================================

class TestBackwardCompatibilityAndLaunchFailure:
    """콜백/로거 미지정 시 동작 유지 + 프로세스를 띄우지 못한 경우."""

    def test_none_tick_callback_is_backward_compatible(self, tmp_path, monkeypatch, quiet_logger):
        """tickCallback을 생략해도 예외 없이 동작해야 한다."""
        _install_fake_popen(monkeypatch, 4, 0, b"payload")

        returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", inLogger=quiet_logger
        )

        assert returncode == 0
        assert stdoutBytes == b"payload"

    def test_none_logger_falls_back_to_module_logger(self, tmp_path, monkeypatch):
        """logger를 생략하면 모듈 지연 Logger를 쓰고 예외 없이 동작해야 한다.

        모듈 Logger가 실제 파일을 만들지 않도록 `_get_logger`를 mock으로 대체한다.
        """
        _install_fake_popen(monkeypatch, 2, 0, b"payload")
        fakeLogger = MagicMock()
        monkeypatch.setattr(_mod, "_get_logger", lambda: fakeLogger)

        returncode, _stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], tmp_path / "stdout.log", None, None
        )

        assert returncode == 0
        assert fakeLogger.info.called

    def test_stdout_parent_directory_created(self, tmp_path, monkeypatch, quiet_logger):
        """stdout 임시 파일의 상위 디렉토리가 없으면 생성되어야 한다."""
        _install_fake_popen(monkeypatch, 1, 0, b"x")
        stdoutPath = tmp_path / "nested" / "deeper" / "stdout.log"

        _mod.run_headless_with_pump(["fake.exe"], stdoutPath, None, quiet_logger)

        assert stdoutPath.exists()

    def test_string_stdout_path_is_accepted(self, tmp_path, monkeypatch, quiet_logger):
        """stdout 경로를 문자열로 줘도 동작한다 (MeshValidator는 str 경로를 쓴다)."""
        _install_fake_popen(monkeypatch, 1, 0, b"x")

        returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["fake.exe"], str(tmp_path / "stdout.log"), None, quiet_logger
        )

        assert returncode == 0
        assert stdoutBytes == b"x"

    def test_launch_failure_returns_none_returncode(self, tmp_path, monkeypatch, quiet_logger):
        """Popen 자체가 실패하면 (None, b'')를 돌려준다 - MeshValidator 규약.

        "실행 실패"와 "실행했고 코드가 0"을 구분해야 판정이 종료 코드를 진단
        정보로 쓸 수 있다.
        """
        def _failingPopen(inCmd, **kwargs):
            raise FileNotFoundError("UnrealEditor.exe 없음")

        monkeypatch.setattr(_mod.subprocess, "Popen", _failingPopen)

        returncode, stdoutBytes = _mod.run_headless_with_pump(
            ["missing.exe"], tmp_path / "stdout.log", None, quiet_logger
        )

        assert returncode is None
        assert stdoutBytes == b""
        assert quiet_logger.error.called


# ============================================================================
# ④ detect_import_script_error (BatchAnim 실물 샘플 + NewAnim 경계)
# ============================================================================

class TestDetectImportScriptError:
    """stdout 에러 마커 감지 검증."""

    def test_detects_error_marker_in_real_failure_stdout(self):
        """실제 실패 로그 샘플에서 에러 마커를 감지한다."""
        assert _mod.detect_import_script_error(_REAL_FAILURE_STDOUT) is True

    def test_no_error_on_success_stdout(self):
        """정상 임포트 stdout에서는 실패로 판정하지 않는다."""
        assert _mod.detect_import_script_error(_SUCCESS_STDOUT) is False

    def test_empty_and_none_return_false(self):
        """빈 문자열/None은 실패로 판정하지 않는다 (마커 부재)."""
        assert _mod.detect_import_script_error("") is False
        assert _mod.detect_import_script_error(None) is False

    def test_marker_without_surrounding_context(self):
        """마커 단독 출현도 감지한다 (위치/포맷 비의존)."""
        assert _mod.detect_import_script_error(
            "LogEditorPythonExecuter: Error: Python script executed with errors"
        ) is True

    def test_marker_constant_is_the_ue5_python_executer_error_prefix(self):
        """마커 상수가 UE5 파이썬 실행기의 에러 접두와 같다 (판정 모듈과 공유되는 계약)."""
        assert _mod.IMPORT_SCRIPT_ERROR_MARKER == "LogEditorPythonExecuter: Error"


# ============================================================================
# ⑤ decode_process_stdout
# ============================================================================

class TestDecodeProcessStdout:
    """stdout 바이트 디코딩 폴백 검증."""

    def test_empty_bytes_returns_empty(self):
        """빈 바이트면 빈 문자열을 반환해야 한다."""
        assert _mod.decode_process_stdout(b"") == ""

    def test_utf8_decoded(self):
        """utf-8 바이트는 그대로 디코딩되어야 한다."""
        assert _mod.decode_process_stdout("로그".encode("utf-8")) == "로그"

    def test_cp949_fallback(self):
        """utf-8 실패 시 cp949로 폴백해야 한다."""
        assert _mod.decode_process_stdout("한글".encode("cp949")) == "한글"

    def test_invalid_bytes_replaced(self):
        """모든 디코딩 실패 시 errors='replace'로 문자열을 반환해야 한다."""
        result = _mod.decode_process_stdout(b"\xff\xfe\xff")
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# ⑥ backup_import_script (2단 백업)
# ============================================================================

class TestBackupImportScript:
    """임포트 스크립트 백업 검증."""

    def _make_script(self, inTmpPath: Path) -> Path:
        """백업 대상 스크립트 파일을 생성한다."""
        scriptPath = inTmpPath / "animImportScript.py"
        scriptPath.write_text("print('import')", encoding="utf-8")
        return scriptPath

    def test_last_backup_created_in_given_directory(self, tmp_path):
        """성공 실행 후 _last_ 백업이 지정 디렉토리에 원본 stem 기반 이름으로 생성된다."""
        scriptPath = self._make_script(tmp_path)
        backupDir = tmp_path / "backup" / "Temp"

        backupPath = _mod.backup_import_script(scriptPath, backupDir, inIsFailed=False)

        assert backupPath is not None
        assert backupPath.exists()
        assert backupPath.parent == backupDir
        assert backupPath.name.startswith("animImportScript_last_")
        assert backupPath.suffix == ".py"
        assert backupPath.read_text(encoding="utf-8") == "print('import')"

    def test_failed_backup_created(self, tmp_path):
        """실패 시 _failed_ 백업이 생성되어야 한다."""
        scriptPath = self._make_script(tmp_path)

        backupPath = _mod.backup_import_script(scriptPath, tmp_path / "backup", inIsFailed=True)

        assert backupPath is not None
        assert "_failed_" in backupPath.name

    def test_default_is_last_backup(self, tmp_path):
        """`inIsFailed`를 생략하면 `_last_` 백업이다."""
        scriptPath = self._make_script(tmp_path)

        backupPath = _mod.backup_import_script(scriptPath, tmp_path / "backup")

        assert "_last_" in backupPath.name

    def test_missing_source_returns_none(self, tmp_path):
        """원본 스크립트가 없으면 None을 반환해야 한다."""
        backupPath = _mod.backup_import_script(
            tmp_path / "missing.py", tmp_path / "backup", inIsFailed=False
        )
        assert backupPath is None

    def test_string_paths_are_accepted(self, tmp_path):
        """경로를 문자열로 줘도 동작한다."""
        scriptPath = self._make_script(tmp_path)

        backupPath = _mod.backup_import_script(str(scriptPath), str(tmp_path / "backup"))

        assert backupPath is not None
        assert backupPath.exists()


# ============================================================================
# ⑦ build_headless_command - 플래그 9종, -abslog 항상
# ============================================================================

class TestBuildHeadlessCommand:
    """명령줄 빌더 검증(순수 함수)."""

    _EDITOR = r"E:\UE\Engine\Binaries\Win64\UnrealEditor.exe"
    _PROJECT = r"E:\Omni\Omni.uproject"
    _SCRIPT = r"E:\DevStorage_root\DevStorage\Temp\animImportScript.py"
    _LOG = r"E:\DevStorage_root\DevStorage\Temp\ue5_import.log"

    def test_editor_and_project_lead_the_command(self):
        """실행 파일과 프로젝트가 앞 두 인자다."""
        cmd = _mod.build_headless_command(self._EDITOR, self._PROJECT, self._SCRIPT, self._LOG)

        assert cmd[0] == self._EDITOR
        assert cmd[1] == self._PROJECT

    def test_script_and_abslog_are_embedded(self):
        """`-ExecutePythonScript`와 `-abslog`에 경로가 그대로 실린다."""
        cmd = _mod.build_headless_command(self._EDITOR, self._PROJECT, self._SCRIPT, self._LOG)

        assert f"-ExecutePythonScript={self._SCRIPT}" in cmd
        assert f"-abslog={self._LOG}" in cmd

    def test_abslog_is_always_present(self):
        """`-abslog`는 선택이 아니다 - 세 툴 중 BatchAnimExporter만 빠져 있던 차이를 엄격한 쪽으로 통일."""
        cmd = _mod.build_headless_command("e", "p", "s", "l")

        assert any(arg.startswith("-abslog=") for arg in cmd)

    def test_nine_flags_from_headless_execution_reference(self):
        """`ue5/headless_execution.md` 규약 플래그 9종이 전부 있고 그 외는 없다."""
        cmd = _mod.build_headless_command(self._EDITOR, self._PROJECT, self._SCRIPT, self._LOG)
        flags = cmd[2:]

        assert len(flags) == 9
        expectedFixed = {
            "-stdout", "-unattended", "-nopause", "-nosplash",
            "-NOSOUND", "-nullrhi", "-RenderOffScreen",
        }
        assert expectedFixed.issubset(set(flags))
        assert set(_mod.HEADLESS_FLAGS) == expectedFixed

    def test_path_objects_are_accepted(self):
        """스크립트·로그 경로에 Path를 줘도 문자열로 실린다."""
        cmd = _mod.build_headless_command(
            self._EDITOR, self._PROJECT, Path(self._SCRIPT), Path(self._LOG)
        )

        assert all(isinstance(arg, str) for arg in cmd)
        assert f"-ExecutePythonScript={self._SCRIPT}" in cmd


# ============================================================================
# 패키지 공개 심볼
# ============================================================================

def test_symbols_are_re_exported_from_ue5_package():
    """`pyjallib.ue5`에서 실행기 심볼을 바로 import할 수 있다 (툴 배선 경로)."""
    from pyjallib import ue5

    assert ue5.run_headless_with_pump is _mod.run_headless_with_pump
    assert ue5.build_headless_command is _mod.build_headless_command
    assert ue5.detect_import_script_error is _mod.detect_import_script_error
    assert ue5.backup_import_script is _mod.backup_import_script
