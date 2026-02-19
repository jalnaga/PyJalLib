#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Align 서비스 헤드레스 테스트 스크립트.

3ds Max 내부에서 실행되며, pyjallib.max.align.Align 클래스의
객체 정렬 기능을 검증한다.

테스트 유형: Type B (3ds Max 내부 실행)
"""

import sys
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.align import Align

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Align", LOG_DIR)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _point3_approx_equal(inP1, inP2, inTol=0.01):
    """두 Point3 값이 허용 오차 내에서 같은지 비교한다.

    Args:
        inP1: 첫 번째 Point3
        inP2: 두 번째 Point3
        inTol: 허용 오차. 기본값 0.01.

    Returns:
        허용 오차 이내이면 True
    """
    return (
        abs(inP1.x - inP2.x) < inTol
        and abs(inP1.y - inP2.y) < inTol
        and abs(inP1.z - inP2.z) < inTol
    )


def _get_scene_object_count():
    """씬 내 전체 객체 수를 반환한다."""
    count = 0
    for _ in rt.objects:
        count += 1
    return count


# --------------------------------------------------------------------------- #
# TC01: Align 인스턴스 생성
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    align = Align()
    reporter.assert_test(
        align is not None,
        "TC01 Align 인스턴스 생성",
        "Align() 반환값이 None"
    )
except Exception as e:
    reporter.error("TC01 Align 인스턴스 생성", str(e))

# --------------------------------------------------------------------------- #
# TC02: align_to_last() - 배열 마지막 객체 위치/회전으로 전체 정렬
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    align = Align()

    p1 = rt.Point(name="test1", pos=rt.Point3(0, 0, 0))
    p2 = rt.Point(name="test2", pos=rt.Point3(10, 0, 0))
    targetPos = rt.Point3(50, 30, 20)
    p3 = rt.Point(name="test3", pos=targetPos)

    align.align_to_last([p1, p2, p3])

    # p1, p2 모두 p3의 트랜스폼(위치+회전)과 일치해야 함
    result = (
        _point3_approx_equal(p1.pos, targetPos)
        and _point3_approx_equal(p2.pos, targetPos)
    )
    reporter.assert_test(
        result,
        "TC02 align_to_last 위치 정렬",
        f"p1.pos={p1.pos}, p2.pos={p2.pos}, 기대={targetPos}"
    )
except Exception as e:
    reporter.error("TC02 align_to_last 위치 정렬", str(e))

# --------------------------------------------------------------------------- #
# TC03: align_to_last_pos() - 위치만 정렬, 회전 유지
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    align = Align()

    p1 = rt.Point(name="test1", pos=rt.Point3(0, 0, 0))
    # p1에 회전 적용
    rt.rotate(p1, rt.EulerAngles(45, 0, 0))
    p1OrigRot = rt.copy(p1.rotation)

    targetPos = rt.Point3(100, 200, 300)
    p2 = rt.Point(name="test2", pos=targetPos)

    objCountBefore = _get_scene_object_count()
    align.align_to_last_pos([p1, p2])
    objCountAfter = _get_scene_object_count()

    # 위치가 대상과 일치하는지 확인
    posOk = _point3_approx_equal(p1.pos, targetPos)

    # 회전이 원래 값을 유지하는지 확인
    p1CurRot = p1.rotation
    rotOk = (
        abs(p1CurRot.x - p1OrigRot.x) < 0.01
        and abs(p1CurRot.y - p1OrigRot.y) < 0.01
        and abs(p1CurRot.z - p1OrigRot.z) < 0.01
        and abs(p1CurRot.w - p1OrigRot.w) < 0.01
    )

    reporter.assert_test(
        posOk,
        "TC03-a align_to_last_pos 위치 정렬",
        f"p1.pos={p1.pos}, 기대={targetPos}"
    )
    reporter.assert_test(
        rotOk,
        "TC03-b align_to_last_pos 회전 유지",
        f"p1.rot={p1CurRot}, 기대={p1OrigRot}"
    )
    # 임시 객체가 남지 않았는지 확인
    reporter.assert_test(
        objCountAfter == objCountBefore,
        "TC03-c align_to_last_pos 임시 객체 정리",
        f"객체 수: 전={objCountBefore}, 후={objCountAfter}"
    )
except Exception as e:
    reporter.error("TC03 align_to_last_pos", str(e))

# --------------------------------------------------------------------------- #
# TC04: align_to_last_rot() - 회전만 정렬, 위치 유지
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    align = Align()

    origPos = rt.Point3(10, 20, 30)
    p1 = rt.Point(name="test1", pos=origPos)

    p2 = rt.Point(name="test2", pos=rt.Point3(100, 200, 300))
    rt.rotate(p2, rt.EulerAngles(0, 90, 0))
    p2Rot = rt.copy(p2.rotation)

    objCountBefore = _get_scene_object_count()
    align.align_to_last_rot([p1, p2])
    objCountAfter = _get_scene_object_count()

    # 위치가 원래 값을 유지하는지 확인
    posOk = _point3_approx_equal(p1.pos, origPos)

    # 회전이 대상과 일치하는지 확인
    p1CurRot = p1.rotation
    rotOk = (
        abs(p1CurRot.x - p2Rot.x) < 0.01
        and abs(p1CurRot.y - p2Rot.y) < 0.01
        and abs(p1CurRot.z - p2Rot.z) < 0.01
        and abs(p1CurRot.w - p2Rot.w) < 0.01
    )

    reporter.assert_test(
        posOk,
        "TC04-a align_to_last_rot 위치 유지",
        f"p1.pos={p1.pos}, 기대={origPos}"
    )
    reporter.assert_test(
        rotOk,
        "TC04-b align_to_last_rot 회전 정렬",
        f"p1.rot={p1CurRot}, 기대={p2Rot}"
    )
    # 임시 객체가 남지 않았는지 확인
    reporter.assert_test(
        objCountAfter == objCountBefore,
        "TC04-c align_to_last_rot 임시 객체 정리",
        f"객체 수: 전={objCountBefore}, 후={objCountAfter}"
    )
except Exception as e:
    reporter.error("TC04 align_to_last_rot", str(e))

# --------------------------------------------------------------------------- #
# 결과 요약
# --------------------------------------------------------------------------- #
reporter.summary()
reporter.close()
