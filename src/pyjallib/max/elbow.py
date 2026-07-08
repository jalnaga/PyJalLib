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
    """팔꿈치 볼륨 본을 생성하는 클래스.

    VolumeBone을 상속하여 팔꿈치 굽힘에 따라 바깥쪽·안쪽으로 밀리는 볼륨 본 2개를 구성한다.
    """

    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """Elbow 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
        """
        super().__init__(nameService=nameService, animService=animService, constraintService=constraintService, boneService=boneService, helperService=helperService)
    
    def create_bones(self, inForeArm, inUpperArm, inRotScale=0.5, inVolumeSize=4.0, inRotAxis="Z", inElbowTransAxis="PosY", inInnerElbowTransAxis="NegY", inElbowTransScale=0.25, inInnerElbowTransScale=1.0):
        """팔꿈치 볼륨 본들을 생성한다.

        VolumeBone.create_bones로 볼륨 본을 만든 뒤 팔꿈치 명명 규칙에 맞게
        본·헬퍼의 이름을 변경한다. 팔 방향에 따라 앞뒤 스케일을 자동으로 뒤집는다.

        Args:
            inForeArm (rt.Node): 전완 본. 볼륨 본의 기준 객체가 된다.
            inUpperArm (rt.Node): 상완 본. 볼륨 본의 부모 기준이 된다.
            inRotScale (float): 회전 반영 비율
            inVolumeSize (float): 볼륨 본 크기
            inRotAxis (str): 회전 감지 축 ("X", "Y", "Z")
            inElbowTransAxis (str): 팔꿈치(뒤쪽) 본 이동 축 (예: "PosY")
            inInnerElbowTransAxis (str): 안쪽 팔꿈치(앞쪽) 본 이동 축 (예: "NegY")
            inElbowTransScale (float): 팔꿈치 본 이동 스케일
            inInnerElbowTransScale (float): 안쪽 팔꿈치 본 이동 스케일

        Returns:
            BoneChain | None | False: 생성된 팔꿈치 본 체인. 입력 노드가 유효하지 않으면 False, 볼륨 본 생성에 실패하면 None
        """
        if not rt.isValidNode(inForeArm) or not rt.isValidNode(inUpperArm):
            return False
        
        # 이름 생성 (로컬 변수로 처리)
        filteringChar = self.name.get_filtering_char(inUpperArm.name)
        elbowName = self.name.replace_name_part("RealName", inUpperArm.name, "Elbow")
        elbowRootName = self.name.replace_name_part("RealName", elbowName, "Elbow" + filteringChar + "Root")
        elbowRootDumName = self.name.replace_name_part("Type", elbowRootName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        elbowFwdName = self.name.replace_name_part("FrontBack", elbowName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        elbowBckName = self.name.replace_name_part("FrontBack", elbowName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        
        # 소문자 처리
        if self.name.get_name("RealName", inUpperArm.name)[0].islower():
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
        
        if self.bone.is_skin_bone(inForeArm) or self.bone.is_skin_bone(inUpperArm):
            for item in volumeBoneResult.bones:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
            for item in volumeBoneResult.helpers:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        rt.redrawViews()
        
        return volumeBoneResult
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 팔꿈치 본을 재생성한다.

        기존 본과 헬퍼를 삭제한 뒤 소스 본과 파라미터로 셋업을 다시 만든다.

        Args:
            inBoneChain (BoneChain): 팔꿈치 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 팔꿈치 본 체인. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
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
