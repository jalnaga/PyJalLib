#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper 모듈 - 헬퍼 객체 생성 및 관리 기능
원본 MAXScript의 helper.ms에서 변환됨
"""

from pymxs import runtime as rt
from .name import Name # Import Name service

class Helper:
    """
    헬퍼 객체 관련 기능을 위한 클래스
    MAXScript의 _Helper 구조체를 Python 클래스로 변환
    
    pymxs 모듈을 통해 3ds Max의 기능을 직접 접근합니다.
    """
    
    def __init__(self, nameService=None):
        """
        초기화 함수
        
        Args:
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
    
    def create_point(self, inName, size=2, boxToggle=False, crossToggle=True, pointColor=(14, 255, 2), pos=(0, 0, 0)):
        """
        포인트 헬퍼 생성
        
        Args:
            inName: 헬퍼 이름
            size: 헬퍼 크기
            boxToggle: 박스 표시 여부
            crossToggle: 십자 표시 여부
            pointColor: 색상
            pos: 위치
            
        Returns:
            생성된 포인트 헬퍼
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
        빈 포인트 헬퍼 생성
        
        Args:
            inName: 헬퍼 이름
            
        Returns:
            생성된 빈 포인트 헬퍼
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
        헬퍼 타입 패턴에 따라 Type namePart 값 찾기
        
        Args:
            helperType: 헬퍼 타입 문자열 ("Dummy", "IK", "Target", "Parent", "ExposeTm")
            
        Returns:
            찾은 Type namePart 값
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
        객체로부터 헬퍼 이름 생성
        
        Args:
            inObj: 원본 객체
            make_two: 두 개의 이름 생성 여부
            is_exp: ExposeTM 타입 여부
            
        Returns:
            생성된 헬퍼 이름 배열 [포인트 이름, 타겟 이름]
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
        객체로부터 헬퍼 형태 생성
        
        Args:
            inObj: 원본 객체
            
        Returns:
            [헬퍼 크기, 십자 표시 여부, 박스 표시 여부]
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
        헬퍼 생성
        
        Args:
            make_two: 두 개의 헬퍼 생성 여부
            
        Returns:
            생성된 헬퍼 배열
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
        부모 헬퍼 생성
        """
        # 선택된 객체가 있는 경우에만 처리
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
    
    def create_exp_tm(self):
        """
        ExposeTM 헬퍼 생성
        
        Returns:
            생성된 ExposeTM 헬퍼 배열
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
        헬퍼 크기 설정
        
        Args:
            inObj: 대상 객체
            inNewSize: 새 크기
            
        Returns:
            설정된 객체
        """
        # 헬퍼 클래스 타입인 경우에만 처리
        if rt.superClassOf(inObj) == rt.Helper:
            rt.setProperty(inObj, "size", inNewSize)
            return inObj
        return None
    
    def add_size(self, inObj, inAddSize):
        """
        헬퍼 크기 증가
        
        Args:
            inObj: 대상 객체
            inAddSize: 증가할 크기
            
        Returns:
            설정된 객체
        """
        # 헬퍼 클래스 타입인 경우에만 처리
        if rt.superClassOf(inObj) == rt.Helper:
            inObj.size += inAddSize
            return inObj
        return None
    
    def set_shape_to_center(self, inObj):
        """
        형태를 센터 마커로 설정
        
        Args:
            inObj: 대상 객체
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.centermarker = True
            inObj.box = True
            inObj.axistripod = False
            inObj.cross = False
    
    def set_shape_to_axis(self, inObj):
        """
        형태를 축 마커로 설정
        
        Args:
            inObj: 대상 객체
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.axistripod = True
            inObj.centermarker = False
            inObj.box = False
            inObj.cross = False
    
    def set_shape_to_cross(self, inObj):
        """
        형태를 십자 마커로 설정
        
        Args:
            inObj: 대상 객체
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.cross = True
            inObj.box = False
            inObj.centermarker = False
            inObj.axistripod = False
    
    def set_shape_to_box(self, inObj):
        """
        형태를 박스 마커로 설정
        
        Args:
            inObj: 대상 객체
        """
        # Point 또는 ExposeTm 클래스인 경우에만 처리
        if rt.classOf(inObj) == rt.ExposeTm or rt.classOf(inObj) == rt.Point:
            inObj.box = True
            inObj.centermarker = False
            inObj.axistripod = False
            inObj.cross = False
