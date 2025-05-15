#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 제약(Constraint) 모듈

3ds Max에서 제약 컨트롤러를 생성하고 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 다양한 제약 컨트롤러 관리 (위치, 회전, LookAt 등)
- 제약 컨트롤러의 타겟 및 가중치 설정
- 컨트롤러 계층 구조 관리
- 고급 스크립팅 기반 제약 구현

## 구현 정보
- 원본 MAXScript의 constraint.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt
import textwrap

# Import necessary service classes for default initialization
from .name import Name
from .helper import Helper


class Constraint:
    """
    # Constraint 클래스
    
    3ds Max에서 다양한 제약 컨트롤러를 생성하고 관리하는 기능을 제공합니다.
    
    ## 주요 기능
    - 위치, 회전, LookAt 제약 컨트롤러 생성 및 관리
    - 컨트롤러 리스트 관리 및 액세스
    - 제약 컨트롤러 타겟 및 가중치 조정
    - 스크립트 기반 고급 제약 구현
    - 여러 타겟을 가진 복합 제약 설정
    
    ## 구현 정보
    - MAXScript의 _Constraint 구조체를 Python 클래스로 재구현
    - 다양한 서비스 클래스와 연동하여 확장 기능 제공
    
    ## 사용 예시
    ```python
    # Constraint 객체 생성
    constraint = Constraint()
    
    # 선택된 객체들 중 첫 번째 객체에 두 번째 객체를 타겟으로 하는 위치 제약 적용
    selected = rt.selection
    if len(selected) >= 2:
        constraint.assign_pos_const(selected[0], selected[1])
    ```
    """
    
    def __init__(self, nameService=None, helperService=None):
        """
        Constraint 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - helperService (Helper, optional): 헬퍼 객체 서비스 (기본값: None, 새로 생성)
        
        ## 참고
        - 서비스 인스턴스가 제공되지 않으면 자동으로 생성됩니다.
        - helperService는 nameService에 의존성이 있어 적절히 연결됩니다.
        """
        self.name = nameService if nameService else Name()
        self.helper = helperService if helperService else Helper(nameService=self.name) # Pass the potentially newly created nameService
    
    def collapse(self, inObj):
        """
        객체의 트랜스폼 컨트롤러를 기본 컨트롤러로 초기화하고 현재 변환 상태를 유지합니다.
        
        ## Parameters
        - inObj (MaxObject): 초기화할 대상 객체
        
        ## 동작 방식
        1. Biped_Object가 아닌 객체에 대해서만 실행
        2. 현재 변환 상태를 백업
        3. 위치, 회전, 스케일 컨트롤러를 기본 컨트롤러로 재설정
        4. 백업한 변환 상태 복원
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
        객체의 위치와 회전 컨트롤러 리스트에서 마지막 컨트롤러를 활성화합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
        
        ## 동작 방식
        1. 위치 컨트롤러가 리스트 형태인 경우 마지막 컨트롤러 활성화
        2. 회전 컨트롤러가 리스트 형태인 경우 마지막 컨트롤러 활성화
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
        객체의 위치 리스트 컨트롤러를 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - Position_list: 위치 리스트 컨트롤러 (없으면 None)
        
        ## 동작 방식
        객체의 위치 컨트롤러가 Position_list 타입인 경우에만 해당 컨트롤러를 반환
        """
        returnPosListCtr = None
        
        # 위치 컨트롤러가 리스트 형태인지 확인
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) == rt.Position_list:
            returnPosListCtr = pos_controller
            
        return returnPosListCtr
    
    def assign_pos_list(self, inObj):
        """
        객체에 위치 리스트 컨트롤러를 할당하거나 기존 것을 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - Position_list: 위치 리스트 컨트롤러
        
        ## 동작 방식
        1. 현재 위치 컨트롤러가 리스트 형태가 아니면 새로 생성하여 할당
        2. 이미 리스트 형태면 그대로 반환
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
        객체의 위치 제약 컨트롤러를 찾아 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - Position_Constraint: 위치 제약 컨트롤러 (없으면 None)
        
        ## 동작 방식
        1. 위치 컨트롤러가 리스트 형태인 경우 리스트 내 모든 컨트롤러 검사
        2. 활성화된 컨트롤러가 Position_Constraint면 즉시 반환
        3. 위치 컨트롤러가 직접 Position_Constraint인 경우도 반환
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
        객체에 위치 제약 컨트롤러를 할당하고 지정된 타겟을 추가합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTarget (MaxObject): 타겟 객체
        - keepInit (bool): 기존 변환 유지 여부 (기본값: False)
            
        ## Returns
        - Position_Constraint: 설정된 위치 제약 컨트롤러
        
        ## 동작 방식
        1. 위치 컨트롤러가 리스트 형태가 아니면 변환
        2. 기존 위치 제약 컨트롤러가 없으면 새로 생성
        3. 타겟 추가 및 가중치 조정 (새 타겟은 이전 타겟들의 가중치를 조정)
        4. 상대적 모드 설정
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
        객체에 여러 타겟을 가진 위치 제약 컨트롤러를 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTargetArray (list): 타겟 객체 배열
        - keepInit (bool): 기존 변환 유지 여부 (기본값: False)
            
        ## Returns
        - Position_Constraint: 설정된 위치 제약 컨트롤러
        
        ## 동작 방식
        각 타겟에 대해 assign_pos_const 메서드를 호출하여 제약 구성
        """
        for item in inTargetArray:
            self.assign_pos_const(inObj, item, keepInit=keepInit)
        
        return self.get_pos_const(inObj)
    
    def add_target_to_pos_const(self, inObj, inTarget, inWeight):
        """
        기존 위치 제약 컨트롤러에 새 타겟을 추가하고 지정된 가중치를 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약이 적용된 객체
        - inTarget (MaxObject): 추가할 타겟 객체
        - inWeight (float): 적용할 가중치 값
            
        ## Returns
        - Position_Constraint: 업데이트된 위치 제약 컨트롤러
        
        ## 동작 방식
        1. assign_pos_const를 호출하여 타겟 추가
        2. 마지막 타겟에 특정 가중치 적용
        """
        # 위치 제약 컨트롤러에 타겟 추가
        targetPosConst = self.assign_pos_const(inObj, inTarget)
        
        # 마지막 타겟에 특정 가중치 적용
        targetNum = targetPosConst.getNumTargets()
        targetPosConst.SetWeight(targetNum, inWeight)
        
        return targetPosConst
    
    def assign_pos_xyz(self, inObj):
        """
        객체에 위치 XYZ 컨트롤러를 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 컨트롤러를 할당할 객체
            
        ## Returns
        - Position_XYZ: 할당된 위치 XYZ 컨트롤러
        
        ## 동작 방식
        1. 위치 컨트롤러가 리스트 형태가 아니면 변환
        2. 위치 리스트 컨트롤러에 Position_XYZ 컨트롤러 추가
        3. 위치 리스트의 활성 컨트롤러로 설정
        """
        # 위치 컨트롤러가 리스트 형태가 아니면 변환
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) != rt.Position_list:
            rt.setPropertyController(inObj.controller, "Position", rt.Position_list())
            
        # 위치 리스트 컨트롤러 가져오기
        posList = self.assign_pos_list(inObj)
        
        # Position_XYZ 컨트롤러 할당
        posXYZ = rt.Position_XYZ()
        rt.setPropertyController(posList, "Available", posXYZ)
        posList.setActive(posList.count)
        
        return posXYZ
    
    def assign_pos_script_controller(self, inObj):
        """
        객체에 스크립트 기반 위치 컨트롤러를 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 컨트롤러를 할당할 객체
            
        ## Returns
        - Position_Script: 할당된 스크립트 기반 위치 컨트롤러
        
        ## 동작 방식
        1. 위치 컨트롤러가 리스트 형태가 아니면 변환
        2. 위치 리스트 컨트롤러에 Position_Script 컨트롤러 추가
        3. 위치 리스트의 활성 컨트롤러로 설정
        """
        # 위치 컨트롤러가 리스트 형태가 아니면 변환
        pos_controller = rt.getPropertyController(inObj.controller, "Position")
        if rt.classOf(pos_controller) != rt.Position_list:
            rt.setPropertyController(inObj.controller, "Position", rt.Position_list())
            
        # 위치 리스트 컨트롤러 가져오기
        posList = self.assign_pos_list(inObj)
        
        # 스크립트 기반 위치 컨트롤러 할당
        scriptPos = rt.Position_Script()
        rt.setPropertyController(posList, "Available", scriptPos)
        posList.setActive(posList.count)
        
        return scriptPos
    
    def get_rot_list_controller(self, inObj):
        """
        객체의 회전 리스트 컨트롤러를 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - Rotation_list: 회전 리스트 컨트롤러 (없으면 None)
        
        ## 동작 방식
        객체의 회전 컨트롤러가 Rotation_list 타입인 경우에만 해당 컨트롤러를 반환
        """
        returnRotListCtr = None
        
        # 회전 컨트롤러가 리스트 형태인지 확인
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) == rt.Rotation_list:
            returnRotListCtr = rot_controller
            
        return returnRotListCtr
    
    def assign_rot_list(self, inObj):
        """
        객체에 회전 리스트 컨트롤러를 할당하거나 기존 것을 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - Rotation_list: 회전 리스트 컨트롤러
        
        ## 동작 방식
        1. 현재 회전 컨트롤러가 리스트 형태가 아니면 새로 생성하여 할당
        2. 이미 리스트 형태면 그대로 반환
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
        객체의 회전 제약 컨트롤러를 찾아 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - Orientation_Constraint: 회전 제약 컨트롤러 (없으면 None)
        
        ## 동작 방식
        1. 회전 컨트롤러가 리스트 형태인 경우 리스트 내 모든 컨트롤러 검사
        2. 활성화된 컨트롤러가 Orientation_Constraint면 즉시 반환
        3. 회전 컨트롤러가 직접 Orientation_Constraint인 경우도 반환
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
        객체에 회전 제약 컨트롤러를 할당하고 지정된 타겟을 추가합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTarget (MaxObject): 타겟 객체
        - keepInit (bool): 기존 변환 유지 여부 (기본값: False)
            
        ## Returns
        - Orientation_Constraint: 설정된 회전 제약 컨트롤러
        
        ## 동작 방식
        1. 회전 컨트롤러가 리스트 형태가 아니면 변환
        2. 기존 회전 제약 컨트롤러가 없으면 새로 생성
        3. 타겟 추가 및 가중치 조정 (새 타겟은 이전 타겟들의 가중치를 조정)
        4. 상대적 모드 설정
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
        객체에 여러 타겟을 가진 회전 제약 컨트롤러를 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTargetArray (list): 타겟 객체 배열
        - keepInit (bool): 기존 변환 유지 여부 (기본값: False)
            
        ## Returns
        - Orientation_Constraint: 설정된 회전 제약 컨트롤러
        
        ## 동작 방식
        각 타겟에 대해 assign_rot_const 메서드를 호출하여 제약 구성
        """
        for item in inTargetArray:
            self.assign_rot_const(inObj, item, keepInit=keepInit)
        
        return self.get_rot_const(inObj)
    
    def add_target_to_rot_const(self, inObj, inTarget, inWeight):
        """
        기존 회전 제약 컨트롤러에 새 타겟을 추가하고 지정된 가중치를 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약이 적용된 객체
        - inTarget (MaxObject): 추가할 타겟 객체
        - inWeight (float): 적용할 가중치 값
            
        ## Returns
        - Orientation_Constraint: 업데이트된 회전 제약 컨트롤러
        
        ## 동작 방식
        1. assign_rot_const를 호출하여 타겟 추가
        2. 마지막 타겟에 특정 가중치 적용
        """
        # 회전 제약 컨트롤러에 타겟 추가
        targetRotConstraint = self.assign_rot_const(inObj, inTarget)
        
        # 마지막 타겟에 특정 가중치 적용
        targetNum = targetRotConstraint.getNumTargets()
        targetRotConstraint.SetWeight(targetNum, inWeight)
        
        return targetRotConstraint
    
    def assign_euler_xyz(self, inObj):
        """
        객체에 오일러 XYZ 회전 컨트롤러를 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 컨트롤러를 할당할 객체
            
        ## Returns
        - Euler_XYZ: 할당된 오일러 XYZ 컨트롤러
        
        ## 동작 방식
        1. 회전 컨트롤러가 리스트 형태가 아니면 변환
        2. 회전 리스트 컨트롤러에 Euler_XYZ 컨트롤러 추가
        3. 회전 리스트의 활성 컨트롤러로 설정
        """
        # 회전 컨트롤러가 리스트 형태가 아니면 변환
        rot_controller = rt.getPropertyController(inObj.controller, "Rotation")
        if rt.classOf(rot_controller) != rt.Rotation_list:
            rt.setPropertyController(inObj.controller, "Rotation", rt.Rotation_list())
            
        # 회전 리스트 컨트롤러 가져오기
        rotList = self.assign_rot_list(inObj)
        
        # Euler_XYZ 컨트롤러 할당
        eulerXYZ = rt.Euler_XYZ()
        rt.setPropertyController(rotList, "Available", eulerXYZ)
        rotList.setActive(rotList.count)
        
        return eulerXYZ
    
    def get_lookat(self, inObj):
        """
        객체의 LookAt 제약 컨트롤러를 찾아 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - LookAt_Constraint: LookAt 제약 컨트롤러 (없으면 None)
        
        ## 동작 방식
        1. 회전 컨트롤러가 리스트 형태인 경우 리스트 내 모든 컨트롤러 검사
        2. 활성화된 컨트롤러가 LookAt_Constraint면 즉시 반환
        3. 회전 컨트롤러가 직접 LookAt_Constraint인 경우도 반환
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
        객체에 LookAt 제약 컨트롤러를 할당하고 지정된 타겟을 추가합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTarget (MaxObject): 타겟 객체
        - keepInit (bool): 기존 변환 유지 여부 (기본값: False)
            
        ## Returns
        - LookAt_Constraint: 설정된 LookAt 제약 컨트롤러
        
        ## 동작 방식
        1. 회전 컨트롤러가 리스트 형태가 아니면 변환
        2. 기존 LookAt 제약 컨트롤러가 없으면 새로 생성
        3. 타겟 추가 및 가중치 조정 (새 타겟은 이전 타겟들의 가중치를 조정)
        4. 상대적 모드 설정 및 벡터 길이 0으로 설정
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
        객체에 여러 타겟을 가진 LookAt 제약 컨트롤러를 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTargetArray (list): 타겟 객체 배열
        - keepInit (bool): 기존 변환 유지 여부 (기본값: False)
            
        ## Returns
        - LookAt_Constraint: 설정된 LookAt 제약 컨트롤러
        
        ## 동작 방식
        각 타겟에 대해 assign_lookat 메서드를 호출하여 제약 구성
        """
        for item in inTargetArray:
            self.assign_lookat(inObj, item, keepInit=keepInit)
        
        return self.get_lookat(inObj)
    
    def assign_lookat_flipless(self, inObj, inTarget):
        """
        플립 현상 없는 LookAt 제약 컨트롤러를 스크립트 기반으로 구현하여 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체 (부모가 있어야 함)
        - inTarget (MaxObject): 바라볼 타겟 객체
            
        ## Returns
        - Rotation_Script: 생성된 회전 스크립트 컨트롤러 또는 None (실패 시)
        
        ## 동작 방식
        1. 부모가 있는 객체에만 적용 가능
        2. 회전 스크립트 컨트롤러 생성 및 필요한 노드 추가
        3. 벡터 계산을 통한 회전 스크립트 설정
        4. 회전 컨트롤러 리스트에 추가
        
        ## 스크립트 내용
        스크립트는 타겟 벡터를 계산하고 회전축과 각도를 결정하여 쿼터니언 회전 생성
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
            
            return targetRotConstraint
    
    def assign_rot_const_scripted(self, inObj, inTarget):
        """
        스크립트 기반 회전 제약을 구현하여 할당합니다.
        
        ## Parameters
        - inObj (MaxObject): 제약을 적용할 객체
        - inTarget (MaxObject): 회전 참조 타겟 객체
            
        ## Returns
        - Rotation_Script: 생성된 회전 스크립트 컨트롤러
        
        ## 동작 방식
        1. 회전 스크립트 컨트롤러 생성 및 회전 컨트롤러 리스트에 추가
        2. 헬퍼 객체 및 ExposeTm 생성 및 설정
        3. 오일러 회전값을 쿼터니언으로 변환하는 스크립트 설정
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
        rotPointName = self.name.replace_Type(inObj.name, self.name.get_dummy_value())
        rotMeasurePointName = self.name.increase_index(rotPointName, 1)
        rotExpName = self.name.replace_Type(inObj.name, self.name.get_exposeTm_value())
        rotExpName = self.name.replace_Index(rotExpName, "0")
        
        print(f"dumStr: {self.name.get_dummy_value()}")
        print(f"exposeTmStr: {self.name.get_exposeTm_value()}")
        print(f"rotPointName: {rotPointName}, rotMeasurePointName: {rotMeasurePointName}, rotExpName: {rotExpName}")
        
        # 헬퍼 객체 생성
        rotPoint = self.helper.create_point(rotPointName, size=2, boxToggle=True, crossToggle=False)
        rotMeasuerPoint = self.helper.create_point(rotMeasurePointName, size=3, boxToggle=True, crossToggle=False)
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
        스크립트 기반 LookAt 제약을 구현하여 할당합니다.
        
        ## Parameters
        - inOri (MaxObject): 제약을 적용할 객체
        - inTarget (list): 바라볼 타겟 객체 배열
            
        ## Returns
        - dict: 제약 컨트롤러 모음 딕셔너리
            - "lookAt": LookAt 컨트롤러
            - "x", "y", "z": 각 축별 회전 컨트롤러
        
        ## 동작 방식
        1. 헬퍼 객체들 생성 및 설정
        2. ExposeTm을 사용한 회전값 추출 구조 설정
        3. LookAt 제약 및 축별 회전 컨트롤러 설정
        4. Float_Expression 컨트롤러를 사용한 값 전달
        """
        oriObj = inOri
        oriParentObj = inOri.parent
        targetObjArray = inTarget
        
        # 객체 이름 생성
        objName = self.name.get_string(oriObj.name)
        indexVal = self.name.get_index_as_digit(oriObj.name)
        indexNum = 0 if indexVal is False else indexVal
        dummyName = self.name.add_prefix_to_real_name(objName, self.name.get_dummy_value())
        
        lookAtPointName = self.name.replace_Index(dummyName, str(indexNum))
        lookAtMeasurePointName = self.name.replace_Index(dummyName, str(indexNum+1))
        lookAtExpPointName = dummyName + self.name.get_exposeTm_value()
        lookAtExpPointName = self.name.replace_Index(lookAtExpPointName, "0")
        
        # 헬퍼 객체 생성
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
        
        return {"lookAt":lookAtPoint_rot_controller, "x":x_controller, "y":y_controller, "z":z_controller}
    
    def assign_attachment(self, inPlacedObj, inSurfObj, bAlign=False, shiftAxis=(0, 0, 1), shiftAmount=3.0):
        """
        객체를 다른 객체의 표면에 부착하는 Attachment 제약 컨트롤러를 할당합니다.
        
        ## Parameters
        - inPlacedObj (MaxObject): 부착될 객체
        - inSurfObj (MaxObject): 표면 객체
        - bAlign (bool): 표면 법선에 맞춰 정렬할지 여부 (기본값: False)
        - shiftAxis (tuple): 레이 방향 축 (기본값: Z축 (0,0,1))
        - shiftAmount (float): 레이 거리 (기본값: 3.0)
            
        ## Returns
        - Attachment: 생성된 Attachment 컨트롤러 또는 None (실패 시)
        
        ## 동작 방식
        1. 현재 변환 행렬 백업 및 레이 방향 계산
        2. 레이캐스트를 통해 교차점 검사
        3. 교차점이 있으면 Attachment 제약 생성 및 설정
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
        객체의 위치 컨트롤러 리스트에서 각 컨트롤러의 이름을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - list: 컨트롤러 이름 배열
        
        ## 동작 방식
        Position_list 타입의 컨트롤러가 있는 경우 모든 하위 컨트롤러의 이름을 수집
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
        객체의 위치 컨트롤러 리스트에서 각 컨트롤러의 가중치를 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - list: 컨트롤러 가중치 배열
        
        ## 동작 방식
        Position_list 타입의 컨트롤러가 있는 경우 가중치 배열 반환
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
        객체의 위치 컨트롤러 리스트에서 특정 컨트롤러의 이름을 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
        - inLayerNum (int): 컨트롤러 인덱스 (1부터 시작)
        - inNewName (str): 새 이름
        
        ## 동작 방식
        위치 컨트롤러 리스트가 있으면 지정된 인덱스의 컨트롤러 이름 설정
        """
        # 위치 컨트롤러 리스트 가져오기
        listCtr = self.get_pos_list_controller(inObj)
        
        # 리스트가 있으면 이름 설정
        if listCtr is not None:
            listCtr.setName(inLayerNum, inNewName)
    
    def set_pos_controllers_weight_in_list(self, inObj, inLayerNum, inNewWeight):
        """
        객체의 위치 컨트롤러 리스트에서 특정 컨트롤러의 가중치를 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
        - inLayerNum (int): 컨트롤러 인덱스 (1부터 시작)
        - inNewWeight (float): 새 가중치
        
        ## 동작 방식
        위치 컨트롤러 리스트가 있으면 지정된 인덱스의 컨트롤러 가중치 설정
        """
        # 위치 컨트롤러 리스트 가져오기
        listCtr = self.get_pos_list_controller(inObj)
        
        # 리스트가 있으면 가중치 설정
        if listCtr is not None:
            listCtr.weight[inLayerNum] = inNewWeight
    
    def get_rot_controllers_name_from_list(self, inObj):
        """
        객체의 회전 컨트롤러 리스트에서 각 컨트롤러의 이름을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - list: 컨트롤러 이름 배열
        
        ## 동작 방식
        Rotation_list 타입의 컨트롤러가 있는 경우 모든 하위 컨트롤러의 이름을 수집
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
        객체의 회전 컨트롤러 리스트에서 각 컨트롤러의 가중치를 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
            
        ## Returns
        - list: 컨트롤러 가중치 배열
        
        ## 동작 방식
        Rotation_list 타입의 컨트롤러가 있는 경우 가중치 배열 반환
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
        객체의 회전 컨트롤러 리스트에서 특정 컨트롤러의 이름을 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
        - inLayerNum (int): 컨트롤러 인덱스 (1부터 시작)
        - inNewName (str): 새 이름
        
        ## 동작 방식
        회전 컨트롤러 리스트가 있으면 지정된 인덱스의 컨트롤러 이름 설정
        """
        # 회전 컨트롤러 리스트 가져오기
        listCtr = self.get_rot_list_controller(inObj)
        
        # 리스트가 있으면 이름 설정
        if listCtr is not None:
            listCtr.setName(inLayerNum, inNewName)
    
    def set_rot_controllers_weight_in_list(self, inObj, inLayerNum, inNewWeight):
        """
        객체의 회전 컨트롤러 리스트에서 특정 컨트롤러의 가중치를 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 대상 객체
        - inLayerNum (int): 컨트롤러 인덱스 (1부터 시작)
        - inNewWeight (float): 새 가중치
        
        ## 동작 방식
        회전 컨트롤러 리스트가 있으면 지정된 인덱스의 컨트롤러 가중치 설정
        """
        # 회전 컨트롤러 리스트 가져오기
        listCtr = self.get_rot_list_controller(inObj)
        
        # 리스트가 있으면 가중치 설정
        if listCtr is not None:
            listCtr.weight[inLayerNum] = inNewWeight
