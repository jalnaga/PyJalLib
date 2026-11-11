#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
뼈대(Bone) 모듈 - 3ds Max용 뼈대 생성 관련 기능 제공
원본 MAXScript의 bone.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from dataclasses import dataclass

from pymxs import runtime as rt
from .name import Name
from .anim import Anim
from .helper import Helper
from .constraint import Constraint


class Bone:
    """3ds Max 뼈대(Bone)의 생성·설정·계층 관리와 스킨 본 생성·연결 기능을 제공하는 클래스."""
    
    def __init__(self, nameService=None, animService=None, helperService=None, constraintService=None):
        """서비스 인스턴스들을 주입받아 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.const = constraintService if constraintService else Constraint(nameService=self.name, helperService=self.helper)
    
    def remove_ik(self, inBone):
        """뼈대에서 IK 체인을 제거한다.

        pos 또는 rotation 속성이 없는 경우에만 IK 체인을 제거한다.

        Args:
            inBone (rt.Node): IK 체인을 제거할 뼈대 객체
        """
        # pos 또는 rotation 속성이 없는 경우에만 IK 체인 제거
        if (not rt.isProperty(inBone, "pos")) or (not rt.isProperty(inBone, "rotation")):
            rt.HDIKSys.RemoveChain(inBone)
    
    def get_bone_assemblyHead(self, inBone):
        """뼈대가 속한 어셈블리의 헤드 뼈대를 찾아 반환한다.

        Args:
            inBone (rt.Node): 대상 뼈대 객체

        Returns:
            rt.Node | None: 어셈블리 헤드 뼈대. 찾지 못하면 None
        """
        tempBone = inBone
        while tempBone is not None:
            if tempBone.assemblyHead:
                return tempBone
            if not tempBone.assemblyMember:
                break
            tempBone = tempBone.parent
        
        return None
    
    def put_child_into_bone_assembly(self, inBone):
        """부모가 어셈블리 멤버인 경우 자식 뼈대를 어셈블리에 추가한다.

        Args:
            inBone (rt.Node): 어셈블리에 추가할 자식 뼈대
        """
        if inBone.parent is not None and inBone.parent.assemblyMember:
            inBone.assemblyMember = True
            inBone.assemblyMemberOpen = True
    
    def sort_bones_as_hierarchy(self, inBoneArray):
        """뼈대 배열을 계층 구조 깊이 순으로 정렬한다.

        각 뼈대의 조상 수를 계산하여 루트에 가까운 순서대로 정렬한다.

        Args:
            inBoneArray (list[rt.Node]): 정렬할 뼈대 객체 배열

        Returns:
            list[rt.Node]: 계층 구조에 따라 정렬된 뼈대 배열
        """
        # BoneLevel 구조체 정의 (Python 클래스로 구현)
        @dataclass
        class BoneLevel:
            index: int
            level: int
        
        # 뼈대 구조체 배열 초기화
        bones = []
        
        # 뼈대 구조체 배열 채우기. 계층 수준을 0으로 초기화
        for i in range(len(inBoneArray)):
            bones.append(BoneLevel(i, 0))
        
        # 뼈대 배열의 각 뼈대에 대한 계층 수준 계산
        # 계층 수준은 현재 뼈대와 루트 노드 사이의 조상 수
        for i in range(len(bones)):
            node = inBoneArray[bones[i].index]
            n = 0
            while node is not None:
                n += 1
                node = node.parent
            bones[i].level = n
        
        # 계층 수준에 따라 뼈대 배열 정렬
        bones.sort(key=lambda x: x.level)
        
        # 정렬된 뼈대를 저장할 새 배열 준비
        returnBonesArray = []
        for i in range(len(inBoneArray)):
            returnBonesArray.append(inBoneArray[bones[i].index])
        
        return returnBonesArray
    
    def correct_negative_stretch(self, bone, ask=True):
        """뼈대 축의 음수 오브젝트 오프셋 스케일을 보정한다.

        Args:
            bone (rt.Node): 보정할 뼈대 객체
            ask (bool): True면 보정 전 사용자에게 확인 다이얼로그를 표시한다.
        """
        axisIndex = 0
        
        # 뼈대 축에 따라 인덱스 설정
        if bone.boneAxis == rt.Name("X"):
            axisIndex = 0
        elif bone.boneAxis == rt.Name("Y"):
            axisIndex = 1
        elif bone.boneAxis == rt.Name("Z"):
            axisIndex = 2
        
        ooscale = bone.objectOffsetScale
        
        # 음수 스케일 보정
        if (ooscale[axisIndex] < 0) and ((not ask) or rt.queryBox("Correct negative scale?", title=bone.Name)):
            ooscale[axisIndex] = -ooscale[axisIndex]
            axisIndex = axisIndex + 2
            if axisIndex > 2:
                axisIndex = axisIndex - 3
            ooscale[axisIndex] = -ooscale[axisIndex]
            bone.objectOffsetScale = ooscale
    
    def reset_scale_of_selected_bones(self, ask=True):
        """선택된 뼈대들의 스케일을 계층 순서대로 초기화한다.

        Args:
            ask (bool): True면 각 뼈대에 대해 음수 스케일 보정을 확인 없이 함께 수행한다.
        """
        # 선택된 객체 중 BoneGeometry 타입만 수집
        bones = [item for item in rt.selection if rt.classOf(item) == rt.BoneGeometry]
        
        # 계층 구조에 따라 뼈대 정렬
        bones = self.sort_bones_as_hierarchy(rt.selection)
        
        # 뼈대 배열의 모든 뼈대에 대해 스케일 초기화
        for i in range(len(bones)):
            rt.ResetScale(bones[i])
            if ask:
                self.correct_negative_stretch(bones[i], False)
    
    def is_nub_bone(self, inputBone):
        """뼈대가 부모와 자식이 없는 단일(Nub) 뼈대인지 확인한다.

        Args:
            inputBone (rt.Node): 확인할 뼈대 객체

        Returns:
            bool: Nub 뼈대면 True, 아니면 False
        """
        if rt.classOf(inputBone) == rt.BoneGeometry:
            if inputBone.parent is None and inputBone.children.count == 0:
                return True
            else:
                return False
        return False
    
    def is_end_bone(self, inputBone):
        """뼈대가 부모는 있지만 자식이 없는 End 뼈대인지 확인한다.

        Args:
            inputBone (rt.Node): 확인할 뼈대 객체

        Returns:
            bool: End 뼈대면 True, 아니면 False
        """
        if rt.classOf(inputBone) == rt.BoneGeometry:
            if inputBone.parent is not None and inputBone.children.count == 0:
                return True
            else:
                return False
        return False
    
    def create_nub_bone(self, inName, inSize, inBoneScaleType=rt.Name("none")):
        """Nub 뼈대를 원점에 생성한다.

        Args:
            inName (str): 뼈대 이름. Index와 Nub namePart는 제거되고 고유 이름으로 생성된다.
            inSize (float): 뼈대 크기
            inBoneScaleType (rt.Name): 뼈대 스케일 타입

        Returns:
            rt.Node: 생성된 Nub 뼈대
        """
        nubBone = None
        
        # 화면 갱신 중지 상태에서 뼈대 생성
        rt.disableSceneRedraw()
        
        # 뼈대 생성 및 속성 설정
        nubBone = rt.BoneSys.createBone(rt.Point3(0, 0, 0), rt.Point3(1, 0, 0), rt.Point3(0, 0, 1))
        
        nubBone.width = inSize
        nubBone.height = inSize
        nubBone.taper = 90
        nubBone.length = inSize
        nubBone.frontfin = False
        nubBone.backfin = False
        nubBone.sidefins = False
        nubBone.name = self.name.remove_name_part("Index", inName)
        nubBone.name = self.name.remove_name_part("Nub", nubBone.name)
        # nubBone.name = self.name.replace_name_part("Nub", nubBone.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
        nubBone.name = self.name.gen_unique_name(nubBone.name)
        
        nubBone.boneScaleType = inBoneScaleType
        
        # 화면 갱신 재개
        rt.enableSceneRedraw()
        rt.redrawViews()
        
        return nubBone
    
    def create_nub_bone_on_obj(self, inObj, inSize=1):
        """객체의 트랜스폼 위치에 Nub 뼈대를 생성한다.

        Args:
            inObj (rt.Node): 위치를 참조할 객체
            inSize (float): 뼈대 크기

        Returns:
            rt.Node: 생성된 Nub 뼈대
        """
        boneName = self.name.get_string(inObj.name)
        newBone = self.create_nub_bone(boneName, inSize)
        newBone.transform = inObj.transform
        
        return newBone
    
    def create_end_bone(self, inBone):
        """뼈대의 끝에 End 뼈대를 생성하여 자식으로 연결한다.

        Args:
            inBone (rt.Node): 부모가 될 뼈대 객체

        Returns:
            rt.Node: 생성된 End 뼈대
        """
        parentBone = inBone
        parentTrans = parentBone.transform
        parentPos = parentTrans.translation
        boneName = self.name.get_string(parentBone.name)
        newBone = self.create_nub_bone(boneName, parentBone.width)
        
        parentBoneIndex = self.name.get_name("Index", parentBone.name)
        if parentBoneIndex != "":
            newBone.name = self.name.increase_index(parentBone.name, 1)
        
        newBone.transform = parentTrans
        
        # 로컬 좌표계에서 이동
        self.anim.move_local(newBone, parentBone.length, 0, 0)
        
        newBone.parent = parentBone
        self.put_child_into_bone_assembly(newBone)
        
        # 뼈대 속성 설정
        newBone.width = parentBone.width
        newBone.height = parentBone.height
        newBone.frontfin = False
        newBone.backfin = False
        newBone.sidefins = False
        newBone.taper = 90
        newBone.length = (parentBone.width + parentBone.height) / 2
        newBone.wirecolor = parentBone.wirecolor
        
        return newBone
    
    def create_bone(self, inPointArray, inName, end=True, delPoint=False, parent=False, size=2, normals=None, inBoneScaleType=rt.Name("none")):
        """포인트 배열을 따라 뼈대 체인을 생성한다.

        Args:
            inPointArray (list[rt.Node]): 뼈대 위치를 정의하는 포인트 객체 배열
            inName (str): 뼈대 기본 이름. Index namePart가 순번으로 치환된다.
            end (bool): True면 마지막에 End 뼈대를 추가로 생성한다.
            delPoint (bool): True면 생성 후 포인트 객체(Dummy, ExposeTm, Point)를 삭제한다.
            parent (bool): True면 첫 뼈대의 부모가 될 Nub 포인트를 생성한다.
            size (float): 뼈대 크기
            normals (list[rt.Point3] | None): 법선 벡터 배열. 포인트 배열과 길이가 같으면 Z축 방향 계산에 사용한다.
            inBoneScaleType (rt.Name): 뼈대 스케일 타입

        Returns:
            list[rt.Node] | False: 생성된 뼈대 배열. 포인트가 1개면 False
        """
        if normals is None:
            normals = []
            
        tempBone = None
        newBone = None
        
        returnBoneArray = []
        
        if len(inPointArray) != 1:
            for i in range(len(inPointArray) - 1):
                boneNum = i
                
                if len(normals) == len(inPointArray):
                    xDir = rt.normalize(inPointArray[i+1].transform.position - inPointArray[i].transform.position)
                    zDir = rt.normalize(rt.cross(xDir, normals[i]))
                    newBone = rt.BoneSys.createBone(inPointArray[i].transform.position, inPointArray[i+1].transform.position, zDir)
                else:
                    newBone = rt.BoneSys.createBone(inPointArray[i].transform.position, inPointArray[i+1].transform.position, rt.Point3(0, -1, 0))
                
                newBone.boneFreezeLength = True
                newBone.boneScaleType = inBoneScaleType
                newBone.name = self.name.replace_name_part("Index", inName, str(boneNum))
                newBone.height = size
                newBone.width = size
                newBone.frontfin = False
                newBone.backfin = False
                newBone.sidefins = False
                
                returnBoneArray.append(newBone)
                
                if tempBone is not None:
                    tempTm = rt.copy(newBone.transform * rt.Inverse(tempBone.transform))
                    localRot = rt.quatToEuler(tempTm.rotation).x
                    
                    self.anim.rotate_local(newBone, -localRot, 0, 0)
                
                newBone.parent = tempBone
                tempBone = newBone
            
            if delPoint:
                for i in range(len(inPointArray)):
                    if (rt.classOf(inPointArray[i]) == rt.Dummy) or (rt.classOf(inPointArray[i]) == rt.ExposeTm) or (rt.classOf(inPointArray[i]) == rt.Point):
                        rt.delete(inPointArray[i])
            
            if parent:
                parentNubPointName = self.name.replace_type(inName, self.name.get_parent_str())
                parentNubPoint = self.helper.create_point(parentNubPointName, size=size, boxToggle=True, crossToggle=True)
                parentNubPoint.transform = returnBoneArray[0].transform
                returnBoneArray[0].parent = parentNubPoint
            
            rt.select(newBone)
            
            if end:
                endBone = self.create_end_bone(newBone)
                returnBoneArray.append(endBone)
                
                rt.clearSelection()
                
                return returnBoneArray
            else:
                return returnBoneArray
        else:
            return False
    
    def create_simple_bone(self, inLength, inName, end=True, size=1):
        """시작점과 끝점을 지정하여 간단한 뼈대를 생성한다.

        Args:
            inLength (float): 뼈대 길이
            inName (str): 뼈대 이름
            end (bool): True면 End 뼈대를 추가로 생성한다.
            size (float): 뼈대 크기

        Returns:
            list[rt.Node] | False: 생성된 뼈대 배열. 실패 시 False
        """
        startPoint = self.helper.create_point("tempStart")
        endPoint = self.helper.create_point("tempEnd", pos=(inLength, 0, 0))
        returnBoneArray = self.create_bone([startPoint, endPoint], inName, end=end, delPoint=True, size=size)
        
        return returnBoneArray
    
    def create_stretch_bone(self, inPointArray, inName, size=2):
        """포인트를 따라 움직이는 스트레치 뼈대를 생성한다.

        각 뼈대에 위치 제약과 LookAt 제약을 할당한다.

        Args:
            inPointArray (list[rt.Node]): 뼈대 위치를 정의하는 포인트 배열
            inName (str): 뼈대 기본 이름
            size (float): 뼈대 크기

        Returns:
            list[rt.Node]: 생성된 스트레치 뼈대 배열
        """
        tempBone = []
        tempBone = self.create_bone(inPointArray, inName, size=size)
        
        for i in range(len(tempBone) - 1):
            self.const.assign_pos_const(tempBone[i], inPointArray[i])
            self.const.assign_lookat(tempBone[i], inPointArray[i+1])
        self.const.assign_pos_const(tempBone[-1], inPointArray[-1])
        
        return tempBone
    
    def create_simple_stretch_bone(self, inStart, inEnd, inName, squash=False, size=1):
        """시작점과 끝점을 지정하여 간단한 스트레치 뼈대를 생성한다.

        Args:
            inStart (rt.Node): 시작 포인트
            inEnd (rt.Node): 끝 포인트
            inName (str): 뼈대 이름
            squash (bool): True면 첫 뼈대의 스케일 타입을 squash로 설정한다.
            size (float): 뼈대 크기

        Returns:
            list[rt.Node]: 생성된 스트레치 뼈대 배열
        """
        returnArray = []
        returnArray = self.create_stretch_bone([inStart, inEnd], inName, size=size)
        if squash:
            returnArray[0].boneScaleType = rt.Name("squash")
        
        return returnArray
    
    def get_bone_shape(self, inBone):
        """뼈대의 형태 속성 16개를 배열로 가져온다.

        폭·높이·테이퍼·길이와 측면/전면/후면 핀 속성을 순서대로 담는다.

        Args:
            inBone (rt.Node): 속성을 가져올 뼈대 객체

        Returns:
            list: 뼈대 형태 속성 배열. BoneGeometry가 아니면 빈 배열
        """
        returnArray = []
        if rt.classOf(inBone) == rt.BoneGeometry:
            returnArray = [None] * 16  # 빈 배열 초기화
            returnArray[0] = inBone.width
            returnArray[1] = inBone.height
            returnArray[2] = inBone.taper
            returnArray[3] = inBone.length
            returnArray[4] = inBone.sidefins
            returnArray[5] = inBone.sidefinssize
            returnArray[6] = inBone.sidefinsstarttaper
            returnArray[7] = inBone.sidefinsendtaper
            returnArray[8] = inBone.frontfin
            returnArray[9] = inBone.frontfinsize
            returnArray[10] = inBone.frontfinstarttaper
            returnArray[11] = inBone.frontfinendtaper
            returnArray[12] = inBone.backfin
            returnArray[13] = inBone.backfinsize
            returnArray[14] = inBone.backfinstarttaper
            returnArray[15] = inBone.backfinendtaper
        
        return returnArray
    
    def pasete_bone_shape(self, targetBone, shapeArray):
        """뼈대에 형태 속성 배열을 적용한다.

        길이는 변경하지 않으며, End 뼈대인 경우 핀을 끄고 Nub 형태로 보정한다.

        Args:
            targetBone (rt.Node): 속성을 적용할 뼈대 객체
            shapeArray (list): get_bone_shape로 얻은 형태 속성 배열

        Returns:
            bool: 성공하면 True, BoneGeometry가 아니면 False
        """
        if rt.classOf(targetBone) == rt.BoneGeometry:
            targetBone.width = shapeArray[0]
            targetBone.height = shapeArray[1]
            targetBone.taper = shapeArray[2]
            #targetBone.length = shapeArray[3]  # 길이는 변경하지 않음
            targetBone.sidefins = shapeArray[4]
            targetBone.sidefinssize = shapeArray[5]
            targetBone.sidefinsstarttaper = shapeArray[6]
            targetBone.sidefinsendtaper = shapeArray[7]
            targetBone.frontfin = shapeArray[8]
            targetBone.frontfinsize = shapeArray[9]
            targetBone.frontfinstarttaper = shapeArray[10]
            targetBone.frontfinendtaper = shapeArray[11]
            targetBone.backfin = shapeArray[12]
            targetBone.backfinsize = shapeArray[13]
            targetBone.backfinstarttaper = shapeArray[14]
            targetBone.backfinendtaper = shapeArray[15]
            
            if self.is_end_bone(targetBone):
                targetBone.taper = 90
                targetBone.length = (targetBone.width + targetBone.height) / 2
                targetBone.frontfin = False
                targetBone.backfin = False
                targetBone.sidefins = False
            
            return True
        return False
    
    def set_fin_on(self, inBone, side=True, front=True, back=False, inSize=2.0, inTaper=0.0):
        """뼈대의 핀(fin)을 활성화하고 크기와 테이퍼를 설정한다.

        End 뼈대에는 적용하지 않는다.

        Args:
            inBone (rt.Node): 핀을 설정할 뼈대 객체
            side (bool): 측면 핀 활성화 여부
            front (bool): 전면 핀 활성화 여부
            back (bool): 후면 핀 활성화 여부
            inSize (float): 핀 크기
            inTaper (float): 핀 테이퍼 값
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            if not self.is_end_bone(inBone):
                inBone.frontfin = front
                inBone.frontfinsize = inSize
                inBone.frontfinstarttaper = inTaper
                inBone.frontfinendtaper = inTaper
                
                inBone.sidefins = side
                inBone.sidefinssize = inSize
                inBone.sidefinsstarttaper = inTaper
                inBone.sidefinsendtaper = inTaper
                
                inBone.backfin = back
                inBone.backfinsize = inSize
                inBone.backfinstarttaper = inTaper
                inBone.backfinendtaper = inTaper
    
    def set_fin_off(self, inBone):
        """뼈대의 모든 핀(fin)을 비활성화한다.

        Args:
            inBone (rt.Node): 핀을 비활성화할 뼈대 객체
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            inBone.frontfin = False
            inBone.sidefins = False
            inBone.backfin = False
    
    def set_bone_size(self, inBone, inSize):
        """뼈대의 폭과 높이를 설정한다.

        End 또는 Nub 뼈대인 경우 길이도 같은 크기로 설정한다.

        Args:
            inBone (rt.Node): 크기를 설정할 뼈대 객체
            inSize (float): 설정할 크기
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            inBone.width = inSize
            inBone.height = inSize
            
            if self.is_end_bone(inBone) or self.is_nub_bone(inBone):
                inBone.taper = 90
                inBone.length = inSize
    
    def set_bone_taper(self, inBone, inTaper):
        """뼈대의 테이퍼 값을 설정한다.

        End 뼈대에는 적용하지 않는다.

        Args:
            inBone (rt.Node): 테이퍼를 설정할 뼈대 객체
            inTaper (float): 설정할 테이퍼 값
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            if not self.is_end_bone(inBone):
                inBone.taper = inTaper
    
    def delete_bones_safely(self, inBoneArray):
        """뼈대 배열의 컨트롤러를 초기화하고 부모 관계를 해제한 뒤 삭제한다.

        입력 배열은 삭제 후 비워진다.

        Args:
            inBoneArray (list[rt.Node]): 삭제할 뼈대 배열
        """
        if len(inBoneArray) > 0:
            for targetBone in inBoneArray:
                self.const.collapse(targetBone)
                targetBone.parent = None
                rt.delete(targetBone)
            
            inBoneArray.clear()
    
    def select_first_children(self, inObj):
        """객체를 선택에 추가하고 자식들을 재귀적으로 선택한다.

        Args:
            inObj (rt.Node): 시작 객체

        Returns:
            bool | None: 재귀 판정에 사용되는 중간 결과. 자식이 없으면 None
        """
        rt.selectmore(inObj)
        
        for i in range(inObj.children.count):
            if self.select_first_children(inObj.children[i]):
                if inObj.children.count == 0 or inObj.children[0] is None:
                    return True
            else:
                return False
    
    def get_every_children(self, inObj):
        """객체의 모든 하위 자식들을 재귀적으로 수집한다.

        Args:
            inObj (rt.Node): 시작 객체

        Returns:
            list[rt.Node]: 모든 하위 자식 객체 배열
        """
        children = []
        
        if inObj.children.count != 0 and inObj.children[0] is not None:
            for i in range(inObj.children.count):
                children.append(inObj.children[i])
                children.extend(self.get_every_children(inObj.children[i]))
        
        return children
    
    def select_every_children(self, inObj, includeSelf=False):
        """객체의 모든 하위 자식들을 선택한다.

        Args:
            inObj (rt.Node): 시작 객체
            includeSelf (bool): True면 자신도 선택에 포함한다.
        """
        children = self.get_every_children(inObj)
        
        # 자신도 포함하는 경우
        if includeSelf:
            children.insert(0, inObj)
        
        rt.select(children)
    
    def get_bone_end_position(self, inBone):
        """뼈대의 끝 위치를 월드 좌표로 계산한다.

        Args:
            inBone (rt.Node): 대상 뼈대 객체

        Returns:
            rt.Point3: 뼈대 끝 위치. BoneGeometry가 아니면 트랜스폼의 이동 값
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            return rt.Point3(inBone.length, 0, 0) * inBone.objectTransform
        else:
            return inBone.transform.translation
    
    def link_skin_bone(self, inSkinBone, inOriBone):
        """스킨 뼈대를 링크 제약으로 원본 뼈대에 연결한다.

        Args:
            inSkinBone (rt.Node): 연결할 스킨 뼈대
            inOriBone (rt.Node): 원본 뼈대
        """
        self.anim.save_xform(inSkinBone)
        self.anim.set_xform(inSkinBone, space="World")
        
        self.anim.save_xform(inOriBone)
        
        rt.setPropertyController(inSkinBone.controller, "Scale", rt.scaleXYZ())
        
        linkConst = rt.link_constraint()
        linkConst.addTarget(inOriBone, 0)
        
        inSkinBone.controller = linkConst
        
        self.anim.set_xform(inSkinBone, space="World")
    
    def link_skin_bones(self, inSkinBoneArray, inOriBoneArray):
        """스킨 뼈대 배열을 이름 패턴 매칭으로 원본 뼈대 배열에 연결한다.

        Args:
            inSkinBoneArray (list[rt.Node]): 연결할 스킨 뼈대 배열
            inOriBoneArray (list[rt.Node]): 원본 뼈대 배열

        Returns:
            bool: 성공하면 True, 두 배열의 길이가 다르면 False
        """
        if len(inSkinBoneArray) != len(inOriBoneArray):
            print("Error: Skin bone array and original bone array must have the same length.")
            return False
        
        skinBoneDict = {}
        oriBoneDict = {}
        
        # 스킨 뼈대 딕셔너리 생성 (이름과 패턴화된 이름을 함께 저장)
        for item in inSkinBoneArray:
            # 아이템 저장
            skinBoneDict[item.name] = item
            # 언더스코어를 별표로 변환한 패턴 생성
            namePattern = self.name.remove_name_part("Base", item.name)
            namePattern = namePattern.replace("_", "*")
            skinBoneDict[item.name + "_Pattern"] = namePattern
        
        # 원본 뼈대 딕셔너리 생성 (이름과 패턴화된 이름을 함께 저장)
        for item in inOriBoneArray:
            # 아이템 저장
            oriBoneDict[item.name] = item
            # 공백을 별표로 변환한 패턴 생성
            namePattern = self.name.remove_name_part("Base", item.name)
            namePattern = namePattern.replace(" ", "*")
            oriBoneDict[item.name + "_Pattern"] = namePattern
        
        # 정렬된 배열 생성
        sortedSkinBoneArray = []
        sortedOriBoneArray = []
        
        # 같은 패턴을 가진 뼈대들을 찾아 매칭
        for skinName, skinBone in [(k, v) for k, v in skinBoneDict.items() if not k.endswith("_Pattern")]:
            skinPattern = skinBoneDict[skinName + "_Pattern"]
            
            for oriName, oriBone in [(k, v) for k, v in oriBoneDict.items() if not k.endswith("_Pattern")]:
                oriPattern = oriBoneDict[oriName + "_Pattern"]
                
                if rt.matchPattern(skinName, pattern=oriPattern):
                    sortedSkinBoneArray.append(skinBone)
                    sortedOriBoneArray.append(oriBone)
                    break
        # 링크 연결 수행
        for i in range(len(sortedSkinBoneArray)):
            self.link_skin_bone(sortedSkinBoneArray[i], sortedOriBoneArray[i])
        
        return True
    
    def unlink_skin_bone(self, inSkinBone):
        """스킨 뼈대의 링크 제약을 해제하고 기본 PRS 컨트롤러로 되돌린다.

        Args:
            inSkinBone (rt.Node): 연결 해제할 스킨 뼈대

        Returns:
            bool: 항상 True
        """
        self.anim.save_xform(inSkinBone)
        self.anim.set_xform(inSkinBone)
        
        inSkinBone.controller = rt.prs()
        self.anim.set_xform(inSkinBone, space="World")
        
        return True
    
    def unlink_skin_bones(self, inSkinBoneArray):
        """스킨 뼈대 배열의 링크 제약을 일괄 해제한다.

        Args:
            inSkinBoneArray (list[rt.Node]): 연결 해제할 스킨 뼈대 배열

        Returns:
            bool: 항상 True
        """
        for item in inSkinBoneArray:
            if rt.isValidObj(item):
                self.unlink_skin_bone(item)
        
        return True
    
    def gen_skin_bone_name(self, inName, inSkinBoneBaseName=None):
        """원본 이름의 Base 부분을 스킨 본 이름으로 치환하여 스킨 뼈대 이름을 생성한다.

        Args:
            inName (str): 원본 뼈대 이름
            inSkinBoneBaseName (str | None): 스킨 본 Base 이름. None이면 Name 서비스의 SkinBone 값을 사용한다.

        Returns:
            str: 생성된 스킨 뼈대 이름
        """
        skinBoneBaseName = self.name.get_name_part_value_by_description("Base", "SkinBone")
        if inSkinBoneBaseName is not None:
            skinBoneBaseName = inSkinBoneBaseName
        
        skinBoneName = self.name.replace_name_part("Base", inName, skinBoneBaseName)
        skinBoneName = self.name.replace_filtering_char(skinBoneName, "_")
        return skinBoneName
    
    def set_skin_bone_property(self, inSkinBone, inSkinBoneBool):
        """객체에 스킨 본 여부를 사용자 프로퍼티(IsSkinBone)로 기록한다.

        Args:
            inSkinBone (rt.Node): 대상 스킨 뼈대
            inSkinBoneBool (bool): 스킨 본 여부 값

        Returns:
            rt.Node: 프로퍼티가 설정된 스킨 뼈대
        """
        rt.setUserProp(inSkinBone, rt.Name("IsSkinBone"), str(inSkinBoneBool))
        return inSkinBone
    
    def is_skin_bone(self, inSkinBone):
        """객체의 사용자 프로퍼티(IsSkinBone)로 스킨 본인지 확인한다.

        Args:
            inSkinBone (rt.Node): 확인할 객체

        Returns:
            bool: 스킨 본이면 True, 아니면 False
        """
        result = rt.getUserProp(inSkinBone, rt.Name("IsSkinBone"))
        if result == True:
            return True
        else:
            return False
    
    def set_skin_bone_ori_bone(self, inSkinBone, inOriBone=None):
        """스킨 뼈대에 원본 뼈대 참조를 사용자 프로퍼티(OriBone)로 기록한다.

        Args:
            inSkinBone (rt.Node): 대상 스킨 뼈대
            inOriBone (rt.Node | None): 원본 뼈대. None이면 "undefined"로 기록한다.

        Returns:
            rt.Node: 프로퍼티가 설정된 스킨 뼈대
        """
        oriBoneName = "undefined"
        if inOriBone is not None:
            oriBoneName = f"$'{inOriBone.name}'"
        
        rt.setUserProp(inSkinBone, rt.Name("OriBone"), oriBoneName)
        return inSkinBone
    
    def get_skin_bone_ori_bone(self, inSkinBone):
        """스킨 뼈대의 사용자 프로퍼티(OriBone)에서 원본 뼈대를 가져온다.

        Args:
            inSkinBone (rt.Node): 대상 스킨 뼈대

        Returns:
            rt.Node | None: 원본 뼈대 노드. 프로퍼티가 없으면 None
        """
        result = rt.getUserProp(inSkinBone, rt.Name("OriBone"))
        if result:
            return rt.execute(rt.getUserProp(inSkinBone, rt.Name("OriBone")))
        else:
            return None
    
    def set_skin_bone_parent(self, inSkinBone, inParentBone=None):
        """스킨 뼈대의 부모를 설정하고 사용자 프로퍼티(Parent)로 기록한다.

        Args:
            inSkinBone (rt.Node): 대상 스킨 뼈대
            inParentBone (rt.Node | None): 부모로 설정할 뼈대. None이면 기존 부모의 이름만 기록한다.

        Returns:
            rt.Node: 프로퍼티가 설정된 스킨 뼈대
        """
        parentName = "undefined"
        if inParentBone is not None and rt.isValidNode(inParentBone):
            inSkinBone.parent = inParentBone
            parentName = f"$'{inParentBone.name}'"
        if inParentBone is None and inSkinBone.parent is not None and rt.isValidNode(inSkinBone.parent):
            parentName = f"$'{inSkinBone.parent.name}'"
        
        rt.setUserProp(inSkinBone, rt.Name("Parent"), parentName)
        return inSkinBone
    
    def get_skin_bone_parent(self, inSkinBone):
        """스킨 뼈대의 사용자 프로퍼티(Parent)에서 부모 뼈대를 가져온다.

        Args:
            inSkinBone (rt.Node): 대상 스킨 뼈대

        Returns:
            rt.Node | None: 부모 뼈대 노드. 프로퍼티가 없으면 None
        """
        result = rt.getUserProp(inSkinBone, rt.Name("Parent"))
        if result:
            return rt.execute(rt.getUserProp(inSkinBone, rt.Name("Parent")))
        else:
            return None
    
    def create_skin_bone(self, inBone, inMesh=True, inLink=True, inSkinBoneBaseName=None):
        """원본 뼈대와 같은 트랜스폼의 스킨 뼈대를 생성한다.

        Args:
            inBone (rt.Node): 원본 뼈대
            inMesh (bool): True면 원본 메시 스냅샷을 생성하고 스킨 뼈대에 Edit_Poly 모디파이어를 추가한다.
            inLink (bool): True면 원본 뼈대에 링크 제약으로 연결한다.
            inSkinBoneBaseName (str | None): 스킨 본 Base 이름. None이면 Name 서비스의 SkinBone 값을 사용한다.

        Returns:
            rt.Node: 생성된 스킨 뼈대
        """
        skinBoneFilteringChar = "_"
        skinBonePushAmount = -0.02
        
        skinBoneBaseName = self.name.get_name_part_value_by_description("Base", "SkinBone")
        if inSkinBoneBaseName is not None:
            skinBoneBaseName = inSkinBoneBaseName
        
        skinBoneName = self.name.replace_name_part("Base", inBone.name, skinBoneBaseName)
        skinBoneName = self.name.replace_filtering_char(skinBoneName, skinBoneFilteringChar)
        
        skinBone = self.create_nub_bone(f"{skinBoneBaseName}_TempSkin", 2)
        skinBone.name = skinBoneName
        skinBone.wireColor = rt.Color(255, 88, 199)
        skinBone.transform = inBone.transform
        skinBone.boneEnable = True
        skinBone.renderable = False
        skinBone.boneScaleType = rt.Name("None")
        
        if inMesh:
            snapShotObj = rt.snapshot(inBone)
            rt.addModifier(snapShotObj, rt.Push())
            snapShotObj.modifiers[rt.Name("Push")].Push_Value = skinBonePushAmount
            rt.collapseStack(snapShotObj)
            
            rt.addModifier(skinBone, rt.Edit_Poly())
        
        if inLink:
            self.set_skin_bone_ori_bone(skinBone, inBone)
            self.link_skin_bone(skinBone, inBone)
        
        self.set_skin_bone_property(skinBone, True)
        self.set_skin_bone_parent(skinBone)
        
        return skinBone
        
    
    def create_skin_bones(self, inBoneArray, inSkipNub=True, inMesh=True, inLink=True, inSkinBoneBaseName=None):
        """원본 뼈대 배열로부터 스킨 뼈대들을 생성하고 계층을 연결한다.

        Args:
            inBoneArray (list[rt.Node]): 원본 뼈대 배열
            inSkipNub (bool): True면 End 뼈대를 건너뛴다.
            inMesh (bool): True면 메시 스냅샷 기반 처리를 사용한다.
            inLink (bool): True면 원본 뼈대에 연결한다.
            inSkinBoneBaseName (str | None): 스킨 본 Base 이름. None이면 Name 서비스의 SkinBone 값을 사용한다.

        Returns:
            list[rt.Node]: 생성된 스킨 뼈대 배열
        """
        returnBones = []
        targetBones = self.sort_bones_as_hierarchy(inBoneArray)
        
        for i in range(len(targetBones)):
            if inSkipNub:
                if self.is_end_bone(targetBones[i]):
                    continue
            skinBone = self.create_skin_bone(targetBones[i], inMesh=inMesh, inLink=inLink, inSkinBoneBaseName=inSkinBoneBaseName)
            skinBoneParentName = None
            skinBoneParent = None
            if targetBones[i].parent is not None:
                skinBoneParentName = self.gen_skin_bone_name(targetBones[i].parent.name, inSkinBoneBaseName=inSkinBoneBaseName)
                skinBoneParent = rt.getNodeByName(skinBoneParentName)
                if rt.isValidNode(skinBoneParent):
                    self.set_skin_bone_parent(skinBone, inParentBone=skinBoneParent)
            returnBones.append(skinBone)
        
        for item in returnBones:
            item.showLinks = True
            item.showLinksOnly = True
        
        return returnBones
    
    def create_skin_bone_from_bip(self, inBoneArray, inSkipNub=True, inMesh=False, inLink=True, inSkinBoneBaseName=None):
        """바이페드 객체 배열로부터 스킨 뼈대들을 생성한다.

        Twist 뼈대와 루트 노드를 제외한 Biped_Object만 대상으로 한다.

        Args:
            inBoneArray (list[rt.Node]): 바이페드 객체 배열
            inSkipNub (bool): True면 End 뼈대를 건너뛴다.
            inMesh (bool): True면 메시 스냅샷 기반 처리를 사용한다.
            inLink (bool): True면 원본 뼈대에 연결한다.
            inSkinBoneBaseName (str | None): 스킨 본 Base 이름. None이면 Name 서비스의 SkinBone 값을 사용한다.

        Returns:
            list[rt.Node]: 생성된 스킨 뼈대 배열
        """
        # 바이페드 객체만 필터링, Twist 뼈대 제외, 루트 노드 제외
        targetBones = [item for item in inBoneArray 
                      if (rt.classOf(item) == rt.Biped_Object) 
                      and (not rt.matchPattern(item.name.lower, pattern="*twist*")) 
                      and (item != item.controller.rootNode)]
        
        returnSkinBones = self.create_skin_bones(targetBones, inSkipNub=inSkipNub, inMesh=inMesh, inLink=inLink, inSkinBoneBaseName=inSkinBoneBaseName)
        
        return returnSkinBones
    
    def is_bip_skin_bone(self, inSkinBone):
        """스킨 뼈대의 원본이 바이페드 계열 컨트롤러인지 확인한다.

        Args:
            inSkinBone (rt.Node): 확인할 스킨 뼈대

        Returns:
            bool: 원본 컨트롤러가 BipSlave_control, Footsteps, Vertical_Horizontal_Turn 중 하나면 True
        """
        if self.is_skin_bone(inSkinBone):
            oriObj = self.get_skin_bone_ori_bone(inSkinBone)
            if not rt.isValidNode(oriObj):
                return False
            
            if (rt.classOf(oriObj.controller) == rt.BipSlave_control or 
                rt.classOf(oriObj.controller) == rt.Footsteps or 
                rt.classOf(oriObj.controller) == rt.Vertical_Horizontal_Turn):
                return True
        
        return False
    
    def set_bone_on(self, inBone):
        """뼈대를 활성화한다.

        Args:
            inBone (rt.Node): 활성화할 뼈대 객체
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            inBone.boneEnable = True
    
    def set_bone_off(self, inBone):
        """뼈대를 비활성화한다.

        Args:
            inBone (rt.Node): 비활성화할 뼈대 객체
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            inBone.boneEnable = False
    
    def set_bone_on_selection(self):
        """선택된 모든 뼈대를 활성화한다."""
        selArray = list(rt.getCurrentSelection())
        for item in selArray:
            self.set_bone_on(item)
    
    def set_bone_off_selection(self):
        """선택된 모든 뼈대를 비활성화한다."""
        selArray = list(rt.getCurrentSelection())
        for item in selArray:
            self.set_bone_off(item)
    
    def set_freeze_length_on(self, inBone):
        """뼈대의 길이 고정을 활성화한다.

        Args:
            inBone (rt.Node): 길이를 고정할 뼈대 객체
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            inBone.boneFreezeLength = True
    
    def set_freeze_length_off(self, inBone):
        """뼈대의 길이 고정을 비활성화한다.

        Args:
            inBone (rt.Node): 길이 고정을 해제할 뼈대 객체
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            inBone.boneFreezeLength = False
    
    def set_freeze_length_on_selection(self):
        """선택된 모든 뼈대의 길이 고정을 활성화한다."""
        selArray = list(rt.getCurrentSelection())
        for item in selArray:
            self.set_freeze_length_on(item)
    
    def set_freeze_length_off_selection(self):
        """선택된 모든 뼈대의 길이 고정을 비활성화한다."""
        selArray = list(rt.getCurrentSelection())
        for item in selArray:
            self.set_freeze_length_off(item)
            
    def turn_bone(self, inBone, inAngle):
        """뼈대의 로컬 X축을 입력된 각도만큼 회전한다.

        자식에는 영향을 주지 않는다.

        Args:
            inBone (rt.Node): 회전할 뼈대 객체
            inAngle (float): 회전 각도(도 단위)
        """
        if rt.classOf(inBone) == rt.BoneGeometry:
            self.anim.rotate_local(inBone, inAngle, 0, 0, dontAffectChildren=True)