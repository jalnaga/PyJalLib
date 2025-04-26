#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
제약(Constraint) 모듈 - 3ds Max용 제약 관련 기능 제공
원본 MAXScript의 constraint.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt
import textwrap

# Import necessary service classes for default initialization
from .name import Name
from .helper import Helper


class Constraint:
    """
    제약(Constraint) 관련 기능을 제공하는 클래스.
    MAXScript의 _Constraint 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, helperService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 관련 서비스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.helper = helperService if helperService else Helper(nameService=self.name) # Pass the potentially newly created nameService
    
    def collapse(self, inObj):
        """
        비 Biped 객체의 트랜스폼 컨트롤러를 기본 컨트롤러로 초기화하고 현재 변환 상태 유지.
        
        Args:
            inObj: 초기화할 대상 객체
            
        Returns:
            None
        """
        if rt.classOf(inObj) != rt.Biped_Object:
            # 현재 변환 상태 백업
            tempTransform = rt.getProperty(inObj, "transform")
            
            # 기본 컨트롤러로 위치, 회전, 스케일 초기화
            rt.setPropertyController(inObj.controller, "Position", rt.Position_XYZ())
            rt.setPropertyController(inObj.controller, "Rotation", rt.Euler_XYZ())
            rt.setPropertyController(inObj.controller, "Scale", rt.Bezier_Scale())
            
            # 백업한 변환 상태 복원
            rt.setProperty(inObj, "transform", tempTransform)
    
    def set_active_last(self, inObj):
        """
        객체의 위치와 회전 컨트롤러 리스트에서 마지막 컨트롤러를 활성화.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            None
        """
        # 위치 컨트롤러가 리스트 형태면 마지막 컨트롤러 활성화
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) == rt.Position_list:
            pos_controller.setActive(pos_controller.count)
            
        # 회전 컨트롤러가 리스트 형태면 마지막 컨트롤러 활성화
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            rot_controller.setActive(rot_controller.count)
    
    def get_pos_list_controller(self, inObj):
        """
        객체의 위치 리스트 컨트롤러를 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            위치 리스트 컨트롤러 (없으면 None)
        """
        returnPosListCtr = None
        
        # 위치 컨트롤러가 리스트 형태인지 확인
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) == rt.Position_list:
            returnPosListCtr = pos_controller
            
        return returnPosListCtr
    
    def assign_pos_list(self, inObj):
        """
        객체에 위치 리스트 컨트롤러를 할당하거나 기존 것을 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            위치 리스트 컨트롤러
        """
        returnPosListCtr = None
        
        # 현재 위치 컨트롤러 확인
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        
        # 리스트 형태가 아니면 새로 생성
        if rt.classOf(pos_controller) != rt.Position_list:
            returnPosListCtr = rt.Position_list()
            rt.setPropertyController(inObj.controller, "Position", returnPosListCtr)
            return returnPosListCtr
            
        # 이미 리스트 형태면 그대로 반환
        if rt.classOf(pos_controller) == rt.Position_list:
            returnPosListCtr = pos_controller
            
        return returnPosListCtr
    
    def get_pos_const(self, inObj):
        """
        객체의 위치 제약 컨트롤러를 찾아 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            위치 제약 컨트롤러 (없으면 None)
        """
        returnConst = None
        
        # 위치 컨트롤러가 리스트 형태인 경우
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) == rt.Position_list:
            lst = pos_controller
            constNum = lst.getCount()
            activeNum = lst.getActive()
            
            # 리스트 내 모든 컨트롤러 검사
            for i in range(constNum):
                sub_controller = lst[i].controller
                if rt.classOf(sub_controller) == rt.Position_Constraint:
                    returnConst = sub_controller
                    # 현재 활성화된 컨트롤러면 즉시 반환
                    if activeNum == i:
                        return returnConst
        
        # 위치 컨트롤러가 직접 Position_Constraint인 경우
        elif rt.classOf(pos_controller) == rt.Position_Constraint:
            returnConst = pos_controller
            
        return returnConst
    
    def assign_pos_const(self, inObj, inTarget, keepInit=False):
        """
        객체에 위치 제약 컨트롤러를 할당하고 지정된 타겟을 추가.
        
        Args:
            inObj: 제약을 적용할 객체
            inTarget: 타겟 객체
            keepInit: 기존 변환 유지 여부 (기본값: False)
            
        Returns:
            위치 제약 컨트롤러
        """
        # 위치 컨트롤러가 리스트 형태가 아니면 변환
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) != rt.Position_list:
            rt.setPropertyController(inObj.controller, "Position", rt.Position_list())
            
        # 기존 위치 제약 컨트롤러 확인
        targetPosConstraint = self.get_pos_const(inObj)
        
        # 위치 제약 컨트롤러가 없으면 새로 생성
        if targetPosConstraint is None:
            targetPosConstraint = rt.Position_Constraint()
            pos_list = self.get_pos_list_controller(inObj)
            rt.setPropertyController(pos_list, "Available", targetPosConstraint)
            pos_list.setActive(pos_list.count)
        
        # 타겟 추가 및 가중치 조정
        targetNum = targetPosConstraint.getNumTargets()
        targetWeight = 100.0 / (targetNum + 1)
        targetPosConstraint.appendTarget(inTarget, targetWeight)
        
        # 기존 타겟이 있으면 가중치 재조정
        if targetNum > 0:
            newWeightScale = 100.0 - targetWeight
            for i in range(1, targetNum + 1):  # Maxscript는 1부터 시작
                newWeight = targetPosConstraint.GetWeight(i) * 0.01 * newWeightScale
                targetPosConstraint.SetWeight(i, newWeight)
                
        # 상대적 모드 설정
        targetPosConstraint.relative = keepInit
        
        return targetPosConstraint
    
    def assign_pos_const_multi(self, inObj, inTargetArray, keepInit=False):
        """
        객체에 여러 타겟을 가진 위치 제약 컨트롤러를 할당.
        
        Args:
            inObj: 제약을 적용할 객체
            inTargetArray: 타겟 객체 배열
            keepInit: 기존 변환 유지 여부 (기본값: False)
            
        Returns:
            None
        """
        for item in inTargetArray:
            self.assign_pos_const(inObj, item, keepInit=keepInit)
    
    def add_target_to_pos_const(self, inObj, inTarget, inWeight):
        """
        기존 위치 제약 컨트롤러에 새 타겟을 추가하고 지정된 가중치 설정.
        
        Args:
            inObj: 제약이 적용된 객체
            inTarget: 추가할 타겟 객체
            inWeight: 적용할 가중치 값
            
        Returns:
            None
        """
        # 위치 제약 컨트롤러에 타겟 추가
        targetPosConst = self.assign_pos_const(inObj, inTarget)
        
        # 마지막 타겟에 특정 가중치 적용
        targetNum = targetPosConst.getNumTargets()
        targetPosConst.SetWeight(targetNum, inWeight)
    
    def assign_pos_xyz(self, inObj):
        """
        객체에 위치 XYZ 컨트롤러를 할당.
        
        Args:
            inObj: 컨트롤러를 할당할 객체
            
        Returns:
            None
        """
        # 위치 컨트롤러가 리스트 형태가 아니면 변환
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) != rt.Position_list:
            rt.setPropertyController(inObj.controller, "Position", rt.Position_list())
            
        # 위치 리스트 컨트롤러 가져오기
        posList = self.assign_pos_list(inObj)
        
        # Position_XYZ 컨트롤러 할당
        rt.setPropertyController(posList, "Available", rt.Position_XYZ())
        posList.setActive(posList.count)
    
    def get_rot_list_controller(self, inObj):
        """
        객체의 회전 리스트 컨트롤러를 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            회전 리스트 컨트롤러 (없으면 None)
        """
        returnRotListCtr = None
        
        # 회전 컨트롤러가 리스트 형태인지 확인
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            returnRotListCtr = rot_controller
            
        return returnRotListCtr
    
    def assign_rot_list(self, inObj):
        """
        객체에 회전 리스트 컨트롤러를 할당하거나 기존 것을 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            회전 리스트 컨트롤러
        """
        returnRotListCtr = None
        
        # 현재 회전 컨트롤러 확인
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        
        # 리스트 형태가 아니면 새로 생성
        if rt.classOf(rot_controller) != rt.Rotation_list:
            returnRotListCtr = rt.Rotation_list()
            rt.setPropertyController(inObj.controller, "Rotation", returnRotListCtr)
            return returnRotListCtr
            
        # 이미 리스트 형태면 그대로 반환
        if rt.classOf(rot_controller) == rt.Rotation_list:
            returnRotListCtr = rot_controller
            
        return returnRotListCtr
    
    def get_rot_const(self, inObj):
        """
        객체의 회전 제약 컨트롤러를 찾아 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            회전 제약 컨트롤러 (없으면 None)
        """
        returnConst = None
        
        # 회전 컨트롤러가 리스트 형태인 경우
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            lst = rot_controller
            constNum = lst.getCount()
            activeNum = lst.getActive()
            
            # 리스트 내 모든 컨트롤러 검사
            for i in range(constNum):  # Maxscript는 1부터 시작
                sub_controller = lst[i].controller
                if rt.classOf(sub_controller) == rt.Orientation_Constraint:
                    returnConst = sub_controller
                    # 현재 활성화된 컨트롤러면 즉시 반환
                    if activeNum == i:
                        return returnConst
        
        # 회전 컨트롤러가 직접 Orientation_Constraint인 경우
        elif rt.classOf(rot_controller) == rt.Orientation_Constraint:
            returnConst = rot_controller
            
        return returnConst
    
    def assign_rot_const(self, inObj, inTarget, keepInit=False):
        """
        객체에 회전 제약 컨트롤러를 할당하고 지정된 타겟을 추가.
        
        Args:
            inObj: 제약을 적용할 객체
            inTarget: 타겟 객체
            keepInit: 기존 변환 유지 여부 (기본값: False)
            
        Returns:
            회전 제약 컨트롤러
        """
        # 회전 컨트롤러가 리스트 형태가 아니면 변환
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) != rt.Rotation_list:
            rt.setPropertyController(inObj.controller, "Rotation", rt.Rotation_list())
            
        # 기존 회전 제약 컨트롤러 확인
        targetRotConstraint = self.get_rot_const(inObj)
        
        # 회전 제약 컨트롤러가 없으면 새로 생성
        if targetRotConstraint is None:
            targetRotConstraint = rt.Orientation_Constraint()
            rot_list = self.get_rot_list_controller(inObj)
            rt.setPropertyController(rot_list, "Available", targetRotConstraint)
            rot_list.setActive(rot_list.count)
        
        # 타겟 추가 및 가중치 조정
        targetNum = targetRotConstraint.getNumTargets()
        targetWeight = 100.0 / (targetNum + 1)
        targetRotConstraint.appendTarget(inTarget, targetWeight)
        
        # 기존 타겟이 있으면 가중치 재조정
        if targetNum > 0:
            newWeightScale = 100.0 - targetWeight
            for i in range(1, targetNum + 1):  # Maxscript는 1부터 시작
                newWeight = targetRotConstraint.GetWeight(i) * 0.01 * newWeightScale
                targetRotConstraint.SetWeight(i, newWeight)
                
        # 상대적 모드 설정
        targetRotConstraint.relative = keepInit
        
        return targetRotConstraint
    
    def assign_rot_const_multi(self, inObj, inTargetArray, keepInit=False):
        """
        객체에 여러 타겟을 가진 회전 제약 컨트롤러를 할당.
        
        Args:
            inObj: 제약을 적용할 객체
            inTargetArray: 타겟 객체 배열
            keepInit: 기존 변환 유지 여부 (기본값: False)
            
        Returns:
            None
        """
        for item in inTargetArray:
            self.assign_rot_const(inObj, item, keepInit=keepInit)
    
    def add_target_to_rot_const(self, inObj, inTarget, inWeight):
        """
        기존 회전 제약 컨트롤러에 새 타겟을 추가하고 지정된 가중치 설정.
        
        Args:
            inObj: 제약이 적용된 객체
            inTarget: 추가할 타겟 객체
            inWeight: 적용할 가중치 값
            
        Returns:
            None
        """
        # 회전 제약 컨트롤러에 타겟 추가
        targetRotConstraint = self.assign_rot_const(inObj, inTarget)
        
        # 마지막 타겟에 특정 가중치 적용
        targetNum = targetRotConstraint.getNumTargets()
        targetRotConstraint.SetWeight(targetNum, inWeight)
    
    def assign_euler_xyz(self, inObj):
        """
        객체에 오일러 XYZ 회전 컨트롤러를 할당.
        
        Args:
            inObj: 컨트롤러를 할당할 객체
            
        Returns:
            None
        """
        # 회전 컨트롤러가 리스트 형태가 아니면 변환
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) != rt.Rotation_list:
            rt.setPropertyController(inObj.controller, "Rotation", rt.Rotation_list())
            
        # 회전 리스트 컨트롤러 가져오기
        rotList = self.assign_rot_list(inObj)
        
        # Euler_XYZ 컨트롤러 할당
        rt.setPropertyController(rotList, "Available", rt.Euler_XYZ())
        rotList.setActive(rotList.count)
    
    def get_lookat(self, inObj):
        """
        객체의 LookAt 제약 컨트롤러를 찾아 반환.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            LookAt 제약 컨트롤러 (없으면 None)
        """
        returnConst = None
        
        # 회전 컨트롤러가 리스트 형태인 경우
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            lst = rot_controller
            constNum = lst.getCount()
            activeNum = lst.getActive()
            
            # 리스트 내 모든 컨트롤러 검사
            for i in range(constNum):
                sub_controller = lst[i].controller
                if rt.classOf(sub_controller) == rt.LookAt_Constraint:
                    returnConst = sub_controller
                    # 현재 활성화된 컨트롤러면 즉시 반환
                    if activeNum == i:
                        return returnConst
        
        # 회전 컨트롤러가 직접 LookAt_Constraint인 경우
        elif rt.classOf(rot_controller) == rt.LookAt_Constraint:
            returnConst = rot_controller
            
        return returnConst
    
    def assign_lookat(self, inObj, inTarget, keepInit=False):
        """
        객체에 LookAt 제약 컨트롤러를 할당하고 지정된 타겟을 추가.
        
        Args:
            inObj: 제약을 적용할 객체
            inTarget: 타겟 객체
            keepInit: 기존 변환 유지 여부 (기본값: False)
            
        Returns:
            LookAt 제약 컨트롤러
        """
        # 회전 컨트롤러가 리스트 형태가 아니면 변환
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) != rt.Rotation_list:
            rt.setPropertyController(inObj.controller, "Rotation", rt.Rotation_list())
            
        # 기존 LookAt 제약 컨트롤러 확인
        targetRotConstraint = self.get_lookat(inObj)
        
        # LookAt 제약 컨트롤러가 없으면 새로 생성
        if targetRotConstraint is None:
            targetRotConstraint = rt.LookAt_Constraint()
            rot_list = self.get_rot_list_controller(inObj)
            rt.setPropertyController(rot_list, "Available", targetRotConstraint)
            rot_list.setActive(rot_list.count)
        
        # 타겟 추가 및 가중치 조정
        targetNum = targetRotConstraint.getNumTargets()
        targetWeight = 100.0 / (targetNum + 1)
        targetRotConstraint.appendTarget(inTarget, targetWeight)
        
        # 기존 타겟이 있으면 가중치 재조정
        if targetNum > 0:
            newWeightScale = 100.0 - targetWeight
            for i in range(1, targetNum + 1):  # Maxscript는 1부터 시작
                newWeight = targetRotConstraint.GetWeight(i) * 0.01 * newWeightScale
                targetRotConstraint.SetWeight(i, newWeight)
                
        # 상대적 모드 설정
        targetRotConstraint.relative = keepInit
        
        targetRotConstraint.lookat_vector_length = 0
        
        return targetRotConstraint
    
    def assign_lookat_multi(self, inObj, inTargetArray, keepInit=False):
        """
        객체에 여러 타겟을 가진 LookAt 제약 컨트롤러를 할당.
        
        Args:
            inObj: 제약을 적용할 객체
            inTargetArray: 타겟 객체 배열
            keepInit: 기존 변환 유지 여부 (기본값: False)
            
        Returns:
            None
        """
        for item in inTargetArray:
            self.assign_lookat(inObj, item, keepInit=keepInit)
    
    def assign_lookat_flipless(self, inObj, inTarget):
        """
        플립 없는 LookAt 제약 컨트롤러를 스크립트 기반으로 구현하여 할당.
        부모가 있는 객체에만 적용 가능.
        
        Args:
            inObj: 제약을 적용할 객체 (부모가 있어야 함)
            inTarget: 바라볼 타겟 객체
            
        Returns:
            None
        """
        # 객체에 부모가 있는 경우에만 실행
        if inObj.parent is not None:
            # 회전 스크립트 컨트롤러 생성
            targetRotConstraint = rt.Rotation_Script()
            
            # 스크립트에 필요한 노드 추가
            targetRotConstraint.AddNode("Target", inTarget)
            targetRotConstraint.AddNode("Parent", inObj.parent)
            
            # 객체 위치 컨트롤러 추가
            pos_controller = rt.getPropertyController(inObj.controller, "Position")
            targetRotConstraint.AddObject("NodePos", pos_controller)
            
            # 회전 계산 스크립트 설정
            script = textwrap.dedent(r'''
                theTargetVector=(Target.transform.position * Inverse Parent.transform)-NodePos.value
                theAxis=Normalize (cross theTargetVector [1,0,0])
                theAngle=acos (dot (Normalize theTargetVector) [1,0,0])
                Quat theAngle theAxis
                ''')
            targetRotConstraint.script = script
            
            # 회전 컨트롤러가 리스트 형태가 아니면 변환
            rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
            if rt.classOf(rot_controller) != rt.Rotation_list:
                rt.setPropertyController(inObj.controller, "Rotation", rt.Rotation_list())
                
            # 회전 리스트에 스크립트 컨트롤러 추가
            rot_list = self.get_rot_list_controller(inObj)
            rt.setPropertyController(rot_list, "Available", targetRotConstraint)
            rot_list.setActive(rot_list.count)
    
    def assign_rot_const_scripted(self, inObj, inTarget):
        """
        스크립트 기반 회전 제약을 구현하여 할당.
        ExposeTransform을 활용한 고급 회전 제약 구현.
        
        Args:
            inObj: 제약을 적용할 객체
            inTarget: 회전 참조 타겟 객체
            
        Returns:
            생성된 회전 스크립트 컨트롤러
        """
        # 회전 스크립트 컨트롤러 생성
        targetRotConstraint = rt.Rotation_Script()
        
        # 회전 컨트롤러 리스트에 추가
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) != rt.Rotation_list:
            rt.setPropertyController(inObj.controller, "Rotation", rt.Rotation_list())
            
        rot_list = self.get_rot_list_controller(inObj)
        rt.setPropertyController(rot_list, "Available", targetRotConstraint)
        rot_list.setActive(rot_list.count)
        
        # 헬퍼 객체 이름 생성
        if self.name:
            rotPointName = self.name.replace_Type(inObj.name, self.name.get_dummy_value())
            rotMeasurePointName = self.name.increase_index(rotPointName, 1)
            rotExpName = self.name.replace_Type(inObj.name, self.name.get_exposeTm_value())
            rotExpName = self.name.replace_Index(rotExpName, "0")
            
            print(f"dumStr: {self.name.get_dummy_value()}")
            print(f"exposeTmStr: {self.name.get_exposeTm_value()}")
            print(f"rotPointName: {rotPointName}, rotMeasurePointName: {rotMeasurePointName}, rotExpName: {rotExpName}")
        else:
            # name 서비스가 없는 경우 기본 이름 사용
            base_name = rt.getProperty(inObj, "name")
            rotPointName = f"dum_{base_name}"
            rotMeasurePointName = f"dum_{base_name}_01"
            rotExpName = f"exp_{base_name}_0"
        
        # 헬퍼 객체 생성
        if self.helper:
            rotPoint = self.helper.create_point(rotPointName, size=2, boxToggle=True, crossToggle=False)
            rotMeasuerPoint = self.helper.create_point(rotMeasurePointName, size=3, boxToggle=True, crossToggle=False)
            rotExpPoint = rt.ExposeTm(name=rotExpName, size=3, box=False, cross=True, wirecolor=rt.Color(14, 255, 2))
        else:
            # 직접 헬퍼 객체 생성
            rotPoint = rt.Point(name=rotPointName, size=2, box=True, cross=False)
            rotMeasuerPoint = rt.Point(name=rotMeasurePointName, size=3, box=True, cross=False)
            rotExpPoint = rt.ExposeTm(name=rotExpName, size=3, box=False, cross=True, wirecolor=rt.Color(14, 255, 2))
        
        # 초기 변환 설정
        rt.setProperty(rotPoint, "transform", rt.getProperty(inObj, "transform"))
        rt.setProperty(rotMeasuerPoint, "transform", rt.getProperty(inObj, "transform"))
        rt.setProperty(rotExpPoint, "transform", rt.getProperty(inObj, "transform"))
        
        # 부모 관계 설정
        rotPoint.parent = inTarget
        rotMeasuerPoint.parent = inTarget.parent
        rotExpPoint.parent = inTarget
        
        # ExposeTm 설정
        rotExpPoint.exposeNode = rotPoint
        rotExpPoint.useParent = False
        rotExpPoint.localReferenceNode = rotMeasuerPoint
        
        # 회전 스크립트 생성
        rotScript = textwrap.dedent(r'''
            local targetRot = rot.localEuler
            local rotX = (radToDeg targetRot.x)
            local rotY = (radToDeg targetRot.y)
            local rotZ = (radToDeg targetRot.z)
            local result = eulerAngles rotX rotY rotZ
            eulerToQuat result
            ''')
        
        # 스크립트에 노드 추가 및 표현식 설정
        targetRotConstraint.AddNode("rot", rotExpPoint)
        targetRotConstraint.SetExpression(rotScript)
        
        return targetRotConstraint
    
    def assign_scripted_lookat(self, inOri, inTarget):
        """
        스크립트 기반 LookAt 제약을 구현하여 할당.
        여러 개의 헬퍼 객체를 생성하여 복잡한 LookAt 제약 구현.
        
        Args:
            inOri: 제약을 적용할 객체
            inTarget: 바라볼 타겟 객체 배열
            
        Returns:
            None
        """
        oriObj = inOri
        oriParentObj = inOri.parent
        targetObjArray = inTarget
        
        # 객체 이름 생성
        if self.name:
            objName = self.name.get_string(oriObj.name)
            indexNum = self.name.get_index_as_digit(oriObj.name)
            dummyName = self.name.add_prefix_to_real_name(objName, self.name.get_dummy_value())
            
            lookAtPointName = self.name.replace_Index(dummyName, str(indexNum))
            lookAtMeasurePointName = self.name.replace_Index(dummyName, str(indexNum+1))
            lookAtExpPointName = dummyName + self.name.get_exposeTm_value()
            lookAtExpPointName = self.name.replace_Index(lookAtExpPointName, "0")
        
        # 헬퍼 객체 생성
        if self.helper:
            lookAtPoint = self.helper.create_point(lookAtPointName, size=2, boxToggle=True, crossToggle=False)
            lookAtMeasurePoint = self.helper.create_point(lookAtMeasurePointName, size=3, boxToggle=True, crossToggle=False)
            lookAtExpPoint = rt.ExposeTm(name=lookAtExpPointName, size=3, box=False, cross=True, wirecolor=rt.Color(14, 255, 2))
        
        # 초기 변환 설정
        rt.setProperty(lookAtPoint, "transform", rt.getProperty(oriObj, "transform"))
        rt.setProperty(lookAtMeasurePoint, "transform", rt.getProperty(oriObj, "transform"))
        rt.setProperty(lookAtExpPoint, "transform", rt.getProperty(oriObj, "transform"))
        
        # 부모 관계 설정
        rt.setProperty(lookAtPoint, "parent", oriParentObj)
        rt.setProperty(lookAtMeasurePoint, "parent", oriParentObj)
        rt.setProperty(lookAtExpPoint, "parent", oriParentObj)
        
        # ExposeTm 설정
        lookAtExpPoint.exposeNode = lookAtPoint
        lookAtExpPoint.useParent = False
        lookAtExpPoint.localReferenceNode = lookAtMeasurePoint
        
        # LookAt 제약 설정
        lookAtPoint_rot_controller = rt.LookAt_Constraint()
        rt.setPropertyController(lookAtPoint.controller, "Rotation", lookAtPoint_rot_controller)
        
        # 타겟 추가
        target_weight = 100.0 / len(targetObjArray)
        for item in targetObjArray:
            lookAtPoint_rot_controller.appendTarget(item, target_weight)
        
        # 오일러 XYZ 컨트롤러 생성
        rotControl = rt.Euler_XYZ()
        
        x_controller = rt.Float_Expression()
        y_controller = rt.Float_Expression()
        z_controller = rt.Float_Expression()
        
        # 스칼라 타겟 추가
        x_controller.AddScalarTarget("rotX", rt.getPropertyController(lookAtExpPoint, "localEulerX"))
        y_controller.AddScalarTarget("rotY", rt.getPropertyController(lookAtExpPoint, "localEulerY"))
        z_controller.AddScalarTarget("rotZ", rt.getPropertyController(lookAtExpPoint, "localEulerZ"))
        
        # 표현식 설정
        x_controller.SetExpression("rotX")
        y_controller.SetExpression("rotY")
        z_controller.SetExpression("rotZ")
        
        # 각 축별 회전에 Float_Expression 컨트롤러 할당
        rt.setPropertyController(rotControl, "X_Rotation", x_controller)
        rt.setPropertyController(rotControl, "Y_Rotation", y_controller)
        rt.setPropertyController(rotControl, "Z_Rotation", z_controller)

        # 회전 컨트롤러 목록 확인 또는 생성
        rot_controller = rt.getPropertyController(oriObj.controller, "Rotation")
        if rt.classOf(rot_controller) != rt.Rotation_list:
            rt.setPropertyController(oriObj.controller, "Rotation", rt.Rotation_list())
        
        # 회전 리스트에 오일러 컨트롤러 추가
        rot_list = self.get_rot_list_controller(oriObj)
        rt.setPropertyController(rot_list, "Available", rotControl)
        
        # 컨트롤러 이름 설정
        rot_controller_num = rot_list.count
        rot_list.setname(rot_controller_num, "Script Rotation")
        
        # 컨트롤러 업데이트
        x_controller.Update()
        y_controller.Update()
        z_controller.Update()
    
    def assign_attachment(self, inPlacedObj, inSurfObj, bAlign=False, shiftAxis=(0, 0, 1), shiftAmount=3.0):
        """
        객체를 다른 객체의 표면에 부착하는 Attachment 제약 컨트롤러 할당.
        
        Args:
            inPlacedObj: 부착될 객체
            inSurfObj: 표면 객체
            bAlign: 표면 법선에 맞춰 정렬할지 여부
            shiftAxis: 레이 방향 축 (기본값: Z축)
            shiftAmount: 레이 거리 (기본값: 3.0)
            
        Returns:
            생성된 Attachment 컨트롤러 또는 None (실패 시)
        """
        # 현재 변환 행렬 백업 및 시작 위치 계산
        placedObjTm = rt.getProperty(inPlacedObj, "transform")
        rt.preTranslate(placedObjTm, rt.Point3(shiftAxis[0], shiftAxis[1], shiftAxis[2]) * (-shiftAmount))
        dirStartPos = placedObjTm.pos
        
        # 끝 위치 계산
        placedObjTm = rt.getProperty(inPlacedObj, "transform")
        rt.preTranslate(placedObjTm, rt.Point3(shiftAxis[0], shiftAxis[1], shiftAxis[2]) * shiftAmount)
        dirEndPos = placedObjTm.pos
        
        # 방향 벡터 및 레이 생성
        dirVec = dirEndPos - dirStartPos
        dirRay = rt.ray(dirEndPos, -dirVec)
        
        # 레이 교차 검사
        intersectArr = rt.intersectRayEx(inSurfObj, dirRay)
        
        # 교차점이 있으면 Attachment 제약 생성
        if intersectArr is not None:
            # 위치 컨트롤러 리스트 생성 또는 가져오기
            posListConst = self.assign_pos_list(inPlacedObj)
            
            # Attachment 컨트롤러 생성
            attConst = rt.Attachment()
            rt.setPropertyController(posListConst, "Available", attConst)
            
            # 제약 속성 설정
            attConst.node = inSurfObj
            attConst.align = bAlign
            
            # 부착 키 추가
            attachKey = rt.attachCtrl.addNewKey(attConst, 0)
            attachKey.face = intersectArr[2] - 1  # 인덱스 조정 (MAXScript는 1부터, Python은 0부터)
            attachKey.coord = intersectArr[3]
            
            return attConst
        else:
            return None
    
    def get_pos_controllers_name_from_list(self, inObj):
        """
        객체의 위치 컨트롤러 리스트에서 각 컨트롤러의 이름을 가져옴.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            컨트롤러 이름 배열
        """
        returnNameArray = []
        
        # 위치 컨트롤러가 리스트 형태인지 확인
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) == rt.Position_list:
            posList = pos_controller
            
            # 각 컨트롤러의 이름을 배열에 추가
            for i in range(1, posList.count + 1):  # MAXScript는 1부터 시작
                returnNameArray.append(posList.getName(i))
                
        return returnNameArray
    
    def get_pos_controllers_weight_from_list(self, inObj):
        """
        객체의 위치 컨트롤러 리스트에서 각 컨트롤러의 가중치를 가져옴.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            컨트롤러 가중치 배열
        """
        returnWeightArray = []
        
        # 위치 컨트롤러가 리스트 형태인지 확인
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) == rt.Position_list:
            posList = pos_controller
            
            # 가중치 배열 가져오기
            returnWeightArray = list(posList.weight)
                
        return returnWeightArray
    
    def set_pos_controllers_name_in_list(self, inObj, inLayerNum, inNewName):
        """
        객체의 위치 컨트롤러 리스트에서 특정 컨트롤러의 이름을 설정.
        
        Args:
            inObj: 대상 객체
            inLayerNum: 컨트롤러 인덱스 (1부터 시작)
            inNewName: 새 이름
            
        Returns:
            None
        """
        # 위치 컨트롤러 리스트 가져오기
        listCtr = self.get_pos_list_controller(inObj)
        
        # 리스트가 있으면 이름 설정
        if listCtr is not None:
            listCtr.setName(inLayerNum, inNewName)
    
    def set_pos_controllers_weight_in_list(self, inObj, inLayerNum, inNewWeight):
        """
        객체의 위치 컨트롤러 리스트에서 특정 컨트롤러의 가중치를 설정.
        
        Args:
            inObj: 대상 객체
            inLayerNum: 컨트롤러 인덱스 (1부터 시작)
            inNewWeight: 새 가중치
            
        Returns:
            None
        """
        # 위치 컨트롤러 리스트 가져오기
        listCtr = self.get_pos_list_controller(inObj)
        
        # 리스트가 있으면 가중치 설정
        if listCtr is not None:
            listCtr.weight[inLayerNum] = inNewWeight
    
    def get_rot_controllers_name_from_list(self, inObj):
        """
        객체의 회전 컨트롤러 리스트에서 각 컨트롤러의 이름을 가져옴.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            컨트롤러 이름 배열
        """
        returnNameArray = []
        
        # 회전 컨트롤러가 리스트 형태인지 확인
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            rotList = rot_controller
            
            # 각 컨트롤러의 이름을 배열에 추가
            for i in range(1, rotList.count + 1):  # MAXScript는 1부터 시작
                returnNameArray.append(rotList.getName(i))
                
        return returnNameArray
    
    def get_rot_controllers_weight_from_list(self, inObj):
        """
        객체의 회전 컨트롤러 리스트에서 각 컨트롤러의 가중치를 가져옴.
        
        Args:
            inObj: 대상 객체
            
        Returns:
            컨트롤러 가중치 배열
        """
        returnWeightArray = []
        
        # 회전 컨트롤러가 리스트 형태인지 확인
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            rotList = rot_controller
            
            # 가중치 배열 가져오기
            returnWeightArray = list(rotList.weight)
                
        return returnWeightArray
    
    def set_rot_controllers_name_in_list(self, inObj, inLayerNum, inNewName):
        """
        객체의 회전 컨트롤러 리스트에서 특정 컨트롤러의 이름을 설정.
        
        Args:
            inObj: 대상 객체
            inLayerNum: 컨트롤러 인덱스 (1부터 시작)
            inNewName: 새 이름
            
        Returns:
            None
        """
        # 회전 컨트롤러 리스트 가져오기
        listCtr = self.get_rot_list_controller(inObj)
        
        # 리스트가 있으면 이름 설정
        if listCtr is not None:
            listCtr.setName(inLayerNum, inNewName)
    
    def set_rot_controllers_weight_in_list(self, inObj, inLayerNum, inNewWeight):
        """
        객체의 회전 컨트롤러 리스트에서 특정 컨트롤러의 가중치를 설정.
        
        Args:
            inObj: 대상 객체
            inLayerNum: 컨트롤러 인덱스 (1부터 시작)
            inNewWeight: 새 가중치
            
        Returns:
            None
        """
        # 회전 컨트롤러 리스트 가져오기
        listCtr = self.get_rot_list_controller(inObj)
        
        # 리스트가 있으면 가중치 설정
        if listCtr is not None:
            listCtr.weight[inLayerNum] = inNewWeight
