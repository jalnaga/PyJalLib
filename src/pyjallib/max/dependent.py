#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dependent 모듈 - 3ds Max 오브젝트 의존성 탐색 기능
선택된 오브젝트와 관련된 모든 의존성 노드들을 찾아내는 기능을 제공합니다.
특히 FBX 익스포트 시 필요한 관련 노드들(컨트롤러, 스킨, 부모 체인 등)을
자동으로 탐색합니다.

탐색 전략은 Handle 기반 BFS 하나다(get_all_dependencies, get_dependents,
get_all_related_to_export). controller/skin을 타겟팅해 익스포트에 최적화되어 있다.

의존성 탐색 결과를 넓히는 **수집 확장 규칙**은 이 모듈이 알지 못한다. 규칙은
``nodeCollectPolicy``(순수 엔진)와 ``nodeCollectResolver``(pymxs 어댑터)가 담당하고,
무엇을 수집할지는 호출부가 :class:`NodeCollectPolicy`로 기술해 주입한다. pyjallib은
범용 오픈소스 라이브러리이므로 특정 프로젝트의 레이어 규약을 전제해서는 안 된다.
"""

from pymxs import runtime as rt

from pyjallib.max.nodeCollectResolver import NodeCollectResolver


class Dependent:
    """오브젝트의 dependency·dependent 노드를 Handle 기반 BFS로 탐색한다."""

    def __init__(self, layerService=None, inCollectPolicy=None):
        """Dependent 클래스를 초기화한다.

        Args:
            layerService (Layer | None): Layer 서비스 인스턴스 (수집 확장 규칙의
                레이어 조회에 사용)
            inCollectPolicy (NodeCollectPolicy | None): 노드 수집 확장 정서.
                None이면 규칙이 하나도 발동하지 않고 순수 의존성 탐색 결과가 나온다.
                라이브러리 기본값 자리에 특정 프로젝트의 레이어 이름을 두지 않기
                위한 선택이다
        """
        self.layerService = layerService
        self.collectPolicy = inCollectPolicy
        self._collectResolver = None

    @property
    def collectResolver(self):
        """수집 확장 어댑터를 지연 생성해 반환한다.

        생성 시점에 layerService가 없을 수 있고(기본 생성), 정서가 주입되지 않으면
        어댑터가 아예 필요하지 않으므로 지연 생성한다.

        Returns:
            NodeCollectResolver | None: layerService가 없으면 None
        """
        if self.layerService is None:
            return None
        if self._collectResolver is None:
            self._collectResolver = NodeCollectResolver(layerService=self.layerService)
        return self._collectResolver

    # ------------------------------------------------------------------ #
    #  탐색 (BFS, Handle 기반, controller/skin 타겟팅)
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
        """주입된 정서의 수집 확장 규칙으로 추가할 노드를 수집한다.

        이름은 하위 호환을 위해 유지한다. pyjallib은 워크스페이스 밖 호출부를
        확인할 수 없는 오픈소스 라이브러리이므로 공개 메서드 이름을 지우지 않는다.
        다만 동작은 정서 기반으로 바뀌어, **어떤 레이어에서 무엇을 수집할지는
        호출부가 정한다.** 이전 구현이 들고 있던 특정 프로젝트의 레이어 접두는
        라이브러리에서 제거되었다.

        정서가 주입되지 않았으면 빈 set을 반환한다. 규칙이 하나도 없으므로 확장이
        일어나지 않는 것이 맞고, 이것은 조용한 결함이 아니라 명시적 "규칙 없음"이다.

        Args:
            inDeps (list[rt.Node]): dependency 노드 리스트

        Returns:
            set[rt.Node]: 규칙으로 추가된 노드 set. 정서 미주입 시 빈 set
        """
        resolver = self.collectResolver
        if resolver is None or self.collectPolicy is None:
            return set()

        resolved = resolver.resolve(self.collectPolicy)
        if resolved is None:
            return set()

        addedNodes, _ = resolver.collect_additions(inDeps, resolved)
        return set(addedNodes)

    def get_all_related_to_export(self, inObjs, inIncludeBiped=False):
        """익스포트에 필요한 모든 관련 노드를 수집하고 선택한다.

        get_dependents -> get_all_dependencies (1차, 원본 기준) ->
        get_all_dependencies (2차, 1차 결과 기준, visited 재사용) ->
        수집 확장 규칙 적용 순서로 dependency를 수집한다.
        결과를 선택(rt.select)하고 반환한다.

        확장 단계에서 예외가 나면 확장 없이 기존 수집 결과를 그대로 반환한다.
        확장 실패로 익스포트가 무너지는 것보다 확장 없이 나가는 편이 낫다.

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

        # 4. 수집 확장 규칙 적용 (정서 미주입이면 빈 set)
        collectedByRule = set()
        try:
            collectedByRule = self.collect_addon_helpers(allDeps)
        except Exception:
            pass

        # 5. 최종 결합 (선택 오브젝트 + 1차 + 2차 + 규칙 확장분)
        combined = list(
            collectedByRule | set(allDeps) | set(dependsOn) | set(objs)
        )

        # 6. 결과 선택 및 반환
        if combined:
            rt.select(combined)

        return combined
