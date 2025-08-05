#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5용 스 - 3ds Max용 뼈대 생성 관련 기능 제공
원본 MAXScript의 bone.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from dataclasses import dataclass

from pymxs import runtime as rt
from .name import Name
from .anim import Anim
from .bone import Bone
from .bip import Bip

class UE5Skeleton:
    def __init__(self, nameService=None, animService=None, boneService=None, bipService=None):
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.bip = bipService if bipService else Bip(nameService=self.name)
        
        self.ue5SpineNum = 5
        self.ue5NeckNum = 2
        
        self.bipRotDict = {
            "pelvis": [180,0,0],
            "spine": [180,0,0],
            "neck": [180,0,0],
            "head": [180,0,0],
            "tail": [180,0,0],
            
            "lArm": [0,0,0],
            "rArm": [0,0,180],
            
            "lLeg": [0,0,180],
            "rLeg": [0,0,0],
            
            "lFingers": [0,0,0],
            "rFingers": [0,0,180],
            
            "lToes": [0,0,0],
            "rToes": [0,0,180]
        }
        self.bipNameDict = {
            "pelvis": ["Pelvis"],
            "spine": ["Spine"],
            "neck": ["Neck"],
            "head": ["Head"],
            "tail": ["Tail"],
            
            "lArm": ["Clavicle", "Upperarm", "Lowerarm", "Hand"],
            "rArm": ["Clavicle", "Upperarm", "Lowerarm", "Hand"],
            "lLeg": ["Thigh", "Calf", "Horselink", "Foot"],
            "rLeg": ["Thigh", "Calf", "Horselink", "Foot"]
        }
        self.fingerNameDict = {
            "Finger0": "Thumb",
            "Finger1": "Index",
            "Finger2": "Middle",
            "Finger3": "Ring",
            "Finger4": "Pinky"
        }
        self.toeNameDict = {
            "Toe": "Ball"
        }
        
    def rotate_bip_skin_bones(self, inSkinBones):
        bipSkinBones = [item for item in inSkinBones if self.bone.is_bip_skin_bone(item)]
        if len(bipSkinBones) == 0:
            return
        
        bipOriBone = self.bone.get_skin_bone_ori_bone(bipSkinBones[0])
        bipNodes = self.bip.get_all_grouped_nodes(bipOriBone)
        
        for bipGroupName in bipNodes:
            if bipGroupName not in self.bipRotDict.keys():
                continue
            bipNodeInGroup = bipNodes[bipGroupName]
            rotAmount = self.bipRotDict[bipGroupName]
            for bipNode in bipNodeInGroup:
                for skinBone in bipSkinBones:
                    targetOriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if targetOriBone == bipNode:
                        self.anim.rotate_local(skinBone, rotAmount[0], rotAmount[1], rotAmount[2], dontAffectChildren=True)
                        break
    
    def convert_bip_finger_skin_bone_name_to_ue5(self, inBip, inSkinBones):
        bipObj = self.bip.get_com(inBip)
        fingerNum = bipObj.controller.fingers
        fingerLinkNum = bipObj.controller.fingerLinks
            
        lFingersList = []
        rFingersList = []
        
        fingerSkinBones = []
        
        for i in range(1, fingerNum+1):
            fingers = []
            for j in range(1, fingerLinkNum+1):
                linkIndex = (i-1)*fingerLinkNum + j
                fingerNode = rt.biped.getNode(bipObj.controller, rt.name("lFingers"), link=linkIndex)
                if fingerNode is not None:
                    fingers.append(fingerNode)
            lFingersList.append(fingers)
        for i in range(1, fingerNum+1):
            fingers = []
            for j in range(1, fingerLinkNum+1):
                linkIndex = (i-1)*fingerLinkNum + j
                fingerNode = rt.biped.getNode(bipObj.controller, rt.name("rFingers"), link=linkIndex)
                if fingerNode is not None:
                    fingers.append(fingerNode)
            rFingersList.append(fingers)
            
        fingerName = [self.fingerNameDict[key] for key in self.fingerNameDict.keys()]
        
        for i, fingers in enumerate(lFingersList):
            for j, item in enumerate(fingers):
                for skinBone in inSkinBones:
                    oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if oriBone == item:
                        skinBone.name = self.name.replace_name_part("RealName", skinBone.name, fingerName[i])
                        skinBone.name = self.name.replace_name_part("Index", skinBone.name, str(j+1))
                        fingerSkinBones.append(skinBone)
                        break
        
        for i, fingers in enumerate(rFingersList):
            for j, item in enumerate(fingers):
                for skinBone in inSkinBones:
                    oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if oriBone == item:
                        skinBone.name = self.name.replace_name_part("RealName", skinBone.name, fingerName[i])
                        skinBone.name = self.name.replace_name_part("Index", skinBone.name, str(j+1))
                        fingerSkinBones.append(skinBone)
                        break
        
        return fingerSkinBones
    
    def convert_bip_toe_skin_bone_name_to_ue5(self, inBip, inSkinBones):
        bipObj = self.bip.get_com(inBip)
        toeNum = bipObj.controller.toes
        toeLinkNum = bipObj.controller.toeLinks
        
        lToesList = []
        rToesList = []
        
        toeSkinBones = []
        
        # Use the same sequential indexing pattern as fingers
        for i in range(1, toeNum+1):
            toes = []
            for j in range(1, toeLinkNum+1):
                linkIndex = (i-1)*toeLinkNum + j
                toeNode = rt.biped.getNode(bipObj.controller, rt.name("lToes"), link=linkIndex)
                if toeNode:
                    toes.append(toeNode)
            if toes:
                lToesList.append(toes)

        for i in range(1, toeNum+1):
            toes = []
            for j in range(1, toeLinkNum+1):
                linkIndex = (i-1)*toeLinkNum + j
                toeNode = rt.biped.getNode(bipObj.controller, rt.name("rToes"), link=linkIndex)
                if toeNode:
                    toes.append(toeNode)
            if toes:
                rToesList.append(toes)
                
        for i, toes in enumerate(lToesList):
            for j, item in enumerate(toes):
                for skinBone in inSkinBones:
                    oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if oriBone == item:
                        skinBone.name = self.name.replace_name_part("RealName", skinBone.name, self.toeNameDict["Toe"]+str(i+1))
                        skinBone.name = self.name.replace_name_part("Index", skinBone.name, str(j+1))
                        toeSkinBones.append(skinBone)
                        break
            
        for i, toes in enumerate(rToesList):
            for j, item in enumerate(toes):
                for skinBone in inSkinBones:
                    oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if oriBone == item:
                        skinBone.name = self.name.replace_name_part("RealName", skinBone.name, self.toeNameDict["Toe"]+str(i+1))
                        skinBone.name = self.name.replace_name_part("Index", skinBone.name, str(j+1))
                        toeSkinBones.append(skinBone)
                        break
        
        if toeNum == 1:
            toeSkinBones = []
            
            if toeLinkNum == 1:
                for skinBone in inSkinBones:
                    oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if oriBone == lToesList[0][0]:
                        skinBone.name = self.name.replace_name_part("RealName", skinBone.name, self.toeNameDict["Toe"])
                        skinBone.name = self.name.remove_name_part("Index", skinBone.name)
                        toeSkinBones.append(skinBone)
                        break
            else:
                for i, item in enumerate(lToesList[0]):
                    for skinBone in inSkinBones:
                        oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                        if oriBone == item:
                            skinBone.name = self.name.replace_name_part("RealName", skinBone.name, self.toeNameDict["Toe"])
                            skinBone.name = self.name.replace_name_part("Index", skinBone.name, str(i+1))
                            toeSkinBones.append(skinBone)
                            break
            
            if toeLinkNum == 1:
                for skinBone in inSkinBones:
                    oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                    if oriBone == rToesList[0][0]:
                        skinBone.name = self.name.replace_name_part("RealName", skinBone.name, self.toeNameDict["Toe"])
                        skinBone.name = self.name.remove_name_part("Index", skinBone.name)
                        toeSkinBones.append(skinBone)
                        break
            else:
                for i, item in enumerate(rToesList[0]):
                    for skinBone in inSkinBones:
                        oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
                        if oriBone == item:
                            skinBone.name = self.name.replace_name_part("RealName", skinBone.name, self.toeNameDict["Toe"])
                            skinBone.name = self.name.replace_name_part("Index", skinBone.name, str(i+1))
                            toeSkinBones.append(skinBone)
                            break
        
        return toeSkinBones
    
    def convert_bip_skin_bone_name_to_ue5(self, inSkinBones):
        bipSkinBones = [item for item in inSkinBones if self.bone.is_bip_skin_bone(item)]
        if len(bipSkinBones) == 0:
            return
        
        returnBones = []
        
        bipOriBone = self.bone.get_skin_bone_ori_bone(bipSkinBones[0])
        bipNodes = self.bip.get_all_grouped_nodes(bipOriBone)
        
        bipLimbBones = []
        
        for skinBone in bipSkinBones:
            oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
            for bipGroupName in bipNodes:
                if bipGroupName not in self.bipNameDict.keys():
                    continue
                
                bipNodeInGroup = bipNodes[bipGroupName]
                for index, bipNode in enumerate(bipNodeInGroup):
                    if oriBone == bipNode:
                        newSkinBoneRealName = ""
                        newSkinBoneIndex = ""
                        
                        if bipGroupName == "spine" or bipGroupName == "neck" or bipGroupName == "tail":
                            newSkinBoneRealName = self.bipNameDict[bipGroupName][0]
                            newSkinBoneIndex = self.name.get_name("Index", skinBone.name)
                            if newSkinBoneIndex == "":
                                newSkinBoneIndex = "0"
                            newSkinBoneIndex = str(int(newSkinBoneIndex)+1)
                        
                        elif bipGroupName == "head" or bipGroupName == "pelvis":
                            newSkinBoneRealName = self.bipNameDict[bipGroupName][0]
                            newSkinBoneIndex = ""
                                
                        elif bipGroupName == "lLeg" or bipGroupName == "rLeg":
                            newSkinBoneIndex = ""
                            if len(bipNodeInGroup) != 4:
                                if index < 2:
                                    newSkinBoneRealName = self.bipNameDict[bipGroupName][index]
                                elif index == 2:
                                    newSkinBoneRealName = self.bipNameDict[bipGroupName][3]
                            else:
                                newSkinBoneRealName = self.bipNameDict[bipGroupName][index]
                        
                        elif bipGroupName == "lArm" or bipGroupName == "rArm":
                            newSkinBoneIndex = ""
                            newSkinBoneRealName = self.bipNameDict[bipGroupName][index]
                        
                        skinBoneName = skinBone.name
                        skinBoneName = self.name.replace_name_part("RealName", skinBoneName, newSkinBoneRealName)
                        skinBoneName = self.name.replace_name_part("Index", skinBoneName, newSkinBoneIndex)
                        skinBoneName = self.name.replace_filtering_char(skinBoneName, "_")
                        skinBone.name = skinBoneName
                        bipLimbBones.append(skinBone)
                        break
                    
        fingerSkinBones = self.convert_bip_finger_skin_bone_name_to_ue5(bipOriBone, bipSkinBones)
        toeSkinBones = self.convert_bip_toe_skin_bone_name_to_ue5(bipOriBone, bipSkinBones)
        
        returnBones = bipLimbBones + fingerSkinBones + toeSkinBones
        
        return returnBones
    
    def match_spine_skin_bone_numbers_to_ue5(self, inSkinBones):
        bipSkinBones = [item for item in inSkinBones if self.bone.is_bip_skin_bone(item)]
        if len(bipSkinBones) == 0:
            return []
        
        bipOriBone = self.bone.get_skin_bone_ori_bone(bipSkinBones[0])
        bipSpines = self.bip.get_grouped_nodes(bipOriBone, "spine")
        if len(bipSpines) >= self.ue5SpineNum:
            return []
        
        bipNeck = self.bip.get_grouped_nodes(bipOriBone, "neck")[0]
        bipLClavicle = self.bip.get_grouped_nodes(bipOriBone, "lArm")[0]
        bipRClavicle = self.bip.get_grouped_nodes(bipOriBone, "rArm")[0]
        
        skinSpines = []
        for skinBone in bipSkinBones:
            oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
            if oriBone in bipSpines:
                skinSpines.append(skinBone)
        
        skinNeck = None
        skinLClavicle = None
        skinRClavicle = None
        for skinBone in bipSkinBones:
            oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
            if oriBone == bipLClavicle:
                skinLClavicle = skinBone
            elif oriBone == bipRClavicle:
                skinRClavicle = skinBone
            elif oriBone == bipNeck:
                skinNeck = skinBone
        
        spineDistance = rt.distance(skinSpines[-1], skinNeck)
        spineDistanceOffset = spineDistance / (self.ue5SpineNum - len(skinSpines) + 1)
        
        genSpineSkinBones = []
        
        skinBoneName = skinSpines[-1].name
        skinBoneRealName = self.name.get_name("RealName", skinBoneName)
        skinBoneIndex = self.name.get_name("Index", skinBoneName)
        if skinBoneIndex == "":
            skinBoneIndex = "0"
        
        parentSkinBone = skinSpines[-1]
        for i in range(int(skinBoneIndex), self.ue5SpineNum-1):
            skinBone = self.bone.create_nub_bone(skinBoneRealName, 2)
            skinBoneName = self.name.replace_name_part("Index", skinBoneName, str(i+1))
            skinBoneName = self.name.replace_filtering_char(skinBoneName, "_")
            skinBone.name = skinBoneName
            skinBone.wireColor = rt.Color(255, 88, 199)
            skinBone.transform = parentSkinBone.transform
            skinBone.boneEnable = True
            skinBone.renderable = False
            skinBone.boneScaleType = rt.Name("None")
            
            self.anim.move_local(skinBone, spineDistanceOffset, 0, 0)
            
            skinBone.parent = parentSkinBone
            
            self.bone.set_skin_bone_property(skinBone, True)
            self.bone.set_skin_bone_ori_bone(skinBone, inOriBone=bipSpines[-1])
            self.bone.set_skin_bone_parent(skinBone, inParentBone=parentSkinBone)
            
            parentSkinBone = skinBone
            
            skinBone.showLinks = True
            skinBone.showLinksOnly = True
            
            genSpineSkinBones.append(skinBone)
            
        
        skinNeck.parent = genSpineSkinBones[-1]
        skinLClavicle.parent = genSpineSkinBones[-1]
        skinRClavicle.parent = genSpineSkinBones[-1]
        
        self.bone.set_skin_bone_parent(skinNeck)
        self.bone.set_skin_bone_parent(skinLClavicle)
        self.bone.set_skin_bone_parent(skinRClavicle)
        
        return genSpineSkinBones
    
    def match_neck_skin_bone_numbers_to_ue5(self, inSkinBones):
        bipSkinBones = [item for item in inSkinBones if self.bone.is_bip_skin_bone(item)]
        if len(bipSkinBones) == 0:
            return []
        
        bipOriBone = self.bone.get_skin_bone_ori_bone(bipSkinBones[0])
        bipNecks = self.bip.get_grouped_nodes(bipOriBone, "neck")
        if len(bipNecks) >= self.ue5NeckNum:
            return []
        
        bipHead = self.bip.get_grouped_nodes(bipOriBone, "head")[0]
        
        skinNecks = []
        for skinBone in bipSkinBones:
            oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
            if oriBone in bipNecks:
                skinNecks.append(skinBone)
        
        skinHead = None
        for skinBone in bipSkinBones:
            oriBone = self.bone.get_skin_bone_ori_bone(skinBone)
            if oriBone == bipHead:
                skinHead = skinBone
        
        neckDistance = rt.distance(skinNecks[-1], skinHead)
        neckDistanceOffset = neckDistance / (self.ue5NeckNum - len(skinNecks) + 1)
        
        genNeckSkinBones = []
        
        skinBoneName = skinNecks[-1].name
        skinBoneRealName = self.name.get_name("RealName", skinBoneName)
        skinBoneIndex = self.name.get_name("Index", skinBoneName)
        if skinBoneIndex == "":
            skinBoneIndex = "0"
        
        parentSkinBone = skinNecks[-1]
        for i in range(int(skinBoneIndex), self.ue5NeckNum-1):
            skinBone = self.bone.create_nub_bone(skinBoneRealName, 2)
            skinBoneName = self.name.replace_name_part("Index", skinBoneName, str(i+1))
            skinBoneName = self.name.replace_filtering_char(skinBoneName, "_")
            skinBone.name = skinBoneName
            skinBone.wireColor = rt.Color(255, 88, 199)
            skinBone.transform = parentSkinBone.transform
            skinBone.boneEnable = True
            skinBone.renderable = False
            skinBone.boneScaleType = rt.Name("None")
            
            self.anim.move_local(skinBone, neckDistanceOffset, 0, 0)
            
            skinBone.parent = parentSkinBone
            
            self.bone.set_skin_bone_property(skinBone, True)
            self.bone.set_skin_bone_ori_bone(skinBone, inOriBone=bipNecks[-1])
            self.bone.set_skin_bone_parent(skinBone, inParentBone=parentSkinBone)
            
            parentSkinBone = skinBone
            
            skinBone.showLinks = True
            skinBone.showLinksOnly = True
            
            genNeckSkinBones.append(skinBone)
            
        skinHead.parent = genNeckSkinBones[-1]
        
        self.bone.set_skin_bone_parent(skinHead)
        
        return genNeckSkinBones