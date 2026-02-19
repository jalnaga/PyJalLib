#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bone 클래스 테스트 - 3ds Max 환경에서 실행

3ds Max의 뼈대(Bone) 생성 및 관리 기능을 검증하는 테스트 스위트.
Name, Anim, Helper, Constraint 의존성 주입을 사용하여 Bone을 초기화한다.

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\\Dropbox\\Programing\\Code\\PyJalLib\\tests\\max\\test_bone.py").read())

로그 파일: tests/logs/test_Bone.log
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
from pyjallib.max.anim import Anim
from pyjallib.max.helper import Helper
from pyjallib.max.constraint import Constraint
from pyjallib.max.bone import Bone

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Bone", LOG_DIR)


def run_tests():
    """Bone 클래스의 전체 테스트를 실행한다."""

    # --- TC01: Bone 인스턴스 생성 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        nameService = Name()
        animService = Anim()
        helperService = Helper(nameService=nameService)
        constraintService = Constraint(nameService=nameService, helperService=helperService)
        bone = Bone(
            nameService=nameService,
            animService=animService,
            helperService=helperService,
            constraintService=constraintService
        )
        reporter.assert_test(
            bone is not None,
            "TC01 Bone 인스턴스 생성",
            "Bone() 반환값이 None"
        )
    except Exception as e:
        reporter.error("TC01 Bone 인스턴스 생성", str(e))

    # --- TC02: create_nub_bone() - Nub 뼈대 생성 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        nub = bone.create_nub_bone("TestBone", 2)
        reporter.assert_test(
            nub is not None,
            "TC02 create_nub_bone 생성",
            "반환된 Nub 뼈대가 None"
        )
        reporter.assert_test(
            rt.classOf(nub) == rt.BoneGeometry,
            "TC02 create_nub_bone 타입 확인",
            f"기대: BoneGeometry, 실제: {rt.classOf(nub)}"
        )
        reporter.assert_test(
            nub.taper == 90,
            "TC02 create_nub_bone taper 값",
            f"기대: 90, 실제: {nub.taper}"
        )
    except Exception as e:
        reporter.error("TC02 create_nub_bone", str(e))

    # --- TC03: is_nub_bone() - Nub 뼈대 판별 (True) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        nub = bone.create_nub_bone("NubTest", 2)

        result = bone.is_nub_bone(nub)
        reporter.assert_test(
            result is True,
            "TC03 is_nub_bone True 판별",
            f"기대: True, 실제: {result}"
        )
    except Exception as e:
        reporter.error("TC03 is_nub_bone True", str(e))

    # --- TC04: is_nub_bone() - 일반 뼈대 판별 (False) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        # 간단한 뼈대 체인 생성 (부모-자식 관계가 있으므로 Nub이 아님)
        boneChain = bone.create_simple_bone(30, "RegularBone", end=True, size=2)

        # 체인의 첫 번째 뼈대는 자식이 있으므로 Nub이 아님
        result = bone.is_nub_bone(boneChain[0])
        reporter.assert_test(
            result is False,
            "TC04 is_nub_bone False 판별 (일반 뼈대)",
            f"기대: False, 실제: {result}"
        )
    except Exception as e:
        reporter.error("TC04 is_nub_bone False", str(e))

    # --- TC05: create_simple_bone() - 간단한 뼈대 체인 생성 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(50, "SimpleBone", end=True, size=2)

        reporter.assert_test(
            boneChain is not None and len(boneChain) > 0,
            "TC05 create_simple_bone 체인 생성",
            "반환된 뼈대 배열이 None 또는 빈 배열"
        )
        # end=True이므로 뼈대 + end 뼈대 = 최소 2개
        reporter.assert_test(
            len(boneChain) >= 2,
            "TC05 create_simple_bone 뼈대 수",
            f"기대: 2개 이상, 실제: {len(boneChain)}개"
        )
    except Exception as e:
        reporter.error("TC05 create_simple_bone", str(e))

    # --- TC06: create_end_bone() - End 뼈대 생성 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(40, "EndTest", end=False, size=2)
        parentBone = boneChain[0]

        endBone = bone.create_end_bone(parentBone)
        reporter.assert_test(
            endBone is not None,
            "TC06 create_end_bone 생성",
            "반환된 End 뼈대가 None"
        )
        reporter.assert_test(
            endBone.parent is not None and endBone.parent == parentBone,
            "TC06 create_end_bone 부모 연결",
            f"기대: 부모={parentBone.name}, 실제: 부모={endBone.parent.name if endBone.parent is not None else 'None'}"
        )
    except Exception as e:
        reporter.error("TC06 create_end_bone", str(e))

    # --- TC07: is_end_bone() - End 뼈대 판별 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(40, "EndCheck", end=True, size=2)

        # 마지막 뼈대가 End 뼈대여야 함
        lastBone = boneChain[-1]
        result = bone.is_end_bone(lastBone)
        reporter.assert_test(
            result is True,
            "TC07 is_end_bone End 뼈대 판별",
            f"기대: True, 실제: {result}"
        )

        # 첫 번째 뼈대는 End가 아님 (자식이 있으므로)
        firstBone = boneChain[0]
        resultFirst = bone.is_end_bone(firstBone)
        reporter.assert_test(
            resultFirst is False,
            "TC07 is_end_bone 일반 뼈대 판별",
            f"기대: False, 실제: {resultFirst}"
        )
    except Exception as e:
        reporter.error("TC07 is_end_bone", str(e))

    # --- TC08: sort_bones_as_hierarchy() - 계층 정렬 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(60, "SortBone", end=True, size=2)

        # 역순으로 배열을 만들어 정렬 테스트
        reversed_chain = list(reversed(boneChain))
        sorted_chain = bone.sort_bones_as_hierarchy(reversed_chain)

        reporter.assert_test(
            len(sorted_chain) == len(boneChain),
            "TC08 sort_bones_as_hierarchy 배열 길이",
            f"기대: {len(boneChain)}, 실제: {len(sorted_chain)}"
        )
        # 정렬 후 첫 번째가 루트(부모 없음)여야 함
        reporter.assert_test(
            sorted_chain[0].parent is None,
            "TC08 sort_bones_as_hierarchy 루트 뼈대 위치",
            f"정렬 후 첫 번째 뼈대의 부모: {sorted_chain[0].parent}"
        )
    except Exception as e:
        reporter.error("TC08 sort_bones_as_hierarchy", str(e))

    # --- TC09: get_bone_shape() - 뼈대 형태 속성 조회 (16개 항목) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(50, "ShapeBone", end=False, size=3)
        targetBone = boneChain[0]

        shapeArray = bone.get_bone_shape(targetBone)
        reporter.assert_test(
            len(shapeArray) == 16,
            "TC09 get_bone_shape 속성 개수",
            f"기대: 16, 실제: {len(shapeArray)}"
        )
        # width(인덱스 0)가 설정한 size와 일치
        reporter.assert_test(
            shapeArray[0] == 3,
            "TC09 get_bone_shape width 값",
            f"기대: 3, 실제: {shapeArray[0]}"
        )
        # height(인덱스 1)가 설정한 size와 일치
        reporter.assert_test(
            shapeArray[1] == 3,
            "TC09 get_bone_shape height 값",
            f"기대: 3, 실제: {shapeArray[1]}"
        )
    except Exception as e:
        reporter.error("TC09 get_bone_shape", str(e))

    # --- TC10: set_bone_size() - 뼈대 크기 설정 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(40, "SizeBone", end=False, size=2)
        targetBone = boneChain[0]

        bone.set_bone_size(targetBone, 5)
        reporter.assert_test(
            targetBone.width == 5,
            "TC10 set_bone_size width",
            f"기대: 5, 실제: {targetBone.width}"
        )
        reporter.assert_test(
            targetBone.height == 5,
            "TC10 set_bone_size height",
            f"기대: 5, 실제: {targetBone.height}"
        )
    except Exception as e:
        reporter.error("TC10 set_bone_size", str(e))

    # --- TC11: set_fin_on() / set_fin_off() - 핀 on/off ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(40, "FinBone", end=False, size=2)
        targetBone = boneChain[0]

        # 핀 활성화
        bone.set_fin_on(targetBone, side=True, front=True, back=True, inSize=3.0)
        reporter.assert_test(
            targetBone.frontfin is True,
            "TC11 set_fin_on frontfin 활성화",
            f"기대: True, 실제: {targetBone.frontfin}"
        )
        reporter.assert_test(
            targetBone.sidefins is True,
            "TC11 set_fin_on sidefins 활성화",
            f"기대: True, 실제: {targetBone.sidefins}"
        )
        reporter.assert_test(
            targetBone.backfin is True,
            "TC11 set_fin_on backfin 활성화",
            f"기대: True, 실제: {targetBone.backfin}"
        )

        # 핀 비활성화
        bone.set_fin_off(targetBone)
        reporter.assert_test(
            targetBone.frontfin is False,
            "TC11 set_fin_off frontfin 비활성화",
            f"기대: False, 실제: {targetBone.frontfin}"
        )
        reporter.assert_test(
            targetBone.sidefins is False,
            "TC11 set_fin_off sidefins 비활성화",
            f"기대: False, 실제: {targetBone.sidefins}"
        )
        reporter.assert_test(
            targetBone.backfin is False,
            "TC11 set_fin_off backfin 비활성화",
            f"기대: False, 실제: {targetBone.backfin}"
        )
    except Exception as e:
        reporter.error("TC11 set_fin_on/off", str(e))

    # --- TC12: get_every_children() - 모든 자식 조회 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(60, "ChildBone", end=True, size=2)

        # 루트 뼈대의 모든 자식 조회
        rootBone = boneChain[0]
        children = bone.get_every_children(rootBone)

        # end=True로 생성했으므로 뼈대 체인은 [root, end]이고 자식은 end 1개
        expectedChildCount = len(boneChain) - 1
        reporter.assert_test(
            len(children) == expectedChildCount,
            "TC12 get_every_children 자식 수",
            f"기대: {expectedChildCount}, 실제: {len(children)}"
        )
    except Exception as e:
        reporter.error("TC12 get_every_children", str(e))

    # --- TC13: get_bone_end_position() - 뼈대 끝 위치 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        bone = Bone()
        boneChain = bone.create_simple_bone(50, "EndPosBone", end=False, size=2)
        targetBone = boneChain[0]

        endPos = bone.get_bone_end_position(targetBone)
        reporter.assert_test(
            endPos is not None,
            "TC13 get_bone_end_position 반환값",
            "반환된 위치가 None"
        )
        # 뼈대 길이가 50이고 원점에서 X축 방향으로 생성되었으므로
        # 끝 위치의 X 좌표는 대략 50 근처여야 함
        reporter.assert_test(
            abs(endPos.x - 50.0) < 1.0,
            "TC13 get_bone_end_position X 좌표",
            f"기대: ~50.0, 실제: {endPos.x}"
        )
    except Exception as e:
        reporter.error("TC13 get_bone_end_position", str(e))

    # --- 최종 정리 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
    except Exception:
        pass


# 테스트 실행
run_tests()
reporter.summary()
reporter.close()
