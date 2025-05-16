#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# Helper 모듈

3ds Max에서 헬퍼 객체를 생성하고 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 포인트 및 ExposeTM 헬퍼 객체 생성
- 헬퍼 형태 및 속성 설정
- 기존 객체 기반 헬퍼 자동 생성
- 헬퍼 크기 및 표시 속성 관리

## 구현 정보
- 원본 MAXScript의 helper.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt
from .name import Name # Import Name service

class Helper:
    """
    # Helper 클래스
    
    3ds Max에서 헬퍼 객체를 생성하고 관리하는 기능을 제공합니다.
    
    ## 주요 기능
    - 다양한 헬퍼 객체 생성 (Point, ExposeTM)
    - 선택된 객체 기반 헬퍼 자동 생성
    - 헬퍼 형태 및 시각적 속성 설정
    - 헬퍼 이름 자동 생성 및 규칙 적용
    
    ## 구현 정보
    - MAXScript의 _Helper 구조체를 Python 클래스로 재구현
    - Name 서비스와 연동하여 명명 규칙 적용
    - pymxs 모듈을 통해 3ds Max API 직접 접근
    
    ## 사용 예시
    ```python
    # 헬퍼 객체 생성
    helper = Helper()
    
    # 커스텀 포인트 헬퍼 생성
    point = helper.create_point("ControlPoint", size=3, boxToggle=True)
    
    # 선택된 객체 기반 헬퍼 생성
    helpers = helper.create_helper()
    ```
    """
    
    def __init__(self, nameService=None):
        """
        Helper 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        """
        self.name = nameService if nameService else Name()
    
    def create_point(self, inName, size=2, boxToggle=False, crossToggle=True, pointColor=(14, 255, 2), pos=(0, 0, 0)):
        """
        포인트 헬퍼 객체를 생성합니다.
        
        ## Parameters
        - inName (str): 헬퍼의 이름
        - size (float): 헬퍼의 크기 (기본값: 2)
        - boxToggle (bool): 박스 표시 여부 (기본값: False)
        - crossToggle (bool): 십자 표시 여부 (기본값: True)
        - pointColor (tuple): RGB 색상값 (기본값: (14, 255, 2), 밝은 녹색)
        - pos (tuple): 생성 위치 좌표 (기본값: (0, 0, 0))
            
        ## Returns
        - Point: 생성된 포인트 헬퍼 객체
        
        ## 동작 방식
        1. rt.Point 객체 생성
        2. 시각적 속성 설정 (크기, 박스, 십자, 색상 등)
        3. 이름 및 위치 설정
        4. 추가 속성 설정 (centermarker, axistripod 비활성화)
        """
        # Point 객체 생성
        returnPoint = rt.Point()
        rt.setProperty(returnPoint, "size", size)
        rt.setProperty(returnPoint, "box", boxToggle)
        rt.setProperty(returnPoint, "cross", crossToggle)
        
        # 색상 설정 (MAXScript의 color를 Point3로 변환)
        rt.setProperty(returnPoint, "wirecolor", rt.Color(pointColor[0], pointColor[1], pointColor[2]))
        
        # 이름과 위치 설정
        rt.setProperty(returnPoint, "position", rt.Point3(pos[0], pos[1], pos[2]))
        rt.setProperty(returnPoint, "name", inName)
        
        # 추가 속성 설정
        returnPoint.centermarker = False
        returnPoint.axistripod = False
        rt.setProperty(returnPoint, "centermarker", False)
        rt.setProperty(returnPoint, "axistripod", False)
        
        return returnPoint
    
    def create_empty_point(self, inName):
        """
        시각적으로 보이지 않는 빈 포인트 헬퍼를 생성합니다.
        
        ## Parameters
        - inName (str): 헬퍼의 이름
            
        ## Returns
        - Point: 생성된 빈 포인트 헬퍼 객체
        
        ## 동작 방식
        1. 크기 0, 십자선 없는 포인트 생성
        2. 프리즈(변환 불가) 상태로 설정
        """
        # 빈 포인트 생성 (size:0, crossToggle:off)
        returnPoint = self.create_point(inName, size=0, crossToggle=False)
        rt.setProperty(returnPoint, "centermarker", False)
        rt.setProperty(returnPoint, "axistripod", False)
        
        # MAXScript의 freeze 기능 구현
        rt.freeze(returnPoint)
        
        return returnPoint
    
    def get_name_by_type(self, helperType):
        """
        헬퍼 타입에 따른 Type namePart 값을 찾습니다.
        
        ## Parameters
        - helperType (str): 헬퍼 타입 문자열 ("Dummy", "IK", "Target", "Parent", "ExposeTm")
            
        ## Returns
        - str: 찾은 Type namePart 값
        
        ## 동작 방식
        1. 헬퍼 타입 패턴 정의 (Dummy, IK, Target 등)
        2. 지정된 타입과 일치하는 패턴을 namePart 값에서 검색
        3. 일치하는 값이 없으면 기본값 반환
        """
        typePart = self.name.get_name_part("Type")
        predefinedValues = typePart.get_predefined_values()
        firstTypeValue = typePart.get_value_by_min_weight()
        
        
        # 헬퍼 타입 패턴 정의
        helperNamePatterns = {
            "Dummy": ["dum", "Dum", "Dummy", "Helper", "Hpr", "Dmy"],
            "IK": ["ik", "IK", "Ik"],
            "Target": ["Tgt", "Target", "TG", "Tg", "T"],
            "Parent": ["Prn", "PRN", "Parent", "P"],
            "ExposeTm": ["Exp", "Etm", "EXP", "ETM"]
        }
        
        # 타입 패턴 가져오기
        patterns = helperNamePatterns.get(helperType, [])
        if not patterns:
            return firstTypeValue
        
        # 패턴과 일치하는 값 찾기
        for value in predefinedValues:
            if value in patterns:
                return value
        
        # 일치하는 값이 없으면 기본값 반환
        return firstTypeValue
    
    def gen_helper_name_from_obj(self, inObj, make_two=False, is_exp=False):
        """
        객체로부터 헬퍼 이름을 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 이름을 생성할 원본 객체
        - make_two (bool): 두 개의 이름 생성 여부 (기본값: False)
        - is_exp (bool): ExposeTM 타입으로 생성할지 여부 (기본값: False)
            
        ## Returns
        - list: 생성된 헬퍼 이름 배열 [포인트 이름, 타겟 이름]
            타겟 이름은 make_two가 True인 경우에만 생성됨
        
        ## 동작 방식
        1. 적절한 타입 값 선택 (Dummy 또는 ExposeTm)
        2. 원본 객체 이름의 Type 부분 교체 또는 인덱스 증가
        3. make_two가 True이면 타겟 이름도 생성
        """
        pointName = ""
        targetName = ""
        
        # 타입 설정
        typeName = self.get_name_by_type("Dummy")
        if is_exp:
            typeName = self.get_name_by_type("ExposeTm")
        
        # 이름 생성
        tempName = self.name.replace_name_part("Type", inObj.name, typeName)
        if self.name.get_name("Type", inObj.name) == typeName:
            tempName = self.name.increase_index(tempName, 1)
        
        pointName = tempName
        
        # 타겟 이름 생성
        if make_two:
            targetName = self.name.add_suffix_to_real_name(tempName, self.get_name_by_type("Target"))
        
        return [pointName, targetName]
    
    def gen_helper_shape_from_obj(self, inObj):
        """
        객체 정보를 기반으로 헬퍼 형태 설정값을 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 형태 정보를 가져올 원본 객체
            
        ## Returns
        - list: [헬퍼 크기, 십자 표시 여부, 박스 표시 여부]
        
        ## 동작 방식
        1. 객체 타입에 따라 적절한 크기와 형태 계산
        2. BoneGeometry 타입은 width/height 중 큰 값 사용
        3. Point/ExposeTm 타입은 기존 설정 + 추가 크기 사용
        """
        helperSize = 2.0
        crossToggle = False
        boxToggle = True
        
        # BoneGeometry 타입 처리
        if rt.classOf(inObj) == rt.BoneGeometry:
            # amax 함수를 사용하여 width, height 중 큰 값 선택
            helperSize = max(inObj.width, inObj.height)
        
        # Point나 ExposeTm 타입 처리
        if rt.classOf(inObj) == rt.Point or rt.classOf(inObj) == rt.ExposeTm:
            helperSize = inObj.size + 0.5
            if inObj.cross:
                crossToggle = False
                boxToggle = True
            if inObj.box:
                crossToggle = True
                boxToggle = False
        
        return [helperSize, crossToggle, boxToggle]
    
    def create_helper(self, make_two=False):
        """
        선택된 객체를 기반으로 헬퍼 객체를 생성합니다.
        
        ## Parameters
        - make_two (bool): 두 개의 헬퍼 생성 여부 (기본값: False)
            
        ## Returns
        - list: 생성된 헬퍼 객체 배열
        
        ## 동작 방식
        1. 선택된 객체 각각에 대해 형태와 이름 결정
        2. make_two=True이면 포인트와 타겟 헬퍼 쌍 생성
        3. make_two=False이면 단일 헬퍼 생성
        4. 선택된 객체가 없으면 기본 포인트 헬퍼 생성
        """
        createdHelperArray = []
        
        # 선택된 객체가 있는 경우
        if rt.selection.count > 0:
            selArray = rt.getCurrentSelection()
            
            for item in selArray:
                # 헬퍼 크기 및 형태 설정
                helperShapeArray = self.gen_helper_shape_from_obj(item)
                helperSize = helperShapeArray[0]
                crossToggle = helperShapeArray[1]
                boxToggle = helperShapeArray[2]
                
                # 헬퍼 이름 설정
                helperNameArray = self.gen_helper_name_from_obj(item, make_two=make_two)
                pointName = helperNameArray[0]
                targetName = helperNameArray[1]
                
                # 두 개의 헬퍼 생성 (포인트와 타겟)
                if make_two:
                    # 타겟 포인트 생성
                    targetPoint = self.create_point(
                        targetName, 
                        size=helperSize, 
                        boxToggle=False, 
                        crossToggle=True, 
                        pointColor=(14, 255, 2), 
                        pos=(0, 0, 0)
                    )
                    rt.setProperty(targetPoint, "transform", rt.getProperty(item, "transform"))
                    
                    # 메인 포인트 생성
                    genPoint = self.create_point(
                        pointName, 
                        size=helperSize, 
                        boxToggle=True, 
                        crossToggle=False, 
                        pointColor=(14, 255, 2), 
                        pos=(0, 0, 0)
                    )
                    rt.setProperty(genPoint, "transform", rt.getProperty(item, "transform"))
                    
                    # 배열에 추가
                    createdHelperArray.append(targetPoint)
                    createdHelperArray.append(genPoint)
                else:
                    # 단일 포인트 생성
                    genPoint = self.create_point(
                        pointName, 
                        size=helperSize, 
                        boxToggle=boxToggle, 
                        crossToggle=crossToggle, 
                        pointColor=(14, 255, 2), 
                        pos=(0, 0, 0)
                    )
                    rt.setProperty(genPoint, "transform", rt.getProperty(item, "transform"))
                    createdHelperArray.append(genPoint)
        else:
            # 선택된 객체가 없는 경우 기본 포인트 생성
            genPoint = rt.Point(wirecolor=rt.Color(14, 255, 2))
            createdHelperArray.append(genPoint)
        
        # 생성된 헬퍼들 선택
        rt.select(createdHelperArray)
        return createdHelperArray
    
    def create_parent_helper(self):
        """
        선택된 객체의 부모 헬퍼를 생성합니다.
        
        ## Returns
        - list: 생성된 부모 헬퍼 객체 배열
        
        ## 동작 방식
        1. 선택된 객체 각각에 대해 부모 헬퍼 생성
        2. 헬퍼는 원본 객체와 동일한 위치와 방향에 생성
        3. 헬퍼가 원본 객체의 부모 객체가 되도록 계층 구조 설정
        4. 헬퍼 이름은 Parent 타입으로 설정
        """
        # 선택된 객체가 있는 경우에만 처리
        returnHelpers = []
        if rt.selection.count > 0:
            selArray = rt.getCurrentSelection()
            
            for item in selArray:
                # 헬퍼 크기 및 형태 설정
                helperShapeArray = self.gen_helper_shape_from_obj(item)
                helperSize = helperShapeArray[0]
                crossToggle = helperShapeArray[1]
                boxToggle = helperShapeArray[2]
                
                # 헬퍼 이름 설정
                helperNameArray = self.gen_helper_name_from_obj(item)
                pointName = helperNameArray[0]
                targetName = helperNameArray[1]
                
                # 부모 헬퍼 생성
                genPoint = self.create_point(
                    pointName,
                    size=helperSize,
                    boxToggle=True,
                    crossToggle=False,
                    pointColor=(14, 255, 2),
                    pos=(0, 0, 0)
                )
                
                # 트랜스폼 및 부모 설정
                rt.setProperty(genPoint, "transform", rt.getProperty(item, "transform"))
                rt.setProperty(genPoint, "parent", rt.getProperty(item, "parent"))
                rt.setProperty(item, "parent", genPoint)
                
                # 부모 헬퍼로 이름 변경
                finalName = self.name.replace_name_part("Type", genPoint.name, self.get_name_by_type("Parent"))
                rt.setProperty(genPoint, "name", finalName)
                
                returnHelpers.append(genPoint)
            
        return returnHelpers
        
    
    def create_exp_tm(self):
        """
        선택된 객체를 기반으로 ExposeTM 헬퍼를 생성합니다.
        
        ## Returns
        - list: 생성된 ExposeTM 헬퍼 객체 배열
        
        ## 동작 방식
        1. 선택된 객체 각각에 대해 ExposeTM 헬퍼 생성
        2. 헬퍼 이름과 형태는 원본 객체를 기반으로 결정
        3. 선택된 객체가 없으면 기본 ExposeTM 헬퍼 생성
        """
        createdHelperArray = []
        
        # 선택된 객체가 있는 경우
        if rt.selection.count > 0:
            selArray = rt.getCurrentSelection()
            
            for item in selArray:
                # 헬퍼 크기 및 형태 설정
                helperShapeArray = self.gen_helper_shape_from_obj(item)
                helperSize = helperShapeArray[0]
                crossToggle = helperShapeArray[1]
                boxToggle = helperShapeArray[2]
                
                # 헬퍼 이름 설정 (ExposeTM 용)
                helperNameArray = self.gen_helper_name_from_obj(item, make_two=False, is_exp=True)
                pointName = helperNameArray[0]
                
                # ExposeTM 객체 생성
                genPoint = rt.ExposeTM(
                    name=pointName,
                    size=helperSize,
                    box=boxToggle,
                    cross=crossToggle,
                    wirecolor=rt.Color(14, 255, 2),
                    pos=rt.Point3(0, 0, 0)
                )
                rt.setProperty(genPoint, "transform", rt.getProperty(item, "transform"))
                createdHelperArray.append(genPoint)
        else:
            # 선택된 객체가 없는 경우 기본 ExposeTM 생성
            genPoint = rt.ExposeTM(wirecolor=rt.Color(14, 255, 2))
            createdHelperArray.append(genPoint)
        
        # 생성된 헬퍼 객체들 선택
        rt.select(createdHelperArray)
        return createdHelperArray
    
    def set_size(self, inObj, inNewSize):
        """
        헬퍼 객체의 크기를 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 크기를 설정할 헬퍼 객체
        - inNewSize (float): 설정할 새 크기
            
        ## Returns
        - MaxObject: 크기가 설정된 헬퍼 객체 또는 None (헬퍼가 아닌 경우)
        """
        # 헬퍼 클래스 타입인 경우에만 처리
        if rt.superClassOf(inObj) == rt.Helper:
            rt.setProperty(inObj, "size", inNewSize)
            return inObj
        return None
    
    def add_size(self, inObj, inAddSize):
        """
        헬퍼 객체의 크기를 증가시킵니다.
        
        ## Parameters
        - inObj (MaxObject): 크기를 증가시킬 헬퍼 객체
        - inAddSize (float): 증가시킬 크기 값
            
        ## Returns
        - MaxObject: 크기가 증가된 헬퍼 객체 또는 None (헬퍼가 아닌 경우)
        """
        # 헬퍼 클래스 타입인 경우에만 처리
        if rt.superClassOf(inObj) == rt.Helper:
            inObj.size += inAddSize
            return inObj
        return None
    
    def set_shape_to_center(self, inObj):
        """
        헬퍼 객체의 형태를 센터 마커로 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 형태를 설정할 헬퍼 객체
        
        ## 동작 방식
        Point 또는 ExposeTm 객체에 대해:
        - centermarker: True
        - box: True
        - axistripod: False
        - cross: False
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.centermarker = True
            inObj.box = True
            inObj.axistripod = False
            inObj.cross = False
    
    def set_shape_to_axis(self, inObj):
        """
        헬퍼 객체의 형태를 축 표시 형태로 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 형태를 설정할 헬퍼 객체
        
        ## 동작 방식
        Point 또는 ExposeTm 객체에 대해:
        - axistripod: True
        - centermarker: False
        - box: False
        - cross: False
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.axistripod = True
            inObj.centermarker = False
            inObj.box = False
            inObj.cross = False
    
    def set_shape_to_cross(self, inObj):
        """
        헬퍼 객체의 형태를 십자 표시 형태로 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 형태를 설정할 헬퍼 객체
        
        ## 동작 방식
        Point 또는 ExposeTm 객체에 대해:
        - cross: True
        - box: False
        - centermarker: False
        - axistripod: False
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.cross = True
            inObj.box = False
            inObj.centermarker = False
            inObj.axistripod = False
    
    def set_shape_to_box(self, inObj):
        """
        헬퍼 객체의 형태를 박스 표시 형태로 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 형태를 설정할 헬퍼 객체
        
        ## 동작 방식
        Point 또는 ExposeTm 객체에 대해:
        - box: True
        - centermarker: False
        - axistripod: False
        - cross: False
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.box = True
            inObj.centermarker = False
            inObj.axistripod = False
            inObj.cross = False
            
    def get_shape(self, inObj):
        """
        헬퍼 객체의 시각적 형태 속성을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 형태 정보를 가져올 헬퍼 객체
            
        ## Returns
        - dict: 헬퍼의 형태 속성 딕셔너리
            - "size" (float): 크기
            - "centermarker" (bool): 센터 마커 활성화 여부
            - "axistripod" (bool): 축 표시 활성화 여부
            - "cross" (bool): 십자 표시 활성화 여부
            - "box" (bool): 박스 표시 활성화 여부
        
        ## 동작 방식
        - ExposeTm 또는 Point 객체인 경우 실제 속성값 반환
        - 그 외의 경우 기본값 반환
        """
        returnDict = {
            "size": 2.0,
            "centermarker": False,
            "axistripod": False,
            "cross": True,
            "box": False
        }
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            returnDict["size"] = inObj.size
            returnDict["centermarker"] = inObj.centermarker
            returnDict["axistripod"] = inObj.axistripod
            returnDict["cross"] = inObj.cross
            returnDict["box"] = inObj.box
        
        return returnDict
    
    def set_shape(self, inObj, inShapeDict):
        """
        헬퍼 객체의 시각적 형태 속성을 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 형태를 설정할 헬퍼 객체
        - inShapeDict (dict): 설정할 형태 속성 딕셔너리
            - "size" (float): 크기
            - "centermarker" (bool): 센터 마커 활성화 여부
            - "axistripod" (bool): 축 표시 활성화 여부
            - "cross" (bool): 십자 표시 활성화 여부
            - "box" (bool): 박스 표시 활성화 여부
            
        ## Returns
        - MaxObject: 형태가 설정된 헬퍼 객체 또는 None (호환되지 않는 객체인 경우)
        
        ## 동작 방식
        ExposeTm 또는 Point 객체인 경우에만 속성 설정
        """
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.size = inShapeDict["size"]
            inObj.centermarker = inShapeDict["centermarker"]
            inObj.axistripod = inShapeDict["axistripod"]
            inObj.cross = inShapeDict["cross"]
            inObj.box = inShapeDict["box"]
            
            return inObj
