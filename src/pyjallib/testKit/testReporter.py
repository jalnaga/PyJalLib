#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
테스트 리포터 모듈.

DCC 내부에서 실행되는 테스트 스크립트가 import하여 사용한다.
기존 테스트 파일의 보일러플레이트(assert_test, _passed, _failed, logging 설정)를 통합한다.

의존성: Python stdlib만 사용 (logging, pathlib).
"""

import logging
from pathlib import Path
from typing import Optional


class TestReporter:
    """DCC 내부 테스트용 리포터.

    테스트 스크립트에서 인스턴스를 생성하면 로그 파일이 자동 설정되고,
    assert_test/error 메서드로 결과를 기록한다.

    Example:
        reporter = TestReporter("CheckLayer", Path("tests/logs"))
        reporter.assert_test(result is True, "TC01 인스턴스 생성")
        reporter.summary()
    """

    def __init__(
        self,
        inSuiteName: str,
        inLogDir: Path,
        inLogFilename: Optional[str] = None,
    ) -> None:
        """리포터를 초기화하고 로그 파일을 설정한다.

        Args:
            inSuiteName: 테스트 스위트 이름
            inLogDir: 로그 파일을 저장할 디렉토리 경로
            inLogFilename: 로그 파일명. None이면 "test_{suiteName}.log" 자동 생성.
        """
        self._suiteName: str = inSuiteName
        self._passed: int = 0
        self._failed: int = 0

        # 로그 디렉토리 생성
        logDir = Path(inLogDir)
        logDir.mkdir(parents=True, exist_ok=True)

        # 로그 파일 경로 결정
        if inLogFilename is not None:
            logFilename = inLogFilename
        else:
            logFilename = f"test_{inSuiteName}.log"
        self._logPath: Path = logDir / logFilename

        # 고유 로거 생성 (모듈 이름 + 스위트 이름으로 격리)
        loggerName = f"pyjallib.testKit.{inSuiteName}"
        self._logger: logging.Logger = logging.getLogger(loggerName)
        self._logger.setLevel(logging.INFO)

        # 기존 핸들러 제거 (재생성 시 중복 방지, 파일 디스크립터 누수 방지)
        for handler in self._logger.handlers:
            handler.close()
        self._logger.handlers.clear()

        # 파일 핸들러 설정
        fileHandler = logging.FileHandler(
            str(self._logPath), mode="w", encoding="utf-8"
        )
        fileHandler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fileHandler.setFormatter(formatter)
        self._logger.addHandler(fileHandler)

        # 부모 로거로 전파 방지
        self._logger.propagate = False

        # TEST START 마커 기록
        self._logger.info(f"=== TEST START: {self._suiteName} ===")

    def assert_test(
        self, inCondition: bool, inTestName: str, inDetail: str = ""
    ) -> None:
        """조건을 검증하고 결과를 로그에 기록한다.

        Args:
            inCondition: 테스트 통과 여부
            inTestName: 테스트 케이스 이름
            inDetail: 실패 시 추가 상세 정보
        """
        if inCondition:
            self._passed += 1
            self._logger.info(f"SUCCESS: {inTestName}")
        else:
            self._failed += 1
            msg = f"FAIL: {inTestName}"
            if inDetail:
                msg += f" - {inDetail}"
            self._logger.error(msg)

    def error(self, inTestName: str, inErrorMessage: str) -> None:
        """예외 발생 시 에러를 로그에 기록한다.

        Args:
            inTestName: 테스트 케이스 이름
            inErrorMessage: 에러 메시지
        """
        self._failed += 1
        self._logger.error(f"ERROR: {inTestName} - {inErrorMessage}")

    @property
    def passed(self) -> int:
        """통과한 테스트 수를 반환한다."""
        return self._passed

    @property
    def failed(self) -> int:
        """실패한 테스트 수를 반환한다."""
        return self._failed

    @property
    def total(self) -> int:
        """전체 테스트 수를 반환한다."""
        return self._passed + self._failed

    def summary(self) -> tuple[int, int, int]:
        """테스트 결과 요약을 로그에 기록하고 카운터 튜플을 반환한다.

        Returns:
            (passed, failed, total) 튜플
        """
        totalCount = self._passed + self._failed
        self._logger.info(
            f"=== TEST END: {self._passed}/{totalCount} passed, "
            f"{self._failed} failed ==="
        )
        return (self._passed, self._failed, totalCount)

    def close(self) -> None:
        """로거의 파일 핸들러를 닫고 제거하여 파일 디스크립터 누수를 방지한다."""
        for handler in self._logger.handlers:
            handler.close()
        self._logger.handlers.clear()

    @property
    def log_path(self) -> Path:
        """로그 파일 경로를 반환한다."""
        return self._logPath
