#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max Attribute 서비스 테스트 스크립트.

pyjallib.max.attribute.Attribute 클래스의 주요 기능을 검증한다.
3ds Max 내부에서 실행되며, TestReporter를 통해 결과를 로그에 기록한다.

테스트 대상:
    - build_param_def_string: MaxScript 어트리뷰트 정의 문자열 생성
    - add_attribute_def: 노드에 커스텀 어트리뷰트 추가 (중복 방지 포함)
    - has_attribute_def: 어트리뷰트 존재 여부 확인
    - find_attribute_def: 어트리뷰트 정의 객체 반환
    - get_all_attribute_defs: 모든 어트리뷰트 정의 목록
    - remove_attribute_def: 어트리뷰트 제거
    - redefine_attribute_def: 재정의 및 값 보존
    - get_property / set_property: 단일 프로퍼티 읽기/쓰기
    - get_all_properties / set_all_properties: 전체 프로퍼티 일괄 처리
    - assign_float_controllers: float 프로퍼티 컨트롤러 할당
"""

import importlib.util
import sys
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

# attribute.py는 새 모듈이므로 3DS Max 기동 시 사전 로드되지 않는다.
# 기동 스크립트가 캐시한 pyjallib.max 패키지에 등록되지 않아
# 패키지 경로 import가 실패하므로 importlib로 직접 로드한다.
_attrPath = (
    Path(__file__).parent.parent.parent / "src" / "pyjallib" / "max" / "attribute.py"
)
_spec = importlib.util.spec_from_file_location("pyjallib.max.attribute", _attrPath)
_attrModule = importlib.util.module_from_spec(_spec)
sys.modules["pyjallib.max.attribute"] = _attrModule
_spec.loader.exec_module(_attrModule)

from pymxs import runtime as rt
from pyjallib.testKit import TestReporter

Attribute = _attrModule.Attribute

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Attribute", LOG_DIR)

# 테스트 공통 파라미터 정의
_TEST_DEF_NAME = "TestAttr"
_TEST_PARAMS = [
    {"name": "weight", "type": "float", "default": 0.0},
    {"name": "count", "type": "integer", "default": 0},
    {"name": "enabled", "type": "boolean", "default": True},
    {"name": "label", "type": "string", "default": ""},
]

# 어트리뷰트 홀더 모디파이어 대상 테스트용 정의 소스 (TC23~TC32).
# build_param_def_string으로는 만들 수 없는 롤아웃 포함 정의를 담아,
# add_attribute_def_from_source가 실제로 그 경로를 커버하는지 확인한다.
_HOLDER_DEF_NAME = "HolderProbeData"
_HOLDER_DEF_SOURCE = """
attributes HolderProbeData
(
    parameters main rollout:HolderProbeRollout
    (
        holderWeight type:#float ui:spnHolderWeight default:0.0
        holderCount type:#integer ui:spnHolderCount default:0
    )

    rollout HolderProbeRollout "홀더 프로브 롤아웃"
    (
        spinner spnHolderWeight "holderWeight" type:#float range:[-100.0, 100.0, 0.0]
        spinner spnHolderCount "holderCount" type:#integer range:[-100, 100, 0]
    )
)
"""


# ============================================================
# TC01: Attribute 인스턴스 생성
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    attrService = Attribute()
    reporter.assert_test(
        attrService is not None,
        "TC01 Attribute 인스턴스 생성",
        "Attribute() 생성 결과가 None",
    )
except Exception as e:
    reporter.error("TC01 Attribute 인스턴스 생성", str(e))


# ============================================================
# TC02: build_param_def_string 출력 형식 검증
# ============================================================
try:
    params = [{"name": "weight", "type": "float", "default": 1.5}]
    result = attrService.build_param_def_string("MyAttr", params)

    # 헤더 라인 포함 여부 확인
    hasHeader = "attributes MyAttr" in result
    hasParamsBlock = "parameters main" in result
    hasParamLine = "weight type:#float default:1.5" in result
    hasClosing = result.strip().endswith(")")

    reporter.assert_test(
        hasHeader and hasParamsBlock and hasParamLine and hasClosing,
        "TC02 build_param_def_string 출력 형식 검증",
        f"hasHeader={hasHeader}, hasParamsBlock={hasParamsBlock}, "
        f"hasParamLine={hasParamLine}, hasClosing={hasClosing}\n결과:\n{result}",
    )
except Exception as e:
    reporter.error("TC02 build_param_def_string 출력 형식 검증", str(e))


# ============================================================
# TC03: build_param_def_string - 4가지 타입 포함 출력 확인
# ============================================================
try:
    result = attrService.build_param_def_string(_TEST_DEF_NAME, _TEST_PARAMS)

    hasFloat = "weight type:#float default:0.0" in result
    hasInteger = "count type:#integer default:0" in result
    hasBoolean = "enabled type:#boolean default:true" in result
    hasString = 'label type:#string default:""' in result

    reporter.assert_test(
        hasFloat and hasInteger and hasBoolean and hasString,
        "TC03 build_param_def_string 4가지 타입 출력 확인",
        f"hasFloat={hasFloat}, hasInteger={hasInteger}, "
        f"hasBoolean={hasBoolean}, hasString={hasString}\n결과:\n{result}",
    )
except Exception as e:
    reporter.error("TC03 build_param_def_string 4가지 타입 출력 확인", str(e))


# ============================================================
# TC04: add_attribute_def 성공
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    testNode = rt.Box(name="TestBox", width=10, height=10, length=10)

    addResult = attrService.add_attribute_def(testNode, _TEST_DEF_NAME, _TEST_PARAMS)

    reporter.assert_test(
        addResult is True,
        "TC04 add_attribute_def 성공",
        f"기대: True, 실제: {addResult}",
    )
except Exception as e:
    reporter.error("TC04 add_attribute_def 성공", str(e))


# ============================================================
# TC05: has_attribute_def True 확인 (추가 후)
# ============================================================
try:
    hasAttr = attrService.has_attribute_def(testNode, _TEST_DEF_NAME)

    reporter.assert_test(
        hasAttr is True,
        "TC05 has_attribute_def True 확인 (추가 후)",
        f"기대: True, 실제: {hasAttr}",
    )
except Exception as e:
    reporter.error("TC05 has_attribute_def True 확인 (추가 후)", str(e))


# ============================================================
# TC06: find_attribute_def 반환값 확인
# ============================================================
try:
    attrDef = attrService.find_attribute_def(testNode, _TEST_DEF_NAME)

    reporter.assert_test(
        attrDef is not None,
        "TC06 find_attribute_def 반환값 확인",
        f"기대: not None, 실제: {attrDef}",
    )
except Exception as e:
    reporter.error("TC06 find_attribute_def 반환값 확인", str(e))


# ============================================================
# TC07: add_attribute_def 중복 방지 (False 반환)
# ============================================================
try:
    dupResult = attrService.add_attribute_def(testNode, _TEST_DEF_NAME, _TEST_PARAMS)

    reporter.assert_test(
        dupResult is False,
        "TC07 add_attribute_def 중복 방지 (False 반환)",
        f"기대: False, 실제: {dupResult}",
    )
except Exception as e:
    reporter.error("TC07 add_attribute_def 중복 방지 (False 반환)", str(e))


# ============================================================
# TC08: get_all_attribute_defs 목록 확인
# ============================================================
try:
    allDefs = attrService.get_all_attribute_defs(testNode)

    reporter.assert_test(
        isinstance(allDefs, list) and len(allDefs) >= 1,
        "TC08 get_all_attribute_defs 목록 확인",
        f"기대: 리스트 길이 >= 1, 실제: {len(allDefs)}개",
    )
except Exception as e:
    reporter.error("TC08 get_all_attribute_defs 목록 확인", str(e))


# ============================================================
# TC09: remove_attribute_def 성공
# ============================================================
try:
    removeResult = attrService.remove_attribute_def(testNode, _TEST_DEF_NAME)

    reporter.assert_test(
        removeResult is True,
        "TC09 remove_attribute_def 성공",
        f"기대: True, 실제: {removeResult}",
    )
except Exception as e:
    reporter.error("TC09 remove_attribute_def 성공", str(e))


# ============================================================
# TC10: has_attribute_def False 확인 (제거 후)
# ============================================================
try:
    hasAttrAfterRemove = attrService.has_attribute_def(testNode, _TEST_DEF_NAME)

    reporter.assert_test(
        hasAttrAfterRemove is False,
        "TC10 has_attribute_def False 확인 (제거 후)",
        f"기대: False, 실제: {hasAttrAfterRemove}",
    )
except Exception as e:
    reporter.error("TC10 has_attribute_def False 확인 (제거 후)", str(e))


# ============================================================
# TC11: get_property - float 기본값 읽기
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    propNode = rt.Box(name="PropTestBox", width=10, height=10, length=10)
    attrService.add_attribute_def(propNode, _TEST_DEF_NAME, _TEST_PARAMS)

    weightVal = attrService.get_property(propNode, _TEST_DEF_NAME, "weight")

    reporter.assert_test(
        weightVal is not None and abs(float(weightVal) - 0.0) < 1e-6,
        "TC11 get_property float 기본값 읽기",
        f"기대: 0.0, 실제: {weightVal}",
    )
except Exception as e:
    reporter.error("TC11 get_property float 기본값 읽기", str(e))


# ============================================================
# TC12: set_property / get_property - float 값 변경 검증
# ============================================================
try:
    setResult = attrService.set_property(propNode, _TEST_DEF_NAME, "weight", 0.75)
    newWeightVal = attrService.get_property(propNode, _TEST_DEF_NAME, "weight")

    reporter.assert_test(
        setResult is True
        and newWeightVal is not None
        and abs(float(newWeightVal) - 0.75) < 1e-6,
        "TC12 set_property / get_property float 값 변경",
        f"setResult={setResult}, 기대: 0.75, 실제: {newWeightVal}",
    )
except Exception as e:
    reporter.error("TC12 set_property / get_property float 값 변경", str(e))


# ============================================================
# TC13: get_property / set_property - integer 타입 검증
# ============================================================
try:
    attrService.set_property(propNode, _TEST_DEF_NAME, "count", 42)
    countVal = attrService.get_property(propNode, _TEST_DEF_NAME, "count")

    reporter.assert_test(
        countVal is not None and int(countVal) == 42,
        "TC13 get_property / set_property integer 타입 검증",
        f"기대: 42, 실제: {countVal}",
    )
except Exception as e:
    reporter.error("TC13 get_property / set_property integer 타입 검증", str(e))


# ============================================================
# TC14: get_property / set_property - boolean 타입 검증
# ============================================================
try:
    attrService.set_property(propNode, _TEST_DEF_NAME, "enabled", False)
    enabledVal = attrService.get_property(propNode, _TEST_DEF_NAME, "enabled")

    reporter.assert_test(
        enabledVal is False,
        "TC14 get_property / set_property boolean 타입 검증",
        f"기대: False, 실제: {enabledVal}",
    )
except Exception as e:
    reporter.error("TC14 get_property / set_property boolean 타입 검증", str(e))


# ============================================================
# TC15: get_property / set_property - string 타입 검증
# ============================================================
try:
    attrService.set_property(propNode, _TEST_DEF_NAME, "label", "Hello")
    labelVal = attrService.get_property(propNode, _TEST_DEF_NAME, "label")

    reporter.assert_test(
        labelVal == "Hello",
        "TC15 get_property / set_property string 타입 검증",
        f"기대: 'Hello', 실제: {labelVal}",
    )
except Exception as e:
    reporter.error("TC15 get_property / set_property string 타입 검증", str(e))


# ============================================================
# TC16: get_all_properties 전체 읽기
# ============================================================
try:
    allProps = attrService.get_all_properties(propNode, _TEST_DEF_NAME)

    # 4가지 파라미터가 모두 포함되어 있어야 함
    hasAllKeys = (
        "weight" in allProps
        and "count" in allProps
        and "enabled" in allProps
        and "label" in allProps
    )

    reporter.assert_test(
        isinstance(allProps, dict) and hasAllKeys,
        "TC16 get_all_properties 전체 읽기",
        f"키 목록: {list(allProps.keys())}",
    )
except Exception as e:
    reporter.error("TC16 get_all_properties 전체 읽기", str(e))


# ============================================================
# TC17: set_all_properties 전체 쓰기 검증
# ============================================================
try:
    newValues = {
        "weight": 0.5,
        "count": 99,
        "enabled": True,
        "label": "Bulk",
    }
    setAllResult = attrService.set_all_properties(propNode, _TEST_DEF_NAME, newValues)

    # 값이 실제로 반영되었는지 확인
    verifyProps = attrService.get_all_properties(propNode, _TEST_DEF_NAME)
    weightOk = abs(float(verifyProps.get("weight", -1)) - 0.5) < 1e-6
    countOk = int(verifyProps.get("count", -1)) == 99
    enabledOk = verifyProps.get("enabled") is True
    labelOk = verifyProps.get("label") == "Bulk"

    reporter.assert_test(
        setAllResult is True and weightOk and countOk and enabledOk and labelOk,
        "TC17 set_all_properties 전체 쓰기 검증",
        f"setAllResult={setAllResult}, weightOk={weightOk}, countOk={countOk}, "
        f"enabledOk={enabledOk}, labelOk={labelOk}",
    )
except Exception as e:
    reporter.error("TC17 set_all_properties 전체 쓰기 검증", str(e))


# ============================================================
# TC18: 존재하지 않는 프로퍼티 get_property -> None 반환
# ============================================================
try:
    noneVal = attrService.get_property(propNode, _TEST_DEF_NAME, "nonexistent_prop")

    reporter.assert_test(
        noneVal is None,
        "TC18 존재하지 않는 프로퍼티 get_property None 반환",
        f"기대: None, 실제: {noneVal}",
    )
except Exception as e:
    reporter.error("TC18 존재하지 않는 프로퍼티 get_property None 반환", str(e))


# ============================================================
# TC19: 존재하지 않는 프로퍼티 set_property -> False 반환
# ============================================================
try:
    falseResult = attrService.set_property(
        propNode, _TEST_DEF_NAME, "nonexistent_prop", 123
    )

    reporter.assert_test(
        falseResult is False,
        "TC19 존재하지 않는 프로퍼티 set_property False 반환",
        f"기대: False, 실제: {falseResult}",
    )
except Exception as e:
    reporter.error("TC19 존재하지 않는 프로퍼티 set_property False 반환", str(e))


# ============================================================
# TC20: redefine_attribute_def 값 보존 검증
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    redefNode = rt.Box(name="RedefTestBox", width=10, height=10, length=10)

    # 초기 어트리뷰트 추가 후 값 설정
    attrService.add_attribute_def(redefNode, _TEST_DEF_NAME, _TEST_PARAMS)
    attrService.set_property(redefNode, _TEST_DEF_NAME, "weight", 0.33)
    attrService.set_property(redefNode, _TEST_DEF_NAME, "count", 7)

    # weight, count는 유지하고 새 파라미터 추가하는 방식으로 재정의
    newParams = [
        {"name": "weight", "type": "float", "default": 0.0},
        {"name": "count", "type": "integer", "default": 0},
        {"name": "newProp", "type": "boolean", "default": False},
    ]
    redefResult = attrService.redefine_attribute_def(
        redefNode, _TEST_DEF_NAME, newParams
    )

    # 재정의 후 기존 값이 복원되었는지 확인
    weightAfter = attrService.get_property(redefNode, _TEST_DEF_NAME, "weight")
    countAfter = attrService.get_property(redefNode, _TEST_DEF_NAME, "count")

    weightOk = weightAfter is not None and abs(float(weightAfter) - 0.33) < 1e-6
    countOk = countAfter is not None and int(countAfter) == 7

    reporter.assert_test(
        redefResult is True and weightOk and countOk,
        "TC20 redefine_attribute_def 값 보존 검증",
        f"redefResult={redefResult}, weightAfter={weightAfter} (기대 0.33), "
        f"countAfter={countAfter} (기대 7)",
    )
except Exception as e:
    reporter.error("TC20 redefine_attribute_def 값 보존 검증", str(e))


# ============================================================
# TC21: assign_float_controllers 할당 확인
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    ctrlNode = rt.Box(name="CtrlTestBox", width=10, height=10, length=10)

    # float 파라미터만 포함한 어트리뷰트 추가
    floatParams = [
        {"name": "alpha", "type": "float", "default": 0.0},
        {"name": "beta", "type": "float", "default": 1.0},
    ]
    attrService.add_attribute_def(ctrlNode, _TEST_DEF_NAME, floatParams)

    assignResult = attrService.assign_float_controllers(ctrlNode, _TEST_DEF_NAME)

    # 컨트롤러가 할당되었는지 확인
    caBlock = attrService._get_ca_block(ctrlNode, _TEST_DEF_NAME)
    alphaCtrl = rt.getPropertyController(caBlock, "alpha")
    betaCtrl = rt.getPropertyController(caBlock, "beta")

    reporter.assert_test(
        assignResult is True and alphaCtrl is not None and betaCtrl is not None,
        "TC21 assign_float_controllers 할당 확인",
        f"assignResult={assignResult}, alphaCtrl={alphaCtrl}, betaCtrl={betaCtrl}",
    )
except Exception as e:
    reporter.error("TC21 assign_float_controllers 할당 확인", str(e))


# ============================================================
# TC22: assign_float_controllers 중복 할당 방지
# ============================================================
try:
    # TC21에서 이미 컨트롤러 할당 완료. 동일 컨트롤러 객체 참조를 기억해 둔 뒤
    # 재호출 후에도 동일 컨트롤러가 유지되는지 확인.
    caBlockBefore = attrService._get_ca_block(ctrlNode, _TEST_DEF_NAME)
    alphaCtrlBefore = rt.getPropertyController(caBlockBefore, "alpha")

    # 재호출
    reassignResult = attrService.assign_float_controllers(ctrlNode, _TEST_DEF_NAME)

    caBlockAfter = attrService._get_ca_block(ctrlNode, _TEST_DEF_NAME)
    alphaCtrlAfter = rt.getPropertyController(caBlockAfter, "alpha")

    # 재호출도 True를 반환하고, 기존 컨트롤러가 교체되지 않아야 함
    # (MaxScript 객체 동일성: classOf로 타입 유지 확인)
    ctrlTypeOk = (
        alphaCtrlBefore is not None
        and alphaCtrlAfter is not None
        and str(rt.classOf(alphaCtrlBefore)) == str(rt.classOf(alphaCtrlAfter))
    )

    reporter.assert_test(
        reassignResult is True and ctrlTypeOk,
        "TC22 assign_float_controllers 중복 할당 방지",
        f"reassignResult={reassignResult}, "
        f"alphaBefore={alphaCtrlBefore}, alphaAfter={alphaCtrlAfter}",
    )
except Exception as e:
    reporter.error("TC22 assign_float_controllers 중복 할당 방지", str(e))


# ============================================================
# TC23: ensure_attribute_holder - 홀더 생성
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    holderNode = rt.Point(name="HolderNode")

    holder = attrService.ensure_attribute_holder(holderNode)

    reporter.assert_test(
        holder is not None
        and str(rt.classOf(holder)) == "EmptyModifier"
        and int(holderNode.modifiers.count) == 1,
        "TC23 ensure_attribute_holder 홀더 생성",
        f"holder={holder}, "
        f"classOf={rt.classOf(holder) if holder is not None else None}, "
        f"modifierCount={int(holderNode.modifiers.count)}",
    )
except Exception as e:
    reporter.error("TC23 ensure_attribute_holder 홀더 생성", str(e))


# ============================================================
# TC24: ensure_attribute_holder 멱등성 - 2회 호출해도 모디파이어 1개
# ============================================================
try:
    # TC23의 holderNode를 이어서 사용. 이미 홀더가 있는 상태에서 재호출.
    secondHolder = attrService.ensure_attribute_holder(holderNode)

    reporter.assert_test(
        secondHolder is not None and int(holderNode.modifiers.count) == 1,
        "TC24 ensure_attribute_holder 멱등성",
        f"2회 호출 후 modifierCount={int(holderNode.modifiers.count)} (기대 1), "
        f"secondHolder={secondHolder}",
    )
except Exception as e:
    reporter.error("TC24 ensure_attribute_holder 멱등성", str(e))


# ============================================================
# TC25: find_attribute_holder / find_attribute_holder_index
# ============================================================
try:
    foundHolder = attrService.find_attribute_holder(holderNode)
    foundIndex = attrService.find_attribute_holder_index(holderNode)

    reporter.assert_test(
        foundHolder is not None and foundIndex == 0,
        "TC25 find_attribute_holder / index 조회",
        f"foundHolder={foundHolder}, foundIndex={foundIndex} (기대 0)",
    )
except Exception as e:
    reporter.error("TC25 find_attribute_holder / index 조회", str(e))


# ============================================================
# TC26: 홀더 없는 노드 - find는 None, index는 -1, remove는 False
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    bareNode = rt.Point(name="BareNode")

    bareHolder = attrService.find_attribute_holder(bareNode)
    bareIndex = attrService.find_attribute_holder_index(bareNode)
    bareRemove = attrService.remove_attribute_holder(bareNode)

    reporter.assert_test(
        bareHolder is None and bareIndex == -1 and bareRemove is False,
        "TC26 홀더 부재 시 반환값",
        f"find={bareHolder} (기대 None), index={bareIndex} (기대 -1), "
        f"remove={bareRemove} (기대 False)",
    )
except Exception as e:
    reporter.error("TC26 홀더 부재 시 반환값", str(e))


# ============================================================
# TC27: remove_attribute_holder - 홀더와 그 위의 CA가 함께 사라진다
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    removeNode = rt.Point(name="RemoveNode")
    removeHolder = attrService.ensure_attribute_holder(removeNode)
    attrService.add_attribute_def_from_source(
        removeHolder, "HolderProbeData", _HOLDER_DEF_SOURCE
    )

    caBeforeRemove = attrService.find_attribute_def(removeHolder, "HolderProbeData")
    removeResult = attrService.remove_attribute_holder(removeNode)

    reporter.assert_test(
        caBeforeRemove is not None
        and removeResult is True
        and int(removeNode.modifiers.count) == 0
        and attrService.find_attribute_holder(removeNode) is None,
        "TC27 remove_attribute_holder 홀더+CA 동반 제거",
        f"caBeforeRemove={caBeforeRemove}, removeResult={removeResult}, "
        f"modifierCount={int(removeNode.modifiers.count)} (기대 0)",
    )
except Exception as e:
    reporter.error("TC27 remove_attribute_holder 홀더+CA 동반 제거", str(e))


# ============================================================
# TC28: add_attribute_def_from_source - 롤아웃 포함 정의를 모디파이어에 부착
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    srcNode = rt.Point(name="SrcNode")
    srcHolder = attrService.ensure_attribute_holder(srcNode)

    addResult = attrService.add_attribute_def_from_source(
        srcHolder, "HolderProbeData", _HOLDER_DEF_SOURCE
    )
    srcDef = attrService.find_attribute_def(srcHolder, "HolderProbeData")

    reporter.assert_test(
        addResult is True and srcDef is not None and str(srcDef.name) == "HolderProbeData",
        "TC28 add_attribute_def_from_source 롤아웃 포함 정의 부착",
        f"addResult={addResult}, srcDef={srcDef}",
    )
except Exception as e:
    reporter.error("TC28 add_attribute_def_from_source 롤아웃 포함 정의 부착", str(e))


# ============================================================
# TC29: add_attribute_def_from_source - 중복 부착 차단
# ============================================================
try:
    # TC28에서 이미 부착된 상태. 같은 이름 재부착은 False여야 한다.
    duplicateResult = attrService.add_attribute_def_from_source(
        srcHolder, "HolderProbeData", _HOLDER_DEF_SOURCE
    )

    reporter.assert_test(
        duplicateResult is False and rt.custAttributes.count(srcHolder) == 1,
        "TC29 add_attribute_def_from_source 중복 차단",
        f"duplicateResult={duplicateResult} (기대 False), "
        f"caCount={rt.custAttributes.count(srcHolder)} (기대 1)",
    )
except Exception as e:
    reporter.error("TC29 add_attribute_def_from_source 중복 차단", str(e))


# ============================================================
# TC30: add_attribute_def_from_source - 정의 이름 불일치 시 부착하지 않음
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    mismatchNode = rt.Point(name="MismatchNode")
    mismatchHolder = attrService.ensure_attribute_holder(mismatchNode)

    mismatchResult = attrService.add_attribute_def_from_source(
        mismatchHolder, "WrongName", _HOLDER_DEF_SOURCE
    )

    reporter.assert_test(
        mismatchResult is False and rt.custAttributes.count(mismatchHolder) == 0,
        "TC30 정의 이름 불일치 시 부착 차단",
        f"mismatchResult={mismatchResult} (기대 False), "
        f"caCount={rt.custAttributes.count(mismatchHolder)} (기대 0)",
    )
except Exception as e:
    reporter.error("TC30 정의 이름 불일치 시 부착 차단", str(e))


# ============================================================
# TC31: 모디파이어 대상 CRUD 왕복 (조회 -> 읽기/쓰기 -> 컨트롤러 -> 삭제)
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    crudNode = rt.Point(name="CrudNode")
    crudHolder = attrService.ensure_attribute_holder(crudNode)
    attrService.add_attribute_def_from_source(
        crudHolder, "HolderProbeData", _HOLDER_DEF_SOURCE
    )

    # 프로퍼티 목록
    propNames = set(attrService.get_all_properties(crudHolder, "HolderProbeData").keys())

    # 단일 읽기/쓰기
    setOk = attrService.set_property(crudHolder, "HolderProbeData", "holderWeight", 0.42)
    readBack = attrService.get_property(crudHolder, "HolderProbeData", "holderWeight")

    # 일괄 쓰기
    setAllOk = attrService.set_all_properties(
        crudHolder, "HolderProbeData", {"holderWeight": 0.8, "holderCount": 3}
    )
    allValues = attrService.get_all_properties(crudHolder, "HolderProbeData")

    # 컨트롤러 할당
    ctrlOk = attrService.assign_float_controllers(crudHolder, "HolderProbeData")
    crudBlock = attrService._get_ca_block(crudHolder, "HolderProbeData")
    weightCtrl = rt.getPropertyController(crudBlock, "holderWeight")

    # 정의 삭제 (모디파이어는 남는다)
    removeDefOk = attrService.remove_attribute_def(crudHolder, "HolderProbeData")

    reporter.assert_test(
        propNames == {"holderWeight", "holderCount"}
        and setOk is True
        and abs(readBack - 0.42) < 0.001
        and setAllOk is True
        and abs(allValues["holderWeight"] - 0.8) < 0.001
        and allValues["holderCount"] == 3
        and ctrlOk is True
        and weightCtrl is not None
        and removeDefOk is True
        and rt.custAttributes.count(crudHolder) == 0
        and int(crudNode.modifiers.count) == 1,
        "TC31 모디파이어 대상 CRUD 왕복",
        f"propNames={propNames}, setOk={setOk}, readBack={readBack}, "
        f"setAllOk={setAllOk}, allValues={allValues}, ctrlOk={ctrlOk}, "
        f"weightCtrl={weightCtrl}, removeDefOk={removeDefOk}, "
        f"caCount={rt.custAttributes.count(crudHolder)}, "
        f"modifierCount={int(crudNode.modifiers.count)}",
    )
except Exception as e:
    reporter.error("TC31 모디파이어 대상 CRUD 왕복", str(e))


# ============================================================
# TC32: 노드 기준 조회는 모디파이어 CA를 보지 못한다 (문서화된 범위 차이)
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    scopeNode = rt.Point(name="ScopeNode")
    scopeHolder = attrService.ensure_attribute_holder(scopeNode)
    attrService.add_attribute_def_from_source(
        scopeHolder, "HolderProbeData", _HOLDER_DEF_SOURCE
    )

    viaHolder = attrService.find_attribute_def(scopeHolder, "HolderProbeData")
    viaNode = attrService.find_attribute_def(scopeNode, "HolderProbeData")
    hasViaNode = attrService.has_attribute_def(scopeNode, "HolderProbeData")

    reporter.assert_test(
        viaHolder is not None and viaNode is None and hasViaNode is False,
        "TC32 노드 기준 조회는 모디파이어 CA 미노출",
        f"viaHolder={viaHolder} (기대 not None), viaNode={viaNode} (기대 None), "
        f"hasViaNode={hasViaNode} (기대 False)",
    )
except Exception as e:
    reporter.error("TC32 노드 기준 조회는 모디파이어 CA 미노출", str(e))


# ============================================================
# TC33: has_attribute_def가 모디파이어 대상에서 동작한다
#
# 종전에는 rt.isvalidnode 가드가 살아 있는 모디파이어에도 False를 반환해
# 어트리뷰트가 실제로 있어도 False가 나왔다. 생존 판정을 rt.isDeleted로 바꾼 뒤의
# 회귀 게이트다.
# ============================================================
try:
    hasViaHolder = attrService.has_attribute_def(scopeHolder, "HolderProbeData")
    hasWrongName = attrService.has_attribute_def(scopeHolder, "NoSuchDefName")

    reporter.assert_test(
        hasViaHolder is True and hasWrongName is False,
        "TC33 has_attribute_def 모디파이어 대상 동작",
        f"hasViaHolder={hasViaHolder} (기대 True), "
        f"hasWrongName={hasWrongName} (기대 False)",
    )
except Exception as e:
    reporter.error("TC33 has_attribute_def 모디파이어 대상 동작", str(e))


# ============================================================
# TC34: has_attribute_def의 노드 대상 동작이 보존된다
#
# 살아 있는 노드는 통과하고 삭제된 노드는 차단해야 한다 (기존 동작).
# ============================================================
try:
    rt.resetMaxFile(rt.Name("noPrompt"))
    liveNode = rt.Point(name="LiveNode")
    attrService.add_attribute_def(liveNode, _TEST_DEF_NAME, _TEST_PARAMS)
    hasOnLiveNode = attrService.has_attribute_def(liveNode, _TEST_DEF_NAME)

    doomedNode = rt.Point(name="DoomedNode")
    attrService.add_attribute_def(doomedNode, _TEST_DEF_NAME, _TEST_PARAMS)
    hasBeforeDelete = attrService.has_attribute_def(doomedNode, _TEST_DEF_NAME)
    rt.delete(doomedNode)
    hasAfterDelete = attrService.has_attribute_def(doomedNode, _TEST_DEF_NAME)

    hasOnNone = attrService.has_attribute_def(None, _TEST_DEF_NAME)

    reporter.assert_test(
        hasOnLiveNode is True
        and hasBeforeDelete is True
        and hasAfterDelete is False
        and hasOnNone is False,
        "TC34 has_attribute_def 노드 대상 동작 보존",
        f"살아있는 노드={hasOnLiveNode} (기대 True), "
        f"삭제 전={hasBeforeDelete} (기대 True), "
        f"삭제 후={hasAfterDelete} (기대 False), "
        f"None={hasOnNone} (기대 False)",
    )
except Exception as e:
    reporter.error("TC34 has_attribute_def 노드 대상 동작 보존", str(e))


# ============================================================
# 결과 요약 및 정리
# ============================================================
reporter.summary()
reporter.close()
