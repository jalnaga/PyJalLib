#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고간 부 본 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint

from .boneChain import BoneChain

class GroinBone:
    """
    고간 부 본 관련 기능을 위한 클래스
    3DS Max에서 고간 부 본을 생성하고 관리하는 기능을 제공합니다.
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            twistBoneService: 트위스트 본 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
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
        서비스가 아닌 클래스 자체의 작업 데이터를 초기화하는 함수입니다.
        
        Returns:
            self: 메소드 체이닝을 위한 자기 자신 반환
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
        고간 부 본을 생성하는 메소드.
        
        Args:
            inPelvis: Biped 객체
            inLThighTwist: 왼쪽 허벅지 트위스트 본
            inRThighTwist: 오른쪽 허벅지 트위스트 본
            inPelvisWeight: 골반 가중치 (기본값: 40.0)
            inThighWeight: 허벅지 가중치 (기본값: 60.0)
        
        Returns:
            BoneChain: 생성된 고간 부 본 체인 객체 또는 실패 시 False
        """
        
        if rt.isValidNode(inPelvis) == False or rt.isValidNode(inLThighTwist) == False or rt.isValidNode(inRThighTwist) == False:
            rt.messageBox("There is no valid node.")
            return False
        
        groinName = "Groin"
        if inPelvis.name[0].islower():
            groinName = groinName.lower()
        
        groinBaseName = self.name.replace_name_part("RealName", inLThighTwist.name, groinName)
        
        pelvisHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelperName = self.name.replace_name_part("Index", pelvisHelperName, "0")
        pelvisHelperName = self.name.remove_name_part("Side", pelvisHelperName)
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        pelvisHelper.transform = inPelvis.transform
        self.anim.rotate_local(pelvisHelper, 0.0, 0.0, -180.0)
        pelvisHelper.parent = inPelvis
        self.helper.set_shape_to_box(pelvisHelper)
        
        lThighTwistHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        lThighTwistHelperName = self.name.replace_name_part("Side", lThighTwistHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        lThighTwistHelperName = self.name.replace_name_part("Index", lThighTwistHelperName, "0")
        lThighTwistHelper = self.helper.create_point(lThighTwistHelperName)
        lThighTwistHelper.transform = pelvisHelper.transform
        lThighTwistHelper.position = inLThighTwist.position
        lThighTwistHelper.parent = inLThighTwist
        self.helper.set_shape_to_box(lThighTwistHelper)
        
        rThighTwistHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        rThighTwistHelperName = self.name.replace_name_part("Side", rThighTwistHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        rThighTwistHelperName = self.name.replace_name_part("Index", rThighTwistHelperName, "0")
        rThighTwistHelper = self.helper.create_point(rThighTwistHelperName)
        rThighTwistHelper.transform = pelvisHelper.transform
        rThighTwistHelper.position = inRThighTwist.position
        rThighTwistHelper.parent = inRThighTwist
        self.helper.set_shape_to_box(rThighTwistHelper)
        
        groinBoneName = self.name.replace_name_part("Index", groinBaseName, "0")
        groinBoneName = self.name.remove_name_part("Side", groinBoneName)
        groinBone = self.bone.create_nub_bone(groinBoneName, 2)
        groinBone.name = groinBoneName
        groinBone.transform = pelvisHelper.transform
        groinBone.parent = inPelvis
        
        self.const.assign_rot_const_multi(groinBone, [pelvisHelper, lThighTwistHelper, rThighTwistHelper])
        rotConst = self.const.get_rot_list_controller(groinBone)[1]
        rotConst.setWeight(1, inPelvisWeight)
        rotConst.setWeight(2, inThighWeight/2.0)
        rotConst.setWeight(3, inThighWeight/2.0)
        
        # 결과를 멤버 변수에 저장
        self.pelvis = inPelvis
        self.lThighTwist = inLThighTwist
        self.rThighTwist = inRThighTwist
        self.bones = [groinBone]
        self.helpers = [pelvisHelper, lThighTwistHelper, rThighTwistHelper]
        self.pelvisWeight = inPelvisWeight
        self.thighWeight = inThighWeight
        
        # BoneChain 구조에 맞는 결과 딕셔너리 생성
        result = {
            "Bones": [groinBone],
            "Helpers": [pelvisHelper, lThighTwistHelper, rThighTwistHelper],
            "SourceBones": [inPelvis, inLThighTwist, inRThighTwist],
            "Parameters": [inPelvisWeight, inThighWeight]
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        # BoneChain 객체 반환
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """
        기존 BoneChain 객체에서 고간 부 본을 생성합니다.
        기존 설정을 복원하거나 저장된 데이터에서 고간 부 본 셋업을 재생성할 때 사용합니다.
        
        Args:
            inBoneChain (BoneChain): 고간 부 본 정보를 포함한 BoneChain 객체
        
        Returns:
            BoneChain: 업데이트된 BoneChain 객체 또는 실패 시 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        # 기존 객체 삭제
        inBoneChain.delete()
            
        # BoneChain에서 필요한 정보 추출
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        # 필수 소스 본 확인 (최소 3개: 골반, 좌허벅지트위스트, 우허벅지트위스트)
        if len(sourceBones) < 3 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or not rt.isValidNode(sourceBones[2]):
            return None
            
        # 파라미터 가져오기 (또는 기본값 사용)
        pelvisWeight = parameters[0] if len(parameters) > 0 else 40.0
        thighWeight = parameters[1] if len(parameters) > 1 else 60.0
        
        # 새로운 고간 부 본 생성
        inPelvis = sourceBones[0]
        inLThighTwist = sourceBones[1]
        inRThighTwist = sourceBones[2]
        
        return self.create_bone(inPelvis, inLThighTwist, inRThighTwist, pelvisWeight, thighWeight)
