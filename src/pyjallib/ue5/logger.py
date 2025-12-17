#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 모듈 로깅 설정 모듈

Python 표준 logging 모듈만 사용하여 UE5 환경에서 독립적으로 동작합니다.
(loguru 의존성 없음 - 언리얼 에디터 내부에서는 외부 패키지 사용 불가)
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class UE5LogHandler(logging.Handler):
    """UE5 전용 로그 핸들러 - UE5의 로그 시스템과 호환되도록 설계"""
    
    def emit(self, record: logging.LogRecord) -> None:
        """로그 레코드를 UE5 로그 시스템으로 전송
        
        Args:
            record: logging.LogRecord 인스턴스
        """
        try:
            # UE5의 unreal.log 함수 사용
            import unreal
            
            # 메시지 포맷팅
            message = self.format(record) if self.formatter else record.getMessage()
            
            # 로그 레벨에 따라 적절한 UE5 로그 함수 호출
            if record.levelno >= logging.ERROR:
                unreal.log_error(f"[PyJalLib] {message}")
            elif record.levelno >= logging.WARNING:
                unreal.log_warning(f"[PyJalLib] {message}")
            elif record.levelno >= logging.INFO:
                unreal.log(f"[PyJalLib] {message}")
            else:  # DEBUG
                unreal.log(f"[PyJalLib-DEBUG] {message}")
                
        except ImportError:
            # unreal 모듈이 없는 경우 표준 출력 사용
            message = self.format(record) if self.formatter else record.getMessage()
            print(f"[PyJalLib] {message}")
        except Exception:
            # 모든 예외를 무시하여 로깅 실패가 애플리케이션을 중단하지 않도록 함
            pass


