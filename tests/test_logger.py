#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib Logger 클래스 테스트
loguru 기반 Logger 클래스의 기능을 검증합니다.
"""

import tempfile
import os
from pathlib import Path

from pyjallib.logger import Logger


class TestLoggerInit:
    """Logger 클래스 초기화 테스트"""

    def test_default_init(self):
        """기본 파라미터로 초기화 테스트"""
        logger = Logger()
        
        # 기본 로그 경로 확인 (Documents/PyJalLib/logs/)
        expectedPath = Path.home() / "Documents" / "PyJalLib" / "logs"
        assert logger._logPath == expectedPath
        
        # 기본 파일명 확인
        assert logger._logFileName == "pyjallib"
        
        # 기본 콘솔 활성화 확인
        assert logger._enableConsole is True
        
        # 기본 로그 레벨 확인
        assert logger._logLevel == "DEBUG"
        
        # 핸들러 정리
        logger.remove_handlers()

    def test_custom_log_path(self):
        """커스텀 로그 경로로 초기화 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            customPath = os.path.join(tmpDir, "custom_logs")
            logger = Logger(inLogPath=customPath)
            
            try:
                assert logger._logPath == Path(customPath)
                # 디렉토리가 생성되었는지 확인
                assert Path(customPath).exists()
            finally:
                logger.remove_handlers()

    def test_custom_log_filename(self):
        """커스텀 로그 파일명으로 초기화 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inLogFileName="custom_log")
            try:
                assert logger._logFileName == "custom_log"
            finally:
                logger.remove_handlers()

    def test_console_disabled(self):
        """콘솔 출력 비활성화 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                assert logger._enableConsole is False
            finally:
                logger.remove_handlers()

    def test_custom_log_level(self):
        """커스텀 로그 레벨 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inLogLevel="WARNING")
            try:
                assert logger._logLevel == "WARNING"
            finally:
                logger.remove_handlers()

    def test_log_level_case_insensitive(self):
        """로그 레벨 대소문자 구분 없이 동작하는지 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inLogLevel="warning")
            try:
                assert logger._logLevel == "WARNING"
            finally:
                logger.remove_handlers()


class TestLoggerMethods:
    """Logger 로깅 메서드 테스트"""

    def test_debug_method(self):
        """debug 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                logger.debug("디버그 테스트 메시지")
                
                # 로그 파일이 생성되었는지 확인
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
            finally:
                logger.remove_handlers()

    def test_info_method(self):
        """info 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                logger.info("정보 테스트 메시지")
                
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
            finally:
                logger.remove_handlers()

    def test_warning_method(self):
        """warning 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                logger.warning("경고 테스트 메시지")
                
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
            finally:
                logger.remove_handlers()

    def test_error_method(self):
        """error 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                logger.error("에러 테스트 메시지")
                
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
            finally:
                logger.remove_handlers()

    def test_critical_method(self):
        """critical 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                logger.critical("치명적 에러 테스트 메시지")
                
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
            finally:
                logger.remove_handlers()

    def test_exception_method(self):
        """exception 메서드 테스트 - traceback 포함"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                try:
                    raise ValueError("테스트 예외")
                except ValueError:
                    logger.exception("예외 발생 테스트")
                
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
                
                # 로그 파일 내용에 traceback이 포함되어 있는지 확인
                logContent = logFiles[0].read_text(encoding="utf-8")
                assert "ValueError" in logContent or "테스트 예외" in logContent
            finally:
                logger.remove_handlers()


class TestLoggerFileNaming:
    """Logger 파일명 패턴 테스트"""

    def test_log_file_naming_pattern(self):
        """로그 파일명이 {파일명}_{YYYYMMDD}.log 패턴인지 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inLogFileName="test_log", inEnableConsole=False)
            try:
                logger.info("테스트 메시지")
                
                logFiles = list(Path(tmpDir).glob("*.log"))
                assert len(logFiles) >= 1
                
                # 파일명 패턴 확인: test_log_YYYYMMDD.log
                fileName = logFiles[0].name
                assert fileName.startswith("test_log_")
                assert fileName.endswith(".log")
                
                # 날짜 부분이 8자리 숫자인지 확인
                datePart = fileName.replace("test_log_", "").replace(".log", "")
                assert len(datePart) == 8
                assert datePart.isdigit()
            finally:
                logger.remove_handlers()


class TestLoggerConsoleControl:
    """Logger 콘솔 출력 제어 테스트"""

    def test_console_enabled_by_default(self):
        """기본적으로 콘솔 출력이 활성화되어 있는지 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir)
            try:
                assert logger._enableConsole is True
                # 콘솔 핸들러 포함하여 2개의 핸들러가 등록되어야 함
                assert len(logger._handlerIds) == 2
            finally:
                logger.remove_handlers()

    def test_console_can_be_disabled(self):
        """콘솔 출력을 비활성화할 수 있는지 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            try:
                assert logger._enableConsole is False
                # 파일 핸들러만 등록되어야 함
                assert len(logger._handlerIds) == 1
            finally:
                logger.remove_handlers()


class TestLoggerHandlerManagement:
    """Logger 핸들러 관리 테스트"""

    def test_remove_handlers(self):
        """핸들러 제거 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpDir:
            logger = Logger(inLogPath=tmpDir, inEnableConsole=False)
            
            # 핸들러가 등록되어 있는지 확인
            assert len(logger._handlerIds) == 1
            
            # 핸들러 제거
            logger.remove_handlers()
            
            # 핸들러 목록이 비어있는지 확인
            assert len(logger._handlerIds) == 0
