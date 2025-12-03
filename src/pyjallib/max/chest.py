#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
가슴 본(Armpit) 모듈 - 3ds Max용 가슴 본 기능 제공
해부학적인 척추 위치에서 대흉근 쪽을 바라보는 헬퍼를 사용해서, 어깨 움직임에 따라 늘어나거사 수축하는 대흉근용 본을 만든다.
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint
from .align import Align

from .boneChain import BoneChain

class Chest:
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, alignService=None):
        """
        Chest 클래스의 주요 컴포넌트들을 초기화합니다.
        
        Args:
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
            animService: Anim 서비스 인스턴스 (제공되지 않으면 새로 생성)
            helperService: Helper 서비스 인스턴스 (제공되지 않으면 새로 생성)
            boneService: Bone 서비스 인스턴스 (제공되지 않으면 새로 생성)
            constraintService: Constraint 서비스 인스턴스 (제공되지 않으면 새로 생성)
            alignService: Align 서비스 인스턴스 (제공되지 않으면 새로 생성) 
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.align = alignService if alignService else Align()
        
        self.boneSize = 2.0
        
        self.genBones = []
        self.genHelpers = []
        
        self.pelvis = None
        self.spine = None
        self.neck = None
        self.autoClavicle = None
        self.upperArm = None
    
    def reset(self) -> None:
        """
        Chest 클래스의 주요 컴포넌트들을 초기화합니다.
        서비스가 아닌 클래스 자체의 작업 데이터를 초기화하는 함수입니다.
        """
        self.boneSize = 2.0
        
        self.genBones = []
        self.genHelpers = []
        
        self.pelvis = None
        self.spine = None
        self.neck = None
        self.autoClavicle = None
        self.upperArm = None
        
    def create_bones(self, inSpine: rt.Object, inNeck: rt.Object, inAutoClavicle: rt.Object, inUpperArm: rt.Object,
                     inSpineHeightScale: float = 0.33, inSpinePushScale: float = 0.5,
                     inFrontWeight: float = 60.0, inShoulderWeight: float = 40.0,
                     inChestMuscleHeightScale: float = 0.15, inShoulderPushScale: float = 0.25) -> BoneChain:
        """
        Chest 본들을 생성합니다.
        
        Args:
            inSpine: 몸통 본
            inNeck: 목 본
            inAutoClavicle: 자동 쇄골 본
            inUpperArm: 상완 본
            inSpineHeightScale: 척추 높이 비율 (기본값: 0.33)
            inSpinePushScale: 척추 앞뒤 밀림 비율 (기본값: 0.5)
            inFrontWeight: 가슴쪽 LookAt 웨이트 (기본값: 60.0)
            inShoulderWeight: 어깨쪽 LookAt 웨이트 (기본값: 40.0)
            inChestMuscleHeightScale: 대흉근 높이 비율 (기본값: 0.15)
            inShoulderPushScale: 어깨 밀림 비율 (기본값: 0.25)
        """
        
        if not rt.isValidNode(inSpine) or not rt.isValidNode(inNeck) or not rt.isValidNode(inAutoClavicle) or not rt.isValidNode(inUpperArm):
            return None
        
        self.spine = inSpine
        self.neck = inNeck
        self.autoClavicle = inAutoClavicle
        self.upperArm = inUpperArm
        
        genBones = []
        genHelpers = []
        
        chestName = self.name.replace_name_part("RealName", self.upperArm.name, "Chest")
        if self.name.get_name("RealName", self.upperArm.name)[0].islower():
            chestName = chestName.lower()
        
        # 몸통 길이 계산
        spineLength = rt.distance(self.spine, self.neck)
        
        # 몸통의 정면이 로컬 +Y 방향인지 -Y 방향인지 결정
        spineZAxisVec = self.spine.objectTransform.row3
        spineFacingDir = rt.normalize(self.neck.transform.position - self.spine.transform.position)
        spineFwdVec = rt.cross(spineZAxisVec, spineFacingDir)
        fwdDir = 1.0 if rt.dot(spineFwdVec, rt.normalize(self.spine.objectTransform.row2)) < 0.0 else -1.0
        
        # 뒤쪽 척추 룩엣 헬퍼 생성
        chestBackLookAtHelperName = self.name.replace_name_part("Type", chestName, self.name.get_name_part_value_by_description("Type", "LookAt"))
        chestBackLookAtHelper = self.helper.create_point(chestBackLookAtHelperName)
        self.helper.set_shape_to_axis(chestBackLookAtHelper)
        chestBackLookAtHelper.transform = self.spine.transform
        self.anim.move_local(chestBackLookAtHelper, spineLength*inSpineHeightScale, -fwdDir*spineLength*inSpinePushScale, 0.0)
        chestBackLookAtHelper.parent = self.spine
        
        # 앞쪽 갈비펴 타겟 헬퍼 생성
        chestFrontTargetHelperName = self.name.replace_name_part("Type", chestName, self.name.get_name_part_value_by_description("Type", "Target"))
        chestFrontTargetHelperName = self.name.replace_name_part("FrontBack", chestFrontTargetHelperName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        chestFrontTargetHelper = self.helper.create_point(chestFrontTargetHelperName)
        self.helper.set_shape_to_cross(chestFrontTargetHelper)
        chestFrontTargetHelper.transform  = self.spine.transform
        self.anim.move_local(chestFrontTargetHelper, spineLength*inSpineHeightScale, fwdDir*spineLength*inSpinePushScale, 0.0)
        chestFrontTargetHelper.parent = self.spine
        
        # 어깨 타겟 헬퍼 생성
        chestShoulderTargetHelperName = self.name.add_suffix_to_real_name(chestName, "Shoulder")
        if self.name.get_name("RealName", self.upperArm.name)[0].islower():
            chestShoulderTargetHelperName = chestShoulderTargetHelperName.lower()
        chestShoulderTargetHelperName = self.name.replace_name_part("Type", chestShoulderTargetHelperName, self.name.get_name_part_value_by_description("Type", "Target"))
        chestShoulderTargetHelper = self.helper.create_point(chestShoulderTargetHelperName)
        self.helper.set_shape_to_cross(chestShoulderTargetHelper)
        chestShoulderTargetHelper.transform = self.upperArm.transform
        chestShoulderTargetHelper.parent = self.autoClavicle
        
        # 뒤쪽 척추 룩엣 헬퍼에 룩엣 컨스트레인 설정
        chestBackLookAtConst = self.const.assign_lookat_multi(chestBackLookAtHelper, [chestFrontTargetHelper, chestShoulderTargetHelper])
        chestBackLookAtConst.upnode_world = False
        chestBackLookAtConst.pickUpNode = self.spine
        chestBackLookAtConst.lookat_vector_length = 0.0
        chestBackLookAtConst.SetWeight(1, inFrontWeight)
        chestBackLookAtConst.SetWeight(2, inShoulderWeight)
        
        # 갈비뼈 위를 흐르는 대흉근 헬퍼 생성
        chestFrontMuscleHelperName = self.name.replace_name_part("Type", chestName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        chestFrontMuscleHelper = self.helper.create_point(chestFrontMuscleHelperName)
        self.helper.set_shape_to_box(chestFrontMuscleHelper)
        chestFrontMuscleHelper.transform = chestBackLookAtHelper.transform
        self.anim.move_local(chestFrontMuscleHelper, spineLength, -spineLength*inChestMuscleHeightScale, 0.0)
        chestFrontMuscleHelper.parent = chestBackLookAtHelper
        
        # 몸통쪽 대흉근 본 생성
        chestInBoneName = self.name.replace_name_part("InOut", chestName, self.name.get_name_part_value_by_description("InOut", "In"))
        chestInBone = self.bone.create_nub_bone(chestInBoneName, self.boneSize)
        chestInBone.transform = chestFrontTargetHelper.transform
        chestInBone.parent = self.spine
        chestInBoneLookAtConst = self.const.assign_lookat(chestInBone, chestFrontMuscleHelper)
        chestInBoneLookAtConst.upnode_world = False
        chestInBoneLookAtConst.pickUpNode = self.spine
        chestInBoneLookAtConst.lookat_vector_length = 0.0
        chestInBoneLookAtConst.StoUP_axis = 1
        chestInBoneLookAtConst.upnode_axis = 1
        
        # 어깨쪽 대흉근 본 생성
        chestOutBoneName = self.name.replace_name_part("InOut", chestName, self.name.get_name_part_value_by_description("InOut", "Out"))
        chestOutBone = self.bone.create_nub_bone(chestOutBoneName, self.boneSize)
        chestOutBone.transform = self.upperArm.transform
        
        upperArmZAxisVec = self.upperArm.objectTransform.row3
        upperArmFacingDir = rt.normalize(self.upperArm.transform.position - self.autoClavicle.transform.position)
        upperArmFwdVec = rt.cross(upperArmZAxisVec, upperArmFacingDir)
        fwdDir = 1.0 if rt.dot(upperArmFwdVec, rt.normalize(self.upperArm.objectTransform.row2)) < 0.0 else -1.0
        self.anim.move_local(chestOutBone, 0.0, fwdDir*spineLength*inShoulderPushScale, 0.0)
        
        chestOutBone.parent = self.autoClavicle
        chestOutBoneLookAtConst = self.const.assign_lookat(chestOutBone, chestFrontMuscleHelper)
        chestOutBoneLookAtConst.upnode_world = False
        chestOutBoneLookAtConst.pickUpNode = self.autoClavicle
        chestOutBoneLookAtConst.lookat_vector_length = 0.0
        chestOutBoneLookAtConst.StoUP_axis = 1
        chestOutBoneLookAtConst.upnode_axis = 1
        
        genBones.append(chestInBone)
        genBones.append(chestOutBone)
        genHelpers.append(chestBackLookAtHelper)
        genHelpers.append(chestFrontTargetHelper)
        genHelpers.append(chestShoulderTargetHelper)
        genHelpers.append(chestFrontMuscleHelper)
        
        self.genBones = genBones
        self.genHelpers = genHelpers
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers,
            "SourceBones": [self.spine, self.neck, self.autoClavicle, self.upperArm],
            "Parameters": [inSpineHeightScale, inSpinePushScale, inFrontWeight, inShoulderWeight, inChestMuscleHeightScale, inShoulderPushScale]
        }
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """
        Chest 본들을 기존 BoneChain에서 재생성합니다.
        
        Args:
            inBoneChain: 기존 BoneChain
            
        Returns:
            BoneChain: 업데이트된 BoneChain 객체 또는 실패 시 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 4 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or not rt.isValidNode(sourceBones[2]) or not rt.isValidNode(sourceBones[3]):
            return None
        
        spine = sourceBones[0]
        neck = sourceBones[1]
        autoClavicle = sourceBones[2]
        upperArm = sourceBones[3]
        
        # 파라미터 추출
        if len(parameters) >= 6:
            spineHeightScale = parameters[0]
            spinePushScale = parameters[1]
            frontWeight = parameters[2]
            shoulderWeight = parameters[3]
            chestMuscleHeightScale = parameters[4]
            shoulderPushScale = parameters[5]
        else:
            # 기본값
            spineHeightScale = 0.33
            spinePushScale = 0.5
            frontWeight = 60.0
            shoulderWeight = 40.0
            chestMuscleHeightScale = 0.15
            shoulderPushScale = 0.25
        
        return self.create_bones(spine, neck, autoClavicle, upperArm,
                                 spineHeightScale, spinePushScale,
                                 frontWeight, shoulderWeight,
                                 chestMuscleHeightScale, shoulderPushScale)