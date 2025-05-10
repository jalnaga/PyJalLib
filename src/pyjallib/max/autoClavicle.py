#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
자동 쇄골(AutoClavicle) 모듈 - 3ds Max용 자동화된 쇄골 기능 제공
원본 MAXScript의 autoclavicle.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt


class AutoClavicle:
    """
    자동 쇄골(AutoClavicle) 관련 기능을 제공하는 클래스.
    MAXScript의 _AutoClavicleBone 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, jalService=None):
        """
        클래스 초기화
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 서비스 (제공되지 않으면 새로 생성)
            jalService: jal 서비스 인스턴스 (제공되지 않으면 전역 jal 사용)
        """
        # jalService가 제공되면 사용, 그렇지 않으면 전역 jal 사용
        if jalService is not None:
            jal = jalService
        else:
            try:
                import __main__
                jal = __main__.jal
            except (ImportError, AttributeError) as e:
                raise RuntimeError("jal 서비스를 찾을 수 없습니다. __main__.jal이 설정되어 있는지 확인하거나, jalService 인자를 전달하세요.") from e
        
        self.name = jal.name
        self.anim = jal.anim
        self.helper = jal.helper
        self.bone = jal.bone
        self.const = jal.constraint
        self.bip = jal.bip
        
        self.boneSize = 2.0
        self.clavicle = None
        self.upperArm = None
        self.liftScale = 0.8
        self.genBones = []
        self.genHelpers = []
    
    def create_bones(self, inClavicle, inUpperArm, liftScale=0.8):
        """
        자동 쇄골 뼈를 생성하고 설정합니다.
        
        Args:
            inClavicle: 쇄골 뼈 객체
            inUpperArm: 상완 뼈 객체
            liftScale: 들어올림 스케일 (기본값: 0.8)
            
        Returns:
            생성된 자동 쇄골 뼈대 배열
        """
        if not rt.isValidNode(inClavicle) or not rt.isValidNode(inUpperArm):
            return False
        
        self.clavicle = inClavicle
        self.upperArm = inUpperArm
        self.liftScale = liftScale
        self.genBones = []
        self.genHelpers = []
        
        # 쇄골과 상완 사이의 거리 계산
        clavicleLength = rt.distance(inClavicle, inUpperArm)
        
        # 임시 헬퍼 포인트 생성
        tempHelperA = rt.Point()
        tempHelperB = rt.Point()
        tempHelperA.transform = inClavicle.transform
        tempHelperB.transform = inClavicle.transform
        self.anim.move_local(tempHelperB, clavicleLength/2.0, 0.0, 0.0)
        
        # 자동 쇄골 이름 생성 및 뼈대 생성
        autoClavicleName = self.name.replace_name_part("RealName", inClavicle.name, "AutoClavicle")
        autoClavicleBones = self.bone.create_bone(
            [tempHelperA, tempHelperB], 
            autoClavicleName, 
            end=True, 
            delPoint=True, 
            parent=False, 
            size=self.boneSize
        )
        autoClavicleBones[0].transform = inClavicle.transform
        self.anim.move_local(autoClavicleBones[0], clavicleLength/2.0, 0.0, 0.0)
        autoClavicleBones[0].parent = inClavicle
        self.genBones.extend(autoClavicleBones)
        
        # LookAt 설정
        ikGoal = self.helper.create_point(autoClavicleName, boxToggle=False, crossToggle=True)
        ikGoal.transform = autoClavicleBones[1].transform
        ikGoal.name = self.name.replace_name_part("Type", autoClavicleName, "T")
        autClavicleLookAtConst = self.const.assign_lookat(autoClavicleBones[0], ikGoal)
        autClavicleLookAtConst.upnode_world = False
        autClavicleLookAtConst.pickUpNode = inClavicle
        autClavicleLookAtConst.lookat_vector_length = 0.0
        self.genHelpers.append(ikGoal)
        
        # 회전 헬퍼 포인트 생성
        autoClavicleRotHelper = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, "Rot"))
        autoClavicleRotHelper.transform = autoClavicleBones[0].transform
        autoClavicleRotHelper.parent = inClavicle
        self.genHelpers.append(autoClavicleRotHelper)
        
        # 타겟 헬퍼 포인트 생성 (쇄골과 상완용)
        rotTargetClavicle = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, "T"))
        rotTargetClavicle.transform = inClavicle.transform
        self.anim.move_local(rotTargetClavicle, clavicleLength, 0.0, 0.0)
        self.genHelpers.append(rotTargetClavicle)
        
        rotTargetUpperArm = self.helper.create_point(self.name.replace_name_part("Type", autoClavicleName, "T"))
        rotTargetUpperArm.name = self.name.add_suffix_to_real_name(rotTargetUpperArm.name, "UArm")
        rotTargetUpperArm.transform = inUpperArm.transform
        self.anim.move_local(rotTargetUpperArm, (clavicleLength/2.0)*liftScale, 0.0, 0.0)
        self.genHelpers.append(rotTargetUpperArm)
        
        # 부모 설정
        rotTargetClavicle.parent = inClavicle
        rotTargetUpperArm.parent = inUpperArm
        
        # LookAt 제약 설정
        # self.const.assign_lookat_multi(autoClavicleRotHelper, [rotTargetClavicle, rotTargetUpperArm])
        lookAtConst = self.const.assign_scripted_lookat(autoClavicleRotHelper, [rotTargetClavicle, rotTargetUpperArm])["lookAt"]
        
        lookAtConst.upnode_world = False
        lookAtConst.pickUpNode = inClavicle
        lookAtConst.lookat_vector_length = 0.0
        
        ikGoal.parent = autoClavicleRotHelper
        
        return autoClavicleBones
    
    def get_bones(self):
        """
        자동 쇄골 뼈를 가져옵니다.
        
        Args:
            inClavicle: 쇄골 뼈 객체
            inUpperArm: 상완 뼈 객체
            
        Returns:
            자동 쇄골 뼈대 배열
        """
        if len(self.genBones) == 0:
            return []
        
        validResults = []
        for item in self.genBones:
            validResults.append(rt.isValidNode(item))
        if not all(validResults):
            return []
        
        return self.genBones
    
    def get_helpers(self):
        """
        자동 쇄골 헬퍼를 가져옵니다.
        
        Args:
            inClavicle: 쇄골 뼈 객체
            inUpperArm: 상완 뼈 객체
            
        Returns:
            자동 쇄골 헬퍼 배열
        """
        if len(self.genHelpers) == 0:
            return []
        
        validResults = []
        for item in self.genHelpers:
            validResults.append(rt.isValidNode(item))
        if not all(validResults):
            return []
        
        return self.genHelpers
    
    def delete(self):
        """
        자동 쇄골 뼈와 헬퍼를 삭제합니다.
        
        Args:
            None
            
        Returns:
            None
        """
        rt.delete(self.genBones)
        rt.delete(self.genHelpers)
        
        self.genBones = []
        self.genHelpers = []
        
    def update_liftScale(self, liftScale=0.8):
        """
        자동 쇄골 뼈의 들어올림 스케일을 업데이트합니다.
        
        Args:
            liftScale: 들어올림 스케일 (기본값: 0.8)
            
        Returns:
            None
        """
        if len(self.genBones) == 0:
            return False
        
        self.delete()
        self.create_bones(self.clavicle, self.upperArm, liftScale=liftScale)
    