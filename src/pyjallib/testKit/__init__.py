#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pyjallib.testKit 패키지

DCC 독립적 테스트 자동화 인프라.
stdlib만 사용하여 어떤 Python 환경에서든 추가 설치 없이 동작한다.

주요 모듈:
    - testReporter: DCC 내부에서 사용하는 테스트 리포터
    - testLogAnalyzer: 외부에서 로그 파일을 파싱하는 분석기
    - testRunner: subprocess로 DCC 프로세스를 실행하는 코어 러너
"""

from pyjallib.testKit.testReporter import TestReporter
from pyjallib.testKit.testLogAnalyzer import TestLogAnalyzer, TestResult
from pyjallib.testKit.testRunner import RunResult, TestRunner

__all__ = [
    "TestReporter",
    "TestLogAnalyzer",
    "TestResult",
    "TestRunner",
    "RunResult",
]
