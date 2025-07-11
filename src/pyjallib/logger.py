#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib 중앙 집중식 로깅 모듈
모든 PyJalLib 모듈에서 사용할 수 있는 통합 로깅 시스템을 제공합니다.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from pyjallib.exceptions import PyJalLibError


class Logger:
    """PyJalLib 간단한 로깅 클래스"""
    
    def __init__(self, inLogPath: Optional[str] = None, inLogFileName: Optional[str] = None, inEnableConsole: bool = True):
        """로거 인스턴스 초기화
        
        Args:
            inLogPath (str, optional): 로그 파일 저장 경로. 
                                     None인 경우 기본 경로 사용 (Documents/PyJalLib/logs)
            inLogFileName (str, optional): 로그 파일명 (확장자 제외). 
                                         None인 경우 기본값 "pyjallib" 사용
                                         실제 파일명은 "YYYYMMDD_파일명.log" 형식으로 생성
            inEnableConsole (bool): 콘솔 출력 활성화 여부 (기본값: True)
        """
        # 기본 로그 경로 설정
        if inLogPath is None:
            documents_path = Path.home() / "Documents"
            self._logPath = documents_path / "PyJalLib" / "logs"
        else:
            self._logPath = Path(inLogPath)
            
        # 로그 디렉토리 생성
        self._logPath.mkdir(parents=True, exist_ok=True)
        
        # 로그 파일명 설정 (확장자 제외)
        self._logFileName = inLogFileName if inLogFileName is not None else "pyjallib"
        
        # 출력 옵션 설정
        self._enableConsole = inEnableConsole
        self._sessionName = None  # 초기에는 세션 없음
        
        # 로거 생성 및 설정
        self._logger = logging.getLogger(f"pyjallib_{id(self)}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()  # 기존 핸들러 제거
        self._setup_handlers()
    
    def debug(self, inMessage: str) -> None:
        """디버그 레벨 로그 메시지"""
        self._logger.debug(inMessage)
        
    def info(self, inMessage: str) -> None:
        """정보 레벨 로그 메시지"""
        self._logger.info(inMessage)
        
    def warning(self, inMessage: str) -> None:
        """경고 레벨 로그 메시지"""
        self._logger.warning(inMessage)
        
    def error(self, inMessage: str) -> None:
        """에러 레벨 로그 메시지"""
        self._logger.error(inMessage)
        
    def critical(self, inMessage: str) -> None:
        """치명적 에러 레벨 로그 메시지"""
        self._logger.critical(inMessage)
        
    def set_session(self, inSessionName: str) -> None:
        """새로운 로깅 세션 설정 및 시작
        
        Args:
            inSessionName (str): 세션 구분용 이름
        """
        # 기존 세션이 있다면 종료
        if self._sessionName is not None:
            self.end_session()
            
        # 새 세션 시작
        self._sessionName = inSessionName
        separator_msg = f"===== {self._sessionName} 로깅 시작 ====="
        self._log_separator(separator_msg)
        
    def end_session(self) -> None:
        """현재 로깅 세션 종료 구분선 출력"""
        if self._sessionName is not None:
            separator_msg = f"===== {self._sessionName} 로깅 끝 ====="
            self._log_separator(separator_msg)
            self._sessionName = None
            
    def close(self) -> None:
        """로거 핸들러들을 명시적으로 닫기"""
        for handler in self._logger.handlers[:]:
            try:
                handler.close()
                self._logger.removeHandler(handler)
            except Exception:
                pass
    
    def log_exception(self, inException: Exception, inCustomMessage: Optional[str] = None) -> None:
        """예외 정보를 로그에 기록
        
        Args:
            inException (Exception): 기록할 예외 객체
            inCustomMessage (str, optional): 사용자 정의 메시지. None인 경우 예외 메시지만 기록
        """
        if inCustomMessage:
            message = f"{inCustomMessage}: {inException}"
        else:
            message = str(inException)
        
        self._logger.error(message)
    
    def log_pyjallib_error(self, inError: PyJalLibError, inCustomMessage: Optional[str] = None) -> None:
        """PyJalLib 예외를 로그에 기록 (함수명 포함)
        
        Args:
            inError (PyJalLibError): PyJalLib 예외 객체
            inCustomMessage (str, optional): 사용자 정의 메시지
        """
        # PyJalLibError는 이미 함수명이 포함된 메시지를 반환
        if inCustomMessage:
            message = f"{inCustomMessage}: {inError}"
        else:
            message = str(inError)
        
        self._logger.error(message)
    
    def log_function_error(self, inFunctionName: str, inMessage: str) -> None:
        """함수명을 포함한 에러 메시지를 로그에 기록
        
        Args:
            inFunctionName (str): 함수명
            inMessage (str): 에러 메시지
        """
        message = f"[{inFunctionName}] {inMessage}"
        self._logger.error(message)
        
    def _log_separator(self, inMessage: str) -> None:
        """구분선 메시지를 모든 핸들러에 직접 출력"""
        # 구분선은 INFO 레벨로 출력하되, 특별한 포맷 사용
        separator_record = logging.LogRecord(
            name=self._logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=inMessage,
            args=(),
            exc_info=None
        )
        
        # 각 핸들러에 직접 전송 (포맷터 우회)
        for handler in self._logger.handlers:
            try:
                # 핸들러 레벨 확인
                if handler.level <= logging.INFO:
                    # 구분선만 특별한 포맷으로 출력
                    if hasattr(handler, 'stream'):
                        handler.stream.write(inMessage + "\n")
                        if hasattr(handler, 'flush'):
                            handler.flush()
            except Exception:
                # 핸들러 오류 시 무시
                pass
        
    def _setup_handlers(self) -> None:
        """로거에 핸들러 설정"""
        # 파일 핸들러 (항상 활성화) - 날짜 기반 파일명
        current_date = datetime.now().strftime("%Y%m%d")
        log_filename = f"{current_date}_{self._logFileName}.log"
        log_file = self._logPath / log_filename
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(self._get_formatter())
        self._logger.addHandler(file_handler)
        
        # 콘솔 핸들러 (선택사항)
        if self._enableConsole:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self._get_formatter())
            self._logger.addHandler(console_handler)
            
    def _get_formatter(self) -> logging.Formatter:
        """표준 포맷터 반환"""
        return logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ) 