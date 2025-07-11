#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 모듈 로깅 설정 모듈
메인 Logger 클래스를 상속하여 UE5 전용 기능을 추가합니다.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from pyjallib.logger import Logger


class UE5LogHandler(logging.Handler):
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


class UE5Logger(Logger):
    """UE5 전용 로거 클래스 - 메인 Logger 클래스를 상속하여 UE5 기능을 추가"""
    
    def __init__(self, inLogPath: Optional[str] = None, inLogFileName: Optional[str] = None, 
                 inEnableConsole: bool = True, inEnableUE5: bool = True):
        """UE5 로거 인스턴스 초기화
        
        Args:
            inLogPath (str, optional): 로그 파일 저장 경로. 
                                     None인 경우 기본 경로 사용 (Documents/PyJalLib/logs)
            inLogFileName (str, optional): 로그 파일명 (확장자 제외). 
                                         None인 경우 기본값 "ue5_module" 사용
                                         실제 파일명은 "YYYYMMDD_파일명.log" 형식으로 생성
            inEnableConsole (bool): 콘솔 출력 활성화 여부 (기본값: True)
            inEnableUE5 (bool): UE5 출력 활성화 여부 (기본값: True)
        """
        # UE5 기본 파일명 설정
        if inLogFileName is None:
            inLogFileName = "ue5_module"
            
        # 부모 클래스 초기화
        super().__init__(inLogPath, inLogFileName, inEnableConsole)
        
        # UE5 핸들러 설정
        self._enableUE5 = inEnableUE5
        if self._enableUE5:
            self._add_ue5_handler()
    
    def set_ue5_log_level(self, inLevel: str):
        """
        UE5 출력의 로깅 레벨을 설정합니다.
        
        Args:
            inLevel (str): 로깅 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
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
    
    def enable_ue5_output(self, inEnable: bool = True):
        """
        UE5 출력을 활성화/비활성화합니다.
        
        Args:
            inEnable (bool): UE5 출력 활성화 여부
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
    
    def _add_ue5_handler(self):
        """UE5 핸들러를 로거에 추가"""
        try:
            ue5_handler = UE5LogHandler()
            ue5_handler.setLevel(logging.INFO)  # UE5에서는 INFO 이상만 표시
            ue5_handler.setFormatter(self._get_formatter())
            self._logger.addHandler(ue5_handler)
        except Exception:
            # UE5 핸들러 생성 실패 시 무시
            pass
    
    def _remove_ue5_handler(self):
        """UE5 핸들러를 로거에서 제거"""
        for handler in self._logger.handlers[:]:
            if isinstance(handler, UE5LogHandler):
                self._logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
    
    def _log_separator(self, inMessage: str) -> None:
        """구분선 메시지를 모든 핸들러에 직접 출력 (UE5 핸들러 포함)"""
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
                    if isinstance(handler, UE5LogHandler):
                        # UE5 핸들러의 경우 직접 emit 호출
                        handler.emit(separator_record)
                    elif hasattr(handler, 'stream'):
                        # 구분선만 특별한 포맷으로 출력
                        handler.stream.write(inMessage + "\n")
                        if hasattr(handler, 'flush'):
                            handler.flush()
            except Exception:
                # 핸들러 오류 시 무시
                pass


# 편의를 위한 전역 UE5 로거 인스턴스
ue5_logger = UE5Logger()

# 호환성을 위한 기존 함수들
def set_log_level(inLevel: str):
    """
    UE5 모듈의 로깅 레벨을 설정합니다.
    
    Args:
        inLevel (str): 로깅 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
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

def set_ue5_log_level(inLevel: str):
    """
    UE5 출력의 로깅 레벨을 설정합니다.
    
    Args:
        inLevel (str): 로깅 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    ue5_logger.set_ue5_log_level(inLevel)

def get_log_file_path():
    """
    현재 로그 파일의 경로를 반환합니다.
    
    Returns:
        str: 로그 파일의 절대 경로
    """
    documents_path = Path.home() / "Documents"
    log_folder = documents_path / "PyJalLib" / "logs"
    current_date = datetime.now().strftime("%Y%m%d")
    log_filename = f"{current_date}_ue5_module.log"
    return str(log_folder / log_filename)

def set_log_file_path(inLogFolder: str = None, inLogFilename: str = None):
    """
    로그 파일의 경로를 동적으로 변경합니다.
    
    Args:
        inLogFolder (str, optional): 로그 폴더 경로. None인 경우 기본 Documents/PyJalLib/logs 사용
        inLogFilename (str, optional): 로그 파일명. None인 경우 기본 날짜 기반 파일명 사용
    """
    # 새로운 UE5Logger 인스턴스 생성
    global ue5_logger
    
    # 기존 로거 정리
    ue5_logger.close()
    
    # 새로운 로거 생성
    ue5_logger = UE5Logger(inLogPath=inLogFolder, inLogFileName=inLogFilename)
    ue5_logger.info(f"로그 파일 경로가 변경되었습니다.")

# 로깅 설정 완료 메시지
ue5_logger.info("UE5 모듈 로깅 시스템 초기화 완료") 