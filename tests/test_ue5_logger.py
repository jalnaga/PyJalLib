#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5Logger 독립 클래스 테스트

UE5Logger가 pyjallib.Logger 상속 없이 독립적으로 동작하는지 검증합니다.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from pyjallib.ue5.logger import (
    UE5Logger,
    UE5LogHandler,
    ue5_logger,
    set_log_level,
    set_ue5_log_level,
    get_log_file_path,
)


class TestUE5LoggerIndependence:
    """UE5Logger 독립성 테스트"""

    def test_ue5logger_does_not_inherit_pyjallib_logger(self):
        """UE5Logger가 pyjallib.Logger를 상속하지 않는지 확인"""
        # pyjallib.Logger를 import 시도
        from pyjallib.logger import Logger as PyJalLibLogger
        
        # UE5Logger의 MRO(Method Resolution Order)에 PyJalLibLogger가 없어야 함
        assert PyJalLibLogger not in UE5Logger.__mro__
        
    def test_ue5logger_uses_standard_logging(self):
        """UE5Logger가 표준 logging 모듈을 사용하는지 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False)
            
            # 내부 로거가 표준 logging.Logger 인스턴스인지 확인
            assert isinstance(logger._logger, logging.Logger)
            
            logger.close()


class TestUE5LoggerInstantiation:
    """UE5Logger 인스턴스 생성 테스트"""

    def test_create_with_defaults(self):
        """기본값으로 인스턴스 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False)
            
            assert logger._logPath == Path(tmpdir)
            assert logger._logFileName == "ue5"
            assert logger._enableConsole is True
            assert logger._enableUE5 is False
            assert logger._logLevel == "DEBUG"
            
            logger.close()
    
    def test_create_with_custom_values(self):
        """사용자 지정 값으로 인스턴스 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(
                inLogPath=tmpdir,
                inLogFileName="custom_log",
                inEnableConsole=False,
                inEnableUE5=False,
                inLogLevel="WARNING"
            )
            
            assert logger._logFileName == "custom_log"
            assert logger._enableConsole is False
            assert logger._logLevel == "WARNING"
            
            logger.close()
    
    def test_log_directory_created(self):
        """로그 디렉토리가 자동 생성되는지 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "nested" / "log" / "dir"
            logger = UE5Logger(inLogPath=str(log_path), inEnableUE5=False)
            
            assert log_path.exists()
            assert log_path.is_dir()
            
            logger.close()


class TestUE5LoggerLoggingMethods:
    """UE5Logger 로깅 메서드 테스트"""

    def test_debug_method(self):
        """debug() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            # 예외 없이 호출되어야 함
            logger.debug("디버그 메시지")
            
            logger.close()
    
    def test_info_method(self):
        """info() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            logger.info("정보 메시지")
            
            logger.close()
    
    def test_warning_method(self):
        """warning() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            logger.warning("경고 메시지")
            
            logger.close()
    
    def test_error_method(self):
        """error() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            logger.error("에러 메시지")
            
            logger.close()
    
    def test_critical_method(self):
        """critical() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            logger.critical("치명적 에러 메시지")
            
            logger.close()
    
    def test_exception_method(self):
        """exception() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            try:
                raise ValueError("테스트 예외")
            except ValueError:
                logger.exception("예외 발생")
            
            logger.close()


