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
    
    def rotate_local(self, inObj, rx, ry, rz):
        """
        객체를 로컬 좌표계에서 회전시킴.
        
        매개변수:
            inObj : 회전할 객체
            rx    : X축 회전 각도 (도 단위)
            ry    : Y축 회전 각도 (도 단위)
            rz    : Z축 회전 각도 (도 단위)
        """
        # 현재 객체의 변환 행렬을 가져옴
        currentMatrix = rt.getProperty(inObj, "transform")
        # 오일러 각도를 통해 회전 행렬(쿼터니언) 생성
        eulerAngles = rt.eulerAngles(rx, ry, rz)
        quatRotation = rt.eulertoquat(eulerAngles)
        # preRotate를 이용해 회전 적용
        rt.preRotate(currentMatrix, quatRotation)
        # 변경된 행렬을 객체에 설정
        rt.setProperty(inObj, "transform", currentMatrix)
    
    def move_local(self, inObj, mx, my, mz):
        """
        객체를 로컬 좌표계에서 이동시킴.
        
        매개변수:
            inObj : 이동할 객체
            mx    : X축 이동 거리
            my    : Y축 이동 거리
            mz    : Z축 이동 거리
        """
        # 현재 변환 행렬 가져오기
        currentMatrix = rt.getProperty(inObj, "transform")
        # 이동량을 Point3 형태로 생성
        translation = rt.Point3(mx, my, mz)
        # preTranslate를 이용해 행렬에 이동 적용
        rt.preTranslate(currentMatrix, translation)
        # 적용된 이동 변환 행렬을 객체에 설정
        rt.setProperty(inObj, "transform", currentMatrix)
    
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
            
        # 씬 리드로우(화면 업데이트)를 중단하여 성능 최적화
        rt.disableSceneRedraw()
        
        # 진행 상태 표시 시작
        progressMessage = f"Collapse transform {inObj.name}..."
        rt.progressStart(progressMessage, allowCancel=True)
        
        # 임시 포인트 객체 생성 (중간 변환값 저장용)
        p = rt.Point()
        
        # 각 프레임에서 대상 객체의 변환 정보를 임시 포인트에 저장
        for k in range(startFrame, endFrame+1):
            with attime(k):
                with animate(True):
                    rt.setProperty(p, "transform", rt.getProperty(inObj, "transform"))
                    
        # 트랜스폼 컨트롤러를 스크립트와 PRS 컨트롤러로 재설정
        rt.setPropertyController(inObj.controller, "Transform", rt.transform_Script())
        rt.setPropertyController(inObj.controller, "Transform", rt.prs())
        
        # 각 프레임별로 임시 포인트와의 차이를 계산해서 최종 변환 적용
        for k in range(startFrame, endFrame+1):
            with attime(k):
                with animate(True):
                    tm = inObj.transform * rt.inverse(p.transform)
                    rt.setProperty(inObj, "rotation", tm.rotation)
                    rt.setProperty(inObj, "position", p.transform.position)
                    rt.setProperty(inObj, "scale", p.transform.scale)
            
            # 진행 상황 업데이트 (백분율 계산)
            rt.progressUpdate(100 * k / endFrame)
        
        # 임시 포인트 객체 삭제
        rt.delete(p)
        
        # 진행 상태 종료 및 씬 업데이트 재활성화
        rt.progressEnd()
        rt.enableSceneRedraw()
    
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
            
        # 대상 객체와 기준 객체가 유효한지 확인
        if rt.isValidNode(inObj) and rt.isValidNode(inTarget):
            # 씬 업데이트 중단
            rt.disableSceneRedraw()
            
            # 진행 상태 표시 시작
            progressMessage = f"Match transform {inObj.name} to {inTarget.name}"
            rt.progressStart(progressMessage, allowCancel=True)
            progressCounter = 0
            
            # 임시 포인트 객체 생성 (타겟 변환 저장용)
            p = rt.Point()
            
            # 각 프레임마다 inTarget의 변환을 저장하고 inObj의 기존 키 삭제
            for k in range(startFrame, endFrame + 1):
                with attime(k):
                    with animate(True):
                        rt.setProperty(p, "transform", rt.getProperty(inTarget, "transform"))
                
                # inObj의 위치, 회전, 스케일 컨트롤러에서 기존 키 삭제
                inObjControllers = []
                inObjControllers.append(rt.getPropertyController(inObj.controller, "Position"))
                inObjControllers.append(rt.getPropertyController(inObj.controller, "Rotation"))
                inObjControllers.append(rt.getPropertyController(inObj.controller, "Scale"))
                
                for controller in inObjControllers:
                    rt.deselectKeys(controller)
                    rt.selectKeys(controller, k)
                    rt.deleteKeys(controller, rt.Name("selection"))
                    rt.deselectKeys(controller)
                    
                progressCounter += 1
                if progressCounter >= 100:
                    progressCounter = 0
                rt.progressUpdate(progressCounter)
                    
            # 시작 프레임 이전의 불필요한 키 삭제
            if startFrame != rt.animationRange.start:
                dumPointControllers = []
                dumPointControllers.append(rt.getPropertyController(p.controller, "Position"))
                dumPointControllers.append(rt.getPropertyController(p.controller, "Rotation"))
                dumPointControllers.append(rt.getPropertyController(p.controller, "Scale"))
                
                for controller in dumPointControllers:
                    rt.deselectKeys(controller)
                    rt.selectKeys(controller, startFrame)
                    rt.deleteKeys(controller, rt.Name("selection"))
                    rt.deselectKeys(controller)
                
                progressCounter += 1
                if progressCounter >= 100:
                    progressCounter = 0
                rt.progressUpdate(progressCounter)
            
            # inTarget의 각 컨트롤러에서 키 배열을 가져옴
            inTargetPosController = rt.getPropertyController(inTarget.controller, "Position")
            inTargetRotController = rt.getPropertyController(inTarget.controller, "Rotation")
            inTargetScaleController = rt.getPropertyController(inTarget.controller, "Scale")
            
            posKeyArray = inTargetPosController.keys
            rotKeyArray = inTargetRotController.keys
            scaleKeyArray = inTargetScaleController.keys
            
            # 시작 프레임 및 끝 프레임의 변환 적용
            with attime(startFrame):
                with animate(True):
                    rt.setProperty(inObj, "transform", rt.getProperty(p, "transform"))
            with attime(endFrame):
                with animate(True):
                    rt.setProperty(inObj, "transform", rt.getProperty(p, "transform"))
            
            # 위치 키프레임 적용
            for key in posKeyArray:
                keyTime = int(rt.getProperty(key, "time"))
                if keyTime >= startFrame and keyTime <= endFrame:
                    with attime(keyTime):
                        with animate(True):
                            rt.setProperty(inObj, "transform", rt.getProperty(p, "transform"))
                progressCounter += 1
                if progressCounter >= 100:
                    progressCounter = 0
                rt.progressUpdate(progressCounter)
            
            # 회전 키프레임 적용
            for key in rotKeyArray:
                keyTime = int(rt.getProperty(key, "time"))
                if keyTime >= startFrame and keyTime <= endFrame:
                    with attime(keyTime):
                        with animate(True):
                            rt.setProperty(inObj, "transform", rt.getProperty(p, "transform"))
                progressCounter += 1
                if progressCounter >= 100:
                    progressCounter = 0
                rt.progressUpdate(progressCounter)
                            
            # 스케일 키프레임 적용
            for key in scaleKeyArray:
                keyTime = int(rt.getProperty(key, "time"))
                if keyTime >= startFrame and keyTime <= endFrame:
                    with attime(keyTime):
                        with animate(True):
                            rt.setProperty(inObj, "transform", rt.getProperty(p, "transform"))
                progressCounter += 1
                if progressCounter >= 100:
                    progressCounter = 0
                rt.progressUpdate(progressCounter)
            
            # 임시 포인트 객체 삭제
            rt.delete(p)
            
            # 진행 상태 100% 업데이트 후 종료
            rt.progressUpdate(100)
            rt.progressEnd()
            rt.enableSceneRedraw()
    
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
                for k in inController.keys:
                    keys_list.append(k)

            # 하위 컨트롤러에 대해서 재귀적으로 검색
            for i in range(inController.numSubs):
                sub_controller = inController[i]  # 1부터 시작하는 인덱스
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
                keyTimes = [key.time for key in keys]
                minTime = rt.amin(keyTimes)
                maxTime = rt.amax(keyTimes)
                minIndex = keyTimes.index(minTime)
                maxIndex = keyTimes.index(maxTime)
                return [rt.amin(minIndex), rt.amax(maxIndex)]
            else:
                return []
    
    def delete_all_keys(self, inObj):
        """
        객체에 적용된 모든 키프레임을 삭제함.
        
        매개변수:
            inObj : 삭제 대상 객체
        """
        rt.deleteKeys(inObj, rt.Name('allKeys'))
    
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
        
        # 하위 애니메이션에 대해 재귀적으로 검사
        for i in range(node.numSubs):
            animated = self.is_node_animated(node[i])
            if animated:
                break
        
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
    
    def save_xform(self, inObj):
        """
        객체의 현재 변환 행렬(월드, 부모 스페이스)을 저장하여 복원을 가능하게 함.
        
        매개변수:
            inObj : 변환 값을 저장할 객체
        """
        try:
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
        except:
            # 오류 발생 시 예외 무시
            pass
    
    def set_xform(self, inObj, space="World"):
        """
        저장된 변환 행렬을 객체에 적용함.
        
        매개변수:
            inObj : 변환 값을 적용할 객체
            space : "World" 또는 "Parent" (적용할 변환 공간)
        """
        try:
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
        except:
            # 오류 발생 시 예외 무시
            pass
