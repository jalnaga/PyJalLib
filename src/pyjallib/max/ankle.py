#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
발목 모듈
자동으로 발목 본을 생성.
"""

from pymxs import runtime as rt

from .volumeBone import VolumeBone
from .boneChain import BoneChain

class Ankle(VolumeBone):
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        super().__init__(nameService=nameService, animService=animService, constraintService=constraintService, boneService=boneService, helperService=helperService)
    
    def create_bones(self, inFoot, inCalf, inRotScale=0.5, inVolumeSize=4.0, inRotAxis="Z", inAnkleTransAxis="PosY", inInnerAnkleTransAxis="NegY", inAnkleTransScale=1.5, inInnerAnkleTransScale=1.0):
        """발목 볼륨 본들을 생성합니다."""
        if not rt.isValidNode(inFoot) or not rt.isValidNode(inCalf):
            return False
        
        # 이름 생성 (로컬 변수로 처리)
        filteringChar = self.name.get_filtering_char(inCalf.name)
        ankleName = self.name.replace_name_part("RealName", inCalf.name, "Ankle")
        ankleRootName = self.name.replace_name_part("RealName", ankleName, "Ankle" + filteringChar + "Root")
        ankleRootDumName = self.name.replace_name_part("Type", ankleRootName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        ankleFwdName = self.name.replace_name_part("FrontBack", ankleName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        ankleBckName = self.name.replace_name_part("FrontBack", ankleName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        
        # 소문자 처리
        if self.name.get_name("RealName", inCalf.name)[0].islower():
            ankleName = ankleName.lower()
            ankleRootName = ankleRootName.lower()
            ankleRootDumName = ankleRootDumName.lower()
            ankleFwdName = ankleFwdName.lower()
            ankleBckName = ankleBckName.lower()
        
        # 방향 결정
        facingDirVec = inFoot.transform.position - inCalf.transform.position
        inObjXAxisVec = inFoot.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        # 축과 스케일 설정 - 모든 배열의 길이를 맞춤
        rotAxises = [inRotAxis, inRotAxis]  # 2개의 볼륨 본이므로 같은 회전축을 2번
        transAxises = [inAnkleTransAxis, inInnerAnkleTransAxis]
        transScales = [inAnkleTransScale, inInnerAnkleTransScale]
        transAxisNames = [inAnkleTransAxis, inInnerAnkleTransAxis]
        
        if distanceDir < 0:
            transScales = [inInnerAnkleTransScale, inAnkleTransScale]
            transAxisNames = [inInnerAnkleTransAxis, inAnkleTransAxis]
        
        # 부모 클래스의 create_bones 호출
        volumeBoneResult = super().create_bones(inFoot, inCalf, inRotScale, inVolumeSize, rotAxises, transAxises, transScales)
        
        # volumeBoneResult가 None이면 실패 반환
        if not volumeBoneResult:
            return None
        
        # 생성된 본들의 이름 변경
        if hasattr(volumeBoneResult, 'bones') and volumeBoneResult.bones:
            for item in volumeBoneResult.bones:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = ankleRootName
                # 축 이름의 의미(Pos=앞, Neg=뒤)를 기준으로 이름 매핑
                elif rt.matchPattern(item.name.lower(), pattern="*pos*"):
                    item.name = ankleFwdName
                elif rt.matchPattern(item.name.lower(), pattern="*neg*"):
                    item.name = ankleBckName
        
        # 생성된 헬퍼들의 이름 변경
        if hasattr(volumeBoneResult, 'helpers') and volumeBoneResult.helpers:
            for item in volumeBoneResult.helpers:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = ankleRootDumName
        
        if self.bone.is_skin_bone(inFoot) or self.bone.is_skin_bone(inCalf):
            for item in volumeBoneResult.bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in volumeBoneResult.helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        rt.redrawViews()
        
        return volumeBoneResult
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain에서 발목 본들을 재생성합니다."""
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 2 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]):
            return None
        
        # 매개변수 추출
        inFoot = sourceBones[0]
        inCalf = sourceBones[1]
        inRotScale = parameters[0] if len(parameters) > 0 else 0.5
        inVolumeSize = parameters[1] if len(parameters) > 1 else 4.0
        inRotAxis = parameters[2] if len(parameters) > 2 else "Z"
        inAnkleTransAxis = parameters[3] if len(parameters) > 3 else "PosY"
        inInnerAnkleTransAxis = parameters[4] if len(parameters) > 4 else "NegY"
        inAnkleTransScale = parameters[5] if len(parameters) > 5 else 1.5
        inInnerAnkleTransScale = parameters[6] if len(parameters) > 6 else 1.0
        
        return self.create_bones(inFoot, inCalf, inRotScale, inVolumeSize, inRotAxis, inAnkleTransAxis, inInnerAnkleTransAxis, inAnkleTransScale, inInnerAnkleTransScale)

