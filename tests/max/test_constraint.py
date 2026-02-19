#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Constraint 클래스 테스트 - 3ds Max 환경에서 실행

3ds Max의 제약(Constraint) 기능을 검증하는 테스트 스위트.
Name, Helper 의존성 주입을 사용하여 Constraint를 초기화하고,
포인트 헬퍼를 이용하여 각종 제약 기능을 테스트한다.

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\\Dropbox\\Programing\\Code\\PyJalLib\\tests\\max\\test_constraint.py").read())

로그 파일: tests/logs/test_Constraint.log
"""

import sys
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.name import Name
from pyjallib.max.helper import Helper
from pyjallib.max.constraint import Constraint

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Constraint", LOG_DIR)


def create_test_helpers():
    """테스트용 포인트 헬퍼 3개를 생성한다.

    Returns:
        (point1, point2, point3) 튜플
    """
    p1 = rt.Point(name="TestPoint1", position=rt.Point3(0, 0, 0))
    p2 = rt.Point(name="TestPoint2", position=rt.Point3(50, 0, 0))
    p3 = rt.Point(name="TestPoint3", position=rt.Point3(100, 0, 0))
    return p1, p2, p3


def run_tests():
    """Constraint 클래스의 전체 테스트를 실행한다."""

    # --- TC01: Constraint 인스턴스 생성 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        nameService = Name()
        helperService = Helper(nameService=nameService)
        constraint = Constraint(nameService=nameService, helperService=helperService)
        reporter.assert_test(
            constraint is not None,
            "TC01 Constraint 인스턴스 생성",
            "Constraint() 반환값이 None"
        )
    except Exception as e:
        reporter.error("TC01 Constraint 인스턴스 생성", str(e))

    # --- TC02: assign_pos_list() - 위치 리스트 컨트롤러 할당 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1 = rt.Point(name="PosListTarget", position=rt.Point3(0, 0, 0))

        posList = constraint.assign_pos_list(p1)
        reporter.assert_test(
            posList is not None,
            "TC02 assign_pos_list 리스트 컨트롤러 할당",
            "반환된 위치 리스트 컨트롤러가 None"
        )
        reporter.assert_test(
            rt.classOf(posList) == rt.Position_list,
            "TC02 assign_pos_list 컨트롤러 타입",
            f"기대: Position_list, 실제: {rt.classOf(posList)}"
        )
    except Exception as e:
        reporter.error("TC02 assign_pos_list", str(e))

    # --- TC03: assign_pos_const() - 위치 제약 할당, 타겟 추가 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        posConst = constraint.assign_pos_const(p1, p2)
        reporter.assert_test(
            posConst is not None,
            "TC03 assign_pos_const 위치 제약 할당",
            "반환된 위치 제약 컨트롤러가 None"
        )
        targetNum = posConst.getNumTargets()
        reporter.assert_test(
            targetNum == 1,
            "TC03 assign_pos_const 타겟 수",
            f"기대: 1, 실제: {targetNum}"
        )
    except Exception as e:
        reporter.error("TC03 assign_pos_const", str(e))

    # --- TC04: get_pos_const() - 위치 제약 조회 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        constraint.assign_pos_const(p1, p2)
        retrievedConst = constraint.get_pos_const(p1)
        reporter.assert_test(
            retrievedConst is not None,
            "TC04 get_pos_const 위치 제약 조회",
            "조회된 위치 제약 컨트롤러가 None"
        )
        reporter.assert_test(
            rt.classOf(retrievedConst) == rt.Position_Constraint,
            "TC04 get_pos_const 컨트롤러 타입",
            f"기대: Position_Constraint, 실제: {rt.classOf(retrievedConst)}"
        )
    except Exception as e:
        reporter.error("TC04 get_pos_const", str(e))

    # --- TC05: assign_rot_list() - 회전 리스트 컨트롤러 할당 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1 = rt.Point(name="RotListTarget", position=rt.Point3(0, 0, 0))

        rotList = constraint.assign_rot_list(p1)
        reporter.assert_test(
            rotList is not None,
            "TC05 assign_rot_list 리스트 컨트롤러 할당",
            "반환된 회전 리스트 컨트롤러가 None"
        )
        reporter.assert_test(
            rt.classOf(rotList) == rt.Rotation_list,
            "TC05 assign_rot_list 컨트롤러 타입",
            f"기대: Rotation_list, 실제: {rt.classOf(rotList)}"
        )
    except Exception as e:
        reporter.error("TC05 assign_rot_list", str(e))

    # --- TC06: assign_rot_const() - 회전 제약 할당 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        rotConst = constraint.assign_rot_const(p1, p2)
        reporter.assert_test(
            rotConst is not None,
            "TC06 assign_rot_const 회전 제약 할당",
            "반환된 회전 제약 컨트롤러가 None"
        )
        targetNum = rotConst.getNumTargets()
        reporter.assert_test(
            targetNum == 1,
            "TC06 assign_rot_const 타겟 수",
            f"기대: 1, 실제: {targetNum}"
        )
    except Exception as e:
        reporter.error("TC06 assign_rot_const", str(e))

    # --- TC07: get_rot_const() - 회전 제약 조회 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        constraint.assign_rot_const(p1, p2)
        retrievedConst = constraint.get_rot_const(p1)
        reporter.assert_test(
            retrievedConst is not None,
            "TC07 get_rot_const 회전 제약 조회",
            "조회된 회전 제약 컨트롤러가 None"
        )
        reporter.assert_test(
            rt.classOf(retrievedConst) == rt.Orientation_Constraint,
            "TC07 get_rot_const 컨트롤러 타입",
            f"기대: Orientation_Constraint, 실제: {rt.classOf(retrievedConst)}"
        )
    except Exception as e:
        reporter.error("TC07 get_rot_const", str(e))

    # --- TC08: assign_lookat() - LookAt 제약 할당 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        lookAt = constraint.assign_lookat(p1, p2)
        reporter.assert_test(
            lookAt is not None,
            "TC08 assign_lookat LookAt 제약 할당",
            "반환된 LookAt 컨트롤러가 None"
        )
        targetNum = lookAt.getNumTargets()
        reporter.assert_test(
            targetNum == 1,
            "TC08 assign_lookat 타겟 수",
            f"기대: 1, 실제: {targetNum}"
        )
    except Exception as e:
        reporter.error("TC08 assign_lookat", str(e))

    # --- TC09: get_lookat() - LookAt 제약 조회 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        constraint.assign_lookat(p1, p2)
        retrievedConst = constraint.get_lookat(p1)
        reporter.assert_test(
            retrievedConst is not None,
            "TC09 get_lookat LookAt 제약 조회",
            "조회된 LookAt 컨트롤러가 None"
        )
        reporter.assert_test(
            rt.classOf(retrievedConst) == rt.LookAt_Constraint,
            "TC09 get_lookat 컨트롤러 타입",
            f"기대: LookAt_Constraint, 실제: {rt.classOf(retrievedConst)}"
        )
    except Exception as e:
        reporter.error("TC09 get_lookat", str(e))

    # --- TC10: collapse() - 컨트롤러 초기화 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, _p3 = create_test_helpers()

        # 위치 제약을 할당한 후 collapse
        constraint.assign_pos_const(p1, p2)
        constraint.collapse(p1)

        # collapse 후 위치 컨트롤러가 기본(Position_XYZ)으로 돌아가야 함
        posController = rt.getPropertyController(p1.controller, "Position")
        reporter.assert_test(
            rt.classOf(posController) == rt.Position_XYZ,
            "TC10 collapse 컨트롤러 초기화",
            f"기대: Position_XYZ, 실제: {rt.classOf(posController)}"
        )
    except Exception as e:
        reporter.error("TC10 collapse", str(e))

    # --- TC11: set_active_last() - 마지막 컨트롤러 활성화 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        constraint = Constraint()
        p1, p2, p3 = create_test_helpers()

        # 위치 리스트에 제약 추가
        constraint.assign_pos_const(p1, p2)
        # 추가 제약 위에 XYZ 컨트롤러 추가
        constraint.assign_pos_xyz(p1)

        # 마지막 컨트롤러 활성화
        constraint.set_active_last(p1)

        posController = rt.getPropertyController(p1.controller, "Position")
        if rt.classOf(posController) == rt.Position_list:
            activeIdx = posController.getActive()
            totalCount = posController.count
            reporter.assert_test(
                activeIdx == totalCount,
                "TC11 set_active_last 마지막 컨트롤러 활성화",
                f"기대: active={totalCount}, 실제: active={activeIdx}"
            )
        else:
            reporter.assert_test(
                False,
                "TC11 set_active_last 마지막 컨트롤러 활성화",
                f"위치 컨트롤러가 리스트 형태가 아님: {rt.classOf(posController)}"
            )
    except Exception as e:
        reporter.error("TC11 set_active_last", str(e))

    # --- 최종 정리 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
    except Exception:
        pass


# 테스트 실행
run_tests()
reporter.summary()
reporter.close()
