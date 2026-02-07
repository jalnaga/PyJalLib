#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckLayer 모듈 - 3ds Max 레이어 검사 기능
원본 MAXScript의 ODC_Char_AssetChecks_Struct 중 LAYER 섹션을 Python으로 변환
"""

from pymxs import runtime as rt


class CheckLayer:
    """
    레이어 검사를 위한 클래스

    레이어 이름, 계층 구조, 빈 레이어 등을 검증하는 기능을 제공합니다.
    딕셔너리 리스트로 유효한 레이어 계층 정의를 설정하여 검증 기준으로 사용합니다.

    Attributes:
        layerService: Layer 서비스 인스턴스
    """

    def __init__(self, layerService=None):
        """
        초기화 함수

        Args:
            layerService: Layer 서비스 인스턴스 (빈 레이어 삭제 등에 사용)
        """
        self.layerService = layerService
        self._layerHierarchy = []

    def set_layer_hierarchy(self, inLayerHierarchy):
        """
        레이어 계층 정의를 설정.

        딕셔너리 리스트를 받아 내부 레이어 계층 데이터로 저장합니다.
        각 딕셔너리는 "layer_name"과 "layer_parent" 키를 포함해야 합니다.

        Args:
            inLayerHierarchy: 레이어 계층 딕셔너리 리스트
                예: [{"layer_name": "Mesh_Body", "layer_parent": "Mesh"}, ...]

        Returns:
            None
        """
        self._layerHierarchy = inLayerHierarchy

    def has_empty_layers(self):
        """
        빈 레이어가 존재하는지 확인.

        기본 레이어(0번)를 제외한 모든 레이어를 순회하며
        노드가 없는 레이어가 있는지 확인합니다.

        Returns:
            bool: 빈 레이어가 존재하면 True
        """
        for i in range(rt.LayerManager.count - 1, 0, -1):
            nodes = self.layerService.get_nodes_from_layer(i)
            if len(nodes) == 0:
                return True
        return False

    def fix_empty_layers(self):
        """
        빈 레이어를 반복적으로 삭제.

        부모-자식 관계 때문에 한 번으로 모든 빈 레이어가 삭제되지 않을 수 있으므로
        빈 레이어가 없을 때까지 반복합니다.

        Returns:
            None
        """
        while self.has_empty_layers():
            self.layerService.del_empty_layer()

    def is_default_layer_empty(self):
        """
        기본 레이어(0번)가 비어있는지 확인.

        Returns:
            bool: 기본 레이어에 노드가 없으면 True
        """
        nodes = self.layerService.get_nodes_from_layer(0)
        return len(nodes) == 0

    def is_correct_layer_name(self, inLayerName):
        """
        레이어 이름이 유효한지 계층 데이터 기준으로 검증.

        검증 절차:
        1. 레이어가 존재하는지 확인
        2. 계층 데이터에 레이어 이름이 등록되어 있는지 확인
        3. 부모 레이어가 있으면 부모 이름도 등록되어 있는지 확인
        4. 위 조건을 만족하지 않으면, parent_* 패턴 매칭을 시도

        Args:
            inLayerName: 검증할 레이어 이름

        Returns:
            bool: 레이어 이름이 유효하면 True
        """
        layerIndex = self.layerService.get_layer_number(inLayerName)
        if layerIndex is False:
            return False

        validNames = [item["layer_name"] for item in self._layerHierarchy]
        validParents = [item["layer_parent"] for item in self._layerHierarchy]

        selLayer = rt.layerManager.getLayer(layerIndex)
        layerName = selLayer.name
        parentLayer = selLayer.getParent()
        layerParent = parentLayer.name if parentLayer is not None else ""

        nameFound = layerName in validNames
        parentValid = True
        if layerParent != "":
            parentValid = layerParent in validParents

        if nameFound and parentValid:
            return True

        # 부모_* 패턴 매칭 시도
        if layerParent != "":
            if rt.matchPattern(layerName, pattern=layerParent + "_*"):
                return True

        return False

    def has_correct_layer_names(self):
        """
        모든 레이어 이름이 유효한지 확인.

        기본 레이어(0번)를 제외한 모든 레이어에 is_correct_layer_name을 적용합니다.

        Returns:
            bool: 모든 레이어 이름이 유효하면 True
        """
        for i in range(rt.LayerManager.count - 1, 0, -1):
            selLayer = rt.layerManager.getLayer(i)
            layerName = selLayer.name
            if not self.is_correct_layer_name(layerName):
                return False
        return True

    def is_object_in_correct_layer(self, inObj):
        """
        오브젝트가 올바른 레이어에 있는지 확인.

        Geometry(Biped/BoneGeometry 제외) -> Mesh_* 레이어
        Bone/Point/Biped/Dummy(Biped 자식) -> Bone_* 레이어

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: 오브젝트가 올바른 레이어에 있으면 True
        """
        layerName = inObj.layer.name

        if not self.is_correct_layer_name(layerName):
            return False

        isGeo = (
            rt.superClassOf(inObj) == rt.GeometryClass
            and rt.classOf(inObj) != rt.Biped_Object
            and rt.classOf(inObj) != rt.BoneGeometry
        )
        isBone = (
            rt.classOf(inObj) == rt.Point
            or rt.classOf(inObj) == rt.BoneGeometry
            or rt.classOf(inObj) == rt.Biped_Object
            or (
                rt.classOf(inObj) == rt.Dummy
                and inObj.parent is not None
                and rt.classOf(inObj.parent) == rt.Biped_Object
            )
        )

        if isGeo:
            if rt.matchPattern(layerName, pattern="Mesh_*"):
                return True
            # Utility 최상위 레이어 확인
            topParent = self._get_top_parent_layer_name(layerName)
            if topParent == "Utility":
                return True
            return False

        if isBone:
            if rt.matchPattern(layerName, pattern="Bone_*"):
                return True
            return False

        return False

    def _get_top_parent_layer_name(self, inLayerName):
        """
        레이어의 최상위 부모 레이어 이름을 반환.

        Args:
            inLayerName: 레이어 이름

        Returns:
            str: 최상위 부모 레이어 이름. 부모가 없으면 자기 자신의 이름 반환.
        """
        layerIndex = self.layerService.get_layer_number(inLayerName)
        if layerIndex is False:
            return ""

        currentLayer = rt.layerManager.getLayer(layerIndex)
        while currentLayer.getParent() is not None:
            currentLayer = currentLayer.getParent()

        return currentLayer.name
