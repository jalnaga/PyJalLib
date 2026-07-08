#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dependent 모듈 - 3ds Max 오브젝트 의존성 탐색 기능
선택된 오브젝트와 관련된 모든 의존성 노드들을 찾아내는 기능을 제공합니다.
특히 FBX 익스포트 시 필요한 관련 노드들(컨트롤러, 스킨, 부모 체인, 자식 노드, AddOn Helper 등)을
자동으로 탐색합니다.

두 가지 탐색 전략을 제공합니다:
- 기본 메서드 (get_all_dependencies, get_dependents, get_all_related_to_export):
  Handle 기반 BFS, controller/skin 타겟팅. 익스포트에 최적화.
- Deep 메서드 (get_deep_dependencies, get_deep_dependents, get_all_related):
  Name 기반 재귀 DFS, refs.dependsOn 전체 탐색. 포괄적 의존성 수집.
"""

from pymxs import runtime as rt


class Dependent:
    """오브젝트의 dependency·dependent 노드를 탐색한다. Handle 기반 BFS 기본 메서드와 Name 기반 재귀 DFS Deep 메서드를 제공한다."""

    def __init__(self, layerService=None):
        """Dependent 클래스를 초기화한다.

        Args:
            layerService (Layer | None): Layer 서비스 인스턴스 (AddOn 레이어 탐색에 사용)
        """
        self.layerService = layerService

    # ------------------------------------------------------------------ #
    #  기본 메서드 (BFS, Handle 기반, controller/skin 타겟팅)
    # ------------------------------------------------------------------ #

    def get_all_dependencies(self, inObjArray, inVisited=None, inIncludeBiped=False):
        """주어진 오브젝트 배열의 모든 dependency 노드를 BFS로 수집한다.

        Handle 기반 O(1) 중복 체크와 BFS queue를 사용하여 최적화된 성능을 제공한다.
        controller dependencies, skin dependencies, parent chain을 수집한다.

        Args:
            inObjArray (rt.Node | list[rt.Node]): 탐색할 오브젝트 배열. 단일 오브젝트도 허용된다.
            inVisited (set[int] | None): 이미 방문한 노드의 handle set. None이면 새로 생성하며, 재사용 가능하다.
            inIncludeBiped (bool): Biped_Object 포함 여부

        Returns:
            tuple[list[rt.Node], set[int]]: (dependency 노드 리스트, 방문한 노드 handle set)
        """
        if inVisited is None:
            inVisited = set()

        nodeArray = []
        nodeHandles = set()

        # queue 초기화
        if hasattr(inObjArray, '__iter__') and not isinstance(inObjArray, str):
            queue = list(inObjArray)
        else:
            queue = [inObjArray]

        # pymxs 함수 로컬 참조를 통한 성능 최적화
        getHandleByAnim = rt.getHandleByAnim
        classOf = rt.classOf
        bipedObject = rt.Biped_Object
        isValidNode = rt.isValidNode
        isProperty = rt.isProperty
        rtName = rt.Name
        refsDependsOn = rt.refs.dependsOn

        while queue:
            obj = queue.pop()

            # visited 체크 (handle 기반)
            objHandle = getHandleByAnim(obj)
            if objHandle in inVisited:
                continue
            inVisited.add(objHandle)

            # Biped_Object 필터링
            if not inIncludeBiped and classOf(obj) == bipedObject:
                continue

            # controller dependencies
            if hasattr(obj, 'controller') and obj.controller is not None:
                deps = refsDependsOn(obj.controller)
                for dep in deps:
                    if isValidNode(dep):
                        depHandle = getHandleByAnim(dep)
                        if depHandle not in nodeHandles:
                            nodeHandles.add(depHandle)
                            nodeArray.append(dep)
                    else:
                        queue.append(dep)

            # skin dependencies
            if isProperty(obj, rtName('skin')) and obj.skin is not None:
                deps = refsDependsOn(obj.skin)
                for dep in deps:
                    if isValidNode(dep):
                        depHandle = getHandleByAnim(dep)
                        if depHandle not in nodeHandles:
                            nodeHandles.add(depHandle)
                            nodeArray.append(dep)
                    else:
                        queue.append(dep)

            # parent chain
            if isValidNode(obj):
                objHandleNode = getHandleByAnim(obj)
                if objHandleNode not in nodeHandles:
                    nodeHandles.add(objHandleNode)
                    nodeArray.append(obj)
                if obj.parent is not None:
                    queue.append(obj.parent)

        return nodeArray, inVisited

    def get_dependents(self, inObjs):
        """주어진 오브젝트 배열의 모든 dependent 노드(자식, DependentNodes)를 수집한다.

        Handle 기반 O(1) 중복 체크를 사용한다.

        Args:
            inObjs (list[rt.Node]): 탐색할 오브젝트 배열

        Returns:
            list[rt.Node]: dependent 노드 리스트 (children + DependentNodes)
        """
        objs = list(inObjs)
        objsHandles = {rt.getHandleByAnim(o) for o in objs}

        dependentsNodes = []
        dependentsHandles = set()

        # pymxs 함수 로컬 참조를 통한 성능 최적화
        getHandleByAnim = rt.getHandleByAnim
        dependentNodes = rt.refs.DependentNodes

        # children 수집 (원본 리스트에 추가하며 재귀 탐색)
        initialCount = len(objs)
        i = 0
        while i < len(objs):
            obj = objs[i]
            for c in obj.children:
                cHandle = getHandleByAnim(c)
                if cHandle not in objsHandles:
                    objsHandles.add(cHandle)
                    objs.append(c)
            i += 1

        # 재귀적으로 수집된 children을 결과에 포함
        for obj in objs[initialCount:]:
            objHandle = getHandleByAnim(obj)
            if objHandle not in dependentsHandles:
                dependentsHandles.add(objHandle)
                dependentsNodes.append(obj)

        # DependentNodes 수집
        for obj in objs:
            for d in dependentNodes(obj):
                dHandle = getHandleByAnim(d)
                if dHandle not in dependentsHandles:
                    dependentsHandles.add(dHandle)
                    dependentsNodes.append(d)

        return dependentsNodes

    def collect_addon_helpers(self, inDeps):
        """Rig_AddOn_* 레이어에서 Helper 클래스 노드를 수집한다.

        Args:
            inDeps (list[rt.Node]): dependency 노드 리스트

        Returns:
            set[rt.Node]: 수집된 AddOn Helper 노드 set
        """
        addonHelper = set()
        processedLayers = set()
        helperClass = rt.helper
        superClassOf = rt.superClassOf

        for item in inDeps:
            layerName = item.layer.name
            if layerName.startswith('Rig_AddOn_') and layerName not in processedLayers:
                processedLayers.add(layerName)
                layerNodes = self.layerService.get_nodes_by_layername(layerName)
                for obj in layerNodes:
                    if superClassOf(obj) == helperClass:
                        addonHelper.add(obj)

        return addonHelper

    def get_all_related_to_export(self, inObjs, inIncludeBiped=False):
        """익스포트에 필요한 모든 관련 노드를 수집하고 선택한다.

        get_dependents -> get_all_dependencies (1차, 원본 기준) ->
        get_all_dependencies (2차, 1차 결과 기준, visited 재사용) ->
        collect_addon_helpers 순서로 dependency를 수집한다.
        결과를 선택(rt.select)하고 반환한다.

        Args:
            inObjs (list[rt.Node]): 탐색 시작 오브젝트 배열
            inIncludeBiped (bool): Biped_Object 포함 여부

        Returns:
            list[rt.Node]: 익스포트에 필요한 모든 관련 노드 리스트. 입력이 비면 빈 리스트
        """
        if not inObjs:
            return []

        objs = list(inObjs)

        # 1. Dependents 수집 (통계/참조용, 최종 결합에 미포함)
        self.get_dependents(objs)

        # 2. 1차 dependency 탐색 (원본 오브젝트 기준)
        visited = set()
        dependsOn, visited = self.get_all_dependencies(
            objs, visited, inIncludeBiped=inIncludeBiped
        )

        # 3. 2차 dependency 탐색 (1차 결과 기준, visited 재사용)
        allDeps, visited = self.get_all_dependencies(
            dependsOn, visited, inIncludeBiped=inIncludeBiped
        )

        # 4. AddOn Helpers 수집
        addonHelpers = set()
        if self.layerService is not None:
            try:
                addonHelpers = self.collect_addon_helpers(allDeps)
            except Exception:
                pass

        # 5. 최종 결합 (선택 오브젝트 + 1차 + 2차 + AddOn Helpers)
        combined = list(
            addonHelpers | set(allDeps) | set(dependsOn) | set(objs)
        )

        # 6. 결과 선택 및 반환
        if combined:
            rt.select(combined)

        return combined

    # ------------------------------------------------------------------ #
    #  Deep 메서드 (재귀 DFS, Name 기반, refs.dependsOn 전체 탐색)
    # ------------------------------------------------------------------ #

    def get_deep_dependencies(self, inObjArray, inVisited=None, inIncludeBiped=False):
        """주어진 오브젝트 배열의 모든 dependency 노드를 재귀적으로 수집한다.

        refs.dependsOn(obj) 전체 오브젝트 탐색과 skinOps 본 순회를 사용하여
        포괄적인 의존성을 수집한다. Biped 부모를 건너뛰고 상위 체인도 탐색한다.

        Args:
            inObjArray (list[rt.Node]): 탐색할 오브젝트 배열
            inVisited (set[str] | None): 이미 방문한 노드 이름 집합 (순환 참조 방지, 내부 사용). None이면 새로 생성한다.
            inIncludeBiped (bool): Biped_Object 포함 여부

        Returns:
            tuple[list[rt.Node], set[str]]: (dependency 노드 리스트, 방문한 노드 이름 집합)
        """
        # pymxs 함수 로컬 참조를 통한 성능 최적화
        isValidNode = rt.isValidNode
        classOf = rt.classOf
        bipedObject = rt.Biped_Object
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

            # Biped 오브젝트 필터링
            objClass = classOf(obj)
            if not inIncludeBiped and objClass == bipedObject:
                continue

            result.append(obj)

            # 컨트롤러 dependency 수집 (전체 오브젝트 대상)
            try:
                deps = refs_dependsOn(obj)
                if deps is not None:
                    validDeps = []
                    for dep in deps:
                        if isValidNode(dep):
                            depClass = classOf(dep)
                            if inIncludeBiped or depClass != bipedObject:
                                validDeps.append(dep)

                    if validDeps:
                        subResult, inVisited = self.get_deep_dependencies(
                            validDeps, inVisited,
                            inIncludeBiped=inIncludeBiped
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
                                if inIncludeBiped or boneClass != bipedObject:
                                    skinBones.append(bone)

                        if skinBones:
                            subResult, inVisited = self.get_deep_dependencies(
                                skinBones, inVisited,
                                inIncludeBiped=inIncludeBiped
                            )
                            result.extend(subResult)
            except Exception:
                pass

            # 부모 체인 수집 (Biped 건너뛰고 상위도 탐색)
            try:
                parent = obj.parent
                while parent is not None and isValidNode(parent):
                    parentClass = classOf(parent)
                    if inIncludeBiped or parentClass != bipedObject:
                        if str(parent.name) not in inVisited:
                            subResult, inVisited = self.get_deep_dependencies(
                                [parent], inVisited,
                                inIncludeBiped=inIncludeBiped
                            )
                            result.extend(subResult)
                    parent = parent.parent
            except Exception:
                pass

        return result, inVisited

    def get_deep_dependents(self, inObjs, inIncludeBiped=False):
        """주어진 오브젝트 배열의 모든 dependent 노드(자식, DependentNodes)를 수집한다.

        원본 오브젝트를 결과에 포함하며, children과 DependentNodes를
        개별 필터링하여 수집한다.

        Args:
            inObjs (list[rt.Node]): 탐색할 오브젝트 배열
            inIncludeBiped (bool): Biped_Object 포함 여부

        Returns:
            list[rt.Node]: dependent 노드 리스트 (원본 + children + DependentNodes)
        """
        # pymxs 함수 로컬 참조를 통한 성능 최적화
        isValidNode = rt.isValidNode
        classOf = rt.classOf
        bipedObject = rt.Biped_Object
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
                                if inIncludeBiped or childClass != bipedObject:
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
                                if inIncludeBiped or depNodeClass != bipedObject:
                                    result.append(depNode)
            except Exception:
                pass

        return result

    def get_all_related(self, inObjs, inIncludeBiped=False):
        """모든 관련 노드를 포괄적으로 수집하고 선택한다.

        get_deep_dependents로 자식/DependentNodes를 수집한 뒤,
        get_deep_dependencies로 전체 의존성을 탐색한다.
        *AddOn* 레이어의 Helper 노드도 탐색하여 포함하고,
        결과를 선택(rt.select)한 뒤 반환한다.

        Args:
            inObjs (list[rt.Node]): 탐색 시작 오브젝트 배열
            inIncludeBiped (bool): Biped_Object 포함 여부

        Returns:
            list[rt.Node]: 모든 관련 노드 리스트. 입력이 비면 빈 리스트
        """
        if not inObjs:
            return []

        # pymxs 함수 로컬 참조
        isValidNode = rt.isValidNode
        classOf = rt.classOf
        bipedObject = rt.Biped_Object

        # 1. Dependents 수집 (자식, DependentNodes)
        dependents = self.get_deep_dependents(
            inObjs, inIncludeBiped=inIncludeBiped
        )

        # 2. Dependencies 수집 (컨트롤러, 스킨, 부모 체인)
        allDeps, visited = self.get_deep_dependencies(
            dependents, inIncludeBiped=inIncludeBiped
        )

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
                addonLayers = self.layerService.get_layer_by_namepattern(
                    "*AddOn*"
                )

                for layerName in addonLayers:
                    layerNodes = self.layerService.get_nodes_by_layername(
                        layerName
                    )
                    for node in layerNodes:
                        if isValidNode(node):
                            nodeName = str(node.name)
                            if nodeName not in resultSet:
                                nodeClass = classOf(node)
                                includable = (
                                    inIncludeBiped
                                    or nodeClass != bipedObject
                                )
                                if includable:
                                    if rt.superClassOf(node) == rt.Helper:
                                        resultSet.add(nodeName)
                                        result.append(node)
            except Exception:
                pass

        # 5. 결과 선택 및 반환
        if result:
            rt.select(result)

        return result
