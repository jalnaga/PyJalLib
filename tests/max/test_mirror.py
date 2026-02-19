#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mirror 서비스 헤드레스 테스트 스크립트.

3ds Max 내부에서 실행되며, pyjallib.max.mirror.Mirror 클래스의
객체/뼈대 미러링 기능을 검증한다.

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
from pyjallib.max.mirror import Mirror
from pyjallib.max.name import Name
from pyjallib.max.bone import Bone

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Mirror", LOG_DIR)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def _approx_equal(inA, inB, inTol=0.01):
    """두 스칼라 값이 허용 오차 내에서 같은지 비교한다.

    Args:
        inA: 첫 번째 값
        inB: 두 번째 값
        inTol: 허용 오차. 기본값 0.01.

    Returns:
        허용 오차 이내이면 True
    """
    return abs(inA - inB) < inTol


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


# --------------------------------------------------------------------------- #
# TC01: Mirror 인스턴스 생성
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    mirror = Mirror(nameService=nameService, boneService=boneService)
    reporter.assert_test(
        mirror is not None,
        "TC01 Mirror 인스턴스 생성",
        "Mirror() 반환값이 None"
    )
except Exception as e:
    reporter.error("TC01 Mirror 인스턴스 생성", str(e))

# --------------------------------------------------------------------------- #
# TC02: mirror_matrix() - X축 미러 행렬 (위치 x좌표 부호 반전)
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    mirror = Mirror(nameService=nameService, boneService=boneService)

    # 원본 위치를 가진 변환 행렬 생성
    origTM = rt.matrix3(1)
    origTM.translation = rt.Point3(30, 10, 5)

    resultTM = mirror.mirror_matrix(mAxis="x", mFlip="x", tm=origTM)
    resultPos = resultTM.translation

    # X축 미러이므로 x좌표가 반전되어야 함
    reporter.assert_test(
        _approx_equal(resultPos.x, -30.0) and _approx_equal(resultPos.y, 10.0) and _approx_equal(resultPos.z, 5.0),
        "TC02 mirror_matrix X축 반전",
        f"결과 위치={resultPos}, 기대=(-30, 10, 5)"
    )
except Exception as e:
    reporter.error("TC02 mirror_matrix X축 반전", str(e))

# --------------------------------------------------------------------------- #
# TC03: apply_mirror() - 포인트 객체 미러 복제 (cloneStatus=2)
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    mirror = Mirror(nameService=nameService, boneService=boneService)

    origPos = rt.Point3(20, 0, 0)
    p1 = rt.Point(name="Lf_Test_00", pos=origPos)

    copyObj = mirror.apply_mirror(p1, axis=1, flip=2, cloneStatus=2)

    # 복제본이 생성되었는지 확인
    reporter.assert_test(
        copyObj is not None and copyObj is not p1,
        "TC03-a apply_mirror 복제본 생성",
        f"copyObj is None: {copyObj is None}, copyObj is p1: {copyObj is p1}"
    )

    # 복제본의 x좌표가 반전되었는지 확인
    if copyObj is not None:
        reporter.assert_test(
            _approx_equal(copyObj.pos.x, -origPos.x),
            "TC03-b apply_mirror 복제본 X좌표 반전",
            f"copyObj.pos.x={copyObj.pos.x}, 기대={-origPos.x}"
        )
    else:
        reporter.error("TC03-b apply_mirror 복제본 X좌표 반전", "copyObj가 None")
except Exception as e:
    reporter.error("TC03 apply_mirror 복제", str(e))

# --------------------------------------------------------------------------- #
# TC04: apply_mirror() - 원본 변경 (cloneStatus=1)
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    mirror = Mirror(nameService=nameService, boneService=boneService)

    origPos = rt.Point3(15, 5, 0)
    p1 = rt.Point(name="Lf_Test_00", pos=origPos)

    resultObj = mirror.apply_mirror(p1, axis=1, flip=2, cloneStatus=1)

    # cloneStatus=1이므로 반환된 객체가 원본과 같아야 함
    reporter.assert_test(
        resultObj is p1,
        "TC04-a apply_mirror 원본 변경 반환",
        f"resultObj is p1: {resultObj is p1}"
    )

    # 원본의 x좌표가 반전되었는지 확인
    reporter.assert_test(
        _approx_equal(p1.pos.x, -origPos.x),
        "TC04-b apply_mirror 원본 X좌표 반전",
        f"p1.pos.x={p1.pos.x}, 기대={-origPos.x}"
    )
