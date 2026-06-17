# -*- coding: utf-8 -*-
"""pyjallib.logger.Logger 테스트 (Type A - Console pytest).

표준 logging 기반 Logger의 동작/격리/포맷/로테이션 구성/핸들러 정리를 검증한다.
모든 로그 파일은 tmp_path로 격리하여 환경 오염을 방지한다.
"""

import re
import logging
from logging.handlers import TimedRotatingFileHandler

from pyjallib.logger import Logger


def _read_log(logPath, fileName="pyjallib"):
    """tmp_path에 기록된 로그 파일 내용을 UTF-8로 읽어 반환한다."""
    return (logPath / f"{fileName}.log").read_text(encoding="utf-8")


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
    """핸들러 구성 검증: 파일 핸들러는 일자 suffix를 갖는 TimedRotatingFileHandler."""
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
        # 일자 suffix가 지정되어야 백업 파일명에 일자가 드러난다.
        assert fileHandler.suffix == "%Y%m%d"
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


def test_remove_handlers_clears(tmp_path):
    """remove_handlers() 호출 후 핸들러 목록과 logger 핸들러가 모두 비워지는지 검증."""
    logger = Logger(
        inLogPath=str(tmp_path), inLogFileName="pyjallib", inEnableConsole=True
    )
    assert len(logger._handlers) == 2
    logger.remove_handlers()
    assert len(logger._handlers) == 0
    assert len(logger._logger.handlers) == 0
