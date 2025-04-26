#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Layer 모듈 - 3ds Max 레이어 관리 기능
원본 MAXScript의 layer.ms를 Python으로 변환
"""

from pymxs import runtime as rt
import pymxs

class Layer:
    """
    레이어 관련 기능을 위한 클래스
    MAXScript의 _Layer 구조체를 Python 클래스로 변환
    
    pymxs 모듈을 통해 3ds Max의 레이어 관리 기능을 제어합니다.
    """
    
    def __init__(self):
        """
        초기화 함수
        """
        pass
    
    def reset_layer(self):
        """
        모든 레이어를 초기화하고 기본 레이어로 객체 이동
        
        Returns:
            None
        """
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
        """
        레이어 번호로 해당 레이어의 노드들을 가져옴
        
        Args:
            inLayerNum: 레이어 번호
            
        Returns:
            레이어에 포함된 노드 배열 또는 빈 배열
        """
        layer = rt.ILayerManager.getLayerObject(inLayerNum)
        if layer is not None:
            layerNodes = rt.refs.dependents(layer)
            return layerNodes
        else:
            return rt.Array()
    
    def get_layer_number(self, inLayerName):
        """
        레이어 이름으로 레이어 번호를 찾음
        
        Args:
            inLayerName: 레이어 이름
            
        Returns:
            레이어 번호 또는 False (없는 경우)
        """
        # 모든 레이어를 순회하며 이름 비교
        for i in range(rt.LayerManager.count):
            layer = rt.layerManager.getLayer(i)
            if layer.name == inLayerName:
                return i
        
        return False
    
    def get_nodes_by_layername(self, inLayerName):
        """
        레이어 이름으로 해당 레이어의 노드들을 가져옴
        
        Args:
            inLayerName: 레이어 이름
            
        Returns:
            레이어에 포함된 노드 배열
        """
        return self.get_nodes_from_layer(self.get_layer_number(inLayerName))
    
    def del_empty_layer(self, showLog=False):
        """
        빈 레이어 삭제
        
        Args:
            showLog: 삭제 결과 메시지 표시 여부
            
        Returns:
            None
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
        """
        객체 배열로 새 레이어 생성
        
        Args:
            inArray: 레이어에 추가할 객체 배열
            inLayerName: 생성할 레이어 이름
            
        Returns:
            생성된 레이어
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
        """
        레이어 삭제
        
        Args:
            inLayerName: 삭제할 레이어 이름
            forceDelete: 레이어 내 객체도 함께 삭제할지 여부 (False면 기본 레이어로 이동)
            
        Returns:
            성공 여부
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
        """
        레이어 부모 설정
        
        Args:
            inLayerName: 자식 레이어 이름
            inParentName: 부모 레이어 이름
            
        Returns:
            성공 여부
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
        """
        레이어 이름의 특정 부분을 교체
        
        Args:
            inLayerIndex: 레이어 인덱스
            searchFor: 검색할 문자열
            replaceWith: 교체할 문자열
            
        Returns:
            None
        """
        targetLayer = rt.LayerManager.getLayer(inLayerIndex)
        layerName = targetLayer.name
        
        # 문자열 찾기
        find_at = layerName.find(searchFor)
        
        # 찾은 경우 교체
        if find_at != -1:
            new_name = layerName.replace(searchFor, replaceWith)
            targetLayer.setName(new_name)
    
    def is_valid_layer(self, inLayerName=None, inLayerIndex=None):
        """
        유효한 레이어인지 확인
        
        Args:
            inLayerName: 레이어 이름 (선택)
            inLayerIndex: 레이어 인덱스 (선택)
            
        Returns:
            유효 여부
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