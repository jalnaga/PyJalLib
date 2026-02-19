#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max Helper 서비스 테스트 스크립트.

pyjallib.max.helper.Helper 클래스의 주요 기능을 검증한다.
3ds Max 내부에서 실행되며, TestReporter를 통해 결과를 로그에 기록한다.

테스트 대상:
    - Helper 인스턴스 생성 (Name 서비스 주입)
    - create_point (기본, 옵션)
    - create_empty_point
    - set_size, add_size
    - set_shape_to_cross, set_shape_to_box
    - get_shape, set_shape
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

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Helper", LOG_DIR)


# ============================================================
# TC01: Helper 인스턴스 생성 (Name 서비스 주입)
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    nameService = Name()
    helperService = Helper(nameService=nameService)
    reporter.assert_test(
        helperService is not None and helperService.name is nameService,
        "TC01 Helper 인스턴스 생성 및 Name 서비스 주입",
        f"helperService: {helperService}, name: {helperService.name}"
    )
except Exception as e:
    reporter.error("TC01 Helper 인스턴스 생성 및 Name 서비스 주입", str(e))


# ============================================================
# TC02: create_point() - 기본 포인트 생성, 이름/크기/색상 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point("TestPoint", size=5)

    nameOk = point.name == "TestPoint"
    sizeOk = abs(point.size - 5.0) < 0.01
    # 기본 색상: (14, 255, 2)
    colorOk = (
        abs(point.wirecolor.r - 14) < 1
        and abs(point.wirecolor.g - 255) < 1
        and abs(point.wirecolor.b - 2) < 1
    )

    reporter.assert_test(
        nameOk and sizeOk and colorOk,
        "TC02 create_point 기본 포인트 생성",
        f"이름: {point.name}(기대: TestPoint), "
        f"크기: {point.size}(기대: 5), "
        f"색상: ({point.wirecolor.r}, {point.wirecolor.g}, {point.wirecolor.b})(기대: 14,255,2)"
    )
except Exception as e:
    reporter.error("TC02 create_point 기본 포인트 생성", str(e))


# ============================================================
# TC03: create_point() - boxToggle/crossToggle 옵션 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point(
        "OptionPoint", size=3, boxToggle=True, crossToggle=False
    )

    boxOk = point.box is True
    crossOk = point.cross is False

    reporter.assert_test(
        boxOk and crossOk,
        "TC03 create_point boxToggle/crossToggle 옵션",
        f"box: {point.box}(기대: True), cross: {point.cross}(기대: False)"
    )
except Exception as e:
    reporter.error("TC03 create_point boxToggle/crossToggle 옵션", str(e))


# ============================================================
# TC04: create_empty_point() - 빈 포인트 생성, size=0 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    emptyPoint = helperService.create_empty_point("EmptyPoint")

    nameOk = emptyPoint.name == "EmptyPoint"
    sizeOk = abs(emptyPoint.size - 0.0) < 0.01
    crossOk = emptyPoint.cross is False

    reporter.assert_test(
        nameOk and sizeOk and crossOk,
        "TC04 create_empty_point 빈 포인트 생성",
        f"이름: {emptyPoint.name}(기대: EmptyPoint), "
        f"크기: {emptyPoint.size}(기대: 0), "
        f"cross: {emptyPoint.cross}(기대: False)"
    )
except Exception as e:
    reporter.error("TC04 create_empty_point 빈 포인트 생성", str(e))


# ============================================================
# TC05: set_size() - 헬퍼 크기 변경
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point("SizeTest", size=2)
    result = helperService.set_size(point, 10)

    reporter.assert_test(
        result is not None and abs(point.size - 10.0) < 0.01,
        "TC05 set_size 헬퍼 크기 변경",
        f"크기: {point.size}(기대: 10)"
    )
except Exception as e:
    reporter.error("TC05 set_size 헬퍼 크기 변경", str(e))


