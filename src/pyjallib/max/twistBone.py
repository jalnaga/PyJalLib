#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
트위스트 뼈대(Twist Bone) 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공
원본 MAXScript의 twistBone.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .constraint import Constraint
from .bip import Bip
from .bone import Bone


class TwistBone:
    """
    트위스트 뼈대(Twist Bone) 관련 기능을 제공하는 클래스.
    MAXScript의 _TwistBone 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, bipService=None, boneService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: 바이페드 서비스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # Ensure dependent services use the potentially newly created instances
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(animService=self.anim, nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        
        # 표현식 초기화
        self._init_expressions()
    
    def _init_expressions(self):
        """표현식 초기화"""
        # 허벅지(Thigh) 표현식
        self.thighExpression = (
            "try(\n"
            "TM=Limb.transform*inverse Limb.parent.transform\n"
            "vector=normalize (cross -TM.row1 [1,0,0])\n"
            "angle=acos -(normalize TM.row1).x\n"
            "(quat 0 1 0 0)*(quat angle vector)*inverse TM.rotation)\n"
            "catch((quat 0 0 0 1))"
        )
        
        # 허벅지 추가 표현식
        self.thighExtraExpression = (
            "try(\n"
            "(Limb.transform*inverse LimbParent.transform).rotation\n"
            ")catch((quat 0 0 0 1))"
        )
        
        # 종아리(Calf) 표현식
        self.calfExpression = (
            "try(\n"
            "TM=Limb.transform*inverse Limb.parent.transform\n"
            "vector=normalize (cross TM.row1 [1,0,0])\n"
            "angle=acos (normalize TM.row1).x\n"
            "TM.rotation*(quat -angle vector))\n"
            "catch((quat 0 0 0 1))"
        )
        
        # 종아리 추가 표현식
        self.calfExtraExpression = (
            "try(dependson TB\n"
            "TB.rotation.controller[1].value\n"
            ")catch((quat 0 0 0 1))"
        )
        
        # 상완(Upper Arm) 표현식
        self.upperArmExpression = (
            "try(\n"
            "TM=Limb.transform*inverse Limb.parent.transform\n"
            "vector=normalize (cross TM.row1 [1,0,0])\n"
            "angle=acos (normalize TM.row1).x\n"
            "(quat angle vector)*inverse TM.rotation)\n"
            "catch((quat 0 0 0 1))"
        )
        
        # 상완 추가 표현식
        self.upperArmExtraExpression = (
            "try(\n"
            "(Limb.transform*inverse LimbParent.transform).rotation\n"
            ")catch((quat 0 0 0 1))"
        )
        
        # 오른쪽 전완(Forearm) 표현식
        self.rForeArmExpression = (
            "try(\n"
            "TM=(matrix3 [1,0,0] [0,0,-1] [0,1,0] [0,0,0])*Limb.transform*inverse Limb.parent.transform\n"
            "vector=normalize (cross TM.row1 [1,0,0])\n"
            "angle=acos (normalize TM.row1).x\n"
            "TM.rotation*(quat -angle vector))\n"
            "catch((quat 0 0 0 1))"
        )
        
        # 왼쪽 전완(Forearm) 표현식
        self.lForeArmExpression = (
            "try(\n"
            "TM=(matrix3 [1,0,0] [0,0,1] [0,-1,0] [0,0,0])*Limb.transform*inverse Limb.parent.transform\n"
            "vector=normalize (cross TM.row1 [1,0,0])\n"
            "angle=acos (normalize TM.row1).x\n"
            "TM.rotation*(quat -angle vector))\n"
            "catch((quat 0 0 0 1))"
        )
        
        # 전완 추가 표현식
        self.foreArmExtraExpression = (
            "try(dependson TB\n"
            "TB.rotation.controller[1].value\n"
            ")catch((quat 0 0 0 1))"
        )
    
    def create_bones(self, inObj, inChild, inTwistNum, inExpression, inExtraExpression, inControllerLimb, inWeightVar):
        """
        트위스트 뼈대 체인 생성
        
        Args:
            inObj: 시작 객체
            inChild: 끝 객체
            inTwistNum: 트위스트 뼈대 개수
            inExpression: 기본 회전 표현식
            inExtraExpression: 추가 회전 표현식
            inControllerLimb: 컨트롤러 대상 팔다리
            inWeightVar: 가중치
            
        Returns:
            생성된 트위스트 뼈대 체인 배열
        """
        Limb = inObj
        distanceVar = rt.distance(Limb, inChild)
        facingDirVec = inChild.transform.position - inObj.transform.position
        inObjXAxisVec = inObj.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
        TBExpression = inExpression
        ControllerLimb = inControllerLimb
        weightVar = inWeightVar
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "twist")
        TwistBone = self.bone.create_nub_bone(boneName, 2)
        TwistBone.name = self.name.replace_name_part("Index", boneName, "0")
        TwistBone.name = self.name.remove_name_part("Nub", TwistBone.name)
        TwistBone.transform = Limb.transform
        TwistBone.parent = Limb
        
        # 회전 컨트롤러 설정
        TBRotListController = self.const.assign_rot_list(TwistBone)
        TBController = rt.Rotation_Script()
        TBController.addNode("Limb", ControllerLimb)
        TBController.setExpression(TBExpression)
        
        rt.setPropertyController(TBRotListController, "Available", TBController)
        TBRotListController.delete(1)
        TBRotListController.setActive(TBRotListController.count)
        TBRotListController.weight[0] = weightVar
        
        boneChainArray.append(TwistBone)
        
        # 추가 회전 컨트롤러 설정
        TBExtraController = rt.Rotation_Script()
        if rt.matchPattern(inExtraExpression, pattern="*\nTB.*"):
            TBExtraController.addNode("TB", TwistBone)
        else:
            TBExtraController.addNode("Limb", Limb)
            TBExtraController.addNode("LimbParent", TwistBone)
        TBExtraController.setExpression(inExtraExpression)
        
        PrevTBE = TwistBone
        
        # 추가 트위스트 뼈대 생성 (2개 이상인 경우)
        if inTwistNum > 1:
            for j in range(2, inTwistNum):
                TwistBoneExtra = self.bone.create_nub_bone(boneName, 2)
                TwistBoneExtra.name = self.name.remove_name_part("Nub", TwistBoneExtra.name)
                matAux = rt.matrix3(1)
                matAux.position = rt.Point3(distanceVar/inTwistNum*distanceDir, 0, 0)
                TwistBoneExtra.transform = matAux * PrevTBE.transform
                TwistBoneExtra.name = self.name.replace_name_part("Index", boneName, str(j-1))
                TwistBoneExtra.parent = PrevTBE
                
                # 회전 컨트롤러 설정
                TBExtraRotListController = self.const.assign_rot_list(TwistBoneExtra)
                rt.setPropertyController(TBExtraRotListController, "Available", TBExtraController)
                TBExtraRotListController.delete(1)
                TBExtraRotListController.setActive(TBExtraRotListController.count)
                TBExtraRotListController.weight[0] = 100 / (inTwistNum - 1)
                
                PrevTBE = TwistBoneExtra
                boneChainArray.append(TwistBoneExtra)
            
            # 마지막 트위스트 뼈대 생성
            TwistBoneEnd = self.bone.create_nub_bone(boneName, 2)
            TwistBoneEnd.name = self.name.remove_name_part("Nub", TwistBoneEnd.name)
            matAux = rt.matrix3(1)
            matAux.position = rt.Point3(distanceVar/inTwistNum*distanceDir, 0, 0)
            TwistBoneEnd.transform = matAux * PrevTBE.transform
            TwistBoneEnd.name = self.name.replace_name_part("Index", boneName, str(inTwistNum-1))
            TwistBoneEnd.parent = inObj
            
            boneChainArray.append(TwistBoneEnd)
        
        return boneChainArray
    
    def reorder_bones(self, inBoneChainArray, inObj, inChild):
        """
        뼈대 체인의 순서 재배치
        
        Args:
            inBoneChainArray: 재배치할 뼈대 체인 배열
            
        Returns:
            재배치된 뼈대 체인 배열
        """
        boneChainArray = rt.deepcopy(inBoneChainArray)
        returnBoneArray = []
        
        # 첫 번째와 마지막 뼈대 가져오기
        firstBone = boneChainArray[0]
        lastBone = boneChainArray[-1]
        returnBoneArray.append(lastBone)
        
        distanceVar = rt.distance(inObj, inChild)/(len(boneChainArray))
        facingDirVec = inChild.transform.position - inObj.transform.position
        inObjXAxisVec = inObj.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        
            
        if len(boneChainArray) > 1:
            self.anim.move_local(firstBone, distanceVar*distanceDir, 0, 0)
            self.anim.move_local(lastBone, -distanceVar*distanceDir*(len(boneChainArray)-1), 0, 0)
            lastBone.transform = inObj.transform
        
        for i in range(0, len(boneChainArray)-1):
            returnBoneArray.append(boneChainArray[i])
        
        # 새로운 순서대로 이름 재설정
        for i in range(len(returnBoneArray)):
            returnBoneArray[i].name = self.name.replace_Index(returnBoneArray[i].name, str(i+1))
        
        return returnBoneArray
    
    def create_upperArm_type(self, inObj, inChild, inTwistNum):
        """
        상완(Upper Arm) 타입의 트위스트 뼈대 생성
        
        Args:
            inObj: 상완 뼈대 객체
            inTwistNum: 트위스트 뼈대 개수
            
        Returns:
            생성된 트위스트 뼈대 체인 또는 False(실패 시)
        """
        if inObj.parent is None or inObj.children.count == 0:
            return False
        
        weightVal = 100.0
        controllerLimb = inChild
        
        genBones = self.create_bones(
            inObj,
            controllerLimb,
            inTwistNum,
            self.upperArmExpression,
            self.upperArmExtraExpression,
            inObj,
            weightVal
        )
        
        returnVal = {
            "Bones": genBones,
            "Type": "upperArm",
            "Parent": inObj,
            "Limb": controllerLimb,
            "TwistNum": inTwistNum,
            "Weight": weightVal
        }
        
        return returnVal
    
    def create_foreArm_type(self, inObj, inChild, inTwistNum, reorder=True, side="Left"):
        """
        전완(Forearm) 타입의 트위스트 뼈대 생성
        
        Args:
            inObj: 전완 뼈대 객체
            inTwistNum: 트위스트 뼈대 개수
            side: 좌/우측 ("left" 또는 "right", 기본값: "left")
            
        Returns:
            생성된 트위스트 뼈대 체인 또는 False(실패 시)
        """
        if inObj.parent is None or inObj.children.count == 0:
            return False
        
        controllerLimb = inChild
        weightVal = 100.0
        
        # 좌/우측에 따른 표현식 선택
        TBExpression = self.lForeArmExpression if side == "Left" else self.rForeArmExpression
        
        if inTwistNum > 1:
            weightVal = 100 / (inTwistNum - 1)
            
        createdBones = self.create_bones(
            inObj,
            controllerLimb,
            inTwistNum,
            TBExpression,
            self.foreArmExtraExpression,
            controllerLimb,
            weightVal
        )
        
        genBones = self.reorder_bones(createdBones, inObj, inChild) if reorder else createdBones
        
        returnVal = {
            "Bones": genBones,
            "Type": "foreArm",
            "Parent": inObj,
            "Limb": controllerLimb,
            "TwistNum": inTwistNum,
            "Weight": weightVal
        }
        
        return returnVal
    
    def create_thigh_type(self, inObj, inChild, inTwistNum):
        """
        허벅지(Thigh) 타입의 트위스트 뼈대 생성
        
        Args:
            inObj: 허벅지 뼈대 객체
            inTwistNum: 트위스트 뼈대 개수
            
        Returns:
            생성된 트위스트 뼈대 체인 또는 False(실패 시)
        """
        if inObj.parent is None or inObj.children.count == 0:
            return False
        
        controllerLimb = inChild
        weightVal = 100
        
        genBones = self.create_bones(
            inObj,
            controllerLimb,
            inTwistNum,
            self.thighExpression,
            self.thighExtraExpression,
            inObj,
            weightVal
        )
        
        returnVal = {
            "Bones": genBones,
            "Type": "thigh",
            "Parent": inObj,
            "Limb": controllerLimb,
            "TwistNum": inTwistNum,
            "Weight": weightVal
        }
        
        return returnVal
    
    def create_calf_type(self, inObj, inChild, inTwistNum, reorder=True, side="Left"):
        """
        종아리(Calf) 타입의 트위스트 뼈대 생성
        
        Args:
            inObj: 종아리 뼈대 객체
            inTwistNum: 트위스트 뼈대 개수
            side: 좌/우측 ("left" 또는 "right", 기본값: "left")
            
        Returns:
            생성된 트위스트 뼈대 체인 또는 False(실패 시)
        """
        if inObj.parent is None or inObj.children.count == 0:
            return False
        
        controllerLimb = inChild
        weightVal = 100
        
        # 복수 뼈대인 경우 가중치 조정
        if inTwistNum > 1:
            weightVal = 100 / (inTwistNum - 1)
            
        createdBones = self.create_bones(
            inObj,
            controllerLimb,
            inTwistNum,
            self.calfExpression,
            self.calfExtraExpression,
            controllerLimb,
            weightVal
        )
        genBones = self.reorder_bones(createdBones, inObj, inChild) if reorder else createdBones
        
        returnVal = {
            "Bones": genBones,
            "Type": "calf",
            "Parent": inObj,
            "Limb": controllerLimb,
            "TwistNum": inTwistNum,
            "Weight": weightVal
        }
        
        return returnVal
    
    def create_bend_type(self):
        """
        굽힘(Bend) 타입의 트위스트 뼈대 생성
        (아직 구현되지 않음)
        """
        pass