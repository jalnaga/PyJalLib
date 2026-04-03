#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
선택 모듈 - 3ds Max용 객체 선택 관련 기능 제공
원본 MAXScript의 select.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

import time

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .bone import Bone
from .layer import Layer


class Select:
    """
    객체 선택 관련 기능을 제공하는 클래스.
    MAXScript의 _Select 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, boneService=None, layerService=None):
        """
        클래스 초기화

        Args:
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
            boneService: Bone 서비스 인스턴스 (제공되지 않으면 새로 생성)
            layerService: Layer 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name)
        self.layer = layerService if layerService else Layer()
    
    def set_selectionSet_to_all(self):
        """
        모든 유형의 객체를 선택하도록 필터 설정
        """
        rt.SetSelectFilter(1)
    
    def set_selectionSet_to_bone(self):
        """
        뼈대 객체만 선택하도록 필터 설정
        """
        rt.SetSelectFilter(8)
    
    def reset_selectionSet(self):
        """
        선택 필터를 기본값으로 재설정
        """
        rt.SetSelectFilter(1)
    
    def set_selectionSet_to_helper(self):
        """
        헬퍼 객체만 선택하도록 필터 설정
        """
        rt.SetSelectFilter(6)
    
    def set_selectionSet_to_point(self):
        """
        포인트 객체만 선택하도록 필터 설정
        """
        rt.SetSelectFilter(10)
    
    def set_selectionSet_to_spline(self):
        """
        스플라인 객체만 선택하도록 필터 설정
        """
        rt.SetSelectFilter(3)
    
    def set_selectionSet_to_mesh(self):
        """
        메시 객체만 선택하도록 필터 설정
        """
        rt.SetSelectFilter(2)
    
    def filter_bip(self):
        """
        현재 선택 항목에서 Biped 객체만 필터링하여 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.Biped_Object]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_bone(self):
        """
        현재 선택 항목에서 뼈대 객체만 필터링하여 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.BoneGeometry]
            rt.clearSelection()
            rt.select(filtered_sel)
            
    def filter_end_bone(self):
        """
        현재 선택 항목에서 뼈대 객체만 필터링하여 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if self.bone.is_end_bone(item)]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_helper(self):
        """
        현재 선택 항목에서 헬퍼 객체(Point, IK_Chain)만 필터링하여 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.Point or rt.classOf(item) == rt.IK_Chain_Object]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_expTm(self):
        """
        현재 선택 항목에서 ExposeTm 객체만 필터링하여 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.ExposeTm]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_spline(self):
        """
        현재 선택 항목에서 스플라인 객체만 필터링하여 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.superClassOf(item) == rt.shape]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def select_children(self, inObj, includeSelf=False):
        """
        객체의 모든 자식을 선택
        
        Args:
            in_obj: 부모 객체
            include_self: 자신도 포함할지 여부 (기본값: False)
            
        Returns:
            선택된 자식 객체 리스트
        """
        children = self.bone.select_every_children(inObj=inObj, includeSelf=includeSelf)
        
        return children
    
    def distinguish_hierachy_objects(self, inArray):
        """
        계층이 있는 객체와 없는 객체 구분
        
        Args:
            inArray: 검사할 객체 배열
            
        Returns:
            [계층이 없는 객체 배열, 계층이 있는 객체 배열]
        """
        return_array = [[], []]  # 첫 번째는 독립 객체, 두 번째는 계층 객체
        
        for item in inArray:
            if item.parent is None and item.children.count == 0:
                return_array[0].append(item)  # 부모와 자식이 없는 경우
            else:
                return_array[1].append(item)  # 부모나 자식이 있는 경우
        
        return return_array
    
    def get_nonLinked_objects(self, inArray):
        """
        링크(계층구조)가 없는 독립 객체만 반환
        
        Args:
            inArray: 검사할 객체 배열
            
        Returns:
            독립적인 객체 배열
        """
        return self.distinguish_hierachy_objects(inArray)[0]
    
    def get_linked_objects(self, inArray):
        """
        링크(계층구조)가 있는 객체만 반환
        
        Args:
            inArray: 검사할 객체 배열
            
        Returns:
            계층 구조를 가진 객체 배열
        """
        return self.distinguish_hierachy_objects(inArray)[1]
    
    def sort_by_hierachy(self, inArray):
        """
        객체를 계층 구조에 따라 정렬
        
        Args:
            inArray: 정렬할 객체 배열
            
        Returns:
            계층 순서대로 정렬된 객체 배열
        """
        return self.bone.sort_bones_as_hierarchy(inArray)
    
    def sort_by_index(self, inArray):
        """
        객체를 이름에 포함된 인덱스 번호에 따라 정렬
        
        Args:
            inArray: 정렬할 객체 배열
            
        Returns:
            인덱스 순서대로 정렬된 객체 배열
        """
        if len(inArray) == 0:
            return []
        
        nameArray = [item.name for item in inArray]
        sortedNameArray = self.name.sort_by_index(nameArray)
        
        sortedArray = [item for item in inArray]
        
        for i, sortedName in enumerate(sortedNameArray):
            foundIndex = nameArray.index(sortedName)
            sortedArray[i] = inArray[foundIndex]
        
        return sortedArray
    
    def sort_objects(self, inArray):
        """
        객체를 적절한 방법으로 정렬 (독립 객체와 계층 객체 모두 고려)
        
        Args:
            inArray: 정렬할 객체 배열
            
        Returns:
            정렬된 객체 배열
        """
        returnArray = []
        
        # 독립 객체와 계층 객체 분류
        aloneObjArray = self.get_nonLinked_objects(inArray)
        hierachyObjArray = self.get_linked_objects(inArray)
        
        # 각각의 방식으로 정렬
        sortedAloneObjArray = self.sort_by_index(aloneObjArray)
        sortedHierachyObjArray = self.sort_by_hierachy(hierachyObjArray)
        
        # 첫 인덱스 비교를 위한 초기화
        firstIndexOfAloneObj = 10000
        firstIndexOfHierachyObj = 10000
        is_alone_importer = False
        
        # 독립 객체의 첫 인덱스 확인
        if len(sortedAloneObjArray) > 0:
            index_digit = self.name.get_index_as_digit(sortedAloneObjArray[0].name)
            if index_digit is False:
                firstIndexOfAloneObj = 0
            else:
                firstIndexOfAloneObj = index_digit
        
        # 계층 객체의 첫 인덱스 확인
        if len(sortedHierachyObjArray) > 0:
            index_digit = self.name.get_index_as_digit(sortedHierachyObjArray[0].name)
            if index_digit is False:
                firstIndexOfHierachyObj = 0
            else:
                firstIndexOfHierachyObj = index_digit
        
        # 인덱스에 따라 순서 결정
        if firstIndexOfAloneObj < firstIndexOfHierachyObj:
            is_alone_importer = True
            
        # 결정된 순서에 따라 배열 합치기    
        if is_alone_importer:
            for item in sortedAloneObjArray:
                returnArray.append(item)
            for item in sortedHierachyObjArray:
                returnArray.append(item)
        else:
            for item in sortedHierachyObjArray:
                returnArray.append(item)
            for item in sortedAloneObjArray:
                returnArray.append(item)
        
        return returnArray

    def get_all_dependencies_optimized(self, inObjs, inVisited=None):
        """재귀적으로 모든 dependency 노드를 수집한다.

        Handle 기반 O(1) 중복 체크와 BFS queue를 사용하여 최적화된 성능을 제공한다.
        controller dependencies, skin dependencies, parent chain을 수집하며
        Biped_Object는 스킵한다.

        Args:
            inObjs: 단일 오브젝트 또는 오브젝트 리스트
            inVisited: 이미 방문한 노드의 handle set (재사용 가능)

        Returns:
            tuple: (node_array, visited)
                - node_array: 수집된 노드 리스트
                - visited: 업데이트된 visited set
        """
        if inVisited is None:
            inVisited = set()

        nodeArray = []
        nodeHandles = set()

        # queue 초기화
        if hasattr(inObjs, '__iter__') and not isinstance(inObjs, str):
            queue = list(inObjs)
        else:
            queue = [inObjs]

        # 자주 사용하는 함수 로컬 참조 (속도 향상)
        getHandleByAnim = rt.getHandleByAnim
        classof = rt.classof
        bipedObject = rt.Biped_Object
        isvalidnode = rt.isvalidnode
        isProperty = rt.isProperty
        rtName = rt.Name
        refsDependson = rt.refs.dependson

        while queue:
            obj = queue.pop()

            # visited 체크 (handle 기반)
            objHandle = getHandleByAnim(obj)
            if objHandle in inVisited:
                continue
            inVisited.add(objHandle)

            # Biped_Object는 스킵
            if classof(obj) == bipedObject:
                continue

            # controller dependencies
            if hasattr(obj, 'controller') and obj.controller is not None:
                deps = refsDependson(obj.controller)
                for dep in deps:
                    if isvalidnode(dep):
                        depHandle = getHandleByAnim(dep)
                        if depHandle not in nodeHandles:
                            nodeHandles.add(depHandle)
                            nodeArray.append(dep)
                    else:
                        queue.append(dep)

            # skin dependencies
            if isProperty(obj, rtName('skin')) and obj.skin is not None:
                deps = refsDependson(obj.skin)
                for dep in deps:
                    if isvalidnode(dep):
                        depHandle = getHandleByAnim(dep)
                        if depHandle not in nodeHandles:
                            nodeHandles.add(depHandle)
                            nodeArray.append(dep)
                    else:
                        queue.append(dep)

            # parent chain
            if isvalidnode(obj):
                objHandleNode = getHandleByAnim(obj)
                if objHandleNode not in nodeHandles:
                    nodeHandles.add(objHandleNode)
                    nodeArray.append(obj)
                if obj.parent is not None:
                    queue.append(obj.parent)

        return nodeArray, inVisited

    def get_dependents(self, inObjs):
        """children과 DependentNodes를 수집한다.

        입력 오브젝트의 모든 자식을 재귀적으로 수집한 후,
        각 오브젝트의 DependentNodes도 수집하여 합산 반환한다.
        Handle 기반 O(1) 중복 체크를 사용한다.

        Args:
            inObjs: 오브젝트 리스트

        Returns:
            list: 수집된 dependent 노드 리스트 (children + DependentNodes)
        """
        objs = list(inObjs)
        objsHandles = {rt.getHandleByAnim(o) for o in objs}

        dependentsNodes = []
        dependentsHandles = set()

        # 자주 사용하는 함수 로컬 참조
        getHandleByAnim = rt.getHandleByAnim
        dependentNodes = rt.refs.DependentNodes

        # children 수집 (원본 리스트에 추가)
        initialCount = len(objs)
        i = 0
        while i < len(objs):
            obj = objs[i]
            for c in obj.children:
                cHandle = getHandleByAnim(c)
                if cHandle not in objsHandles:
                    objsHandles.add(cHandle)
                    objs.append(c)
            i += 1

        # 재귀적으로 수집된 children을 결과에 포함
        for obj in objs[initialCount:]:
            objHandle = getHandleByAnim(obj)
            if objHandle not in dependentsHandles:
                dependentsHandles.add(objHandle)
                dependentsNodes.append(obj)

        # DependentNodes 수집
        for obj in objs:
            for d in dependentNodes(obj):
                dHandle = getHandleByAnim(d)
                if dHandle not in dependentsHandles:
                    dependentsHandles.add(dHandle)
                    dependentsNodes.append(d)

        return dependentsNodes

    def collect_addon_helpers(self, inDeps):
        """Rig_AddOn_* 레이어에서 Helper 클래스 노드를 수집한다.

        dependency 노드 리스트에서 Rig_AddOn_* 레이어에 속한 노드를 찾고,
        해당 레이어의 모든 Helper 클래스 노드를 수집한다.

        Args:
            inDeps: dependency 노드 리스트

        Returns:
            set: 수집된 AddOn Helper 노드 set
        """
        addonHelper = set()
        processedLayers = set()
        helperClass = rt.helper
        superClassof = rt.superClassof

        for item in inDeps:
            layerName = item.layer.name
            if layerName.startswith('Rig_AddOn_') and layerName not in processedLayers:
                processedLayers.add(layerName)
                objsInLayer = self.layer.get_nodes_by_layername(layerName)
                for obj in objsInLayer:
                    if superClassof(obj) == helperClass:
                        addonHelper.add(obj)

        return addonHelper

    def select_dependencies(self, inObjs):
        """전체 플로우를 실행하여 dependency를 수집한다.

        get_dependents -> get_all_dependencies_optimized (1차) ->
        get_all_dependencies_optimized (2차, visited 재사용) ->
        collect_addon_helpers -> 결합 순서로 dependency를 수집한다.

        Args:
            inObjs: 선택된 오브젝트 리스트

        Returns:
            dict: {
                'nodes': 최종 노드 리스트 (combined),
                'stats': {
                    'selected_count': 선택된 오브젝트 수,
                    'dependents_count': dependents 수,
                    'dependencies_1st_count': 1차 dependencies 수,
                    'dependencies_2nd_count': 2차 dependencies 수,
                    'addon_helpers_count': AddOn Helper 수,
                    'total_count': 최종 노드 수,
                    'time_dependents_ms': get_dependents 소요 시간 (ms),
                    'time_dependencies_1st_ms': 1차 dependencies 소요 시간 (ms),
                    'time_dependencies_2nd_ms': 2차 dependencies 소요 시간 (ms),
                    'time_total_ms': 전체 소요 시간 (ms)
                }
            }
        """
        tTotal = time.time()
        stats = {}

        objs = list(inObjs)
        stats['selected_count'] = len(objs)

        # get_dependents 호출
        t1 = time.time()
        dependents = self.get_dependents(objs)
        stats['dependents_count'] = len(dependents)
        stats['time_dependents_ms'] = (time.time() - t1) * 1000

        # 1차 dependency 탐색
        t2 = time.time()
        visited = set()
        dependsOn, visited = self.get_all_dependencies_optimized(objs, visited)
        stats['dependencies_1st_count'] = len(dependsOn)
        stats['time_dependencies_1st_ms'] = (time.time() - t2) * 1000

        # 2차 dependency 탐색 (visited 재사용)
        t3 = time.time()
        allDeps, visited = self.get_all_dependencies_optimized(dependsOn, visited)
        stats['dependencies_2nd_count'] = len(allDeps)
        stats['time_dependencies_2nd_ms'] = (time.time() - t3) * 1000

        # AddOn Helpers 수집
        addonHelpers = self.collect_addon_helpers(allDeps)
        stats['addon_helpers_count'] = len(addonHelpers)

        # 최종 결합
        combined = list(addonHelpers | set(allDeps) | set(dependsOn) | set(objs))
        stats['total_count'] = len(combined)
        stats['time_total_ms'] = (time.time() - tTotal) * 1000

        return {
            'nodes': combined,
            'stats': stats
        }