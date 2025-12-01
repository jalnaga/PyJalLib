#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
서혜부 모듈
자동으로 서혜부 본을 생성.
"""

from pymxs import runtime as rt

from .volumeBone import VolumeBone
from .boneChain import BoneChain

class Inguinal(VolumeBone):
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        super().__init__(nameService=nameService, animService=animService, constraintService=constraintService, boneService=boneService, helperService=helperService)
    
    def create_bones(self, inThighTwist, inPelvis, inCalf, inRotScale=0.5, inVolumeSize=10.0, inFwdRotAxis="Z", inOutRotAxis="Y", inFwdTransAxis="PosY", inOutTransAxis="PosZ", inFwdTransScale=2.0, inOutTransScale=2.5):
        """서혜부 볼륨 본들을 생성합니다."""
        if not rt.isValidNode(inThighTwist) or not rt.isValidNode(inPelvis) or not rt.isValidNode(inCalf):
            return False
        
        # 이름 생성 (로컬 변수로 처리)
        filteringChar = self.name._get_filtering_char(inThighTwist.name)
        inguinalName = self.name.replace_name_part("RealName", inThighTwist.name, "Inguinal")
        inguinalName = self.name.remove_name_part("Nub", inguinalName)
        inguinalName = self.name.remove_name_part("Index", inguinalName)
        inguinalRootName = self.name.replace_name_part("RealName", inguinalName, "Inguinal" + filteringChar + "Root")
        inguinalRootDumName = self.name.replace_name_part("Type", inguinalRootName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        inguinalFwdName = self.name.replace_name_part("FrontBack", inguinalName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        inguinalOutName = self.name.replace_name_part("InOut", inguinalName, self.name.get_name_part_value_by_description("InOut", "Out"))
        
        # 소문자 처리
        if self.name.get_name("RealName", inThighTwist.name)[0].islower():
            inguinalName = inguinalName.lower()
            inguinalRootName = inguinalRootName.lower()
            inguinalRootDumName = inguinalRootDumName.lower()
            inguinalFwdName = inguinalFwdName.lower()
            inguinalOutName = inguinalOutName.lower()
        
        # 방향 결정
        facingDirVec = inCalf.transform.position - inThighTwist.transform.position
        inObjXAxisVec = inThighTwist.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        # 축과 스케일 설정 - 2개의 볼륨 본: Fwd(앞), Out(바깥)
        rotAxises = [inFwdRotAxis, inOutRotAxis]
        transAxises = [inFwdTransAxis, inOutTransAxis]
        transScales = [inFwdTransScale, inOutTransScale]
        transAxisNames = [inFwdTransAxis, inOutTransAxis]
        
        if distanceDir < 0:
            # Neg 접두사를 Pos로 변환하여 방향 전환
            transAxises = ["Neg" + inFwdTransAxis[3:], "Neg" + inOutTransAxis[3:]]
            transAxisNames = [transAxises[0], transAxises[1]]
        
        # 부모 클래스의 create_bones 호출
        volumeBoneResult = super().create_bones(inThighTwist, inPelvis, inRotScale, inVolumeSize, rotAxises, transAxises, transScales)
        
        # volumeBoneResult가 None이면 실패 반환
        if not volumeBoneResult:
            return None
        
        # 생성된 본들의 포지션 스크립팅 변경
        if hasattr(volumeBoneResult, 'bones') and volumeBoneResult.bones:
            for item in volumeBoneResult.bones:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = inguinalRootName
                elif rt.matchPattern(item.name.lower(), pattern="*" + transAxisNames[0].lower() + "*"):
                    item.name = inguinalFwdName
                    posScriptConst = self.const.get_pos_list_controller(item)[1]
                    scriptExpression = posScriptConst.script
                    newScriptExpression = "result = trAxis * saturatedTwist * volumeSize * transScale\nif swizzledRot.z > 0 then result\nelse result * 0.0\n"
                    scriptExpression = scriptExpression.replace("trAxis * saturatedTwist * volumeSize * transScale", newScriptExpression)
                    posScriptConst.setExpression(scriptExpression)
                    posScriptConst.update()
                elif rt.matchPattern(item.name.lower(), pattern="*" + transAxisNames[1].lower() + "*"):
                    item.name = inguinalOutName
                    posScriptConst = self.const.get_pos_list_controller(item)[1]
                    scriptExpression = posScriptConst.script
                    newScriptExpression = "result = trAxis * saturatedTwist * volumeSize * transScale\nif swizzledRot.y < 0 then result\nelse result * 0.0\n"
                    scriptExpression = scriptExpression.replace("trAxis * saturatedTwist * volumeSize * transScale", newScriptExpression)
                    posScriptConst.setExpression(scriptExpression)
                    posScriptConst.update()
        # 생성된 헬퍼들의 이름 변경
        if hasattr(volumeBoneResult, 'helpers') and volumeBoneResult.helpers:
            for item in volumeBoneResult.helpers:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = inguinalRootDumName
        
        if self.bone.is_skin_bone(inThighTwist) or self.bone.is_skin_bone(inPelvis) or self.bone.is_skin_bone(inCalf):
            for item in volumeBoneResult.bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in volumeBoneResult.helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        result = {
            "Bones": volumeBoneResult.bones,
            "Helpers": volumeBoneResult.helpers,
            "SourceBones": [inThighTwist, inPelvis, inCalf],
            "Parameters": [inRotScale, inVolumeSize, inFwdRotAxis, inOutRotAxis, inFwdTransAxis, inOutTransAxis, inFwdTransScale, inOutTransScale]
        }
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain에서 서혜부 본들을 재생성합니다."""
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 3 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or not rt.isValidNode(sourceBones[2]):
            return None
        
        # 매개변수 추출
        inThighTwist = sourceBones[0]
        inPelvis = sourceBones[1]
        inCalf = sourceBones[2]
        inRotScale = parameters[0] if len(parameters) > 0 else 0.5
        inVolumeSize = parameters[1] if len(parameters) > 1 else 6.0
        inFwdRotAxis = parameters[2] if len(parameters) > 2 else "Z"
        inOutRotAxis = parameters[3] if len(parameters) > 3 else "Y"
        inFwdTransAxis = parameters[4] if len(parameters) > 4 else "PosY"
        inOutTransAxis = parameters[5] if len(parameters) > 5 else "PosZ"
        inFwdTransScale = parameters[6] if len(parameters) > 6 else 2.0
        inOutTransScale = parameters[7] if len(parameters) > 7 else 2.0
        
        return self.create_bones(inThighTwist, inPelvis, inCalf, inRotScale, inVolumeSize, inFwdRotAxis, inOutRotAxis, inFwdTransAxis, inOutTransAxis, inFwdTransScale, inOutTransScale) 