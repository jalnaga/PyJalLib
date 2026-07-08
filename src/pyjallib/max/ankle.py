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
    """발과 종아리 본을 기반으로 발목 볼륨 본을 자동 생성하는 클래스.

    VolumeBone을 상속해 발목 앞·뒤 두 방향의 볼륨 본을 만들고 발목 이름 규칙으로 정리한다.
    """

    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """Ankle 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 서비스. None이면 새로 생성한다.
        """
        super().__init__(nameService=nameService, animService=animService, constraintService=constraintService, boneService=boneService, helperService=helperService)
    
    def create_bones(self, inFoot, inCalf, inRotScale=0.5, inVolumeSize=4.0, inRotAxis="Z", inAnkleTransAxis="PosY", inInnerAnkleTransAxis="NegY", inAnkleTransScale=1.5, inInnerAnkleTransScale=1.0):
        """발목 볼륨 본들을 생성한다.

        부모 클래스(VolumeBone)의 create_bones로 앞·뒤 볼륨 본을 만든 뒤
        발목 이름 규칙으로 이름을 바꾼다.

        Args:
            inFoot (rt.Node): 발 본
            inCalf (rt.Node): 종아리 본
            inRotScale (float): 회전 반영 비율
            inVolumeSize (float): 볼륨 크기
            inRotAxis (str): 회전 축 ("X", "Y", "Z"). 두 볼륨 본에 동일하게 적용된다.
            inAnkleTransAxis (str): 발목 앞쪽 본의 이동 축 ("PosX"~"NegZ")
            inInnerAnkleTransAxis (str): 발목 안쪽(뒤쪽) 본의 이동 축 ("PosX"~"NegZ")
            inAnkleTransScale (float): 발목 앞쪽 본의 이동 스케일
            inInnerAnkleTransScale (float): 발목 안쪽 본의 이동 스케일

        Returns:
            BoneChain | None | False: 생성된 발목 본 체인. 유효하지 않은 노드가 있으면 False, 볼륨 본 생성에 실패하면 None
        """
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
        """기존 BoneChain 객체에서 발목 본들을 재생성한다.

        Args:
            inBoneChain (BoneChain): 발목 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 BoneChain. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
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

