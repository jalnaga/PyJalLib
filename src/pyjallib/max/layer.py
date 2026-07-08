#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Layer 모듈 - 3ds Max 레이어 관리 기능
원본 MAXScript의 layer.ms를 Python으로 변환
"""

from pymxs import runtime as rt

class Layer:
    """3ds Max 레이어의 생성·삭제·노드 이동·조회 등 레이어 관리 기능을 제공한다."""

    def __init__(self):
        """Layer 클래스를 초기화한다."""
        pass

    def reset_layer(self):
        """모든 레이어를 삭제하고 소속 객체를 기본 레이어(0번)로 이동한다."""
        # 기본 레이어(0번 레이어) 가져오기
        defaultLayer = rt.layerManager.getLayer(0)
        layerNameArray = []
        defaultLayer.current = True
        
        # 레이어가 1개 이상 존재하면
        if rt.LayerManager.count > 1:
            # 모든 레이어 순회하며 객체들을 기본 레이어로 이동
            for i in range(1, rt.layerManager.count):
                ilayer = rt.layerManager.getLayer(i)
                layerName = ilayer.name
                layerNameArray.append(layerName)
                
                layer = rt.ILayerManager.getLayerObject(i)
                layerNodes = rt.refs.dependents(layer)
                
                # 레이어의 모든 노드를 기본 레이어로 이동
                for item in layerNodes:
                    if rt.isValidNode(item):
                        defaultLayer.addNode(item)
            
            # 모든 레이어 삭제
            for item in layerNameArray:
                rt.LayerManager.deleteLayerByName(item)
    
    def get_nodes_from_layer(self, inLayerNum):
        """레이어 번호로 해당 레이어의 유효한 노드들을 수집한다.

        Args:
            inLayerNum (int | False | None): 레이어 번호. False나 None이면 빈 리스트를 반환한다.

        Returns:
            list[rt.Node]: 레이어에 포함된 노드 리스트. 빈 리스트 가능
        """
        returnVal = []
        
        if inLayerNum is False or inLayerNum is None:
            return returnVal
        
        code = f"""
        layer = layermanager.getLayer {inLayerNum}
        layer.nodes &theNodes
        theNodes
        """

        nodes = rt.execute(code)
        
        for item in nodes:
            if rt.isValidNode(item):
                returnVal.append(item)
                    
        return returnVal
    
    def get_layer_number(self, inLayerName):
        """레이어 이름으로 레이어 번호를 찾는다.

        Args:
            inLayerName (str): 레이어 이름

        Returns:
            int | False: 레이어 번호. 해당 이름의 레이어가 없으면 False
        """
        # 모든 레이어를 순회하며 이름 비교
        for i in range(rt.LayerManager.count):
            layer = rt.layerManager.getLayer(i)
            if layer.name == inLayerName:
                return i
        
        return False
    
    def get_layer_by_namepattern(self, inLayerNamePattern):
        """이름 패턴과 일치하는 레이어들의 이름을 수집한다.

        Args:
            inLayerNamePattern (str): 레이어 이름 패턴 (와일드카드 사용 가능)

        Returns:
            list[str]: 패턴과 일치하는 레이어 이름 리스트
        """
        returnVal = []
        for i in range(rt.LayerManager.count):
            layer = rt.layerManager.getLayer(i)
            if rt.matchPattern(layer.name, pattern=inLayerNamePattern):
                returnVal.append(layer.name)
        
        return returnVal
    
    def get_nodes_by_layername(self, inLayerName):
        """레이어 이름으로 해당 레이어의 노드들을 수집한다.

        Args:
            inLayerName (str): 레이어 이름

        Returns:
            list[rt.Node]: 레이어에 포함된 노드 리스트. 레이어가 없으면 빈 리스트
        """
        return self.get_nodes_from_layer(self.get_layer_number(inLayerName))
    
    def del_empty_layer(self, showLog=False):
        """노드가 없는 빈 레이어를 모두 삭제한다.

        Args:
            showLog (bool): True면 삭제된 레이어 수를 출력한다.
        """
        deleted_layer_count = 0
        deflayer = rt.layermanager.getlayer(0)
        deflayer.current = True
        
        # 모든 레이어를 역순으로 순회 (삭제 시 인덱스 변경 문제 방지)
        for i in range(rt.Layermanager.count-1, 0, -1):
            layer = rt.layermanager.getLayer(i)
            thisLayerName = layer.name
            nodes = self.get_nodes_from_layer(i)
            
            # 노드가 없는 레이어 삭제
            if len(nodes) == 0:
                rt.LayerManager.deleteLayerbyname(thisLayerName)
                deleted_layer_count += 1
        
        # 로그 표시 옵션이 활성화되어 있고 삭제된 레이어가 있는 경우
        if showLog and deleted_layer_count != 0:
            print(f"Number of layers removed = {deleted_layer_count}")
    
    def create_layer_from_array(self, inArray, inLayerName):
        """객체 배열로 레이어를 생성하고 객체들을 추가한다.

        동일 이름의 레이어가 이미 있으면 새로 만들지 않고 그 레이어에 객체를 추가한다.

        Args:
            inArray (list[rt.Node]): 레이어에 추가할 객체 배열
            inLayerName (str): 생성할 레이어 이름

        Returns:
            rt.MixinInterface: 생성되었거나 기존에 존재하던 레이어 객체
        """
        new_layer = None
        layer_index = self.get_layer_number(inLayerName)
        
        # 레이어가 없으면 새로 생성, 있으면 기존 레이어 사용
        if layer_index is False:
            new_layer = rt.LayerManager.newLayer()
            new_layer.setName(inLayerName)
        else:
            new_layer = rt.layerManager.getLayer(layer_index)
        
        # 모든 객체를 레이어에 추가
        for item in inArray:
            new_layer.addNode(item)
        
        return new_layer
    
    def delete_layer(self, inLayerName, forceDelete=False):
        """레이어를 삭제하고 소속 객체를 삭제하거나 기본 레이어로 이동한다.

        Args:
            inLayerName (str): 삭제할 레이어 이름
            forceDelete (bool): True면 레이어 내 객체도 함께 삭제한다. False면 객체를 기본 레이어로 이동한다.

        Returns:
            bool: 레이어 삭제 성공 여부
        """
        return_val = False
        deflayer = rt.layermanager.getlayer(0)
        deflayer.current = True
        
        # 레이어의 모든 노드 가져오기
        nodes = self.get_nodes_by_layername(inLayerName)
        
        if len(nodes) > 0:
            if forceDelete:
                # 강제 삭제 옵션이 켜져 있으면 객체도 함께 삭제
                rt.delete(nodes)
                nodes = rt.Array()
            else:
                # 아니면 기본 레이어로 이동
                for item in nodes:
                    deflayer.addNode(item)
        
        # 레이어 삭제
        return_val = rt.LayerManager.deleteLayerbyname(inLayerName)
        
        return return_val
    
    def set_parent_layer(self, inLayerName, inParentName):
        """레이어의 부모 레이어를 설정한다.

        Args:
            inLayerName (str): 자식 레이어 이름
            inParentName (str): 부모 레이어 이름

        Returns:
            bool: 두 레이어가 모두 존재하여 부모 설정에 성공하면 True
        """
        returnVal = False
        
        # 타겟 레이어와 부모 레이어 가져오기
        targetLayer = rt.layermanager.getlayer(self.get_layer_number(inLayerName))
        parentLayer = rt.layermanager.getlayer(self.get_layer_number(inParentName))
        
        # 두 레이어가 모두 존재하면 부모 설정
        if targetLayer is not None and parentLayer is not None:
            targetLayer.setParent(parentLayer)
            returnVal = True
        
        return returnVal
    
    def rename_layer_from_index(self, inLayerIndex, searchFor, replaceWith):
        """레이어 이름에서 특정 문자열을 찾아 교체한다.

        Args:
            inLayerIndex (int): 레이어 인덱스
            searchFor (str): 검색할 문자열
            replaceWith (str): 교체할 문자열
        """
        targetLayer = rt.LayerManager.getLayer(inLayerIndex)
        layerName = targetLayer.name
        
        # 문자열 찾기
        find_at = layerName.find(searchFor)
        
        # 찾은 경우 교체
        if find_at != -1:
            new_name = layerName.replace(searchFor, replaceWith)
            targetLayer.setName(new_name)
    
    def get_nodes_in_layer_and_children(self, inLayerName: str) -> list:
        """레이어와 하위 레이어에서 노드를 재귀적으로 수집한다.

        지정된 레이어의 노드뿐 아니라, 그 하위 레이어(자식 레이어)의
        노드까지 재귀적으로 모두 수집하여 반환한다.

        Args:
            inLayerName (str): 대상 레이어 이름

        Returns:
            list[rt.Node]: 수집된 노드 리스트. 레이어가 존재하지 않으면 빈 리스트
        """
        rootLayer = rt.LayerManager.getLayerFromName(inLayerName)
        if rootLayer is None:
            return []

        return self._collect_nodes_from_layer(rootLayer)

    def _collect_nodes_from_layer(self, inLayer) -> list:
        """레이어 객체에서 노드를 재귀적으로 수집하는 내부 메서드.

        Args:
            inLayer: 대상 레이어 객체

        Returns:
            수집된 노드 리스트
        """
        nodeList = []

        # 현재 레이어의 노드 수집
        layerNum = self.get_layer_number(inLayer.name)
        if layerNum is not False:
            nodeList = self.get_nodes_from_layer(layerNum)

        # 하위 레이어의 노드 재귀 수집
        for i in range(rt.LayerManager.count):
            childLayer = rt.layerManager.getLayer(i)
            if childLayer is not None:
                parentLayer = childLayer.getParent()
                if parentLayer is not None and parentLayer.name == inLayer.name:
                    nodeList.extend(self._collect_nodes_from_layer(childLayer))

        return nodeList

    def is_valid_layer(self, inLayerName=None, inLayerIndex=None):
        """이름 또는 인덱스로 레이어의 존재 여부를 확인한다.

        Args:
            inLayerName (str | None): 레이어 이름. None이면 inLayerIndex로 확인한다.
            inLayerIndex (int | None): 레이어 인덱스

        Returns:
            bool: 레이어가 존재하면 True
        """
        layer = None
        
        # 이름으로 확인
        if inLayerName is not None:
            layer = rt.LayerManager.getLayerFromName(inLayerName)
        # 인덱스로 확인
        elif inLayerIndex is not None:
            layer = rt.LayerManager.getLayer(inLayerIndex)
        
        # 레이어가 있으면 True, 없으면 False
        return layer is not None