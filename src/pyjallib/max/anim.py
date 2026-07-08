#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
애니메이션 모듈 - 3ds Max용 애니메이션 관련 기능 제공
원본 MAXScript의 anim.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import undo
from pymxs import runtime as rt


class Anim:
    """3ds Max 애니메이션의 키프레임 수집·삭제, 트랜스폼 고정·병합·매칭, 저장·로드 기능을 제공하는 클래스."""
    
    def __init__(self):
        """클래스를 초기화한다 (특별한 초기화 동작 없음)."""
        pass
    
    def rotate_local(self, inObj, rx, ry, rz, dontAffectChildren=False):
        """객체를 로컬 좌표계 기준으로 회전시킨다.

        Args:
            inObj (rt.Node): 회전할 객체
            rx (float): X축 회전 각도 (도 단위)
            ry (float): Y축 회전 각도 (도 단위)
            rz (float): Z축 회전 각도 (도 단위)
            dontAffectChildren (bool): True이면 회전 동안 자식들의 부모 연결을 임시로 해제해 자식에 영향을 주지 않는다.
        """
        tempParent = None
        tempChildren = []
        if dontAffectChildren:
            # 자식 객체에 영향을 주지 않도록 설정
            tempParent = inObj.parent
            for item in inObj.children:
                tempChildren.append(item)
            for item in tempChildren:
                item.parent = None
                
        # 현재 객체의 변환 행렬을 가져옴
        currentMatrix = rt.getProperty(inObj, "transform")
        # 오일러 각도를 통해 회전 행렬(쿼터니언) 생성
        eulerAngles = rt.eulerAngles(rx, ry, rz)
        quatRotation = rt.eulertoquat(eulerAngles)
        # preRotate를 이용해 회전 적용
        rt.preRotate(currentMatrix, quatRotation)
        # 변경된 행렬을 객체에 설정
        rt.setProperty(inObj, "transform", currentMatrix)
        
        if dontAffectChildren:
            # 자식 객체의 부모를 원래대로 복원
            for item in tempChildren:
                item.parent = inObj
            inObj.parent = tempParent
    
    def move_local(self, inObj, mx, my, mz, dontAffectChildren=False):
        """객체를 로컬 좌표계 기준으로 이동시킨다.

        Args:
            inObj (rt.Node): 이동할 객체
            mx (float): X축 이동 거리
            my (float): Y축 이동 거리
            mz (float): Z축 이동 거리
            dontAffectChildren (bool): True이면 이동 동안 자식들의 부모 연결을 임시로 해제해 자식에 영향을 주지 않는다.
        """
        tempParent = None
        tempChildren = []
        if dontAffectChildren:
            # 자식 객체에 영향을 주지 않도록 설정
            tempParent = inObj.parent
            for item in inObj.children:
                tempChildren.append(item)
            for item in tempChildren:
                item.parent = None
        
        # 현재 변환 행렬 가져오기
        currentMatrix = rt.getProperty(inObj, "transform", dontAffectChildren=False)
        # 이동량을 Point3 형태로 생성
        translation = rt.Point3(mx, my, mz)
        # preTranslate를 이용해 행렬에 이동 적용
        rt.preTranslate(currentMatrix, translation)
        # 적용된 이동 변환 행렬을 객체에 설정
        rt.setProperty(inObj, "transform", currentMatrix)
        
        if dontAffectChildren:
            # 자식 객체의 부모를 원래대로 복원
            for item in tempChildren:
                item.parent = inObj
            inObj.parent = tempParent
    
    def reset_transform_controller(self, inObj):
        """객체의 위치·회전·스케일 컨트롤러를 기본 컨트롤러로 재설정한다.

        Biped_Object는 처리하지 않으며, 재설정 후 기존 트랜스폼을 복원한다.

        Args:
            inObj (rt.Node): 컨트롤러를 재설정할 객체
        """
        # Biped_Object가 아닐 경우에만 실행
        if rt.classOf(inObj) != rt.Biped_Object:
            # 현재 변환 행렬 백업
            tempTransform = rt.getProperty(inObj, "transform")
            # 위치, 회전, 스케일 컨트롤러를 기본 컨트롤러로 재설정
            rt.setPropertyController(inObj.controller, "Position", rt.Position_XYZ())
            rt.setPropertyController(inObj.controller, "Rotation", rt.Euler_XYZ())
            rt.setPropertyController(inObj.controller, "Scale", rt.Bezier_Scale())
            # 백업한 행렬을 다시 객체에 할당
            inObj.transform = tempTransform
    
    def freeze_transform(self, inObj):
        """객체의 회전·위치 컨트롤러를 리스트 컨트롤러로 감싸 현재 변환을 고정(freeze)한다.

        Frozen/Zero 레이어를 가진 Rotation_list·Position_list를 구성하고 Zero 컨트롤러를 활성화한다.

        Args:
            inObj (rt.Node): 변환을 고정할 객체
        """
        curObj = inObj
        
        # 회전 컨트롤러 고정 (Rotation_list 사용)
        if rt.classOf(rt.getPropertyController(curObj.controller, "Rotation")) != rt.Rotation_list():
            rotList = rt.Rotation_list()
            rt.setPropertyController(curObj.controller, "Rotation", rotList)
            rt.setPropertyController(rotList, "Available", rt.Euler_xyz())
            
            # 컨트롤러 이름 설정
            rotList.setname(1, "Frozen Rotation")
            rotList.setname(2, "Zero Euler XYZ")
            
            # 활성 컨트롤러 설정
            rotList.setActive(2)
        
        # 포지션 컨트롤러 고정 (Position_list 사용)
        if rt.classOf(rt.getPropertyController(curObj.controller, "position")) != rt.Position_list():
            posList = rt.Position_list()
            rt.setPropertyController(curObj.controller, "position", posList)
            rt.setPropertyController(posList, "Available", rt.Position_XYZ())
            
            # 컨트롤러 이름 설정
            posList.setname(1, "Frozen Position")
            posList.setname(2, "Zero Position XYZ")
            
            # 활성 컨트롤러 설정
            posList.setActive(2)
            
            # 위치를 0으로 초기화
            zeroPosController = rt.getPropertyController(posList, "Zero Position XYZ")
            xPosController = rt.getPropertyController(zeroPosController, "X Position")
            yPosController = rt.getPropertyController(zeroPosController, "Y Position")
            zPosController = rt.getPropertyController(zeroPosController, "Z Position")
            
            rt.setProperty(xPosController, "value", 0.0)
            rt.setProperty(yPosController, "value", 0.0)
            rt.setProperty(zPosController, "value", 0.0)

    def collape_anim_transform(self, inObj, startFrame=None, endFrame=None):
        """객체의 애니메이션 변환을 프레임별로 베이크하여 단일 PRS 컨트롤러로 병합한다.

        MAXScript를 실행해 임시 포인트에 변환을 기록한 뒤 객체의 컨트롤러를 PRS로 교체하고 프레임마다 키를 다시 생성한다.

        Args:
            inObj (rt.Node): 변환을 병합할 객체
            startFrame (int | None): 시작 프레임. None이면 애니메이션 범위의 시작을 사용한다.
            endFrame (int | None): 끝 프레임. None이면 애니메이션 범위의 끝을 사용한다.
        """
        # 시작과 끝 프레임이 지정되지 않은 경우 기본값 할당
        if startFrame is None:
            startFrame = int(rt.animationRange.start)
        if endFrame is None:
            endFrame = int(rt.animationRange.end)
        
        maxScriptCode = ""
        maxScriptCode += "disableSceneRedraw()\n"
        maxScriptCode += f"progressStart (\"Collapse transform {inObj.name}...\")\n"
        maxScriptCode += f"inObj = $'{inObj.name}'\n"
        maxScriptCode += "p = point()\n"
        maxScriptCode += f"for k = {startFrame} to {endFrame} do (\n"
        maxScriptCode += "    at time k (\n"
        maxScriptCode += "        with animate on p.transform = inObj.transform\n"
        maxScriptCode += "    )\n"
        maxScriptCode += ")\n"
        maxScriptCode += "\n"
        maxScriptCode += "inObj.transform.controller = transform_script()\n"
        maxScriptCode += "inObj.transform.controller = prs()\n"
        maxScriptCode += "\n"
        maxScriptCode += f"for k = {startFrame} to {endFrame} do (\n"
        maxScriptCode += "    at time k (\n"
        maxScriptCode += "        with animate on (\n"
        maxScriptCode += "            in coordsys (transmatrix inObj.transform.pos) inObj.rotation = inverse p.transform.rotation\n"
        maxScriptCode += "            in coordsys world inObj.position = p.transform.position\n"
        maxScriptCode += "            inObj.scale = p.scale\n"
        maxScriptCode += "        )\n"
        maxScriptCode += "    )\n"
        maxScriptCode += f"    progressUpdate (100 * k / {endFrame})\n"
        maxScriptCode += ")\n"
        maxScriptCode += "\n"
        maxScriptCode += f"if {startFrame} != animationRange.start then (\n"
        maxScriptCode += "    deselectKeys inObj.transform.controller\n"
        maxScriptCode += "    selectKeys inObj.transform.controller animationRange.start\n"
        maxScriptCode += "    deleteKeys inObj.transform.controller #selection\n"
        maxScriptCode += "    deselectKeys inObj.transform.controller\n"
        maxScriptCode += ")\n"
        maxScriptCode += "\n"
        maxScriptCode += "delete p\n"
        maxScriptCode += "progressEnd()\n"
        maxScriptCode += "enableSceneRedraw()\n"
        
        rt.execute(maxScriptCode)
    
    def match_anim_transform(self, inObj, inTarget, startFrame=None, endFrame=None):
        """객체의 애니메이션 변환을 대상 객체의 변환과 일치시킨다.

        구간 내 기존 키를 제거한 뒤 대상 객체의 위치·회전·스케일 키 시점마다 변환을 복사해 키를 생성한다.

        Args:
            inObj (rt.Node): 변환을 적용할 객체
            inTarget (rt.Node): 기준이 되는 대상 객체
            startFrame (int | None): 시작 프레임. None이면 애니메이션 범위의 시작을 사용한다.
            endFrame (int | None): 끝 프레임. None이면 애니메이션 범위의 끝을 사용한다.
        """
        # 시작/끝 프레임 기본값 설정
        if startFrame is None:
            startFrame = int(rt.animationRange.start)
        if endFrame is None:
            endFrame = int(rt.animationRange.end)
            
        maxscriptCode = ""
        maxscriptCode += f"inObj = $'{inObj.name}'\n"
        maxscriptCode += f"inTarget = $'{inTarget.name}'\n"
        maxscriptCode += "if (isValidNode inObj) and (isValidNode inTarget) then (\n"
        maxscriptCode += "    disableSceneRedraw()\n"
        maxscriptCode += f"    progressStart (\"Match transform {inObj.name} to {inTarget.name} \")\n"
        maxscriptCode += "\n"
        maxscriptCode += "    p = point()\n"
        maxscriptCode += f"    for k = {startFrame} to {endFrame} do (\n"
        maxscriptCode += "        at time k (\n"
        maxscriptCode += "            with animate on p.transform = inTarget.transform\n"
        maxscriptCode += "        )\n"
        maxscriptCode += "\n"
        maxscriptCode += "        deselectKeys inObj.transform.controller\n"
        maxscriptCode += "        selectKeys inObj.transform.controller k\n"
        maxscriptCode += "        deleteKeys inObj.transform.controller #selection\n"
        maxscriptCode += "        deselectKeys inObj.transform.controller\n"
        maxscriptCode += "    )\n"
        maxscriptCode += "\n"
        maxscriptCode += "    progressUpdate 20\n"
        maxscriptCode += "\n"
        maxscriptCode += f"    if {startFrame} != animationRange.start then (\n"
        maxscriptCode += "        deselectKeys p.transform.controller\n"
        maxscriptCode += "        selectKeys p.transform.controller animationRange.start\n"
        maxscriptCode += "        deleteKeys p.transform.controller #selection\n"
        maxscriptCode += "        deselectKeys p.transform.controller\n"
        maxscriptCode += "    )\n"
        maxscriptCode += "\n"
        maxscriptCode += "    progressUpdate 25\n"
        maxscriptCode += "\n"
        maxscriptCode += "    local posKeyArray = inTarget.pos.controller.keys\n"
        maxscriptCode += "    local rotKeyArray = inTarget.rotation.controller.keys\n"
        maxscriptCode += "    local scaleKeyArray = inTarget.scale.controller.keys\n"
        maxscriptCode += "\n"
        maxscriptCode += f"    at time {startFrame} (\n"
        maxscriptCode += "        with animate on inObj.transform = p.transform\n"
        maxscriptCode += "    )\n"
        maxscriptCode += f"    at time {endFrame} (\n"
        maxscriptCode += "        with animate on inObj.transform = p.transform\n"
        maxscriptCode += "    )\n"
        maxscriptCode += "\n"
        maxscriptCode += "    for key in posKeyArray do (\n"
        maxscriptCode += f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        maxscriptCode += "            at time key.time (\n"
        maxscriptCode += "                with animate on inObj.transform = p.transform\n"
        maxscriptCode += "            )\n"
        maxscriptCode += "        )\n"
        maxscriptCode += "    )\n"
        maxscriptCode += "    progressUpdate 40\n"
        maxscriptCode += "    for key in rotKeyArray do (\n"
        maxscriptCode += f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        maxscriptCode += "            at time key.time (\n"
        maxscriptCode += "                with animate on inObj.transform = p.transform\n"
        maxscriptCode += "            )\n"
        maxscriptCode += "        )\n"
        maxscriptCode += "    )\n"
        maxscriptCode += "    progressUpdate 60\n"
        maxscriptCode += "    for key in scaleKeyArray do (\n"
        maxscriptCode += f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        maxscriptCode += "            at time key.time (\n"
        maxscriptCode += "                with animate on inObj.transform = p.transform\n"
        maxscriptCode += "            )\n"
        maxscriptCode += "        )\n"
        maxscriptCode += "    )\n"
        maxscriptCode += "    progressUpdate 80\n"
        maxscriptCode += "\n"
        maxscriptCode += "    delete p\n"
        maxscriptCode += "\n"
        maxscriptCode += "    progressUpdate 100\n"
        maxscriptCode += "    progressEnd()\n"
        maxscriptCode += "    enableSceneRedraw()\n"
        maxscriptCode += ")\n"
        
        rt.execute(maxscriptCode)
    
    def create_average_pos_transform(self, inTargetArray):
        """여러 객체의 평균 위치를 계산한 변환 행렬을 생성한다.

        임시 포인트에 Position_Constraint를 걸어 평균 위치를 구한 뒤 행렬만 복사하고 임시 객체는 삭제한다.

        Args:
            inTargetArray (list[rt.Node]): 평균 위치 계산 대상 객체 배열

        Returns:
            rt.Matrix3: 평균 위치가 적용된 변환 행렬
        """
        # 임시 포인트 객체 생성
        posConstDum = rt.Point()
        
        # 포지션 제약 컨트롤러 생성
        targetPosConstraint = rt.Position_Constraint()
        
        # 대상 객체에 동일 가중치 부여 (전체 100%)
        targetWeight = 100.0 / (len(inTargetArray) + 1)
        
        # 제약 컨트롤러를 임시 객체에 할당
        rt.setPropertyController(posConstDum.controller, "Position", targetPosConstraint)
        
        # 각 대상 객체를 제약에 추가
        for item in inTargetArray:
            targetPosConstraint.appendTarget(item, targetWeight)
        
        # 계산된 변환 값을 복사
        returnTransform = rt.copy(rt.getProperty(posConstDum, "transform"))
        
        # 임시 객체 삭제
        rt.delete(posConstDum)
        
        return returnTransform
    
    def create_average_rot_transform(self, inTargetArray):
        """여러 객체의 평균 회전을 계산한 변환 행렬을 생성한다.

        임시 포인트에 Orientation_Constraint를 걸어 평균 회전을 구한 뒤 행렬만 복사하고 임시 객체는 삭제한다.

        Args:
            inTargetArray (list[rt.Node]): 평균 회전 계산 대상 객체 배열

        Returns:
            rt.Matrix3: 평균 회전이 적용된 변환 행렬
        """
        # 임시 포인트 객체 생성
        rotConstDum = rt.Point()
        
        # 방향(회전) 제약 컨트롤러 생성
        targetOriConstraint = rt.Orientation_Constraint()
        
        # 대상 객체에 동일 가중치 부여
        targetWeight = 100.0 / (len(inTargetArray) + 1)
        
        # 회전 제약 컨트롤러를 임시 객체에 할당
        rt.setPropertyController(rotConstDum.controller, "Rotation", targetOriConstraint)
        
        # 각 대상 객체를 제약에 추가
        for item in inTargetArray:
            targetOriConstraint.appendTarget(item, targetWeight)
        
        # 계산된 변환 값을 복사
        returnTransform = rt.copy(rt.getProperty(rotConstDum, "transform"))
        
        # 임시 객체 삭제
        rt.delete(rotConstDum)
        
        return returnTransform
        
    def get_all_keys_in_controller(self, inController, keys_list):
        """컨트롤러와 그 하위 컨트롤러의 모든 키프레임을 재귀적으로 수집한다.

        Args:
            inController (rt.Controller): 키프레임을 검색할 컨트롤러
            keys_list (list[rt.MAXKey]): 수집된 키가 추가될 리스트 (참조로 전달)
        """
        with undo(False):
            # 현재 컨트롤러에 키프레임이 있으면 리스트에 추가
            if rt.isProperty(inController, 'keys'):
                if inController.keys:
                    for k in inController.keys:
                        keys_list.append(k)

            # 하위 컨트롤러에 대해서 재귀적으로 검색
            for i in range(inController.numSubs):
                try:
                    sub_controller = inController[i]
                except:
                    sub_controller = None
                if sub_controller:
                    self.get_all_keys_in_controller(sub_controller, keys_list)
                    
    def get_all_keys(self, inObj):
        """객체에 적용된 모든 키프레임을 수집한다.

        Biped COM(루트)은 vertical·horizontal·turning 컨트롤러의 키를, 일반 Biped 객체는
        자신의 컨트롤러 키를, 그 외 객체는 하위 컨트롤러까지 재귀적으로 수집한다.

        Args:
            inObj (rt.Node): 키프레임을 검색할 객체

        Returns:
            list[rt.MAXKey]: 수집된 키프레임 목록. 유효한 노드가 아니면 빈 리스트
        """
        with undo(False):
            keys_list = []
            if rt.isValidNode(inObj):
                if rt.classOf(inObj) == rt.Biped_Object:
                    if inObj.controller.rootNode == inObj:
                        bipComVertKeys = inObj.controller.vertical.controller.keys
                        bipComHorKeys = inObj.controller.horizontal.controller.keys
                        bipComTurningKeys = inObj.controller.turning.controller.keys
                        for key in bipComVertKeys:
                            if key not in keys_list:
                                keys_list.append(key)
                        for key in bipComHorKeys:
                            if key not in keys_list:
                                keys_list.append(key)
                        for key in bipComTurningKeys:
                            if key not in keys_list:
                                keys_list.append(key)
                    else:
                        keys_list = inObj.controller.keys
                else:
                    self.get_all_keys_in_controller(inObj.controller, keys_list)
            
            return keys_list
    
    def get_start_end_keys(self, inObj):
        """객체의 키프레임 중 시간상 가장 빠른 키와 가장 늦은 키를 찾는다.

        Args:
            inObj (rt.Node): 키프레임을 검색할 객체

        Returns:
            list[rt.MAXKey]: [시작 키, 끝 키] 형태의 리스트. 키가 없으면 빈 리스트
        """
        with undo(False):
            keys = self.get_all_keys(inObj)
            if keys and len(keys) > 0:
                # 각 키의 시간값을 추출하여 최소, 최대값 확인
                times = [key.time for key in keys]
                minTime = rt.amin(times)
                maxTime = rt.amax(times)
                minIndex = times.index(minTime)
                maxIndex = times.index(maxTime)
                return [keys[minIndex], keys[maxIndex]]
            else:
                return []
    
    def delete_all_keys(self, inObj):
        """객체에 적용된 모든 키프레임을 삭제한다.

        Args:
            inObj (rt.Node): 키를 삭제할 객체
        """
        rt.deleteKeys(inObj, rt.Name('allKeys'))
    
    def delete_keys_in_range(self, node, startFrame, endFrame):
        """지정한 프레임 범위에서 노드의 위치·회전·스케일 키를 삭제한다.

        Args:
            node (rt.Node): 키를 삭제할 노드
            startFrame (int): 시작 프레임
            endFrame (int): 끝 프레임

        Returns:
            bool: 삭제 성공 여부. 유효하지 않은 노드거나 실행 중 예외가 발생하면 False
        """
        if not rt.isValidNode(node):
            return False
        
        try:
            maxscriptCode = f"""
            (
                selectKeys $'{node.name}'.position.controller (interval {startFrame} {endFrame})
                deleteKeys $'{node.name}'.position.controller #selection
                
                selectKeys $'{node.name}'.rotation.controller (interval {startFrame} {endFrame})
                deleteKeys $'{node.name}'.rotation.controller #selection
                
                selectKeys $'{node.name}'.scale.controller (interval {startFrame} {endFrame})
                deleteKeys $'{node.name}'.scale.controller #selection
            )
            """
            rt.execute(maxscriptCode)
            return True
        except Exception as e:
            print(f"Error deleting keys in range: {e}")
            return False
    
    def is_node_animated(self, node):
        """노드와 그 하위 요소(서브 애니메이션, 커스텀 속성)의 애니메이션 여부를 재귀적으로 확인한다.

        Args:
            node (rt.Node | rt.SubAnim): 애니메이션 여부를 확인할 노드 또는 서브 애니메이션

        Returns:
            bool: 애니메이션 키가 하나라도 있으면 True
        """
        animated = False
        obj = node

        # SubAnim인 경우 키프레임 여부 확인
        if rt.isKindOf(node, rt.SubAnim):
            if node.keys and len(node.keys) > 0:
                animated = True
            obj = node.object
        
        # MaxWrapper인 경우 커스텀 속성에 대해 확인
        if rt.isKindOf(obj, rt.MaxWrapper):
            for ca in obj.custAttributes:
                animated = self.is_node_animated(ca)
                if animated:
                    break
        
        try:
        # 하위 애니메이션에 대해 재귀적으로 검사
            for i in range(node.numSubs):
                animated = self.is_node_animated(node[i])
                if animated:
                    break
        except:
            animated = False
        
        return animated
    
    def find_animated_nodes(self, nodes=None):
        """애니메이션이 적용된 노드를 모두 찾는다.

        Args:
            nodes (list[rt.Node] | None): 검색 대상 노드 리스트. None이면 씬의 전체 객체를 검색한다.

        Returns:
            list[rt.Node]: 애니메이션이 적용된 노드 리스트
        """
        if nodes is None:
            nodes = rt.objects
        
        result = []
        for node in nodes:
            if self.is_node_animated(node):
                result.append(node)
        
        return result
    
    def find_animated_material_nodes(self, nodes=None):
        """애니메이션이 적용된 재질을 가진 노드를 모두 찾는다.

        Args:
            nodes (list[rt.Node] | None): 검색 대상 노드 리스트. None이면 씬의 전체 객체를 검색한다.

        Returns:
            list[rt.Node]: 재질에 애니메이션이 적용된 노드 리스트
        """
        if nodes is None:
            nodes = rt.objects
        
        result = []
        for node in nodes:
            mat = rt.getProperty(node, "material")
            if mat is not None and self.is_node_animated(mat):
                result.append(node)
        
        return result
    
    def find_animated_transform_nodes(self, nodes=None):
        """애니메이션이 적용된 변환 컨트롤러를 가진 노드를 모두 찾는다.

        Args:
            nodes (list[rt.Node] | None): 검색 대상 노드 리스트. None이면 씬의 전체 객체를 검색한다.

        Returns:
            list[rt.Node]: 변환에 애니메이션이 적용된 노드 리스트
        """
        if nodes is None:
            nodes = rt.objects
        
        result = []
        for node in nodes:
            controller = rt.getProperty(node, "controller")
            if self.is_node_animated(controller):
                result.append(node)
        
        return result
    
    def save_animation(self, inObjs, inSaveFilePath, inKeyPerFrame=True):
        """객체들의 애니메이션을 애니메이션 파일로 저장한다.

        애니메이션이 적용된 노드만 골라 LoadSaveAnimation으로 저장하며, 저장 구간은 현재 애니메이션 범위이다.

        Args:
            inObjs (list[rt.Node]): 애니메이션을 저장할 객체 리스트
            inSaveFilePath (str): 저장할 파일 경로
            inKeyPerFrame (bool): True이면 구간 내 매 프레임에 키를 만들어 저장한다.

        Returns:
            bool: 저장 성공 여부. 리스트가 비었거나 유효하지 않은 노드가 있으면 False
        """
        
        if not(len(inObjs) > 0):
            return False
        
        for obj in inObjs:
            if not(rt.isValidNode(obj)):
                return False
        
        animatedNodes = self.find_animated_nodes(inObjs)
        rt.LoadSaveAnimation.setUpAnimsForSave(animatedNodes, animatedTracks=True, includeContraints=True, keyable=True)
        animSaveResult = rt.LoadSaveAnimation.saveAnimation(
            inSaveFilePath,
            animatedNodes,
            "tempVal",
            "tempVal",
            animatedTracks=True,
            includeConstraints=True,
            keyableTracks=True,
            SaveSegment=True,
            segInterval=rt.animationRange,
            segKeyPerFrame=inKeyPerFrame
        )
        
        return animSaveResult
    
    def load_animation(self, inObjs, inLoadFilePath, inMapFilePath=None):
        """애니메이션 파일을 객체들에 로드한다.

        Args:
            inObjs (list[rt.Node]): 애니메이션을 로드할 객체 리스트
            inLoadFilePath (str): 로드할 애니메이션 파일 경로
            inMapFilePath (str | None): None이 아니면 맵 파일 사용 모드로 로드한다. 전달된 경로
                문자열 자체는 사용되지 않고 getAnimMapFile()로 얻은 맵 파일이 사용된다.

        Returns:
            bool: 로드 성공 여부. 파일이 존재하지 않으면 False
        """
        animLoadResult = False
        if not(rt.doesFileExist(inLoadFilePath)):
            return False
        
        rt.LoadSaveAnimation.setUpAnimsForLoad(inObjs, includePB2s=True, stripLayers=True)
        animMapFile = None
        animMapFileLoaded = False
        if inMapFilePath is not None:
            animMapFile = rt.LoadSaveAnimation.getAnimMapFile()
            animMapFileLoaded = True
            animLoadResult = rt.LoadSaveAnimation.loadAnimation(
                inLoadFilePath, inObjs, 
                insert=False, 
                relative=False, 
                insertTime=0, 
                stripLayers=True, 
                useMapFile=animMapFileLoaded, 
                mapFileName=animMapFile
            )
        else:
            animLoadResult = rt.LoadSaveAnimation.loadAnimation(
                inLoadFilePath, 
                inObjs, 
                insert=False, 
                relative=False, 
                insertTime=0, 
                stripLayers=True
            )
        
        return animLoadResult
        
    
    def save_xform(self, inObj):
        """객체의 현재 변환 행렬을 월드·부모 스페이스 문자열로 사용자 프로퍼티에 저장한다.

        부모 스페이스 행렬(ParentSpaceMatrix)은 부모가 있는 경우에만 저장한다.

        Args:
            inObj (rt.Node): 변환 값을 저장할 객체
        """
        # 월드 스페이스 행렬 저장
        transformString = str(inObj.transform)
        rt.setUserProp(inObj, rt.Name("WorldSpaceMatrix"), transformString)
        
        # 부모가 존재하면 부모 스페이스 행렬도 저장
        parent = inObj.parent
        if parent is not None:
            parentTransform = parent.transform
            inverseParent = rt.inverse(parentTransform)
            objTransform = inObj.transform
            parentSpaceMatrix = objTransform * inverseParent
            rt.setUserProp(inObj, rt.Name("ParentSpaceMatrix"), str(parentSpaceMatrix))
    
    def set_xform(self, inObj, space="World"):
        """save_xform으로 저장된 변환 행렬을 객체에 적용한다.

        Args:
            inObj (rt.Node): 변환 값을 적용할 객체
            space (str): 적용할 변환 공간. "World" 또는 "Parent"
        """
        if space == "World":
            # 월드 스페이스 행렬 적용
            matrixString = rt.getUserProp(inObj, rt.Name("WorldSpaceMatrix"))
            transformMatrix = rt.execute(matrixString)
            rt.setProperty(inObj, "transform", transformMatrix)
        elif space == "Parent":
            # 부모 스페이스 행렬 적용
            parent = inObj.parent
            matrixString = rt.getUserProp(inObj, rt.Name("ParentSpaceMatrix"))
            parentSpaceMatrix = rt.execute(matrixString)
            if parent is not None:
                parentTransform = parent.transform
                transformMatrix = parentSpaceMatrix * parentTransform
                rt.setProperty(inObj, "transform", transformMatrix)
