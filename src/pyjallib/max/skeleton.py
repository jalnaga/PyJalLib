#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
스켈레톤 모듈 - 3ds Max용 스켈레톤 관련 기능 제공
원본 MAXScript의 skeleton.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .anim import Anim
from .name import Name
from .bone import Bone
from .bip import Bip
from .layer import Layer

from .progress import Progress


class Skeleton:
    """
    스켈레톤 관련 기능을 제공하는 클래스.
    MAXScript의 _Skeleton 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, animService=None, nameService=None, boneService=None, bipService=None, layerService=None):
        """
        클래스 초기화
        
        Args:
            animService: Anim 서비스 인스턴스 (제공되지 않으면 새로 생성)
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
            boneService: Bone 서비스 인스턴스 (제공되지 않으면 새로 생성)
            bipService: Bip 서비스 인스턴스 (제공되지 않으면 새로 생성)
            layerService: Layer 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.anim = animService if animService else Anim()
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.bip = bipService if bipService else Bip(animService=self.anim, nameService=self.name, boneService=self.bone)
        self.layer = layerService if layerService else Layer()
        
    # def get_dependencies(self, inObj):
    #     """
    #     객체의 의존성을 가져옴
        
    #     Args:
    #         inObj: 의존성을 확인할 객체 또는 객체 배열
            
    #     Returns:
    #         의존성 노드 배열
    #     """
    #     # core - 단일 객체인 경우 배열로 변환
    #     if rt.classOf(inObj) != rt.Array:
    #         inObj = [inObj]
    #     else:
    #         # rt.Array를 Python 리스트로 변환
    #         inObj = list(inObj)
        
    #     nodeArray = []
    #     res = inObj.copy()
        
    #     for each in inObj:
    #         # Biped 객체인 경우 건너뛰기
    #         if self.bip.is_biped_object(each):
    #             continue
            
    #         # 컨트롤러의 의존성 추가
    #         controller_deps = rt.refs.dependson(each.controller)
    #         if controller_deps:
    #             res.extend(controller_deps)
            
    #         # Skin 속성이 있는 경우 Skin의 의존성 추가
    #         if rt.isProperty(each, rt.name("Skin")):
    #             skin_deps = rt.refs.dependson(each.skin)
    #             if skin_deps:
    #                 res.extend(skin_deps)
            
    #         # 의존성 배열을 순회하면서 추가 의존성 확인
    #         i = 0
    #         while i < len(res):
    #             # 노드가 아닌 경우 추가 의존성 확인
    #             if rt.superClassOf(res[i]) != rt.node:
    #                 additional_deps = rt.refs.dependson(res[i])
    #                 if additional_deps:
    #                     res.extend(additional_deps)
    #             # 유효한 노드인 경우
    #             if rt.isValidNode(res[i]):
    #                 # 노드 배열에 추가
    #                 if res[i] not in nodeArray:
    #                     nodeArray.append(res[i])
                    
    #                 # 부모 노드 확인 및 추가
    #                 parentNode = res[i].parent
    #                 if rt.isValidNode(parentNode) and parentNode not in nodeArray:
    #                     res.append(parentNode)
    #                     nodeArray.append(parentNode)
                
    #             i += 1
        
    #     return nodeArray
    
    def get_dependencies(self, inObjs):
        targetObjs = rt.Array()
        for item in inObjs:
            if rt.isValidNode(item):
                rt.append(targetObjs, item)

        maxcriptCode = ""
        maxcriptCode += "fn pyjallib_max_skeleton_get_dependencies obj = \n"
        maxcriptCode += "(\n"
        maxcriptCode += "    node_array = #()\n"
        maxcriptCode += "    res = deepCopy obj\n"
        maxcriptCode += "    \n"
        maxcriptCode += "    for each in obj do \n"
        maxcriptCode += "    (\n"
        maxcriptCode += "        isBipedObj = (classOf each.controller == BipSlave_control) or (classOf each.controller == Footsteps) or (classOf each.controller == Vertical_Horizontal_Turn)\n"
        maxcriptCode += "        if isBipedObj then continue\n"
        maxcriptCode += "\n"
        maxcriptCode += "        join res (refs.dependson each.controller)\n"
        maxcriptCode += "\n"
        maxcriptCode += "        if isproperty each #skin do ( join res (refs.dependson each.skin) )\n"
        maxcriptCode += "\n"
        maxcriptCode += "        i = 0\n"
        maxcriptCode += "        while i < res.count do \n"
        maxcriptCode += "        (\n"
        maxcriptCode += "            i += 1\n"
        maxcriptCode += "            if classof (superclassof res[i]) != node then \n"
        maxcriptCode += "                join res (refs.dependson res[i])\n"
        maxcriptCode += "\n"
        maxcriptCode += "            else if isvalidnode res[i] do\n"
        maxcriptCode += "            (\n"
        maxcriptCode += "                appendifunique node_array res[i]\n"
        maxcriptCode += "\n"
        maxcriptCode += "                parent_node=res[i].parent\n"
        maxcriptCode += "                if isValidNode parent_node and findItem node_array parent_node == 0 do\n"
        maxcriptCode += "                ( \n"
        maxcriptCode += "                    appendIfUnique res parent_node\n"
        maxcriptCode += "                    appendIfUnique node_array parent_node\n"
        maxcriptCode += "                )\n"
        maxcriptCode += "            )\n"
        maxcriptCode += "        )\n"
        maxcriptCode += "    )\n"
        maxcriptCode += "    \n"
        maxcriptCode += "    return node_array\n"
        maxcriptCode += ")\n"

        rt.execute(maxcriptCode)
        return rt.pyjallib_max_skeleton_get_dependencies(targetObjs)
    
    def get_all_dependencies(self, inObjs, inAddonLayerName="Rig_Addon"):
        """
        객체의 모든 의존성을 가져옴 (애드온 레이어 포함)
        
        Args:
            inObjs: 의존성을 확인할 객체 배열
            inAddonLayerName: 애드온 레이어 이름 (기본값: "Rig_Addon")
            
        Returns:
            모든 의존성 노드 배열 (중복 제거됨)
        """
        returnArray = []
        nodeArray = self.get_dependencies(inObjs)
        
        # 애드온 레이어의 노드들만 필터링
        addOnArray = []
        for item in nodeArray:
            if item.layer.name == inAddonLayerName:
                addOnArray.append(item)
        
        # 애드온 노드들의 의존성 가져오기
        addOnRefArray = self.get_dependencies(addOnArray)
            
        # 모든 노드들을 returnArray에 추가 (중복 없이)
        for item in nodeArray:
            if item not in returnArray:
                returnArray.append(item)
        
        for item in addOnRefArray:
            if item not in returnArray:
                returnArray.append(item)
        
        return returnArray