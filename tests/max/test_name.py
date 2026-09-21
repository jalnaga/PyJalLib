#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max Name 서비스 테스트 스크립트.

pyjallib.max.name.Name 클래스의 주요 기능을 검증한다.
3ds Max 내부에서 실행되며, TestReporter를 통해 결과를 로그에 기록한다.

테스트 대상:
    - Name 인스턴스 생성 (기본 config 로드)
    - get_Base_values, get_Type_values, get_Side_values
    - is_Type, has_Type, replace_Type, remove_Type
    - gen_unique_name, gen_mirroring_name
    - get_parent_value, get_dummy_value
    - sort_by_name
"""

import sys
from pathlib import Path

# pyjallib 소스 경로 선주입 + 배포본 선점 퍼지.
# 3ds Max는 기동 시 배포본 pyjallib을 sys.modules에 선점하므로, 경로만 앞에 넣으면
# 캐시 히트로 배포본이 검증된다. _bootstrap이 퍼지까지 하고 TC00이 출처를 단정한다.
sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.name import Name

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Name", LOG_DIR)

# TC00: 이 체크아웃의 소스를 검증하고 있는가.
# 배포본이 로드되면 워크트리 수정이 한 줄도 실행되지 않는데 초록이 뜬다.
import pyjallib  # noqa: E402

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)


# ============================================================
# TC01: Name 인스턴스 생성 (기본 config 로드)
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    nameService = Name()
    reporter.assert_test(
        nameService is not None,
        "TC01 Name 인스턴스 생성",
        "Name() 생성 결과가 None"
    )
except Exception as e:
    reporter.error("TC01 Name 인스턴스 생성", str(e))


# ============================================================
# TC02: get_Base_values() 반환값 비어있지 않음
# ============================================================
try:
    baseValues = nameService.get_Base_values()
    reporter.assert_test(
        len(baseValues) > 0,
        "TC02 get_Base_values 비어있지 않음",
        f"반환값: {baseValues}"
    )
except Exception as e:
    reporter.error("TC02 get_Base_values 비어있지 않음", str(e))


# ============================================================
# TC03: get_Type_values() 반환값 비어있지 않음
# ============================================================
try:
    typeValues = nameService.get_Type_values()
    reporter.assert_test(
        len(typeValues) > 0,
        "TC03 get_Type_values 비어있지 않음",
        f"반환값: {typeValues}"
    )
except Exception as e:
    reporter.error("TC03 get_Type_values 비어있지 않음", str(e))


# ============================================================
# TC04: get_Side_values() 반환값 비어있지 않음
# ============================================================
try:
    sideValues = nameService.get_Side_values()
    reporter.assert_test(
        len(sideValues) > 0,
        "TC04 get_Side_values 비어있지 않음",
        f"반환값: {sideValues}"
    )
except Exception as e:
    reporter.error("TC04 get_Side_values 비어있지 않음", str(e))


# ============================================================
# TC05: is_Type() - predefined value 확인
# ============================================================
try:
    # Type values: ["Dum", "P", "Exp", "IK", "T", "Rot", "Pos", "Lat", "UpN"]
    # "Dum"은 Type의 첫 번째 predefined value
    result = nameService.is_Type("Dum")
    reporter.assert_test(
        result is True,
        "TC05 is_Type('Dum') True 확인",
        f"기대: True, 실제: {result}"
    )
except Exception as e:
    reporter.error("TC05 is_Type('Dum') True 확인", str(e))


# ============================================================
# TC06: has_Type() - Type 파트 포함 확인
# ============================================================
try:
    # "TestBnSpine"에서 "Bn"이 아닌 Type value가 포함되어 있는지 확인
    # "DumSpine"에는 "Dum"이 포함되어 있어야 함
    result = nameService.has_Type("DumSpine")
    reporter.assert_test(
        result is True,
        "TC06 has_Type('DumSpine') True 확인",
        f"기대: True, 실제: {result}"
    )
except Exception as e:
    reporter.error("TC06 has_Type('DumSpine') True 확인", str(e))


# ============================================================
# TC07: replace_Type() - Type 파트 교체
# ============================================================
try:
    # "DumSpine"에서 Type인 "Dum"을 "P"로 교체
    result = nameService.replace_Type("DumSpine", "P")
    reporter.assert_test(
        result == "PSpine",
        "TC07 replace_Type('DumSpine', 'P') 결과 확인",
        f"기대: 'PSpine', 실제: '{result}'"
    )
except Exception as e:
    reporter.error("TC07 replace_Type('DumSpine', 'P') 결과 확인", str(e))


# ============================================================
# TC08: remove_Type() - Type 파트 제거
# ============================================================
try:
    result = nameService.remove_Type("DumSpine")
    reporter.assert_test(
        "Dum" not in result and "Spine" in result,
        "TC08 remove_Type('DumSpine') 결과 확인",
        f"결과에 'Dum' 없고 'Spine' 있어야 함, 실제: '{result}'"
    )
except Exception as e:
    reporter.error("TC08 remove_Type('DumSpine') 결과 확인", str(e))


# ============================================================
# TC09: gen_unique_name() - 고유 이름 생성 (pymxs 의존, 빈 씬)
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    # 빈 씬에서 고유 이름 생성 - Index 부분이 1이어야 함
    uniqueName = nameService.gen_unique_name("DumSpine01")
    reporter.assert_test(
        uniqueName is not None and len(uniqueName) > 0,
        "TC09 gen_unique_name 빈 씬에서 고유 이름 생성",
        f"결과: '{uniqueName}'"
    )
except Exception as e:
    reporter.error("TC09 gen_unique_name 빈 씬에서 고유 이름 생성", str(e))


# ============================================================
# TC10: gen_mirroring_name() - Side가 있는 이름 미러링
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    # Side "L"이 포함된 이름의 미러 -> "R"로 변경되어야 함
    mirrorName = nameService.gen_mirroring_name("DumLSpine01")
    hasMirrored = "R" in mirrorName and "L" not in mirrorName
    reporter.assert_test(
        hasMirrored,
        "TC10 gen_mirroring_name Side L->R 미러링",
        f"기대: 'L'이 'R'로 변경, 실제: '{mirrorName}'"
    )
except Exception as e:
    reporter.error("TC10 gen_mirroring_name Side L->R 미러링", str(e))


# ============================================================
# TC11: get_parent_value() - Type description으로 값 조회
# ============================================================
try:
    # "Parent" description -> "P" value
    parentValue = nameService.get_parent_value()
    reporter.assert_test(
        parentValue == "P",
        "TC11 get_parent_value() 반환값 확인",
        f"기대: 'P', 실제: '{parentValue}'"
    )
except Exception as e:
    reporter.error("TC11 get_parent_value() 반환값 확인", str(e))


# ============================================================
# TC12: get_dummy_value() - Dummy description 값 조회
# ============================================================
try:
    # "Dummy" description -> "Dum" value
    dummyValue = nameService.get_dummy_value()
    reporter.assert_test(
        dummyValue == "Dum",
        "TC12 get_dummy_value() 반환값 확인",
        f"기대: 'Dum', 실제: '{dummyValue}'"
    )
except Exception as e:
    reporter.error("TC12 get_dummy_value() 반환값 확인", str(e))


# ============================================================
# TC13: sort_by_name() - 객체 배열 이름 정렬
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    # 테스트용 객체 3개 생성 (역순 이름)
    objC = rt.Point(name="Charlie")
    objA = rt.Point(name="Alpha")
    objB = rt.Point(name="Bravo")

    unsorted = [objC, objA, objB]
    sortedObjs = nameService.sort_by_name(unsorted)
    sortedNames = [obj.name for obj in sortedObjs]

    reporter.assert_test(
        sortedNames == ["Alpha", "Bravo", "Charlie"],
        "TC13 sort_by_name 이름 정렬 확인",
        f"기대: ['Alpha', 'Bravo', 'Charlie'], 실제: {sortedNames}"
    )
except Exception as e:
    reporter.error("TC13 sort_by_name 이름 정렬 확인", str(e))


# ============================================================
# 결과 요약 및 정리
# ============================================================
reporter.summary()
reporter.close()
