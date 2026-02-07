#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckLayer 클래스 테스트 - 3ds Max 환경에서 실행

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\Dropbox\Programing\Python\PyJalLib\tests\max\test_checkLayer.py").read())

로그 파일: tests/logs/test_max_checkLayer.log
"""

import sys
import logging
from pathlib import Path

from pymxs import runtime as rt

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pyjallib.max.checkLayer import CheckLayer
from pyjallib.max.layer import Layer

# 로그 설정
LOG_DIR = PROJECT_ROOT / "tests" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "test_max_checkLayer.log"

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

# 테스트용 레이어 계층 데이터
SAMPLE_HIERARCHY = [
    {"layer_name": "Bip", "layer_parent": ""},
    {"layer_name": "Bip_AddOn", "layer_parent": "Bip"},
    {"layer_name": "Bip_Controller", "layer_parent": "Bip"},
    {"layer_name": "Mesh", "layer_parent": ""},
    {"layer_name": "Rig", "layer_parent": ""},
    {"layer_name": "Rig_AddOn", "layer_parent": "Rig"},
    {"layer_name": "Rig_AddOn_Ankle", "layer_parent": "Rig_AddOn"}
]


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


def create_sample_layers():
    """SAMPLE_HIERARCHY 기반 레이어 계층 생성."""
    # 레이어 생성
    bipLayer = rt.LayerManager.newLayerFromName("Bip")
    bipAddOnLayer = rt.LayerManager.newLayerFromName("Bip_AddOn")
    bipControllerLayer = rt.LayerManager.newLayerFromName("Bip_Controller")
    rt.LayerManager.newLayerFromName("Mesh")
    rigLayer = rt.LayerManager.newLayerFromName("Rig")
    rigAddOnLayer = rt.LayerManager.newLayerFromName("Rig_AddOn")
    rigAddOnAnkleLayer = rt.LayerManager.newLayerFromName("Rig_AddOn_Ankle")

    # 부모-자식 관계 설정
    bipAddOnLayer.setParent(bipLayer)
    bipControllerLayer.setParent(bipLayer)
    rigAddOnLayer.setParent(rigLayer)
    rigAddOnAnkleLayer.setParent(rigAddOnLayer)


def run_tests():
    """CheckLayer 전체 테스트 실행."""
    global _passed, _failed
    logger.info("=== TEST START: CheckLayer ===")

    layerService = Layer()

    # --- TC01: 인스턴스 생성 (layerService 주입) ---
    try:
        checker = CheckLayer(layerService=layerService)
        assert_test(checker is not None, "TC01 인스턴스 생성 (layerService 주입)")
    except Exception as e:
        assert_test(False, "TC01 인스턴스 생성", str(e))
        logger.info("=== TEST END (인스턴스 생성 실패로 중단) ===")
        return

    # --- TC02: 인스턴스 생성 (layerService 없이) ---
    try:
        checker_no_svc = CheckLayer()
        assert_test(
            checker_no_svc.layerService is None,
            "TC02 layerService 없이 인스턴스 생성, layerService == None"
        )
    except Exception as e:
        assert_test(False, "TC02 layerService 없이 인스턴스 생성", str(e))

    # --- TC03: 메서드 존재 확인 ---
    expected_methods = [
        "set_layer_hierarchy",
        "has_empty_layers",
        "fix_empty_layers",
        "is_default_layer_empty",
        "is_correct_layer_name",
        "has_correct_layer_names",
        "is_object_in_correct_layer",
    ]
    for method_name in expected_methods:
        assert_test(
            hasattr(checker, method_name) and callable(getattr(checker, method_name)),
            f"TC03 메서드 존재: {method_name}"
        )

    # --- TC04: set_layer_hierarchy 데이터 저장 ---
    try:
        checker.set_layer_hierarchy(SAMPLE_HIERARCHY)
        assert_test(
            checker._layerHierarchy == SAMPLE_HIERARCHY,
            "TC04 set_layer_hierarchy 데이터 저장"
        )
    except Exception as e:
        assert_test(False, "TC04 set_layer_hierarchy", str(e))

    # --- TC05: set_layer_hierarchy 덮어쓰기 ---
    try:
        new_hierarchy = [{"layer_name": "Custom", "layer_parent": ""}]
        checker.set_layer_hierarchy(new_hierarchy)
        assert_test(
            len(checker._layerHierarchy) == 1,
            "TC05 set_layer_hierarchy 덮어쓰기"
        )
        # 원복
        checker.set_layer_hierarchy(SAMPLE_HIERARCHY)
    except Exception as e:
        assert_test(False, "TC05 set_layer_hierarchy 덮어쓰기", str(e))

    # --- TC06: 빈 씬에서 has_empty_layers ---
    # 새 씬으로 리셋 후 테스트
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        result = checker.has_empty_layers()
        assert_test(
            isinstance(result, bool),
            "TC06 has_empty_layers 반환 타입이 bool",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC06 has_empty_layers", str(e))

    # --- TC07: 빈 레이어 생성 후 has_empty_layers == True ---
    try:
        rt.LayerManager.newLayerFromName("TestEmptyLayer")
        result = checker.has_empty_layers()
        assert_test(
            result is True,
            "TC07 빈 레이어 생성 후 has_empty_layers == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC07 빈 레이어 생성 후 검사", str(e))

    # --- TC08: fix_empty_layers로 빈 레이어 삭제 ---
    try:
        checker.fix_empty_layers()
        result = checker.has_empty_layers()
        assert_test(
            result is False,
            "TC08 fix_empty_layers 후 has_empty_layers == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC08 fix_empty_layers", str(e))

    # --- TC09: is_default_layer_empty (빈 씬) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        result = checker.is_default_layer_empty()
        assert_test(
            result is True,
            "TC09 빈 씬에서 is_default_layer_empty == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC09 is_default_layer_empty 빈 씬", str(e))

    # --- TC10: 기본 레이어에 오브젝트 추가 후 is_default_layer_empty == False ---
    try:
        testBox = rt.Box()
        defaultLayer = rt.layerManager.getLayer(0)
        defaultLayer.addNode(testBox)
        result = checker.is_default_layer_empty()
        assert_test(
            result is False,
            "TC10 오브젝트 추가 후 is_default_layer_empty == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC10 is_default_layer_empty 오브젝트 추가", str(e))

    # --- TC11: 올바른 레이어 구조 생성 후 has_correct_layer_names ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        checker.set_layer_hierarchy(SAMPLE_HIERARCHY)
        create_sample_layers()

        result = checker.has_correct_layer_names()
        assert_test(
            result is True,
            "TC11 올바른 레이어 구조에서 has_correct_layer_names == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC11 has_correct_layer_names", str(e))

    # --- TC12: is_correct_layer_name 개별 레이어 검증 (등록된 이름) ---
    try:
        result_bip = checker.is_correct_layer_name("Bip")
        result_addon = checker.is_correct_layer_name("Bip_AddOn")
        result_ankle = checker.is_correct_layer_name("Rig_AddOn_Ankle")
        all_pass = result_bip is True and result_addon is True and result_ankle is True
        assert_test(
            all_pass,
            "TC12 is_correct_layer_name 개별 검증 (Bip, Bip_AddOn, Rig_AddOn_Ankle)",
            f"Bip: {result_bip}, Bip_AddOn: {result_addon}, Rig_AddOn_Ankle: {result_ankle}"
        )
    except Exception as e:
        assert_test(False, "TC12 is_correct_layer_name", str(e))

    # --- TC13: is_correct_layer_name parent_* 패턴 매칭 ---
    # 계층에 없지만 부모 레이어의 "parent_*" 패턴에 매칭되는 레이어
    try:
        rigNewLayer = rt.LayerManager.newLayerFromName("Rig_Custom")
        rigParent = rt.LayerManager.getLayerFromName("Rig")
        rigNewLayer.setParent(rigParent)
        result = checker.is_correct_layer_name("Rig_Custom")
        assert_test(
            result is True,
            "TC13 parent_* 패턴 매칭: Rig_Custom (부모 Rig) == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC13 is_correct_layer_name parent_* 패턴", str(e))

    # --- TC14: is_correct_layer_name 미등록 레이어 -> False ---
    try:
        rt.LayerManager.newLayerFromName("UnknownLayer")
        result = checker.is_correct_layer_name("UnknownLayer")
        assert_test(
            result is False,
            "TC14 미등록 레이어 is_correct_layer_name == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC14 is_correct_layer_name 미등록", str(e))

    # --- TC15: is_object_in_correct_layer (Geo -> Mesh_* 레이어) ---
    try:
        meshSubLayer = rt.LayerManager.newLayerFromName("Mesh_Body")
        meshParent = rt.LayerManager.getLayerFromName("Mesh")
        meshSubLayer.setParent(meshParent)

        testBox = rt.Box(name="TestGeo")
        meshSubLayer.addNode(testBox)
        result = checker.is_object_in_correct_layer(testBox)
        assert_test(
            result is True,
            "TC15 Geometry가 Mesh_Body 레이어에 있을 때 == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC15 is_object_in_correct_layer Geo", str(e))

    # --- TC16: is_object_in_correct_layer (Bone -> Bone_* 레이어) ---
    try:
        boneLayer = rt.LayerManager.newLayerFromName("Bone")
        boneSubLayer = rt.LayerManager.newLayerFromName("Bone_Body")
        boneSubLayer.setParent(boneLayer)

        testBone = rt.BoneSys.createBone(
            rt.Point3(0, 0, 0),
            rt.Point3(10, 0, 0),
            rt.Point3(0, 0, 1)
        )
        boneSubLayer.addNode(testBone)
        result = checker.is_object_in_correct_layer(testBone)
        assert_test(
            result is True,
            "TC16 Bone이 Bone_Body 레이어에 있을 때 == True",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC16 is_object_in_correct_layer Bone", str(e))

    # --- TC17: is_object_in_correct_layer (Geo가 Mesh가 아닌 레이어) -> False ---
    try:
        testBox2 = rt.Box(name="TestGeo2")
        bipLayer = rt.LayerManager.getLayerFromName("Bip")
        bipLayer.addNode(testBox2)
        result = checker.is_object_in_correct_layer(testBox2)
        assert_test(
            result is False,
            "TC17 Geometry가 Bip 레이어에 있을 때 == False",
            f"실제: {result}"
        )
    except Exception as e:
        assert_test(False, "TC17 is_object_in_correct_layer Geo 잘못된 레이어", str(e))

    # --- 정리 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
    except Exception:
        pass

    # --- 결과 요약 ---
    total = _passed + _failed
    logger.info(f"=== TEST END: {_passed}/{total} passed, {_failed} failed ===")


run_tests()
