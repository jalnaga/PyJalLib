#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
애니메이션 모듈 - 3ds Max용 애니메이션 관련 기능 제공
원본 MAXScript의 anim.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

import math
import copy
from pymxs import attime, animate, undo
from pymxs import runtime as rt


class Anim:
    """
    애니메이션 관련 기능을 제공하는 클래스.
    MAXScript의 _Anim 구조체 개념을 Python으로 재구현한 클래스이며, 3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self):
        """클래스 초기화 (현재 특별한 초기화 동작은 없음)"""
        pass
    
    def rotate_local(self, inObj, rx, ry, rz, dontAffectChildren=False):
        """
        객체를 로컬 좌표계에서 회전시킴.
        
        매개변수:
            inObj : 회전할 객체
            rx    : X축 회전 각도 (도 단위)
            ry    : Y축 회전 각도 (도 단위)
            rz    : Z축 회전 각도 (도 단위)
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
        """
        객체를 로컬 좌표계에서 이동시킴.
        
        매개변수:
            inObj : 이동할 객체
            mx    : X축 이동 거리
            my    : Y축 이동 거리
            mz    : Z축 이동 거리
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
        """
        객체의 트랜스폼 컨트롤러를 기본 상태로 재설정함.
        
        매개변수:
            inObj : 초기화할 객체
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
        """
        객체의 변환(회전, 위치)을 키프레임에 의한 애니메이션 영향 없이 고정함.
        
        매개변수:
            inObj : 변환을 고정할 객체
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
        """
        객체의 애니메이션 변환을 병합하여 단일 트랜스폼으로 통합함.
        
        매개변수:
            inObj      : 변환 병합 대상 객체
            startFrame : 시작 프레임 (기본값: 애니메이션 범위의 시작)
            endFrame   : 끝 프레임 (기본값: 애니메이션 범위의 끝)
        """
        # 시작과 끝 프레임이 지정되지 않은 경우 기본값 할당
        if startFrame is None:
            startFrame = int(rt.animationRange.start)
        if endFrame is None:
            endFrame = int(rt.animationRange.end)
        
        maxScriptCode = f""
        maxScriptCode += f"disableSceneRedraw()\n"
        maxScriptCode += f"progressStart (\"Collapse transform {inObj.name}...\")\n"
        maxScriptCode += f"inObj = $'{inObj.name}'\n"
        maxScriptCode += f"p = point()\n"
        maxScriptCode += f"for k = {startFrame} to {endFrame} do (\n"
        maxScriptCode += f"    at time k (\n"
        maxScriptCode += f"        with animate on p.transform = inObj.transform\n"
        maxScriptCode += f"    )\n"
        maxScriptCode += f")\n"
        maxScriptCode += f"\n"
        maxScriptCode += f"inObj.transform.controller = transform_script()\n"
        maxScriptCode += f"inObj.transform.controller = prs()\n"
        maxScriptCode += f"\n"
        maxScriptCode += f"for k = {startFrame} to {endFrame} do (\n"
        maxScriptCode += f"    at time k (\n"
        maxScriptCode += f"        with animate on (\n"
        maxScriptCode += f"            in coordsys (transmatrix inObj.transform.pos) inObj.rotation = inverse p.transform.rotation\n"
        maxScriptCode += f"            in coordsys world inObj.position = p.transform.position\n"
        maxScriptCode += f"            inObj.scale = p.scale\n"
        maxScriptCode += f"        )\n"
        maxScriptCode += f"    )\n"
        maxScriptCode += f"    progressUpdate (100 * k / {endFrame})\n"
        maxScriptCode += f")\n"
        maxScriptCode += f"\n"
        maxScriptCode += f"if {startFrame} != animationRange.start then (\n"
        maxScriptCode += f"    deselectKeys inObj.transform.controller\n"
        maxScriptCode += f"    selectKeys inObj.transform.controller animationRange.start\n"
        maxScriptCode += f"    deleteKeys inObj.transform.controller #selection\n"
        maxScriptCode += f"    deselectKeys inObj.transform.controller\n"
        maxScriptCode += f")\n"
        maxScriptCode += f"\n"
        maxScriptCode += f"delete p\n"
        maxScriptCode += f"progressEnd()\n"
        maxScriptCode += f"enableSceneRedraw()\n"
        
        rt.execute(maxScriptCode)
    
    def match_anim_transform(self, inObj, inTarget, startFrame=None, endFrame=None):
        """
        한 객체의 애니메이션 변환을 다른 객체의 변환과 일치시킴.
        
        매개변수:
            inObj      : 변환을 적용할 객체
            inTarget   : 기준이 될 대상 객체
            startFrame : 시작 프레임 (기본값: 애니메이션 범위의 시작)
            endFrame   : 끝 프레임 (기본값: 애니메이션 범위의 끝)
        """
        # 시작/끝 프레임 기본값 설정
        if startFrame is None:
            startFrame = int(rt.animationRange.start)
        if endFrame is None:
            endFrame = int(rt.animationRange.end)
            
        maxscriptCode = f""
        maxscriptCode += f"inObj = $'{inObj.name}'\n"
        maxscriptCode += f"inTarget = $'{inTarget.name}'\n"
        maxscriptCode += f"if (isValidNode inObj) and (isValidNode inTarget) then (\n"
        maxscriptCode += f"    disableSceneRedraw()\n"
        maxscriptCode += f"    progressStart (\"Match transform {inObj.name} to {inTarget.name} \")\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    p = point()\n"
        maxscriptCode += f"    for k = {startFrame} to {endFrame} do (\n"
        maxscriptCode += f"        at time k (\n"
        maxscriptCode += f"            with animate on p.transform = inTarget.transform\n"
        maxscriptCode += f"        )\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"        deselectKeys inObj.transform.controller\n"
        maxscriptCode += f"        selectKeys inObj.transform.controller k\n"
        maxscriptCode += f"        deleteKeys inObj.transform.controller #selection\n"
        maxscriptCode += f"        deselectKeys inObj.transform.controller\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    progressUpdate 20\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    if {startFrame} != animationRange.start then (\n"
        maxscriptCode += f"        deselectKeys p.transform.controller\n"
        maxscriptCode += f"        selectKeys p.transform.controller animationRange.start\n"
        maxscriptCode += f"        deleteKeys p.transform.controller #selection\n"
        maxscriptCode += f"        deselectKeys p.transform.controller\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    progressUpdate 25\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    local posKeyArray = inTarget.pos.controller.keys\n"
        maxscriptCode += f"    local rotKeyArray = inTarget.rotation.controller.keys\n"
        maxscriptCode += f"    local scaleKeyArray = inTarget.scale.controller.keys\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    at time {startFrame} (\n"
        maxscriptCode += f"        with animate on inObj.transform = p.transform\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"    at time {endFrame} (\n"
        maxscriptCode += f"        with animate on inObj.transform = p.transform\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    for key in posKeyArray do (\n"
        maxscriptCode += f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        maxscriptCode += f"            at time key.time (\n"
        maxscriptCode += f"                with animate on inObj.transform = p.transform\n"
        maxscriptCode += f"            )\n"
        maxscriptCode += f"        )\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"    progressUpdate 40\n"
        maxscriptCode += f"    for key in rotKeyArray do (\n"
        maxscriptCode += f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        maxscriptCode += f"            at time key.time (\n"
        maxscriptCode += f"                with animate on inObj.transform = p.transform\n"
        maxscriptCode += f"            )\n"
        maxscriptCode += f"        )\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"    progressUpdate 60\n"
        maxscriptCode += f"    for key in scaleKeyArray do (\n"
        maxscriptCode += f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        maxscriptCode += f"            at time key.time (\n"
        maxscriptCode += f"                with animate on inObj.transform = p.transform\n"
        maxscriptCode += f"            )\n"
        maxscriptCode += f"        )\n"
        maxscriptCode += f"    )\n"
        maxscriptCode += f"    progressUpdate 80\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    delete p\n"
        maxscriptCode += f"\n"
        maxscriptCode += f"    progressUpdate 100\n"
        maxscriptCode += f"    progressEnd()\n"
        maxscriptCode += f"    enableSceneRedraw()\n"
        maxscriptCode += f")\n"
        
        rt.execute(maxscriptCode)
    
    def create_average_pos_transform(self, inTargetArray):
        """
        여러 객체들의 평균 위치를 계산하여 단일 변환 행렬을 생성함.
        
        매개변수:
            inTargetArray : 평균 위치 계산 대상 객체 배열
            
        반환:
            계산된 평균 위치를 적용한 변환 행렬
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
        """
        여러 객체들의 평균 회전을 계산하여 단일 변환 행렬을 생성함.
        
        매개변수:
            inTargetArray : 평균 회전 계산 대상 객체 배열
            
        반환:
            계산된 평균 회전을 적용한 변환 행렬
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
        """
        주어진 컨트롤러와 그 하위 컨트롤러에서 모든 키프레임을 재귀적으로 수집함.
        
        매개변수:
            inController : 키프레임 검색 대상 컨트롤러 객체
            keys_list    : 수집된 키프레임들을 저장할 리스트 (참조로 전달)
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
        """
        객체에 적용된 모든 키프레임을 가져옴.
        
        매개변수:
            inObj : 키프레임을 검색할 객체
            
        반환:
            객체에 적용된 키프레임들의 리스트
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
        """
        객체의 키프레임 중 가장 먼저와 마지막 키프레임을 찾음.
        
        매개변수:
            inObj : 키프레임을 검색할 객체
            
        반환:
            [시작 키프레임, 끝 키프레임] (키가 없으면 빈 리스트 반환)
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
        """
        객체에 적용된 모든 키프레임을 삭제함.
        
        매개변수:
            inObj : 삭제 대상 객체
        """
        rt.deleteKeys(inObj, rt.Name('allKeys'))
    
    def delete_keys_in_range(self, node, startFrame, endFrame):
        """
        지정된 프레임 범위에서 노드의 모든 키를 삭제하는 함수
        
        Args:
            node: 키를 삭제할 노드
            startFrame (int): 시작 프레임
            endFrame (int): 끝 프레임
        
        Returns:
            bool: 성공 여부
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
        """
        객체 및 그 하위 요소(애니메이션, 커스텀 속성 등)가 애니메이션 되었는지 재귀적으로 확인함.
        
        매개변수:
            node : 애니메이션 여부를 확인할 객체 또는 서브 애니메이션
            
        반환:
            True  : 애니메이션이 적용된 경우
            False : 애니메이션이 없는 경우
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
        """
        애니메이션이 적용된 객체들을 모두 찾음.
        
        매개변수:
            nodes : 검색 대상 객체 리스트 (None이면 전체 객체)
            
        반환:
            애니메이션이 적용된 객체들의 리스트
        """
        if nodes is None:
            nodes = rt.objects
        
        result = []
        for node in nodes:
            if self.is_node_animated(node):
                result.append(node)
        
        return result
    
    def find_animated_material_nodes(self, nodes=None):
        """
        애니메이션이 적용된 재질을 가진 객체들을 모두 찾음.
        
        매개변수:
            nodes : 검색 대상 객체 리스트 (None이면 전체 객체)
            
        반환:
            애니메이션이 적용된 재질을 가진 객체들의 리스트
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
        """
        애니메이션이 적용된 변환 정보를 가진 객체들을 모두 찾음.
        
        매개변수:
            nodes : 검색 대상 객체 리스트 (None이면 전체 객체)
            
        반환:
            애니메이션이 적용된 변환 데이터를 가진 객체들의 리스트
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
        """
        객체의 애니메이션을 저장함.
        
        매개변수:
            inObj : 애니메이션을 저장할 객체
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
        """
        애니메이션을 로드함.
        
        매개변수:
            inObjs : 애니메이션을 로드할 객체
            inLoadFilePath : 애니메이션을 로드할 파일 경로
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
        """
        객체의 현재 변환 행렬(월드, 부모 스페이스)을 저장하여 복원을 가능하게 함.
        
        매개변수:
            inObj : 변환 값을 저장할 객체
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
        """
        저장된 변환 행렬을 객체에 적용함.
        
        매개변수:
            inObj : 변환 값을 적용할 객체
            space : "World" 또는 "Parent" (적용할 변환 공간)
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