except Exception as e:
    reporter.error("TC04 apply_mirror 원본 변경", str(e))

# --------------------------------------------------------------------------- #
# TC05: mirror_object() - 배열 미러링 (negative=True 내부 사용)
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    mirror = Mirror(nameService=nameService, boneService=boneService)

    p1 = rt.Point(name="Lf_Obj01_00", pos=rt.Point3(10, 0, 0))
    p2 = rt.Point(name="Lf_Obj02_00", pos=rt.Point3(20, 5, 0))

    resultArray = mirror.mirror_object([p1, p2], mAxis=1, cloneStatus=2)

    reporter.assert_test(
        len(resultArray) == 2,
        "TC05-a mirror_object 결과 개수",
        f"결과={len(resultArray)}, 기대=2"
    )

    if len(resultArray) == 2:
        # 각 복제본의 x좌표가 반전되었는지 확인
        result1Ok = _approx_equal(resultArray[0].pos.x, -10.0)
        result2Ok = _approx_equal(resultArray[1].pos.x, -20.0)
        reporter.assert_test(
            result1Ok and result2Ok,
            "TC05-b mirror_object X좌표 반전",
            f"r1.pos.x={resultArray[0].pos.x}, r2.pos.x={resultArray[1].pos.x}, "
            f"기대=(-10, -20)"
        )
    else:
        reporter.error("TC05-b mirror_object X좌표 반전", "결과 배열 길이 불일치")
except Exception as e:
    reporter.error("TC05 mirror_object", str(e))

# --------------------------------------------------------------------------- #
# TC06: mirror_bone() - 뼈대 미러링 (X축)
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    nameService = Name()
    boneService = Bone(nameService=nameService)
    mirror = Mirror(nameService=nameService, boneService=boneService)

    # 뼈대 체인 생성 (2개 뼈대 + 엔드 뼈대)
    bone1 = rt.BoneSys.createBone(
        rt.Point3(10, 0, 0), rt.Point3(20, 0, 0), rt.Point3(0, 0, 1)
    )
    bone1.name = "Lf_TestBone_00"

    bone2 = rt.BoneSys.createBone(
        rt.Point3(20, 0, 0), rt.Point3(30, 0, 0), rt.Point3(0, 0, 1)
    )
    bone2.name = "Lf_TestBone_01"
    bone2.parent = bone1

    mirroredBones = mirror.mirror_bone([bone1, bone2], mAxis=1)

    # 미러링된 뼈대가 생성되었는지 확인
    reporter.assert_test(
        len(mirroredBones) >= 2,
        "TC06-a mirror_bone 결과 개수",
        f"결과={len(mirroredBones)}, 기대>=2"
    )

    if len(mirroredBones) >= 1:
        # 미러링된 첫 번째 뼈대의 x좌표가 반전되었는지 확인
        mirroredPos = mirroredBones[0].pos
        reporter.assert_test(
            _approx_equal(mirroredPos.x, -10.0),
            "TC06-b mirror_bone X좌표 반전",
            f"mirroredBones[0].pos.x={mirroredPos.x}, 기대=-10"
        )
    else:
        reporter.error("TC06-b mirror_bone X좌표 반전", "미러링된 뼈대 없음")

    if len(mirroredBones) >= 2:
        # 계층 구조 유지 확인
        reporter.assert_test(
            mirroredBones[1].parent is not None and mirroredBones[1].parent.name == mirroredBones[0].name,
            "TC06-c mirror_bone 계층 구조 유지",
            f"mirroredBones[1].parent={mirroredBones[1].parent}, "
            f"기대={mirroredBones[0].name}"
        )
    else:
        reporter.error("TC06-c mirror_bone 계층 구조 유지", "미러링된 뼈대 부족")
except Exception as e:
    reporter.error("TC06 mirror_bone", str(e))

# --------------------------------------------------------------------------- #
# 결과 요약
# --------------------------------------------------------------------------- #
reporter.summary()
reporter.close()
