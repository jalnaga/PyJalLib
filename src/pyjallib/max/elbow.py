#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
팔꿈치 모듈
자동으로 팔꿈치 본을 생성.
"""

from pymxs import runtime as rt

from .volumeBone import VolumeBone
from .boneChain import BoneChain

class Elbow(VolumeBone):
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        super().__init__(nameService=nameService, animService=animService, constraintService=constraintService, boneService=boneService, helperService=helperService)
    
    def create_bones(self, inForeArm, inUpperArm, inRotScale=0.5, inVolumeSize=4.0, inRotAxis="Z", inElbowTransAxis="PosY", inInnerElbowTransAxis="NegY", inElbowTransScale=0.25, inInnerElbowTransScale=1.0):
        """팔꿈치 볼륨 본들을 생성합니다."""
        if not rt.isValidNode(inForeArm) or not rt.isValidNode(inUpperArm):
            return False
        
        # 이름 생성 (로컬 변수로 처리)
        filteringChar = self.name._get_filtering_char(inUpperArm.name)
        elbowName = self.name.replace_name_part("RealName", inUpperArm.name, "Elbow")
        elbowRootName = self.name.replace_name_part("RealName", elbowName, "Elbow" + filteringChar + "Root")
        elbowRootDumName = self.name.replace_name_part("Type", elbowRootName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        elbowFwdName = self.name.replace_name_part("RealName", elbowName, "Elbow" + filteringChar + "Fwd")
        elbowBckName = self.name.replace_name_part("RealName", elbowName, "Elbow" + filteringChar + "Bck")
        
        # 소문자 처리
        if inUpperArm.name[0].islower():
            elbowName = elbowName.lower()
            elbowRootName = elbowRootName.lower()
            elbowRootDumName = elbowRootDumName.lower()
            elbowFwdName = elbowFwdName.lower()
            elbowBckName = elbowBckName.lower()
        
        # 방향 결정
        facingDirVec = inForeArm.transform.position - inUpperArm.transform.position
        inObjXAxisVec = inForeArm.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        # 축과 스케일 설정 - 모든 배열의 길이를 맞춤
        rotAxises = [inRotAxis, inRotAxis]  # 2개의 볼륨 본이므로 같은 회전축을 2번
        transAxises = [inElbowTransAxis, inInnerElbowTransAxis]
        transScales = [inElbowTransScale, inInnerElbowTransScale]
        transAxisNames = [inElbowTransAxis, inInnerElbowTransAxis]
        
        if distanceDir < 0:
            transScales = [inInnerElbowTransScale, inElbowTransScale]
            transAxisNames = [inInnerElbowTransAxis, inElbowTransAxis]
        
        # 부모 클래스의 create_bones 호출
        volumeBoneResult = super().create_bones(inForeArm, inUpperArm, inRotScale, inVolumeSize, rotAxises, transAxises, transScales)
        
        # volumeBoneResult가 None이면 실패 반환
        if not volumeBoneResult:
            return None
        
        # 생성된 본들의 이름 변경
        if hasattr(volumeBoneResult, 'bones') and volumeBoneResult.bones:
            for item in volumeBoneResult.bones:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = elbowRootName
                elif rt.matchPattern(item.name.lower(), pattern="*"+transAxisNames[0].lower()+"*"):
                    item.name = elbowBckName
                elif rt.matchPattern(item.name.lower(), pattern="*"+transAxisNames[1].lower()+"*"):
                    item.name = elbowFwdName
        
        # 생성된 헬퍼들의 이름 변경
        if hasattr(volumeBoneResult, 'helpers') and volumeBoneResult.helpers:
            for item in volumeBoneResult.helpers:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = elbowRootDumName
        
        rt.redrawViews()
        
        return volumeBoneResult
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain에서 팔꿈치 본들을 재생성합니다."""
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 2 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]):
            return None
        
        # 매개변수 추출
        inForeArm = sourceBones[0]
        inUpperArm = sourceBones[1]
        inRotScale = parameters[0] if len(parameters) > 0 else 0.5
        inVolumeSize = parameters[1] if len(parameters) > 1 else 4.0
        inRotAxis = parameters[2] if len(parameters) > 2 else "Z"
        inElbowTransAxis = parameters[3] if len(parameters) > 3 else "PosY"
        inInnerElbowTransAxis = parameters[4] if len(parameters) > 4 else "NegY"
        inElbowTransScale = parameters[5] if len(parameters) > 5 else 0.25
        inInnerElbowTransScale = parameters[6] if len(parameters) > 6 else 1.0
        
        return self.create_bones(inForeArm, inUpperArm, inRotScale, inVolumeSize, inRotAxis, inElbowTransAxis, inInnerElbowTransAxis, inElbowTransScale, inInnerElbowTransScale)
