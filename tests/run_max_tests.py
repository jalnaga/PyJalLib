#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3DS Max 헤드레스 테스트 러너.

MaxTestRunner로 tests/max/ 하위의 모든 테스트 스크립트를 순차 실행하고,
TestLogAnalyzer로 로그를 분석하여 결과를 출력한다.

사용법:
    uv run python tests/run_max_tests.py
"""

import importlib.util
import sys
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

# MaxTestRunner는 pyjallib.max 패키지를 통해 import하면 pymxs 의존 모듈까지
# 전부 로드되므로, importlib으로 maxTestRunner.py 파일만 직접 로드한다.
_maxTestRunnerPath = Path(__file__).parent.parent / "src" / "pyjallib" / "max" / "maxTestRunner.py"
_spec = importlib.util.spec_from_file_location("maxTestRunner", _maxTestRunnerPath)
_maxTestRunnerModule = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_maxTestRunnerModule)
MaxTestRunner = _maxTestRunnerModule.MaxTestRunner

from pyjallib.testKit import TestLogAnalyzer

# 설정
MAX_PATH = Path(r"C:\Program Files\Autodesk\3ds Max 2024")
TESTS_DIR = Path(__file__).parent / "max"
LOG_DIR = Path(__file__).parent / "logs"
TIMEOUT = 300  # 초

# 테스트 스크립트 목록 (실행 순서)
TEST_SCRIPTS = [
    "test_name.py",
    "test_anim.py",
    "test_helper.py",
    "test_layer.py",
    "test_constraint.py",
    "test_bone.py",
    "test_link.py",
    "test_align.py",
    "test_select.py",
    "test_mirror.py",
    "test_attribute.py",
    "test_ui_fuzzy_search_combo_box.py",
]

# TestReporter SuiteName 오버라이드:
# 스크립트 파일명에서 자동 계산한 이름과 TestReporter SuiteName이 다를 때 명시적으로 지정.
# key: 스크립트 파일명 (확장자 포함), value: TestReporter SuiteName
LOG_NAME_OVERRIDES = {
    "test_ui_fuzzy_search_combo_box.py": "FuzzySearchComboBoxUI",
}


def main() -> None:
    """모든 Max 테스트를 순차 실행하고 결과를 분석한다."""
    runner = MaxTestRunner(MAX_PATH)
    analyzer = TestLogAnalyzer()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 실행할 스크립트 필터링 (존재하는 것만)
    scripts = []
    for scriptName in TEST_SCRIPTS:
        scriptPath = TESTS_DIR / scriptName
        if scriptPath.exists():
            scripts.append(scriptPath)
        else:
            print(f"[SKIP] {scriptName} - 파일 없음")

    if not scripts:
        print("실행할 테스트 스크립트가 없습니다.")
        return

    print(f"3DS Max 경로: {MAX_PATH}")
    print(f"테스트 스크립트: {len(scripts)}개")
    print(f"로그 디렉토리: {LOG_DIR}")
    print("=" * 60)

    # 테스트 실행 (3dsmaxbatch.exe는 단일 인스턴스 제한이므로 직렬 실행)
    runResults = []
    for scriptPath in scripts:
        suiteName = scriptPath.stem
        # TestReporter의 로그 명명 규칙에 맞춤: test_{SuiteName}.log
        # test_name.py → "Name" → test_Name.log
        # LOG_NAME_OVERRIDES에 등록된 경우 오버라이드된 SuiteName을 사용
        scriptFileName = scriptPath.name
        if scriptFileName in LOG_NAME_OVERRIDES:
            reporterSuiteName = LOG_NAME_OVERRIDES[scriptFileName]
        else:
            reporterSuiteName = suiteName.removeprefix("test_").capitalize()
        expectedLogPath = LOG_DIR / f"test_{reporterSuiteName}.log"
        print(f"\n[RUN] {suiteName} ...", end=" ", flush=True)

        runResult = runner.run(
            inScriptPath=scriptPath,
            inLogDir=LOG_DIR,
            inTimeout=TIMEOUT,
            inLogPath=expectedLogPath,
        )
        runResults.append((suiteName, runResult))

        if runResult.timed_out:
            print("TIMEOUT")
        elif runResult.returncode != 0:
            print(f"EXIT CODE {runResult.returncode}")
        else:
            print("완료")

    # 로그 분석
    print("\n" + "=" * 60)
    print("테스트 결과 분석")
    print("=" * 60)

    totalPassed = 0
    totalFailed = 0
    totalErrors = 0
    suiteResults = []

    for suiteName, runResult in runResults:
        logPath = runResult.log_path
        if logPath is not None and logPath.exists():
            testResult = analyzer.analyze(logPath)
            passed = analyzer.is_passed(testResult)
            suiteResults.append((suiteName, testResult, passed, logPath))

            totalPassed += testResult.passed
            totalFailed += testResult.failed
            totalErrors += testResult.errors

            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {suiteName}: "
                  f"{testResult.passed} passed, "
                  f"{testResult.failed} failed, "
                  f"{testResult.errors} errors "
                  f"(완료: {'Y' if testResult.completed else 'N'})")

            if not passed:
                if testResult.failures:
                    for failure in testResult.failures:
                        print(f"         FAIL: {failure}")
                if testResult.error_details:
                    for error in testResult.error_details:
                        print(f"         ERROR: {error}")
        else:
            print(f"  [SKIP] {suiteName}: 로그 파일 없음 ({logPath})")
            suiteResults.append((suiteName, None, False, logPath))

        # listener 로그 경로도 표시
        if runResult.listener_log_path is not None and runResult.listener_log_path.exists():
            print(f"         listener: {runResult.listener_log_path}")

    # 최종 요약
    totalTests = totalPassed + totalFailed + totalErrors
    allPassed = totalFailed == 0 and totalErrors == 0
    finalStatus = "ALL PASSED" if allPassed else "SOME FAILED"

    print("\n" + "=" * 60)
    print(f"최종 결과: {finalStatus}")
    print(f"  총 TC: {totalTests} | 통과: {totalPassed} | 실패: {totalFailed} | 에러: {totalErrors}")
    print(f"  스위트: {len(suiteResults)}개 중 "
          f"{sum(1 for _, _, p, _ in suiteResults if p)}개 통과")
    print("=" * 60)

    # 로그 파일 경로 출력
    print("\n로그 파일 경로:")
    for suiteName, _, _, logPath in suiteResults:
        if logPath is not None and logPath.exists():
            print(f"  {suiteName}: {logPath}")


if __name__ == "__main__":
    main()
