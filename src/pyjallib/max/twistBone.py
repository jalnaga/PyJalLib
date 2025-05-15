#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 트위스트 뼈대(TwistBone) 모듈

3ds Max에서 캐릭터 리깅에 필요한 트위스트 뼈대를 생성하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 상체(Upper) 및 하체(Lower) 트위스트 뼈대 자동 생성
- 스크립트 기반 비틀림 제어
- 비틀림 가중치 자동 분배
- 계층 구조 자동 설정

## 구현 정보
- 원본 MAXScript의 twistBone.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
- 스크립트 표현식을 통한 정밀한 비틀림 제어
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .constraint import Constraint
from .bip import Bip
from .bone import Bone


class TwistBone:
    """
    # TwistBone 클래스
    
    3ds Max에서 캐릭터 리깅을 위한 트위스트 뼈대를 생성하고 제어하는 기능을 제공합니다.
    
    ## 주요 기능
    - 상체(Upper) 및 하체(Lower) 트위스트 뼈대 자동 생성
    - 스크립트 컨트롤러를 통한 정밀한 비틀림 제어
    - 뼈대 간 가중치 자동 분배
    - 이름 규칙 자동 적용
    
    ## 구현 정보
    - MAXScript의 _TwistBone 구조체를 Python 클래스로 재구현
    - rotation_script 컨트롤러를 통한 비틀림 계산
    - 상/하체에 따른 서로 다른 회전 표현식 적용
    
    ## 사용 예시
    ```python
    # TwistBone 객체 생성
    twist_bone = TwistBone()
    
    # 상체 트위스트 뼈대 생성 (어깨-팔꿈치)
    upper_result = twist_bone.create_upper_limb_bones(shoulder, elbow)
    
    # 하체 트위스트 뼈대 생성 (팔꿈치-손목)
    lower_result = twist_bone.create_lower_limb_bones(elbow, wrist)
    ```
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, bipService=None, boneService=None):
        """
        TwistBone 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - animService (Anim, optional): 애니메이션 서비스 (기본값: None, 새로 생성)
        - constraintService (Constraint, optional): 제약 서비스 (기본값: None, 새로 생성)
        - bipService (Bip, optional): 바이페드 서비스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): 뼈대 서비스 (기본값: None, 새로 생성)
        
        ## 참고
        - 서비스 인스턴스가 제공되지 않으면 자동으로 생성됩니다.
        - 종속성 있는 서비스들은 적절히 연결됩니다.
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # Ensure dependent services use the potentially newly created instances
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(animService=self.anim, nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        
        # 객체 속성 초기화
        self.limb = None
        self.child = None
        self.twistNum = 0
        self.bones = []
        self.twistType = ""
        
        self.upperTwistBoneExpression = (
            "localTm = limb.transform * (inverse limbParent.transform)\n"
            "tm = localTm * inverse(localRefTm)\n"
            "\n"
            "q = tm.rotation\n"
            "\n"
            "axis = [1,0,0]\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat q.angle proj\n"
            "twist = normalize twist\n"
            "--swing = tm.rotation * (inverse twist)\n"
            "\n"
            "inverse twist\n"
        )
        
        self.lowerTwistBoneExpression = (
            "localTm = limb.transform * (inverse limbParent.transform)\n"
            "tm = localTm * inverse(localRefTm)\n"
            "\n"
            "q = tm.rotation\n"
            "\n"
            "axis = [1,0,0]\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat q.angle proj\n"
            "twist = normalize twist\n"
            "--swing = tm.rotation * (inverse twist)\n"
            "\n"
            "twist\n"
        )
            
    def reset(self):
        """
        클래스의 작업 데이터를 초기화합니다.
        
        서비스 객체는 유지하면서 클래스의 작업 상태만 초기화합니다.
        
        ## Returns
        - self: 메소드 체이닝을 위한 자기 자신 반환
        """
        self.limb = None
        self.child = None
        self.twistNum = 0
        self.bones = []
        self.twistType = ""
        
        return self
            
    def create_upper_limb_bones(self, inObj, inChild, twistNum=4):
        """
        상체 트위스트 뼈대(어깨, 상완 등)를 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 트위스트 뼈대의 부모 객체(뼈) (일반적으로 상완 또는 대퇴부)
        - inChild (MaxObject): 자식 객체(뼈) (일반적으로 전완 또는 하퇴부)
        - twistNum (int): 생성할 트위스트 뼈대의 개수 (기본값: 4)
        
        ## Returns
        - dict: 생성된 트위스트 뼈대 정보를 담고 있는 사전 객체
            - "Bones": 생성된 뼈대 객체들의 배열
            - "Type": "Upper" (상체 타입)
            - "Limb": 부모 객체 참조
            - "Child": 자식 객체 참조
            - "TwistNum": 생성된 트위스트 뼈대 개수
        
        ## 동작 방식
        1. 뼈대 간 거리 및 방향 계산
        2. 기본 트위스트 뼈대 생성 및 스크립트 컨트롤러 설정
        3. 가중치 분배 및 추가 트위스트 뼈대 생성
        4. 계층 구조 설정 및 이름 규칙 적용
        """
        limb = inObj
        distance = rt.distance(limb, inChild)
        facingDirVec = inChild.transform.position - inObj.transform.position
        inObjXAxisVec = inObj.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        offssetAmount = (distance / twistNum) * distanceDir
        weightVal = 100.0 / (twistNum-1)
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "Twist")
        if inObj.name[0].islower():
            boneName = boneName.lower()
        twistBone = self.bone.create_nub_bone(boneName, 2)
        twistBone.name = self.name.replace_name_part("Index", boneName, "1")
        twistBone.name = self.name.remove_name_part("Nub", twistBone.name)
        twistBone.transform = limb.transform
        twistBone.parent = limb
        twistBoneLocalRefTM = limb.transform * rt.inverse(limb.parent.transform)
        
        twistBoneRotListController = self.const.assign_rot_list(twistBone)
        twistBoneController = rt.Rotation_Script()
        twistBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
        twistBoneController.addNode("limb", limb)
        twistBoneController.addNode("limbParent", limb.parent)
        twistBoneController.setExpression(self.upperTwistBoneExpression)
        twistBoneController.update()
        
        rt.setPropertyController(twistBoneRotListController, "Available", twistBoneController)
        twistBoneRotListController.delete(1)
        twistBoneRotListController.setActive(twistBoneRotListController.count)
        twistBoneRotListController.weight[0] = 100.0
        
        boneChainArray.append(twistBone)
        
        if twistNum > 1:
            lastBone = self.bone.create_nub_bone(boneName, 2)
            lastBone.name = self.name.replace_name_part("Index", boneName, str(twistNum))
            lastBone.name = self.name.remove_name_part("Nub", lastBone.name)
            lastBone.transform = limb.transform
            lastBone.parent = limb
            self.anim.move_local(lastBone, offssetAmount*(twistNum-1), 0, 0)
            
            if twistNum > 2:
                for i in range(1, twistNum-1):
                    twistExtraBone = self.bone.create_nub_bone(boneName, 2)
                    twistExtraBone.name = self.name.replace_name_part("Index", boneName, str(i+1))
                    twistExtraBone.name = self.name.remove_name_part("Nub", twistExtraBone.name)
                    twistExtraBone.transform = limb.transform
                    twistExtraBone.parent = limb
                    self.anim.move_local(twistExtraBone, offssetAmount*i, 0, 0)
                    
                    twistExtraBoneRotListController = self.const.assign_rot_list(twistExtraBone)
                    twistExtraBoneController = rt.Rotation_Script()
                    twistExtraBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
                    twistExtraBoneController.addNode("limb", limb)
                    twistExtraBoneController.addNode("limbParent", limb.parent)
                    twistExtraBoneController.setExpression(self.upperTwistBoneExpression)
                    
                    rt.setPropertyController(twistExtraBoneRotListController, "Available", twistExtraBoneController)
                    twistExtraBoneRotListController.delete(1)
                    twistExtraBoneRotListController.setActive(twistExtraBoneRotListController.count)
                    twistExtraBoneRotListController.weight[0] = weightVal * (twistNum-1-i)
                    
                    boneChainArray.append(twistExtraBone)
            
            boneChainArray.append(lastBone)
        
        # 결과를 멤버 변수에 저장
        self.limb = inObj
        self.child = inChild
        self.twistNum = twistNum
        self.bones = boneChainArray
        self.twistType = "Upper"
        
        returnVal = {
            "Bones": boneChainArray,
            "Type": "Upper",
            "Limb": inObj,
            "Child": inChild,
            "TwistNum": twistNum
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return returnVal

    def create_lower_limb_bones(self, inObj, inChild, twistNum=4):
        """
        하체 트위스트 뼈대(전완, 하퇴 등)를 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 트위스트 뼈대의 부모 객체(뼈) (일반적으로 전완 또는 하퇴부)
        - inChild (MaxObject): 자식 객체(뼈) (일반적으로 손목 또는 발목)
        - twistNum (int): 생성할 트위스트 뼈대의 개수 (기본값: 4)
        
        ## Returns
        - dict: 생성된 트위스트 뼈대 정보를 담고 있는 사전 객체
            - "Bones": 생성된 뼈대 객체들의 배열
            - "Type": "Lower" (하체 타입)
            - "Limb": 부모 객체 참조
            - "Child": 자식 객체 참조
            - "TwistNum": 생성된 트위스트 뼈대 개수
        
        ## 동작 방식
        1. 뼈대 간 거리 및 방향 계산
        2. 기본 트위스트 뼈대 생성 및 스크립트 컨트롤러 설정
        3. 가중치 분배 및 추가 트위스트 뼈대 생성
        4. 상체와 다른 배치 방식 및 회전 표현식 적용
        """
        limb = inChild
        distance = rt.distance(inObj, inChild)
        facingDirVec = inChild.transform.position - inObj.transform.position
        inObjXAxisVec = inObj.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        offssetAmount = (distance / twistNum) * distanceDir
        weightVal = 100.0 / (twistNum-1)
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "Twist")
        if inObj.name[0].islower():
            boneName = boneName.lower()
        twistBone = self.bone.create_nub_bone(boneName, 2)
        twistBone.name = self.name.replace_name_part("Index", boneName, "1")
        twistBone.name = self.name.remove_name_part("Nub", twistBone.name)
        twistBone.transform = inObj.transform
        twistBone.parent = inObj
        self.anim.move_local(twistBone, offssetAmount*(twistNum-1), 0, 0)
        twistBoneLocalRefTM = limb.transform * rt.inverse(limb.parent.transform)
        
        twistBoneRotListController = self.const.assign_rot_list(twistBone)
        twistBoneController = rt.Rotation_Script()
        twistBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
        twistBoneController.addNode("limb", limb)
        twistBoneController.addNode("limbParent", limb.parent)
        twistBoneController.setExpression(self.lowerTwistBoneExpression)
        twistBoneController.update()
        
        rt.setPropertyController(twistBoneRotListController, "Available", twistBoneController)
        twistBoneRotListController.delete(1)
        twistBoneRotListController.setActive(twistBoneRotListController.count)
        twistBoneRotListController.weight[0] = 100.0
        
        if twistNum > 1:
            lastBone = self.bone.create_nub_bone(boneName, 2)
            lastBone.name = self.name.replace_name_part("Index", boneName, str(twistNum))
            lastBone.name = self.name.remove_name_part("Nub", lastBone.name)
            lastBone.transform = inObj.transform
            lastBone.parent = inObj
            self.anim.move_local(lastBone, 0, 0, 0)
            
            if twistNum > 2:
                for i in range(1, twistNum-1):
                    twistExtraBone = self.bone.create_nub_bone(boneName, 2)
                    twistExtraBone.name = self.name.replace_name_part("Index", boneName, str(i+1))
                    twistExtraBone.name = self.name.remove_name_part("Nub", twistExtraBone.name)
                    twistExtraBone.transform = inObj.transform
                    twistExtraBone.parent = inObj
                    self.anim.move_local(twistExtraBone, offssetAmount*(twistNum-1-i), 0, 0)
                    
                    twistExtraBoneRotListController = self.const.assign_rot_list(twistExtraBone)
                    twistExtraBoneController = rt.Rotation_Script()
                    twistExtraBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
                    twistExtraBoneController.addNode("limb", limb)
                    twistExtraBoneController.addNode("limbParent", limb.parent)
                    twistExtraBoneController.setExpression(self.lowerTwistBoneExpression)
                    
                    rt.setPropertyController(twistExtraBoneRotListController, "Available", twistExtraBoneController)
                    twistExtraBoneRotListController.delete(1)
                    twistExtraBoneRotListController.setActive(twistExtraBoneRotListController.count)
                    twistExtraBoneRotListController.weight[0] = weightVal * (twistNum-1-i)
                    
                    boneChainArray.append(twistExtraBone)
            
            boneChainArray.append(lastBone)
        
        # 결과를 멤버 변수에 저장
        self.limb = inObj
        self.child = inChild
        self.twistNum = twistNum
        self.bones = boneChainArray
        self.twistType = "Lower"
        
        returnVal = {
            "Bones": boneChainArray,
            "Type": "Lower",
            "Limb": inObj,
            "Child": inChild,
            "TwistNum": twistNum
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return returnVal