#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
겨드랑이 본(Armpit) 모듈 - 3ds Max용 겨드랑이 본 기능 제공
어깨본에서 링크되어 몸통본을 바라보면서 어깨의 높이 변화에 따라 몸통 바깥면을 따라 움직이는 본을 만드는 모듈
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

class Armpit:
    """겨드랑이 본을 생성하는 클래스.

    어깨 본에 링크된 LookAt 헬퍼가 몸통을 바라보게 하여, 어깨 높이 변화에 따라 몸통 바깥면을 따라 움직이는 본 셋업을 구성한다.
    """

    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, alignService=None):
        """Armpit 클래스를 초기화한다.

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
        
        self.shoulder = None
        self.neck = None
        self.spine = None
        
        self.genBones = []
        self.genHelpers = []
        
    def reset(self):
        """클래스의 작업 데이터를 초기 상태로 되돌린다."""
        self.boneSize = 2.0
        
        self.shoulder = None
        self.neck = None
        self.spine = None
        
        self.genBones = []
        self.genHelpers = []
        
    
    def create_bones(self, inShoulder, inSpine, inNeck, inSpineLengthScale=0.67):
        """겨드랑이 본과 보조 헬퍼들을 생성한다.

        어깨에 링크된 LookAt 헬퍼가 몸통쪽 타겟을 바라보게 하고,
        그 아래 위치 헬퍼를 따라가는 겨드랑이 본을 몸통의 자식으로 구성한다.

        Args:
            inShoulder (rt.Node): 어깨 본
            inSpine (rt.Node): 몸통 본
            inNeck (rt.Node): 목 본
            inSpineLengthScale (float): 몸통 길이 비율. 헬퍼 배치 거리 계산에 사용한다.

        Returns:
            BoneChain | False: 생성된 겨드랑이 본 체인. 입력 노드가 유효하지 않으면 False
        """
        if not rt.isValidNode(inShoulder) or not rt.isValidNode(inNeck) or not rt.isValidNode(inSpine):
            return False
        
        genBones = []
        genHelpers = []
        
        self.shoulder = inShoulder
        self.spine = inSpine
        self.neck = inNeck
        
        # 몸통 길이 계산
        spineLength = rt.distance(self.spine, self.neck) * inSpineLengthScale
        
        # 겨드랑이 본 이름 생성
        armpitName = self.name.replace_name_part("RealName", self.shoulder.name, "Armpit")
        if self.name.get_name("RealName", self.shoulder.name)[0].islower():
            armpitName = armpitName.lower()
        
        # 겨드랑이 룩엣 헬퍼 생성
        armpitLookAtName = self.name.replace_name_part("Type", armpitName, self.name.get_name_part_value_by_description("Type", "LookAt"))
        armpitLookAtHelper = self.helper.create_point(armpitLookAtName)
        self.helper.set_shape_to_axis(armpitLookAtHelper)
        armpitLookAtHelper.transform = self.shoulder.transform
        
        tempTarget = self.helper.create_point("Temp")
        tempTarget.transform = self.shoulder.transform
        rt.move(tempTarget, rt.Point3(0.0, 0.0, -spineLength))
        
        armpitLookAtConst = self.const.assign_lookat(armpitLookAtHelper, tempTarget)
        armpitLookAtConst.upnode_world = False
        armpitLookAtConst.pickUpNode = self.spine
        armpitLookAtConst.lookat_vector_length = 0.0
        
        self.const.collapse(armpitLookAtHelper)
        rt.delete(tempTarget)
        
        armpitLookAtTargetName = self.name.replace_name_part("Type", armpitName, self.name.get_name_part_value_by_description("Type", "Target"))
        armpitLookAtTarget = self.helper.create_point(armpitLookAtTargetName)
        self.helper.set_shape_to_cross(armpitLookAtTarget)
        armpitLookAtTarget.transform = armpitLookAtHelper.transform
        self.anim.move_local(armpitLookAtTarget, spineLength, 0.0, 0.0)
        rt.select([armpitLookAtTarget, self.spine])
        self.align.align_to_last_rot([armpitLookAtTarget, self.spine])
        
        armpitLookAtHelper.parent = self.shoulder
        armpitLookAtTarget.parent = self.spine
        
        armpitLookAtConst = self.const.assign_lookat(armpitLookAtHelper, armpitLookAtTarget)
        armpitLookAtConst.upnode_world = False
        armpitLookAtConst.pickUpNode = self.spine
        armpitLookAtConst.lookat_vector_length = 0.0
        
        armpitPosHelperName = self.name.replace_name_part("Type", armpitName, self.name.get_name_part_value_by_description("Type", "Position"))
        armpitPosHelper = self.helper.create_point(armpitPosHelperName)
        self.helper.set_shape_to_box(armpitPosHelper)
        armpitPosHelper.transform = armpitLookAtTarget.transform
        
        armpitPosHelper.parent = armpitLookAtHelper
        
        genHelpers.append(armpitLookAtHelper)
        genHelpers.append(armpitLookAtTarget)
        genHelpers.append(armpitPosHelper)
        
        # 겨드랑이 본 생성
        armpitBone = self.bone.create_nub_bone(armpitName, self.boneSize)
        armpitBone.name = armpitName
        armpitBone.transform = armpitPosHelper.transform
        armpitBone.parent = self.spine
        self.const.assign_pos_const(armpitBone, armpitPosHelper)
        
        genBones.append(armpitBone)
        
        self.genBones = genBones
        self.genHelpers = genHelpers
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers,
            "SourceBones": [self.shoulder, self.spine, self.neck],
            "Parameters": [inSpineLengthScale]
        }
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
        
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 겨드랑이 본을 재생성한다.

        기존 본과 헬퍼를 삭제한 뒤 소스 본과 파라미터로 셋업을 다시 만든다.

        Args:
            inBoneChain (BoneChain): 겨드랑이 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 겨드랑이 본 체인. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 3 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or not rt.isValidNode(sourceBones[2]):
            return None
        
        shoulder = sourceBones[0]
        spine = sourceBones[1]
        neck = sourceBones[2]
        
        # 파라미터 추출
        if len(parameters) >= 1:
            spineLengthScale = parameters[0]
        else:
            spineLengthScale = 0.67  # 기본값
        
        return self.create_bones(shoulder, spine, neck, spineLengthScale)
        