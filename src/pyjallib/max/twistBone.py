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
        
        self.upperTwistBoneExpression = (
            "localTm = limb.transform * (inverse limbParent.transform)\n"
            "tm = localTm * inverse(localRefTm)\n"
            "\n"
            "q = tm.rotation\n"
            "\n"
            "axis = [1,0,0]\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat q.angle proj\n"
            "twist = normalize twist\n"
            "--swing = tm.rotation * (inverse twist)\n"
            "\n"
            "inverse twist\n"
        )
        
        self.lowerTwistBoneExpression = (
            "localTm = limb.transform * (inverse limbParent.transform)\n"
            "tm = localTm * inverse(localRefTm)\n"
            "\n"
            "q = tm.rotation\n"
            "\n"
            "axis = [1,0,0]\n"
            "proj = (dot q.axis axis) * axis\n"
            "twist = quat q.angle proj\n"
            "twist = normalize twist\n"
            "--swing = tm.rotation * (inverse twist)\n"
            "\n"
            "twist\n"
        )
            
    def create_upper_limb_bones(self, inObj, inChild, twistNum=4):
        """
        트위스트 뼈대 생성 메소드.
        
        Args:
            inObj: 트위스트 뼈대의 부모 객체
            inChild: 자식 객체 배열
            twistNum: 트위스트 뼈대 개수 (기본값: 4)
        
        Returns:
            dict: 생성된 트위스트 뼈대 정보
        """
        limb = inObj
        distance = rt.distance(limb, inChild)
        facingDirVec = inChild.transform.position - inObj.transform.position
        inObjXAxisVec = inObj.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        offssetAmount = (distance / twistNum) * distanceDir
        weightVal = 100.0 / (twistNum-1)
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "Twist")
        if inObj.name[0].islower():
            boneName = boneName.lower()
        twistBone = self.bone.create_nub_bone(boneName, 2)
        twistBone.name = self.name.replace_name_part("Index", boneName, "1")
        twistBone.name = self.name.remove_name_part("Nub", twistBone.name)
        twistBone.transform = limb.transform
        twistBone.parent = limb
        twistBoneLocalRefTM = limb.transform * rt.inverse(limb.parent.transform)
        
        twistBoneRotListController = self.const.assign_rot_list(twistBone)
        twistBoneController = rt.Rotation_Script()
        twistBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
        twistBoneController.addNode("limb", limb)
        twistBoneController.addNode("limbParent", limb.parent)
        twistBoneController.setExpression(self.upperTwistBoneExpression)
        twistBoneController.update()
        
        rt.setPropertyController(twistBoneRotListController, "Available", twistBoneController)
        twistBoneRotListController.delete(1)
        twistBoneRotListController.setActive(twistBoneRotListController.count)
        twistBoneRotListController.weight[0] = 100.0
        
        boneChainArray.append(twistBone)
        
        if twistNum > 1:
            lastBone = self.bone.create_nub_bone(boneName, 2)
            lastBone.name = self.name.replace_name_part("Index", boneName, str(twistNum))
            lastBone.name = self.name.remove_name_part("Nub", lastBone.name)
            lastBone.transform = limb.transform
            lastBone.parent = limb
            self.anim.move_local(lastBone, offssetAmount*(twistNum-1), 0, 0)
            
            if twistNum > 2:
                for i in range(1, twistNum-1):
                    twistExtraBone = self.bone.create_nub_bone(boneName, 2)
                    twistExtraBone.name = self.name.replace_name_part("Index", boneName, str(i+1))
                    twistExtraBone.name = self.name.remove_name_part("Nub", twistExtraBone.name)
                    twistExtraBone.transform = limb.transform
                    twistExtraBone.parent = limb
                    self.anim.move_local(twistExtraBone, offssetAmount*i, 0, 0)
                    
                    twistExtraBoneRotListController = self.const.assign_rot_list(twistExtraBone)
                    twistExtraBoneController = rt.Rotation_Script()
                    twistExtraBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
                    twistExtraBoneController.addNode("limb", limb)
                    twistExtraBoneController.addNode("limbParent", limb.parent)
                    twistExtraBoneController.setExpression(self.upperTwistBoneExpression)
                    
                    rt.setPropertyController(twistExtraBoneRotListController, "Available", twistExtraBoneController)
                    twistExtraBoneRotListController.delete(1)
                    twistExtraBoneRotListController.setActive(twistExtraBoneRotListController.count)
                    twistExtraBoneRotListController.weight[0] = weightVal
                    
                    boneChainArray.append(twistExtraBone)
            
            boneChainArray.append(lastBone)
        
        returnVal = {
            "Bones": boneChainArray,
            "Type": "Upper",
            "Limb": inObj,
            "Child": inChild,
            "TwistNum": twistNum
        }
        
        return returnVal

    def create_lower_limb_bones(self, inObj, inChild, twistNum=4):
        """
        트위스트 뼈대 생성 메소드.
        
        Args:
            inObj: 트위스트 뼈대의 부모 객체
            inChild: 자식 객체 배열
            twistNum: 트위스트 뼈대 개수 (기본값: 4)
        
        Returns:
            dict: 생성된 트위스트 뼈대 정보
        """
        limb = inChild
        distance = rt.distance(inObj, inChild)
        facingDirVec = inChild.transform.position - inObj.transform.position
        inObjXAxisVec = inObj.objectTransform.row1
        distanceDir = 1.0 if rt.dot(inObjXAxisVec, facingDirVec) > 0 else -1.0
        offssetAmount = (distance / twistNum) * distanceDir
        weightVal = 100.0 / (twistNum-1)
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "Twist")
        if inObj.name[0].islower():
            boneName = boneName.lower()
        twistBone = self.bone.create_nub_bone(boneName, 2)
        twistBone.name = self.name.replace_name_part("Index", boneName, "1")
        twistBone.name = self.name.remove_name_part("Nub", twistBone.name)
        twistBone.transform = inObj.transform
        twistBone.parent = inObj
        self.anim.move_local(twistBone, offssetAmount*(twistNum-1), 0, 0)
        twistBoneLocalRefTM = limb.transform * rt.inverse(limb.parent.transform)
        
        twistBoneRotListController = self.const.assign_rot_list(twistBone)
        twistBoneController = rt.Rotation_Script()
        twistBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
        twistBoneController.addNode("limb", limb)
        twistBoneController.addNode("limbParent", limb.parent)
        twistBoneController.setExpression(self.lowerTwistBoneExpression)
        twistBoneController.update()
        
        rt.setPropertyController(twistBoneRotListController, "Available", twistBoneController)
        twistBoneRotListController.delete(1)
        twistBoneRotListController.setActive(twistBoneRotListController.count)
        twistBoneRotListController.weight[0] = 100.0
        
        if twistNum > 1:
            lastBone = self.bone.create_nub_bone(boneName, 2)
            lastBone.name = self.name.replace_name_part("Index", boneName, str(twistNum))
            lastBone.name = self.name.remove_name_part("Nub", lastBone.name)
            lastBone.transform = inObj.transform
            lastBone.parent = inObj
            self.anim.move_local(lastBone, 0, 0, 0)
            
            if twistNum > 2:
                for i in range(1, twistNum-1):
                    twistExtraBone = self.bone.create_nub_bone(boneName, 2)
                    twistExtraBone.name = self.name.replace_name_part("Index", boneName, str(i+1))
                    twistExtraBone.name = self.name.remove_name_part("Nub", twistExtraBone.name)
                    twistExtraBone.transform = inObj.transform
                    twistExtraBone.parent = inObj
                    self.anim.move_local(twistExtraBone, offssetAmount*(twistNum-1-i), 0, 0)
                    
                    twistExtraBoneRotListController = self.const.assign_rot_list(twistExtraBone)
                    twistExtraBoneController = rt.Rotation_Script()
                    twistExtraBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
                    twistExtraBoneController.addNode("limb", limb)
                    twistExtraBoneController.addNode("limbParent", limb.parent)
                    twistExtraBoneController.setExpression(self.lowerTwistBoneExpression)
                    
                    rt.setPropertyController(twistExtraBoneRotListController, "Available", twistExtraBoneController)
                    twistExtraBoneRotListController.delete(1)
                    twistExtraBoneRotListController.setActive(twistExtraBoneRotListController.count)
                    twistExtraBoneRotListController.weight[0] = weightVal
                    
                    boneChainArray.append(twistExtraBone)
            
            boneChainArray.append(lastBone)
        
        returnVal = {
            "Bones": boneChainArray,
            "Type": "Lower",
            "Limb": inObj,
            "Child": inChild,
            "TwistNum": twistNum
        }
        
        return returnVal