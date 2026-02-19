#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Select 서비스 헤드레스 테스트 스크립트.

3ds Max 내부에서 실행되며, pyjallib.max.select.Select 클래스의
객체 선택/분류/정렬 기능을 검증한다.

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
from pyjallib.max.select import Select
from pyjallib.max.name import Name
from pyjallib.max.bone import Bone

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Select", LOG_DIR)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


# --------------------------------------------------------------------------- #
# TC01: Select 인스턴스 생성
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    sel = Select(nameService=nameService, boneService=boneService)
    reporter.assert_test(
        sel is not None,
        "TC01 Select 인스턴스 생성",
        "Select() 반환값이 None"
    )
except Exception as e:
    reporter.error("TC01 Select 인스턴스 생성", str(e))

# --------------------------------------------------------------------------- #
# TC02: distinguish_hierachy_objects() - 독립/계층 객체 분류
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    sel = Select(nameService=nameService, boneService=boneService)

    # 독립 객체 2개
    alone1 = rt.Point(name="alone1", pos=rt.Point3(0, 0, 0))
    alone2 = rt.Point(name="alone2", pos=rt.Point3(10, 0, 0))

    # 계층 객체 2개 (parent-child)
    parent = rt.Point(name="parent", pos=rt.Point3(20, 0, 0))
    child = rt.Point(name="child", pos=rt.Point3(30, 0, 0))
    child.parent = parent

    allObjs = [alone1, alone2, parent, child]
    result = sel.distinguish_hierachy_objects(allObjs)

    aloneObjs = result[0]
    hierObjs = result[1]

    reporter.assert_test(
        len(aloneObjs) == 2 and len(hierObjs) == 2,
        "TC02 distinguish_hierachy_objects 개수",
        f"독립={len(aloneObjs)}, 계층={len(hierObjs)}, 기대: 각 2"
    )
    reporter.assert_test(
        alone1 in aloneObjs and alone2 in aloneObjs,
        "TC02-b 독립 객체 확인",
        f"aloneObjs 내용 불일치"
    )
    reporter.assert_test(
        parent in hierObjs and child in hierObjs,
        "TC02-c 계층 객체 확인",
        f"hierObjs 내용 불일치"
    )
except Exception as e:
    reporter.error("TC02 distinguish_hierachy_objects", str(e))

# --------------------------------------------------------------------------- #
# TC03: get_nonLinked_objects() - 독립 객체만 반환
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    sel = Select(nameService=nameService, boneService=boneService)

    alone1 = rt.Point(name="alone1", pos=rt.Point3(0, 0, 0))
    parent = rt.Point(name="parent", pos=rt.Point3(10, 0, 0))
    child = rt.Point(name="child", pos=rt.Point3(20, 0, 0))
    child.parent = parent

    result = sel.get_nonLinked_objects([alone1, parent, child])

    reporter.assert_test(
        len(result) == 1 and alone1 in result,
        "TC03 get_nonLinked_objects",
        f"결과={[o.name for o in result]}, 기대=[alone1]"
    )
except Exception as e:
    reporter.error("TC03 get_nonLinked_objects", str(e))

# --------------------------------------------------------------------------- #
# TC04: get_linked_objects() - 계층 객체만 반환
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    sel = Select(nameService=nameService, boneService=boneService)

    alone1 = rt.Point(name="alone1", pos=rt.Point3(0, 0, 0))
    parent = rt.Point(name="parent", pos=rt.Point3(10, 0, 0))
    child = rt.Point(name="child", pos=rt.Point3(20, 0, 0))
    child.parent = parent

    result = sel.get_linked_objects([alone1, parent, child])

    reporter.assert_test(
        len(result) == 2 and parent in result and child in result,
        "TC04 get_linked_objects",
        f"결과={[o.name for o in result]}, 기대=[parent, child]"
    )
except Exception as e:
    reporter.error("TC04 get_linked_objects", str(e))

# --------------------------------------------------------------------------- #
# TC05: sort_by_hierachy() - 계층 정렬 (부모 먼저)
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    sel = Select(nameService=nameService, boneService=boneService)

    # 3단계 계층: grandparent -> parent -> child
    grandparent = rt.Point(name="gp", pos=rt.Point3(0, 0, 0))
    parent = rt.Point(name="par", pos=rt.Point3(10, 0, 0))
    child = rt.Point(name="ch", pos=rt.Point3(20, 0, 0))
    parent.parent = grandparent
    child.parent = parent

    # 역순으로 전달
    result = sel.sort_by_hierachy([child, parent, grandparent])

    # 부모가 먼저 와야 함: grandparent -> parent -> child
    reporter.assert_test(
        result[0] is grandparent and result[1] is parent and result[2] is child,
        "TC05 sort_by_hierachy",
        f"정렬 결과=[{result[0].name}, {result[1].name}, {result[2].name}], "
        f"기대=[gp, par, ch]"
    )
except Exception as e:
    reporter.error("TC05 sort_by_hierachy", str(e))

# --------------------------------------------------------------------------- #
# TC06: filter_bone() - 뼈대만 필터링
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    sel = Select(nameService=nameService, boneService=boneService)

    # 뼈대 생성
    bone1 = rt.BoneSys.createBone(
        rt.Point3(0, 0, 0), rt.Point3(10, 0, 0), rt.Point3(0, 0, 1)
    )
    bone1.name = "testBone1"

    # 포인트 생성
    point1 = rt.Point(name="testPoint1", pos=rt.Point3(20, 0, 0))

    # 전체 선택
    rt.select([bone1, point1])
    selCountBefore = rt.selection.count

    # filter_bone 실행
    sel.filter_bone()

    # 선택된 객체 확인
    currentSel = list(rt.getCurrentSelection())
    allAreBones = all(rt.classOf(item) == rt.BoneGeometry for item in currentSel)

    reporter.assert_test(
        len(currentSel) == 1 and allAreBones,
        "TC06 filter_bone",
        f"선택 전={selCountBefore}, 선택 후={len(currentSel)}, "
        f"모두 뼈대={allAreBones}"
    )
except Exception as e:
    reporter.error("TC06 filter_bone", str(e))

# --------------------------------------------------------------------------- #
# 결과 요약
# --------------------------------------------------------------------------- #
reporter.summary()
reporter.close()
