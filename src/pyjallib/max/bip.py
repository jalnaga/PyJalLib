#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Biped 모듈 - 3ds Max의 Biped 객체 관련 기능 제공
원본 MAXScript의 bip.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""


import os

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .anim import Anim
from .name import Name
from .bone import Bone


class Bip:
    """3ds Max Biped 객체의 탐색·그룹화·키 조작과 BIP/FIG 파일 입출력 기능을 제공하는 클래스."""
    
    def __init__(self, animService=None, nameService=None, boneService=None):
        """클래스를 초기화한다.

        Args:
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            boneService (Bone | None): 본 서비스. None이면 새로 생성한다.
        """
        self.anim = animService if animService else Anim()
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim) # Pass potentially new instances
    
    def get_bips(self):
        """씬 내의 모든 Biped_Object를 찾는다.

        Returns:
            list[rt.Node]: 씬의 Biped_Object 리스트
        """
        return [obj for obj in rt.objects if rt.isKindOf(obj, rt.Biped_Object)]
    
    def get_coms_name(self):
        """씬 내 모든 Biped COM(Center of Mass)의 이름을 반환한다.

        Returns:
            list[str]: 중복 제거된 Biped COM 이름 리스트
        """
        bips = self.get_bips()
        bipComsName = []
        
        for obj in bips:
            rootName = obj.controller.rootName
            if rootName not in bipComsName:
                bipComsName.append(rootName)
                
        return bipComsName
    
    def get_coms(self):
        """씬 내 모든 Biped COM(Center of Mass) 노드를 반환한다.

        Returns:
            list[rt.Node]: 중복 제거된 Biped COM 노드 리스트
        """
        bips = self.get_bips()
        bipComs = []
        
        for obj in bips:
            rootNode = obj.controller.rootNode
            if rootNode not in bipComs:
                bipComs.append(rootNode)
                
        return bipComs
    
    def is_biped_object(self, inObj):
        """객체가 Biped 관련 객체인지 확인한다.

        Args:
            inObj (rt.Node): 확인할 객체

        Returns:
            bool: 컨트롤러가 BipSlave_control, Footsteps, Vertical_Horizontal_Turn 중 하나이면 True
        """
        return (rt.classOf(inObj.controller) == rt.BipSlave_control or 
                rt.classOf(inObj.controller) == rt.Footsteps or 
                rt.classOf(inObj.controller) == rt.Vertical_Horizontal_Turn)
    
    def get_com(self, inBip):
        """Biped 객체가 속한 COM(Center of Mass) 노드를 반환한다.

        Args:
            inBip (rt.Node): COM을 찾을 Biped 객체

        Returns:
            rt.Node | None: Biped의 COM 노드. Biped 관련 객체가 아니면 None
        """
        if self.is_biped_object(inBip):
            return inBip.controller.rootNode
        return None
    
    def get_all(self, inBip):
        """Biped와 연결된 모든 Biped 관련 객체를 반환한다 (더미·Footstep 포함).

        COM에서 시작해 자식·부모 계층을 순회하며 Biped 관련 객체를 수집한다.

        Args:
            inBip (rt.Node): 기준 Biped 객체

        Returns:
            list[rt.Node]: Biped 관련 객체 리스트. Biped 관련 객체가 아니면 빈 리스트
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
        """Biped의 실제 본 노드만 반환한다 (더미·Footstep 제외).

        Args:
            inBip (rt.Node): 기준 Biped 객체

        Returns:
            list[rt.Node]: Biped 본 노드 리스트. Biped 관련 객체가 아니면 빈 리스트
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
        """Biped의 더미와 Footstep 객체만 반환한다.

        Args:
            inBip (rt.Node): 기준 Biped 객체

        Returns:
            list[rt.Node]: 더미·Footstep 객체 리스트. Biped 관련 객체가 아니면 빈 리스트
        """
        returnVal = []
        
        if self.is_biped_object(inBip):
            bipArray = self.get_all(inBip)
            returnVal = [item for item in bipArray if rt.classOf(item) == rt.Dummy or rt.classOf(item.controller) == rt.Footsteps]
        
        return returnVal
    
    def get_all_grouped_nodes(self, inBip):
        """Biped 노드를 신체 부위 그룹별로 분류하여 반환한다.

        그룹 키: lArm, rArm, lFingers, rFingers, lLeg, rLeg, lToes, rToes, spine, tail,
        head, pelvis, neck, pony1, pony2, prop1, prop2, prop3.

        Args:
            inBip (rt.Node): 기준 Biped 객체

        Returns:
            dict[str, list[rt.Node]]: 그룹 이름을 키로 하는 노드 리스트 dict. Biped_Object가 아니면 모든 값이 빈 리스트
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
        """Biped에서 지정한 그룹 이름에 속하는 노드를 반환한다.

        Args:
            inBip (rt.Node): 기준 Biped 객체
            inGroupName (str): 그룹 이름 (예: "lArm", "rLeg", "spine")

        Returns:
            list[rt.Node]: 해당 그룹의 Biped 노드 리스트. 그룹 이름이 없으면 빈 리스트
        """
        nodes = self.get_all_grouped_nodes(inBip)
        
        if inGroupName in nodes:
            return nodes[inGroupName]
        
        return []
    
    def is_left_node(self, inNode):
        """노드가 Biped의 왼쪽(팔·손가락·다리·발가락) 그룹에 속하는지 확인한다.

        Args:
            inNode (rt.Node): 확인할 노드

        Returns:
            bool: 왼쪽 그룹에 속하면 True. Biped_Object가 아니면 False
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
        """노드가 Biped의 오른쪽(팔·손가락·다리·발가락) 그룹에 속하는지 확인한다.

        Args:
            inNode (rt.Node): 확인할 노드

        Returns:
            bool: 오른쪽 그룹에 속하면 True. Biped_Object가 아니면 False
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
        """Biped 노드를 정해진 스켈레톤 그룹 순서로 정렬하여 반환한다.

        순서: head, pelvis, lArm, lFingers, lLeg, lToes, neck, rArm, rFingers, rLeg, rToes,
        spine, tail, pony1, pony2, prop1, prop2, prop3.

        Args:
            inBip (rt.Node): 기준 Biped 객체

        Returns:
            list[rt.Node]: 그룹 순서대로 정렬된 Biped 노드 리스트
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
    
    def add_offset_time_to_selected_nodes(self, inBipNodes, inOffset):
        """Biped 노드들의 애니메이션 키를 지정한 오프셋만큼 이동시킨다.

        COM 노드는 horizontal·vertical·turning 컨트롤러의 키를, 그 외 노드는 자신의
        컨트롤러 키를 전체 선택하여 이동한다.

        Args:
            inBipNodes (list[rt.Node]): 키를 이동할 Biped 노드 리스트
            inOffset (int): 이동할 프레임 오프셋

        Returns:
            bool: 성공 여부. 리스트가 비었거나 첫 노드가 Biped 관련 객체가 아니면 False
        """
        if not inBipNodes:
            return False
        
        if not self.is_biped_object(inBipNodes[0]):
            return False
        
        for item in inBipNodes:
            if item == item.controller.rootNode:
                horizontalController = rt.getPropertyController(item.controller, "horizontal")
                verticalController = rt.getPropertyController(item.controller, "vertical")
                turningController = rt.getPropertyController(item.controller, "turning")
                
                rt.biped.deselectKeys(horizontalController)
                rt.biped.selectKeys(horizontalController)
                rt.biped.moveKeys(horizontalController, inOffset)
                
                rt.biped.deselectKeys(verticalController)
                rt.biped.selectKeys(verticalController)
                rt.biped.moveKeys(verticalController, inOffset)
                
                rt.biped.deselectKeys(turningController)
                rt.biped.selectKeys(turningController)
                rt.biped.moveKeys(turningController, inOffset)
            else:
                rt.biped.deselectKeys(item.controller)
                rt.biped.selectKeys(item.controller)
                rt.biped.moveKeys(item.controller, inOffset)
        return True
    
    def load_bip_file(self, inBipRoot, inFile):
        """Biped에 BIP 애니메이션 파일을 로드하고 애니메이션 범위를 조정한다.

        로드 후 각 노드의 마지막 키 시간을 수집하여 애니메이션 범위를 0부터 최대 키 시간까지로
        설정하고 슬라이더를 0으로 이동한다.

        Args:
            inBipRoot (rt.Node): 로드 대상 Biped 루트(COM) 노드
            inFile (str): 로드할 BIP 파일 경로
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
        """Biped에 FIG(피규어) 파일을 로드한다.

        Args:
            inBipRoot (rt.Node): 로드 대상 Biped 루트(COM) 노드
            inFile (str): 로드할 FIG 파일 경로
        """
        inBipRoot.controller.figureMode = False
        inBipRoot.controller.figureMode = True
        rt.biped.LoadFigFile(inBipRoot.controller, inFile)
        inBipRoot.controller.figureMode = False
    
    def save_fig_file(self, inBipRoot, fileName):
        """Biped의 피규어를 FIG 파일로 저장한다.

        Args:
            inBipRoot (rt.Node): 저장 대상 Biped 루트(COM) 노드
            fileName (str): 저장할 FIG 파일 경로
        """
        inBipRoot.controller.figureMode = False
        inBipRoot.controller.figureMode = True
        rt.biped.saveFigFile(inBipRoot.controller, fileName)
    
    def turn_on_figure_mode(self, inBipRoot):
        """Biped의 Figure 모드를 켠다.

        Args:
            inBipRoot (rt.Node): 대상 Biped 루트(COM) 노드
        """
        inBipRoot.controller.figureMode = True
    
    def turn_off_figure_mode(self, inBipRoot):
        """Biped의 Figure 모드를 끈다.

        Args:
            inBipRoot (rt.Node): 대상 Biped 루트(COM) 노드
        """
        inBipRoot.controller.figureMode = False
    
    def delete_copy_collection(self, inBipRoot, inName):
        """이름이 일치하는 Biped 복사 컬렉션을 삭제한다.

        Args:
            inBipRoot (rt.Node): 대상 Biped 루트(COM) 노드
            inName (str): 삭제할 컬렉션 이름
        """
        if self.is_biped_object(inBipRoot):
            colNum = rt.biped.numCopyCollections(inBipRoot.controller)
            if colNum > 0:
                for i in range(1, colNum + 1):
                    if rt.biped.getCopyCollection(inBipRoot.controller, i).name == inName:
                        rt.biped.deleteCopyCollection(inBipRoot.controller, i)
                        break
    
    def delete_all_copy_collection(self, inBipRoot):
        """Biped의 모든 복사 컬렉션을 삭제한다.

        Args:
            inBipRoot (rt.Node): 대상 Biped 루트(COM) 노드
        """
        if self.is_biped_object(inBipRoot):
            colNum = rt.biped.numCopyCollections(inBipRoot.controller)
            if colNum > 0:
                rt.biped.deleteAllCopyCollections(inBipRoot.controller)
    
    def collapse_layers(self, inBipRoot):
        """Biped의 모든 레이어를 병합한다.

        Args:
            inBipRoot (rt.Node): 대상 Biped 루트(COM) 노드

        Returns:
            None | bool: Biped 관련 객체가 아니면 False. 정상 수행 시 None
        """
        if not self.is_biped_object(inBipRoot):
            return False
        
        layerNum = rt.biped.numLayers(inBipRoot.controller)
        while layerNum > 0:
            rt.biped.collapseAtLayer(inBipRoot.controller, 0)
            layerNum = rt.biped.numLayers(inBipRoot.controller)
    
    def get_animation_range(self, inBipNodes):
        """Biped 노드들의 키 시간으로부터 애니메이션 범위를 계산한다.

        Args:
            inBipNodes (list[rt.Node]): 대상 Biped 노드 리스트

        Returns:
            rt.Interval | bool: 최소~최대 키 시간 구간. 키가 없으면 (0, 1) 구간.
                Biped 관련 객체가 아닌 노드가 하나라도 있으면 False
        """
        for item in inBipNodes:
            if not self.is_biped_object(item):
                return False
        
        minFrame = 0
        maxFrame = 1
        allTargetBipedObjs = inBipNodes
        keyTimes = []
        for item in allTargetBipedObjs:
            if item == item.controller.rootNode:
                horizontalController = rt.getPropertyController(item.controller, "horizontal")
                verticalController = rt.getPropertyController(item.controller, "vertical")
                turningController = rt.getPropertyController(item.controller, "turning")
                
                for key in horizontalController.keys:
                    keyTimes.append(float(key.time))
                for key in verticalController.keys:
                    keyTimes.append(float(key.time))
                for key in turningController.keys:
                    keyTimes.append(float(key.time))
            else:
                for key in item.controller.keys:
                    keyTimes.append(float(key.time))
        if keyTimes:
            minFrame = min(keyTimes)
            maxFrame = max(keyTimes)
        
        return rt.interval(minFrame, maxFrame)
    
    def save_bip_file(self, inBipRoot, inFile, inBakeAllKeys=True, inCollapseLayers=True, inUseAnimationRangeOnly=True, progress_callback=None):
        """Biped 애니메이션을 BIP 파일로 저장한다.

        필요 시 레이어를 병합하고 저장 구간을 계산한 뒤 saveBipFileSegment로 저장한다.

        Args:
            inBipRoot (rt.Node): 저장 대상 Biped 루트(COM) 노드
            inFile (str): 저장할 BIP 파일 경로. 디렉토리가 없으면 생성한다.
            inBakeAllKeys (bool): True이면 매 프레임 키를 베이크(keyPerFrame)하여 저장한다.
            inCollapseLayers (bool): True이면 저장 전에 레이어를 병합한다.
            inUseAnimationRangeOnly (bool): True이면 키 범위 대신 현재 애니메이션 범위를 저장 구간으로 사용한다.
            progress_callback (None): 사용되지 않는 파라미터

        Returns:
            bool: 저장 성공 여부. Biped 관련 객체가 아니거나 디렉토리 생성에 실패하면 False
        """
        if not self.is_biped_object(inBipRoot):
            return False
        
        directory = os.path.dirname(inFile)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError:
                return False
        
        if inCollapseLayers:
            self.collapse_layers(inBipRoot)
                    
        allTargetBipedObjs = self.get_nodes(inBipRoot)
        bipAnimRange = self.get_animation_range(allTargetBipedObjs)
        
        bakeStartFrame = bipAnimRange.start
        bakeEndFrame = bipAnimRange.end
        
        if inUseAnimationRangeOnly:
            startFrame = rt.execute("(animationRange.start as integer) / TicksPerFrame")
            endFrame = rt.execute("(animationRange.end as integer) / TicksPerFrame")
            bakeStartFrame = startFrame
            bakeEndFrame = endFrame
        
        if inBakeAllKeys:
            rt.biped.saveBipFileSegment(inBipRoot.controller, inFile, bakeStartFrame, bakeEndFrame, rt.name("keyPerFrame"))
        else:
            rt.biped.saveBipFileSegment(inBipRoot.controller, inFile, bakeStartFrame, bakeEndFrame)
        
        return True
    
    def link_base_skeleton(self, skinBoneBaseName="b"):
        """씬의 유일한 Biped의 본들에 대응하는 스킨 본을 찾아 링크한다.

        Biped 본 이름의 Base 파트를 지정한 문자열로 치환해 대응 스킨 본을 찾고,
        계층 순서대로 link_skin_bone을 수행한다. Twist 본과 COM은 대상에서 제외한다.

        Args:
            skinBoneBaseName (str): 스킨 본 이름의 Base 파트 문자열

        Returns:
            None | bool: 씬의 Biped COM이 정확히 1개가 아니면 False. 정상 수행 시 None
        """
        bipComs = self.get_coms()
        if len(bipComs) != 1:
            return False
        
        bipCom = bipComs[0]
        bipNodes = self.get_nodes(bipCom)
        
        targetBones = [item for item in bipNodes 
                      if (rt.classOf(item) == rt.Biped_Object) 
                      and (not rt.matchPattern(item.name, pattern="*Twist*")) 
                      and (item != item.controller.rootNode)]
        sortedBipBones = self.bone.sort_bones_as_hierarchy(targetBones)
        
        skinBones = []
        for item in sortedBipBones:
            skinBoneName = self.name.replace_name_part("Base", item.name, skinBoneBaseName)
            skinBoneName = self.name.replace_filtering_char(skinBoneName, "_")
            foundSkinBone = rt.getNodeByName(skinBoneName)
            if rt.isValidObj(foundSkinBone):
                skinBones.append(foundSkinBone)
            else:
                skinBones.append(None)
        
        for i, item in enumerate(sortedBipBones):
            if skinBones[i] is not None:
                self.bone.link_skin_bone(skinBones[i], item)
    
    def unlink_base_skeleton(self, skinBoneBaseName="b"):
        """씬의 유일한 Biped의 본들에 대응하는 스킨 본의 링크를 해제한다.

        Biped 본 이름의 Base 파트를 지정한 문자열로 치환해 대응 스킨 본을 찾고,
        찾은 스킨 본마다 unlink_skin_bone을 수행한다. Twist 본과 COM은 대상에서 제외한다.

        Args:
            skinBoneBaseName (str): 스킨 본 이름의 Base 파트 문자열

        Returns:
            None | bool: 씬의 Biped COM이 정확히 1개가 아니면 False. 정상 수행 시 None
        """
        bipComs = self.get_coms()
        if len(bipComs) != 1:
            return False
        
        bipCom = bipComs[0]
        bipNodes = self.get_nodes(bipCom)
        targetBones = [item for item in bipNodes 
                      if (rt.classOf(item) == rt.Biped_Object) 
                      and (not rt.matchPattern(item.name, pattern="*Twist*")) 
                      and (item != item.controller.rootNode)]
        sortedBipBones = self.bone.sort_bones_as_hierarchy(targetBones)
        skinBones = []
        for item in sortedBipBones:
            skinBoneName = self.name.replace_name_part("Base", item.name, skinBoneBaseName)
            skinBoneName = self.name.replace_filtering_char(skinBoneName, "_")
            foundSkinBone = rt.getNodeByName(skinBoneName)
            if rt.isValidObj(foundSkinBone):
                skinBones.append(foundSkinBone)
            else:
                skinBones.append(None)
        
        for item in skinBones:
            if item is not None:
                self.bone.unlink_skin_bone(item)
    