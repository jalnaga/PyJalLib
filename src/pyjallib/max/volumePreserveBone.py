#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
관절 부피 유지 본(Volume preserve Bone) 모듈 - 3ds Max용 관절의 부피를 유지하기 위해 추가되는 중간본들을 위한 모듈
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint

class VolumePreserveBone:
    """
    관절 부피 유지 본(Volume preserve Bone) 클래스
    3ds Max에서 관절의 부피를 유지하기 위해 추가되는 중간본들을 위한 클래스
    """
    def __init__(self, nameService=None, animService=None, constService=None, boneService=None, helperService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constService: 제약 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constService if constService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        
        self.obj = None
        
    def create_rot_helpers(self, inObj, inRotScale=0.5):
        if rt.isValidNode(inObj) == False or rt.isValidNode(inObj.parent) == False:
            return False
        
        volName = self.name.get_RealName(inObj.name)
        volName = volName + "Vol"
        
        parentObj = inObj.parent
        
        rt.select(inObj)
        rotHelpers = self.helper.create_helper(make_two=True)
        rotHelpers[0].parent = inObj
        rotHelpers[1].parent = parentObj
        
        rotHelpers[0].name = self.name.replace_RealName(rotHelpers[0].name, volName)
        rotHelpers[1].name = self.name.replace_RealName(rotHelpers[1].name, volName + self.name.get_name_part_value_by_description("Type", "Target"))
        
        rotConst = self.const.assign_rot_const_multi(rotHelpers[0], [inObj, rotHelpers[1]])
        rotConst.setWeight(1, inRotScale * 100.0)
        rotConst.setWeight(2, (1.0 - inRotScale) * 100.0)
        
        return rotHelpers
        
    def create_init_bone(self, inObj, inVolumeSize, inRotHelpers, inRotAxis="Z", inTransAxis="PosY", inTransScale=1.0):
        if rt.isValidNode(inObj) == False or rt.isValidNode(inObj.parent) == False:
            return False
        
        returnVal = {
            "Bones": [],
            "Helpers": [],
            "RotAxis": inRotAxis,
            "TransAxis": inTransAxis,
            "TransScale": inTransScale
        }
        
        volName = self.name.get_RealName(inObj.name)
        volName = volName + "Vol"
        
        # ExposeTM을 사용하여 회전값을 가져오는 방법
        # rt.select(inObj)
        # expHelper = self.helper.create_exp_tm()[0]
        # expHelper.parent = parentObj
        # expHelper.exposeNode = rotHelpers[0]
        # expHelper.useParent = False
        # expHelper.localReferenceNode = rotHelpers[1]
        # expHelper.eulerXOrder = 5
        # expHelper.eulerYOrder = 5
        # expHelper.eulerZOrder = 5
    
        # expHelper.name = self.name.replace_RealName(expHelper.name, volName)
        
        boneGenHelperA = rt.point()
        boneGenHelperB = rt.point()
        boneGenHelperA.transform = inObj.transform
        boneGenHelperB.transform = inObj.transform
        
        if inTransAxis == "PosX":
            self.anim.move_local(boneGenHelperB, inVolumeSize, 0, 0)
        elif inTransAxis == "NegX":
            self.anim.move_local(boneGenHelperB, -inVolumeSize, 0, 0)
        elif inTransAxis == "PosY":
            self.anim.move_local(boneGenHelperB, 0, inVolumeSize, 0)
        elif inTransAxis == "NegY":
            self.anim.move_local(boneGenHelperB, 0, -inVolumeSize, 0)
        elif inTransAxis == "PosZ":
            self.anim.move_local(boneGenHelperB, 0, 0, inVolumeSize)
        elif inTransAxis == "NegZ":
            self.anim.move_local(boneGenHelperB, 0, 0, -inVolumeSize)
            
        row = ""
        sourceUpAxist = 0
        upAxis = 0
        if inRotAxis == "Y":
            row = "row3"
            sourceUpAxist = 2
            upAxis = 2
        elif inRotAxis == "Z":
            row = "row2"
            sourceUpAxist = 3
            upAxis = 3
            
        volumeBoneName = self.name.replace_RealName(self.name.get_string(inObj.name), volName + inRotAxis + inTransAxis)
        
        volumeBones = self.bone.create_simple_bone(inVolumeSize, volumeBoneName)
        volumeBones[0].transform = inObj.transform
        lookatConst = self.const.assign_lookat(volumeBones[0], boneGenHelperB)
        lookatConst.pickUpNode = inObj
        lookatConst.upnode_world = False
        lookatConst.StoUP_axis = sourceUpAxist
        lookatConst.upnode_axis = upAxis
        self.const.collapse(volumeBones[0])
        
        rt.delete(boneGenHelperA)
        rt.delete(boneGenHelperB)
        
        volumeBones[0].parent = inRotHelpers[0]
        rt.select(volumeBones[0])
        parentHelper = self.helper.create_parent_helper()[0]
        
        posConst = self.const.assign_pos_script_controller(volumeBones[0])
        # posConst.AddNode("rotExp", expHelper)
        posConst.AddNode("rotObj", inRotHelpers[0])
        posConst.AddNode("rotParent", inRotHelpers[1])
        posConst.AddConstant("volumeSize", inVolumeSize)
        posConst.AddConstant("transScale", inTransScale)
        
        posConstCode = f""
        posConstCode += f"local parentXAxis = (normalize rotParent.objectTransform.{row})\n"
        posConstCode += f"local rotObjXAxis = (normalize rotObj.objectTransform.{row})\n"
        posConstCode += f"local rotAmount = (1.0 - (dot parentXAxis rotObjXAxis))/2.0\n"
        posConstCode += f"local posX = rotAmount * volumeSize * transScale\n"
        posConstCode += f"[posX, 0.0, 0.0]\n"
        
        posConst.SetExpression(posConstCode)
        posConst.Update()
        
        returnVal["Bones"] = volumeBones
        returnVal["Helpers"] = [parentHelper]
        
        return returnVal
    
    def create_bones(self, inObj, inVolumeSize, inRotAxises, inRotScale, inTransAxiese, inTransScales):
        if rt.isValidNode(inObj) == False or rt.isValidNode(inObj.parent) == False:
            return False
        
        if not len(inTransAxiese) == len(inTransScales) == len(inTransAxiese) == len(inRotAxises):
            return False
        
        allBones = []
        allHelpers = []
        
        returnVal = {
            "VolumeSize": inVolumeSize,
            "RotScale": inRotScale,
            "RotHelpers": [],
            "BoneGroups": [],
            "AllBones": [],
            "AllHelpers": []
        }
        
        self.obj = inObj
        
        rotHelpers = self.create_rot_helpers(inObj, inRotScale=inRotScale)
        returnVal["RotHelpers"] = rotHelpers
        
        for i in range(len(inRotAxises)):
            genResult = self.create_init_bone(inObj, inVolumeSize, rotHelpers, inRotAxises[i], inTransAxiese[i], inTransScales[i])
            allBones.extend(genResult["Bones"])
            allHelpers.extend(genResult["Helpers"])
            
            # Add the individual bone group result to our return value
            returnVal["BoneGroups"].append(genResult)
        
        # Add rotation helpers to the helpers list
        allHelpers.insert(0, rotHelpers[0])
        allHelpers.insert(1, rotHelpers[1])
        
        # Add all bones and helpers to the return value
        returnVal["AllBones"] = allBones
        returnVal["AllHelpers"] = allHelpers
            
        return returnVal