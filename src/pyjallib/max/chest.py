#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
가슴 본(Chest) 모듈 - 3ds Max용 가슴 본 기능 제공
해부학적인 척추 위치에서 대흉근 쪽을 바라보는 헬퍼를 사용해서, 어깨 움직임에 따라 늘어나거나 수축하는 대흉근용 본을 만든다.
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
    """대흉근용 가슴 본을 생성하는 클래스.

    척추 위치의 LookAt 헬퍼가 대흉근 쪽을 바라보게 하여, 어깨 움직임에 따라 늘어나거나 수축하는 가슴 본 셋업을 구성한다.
    """

    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, alignService=None):
        """Chest 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            alignService (Align | None): 정렬 서비스. None이면 새로 생성한다.
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
        """클래스의 작업 데이터를 초기 상태로 되돌린다."""
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
                     inChestMusclePushScale: float = 1.0, inChestMuscleHeightScale: float = 0.15,
                     inShoulderPushScale: float = 0.25) -> BoneChain:
        """가슴(대흉근) 본과 보조 헬퍼들을 생성한다.

        척추 뒤쪽의 LookAt 헬퍼가 앞쪽 타겟과 어깨 타겟을 가중치로 바라보게 하고,
        그 아래 대흉근 헬퍼를 향하는 몸통쪽(In)·어깨쪽(Out) 본 2개를 구성한다.

        Args:
            inSpine (rt.Node): 몸통 본
            inNeck (rt.Node): 목 본
            inAutoClavicle (rt.Node): 자동 쇄골 본
            inUpperArm (rt.Node): 상완 본
            inSpineHeightScale (float): 척추 높이 비율
            inSpinePushScale (float): 척추 앞뒤 밀림 비율
            inFrontWeight (float): 가슴쪽 LookAt 웨이트
            inShoulderWeight (float): 어깨쪽 LookAt 웨이트
            inChestMusclePushScale (float): 대흉근 X축 밀림 비율
            inChestMuscleHeightScale (float): 대흉근 높이 비율
            inShoulderPushScale (float): 어깨 밀림 비율

        Returns:
            BoneChain | None: 생성된 가슴 본 체인. 입력 노드가 유효하지 않으면 None
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
        self.anim.move_local(chestFrontMuscleHelper, spineLength*inChestMusclePushScale, -spineLength*inChestMuscleHeightScale, 0.0)
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
            "Parameters": [inSpineHeightScale, inSpinePushScale, inFrontWeight, inShoulderWeight, inChestMusclePushScale, inChestMuscleHeightScale, inShoulderPushScale]
        }
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 가슴 본을 재생성한다.

        기존 본과 헬퍼를 삭제한 뒤 소스 본과 파라미터로 셋업을 다시 만든다.

        Args:
            inBoneChain (BoneChain): 가슴 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 가슴 본 체인. 체인이 비었거나 소스 본이 유효하지 않으면 None
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
        if len(parameters) >= 7:
            spineHeightScale = parameters[0]
            spinePushScale = parameters[1]
            frontWeight = parameters[2]
            shoulderWeight = parameters[3]
            chestMusclePushScale = parameters[4]
            chestMuscleHeightScale = parameters[5]
            shoulderPushScale = parameters[6]
        else:
            # 기본값
            spineHeightScale = 0.33
            spinePushScale = 0.5
            frontWeight = 60.0
            shoulderWeight = 40.0
            chestMusclePushScale = 1.0
            chestMuscleHeightScale = 0.15
            shoulderPushScale = 0.25
        
        return self.create_bones(spine, neck, autoClavicle, upperArm,
                                 spineHeightScale, spinePushScale,
                                 frontWeight, shoulderWeight,
                                 chestMusclePushScale, chestMuscleHeightScale, shoulderPushScale)