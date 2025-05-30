#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Root Motion 모듈
3DS Max에서 Root Motion을 처리하는 기능을 제공
"""

from pymxs import runtime as rt
from pymxs import attime, animate, undo

from .name import Name
from .anim import Anim
from .helper import Helper
from .constraint import Constraint
from .bip import Bip

class RootMotion:
    """
    Root Motion 관련 기능을 위한 클래스
    3DS Max에서 Root Motion을 처리하는 기능을 제공합니다.
    """

    def __init__(self, nameService=None, animService=None, constraintService=None, helperService=None, bipService=None):
        """
        클래스 초기화.

        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)

        # Root Motion 관련 변수 초기화
        self.rootNode = None
        self.pelvis = None
        self.lFoot = None
        self.rFoot = None
        self.floorThreshold = 2.0  # 바닥 접촉 임계값 기본값
        self.footSpeedThreshold = 1.0  # 발 속도 임계값 기본값
        self.fps = 60.0
        self.keepZAtZero = True  # Z축을 0으로 유지할지 여부
        self.followZRotation = False  # XY 회전을 잠글지 여부

    def is_foot_planted(self, footBone, frameTime, floorThreshold=2.0, fps=60.0, footSpeedThreshold=0.1):
        """
        발이 바닥에 고정되어 있는지 확인하는 함수
        
        Args:
            footBone (node): 발 본 객체
            frameTime (int): 현재 프레임 시간
            floorThreshold (float): 바닥 접촉 임계값 (기본값: 2.0)
            fps (float): 초당 프레임 수 (기본값: 60.0)
            footSpeedThreshold (float): 발 속도 임계값 (기본값: 0.1)
        
        Returns:
            bool: 발이 바닥에 고정되어 있으면 True, 그렇지 않으면 False
        """
        footPosCurrentWorld = footBone.transform.position
        footPosPrevWorld = footBone.transform.position
        isPlanted = False
        frameIntervalSec = 1.0 / fps if fps > 0 else 0.0
        
        with attime(frameTime):
            footPosCurrentWorld = footBone.transform.position
        
        if frameTime > int(rt.animationRange.start):
            with attime(frameTime -1):
                footPosPrevWorld = footBone.transform.position
            
            distMovedXY = rt.distance(rt.Point2(footPosCurrentWorld.x, footPosCurrentWorld.y),
                                      rt.Point2(footPosPrevWorld.x, footPosPrevWorld.y))
            if frameIntervalSec > 0.0:
                footSpeedXY = distMovedXY
            else:
                footSpeedXY = 0.0
        else:
            footSpeedXY = 0.0
            
        if footPosCurrentWorld.z <= floorThreshold and footSpeedXY <= footSpeedThreshold:
            isPlanted = True
        
        return isPlanted

    def create_root_motion_from_bounding_box(self, bipCom, rootBone, startFrame, endFrame, floorThreshold=2.0, footSpeedThreshold=1.0, keepZAtZero=True, followZRotation=False):
        """
        Root Motion을 Bounding Box를 기반으로 생성하는 함수 (키프레임 데이터만 생성)
        
        Args:
            bipCom (node): Biped COM 객체
            rootBone (node): 루트 본 객체
            startFrame (int): 시작 프레임
            endFrame (int): 끝 프레임
            floorThreshold (float): 바닥 접촉 임계값 (기본값: 2.0)
            footSpeedThreshold (float): 발 속도 임계값 (기본값: 1.0)
            keepZAtZero (bool): Z축을 0으로 유지할지 여부 (기본값: True)
            followZRotation (bool): Z축 회전을 따라갈지 여부 (기본값: False)
        
        Returns:
            dict: 키프레임 데이터 딕셔너리 (실패시 None)
        """
        # 입력 검증
        if not rt.isValidNode(rootBone) or startFrame >= endFrame or not rt.isValidNode(bipCom):
            return None
        
        self.rootNode = rootBone
          # 발 본 가져오기
        lToes_nodes = self.bip.get_grouped_nodes(bipCom, "lToes")
        rToes_nodes = self.bip.get_grouped_nodes(bipCom, "rToes")
        if not lToes_nodes or not rToes_nodes:
            return None
        
        self.lFoot = lToes_nodes[0]
        self.rFoot = rToes_nodes[0]
        self.pelvis = self.bip.get_grouped_nodes(bipCom, "pelvis")[0]
        
        # 필요한 Biped 노드 그룹들을 수집
        node_groups = ["pelvis", "lLeg", "rLeg", "spine", "neck", "head"]
        allBipNodes = []
        
        for group in node_groups:
            nodes = self.bip.get_grouped_nodes(bipCom, group)
            allBipNodes.extend(nodes)
          # 유효한 노드만 필터링
        allBipNodes = [node for node in allBipNodes if node and rt.isValidNode(node)]
        if not allBipNodes:
            return None
        
        self.floorThreshold = floorThreshold
        self.footSpeedThreshold = footSpeedThreshold
        self.keepZAtZero = keepZAtZero
        self.followZRotation = followZRotation
        
        # 시작 프레임에서 상대적 위치 계산
        with attime(startFrame):            # 바운딩 박스 계산
            initialBbox = rt.box3()
            for obj in allBipNodes:
                initialBbox += obj.boundingBox
            # 바운딩 박스 유효성 확인
            if initialBbox.min == initialBbox.max:
                return None
            
            initialBboxCenter = initialBbox.center
            initialBboxSize = initialBbox.max - initialBbox.min
            initialRootPos = bipCom.transform.position
            initialZOffset = -bipCom.transform.position.z
            initialRot = self.rootNode.transform.rotation
            
            # 상대적 오프셋 계산 (0으로 나누기 방지)
            MIN_SIZE = 0.001
            relativeOffsetX = (initialRootPos.x - initialBboxCenter.x) / initialBboxSize.x if abs(initialBboxSize.x) > MIN_SIZE else 0.0
            relativeOffsetY = (initialRootPos.y - initialBboxCenter.y) / initialBboxSize.y if abs(initialBboxSize.y) > MIN_SIZE else 0.0
        
        # 키프레임 데이터 수집
        keyframe_data = {}
        
        for t in range(startFrame, endFrame + 1):
            isLFootPlanted = self.is_foot_planted(self.lFoot, t, self.floorThreshold, self.fps, self.footSpeedThreshold)
            isRFootPlanted = self.is_foot_planted(self.rFoot, t, self.floorThreshold, self.fps, self.footSpeedThreshold)
            
            # 양발이 모두 땅에 붙어있지 않을 때만 루트 모션 계산
            if not (isLFootPlanted and isRFootPlanted):
                # 현재 프레임의 바운딩 박스 계산
                with attime(t):
                    currentBbox = rt.box3()
                    validNodeCount = 0
                    
                    for obj in allBipNodes:
                        currentBbox += obj.boundingBox
                        validNodeCount += 1
                      # 유효한 바운딩 박스 확인
                    if validNodeCount == 0 or currentBbox.min == currentBbox.max:
                        continue
                    
                    currentBboxCenter = currentBbox.center
                    currentBboxSize = currentBbox.max - currentBbox.min
                    # 새로운 루트 위치 계산
                    if self.keepZAtZero:
                        newRootPos = rt.Point3(
                            currentBboxCenter.x + (relativeOffsetX * currentBboxSize.x),
                            currentBboxCenter.y + (relativeOffsetY * currentBboxSize.y),
                            0.0  # Z축은 0으로 유지
                        )
                    else:
                        newRootPos = rt.Point3(
                            currentBboxCenter.x + (relativeOffsetX * currentBboxSize.x),
                            currentBboxCenter.y + (relativeOffsetY * currentBboxSize.y),
                            self.pelvis.transform.position.z + initialZOffset  # Z축은 현재 펠비스 위치에 오프셋 추가
                        )
                    
                    # 로테이션 계산
                    if self.followZRotation:
                        # 펠비스의 Z축 회전을 따라감
                        newRootRot = rt.EulerAngles(0, 0, rt.quatToEuler(bipCom.transform.rotation).z)
                    else:
                        # 회전 없음 (기본값)
                        newRootRot = rt.quatToEuler(initialRot)
                    # 딕셔너리에 위치와 회전 정보 저장
                    keyframe_data[t] = {
                        'position': newRootPos,
                        'rotation': newRootRot
                    }
        
        return keyframe_data

    def apply_keyframes_locomotion_mode(self, keyframe_data):
        """
        로코모션 모드로 키프레임을 적용하는 함수 (시작과 끝 프레임에만 키 생성)
        
        Args:
            keyframe_data (dict): 키프레임 데이터 딕셔너리
        
        Returns:
            bool: 성공 여부
        """
        if not keyframe_data or not self.rootNode:
            return False
        
        node_name = self.rootNode.name
        frame_list = sorted(keyframe_data.keys())
        
        if len(frame_list) < 2:
            return False
        
        # 시작과 끝 프레임만 선택
        start_frame = frame_list[0]
        end_frame = frame_list[-1]
        
        start_data = keyframe_data[start_frame]
        end_data = keyframe_data[end_frame]
        
        maxscriptCode = f"""
        (
            animate on(
                -- 시작 프레임 키
                at time {start_frame} (
                    $'{node_name}'.position = [{start_data["position"].x}, {start_data["position"].y}, {start_data["position"].z}]
                    $'{node_name}'.transform = (matrix3 1) * (rotateXMatrix {start_data["rotation"].x}) * (rotateYMatrix {start_data["rotation"].y}) * (rotateZMatrix {start_data["rotation"].z}) * (transMatrix $'{node_name}'.pos)
                )
                
                -- 끝 프레임 키
                at time {end_frame} (
                    $'{node_name}'.position = [{end_data["position"].x}, {end_data["position"].y}, {end_data["position"].z}]
                    $'{node_name}'.transform = (matrix3 1) * (rotateXMatrix {start_data["rotation"].x}) * (rotateYMatrix {start_data["rotation"].y}) * (rotateZMatrix {start_data["rotation"].z}) * (transMatrix $'{node_name}'.pos)
                )
            )
        )
        """
        
        try:
            # 첫 번째 실행 (3DS Max 버그 우회용)
            rt.execute(maxscriptCode)
            
            # 생성된 키들을 프레임 범위에서만 삭제
            self.anim.delete_keys_in_range(self.rootNode, start_frame, end_frame)
            
            # 두 번째 실행 (실제 키 생성)
            rt.execute(maxscriptCode)
            return True
        except Exception as e:
            print(f"Error applying keyframes in locomotion mode: {e}")
            return False

    def apply_keyframes_normal_mode(self, keyframe_data):
        """
        일반 모드로 키프레임을 적용하는 함수 (모든 키프레임에 키 생성)
        
        Args:
            keyframe_data (dict): 키프레임 데이터 딕셔너리
        
        Returns:
            bool: 성공 여부
        """
        if not keyframe_data or not self.rootNode:
            return False
        
        node_name = self.rootNode.name
        frame_list = list(keyframe_data.keys())
        pos_list = [f'[{data["position"].x}, {data["position"].y}, {data["position"].z}]' for data in keyframe_data.values()]
        rot_list = [f'(eulerAngles {data["rotation"].x} {data["rotation"].y} {data["rotation"].z})' for data in keyframe_data.values()]
        
        maxScriptFrameArray = f"#({', '.join(map(str, frame_list))})"
        maxScriptPosArray = f"#({', '.join(pos_list)})"
        maxScriptRotArray = f"#({', '.join(rot_list)})"
        
        maxscriptCode = f"""
        (
            local frameArray = {maxScriptFrameArray}
            local posArray = {maxScriptPosArray}
            local rotArray = {maxScriptRotArray}
            
            animate on(
                for i = 1 to frameArray.count do
                (
                    local frame_time = frameArray[i]
                    local position = posArray[i]
                    local rotation = rotArray[i]
                    
                    at time frame_time (
                        $'{node_name}'.position = position
                        $'{node_name}'.transform = (matrix3 1) * (rotateXMatrix rotation.x) * (rotateYMatrix rotation.y) * (rotateZMatrix rotation.z) * (transMatrix $'{node_name}'.pos)
                    )
                )
            )
        )
        """
        
        try:
            # 첫 번째 실행 (3DS Max 버그 우회용)
            rt.execute(maxscriptCode)
            
            # 생성된 키들을 프레임 범위에서만 삭제
            if frame_list:
                start_frame = min(frame_list)
                end_frame = max(frame_list)
                self.anim.delete_keys_in_range(self.rootNode, start_frame, end_frame)
            
            # 두 번째 실행 (실제 키 생성)
            rt.execute(maxscriptCode)
            return True
        except Exception as e:
            print(f"Error applying keyframes in normal mode: {e}")
            return False