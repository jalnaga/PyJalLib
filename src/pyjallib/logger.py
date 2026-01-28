#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib 로깅 모듈 - loguru 기반

loguru를 래핑하여 PyJalLib 전용 로깅 기능을 제공합니다.
"""

import sys
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger


class Logger:
    """PyJalLib 로깅 클래스 - loguru 래퍼

    loguru를 기반으로 파일 및 콘솔 로깅을 제공합니다.

    Attributes:
        _logPath (Path): 로그 파일 저장 경로
        _logFileName (str): 로그 파일명 (확장자 제외)
        _enableConsole (bool): 콘솔 출력 활성화 여부
        _logLevel (str): 로깅 레벨
        _handlerIds (list): 등록된 loguru 핸들러 ID 목록
        _instanceId (str): Logger 인스턴스 고유 ID (핸들러 격리용)
        _logger: 인스턴스별 바인딩된 logger 객체

    Example:
        >>> logger = Logger()
        >>> logger.info("정보 메시지")
        >>> logger.error("에러 메시지")
    """

    # 클래스 변수: loguru 기본 핸들러 제거 여부 추적
    _default_handler_removed = False

    def __init__(
        self,
        inLogPath: Optional[str] = None,
        inLogFileName: Optional[str] = None,
        inEnableConsole: bool = True,
        inLogLevel: str = "DEBUG",
    ) -> None:
        """Logger 인스턴스 초기화

        Args:
            inLogPath: 로그 파일 저장 경로.
                       None인 경우 기본 경로 사용 (Documents/PyJalLib/logs/)
            inLogFileName: 로그 파일명 (확장자 제외).
                           None인 경우 기본값 "pyjallib" 사용
            inEnableConsole: 콘솔(stderr) 출력 활성화 여부. 기본값 True
            inLogLevel: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                        기본값 "DEBUG"
        """
        # 로그 경로 설정
        if inLogPath is None:
            documentsPath = Path.home() / "Documents"
            self._logPath = documentsPath / "PyJalLib" / "logs"
        else:
            self._logPath = Path(inLogPath)

        # 로그 디렉토리 생성
        self._logPath.mkdir(parents=True, exist_ok=True)

        # 로그 파일명 설정
        self._logFileName = inLogFileName if inLogFileName is not None else "pyjallib"

        # 출력 옵션 설정
        self._enableConsole = inEnableConsole
        self._logLevel = inLogLevel.upper()

        # 핸들러 ID 저장 목록
        self._handlerIds: list[int] = []

        # 인스턴스 고유 ID 생성 (핸들러 격리용)
        self._instanceId = str(uuid.uuid4())

        # 인스턴스별 바인딩된 logger 생성
        self._logger = logger.bind(instance_id=self._instanceId)

        # loguru 설정
        self._setup_logger()

    def _setup_logger(self) -> None:
        """loguru 핸들러 설정

        새로운 핸들러를 등록합니다.
        - 파일 핸들러: 항상 활성화
        - 콘솔 핸들러: inEnableConsole에 따라 결정

        Note: 첫 번째 Logger 인스턴스 생성 시 loguru의 기본 핸들러를 제거합니다.
        이후 filter 함수를 사용하여 각 인스턴스의 ID를 가진 로그만 처리하여
        완전한 격리를 보장합니다.
        """

        # 첫 번째 Logger 인스턴스인 경우 loguru 기본 핸들러 제거
        if not Logger._default_handler_removed:
            logger.remove()  # 기본 stderr 핸들러 제거
            Logger._default_handler_removed = True

        # 파일 핸들러 설정
        # 파일명 패턴: {로그경로}/{파일명}_{time:YYYYMMDD}.log
        logFilePath = self._logPath / f"{self._logFileName}_{{time:YYYYMMDD}}.log"

        fileHandlerId = logger.add(
            str(logFilePath),
            level=self._logLevel,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
            filter=lambda record: record["extra"].get("instance_id")
            == self._instanceId,
        )
        self._handlerIds.append(fileHandlerId)

        # 콘솔 핸들러 설정 (선택사항)
        if self._enableConsole:
            consoleHandlerId = logger.add(
                sys.stderr,
                level=self._logLevel,
                filter=lambda record: record["extra"].get("instance_id")
                == self._instanceId,
            )
            self._handlerIds.append(consoleHandlerId)

    def debug(self, inMessage: str) -> None:
        """디버그 레벨 로그 메시지 출력

        Args:
            inMessage: 출력할 로그 메시지
        """
        self._logger.debug(inMessage)

    def info(self, inMessage: str) -> None:
        """정보 레벨 로그 메시지 출력

        Args:
            inMessage: 출력할 로그 메시지
        """
        self._logger.info(inMessage)

    def warning(self, inMessage: str) -> None:
        """경고 레벨 로그 메시지 출력

        Args:
            inMessage: 출력할 로그 메시지
        """
        self._logger.warning(inMessage)

    def error(self, inMessage: str) -> None:
        """에러 레벨 로그 메시지 출력

        Args:
            inMessage: 출력할 로그 메시지
        """
        self._logger.error(inMessage)

    def critical(self, inMessage: str) -> None:
        """치명적 에러 레벨 로그 메시지 출력

        Args:
            inMessage: 출력할 로그 메시지
        """
        self._logger.critical(inMessage)

    def exception(self, inMessage: str) -> None:
        """예외 정보를 포함한 에러 로그 메시지 출력

        현재 예외의 traceback 정보를 함께 기록합니다.
        try-except 블록 내에서 호출해야 합니다.

        Args:
            inMessage: 출력할 로그 메시지

        Example:
            >>> try:
            ...     raise ValueError("테스트 예외")
            ... except ValueError:
            ...     logger.exception("예외 발생")
        """
        self._logger.exception(inMessage)

    def remove_handlers(self) -> None:
        """등록된 모든 핸들러 제거

        Logger 인스턴스가 더 이상 필요하지 않을 때 호출하여
        파일 핸들러를 정리합니다.
        """
        for handlerId in self._handlerIds:
            try:
                logger.remove(handlerId)
            except ValueError:
                # 이미 제거된 핸들러인 경우 무시
                pass
        self._handlerIds.clear()
