#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# Layer 모듈

3ds Max의 레이어 시스템을 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 레이어 생성 및 삭제
- 레이어 계층 구조 관리
- 레이어 이름 변경 및 속성 설정
- 노드와 레이어 간 연결 관리
- 빈 레이어 정리

## 구현 정보
- 원본 MAXScript의 layer.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt
import pymxs

class Layer:
    """
    # Layer 클래스
    
    3ds Max의 레이어 관리 기능을 제공하는 클래스입니다.
    
    ## 주요 기능
    - 레이어 생성, 삭제, 이름 변경
    - 레이어에 객체 추가 및 제거
    - 레이어 부모-자식 관계 설정
    - 빈 레이어 정리
    - 레이어 유효성 검사
    
    ## 구현 정보
    - MAXScript의 _Layer 구조체를 Python 클래스로 재구현
    - pymxs.runtime을 통해 3ds Max의 레이어 관리 기능 직접 제어
    
    ## 사용 예시
    ```python
    # Layer 객체 생성
    layer_mgr = Layer()
    
    # 선택된 객체로 새 레이어 생성
    new_layer = layer_mgr.create_layer_from_array(rt.selection, "MyLayer")
    
    # 빈 레이어 정리
    layer_mgr.del_empty_layer()
    
    # 레이어 이름 변경
    layer_mgr.rename_layer_from_index(1, "Old", "New")
    ```
    """
    
    def __init__(self):
        """
        Layer 클래스를 초기화합니다.
        """
        pass
    
    def reset_layer(self):
        """
        모든 레이어를 초기화하고 모든 객체를 기본 레이어로 이동합니다.
        
        ## 동작 방식
        1. 기본 레이어(0번 레이어)를 현재 레이어로 설정
        2. 모든 추가 레이어의 객체를 기본 레이어로 이동
        3. 빈 레이어가 된 추가 레이어들을 삭제
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
        레이어 번호로 해당 레이어의 객체들을 가져옵니다.
        
        ## Parameters
        - inLayerNum (int): 레이어 번호 (0부터 시작)
            
        ## Returns
        - list: 레이어에 포함된 노드 배열 또는 빈 배열 (레이어가 없는 경우)
        
        ## 동작 방식
        1. 지정된 레이어 번호의 레이어 객체 가져오기
        2. refs.dependents를 사용하여 레이어에 종속된 모든 노드 가져오기
        3. 유효한 노드만 필터링하여 반환
        """
        returnVal = []
        layer = rt.ILayerManager.getLayerObject(inLayerNum)
        if layer is not None:
            layerNodes = rt.refs.dependents(layer)
            for item in layerNodes:
                if rt.isValidNode(item):
                    returnVal.append(item)
                    
        return returnVal
    
    def get_layer_number(self, inLayerName):
        """
        레이어 이름으로 레이어 번호를 찾습니다.
        
        ## Parameters
        - inLayerName (str): 레이어 이름
            
        ## Returns
        - int or bool: 레이어 번호 또는 False (없는 경우)
        
        ## 동작 방식
        모든 레이어를 순회하며 이름이 일치하는 레이어의 인덱스를 반환합니다.
        """
        for i in range(rt.LayerManager.count):
            layer = rt.layerManager.getLayer(i)
            if layer.name == inLayerName:
                return i
        
        return False
    
    def get_nodes_by_layername(self, inLayerName):
        """
        레이어 이름으로 해당 레이어의 객체들을 가져옵니다.
        
        ## Parameters
        - inLayerName (str): 레이어 이름
            
        ## Returns
        - list: 레이어에 포함된 노드 배열
        
        ## 동작 방식
        get_layer_number와 get_nodes_from_layer를 조합하여 레이어 이름으로 노드를 가져옵니다.
        """
        return self.get_nodes_from_layer(self.get_layer_number(inLayerName))
    
    def del_empty_layer(self, showLog=False):
        """
        빈 레이어를 삭제합니다.
        
        ## Parameters
        - showLog (bool): 삭제 결과 메시지 표시 여부 (기본값: False)
        
        ## 동작 방식
        1. 기본 레이어(0번 레이어)를 현재 레이어로 설정
        2. 레이어를 역순으로 순회하며 빈 레이어 확인 및 삭제
        3. 설정에 따라 삭제된 레이어 수 메시지 표시
        
        ## 참고
        역순으로 순회하는 이유는 레이어 삭제 시 인덱스가 변경되는 문제를 방지하기 위함입니다.
        """
        deleted_layer_count = 0
        deflayer = rt.layermanager.getlayer(0)
        deflayer.current = True
        
        for i in range(rt.Layermanager.count-1, 0, -1):
            layer = rt.layermanager.getLayer(i)
            thisLayerName = layer.name
            nodes = self.get_nodes_from_layer(i)
            
            if len(nodes) == 0:
                rt.LayerManager.deleteLayerbyname(thisLayerName)
                deleted_layer_count += 1
        
        if showLog and deleted_layer_count != 0:
            print(f"Number of layers removed = {deleted_layer_count}")
    
    def create_layer_from_array(self, inArray, inLayerName):
        """
        객체 배열로 새 레이어를 생성합니다.
        
        ## Parameters
        - inArray (list): 레이어에 추가할 객체 배열
        - inLayerName (str): 생성할 레이어 이름
            
        ## Returns
        - ILayer: 생성된 레이어 객체
        
        ## 동작 방식
        1. 지정된 이름의 레이어가 있는지 확인
        2. 없으면 새 레이어 생성, 있으면 기존 레이어 사용
        3. 배열의 모든 객체를 레이어에 추가
        """
        new_layer = None
        layer_index = self.get_layer_number(inLayerName)
        
        if layer_index is False:
            new_layer = rt.LayerManager.newLayer()
            new_layer.setName(inLayerName)
        else:
            new_layer = rt.layerManager.getLayer(layer_index)
        
        for item in inArray:
            new_layer.addNode(item)
        
        return new_layer
    
    def delete_layer(self, inLayerName, forceDelete=False):
        """
        레이어를 삭제합니다.
        
        ## Parameters
        - inLayerName (str): 삭제할 레이어 이름
        - forceDelete (bool): 레이어 내 객체도 함께 삭제할지 여부 (기본값: False)
            
        ## Returns
        - bool: 삭제 성공 여부
        
        ## 동작 방식
        1. 기본 레이어(0번 레이어)를 현재 레이어로 설정
        2. 레이어의 모든 노드 가져오기
        3. forceDelete=True면 노드 함께 삭제, False면 기본 레이어로 이동
        4. 레이어 삭제
        """
        return_val = False
        deflayer = rt.layermanager.getlayer(0)
        deflayer.current = True
        
        nodes = self.get_nodes_by_layername(inLayerName)
        
        if len(nodes) > 0:
            if forceDelete:
                rt.delete(nodes)
                nodes = rt.Array()
            else:
                for item in nodes:
                    deflayer.addNode(item)
        
        return_val = rt.LayerManager.deleteLayerbyname(inLayerName)
        
        return return_val
    
    def set_parent_layer(self, inLayerName, inParentName):
        """
        레이어 부모-자식 관계를 설정합니다.
        
        ## Parameters
        - inLayerName (str): 자식 레이어 이름
        - inParentName (str): 부모 레이어 이름
            
        ## Returns
        - bool: 설정 성공 여부
        
        ## 동작 방식
        1. 타겟 레이어와 부모 레이어 객체 가져오기
        2. 두 레이어가 모두 유효하면 부모-자식 관계 설정
        """
        returnVal = False
        
        targetLayer = rt.layermanager.getlayer(self.get_layer_number(inLayerName))
        parentLayer = rt.layermanager.getlayer(self.get_layer_number(inParentName))
        
        if targetLayer is not None and parentLayer is not None:
            targetLayer.setParent(parentLayer)
            returnVal = True
        
        return returnVal
    
    def rename_layer_from_index(self, inLayerIndex, searchFor, replaceWith):
        """
        레이어 이름의 특정 부분을 교체합니다.
        
        ## Parameters
        - inLayerIndex (int): 레이어 인덱스
        - searchFor (str): 검색할 문자열
        - replaceWith (str): 교체할 문자열
        
        ## 동작 방식
        1. 지정된 인덱스의 레이어 가져오기
        2. 레이어 이름에서 검색 문자열 찾기
        3. 문자열 교체 후 새 이름 설정
        """
        targetLayer = rt.LayerManager.getLayer(inLayerIndex)
        layerName = targetLayer.name
        
        find_at = layerName.find(searchFor)
        
        if find_at != -1:
            new_name = layerName.replace(searchFor, replaceWith)
            targetLayer.setName(new_name)
    
    def is_valid_layer(self, inLayerName=None, inLayerIndex=None):
        """
        레이어가 유효한지 확인합니다.
        
        ## Parameters
        - inLayerName (str, optional): 확인할 레이어 이름 (기본값: None)
        - inLayerIndex (int, optional): 확인할 레이어 인덱스 (기본값: None)
            
        ## Returns
        - bool: 레이어 유효 여부
        
        ## 동작 방식
        - 이름 또는 인덱스로 레이어를 가져와 존재 여부 확인
        - 두 매개변수 모두 None이면 False 반환
        """
        layer = None
        
        if inLayerName is not None:
            layer = rt.LayerManager.getLayerFromName(inLayerName)
        elif inLayerIndex is not None:
            layer = rt.LayerManager.getLayer(inLayerIndex)
        
        return layer is not None