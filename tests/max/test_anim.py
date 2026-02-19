#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max Anim 서비스 테스트 스크립트.

pyjallib.max.anim.Anim 클래스의 주요 기능을 검증한다.
3ds Max 내부에서 실행되며, TestReporter를 통해 결과를 로그에 기록한다.

테스트 대상:
    - Anim 인스턴스 생성
    - rotate_local, move_local
    - reset_transform_controller
    - delete_all_keys
    - is_node_animated (비애니메이션 / 애니메이션)
    - find_animated_nodes
    - save_xform / set_xform
"""

import sys
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

import pymxs
from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.anim import Anim

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Anim", LOG_DIR)


# ============================================================
# TC01: Anim 인스턴스 생성
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    animService = Anim()
    reporter.assert_test(
        animService is not None,
        "TC01 Anim 인스턴스 생성",
        "Anim() 생성 결과가 None"
    )
except Exception as e:
    reporter.error("TC01 Anim 인스턴스 생성", str(e))


# ============================================================
# TC02: rotate_local() - 로컬 회전 후 transform 변경 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="RotateTest")
    origTransform = rt.copy(obj.transform)

    animService.rotate_local(obj, 45, 0, 0)

    # 회전 후 transform이 원본과 달라야 함
    transformChanged = (str(obj.transform) != str(origTransform))
    reporter.assert_test(
        transformChanged,
        "TC02 rotate_local 회전 후 transform 변경",
        f"원본: {origTransform}, 현재: {obj.transform}"
    )
except Exception as e:
    reporter.error("TC02 rotate_local 회전 후 transform 변경", str(e))


# ============================================================
# TC03: move_local() - 로컬 이동 후 position 변경 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="MoveTest")
    origPos = rt.copy(obj.position)

    animService.move_local(obj, 10, 20, 30)

    # 이동 후 position이 원본과 달라야 함
    posChanged = (str(obj.position) != str(origPos))
    reporter.assert_test(
        posChanged,
        "TC03 move_local 이동 후 position 변경",
        f"원본: {origPos}, 현재: {obj.position}"
    )
except Exception as e:
    reporter.error("TC03 move_local 이동 후 position 변경", str(e))


# ============================================================
# TC04: reset_transform_controller() - 컨트롤러 리셋 후 정상 동작 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="ResetCtrlTest")
    # 객체를 이동시킨 후 컨트롤러 리셋
    obj.position = rt.Point3(50, 50, 50)
    savedTransform = rt.copy(obj.transform)

    animService.reset_transform_controller(obj)

    # 리셋 후에도 transform이 보존되어야 함
    transformPreserved = (str(obj.transform) == str(savedTransform))
    reporter.assert_test(
        transformPreserved,
        "TC04 reset_transform_controller 후 transform 보존",
        f"저장된: {savedTransform}, 현재: {obj.transform}"
    )
except Exception as e:
    reporter.error("TC04 reset_transform_controller 후 transform 보존", str(e))


# ============================================================
# TC05: delete_all_keys() - 키프레임 삭제 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="DeleteKeysTest")

    # 키프레임 추가
    with pymxs.animate(True):
        with pymxs.attime(0):
            obj.position = rt.Point3(0, 0, 0)
        with pymxs.attime(10):
            obj.position = rt.Point3(10, 0, 0)
        with pymxs.attime(20):
            obj.position = rt.Point3(20, 0, 0)

    # 키프레임 삭제
    animService.delete_all_keys(obj)

    # 삭제 후 키가 없어야 함
    keys = animService.get_all_keys(obj)
    reporter.assert_test(
        len(keys) == 0,
        "TC05 delete_all_keys 후 키프레임 없음",
        f"남은 키 수: {len(keys)}"
    )
except Exception as e:
    reporter.error("TC05 delete_all_keys 후 키프레임 없음", str(e))


# ============================================================
# TC06: is_node_animated() - 애니메이션 없는 객체는 False
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="NotAnimated")

    result = animService.is_node_animated(obj)
    reporter.assert_test(
        result is False,
        "TC06 is_node_animated 애니메이션 없는 객체 False",
        f"기대: False, 실제: {result}"
    )
except Exception as e:
    reporter.error("TC06 is_node_animated 애니메이션 없는 객체 False", str(e))


# ============================================================
# TC07: is_node_animated() - 키프레임이 있는 객체는 True
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="Animated")

    # pymxs.animate 컨텍스트 매니저로 키프레임 추가
    with pymxs.animate(True):
        with pymxs.attime(0):
            obj.position = rt.Point3(0, 0, 0)
        with pymxs.attime(10):
            obj.position = rt.Point3(10, 0, 0)

    result = animService.is_node_animated(obj)
    reporter.assert_test(
        result is True,
        "TC07 is_node_animated 키프레임 있는 객체 True",
        f"기대: True, 실제: {result}"
    )
except Exception as e:
    reporter.error("TC07 is_node_animated 키프레임 있는 객체 True", str(e))


# ============================================================
# TC08: find_animated_nodes() - 애니메이션된 노드만 필터링
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    objStatic = rt.Point(name="StaticNode")
    objAnim1 = rt.Point(name="AnimNode1")
    objAnim2 = rt.Point(name="AnimNode2")

    # objAnim1, objAnim2에만 키프레임 추가
    with pymxs.animate(True):
        with pymxs.attime(0):
            objAnim1.position = rt.Point3(0, 0, 0)
            objAnim2.position = rt.Point3(0, 0, 0)
        with pymxs.attime(10):
            objAnim1.position = rt.Point3(10, 0, 0)
            objAnim2.position = rt.Point3(0, 10, 0)

    allNodes = [objStatic, objAnim1, objAnim2]
    animatedNodes = animService.find_animated_nodes(allNodes)
    animatedNames = [n.name for n in animatedNodes]

    # StaticNode는 포함되지 않아야 함
    hasStatic = "StaticNode" in animatedNames
    hasAnim1 = "AnimNode1" in animatedNames
    hasAnim2 = "AnimNode2" in animatedNames

    reporter.assert_test(
        hasAnim1 and hasAnim2 and not hasStatic,
        "TC08 find_animated_nodes 애니메이션 노드만 필터링",
        f"기대: AnimNode1, AnimNode2만 포함, 실제: {animatedNames}"
    )
except Exception as e:
    reporter.error("TC08 find_animated_nodes 애니메이션 노드만 필터링", str(e))


# ============================================================
# TC09: save_xform / set_xform - 변환 저장/복원
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    obj = rt.Point(name="XformTest")

    # 특정 위치로 이동
    obj.position = rt.Point3(100, 200, 300)
    savedPos = rt.copy(obj.position)

    # 변환 저장
    animService.save_xform(obj)

    # 위치를 변경
    obj.position = rt.Point3(0, 0, 0)

    # 저장된 변환 복원 (World space)
    animService.set_xform(obj, space="World")
    restoredPos = obj.position

    # 복원된 위치가 저장된 위치와 같아야 함
    posMatch = (
        abs(restoredPos.x - savedPos.x) < 0.01
        and abs(restoredPos.y - savedPos.y) < 0.01
        and abs(restoredPos.z - savedPos.z) < 0.01
    )
    reporter.assert_test(
        posMatch,
        "TC09 save_xform/set_xform 변환 저장/복원",
        f"저장: ({savedPos.x}, {savedPos.y}, {savedPos.z}), "
        f"복원: ({restoredPos.x}, {restoredPos.y}, {restoredPos.z})"
    )
except Exception as e:
    reporter.error("TC09 save_xform/set_xform 변환 저장/복원", str(e))


# ============================================================
# 결과 요약 및 정리
# ============================================================
reporter.summary()
reporter.close()
