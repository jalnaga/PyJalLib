#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyJalLib 커스텀 예외 클래스들
라이브러리에서 발생할 수 있는 다양한 예외 상황을 명확히 구분하기 위한 예외 클래스 정의
"""

import inspect
from typing import Optional


class PyJalLibError(Exception):
    """PyJalLib 기본 예외 클래스"""
    
    def __init__(self, inMessage: str, inFunctionName: Optional[str] = None):
        """
        Args:
            inMessage (str): 에러 메시지
            inFunctionName (str, optional): 에러가 발생한 함수명. None인 경우 자동으로 감지 시도
        """
        self.function_name = inFunctionName or self._get_caller_function_name()
        super().__init__(inMessage)
    
    def _get_caller_function_name(self) -> Optional[str]:
        """호출자 함수명을 자동으로 감지"""
        try:
            # 현재 스택에서 호출자 함수명 찾기
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                return frame.f_back.f_back.f_code.co_name
        except Exception:
            pass
        return None
    
    def get_function_name(self) -> Optional[str]:
        """에러가 발생한 함수명 반환"""
        return self.function_name
    
    def __str__(self) -> str:
        """에러 메시지 반환 (함수명 포함)"""
        message = super().__str__()
        if self.function_name:
            return f"[{self.function_name}] {message}"
        return message


class PerforceError(PyJalLibError):
    """Perforce 관련 예외"""
    pass


class ValidationError(PyJalLibError):
    """입력값 검증 실패 예외"""
    pass


class FileOperationError(PyJalLibError):
    """파일 작업 실패 예외"""
    pass


class NamingConfigError(PyJalLibError):
    """NamingConfig 관련 예외"""
    pass


class MaxError(PyJalLibError):
    """3ds Max 관련 예외"""
    pass


class UE5Error(PyJalLibError):
    """UE5 관련 예외"""
    pass 