#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper 모듈 - 헬퍼 객체 생성 및 관리 기능
원본 MAXScript의 helper.ms에서 변환됨
"""

from pymxs import runtime as rt
from .name import Name # Import Name service

class Helper:
    """3ds Max 포인트·ExposeTm 헬퍼의 생성과 형태, 크기 관리 기능을 제공하는 클래스."""
    
    def __init__(self, nameService=None):
        """Name 서비스를 주입받아 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
        """
        self.name = nameService if nameService else Name()
    
    def create_point(self, inName, size=2, boxToggle=False, crossToggle=True, pointColor=(14, 255, 2), pos=(0, 0, 0)):
        """포인트 헬퍼를 생성한다.

        Args:
            inName (str): 헬퍼 이름
            size (float): 헬퍼 크기
            boxToggle (bool): 박스 표시 여부
            crossToggle (bool): 십자 표시 여부
            pointColor (tuple[int, int, int]): 와이어 색상(RGB)
            pos (tuple[float, float, float]): 생성 위치

        Returns:
            rt.Node: 생성된 포인트 헬퍼
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
        """크기 0의 프리즈된 빈 포인트 헬퍼를 생성한다.

        Args:
            inName (str): 헬퍼 이름

        Returns:
            rt.Node: 생성된 빈 포인트 헬퍼
        """
        # 빈 포인트 생성 (size:0, crossToggle:off)
        returnPoint = self.create_point(inName, size=0, crossToggle=False)
        rt.setProperty(returnPoint, "centermarker", False)
        rt.setProperty(returnPoint, "axistripod", False)
        
        # MAXScript의 freeze 기능 구현
        rt.freeze(returnPoint)
        
        return returnPoint
    
    def get_name_by_type(self, helperType):
        """헬퍼 타입 설명에 해당하는 Type namePart 값을 찾는다.

        Args:
            helperType (str): 헬퍼 타입 문자열 ("Dummy", "IK", "Target", "Parent", "ExposeTm")

        Returns:
            str: 찾은 Type namePart 값. 없으면 최소 가중치의 기본 Type 값
        """
        typePart = self.name.get_name_part("Type")
        firstTypeValue = typePart.get_value_by_min_weight()
        
        helperTypeName = self.name.get_name_part_value_by_description("Type", helperType)
        if helperTypeName != "":
            return helperTypeName
        
        return firstTypeValue
    
    def gen_helper_name_from_obj(self, inObj, make_two=False, is_exp=False):
        """객체 이름으로부터 헬퍼 이름을 생성한다.

        Args:
            inObj (rt.Node): 원본 객체
            make_two (bool): True면 타겟 이름도 함께 생성한다.
            is_exp (bool): True면 ExposeTm 타입 이름을 사용한다.

        Returns:
            list[str]: [포인트 이름, 타겟 이름]. make_two가 False면 타겟 이름은 빈 문자열
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
            targetSuffix = self.name.get_filtering_char(tempName) + self.get_name_by_type("Target")
            targetName = self.name.add_suffix_to_real_name(tempName, targetSuffix)
        
        return [pointName, targetName]
    
    def gen_helper_shape_from_obj(self, inObj):
        """객체 타입에 따라 헬퍼 형태 값을 생성한다.

        Args:
            inObj (rt.Node): 원본 객체

        Returns:
            list: [헬퍼 크기(float), 십자 표시 여부(bool), 박스 표시 여부(bool)]
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
        """선택된 객체들의 트랜스폼 위치에 포인트 헬퍼를 생성한다.

        선택이 없으면 기본 포인트 하나를 생성한다.

        Args:
            make_two (bool): True면 객체마다 타겟과 메인 두 개의 헬퍼를 생성한다.

        Returns:
            list[rt.Node]: 생성된 헬퍼 배열
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
        """선택된 객체마다 부모 헬퍼를 생성하여 계층 사이에 삽입한다.

        Returns:
            list[rt.Node]: 생성된 부모 헬퍼 배열. 선택이 없으면 빈 리스트
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
        """선택된 객체들의 트랜스폼 위치에 ExposeTm 헬퍼를 생성한다.

        선택이 없으면 기본 ExposeTm 하나를 생성한다.

        Returns:
            list[rt.Node]: 생성된 ExposeTm 헬퍼 배열
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
        """헬퍼의 크기를 설정한다.

        Args:
            inObj (rt.Node): 대상 헬퍼 객체
            inNewSize (float): 새 크기

        Returns:
            rt.Node | None: 크기가 설정된 객체. 헬퍼가 아니면 None
        """
        # 헬퍼 클래스 타입인 경우에만 처리
        if rt.superClassOf(inObj) == rt.Helper:
            rt.setProperty(inObj, "size", inNewSize)
            return inObj
        return None
    
    def add_size(self, inObj, inAddSize):
        """헬퍼의 크기를 증가시킨다.

        Args:
            inObj (rt.Node): 대상 헬퍼 객체
            inAddSize (float): 증가시킬 크기

        Returns:
            rt.Node | None: 크기가 변경된 객체. 헬퍼가 아니면 None
        """
        # 헬퍼 클래스 타입인 경우에만 처리
        if rt.superClassOf(inObj) == rt.Helper:
            inObj.size += inAddSize
            return inObj
        return None
    
    def set_shape_to_center(self, inObj):
        """헬퍼 형태를 센터 마커와 박스 표시로 설정한다.

        Args:
            inObj (rt.Node): 대상 헬퍼 객체(Point 또는 ExposeTm)
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.centermarker = True
            inObj.box = True
            inObj.axistripod = False
            inObj.cross = False
    
    def set_shape_to_axis(self, inObj):
        """헬퍼 형태를 축 삼각대 표시로 설정한다.

        Args:
            inObj (rt.Node): 대상 헬퍼 객체(Point 또는 ExposeTm)
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.axistripod = True
            inObj.centermarker = False
            inObj.box = False
            inObj.cross = False
    
    def set_shape_to_cross(self, inObj):
        """헬퍼 형태를 십자 표시로 설정한다.

        Args:
            inObj (rt.Node): 대상 헬퍼 객체(Point 또는 ExposeTm)
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.cross = True
            inObj.box = False
            inObj.centermarker = False
            inObj.axistripod = False
    
    def set_shape_to_box(self, inObj):
        """헬퍼 형태를 박스 표시로 설정한다.

        Args:
            inObj (rt.Node): 대상 헬퍼 객체(Point 또는 ExposeTm)
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.box = True
            inObj.centermarker = False
            inObj.axistripod = False
            inObj.cross = False
            
    def get_shape(self, inObj):
        """헬퍼 객체의 시각적 형태 속성을 가져온다.

        Args:
            inObj (rt.Node): 형태 정보를 가져올 헬퍼 객체

        Returns:
            dict: 헬퍼 형태 속성. Point/ExposeTm이 아니면 기본값을 반환한다.
                - size (float): 크기
                - centermarker (bool): 센터 마커 표시 여부
                - axistripod (bool): 축 삼각대 표시 여부
                - cross (bool): 십자 표시 여부
                - box (bool): 박스 표시 여부
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
        """헬퍼 객체의 표시 형태를 딕셔너리 값으로 설정한다.

        Args:
            inObj (rt.Node): 설정을 적용할 헬퍼 객체(Point 또는 ExposeTm)
            inShapeDict (dict): 형태 딕셔너리(size, centermarker, axistripod, cross, box 키)

        Returns:
            rt.Node | None: 형태가 설정된 객체. Point/ExposeTm이 아니면 None
        """
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.size = inShapeDict["size"]
            inObj.centermarker = inShapeDict["centermarker"]
            inObj.axistripod = inShapeDict["axistripod"]
            inObj.cross = inShapeDict["cross"]
            inObj.box = inShapeDict["box"]
            
            return inObj
