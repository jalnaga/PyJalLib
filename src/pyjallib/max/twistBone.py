#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
트위스트 뼈대(Twist Bone) 모듈 - 3ds Max용 트위스트 뼈대 생성 관련 기능 제공

이 모듈은 3D 캐릭터 리깅에서 사용되는 트위스트 뼈대를 생성하고 제어하는 기능을 제공합니다.
트위스트 뼈대는 팔이나 다리의 회전 움직임을 더욱 자연스럽게 표현하기 위해 사용됩니다.
원본 MAXScript의 twistBone.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현되어
3ds Max 내에서 스크립트 형태로 실행할 수 있습니다.
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
    
    이 클래스는 3ds Max에서 트위스트 뼈대를 생성하고 제어하는 다양한 기능을 제공합니다.
    MAXScript의 _TwistBone 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    
    트위스트 뼈대는 상체(Upper)와 하체(Lower) 두 가지 타입으로 생성이 가능하며,
    각각 다른 회전 표현식을 사용하여 자연스러운 회전 움직임을 구현합니다.
    """
    
    def __init__(self, nameService=None, animService=None, constraintService=None, bipService=None, boneService=None):
        """
        TwistBone 클래스 초기화.
        
        의존성 주입 방식으로 필요한 서비스들을 외부에서 제공받거나 내부에서 생성합니다.
        서비스들이 제공되지 않을 경우 각 서비스의 기본 인스턴스를 생성하여 사용합니다.
        
        Args:
            nameService (Name, optional): 이름 처리 서비스. 기본값은 None이며, 제공되지 않으면 새로 생성됩니다.
            animService (Anim, optional): 애니메이션 서비스. 기본값은 None이며, 제공되지 않으면 새로 생성됩니다.
            constraintService (Constraint, optional): 제약 서비스. 기본값은 None이며, 제공되지 않으면 새로 생성됩니다.
            bipService (Bip, optional): 바이페드 서비스. 기본값은 None이며, 제공되지 않으면 새로 생성됩니다.
            boneService (Bone, optional): 뼈대 서비스. 기본값은 None이며, 제공되지 않으면 새로 생성됩니다.
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
        상체(팔, 어깨 등) 부분의 트위스트 뼈대를 생성하는 메소드.
        
        상체용 트위스트 뼈대는 부모 객체(inObj)의 위치에서 시작하여 
        자식 객체(inChild) 방향으로 여러 개의 뼈대를 생성합니다.
        생성된 뼈대들은 스크립트 컨트롤러를 통해 자동으로 회전되어
        자연스러운 트위스트 움직임을 표현합니다.
        
        Args:
            inObj: 트위스트 뼈대의 부모 객체(뼈). 일반적으로 상완 또는 대퇴부에 해당합니다.
            inChild: 자식 객체(뼈). 일반적으로 전완 또는 하퇴부에 해당합니다.
            twistNum (int, optional): 생성할 트위스트 뼈대의 개수. 기본값은 4입니다.
        
        Returns:
            dict: 생성된 트위스트 뼈대 정보를 담고 있는 사전 객체입니다.
                 "Bones": 생성된 뼈대 객체들의 배열
                 "Type": "Upper" (상체 타입)
                 "Limb": 부모 객체 참조
                 "Child": 자식 객체 참조
                 "TwistNum": 생성된 트위스트 뼈대 개수
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
        하체(팔뚝, 다리 등) 부분의 트위스트 뼈대를 생성하는 메소드.
        
        하체용 트위스트 뼈대는 부모 객체(inObj)의 위치에서 시작하여 
        자식 객체(inChild) 쪽으로 여러 개의 뼈대를 생성합니다.
        상체와는 다른 회전 표현식을 사용하여 하체에 적합한 트위스트 움직임을 구현합니다.
        
        Args:
            inObj: 트위스트 뼈대의 부모 객체(뼈). 일반적으로 전완 또는 하퇴부에 해당합니다.
            inChild: 자식 객체(뼈). 일반적으로 손목 또는 발목에 해당합니다.
            twistNum (int, optional): 생성할 트위스트 뼈대의 개수. 기본값은 4입니다.
        
        Returns:
            dict: 생성된 트위스트 뼈대 정보를 담고 있는 사전 객체입니다.
                 "Bones": 생성된 뼈대 객체들의 배열
                 "Type": "Lower" (하체 타입)
                 "Limb": 부모 객체 참조
                 "Child": 자식 객체 참조
                 "TwistNum": 생성된 트위스트 뼈대 개수
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