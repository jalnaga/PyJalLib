# -*- coding: utf-8 -*-
"""pyjallib.logger.Logger 테스트 (Type A - Console pytest).

표준 logging 기반 Logger의 동작/격리/포맷/로테이션 구성/핸들러 정리를 검증한다.
모든 로그 파일은 tmp_path로 격리하여 환경 오염을 방지한다.
"""

import re
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from pyjallib.logger import DatedTimedRotatingFileHandler, Logger


def _dated_log_name(fileName="pyjallib"):
    """오늘 일자를 담은 로그 파일명을 만든다 (`{fileName}_{YYYYMMDD}.log`)."""
    return f"{fileName}_{datetime.now().strftime('%Y%m%d')}.log"


def _read_log(logPath, fileName="pyjallib"):
    """tmp_path에 기록된 로그 파일 내용을 UTF-8로 읽어 반환한다."""
    return (logPath / _dated_log_name(fileName)).read_text(encoding="utf-8")


def test_six_methods_write_to_file(tmp_path):
    """6개 로깅 메서드가 모두 정상 동작하여 파일에 기록되는지 검증."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=False
    )
    try:
        logger.debug("디버그")
        logger.info("정보")
        logger.warning("경고")
        logger.error("에러")
        logger.critical("치명")
        try:
            raise ValueError("테스트 예외")
        except ValueError:
            logger.exception("예외 발생")

        content = _read_log(tmp_path)
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            assert f"[{level}]" in content
        # exception()은 traceback을 자동 포함한다.
        assert "Traceback (most recent call last)" in content
        assert "ValueError: 테스트 예외" in content
    finally:
        logger.remove_handlers()


def test_multi_instance_isolation(tmp_path):
    """멀티 인스턴스 격리: 각 logger가 자기 파일에만 기록되고 혼선이 없는지 검증."""
    path1 = tmp_path / "one"
    path2 = tmp_path / "two"
    logger1 = Logger(
        inLogPath=str(path1), inLogFileName="logone", inEnableConsole=False
    )
    logger2 = Logger(
        inLogPath=str(path2), inLogFileName="logtwo", inEnableConsole=False
    )
    try:
        logger1.info("첫번째 인스턴스 메시지")
        logger2.info("두번째 인스턴스 메시지")

        content1 = _read_log(path1, "logone")
        content2 = _read_log(path2, "logtwo")

        assert "첫번째 인스턴스 메시지" in content1
        assert "두번째 인스턴스 메시지" not in content1
        assert "두번째 인스턴스 메시지" in content2
        assert "첫번째 인스턴스 메시지" not in content2

        # named logger가 고유하고 루트로 전파되지 않아야 한다.
        assert logger1._logger.name != logger2._logger.name
        assert logger1._logger.propagate is False
        assert logger2._logger.propagate is False
    finally:
        logger1.remove_handlers()
        logger2.remove_handlers()


def test_no_console_duplication(tmp_path, capsys):
    """propagate=False로 콘솔 중복 출력이 없는지 검증 (인스턴스당 stderr 1줄)."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=True
    )
    try:
        logger.info("콘솔 메시지")
        captured = capsys.readouterr()
        # 메시지가 stderr에 정확히 한 번만 나타나야 한다.
        assert captured.err.count("콘솔 메시지") == 1
    finally:
        logger.remove_handlers()


