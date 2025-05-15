#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# Hip 모듈

3ds Max에서 고관절(hip)을 자동화하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 허벅지 회전 기반 고관절 본 생성
- 골반과 허벅지 가중치 기반 회전 제약
- 포지션 스크립트 기반 자동 위치 이동

## 구현 정보
- 원본 MAXScript의 hip.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint


class Hip:
    """
    # Hip 클래스
    
    3ds Max에서 고관절(hip) 관련 기능을 제공하는 클래스입니다.
    
    ## 주요 기능
    - 골반과 허벅지 사이의 고관절 본 생성
    - 골반과 허벅지 사이의 가중치 기반 회전 제약
    - 허벅지 회전에 따른 자동 위치 이동 적용
    - 포지션 스크립트를 통한 고관절 위치 자동화
    
    ## 구현 정보
    - MAXScript의 _Hip 구조체를 Python 클래스로 재구현
    - 다양한 서비스 클래스를 의존성 주입으로 활용
    
    ## 사용 예시
    ```python
    # Hip 객체 생성
    hip = Hip()
    
    # 고관절 본 생성
    result = hip.create_bone(pelvis, thigh, thighTwist, calf)
    
    # 결과에서 생성된 본과 헬퍼 접근
    hip_bone = result["Bones"][0]
    hip_helpers = result["Helpers"]
    ```
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None):
        """
        Hip 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - animService (Anim, optional): 애니메이션 서비스 (기본값: None, 새로 생성)
        - helperService (Helper, optional): 헬퍼 객체 서비스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): 뼈대 서비스 (기본값: None, 새로 생성)
        - constraintService (Constraint, optional): 제약 서비스 (기본값: None, 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.const = constraintService if constraintService else Constraint(nameService=self.name, helperService=self.helper)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim, helperService=self.helper, constraintService=self.const)
        
        # 기본 속성 초기화
        self.pelvisWeight = 0.6
        self.thighWeight = 0.4
        self.pushAmount = 10
        
        self.pelvis = None
        self.thigh = None
        self.thighTwist = None
        self.calf = None
        
        self.pelvisHelper = None
        self.thighHelper = None
        self.thighTwistHelper = None
        self.thighRotHelper = None
        self.thighPosHelper = None
        self.thighRotRootHelper = None
        
        self.helpers = []
        self.bones = []
        
        self.posScriptExpression = (
            "localLimbTm = limb.transform * inverse limbParent.transform\n"
            "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "eulerRot = (quatToEuler q order:5)\n"
            "swizzledRot = (eulerAngles eulerRot.y eulerRot.z eulerRot.x)\n"
            "\n"
            "axis = [0,0,1]\n"
            "\n"
            "saturatedTwistZ = (swizzledRot.x*axis.x + swizzledRot.y*axis.y + swizzledRot.z*axis.z)/180.0\n"
            "pushScaleY = amax 0.0 saturatedTwistZ\n"
            "\n"
            "axis = [0,1,0]\n"
            "saturatedTwistY = (swizzledRot.x*axis.x + swizzledRot.y*axis.y + swizzledRot.z*axis.z)/180.0\n"
            "pushScaleZ = amax 0.0 saturatedTwistY\n"
            "\n"
            "\n"
            "[0, pushAmount * pushScaleY, -pushAmount * pushScaleZ]\n"
        )
        
    def reset(self):
        """
        클래스의 주요 컴포넌트들을 초기화합니다.
        
        작업 결과를 저장하는 멤버 변수들을 초기 상태로 되돌립니다.
        서비스 객체(name, anim 등)는 유지합니다.
        
        ## Returns
        - self: 메소드 체이닝을 위한 자기 자신 반환
        """
        self.pelvisWeight = 0.6
        self.thighWeight = 0.4
        self.pushAmount = 10
        
        self.pelvis = None
        self.thigh = None
        self.thighTwist = None
        self.calf = None
        
        self.pelvisHelper = None
        self.thighHelper = None
        self.thighTwistHelper = None
        self.thighRotHelper = None
        self.thighPosHelper = None
        self.thighRotRootHelper = None
        
        self.helpers = []
        self.bones = []
        
        return self
    
    def create_helper(self, inPelvis, inThigh, inThighTwist):
        """
        고관절 시스템에 필요한 헬퍼 객체들을 생성합니다.
        
        ## Parameters
        - inPelvis (MaxObject): 골반 뼈대 객체
        - inThigh (MaxObject): 허벅지 뼈대 객체
        - inThighTwist (MaxObject): 허벅지 트위스트 뼈대 객체
            
        ## Returns
        - bool: 헬퍼 생성 성공 여부
        
        ## 동작 방식
        1. 골반 헬퍼, 허벅지 헬퍼, 허벅지 트위스트 헬퍼 생성
        2. 회전 및 위치 헬퍼 생성
        3. 각 헬퍼를 적절한 부모에 연결
        4. 이름 규칙에 따라 헬퍼 이름 설정
        """
        if not rt.isValidNode(inPelvis) or not rt.isValidNode(inThigh) or not rt.isValidNode(inThighTwist):
            return False
        
        self.pelvis = inPelvis
        self.thigh = inThigh
        self.thighTwist = inThighTwist
        
        filteringChar = self.name._get_filtering_char(inThigh.name)
        isLower = inThigh.name[0].islower()
        
        pelvisHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_RealName(inPelvis.name)+filteringChar+"Hip")
        pelvisHelperName = self.name.replace_name_part("Type", pelvisHelperName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        rt.setProperty(pelvisHelper, "transform", inThigh.transform)
        pelvisHelper.parent = inPelvis
        
        tihgTwistHeleprName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_RealName(inThighTwist.name)+filteringChar+"Hip")
        tihgTwistHeleprName = self.name.replace_name_part("Type", tihgTwistHeleprName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        thighTwistHelper = self.helper.create_point(tihgTwistHeleprName)
        rt.setProperty(thighTwistHelper, "transform", inThighTwist.transform)
        thighTwistHelper.parent = inThighTwist
        
        tihghRotHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_RealName(inThigh.name)+filteringChar+"Hip")
        tihghRotHelperName = self.name.replace_name_part("Type", tihghRotHelperName, self.name.get_name_part_value_by_description("Type", "Rotation"))
        thighRotHelper = self.helper.create_point(tihghRotHelperName)
        rt.setProperty(thighRotHelper, "transform", inThighTwist.transform)
        thighRotHelper.parent = inThigh
        
        thighPosHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_RealName(inThigh.name)+filteringChar+"Hip")
        thighPosHelperName = self.name.replace_name_part("Type", thighPosHelperName, self.name.get_name_part_value_by_description("Type", "Position"))
        thighPosHelper = self.helper.create_point(thighPosHelperName)
        rt.setProperty(thighPosHelper, "transform", inThighTwist.transform)
        thighPosHelper.parent = thighRotHelper
        
        thighRotRootHelperName = self.name.replace_name_part("RealName", inThigh.name, self.name.get_RealName(inThigh.name)+filteringChar+"Hip")
        thighRotRootHelperName = self.name.replace_name_part("Type", thighRotRootHelperName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        thighRotRootHelper = self.helper.create_point(thighRotRootHelperName)
        rt.setProperty(thighRotRootHelper, "transform", thighRotHelper.transform)
        thighRotRootHelper.parent = inThighTwist
        
        if isLower:
            pelvisHelper.name = pelvisHelper.name.lower()
            thighTwistHelper.name = thighTwistHelper.name.lower()
            thighRotHelper.name = thighRotHelper.name.lower()
            thighPosHelper.name = thighPosHelper.name.lower()
            thighRotRootHelper.name = thighRotRootHelper.name.lower()
            
        self.pelvisHelper = pelvisHelper
        self.thighTwistHelper = thighTwistHelper
        self.thighRotHelper = thighRotHelper
        self.thighPosHelper = thighPosHelper
        self.thighRotRootHelper = thighRotRootHelper
        
        self.helpers.append(pelvisHelper)
        self.helpers.append(thighTwistHelper)
        self.helpers.append(thighRotHelper)
        self.helpers.append(thighPosHelper)
        self.helpers.append(thighRotRootHelper)
    
    def assing_constraint(self, inCalf, inPelvisWeight=0.6, inThighWeight=0.4, inPushAmount=5.0):
        """
        고관절 시스템에 제약 조건을 할당합니다.
        
        ## Parameters
        - inCalf (MaxObject): 종아리 뼈대 객체
        - inPelvisWeight (float): 골반 가중치 (기본값: 0.6)
        - inThighWeight (float): 허벅지 가중치 (기본값: 0.4)
        - inPushAmount (float): 위치 이동량 (기본값: 5.0)
        
        ## 동작 방식
        1. 종아리 뼈대 방향에 따라 방향성 결정
        2. 회전 제약에 골반과 허벅지 트위스트 가중치 설정
        3. 위치 스크립트 컨트롤러에 스크립트 표현식 할당
        4. 노드와 상수값을 스크립트 컨트롤러에 연결
        """
        self.calf = inCalf
        self.pelvisWeight = inPelvisWeight
        self.thighWeight = inThighWeight
        self.pushAmount = rt.Float(inPushAmount)
        
        facingDirVec = self.calf.transform.position - self.thigh.transform.position
        inObjXAxisVec = self.thigh.objectTransform.row1
        distanceDir = -1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else 1.0
        
        rotConst = self.const.assign_rot_const_multi(self.thighRotHelper, [self.pelvisHelper, self.thighTwistHelper])
        rotConst.setWeight(1, self.pelvisWeight * 100.0)
        rotConst.setWeight(2, self.thighWeight * 100.0)
        
        localRotRefTm = self.thighRotHelper.transform * rt.inverse(self.thighRotRootHelper.transform)
        posConst = self.const.assign_pos_script_controller(self.thighPosHelper)
        posConst.addNode("limb", self.thighRotHelper)
        posConst.addNode("limbParent", self.thighRotRootHelper)
        posConst.addConstant("localRotRefTm", localRotRefTm)
        posConst.addConstant("pushAmount", self.pushAmount*distanceDir)
        posConst.setExpression(self.posScriptExpression)
        posConst.update()
        
    def create_bone(self, inPelvis, inThigh, inThighTwist, inCalf, pushAmount=5.0, inPelvisWeight=0.6, inThighWeight=0.4):
        """
        골반과 허벅지 사이에 고관절 본을 생성합니다.
        
        ## Parameters
        - inPelvis (MaxObject): 골반 뼈대 객체
        - inThigh (MaxObject): 허벅지 뼈대 객체
        - inThighTwist (MaxObject): 허벅지 트위스트 뼈대 객체
        - inCalf (MaxObject): 종아리 뼈대 객체
        - pushAmount (float): 위치 이동량 (기본값: 5.0)
        - inPelvisWeight (float): 골반 가중치 (기본값: 0.6)
        - inThighWeight (float): 허벅지 가중치 (기본값: 0.4)
            
        ## Returns
        - dict: 생성된 고관절 시스템 정보를 담은 딕셔너리
            - "Pelvis": 골반 객체 참조
            - "Thigh": 허벅지 객체 참조
            - "ThighTwist": 허벅지 트위스트 객체 참조
            - "Bones": 생성된 뼈대 객체 배열
            - "Helpers": 생성된 헬퍼 객체 배열
            - "PelvisWeight": 적용된 골반 가중치
            - "ThighWeight": 적용된 허벅지 가중치
            - "PushAmount": 적용된 위치 이동량
        
        ## 동작 방식
        1. 헬퍼 객체들 생성
        2. 제약 조건 할당
        3. Hip 본 생성 및 설정
        4. 회전 및 위치 제약 적용
        5. 결과 저장 및 반환
        """
        if not rt.isValidNode(inPelvis) or not rt.isValidNode(inThigh) or not rt.isValidNode(inThighTwist):
            return False
        
        self.create_helper(inPelvis, inThigh, inThighTwist)
        self.assing_constraint(inCalf, inPelvisWeight, inThighWeight, inPushAmount=pushAmount)
        
        isLower = inThigh.name[0].islower()
        hipBoneName = self.name.replace_name_part("RealName", inThigh.name, "Hip")
        hipBone = self.bone.create_nub_bone(hipBoneName, 2)
        hipBone.name = self.name.remove_name_part("Nub", hipBone.name)
        if isLower:
            hipBone.name = hipBone.name.lower()
        
        rt.setProperty(hipBone, "transform", inThighTwist.transform)
        hipBone.parent = inThigh
        
        self.const.assign_rot_const(hipBone, self.thighRotHelper)
        self.const.assign_pos_const(hipBone, self.thighPosHelper)
        
        self.bones.append(hipBone)
        
        # 결과를 딕셔너리 형태로 준비
        result = {
            "Pelvis": inPelvis,
            "Thigh": inThigh,
            "ThighTwist": inThighTwist,
            "Bones": self.bones,
            "Helpers": self.helpers,
            "PelvisWeight": inPelvisWeight,
            "ThighWeight": inThighWeight,
            "PushAmount": pushAmount
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return result

