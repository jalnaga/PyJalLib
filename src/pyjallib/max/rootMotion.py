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
        self.accelerationThreshold = 5.0

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
                        'rotation': newRootRot,
                        'bipComPos': bipCom.transform.position,
                        'bipComRot': bipCom.transform.rotation
                    }
        
        return keyframe_data
    def convert_keyframe_data_for_locomotion(self, bipCom, keyframe_data, acceleration_threshold=5.0, direction_threshold=0.3):
        """
        로코모션 모드에 맞게 키프레임 데이터를 변환하는 함수
        
        Args:
            bipCom (node): Biped COM 객체
            keyframe_data (dict): 키프레임 데이터 딕셔너리
            acceleration_threshold (float): 가속도 변화 임계값 (기본값: 5.0)
            direction_threshold (float): 방향 감지 임계값 (기본값: 0.3, 0.0~1.0)
        
        Returns:
            dict: 변환된 키프레임 데이터 딕셔너리
        """
        if not keyframe_data or not rt.isValidNode(bipCom):
            return {}
        
        converted_data = {}
        frame_list = sorted(keyframe_data.keys())
        
        if len(frame_list) < 3:  # 가속도 계산을 위해 최소 3개 프레임 필요
            return {}
        
        self.accelerationThreshold = acceleration_threshold
        
        # 첫 프레임의 bipCom 위치를 기준으로 설정
        first_frame = frame_list[0]
        first_bipcom_pos = keyframe_data[first_frame]['bipComPos']
        
        # 월드 축 방향 벡터 정의
        world_forward = rt.Point3(0, -1, 0)  # 월드 -Y축 (앞)
        world_backward = rt.Point3(0, 1, 0)  # 월드 +Y축 (뒤)
        world_right = rt.Point3(-1, 0, 0)    # 월드 -X축 (오른쪽)
        world_left = rt.Point3(1, 0, 0)      # 월드 +X축 (왼쪽)
        
        # 방향 변경 추적 변수
        prev_direction = ""
        direction_change_positions = {}  # 방향별 마지막 위치 저장
        
        # 각 프레임별 방향 및 변환된 위치 계산
        for i, frame in enumerate(frame_list):
            frame_data = keyframe_data[frame]
            bipcom_pos = frame_data['bipComPos']
            bipcom_rot = frame_data['bipComRot']
            
            # 실제 이동 방향 계산 (위치 변화 기반)
            movement_direction = rt.Point3(0, 0, 0)
            movement_magnitude = 0.0
            
            if i > 0:  # 첫 번째 프레임이 아닌 경우
                prev_frame = frame_list[i - 1]
                prev_pos = keyframe_data[prev_frame]['bipComPos']
                movement_vector = bipcom_pos - prev_pos
                movement_magnitude = rt.length(movement_vector)
                if movement_magnitude > 0.001:  # 임계값보다 큰 움직임만 처리
                    movement_direction = rt.normalize(movement_vector)
            elif i < len(frame_list) - 1:  # 마지막 프레임이 아닌 경우
                next_frame = frame_list[i + 1]
                next_pos = keyframe_data[next_frame]['bipComPos']
                movement_vector = next_pos - bipcom_pos
                movement_magnitude = rt.length(movement_vector)
                if movement_magnitude > 0.001:  # 임계값보다 큰 움직임만 처리
                    movement_direction = rt.normalize(movement_vector)
            
            # 이동 방향이 유효한 경우에만 dot product 계산
            if movement_magnitude > 0.001:  # 매우 작은 움직임 무시
                # 각 방향과의 dot product 계산
                dot_forward = rt.dot(movement_direction, world_forward)
                dot_backward = rt.dot(movement_direction, world_backward)
                dot_right = rt.dot(movement_direction, world_right)
                dot_left = rt.dot(movement_direction, world_left)
            else:
                # 움직임이 거의 없는 경우 모든 dot product를 0으로 설정
                dot_forward = dot_backward = dot_right = dot_left = 0.0
              # 임계값을 넘는 방향들 확인
            active_directions = []
            if abs(dot_forward) > direction_threshold:
                active_directions.append(("forward", dot_forward))
            if abs(dot_backward) > direction_threshold:
                active_directions.append(("backward", dot_backward))
            if abs(dot_right) > direction_threshold:
                active_directions.append(("right", dot_right))
            if abs(dot_left) > direction_threshold:
                active_directions.append(("left", dot_left))
            
            # 주요 방향 결정 (가장 큰 dot product)
            direction = ""
            if active_directions:
                # 절댓값이 가장 큰 방향을 주요 방향으로 설정
                active_directions.sort(key=lambda x: abs(x[1]), reverse=True)
                direction = active_directions[0][0]
              # 로코모션 위치 계산
            if i == 0:
                # 첫 프레임: 기본 위치로 시작
                locomotion_pos = rt.Point3(first_bipcom_pos.x, first_bipcom_pos.y, frame_data['position'].z)
            else:
                # 이전 프레임의 로코모션 위치를 기준으로 시작
                prev_locomotion_pos = converted_data[frame_list[i-1]]['position']
                locomotion_pos = rt.Point3(prev_locomotion_pos.x, prev_locomotion_pos.y, frame_data['position'].z)
                
                # 방향이 바뀌었는지 확인
                direction_changed = (direction != prev_direction and prev_direction != "")
                
                # 각 축별로 독립적으로 업데이트 (임계값 기반)
                x_updated = False
                y_updated = False
                
                # X축 업데이트 (좌우 움직임)
                if abs(dot_right) > direction_threshold or abs(dot_left) > direction_threshold:
                    locomotion_pos.x = bipcom_pos.x
                    x_updated = True
                
                # Y축 업데이트 (앞뒤 움직임)
                if abs(dot_forward) > direction_threshold or abs(dot_backward) > direction_threshold:
                    locomotion_pos.y = bipcom_pos.y
                    y_updated = True
                
                # 방향 변경 시 추가 처리
                if direction_changed:
                    # 방향이 바뀐 경우: 이전 방향의 위치를 저장
                    direction_change_positions[prev_direction] = rt.Point3(prev_locomotion_pos.x, prev_locomotion_pos.y, prev_locomotion_pos.z)
                    
                    # 새로운 방향이 활성화되지 않은 축은 이전 값 유지
                    if not x_updated and prev_direction in ["right", "left"]:
                        # X축이 업데이트되지 않았고 이전이 좌우 방향이었다면 X값 유지
                        locomotion_pos.x = prev_locomotion_pos.x
                    
                    if not y_updated and prev_direction in ["forward", "backward"]:
                        # Y축이 업데이트되지 않았고 이전이 앞뒤 방향이었다면 Y값 유지
                        locomotion_pos.y = prev_locomotion_pos.y
            
            converted_data[frame] = {
                'position': locomotion_pos,
                'rotation': frame_data['rotation'],
                'bipComPos': bipcom_pos,
                'bipComRot': bipcom_rot,
                'direction': direction,
                'direction_changed': direction != prev_direction and prev_direction != "",
                'active_directions': [d[0] for d in active_directions],  # 활성화된 모든 방향들
                'dot_values': {
                    'forward': dot_forward,
                    'backward': dot_backward,
                    'right': dot_right,
                    'left': dot_left
                },
                'direction_threshold': direction_threshold,
                'velocity': rt.Point3(0, 0, 0),
                'acceleration': rt.Point3(0, 0, 0),
                'acceleration_magnitude': 0.0,
                'needs_keyframe': False
            }
            
            # 이전 방향 업데이트
            prev_direction = direction
        
        # 속도 계산
        for i in range(len(frame_list)):
            current_frame = frame_list[i]
            current_data = converted_data[current_frame]
            
            # 속도 계산 (현재 프레임과 다음 프레임 사이)
            if i < len(frame_list) - 1:
                next_frame = frame_list[i + 1]
                next_data = converted_data[next_frame]
                
                frame_diff = next_frame - current_frame
                pos_diff = next_data['position'] - current_data['position']
                
                if frame_diff > 0:
                    velocity = pos_diff / frame_diff
                    current_data['velocity'] = velocity
          # 가속도 계산 및 키프레임 필요성 판단
        for i in range(1, len(frame_list) - 1):  # 첫 번째와 마지막 프레임 제외
            current_frame = frame_list[i]
            prev_frame = frame_list[i - 1]
            next_frame = frame_list[i + 1]
            
            current_data = converted_data[current_frame]
            prev_data = converted_data[prev_frame]
            next_data = converted_data[next_frame]
            
            # 가속도 계산 (속도의 변화율)
            frame_diff_prev = current_frame - prev_frame
            frame_diff_next = next_frame - current_frame
            
            if frame_diff_prev > 0 and frame_diff_next > 0:
                # 평균 프레임 차이로 정규화
                avg_frame_diff = (frame_diff_prev + frame_diff_next) / 2.0
                
                velocity_diff = current_data['velocity'] - prev_data['velocity']
                acceleration = velocity_diff / avg_frame_diff if avg_frame_diff > 0 else rt.Point3(0, 0, 0)
                
                current_data['acceleration'] = acceleration
                current_data['acceleration_magnitude'] = rt.length(acceleration)
                
                # 가속도 변화가 임계값을 넘거나 방향이 바뀌면 키프레임 필요
                if current_data['acceleration_magnitude'] > acceleration_threshold or current_data.get('direction_changed', False):
                    current_data['needs_keyframe'] = True
        
        # 첫 번째와 마지막 프레임은 항상 키프레임 필요
        if frame_list:
            converted_data[frame_list[0]]['needs_keyframe'] = True
            converted_data[frame_list[-1]]['needs_keyframe'] = True
        
        return converted_data

    def apply_keyframes_locomotion_mode(self, keyframe_data):
        """
        로코모션 모드로 키프레임을 적용하는 함수 (needs_keyframe이 True인 프레임에만 키 생성)
        
        Args:
            keyframe_data (dict): 키프레임 데이터 딕셔너리 (convert_keyframe_data_for_locomotion에서 변환된 데이터)
        
        Returns:
            bool: 성공 여부
        """
        if not keyframe_data or not self.rootNode:
            return False
        
        node_name = self.rootNode.name
        frame_list = sorted(keyframe_data.keys())
        
        if len(frame_list) < 1:
            return False
        
        # 디버깅: keyframe_data 내용 출력
        print("=== Locomotion Keyframe Data Debug ===")
        print(f"Total frames: {len(frame_list)}")
        print(f"Frame range: {min(frame_list)} - {max(frame_list)}")
        
        keyframe_needed_count = 0
        for frame, data in keyframe_data.items():
            needs_key = data.get('needs_keyframe', False)
            if needs_key:
                keyframe_needed_count += 1
            
            print(f"Frame {frame}:")
            print(f"  Position: [{data['position'].x:.3f}, {data['position'].y:.3f}, {data['position'].z:.3f}]")
            print(f"  Direction: {data.get('direction', 'unknown')}")
            print(f"  Velocity: [{data['velocity'].x:.3f}, {data['velocity'].y:.3f}, {data['velocity'].z:.3f}]")
            print(f"  Acceleration: [{data['acceleration'].x:.3f}, {data['acceleration'].y:.3f}, {data['acceleration'].z:.3f}]")
            print(f"  Acceleration Magnitude: {data.get('acceleration_magnitude', 0.0):.3f}")
            print(f"  Needs Keyframe: {needs_key}")
            if 'dot_values' in data:
                dots = data['dot_values']
                print(f"  Dot Products - Forward: {dots['forward']:.3f}, Backward: {dots['backward']:.3f}, Right: {dots['right']:.3f}, Left: {dots['left']:.3f}")
            print()
        
        print(f"Frames needing keyframes: {keyframe_needed_count}/{len(frame_list)}")
        print("=" * 40)
        
        # 모든 프레임 데이터를 MAXScript 배열로 준비
        pos_list = [f'[{data["position"].x}, {data["position"].y}, {data["position"].z}]' for data in keyframe_data.values()]
        rot_list = [f'(eulerAngles {data["rotation"].x} {data["rotation"].y} {data["rotation"].z})' for data in keyframe_data.values()]
        needs_keyframe_list = [str(data.get("needs_keyframe", False)).lower() for data in keyframe_data.values()]
        
        maxScriptFrameArray = f"#({', '.join(map(str, frame_list))})"
        maxScriptPosArray = f"#({', '.join(pos_list)})"
        maxScriptRotArray = f"#({', '.join(rot_list)})"
        maxScriptNeedsKeyframeArray = f"#({', '.join(needs_keyframe_list)})"
        
        maxscriptCode = f"""
        (
            local frameArray = {maxScriptFrameArray}
            local posArray = {maxScriptPosArray}
            local rotArray = {maxScriptRotArray}
            local needsKeyframeArray = {maxScriptNeedsKeyframeArray}
            
            animate on(
                for i = 1 to frameArray.count do
                (
                    -- needs_keyframe이 true인 경우에만 키프레임 생성
                    if needsKeyframeArray[i] == true then
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
        )
        """
        
        try:
            # 키프레임이 생성될 범위 계산
            start_frame = min(frame_list)
            end_frame = max(frame_list)
            
            # 첫 번째 실행 (3DS Max 버그 우회용)
            rt.execute(maxscriptCode)
            
            # 생성된 키들을 프레임 범위에서만 삭제
            self.anim.delete_keys_in_range(self.rootNode, start_frame, end_frame)
            
            # 두 번째 실행 (실제 키 생성)
            rt.execute(maxscriptCode)
            
            # needs_keyframe이 True인 프레임 개수 계산
            keyframe_count = sum(1 for data in keyframe_data.values() if data.get('needs_keyframe', False))
            keyframe_frames = [frame for frame, data in keyframe_data.items() if data.get('needs_keyframe', False)]
            
            print(f"Applied {keyframe_count} keyframes for locomotion mode at frames: {keyframe_frames}")
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
    
    def get_bipcom_position(self, frame_time):
        """
        특정 프레임에서 bipCom의 위치를 가져오는 헬퍼 함수
        
        Args:
            frame_time (int): 프레임 시간
        
        Returns:
            Point3: bipCom의 위치
        """
        if hasattr(self, 'pelvis') and self.pelvis and rt.isValidNode(self.pelvis):
            with attime(frame_time):
                return self.pelvis.transform.position
        return rt.Point3(0, 0, 0)