class TestUE5LoggerFileOutput:
    """UE5Logger 파일 출력 테스트"""

    def test_log_file_created(self):
        """로그 파일이 생성되는지 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(
                inLogPath=tmpdir, 
                inLogFileName="test_log",
                inEnableUE5=False,
                inEnableConsole=False
            )
            
            # 로그 메시지 출력
            logger.info("테스트 메시지")
            logger.close()
            
            # 로그 파일 확인
            current_date = datetime.now().strftime("%Y%m%d")
            expected_filename = f"test_log_{current_date}.log"
            log_file = Path(tmpdir) / expected_filename
            
            assert log_file.exists()
    
    def test_log_file_content(self):
        """로그 파일에 내용이 기록되는지 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(
                inLogPath=tmpdir,
                inLogFileName="content_test",
                inEnableUE5=False,
                inEnableConsole=False
            )
            
            test_message = "로그 파일 내용 테스트 메시지"
            logger.info(test_message)
            logger.close()
            
            # 로그 파일 읽기
            current_date = datetime.now().strftime("%Y%m%d")
            log_file = Path(tmpdir) / f"content_test_{current_date}.log"
            
            content = log_file.read_text(encoding="utf-8")
            assert test_message in content
    
    def test_log_file_path_format(self):
        """로그 파일 경로 형식 확인 (파일명_{YYYYMMDD}.log)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(
                inLogPath=tmpdir,
                inLogFileName="format_test",
                inEnableUE5=False
            )
            
            log_path = logger.get_log_file_path()
            current_date = datetime.now().strftime("%Y%m%d")
            
            assert f"format_test_{current_date}.log" in log_path
            
            logger.close()


class TestUE5LoggerRemoveHandlers:
    """remove_handlers() 메서드 테스트"""

    def test_remove_handlers_clears_all_handlers(self):
        """remove_handlers()가 모든 핸들러를 제거하는지 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(
                inLogPath=tmpdir,
                inEnableUE5=True,  # UE5 핸들러도 추가
                inEnableConsole=True
            )
            
            # 핸들러가 있는지 확인
            assert len(logger._logger.handlers) > 0
            
            # 핸들러 제거
            logger.remove_handlers()
            
            # 모든 핸들러가 제거되었는지 확인
            assert len(logger._logger.handlers) == 0
    
    def test_close_is_alias_for_remove_handlers(self):
        """close()가 remove_handlers()의 별칭인지 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False)
            
            assert len(logger._logger.handlers) > 0
            
            logger.close()
            
            assert len(logger._logger.handlers) == 0


class TestUE5LogHandler:
    """UE5LogHandler 테스트"""

    def test_ue5_log_handler_emit_without_unreal(self):
        """unreal 모듈 없이 emit() 호출 시 표준 출력 사용"""
        handler = UE5LogHandler()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="테스트 메시지",
            args=(),
            exc_info=None
        )
        
        # 예외 없이 호출되어야 함 (unreal 없으면 print로 출력)
        handler.emit(record)


class TestUE5SpecificMethods:
    """UE5 전용 메서드 테스트"""

    def test_set_ue5_log_level(self):
        """set_ue5_log_level() 메서드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=True, inEnableConsole=False)
            
            # UE5 핸들러가 있는지 확인
            ue5_handlers = [h for h in logger._logger.handlers if isinstance(h, UE5LogHandler)]
            assert len(ue5_handlers) > 0
            
            # 레벨 변경
            logger.set_ue5_log_level("ERROR")
            
            # 레벨이 변경되었는지 확인
            for handler in logger._logger.handlers:
                if isinstance(handler, UE5LogHandler):
                    assert handler.level == logging.ERROR
            
            logger.close()
    
    def test_enable_ue5_output_enable(self):
        """enable_ue5_output(True) 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=False, inEnableConsole=False)
            
            # 초기에는 UE5 핸들러가 없음
            ue5_handlers = [h for h in logger._logger.handlers if isinstance(h, UE5LogHandler)]
            assert len(ue5_handlers) == 0
            
            # UE5 출력 활성화
            logger.enable_ue5_output(True)
            
            # UE5 핸들러가 추가됨
            ue5_handlers = [h for h in logger._logger.handlers if isinstance(h, UE5LogHandler)]
            assert len(ue5_handlers) == 1
            
            logger.close()
    
    def test_enable_ue5_output_disable(self):
        """enable_ue5_output(False) 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = UE5Logger(inLogPath=tmpdir, inEnableUE5=True, inEnableConsole=False)
            
            # 초기에는 UE5 핸들러가 있음
            ue5_handlers = [h for h in logger._logger.handlers if isinstance(h, UE5LogHandler)]
            assert len(ue5_handlers) == 1
            
            # UE5 출력 비활성화
            logger.enable_ue5_output(False)
            
            # UE5 핸들러가 제거됨
            ue5_handlers = [h for h in logger._logger.handlers if isinstance(h, UE5LogHandler)]
            assert len(ue5_handlers) == 0
            
            logger.close()


class TestModuleLevelFunctions:
    """모듈 레벨 함수 테스트"""

    def test_global_ue5_logger_exists(self):
        """전역 ue5_logger 인스턴스가 존재하는지 확인"""
        assert ue5_logger is not None
        assert isinstance(ue5_logger, UE5Logger)
    
    def test_set_log_level_function(self):
        """set_log_level() 함수 테스트"""
        # 예외 없이 호출되어야 함
        set_log_level("INFO")
        set_log_level("DEBUG")
    
    def test_set_ue5_log_level_function(self):
        """set_ue5_log_level() 함수 테스트"""
        # 예외 없이 호출되어야 함
        set_ue5_log_level("WARNING")
    
    def test_get_log_file_path_function(self):
        """get_log_file_path() 함수 테스트"""
        path = get_log_file_path()
        
        assert path is not None
        assert isinstance(path, str)
        assert ".log" in path


class TestUE5LoggerAPICompatibility:
    """UE5Logger API 호환성 테스트 (pyjallib.Logger와 동일한 API)"""

    def test_has_debug_method(self):
        """debug 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'debug')
        assert callable(getattr(UE5Logger, 'debug'))
    
    def test_has_info_method(self):
        """info 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'info')
        assert callable(getattr(UE5Logger, 'info'))
    
    def test_has_warning_method(self):
        """warning 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'warning')
        assert callable(getattr(UE5Logger, 'warning'))
    
    def test_has_error_method(self):
        """error 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'error')
        assert callable(getattr(UE5Logger, 'error'))
    
    def test_has_critical_method(self):
        """critical 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'critical')
        assert callable(getattr(UE5Logger, 'critical'))
    
    def test_has_exception_method(self):
        """exception 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'exception')
        assert callable(getattr(UE5Logger, 'exception'))
    
    def test_has_remove_handlers_method(self):
        """remove_handlers 메서드 존재 확인"""
        assert hasattr(UE5Logger, 'remove_handlers')
        assert callable(getattr(UE5Logger, 'remove_handlers'))

