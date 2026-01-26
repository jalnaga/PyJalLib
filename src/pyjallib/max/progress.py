#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Progress 모듈 - 3ds Max 작업 진행 상황 표시 관련 기능 제공
"""


class Progress:
    """
    3ds Max 작업 진행 상황 표시 관련 기능을 제공하는 클래스.
    """
    def __init__(self, inTaskName: str, inTotalSteps: int = 0):
        """
        클래스 초기화
        """
        self.taskName = inTaskName
        self.currentStep = 0
        self.totalSteps = inTotalSteps
        self.currentPercent = 0

    def update(self, inCurrentStep: int) -> int:
        """
        현재 진행율(%)을 반환합니다.
        """
        if self.totalSteps == 0:
            self.currentStep = inCurrentStep % 100
            self.currentPercent = int(self.currentStep)
        else:
            self.currentStep = inCurrentStep
            self.currentPercent = int((self.currentStep / self.totalSteps) * 100)
        return self.currentPercent
    
    def reset(self):
        """
        진행 상태를 초기화합니다.
        """
        self.currentStep = 0
        self.currentPercent = 0
