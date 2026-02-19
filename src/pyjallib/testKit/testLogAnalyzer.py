#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
테스트 로그 분석기 모듈.

외부 프로세스에서 테스트 로그 파일을 파싱하고 구조화된 결과를 반환한다.
TestReporter가 생성한 표준 로그 포맷을 파싱하는 것이 주 목적이다.

의존성: Python stdlib만 사용 (dataclasses, pathlib, re).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestResult:
    """테스트 결과를 담는 데이터 클래스.

    Attributes:
        passed: 통과한 테스트 수
        failed: 실패한 테스트 수
        errors: 에러가 발생한 테스트 수
        total: 전체 테스트 수
        completed: 테스트가 정상 완료되었는지 여부
        failures: 실패한 테스트 상세 목록
        error_details: 에러 상세 목록
    """

    passed: int = 0
    failed: int = 0
    errors: int = 0
    total: int = 0
    completed: bool = False
    failures: list[str] = field(default_factory=list)
    error_details: list[str] = field(default_factory=list)


class TestLogAnalyzer:
    """테스트 로그 파일을 파싱하여 구조화된 결과를 반환하는 분석기.

    TestReporter가 생성한 표준 로그 포맷을 파싱한다.
    SUCCESS/FAIL/ERROR 패턴과 TEST END 마커를 인식한다.

    Example:
        analyzer = TestLogAnalyzer()
        result = analyzer.analyze(Path("tests/logs/test_CheckLayer.log"))
        if analyzer.is_passed(result):
            print("모든 테스트 통과")
    """

    # 로그 라인 패턴 (타임스탬프 뒤의 내용을 매칭)
    _SUCCESS_PATTERN: re.Pattern[str] = re.compile(r"SUCCESS: (.+)")
    _FAIL_PATTERN: re.Pattern[str] = re.compile(r"FAIL: (.+)")
    _ERROR_PATTERN: re.Pattern[str] = re.compile(r"ERROR: (.+)")
    _END_PATTERN: re.Pattern[str] = re.compile(r"=== TEST END.*===")

    def analyze(self, inLogPath: Path) -> TestResult:
        """단일 로그 파일을 파싱하여 TestResult를 반환한다.

        Args:
            inLogPath: 분석할 로그 파일 경로

        Returns:
            파싱된 테스트 결과
        """
        result = TestResult()
        logPath = Path(inLogPath)

        if not logPath.exists():
            return result

        content = logPath.read_text(encoding="utf-8")

        for line in content.splitlines():
            # ERROR를 먼저 검사하여 "FAIL:" 라인에 "ERROR:"가 포함된 경우를
            # 올바르게 에러로 분류한다. 순서: ERROR -> FAIL -> SUCCESS -> END
            errorMatch = self._ERROR_PATTERN.search(line)
            if errorMatch is not None:
                result.errors += 1
                result.error_details.append(errorMatch.group(1))
                continue

            failMatch = self._FAIL_PATTERN.search(line)
            if failMatch is not None:
                result.failed += 1
                result.failures.append(failMatch.group(1))
                continue

            successMatch = self._SUCCESS_PATTERN.search(line)
            if successMatch is not None:
                result.passed += 1
                continue

            endMatch = self._END_PATTERN.search(line)
            if endMatch is not None:
                result.completed = True

        result.total = result.passed + result.failed + result.errors
        return result

    def analyze_multiple(self, inLogPaths: list[Path]) -> list[TestResult]:
        """여러 로그 파일을 일괄 분석한다.

        Args:
            inLogPaths: 분석할 로그 파일 경로 목록

        Returns:
            각 로그 파일에 대한 TestResult 목록
        """
        results: list[TestResult] = []
        for logPath in inLogPaths:
            results.append(self.analyze(logPath))
        return results

    def is_passed(self, inResult: TestResult) -> bool:
        """테스트 결과가 통과인지 판정한다.

        실패(failed)와 에러(errors)가 모두 0이고, 테스트가 정상 완료(completed)되어야
        통과로 판정한다.

        Args:
            inResult: 판정할 테스트 결과

        Returns:
            통과 여부
        """
        return (
            inResult.failed == 0 and inResult.errors == 0 and inResult.completed is True
        )

    def format_report(self, inResult: TestResult) -> str:
        """테스트 결과를 사람이 읽기 좋은 텍스트 리포트로 변환한다.

        Args:
            inResult: 리포트로 변환할 테스트 결과

        Returns:
            포맷팅된 텍스트 리포트
        """
        lines: list[str] = []
        lines.append("=" * 50)

        statusText = "PASSED" if self.is_passed(inResult) else "FAILED"
        lines.append(f"테스트 결과: {statusText}")
        lines.append("-" * 50)
        lines.append(f"통과: {inResult.passed}")
        lines.append(f"실패: {inResult.failed}")
        lines.append(f"에러: {inResult.errors}")
        lines.append(f"전체: {inResult.total}")
        lines.append(f"완료: {'예' if inResult.completed else '아니오'}")

        if inResult.failures:
            lines.append("-" * 50)
            lines.append("실패 목록:")
            for failure in inResult.failures:
                lines.append(f"  - {failure}")

        if inResult.error_details:
            lines.append("-" * 50)
            lines.append("에러 목록:")
            for errorDetail in inResult.error_details:
                lines.append(f"  - {errorDetail}")

        lines.append("=" * 50)
        return "\n".join(lines)
