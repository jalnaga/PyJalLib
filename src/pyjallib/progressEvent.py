#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Progress Event System - 범용 진행 상황 이벤트 시스템

모든 pyjallib 모듈에서 사용할 수 있는 범용 이벤트 기반 진행 상황 추적 시스템
"""

from typing import Callable, List


class ProgressEvent:
    """단순한 프로그레스 이벤트 클래스"""
    
    def __init__(self):
        """프로그레스 이벤트 초기화"""
        self.eventListeners: List[Callable[[str, int, int], None]] = []
        self.isCancelled = False
    
    def add_listener(self, inListener: Callable[[str, int, int], None]) -> None:
        """
        프로그레스 리스너 추가
        
        Args:
            inListener: 프로그레스 업데이트를 받을 콜백 함수 (taskName, currentStep, totalSteps)
        """
        if inListener not in self.eventListeners:
            self.eventListeners.append(inListener)
    
    def remove_listener(self, inListener: Callable[[str, int, int], None]) -> None:
        """
        프로그레스 리스너 제거
        
        Args:
            inListener: 제거할 콜백 함수
        """
        if inListener in self.eventListeners:
            self.eventListeners.remove(inListener)
    
    def clear_listeners(self) -> None:
        """모든 프로그레스 리스너 제거"""
        self.eventListeners.clear()
    
    def update_progress(self, inTaskName: str, inCurrentStep: int, inTotalSteps: int) -> None:
        """
        프로그레스 업데이트 이벤트 발생
        
        Args:
            inTaskName: 현재 작업명
            inCurrentStep: 현재 단계
            inTotalSteps: 전체 단계 수
        """
        # 모든 리스너에게 이벤트 전달
        for listener in self.eventListeners:
            try:
                listener(inTaskName, inCurrentStep, inTotalSteps)
            except Exception as e:
                # 리스너 에러는 로그만 남기고 무시 (안정성 보장)
                print(f"Progress listener error: {e}")
    
    def cancel_progress(self) -> None:
        """진행 상황 취소 요청"""
        self.isCancelled = True
    
    def is_cancelled(self) -> bool:
        """취소 상태 확인"""
        return self.isCancelled
    
    def reset_cancel_state(self) -> None:
        """취소 상태 초기화"""
        self.isCancelled = False


 