#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
선택 모듈 - 3ds Max용 객체 선택 관련 기능 제공
원본 MAXScript의 select.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .bone import Bone


class Select:
    """
    객체 선택 관련 기능을 제공하는 클래스.
    MAXScript의 _Select 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, boneService=None):
        """
        클래스 초기화
        
        Args:
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
            boneService: Bone 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name) # Pass the potentially newly created nameService
    
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