class UE5Logger:
    """UE5 전용 독립 로거 클래스
    
    Python 표준 logging 모듈만 사용하여 UE5 환경에서 독립적으로 동작합니다.
    pyjallib.Logger와 동일한 API를 제공하지만 loguru 의존성이 없습니다.
    
    Attributes:
        _logPath (Path): 로그 파일 저장 경로
        _logFileName (str): 로그 파일명 (확장자 제외)
        _enableConsole (bool): 콘솔 출력 활성화 여부
        _enableUE5 (bool): UE5 출력 활성화 여부
        _logLevel (str): 로깅 레벨
        _logger (logging.Logger): 내부 표준 로거 인스턴스
    
    Example:
        >>> logger = UE5Logger()
        >>> logger.info("정보 메시지")
        >>> logger.error("에러 메시지")
    """
    
    def __init__(
        self, 
        inLogPath: Optional[str] = None, 
        inLogFileName: Optional[str] = None, 
        inEnableConsole: bool = True, 
        inEnableUE5: bool = True,
        inLogLevel: str = "DEBUG"
    ) -> None:
        """UE5Logger 인스턴스 초기화
        
        Args:
            inLogPath: 로그 파일 저장 경로. 
                       None인 경우 기본 경로 사용 (Documents/PyJalLib/logs/)
            inLogFileName: 로그 파일명 (확장자 제외). 
                           None인 경우 기본값 "ue5" 사용
            inEnableConsole: 콘솔(stderr) 출력 활성화 여부. 기본값 True
            inEnableUE5: UE5 출력 활성화 여부. 기본값 True
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
        
        # 로그 파일명 설정 (기본값: ue5)
        self._logFileName = inLogFileName if inLogFileName is not None else "ue5"
        
        # 출력 옵션 설정
        self._enableConsole = inEnableConsole
        self._enableUE5 = inEnableUE5
        self._logLevel = inLogLevel.upper()
        
        # 표준 logging 설정
        self._logger: logging.Logger = None  # type: ignore
        self._currentLogFilePath: str = ""  # _setup_logger 전에 미리 초기화
        self._setup_logger()
        
        # UE5 핸들러 설정
        if self._enableUE5:
            self._add_ue5_handler()
    
    def _get_formatter(self) -> logging.Formatter:
        """로그 포매터 반환
        
        Returns:
            logging.Formatter: 로그 메시지 포매터
        """
        return logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def _get_log_level(self) -> int:
        """로깅 레벨 문자열을 logging 상수로 변환
        
        Returns:
            int: logging 모듈의 레벨 상수
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(self._logLevel, logging.DEBUG)
    
    def _setup_logger(self) -> None:
        """표준 logging 핸들러 설정
        
        기존 핸들러를 모두 제거하고 새로운 핸들러를 등록합니다.
        - 파일 핸들러: 항상 활성화
        - 콘솔 핸들러: inEnableConsole에 따라 결정
        """
        # 유니크한 로거 이름 생성 (인스턴스별로 독립적인 로거)
        loggerName = f"pyjallib.ue5.{id(self)}"
        self._logger = logging.getLogger(loggerName)
        
        # 기존 핸들러 모두 제거
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
            handler.close()
        
        # 로거 레벨 설정
        self._logger.setLevel(self._get_log_level())
        
        # 부모 로거로 전파 방지
        self._logger.propagate = False
        
        # 포매터 생성
        formatter = self._get_formatter()
        
        # 파일 핸들러 설정
        # 파일명 패턴: {파일명}_{YYYYMMDD}.log
        currentDate = datetime.now().strftime("%Y%m%d")
        logFilePath = self._logPath / f"{self._logFileName}_{currentDate}.log"
        
        fileHandler = logging.FileHandler(
            str(logFilePath),
            encoding="utf-8"
        )
        fileHandler.setLevel(self._get_log_level())
        fileHandler.setFormatter(formatter)
        self._logger.addHandler(fileHandler)
        
        # 현재 로그 파일 경로 저장 (get_log_file_path용)
        self._currentLogFilePath = str(logFilePath)
        
        # 콘솔 핸들러 설정 (선택사항)
        if self._enableConsole:
            consoleHandler = logging.StreamHandler(sys.stderr)
            consoleHandler.setLevel(self._get_log_level())
            consoleHandler.setFormatter(formatter)
            self._logger.addHandler(consoleHandler)
    
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
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    
    def close(self) -> None:
        """로거 종료 및 리소스 정리
        
        remove_handlers()의 별칭입니다.
        """
        self.remove_handlers()
    
    def set_ue5_log_level(self, inLevel: str) -> None:
        """UE5 출력의 로깅 레벨을 설정합니다.
        
        Args:
            inLevel: 로깅 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if inLevel.upper() not in level_map:
            self.warning(f"잘못된 로깅 레벨: {inLevel}. 기본값 INFO로 설정합니다.")
            inLevel = 'INFO'
        
        # UE5 핸들러 찾기
        for handler in self._logger.handlers:
            if isinstance(handler, UE5LogHandler):
                handler.setLevel(level_map[inLevel.upper()])
                self.info(f"UE5 로깅 레벨이 {inLevel.upper()}로 설정되었습니다.")
                return
        
        self.warning("UE5 핸들러를 찾을 수 없습니다.")
    
    def enable_ue5_output(self, inEnable: bool = True) -> None:
        """UE5 출력을 활성화/비활성화합니다.
        
        Args:
            inEnable: UE5 출력 활성화 여부
        """
        if inEnable and not self._enableUE5:
            # UE5 핸들러 추가
            self._add_ue5_handler()
            self._enableUE5 = True
            self.info("UE5 출력이 활성화되었습니다.")
        elif not inEnable and self._enableUE5:
            # UE5 핸들러 제거
            self._remove_ue5_handler()
            self._enableUE5 = False
            self.info("UE5 출력이 비활성화되었습니다.")
    
    def _add_ue5_handler(self) -> None:
        """UE5 핸들러를 로거에 추가"""
        try:
            ue5_handler = UE5LogHandler()
            ue5_handler.setLevel(logging.INFO)  # UE5에서는 INFO 이상만 표시
            ue5_handler.setFormatter(self._get_formatter())
            self._logger.addHandler(ue5_handler)
        except Exception:
            # UE5 핸들러 생성 실패 시 무시
            pass
    
    def _remove_ue5_handler(self) -> None:
        """UE5 핸들러를 로거에서 제거"""
        for handler in self._logger.handlers[:]:
            if isinstance(handler, UE5LogHandler):
                self._logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
    
    def get_log_file_path(self) -> str:
        """현재 로그 파일 경로 반환
        
        Returns:
            str: 현재 로그 파일의 절대 경로
        """
        return self._currentLogFilePath


# 편의를 위한 전역 UE5 로거 인스턴스
ue5_logger = UE5Logger()


# 호환성을 위한 기존 함수들
def set_log_level(inLevel: str) -> None:
    """UE5 모듈의 로깅 레벨을 설정합니다.
    
    Args:
        inLevel: 로깅 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    if inLevel.upper() not in level_map:
        ue5_logger.warning(f"잘못된 로깅 레벨: {inLevel}. 기본값 INFO로 설정합니다.")
        inLevel = 'INFO'
    
    ue5_logger._logger.setLevel(level_map[inLevel.upper()])
    ue5_logger.info(f"로깅 레벨이 {inLevel.upper()}로 설정되었습니다.")


def set_ue5_log_level(inLevel: str) -> None:
    """UE5 출력의 로깅 레벨을 설정합니다.
    
    Args:
        inLevel: 로깅 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    ue5_logger.set_ue5_log_level(inLevel)


def get_log_file_path() -> str:
    """현재 로그 파일의 경로를 반환합니다.
    
    Returns:
        str: 로그 파일의 절대 경로
    """
    return ue5_logger.get_log_file_path()


def set_log_file_path(inLogFolder: Optional[str] = None, inLogFilename: Optional[str] = None) -> None:
    """로그 파일의 경로를 동적으로 변경합니다.
    
    Args:
        inLogFolder: 로그 폴더 경로. None인 경우 기본 Documents/PyJalLib/logs 사용
        inLogFilename: 로그 파일명. None인 경우 기본 날짜 기반 파일명 사용
    """
    # 새로운 UE5Logger 인스턴스 생성
    global ue5_logger
    
    # 기존 로거 정리
    ue5_logger.close()
    
    # 새로운 로거 생성
    ue5_logger = UE5Logger(inLogPath=inLogFolder, inLogFileName=inLogFilename)
    ue5_logger.info("로그 파일 경로가 변경되었습니다.")


# 로깅 설정 완료 메시지
ue5_logger.info("UE5 모듈 로깅 시스템 초기화 완료")
