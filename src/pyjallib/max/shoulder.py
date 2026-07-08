#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
어깨 모듈
자동으로 어깨 본을 생성.
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint
from .bip import Bip

from .boneChain import BoneChain

class Shoulder:
    """자동 어깨 본을 생성하는 클래스.

    쇄골-상완 사이에 LookAt 헬퍼와 상완 트위스트 가중치 기반 회전 제약으로 움직이는 어깨 본 셋업을 구성한다.
    """

    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, bipService=None):
        """Shoulder 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            bipService (Bip | None): Biped 서비스. None이면 새로 생성한다.
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim)
        
        self.boneSize = 2.0
        
        self.genBones = []
        self.genHelpers = []
        self.clavicle = None
        self.upperArm = None
        self.autoClavicle = None
        self.upperArmTwist = None
        self.twistWeight = 0.7
        
        self.shoulderLookAtTargetPosConstExpression = ""
        self.shoulderLookAtTargetPosConstExpression += "local clavicleDistance = distance clavicle upperArm\n"
        self.shoulderLookAtTargetPosConstExpression += "local xPos = clavicleDistance * distanceDir\n"
        self.shoulderLookAtTargetPosConstExpression += "[xPos, 0.0, 0.0]\n"
    
    def reset(self):
        """클래스의 작업 데이터를 초기 상태로 되돌린다.

        Returns:
            Shoulder: 메서드 체이닝을 위한 자기 자신
        """
        self.genBones = []
        self.genHelpers = []
        self.clavicle = None
        self.upperArm = None
        self.autoClavicle = None
        self.upperArmTwist = None
        self.twistWeight = 0.7
        
        return self
    
    def create_bones(self, inClavicle, inUpperArm, inAutoClavicle, inUpperArmTwist, inTwistWeight=0.7):
        """어깨 본과 보조 헬퍼들을 생성한다.

        쇄골-상완 방향을 기준으로 LookAt 타겟·회전 헬퍼를 구성하고,
        LookAt 헬퍼와 상완 트위스트 본에 가중치를 나눠 어깨 본의 회전을 제어한다.

        Args:
            inClavicle (rt.Node): 쇄골 본
            inUpperArm (rt.Node): 상완 본
            inAutoClavicle (rt.Node): 자동 쇄골 본. 생성되는 어깨 본의 부모가 된다.
            inUpperArmTwist (rt.Node): 상완 트위스트 본
            inTwistWeight (float): 트위스트 회전 가중치 (0.0~1.0)

        Returns:
            BoneChain | False: 생성된 어깨 본 체인. 입력 노드가 유효하지 않으면 False
        """
        if not rt.isValidNode(inClavicle) or not rt.isValidNode(inUpperArm) or not rt.isValidNode(inAutoClavicle) or not rt.isValidNode(inUpperArmTwist):
            return False
        
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        facingDirVec = inUpperArm.transform.position - inClavicle.transform.position
        inObjXAxisVec = inClavicle.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        clavicleLength *= distanceDir
        
        genBones = []
        genHelpers = []
        
        # 자동 쇄골 이름 생성 및 뼈대 생성
        shoulderName = self.name.replace_name_part("RealName", inClavicle.name, "Shoulder")
        if self.name.get_name("RealName", inClavicle.name)[0].islower():
            shoulderName = shoulderName.lower()
            
        shoulderBone = self.bone.create_nub_bone(shoulderName, self.boneSize)
        shoulderBone.name = self.name.remove_name_part("Nub", shoulderBone.name)
        shoulderBone.transform = inUpperArm.transform
        shoulderBone.parent = inAutoClavicle
        genBones.append(shoulderBone)
        
        # 어깨 타겟 포인트 생성
        shoulderLookAtTarget = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "Target")))
        shoulderLookAtTarget.transform = inUpperArm.transform
        shoulderLookAtTarget.parent = inUpperArm
        shoulderLookAtTargetPosConst = self.const.assign_pos_script_controller(shoulderLookAtTarget)
        shoulderLookAtTargetPosConst.addConstant("distanceDir", distanceDir)
        shoulderLookAtTargetPosConst.addNode("clavicle", inClavicle)
        shoulderLookAtTargetPosConst.addNode("upperArm", inUpperArm)
        shoulderLookAtTargetPosConst.setExpression(self.shoulderLookAtTargetPosConstExpression)
        genHelpers.append(shoulderLookAtTarget)
        
        # 어깨 회전 헬퍼 포인트 생성
        shoulderLookAtHelper = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "LookAt")))
        shoulderLookAtHelper.transform = inClavicle.transform
        shoulderLookAtHelper.parent = inClavicle
        shoulderLookAtHelperPosConst = self.const.assign_pos_const(shoulderLookAtHelper, inClavicle)
        
        lookAtConst = self.const.assign_lookat(shoulderLookAtHelper, shoulderLookAtTarget)
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inClavicle
        lookAtConst.lookat_vector_length = 0.0
        if distanceDir < 0:
            lookAtConst.target_axisFlip = True
        genHelpers.append(shoulderLookAtHelper)
        
        # 어깨 최종 회전 헬퍼 포인트 생성
        shoulderRotHelper = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "Rotation")))
        shoulderRotHelper.transform = inUpperArm.transform
        shoulderRotHelper.parent = inUpperArm
        shoulderRotHelperPosConst = self.const.assign_pos_const(shoulderRotHelper, inUpperArm)
        
        shoulderRotHelperRotConst = self.const.assign_rot_const_multi(shoulderRotHelper, [shoulderLookAtHelper, inUpperArmTwist])
        shoulderRotHelperRotConst.setWeight(1, 100.0-(inTwistWeight*100.0))
        shoulderRotHelperRotConst.setWeight(2, inTwistWeight*100.0)
        genHelpers.append(shoulderRotHelper)
        
        # 어깨 최종 회전 오프셋 헬퍼 포인트 생성
        shoulderRotOffsetHelepr = self.helper.create_point(self.name.replace_name_part("Type", shoulderName, self.name.get_name_part_value_by_description("Type", "Dummy")))
        shoulderRotOffsetHelepr.transform = inUpperArm.transform
        shoulderRotOffsetHelepr.parent = shoulderRotHelper
        genHelpers.append(shoulderRotOffsetHelepr)
        
        # 어깨 본 회전 설정
        shoulderBoneRotConst = self.const.assign_rot_const(shoulderBone, shoulderRotOffsetHelepr)
        
        if self.bone.is_skin_bone(inClavicle) or self.bone.is_skin_bone(inUpperArm) or self.bone.is_skin_bone(inAutoClavicle) or self.bone.is_skin_bone(inUpperArmTwist):
            for item in genBones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in genHelpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        self.genBones = genBones
        self.genHelpers = genHelpers
        self.clavicle = inClavicle
        self.upperArm = inUpperArm
        self.autoClavicle = inAutoClavicle
        self.upperArmTwist = inUpperArmTwist
        self.twistWeight = inTwistWeight
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers,
            "SourceBones": [inClavicle, inUpperArm, inAutoClavicle, inUpperArmTwist],
            "Parameters": [inTwistWeight]
        }
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 어깨 본을 재생성한다.

        기존 본과 헬퍼를 삭제한 뒤 소스 본과 파라미터로 셋업을 다시 만든다.

        Args:
            inBoneChain (BoneChain): 어깨 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 어깨 본 체인. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        # BoneChain에서 필요한 정보 추출
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        # 필수 소스 본 확인
        if len(sourceBones) < 4 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or not rt.isValidNode(sourceBones[2]) or not rt.isValidNode(sourceBones[3]):
            return None
            
        # 파라미터 가져오기 (또는 기본값 사용)
        twistWeight = parameters[0] if len(parameters) > 0 else 0.7
        
        # 쇄골 생성
        inClavicle = sourceBones[0]
        inUpperArm = sourceBones[1]
        inAutoClavicle = sourceBones[2]
        inUpperArmTwist = sourceBones[3]
        
        # 새로운 쇄골 생성
        return self.create_bones(inClavicle, inUpperArm, inAutoClavicle, inUpperArmTwist, twistWeight)
    
    
        