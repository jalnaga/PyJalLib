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

class Belt:
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
        self.spine02 = None
        self.bones = []
        self.helpers = []
        self.RotationScale = 0.5

        self.rotScriptExpression = (
            "localNodeTm = node.transform * inverse nodeParent.transform\n"
            "localDeltaTm = localNodeTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "scaledQ = slerp identityQ q rotScale\n"
            "\n"
            "scaledQ\n"
        )
    
    def reset(self):
        """
        클래스의 주요 컴포넌트들을 초기화합니다.
        서비스가 아닌 클래스 자체의 작업 데이터를 초기화하는 함수입니다.
        
        Returns:
            self: 메소드 체이닝을 위한 자기 자신 반환
        """
        self.pelvis = None
        self.spine02 = None
        self.bones = []
        self.helpers = []
        self.RotationScale = 0.5
        
        return self
    
    def create_bone(self, inPelvis, inSpine02, inRotationScale=0.5):
        """
        벨트 본을 생성하는 메소드.
        
        Args:
            inPelvis: Biped 객체
            inSpine02: spine_02 본
            inRotationScale: 회전 가중치 (기본값: 0.5)
        
        Returns:
            BoneChain: 생성된 벨트 본 체인 객체 또는 실패 시 False
        """
        
        if rt.isValidNode(inPelvis) == False or rt.isValidNode(inSpine02) == False:
            rt.messageBox("There is no valid node.")
            return False
        
        BeltRealName = "Belt"
        if self.name.get_name("RealName", inPelvis.name)[0].islower():
            BeltName = "beltRoot"
            DumBeltName = "dum_belt"
            LatBeltName = "lat_belt"
        else:
            BeltName = self.name.replace_name_part("RealName", inPelvis.name, "BeltRoot")
            BeltName = self.name.replace_name_part("Base", BeltName, self.name.get_name_part_value_by_description("Base", "Biped"))

            DumBeltName = self.name.replace_name_part("RealName", inPelvis.name, BeltRealName)
            DumBeltName = self.name.replace_name_part("Type", DumBeltName, self.name.get_name_part_value_by_description("Type", "Dummy"))

            LatBeltName = self.name.replace_name_part("RealName", inPelvis.name, BeltRealName)
            LatBeltName = self.name.replace_name_part("Type", LatBeltName, self.name.get_name_part_value_by_description("Type", "LookAt"))

        LatBeltHelper = self.helper.create_point(LatBeltName)
        LatBeltHelper.transform = inPelvis.transform
        LatBeltHelper.parent = inPelvis
        self.helper.set_shape_to_axis(LatBeltHelper)

        LookAtConst = self.const.assign_lookat(LatBeltHelper, inSpine02)
        LookAtConst.upnode_world = False
        LookAtConst.pickUpNode = inPelvis

        DumBeltHelper = self.helper.create_point(DumBeltName)
        DumBeltHelper.transform = LatBeltHelper.transform
        DumBeltHelper.parent = inPelvis
        self.helper.set_shape_to_box(DumBeltHelper)
        
        BeltBone = self.bone.create_nub_bone(BeltName, 2)
        BeltBone.name = BeltName
        BeltBone.transform = LatBeltHelper.transform
        BeltBone.parent = inPelvis

        beltBoneRotListController = self.const.assign_rot_list(BeltBone)
        beltBoneController = rt.Rotation_Script()
        beltBoneController.addConstant("identityQ", rt.quat(0, 0, 0, 1))
        beltBoneController.addConstant("localRotRefTm", rt.matrix3(rt.Point3(1,0,0), rt.Point3(0,1,0), rt.Point3(0,0,1), rt.Point3(0,0,0)))
        beltBoneController.addNode("node", LatBeltHelper)
        beltBoneController.addNode("nodeParent", DumBeltHelper)
        beltBoneController.addConstant("rotScale", inRotationScale)
        beltBoneController.setExpression(self.rotScriptExpression)        
        beltBoneController.update()

        rt.setPropertyController(beltBoneRotListController, "Available", beltBoneController)
        
        if self.bone.is_skin_bone(inPelvis) or self.bone.is_skin_bone(inSpine02):
            for item in self.bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in self.helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 멤버 변수에 저장
        self.pelvis = inPelvis
        self.spine02 = inSpine02
        self.bones = [BeltBone]
        self.helpers = [LatBeltHelper, DumBeltHelper]
        self.RotationScale = inRotationScale
        
        # BoneChain 구조에 맞는 결과 딕셔너리 생성
        result = {
            "Bones": [BeltBone],
            "Helpers": [LatBeltHelper, DumBeltHelper],
            "SourceBones": [inPelvis, inSpine02],
            "Parameters": [inRotationScale]
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        rt.redrawViews()
        
        # BoneChain 객체 반환
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """
        기존 BoneChain 객체에서 벨트 본을 생성합니다.
        기존 설정을 복원하거나 저장된 데이터에서 벨트 본 셋업을 재생성할 때 사용합니다.
        
        Args:
            inBoneChain (BoneChain): 벨트 본 정보를 포함한 BoneChain 객체
        
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
        
        # 필수 소스 본 확인 (최소 2개: 골반, 스파인02)
        if len(sourceBones) < 2 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]):
            return None
            
        # 파라미터 가져오기 (또는 기본값 사용)
        RotationScale = parameters[0] if len(parameters) > 0 else 0.5
        
        # 새로운 고간 부 본 생성
        inPelvis = sourceBones[0]
        inSpine02 = sourceBones[1]
        
        return self.create_bone(inPelvis, inSpine02, inRotationScale=RotationScale)
