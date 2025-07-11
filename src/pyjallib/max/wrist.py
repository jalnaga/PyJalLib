#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
손목 모듈
자동으로 손목 본을 생성.
"""

from pymxs import runtime as rt

from .volumeBone import VolumeBone
from .boneChain import BoneChain

class Wrist(VolumeBone):
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        super().__init__(nameService=nameService, animService=animService, constraintService=constraintService, boneService=boneService, helperService=helperService)
    
    def create_bones(self, inHand, inForeArm, inRotScale=0.5, inVolumeSize=4.0, inFBRotAxis="Y", inIORotAxis="Z", inFBTransAxis="Z", inIOTransAxis="Y", inFBTransScale=1.0, inIOTransScale=1.0):
        """손목 볼륨 본들을 생성합니다."""
        if not rt.isValidNode(inHand) or not rt.isValidNode(inForeArm):
            return False
        
        # 이름 생성 (로컬 변수로 처리)
        filteringChar = self.name._get_filtering_char(inForeArm.name)
        wristName = self.name.replace_name_part("RealName", inForeArm.name, "Wrist")
        wristRootName = self.name.replace_name_part("RealName", wristName, "Wrist" + filteringChar + "Root")
        wristRootDumName = self.name.replace_name_part("Type", wristRootName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        wristFwdName = self.name.replace_name_part("RealName", wristName, "Wrist" + filteringChar + "Fwd")
        wristBckName = self.name.replace_name_part("RealName", wristName, "Wrist" + filteringChar + "Bck")
        wristInName = self.name.replace_name_part("RealName", wristName, "Wrist" + filteringChar + "In")
        wristOutName = self.name.replace_name_part("RealName", wristName, "Wrist" + filteringChar + "Out")
        
        # 소문자 처리
        if inForeArm.name[0].islower():
            wristName = wristName.lower()
            wristRootName = wristRootName.lower()
            wristRootDumName = wristRootDumName.lower()
            wristFwdName = wristFwdName.lower()
            wristBckName = wristBckName.lower()
            wristInName = wristInName.lower()
            wristOutName = wristOutName.lower()
        
        # 방향 결정
        facingDirVec = inHand.transform.position - inForeArm.transform.position
        inObjXAxisVec = inHand.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        # 축과 스케일 설정 - 2개의 볼륨 본: FB(앞/뒤), IO(안/바깥)
        rotAxises = [inFBRotAxis, inFBRotAxis, inIORotAxis, inIORotAxis]
        transScales = [inFBTransScale, inFBTransScale, inIOTransScale, inIOTransScale]
        transAxises = ["Pos" + inFBTransAxis, "Neg" + inFBTransAxis, "Pos" + inIOTransAxis, "Neg" + inIOTransAxis]
        transAxisNames = [transAxises[0], transAxises[1], transAxises[2], transAxises[3]]
        
        if distanceDir < 0:
            transAxisNames = [transAxises[1], transAxises[0], transAxises[3], transAxises[2]]
        
        # 부모 클래스의 create_bones 호출
        volumeBoneResult = super().create_bones(inHand, inForeArm, inRotScale, inVolumeSize, rotAxises, transAxises, transScales)
        
        # volumeBoneResult가 None이면 실패 반환
        if not volumeBoneResult:
            return None
        
        # 생성된 본들의 이름 변경
        if hasattr(volumeBoneResult, 'bones') and volumeBoneResult.bones:
            for item in volumeBoneResult.bones:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = wristRootName
                elif rt.matchPattern(item.name.lower(), pattern="*" + transAxisNames[0].lower() + "*"):
                    item.name = wristBckName
                elif rt.matchPattern(item.name.lower(), pattern="*" + transAxisNames[1].lower() + "*"):
                    item.name = wristFwdName
                elif rt.matchPattern(item.name.lower(), pattern="*" + transAxisNames[2].lower() + "*"):
                    item.name = wristInName
                elif rt.matchPattern(item.name.lower(), pattern="*" + transAxisNames[3].lower() + "*"):
                    item.name = wristOutName
        
        # 생성된 헬퍼들의 이름 변경
        if hasattr(volumeBoneResult, 'helpers') and volumeBoneResult.helpers:
            for item in volumeBoneResult.helpers:
                if rt.matchPattern(item.name.lower(), pattern="*root*"):
                    item.name = wristRootDumName
        
        rt.redrawViews()
        
        return volumeBoneResult
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain에서 손목 본들을 재생성합니다."""
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 2 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]):
            return None
        
        # 매개변수 추출
        inHand = sourceBones[0]
        inForeArm = sourceBones[1]
        inRotScale = parameters[0] if len(parameters) > 0 else 0.5
        inVolumeSize = parameters[1] if len(parameters) > 1 else 4.0
        inFBRotAxis = parameters[2] if len(parameters) > 2 else "Y"
        inIORotAxis = parameters[3] if len(parameters) > 3 else "Z"
        inFBTransAxis = parameters[4] if len(parameters) > 4 else "Z"
        inIOTransAxis = parameters[5] if len(parameters) > 5 else "Y"
        inFBTransScale = parameters[6] if len(parameters) > 6 else 1.0
        inIOTransScale = parameters[7] if len(parameters) > 7 else 1.0
        
        return self.create_bones(inHand, inForeArm, inRotScale, inVolumeSize, inFBRotAxis, inIORotAxis, inFBTransAxis, inIOTransAxis, inFBTransScale, inIOTransScale)
