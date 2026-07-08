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
    """어깨를 들어올릴 때 자켓이 따라 올라가는 효과를 내는 자켓 패널 본을 생성하는 클래스.

    쇄골 기반의 좌우 패널 4개와 좌우를 블렌드한 중앙 패널 2개를 만든다.
    """

    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, alignService=None):
        """JacketPanel 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 서비스. None이면 새로 생성한다.
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
        
    def reset(self):
        """클래스의 작업 데이터를 초기 상태로 되돌린다.

        서비스가 아닌 클래스 자체의 작업 데이터만 초기화한다.
        """
        self.boneSize = 2.0
        
        self.genBones = []
        self.genHelpers = []
        
    
    def create_side_panel(self, inClavicle, inUpperArm, inSpine, inNeck, inWidthScale=1.65, inForwardScale=0.5, inBackwardScale=0.5, inHeightScale=0.67):
        """한쪽(좌 또는 우) 자켓 패널 본을 앞·뒤 2개 생성한다.

        쇄골에 연결된 LookAt 헬퍼와 척추에 연결된 타겟 헬퍼로 패널 방향을 만들고,
        포지션 헬퍼에 위치 제약된 패널 본을 생성한다.

        Args:
            inClavicle (rt.Node): 쇄골 본
            inUpperArm (rt.Node): 상완 본. 쇄골 길이 계산에 사용된다.
            inSpine (rt.Node): 척추 본
            inNeck (rt.Node): 목 본. 척추 길이 계산에 사용된다.
            inWidthScale (float): 쇄골 길이 기반 너비 스케일
            inForwardScale (float): 앞쪽 방향 스케일
            inBackwardScale (float): 뒤쪽 방향 스케일
            inHeightScale (float): 높이 스케일

        Returns:
            dict | None: 생성 결과. 유효하지 않은 노드가 있으면 None
                - Bones (list[rt.Node]): 앞·뒤 패널 본
                - Helpers (list[rt.Node]): 생성된 헬퍼들
                - FrontPosHelper (rt.Node): 앞쪽 포지션 헬퍼
                - BackPosHelper (rt.Node): 뒤쪽 포지션 헬퍼
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
        self.anim.move_local(frontLookAtHelper, clavicleLength * sideDir / inWidthScale, 0.0, 0.0)
        # 로컬 Y축 방향으로 spine길이 * inForwardScale 이동(앞쪽)
        self.anim.move_local(frontLookAtHelper, 0.0, spineLength * fwdDir * sideDir * inForwardScale, 0.0)
        self.align.align_to_last_rot([frontLookAtHelper, inSpine])
        
        # 임시 타겟 생성하여 초기 회전 설정
        tempTarget = self.helper.create_point("Temp")
        tempTarget.transform = frontLookAtHelper.transform
        self.anim.move_local(tempTarget, -spineLength * inHeightScale, 0.0, 0.0)
        
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
        self.anim.move_local(frontTarget, spineLength * inHeightScale, 0.0, 0.0)
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
        self.anim.move_local(backLookAtHelper, clavicleLength * sideDir / inWidthScale, 0.0, 0.0)
        # 로컬 -Y축 방향으로 spine길이 * inBackwardScale 이동 (뒤쪽)
        self.anim.move_local(backLookAtHelper, 0.0, -spineLength * fwdDir * sideDir * inBackwardScale, 0.0)
        self.align.align_to_last_rot([backLookAtHelper, inSpine])
        
        # 임시 타겟 생성하여 초기 회전 설정
        tempTarget = self.helper.create_point("Temp")
        tempTarget.transform = backLookAtHelper.transform
        self.anim.move_local(tempTarget, -spineLength * inHeightScale, 0.0, 0.0)
        
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
        self.anim.move_local(backTarget, spineLength * inHeightScale, 0.0, 0.0)
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
        
        genBones.append(backPanelBone)
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers,
            "FrontPosHelper": frontPosHelper,
            "BackPosHelper": backPosHelper
        }
        
        return result
        
    def create_center_panel(self, inLeftFrontPosHelper, inRightFrontPosHelper, inLeftBackPosHelper, inRightBackPosHelper, inSpine, inFrontCenterPushScale=1.1, inBackCenterPushScale=1.1):
        """가운데 자켓 패널 본을 앞·뒤 2개 생성한다.

        좌우 포지션 헬퍼를 50:50으로 블렌드하고, 패널이 몸통 안으로
        파고들지 않도록 클램프 위치 스크립트를 할당한다.

        Args:
            inLeftFrontPosHelper (rt.Node): 왼쪽 앞쪽 포지션 헬퍼
            inRightFrontPosHelper (rt.Node): 오른쪽 앞쪽 포지션 헬퍼
            inLeftBackPosHelper (rt.Node): 왼쪽 뒤쪽 포지션 헬퍼
            inRightBackPosHelper (rt.Node): 오른쪽 뒤쪽 포지션 헬퍼
            inSpine (rt.Node): 척추 본
            inFrontCenterPushScale (float): 앞쪽 중앙 패널 Y축 푸시 스케일
            inBackCenterPushScale (float): 뒤쪽 중앙 패널 Y축 푸시 스케일

        Returns:
            dict | None: 생성 결과. 유효하지 않은 노드가 있으면 None
                - Bones (list[rt.Node]): 앞·뒤 중앙 패널 본
                - Helpers (list[rt.Node]): 생성된 헬퍼들
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
        frontBlendHelper.pos = rt.Point3(0.0, frontBlendHelper.transform.position.y*inFrontCenterPushScale, frontBlendHelper.transform.position.z)
        
        self.align.align_to_last_rot([frontBlendHelper, inLeftFrontPosHelper])
        frontBlendHelper.parent = inSpine
        
        # 앞쪽 헬퍼가 몸통 안으로 들어가지 않도록 하는 헬퍼 생성
        frontClampHelperName = self.name.replace_name_part("Type", frontCenterName, self.name.get_name_part_value_by_description("Type", "Target"))
        frontClampHelper = self.helper.create_point(frontClampHelperName)
        self.helper.set_shape_to_cross(frontClampHelper)
        frontClampHelper.transform = frontBlendHelper.transform
        frontClampHelper.parent = inSpine
        
        # 왼쪽 패널과 링크된 앞쪽 헬퍼 생성
        frontLDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        frontLDumHelperName = self.name.replace_name_part("Side", frontLDumHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        frontLDumHelperName = self.name.replace_name_part("FrontBack", frontLDumHelperName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        frontLDumHelper = self.helper.create_point(frontLDumHelperName)
        self.helper.set_shape_to_box(frontLDumHelper)
        frontLDumHelper.transform = frontBlendHelper.transform
        frontLDumHelper.parent = inLeftFrontPosHelper
        
        # 오른쪽 패널과 링크된 앞쪽 헬퍼 생성
        frontRDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        frontRDumHelperName = self.name.replace_name_part("Side", frontRDumHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        frontRDumHelperName = self.name.replace_name_part("FrontBack", frontRDumHelperName, self.name.get_name_part_value_by_description("FrontBack", "Forward"))
        frontRDumHelper = self.helper.create_point(frontRDumHelperName)
        self.helper.set_shape_to_box(frontRDumHelper)
        frontRDumHelper.transform = frontBlendHelper.transform
        frontRDumHelper.parent = inRightFrontPosHelper
        
        self.const.assign_pos_const_multi(frontBlendHelper, [frontLDumHelper, frontRDumHelper])
        self.const.assign_rot_const_multi(frontBlendHelper, [frontLDumHelper, frontRDumHelper])
        
        genHelpers.extend([frontBlendHelper, frontLDumHelper, frontRDumHelper, frontClampHelper])
        
        # 앞쪽 중앙 패널 본 생성
        frontCenterBone = self.bone.create_nub_bone(frontCenterName, self.boneSize)
        frontCenterBone.name = frontCenterName
        frontCenterBone.transform = frontBlendHelper.transform
        frontCenterBone.parent = inSpine
        clampPosConst = self.const.assign_pos_script_controller(frontCenterBone)
        clampPosConst.AddNode("Clamp", frontClampHelper)
        clampPosConst.AddNode("Target", frontBlendHelper)
        clampPosConst.script = "tm = Target.transform * (inverse Clamp.transform)\nyPos = amin 0.0 tm.position.y\n[tm.position.x, yPos, tm.position.z]\n"
        
        genBones.append(frontCenterBone)
        
        # ========== 뒤쪽 중앙 패널 생성 ==========
        
        # 뒤쪽 중앙 패널 이름
        backCenterName = self.name.replace_name_part("FrontBack", centerName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        
        # 뒤쪽 블렌드 헬퍼 생성
        backBlendHelperName = self.name.replace_name_part("Type", backCenterName, self.name.get_name_part_value_by_description("Type", "Position"))
        backBlendHelper = self.helper.create_point(backBlendHelperName)
        self.helper.set_shape_to_box(backBlendHelper)
        backBlendHelper.transform = inLeftBackPosHelper.transform
        backBlendHelper.pos = rt.Point3(0.0, backBlendHelper.transform.position.y*inBackCenterPushScale, backBlendHelper.transform.position.z)
        self.align.align_to_last_rot([backBlendHelper, inLeftBackPosHelper])
        backBlendHelper.parent = inSpine
        
        # 뒤쪽 헬퍼가 몸통 안으로 들어가지 않도록 하는 헬퍼 생성
        backClampHelperName = self.name.replace_name_part("Type", backCenterName, self.name.get_name_part_value_by_description("Type", "Target"))
        backClampHelper = self.helper.create_point(backClampHelperName)
        self.helper.set_shape_to_cross(backClampHelper)
        backClampHelper.transform = backBlendHelper.transform
        backClampHelper.parent = inSpine
        
        # 왼쪽 패널과 링크된 뒤쪽 헬퍼 생성
        backLDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        backLDumHelperName = self.name.replace_name_part("Side", backLDumHelperName, self.name.get_name_part_value_by_description("Side", "Left"))
        backLDumHelperName = self.name.replace_name_part("FrontBack", backLDumHelperName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        backLDumHelper = self.helper.create_point(backLDumHelperName)
        self.helper.set_shape_to_box(backLDumHelper)
        backLDumHelper.transform = backBlendHelper.transform
        backLDumHelper.parent = inLeftBackPosHelper
        
        # 오른쪽 패널과 링크된 뒤쪽 헬퍼 생성
        backRDumHelperName = self.name.replace_name_part("Type", baseName, self.name.get_name_part_value_by_description("Type", "Dummy"))
        backRDumHelperName = self.name.replace_name_part("Side", backRDumHelperName, self.name.get_name_part_value_by_description("Side", "Right"))
        backRDumHelperName = self.name.replace_name_part("FrontBack", backRDumHelperName, self.name.get_name_part_value_by_description("FrontBack", "Backward"))
        backRDumHelper = self.helper.create_point(backRDumHelperName)
        self.helper.set_shape_to_box(backRDumHelper)
        backRDumHelper.transform = backBlendHelper.transform
        backRDumHelper.parent = inRightBackPosHelper
        
        self.const.assign_pos_const_multi(backBlendHelper, [backLDumHelper, backRDumHelper])
        self.const.assign_rot_const_multi(backBlendHelper, [backLDumHelper, backRDumHelper])
        
        genHelpers.extend([backBlendHelper, backLDumHelper, backRDumHelper, backClampHelper])
        
        # 뒤쪽 중앙 패널 본 생성
        backCenterBone = self.bone.create_nub_bone(backCenterName, self.boneSize)
        backCenterBone.name = backCenterName
        backCenterBone.transform = backBlendHelper.transform
        backCenterBone.parent = inSpine
        clampPosConst = self.const.assign_pos_script_controller(backCenterBone)
        clampPosConst.AddNode("Clamp", backClampHelper)
        clampPosConst.AddNode("Target", backBlendHelper)
        clampPosConst.script = "tm = Target.transform * (inverse Clamp.transform)\nyPos = amax 0.0 tm.position.y\n[tm.position.x, yPos, tm.position.z]\n"
        
        genBones.append(backCenterBone)
        
        result = {
            "Bones": genBones,
            "Helpers": genHelpers
        }
        
        return result
        
    def create_bones(self, inLClavicle, inLUpperArm, inRClavicle, inRUpperArm, inSpine, inNeck, inWidthScale=1.65, inForwardScale=0.5, inBackwardScale=0.5, inHeightScale=0.67, inFrontCenterPushScale=1.1, inBackCenterPushScale=1.1):
        """자켓 패널 본 6개(좌앞·좌뒤·우앞·우뒤·중앙앞·중앙뒤)를 생성한다.

        Args:
            inLClavicle (rt.Node): 왼쪽 쇄골 본
            inLUpperArm (rt.Node): 왼쪽 상완 본
            inRClavicle (rt.Node): 오른쪽 쇄골 본
            inRUpperArm (rt.Node): 오른쪽 상완 본
            inSpine (rt.Node): 척추 본
            inNeck (rt.Node): 목 본
            inWidthScale (float): 쇄골 길이 기반 너비 스케일
            inForwardScale (float): 앞쪽 방향 스케일
            inBackwardScale (float): 뒤쪽 방향 스케일
            inHeightScale (float): 높이 스케일
            inFrontCenterPushScale (float): 앞쪽 중앙 패널 Y축 푸시 스케일
            inBackCenterPushScale (float): 뒤쪽 중앙 패널 Y축 푸시 스케일

        Returns:
            BoneChain | None: 생성된 자켓 패널 본 체인. 노드가 유효하지 않거나 패널 생성에 실패하면 None
        """
        if not rt.isValidNode(inLClavicle) or not rt.isValidNode(inLUpperArm) or \
           not rt.isValidNode(inRClavicle) or not rt.isValidNode(inRUpperArm) or \
           not rt.isValidNode(inSpine) or not rt.isValidNode(inNeck):
            return None
        
        allBones = []
        allHelpers = []
        
        # 1. 왼쪽 패널 생성 (앞, 뒤)
        leftResult = self.create_side_panel(inLClavicle, inLUpperArm, inSpine, inNeck, inWidthScale, inForwardScale, inBackwardScale, inHeightScale)
        if leftResult:
            allBones.extend(leftResult["Bones"])
            allHelpers.extend(leftResult["Helpers"])
            leftFrontPosHelper = leftResult["FrontPosHelper"]
            leftBackPosHelper = leftResult["BackPosHelper"]
        else:
            return None
        
        # 2. 오른쪽 패널 생성 (앞, 뒤)
        rightResult = self.create_side_panel(inRClavicle, inRUpperArm, inSpine, inNeck, inWidthScale, inForwardScale, inBackwardScale, inHeightScale)
        if rightResult:
            allBones.extend(rightResult["Bones"])
            allHelpers.extend(rightResult["Helpers"])
            rightFrontPosHelper = rightResult["FrontPosHelper"]
            rightBackPosHelper = rightResult["BackPosHelper"]
        else:
            return None
        
        # 3. 중앙 패널 생성 (앞, 뒤)
        centerResult = self.create_center_panel(leftFrontPosHelper, rightFrontPosHelper, 
                                                leftBackPosHelper, rightBackPosHelper, inSpine, inFrontCenterPushScale, inBackCenterPushScale)
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
            "Parameters": [inWidthScale, inForwardScale, inBackwardScale, inHeightScale, inFrontCenterPushScale, inBackCenterPushScale]
        }
        
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
        
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 자켓 패널 본들을 재생성한다.

        Args:
            inBoneChain (BoneChain): 자켓 패널 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 BoneChain. 체인이 비었거나 소스 본이 유효하지 않으면 None
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
        
        # 파라미터 추출
        if len(parameters) >= 6:
            widthScale = parameters[0]
            forwardScale = parameters[1]
            backwardScale = parameters[2]
            heightScale = parameters[3]
            frontCenterPushScale = parameters[4]
            backCenterPushScale = parameters[5]
        else:
            # 기본값
            widthScale = 1.65
            forwardScale = 0.5
            backwardScale = 0.5
            heightScale = 0.67
            frontCenterPushScale = 1.1
            backCenterPushScale = 1.1
        
        return self.create_bones(lClavicle, lUpperArm, rClavicle, rUpperArm, spine, neck,
                                 widthScale, forwardScale, backwardScale, heightScale,
                                 frontCenterPushScale, backCenterPushScale)

