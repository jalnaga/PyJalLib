#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# Biped 모듈

3ds Max의 Biped 캐릭터 시스템을 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- Biped 객체 접근 및 관리
- 관절 및 뼈대 구조 조작
- Biped 파일(BIP, FIG) 로드 및 저장
- 계층 구조 및 속성 변경
- UE5 호환 이름 변환

## 구현 정보
- 원본 MAXScript의 bip.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

import os

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .anim import Anim
from .name import Name
from .bone import Bone


class Bip:
    """
    # Bip 클래스
    
    3ds Max의 Biped 객체를 관리하는 기능을 제공하는 클래스입니다.
    
    ## 주요 기능
    - Biped 객체 접근 및 참조 수집
    - Biped 뼈대의 구조적 분석 및 탐색
    - 좌/우 노드 식별 및 그룹화
    - BIP/FIG 파일 로드 및 저장
    - 일반 뼈대와 Biped 간 연결 관리
    - UE5 호환 이름 변환
    
    ## 구현 정보
    - MAXScript의 _Bip 구조체를 Python 클래스로 재구현
    - 다양한 서비스 클래스를 활용한 기능 구현
    
    ## 사용 예시
    ```python
    # Bip 객체 생성
    bip = Bip()
    
    # 씬의 모든 Biped COM 가져오기
    coms = bip.get_coms()
    
    # 특정 Biped의 모든 뼈대 가져오기
    bones = bip.get_nodes(coms[0])
    
    # BIP 파일 로드
    bip.load_bip_file(coms[0], "character.bip")
    ```
    """
    
    def __init__(self, animService=None, nameService=None, boneService=None):
        """
        Bip 클래스를 초기화합니다.
        
        ## Parameters
        - animService (Anim, optional): Anim 서비스 인스턴스 (기본값: None, 새로 생성)
        - nameService (Name, optional): Name 서비스 인스턴스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): Bone 서비스 인스턴스 (기본값: None, 새로 생성)
        
        ## 참고
        - 서비스 인스턴스가 제공되지 않으면 자동으로 생성됩니다.
        - Bone 서비스는 Name과 Anim 서비스에 의존성이 있습니다.
        """
        self.anim = animService if animService else Anim()
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim) # Pass potentially new instances
    
    def get_bips(self):
        """
        씬 내의 모든 Biped_Object를 찾습니다.
        
        ## Returns
        - list: Biped_Object 객체 리스트
        """
        return [obj for obj in rt.objects if rt.isKindOf(obj, rt.Biped_Object)]
    
    def get_coms_name(self):
        """
        씬 내 모든 Biped COM(Center of Mass)의 이름 리스트를 반환합니다.
        
        ## Returns
        - list: Biped COM 노드 이름 리스트
        """
        bips = self.get_bips()
        bipComsName = []
        
        for obj in bips:
            rootName = obj.controller.rootName
            if rootName not in bipComsName:
                bipComsName.append(rootName)
                
        return bipComsName
    
    def get_coms(self):
        """
        씬 내 모든 Biped COM(Center of Mass) 객체 리스트를 반환합니다.
        
        ## Returns
        - list: Biped COM 객체 리스트
        """
        bips = self.get_bips()
        bipComs = []
        
        for obj in bips:
            rootNode = obj.controller.rootNode
            if rootNode not in bipComs:
                bipComs.append(rootNode)
                
        return bipComs
    
    def is_biped_object(self, inObj):
        """
        객체가 Biped 관련 객체인지 확인합니다.
        
        ## Parameters
        - inObj (MaxObject): 확인할 객체
            
        ## Returns
        - bool: Biped 관련 객체이면 True, 아니면 False
        
        ## 확인 기준
        컨트롤러가 BipSlave_control, Footsteps, 또는 Vertical_Horizontal_Turn 중 하나인지 검사
        """
        return (rt.classOf(inObj.controller) == rt.BipSlave_control or 
                rt.classOf(inObj.controller) == rt.Footsteps or 
                rt.classOf(inObj.controller) == rt.Vertical_Horizontal_Turn)
    
    def get_com(self, inBip):
        """
        Biped 객체의 COM(Center of Mass)를 반환합니다.
        
        ## Parameters
        - inBip (MaxObject): COM을 찾을 Biped 객체
            
        ## Returns
        - MaxObject: Biped의 COM 객체 또는 None (Biped가 아닌 경우)
        """
        if self.is_biped_object(inBip):
            return inBip.controller.rootNode
        return None
    
    def get_all(self, inBip):
        """
        Biped와 관련된 모든 객체를 반환합니다.
        
        ## Parameters
        - inBip (MaxObject): 기준 Biped 객체
            
        ## Returns
        - list: Biped 관련 모든 객체 리스트 (COM, 뼈대, 더미, 발자국 포함)
        
        ## 동작 방식
        COM에서 시작하여 모든 자식 객체와 부모 객체를 탐색하여 Biped 관련 객체를 수집
        """
        returnVal = []
        
        if self.is_biped_object(inBip):
            root = self.get_com(inBip)
            allNodes = [root]
            returnVal = [root]
            
            for obj in allNodes:
                for child in obj.children:
                    if child not in allNodes:
                        allNodes.append(child)
                    if self.is_biped_object(child) and child not in returnVal:
                        returnVal.append(child)
                
                if obj.parent is not None:
                    if obj.parent not in allNodes:
                        allNodes.append(obj.parent)
                    if self.is_biped_object(obj.parent) and obj.parent not in returnVal:
                        returnVal.append(obj.parent)
        
        return returnVal
    
    def get_nodes(self, inBip):
        """
        Biped의 실제 노드만 반환합니다. (더미나 Footstep은 제외)
        
        ## Parameters
        - inBip (MaxObject): 기준 Biped 객체
            
        ## Returns
        - list: Biped의 실제 뼈대 노드 객체 리스트
        
        ## 제외 대상
        - Dummy 객체
        - Footsteps 컨트롤러를 사용하는 객체
        """
        returnVal = []
        
        if self.is_biped_object(inBip):
            root = self.get_com(inBip)
            allNodes = [root]
            returnVal = [root]
            
            for obj in allNodes:
                for child in obj.children:
                    if rt.classOf(child) != rt.Dummy and rt.classOf(child.controller) != rt.Footsteps:
                        if child not in allNodes:
                            allNodes.append(child)
                        if self.is_biped_object(child) and child not in returnVal:
                            returnVal.append(child)
                
                if obj.parent is not None:
                    if rt.classOf(obj.parent) != rt.Dummy and rt.classOf(obj.parent.controller) != rt.Footsteps:
                        if obj.parent not in allNodes:
                            allNodes.append(obj.parent)
                        if self.is_biped_object(obj.parent) and obj.parent not in returnVal:
                            returnVal.append(obj.parent)
        
        return returnVal
    
    def get_dummy_and_footstep(self, inBip):
        """
        Biped의 더미와 Footstep 객체만 반환합니다.
        
        ## Parameters
        - inBip (MaxObject): 기준 Biped 객체
            
        ## Returns
        - list: 더미와 Footstep 객체 리스트
        """
        returnVal = []
        
        if self.is_biped_object(inBip):
            bipArray = self.get_all(inBip)
            returnVal = [item for item in bipArray if rt.classOf(item) == rt.Dummy or rt.classOf(item.controller) == rt.Footsteps]
        
        return returnVal
    
    def get_all_grouped_nodes(self, inBip):
        """
        Biped의 노드를 체인 이름으로 그룹화하여 반환합니다.
        
        ## Parameters
        - inBip (MaxObject): 기준 Biped 객체
            
        ## Returns
        - dict: 체인 이름을 키로 하는 노드 리스트 딕셔너리
          - 키: 'lArm', 'rArm', 'lFingers', 'rFingers', 'lLeg', 'rLeg', 'lToes', 'rToes', 
                'spine', 'tail', 'head', 'pelvis', 'neck', 'pony1', 'pony2', 'prop1', 'prop2', 'prop3'
          - 값: 해당 체인에 속하는 Biped 노드 리스트
        """
        NODE_CATEGORIES = {
            1: "lArm",
            2: "rArm",
            3: "lFingers",
            4: "rFingers",
            5: "lLeg",
            6: "rLeg",
            7: "lToes",
            8: "rToes",
            9: "spine",
            10: "tail",
            11: "head",
            12: "pelvis",
            17: "neck",
            18: "pony1",
            19: "pony2",
            20: "prop1",
            21: "prop2",
            22: "prop3"
        }
        
        nodes = {category: [] for category in NODE_CATEGORIES.values()}
        
        com = inBip.controller.rootNode
        if rt.classOf(inBip) != rt.Biped_Object:
            return nodes
        
        nn = rt.biped.maxNumNodes(com)
        nl = rt.biped.maxNumLinks(com)
        
        for i in range(1, nn + 1):
            if i not in NODE_CATEGORIES:
                continue
                
            category = NODE_CATEGORIES[i]
            anode = rt.biped.getNode(com, i)
            
            if not anode:
                continue
                
            for j in range(1, nl + 1):
                alink = rt.biped.getNode(com, i, link=j)
                if alink:
                    nodes[category].append(alink)
        
        return nodes
    
    def get_grouped_nodes(self, inBip, inGroupName):
        """
        Biped의 특정 체인 이름에 해당하는 노드를 반환합니다.
        
        ## Parameters
        - inBip (MaxObject): 기준 Biped 객체
        - inGroupName (str): 체인 이름 (예: "lArm", "rLeg" 등)
            
        ## Returns
        - list: 해당 체인에 속하는 Biped 노드 리스트
        """
        nodes = self.get_all_grouped_nodes(inBip)
        
        if inGroupName in nodes:
            return nodes[inGroupName]
        
        return []
    
    def is_left_node(self, inNode):
        """
        노드가 왼쪽 부분에 속하는지 확인합니다.
        
        ## Parameters
        - inNode (MaxObject): 확인할 노드 객체
            
        ## Returns
        - bool: 왼쪽 노드이면 True, 아니면 False
        
        ## 확인 기준
        'lArm', 'lFingers', 'lLeg', 'lToes' 그룹에 속하는지 검사
        """
        if rt.classOf(inNode) != rt.Biped_Object:
            return False
        com = self.get_com(inNode)
        nodes = self.get_all_grouped_nodes(com)
        
        categories = ["lArm", "lFingers", "lLeg", "lToes"]
        for category in categories:
            groupedNodes = nodes[category]
            if inNode in groupedNodes:
                return True
        
        return False
    
    def is_right_node(self, inNode):
        """
        노드가 오른쪽 부분에 속하는지 확인합니다.
        
        ## Parameters
        - inNode (MaxObject): 확인할 노드 객체
            
        ## Returns
        - bool: 오른쪽 노드이면 True, 아니면 False
        
        ## 확인 기준
        'rArm', 'rFingers', 'rLeg', 'rToes' 그룹에 속하는지 검사
        """
        if rt.classOf(inNode) != rt.Biped_Object:
            return False
        com = self.get_com(inNode)
        nodes = self.get_all_grouped_nodes(com)
        
        categories = ["rArm", "rFingers", "rLeg", "rToes"]
        for category in categories:
            groupedNodes = nodes[category]
            if inNode in groupedNodes:
                return True
        
        return False
    
    def get_nodes_by_skeleton_order(self, inBip):
        """
        스켈레톤 순서대로 Biped 노드를 반환합니다.
        
        ## Parameters
        - inBip (MaxObject): 기준 Biped 객체
            
        ## Returns
        - list: 순서대로 정렬된 Biped 노드 리스트
        
        ## 정렬 순서
        head → pelvis → lArm → lFingers → lLeg → lToes → neck →
        rArm → rFingers → rLeg → rToes → spine → tail → 
        pony1 → pony2 → prop1 → prop2 → prop3
        """
        nodes = self.get_all_grouped_nodes(inBip)
                    
        ORDER = [
            "head", "pelvis", "lArm", "lFingers", "lLeg", "lToes", "neck",
            "rArm", "rFingers", "rLeg", "rToes", "spine", "tail", 
            "pony1", "pony2", "prop1", "prop2", "prop3"
        ]
        
        bipNodeArray = []
        for category in ORDER:
            bipNodeArray.extend(nodes[category])
        
        return bipNodeArray
    
    def load_bip_file(self, inBipRoot, inFile):
        """
        Biped BIP 파일을 로드합니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 로드 대상 Biped 루트 노드
        - inFile (str): 로드할 BIP 파일 경로
        
        ## 동작 과정
        1. Figure 모드 비활성화
        2. BIP 파일 로드
        3. Figure 모드 활성화 후 다시 비활성화
        4. 키프레임 범위 조정
        """
        bipNodeArray = self.get_all(inBipRoot)
        
        inBipRoot.controller.figureMode = False
        rt.biped.loadBipFile(inBipRoot.controller, inFile)
        inBipRoot.controller.figureMode = True
        inBipRoot.controller.figureMode = False
        
        keyRange = []
        for i in range(1, len(bipNodeArray)):
            if bipNodeArray[i].controller.keys.count != 0 and bipNodeArray[i].controller.keys.count != -1:
                keyTime = bipNodeArray[i].controller.keys[bipNodeArray[i].controller.keys.count - 1].time
                if keyTime not in keyRange:
                    keyRange.append(keyTime)
        
        if keyRange and max(keyRange) != 0:
            rt.animationRange = rt.interval(0, max(keyRange))
            rt.sliderTime = 0
    
    def load_fig_file(self, inBipRoot, inFile):
        """
        Biped FIG 파일을 로드합니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 로드 대상 Biped 루트 노드
        - inFile (str): 로드할 FIG 파일 경로
        
        ## 동작 과정
        1. Figure 모드 비활성화 후 다시 활성화
        2. FIG 파일 로드
        3. Figure 모드 비활성화
        """
        inBipRoot.controller.figureMode = False
        inBipRoot.controller.figureMode = True
        rt.biped.LoadFigFile(inBipRoot.controller, inFile)
        inBipRoot.controller.figureMode = False
    
    def save_fig_file(self, inBipRoot, fileName):
        """
        Biped FIG 파일을 저장합니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 저장 대상 Biped 루트 노드
        - fileName (str): 저장할 FIG 파일 경로
        
        ## 동작 과정
        1. Figure 모드 비활성화 후 다시 활성화
        2. FIG 파일 저장
        """
        inBipRoot.controller.figureMode = False
        inBipRoot.controller.figureMode = True
        rt.biped.saveFigFile(inBipRoot.controller, fileName)
    
    def turn_on_figure_mode(self, inBipRoot):
        """
        Biped Figure 모드를 켭니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 대상 Biped 객체
        """
        inBipRoot.controller.figureMode = True
    
    def turn_off_figure_mode(self, inBipRoot):
        """
        Biped Figure 모드를 끕니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 대상 Biped 객체
        """
        inBipRoot.controller.figureMode = False
    
    def delete_copy_collection(self, inBipRoot, inName):
        """
        Biped 복사 컬렉션을 삭제합니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 대상 Biped 객체
        - inName (str): 삭제할 컬렉션 이름
        """
        if self.is_biped_object(inBipRoot):
            colNum = rt.biped.numCopyCollections(inBipRoot.controller)
            if colNum > 0:
                for i in range(1, colNum + 1):
                    if rt.biped.getCopyCollection(inBipRoot.controller, i).name == inName:
                        rt.biped.deleteCopyCollection(inBipRoot.controller, i)
                        break
    
    def delete_all_copy_collection(self, inBipRoot):
        """
        Biped의 모든 복사 컬렉션을 삭제합니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 대상 Biped 객체
        """
        if self.is_biped_object(inBipRoot):
            colNum = rt.biped.numCopyCollections(inBipRoot.controller)
            if colNum > 0:
                rt.biped.deleteAllCopyCollections(inBipRoot.controller)
    
    def link_base_skeleton(self, skinBoneBaseName="b"):
        """
        일반 뼈대를 Biped에 연결합니다.
        
        ## Parameters
        - skinBoneBaseName (str): 스킨용 뼈대 기본 이름 (기본값: "b")
        
        ## 동작 과정
        1. 씬의 모든 Biped 객체를 찾음
        2. 각 Biped에 해당하는 일반 뼈대를 이름으로 찾음
        3. 변환 정보 저장
        4. 일반 뼈대에 링크 제약 할당
        5. Biped를 제약의 타겟으로 설정
        """
        rt.setWaitCursor()
        
        bipSkel = self.get_bips()
        baseSkel = [None] * len(bipSkel)
        
        for i in range(len(bipSkel)):
            baseSkeletonName = self.name.replace_base(bipSkel[i].name, skinBoneBaseName)
            baseSkeletonName = self.name.replace_filteringChar(baseSkeletonName, "_")
            baseSkelObj = rt.getNodeByName(baseSkeletonName)
            if rt.isValidObj(baseSkelObj):
                baseSkel[i] = baseSkelObj
        
            self.anim.save_xform(bipSkel[i])
            self.anim.set_xform(bipSkel[i])
            
            self.anim.save_xform(baseSkel[i])
            self.anim.set_xform(baseSkel[i])
        
        for i in range(len(baseSkel)):
            if baseSkel[i] is not None:
                baseSkel[i].scale.controller = rt.scaleXYZ()
                baseSkel[i].controller = rt.link_constraint()
                
                self.anim.set_xform([baseSkel[i]], space="World")
                baseSkel[i].transform.controller.AddTarget(bipSkel[i], 0)
        
        for i in range(len(baseSkel)):
            if baseSkel[i] is not None:
                baseSkel[i].boneEnable = True
                
        rt.setArrowCursor()
    
    def unlink_base_skeleton(self, skinBoneBaseName="b"):
        """
        Biped에서 일반 뼈대 연결을 해제합니다.
        
        ## Parameters
        - skinBoneBaseName (str): 스킨용 뼈대 기본 이름 (기본값: "b")
        
        ## 동작 과정
        1. 씬의 Biped COM과 관련 노드 찾기
        2. 각 Biped 노드에 해당하는 일반 뼈대 찾기
        3. 변환 정보 저장
        4. 링크 제약 제거하고 기본 PRS 컨트롤러로 변경
        5. 원래 위치로 복원
        """
        rt.setWaitCursor()
        
        bipComs = self.get_coms()
        allBips = self.get_nodes(bipComs[0])
        bipSkel = [item for item in allBips if item != bipComs[0]]
        baseSkel = [None] * len(bipSkel)
        
        for i in range(len(bipSkel)):
            baseSkeletonName = self.name.replace_name_part("Base", bipSkel[i].name, skinBoneBaseName)
            baseSkeletonName = self.name.replace_filtering_char(baseSkeletonName, "_")
            print("baseSkeletonName", baseSkeletonName)
            baseSkelObj = rt.getNodeByName(baseSkeletonName)
            print("baseSkelObj", baseSkelObj)
            if rt.isValidObj(baseSkelObj):
                baseSkel[i] = baseSkelObj
        
            self.anim.save_xform(bipSkel[i])
            self.anim.set_xform(bipSkel[i])
            
            self.anim.save_xform(baseSkel[i])
            self.anim.set_xform(baseSkel[i])
        
        for i in range(len(baseSkel)):
            if baseSkel[i] is not None:
                baseSkel[i].controller = rt.prs()
                self.anim.set_xform([baseSkel[i]], space="World")
        
        for i in range(len(baseSkel)):
            if baseSkel[i] is not None:
                baseSkel[i].boneEnable = True
                
        rt.setArrowCursor()
        
    def convert_name_for_ue5(self, inBipRoot, inBipNameConfigFile):
        """
        Biped 이름을 UE5 호환 형식으로 변환합니다.
        
        ## Parameters
        - inBipRoot (MaxObject): 변환할 Biped 객체
        - inBipNameConfigFile (str): Biped 이름 설정 파일 경로
            
        ## Returns
        - bool: 변환 성공 여부
        
        ## 변환 내용
        1. 모든 Biped 노드 이름을 소문자로 변환
        2. 설정 파일의 이름 규칙에 따라 부위별 이름 매핑
        3. 손가락과 발가락 이름을 특수 처리 (index, middle, thumb 등)
        4. Spine과 Neck 노드 인덱스 조정 (1부터 시작하도록)
        """
        bipComs = self.get_coms()
    
        if len(bipComs) > 1:
            rt.messageBox("Please select only one Biped object.")
            return False
        
        from pyjallib.max.name import Name
        
        bipNameTool = Name(configPath=inBipNameConfigFile)
        
        bipObj = bipComs[0]
        bipNodes = self.get_all(bipObj)
        for bipNode in bipNodes:
            if bipNode.name == bipObj.controller.rootName:
                bipNode.name = bipNode.name.lower()
                continue
            
            bipNodeNameDict = bipNameTool.convert_to_dictionary(bipNode.name)
            
            newNameDict = {}
            for namePartName, value in bipNodeNameDict.items():
                namePart = bipNameTool.get_name_part(namePartName)
                desc = namePart.get_description_by_value(value)
                
                if namePartName == "RealName" or namePartName == "Index" or namePartName == "Nub":
                    newNameDict[namePartName] = value
                else:
                    newNameDict[namePartName] = self.name.get_name_part(namePartName).get_value_by_description(desc)
            
            if newNameDict["Index"] == "" and self.name._has_digit(newNameDict["RealName"]):
                if "Finger" not in newNameDict["RealName"]:
                    splitedRealName = self.name._split_into_string_and_digit(newNameDict["RealName"])
                    newNameDict["RealName"] = splitedRealName[0]
                    newNameDict["Index"] = splitedRealName[1]
            if newNameDict["Nub"] == "" and bipNameTool.get_name_part_value_by_description("Nub", "Nub") in (newNameDict["RealName"]):
                newNameDict["RealName"] = newNameDict["RealName"].replace(bipNameTool.get_name_part_value_by_description("Nub", "Nub"), "")
                newNameDict["Nub"] = self.name.get_name_part_value_by_description("Nub", "Nub")
            
            if newNameDict["RealName"] == "Forearm":
                newNameDict["RealName"] = "Lowerarm"
            
            if newNameDict["RealName"] == "Spine" or newNameDict["RealName"] == "Neck":
                if newNameDict["Index"] == "":
                    newNameDict["Index"] = str(int(1)).zfill(self.name.get_padding_num())
                else:
                    newNameDict["Index"] = str(int(newNameDict["Index"]) + 1).zfill(self.name.get_padding_num())
                
            newBipName = self.name.combine(newNameDict)
            
            bipNode.name = newBipName.lower()
            
        indices = []
        if bipObj.controller.knuckles:
            pass
        else:
            indices = list(range(0, 15, 3))
            
        fingerNum = bipObj.controller.fingers
        fingerLinkNum = bipObj.controller.fingerLinks
            
        lFingersList = []
        rFingersList = []
        
        for i in range(1, fingerNum+1):
            fingers = []
            for j in range(1, fingerLinkNum+1):
                linkIndex = (i-1)*fingerLinkNum + j
                fingerNode = rt.biped.getNode(bipObj.controller, rt.name("lFingers"), link=linkIndex)
                fingers.append(fingerNode)
            lFingersList.append(fingers)
        for i in range(1, fingerNum+1):
            fingers = []
            for j in range(1, fingerLinkNum+1):
                linkIndex = (i-1)*fingerLinkNum + j
                fingerNode = rt.biped.getNode(bipObj.controller, rt.name("rFingers"), link=linkIndex)
                fingers.append(fingerNode)
            rFingersList.append(fingers)
            
        fingerName = ["thumb", "index", "middle", "ring", "pinky"]
        
        for i, fingers in enumerate(lFingersList):
            for j, item in enumerate(fingers):
                item.name = self.name.replace_name_part("RealName", item.name, fingerName[i])
                item.name = self.name.replace_name_part("Index", item.name, str(j+1))
            
            fingerNub = self.bone.get_every_children(fingers[-1])[0]
            fingerNub.name = self.name.replace_name_part("RealName", fingerNub.name, fingerName[i])
            fingerNub.name = self.name.remove_name_part("Index", fingerNub.name)
            fingerNub.name = self.name.replace_name_part("Nub", fingerNub.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
        
        for i, fingers in enumerate(rFingersList):
            for j, item in enumerate(fingers):
                item.name = self.name.replace_name_part("RealName", item.name, fingerName[i])
                item.name = self.name.replace_name_part("Index", item.name, str(j+1))
            
            fingerNub = self.bone.get_every_children(fingers[-1])[0]
            fingerNub.name = self.name.replace_name_part("RealName", fingerNub.name, fingerName[i])
            fingerNub.name = self.name.remove_name_part("Index", fingerNub.name)
            fingerNub.name = self.name.replace_name_part("Nub", fingerNub.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
        
        lToesList = []
        rToesList = []
        
        toeNum = bipObj.controller.toes
        toeLinkNum = bipObj.controller.toeLinks
        
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
                item.name = self.name.replace_name_part("RealName", item.name, "ball"+str(i+1))
                item.name = self.name.replace_name_part("Index", item.name, str(j+1))
            
            toeNub = self.bone.get_every_children(toes[-1])[0]
            toeNub.name = self.name.replace_name_part("RealName", toeNub.name, "ball"+str(i+1))
            toeNub.name = self.name.remove_name_part("Index", toeNub.name)
            toeNub.name = self.name.replace_name_part("Nub", toeNub.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
            
        for i, toes in enumerate(rToesList):
            for j, item in enumerate(toes):
                item.name = self.name.replace_name_part("RealName", item.name, "ball"+str(i+1))
                item.name = self.name.replace_name_part("Index", item.name, str(j+1))
            
            toeNub = self.bone.get_every_children(toes[-1])[0]
            toeNub.name = self.name.replace_name_part("RealName", toeNub.name, "ball"+str(i+1))
            toeNub.name = self.name.remove_name_part("Index", toeNub.name)
            toeNub.name = self.name.replace_name_part("Nub", toeNub.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
        
        if toeNum == 1:
            if toeLinkNum == 1:
                lToesList[0][0].name = self.name.replace_name_part("RealName", lToesList[0][0].name, "ball")
                lToesList[0][0].name = self.name.remove_name_part("Index", lToesList[0][0].name)
            else:
                for i, item in enumerate(lToesList[0]):
                    item.name = self.name.replace_name_part("RealName", item.name, "ball")
                    item.name = self.name.replace_name_part("Index", item.name, str(i+1))
            
            toeNub = self.bone.get_every_children(lToesList[0][-1])[0]
            toeNub.name = self.name.replace_name_part("RealName", toeNub.name, "ball")
            toeNub.name = self.name.remove_name_part("Index", toeNub.name)
            toeNub.name = self.name.replace_name_part("Nub", toeNub.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
            
            if toeLinkNum == 1:
                rToesList[0][0].name = self.name.replace_name_part("RealName", lToesList[0][0].name, "ball")
                rToesList[0][0].name = self.name.remove_name_part("Index", lToesList[0][0].name)
            else:
                for i, item in enumerate(rToesList[0]):
                    item.name = self.name.replace_name_part("RealName", item.name, "ball")
                    item.name = self.name.replace_name_part("Index", item.name, str(i+1))
            
            toeNub = self.bone.get_every_children(rToesList[0][-1])[0]
            toeNub.name = self.name.replace_name_part("RealName", toeNub.name, "ball")
            toeNub.name = self.name.remove_name_part("Index", toeNub.name)
            toeNub.name = self.name.replace_name_part("Nub", toeNub.name, self.name.get_name_part_value_by_description("Nub", "Nub"))
        
        return True