# ============================================================
# TC06: add_size() - 헬퍼 크기 증가
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point("AddSizeTest", size=5)
    result = helperService.add_size(point, 3)

    reporter.assert_test(
        result is not None and abs(point.size - 8.0) < 0.01,
        "TC06 add_size 헬퍼 크기 증가",
        f"크기: {point.size}(기대: 8)"
    )
except Exception as e:
    reporter.error("TC06 add_size 헬퍼 크기 증가", str(e))


# ============================================================
# TC07: set_shape_to_cross() - 형태 변경 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point("CrossShapeTest", size=2)
    helperService.set_shape_to_cross(point)

    crossOk = point.cross is True
    boxOk = point.box is False
    centerOk = point.centermarker is False
    axisOk = point.axistripod is False

    reporter.assert_test(
        crossOk and boxOk and centerOk and axisOk,
        "TC07 set_shape_to_cross 형태 변경",
        f"cross: {point.cross}(기대: True), box: {point.box}(기대: False), "
        f"centermarker: {point.centermarker}(기대: False), axistripod: {point.axistripod}(기대: False)"
    )
except Exception as e:
    reporter.error("TC07 set_shape_to_cross 형태 변경", str(e))


# ============================================================
# TC08: set_shape_to_box() - 형태 변경 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point("BoxShapeTest", size=2)
    helperService.set_shape_to_box(point)

    boxOk = point.box is True
    crossOk = point.cross is False
    centerOk = point.centermarker is False
    axisOk = point.axistripod is False

    reporter.assert_test(
        boxOk and crossOk and centerOk and axisOk,
        "TC08 set_shape_to_box 형태 변경",
        f"box: {point.box}(기대: True), cross: {point.cross}(기대: False), "
        f"centermarker: {point.centermarker}(기대: False), axistripod: {point.axistripod}(기대: False)"
    )
except Exception as e:
    reporter.error("TC08 set_shape_to_box 형태 변경", str(e))


# ============================================================
# TC09: get_shape() - 형태 속성 딕셔너리 반환 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point(
        "GetShapeTest", size=7, boxToggle=True, crossToggle=False
    )
    shapeDict = helperService.get_shape(point)

    hasAllKeys = all(
        k in shapeDict for k in ["size", "centermarker", "axistripod", "cross", "box"]
    )
    sizeOk = abs(shapeDict["size"] - 7.0) < 0.01
    boxOk = shapeDict["box"] is True
    crossOk = shapeDict["cross"] is False

    reporter.assert_test(
        hasAllKeys and sizeOk and boxOk and crossOk,
        "TC09 get_shape 형태 속성 딕셔너리 확인",
        f"결과: {shapeDict}"
    )
except Exception as e:
    reporter.error("TC09 get_shape 형태 속성 딕셔너리 확인", str(e))


# ============================================================
# TC10: set_shape() - 형태 속성 설정 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    point = helperService.create_point("SetShapeTest", size=2)

    newShape = {
        "size": 12.0,
        "centermarker": True,
        "axistripod": False,
        "cross": False,
        "box": True
    }
    result = helperService.set_shape(point, newShape)

    sizeOk = abs(point.size - 12.0) < 0.01
    centerOk = point.centermarker is True
    axisOk = point.axistripod is False
    crossOk = point.cross is False
    boxOk = point.box is True

    reporter.assert_test(
        result is not None and sizeOk and centerOk and axisOk and crossOk and boxOk,
        "TC10 set_shape 형태 속성 설정",
        f"size: {point.size}(기대: 12), centermarker: {point.centermarker}(기대: True), "
        f"axistripod: {point.axistripod}(기대: False), cross: {point.cross}(기대: False), "
        f"box: {point.box}(기대: True)"
    )
except Exception as e:
    reporter.error("TC10 set_shape 형태 속성 설정", str(e))


# ============================================================
# 결과 요약 및 정리
# ============================================================
reporter.summary()
reporter.close()