def test_log_format(tmp_path):
    """포맷 검증: 타임스탬프 + [LEVEL] + 메시지, UTF-8 한글 보존."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=False
    )
    try:
        logger.info("한글 로그 메시지 작업 완료")
        content = _read_log(tmp_path).strip()
        # 예: 2026-06-17 14:30:25 [INFO] 한글 로그 메시지 작업 완료
        pattern = (
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[INFO\] 한글 로그 메시지 작업 완료$"
        )
        assert re.match(pattern, content.splitlines()[-1])
    finally:
        logger.remove_handlers()


def test_handler_configuration(tmp_path):
    """핸들러 구성 검증: 파일 핸들러는 자정 롤오버·7일 보관의 일자 파일명 핸들러."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=True
    )
    try:
        # 콘솔 활성화 시 파일 + 콘솔 = 2개 핸들러
        assert len(logger._handlers) == 2

        fileHandlers = [
            h for h in logger._handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(fileHandlers) == 1
        fileHandler = fileHandlers[0]
        # 활성 파일명 자체가 일자를 담는다(백업 rename 규약이 아니다).
        assert isinstance(fileHandler, DatedTimedRotatingFileHandler)
        assert fileHandler.when == "MIDNIGHT"
        assert fileHandler.backupCount == 7

        streamHandlers = [
            h
            for h in logger._handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(streamHandlers) == 1
    finally:
        logger.remove_handlers()


def test_console_disabled_single_handler(tmp_path):
    """inEnableConsole=False면 파일 핸들러 1개만 부착된다."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=False
    )
    try:
        assert len(logger._handlers) == 1
        assert isinstance(logger._handlers[0], TimedRotatingFileHandler)
    finally:
        logger.remove_handlers()


def test_active_log_file_name_carries_date(tmp_path):
    """활성 로그 파일명이 `{파일명}_{YYYYMMDD}.log`여야 한다.

    프로덕션 로그 수집 관행이 이 이름에 맞춰져 있다(2026-07-30 마스터 결정).
    무일자 `{파일명}.log`가 만들어지면 회귀다.
    """
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="AnimExporter", inEnableConsole=False
    )
    try:
        logger.info("일자 파일명 확인")

        expectedName = _dated_log_name("AnimExporter")
        createdNames = sorted(p.name for p in tmp_path.iterdir())

        assert createdNames == [expectedName]
        assert "AnimExporter.log" not in createdNames
    finally:
        logger.remove_handlers()


def test_rollover_switches_to_new_dated_file_without_rename(tmp_path):
    """롤오버가 백업 rename이 아니라 새 일자 파일로 전환해야 한다.

    표준 핸들러라면 활성 파일을 `{name}.log.{YYYYMMDD}`로 rename한다. 활성 파일명이
    이미 일자를 담으므로 rename하면 `AnimExporter_20260730.log.20260731` 같은 산물이
    남는다 - 긴 DCC 세션에서 실제로 발생하는 흠이라 이 단정으로 막는다.
    """
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="AnimExporter", inEnableConsole=False
    )
    try:
        logger.info("롤오버 전")
        fileHandler = logger._handlers[0]

        # 어제 일자 파일에 쓰고 있던 상황을 만든 뒤 롤오버를 강제한다.
        yesterdayPath = tmp_path / "AnimExporter_20260729.log"
        fileHandler.stream.close()
        fileHandler.stream = None
        (tmp_path / _dated_log_name("AnimExporter")).rename(yesterdayPath)
        fileHandler.baseFilename = str(yesterdayPath)
        fileHandler.stream = fileHandler._open()

        fileHandler.doRollover()
        logger.info("롤오버 후")

        # 새 일자 파일로 넘어갔고, 어제 파일은 rename되지 않고 그대로 남는다.
        assert fileHandler.baseFilename.endswith(_dated_log_name("AnimExporter"))
        assert yesterdayPath.exists()
        assert "롤오버 후" in _read_log(tmp_path, "AnimExporter")
        assert "롤오버 후" not in yesterdayPath.read_text(encoding="utf-8")

        # `.log.{YYYYMMDD}` 형태의 백업 산물이 생기지 않아야 한다.
        assert [p.name for p in tmp_path.glob("*.log.*")] == []
    finally:
        logger.remove_handlers()


def test_rollover_purges_files_beyond_backup_count(tmp_path):
    """보관 개수(활성 1 + 백업 7)를 넘는 과거 일자 파일이 정리되어야 한다."""
    # 과거 일자 파일 12개를 미리 만들어 둔다.
    for day in range(1, 13):
        (tmp_path / f"AnimExporter_202607{day:02d}.log").write_text(
            "과거 로그", encoding="utf-8"
        )

    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="AnimExporter", inEnableConsole=False
    )
    try:
        fileHandler = logger._handlers[0]
        fileHandler.doRollover()

        remaining = sorted(p.name for p in tmp_path.glob("AnimExporter_*.log"))

        # 활성 파일 1개 + 백업 7개 = 8개만 남고, 남은 것은 가장 최근 일자들이다.
        assert len(remaining) == 8
        assert _dated_log_name("AnimExporter") in remaining
        assert "AnimExporter_20260701.log" not in remaining
    finally:
        logger.remove_handlers()


def test_remove_handlers_clears(tmp_path):
    """remove_handlers() 호출 후 핸들러 목록과 logger 핸들러가 모두 비워지는지 검증."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=True
    )
    assert len(logger._handlers) == 2
    logger.remove_handlers()
    assert len(logger._handlers) == 0
    assert len(logger._logger.handlers) == 0
