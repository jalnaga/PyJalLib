#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckMaterial 클래스 테스트 - 3ds Max 환경에서 실행

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\Dropbox\Programing\Python\PyJalLib\tests\max\test_checkMaterial.py").read())

로그 파일: tests/logs/test_max_checkMaterial.log
"""

import sys
import logging
from pathlib import Path

from pymxs import runtime as rt

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pyjallib.max.checkMaterial import CheckMaterial

# 로그 설정
LOG_DIR = PROJECT_ROOT / "tests" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "test_max_checkMaterial.log"

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
    """CheckMaterial 전체 테스트 실행."""
    global _passed, _failed
    logger.info("=== TEST START: CheckMaterial ===")

    # --- TC01: 인스턴스 생성 ---
    try:
        checker = CheckMaterial()
        assert_test(checker is not None, "TC01 인스턴스 생성")
    except Exception as e:
        assert_test(False, "TC01 인스턴스 생성", str(e))
        logger.info("=== TEST END (인스턴스 생성 실패로 중단) ===")
        return

    # --- TC02: 메서드 존재 확인 ---
    expected_methods = ["is_mat_ids_continued", "has_correct_material"]
    for method_name in expected_methods:
        assert_test(
            hasattr(checker, method_name) and callable(getattr(checker, method_name)),
            f"TC02 메서드 존재: {method_name}"
        )

    # --- TC03: is_mat_ids_continued - 기본 Box (MatID 1만 존재, 연속) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box()
        rt.convertToPoly(testBox)
        result = checker.is_mat_ids_continued(testBox)
        assert_test(
            result is True,
            "TC03 기본 Box의 MatID가 연속 (1만 존재)",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC03 is_mat_ids_continued 기본 Box", str(e))

    # --- TC04: is_mat_ids_continued - 비연속 MatID ---
    try:
        testBox2 = rt.Box()
        rt.convertToPoly(testBox2)
        # 첫 번째 페이스의 MatID를 3으로 설정 (1, 3이 되어 비연속)
        rt.polyOp.setFaceMatID(testBox2, 1, 3)
        result = checker.is_mat_ids_continued(testBox2)
        assert_test(
            result is False,
            "TC04 비연속 MatID (1과 3) == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC04 is_mat_ids_continued 비연속", str(e))

    # --- TC05: has_correct_material - 머티리얼 없음 -> False ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box()
        testBox.material = None
        result = checker.has_correct_material(testBox)
        assert_test(
            result is False,
            "TC05 머티리얼 없는 오브젝트 == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC05 has_correct_material 머티리얼 없음", str(e))

    # --- TC06: has_correct_material - Multimaterial -> True ---
    try:
        testBox2 = rt.Box()
        testBox2.material = rt.Multimaterial()
        result = checker.has_correct_material(testBox2)
        assert_test(
            result is True,
            "TC06 Multimaterial == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC06 has_correct_material Multimaterial", str(e))

    # --- TC07: has_correct_material - Standard 머티리얼 -> False ---
    try:
        testBox3 = rt.Box()
        testBox3.material = rt.StandardMaterial()
        result = checker.has_correct_material(testBox3)
        assert_test(
            result is False,
            "TC07 StandardMaterial == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC07 has_correct_material Standard", str(e))

    # --- 정리 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
    except Exception:
        pass

    # --- 결과 요약 ---
    total = _passed + _failed
    logger.info(f"=== TEST END: {_passed}/{total} passed, {_failed} failed ===")


run_tests()
