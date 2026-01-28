#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger 클래스 테스트 - 핸들러 격리 및 기본 기능 검증
"""

from loguru import logger

from pyjallib.logger import Logger


class TestLoggerMultiInstance:
    """멀티 인스턴스 핸들러 격리 테스트 그룹"""

    def test_multi_instance_handler_isolation(self, tmp_path):
        """TC1: 두 개의 Logger 인스턴스가 서로의 핸들러를 간섭하지 않는지 검증

        버그 재현: logger.remove()로 인해 logger1의 핸들러가 제거됨
        기대 동작: 각 Logger가 자신의 로그 파일에만 기록
        """
        logPath1 = tmp_path / "log1"
        logPath2 = tmp_path / "log2"

        # Logger 인스턴스 생성 (콘솔 출력 비활성화)
        logger1 = Logger(
            inLogPath=str(logPath1), inLogFileName="logger1", inEnableConsole=False
        )

        logger2 = Logger(
            inLogPath=str(logPath2), inLogFileName="logger2", inEnableConsole=False
        )

        # 각 Logger로 메시지 기록
        logger1.info("Message from logger1")
        logger2.info("Message from logger2")

        # 로그 파일 경로 확인
        logFile1 = list(logPath1.glob("logger1_*.log"))
        logFile2 = list(logPath2.glob("logger2_*.log"))

        assert len(logFile1) == 1, "logger1 로그 파일이 생성되지 않았습니다"
        assert len(logFile2) == 1, "logger2 로그 파일이 생성되지 않았습니다"

        # 로그 파일 내용 검증
        content1 = logFile1[0].read_text(encoding="utf-8")
        content2 = logFile2[0].read_text(encoding="utf-8")

        # logger1 파일에는 logger1 메시지만 존재해야 함
        assert "Message from logger1" in content1, (
            "logger1 메시지가 logger1 파일에 기록되지 않았습니다"
        )
        assert "Message from logger2" not in content1, (
            "logger2 메시지가 logger1 파일에 잘못 기록되었습니다 (격리 실패)"
        )

        # logger2 파일에는 logger2 메시지만 존재해야 함
        assert "Message from logger2" in content2, (
            "logger2 메시지가 logger2 파일에 기록되지 않았습니다"
        )
        assert "Message from logger1" not in content2, (
            "logger1 메시지가 logger2 파일에 잘못 기록되었습니다 (격리 실패)"
        )

        # 핸들러 정리 (비동기 로그 기록 완료 대기)
        logger.complete()
        logger1.remove_handlers()
        logger2.remove_handlers()

    def test_console_handler_isolation(self, tmp_path):
        """TC2: 한 Logger의 콘솔 핸들러가 다른 Logger 생성 후에도 유지되는지 검증

        버그 재현: logger2 생성 시 logger.remove()가 logger1의 콘솔 핸들러 제거
        기대 동작: logger1의 콘솔 핸들러가 유지되어야 함
        """
        logPath1 = tmp_path / "log1"
        logPath2 = tmp_path / "log2"

        # logger1: 콘솔 출력 활성화
        logger1 = Logger(
            inLogPath=str(logPath1), inLogFileName="logger1", inEnableConsole=True
        )

        # logger1 핸들러 개수 확인 (파일 + 콘솔 = 2개)
        initialHandlerCount = len(logger1._handlerIds)
        assert initialHandlerCount == 2, (
            f"logger1 핸들러 개수가 예상과 다릅니다 (예상: 2, 실제: {initialHandlerCount})"
        )

        # logger2: 콘솔 출력 비활성화
        logger2 = Logger(
            inLogPath=str(logPath2), inLogFileName="logger2", inEnableConsole=False
        )

        # logger1 핸들러 개수 재확인 (logger2 생성 후에도 2개 유지되어야 함)
        afterHandlerCount = len(logger1._handlerIds)

        # 버그 시나리오: logger.remove()로 인해 logger1의 핸들러가 무효화됨
        # 이 경우 logger1._handlerIds는 유지되지만 실제 핸들러는 제거됨
        # 따라서 이 테스트는 간접적으로 격리 문제를 감지
        assert afterHandlerCount == 2, (
            f"logger2 생성 후 logger1 핸들러가 변경되었습니다 (예상: 2, 실제: {afterHandlerCount})"
        )

        # 로그 기록 테스트 (logger1이 여전히 동작하는지 확인)
        logger1.info("After logger2 creation")

        logFile1 = list(logPath1.glob("logger1_*.log"))
        assert len(logFile1) == 1, "logger1 로그 파일이 생성되지 않았습니다"

        content1 = logFile1[0].read_text(encoding="utf-8")
        assert "After logger2 creation" in content1, (
            "logger2 생성 후 logger1이 정상 작동하지 않습니다"
        )

        # 핸들러 정리 (비동기 로그 기록 완료 대기)
        logger.complete()
        logger1.remove_handlers()
        logger2.remove_handlers()


class TestLoggerBasicFunctionality:
    """기존 기능 회귀 테스트 그룹"""

    def test_single_logger_basic_logging(self, tmp_path):
        """TC3: 단일 Logger 인스턴스의 기본 동작 검증

        기대 동작: debug/info/warning/error/critical 모든 레벨의 로그가 정상 기록됨
        """
        logPath = tmp_path / "logs"

        testLogger = Logger(
            inLogPath=str(logPath),
            inLogFileName="test",
            inEnableConsole=False,
            inLogLevel="DEBUG",
        )

        # 모든 로그 레벨 테스트
        testLogger.debug("Debug message")
        testLogger.info("Info message")
        testLogger.warning("Warning message")
        testLogger.error("Error message")
        testLogger.critical("Critical message")

        # 로그 파일 확인
        logFiles = list(logPath.glob("test_*.log"))
        assert len(logFiles) == 1, "로그 파일이 생성되지 않았습니다"

        content = logFiles[0].read_text(encoding="utf-8")

        # 모든 메시지가 기록되었는지 검증
        assert "Debug message" in content, "DEBUG 레벨 로그가 기록되지 않았습니다"
        assert "Info message" in content, "INFO 레벨 로그가 기록되지 않았습니다"
        assert "Warning message" in content, "WARNING 레벨 로그가 기록되지 않았습니다"
        assert "Error message" in content, "ERROR 레벨 로그가 기록되지 않았습니다"
        assert "Critical message" in content, "CRITICAL 레벨 로그가 기록되지 않았습니다"

        # 핸들러 정리 (비동기 로그 기록 완료 대기)
        logger.complete()
        testLogger.remove_handlers()

    def test_log_level_filtering(self, tmp_path):
        """로그 레벨 필터링 동작 검증

        기대 동작: INFO 레벨 설정 시 DEBUG 메시지는 기록되지 않음
        """
        logPath = tmp_path / "logs"

        testLogger = Logger(
            inLogPath=str(logPath),
            inLogFileName="test_level",
            inEnableConsole=False,
            inLogLevel="INFO",
        )

        testLogger.debug("Debug message - should not appear")
        testLogger.info("Info message - should appear")

        # 로그 파일 확인
        logFiles = list(logPath.glob("test_level_*.log"))
        assert len(logFiles) == 1, "로그 파일이 생성되지 않았습니다"

        content = logFiles[0].read_text(encoding="utf-8")

        # INFO 레벨 설정 시 DEBUG는 기록되지 않아야 함
        assert "Debug message" not in content, (
            "INFO 레벨 설정에서 DEBUG 메시지가 잘못 기록되었습니다"
        )
        assert "Info message" in content, "INFO 레벨 메시지가 기록되지 않았습니다"

        # 핸들러 정리 (비동기 로그 기록 완료 대기)
        logger.complete()
        testLogger.remove_handlers()
