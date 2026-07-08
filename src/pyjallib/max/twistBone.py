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

from .boneChain import BoneChain


class TwistBone:
    """팔·다리의 트위스트 본을 생성하는 클래스.

    상체(Upper)·하체(Lower) 타입별 회전 표현식을 사용해 회전을 분산하는 트위스트 본 체인을 구성한다.
    """

    def __init__(self, nameService=None, animService=None, constraintService=None, bipService=None, boneService=None):
        """TwistBone 클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            bipService (Bip | None): Biped 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 뼈대 서비스. None이면 새로 생성한다.
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        # Ensure dependent services use the potentially newly created instances
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(animService=self.anim, nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        
        # 객체 속성 초기화
        self.limb = None
        self.child = None
        self.twistNum = 0
        self.bones = []
        self.twistType = ""
        
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
            
    def reset(self):
        """클래스의 작업 데이터를 초기 상태로 되돌린다.

        Returns:
            TwistBone: 메서드 체이닝을 위한 자기 자신
        """
        self.limb = None
        self.child = None
        self.twistNum = 0
        self.bones = []
        self.twistType = ""
        
        return self
            
    def create_upper_limb_bones(self, inObj, inChild, twistNum=4):
        """팔·다리 상부(상완, 대퇴부 등)의 트위스트 본들을 생성한다.

        부모 객체 위치에서 자식 객체 방향으로 본들을 배치하고,
        상체용 회전 표현식의 스크립트 컨트롤러로 회전을 분산한다.

        Args:
            inObj (rt.Node): 트위스트 본의 부모 객체. 일반적으로 상완 또는 대퇴부.
            inChild (rt.Node): 자식 객체. 일반적으로 전완 또는 하퇴부.
            twistNum (int): 생성할 트위스트 본의 개수

        Returns:
            BoneChain: 생성된 트위스트 본 체인
        """
        limb = inObj
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "Twist")
        if self.name.get_name("RealName", inObj.name)[0].islower():
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
            weightVal = 100.0 / (twistNum-1)
            posWeightVal = 100.0 / twistNum
            
            lastBone = self.bone.create_nub_bone(boneName, 2)
            lastBone.name = self.name.replace_name_part("Index", boneName, str(twistNum))
            lastBone.name = self.name.remove_name_part("Nub", lastBone.name)
            lastBone.transform = limb.transform
            lastBone.parent = limb
            lastBonePosConst = self.const.assign_pos_const_multi(lastBone, [limb, inChild])
            lastBonePosConst.setWeight(1, 100.0 - (posWeightVal*(twistNum-1)))
            lastBonePosConst.setWeight(2, posWeightVal*(twistNum-1))
            
            if twistNum > 2:
                for i in range(1, twistNum-1):
                    twistExtraBone = self.bone.create_nub_bone(boneName, 2)
                    twistExtraBone.name = self.name.replace_name_part("Index", boneName, str(i+1))
                    twistExtraBone.name = self.name.remove_name_part("Nub", twistExtraBone.name)
                    twistExtraBone.transform = limb.transform
                    twistExtraBone.parent = limb
                    twistExtraBonePosConst = self.const.assign_pos_const_multi(twistExtraBone, [limb, inChild])
                    twistExtraBonePosConst.setWeight(1, 100.0 - (posWeightVal*i))
                    twistExtraBonePosConst.setWeight(2, posWeightVal*i)
                    
                    twistExtraBoneRotListController = self.const.assign_rot_list(twistExtraBone)
                    twistExtraBoneController = rt.Rotation_Script()
                    twistExtraBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
                    twistExtraBoneController.addNode("limb", limb)
                    twistExtraBoneController.addNode("limbParent", limb.parent)
                    twistExtraBoneController.setExpression(self.upperTwistBoneExpression)
                    
                    rt.setPropertyController(twistExtraBoneRotListController, "Available", twistExtraBoneController)
                    twistExtraBoneRotListController.delete(1)
                    twistExtraBoneRotListController.setActive(twistExtraBoneRotListController.count)
                    twistExtraBoneRotListController.weight[0] = weightVal * (twistNum-1-i)
                    
                    boneChainArray.append(twistExtraBone)
            
            boneChainArray.append(lastBone)
        
        if self.bone.is_skin_bone(inObj) or self.bone.is_skin_bone(inChild):
            for item in boneChainArray:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 BoneChain 형태로 준비
        result = {
            "Bones": boneChainArray,
            "Helpers": [],
            "SourceBones": [inObj, inChild],
            "Parameters": [twistNum, "Upper"]
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return BoneChain.from_result(result)

    def create_lower_limb_bones(self, inObj, inChild, twistNum=4):
        """팔·다리 하부(전완, 하퇴부 등)의 트위스트 본들을 생성한다.

        부모 객체 위치에서 자식 객체 쪽으로 본들을 배치하고,
        상체용과 다른 하체용 회전 표현식의 스크립트 컨트롤러로 회전을 분산한다.

        Args:
            inObj (rt.Node): 트위스트 본의 부모 객체. 일반적으로 전완 또는 하퇴부.
            inChild (rt.Node): 자식 객체. 일반적으로 손목 또는 발목.
            twistNum (int): 생성할 트위스트 본의 개수

        Returns:
            BoneChain: 생성된 트위스트 본 체인
        """
        limb = inChild
        
        posWeightVal = 100.0 / twistNum
        
        boneChainArray = []
        
        # 첫 번째 트위스트 뼈대 생성
        boneName = self.name.add_suffix_to_real_name(inObj.name, self.name._get_filtering_char(inObj.name) + "Twist")
        if self.name.get_name("RealName", inObj.name)[0].islower():
            boneName = boneName.lower()
        twistBone = self.bone.create_nub_bone(boneName, 2)
        twistBone.name = self.name.replace_name_part("Index", boneName, "1")
        twistBone.name = self.name.remove_name_part("Nub", twistBone.name)
        twistBone.transform = inObj.transform
        twistBone.parent = inObj
        twistBonePosConst = self.const.assign_pos_const_multi(twistBone, [limb, inObj])
        twistBonePosConst.setWeight(1, posWeightVal*(twistNum-1))
        twistBonePosConst.setWeight(2, 100.0 - (posWeightVal*(twistNum-1)))
        
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
        
        # 첫 번째 트위스트 본을 boneChainArray에 추가
        boneChainArray.append(twistBone)
        
        if twistNum > 1:
            weightVal = 100.0 / (twistNum-1)
            
            lastBone = self.bone.create_nub_bone(boneName, 2)
            lastBone.name = self.name.replace_name_part("Index", boneName, str(twistNum))
            lastBone.name = self.name.remove_name_part("Nub", lastBone.name)
            lastBone.transform = inObj.transform
            lastBone.parent = inObj
            
            if twistNum > 2:
                for i in range(1, twistNum-1):
                    twistExtraBone = self.bone.create_nub_bone(boneName, 2)
                    twistExtraBone.name = self.name.replace_name_part("Index", boneName, str(i+1))
                    twistExtraBone.name = self.name.remove_name_part("Nub", twistExtraBone.name)
                    twistExtraBone.transform = inObj.transform
                    twistExtraBone.parent = inObj
                    twistExtraBonePosConst = self.const.assign_pos_const_multi(twistExtraBone, [limb, inObj])
                    twistExtraBonePosConst.setWeight(1, 100.0 - (posWeightVal*(i+1)))
                    twistExtraBonePosConst.setWeight(2, posWeightVal*(i+1))
                    
                    twistExtraBoneRotListController = self.const.assign_rot_list(twistExtraBone)
                    twistExtraBoneController = rt.Rotation_Script()
                    twistExtraBoneController.addConstant("localRefTm", twistBoneLocalRefTM)
                    twistExtraBoneController.addNode("limb", limb)
                    twistExtraBoneController.addNode("limbParent", limb.parent)
                    twistExtraBoneController.setExpression(self.lowerTwistBoneExpression)
                    
                    rt.setPropertyController(twistExtraBoneRotListController, "Available", twistExtraBoneController)
                    twistExtraBoneRotListController.delete(1)
                    twistExtraBoneRotListController.setActive(twistExtraBoneRotListController.count)
                    twistExtraBoneRotListController.weight[0] = weightVal * (twistNum-1-i)
                    
                    boneChainArray.append(twistExtraBone)
            
            boneChainArray.append(lastBone)
        
        if self.bone.is_skin_bone(inObj) or self.bone.is_skin_bone(inChild):
            for item in boneChainArray:
                self.bone.set_skin_bone_property(item, True)
                self.bone.set_skin_bone_parent(item)
        
        # 결과를 BoneChain 형태로 준비
        result = {
            "Bones": boneChainArray,
            "Helpers": [],
            "SourceBones": [inObj, inChild],
            "Parameters": [twistNum, "Lower"]
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        rt.redrawViews()
        
        return BoneChain.from_result(result)
    
    def create_bones_from_chain(self, inBoneChain: BoneChain):
        """기존 BoneChain 객체에서 트위스트 본을 재생성한다.

        기존 본과 헬퍼를 삭제한 뒤 파라미터의 타입("Upper"/"Lower")에 따라
        상부·하부용 생성 메서드로 셋업을 다시 만든다.

        Args:
            inBoneChain (BoneChain): 트위스트 본 정보를 포함한 BoneChain 객체

        Returns:
            BoneChain | None: 재생성된 트위스트 본 체인. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            return None
            
        # 기존 객체 삭제 (delete_all 대신 delete 사용)
        # delete는 bones와 helpers만 삭제하고 sourceBones와 parameters는 유지함
        inBoneChain.delete()
            
        # BoneChain에서 필요한 정보 추출
        sourceBones = inBoneChain.sourceBones
        parameters = inBoneChain.parameters
        
        # 필수 소스 본 확인
        if len(sourceBones) < 2 or not rt.isValidNode(sourceBones[0]) or not rt.isValidNode(sourceBones[1]):
            return None
            
        # 파라미터 가져오기 (또는 기본값 사용)
        twistNum = parameters[0] if len(parameters) > 0 else 4
        twistType = parameters[1] if len(parameters) > 1 else "Upper"
        
        # 본 생성
        inObj = sourceBones[0]
        inChild = sourceBones[1]
        
        # 타입에 따라 적절한 방식으로 트위스트 본 생성
        if twistType == "Upper":
            return self.create_upper_limb_bones(inObj, inChild, twistNum)
        else:
            return self.create_lower_limb_bones(inObj, inChild, twistNum)