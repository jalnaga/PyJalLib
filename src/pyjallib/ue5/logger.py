#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 모듈 로깅 설정 모듈
UE5 모듈의 중앙 집중식 로깅 시스템을 관리합니다.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

class UE5LogHandler(logging.Handler):
    """UE5 전용 로그 핸들러 - UE5의 로그 시스템과 호환되도록 설계"""
    
    def emit(self, record):
        """로그 레코드를 UE5 로그 시스템으로 전송"""
        try:
            # UE5의 unreal.log 함수 사용
            import unreal
            
            # 로그 레벨에 따라 적절한 UE5 로그 함수 호출
            if record.levelno >= logging.ERROR:
                unreal.log_error(f"[PyJalLib] {record.getMessage()}")
            elif record.levelno >= logging.WARNING:
                unreal.log_warning(f"[PyJalLib] {record.getMessage()}")
            elif record.levelno >= logging.INFO:
                unreal.log(f"[PyJalLib] {record.getMessage()}")
            else:  # DEBUG
                unreal.log(f"[PyJalLib-DEBUG] {record.getMessage()}")
                
        except ImportError:
            # unreal 모듈이 없는 경우 표준 출력 사용
            print(f"[PyJalLib] {record.getMessage()}")
        except Exception:
            # 모든 예외를 무시하여 로깅 실패가 애플리케이션을 중단하지 않도록 함
            pass

def _setup_ue5_logging():
    """UE5 모듈의 중앙 집중식 로깅 설정"""
    
    # Documents 폴더 경로 가져오기
    documents_path = Path.home() / "Documents"
    log_folder = documents_path / "PyJalLib" / "logs"
    
    # 로그 폴더 생성
    log_folder.mkdir(parents=True, exist_ok=True)
    
    # 로그 파일명 생성 (날짜 포함)
    current_date = datetime.now().strftime("%Y%m%d")
    log_filename = f"ue5_module_{current_date}.log"
    log_file_path = log_folder / log_filename
    
    # UE5 모듈 전용 로거 생성
    ue5_logger = logging.getLogger('pyjallib.ue5')
    ue5_logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in ue5_logger.handlers[:]:
        ue5_logger.removeHandler(handler)
    
    # 파일 핸들러 설정 (UTF-8 인코딩)
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # UE5 전용 핸들러 설정
    ue5_handler = UE5LogHandler()
    ue5_handler.setLevel(logging.INFO)  # UE5에서는 INFO 이상만 표시
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    ue5_handler.setFormatter(formatter)
    
    # 핸들러 추가
    ue5_logger.addHandler(file_handler)
    ue5_logger.addHandler(ue5_handler)
    
    # 로거가 상위 로거로 전파되지 않도록 설정
    ue5_logger.propagate = False
    
    return ue5_logger

# 로깅 설정 실행
ue5_logger = _setup_ue5_logging()

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
    
    ue5_logger.setLevel(level_map[inLevel.upper()])
    ue5_logger.info(f"로깅 레벨이 {inLevel.upper()}로 설정되었습니다.")

def set_ue5_log_level(inLevel: str):
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
        ue5_logger.warning(f"잘못된 로깅 레벨: {inLevel}. 기본값 INFO로 설정합니다.")
        inLevel = 'INFO'
    
    # UE5 핸들러 찾기
    for handler in ue5_logger.handlers:
        if isinstance(handler, UE5LogHandler):
            handler.setLevel(level_map[inLevel.upper()])
            ue5_logger.info(f"UE5 로깅 레벨이 {inLevel.upper()}로 설정되었습니다.")
            return
    
    ue5_logger.warning("UE5 핸들러를 찾을 수 없습니다.")

def get_log_file_path():
    """
    현재 로그 파일의 경로를 반환합니다.
    
    Returns:
        str: 로그 파일의 절대 경로
    """
    documents_path = Path.home() / "Documents"
    log_folder = documents_path / "PyJalLib" / "logs"
    current_date = datetime.now().strftime("%Y%m%d")
    log_filename = f"ue5_module_{current_date}.log"
    return str(log_folder / log_filename)

def set_log_file_path(inLogFolder: str = None, inLogFilename: str = None):
    """
    로그 파일의 경로를 동적으로 변경합니다.
    
    Args:
        inLogFolder (str, optional): 로그 폴더 경로. None인 경우 기본 Documents/PyJalLib/logs 사용
        inLogFilename (str, optional): 로그 파일명. None인 경우 기본 날짜 기반 파일명 사용
    """
    # 기본값 설정
    if inLogFolder is None:
        documents_path = Path.home() / "Documents"
        inLogFolder = str(documents_path / "PyJalLib" / "logs")
    
    if inLogFilename is None:
        current_date = datetime.now().strftime("%Y%m%d")
        inLogFilename = f"ue5_module_{current_date}.log"
    
    # 경로 생성
    log_folder = Path(inLogFolder)
    log_folder.mkdir(parents=True, exist_ok=True)
    log_file_path = log_folder / inLogFilename
    
    # 기존 파일 핸들러 제거
    for handler in ue5_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            ue5_logger.removeHandler(handler)
            handler.close()
    
    # 새로운 파일 핸들러 생성
    new_file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    new_file_handler.setLevel(logging.DEBUG)
    
    # 포맷터 설정 (기존과 동일)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    new_file_handler.setFormatter(formatter)
    
    # 새 핸들러 추가
    ue5_logger.addHandler(new_file_handler)
    
    ue5_logger.info(f"로그 파일 경로가 변경되었습니다: {log_file_path}")

# 로깅 설정 완료 메시지
ue5_logger.info("UE5 모듈 로깅 시스템 초기화 완료") 