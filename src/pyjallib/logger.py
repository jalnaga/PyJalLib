#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib 중앙 집중식 로깅 모듈
모든 PyJalLib 모듈에서 사용할 수 있는 통합 로깅 시스템을 제공합니다.
"""

import logging
from pathlib import Path
from typing import Optional


class Logger:
    """PyJalLib 간단한 로깅 클래스"""
    
    def __init__(self, inLogPath: Optional[str] = None, inEnableConsole: bool = True, inEnableUE5: bool = False):
        """로거 인스턴스 초기화
        
        Args:
            inLogPath (str, optional): 로그 파일 저장 경로. 
                                     None인 경우 기본 경로 사용 (Documents/PyJalLib/logs)
            inEnableConsole (bool): 콘솔 출력 활성화 여부 (기본값: True)
            inEnableUE5 (bool): UE5 출력 활성화 여부 (기본값: False)
        """
        # 기본 로그 경로 설정
        if inLogPath is None:
            documents_path = Path.home() / "Documents"
            self._logPath = documents_path / "PyJalLib" / "logs"
        else:
            self._logPath = Path(inLogPath)
            
        # 로그 디렉토리 생성
        self._logPath.mkdir(parents=True, exist_ok=True)
        
        # 출력 옵션 설정
        self._enableConsole = inEnableConsole
        self._enableUE5 = inEnableUE5
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
                    elif isinstance(handler, _UE5LogHandler):
                        # UE5 핸들러의 경우 직접 emit 호출
                        handler.emit(separator_record)
            except Exception:
                # 핸들러 오류 시 무시
                pass
        
    def _setup_handlers(self) -> None:
        """로거에 핸들러 설정"""
        # 파일 핸들러 (항상 활성화)
        log_file = self._logPath / "pyjallib.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(self._get_formatter())
        self._logger.addHandler(file_handler)
        
        # 콘솔 핸들러 (선택사항)
        if self._enableConsole:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self._get_formatter())
            self._logger.addHandler(console_handler)
            
        # UE5 핸들러 (선택사항)
        if self._enableUE5:
            ue5_handler = self._create_ue5_handler()
            if ue5_handler:
                self._logger.addHandler(ue5_handler)
            
    def _get_formatter(self) -> logging.Formatter:
        """표준 포맷터 반환"""
        return logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
    def _create_ue5_handler(self) -> Optional[logging.Handler]:
        """UE5 핸들러 생성 (기존 UE5LogHandler 코드 활용)"""
        try:
            return _UE5LogHandler()
        except Exception:
            # UE5 핸들러 생성 실패 시 None 반환
            return None


class _UE5LogHandler(logging.Handler):
    """UE5 전용 로그 핸들러 - UE5의 로그 시스템과 호환되도록 설계"""
    
    def emit(self, record):
        """로그 레코드를 UE5 로그 시스템으로 전송"""
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