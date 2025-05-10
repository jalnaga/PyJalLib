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
from .bip import Bip

class GroinBone:
    """
    고간 부 본 관련 기능을 위한 클래스
    3DS Max에서 고간 부 본을 생성하고 관리하는 기능을 제공합니다.
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, bipService=None, boneService=None, helperService=None):
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
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        
        self.bipObj = None
        self.genBones = []
        self.genHelpers = []
    
    def create_bone(self, inPelvis, inLThighTwist, inRThighTwist, inPelvisWeight=40.0, inThighWeight=60.0):
        """
        고간 부 본을 생성하는 메소드.
        
        Args:
            inPelvis: Biped 객체
            inPelvisWeight: 골반 가중치 (기본값: 40.0)
            inThighWeight: 허벅지 가중치 (기본값: 60.0)
        
        Returns:
            성공 여부 (Boolean)
        """
        if rt.isValidNode(inPelvis) == False or rt.isValidNode(inLThighTwist) == False or rt.isValidNode(inRThighTwist) == False:
            rt.messageBox("There is no valid node.")
            return False
        
        groinBaseName = self.name.add_suffix_to_real_name(inPelvis.name, self.name._get_filtering_char(inPelvis.name) + "Groin")
        
        pelvisHelperName = self.name.replace_name_part("Type", groinBaseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        pelvisHelperName = self.name.replace_name_part("Index", pelvisHelperName, "00")
        pelvisHelper = self.helper.create_point(pelvisHelperName)
        pelvisHelper.transform = inPelvis.transform
        self.anim.rotate_local(pelvisHelper, 90, 0, 0)
        self.anim.rotate_local(pelvisHelper, 0, 0, -90)
        pelvisHelper.parent = inPelvis
        self.helper.set_shape_to_box(pelvisHelper)
        self.genHelpers.append(pelvisHelper)
        
        groinBoneName = self.name.replace_name_part("Index", groinBaseName, "00")
        groinBones = self.bone.create_simple_bone(3.0, groinBoneName, size=2)
        groinBones[0].transform = pelvisHelper.transform
        groinBones[0].parent = inPelvis
        for groinBone in groinBones:
            self.genBones.append(groinBone)
        
        self.const.assign_rot_const_multi(groinBones[0], [pelvisHelper, inLThighTwist, inRThighTwist])
        rotConst = self.const.get_rot_list_controller(groinBones[0])[1]
        rotConst.setWeight(1, inPelvisWeight)
        rotConst.setWeight(2, inThighWeight/2.0)
        rotConst.setWeight(3, inThighWeight/2.0)
        
        return True

class GroinBoneChain:
    """
    고간 부 본 체인(Groin Bone Chain) 관련 기능을 제공하는 클래스.
    GroinBone 클래스가 생성한 고간 부 본들과 헬퍼들을 관리하고 접근하는 인터페이스를 제공합니다.
    
    Examples:
        # GroinBone 클래스로 고간 본 생성 후 체인으로 관리하기
        groin_bone = GroinBone()
        biped_obj = rt.selection[0]  # 선택된 바이패드 객체
        
        # 고간 본 생성
        success = groin_bone.create_bone(biped_obj, 40.0, 60.0)
        if success:
            # 생성된 본과 헬퍼로 체인 생성
            chain = GroinBoneChain.from_groin_bone_result(
                groin_bone.genBones, 
                groin_bone.genHelpers,
                biped_obj,
                40.0,
                60.0
            )
            
            # 체인 가중치 업데이트
            chain.update_weights(35.0, 65.0)
            
            # 본과 헬퍼 이름 변경
            chain.rename_bones(prefix="Character_", suffix="_Groin")
            chain.rename_helpers(prefix="Character_", suffix="_Helper")
            
            # 현재 가중치 값 확인
            pelvis_w, thigh_w = chain.get_weights()
            print(f"Current weights: Pelvis={pelvis_w}, Thigh={thigh_w}")
            
            # 체인 삭제
            # chain.delete_all()
    """
    
    def __init__(self, bones=None, helpers=None, biped_obj=None):
        """
        클래스 초기화.
        
        Args:
            bones: 고간 부 본 체인을 구성하는 뼈대 배열 (기본값: None)
            helpers: 고간 부 본과 연관된 헬퍼 객체 배열 (기본값: None)
            biped_obj: 연관된 Biped 객체 (기본값: None)
        """
        self.bones = bones if bones else []
        self.helpers = helpers if helpers else []
        self.biped_obj = biped_obj
        self.pelvis_weight = 40.0  # 기본 골반 가중치
        self.thigh_weight = 60.0   # 기본 허벅지 가중치
    
    def is_empty(self):
        """
        체인이 비어있는지 확인
        
        Returns:
            본과 헬퍼가 모두 비어있으면 True, 아니면 False
        """
        return len(self.bones) == 0 and len(self.helpers) == 0
    
    def clear(self):
        """체인의 모든 본과 헬퍼 참조 제거"""
        self.bones = []
        self.helpers = []
    
    def delete_all(self):
        """
        체인의 모든 본과 헬퍼를 3ds Max 씬에서 삭제
        
        Returns:
            삭제 성공 여부 (boolean)
        """
        if self.is_empty():
            return False
            
        try:
            rt.delete(self.bones)
            rt.delete(self.helpers)
            self.clear()
            return True
        except:
            return False
    
    def update_weights(self, pelvis_weight=None, thigh_weight=None):
        """
        고간 부 본의 가중치 업데이트
        
        Args:
            pelvis_weight: 골반 가중치 (None인 경우 현재 값 유지)
            thigh_weight: 허벅지 가중치 (None인 경우 현재 값 유지)
            
        Returns:
            업데이트 성공 여부 (boolean)
        """
        if self.is_empty() or not self.biped_obj:
            return False
            
        # 새 가중치 설정
        if pelvis_weight is not None:
            self.pelvis_weight = pelvis_weight
        if thigh_weight is not None:
            self.thigh_weight = thigh_weight
            
        # 메인 본의 회전 제약 컨트롤러에서 가중치 업데이트
        try:
            main_bone = self.bones[0] if self.bones else None
            if main_bone and rt.classOf(main_bone.rotation.controller) == rt.List:
                rot_controller = main_bone.rotation.controller
                for i in range(1, rot_controller.count + 1):
                    if rt.classOf(rot_controller[i]) == rt.Rotation_List:
                        rot_list = rot_controller[i]
                        rot_list.setWeight(1, self.pelvis_weight)
                        rot_list.setWeight(2, self.thigh_weight/2.0)
                        rot_list.setWeight(3, self.thigh_weight/2.0)
                        return True
            return False
        except:
            return False
    
    def get_weights(self):
        """
        현재 설정된 가중치 값 가져오기
        
        Returns:
            (pelvis_weight, thigh_weight) 형태의 튜플
        """
        return (self.pelvis_weight, self.thigh_weight)
    
    @classmethod
    def from_groin_bone_result(cls, bones, helpers, biped_obj=None, pelvis_weight=40.0, thigh_weight=60.0):
        """
        GroinBone 클래스의 결과로부터 GroinBoneChain 인스턴스 생성
        
        Args:
            bones: GroinBone 클래스가 생성한 뼈대 배열
            helpers: GroinBone 클래스가 생성한 헬퍼 배열
            biped_obj: 연관된 Biped 객체 (기본값: None)
            pelvis_weight: 골반 가중치 (기본값: 40.0)
            thigh_weight: 허벅지 가중치 (기본값: 60.0)
            
        Returns:
            GroinBoneChain 인스턴스
        """
        chain = cls(bones, helpers, biped_obj)
        chain.pelvis_weight = pelvis_weight
        chain.thigh_weight = thigh_weight
        return chain


