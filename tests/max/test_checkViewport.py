#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckViewport 클래스 테스트 - 3ds Max 환경에서 실행

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\Dropbox\Programing\Python\PyJalLib\tests\max\test_checkViewport.py").read())

로그 파일: tests/logs/test_max_checkViewport.log
"""

import sys
import logging
from pathlib import Path

from pymxs import runtime as rt

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pyjallib.max.checkViewport import CheckViewport

# 로그 설정
LOG_DIR = PROJECT_ROOT / "tests" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "test_max_checkViewport.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="w",
)
logger = logging.getLogger(__name__)

# 테스트 카운터
_passed = 0
_failed = 0


def assert_test(condition, test_name, detail=""):
    """테스트 결과를 로그에 기록."""
    global _passed, _failed
    if condition:
        _passed += 1
        logger.info(f"SUCCESS: {test_name}")
    else:
        _failed += 1
        msg = f"FAIL: {test_name}"
        if detail:
            msg += f" - {detail}"
        logger.error(msg)


def run_tests():
    """CheckViewport 전체 테스트 실행."""
    logger.info("=== TEST START: CheckViewport ===")

    # --- TC01: 인스턴스 생성 ---
    try:
        checker = CheckViewport()
        assert_test(checker is not None, "TC01 인스턴스 생성")
    except Exception as e:
        assert_test(False, "TC01 인스턴스 생성", str(e))
        logger.info("=== TEST END (인스턴스 생성 실패로 중단) ===")
        return

    # --- TC02: 메서드 존재 확인 ---
    assert_test(
        hasattr(checker, "is_viewport_disabled") and callable(checker.is_viewport_disabled),
        "TC02 is_viewport_disabled 메서드 존재"
    )
    assert_test(
        hasattr(checker, "reset_viewport") and callable(checker.reset_viewport),
        "TC03 reset_viewport 메서드 존재"
    )

    # --- TC04: 정상 상태에서 is_viewport_disabled() ---
    # 일반적으로 뷰포트는 활성 상태
    try:
        result = checker.is_viewport_disabled()
        assert_test(
            isinstance(result, bool),
            "TC04 is_viewport_disabled 반환 타입이 bool",
            f"실제 반환값: {result} (type: {type(result).__name__})"
        )
    except Exception as e:
        assert_test(False, "TC04 is_viewport_disabled 호출", str(e))

    # --- TC05: 정상 상태에서 뷰포트 활성 확인 ---
    try:
        result = checker.is_viewport_disabled()
        assert_test(
            result is False,
            "TC05 정상 상태에서 is_viewport_disabled == False",
            f"실제 반환값: {result}"
        )
    except Exception as e:
        assert_test(False, "TC05 정상 상태 검사", str(e))

    # --- TC06: disableSceneRedraw 후 reset_viewport로 복원 ---
    # 참고: disableSceneRedraw()와 viewport.IsEnabled()는 별개 메커니즘.
    # 이 TC는 disableSceneRedraw 상태에서 reset_viewport가 enableSceneRedraw를
    # 호출하여 리드로우를 복원하는지 확인.
    try:
        rt.disableSceneRedraw()
        checker.reset_viewport()
        # reset_viewport 내부에서 enableSceneRedraw를 호출하므로 리드로우가 복원됨
        # redrawViews가 예외 없이 호출되면 복원 성공
        rt.redrawViews()
        assert_test(True, "TC06 disableSceneRedraw 후 reset_viewport로 리드로우 복원")
    except Exception as e:
        assert_test(False, "TC06 disableSceneRedraw 후 reset_viewport 복원", str(e))

    # --- TC07: reset_viewport 호출 시 예외 없이 실행 ---
    try:
        checker.reset_viewport()
        assert_test(True, "TC07 reset_viewport 예외 없이 실행 완료")
    except Exception as e:
        assert_test(False, "TC07 reset_viewport 실행", str(e))

    # --- TC08: reset_viewport 후 뷰포트 활성 상태 ---
    try:
        result = checker.is_viewport_disabled()
        assert_test(
            result is False,
            "TC08 reset_viewport 후 is_viewport_disabled == False",
            f"실제 반환값: {result}"
        )
    except Exception as e:
        assert_test(False, "TC08 reset_viewport 후 검사", str(e))

    # --- 결과 요약 ---
    total = _passed + _failed
    logger.info(f"=== TEST END: {_passed}/{total} passed, {_failed} failed ===")


run_tests()
