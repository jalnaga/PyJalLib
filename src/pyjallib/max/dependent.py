#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dependent 모듈 - 3ds Max 오브젝트 의존성 탐색 기능
선택된 오브젝트와 관련된 모든 의존성 노드들을 찾아내는 기능을 제공합니다.
특히 FBX 익스포트 시 필요한 관련 노드들(컨트롤러, 스킨, 부모 체인, 자식 노드, AddOn Helper 등)을
자동으로 탐색합니다.
"""

from pymxs import runtime as rt


class Dependent:
    """
    오브젝트 의존성 탐색을 위한 클래스

    3ds Max에서 특정 오브젝트의 dependency 노드들(컨트롤러 타겟, 스킨 본, 부모 체인 등)과
    dependent 노드들(자식, DependentNodes)을 탐색합니다.

    Attributes:
        layerService: Layer 서비스 인스턴스
    """

    def __init__(self, layerService=None):
        """
        초기화 함수

        Args:
            layerService: Layer 서비스 인스턴스 (AddOn 레이어 탐색에 사용)
        """
        self.layerService = layerService

    def get_all_dependencies(self, inObjArray, inVisited=None):
        """
        주어진 오브젝트 배열의 모든 dependency 노드를 재귀적으로 수집합니다.

        컨트롤러 타겟, 스킨 본, 부모 체인을 추적하여 모든 관련 노드를 수집합니다.
        Biped 오브젝트는 결과에서 제외됩니다.

        Args:
            inObjArray: 탐색할 오브젝트 배열
            inVisited: 이미 방문한 노드 집합 (순환 참조 방지, 내부 사용)

        Returns:
            tuple: (dependency 노드 리스트, 방문한 노드 집합)
        """
        # pymxs 함수 로컬 참조를 통한 성능 최적화
        isValidNode = rt.isValidNode
        classOf = rt.classOf
        refs_dependsOn = rt.refs.dependsOn
        skinOps_GetBoneNode = rt.skinOps.GetBoneNode
        skinOps_GetNumberBones = rt.skinOps.GetNumberBones

        # 방문 집합 초기화
        if inVisited is None:
            inVisited = set()

        result = []

        for obj in inObjArray:
            # 유효하지 않은 노드 스킵
            if not isValidNode(obj):
                continue

            # 이미 방문한 노드 스킵 (순환 참조 방지)
            objName = str(obj.name)
            if objName in inVisited:
                continue

            inVisited.add(objName)

            # Biped 오브젝트 제외
            objClass = classOf(obj)
            if objClass == rt.Biped_Object:
                continue

            result.append(obj)

            # 컨트롤러 dependency 수집
            try:
                deps = refs_dependsOn(obj)
                if deps is not None:
                    validDeps = []
                    for dep in deps:
                        if isValidNode(dep):
                            depClass = classOf(dep)
                            # Biped 제외
                            if depClass != rt.Biped_Object:
                                validDeps.append(dep)

                    if validDeps:
                        subResult, inVisited = self.get_all_dependencies(
                            validDeps, inVisited
                        )
                        result.extend(subResult)
            except Exception:
                pass

            # 스킨 모디파이어의 본 수집
            try:
                for mod in obj.modifiers:
                    if classOf(mod) == rt.Skin:
                        numBones = skinOps_GetNumberBones(mod)
                        skinBones = []
                        for i in range(1, numBones + 1):
                            bone = skinOps_GetBoneNode(mod, i)
                            if isValidNode(bone):
                                boneClass = classOf(bone)
                                # Biped 제외
                                if boneClass != rt.Biped_Object:
                                    skinBones.append(bone)

                        if skinBones:
                            subResult, inVisited = self.get_all_dependencies(
                                skinBones, inVisited
                            )
                            result.extend(subResult)
            except Exception:
                pass

            # 부모 체인 수집
            try:
                parent = obj.parent
                while parent is not None and isValidNode(parent):
                    parentClass = classOf(parent)
                    # Biped 제외
                    if parentClass != rt.Biped_Object:
                        if str(parent.name) not in inVisited:
                            subResult, inVisited = self.get_all_dependencies(
                                [parent], inVisited
                            )
                            result.extend(subResult)
                    parent = parent.parent
            except Exception:
                pass

        return result, inVisited

    def get_dependents(self, inObjs):
        """
        주어진 오브젝트 배열의 모든 dependent 노드(자식, DependentNodes)를 수집합니다.

        Args:
            inObjs: 탐색할 오브젝트 배열

        Returns:
            list: dependent 노드 리스트 (원본 리스트 확장)
        """
        # pymxs 함수 로컬 참조를 통한 성능 최적화
        isValidNode = rt.isValidNode
        classOf = rt.classOf
        refs_dependentNodes = rt.refs.dependentNodes

        result = list(inObjs)  # 원본 리스트 복사
        visited = set()

        # 원본 리스트의 노드들을 방문 집합에 추가
        for obj in inObjs:
            if isValidNode(obj):
                visited.add(str(obj.name))

        # 처리할 노드 큐
        toProcess = list(inObjs)

        while toProcess:
            obj = toProcess.pop(0)

            if not isValidNode(obj):
                continue

            # Children 수집
            try:
                children = obj.children
                if children is not None:
                    for child in children:
                        if isValidNode(child):
                            childName = str(child.name)
                            if childName not in visited:
                                visited.add(childName)
                                childClass = classOf(child)
                                # Biped 제외
                                if childClass != rt.Biped_Object:
                                    result.append(child)
                                    toProcess.append(child)
            except Exception:
                pass

            # DependentNodes 수집
            try:
                depNodes = refs_dependentNodes(obj)
                if depNodes is not None:
                    for depNode in depNodes:
                        if isValidNode(depNode):
                            depNodeName = str(depNode.name)
                            if depNodeName not in visited:
                                visited.add(depNodeName)
                                depNodeClass = classOf(depNode)
                                # Biped 제외
                                if depNodeClass != rt.Biped_Object:
                                    result.append(depNode)
            except Exception:
                pass

        return result

    def get_all_related_to_export(self, inObjs):
        """
        익스포트에 필요한 모든 관련 노드를 수집합니다.

        get_dependents와 get_all_dependencies를 조합하고,
        AddOn Helper 레이어도 탐색하여 포함합니다.
        결과를 선택(rt.select)하고 반환합니다.

        Args:
            inObjs: 탐색 시작 오브젝트 배열

        Returns:
            list: 익스포트에 필요한 모든 관련 노드 리스트
        """
        if not inObjs:
            return []

        # pymxs 함수 로컬 참조
        isValidNode = rt.isValidNode
        classOf = rt.classOf

        # 1. Dependents 수집 (자식, DependentNodes)
        dependents = self.get_dependents(inObjs)

        # 2. Dependencies 수집 (컨트롤러, 스킨, 부모 체인)
        allDeps, visited = self.get_all_dependencies(dependents)

        # 3. 결과 통합 (중복 제거)
        resultSet = set()
        result = []

        for obj in allDeps:
            if isValidNode(obj):
                objName = str(obj.name)
                if objName not in resultSet:
                    resultSet.add(objName)
                    result.append(obj)

        # 4. AddOn Helper 레이어 탐색 및 포함
        if self.layerService is not None:
            try:
                # "AddOn" 패턴으로 레이어 검색
                addonLayers = self.layerService.get_layer_by_namepattern("*AddOn*")

                for layerName in addonLayers:
                    layerNodes = self.layerService.get_nodes_by_layername(layerName)
                    for node in layerNodes:
                        if isValidNode(node):
                            nodeName = str(node.name)
                            if nodeName not in resultSet:
                                nodeClass = classOf(node)
                                # Biped 제외, Helper 타입만 포함
                                if nodeClass != rt.Biped_Object:
                                    if rt.superClassOf(node) == rt.Helper:
                                        resultSet.add(nodeName)
                                        result.append(node)
            except Exception:
                pass

        # 5. 결과 선택 및 반환
        if result:
            rt.select(result)

        return result
