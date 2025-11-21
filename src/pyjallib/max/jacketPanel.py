#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
자켓 패널 본(JacketPanel) 모듈 - 3ds Max용 자켓 패널 본 기능 제공
어깨를 들어올릴 때 자켓이 따라 올려지는 효과를 만드는 모듈
좌우 패널(clavicle 기반)과 가운데 패널(좌우 블렌드)을 생성
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

class JacketPanel:
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, alignService=None):
        """
        JacketPanel 클래스의 주요 컴포넌트들을 초기화합니다.
        
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
        
    def reset(self):
        """
        JacketPanel 클래스의 주요 컴포넌트들을 초기화합니다.
        서비스가 아닌 클래스 자체의 작업 데이터를 초기화하는 함수입니다.
        """
        self.boneSize = 2.0
        
        self.genBones = []
        self.genHelpers = []
        
    
    def create_side_panel(self, inClavicle, inUpperArm, inSpine, inNeck):
        """
        좌우 자켓 패널 본들을 생성합니다 (앞/뒤 2개).
        
        Args:
            inClavicle: 쇄골 본
            inUpperArm: 상완 본 (clavicle 길이 계산용)
            inSpine: 척추 본
            inNeck: 목 본
            
        Returns:
            dict: 생성된 본, 헬퍼, 포지션 헬퍼 참조
        """
        if not rt.isValidNode(inClavicle) or not rt.isValidNode(inUpperArm) or not rt.isValidNode(inSpine) or not rt.isValidNode(inNeck):
            return None
        
        genBones = []
        genHelpers = []
        
        # 본 길이 계산
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        spineLength = rt.distance(inSpine, inNeck)
        
        facingDirVec = inUpperArm.transform.position - inClavicle.transform.position
        inObjXAxisVec = inClavicle.objectTransform.row1
        sideDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        # 몸통의 정면이 로컬 +Y 방향인지 -Y 방향인지 결정
        spineZAxisVec = inSpine.objectTransform.row3
        spineFacingDir = rt.normalize(inNeck.transform.position - inSpine.transform.position)
        
        spineFwdVec = rt.cross(spineZAxisVec, spineFacingDir)
        fwdDir = 1.0 if rt.dot(spineFwdVec, rt.normalize(inSpine.objectTransform.row2)) < 0.0 else -1.0
        
        # 기본 이름 생성
        baseName = self.name.replace_name_part("RealName", inClavicle.name, "JacketPanel")
        if self.name.get_name("RealName", inClavicle.name)[0].islower():
            baseName = baseName.lower()
        
        # ========== 앞쪽 패널 생성 ==========
        
        # 앞쪽 자켓 패널 이름
        frontPanelName = self.name.replace_name_part("FrontBack", baseName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        
        # 앞쪽 룩엣 헬퍼 생성
        frontLookAtName = self.name.replace_name_part("Type", frontPanelName, self.name.get_name_part_value_by_description("Type", "LookAt"))
        frontLookAtHelper = self.helper.create_point(frontLookAtName)
        self.helper.set_shape_to_axis(frontLookAtHelper)
        frontLookAtHelper.transform = inClavicle.transform
        
        # clavicle 로컬 X축으로 clavicle 길이의 절반 이동
        self.anim.move_local(frontLookAtHelper, clavicleLength * sideDir / 2.0, 0.0, 0.0)
        # 로컬 Y축 방향으로 spine길이 * 0.5 이동(앞쪽)
        self.anim.move_local(frontLookAtHelper, 0.0, spineLength * fwdDir * sideDir * 0.5, 0.0)
        self.align.align_to_last_rot([frontLookAtHelper, inSpine])
        
        # 임시 타겟 생성하여 초기 회전 설정
        tempTarget = self.helper.create_point("Temp")
        tempTarget.transform = frontLookAtHelper.transform
        self.anim.move_local(tempTarget, -spineLength * 0.67, 0.0, 0.0)
        
        self.align.align_to_last_rot([frontLookAtHelper, inClavicle])
        
        frontLookAtConst = self.const.assign_lookat(frontLookAtHelper, tempTarget)
        frontLookAtConst.upnode_world = False
        frontLookAtConst.pickUpNode = inSpine
        frontLookAtConst.lookat_vector_length = 0.0
        
        self.const.collapse(frontLookAtHelper)
        rt.delete(tempTarget)
        
        # 앞쪽 타겟 헬퍼 생성
        frontTargetName = self.name.replace_name_part("Type", frontPanelName, self.name.get_name_part_value_by_description("Type", "Target"))
        frontTarget = self.helper.create_point(frontTargetName)
        self.helper.set_shape_to_cross(frontTarget)
        frontTarget.transform = frontLookAtHelper.transform
        self.anim.move_local(frontTarget, spineLength * 0.67, 0.0, 0.0)
        self.align.align_to_last_rot([frontTarget, inSpine])
        
        frontLookAtHelper.parent = inClavicle
        frontTarget.parent = inSpine
        
        # 룩엣 제약 재설정
        frontLookAtConst = self.const.assign_lookat(frontLookAtHelper, frontTarget)
        frontLookAtConst.upnode_world = False
        frontLookAtConst.pickUpNode = inSpine
        frontLookAtConst.lookat_vector_length = 0.0
        frontLookAtConst.StoUP_axis = 1
        frontLookAtConst.upnode_axis = 1
        
        # 앞쪽 포지션 헬퍼 생성
        frontPosHelperName = self.name.replace_name_part("Type", frontPanelName, self.name.get_name_part_value_by_description("Type", "Position"))
        frontPosHelper = self.helper.create_point(frontPosHelperName)
        self.helper.set_shape_to_box(frontPosHelper)
        frontPosHelper.transform = frontTarget.transform
        frontPosHelper.parent = frontLookAtHelper
        
        genHelpers.extend([frontLookAtHelper, frontTarget, frontPosHelper])
        
        # 앞쪽 자켓 패널 본 생성
        frontPanelBone = self.bone.create_nub_bone(frontPanelName, self.boneSize)
        frontPanelBone.name = frontPanelName
        frontPanelBone.transform = frontPosHelper.transform
        frontPanelBone.parent = inSpine
        self.const.assign_pos_const(frontPanelBone, frontPosHelper)
        self.const.assign_rot_const(frontPanelBone, frontPosHelper)
        
        genBones.append(frontPanelBone)
        
        # ========== 뒤쪽 패널 생성 ==========
        
        # 뒤쪽 자켓 패널 이름
        backPanelName = self.name.replace_name_part("FrontBack", baseName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        
        # 뒤쪽 룩엣 헬퍼 생성
        backLookAtName = self.name.replace_name_part("Type", backPanelName, self.name.get_name_part_value_by_description("Type", "LookAt"))
        backLookAtHelper = self.helper.create_point(backLookAtName)
        self.helper.set_shape_to_axis(backLookAtHelper)
        backLookAtHelper.transform = inClavicle.transform
        
        # clavicle 로컬 X축으로 clavicle 길이의 절반 이동
        self.anim.move_local(backLookAtHelper, clavicleLength * sideDir / 2.0, 0.0, 0.0)
        # 로컬 -Y축 방향으로 spine길이 * 0.5 이동 (뒤쪽)
        self.anim.move_local(backLookAtHelper, 0.0, -spineLength * fwdDir * sideDir * 0.5, 0.0)
        self.align.align_to_last_rot([backLookAtHelper, inSpine])
        
        # 임시 타겟 생성하여 초기 회전 설정
        tempTarget = self.helper.create_point("Temp")
        tempTarget.transform = backLookAtHelper.transform
        self.anim.move_local(tempTarget, -spineLength * 0.67, 0.0, 0.0)
        
        self.align.align_to_last_rot([backLookAtHelper, inClavicle])
        
        backLookAtConst = self.const.assign_lookat(backLookAtHelper, tempTarget)
        backLookAtConst.upnode_world = False
        backLookAtConst.pickUpNode = inSpine
        backLookAtConst.lookat_vector_length = 0.0
        
        self.const.collapse(backLookAtHelper)
        rt.delete(tempTarget)
        
        # 뒤쪽 타겟 헬퍼 생성
        backTargetName = self.name.replace_name_part("Type", backPanelName, self.name.get_name_part_value_by_description("Type", "Target"))
        backTarget = self.helper.create_point(backTargetName)
        self.helper.set_shape_to_cross(backTarget)
        backTarget.transform = backLookAtHelper.transform
        self.anim.move_local(backTarget, spineLength * 0.67, 0.0, 0.0)
        self.align.align_to_last_rot([backTarget, inSpine])
        
        backLookAtHelper.parent = inClavicle
        backTarget.parent = inSpine
        
        # 룩엣 제약 재설정
        backLookAtConst = self.const.assign_lookat(backLookAtHelper, backTarget)
        backLookAtConst.upnode_world = False
        backLookAtConst.pickUpNode = inSpine
        backLookAtConst.lookat_vector_length = 0.0
        backLookAtConst.StoUP_axis = 1
        backLookAtConst.upnode_axis = 1
        
        # 뒤쪽 포지션 헬퍼 생성
        backPosHelperName = self.name.replace_name_part("Type", backPanelName, self.name.get_name_part_value_by_description("Type", "Position"))
        backPosHelper = self.helper.create_point(backPosHelperName)
        self.helper.set_shape_to_box(backPosHelper)
        backPosHelper.transform = backTarget.transform
        backPosHelper.parent = backLookAtHelper
        
        genHelpers.extend([backLookAtHelper, backTarget, backPosHelper])
        
        # 뒤쪽 자켓 패널 본 생성
        backPanelBone = self.bone.create_nub_bone(backPanelName, self.boneSize)
        backPanelBone.name = backPanelName
        backPanelBone.transform = backPosHelper.transform
        backPanelBone.parent = inSpine
        self.const.assign_pos_const(backPanelBone, backPosHelper)
        self.const.assign_rot_const(backPanelBone, backPosHelper)
        
        genBones.append(backPanelBone)
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers,
            "FrontPosHelper": frontPosHelper,
            "BackPosHelper": backPosHelper
        }
        
        return result
        
    def create_center_panel(self, inLeftFrontPosHelper, inRightFrontPosHelper, inLeftBackPosHelper, inRightBackPosHelper, inSpine):
        """
        가운데 자켓 패널 본들을 생성합니다 (앞/뒤 2개).
        좌우 포지션 헬퍼를 50:50으로 블렌드합니다.
        
        Args:
            inLeftFrontPosHelper: 왼쪽 앞쪽 포지션 헬퍼
            inRightFrontPosHelper: 오른쪽 앞쪽 포지션 헬퍼
            inLeftBackPosHelper: 왼쪽 뒤쪽 포지션 헬퍼
            inRightBackPosHelper: 오른쪽 뒤쪽 포지션 헬퍼
            inSpine: 척추 본
            
        Returns:
            dict: 생성된 본, 헬퍼
        """
        if not rt.isValidNode(inLeftFrontPosHelper) or not rt.isValidNode(inRightFrontPosHelper) or \
           not rt.isValidNode(inLeftBackPosHelper) or not rt.isValidNode(inRightBackPosHelper) or \
           not rt.isValidNode(inSpine):
            return None
        
        genBones = []
        genHelpers = []
        
        # 기본 이름 생성 (Center 방향)
        baseName = self.name.replace_name_part("RealName", inSpine.name, "JacketPanel")
        centerName = self.name.replace_name_part("Side", baseName, "")
        if self.name.get_name("RealName", inSpine.name)[0].islower():
            centerName = centerName.lower()
        
        # ========== 앞쪽 중앙 패널 생성 ==========
        
        # 앞쪽 중앙 패널 이름
        frontCenterName = self.name.replace_name_part("FrontBack", centerName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        
        # 앞쪽 블렌드 헬퍼 생성
        frontBlendHelperName = self.name.replace_name_part("Type", frontCenterName, self.name.get_name_part_value_by_description("Type", "Position"))
        frontBlendHelper = self.helper.create_point(frontBlendHelperName)
        self.helper.set_shape_to_box(frontBlendHelper)
        frontBlendHelper.transform = inLeftFrontPosHelper.transform
        frontBlendHelper.pos = rt.Point3(0.0, frontBlendHelper.transform.position.y, frontBlendHelper.transform.position.z)
        
        self.align.align_to_last_rot([frontBlendHelper, inLeftFrontPosHelper])
        frontBlendHelper.parent = inSpine
        
        frontLDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        frontLDumHelperName = self.name.replace_name_part("Side", frontLDumHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        frontLDumHelper = self.helper.create_point(frontLDumHelperName)
        self.helper.set_shape_to_box(frontLDumHelper)
        frontLDumHelper.transform = frontBlendHelper.transform
        frontLDumHelper.parent = inLeftFrontPosHelper
        
        frontRDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        frontRDumHelperName = self.name.replace_name_part("Side", frontRDumHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        frontRDumHelper = self.helper.create_point(frontRDumHelperName)
        self.helper.set_shape_to_box(frontRDumHelper)
        frontRDumHelper.transform = frontBlendHelper.transform
        frontRDumHelper.parent = inRightFrontPosHelper
        
        self.const.assign_pos_const_multi(frontBlendHelper, [frontLDumHelper, frontRDumHelper])
        self.const.assign_rot_const_multi(frontBlendHelper, [frontLDumHelper, frontRDumHelper])
        
        genHelpers.extend([frontBlendHelper, frontLDumHelper, frontRDumHelper])
        
        # 앞쪽 중앙 패널 본 생성
        frontCenterBone = self.bone.create_nub_bone(frontCenterName, self.boneSize)
        frontCenterBone.name = frontCenterName
        frontCenterBone.transform = frontBlendHelper.transform
        frontCenterBone.parent = inSpine
        self.const.assign_pos_const(frontCenterBone, frontBlendHelper)
        self.const.assign_rot_const(frontCenterBone, frontBlendHelper)
        
        genBones.append(frontCenterBone)
        
        # ========== 뒤쪽 중앙 패널 생성 ==========
        
        # 뒤쪽 중앙 패널 이름
        backCenterName = self.name.replace_name_part("FrontBack", centerName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        
        # 뒤쪽 블렌드 헬퍼 생성
        backBlendHelperName = self.name.replace_name_part("Type", backCenterName, self.name.get_name_part_value_by_description("Type", "Position"))
        backBlendHelper = self.helper.create_point(backBlendHelperName)
        self.helper.set_shape_to_box(backBlendHelper)
        backBlendHelper.transform = inLeftBackPosHelper.transform
        backBlendHelper.pos = rt.Point3(0.0, backBlendHelper.transform.position.y, backBlendHelper.transform.position.z)
        self.align.align_to_last_rot([backBlendHelper, inLeftBackPosHelper])
        backBlendHelper.parent = inSpine
        
        backLDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        backLDumHelperName = self.name.replace_name_part("Side", backLDumHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        backLDumHelper = self.helper.create_point(backLDumHelperName)
        self.helper.set_shape_to_box(backLDumHelper)
        backLDumHelper.transform = backBlendHelper.transform
        backLDumHelper.parent = inLeftBackPosHelper
        
        backRDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        backRDumHelperName = self.name.replace_name_part("Side", backRDumHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        backRDumHelper = self.helper.create_point(backRDumHelperName)
        self.helper.set_shape_to_box(backRDumHelper)
        backRDumHelper.transform = backBlendHelper.transform
        backRDumHelper.parent = inRightBackPosHelper
        
        self.const.assign_pos_const_multi(backBlendHelper, [backLDumHelper, backRDumHelper])
        self.const.assign_rot_const_multi(backBlendHelper, [backLDumHelper, backRDumHelper])
        
        genHelpers.extend([backBlendHelper, backLDumHelper, backRDumHelper])
        
        # 뒤쪽 중앙 패널 본 생성
        backCenterBone = self.bone.create_nub_bone(backCenterName, self.boneSize)
        backCenterBone.name = backCenterName
        backCenterBone.transform = backBlendHelper.transform
        backCenterBone.parent = inSpine
        self.const.assign_pos_const(backCenterBone, backBlendHelper)
        self.const.assign_rot_const(backCenterBone, backBlendHelper)
        
        genBones.append(backCenterBone)
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers
        }
        
        return result
        
    def create_bones(self, inLClavicle, inLUpperArm, inRClavicle, inRUpperArm, inSpine, inNeck):
        """
        자켓 패널 본들을 생성합니다 (총 6개: 좌앞, 좌뒤, 우앞, 우뒤, 중앙앞, 중앙뒤).
        
        Args:
            inLClavicle: 왼쪽 쇄골 본
            inLUpperArm: 왼쪽 상완 본
            inRClavicle: 오른쪽 쇄골 본
            inRUpperArm: 오른쪽 상완 본
            inSpine: 척추 본
            inNeck: 목 본
            
        Returns:
            BoneChain: 생성된 본 체인
        """
        if not rt.isValidNode(inLClavicle) or not rt.isValidNode(inLUpperArm) or \
           not rt.isValidNode(inRClavicle) or not rt.isValidNode(inRUpperArm) or \
           not rt.isValidNode(inSpine) or not rt.isValidNode(inNeck):
            return None
        
        allBones = []
        allHelpers = []
        
        # 1. 왼쪽 패널 생성 (앞, 뒤)
        leftResult = self.create_side_panel(inLClavicle, inLUpperArm, inSpine, inNeck)
        if leftResult:
            allBones.extend(leftResult["Bones"])
            allHelpers.extend(leftResult["Helpers"])
            leftFrontPosHelper = leftResult["FrontPosHelper"]
            leftBackPosHelper = leftResult["BackPosHelper"]
        else:
            return None
        
        # 2. 오른쪽 패널 생성 (앞, 뒤)
        rightResult = self.create_side_panel(inRClavicle, inRUpperArm, inSpine, inNeck)
        if rightResult:
            allBones.extend(rightResult["Bones"])
            allHelpers.extend(rightResult["Helpers"])
            rightFrontPosHelper = rightResult["FrontPosHelper"]
            rightBackPosHelper = rightResult["BackPosHelper"]
        else:
            return None
        
        # 3. 중앙 패널 생성 (앞, 뒤)
        centerResult = self.create_center_panel(leftFrontPosHelper, rightFrontPosHelper, 
                                                leftBackPosHelper, rightBackPosHelper, inSpine)
        if centerResult:
            allBones.extend(centerResult["Bones"])
            allHelpers.extend(centerResult["Helpers"])
        else:
            return None
        
        self.genBones = allBones
        self.genHelpers = allHelpers
        
        result = {
            "Bones": allBones,
            "Helpers": allHelpers,
            "SourceBones": [inLClavicle, inLUpperArm, inRClavicle, inRUpperArm, inSpine, inNeck],
            "Parameters": []
        }
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
        
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """
        BoneChain으로부터 자켓 패널 본들을 재생성합니다.
        
        Args:
            inBoneChain: 기존 본 체인
            
        Returns:
            BoneChain: 재생성된 본 체인
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
        
        inBoneChain.delete()
        
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        if len(sourceBones) < 6 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]) or \
           not rt.isValidNode(sourceBones[2]) or not rt.isValidNode(sourceBones[3]) or \
           not rt.isValidNode(sourceBones[4]) or not rt.isValidNode(sourceBones[5]):
            return None
        
        lClavicle = sourceBones[0]
        lUpperArm = sourceBones[1]
        rClavicle = sourceBones[2]
        rUpperArm = sourceBones[3]
        spine = sourceBones[4]
        neck = sourceBones[5]
        
        return self.create_bones(lClavicle, lUpperArm, rClavicle, rUpperArm, spine, neck)

