#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 선택(Select) 모듈

3ds Max에서 객체 선택과 관련된 다양한 기능을 제공하는 모듈입니다.

## 주요 기능
- 선택 필터 설정 및 관리
- 객체 유형별 필터링
- 계층 구조에 따른 객체 정렬
- 자식 객체 선택 및 관리
- 인덱스 기반 객체 정렬

## 구현 정보
- 원본 MAXScript의 select.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .bone import Bone


class Select:
    """
    # Select 클래스
    
    3ds Max에서 객체 선택 및 필터링 기능을 제공하는 클래스입니다.
    
    ## 주요 기능
    - 선택 필터 설정 (뼈대, 헬퍼, 포인트, 스플라인, 메시 등)
    - 선택된 객체의 특정 유형 필터링
    - 계층 구조에 따른 객체 정렬
    - 객체 이름의 인덱스에 따른 정렬
    - 독립/계층 객체 구분 및 처리
    
    ## 구현 정보
    - MAXScript의 _Select 구조체를 Python 클래스로 재구현
    - pymxs 모듈을 통해 3ds Max의 선택 기능 제어
    
    ## 사용 예시
    ```python
    # Select 객체 생성
    select = Select()
    
    # 뼈대 객체만 선택하도록 필터 설정
    select.set_selectionSet_to_bone()
    
    # 현재 선택 항목에서 헬퍼 객체만 필터링
    select.filter_helper()
    
    # 계층 구조에 따라 객체 정렬
    sorted_objs = select.sort_by_hierachy(rt.selection)
    ```
    """
    
    def __init__(self, nameService=None, boneService=None):
        """
        Select 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): 뼈대 서비스 (기본값: None, 새로 생성)
        
        ## 참고
        - 서비스 인스턴스가 제공되지 않으면 자동으로 생성됩니다.
        - Bone 서비스는 Name 서비스에 의존성이 있습니다.
        """
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name) # Pass the potentially newly created nameService
    
    def set_selectionSet_to_all(self):
        """
        모든 유형의 객체를 선택하도록 필터를 설정합니다.
        
        ## 동작 방식
        SetSelectFilter(1)을 호출하여 모든 객체 유형을 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(1)
    
    def set_selectionSet_to_bone(self):
        """
        뼈대 객체만 선택하도록 필터를 설정합니다.
        
        ## 동작 방식
        SetSelectFilter(8)을 호출하여 뼈대 객체만 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(8)
    
    def reset_selectionSet(self):
        """
        선택 필터를 기본값(모든 객체)으로 재설정합니다.
        
        ## 동작 방식
        SetSelectFilter(1)을 호출하여 모든 객체 유형을 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(1)
    
    def set_selectionSet_to_helper(self):
        """
        헬퍼 객체만 선택하도록 필터를 설정합니다.
        
        ## 동작 방식
        SetSelectFilter(6)을 호출하여 헬퍼 객체만 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(6)
    
    def set_selectionSet_to_point(self):
        """
        포인트 객체만 선택하도록 필터를 설정합니다.
        
        ## 동작 방식
        SetSelectFilter(10)을 호출하여 포인트 객체만 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(10)
    
    def set_selectionSet_to_spline(self):
        """
        스플라인 객체만 선택하도록 필터를 설정합니다.
        
        ## 동작 방식
        SetSelectFilter(3)을 호출하여 스플라인 객체만 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(3)
    
    def set_selectionSet_to_mesh(self):
        """
        메시 객체만 선택하도록 필터를 설정합니다.
        
        ## 동작 방식
        SetSelectFilter(2)을 호출하여 메시 객체만 선택 가능하도록 설정합니다.
        """
        rt.SetSelectFilter(2)
    
    def filter_bip(self):
        """
        현재 선택 항목에서 Biped 객체만 필터링하여 선택합니다.
        
        ## 동작 방식
        1. 현재 선택된 객체 배열 가져오기
        2. rt.classOf 함수를 사용하여 Biped_Object 타입 객체만 필터링
        3. 선택 초기화 후 필터링된 객체만 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.Biped_Object]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_bone(self):
        """
        현재 선택 항목에서 뼈대 객체만 필터링하여 선택합니다.
        
        ## 동작 방식
        1. 현재 선택된 객체 배열 가져오기
        2. rt.classOf 함수를 사용하여 BoneGeometry 타입 객체만 필터링
        3. 선택 초기화 후 필터링된 객체만 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.BoneGeometry]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_helper(self):
        """
        현재 선택 항목에서 헬퍼 객체만 필터링하여 선택합니다.
        
        ## 동작 방식
        1. 현재 선택된 객체 배열 가져오기
        2. rt.classOf 함수를 사용하여 Point 또는 IK_Chain_Object 타입 객체만 필터링
        3. 선택 초기화 후 필터링된 객체만 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.Point or rt.classOf(item) == rt.IK_Chain_Object]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_expTm(self):
        """
        현재 선택 항목에서 ExposeTm 객체만 필터링하여 선택합니다.
        
        ## 동작 방식
        1. 현재 선택된 객체 배열 가져오기
        2. rt.classOf 함수를 사용하여 ExposeTm 타입 객체만 필터링
        3. 선택 초기화 후 필터링된 객체만 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.classOf(item) == rt.ExposeTm]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def filter_spline(self):
        """
        현재 선택 항목에서 스플라인 객체만 필터링하여 선택합니다.
        
        ## 동작 방식
        1. 현재 선택된 객체 배열 가져오기
        2. rt.superClassOf 함수를 사용하여 shape 타입 객체만 필터링
        3. 선택 초기화 후 필터링된 객체만 선택
        """
        sel_array = rt.getCurrentSelection()
        if len(sel_array) > 0:
            filtered_sel = [item for item in sel_array if rt.superClassOf(item) == rt.shape]
            rt.clearSelection()
            rt.select(filtered_sel)
    
    def select_children(self, inObj, includeSelf=False):
        """
        객체의 모든 자식을 선택합니다.
        
        ## Parameters
        - inObj (MaxObject): 자식을 선택할 부모 객체
        - includeSelf (bool): 부모 객체도 함께 선택할지 여부 (기본값: False)
            
        ## Returns
        - list: 선택된 자식 객체 리스트
        
        ## 동작 방식
        bone.select_every_children 메서드를 사용하여 모든 자식 객체를 선택합니다.
        """
        children = self.bone.select_every_children(inObj=inObj, includeSelf=includeSelf)
        
        return children
    
    def distinguish_hierachy_objects(self, inArray):
        """
        계층 구조가 있는 객체와 없는 객체를 구분합니다.
        
        ## Parameters
        - inArray (list): 구분할 객체 배열
            
        ## Returns
        - list: [독립 객체 배열, 계층 구조 객체 배열] 형태의 이중 배열
        
        ## 동작 방식
        1. 반환 배열 초기화 ([독립 객체 배열, 계층 구조 객체 배열])
        2. 각 객체의 부모와 자식 여부를 확인
        3. 부모와 자식이 모두 없으면 독립 객체(인덱스 0), 아니면 계층 객체(인덱스 1)로 분류
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
        계층 구조가 없는 독립 객체만 반환합니다.
        
        ## Parameters
        - inArray (list): 필터링할 객체 배열
            
        ## Returns
        - list: 독립적인 객체 배열
        
        ## 동작 방식
        distinguish_hierachy_objects 메서드의 결과에서 첫 번째 배열(독립 객체)을 반환합니다.
        """
        return self.distinguish_hierachy_objects(inArray)[0]
    
    def get_linked_objects(self, inArray):
        """
        계층 구조가 있는 객체만 반환합니다.
        
        ## Parameters
        - inArray (list): 필터링할 객체 배열
            
        ## Returns
        - list: 계층 구조를 가진 객체 배열
        
        ## 동작 방식
        distinguish_hierachy_objects 메서드의 결과에서 두 번째 배열(계층 객체)을 반환합니다.
        """
        return self.distinguish_hierachy_objects(inArray)[1]
    
    def sort_by_hierachy(self, inArray):
        """
        객체를 계층 구조에 따라 정렬합니다.
        
        ## Parameters
        - inArray (list): 정렬할 객체 배열
            
        ## Returns
        - list: 계층 순서대로 정렬된 객체 배열
        
        ## 동작 방식
        bone.sort_bones_as_hierarchy 메서드를 사용하여 객체를 계층 구조에 따라 정렬합니다.
        """
        return self.bone.sort_bones_as_hierarchy(inArray)
    
    def sort_by_index(self, inArray):
        """
        객체를 이름에 포함된 인덱스 번호에 따라 정렬합니다.
        
        ## Parameters
        - inArray (list): 정렬할 객체 배열
            
        ## Returns
        - list: 인덱스 순서대로 정렬된 객체 배열
        
        ## 동작 방식
        1. 객체의 이름 배열 추출
        2. name.sort_by_index 메서드로 이름 배열을 인덱스 기준으로 정렬
        3. 정렬된 이름 순서에 따라 원래 객체 배열 재구성
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
        객체를 적절한 방법으로 정렬합니다.
        
        독립 객체와 계층 객체를 분류하고, 각각 적합한 방식으로 정렬한 후 
        인덱스 값을 기준으로 두 그룹의 순서를 결정합니다.
        
        ## Parameters
        - inArray (list): 정렬할 객체 배열
            
        ## Returns
        - list: 정렬된 객체 배열
        
        ## 동작 방식
        1. 독립 객체와 계층 객체 분류
        2. 각각 인덱스 및 계층 기준으로 정렬
        3. 두 그룹의 첫 객체 인덱스를 비교하여 합치는 순서 결정
        4. 인덱스가 낮은 그룹을 먼저 배치
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