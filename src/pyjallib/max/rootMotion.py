#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Root Motion 모듈
3DS Max에서 Root Motion을 처리하는 기능을 제공
"""

from pymxs import runtime as rt
from pymxs import attime

from .name import Name
from .anim import Anim
from .helper import Helper
from .constraint import Constraint
from .bip import Bip

class RootMotion:
    """Biped 애니메이션에서 루트 모션을 추출해 루트 본에 키프레임으로 적용하는 클래스. 바운딩 박스 기반 위치 계산, 로코모션 모드 변환, 키프레임 적용 기능을 제공한다."""

    def __init__(self, nameService=None, animService=None, constraintService=None, helperService=None, bipService=None):
        """클래스를 초기화한다.

        Args:
            nameService (Name | None): 이름 처리 서비스. None이면 새로 생성한다.
            animService (Anim | None): 애니메이션 서비스. None이면 새로 생성한다.
            constraintService (Constraint | None): 제약 서비스. None이면 새로 생성한다.
            helperService (Helper | None): 헬퍼 객체 서비스. None이면 새로 생성한다.
            bipService (Bip | None): Biped 서비스. None이면 새로 생성한다.
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
        self.accelerationThreshold = 3.0  # 가속도 변화 임계값 (기본값: convert_keyframe_data_for_locomotion의 기본값)
        self.keySmoothness = 10.0 # 키 부드러움 (기본값: apply_keyframes_locomotion_mode의 기본값)
        self.directionThreshold = 0.005 # 방향 감지 임계값 (기본값: convert_keyframe_data_for_locomotion의 기본값)
        self.accelerationFrameRange = 1 # 가속도 계산 프레임 범위 (기본값: convert_keyframe_data_for_locomotion의 기본값)

    def is_foot_planted(self, footBone, frameTime, floorThreshold=2.0, fps=60.0, footSpeedThreshold=0.1):
        """지정 프레임에서 발이 바닥에 고정되어 있는지 판정한다.

        발 높이가 바닥 임계값 이하이고 직전 프레임 대비 XY 이동량이 속도 임계값 이하이면 고정으로 본다.

        Args:
            footBone (rt.Node): 발 본 객체
            frameTime (int): 판정할 프레임
            floorThreshold (float): 바닥 접촉 임계값
            fps (float): 초당 프레임 수
            footSpeedThreshold (float): 발 속도 임계값

        Returns:
            bool: 발이 바닥에 고정되어 있으면 True
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
        """Biped 바운딩 박스를 기반으로 루트 모션 키프레임 데이터를 생성한다 (키 적용은 하지 않음).

        시작 프레임에서 루트와 바운딩 박스 중심의 상대 오프셋을 구한 뒤, 양발이 모두 바닥에
        고정되지 않은 프레임마다 새 루트 위치·회전을 계산한다. 양발이 모두 고정된 프레임은 제외된다.

        Args:
            bipCom (rt.Node): Biped COM 객체
            rootBone (rt.Node): 루트 본 객체
            startFrame (int): 시작 프레임
            endFrame (int): 끝 프레임
            floorThreshold (float): 바닥 접촉 임계값
            footSpeedThreshold (float): 발 속도 임계값
            keepZAtZero (bool): True이면 루트 Z 위치를 0으로 유지한다.
            followZRotation (bool): True이면 COM의 Z축 회전을 따라간다.

        Returns:
            dict[int, dict] | None: 프레임 번호를 키로 하는 키프레임 데이터. 입력이 유효하지
                않거나 발 본·바운딩 박스를 구할 수 없으면 None. 각 프레임 값의 키:
                - position (rt.Point3): 계산된 루트 위치
                - rotation (rt.EulerAngles): 계산된 루트 회전
                - bipComPos (rt.Point3): 해당 프레임의 COM 위치
                - bipComRot (rt.Quat): 해당 프레임의 COM 회전
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
    
    def convert_keyframe_data_for_locomotion(self, bipCom, keyframe_data, acceleration_threshold=3.0, direction_threshold=0.005, acceleration_frame_range=1, followZRotation=False):
        """키프레임 데이터를 로코모션 모드에 맞게 변환한다.

        COM 이동 방향을 전후좌우로 분류해 활성 방향 축의 위치만 갱신하고, 속도·가속도를
        계산하여 키프레임이 필요한 프레임을 표시한다. 첫/마지막 프레임은 항상 키프레임 대상이 된다.

        Args:
            bipCom (rt.Node): Biped COM 객체
            keyframe_data (dict[int, dict]): create_root_motion_from_bounding_box가 생성한 키프레임 데이터
            acceleration_threshold (float): 키프레임 필요 판단에 쓰는 가속도 변화 임계값
            direction_threshold (float): 방향 감지 임계값 (0.0~1.0). 활성 판정에는 (1.0 - 값)을 사용한다.
            acceleration_frame_range (int): 속도·가속도 계산에 사용할 프레임 범위
            followZRotation (bool): True이면 이동 방향에 따라 Z축 회전을 재계산한다.

        Returns:
            dict[int, dict]: 프레임 번호를 키로 하는 변환된 키프레임 데이터. 입력이 유효하지
                않거나 프레임 수가 (2 * 프레임 범위 + 1)보다 적으면 빈 dict. 각 프레임 값의 키:
                - position (rt.Point3): 로코모션 규칙이 적용된 루트 위치
                - rotation (rt.EulerAngles): 최종 회전
                - bipComPos (rt.Point3): COM 위치
                - bipComRot (rt.Quat): COM 회전
                - direction (str): 주 이동 방향 ("forward"/"backward"/"left"/"right"/"Transition")
                - direction_changed (bool): 이전 프레임 대비 방향 변경 여부
                - active_directions (list[str]): 임계값을 넘은 활성 방향 목록 (Transition이면 빈 리스트)
                - dot_values (dict): {forward: float, backward: float, right: float, left: float} 방향별 내적 값
                - direction_threshold (float): 입력한 방향 감지 임계값
                - strict_activation_threshold (float): 실제 활성 판정에 사용한 임계값
                - velocity (rt.Point3): 계산된 속도
                - acceleration (rt.Point3): 계산된 가속도
                - acceleration_magnitude (float): 가속도 크기
                - needs_keyframe (bool): 키프레임 생성 필요 여부
        """
        if not keyframe_data or not rt.isValidNode(bipCom):
            return {}
        
        # Update instance attributes with provided parameters
        self.accelerationThreshold = acceleration_threshold
        self.directionThreshold = direction_threshold
        self.accelerationFrameRange = acceleration_frame_range
        self.followZRotation = followZRotation
        
        converted_data = {}
        frame_list = sorted(keyframe_data.keys())
        
        min_frames_needed = 2 * self.accelerationFrameRange + 1 # Use instance attribute
        if len(frame_list) < min_frames_needed:
            print(f"Warning: Need at least {min_frames_needed} frames for acceleration calculation with range {self.accelerationFrameRange}")
            # Return empty or partially processed if preferred, for now returning empty
            return {}
        
        # self.accelerationThreshold is already set above
        
        first_frame = frame_list[0]
        first_bipcom_pos = keyframe_data[first_frame]['bipComPos']
        
        world_forward = rt.Point3(0, -1, 0)
        world_backward = rt.Point3(0, 1, 0)
        world_right = rt.Point3(-1, 0, 0)
        world_left = rt.Point3(1, 0, 0)
        
        prev_primary_direction = ""
        strict_activation_thresh = 1.0 - self.directionThreshold # Use instance attribute

        for i, frame in enumerate(frame_list):
            frame_data = keyframe_data[frame]
            bipcom_pos = frame_data['bipComPos']
            bipcom_rot = frame_data['bipComRot']
            
            movement_direction_vec = rt.Point3(0, 0, 0)
            movement_magnitude = 0.0
            
            if i > 0:
                prev_frame_data = keyframe_data[frame_list[i-1]]
                movement_vector = bipcom_pos - prev_frame_data['bipComPos']
                movement_magnitude = rt.length(movement_vector)
                if movement_magnitude > 0.001:
                    movement_direction_vec = rt.normalize(movement_vector)
            elif i < len(frame_list) - 1: # First frame, use next frame for initial direction
                next_frame_data = keyframe_data[frame_list[i+1]]
                movement_vector = next_frame_data['bipComPos'] - bipcom_pos
                movement_magnitude = rt.length(movement_vector)
                if movement_magnitude > 0.001:
                    movement_direction_vec = rt.normalize(movement_vector)

            dot_forward = 0.0
            dot_backward = 0.0
            dot_right = 0.0
            dot_left = 0.0

            if movement_magnitude > 0.001:
                dot_forward = rt.dot(movement_direction_vec, world_forward)
                dot_backward = rt.dot(movement_direction_vec, world_backward)
                dot_right = rt.dot(movement_direction_vec, world_right)
                dot_left = rt.dot(movement_direction_vec, world_left)

            # Determine strictly active directions
            strictly_active_directions = []
            if dot_forward >= strict_activation_thresh:
                strictly_active_directions.append(("forward", dot_forward))
            if dot_backward >= strict_activation_thresh:
                strictly_active_directions.append(("backward", dot_backward))
            if dot_right >= strict_activation_thresh:
                strictly_active_directions.append(("right", dot_right))
            if dot_left >= strict_activation_thresh:
                strictly_active_directions.append(("left", dot_left))

            current_primary_direction = ""
            current_active_directions_list = []
            is_transition_frame = not strictly_active_directions

            if is_transition_frame:
                current_primary_direction = "Transition"
            else:
                strictly_active_directions.sort(key=lambda x: x[1], reverse=True) # Sort by dot product value
                current_primary_direction = strictly_active_directions[0][0]
                current_active_directions_list = [d[0] for d in strictly_active_directions]
            
            # Calculate locomotion_pos
            locomotion_pos_z = frame_data['position'].z # Z is always from original calculation or fixed
            if i == 0:
                locomotion_pos = rt.Point3(first_bipcom_pos.x, first_bipcom_pos.y, locomotion_pos_z)
            else:
                prev_locomotion_pos = converted_data[frame_list[i-1]]['position']
                locomotion_pos = rt.Point3(prev_locomotion_pos.x, prev_locomotion_pos.y, locomotion_pos_z)

                if is_transition_frame:
                    locomotion_pos.x = bipcom_pos.x
                    locomotion_pos.y = bipcom_pos.y
                else:
                    # Update Y if forward or backward is strictly active
                    if "forward" in current_active_directions_list or "backward" in current_active_directions_list:
                        locomotion_pos.y = bipcom_pos.y
                    
                    # Update X if right or left is strictly active
                    if "right" in current_active_directions_list or "left" in current_active_directions_list:
                        locomotion_pos.x = bipcom_pos.x
            
            # Direction changed flag considers "Transition" as a distinct direction state
            direction_changed_flag = (current_primary_direction != prev_primary_direction and prev_primary_direction != "")

            # Determine final rotation for the frame
            final_frame_rotation = frame_data['rotation'] # Default to original rotation

            if self.followZRotation: # Use instance attribute
                if current_primary_direction == "Transition":
                    transition_z_rotation = 0.0
                    if dot_forward > 0:
                        transition_z_rotation += (-90.0 * dot_forward)
                    if dot_backward > 0:
                        transition_z_rotation += (90.0 * dot_backward)
                    if dot_left > 0: # world_left (1,0,0) corresponds to 180 deg Z rotation
                        transition_z_rotation += (0.0 * dot_left)
                    if dot_right > 0: # world_right (-1,0,0) corresponds to -180 deg Z rotation
                        transition_z_rotation += (-180.0 * dot_right)
                    
                    # Clamp the transition_z_rotation
                    if transition_z_rotation < -180.0:
                        transition_z_rotation = -180.0
                    elif transition_z_rotation > 180.0:
                        transition_z_rotation = 180.0
                        
                    final_frame_rotation = rt.EulerAngles(0, 0, transition_z_rotation)
                elif current_primary_direction == "forward":
                    final_frame_rotation = rt.EulerAngles(0, 0, -90)
                elif current_primary_direction == "backward":
                    final_frame_rotation = rt.EulerAngles(0, 0, 90)
                elif current_primary_direction == "left":
                    final_frame_rotation = rt.EulerAngles(0, 0, 0)
                elif current_primary_direction == "right":
                    final_frame_rotation = rt.EulerAngles(0, 0, -180)
                # If followZRotation is true but direction is not one of the above (e.g. empty, though unlikely),
                # it will keep the original frame_data['rotation']. This is a safe fallback.

            converted_data[frame] = {
                'position': locomotion_pos,
                'rotation': final_frame_rotation, # Apply the calculated rotation
                'bipComPos': bipcom_pos,
                'bipComRot': bipcom_rot,
                'direction': current_primary_direction,
                'direction_changed': direction_changed_flag,
                'active_directions': current_active_directions_list, # Will be empty for "Transition"
                'dot_values': {
                    'forward': dot_forward,
                    'backward': dot_backward,
                    'right': dot_right,
                    'left': dot_left
                },
                'direction_threshold': direction_threshold, # Store original for reference
                'strict_activation_threshold': strict_activation_thresh,
                'velocity': rt.Point3(0, 0, 0),
                'acceleration': rt.Point3(0, 0, 0),
                'acceleration_magnitude': 0.0,
                'needs_keyframe': False 
            }
            
            prev_primary_direction = current_primary_direction
        
        # 속도 계산 (지정된 프레임 범위를 사용)
        for i in range(len(frame_list)):
            current_frame = frame_list[i]
            current_data = converted_data[current_frame]
            
            prev_index = max(0, i - self.accelerationFrameRange) # Use instance attribute
            next_index = min(len(frame_list) - 1, i + self.accelerationFrameRange) # Use instance attribute
            
            if prev_index != i and next_index != i:
                prev_frame_for_vel = frame_list[prev_index]
                next_frame_for_vel = frame_list[next_index]
                prev_data_for_vel = converted_data[prev_frame_for_vel]
                next_data_for_vel = converted_data[next_frame_for_vel]
                
                frame_diff = float(next_frame_for_vel - prev_frame_for_vel)
                pos_diff = next_data_for_vel['position'] - prev_data_for_vel['position']
                
                if frame_diff > 0:
                    current_data['velocity'] = pos_diff / frame_diff
            elif next_index != i: # Start of range
                next_frame_for_vel = frame_list[next_index]
                next_data_for_vel = converted_data[next_frame_for_vel]
                frame_diff = float(next_frame_for_vel - current_frame)
                pos_diff = next_data_for_vel['position'] - current_data['position']
                if frame_diff > 0:
                    current_data['velocity'] = pos_diff / frame_diff
            elif prev_index != i: # End of range
                prev_frame_for_vel = frame_list[prev_index]
                prev_data_for_vel = converted_data[prev_frame_for_vel]
                frame_diff = float(current_frame - prev_frame_for_vel)
                pos_diff = current_data['position'] - prev_data_for_vel['position']
                if frame_diff > 0:
                    current_data['velocity'] = pos_diff / frame_diff
        
        # 가속도 계산 및 키프레임 필요성 판단
        for i in range(len(frame_list)):
            current_frame = frame_list[i]
            current_data = converted_data[current_frame]
            
            prev_index = max(0, i - self.accelerationFrameRange) # Use instance attribute
            # next_index = min(len(frame_list) - 1, i + acceleration_frame_range) # Not used in this specific accel calc

            if prev_index < i : # Check if there is a distinct previous frame for accel calc
                prev_frame_for_accel = frame_list[prev_index]
                prev_data_for_accel = converted_data[prev_frame_for_accel]
                
                frame_span_from_prev_sample = float(current_frame - prev_frame_for_accel)
                if frame_span_from_prev_sample > 0:
                    velocity_diff = current_data['velocity'] - prev_data_for_accel['velocity']
                    acceleration = velocity_diff / frame_span_from_prev_sample
                    current_data['acceleration'] = acceleration
                    current_data['acceleration_magnitude'] = rt.length(acceleration)
            
            # 키프레임 필요성 판단 로직 수정
            if current_data['direction'] == "Transition":
                if current_data['acceleration_magnitude'] > (self.accelerationThreshold / 2.0):
                    current_data['needs_keyframe'] = True
            else: # "forward", "backward", "left", "right"
                if current_data['acceleration_magnitude'] > self.accelerationThreshold or current_data.get('direction_changed', False):
                    current_data['needs_keyframe'] = True
        
        if frame_list:
            if converted_data: # Ensure converted_data is not empty
                 if frame_list[0] in converted_data:
                    converted_data[frame_list[0]]['needs_keyframe'] = True
                 if len(frame_list) > 1 and frame_list[-1] in converted_data: # Ensure there's more than one frame
                    converted_data[frame_list[-1]]['needs_keyframe'] = True
        
        return converted_data

    def apply_keyframes_locomotion_mode(self, keyframeData, keySmoothness=10.0):
        """로코모션 모드로 키프레임을 적용한다 (needs_keyframe이 True인 프레임에만 키 생성).

        MAXScript를 두 번 실행(3ds Max 버그 우회)하며 실행 사이에 구간 내 기존 키를 삭제하고,
        마지막에 reduceKeys로 키를 정리한다.

        Args:
            keyframeData (dict[int, dict]): convert_keyframe_data_for_locomotion이 변환한 키프레임 데이터
            keySmoothness (float): reduceKeys에 사용할 키 감소 임계값

        Returns:
            bool: 적용 성공 여부. 데이터가 없거나 루트 노드가 설정되지 않았거나 예외가 발생하면 False
        """
        if not keyframeData or not self.rootNode:
            return False
        
        node_name = self.rootNode.name
        frame_list = sorted(keyframeData.keys())
        
        if len(frame_list) < 1:
            return False
        
        # 모든 프레임 데이터를 MAXScript 배열로 준비
        pos_list = [f'[{data["position"].x}, {data["position"].y}, {data["position"].z}]' for data in keyframeData.values()]
        rot_list = [f'(eulerAngles {data["rotation"].x} {data["rotation"].y} {data["rotation"].z})' for data in keyframeData.values()]
        needs_keyframe_list = [str(data.get("needs_keyframe", False)).lower() for data in keyframeData.values()]
        
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
            
            disableSceneRedraw()
            
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
            
            reduceKeys $'{node_name}'.position.controller {keySmoothness} 1f
            reduceKeys $'{node_name}'.rotation.controller {keySmoothness} 1f
            reduceKeys $'{node_name}'.scale.controller {keySmoothness} 1f
            
            enableSceneRedraw()
        )
        """
        
        print(maxscriptCode)
        
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
            
            return True
            
        except Exception as e:
            print(f"Error applying keyframes in locomotion mode: {e}")
            return False

    def apply_keyframes_normal_mode(self, keyframeData, keySmoothness=10.0):
        """일반 모드로 키프레임을 적용한다 (모든 프레임에 키 생성).

        MAXScript를 두 번 실행(3ds Max 버그 우회)하며 실행 사이에 구간 내 기존 키를 삭제하고,
        마지막에 reduceKeys로 키를 정리한다.

        Args:
            keyframeData (dict[int, dict]): 키프레임 데이터 딕셔너리 (position·rotation 키 필요)
            keySmoothness (float): reduceKeys에 사용할 키 감소 임계값

        Returns:
            bool: 적용 성공 여부. 데이터가 없거나 루트 노드가 설정되지 않았거나 예외가 발생하면 False
        """
        if not keyframeData or not self.rootNode:
            return False
        
        node_name = self.rootNode.name
        frame_list = list(keyframeData.keys())
        pos_list = [f'[{data["position"].x}, {data["position"].y}, {data["position"].z}]' for data in keyframeData.values()]
        rot_list = [f'(eulerAngles {data["rotation"].x} {data["rotation"].y} {data["rotation"].z})' for data in keyframeData.values()]
        
        maxScriptFrameArray = f"#({', '.join(map(str, frame_list))})"
        maxScriptPosArray = f"#({', '.join(pos_list)})"
        maxScriptRotArray = f"#({', '.join(rot_list)})"
        
        maxscriptCode = f"""
        (
            local frameArray = {maxScriptFrameArray}
            local posArray = {maxScriptPosArray}
            local rotArray = {maxScriptRotArray}
            
            disableSceneRedraw()
            
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
            
            reduceKeys $'{node_name}'.position.controller {keySmoothness} 1f
            reduceKeys $'{node_name}'.rotation.controller {keySmoothness} 1f
            reduceKeys $'{node_name}'.scale.controller {keySmoothness} 1f
            
            enableSceneRedraw()
        )
        """
        print(maxscriptCode)
        
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
        """특정 프레임에서 펠비스 노드의 월드 위치를 반환한다.

        Args:
            frame_time (int): 프레임 시간

        Returns:
            rt.Point3: 펠비스의 월드 위치. 펠비스가 설정되지 않았거나 유효하지 않으면 (0, 0, 0)
        """
        if hasattr(self, 'pelvis') and self.pelvis and rt.isValidNode(self.pelvis):
            with attime(frame_time):
                return self.pelvis.transform.position
        return rt.Point3(0, 0, 0)