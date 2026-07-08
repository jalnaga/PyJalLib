#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckLayer 모듈 - 3ds Max 레이어 검사 기능
원본 MAXScript의 ODC_Char_AssetChecks_Struct 중 LAYER 섹션을 Python으로 변환
"""

from pymxs import runtime as rt


class CheckLayer:
    """3ds Max 레이어의 이름·계층 구조·빈 레이어를 검증하고 수정하는 클래스.

    딕셔너리 리스트로 정의한 레이어 계층을 검증 기준으로 사용한다.
    """

    def __init__(self, layerService=None):
        """CheckLayer를 초기화한다.

        Args:
            layerService (Layer | None): 레이어 조회·빈 레이어 삭제에 사용하는 Layer 서비스 인스턴스
        """
        self.layerService = layerService
        self._layerHierarchy = []

    def set_layer_hierarchy(self, inLayerHierarchy):
        """레이어 계층 정의를 설정한다.

        딕셔너리 리스트를 내부 레이어 계층 데이터로 저장하여 검증 기준으로 사용한다.

        Args:
            inLayerHierarchy (list[dict]): {layer_name: str, layer_parent: str} 형태의 레이어 계층 리스트
        """
        self._layerHierarchy = inLayerHierarchy

    def has_empty_layers(self):
        """빈 레이어가 존재하는지 확인한다.

        기본 레이어(0번)를 제외한 모든 레이어를 순회하며 노드가 없는 레이어를 찾는다.

        Returns:
            bool: 빈 레이어가 존재하면 True
        """
        for i in range(rt.LayerManager.count - 1, 0, -1):
            nodes = self.layerService.get_nodes_from_layer(i)
            if len(nodes) == 0:
                return True
        return False

    def fix_empty_layers(self):
        """빈 레이어가 없을 때까지 반복적으로 삭제한다.

        부모-자식 관계 때문에 한 번의 삭제로 모든 빈 레이어가 제거되지 않을 수 있으므로 반복한다.
        """
        while self.has_empty_layers():
            self.layerService.del_empty_layer()

    def is_default_layer_empty(self):
        """기본 레이어(0번)가 비어있는지 확인한다.

        Returns:
            bool: 기본 레이어에 노드가 없으면 True
        """
        nodes = self.layerService.get_nodes_from_layer(0)
        return len(nodes) == 0

    def is_correct_layer_name(self, inLayerName):
        """레이어 이름이 계층 정의 기준으로 유효한지 검증한다.

        레이어 존재 여부, 계층 정의 내 이름 등록 여부, 부모 이름 등록 여부를 확인하고,
        조건을 만족하지 않으면 "부모이름_*" 패턴 매칭을 추가로 시도한다.

        Args:
            inLayerName (str): 검증할 레이어 이름

        Returns:
            bool: 레이어 이름이 유효하면 True. 레이어가 존재하지 않으면 False
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
        """모든 레이어 이름이 유효한지 확인한다.

        기본 레이어(0번)를 제외한 모든 레이어에 is_correct_layer_name을 적용한다.

        Returns:
            bool: 모든 레이어 이름이 유효하면 True
        """
        for i in range(rt.LayerManager.count - 1, 0, -1):
            selLayer = rt.layerManager.getLayer(i)
            layerName = selLayer.name
            if not self.is_correct_layer_name(layerName):
                return False
        return True

    def is_object_in_layer(self, inObj, inExpectedLayerName):
        """오브젝트가 특정 레이어에 속해 있는지 확인한다.

        레이어 계층 검증이나 규칙 적용 없이 오브젝트의 레이어 이름만 비교한다.

        Args:
            inObj (rt.Node): 검증할 오브젝트
            inExpectedLayerName (str): 기대하는 레이어 이름

        Returns:
            bool: 오브젝트가 해당 레이어에 있으면 True. 오브젝트나 레이어가 None이면 False
        """
        if inObj is None or inObj.layer is None:
            return False

        return inObj.layer.name == inExpectedLayerName

    def is_object_in_correct_layer_by_type(self, inObj):
        """오브젝트 타입에 따라 올바른 레이어에 있는지 확인한다.

        Geometry(Biped/BoneGeometry 제외)는 Mesh_* 레이어 또는 Utility 최상위 레이어,
        Point/BoneGeometry/Biped/Dummy(Biped 자식)는 Bone_* 레이어에 있어야 한다.
        레이어 이름 자체가 계층 정의 기준으로 유효하지 않으면 False를 반환한다.

        Args:
            inObj (rt.Node): 검증할 오브젝트

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
        """레이어의 최상위 부모 레이어 이름을 반환한다.

        Args:
            inLayerName (str): 레이어 이름

        Returns:
            str: 최상위 부모 레이어 이름. 부모가 없으면 자기 자신의 이름, 레이어가 존재하지 않으면 빈 문자열
        """
        layerIndex = self.layerService.get_layer_number(inLayerName)
        if layerIndex is False:
            return ""

        currentLayer = rt.layerManager.getLayer(layerIndex)
        while currentLayer.getParent() is not None:
            currentLayer = currentLayer.getParent()

        return currentLayer.name
