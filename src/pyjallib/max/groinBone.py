#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 고간 부 본(GroinBone) 모듈

3ds Max에서 고간 부분의 뼈대를 생성하고 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 골반과 허벅지 트위스트 본 사이의 제약 기반 고간 본 생성
- 가중치 기반 자동 회전 제어
- 골반과 허벅지 사이의 중간 위치 보간

## 구현 정보
- pymxs 모듈을 통한 3ds Max API 접근
- 제약 컨트롤러를 활용한 자동 회전 처리
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint

class GroinBone:
    """
    # GroinBone 클래스
    
    3DS Max에서 고간 부 본(groin bone)을 생성하고 관리하는 기능을 제공합니다.
    
    ## 주요 기능
    - 골반과 좌우 허벅지 트위스트 본 사이에 중간 회전을 적용한 고간 본 생성
    - 골반과 허벅지 트위스트 본에 가중치 기반 회전 제약 설정
    - 이름 규칙에 따른 자동 명명 및 계층 구조 설정
    
    ## 구현 정보
    - 회전 제약 컨트롤러를 활용한 자동 회전 계산
    - 헬퍼 객체를 사용한 제약 적용 지점 설정
    - 가중치 조절을 통한 골반/허벅지 회전 영향도 조정
    
    ## 사용 예시
    ```python
    # GroinBone 객체 생성
    groin_bone = GroinBone()
    
    # 골반과 좌우 허벅지 트위스트 본으로 고간 본 생성
    result = groin_bone.create_bone(pelvis, lThighTwist, rThighTwist)
    
    # 생성된 뼈대 객체에 접근
    groin_bone = result["Bones"][0]
    ```
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """
        GroinBone 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - animService (Anim, optional): 애니메이션 서비스 (기본값: None, 새로 생성)
        - constraintService (Constraint, optional): 제약 서비스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): 뼈대 서비스 (기본값: None, 새로 생성)
        - helperService (Helper, optional): 헬퍼 객체 서비스 (기본값: None, 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        
        # 초기화된 결과를 저장할 변수들
        self.pelvis = None
        self.lThighTwist = None
        self.rThighTwist = None
        self.bones = []
        self.helpers = []
        self.pelvisWeight = 40.0
        self.thighWeight = 60.0
    
    def reset(self):
        """
        클래스의 주요 컴포넌트들을 초기화합니다.
        
        작업 결과를 저장하는 멤버 변수들을 초기 상태로 되돌립니다.
        서비스 객체(name, anim 등)는 유지합니다.
        
        ## Returns
        - self: 메소드 체이닝을 위한 자기 자신 반환
        """
        self.pelvis = None
        self.lThighTwist = None
        self.rThighTwist = None
        self.bones = []
        self.helpers = []
        self.pelvisWeight = 40.0
        self.thighWeight = 60.0
        
        return self
    
    def create_bone(self, inPelvis, inLThighTwist, inRThighTwist, inPelvisWeight=40.0, inThighWeight=60.0):
        """
        골반과 허벅지 트위스트 본 사이에 고간 부 본을 생성합니다.
        
        ## Parameters
        - inPelvis (MaxObject): 골반 뼈대 객체
        - inLThighTwist (MaxObject): 왼쪽 허벅지 트위스트 본 객체
        - inRThighTwist (MaxObject): 오른쪽 허벅지 트위스트 본 객체
        - inPelvisWeight (float): 골반 가중치 (기본값: 40.0)
        - inThighWeight (float): 허벅지 가중치 (기본값: 60.0)
        
        ## Returns
        - dict: 생성된 고간 부 본 시스템 정보를 담은 딕셔너리
            - "Pelvis": 골반 객체 참조
            - "LThighTwist": 왼쪽 허벅지 트위스트 본 참조
            - "RThighTwist": 오른쪽 허벅지 트위스트 본 참조
            - "Bones": 생성된 뼈대 객체 배열
            - "Helpers": 생성된 헬퍼 객체 배열
            - "PelvisWeight": 적용된 골반 가중치
            - "ThighWeight": 적용된 허벅지 가중치
        
        ## 동작 방식
        1. 골반, 허벅지 트위스트 본의 유효성 검사
        2. 헬퍼 객체 생성 및 배치
        3. 고간 부 본 생성 및 위치 조정
        4. 회전 제약 설정 및 가중치 조정
        5. 결과 저장 및 반환
        """
        returnVal = {
            "Pelvis": None,
            "LThighTwist": None,
            "RThighTwist": None,
            "Bones": [],
            "Helpers": [],
            "PelvisWeight": inPelvisWeight,
            "ThighWeight": inThighWeight
        }
        if rt.isValidNode(inPelvis) == False or rt.isValidNode(inLThighTwist) == False or rt.isValidNode(inRThighTwist) == False:
            rt.messageBox("There is no valid node.")
            return False
        
        groinName = "Groin"
        if inPelvis.name[0].islower():
            groinName = groinName.lower()
        
        groinBaseName = self.name.add_suffix_to_real_name(inPelvis.name, self.name._get_filtering_char(inLThighTwist.name) + groinName)
        
        pelvisHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelperName = self.name.replace_name_part("Index", pelvisHelperName, "00")
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        pelvisHelper.transform = inPelvis.transform
        self.anim.rotate_local(pelvisHelper, 0.0, 0.0, -180.0)
        pelvisHelper.parent = inPelvis
        self.helper.set_shape_to_box(pelvisHelper)
        
        lThighTwistHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        lThighTwistHelperName = self.name.replace_name_part("Side", lThighTwistHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        lThighTwistHelperName = self.name.replace_name_part("Index", lThighTwistHelperName, "00")
        lThighTwistHelper = self.helper.create_point(lThighTwistHelperName)
        lThighTwistHelper.transform = pelvisHelper.transform
        lThighTwistHelper.position = inLThighTwist.position
        lThighTwistHelper.parent = inLThighTwist
        self.helper.set_shape_to_box(lThighTwistHelper)
        
        rThighTwistHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        rThighTwistHelperName = self.name.replace_name_part("Side", rThighTwistHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        rThighTwistHelperName = self.name.replace_name_part("Index", rThighTwistHelperName, "00")
        rThighTwistHelper = self.helper.create_point(rThighTwistHelperName)
        rThighTwistHelper.transform = pelvisHelper.transform
        rThighTwistHelper.position = inRThighTwist.position
        rThighTwistHelper.parent = inRThighTwist
        self.helper.set_shape_to_box(rThighTwistHelper)
        
        groinBoneName = self.name.replace_name_part("Index", groinBaseName, "00")
        groinBones = self.bone.create_simple_bone(3.0, groinBoneName, size=2)
        groinBones[0].transform = pelvisHelper.transform
        groinBones[0].parent = inPelvis
        
        self.const.assign_rot_const_multi(groinBones[0], [pelvisHelper, lThighTwistHelper, rThighTwistHelper])
        rotConst = self.const.get_rot_list_controller(groinBones[0])[1]
        rotConst.setWeight(1, inPelvisWeight)
        rotConst.setWeight(2, inThighWeight/2.0)
        rotConst.setWeight(3, inThighWeight/2.0)
        
        # 결과를 멤버 변수에 저장
        self.pelvis = inPelvis
        self.lThighTwist = inLThighTwist
        self.rThighTwist = inRThighTwist
        self.bones = groinBones
        self.helpers = [pelvisHelper, lThighTwistHelper, rThighTwistHelper]
        self.pelvisWeight = inPelvisWeight
        self.thighWeight = inThighWeight
        
        returnVal["Pelvis"] = inPelvis
        returnVal["LThighTwist"] = inLThighTwist
        returnVal["RThighTwist"] = inRThighTwist
        returnVal["Bones"] = groinBones
        returnVal["Helpers"] = [pelvisHelper, lThighTwistHelper, rThighTwistHelper]
        returnVal["PelvisWeight"] = inPelvisWeight
        returnVal["ThighWeight"] = inThighWeight
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return returnVal
