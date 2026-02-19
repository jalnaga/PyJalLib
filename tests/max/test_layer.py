#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Layer 클래스 테스트 - 3ds Max 환경에서 실행

3ds Max의 레이어 관리 기능을 검증하는 테스트 스위트.
TestReporter를 사용하여 결과를 로그 파일로 기록한다.

실행 방법:
    3ds Max > Scripting > Run Script > 이 파일 선택
    또는 3ds Max Python 콘솔에서:
        exec(open(r"D:\\Dropbox\\Programing\\Code\\PyJalLib\\tests\\max\\test_layer.py").read())

로그 파일: tests/logs/test_Layer.log
"""

import sys
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.layer import Layer

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Layer", LOG_DIR)


def run_tests():
    """Layer 클래스의 전체 테스트를 실행한다."""

    # --- TC01: Layer 인스턴스 생성 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        reporter.assert_test(
            layer is not None,
            "TC01 Layer 인스턴스 생성",
            "Layer() 반환값이 None"
        )
    except Exception as e:
        reporter.error("TC01 Layer 인스턴스 생성", str(e))

    # --- TC02: 기본 레이어 존재 확인 (인덱스 0) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        defaultLayer = rt.layerManager.getLayer(0)
        reporter.assert_test(
            defaultLayer is not None,
            "TC02 기본 레이어 존재 확인",
            "인덱스 0 레이어가 None"
        )
    except Exception as e:
        reporter.error("TC02 기본 레이어 존재 확인", str(e))

    # --- TC03: create_layer_from_array() - 새 레이어 생성 및 노드 추가 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        box1 = rt.Box(name="TestBox1")
        box2 = rt.Box(name="TestBox2")
        newLayer = layer.create_layer_from_array([box1, box2], "TestLayer")

        reporter.assert_test(
            newLayer is not None,
            "TC03 create_layer_from_array 레이어 생성",
            "반환된 레이어가 None"
        )
        # 레이어에 노드가 추가되었는지 확인
        nodes = layer.get_nodes_by_layername("TestLayer")
        reporter.assert_test(
            len(nodes) == 2,
            "TC03 create_layer_from_array 노드 추가",
            f"기대: 2, 실제: {len(nodes)}"
        )
    except Exception as e:
        reporter.error("TC03 create_layer_from_array", str(e))

    # --- TC04: get_layer_number() - 레이어 이름으로 번호 찾기 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        box = rt.Box(name="TestBox")
        layer.create_layer_from_array([box], "FindMe")
        layerNum = layer.get_layer_number("FindMe")

        reporter.assert_test(
            layerNum is not False and layerNum > 0,
            "TC04 get_layer_number 레이어 번호 조회",
            f"기대: 0보다 큰 정수, 실제: {layerNum}"
        )
    except Exception as e:
        reporter.error("TC04 get_layer_number", str(e))

    # --- TC05: get_nodes_by_layername() - 레이어 이름으로 노드 조회 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        box1 = rt.Box(name="NodeA")
        box2 = rt.Box(name="NodeB")
        box3 = rt.Box(name="NodeC")
        layer.create_layer_from_array([box1, box2, box3], "NodeLayer")

        nodes = layer.get_nodes_by_layername("NodeLayer")
        reporter.assert_test(
            len(nodes) == 3,
            "TC05 get_nodes_by_layername 노드 조회",
            f"기대: 3, 실제: {len(nodes)}"
        )
    except Exception as e:
        reporter.error("TC05 get_nodes_by_layername", str(e))

    # --- TC06: is_valid_layer() - 유효한 레이어 확인 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        box = rt.Box(name="ValidBox")
        layer.create_layer_from_array([box], "ValidLayer")

        result = layer.is_valid_layer(inLayerName="ValidLayer")
        reporter.assert_test(
            result is True,
            "TC06 is_valid_layer 유효한 레이어",
            f"기대: True, 실제: {result}"
        )
    except Exception as e:
        reporter.error("TC06 is_valid_layer 유효한 레이어", str(e))

    # --- TC07: is_valid_layer() - 존재하지 않는 레이어 False 확인 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()

        result = layer.is_valid_layer(inLayerName="NonExistentLayer")
        reporter.assert_test(
            result is False,
            "TC07 is_valid_layer 존재하지 않는 레이어",
            f"기대: False, 실제: {result}"
        )
    except Exception as e:
        reporter.error("TC07 is_valid_layer 존재하지 않는 레이어", str(e))

    # --- TC08: del_empty_layer() - 빈 레이어 삭제 확인 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        # 빈 레이어 생성 (노드 없이)
        rt.LayerManager.newLayerFromName("EmptyLayer1")
        rt.LayerManager.newLayerFromName("EmptyLayer2")
        countBefore = rt.LayerManager.count

        layer.del_empty_layer()
        countAfter = rt.LayerManager.count

        reporter.assert_test(
            countAfter < countBefore,
            "TC08 del_empty_layer 빈 레이어 삭제",
            f"삭제 전: {countBefore}, 삭제 후: {countAfter}"
        )
    except Exception as e:
        reporter.error("TC08 del_empty_layer", str(e))

    # --- TC09: delete_layer() - 레이어 삭제 (객체 기본 레이어로 이동) ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        box = rt.Box(name="MoveBox")
        layer.create_layer_from_array([box], "DeleteMe")

        # 삭제 전 레이어 존재 확인
        existsBefore = layer.is_valid_layer(inLayerName="DeleteMe")

        layer.delete_layer("DeleteMe")

        # 삭제 후 레이어 확인
        existsAfter = layer.is_valid_layer(inLayerName="DeleteMe")

        reporter.assert_test(
            existsBefore is True and existsAfter is False,
            "TC09 delete_layer 레이어 삭제",
            f"삭제 전: {existsBefore}, 삭제 후: {existsAfter}"
        )

        # 노드가 기본 레이어로 이동했는지 확인
        defaultLayerNodes = layer.get_nodes_from_layer(0)
        movedBoxFound = False
        for node in defaultLayerNodes:
            if node.name == "MoveBox":
                movedBoxFound = True
                break
        reporter.assert_test(
            movedBoxFound is True,
            "TC09 delete_layer 노드 기본 레이어 이동",
            "삭제된 레이어의 노드가 기본 레이어에서 발견되지 않음"
        )
    except Exception as e:
        reporter.error("TC09 delete_layer", str(e))

    # --- TC10: reset_layer() - 모든 레이어 초기화 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
        layer = Layer()
        # 여러 레이어 생성
        box1 = rt.Box(name="ResetBox1")
        box2 = rt.Box(name="ResetBox2")
        layer.create_layer_from_array([box1], "Layer1")
        layer.create_layer_from_array([box2], "Layer2")
        rt.LayerManager.newLayerFromName("EmptyLayer")

        layer.reset_layer()

        # 기본 레이어(인덱스 0)만 남아야 함
        reporter.assert_test(
            rt.LayerManager.count == 1,
            "TC10 reset_layer 레이어 초기화",
            f"기대: 레이어 1개, 실제: {rt.LayerManager.count}개"
        )
    except Exception as e:
        reporter.error("TC10 reset_layer", str(e))

    # --- 최종 정리 ---
    try:
        rt.resetMaxFile(rt.Name("noPrompt"))
    except Exception:
        pass


# 테스트 실행
run_tests()
reporter.summary()
reporter.close()
