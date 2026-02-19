#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
testKit 서브패키지 단위 테스트 (Type A - Console/pytest).

TestReporter, TestLogAnalyzer, TestRunner, MaxTestRunner 각각의 기능을 검증한다.
MaxTestRunner는 3ds Max 설치 없이 명령줄 조합만 테스트한다.
"""

import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ============================================================
# Task 11: TestReporter 단위 테스트
# ============================================================


class TestTestReporter:
    """TestReporter 클래스의 단위 테스트."""

    def test_init_creates_log_file(self, tmp_path: Path) -> None:
        """인스턴스 생성 시 로그 파일이 생성되고 TEST START 마커가 기록된다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("SampleSuite", tmp_path)

        assert reporter.log_path.exists()
        content = reporter.log_path.read_text(encoding="utf-8")
        assert "=== TEST START: SampleSuite ===" in content

    def test_init_custom_filename(self, tmp_path: Path) -> None:
        """사용자 지정 로그 파일명이 정상 적용된다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path, inLogFilename="custom.log")

        assert reporter.log_path.name == "custom.log"
        assert reporter.log_path.exists()

    def test_init_default_filename(self, tmp_path: Path) -> None:
        """로그 파일명을 지정하지 않으면 자동 생성된다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("MyTest", tmp_path)

        assert reporter.log_path.name == "test_MyTest.log"

    def test_init_creates_log_dir(self, tmp_path: Path) -> None:
        """존재하지 않는 로그 디렉토리를 자동 생성한다."""
        from pyjallib.testKit import TestReporter

        logDir = tmp_path / "nested" / "dir"
        reporter = TestReporter("Suite", logDir)

        assert logDir.exists()
        assert reporter.log_path.exists()

    def test_assert_test_success(self, tmp_path: Path) -> None:
        """assert_test(True)는 SUCCESS를 기록하고 passed를 증가시킨다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(True, "TC01 테스트")

        assert reporter.passed == 1
        assert reporter.failed == 0
        content = reporter.log_path.read_text(encoding="utf-8")
        assert "SUCCESS: TC01 테스트" in content

    def test_assert_test_failure(self, tmp_path: Path) -> None:
        """assert_test(False)는 FAIL을 기록하고 failed를 증가시킨다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(False, "TC02 실패 테스트", "기대값: True, 실제: False")

        assert reporter.passed == 0
        assert reporter.failed == 1
        content = reporter.log_path.read_text(encoding="utf-8")
        assert "FAIL: TC02 실패 테스트 - 기대값: True, 실제: False" in content

    def test_assert_test_failure_without_detail(self, tmp_path: Path) -> None:
        """assert_test(False)에 detail이 없으면 테스트 이름만 기록한다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(False, "TC03 실패")

        content = reporter.log_path.read_text(encoding="utf-8")
        assert "FAIL: TC03 실패" in content
        # detail이 없으므로 " - " 패턴이 FAIL 라인에 없어야 함
        for line in content.splitlines():
            if "FAIL: TC03 실패" in line:
                assert " - " not in line.split("FAIL: TC03 실패")[1]

    def test_error_method(self, tmp_path: Path) -> None:
        """error 메서드는 ERROR를 기록하고 failed를 증가시킨다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.error("TC04 에러 테스트", "ZeroDivisionError 발생")

        assert reporter.failed == 1
        content = reporter.log_path.read_text(encoding="utf-8")
        assert "ERROR: TC04 에러 테스트 - ZeroDivisionError 발생" in content

    def test_counters_accumulate(self, tmp_path: Path) -> None:
        """여러 assert_test/error 호출 시 카운터가 누적된다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(True, "pass1")
        reporter.assert_test(True, "pass2")
        reporter.assert_test(False, "fail1")
        reporter.error("err1", "error msg")

        assert reporter.passed == 2
        assert reporter.failed == 2
        assert reporter.total == 4

    def test_summary(self, tmp_path: Path) -> None:
        """summary는 TEST END 마커를 기록하고 올바른 튜플을 반환한다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(True, "pass1")
        reporter.assert_test(True, "pass2")
        reporter.assert_test(False, "fail1")

        result = reporter.summary()

        assert result == (2, 1, 3)
        content = reporter.log_path.read_text(encoding="utf-8")
        assert "=== TEST END: 2/3 passed, 1 failed ===" in content

    def test_summary_all_pass(self, tmp_path: Path) -> None:
        """모든 테스트 통과 시 summary 포맷이 정확하다."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(True, "pass1")
        reporter.assert_test(True, "pass2")

        result = reporter.summary()

        assert result == (2, 0, 2)
        content = reporter.log_path.read_text(encoding="utf-8")
        assert "=== TEST END: 2/2 passed, 0 failed ===" in content

    def test_log_format(self, tmp_path: Path) -> None:
        """로그 포맷이 '%(asctime)s [%(levelname)s] %(message)s' 패턴을 따른다."""
        import re

        from pyjallib.testKit import TestReporter

        reporter = TestReporter("Suite", tmp_path)
        reporter.assert_test(True, "format_test")

        content = reporter.log_path.read_text(encoding="utf-8")
        # 타임스탬프 + [LEVEL] + 메시지 패턴 확인
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ \[(INFO|ERROR)\] .+"
        lines = [line for line in content.splitlines() if line.strip()]
        for line in lines:
            assert re.match(pattern, line), f"포맷 불일치: {line}"

    def test_close_removes_handlers(self, tmp_path: Path) -> None:
        """close() 호출 후 로거 핸들러가 모두 제거된다."""
        import logging

        from pyjallib.testKit import TestReporter

        reporter = TestReporter("CloseTest", tmp_path)
        loggerName = "pyjallib.testKit.CloseTest"
        logger = logging.getLogger(loggerName)

        assert len(logger.handlers) > 0
        reporter.close()
        assert len(logger.handlers) == 0

    def test_close_allows_file_access(self, tmp_path: Path) -> None:
        """close() 호출 후 로그 파일에 다른 쓰기가 가능하다 (핸들러 해제 확인)."""
        from pyjallib.testKit import TestReporter

        reporter = TestReporter("CloseAccess", tmp_path)
        reporter.assert_test(True, "TC01")
        reporter.close()

        # 파일이 열려있지 않으므로 쓰기 가능
        logPath = reporter.log_path
        logPath.write_text("overwritten", encoding="utf-8")
        assert logPath.read_text(encoding="utf-8") == "overwritten"


# ============================================================
# Task 12: TestLogAnalyzer 단위 테스트
# ============================================================


class TestTestLogAnalyzer:
    """TestLogAnalyzer 클래스의 단위 테스트."""

    def _create_sample_log(self, inPath: Path, inContent: str) -> Path:
        """테스트용 샘플 로그 파일을 생성한다.

        Args:
            inPath: 로그 파일 경로
            inContent: 로그 내용

        Returns:
            생성된 로그 파일 경로
        """
        inPath.write_text(textwrap.dedent(inContent), encoding="utf-8")
        return inPath

    def test_analyze_normal_log(self, tmp_path: Path) -> None:
        """정상 로그 파일에서 카운터가 정확히 파싱된다."""
        from pyjallib.testKit import TestLogAnalyzer

        logPath = self._create_sample_log(
            tmp_path / "test.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: SampleSuite ===
            2026-02-19 10:00:01,000 [INFO] SUCCESS: TC01 인스턴스 생성
            2026-02-19 10:00:02,000 [INFO] SUCCESS: TC02 메서드 호출
            2026-02-19 10:00:03,000 [ERROR] FAIL: TC03 검증 실패 - 기대값 불일치
            2026-02-19 10:00:04,000 [INFO] === TEST END: 2/3 passed, 1 failed ===
            """,
        )

        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(logPath)

        assert result.passed == 2
        assert result.failed == 1
        assert result.errors == 0
        assert result.total == 3
        assert result.completed is True
        assert len(result.failures) == 1

    def test_analyze_with_errors(self, tmp_path: Path) -> None:
        """ERROR 패턴이 정확히 파싱된다."""
        from pyjallib.testKit import TestLogAnalyzer

        logPath = self._create_sample_log(
            tmp_path / "test.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: Suite ===
            2026-02-19 10:00:01,000 [INFO] SUCCESS: TC01 pass
            2026-02-19 10:00:02,000 [ERROR] ERROR: TC02 exception - ZeroDivisionError
            2026-02-19 10:00:03,000 [INFO] === TEST END: 1/2 passed, 1 failed ===
            """,
        )

        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(logPath)

        assert result.passed == 1
        assert result.errors == 1
        assert len(result.error_details) == 1
        assert "TC02 exception" in result.error_details[0]

    def test_analyze_incomplete_log(self, tmp_path: Path) -> None:
        """TEST END 마커가 없으면 completed=False이다."""
        from pyjallib.testKit import TestLogAnalyzer

        logPath = self._create_sample_log(
            tmp_path / "test.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: Suite ===
            2026-02-19 10:00:01,000 [INFO] SUCCESS: TC01 pass
            """,
        )

        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(logPath)

        assert result.passed == 1
        assert result.completed is False

    def test_analyze_nonexistent_file(self, tmp_path: Path) -> None:
        """존재하지 않는 파일을 분석하면 빈 결과를 반환한다."""
        from pyjallib.testKit import TestLogAnalyzer

        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(tmp_path / "nonexistent.log")

        assert result.passed == 0
        assert result.failed == 0
        assert result.total == 0
        assert result.completed is False

    def test_is_passed_all_success(self, tmp_path: Path) -> None:
        """모든 테스트 통과 + completed 시 is_passed=True이다."""
        from pyjallib.testKit import TestLogAnalyzer

        logPath = self._create_sample_log(
            tmp_path / "test.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: Suite ===
            2026-02-19 10:00:01,000 [INFO] SUCCESS: TC01
            2026-02-19 10:00:02,000 [INFO] SUCCESS: TC02
            2026-02-19 10:00:03,000 [INFO] === TEST END: 2/2 passed, 0 failed ===
            """,
        )

        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(logPath)

        assert analyzer.is_passed(result) is True

    def test_is_passed_with_failure(self, tmp_path: Path) -> None:
        """실패가 있으면 is_passed=False이다."""
        from pyjallib.testKit import TestLogAnalyzer

        logPath = self._create_sample_log(
            tmp_path / "test.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: Suite ===
            2026-02-19 10:00:01,000 [INFO] SUCCESS: TC01
            2026-02-19 10:00:02,000 [ERROR] FAIL: TC02 - detail
            2026-02-19 10:00:03,000 [INFO] === TEST END: 1/2 passed, 1 failed ===
            """,
        )

        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(logPath)

        assert analyzer.is_passed(result) is False

    def test_is_passed_incomplete(self, tmp_path: Path) -> None:
        """completed=False이면 실패가 없어도 is_passed=False이다."""
        from pyjallib.testKit import TestLogAnalyzer, TestResult

        analyzer = TestLogAnalyzer()
        result = TestResult(passed=5, failed=0, errors=0, total=5, completed=False)

        assert analyzer.is_passed(result) is False

    def test_format_report_passed(self, tmp_path: Path) -> None:
        """통과 결과의 리포트 포맷을 검증한다."""
        from pyjallib.testKit import TestLogAnalyzer, TestResult

        analyzer = TestLogAnalyzer()
        result = TestResult(passed=3, failed=0, errors=0, total=3, completed=True)

        report = analyzer.format_report(result)

        assert "PASSED" in report
        assert "통과: 3" in report
        assert "실패: 0" in report
        assert "에러: 0" in report
        assert "전체: 3" in report
        assert "완료: 예" in report

    def test_format_report_failed(self, tmp_path: Path) -> None:
        """실패 결과의 리포트에 실패 목록이 포함된다."""
        from pyjallib.testKit import TestLogAnalyzer, TestResult

        analyzer = TestLogAnalyzer()
        result = TestResult(
            passed=1,
            failed=1,
            errors=1,
            total=3,
            completed=True,
            failures=["TC02 - detail"],
            error_details=["TC03 - ZeroDivision"],
        )

        report = analyzer.format_report(result)

        assert "FAILED" in report
        assert "실패 목록:" in report
        assert "TC02 - detail" in report
        assert "에러 목록:" in report
        assert "TC03 - ZeroDivision" in report

    def test_analyze_multiple(self, tmp_path: Path) -> None:
        """여러 로그 파일을 일괄 분석한다."""
        from pyjallib.testKit import TestLogAnalyzer

        log1 = self._create_sample_log(
            tmp_path / "test1.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: Suite1 ===
            2026-02-19 10:00:01,000 [INFO] SUCCESS: TC01
            2026-02-19 10:00:02,000 [INFO] === TEST END: 1/1 passed, 0 failed ===
            """,
        )
        log2 = self._create_sample_log(
            tmp_path / "test2.log",
            """\
            2026-02-19 10:00:00,000 [INFO] === TEST START: Suite2 ===
            2026-02-19 10:00:01,000 [ERROR] FAIL: TC01 - fail
            2026-02-19 10:00:02,000 [INFO] === TEST END: 0/1 passed, 1 failed ===
            """,
        )

        analyzer = TestLogAnalyzer()
        results = analyzer.analyze_multiple([log1, log2])

        assert len(results) == 2
        assert results[0].passed == 1
        assert results[0].failed == 0
        assert results[1].passed == 0
        assert results[1].failed == 1


# ============================================================
# Task 13: TestRunner 단위 테스트
# ============================================================


class TestTestRunner:
    """TestRunner 클래스의 단위 테스트."""

    def test_build_command(self) -> None:
        """build_command는 [executable, script] 리스트를 반환한다."""
        from pyjallib.testKit import TestRunner

        runner = TestRunner(Path("python"))
        cmd = runner.build_command(Path("test_script.py"))

        assert cmd == ["python", "test_script.py"]

    def test_run_simple_script(self, tmp_path: Path) -> None:
        """간단한 Python 스크립트를 실행하고 RunResult를 검증한다."""
        from pyjallib.testKit import TestRunner

        runner = TestRunner(Path(sys.executable))
        result = runner.run(
            Path("-c"),
            tmp_path,
            inTimeout=10,
        )

        # "-c"는 스크립트가 아닌 플래그이므로, 실제로는 build_command가
        # [python, -c]를 만들어 빈 코드로 실행됨. 에러가 나지만 timed_out은 False.
        assert result.timed_out is False

    def test_run_with_output(self, tmp_path: Path) -> None:
        """stdout을 캡처하는 스크립트를 실행한다."""
        from pyjallib.testKit import TestRunner

        # 간단한 출력 스크립트 작성
        scriptPath = tmp_path / "test_output.py"
        scriptPath.write_text('print("hello from test")', encoding="utf-8")

        runner = TestRunner(Path(sys.executable))
        result = runner.run(scriptPath, tmp_path, inTimeout=10)

        assert result.returncode == 0
        assert "hello from test" in result.stdout
        assert result.timed_out is False

    def test_run_timeout(self, tmp_path: Path) -> None:
        """타임아웃이 발생하면 timed_out=True이다."""
        from pyjallib.testKit import TestRunner

        # 오래 걸리는 스크립트 작성
        scriptPath = tmp_path / "test_timeout.py"
        scriptPath.write_text("import time; time.sleep(60)", encoding="utf-8")

        runner = TestRunner(Path(sys.executable))
        result = runner.run(scriptPath, tmp_path, inTimeout=1)

        assert result.timed_out is True

    def test_run_creates_log_dir(self, tmp_path: Path) -> None:
        """존재하지 않는 로그 디렉토리를 자동 생성한다."""
        from pyjallib.testKit import TestRunner

        scriptPath = tmp_path / "test_simple.py"
        scriptPath.write_text('print("ok")', encoding="utf-8")

        logDir = tmp_path / "nested" / "logs"
        runner = TestRunner(Path(sys.executable))
        runner.run(scriptPath, logDir, inTimeout=10)

        assert logDir.exists()

    def test_run_stderr_capture(self, tmp_path: Path) -> None:
        """stderr 출력을 캡처한다."""
        from pyjallib.testKit import TestRunner

        scriptPath = tmp_path / "test_stderr.py"
        scriptPath.write_text(
            'import sys; sys.stderr.write("error output")', encoding="utf-8"
        )

        runner = TestRunner(Path(sys.executable))
        result = runner.run(scriptPath, tmp_path, inTimeout=10)

        assert "error output" in result.stderr

    def test_run_nonzero_returncode(self, tmp_path: Path) -> None:
        """비정상 종료 시 returncode가 정확하다."""
        from pyjallib.testKit import TestRunner

        scriptPath = tmp_path / "test_exit.py"
        scriptPath.write_text("import sys; sys.exit(42)", encoding="utf-8")

        runner = TestRunner(Path(sys.executable))
        result = runner.run(scriptPath, tmp_path, inTimeout=10)

        assert result.returncode == 42
        assert result.timed_out is False

    def test_executable_path_property(self) -> None:
        """executable_path 프로퍼티가 올바른 경로를 반환한다."""
        from pyjallib.testKit import TestRunner

        runner = TestRunner(Path("/usr/bin/python3"))
        assert runner.executable_path == Path("/usr/bin/python3")

    def test_run_sets_log_path_convention(self, tmp_path: Path) -> None:
        """run() 실행 시 convention 기반으로 log_path가 설정된다."""
        from pyjallib.testKit import TestRunner

        scriptPath = tmp_path / "test_sample.py"
        scriptPath.write_text('print("ok")', encoding="utf-8")

        runner = TestRunner(Path(sys.executable))
        result = runner.run(scriptPath, tmp_path, inTimeout=10)

        assert result.log_path is not None
        assert result.log_path == tmp_path / "test_test_sample.log"

    def test_run_sets_log_path_explicit(self, tmp_path: Path) -> None:
        """run()에 inLogPath를 명시하면 해당 경로가 log_path에 설정된다."""
        from pyjallib.testKit import TestRunner

        scriptPath = tmp_path / "test_sample.py"
        scriptPath.write_text('print("ok")', encoding="utf-8")

        customLogPath = tmp_path / "custom_log.log"
        runner = TestRunner(Path(sys.executable))
        result = runner.run(scriptPath, tmp_path, inTimeout=10, inLogPath=customLogPath)

        assert result.log_path == customLogPath


# ============================================================
# Task 14: MaxTestRunner 단위 테스트 (build_command만)
# ============================================================


class TestMaxTestRunner:
    """MaxTestRunner 클래스의 단위 테스트 (3ds Max 설치 불필요)."""

    @pytest.fixture(autouse=True)
    def _mock_pymxs(self) -> None:
        """pymxs 모듈을 모킹하여 3ds Max 없이 import 가능하게 한다."""
        # max 패키지의 __init__.py가 pymxs를 import하므로 미리 모킹
        mockModules = [
            "pymxs",
            "pymxs.runtime",
            "MaxPlus",
            "qtmax",
            "PySide2",
            "PySide2.QtWidgets",
            "PySide2.QtCore",
            "PySide2.QtGui",
        ]
        originalModules: dict[str, object] = {}
        for modName in mockModules:
            if modName in sys.modules:
                originalModules[modName] = sys.modules[modName]
            sys.modules[modName] = MagicMock()

        yield

        # 정리: 원래 모듈 복원 또는 제거
        for modName in mockModules:
            if modName in originalModules:
                sys.modules[modName] = originalModules[modName]  # type: ignore[assignment]
            else:
                sys.modules.pop(modName, None)

    def test_build_command_basic(self) -> None:
        """기본 명령줄이 올바른 포맷으로 조합된다."""
        from pyjallib.max.maxTestRunner import MaxTestRunner

        runner = MaxTestRunner(Path("C:/Program Files/Autodesk/3ds Max 2025"))
        cmd = runner.build_command(Path("tests/max/test_bone.py"))

        assert cmd[0] == str(
            Path("C:/Program Files/Autodesk/3ds Max 2025/3dsmaxbatch.exe")
        )
        assert "-mxsString" in cmd
        # python.ExecuteFile 패턴 확인
        mxsIdx = cmd.index("-mxsString")
        assert 'python.ExecuteFile @"' in cmd[mxsIdx + 1]
        assert "test_bone.py" in cmd[mxsIdx + 1]
        assert "-silent" in cmd

    def test_build_command_with_scene_file(self) -> None:
        """sceneFile 포함 시 -sceneFile 플래그가 추가된다."""
        from pyjallib.max.maxTestRunner import MaxTestRunner

        runner = MaxTestRunner(Path("C:/3dsMax"))
        cmd = runner.build_command(
            Path("test.py"),
            inSceneFile=Path("scene.max"),
        )

        assert "-sceneFile" in cmd
        sceneIdx = cmd.index("-sceneFile")
        assert cmd[sceneIdx + 1] == "scene.max"

    def test_build_command_without_scene_file(self) -> None:
        """sceneFile이 None이면 -sceneFile 플래그가 없다."""
        from pyjallib.max.maxTestRunner import MaxTestRunner

        runner = MaxTestRunner(Path("C:/3dsMax"))
        cmd = runner.build_command(Path("test.py"))

        assert "-sceneFile" not in cmd

    def test_build_command_with_listener_log(self) -> None:
        """listenerLog 포함 시 -listenerlog 플래그가 추가된다."""
        from pyjallib.max.maxTestRunner import MaxTestRunner

        runner = MaxTestRunner(Path("C:/3dsMax"))
        cmd = runner.build_command(
            Path("test.py"),
            inListenerLog=Path("logs/listener.log"),
        )

        assert "-listenerlog" in cmd
        listenerIdx = cmd.index("-listenerlog")
        assert cmd[listenerIdx + 1] == str(Path("logs/listener.log"))

    def test_build_command_all_options(self) -> None:
        """모든 옵션이 포함된 명령줄을 검증한다."""
        from pyjallib.max.maxTestRunner import MaxTestRunner

        runner = MaxTestRunner(Path("C:/3dsMax"))
        cmd = runner.build_command(
            Path("test.py"),
            inSceneFile=Path("scene.max"),
            inListenerLog=Path("listener.log"),
        )

        # 순서 검증: executable, [-sceneFile scene], -mxsString ..., [-listenerlog ...], -silent
        assert cmd[0] == str(Path("C:/3dsMax/3dsmaxbatch.exe"))
        assert "-sceneFile" in cmd
        assert "-mxsString" in cmd
        assert "-listenerlog" in cmd
        assert cmd[-1] == "-silent"

    def test_executable_path(self) -> None:
        """실행 파일 경로가 3dsmaxbatch.exe로 설정된다."""
        from pyjallib.max.maxTestRunner import MaxTestRunner

        runner = MaxTestRunner(Path("C:/Program Files/Autodesk/3ds Max 2025"))

        expected = Path("C:/Program Files/Autodesk/3ds Max 2025/3dsmaxbatch.exe")
        assert runner.executable_path == expected
