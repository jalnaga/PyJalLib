#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib 로깅 모듈 - Python 표준 logging 기반

외부 의존성 없이 Python 표준 ``logging`` 모듈만으로 파일/콘솔 로깅을 제공합니다.
UE5/3ds Max 등 추가 패키지를 설치할 수 없는 DCC 내장 Python 환경에서도
동일하게 동작합니다.

자동 제공 기능:
    - 타임스탬프/레벨 자동 포맷 (``%Y-%m-%d %H:%M:%S [LEVEL] 메시지``)
    - 일자별 로그 파일 롤오버 + 7일 보관 (TimedRotatingFileHandler)
    - UTF-8 인코딩 (한글 로그 보존)
    - 인스턴스별 named logger 격리 (멀티 인스턴스 간 로그 혼선/콘솔 중복 차단)
"""

import sys
import uuid
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


class Logger:
    """PyJalLib 로깅 클래스 - 표준 logging 기반

    표준 ``logging`` 모듈을 기반으로 파일 및 콘솔 로깅을 제공합니다.
    각 인스턴스는 고유 이름(`pyjallib.{logFileName}.{uuid}`)의 named logger를
    사용하고 ``propagate = False``로 설정하여, 인스턴스 간 로그 혼선과
    콘솔 중복 출력을 구조적으로 차단합니다.

    Attributes:
        _logPath (Path): 로그 파일 저장 경로
        _logFileName (str): 로그 파일명 (확장자 제외)
        _enableConsole (bool): 콘솔 출력 활성화 여부
        _logLevel (str): 로깅 레벨
        _instanceId (str): Logger 인스턴스 고유 ID (named logger 격리용)
        _handlers (list): 이 인스턴스에 부착된 핸들러 객체 목록
        _logger: 인스턴스별 고유 이름의 logging.Logger 객체

    Example:
        >>> logger = Logger()
        >>> logger.info("정보 메시지")
        >>> logger.error("에러 메시지")
    """

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

        # 인스턴스 고유 ID 생성 (named logger 격리용)
        self._instanceId = str(uuid.uuid4())

        # 부착된 핸들러 객체 목록
        self._handlers: list[logging.Handler] = []

        # 인스턴스별 고유 이름의 named logger 획득
        # 고유 uuid가 이름에 포함되므로 다른 인스턴스와 절대 공유되지 않는다.
        self._logger = logging.getLogger(
            f"pyjallib.{self._logFileName}.{self._instanceId}"
        )
        self._logger.setLevel(self._logLevel)
        # 루트 로거로의 전파를 차단하여 콘솔 중복/타 인스턴스 혼선을 방지한다.
        self._logger.propagate = False

        # 핸들러 설정
        self._setup_logger()

    def _setup_logger(self) -> None:
        """logging 핸들러 설정

        - 파일 핸들러: 항상 활성화. 일자별 롤오버 + 7일 보관.
        - 콘솔 핸들러: inEnableConsole에 따라 결정.

        두 핸들러는 공통 Formatter(타임스탬프 + 레벨 + 메시지)를 사용하며,
        인스턴스 고유 named logger에만 부착되므로 인스턴스 간 격리가 보장된다.
        """
        # 공통 포맷터: 타임스탬프 + 레벨 + 메시지
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 파일 핸들러 설정 (일자별 롤오버 + 7일 보관)
        # 매일 자정 새 파일로 롤오버하고, 7일 지난 백업 파일은 자동 삭제한다.
        logFilePath = self._logPath / f"{self._logFileName}.log"
        fileHandler = TimedRotatingFileHandler(
            str(logFilePath),
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        # 롤오버된 백업 파일명에 일자가 드러나도록 suffix 지정 (예: pyjallib.log.20260617)
        fileHandler.suffix = "%Y%m%d"
        fileHandler.setLevel(self._logLevel)
        fileHandler.setFormatter(formatter)
        self._logger.addHandler(fileHandler)
        self._handlers.append(fileHandler)

        # 콘솔 핸들러 설정 (선택사항)
        if self._enableConsole:
            consoleHandler = logging.StreamHandler(sys.stderr)
            consoleHandler.setLevel(self._logLevel)
            consoleHandler.setFormatter(formatter)
            self._logger.addHandler(consoleHandler)
            self._handlers.append(consoleHandler)

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
        파일 핸들러를 정리합니다(파일 핸들 누수 방지).
        """
        for handler in self._handlers:
            try:
                self._logger.removeHandler(handler)
                handler.close()
            except Exception:
                # 이미 제거/닫힌 핸들러인 경우 무시
                pass
        self._handlers.clear()
