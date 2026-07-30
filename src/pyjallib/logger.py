#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib 로깅 모듈 - Python 표준 logging 기반

외부 의존성 없이 Python 표준 ``logging`` 모듈만으로 파일/콘솔 로깅을 제공합니다.
UE5/3ds Max 등 추가 패키지를 설치할 수 없는 DCC 내장 Python 환경에서도
동일하게 동작합니다.

자동 제공 기능:
    - 타임스탬프/레벨 자동 포맷 (``%Y-%m-%d %H:%M:%S [LEVEL] 메시지``)
    - 일자 파일명 + 자정 롤오버 + 7일 보관 (``{파일명}_{YYYYMMDD}.log``)
    - UTF-8 인코딩 (한글 로그 보존)
    - 인스턴스별 named logger 격리 (멀티 인스턴스 간 로그 혼선/콘솔 중복 차단)
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

# 로그 파일명에 붙는 일자 포맷 (예: AnimExporter_20260730.log)
_LOG_DATE_FORMAT = "%Y%m%d"


class DatedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """활성 로그 파일명에 일자를 담고, 자정마다 새 일자 파일로 넘어가는 핸들러.

    표준 ``TimedRotatingFileHandler``는 활성 파일을 고정 이름(``{name}.log``)으로 두고
    롤오버 시 ``{name}.log.{YYYYMMDD}``로 rename한다. 반면 이 핸들러는 **활성 파일명
    자체에 일자를 담고**(``{name}_{YYYYMMDD}.log``), 롤오버 시 rename 없이 다음 일자
    파일로 전환한다. 결과적으로 하루에 파일 하나가 남는다.

    왜 이 규약인가 (2026-07-30):
        프로덕션(DevStorage에 배포된 3ds Max 툴)의 로그 수집 관행이 ``{name}_{날짜}.log``
        이름에 맞춰져 있다. 2026-06-17 loguru -> 표준 logging 전환에서 파일명이
        ``{name}.log`` + 백업 ``.log.{YYYYMMDD}``로 바뀌었는데, **파일명 규약만** 구
        형태로 되돌린다. loguru로 되돌리는 것이 아니라 표준 logging으로 같은 이름을
        재현하는 것이므로, 외부 의존성 0이라는 성질은 유지된다.

    왜 base 이름만 일자로 만들고 표준 핸들러를 그대로 쓰지 않는가:
        생성 시점의 일자로 파일명을 만들어 표준 핸들러에 넘기면, 자정을 넘긴 롤오버가
        그 **굳은 일자 이름**을 백업으로 rename하고 같은 이름을 다시 열어
        ``AnimExporter_20260730.log.20260731`` 같은 산물이 남는다. 긴 DCC 세션에서
        실제로 발생하므로 롤오버 동작 자체를 바꾼다.
    """

    def __init__(
        self,
        inLogDirPath: Path,
        inLogFileName: str,
        inBackupCount: int = 7,
        inEncoding: str = "utf-8",
    ) -> None:
        """일자 파일명 핸들러 초기화

        Args:
            inLogDirPath: 로그 파일을 둘 디렉토리
            inLogFileName: 일자 앞에 붙는 기본 파일명 (확장자·일자 제외)
            inBackupCount: 보관할 과거 일자 파일 개수. 기본값 7
            inEncoding: 파일 인코딩. 기본값 "utf-8"
        """
        self._logDirPath = Path(inLogDirPath)
        self._logFileBaseName = inLogFileName

        super().__init__(
            self._build_log_file_path(),
            when="midnight",
            backupCount=inBackupCount,
            encoding=inEncoding,
        )

    def _build_log_file_path(self) -> str:
        """오늘 일자를 담은 로그 파일 경로를 만든다.

        Returns:
            ``{로그디렉토리}/{기본파일명}_{YYYYMMDD}.log`` 절대 경로 문자열
        """
        today = datetime.now().strftime(_LOG_DATE_FORMAT)
        return str(self._logDirPath / f"{self._logFileBaseName}_{today}.log")

    def doRollover(self) -> None:
        """자정 롤오버 - rename 없이 새 일자 파일로 전환한다.

        활성 파일명이 이미 일자를 담고 있으므로 백업 rename이 필요 없다. 스트림을 닫고
        새 일자 경로로 ``baseFilename``을 갱신한 뒤 다시 열고, 보관 개수를 넘는 과거
        일자 파일을 정리한다.
        """
        if self.stream is not None:
            self.stream.close()
            self.stream = None

        self.baseFilename = os.path.abspath(self._build_log_file_path())
        if not self.delay:
            self.stream = self._open()

        self._purge_old_log_files()

        # 다음 자정으로 롤오버 시각을 재계산한다.
        self.rolloverAt = self.computeRollover(int(time.time()))

    def _purge_old_log_files(self) -> None:
        """보관 개수를 넘는 과거 일자 파일을 삭제한다.

        일자 파일명은 ``{기본파일명}_{YYYYMMDD}.log``라 사전순 정렬이 곧 시간순이다.
        활성 파일은 보관 개수에 포함하지 않는다(표준 핸들러의 ``backupCount``가 활성
        ``{name}.log``를 세지 않는 것과 같은 의미).
        """
        if self.backupCount <= 0:
            return

        datedFilePaths = sorted(self._logDirPath.glob(f"{self._logFileBaseName}_*.log"))

        # 활성 파일 1개 + 백업 backupCount개를 남기고 나머지를 지운다.
        keepCount = self.backupCount + 1
        if len(datedFilePaths) <= keepCount:
            return

        for oldFilePath in datedFilePaths[:-keepCount]:
            try:
                oldFilePath.unlink()
            except OSError:
                # 다른 프로세스가 잡고 있으면 다음 롤오버에서 다시 시도한다.
                pass


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

        # 파일 핸들러 설정 (일자 파일명 + 자정 롤오버 + 7일 보관)
        # 활성 파일명 자체가 일자를 담으므로(예: pyjallib_20260730.log) 하루에 파일 하나가
        # 남는다. 프로덕션 로그 수집 관행에 맞춘 규약이다(DatedTimedRotatingFileHandler 참조).
        fileHandler = DatedTimedRotatingFileHandler(
            self._logPath,
            self._logFileName,
            inBackupCount=7,
            inEncoding="utf-8",
        )
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
