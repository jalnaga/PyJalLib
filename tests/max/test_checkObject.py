#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckObject 클래스 테스트 - 3ds Max 환경에서 실행

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\Dropbox\Programing\Python\PyJalLib\tests\max\test_checkObject.py").read())

로그 파일: tests/logs/test_max_checkObject.log
"""

import sys
import logging
from pathlib import Path

from pymxs import runtime as rt

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pyjallib.max.checkObject import CheckObject

# 로그 설정
LOG_DIR = PROJECT_ROOT / "tests" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "test_max_checkObject.log"

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
    """CheckObject 전체 테스트 실행."""
    global _passed, _failed
    logger.info("=== TEST START: CheckObject ===")

    # --- TC01: 인스턴스 생성 ---
    try:
        checker = CheckObject()
        assert_test(checker is not None, "TC01 인스턴스 생성")
    except Exception as e:
        assert_test(False, "TC01 인스턴스 생성", str(e))
        logger.info("=== TEST END (인스턴스 생성 실패로 중단) ===")
        return

    # --- TC02: 메서드 존재 확인 ---
    expected_methods = [
        "has_valid_name",
        "is_editable_poly",
        "fix_editable_poly",
        "check_ngons",
        "has_ngons",
        "has_init_xform",
        "fix_xform",
        "is_transform_locked",
        "fix_transform_locked",
        "has_correct_mod",
        "check_uv_range",
        "check_num_uv_channels",
        "check_animation_keys",
        "check_animation_keys_fix",
        "check_meshes_not_animated",
    ]
    for method_name in expected_methods:
        assert_test(
            hasattr(checker, method_name) and callable(getattr(checker, method_name)),
            f"TC02 메서드 존재: {method_name}"
        )

    # --- TC03: has_valid_name ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="TestMesh_01")
        result_true = checker.has_valid_name(testBox, "TestMesh_01")
        result_false = checker.has_valid_name(testBox, "WrongName")
        assert_test(
            result_true is True and result_false is False,
            "TC03 has_valid_name (일치 True, 불일치 False)",
            f"일치: {result_true}, 불일치: {result_false}"
        )
    except Exception as e:
        assert_test(False, "TC03 has_valid_name", str(e))

    # --- TC04: is_editable_poly - Box 프리미티브 -> False ---
    try:
        testBox = rt.Box(name="PrimBox")
        result = checker.is_editable_poly(testBox)
        assert_test(
            result is False,
            "TC04 Box 프리미티브 is_editable_poly == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC04 is_editable_poly Box", str(e))

    # --- TC05: is_editable_poly - convertToPoly 후 -> True ---
    try:
        rt.convertToPoly(testBox)
        result = checker.is_editable_poly(testBox)
        assert_test(
            result is True,
            "TC05 convertToPoly 후 is_editable_poly == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC05 is_editable_poly convertToPoly", str(e))

    # --- TC06: fix_editable_poly ---
    try:
        testSphere = rt.Sphere(name="FixTarget")
        checker.fix_editable_poly(testSphere)
        result = checker.is_editable_poly(testSphere)
        assert_test(
            result is True,
            "TC06 fix_editable_poly 후 is_editable_poly == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC06 fix_editable_poly", str(e))

    # --- TC07: has_ngons - 기본 Box (quad만) -> False ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="QuadBox")
        rt.convertToPoly(testBox)
        result = checker.has_ngons(testBox)
        assert_test(
            result is False,
            "TC07 Box(quad만) has_ngons == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC07 has_ngons Box", str(e))

    # --- TC08: has_init_xform - 초기 상태 -> True ---
    try:
        testBox2 = rt.Box(name="InitXform")
        result = checker.has_init_xform(testBox2)
        assert_test(
            result is True,
            "TC08 초기 상태 has_init_xform == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC08 has_init_xform 초기", str(e))

    # --- TC09: has_init_xform - rotation 변경 후 -> False ---
    try:
        rt.rotate(testBox2, rt.eulerAngles(45, 0, 0))
        result = checker.has_init_xform(testBox2)
        assert_test(
            result is False,
            "TC09 회전 후 has_init_xform == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC09 has_init_xform 회전 후", str(e))

    # --- TC10: fix_xform 후 has_init_xform -> True ---
    try:
        rt.convertToPoly(testBox2)
        checker.fix_xform(testBox2)
        result = checker.has_init_xform(testBox2)
        assert_test(
            result is True,
            "TC10 fix_xform 후 has_init_xform == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC10 fix_xform", str(e))

    # --- TC11: is_transform_locked - 기본 상태 -> False ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="LockTest")
        result = checker.is_transform_locked(testBox)
        assert_test(
            result is False,
            "TC11 기본 상태 is_transform_locked == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC11 is_transform_locked 기본", str(e))

    # --- TC12: is_transform_locked - 잠금 후 -> True ---
    try:
        rt.setTransformLockFlags(testBox, rt.Name("all"))
        result = checker.is_transform_locked(testBox)
        assert_test(
            result is True,
            "TC12 잠금 후 is_transform_locked == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC12 is_transform_locked 잠금", str(e))

    # --- TC13: fix_transform_locked 후 -> False ---
    try:
        checker.fix_transform_locked(testBox)
        result = checker.is_transform_locked(testBox)
        assert_test(
            result is False,
            "TC13 fix_transform_locked 후 == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC13 fix_transform_locked", str(e))

    # --- TC14: has_correct_mod - 모디파이어 없음 -> True ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="ModTest")
        rt.convertToPoly(testBox)
        result = checker.has_correct_mod(testBox)
        assert_test(
            result is True,
            "TC14 모디파이어 없음 has_correct_mod == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC14 has_correct_mod 모디파이어 없음", str(e))

    # --- TC15: has_correct_mod - Skin만 -> True ---
    try:
        rt.addModifier(testBox, rt.Skin())
        result = checker.has_correct_mod(testBox)
        assert_test(
            result is True,
            "TC15 Skin만 has_correct_mod == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC15 has_correct_mod Skin", str(e))

    # --- TC16: has_correct_mod - 잘못된 모디파이어 (Bend) -> False ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="BadMod")
        rt.convertToPoly(testBox)
        rt.addModifier(testBox, rt.Bend())
        result = checker.has_correct_mod(testBox)
        assert_test(
            result is False,
            "TC16 Bend 모디파이어 has_correct_mod == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC16 has_correct_mod Bend", str(e))

    # --- TC17: check_num_uv_channels - mapping coords 있는 Box -> 1~2 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="UVTest", mapcoords=True)
        rt.convertToPoly(testBox)
        result = checker.check_num_uv_channels(testBox)
        assert_test(
            result is True,
            "TC17 기본 Box check_num_uv_channels == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC17 check_num_uv_channels", str(e))

    # --- TC18: check_animation_keys - 키 없는 오브젝트 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="AnimTest")
        keys = checker.check_animation_keys(testBox)
        assert_test(
            len(keys) == 0,
            "TC18 키 없는 오브젝트 check_animation_keys 길이 == 0",
            f"실제 키 수: {len(keys)}"
        )
    except Exception as e:
        assert_test(False, "TC18 check_animation_keys 키 없음", str(e))

    # --- TC19: check_animation_keys - 키 추가 후 ---
    try:
        rt.animButtonState = True
        rt.sliderTime = 10
        testBox.pos = rt.Point3(50, 0, 0)
        rt.animButtonState = False
        rt.sliderTime = 0

        keys = checker.check_animation_keys(testBox)
        assert_test(
            len(keys) > 0,
            "TC19 키 추가 후 check_animation_keys 길이 > 0",
            f"실제 키 수: {len(keys)}"
        )
    except Exception as e:
        assert_test(False, "TC19 check_animation_keys 키 추가", str(e))

    # --- TC20: check_animation_keys_fix 후 키 삭제 ---
    try:
        checker.check_animation_keys_fix(testBox)
        keys = checker.check_animation_keys(testBox)
        assert_test(
            len(keys) == 0,
            "TC20 check_animation_keys_fix 후 키 수 == 0",
            f"실제 키 수: {len(keys)}"
        )
    except Exception as e:
        assert_test(False, "TC20 check_animation_keys_fix", str(e))

    # --- TC21: check_meshes_not_animated - 빈 씬 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        testBox = rt.Box(name="NoAnim")
        rt.convertToPoly(testBox)
        result = checker.check_meshes_not_animated()
        assert_test(
            len(result) == 0,
            "TC21 애니메이션 없는 씬 check_meshes_not_animated 길이 == 0",
            f"실제: {len(result)}"
        )
    except Exception as e:
        assert_test(False, "TC21 check_meshes_not_animated 빈 씬", str(e))

    # --- TC22: check_meshes_not_animated - 애니메이션 있는 메쉬 ---
    try:
        rt.animButtonState = True
        rt.sliderTime = 10
        testBox.pos = rt.Point3(50, 0, 0)
        rt.animButtonState = False
        rt.sliderTime = 0

        result = checker.check_meshes_not_animated()
        assert_test(
            len(result) > 0,
            "TC22 애니메이션 있는 메쉬 check_meshes_not_animated 길이 > 0",
            f"실제: {len(result)}"
        )
    except Exception as e:
        assert_test(False, "TC22 check_meshes_not_animated 애니메이션", str(e))

    # --- 정리 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
    except Exception:
        pass

    # --- 결과 요약 ---
    total = _passed + _failed
    logger.info(f"=== TEST END: {_passed}/{total} passed, {_failed} failed ===")


run_tests()
