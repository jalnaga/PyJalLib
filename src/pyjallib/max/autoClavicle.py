#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 자동 쇄골(AutoClavicle) 모듈

3ds Max에서 쇄골 뼈의 자동화된 움직임을 생성하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 쇄골 링크 시스템 자동 생성
- 쇄골과 상완 관절 연결 자동화
- 뼈대 및 제약 조건 설정
- Look-At 제약을 이용한 IK 시스템 구현

## 구현 정보
- 원본 MAXScript의 autoclavicle.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint
from .bip import Bip


class AutoClavicle:
    """
    # AutoClavicle 클래스
    
    3ds Max에서 자동 쇄골 움직임을 생성하는 시스템을 제공하는 클래스입니다.
    
    ## 주요 기능
    - 쇄골 뼈와 상완 뼈 사이의 자동 움직임 구현
    - 보조 뼈와 헬퍼 포인트를 통한 제어
    - Look-At 제약 기반의 제어 시스템 구축
    - 중간 결과를 반환하고 초기화할 수 있는 재사용 가능한 디자인
    
    ## 구현 정보
    - MAXScript의 _AutoClavicleBone 구조체를 Python 클래스로 재구현
    - 다양한 서비스 클래스를 의존성 주입으로 활용
    
    ## 사용 예시
    ```python
    # AutoClavicle 객체 생성
    autoClavicle = AutoClavicle()
    
    # 자동 쇄골 시스템 생성
    result = autoClavicle.create_bones(clavicle_bone, upper_arm_bone)
    
    # 생성된 자동 쇄골 객체들에 접근
    autoClav = result["Bones"][0]
    ```
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, bipService=None):
        """
        AutoClavicle 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - animService (Anim, optional): 애니메이션 서비스 (기본값: None, 새로 생성)
        - helperService (Helper, optional): 헬퍼 객체 서비스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): 뼈대 서비스 (기본값: None, 새로 생성)
        - constraintService (Constraint, optional): 제약 서비스 (기본값: None, 새로 생성)
        - bipService (Bip, optional): Biped 서비스 (기본값: None, 새로 생성)
        
        ## 참고
        - 서비스 인스턴스가 제공되지 않으면 자동으로 생성됩니다.
        - 종속성이 있는 서비스들은 이미 생성된 서비스를 활용합니다.
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim)
        
        self.boneSize = 2.0
        
        # 초기화된 결과를 저장할 변수들
        self.genBones = []
        self.genHelpers = []
        self.clavicle = None
        self.upperArm = None
        self.liftScale = 0.8
        
    def reset(self):
        """
        클래스의 작업 데이터를 초기화합니다.
        
        생성된 뼈, 헬퍼, 참조 등의 내부 상태를 초기화하여 재사용 가능한 상태로 만듭니다.
        
        ## Returns
        - self: 메소드 체이닝을 위한 자기 자신 반환
        """
        self.genBones = []
        self.genHelpers = []
        self.clavicle = None
        self.upperArm = None
        self.liftScale = 0.8
        
        return self
    
    def create_bones(self, inClavicle, inUpperArm, liftScale=0.8):
        """
        자동 쇄골 시스템을 생성하고 설정합니다.
        
        쇄골 뼈와 상완 뼈 사이의 관계를 분석하여 자동으로 움직이는
        쇄골 시스템을 생성합니다.
        
        ## Parameters
        - inClavicle (MaxObject): 쇄골 뼈 객체
        - inUpperArm (MaxObject): 상완 뼈 객체
        - liftScale (float): 들어올림 스케일 (기본값: 0.8)
            
        ## Returns
        - dict: 생성된 자동 쇄골 시스템 정보를 담은 딕셔너리
            - "Bones": 생성된 뼈 객체 배열
            - "Helpers": 생성된 헬퍼 객체 배열
            - "Clavicle": 원본 쇄골 뼈 참조
            - "UpperArm": 원본 상완 뼈 참조
            - "LiftScale": 적용된 들어올림 스케일 값
            
        ## 동작 방식
        1. 쇄골과 상완 뼈 사이의 거리와 방향 계산
        2. 자동 쇄골 뼈 생성 및 초기 변환 설정
        3. 제어를 위한 헬퍼 포인트 생성
        4. Look-At 제약 설정을 통한 자동 움직임 구현
        """
        if not rt.isValidNode(inClavicle) or not rt.isValidNode(inUpperArm):
            return False
        
        # 리스트 초기화
        genBones = []
        genHelpers = []
        
        # 쇄골과 상완 사이의 거리 계산
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        facingDirVec = inUpperArm.transform.position - inClavicle.transform.position
        inObjXAxisVec = inClavicle.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        clavicleLength *= distanceDir
        
        # 자동 쇄골 이름 생성 및 뼈대 생성
        autoClavicleName = self.name.replace_name_part("RealName", inClavicle.name, "Auto" + self.name._get_filtering_char(inClavicle.name) + "Clavicle")
        if inClavicle.name[0].islower():
            autoClavicleName = autoClavicleName.lower()
        
        autoClavicleBone = self.bone.create_nub_bone(autoClavicleName, 2)
        autoClavicleBone.name = self.name.remove_name_part("Nub", autoClavicleBone.name)
        autoClavicleBone.transform = inClavicle.transform
        self.anim.move_local(autoClavicleBone, clavicleLength/2.0, 0.0, 0.0)
        autoClavicleBone.parent = inClavicle
        genBones.extend(autoClavicleBone)
        
        # 타겟 헬퍼 포인트 생성 (쇄골과 상완용)
        rotTargetClavicle = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target")))
        rotTargetClavicle.name = self.name.replace_name_part("Index", rotTargetClavicle.name, "0")
        rotTargetClavicle.transform = inClavicle.transform
        self.anim.move_local(rotTargetClavicle, clavicleLength, 0.0, 0.0)
        
        rotTargetClavicle.parent = inClavicle
        genHelpers.append(rotTargetClavicle)
        
        rotTargetUpperArm = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target")))
        rotTargetUpperArm.name = self.name.add_suffix_to_real_name(rotTargetUpperArm.name, self.name._get_filtering_char(inClavicle.name) + "arm")
        rotTargetUpperArm.transform = inUpperArm.transform
        self.anim.move_local(rotTargetUpperArm, (clavicleLength/2.0)*liftScale, 0.0, 0.0)
        
        rotTargetUpperArm.parent = inUpperArm
        genHelpers.append(rotTargetUpperArm)
        
        # 회전 헬퍼 포인트 생성
        autoClavicleRotHelper = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Rotation")))
        autoClavicleRotHelper.transform = autoClavicleBone.transform
        autoClavicleRotHelper.parent = inClavicle
        
        lookAtConst = self.const.assign_lookat_multi(autoClavicleRotHelper, [rotTargetClavicle, rotTargetUpperArm])
        
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inClavicle
        lookAtConst.lookat_vector_length = 0.0
        
        genHelpers.append(autoClavicleRotHelper)
        
        # ik 헬퍼 포인트 생성
        ikGoal = self.helper.create_point(autoClavicleName, boxToggle=False, crossToggle=True)
        ikGoal.transform = inClavicle.transform
        self.anim.move_local(ikGoal, clavicleLength, 0.0, 0.0)
        ikGoal.name = self.name.replace_name_part("Type", autoClavicleName, self.name.get_name_part_value_by_description("Type", "Target"))
        ikGoal.name = self.name.replace_name_part("Index", ikGoal.name, "1")
        
        ikGoal.parent = autoClavicleRotHelper
        
        autClavicleLookAtConst = self.const.assign_lookat(autoClavicleBone, ikGoal)
        if clavicleLength < 0:
            autClavicleLookAtConst.target_axisFlip = True
        autClavicleLookAtConst.upnode_world = False
        autClavicleLookAtConst.pickUpNode = inClavicle
        autClavicleLookAtConst.lookat_vector_length = 0.0
        genHelpers.append(ikGoal)
        
        # 결과를 멤버 변수에 저장
        self.genBones = genBones
        self.genHelpers = genHelpers
        self.clavicle = inClavicle
        self.upperArm = inUpperArm
        self.liftScale = liftScale
        
        # AutoClavicleChain에 전달할 수 있는 딕셔너리 형태로 결과 반환
        result = {
            "Bones": genBones,
            "Helpers": genHelpers,
            "Clavicle": inClavicle,
            "UpperArm": inUpperArm,
            "LiftScale": liftScale
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return result
