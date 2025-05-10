#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
관절 부피 유지 본(Volume preserve Bone) 모듈 - 3ds Max용 관절의 부피를 유지하기 위해 추가되는 중간본들을 위한 모듈
"""

from pymxs import runtime as rt

class VolumePreserveBone:
    """
    관절 부피 유지 본(Volume preserve Bone) 클래스
    3ds Max에서 관절의 부피를 유지하기 위해 추가되는 중간본들을 위한 클래스
    """
    def __init__(self, jalService=None):
        """
        클래스 초기화.
        
        Args:
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
        self.const = jal.constraint
        self.bone = jal.bone
        self.helper = jal.helper
        
        self.obj = None
        
        self.genBones = []
        self.genHelpers = []
        
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
            "Helpers": []
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
    
    def create_bones(self,inObj, inVolumeSize, inRotAxises, inRotScale, inTransAxiese, inTransScales):
        if rt.isValidNode(inObj) == False or rt.isValidNode(inObj.parent) == False:
            return False
        
        if not len(inTransAxiese) == len(inTransScales) == len(inTransAxiese) == len(inRotAxises):
            return False
        
        self.genBones = []
        self.genHelpers = []
        returnVal = {
            "Bones": [],
            "Helpers": []
        }
        
        self.obj = inObj
        
        rotHelpers = self.create_rot_helpers(inObj, inRotScale=inRotScale)
        
        for i in range(len(inRotAxises)):
            genResult = self.create_init_bone(inObj, inVolumeSize, rotHelpers, inRotAxises[i], inTransAxiese[i], inTransScales[i])
            self.genBones.extend(genResult["Bones"])
            self.genHelpers.extend(genResult["Helpers"])
        
        self.genHelpers.insert(0, rotHelpers[0])
        self.genHelpers.insert(1, rotHelpers[1])
        
        returnVal["Bones"] = self.genBones
        returnVal["Helpers"] = self.genHelpers
            
        return returnVal
    
    def delete(self):
        """
        생성된 본과 헬퍼를 삭제하는 메소드.
        
        Returns:
            None
        """
        rt.delete(self.genBones)
        rt.delete(self.genHelpers)
        
        self.genBones = []
        self.genHelpers = []
    
    def update_setting(self, inVolumeSize, inRotAxises, inRotScale, inTransAxiese, inTransScales):
        """
        생성된 본과 헬퍼의 설정을 업데이트하는 메소드.
        
        Args:
            inVolumeSize: 부피 크기
            inRotAxises: 회전 축 배열
            inRotScale: 회전 스케일
            inTransAxiese: 변환 축 배열
            inTransScales: 변환 스케일 배열
            
        Returns:
            None
        """
        if len(self.genBones) == 0:
            return False
        
        self.delete()
        self.create_bones(self.obj, inVolumeSize, inRotAxises, inRotScale, inTransAxiese, inTransScales)