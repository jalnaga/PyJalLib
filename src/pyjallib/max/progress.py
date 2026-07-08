#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Progress 모듈 - 3ds Max 작업 진행 상황 표시 관련 기능 제공
"""


class Progress:
    """작업의 현재 스텝을 기록하고 진행율(%)을 계산하는 클래스."""
    def __init__(self, inTaskName: str, inTotalSteps: int = 0):
        """Progress 클래스를 초기화한다.

        Args:
            inTaskName (str): 작업 이름
            inTotalSteps (int): 전체 스텝 수. 0이면 update 시 현재 스텝의 100 나머지 값을 진행율로 사용한다.
        """
        self.taskName = inTaskName
        self.currentStep = 0
        self.totalSteps = inTotalSteps
        self.currentPercent = 0

    def update(self, inCurrentStep: int) -> int:
        """현재 스텝을 갱신하고 진행율(%)을 계산하여 반환한다.

        Args:
            inCurrentStep (int): 현재 스텝

        Returns:
            int: 현재 진행율(%). totalSteps가 0이면 inCurrentStep % 100
        """
        if self.totalSteps == 0:
            self.currentStep = inCurrentStep % 100
            self.currentPercent = int(self.currentStep)
        else:
            self.currentStep = inCurrentStep
            self.currentPercent = int((self.currentStep / self.totalSteps) * 100)
        return self.currentPercent
    
    def reset(self):
        """진행 상태(현재 스텝, 진행율)를 0으로 초기화한다."""
        self.currentStep = 0
        self.currentPercent = 0
