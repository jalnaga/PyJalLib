#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Biped 모듈 - 3ds Max의 Biped 객체 관련 기능 제공
원본 MAXScript의 bip.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .anim import Anim
from .name import Name
from .bone import Bone


class Bip:
    """
    Biped 객체 관련 기능을 제공하는 클래스.
    MAXScript의 _Bip 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, animService=None, nameService=None, boneService=None):
        """
        클래스 초기화
        
        Args:
            animService: Anim 서비스 인스턴스 (제공되지 않으면 새로 생성)
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
            boneService: Bone 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.anim = animService if animService else Anim()
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim) # Pass potentially new instances
    
    def get_bips(self):
        """
        씬 내의 모든 Biped_Object를 찾음
        
        Returns:
            Biped_Object 리스트
        """
        return [obj for obj in rt.objects if rt.isKindOf(obj, rt.Biped_Object)]
    
    def get_coms_name(self):
        """
        씬 내 모든 Biped COM(Center of Mass)의 이름 리스트 반환
        
        Returns:
            Biped COM 이름 리스트
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
        씬 내 모든 Biped COM(Center of Mass) 객체 리스트 반환
        
        Returns:
            Biped COM 객체 리스트
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
        객체가 Biped 관련 객체인지 확인
        
        Args:
            inObj: 확인할 객체
            
        Returns:
            Biped 관련 객체이면 True, 아니면 False
        """
        return (rt.classOf(inObj.controller) == rt.BipSlave_control or 
                rt.classOf(inObj.controller) == rt.Footsteps or 
                rt.classOf(inObj.controller) == rt.Vertical_Horizontal_Turn)
    
    def get_com(self, inBip):
        """
        Biped 객체의 COM(Center of Mass) 반환
        
        Args:
            inBip: COM을 찾을 Biped 객체
            
        Returns:
            Biped의 COM 객체 또는 None
        """
        if self.is_biped_object(inBip):
            return inBip.controller.rootNode
        return None
    
    def get_all(self, inBip):
        """
        Biped와 관련된 모든 객체 반환
        
        Args:
            inBip: 기준 Biped 객체
            
        Returns:
            Biped 관련 모든 객체 리스트
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
        Biped의 실제 노드만 반환 (더미나 Footstep은 제외)
        
        Args:
            inBip: 기준 Biped 객체
            
        Returns:
            Biped의 노드 객체 리스트
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
        Biped의 더미와 Footstep 객체만 반환
        
        Args:
            inBip: 기준 Biped 객체
            
        Returns:
            더미와 Footstep 객체 리스트
        """
        returnVal = []
        
        if self.is_biped_object(inBip):
            bipArray = self.get_all(inBip)
            returnVal = [item for item in bipArray if rt.classOf(item) == rt.Dummy or rt.classOf(item.controller) == rt.Footsteps]
        
        return returnVal
    
    def get_all_grouped_nodes(self, inBip):
        """
        Biped의 체인 이름으로 노드 반환
        
        Args:
            inBip: 기준 Biped 객체
            
        Returns:
            해당 체인에 속하는 Biped 노드 리스트
        """
        # Define node categories with their corresponding index numbers
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
        
        # Initialize node collections dictionary
        nodes = {category: [] for category in NODE_CATEGORIES.values()}
        
        com = inBip.controller.rootNode
        if rt.classOf(inBip) != rt.Biped_Object:
            return nodes
        
        nn = rt.biped.maxNumNodes(com)
        nl = rt.biped.maxNumLinks(com)
        
        # Collect nodes by category
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
    
    def get_grouped_nodes(self, inBip,inGroupName):
        """
        Biped의 체인 이름으로 노드 반환
        
        Args:
            inBip: 기준 Biped 객체
            inGroupName: 체인 이름 (예: "lArm", "rLeg" 등)
            
        Returns:
            해당 체인에 속하는 Biped 노드 리스트
        """
        nodes = self.get_all_grouped_nodes(inBip)
        
        if inGroupName in nodes:
            return nodes[inGroupName]
        
        return []
    
    def is_left_node(self, inNode):
        """
        노드가 왼쪽인지 확인
        
        Args:
            inNode: 확인할 노드 객체
            
        Returns:
            왼쪽 노드이면 True, 아니면 False
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
        노드가 오른쪽인지 확인
        
        Args:
            inNode: 확인할 노드 객체
            
        Returns:
            오른쪽 노드이면 True, 아니면 False
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
        스켈레톤 순서대로 Biped 노드 반환
        
        Args:
            inBip: 기준 Biped 객체
            
        Returns:
            순서대로 정렬된 Biped 노드 리스트
        """
        nodes = self.get_all_grouped_nodes(inBip)
                    
        # Define the order of categories in final array
        ORDER = [
            "head", "pelvis", "lArm", "lFingers", "lLeg", "lToes", "neck",
            "rArm", "rFingers", "rLeg", "rToes", "spine", "tail", 
            "pony1", "pony2", "prop1", "prop2", "prop3"
        ]
        
        # Build final array in the desired order
        bipNodeArray = []
        for category in ORDER:
            bipNodeArray.extend(nodes[category])
        
        return bipNodeArray
    
    def load_bip_file(self, inBipRoot, inFile):
        """
        Biped BIP 파일 로드
        
        Args:
            inBipRoot: 로드 대상 Biped 루트 노드
            inFile: 로드할 BIP 파일 경로
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
        Biped FIG 파일 로드
        
        Args:
            inBipRoot: 로드 대상 Biped 루트 노드
            inFile: 로드할 FIG 파일 경로
        """
        inBipRoot.controller.figureMode = False
        inBipRoot.controller.figureMode = True
        rt.biped.LoadFigFile(inBipRoot.controller, inFile)
        inBipRoot.controller.figureMode = False
    
    def save_fig_file(self, inBipRoot, fileName):
        """
        Biped FIG 파일 저장
        
        Args:
            inBipRoot: 저장 대상 Biped 루트 노드
            fileName: 저장할 FIG 파일 경로
        """
        inBipRoot.controller.figureMode = False
        inBipRoot.controller.figureMode = True
        rt.biped.saveFigFile(inBipRoot.controller, fileName)
    
    def turn_on_figure_mode(self, inBipRoot):
        """
        Biped Figure 모드 켜기
        
        Args:
            inBipRoot: 대상 Biped 객체
        """
        inBipRoot.controller.figureMode = True
    
    def turn_off_figure_mode(self, inBipRoot):
        """
        Biped Figure 모드 끄기
        
        Args:
            inBipRoot: 대상 Biped 객체
        """
        inBipRoot.controller.figureMode = False
    
    def delete_copy_collection(self, inBipRoot, inName):
        """
        Biped 복사 컬렉션 삭제
        
        Args:
            inBipRoot: 대상 Biped 객체
            inName: 삭제할 컬렉션 이름
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
        Biped 모든 복사 컬렉션 삭제
        
        Args:
            inBipRoot: 대상 Biped 객체
        """
        if self.is_biped_object(inBipRoot):
            colNum = rt.biped.numCopyCollections(inBipRoot.controller)
            if colNum > 0:
                rt.biped.deleteAllCopyCollections(inBipRoot.controller)
    
    def link_base_skeleton(self):
        """
        기본 스켈레톤 링크 (Biped와 일반 뼈대 연결)
        """
        rt.setWaitCursor()
        skinBoneBaseName = "b"
        
        bipSkel = self.get_bips()
        baseSkel = [None] * len(bipSkel)
        
        for i in range(len(bipSkel)):
            baseSkeletonName = self.name.replace_base(bipSkel[i].name, skinBoneBaseName)
            baseSkeletonName = self.name.replace_filteringChar(baseSkeletonName, "_")
            baseSkelObj = rt.getNodeByName(baseSkeletonName)
            if rt.isValidObj(baseSkelObj):
                baseSkel[i] = baseSkelObj
        
        self.anim.save_xform(bipSkel)
        self.anim.set_xform(bipSkel)
        
        self.anim.save_xform(baseSkel)
        self.anim.set_xform(baseSkel)
        
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
    
    def unlink_base_skeleton(self):
        """
        기본 스켈레톤 링크 해제
        """
        rt.setWaitCursor()
        skinBoneBaseName = "b"
        
        bipSkel = self.get_bips()
        baseSkel = [None] * len(bipSkel)
        
        for i in range(len(bipSkel)):
            baseSkeletonName = self.name.replace_base(bipSkel[i].name, skinBoneBaseName)
            baseSkeletonName = self.name.replace_filteringChar(baseSkeletonName, "_")
            baseSkelObj = rt.getNodeByName(baseSkeletonName)
            if rt.isValidObj(baseSkelObj):
                baseSkel[i] = baseSkelObj
        
        self.anim.save_xform(bipSkel)
        self.anim.set_xform(bipSkel)
        
        self.anim.save_xform(baseSkel)
        self.anim.set_xform(baseSkel)
        
        for i in range(len(baseSkel)):
            if baseSkel[i] is not None:
                baseSkel[i].controller = rt.prs()
                self.anim.set_xform([baseSkel[i]], space="World")
        
        for i in range(len(baseSkel)):
            if baseSkel[i] is not None:
                baseSkel[i].boneEnable = True
                
        rt.setArrowCursor()