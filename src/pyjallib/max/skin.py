#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
스킨 모듈 - 3ds Max용 고급 스킨 관련 기능 제공
원본 MAXScript의 skin2.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

import os
from enum import IntEnum
import textwrap
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from pymxs import runtime as rt

class VertexMode(IntEnum):
    """스킨 스무딩 시 버텍스 그룹핑 방식을 지정하는 열거형."""
    Edges = 1
    Attach = 2
    All = 3
    Stiff = 4


def merge_vertex_weights(
    inEntries: Iterable[Tuple[int, float]],
    inBoneIdRemap: Dict[int, int],
) -> Tuple[List[int], List[float], bool]:
    """버텍스 한 개의 (본 ID, 가중치) 항목을 remap 규칙으로 합산한다 (순수 함수).

    ``inBoneIdRemap``의 키에 해당하는 본 ID는 값(대상 본 ID)으로 바꾼 뒤 같은 ID끼리
    더한다. 여러 원본 본이 한 대상을 가리키면(다대일) 그 대상에 전부 합산된다. 결과
    순서는 remap 적용 후의 ID가 처음 등장한 순서다. pymxs를 호출하지 않으므로 다대일
    합산 규칙을 콘솔(Type A)에서 고정할 수 있다.

    Args:
        inEntries: ``[(boneId, weight), ...]`` - 한 버텍스의 가중치 항목
        inBoneIdRemap: ``{원본 본 ID: 대상 본 ID}``

    Returns:
        ``(ids, weights, touched)``. ``touched``는 remap된 항목이 하나라도 있었는지

    Raises:
        ValueError: remap 대상 본 ID가 None인 항목이 있는 경우(이전 대상이 없는 본)
    """
    merged: Dict[int, float] = {}
    touched = False
    for boneId, weight in inEntries:
        if boneId in inBoneIdRemap:
            targetId = inBoneIdRemap[boneId]
            if targetId is None:
                raise ValueError(f"본 ID {boneId}의 이전 대상이 없습니다.")
            boneId = targetId
            touched = True
        merged[boneId] = merged.get(boneId, 0.0) + float(weight)
    ids = list(merged.keys())
    return ids, [merged[i] for i in ids], touched


def expected_weights_by_handle(
    inWeightsByHandle: Dict[int, Dict[int, float]],
    inTransferByHandle: Dict[int, int],
) -> Dict[int, Dict[int, float]]:
    """이전 전 스냅샷에 remap을 적용한 **기대 가중치**를 만든다 (순수 함수).

    키가 본 ID가 아니라 **노드 핸들**이다. ``addBone``/``removeBone``은 본 ID를 밀 수
    있으므로(빈 슬롯 재사용·제거 후 압축) ID로 전후를 비교하면 서로 다른 본을 견주게
    된다. 핸들은 노드의 수명 동안 불변이라 유일하게 안전한 기준이다.

    Args:
        inWeightsByHandle: ``{버텍스: {본 핸들: 가중치}}`` - 절차 전 스냅샷
        inTransferByHandle: ``{원본 본 핸들: 대상 본 핸들}``

    Returns:
        ``{버텍스: {본 핸들: 기대 가중치}}``
    """
    expected: Dict[int, Dict[int, float]] = {}
    for vertIndex, byHandle in inWeightsByHandle.items():
        merged: Dict[int, float] = {}
        for handle, weight in byHandle.items():
            targetHandle = inTransferByHandle.get(handle, handle)
            merged[targetHandle] = merged.get(targetHandle, 0.0) + float(weight)
        expected[vertIndex] = merged
    return expected


def diff_weights_by_handle(
    inExpected: Dict[int, Dict[int, float]],
    inActual: Dict[int, Dict[int, float]],
    inTolerance: float = 1e-6,
) -> List[Tuple[int, int, float, float]]:
    """기대 가중치와 실제 가중치의 편차 목록을 돌려준다 (순수 함수).

    양쪽 어디에도 없는 본은 가중치 0으로 본다. 버텍스 집합이 다르면 없는 쪽을 빈
    dict로 취급해 그 차이도 편차로 잡는다.

    Args:
        inExpected: ``expected_weights_by_handle`` 결과
        inActual: 절차 후 재조회한 ``{버텍스: {본 핸들: 가중치}}``
        inTolerance: 허용 오차. 기본 1e-6 (``ReplaceVertexWeights`` 재정규화 ULP 흡수)

    Returns:
        ``[(버텍스, 본 핸들, 기대값, 실제값), ...]`` - 허용 오차를 넘은 항목만. 빈 리스트면 일치
    """
    deviations: List[Tuple[int, int, float, float]] = []
    for vertIndex in sorted(set(inExpected) | set(inActual)):
        expectedEntry = inExpected.get(vertIndex, {})
        actualEntry = inActual.get(vertIndex, {})
        for handle in sorted(set(expectedEntry) | set(actualEntry)):
            expectedWeight = float(expectedEntry.get(handle, 0.0))
            actualWeight = float(actualEntry.get(handle, 0.0))
            if abs(expectedWeight - actualWeight) > inTolerance:
                deviations.append((vertIndex, handle, expectedWeight, actualWeight))
    return deviations


def _node_handle(inNode: Any) -> int:
    """노드의 핸들(정수)을 돌려준다."""
    return int(rt.getHandleByAnim(inNode))


def _node_by_handle(inHandle: int) -> Any:
    """핸들로 노드를 되찾는다. 삭제됐으면 None."""
    node = rt.getAnimByHandle(inHandle)
    if node is None or not rt.isValidNode(node):
        return None
    return node


def _save_selection() -> List[Any]:
    """현재 선택을 라이브 뷰에서 분리한 파이썬 리스트로 보관한다."""
    return list(rt.getCurrentSelection())


def _restore_selection(inSaved: List[Any]) -> None:
    """보관한 선택을 복원한다. 삭제된 노드는 건너뛴다."""
    valid = [node for node in inSaved if rt.isValidNode(node)]
    if valid:
        rt.select(rt.Array(*valid))
    else:
        rt.clearSelection()

class Skin:
    """스킨 모디파이어의 바인딩·최적화·저장/로드·가중치 편집 기능을 제공하는 클래스. MAXScript의 ODC_Char_Skin 구조체를 Python으로 재구현하였다."""

    def __init__(self):
        """스킨 매치 리스트를 빈 상태로 초기화한다."""
        self.skin_match_list = []
    
    def has_skin(self, obj=None):
        """객체에 스킨 모디파이어가 있는지 확인한다.

        Args:
            obj (rt.Node | None): 확인할 객체. None이면 현재 선택된 첫 객체를 사용한다.

        Returns:
            bool: 스킨 모디파이어가 있으면 True. 대상 객체가 없으면 False
        """
        if obj is None:
            if len(rt.selection) > 0:
                obj = rt.selection[0]
            else:
                return False
        
        # 객체의 모든 모디파이어를 검사하여 Skin 모디파이어가 있는지 확인
        for mod in obj.modifiers:
            if rt.classOf(mod) == rt.Skin:
                return True
        return False
    
    def is_valid_bone(self, inNode):
        """노드가 스킨 본으로 사용 가능한 타입인지 확인한다.

        Args:
            inNode (rt.Node): 확인할 노드

        Returns:
            bool: GeometryClass, BoneGeometry, Helper 계열이면 True
        """
        return (rt.superClassOf(inNode) == rt.GeometryClass or 
                rt.classOf(inNode) == rt.BoneGeometry or 
                rt.superClassOf(inNode) == rt.Helper)
    
    def get_skin_mod(self, obj=None):
        """객체의 스킨 모디파이어들을 가져온다.

        Args:
            obj (rt.Node | None): 모디파이어를 가져올 객체. None이면 현재 선택된 첫 객체를 사용한다.

        Returns:
            list[rt.Skin]: 스킨 모디파이어 배열. 대상 객체가 없으면 빈 리스트
        """
        if obj is None:
            if len(rt.selection) > 0:
                obj = rt.selection[0]
            else:
                return []
        
        return [mod for mod in obj.modifiers if rt.classOf(mod) == rt.Skin]
    
    def bind_skin(self, obj, bone_array):
        """객체에 스킨 모디파이어를 추가하고 본들을 바인딩한다.

        Args:
            obj (rt.Node): 바인딩할 지오메트리 객체
            bone_array (list[rt.Node]): 바인딩할 본 배열

        Returns:
            bool: 성공 여부. 객체가 None이거나 본이 없거나 지오메트리 객체가 아니면 False
        """
        if obj is None or len(bone_array) < 1:
            print("Select at least 1 influence and an object.")
            return False
        
        # Switch to modify mode
        rt.execute("max modify mode")
        
        # Check if the object is valid for skinning
        if rt.superClassOf(obj) != rt.GeometryClass:
            print(f"{obj.name} must be 'Edit_Mesh' or 'Edit_Poly'.")
            return False
        
        # Add skin modifier
        objmod = rt.Skin()
        rt.addModifier(obj, objmod)
        rt.select(obj)
        
        # Add bones to skin modifier
        wgt = 1.0
        for each in bone_array:
            rt.skinOps.addBone(objmod, each, wgt)
        
        # Set skin modifier options
        objmod.filter_vertices = True
        objmod.filter_envelopes = False
        objmod.filter_cross_sections = True
        objmod.enableDQ = False
        objmod.bone_Limit = 8
        objmod.colorAllWeights = True
        objmod.showNoEnvelopes = True
        
        return True
    
    def optimize_skin(self, skin_mod, bone_limit=8, skin_tolerance=0.01):
        """스킨 모디파이어에서 제로 가중치와 미사용 본을 제거해 최적화한다.

        Args:
            skin_mod (rt.Skin): 최적화할 스킨 모디파이어
            bone_limit (int): 버텍스당 본 제한 수
            skin_tolerance (float): 제로 가중치 제거 허용 오차
        """
        # 스킨 모디파이어 설정
        skin_mod.enableDQ = False
        skin_mod.bone_Limit = bone_limit
        skin_mod.clearZeroLimit = skin_tolerance
        rt.skinOps.RemoveZeroWeights(skin_mod)
        skin_mod.clearZeroLimit = 0
        
        skin_mod.filter_vertices = True
        skin_mod.showNoEnvelopes = True
        
        rt.skinOps.closeWeightTable(skin_mod)
        rt.skinOps.closeWeightTool(skin_mod)
        
        if rt.skinOps.getNumberBones(skin_mod) > 1:
            list_of_bones = [i for i in range(1, rt.skinOps.GetNumberBones(skin_mod) + 1)]
            
            for v in range(1, rt.skinOps.GetNumberVertices(skin_mod) + 1):
                for b in range(1, rt.skinOps.GetVertexWeightCount(skin_mod, v) + 1):
                    bone_id = rt.skinOps.GetVertexWeightBoneID(skin_mod, v, b)
                    if bone_id in list_of_bones:
                        list_of_bones.remove(bone_id)
            
            # 역순으로 본 제거 (인덱스 변경 문제 방지)
            for i in range(len(list_of_bones) - 1, -1, -1):
                bone_id = list_of_bones[i]
                rt.skinOps.SelectBone(skin_mod, bone_id)
                rt.skinOps.removebone(skin_mod, bone_id)
                
            if rt.skinOps.getNumberBones(skin_mod) > 1:
                rt.skinOps.SelectBone(skin_mod, 1)
                
            skin_mod_obj = rt.getCurrentSelection()[0]
                
            print(f"Obj:{skin_mod_obj.name} Removed:{len(list_of_bones)} Left:{rt.skinOps.GetNumberBones(skin_mod)}")
    
    def optimize_skin_process(self, objs=None, optim_all_skin_mod=False, bone_limit=8, skin_tolerance=0.01):
        """여러 객체의 스킨 모디파이어를 순회하며 최적화한다.

        Args:
            objs (list[rt.Node] | None): 최적화할 객체 배열. None이면 현재 선택된 객체들을 사용한다.
            optim_all_skin_mod (bool): True면 각 객체의 모든 스킨 모디파이어를, False면 첫 번째만 최적화한다.
            bone_limit (int): 버텍스당 본 제한 수
            skin_tolerance (float): 제로 가중치 제거 허용 오차
        """
        if objs is None:
            objs = rt.selection
            
        if not objs:
            return
            
        rt.execute("max modify mode")
        
        for obj in objs:
            if self.has_skin(obj):
                mod_id = [i+1 for i in range(len(obj.modifiers)) if rt.classOf(obj.modifiers[i]) == rt.Skin]
                
                if not optim_all_skin_mod:
                    mod_id = [mod_id[0]]
                    
                for each in mod_id:
                    rt.modPanel.setCurrentObject(obj.modifiers[each-1])
                    self.optimize_skin(obj.modifiers[each-1], bone_limit=bone_limit, skin_tolerance=skin_tolerance)
        
        rt.select(objs)
    
    def load_skin(self, obj, file_path, load_bind_pose=False, keep_skin=False, insert_before=None):
        """스킨 데이터 파일을 읽어 객체에 새 스킨 모디파이어를 생성하고 가중치를 적용한다.

        파일에 기록된 본이 씬에 없으면 같은 이름의 Dummy를 생성해 대체한다.

        Args:
            obj (rt.Node): 스킨을 적용할 객체
            file_path (str): 스킨 데이터 파일 경로
            load_bind_pose (bool): 바인드 포즈 파일을 함께 로드해 적용할지 여부
            keep_skin (bool): 기존 스킨 모디파이어 유지 여부. False면 기존 스킨을 모두 삭제한다.
            insert_before (int | None): 새 스킨을 넣을 위치 - ``addModifier``의 ``before:``와 같다
                (N번째(1 = 맨 위) 모디파이어 아래, 0 = 맨 위). None이면 ``1 if keep_skin else 0``.
                기존 스킨을 보존하면서 그 위에 새 스킨을 올리려면 기존 스킨 인덱스 - 1을 넘긴다.
                (보존 여부와 배치 위치가 ``keep_skin`` 하나에 묶여 있어, 보존 + 맨 위 배치를 표현할
                수 없었다 - 2026-10-08 SkinKitPy Load 결함)

        Returns:
            list[rt.Node]: 씬에 없어 Dummy로 대체된 본 배열. 파일 읽기 실패나 버텍스 수 불일치 시 빈 리스트
        """
        # 기본값 설정
        if keep_skin != True:
            keep_skin = False
            
        # 객체 선택
        rt.select(obj)
        data = []
        missing_bones = []
        
        # 파일 열기
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    data.append(line.strip())
        except:
            return []
        
        # 버텍스 수 확인
        if len(data) - 1 != obj.verts.count or obj.verts.count == 0:
            print("Bad number of verts")
            return []
        
        # 기존 스킨 모디파이어 처리
        if not keep_skin:
            for i in range(len(obj.modifiers) - 1, -1, -1):
                if rt.classOf(obj.modifiers[i]) == rt.Skin:
                    rt.deleteModifier(obj, i+1)
                    
        # 모디파이 모드 설정
        rt.setCommandPanelTaskMode(rt.Name('modify'))
        
        # 새 스킨 모디파이어 생성
        new_skin = rt.Skin()
        if insert_before is None:
            insert_before = 1 if keep_skin else 0
        rt.addModifier(obj, new_skin, before=int(insert_before))
        
        # 스킨 이름 설정
        if keep_skin:
            new_skin.name = "Skin_" + os.path.splitext(os.path.basename(file_path))[0]
            
        # 현재 모디파이어 설정
        rt.modPanel.setCurrentObject(new_skin)
        
        tempData = [rt.execute(item) for item in data]
        
        # 본 데이터 처리
        bones_data = rt.execute(tempData[0])
        hierarchy = []
        
        for i in range(len(bones_data)):
            # 본 이름으로 노드 찾기
            my_bone = [node for node in rt.objects if node.name == bones_data[i]]
            
            # 없는 본인 경우 더미 생성
            if len(my_bone) == 0:
                print(f"Missing bone: {bones_data[i]}")
                tmp = rt.Dummy(name=bones_data[i])
                my_bone = [tmp]
                missing_bones.append(tmp)
                
            # 계층 구조 확인
            if len(my_bone) > 1 and len(hierarchy) != 0:
                print(f"Multiple bones are named: {my_bone[0].name} ({len(my_bone)})")
                good_bone = None
                for o in my_bone:
                    if o in hierarchy:
                        good_bone = o
                        break
                if good_bone is not None:
                    my_bone = [good_bone]
                    
            # 사용할 본 결정
            my_bone = my_bone[0]
            
            # 계층에 추가
            if my_bone not in hierarchy:
                hierarchy.append(my_bone)
                all_nodes = list(hierarchy)
                
                for node in all_nodes:
                    # 자식 노드 추가
                    for child in node.children:
                        if child not in all_nodes:
                            all_nodes.append(child)
                    # 부모 노드 추가
                    if node.parent is not None and node.parent not in all_nodes:
                        all_nodes.append(node.parent)
                        
                    # 계층에 추가
                    for node in all_nodes:
                        if self.is_valid_bone(node) and node not in hierarchy:
                            hierarchy.append(node)
                            
            # 본 추가
            rt.skinOps.addBone(new_skin, my_bone, 1.0)
            
            # 바인드 포즈 로드
            if load_bind_pose:
                bind_pose_file = os.path.splitext(file_path)[0] + "bp"
                bind_poses = []
                
                if os.path.exists(bind_pose_file):
                    try:
                        with open(bind_pose_file, 'r') as f:
                            for line in f:
                                bind_poses.append(rt.execute(line.strip()))
                    except:
                        pass
                        
                if i < len(bind_poses) and bind_poses[i] is not None:
                    rt.skinUtils.SetBoneBindTM(obj, my_bone, bind_poses[i])
        
        # 가중치 데이터 처리
        for i in range(1, obj.verts.count + 1):
            bone_id = []
            bone_weight = []
            good_bones = []
            all_bone_weight = [0] * len(bones_data)
            
            # 가중치 합산
            for b in range(len(tempData[i][0])):
                bone_index = tempData[i][0][b]
                weight = tempData[i][1][b]
                all_bone_weight[bone_index-1] += weight
                good_bones.append(bone_index)
                
            # 가중치 적용
            for b in good_bones:
                bone_id.append(b)
                bone_weight.append(all_bone_weight[b-1])
                
            # 가중치 설정
            if len(bone_id) != 0:
                rt.skinOps.SetVertexWeights(new_skin, i, bone_id[0], 1.0)  # Max 2014 sp5 hack
                rt.skinOps.ReplaceVertexWeights(new_skin, i, bone_id, bone_weight)
                
        return missing_bones
    
    def save_skin(self, obj=None, file_path=None, save_bind_pose=False):
        """현재 모디파이 패널의 스킨 모디파이어에서 본·가중치 데이터를 파일로 저장한다.

        MAXScript의 saveskin.ms를 Python으로 변환한 함수이다.

        Args:
            obj (rt.Node | None): 저장할 객체. None이면 현재 선택된 첫 객체를 사용한다.
            file_path (str | None): 저장할 파일 경로. None이면 animations/skindata 폴더에 자동 생성한다.
            save_bind_pose (bool): 바인드 포즈를 별도 bp 파일로 함께 저장할지 여부

        Returns:
            str | None: 저장된 파일 경로. 대상 객체가 없거나 현재 모디파이어가 스킨이 아니거나 저장 실패 시 None
        """
        # 현재 선택된 객체가 없는 경우 선택된 객체 사용
        if obj is None:
            if len(rt.selection) > 0:
                obj = rt.selection[0]
            else:
                print("No object selected")
                return None
                
        # 현재 스킨 모디파이어 가져오기
        skin_mod = rt.modPanel.getCurrentObject()
        
        # 스킨 모디파이어가 아니거나 본이 없는 경우 종료
        if rt.classOf(skin_mod) != rt.Skin or rt.skinOps.GetNumberBones(skin_mod) <= 0:
            print("Current modifier is not a Skin modifier or has no bones")
            return None
            
        # 본 리스트 생성
        bones_list = []
        for i in range(1, rt.skinOps.GetNumberBones(skin_mod) + 1):
            bones_list.append(rt.skinOps.GetBoneName(skin_mod, i, 1))
        
        # 스킨 데이터 생성
        skin_data = "\"#(\\\"" + "\\\",\\\"".join(str(x) for x in bones_list) + "\\\")\"\n"
            
        # 버텍스별 가중치 데이터 수집
        for v in range(1, rt.skinOps.GetNumberVertices(skin_mod) + 1):
            bone_array = []
            weight_array = []
            
            for b in range(1, rt.skinOps.GetVertexWeightCount(skin_mod, v) + 1):
                bone_array.append(rt.skinOps.GetVertexWeightBoneID(skin_mod, v, b))
                weight_array.append(rt.skinOps.GetVertexWeight(skin_mod, v, b))
            
            stringBoneArray = "#(" + ",".join(str(x) for x in bone_array) + ")"
            stringWeightArray = "#(" + ",".join(str(w) for w in weight_array) + ")"
            skin_data += ("#(" + stringBoneArray + ", " + stringWeightArray + ")\n")
            
        # 파일 경로가 지정되지 않은 경우 자동 생성
        if file_path is None:
            # animations 폴더 내 skindata 폴더 생성
            animations_dir = rt.getDir(rt.Name('animations'))
            skin_data_dir = os.path.join(animations_dir, "skindata")
            
            if not os.path.exists(skin_data_dir):
                os.makedirs(skin_data_dir)
                
            # 파일명 생성 (객체명 + 버텍스수 + 면수)
            file_name = f"{obj.name} [v{obj.mesh.verts.count}] [t{obj.mesh.faces.count}].skin"
            file_path = os.path.join(skin_data_dir, file_name)
            
        print(f"Saving to: {file_path}")
        
        # 스킨 데이터 파일 저장
        try:
            with open(file_path, 'w') as f:
                for data in skin_data:
                    f.write(data)
        except Exception as e:
            print(f"Error saving skin data: {e}")
            return None
            
        if save_bind_pose:
            # 바인드 포즈 데이터 수집 및 저장
            bind_poses = []
            for i in range(1, rt.skinOps.GetNumberBones(skin_mod) + 1):
                bone_name = rt.skinOps.GetBoneName(skin_mod, i, 1)
                bone_node = rt.getNodeByName(bone_name)
                bind_pose = rt.skinUtils.GetBoneBindTM(obj, bone_node)
                bind_poses.append(bind_pose)
                
            # 바인드 포즈 파일 저장
            bind_pose_file = file_path[:-4] + "bp"  # .skin -> .bp
            try:
                with open(bind_pose_file, 'w') as f:
                    for pose in bind_poses:
                        f.write(str(pose) + '\n')
            except Exception as e:
                print(f"Error saving bind pose data: {e}")
            
        return file_path
    
    def get_bone_id(self, skin_mod, b_array, type=1, refresh=True):
        """스킨 모디파이어의 본들 중 주어진 배열에 포함된 본의 ID를 가져온다.

        Args:
            skin_mod (rt.Skin): 스킨 모디파이어
            b_array (list[str] | list[rt.Node]): 찾을 본 배열. type이 0이면 본 이름 배열, 1이면 본 노드 배열.
            type (int): 비교 방식. 0=본 이름으로 비교, 1=본 노드로 비교
            refresh (bool): 모디파이 패널을 해당 모디파이어로 갱신할지 여부

        Returns:
            list[int]: 일치한 본의 스킨 내 본 ID 배열 (1-based)
        """
        bone_id = []
        
        if refresh:
            rt.modPanel.setCurrentObject(skin_mod)
            
        for i in range(1, rt.skinOps.GetNumberBones(skin_mod) + 1):
            if type == 0:
                bone_name = rt.skinOps.GetBoneName(skin_mod, i, 1)
                id = b_array.index(bone_name) + 1 if bone_name in b_array else 0
            elif type == 1:
                bone = rt.getNodeByName(rt.skinOps.GetBoneName(skin_mod, i, 1))
                id = b_array.index(bone) + 1 if bone in b_array else 0
                
            if id != 0:
                bone_id.append(i)
                
        return bone_id
    
    def get_bone_id_from_name(self, in_skin_mod, bone_name):
        """본 이름으로 스킨 모디파이어 내 본 ID를 찾는다.

        Args:
            in_skin_mod (rt.Skin): 스킨 모디파이어
            bone_name (str): 찾을 본 이름

        Returns:
            int | None: 본 ID (1-based). 일치하는 본이 없으면 None
        """
        for i in range(1, rt.skinOps.GetNumberBones(in_skin_mod) + 1):
            if rt.skinOps.GetBoneName(in_skin_mod, i, 1) == bone_name:
                return i
        return None
    
    def get_bones_from_skin(self, objs, skin_mod_index):
        """객체들의 지정 인덱스 스킨 모디파이어가 참조하는 본 노드들을 수집한다.

        Args:
            objs (list[rt.Node]): 대상 객체 배열
            skin_mod_index (int): 모디파이어 스택 인덱스 (0-based)

        Returns:
            list[rt.Node]: 스킨에 사용된 본 배열 (중복 제거됨)
        """
        inf_list = []
        
        for obj in objs:
            if rt.isValidNode(obj):
                deps = rt.refs.dependsOn(obj.modifiers[skin_mod_index])
                for n in deps:
                    if rt.isValidNode(n) and self.is_valid_bone(n):
                        if n not in inf_list:
                            inf_list.append(n)
                            
        return inf_list
    
    def find_skin_mod_id(self, obj):
        """객체의 모디파이어 스택에서 스킨 모디파이어 인덱스를 모두 찾는다.

        Args:
            obj (rt.Node): 대상 객체

        Returns:
            list[int]: 스킨 모디파이어 인덱스 배열 (1-based)
        """
        return [i+1 for i in range(len(obj.modifiers)) if rt.classOf(obj.modifiers[i]) == rt.Skin]
    
    def sel_vert_from_bones(self, skin_mod, threshold=0.01):
        """스킨에서 현재 선택된 본의 가중치가 임계값 이상인 버텍스들을 선택한다.

        Args:
            skin_mod (rt.Skin | None): 스킨 모디파이어. None이면 아무것도 선택하지 않는다.
            threshold (float): 가중치 임계값

        Returns:
            list[int]: 선택된 버텍스 인덱스 배열 (1-based)
        """
        verts_to_sel = []
        
        if skin_mod is not None:
            le_bone = rt.skinOps.getSelectedBone(skin_mod)
            svc = rt.skinOps.GetNumberVertices(skin_mod)
            
            for o in range(1, svc + 1):
                lv = rt.skinOps.GetVertexWeightCount(skin_mod, o)
                
                for k in range(1, lv + 1):
                    if rt.skinOps.GetVertexWeightBoneID(skin_mod, o, k) == le_bone:
                        if rt.skinOps.GetVertexWeight(skin_mod, o, k) >= threshold:
                            if o not in verts_to_sel:
                                verts_to_sel.append(o)
                                
            rt.skinOps.SelectVertices(skin_mod, verts_to_sel)
            
        else:
            print("You must have a skinned object selected")
            
        return verts_to_sel
    
    def sel_all_verts(self, skin_mod):
        """스킨 모디파이어의 모든 버텍스를 선택한다.

        Args:
            skin_mod (rt.Skin | None): 스킨 모디파이어. None이면 아무것도 선택하지 않는다.

        Returns:
            list[int]: 선택된 버텍스 인덱스 배열 (1-based)
        """
        verts_to_sel = []
        
        if skin_mod is not None:
            svc = rt.skinOps.GetNumberVertices(skin_mod)
            
            for o in range(1, svc + 1):
                verts_to_sel.append(o)
                
            rt.skinOps.SelectVertices(skin_mod, verts_to_sel)
            
        return verts_to_sel
    
    def make_rigid_skin(self, skin_mod, vert_list):
        """버텍스들의 가중치를 평균 내어 경직(rigid) 가중치를 계산한다.

        Args:
            skin_mod (rt.Skin): 스킨 모디파이어
            vert_list (list[int]): 버텍스 인덱스 리스트

        Returns:
            list: [본 ID 배열(list[int]), 정규화된 가중치 배열(list[float])] 형태의 2요소 리스트.
                평균 가중치가 0.01 이하인 본은 제외된다.
        """
        weight_array = {}
        vert_count = 0
        bone_array = []
        final_weight = []
        
        # 가중치 수집
        for v in vert_list:
            for cur_bone in range(1, rt.skinOps.GetVertexWeightCount(skin_mod, v) + 1):
                cur_id = rt.skinOps.GetVertexWeightBoneID(skin_mod, v, cur_bone)
                
                if cur_id not in weight_array:
                    weight_array[cur_id] = 0
                    
                cur_weight = rt.skinOps.GetVertexWeight(skin_mod, v, cur_bone)
                weight_array[cur_id] += cur_weight
                vert_count += cur_weight
                
        # 최종 가중치 계산
        for i in weight_array:
            if weight_array[i] > 0:
                new_val = weight_array[i] / vert_count
                if new_val > 0.01:
                    bone_array.append(i)
                    final_weight.append(new_val)
                    
        return [bone_array, final_weight]
    
    def transfert_skin_data(self, skin_mod, source_bone, target_bone, vtx_list):
        """지정 버텍스들에서 원본 본의 스킨 가중치를 대상 본으로 이전한다.

        ``transfer_bone_weights`` 위의 호환 래퍼다(시그니처·이름 불변). 원본 본은 Skin에서
        제거하지 않는다. 구 구현과의 관측 가능한 차이 하나: 구 구현은 원본 본 항목을
        가중치 0으로 남겼지만, 이 구현은 항목을 제거하고 대상에 합산한다. 본별 가중치
        값은 동일하다(0 == 부재)지만 ``GetVertexWeightCount``가 1 작을 수 있다.

        Args:
            skin_mod (rt.Node): 스킨이 적용된 대상 객체 (skin 속성으로 스킨 모디파이어에 접근)
            source_bone (rt.Node): 가중치를 가져올 원본 본
            target_bone (rt.Node): 가중치를 넘겨받을 대상 본
            vtx_list (list[int]): 대상 버텍스 인덱스 리스트 (1-based)

        Raises:
            RuntimeError: 객체에서 Skin 모디파이어를 찾지 못한 경우, 또는
                ``transfer_bone_weights``의 예외 조건
        """
        try:
            skinModifier = skin_mod.skin
        except Exception as e:
            raise RuntimeError(f"'{skin_mod}'에서 Skin 모디파이어를 찾을 수 없습니다.") from e
        if skinModifier is None or rt.classOf(skinModifier) != rt.Skin:
            raise RuntimeError(f"'{skin_mod}'의 skin 속성이 Skin 모디파이어가 아닙니다.")

        self.transfer_bone_weights(
            skin_mod,
            skinModifier,
            {_node_handle(source_bone): _node_handle(target_bone)},
            set(),
            inVertexIndices=list(vtx_list),
        )

    def activate_skin(self, inNode: Any, inSkinMod: Any) -> None:
        """skinOps 호출이 성립하도록 노드를 선택하고 Skin을 Modify 패널의 현재 객체로 둔다.

        **현재 선택을 바꾼다.** 호출 전 선택을 보존해야 하면 호출자가 보관·복원한다
        (``transfer_bone_weights``는 내부에서 보관·복원한다).

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: 활성화할 Skin 모디파이어
        """
        rt.select(inNode)
        rt.setCommandPanelTaskMode(rt.Name("modify"))
        rt.modPanel.setCurrentObject(inSkinMod)

    def get_bone_table(self, inSkinMod: Any) -> Dict[int, Dict[str, Any]]:
        """Skin의 본 ID 대조표 ``{boneId: {"name", "handle", "byName"}}``를 만든다.

        **본 ID API만 사용한다**(``GetNumberBones`` / ``GetBoneName`` / ``GetBoneNode``).
        본 ID와 리스트 ID는 다르므로 ``GetBoneIDByListID`` 계열과 섞지 않는다. 본 ID는
        1..GetNumberBones 연속이다. 노드 대조는 ``GetBoneNode``가 준 노드의 핸들로 하고,
        ``GetBoneNode``가 None을 주면 이름으로 폴백하되 동명 노드 오대조 가능성이 있으므로
        ``"byName": True``로 표시한다. 어느 쪽으로도 노드를 찾지 못하면 ``handle``은 None.

        ``activate_skin``이 선행되어야 한다.

        Args:
            inSkinMod: Skin 모디파이어

        Returns:
            ``{boneId: {"name": str, "handle": int | None, "byName": bool}}``
        """
        table: Dict[int, Dict[str, Any]] = {}
        for boneId in range(1, int(rt.skinOps.GetNumberBones(inSkinMod)) + 1):
            boneName = str(rt.skinOps.GetBoneName(inSkinMod, boneId, 1))
            handle = None
            byName = False
            boneNode = rt.skinOps.GetBoneNode(inSkinMod, boneId)
            if boneNode is not None:
                handle = _node_handle(boneNode)
            else:
                fallback = rt.getNodeByName(boneName)
                if fallback is not None:
                    handle = _node_handle(fallback)
                    byName = True
            table[boneId] = {"name": boneName, "handle": handle, "byName": byName}
        return table

    def get_vertex_weights(
        self, inSkinMod: Any, inVertexIndices: Optional[Iterable[int]] = None
    ) -> Dict[int, List[Tuple[int, float]]]:
        """버텍스별 가중치 ``{vertIndex(1-based): [(boneId, weight), ...]}``를 읽는다.

        ``activate_skin``이 선행되어야 한다.

        Args:
            inSkinMod: Skin 모디파이어
            inVertexIndices: 읽을 버텍스 인덱스(1-based). None이면 전 버텍스

        Returns:
            버텍스 인덱스 → ``(본 ID, 가중치)`` 목록. 본 ID는 ``get_bone_table``의 키와 같다
        """
        if inVertexIndices is None:
            indices: Iterable[int] = range(1, int(rt.skinOps.GetNumberVertices(inSkinMod)) + 1)
        else:
            indices = [int(v) for v in inVertexIndices]
        weights: Dict[int, List[Tuple[int, float]]] = {}
        for v in indices:
            entries: List[Tuple[int, float]] = []
            for k in range(1, int(rt.skinOps.GetVertexWeightCount(inSkinMod, v)) + 1):
                entries.append(
                    (
                        int(rt.skinOps.GetVertexWeightBoneID(inSkinMod, v, k)),
                        float(rt.skinOps.GetVertexWeight(inSkinMod, v, k)),
                    )
                )
            weights[v] = entries
        return weights

    def get_used_bone_handles(
        self,
        inBoneTable: Dict[int, Dict[str, Any]],
        inWeights: Dict[int, List[Tuple[int, float]]],
    ) -> Set[int]:
        """가중치가 0보다 큰 버텍스가 하나라도 있는 본의 노드 핸들 집합을 돌려준다 (순수).

        pymxs를 호출하지 않는다. 대조표에 없는 본 ID와 핸들이 None인 본은 제외한다.

        Args:
            inBoneTable: ``get_bone_table`` 결과
            inWeights: ``get_vertex_weights`` 결과

        Returns:
            사용 중인 본의 노드 핸들 집합
        """
        usedIds: Set[int] = set()
        for entries in inWeights.values():
            for boneId, weight in entries:
                if weight > 0.0:
                    usedIds.add(boneId)
        return {
            inBoneTable[boneId]["handle"]
            for boneId in usedIds
            if boneId in inBoneTable and inBoneTable[boneId]["handle"] is not None
        }

    def transfer_bone_weights(
        self,
        inNode: Any,
        inSkinMod: Any,
        inTransferByHandle: Dict[int, int],
        inRemoveHandles: Iterable[int],
        inVertexWeights: Optional[Dict[int, List[Tuple[int, float]]]] = None,
        inVertexIndices: Optional[Iterable[int]] = None,
        inVerifySampleLimit: int = 64,
    ) -> Dict[str, Any]:
        """Skin 하나에서 본 가중치를 다대일로 이전하고, 지정 본을 Skin에서 제거한다.

        본 식별은 **노드 핸들**(정수)이다. 절차는 다음 순서로 진행하며 순서가 결과를 가른다.

        1. 현재 선택을 보관한다(모든 부작용보다 앞).
        2. ``get_bone_table``로 본 ID ↔ 핸들 대조표를 만든다.
        3. 이전 대상 본이 이 Skin에 없으면 ``addBone(skin, node, 0)``으로 먼저 넣고 대조표와
           **가중치·사용 본 집합을 모두 다시 읽는다**(아래 "본 ID는 밀린다" 참조). 새 본의
           bind 행렬은 "지금" 트랜스폼이므로 씬이 bind pose여야 정확하다 - 이 경우
           ``warnings``에 경고를 넣는다.
        4. 원본 본에 가중치가 있는 버텍스만 ``merge_vertex_weights``로 합산해
           ``ReplaceVertexWeights``로 쓴다. 쓴 직후 앞쪽 표본(``inVerifySampleLimit``개)을
           재조회해 원본 본 잔여 가중치가 0인지 확인한다(호출 성공 ≠ 효과).
        5. ``inRemoveHandles``의 본을 ``removeBone``으로 **ID 내림차순** 제거한다(제거 시 ID가
           밀린다). ``inRemoveHandles``가 비어 있으면 이 단계와 6을 건너뛴다.
        6. 제거 후 대조표를 재조회해 제거 본이 남아 있지 않음을 단정한다.
        7. 쓴 버텍스를 재조회해 **노드 핸들 기준** 기대값과 대조한다. 편차가 1e-6을 넘으면
           ``RuntimeError``를 올린다.
        8. 선택을 복원한다(예외 시에도).

        **본 ID는 밀린다 - ``addBone`` 전에 읽은 본 ID를 그 뒤에 쓰면 안 된다.**
        Max는 이전에 ``removeBone``으로 비워 둔 슬롯이 있으면 새 본에게 **가장 낮은 빈
        자리부터** 내주고, 그 뒤 본의 ID를 한 칸씩 민다. 2026-09-15 프로덕션 Skin 실측 -
        258본짜리 Skin에 본 하나를 추가하자 새 본이 ID 1을 차지하고 전 본이 밀렸다::

            전:  1 spine_03   2 neck_twist_01   3 head            4 neck_twist_02  ...
            후:  1 neck       2 spine_03        3 neck_twist_01   4 head           ...

        리거가 본을 붙였다 뗐다 한 Skin에는 빈 슬롯이 흔하다. 갓 만든 Skin은 빈 슬롯이
        없어 항상 끝에 붙으므로(합성 44조합 실측) 이 결함은 프로덕션에서만 드러났다.
        그래서 3에서 가중치를 다시 읽고, 전후 비교는 ID가 아니라 **핸들**로 한다.

        **``ReplaceVertexWeights``는 버텍스를 재정규화한다.** 이전과 무관한 본의 가중치도
        float32 ULP 수준(약 4.5e-8)으로 바뀔 수 있으므로 "바이트 동일"을 기대하지 않는다.

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: Skin 모디파이어
            inTransferByHandle: ``{원본 본 핸들: 대상 본 핸들}``. 여러 원본이 한 대상을 가리켜도 된다
            inRemoveHandles: Skin에서 제거할 본 핸들 집합. 빈 집합이면 이전만 한다
            inVertexWeights: 미리 읽어 둔 ``get_vertex_weights`` 결과. None이면 여기서 읽는다.
                ``addBone``이 일어나면 본 ID가 밀 수 있으므로 **이 값을 버리고 내부에서 같은
                버텍스 범위를 다시 읽는다** - 호출자가 수확 단계에서 떠 온 캐시는 그 시점에
                무효다
            inVertexIndices: 대상 버텍스(1-based). None이면 전 버텍스. ``inVertexWeights``가 함께
                주어지면 그 안에서 이 인덱스만 쓴다
            inVerifySampleLimit: 쓰기 직후 재조회 검증할 버텍스 수 상한. 기본 64

        Returns:
            ``{"transferred": {원본 본 핸들: {"target": 대상 핸들, "verts": int, "weightSum": float}},
            "removedBones": [이름 정렬], "addedBones": [이름], "touchedVerts": int,
            "warnings": [str], "verifiedVerts": int, "boneIdsShifted": bool}``

            ``verifiedVerts``는 7에서 기대값과 대조한 버텍스 수, ``boneIdsShifted``는
            ``addBone``이 기존 본 ID를 밀었는지다(밀렸으면 ``warnings``에도 한 줄 남는다).

        Raises:
            RuntimeError: ① ``inRemoveHandles`` 중 가중치가 있는 본에 이전 대상이 없다
                ② 이전 대상 본이 씬에 없거나 ``addBone`` 효과가 없다
                ③ 표본 재조회에서 원본 본 잔여 가중치가 남았다
                ④ 제거 후 제거 본이 Skin에 남아 있다
                ⑤ 사후 검증에서 쓴 버텍스의 가중치가 핸들 기준 기대값과 1e-6을 넘게 다르다
                (또는 ``inSkinMod``가 Skin 모디파이어가 아니다)
        """
        transferByHandle: Dict[int, int] = dict(inTransferByHandle)
        removeHandles: Set[int] = set(inRemoveHandles)
        savedSelection = _save_selection()
        warnings: List[str] = []
        try:
            if rt.classOf(inSkinMod) != rt.Skin:
                raise RuntimeError(
                    f"'{inNode.name}'에 준 모디파이어는 Skin이 아닙니다: {rt.classOf(inSkinMod)}"
                )
            self.activate_skin(inNode, inSkinMod)

            table = self.get_bone_table(inSkinMod)
            if inVertexWeights is not None:
                weights = inVertexWeights
                if inVertexIndices is not None:
                    wanted = [int(v) for v in inVertexIndices]
                    weights = {v: inVertexWeights[v] for v in wanted if v in inVertexWeights}
            else:
                weights = self.get_vertex_weights(inSkinMod, inVertexIndices)

            byNameEntries = [e["name"] for e in table.values() if e.get("byName")]
            if byNameEntries:
                warnings.append(
                    f"GetBoneNode가 None을 준 본 {len(byNameEntries)}개를 이름으로 대조했습니다: "
                    f"{byNameEntries[:5]}"
                )

            usedBoneIds: Set[int] = {
                boneId
                for entries in weights.values()
                for boneId, weight in entries
                if weight > 0.0
            }
            removeBoneIds = {bid for bid, e in table.items() if e["handle"] in removeHandles}

            # 사용 중인 제거 본에 이전 대상이 없으면 여기서 멈춘다 - 이대로 제거하면 가중치가 사라진다
            missingTargets = [
                table[bid]["name"]
                for bid in sorted(usedBoneIds & removeBoneIds)
                if table[bid]["handle"] not in transferByHandle
            ]
            if missingTargets:
                raise RuntimeError(
                    f"'{inNode.name}' Skin에서 이전 대상이 없는 사용 본: {missingTargets}"
                )

            idsByHandle = self._bone_ids_by_handle(table)
            sourceBoneIds = {
                bid for bid in usedBoneIds if table[bid]["handle"] in transferByHandle
            }

            # 절차 전 스냅샷을 **핸들 기준**으로 떠 둔다 - 사후 검증의 기준값이다.
            # 본 ID는 addBone/removeBone이 밀 수 있으므로 기준으로 쓸 수 없다.
            snapshotByHandle: Dict[int, Dict[int, float]] = {}
            for vertIndex, entries in weights.items():
                byHandle: Dict[int, float] = {}
                for boneId, weight in entries:
                    if weight <= 0.0:
                        continue
                    handle = table[boneId]["handle"] if boneId in table else None
                    if handle is None:
                        continue
                    byHandle[handle] = byHandle.get(handle, 0.0) + float(weight)
                snapshotByHandle[vertIndex] = byHandle

            # 대상 본이 Skin에 없으면 addBone 후 대조표 재구성
            tableBeforeAdd = table
            boneIdsShifted = False
            neededTargets = sorted(
                {transferByHandle[table[bid]["handle"]] for bid in sourceBoneIds}
            )
            addedBones: List[str] = []
            for targetHandle in neededTargets:
                if targetHandle in idsByHandle:
                    continue
                targetNode = _node_by_handle(targetHandle)
                if targetNode is None:
                    raise RuntimeError(f"이전 대상 본(핸들 {targetHandle})이 씬에 없습니다.")
                countBefore = int(rt.skinOps.GetNumberBones(inSkinMod))
                rt.skinOps.addBone(inSkinMod, targetNode, 0)
                if int(rt.skinOps.GetNumberBones(inSkinMod)) != countBefore + 1:
                    raise RuntimeError(
                        f"'{inNode.name}' Skin에 '{targetNode.name}' addBone 효과 없음"
                    )
                addedBones.append(str(targetNode.name))
            if addedBones:
                # 새로 추가된 본의 bind 행렬은 "지금" 트랜스폼이다. 씬이 bind pose가 아니면
                # 그 본으로 옮긴 가중치가 다른 변형을 만든다 - 리거가 알아야 한다.
                warnings.append(
                    f"이전 대상 본 {len(addedBones)}개를 Skin에 새로 추가했습니다 {addedBones} - "
                    f"씬이 bind pose(리깅 기준 자세)여야 결과가 정확합니다."
                )
                table = self.get_bone_table(inSkinMod)
                idsByHandle = self._bone_ids_by_handle(table)
                removeBoneIds = {bid for bid, e in table.items() if e["handle"] in removeHandles}

                # addBone은 본 ID를 **밀 수 있다**. Max는 이전에 removeBone으로 비워 둔
                # 슬롯이 있으면 가장 낮은 빈 자리부터 새 본에 내주고, 그 뒤 본의 ID가
                # 전부 한 칸씩 밀린다(2026-09-15 실측 - 프로덕션 Skin에서 새 본이 ID 1을
                # 차지하며 258본이 밀렸다). 그러면 addBone **전에** 읽어 둔 가중치 항목과
                # usedBoneIds는 다른 본을 가리키게 되므로 여기서 다시 읽는다.
                shiftedBones = [
                    (bid, str(entry["name"]), str(table[bid]["name"]))
                    for bid, entry in sorted(tableBeforeAdd.items())
                    if bid in table and table[bid]["handle"] != entry["handle"]
                ]
                boneIdsShifted = bool(shiftedBones)
                if boneIdsShifted:
                    warnings.append(
                        f"addBone이 본 ID를 밀었습니다({len(shiftedBones)}개) - 예: "
                        f"{[f'ID {bid}: {before} -> {after}' for bid, before, after in shiftedBones[:3]]}. "
                        f"가중치를 다시 읽어 반영했습니다."
                    )

                # 읽는 범위는 애초 대상 버텍스 그대로다(부분 이전이면 그 범위만).
                weights = self.get_vertex_weights(inSkinMod, sorted(weights))
                usedBoneIds = {
                    boneId
                    for entries in weights.values()
                    for boneId, weight in entries
                    if weight > 0.0
                }
                sourceBoneIds = {
                    bid for bid in usedBoneIds if table[bid]["handle"] in transferByHandle
                }

            remap: Dict[int, int] = {
                bid: idsByHandle[transferByHandle[table[bid]["handle"]]] for bid in sourceBoneIds
            }

            # 버텍스별 합산 → ReplaceVertexWeights
            transferred: Dict[int, Dict[str, Any]] = {}
            touchedIndices: List[int] = []
            touchedCount = 0
            verified = 0
            for vertIndex, entries in weights.items():
                ids, ws, touched = merge_vertex_weights(entries, remap)
                if not touched:
                    continue
                touchedIndices.append(vertIndex)
                for boneId, weight in entries:
                    if boneId not in remap:
                        continue
                    srcHandle = table[boneId]["handle"]
                    detail = transferred.setdefault(
                        srcHandle,
                        {"target": transferByHandle[srcHandle], "verts": 0, "weightSum": 0.0},
                    )
                    detail["verts"] = int(detail["verts"]) + 1
                    detail["weightSum"] = float(detail["weightSum"]) + weight
                rt.skinOps.ReplaceVertexWeights(inSkinMod, vertIndex, ids, ws)
                touchedCount += 1

                if verified < inVerifySampleLimit:
                    verified += 1
                    residual = 0.0
                    for k in range(1, int(rt.skinOps.GetVertexWeightCount(inSkinMod, vertIndex)) + 1):
                        if int(rt.skinOps.GetVertexWeightBoneID(inSkinMod, vertIndex, k)) in remap:
                            residual += float(rt.skinOps.GetVertexWeight(inSkinMod, vertIndex, k))
                    if residual > 1e-6:
                        raise RuntimeError(
                            f"'{inNode.name}' 버텍스 {vertIndex}: ReplaceVertexWeights 후 원본 본 "
                            f"잔여 가중치 {residual}"
                        )

            # removeBone - ID 내림차순
            removedBones: List[str] = []
            if removeHandles:
                namesToRemove = {table[bid]["name"] for bid in removeBoneIds}
                for boneId in sorted(removeBoneIds, reverse=True):
                    rt.skinOps.removeBone(inSkinMod, boneId)

                afterTable = self.get_bone_table(inSkinMod)
                residualNames = [
                    e["name"] for e in afterTable.values() if e["handle"] in removeHandles
                ]
                if residualNames:
                    raise RuntimeError(
                        f"'{inNode.name}' Skin에 제거 본이 남아 있습니다 ({len(residualNames)}개): "
                        f"{residualNames[:10]}"
                    )
                removedBones = sorted(namesToRemove)
                finalTable = afterTable
            else:
                finalTable = table

            # 사후 검증 - 쓴 버텍스를 **핸들 기준**으로 기대값과 대조한다.
            # 본 ID는 addBone(빈 슬롯 재사용)과 removeBone(제거 후 압축)이 양쪽에서 밀므로
            # ID로 비교하면 서로 다른 본을 견주게 된다. 이 결함이 정확히 그렇게 조용히
            # 지나갔으므로, 라이브러리가 스스로 단정한다.
            verifiedVerts = 0
            if touchedIndices:
                # 쓰기 직후의 재조회는 갱신 없이는 **0을 돌려준다**(2026-09-15 실측 -
                # `addBone`/`removeBone`이 한 번도 없었던 경로에서 방금 쓴 가중치가 전부 0으로
                # 읽혔다. 구조 변경이 있으면 그 호출이 갱신을 강제해 증상이 숨는다).
                # 조회가 예외 대신 거짓 답을 주는 형태이므로 읽기 전에 갱신을 명시한다
                # (`max/pymxs_pitfalls_advanced.md` §28-a).
                self.activate_skin(inNode, inSkinMod)
                rt.completeRedraw()
                actualRaw = self.get_vertex_weights(inSkinMod, touchedIndices)
                actualByHandle: Dict[int, Dict[int, float]] = {}
                for vertIndex, entries in actualRaw.items():
                    byHandle = {}
                    for boneId, weight in entries:
                        if weight <= 0.0:
                            continue
                        handle = finalTable[boneId]["handle"] if boneId in finalTable else None
                        if handle is None:
                            continue
                        byHandle[handle] = byHandle.get(handle, 0.0) + float(weight)
                    actualByHandle[vertIndex] = byHandle

                expected = expected_weights_by_handle(
                    {v: snapshotByHandle[v] for v in touchedIndices if v in snapshotByHandle},
                    transferByHandle,
                )
                deviations = diff_weights_by_handle(expected, actualByHandle)
                if deviations:
                    nameByHandle = {
                        e["handle"]: str(e["name"])
                        for e in finalTable.values()
                        if e["handle"] is not None
                    }
                    detail = ", ".join(
                        f"v{vertIndex} '{nameByHandle.get(handle, f'핸들 {handle}')}' "
                        f"기대 {expectedWeight:.6g} 실제 {actualWeight:.6g}"
                        for vertIndex, handle, expectedWeight, actualWeight in deviations[:5]
                    )
                    raise RuntimeError(
                        f"'{inNode.name}' 이전 결과가 기대값과 다릅니다 "
                        f"({len(deviations)}건 / 검증 버텍스 {len(touchedIndices)}개): {detail}"
                    )
                verifiedVerts = len(touchedIndices)

            return {
                "transferred": transferred,
                "removedBones": removedBones,
                "addedBones": addedBones,
                "touchedVerts": touchedCount,
                "warnings": warnings,
                "verifiedVerts": verifiedVerts,
                "boneIdsShifted": boneIdsShifted,
            }
        finally:
            _restore_selection(savedSelection)

    @staticmethod
    def _bone_ids_by_handle(inTable: Dict[int, Dict[str, Any]]) -> Dict[int, int]:
        """대조표를 ``{노드 핸들: 본 ID}``로 뒤집는다. 핸들이 None인 본은 제외한다."""
        return {
            entry["handle"]: boneId
            for boneId, entry in inTable.items()
            if entry["handle"] is not None
        }

    # ------------------------------------------------------------------
    # 선택 / 일괄 쓰기 / 본 목록·추가·제거 / 복제 / 대칭
    # (2026-10 SkinKit 포팅에서 추가. 연산 자체는 skinWeightMath 순수 함수에 둔다)
    # ------------------------------------------------------------------

    def get_selected_vertices(self, inSkinMod: Any) -> List[int]:
        """Skin에서 선택된 버텍스 인덱스(1-based, 오름차순)를 돌려준다.

        ``skinOps.getSelectedVertices`` 단일 호출이다(2026-10-06 실측 - 정수 배열을 준다).
        버텍스마다 ``IsVertexSelected``를 부르는 것보다 싸서 선택 변경 폴링에 쓸 수 있다.
        ``activate_skin``이 선행되어야 한다.

        Args:
            inSkinMod: Skin 모디파이어

        Returns:
            선택 버텍스 인덱스 목록
        """
        return sorted(int(v) for v in rt.skinOps.getSelectedVertices(inSkinMod))

    def select_vertices(self, inSkinMod: Any, inVertices: Iterable[int]) -> None:
        """Skin 버텍스 선택을 지정한 목록으로 **바꾼다**(빈 목록이면 전부 해제).

        스크립트로 바꾼 선택은 ``NodeEventCallback``의 ``subobjectSelectionChanged``를
        발화시키지 않는다(2026-10-06 실측 - batch/GUI 양쪽). 선택 변경을 감지하는 쪽은
        폴링을 함께 둬야 한다. ``activate_skin``이 선행되어야 한다.

        Args:
            inSkinMod: Skin 모디파이어
            inVertices: 선택할 버텍스(1-based)
        """
        rt.skinOps.SelectVertices(inSkinMod, sorted({int(v) for v in inVertices}))

    def set_vertex_weights(
        self,
        inSkinMod: Any,
        inWeights: Dict[int, Tuple[Sequence[int], Sequence[float]]],
        inNormalize: bool = True,
        inWriteEmpty: bool = False,
    ) -> List[int]:
        """여러 버텍스의 가중치를 한 번에 쓴다.

        - 0 이하 가중치 항목은 버리고, 같은 본이 두 번 나오면 더한다.
        - ``inNormalize``면 합 1로 정규화한다. **단일 본 항목에 1.0 미만 값을 쓰면 Max가
          0.0으로 기록한다**(2026-10-06 실측: 0.2 -> 0.0. 다중 본은 재정규화된다) - 그래서
          기본값이 True다.
        - 항목이 비면 기본은 건너뛴다. ``inWriteEmpty``면 빈 배열을 써서 **무웨이트**로
          만든다(새 Skin에 원본 가중치를 옮길 때 엔벨로프 자동 가중치를 지우는 용도).
        - "Max 2014 sp5 hack"(``SetVertexWeights`` 선행)은 쓰지 않는다 - Max 2024에서 유무
          결과가 같았다(2026-10-06 실측).
        - ``disableRefMsgs`` 구간에서 쓰고, 끝난 뒤 마지막 버텍스를 한 번 더 써서 갱신을
          강제한다(원본 ApplyWeights 패턴).

        쓰기 직후 재조회는 0을 줄 수 있다. 검증 읽기 전에는 ``activate_skin`` +
        ``completeRedraw``를 부른다(``max/skin_bone_id.md`` §4). ``activate_skin``이 선행되어야 한다.

        Args:
            inSkinMod: Skin 모디파이어
            inWeights: ``{버텍스(1-based): (본 ID 목록, 가중치 목록)}``
            inNormalize: 합 1 정규화 여부. 기본 True
            inWriteEmpty: 빈 항목을 무웨이트로 쓸지. 기본 False(건너뜀)

        Returns:
            실제로 쓴 버텍스 목록(오름차순)
        """
        from pyjallib.max.skinWeightMath import normalize_weights

        items: List[Tuple[int, List[int], List[float]]] = []
        for vertIndex in sorted(inWeights):
            boneIds, weights = inWeights[vertIndex]
            merged: Dict[int, float] = {}
            for boneId, weight in zip(boneIds, weights):
                if float(weight) > 0.0:
                    merged[int(boneId)] = merged.get(int(boneId), 0.0) + float(weight)
            if not merged:
                if inWriteEmpty:
                    items.append((int(vertIndex), [], []))
                continue
            ids = list(merged.keys())
            ws = [merged[b] for b in ids]
            if inNormalize:
                ws = normalize_weights(ws)
            items.append((int(vertIndex), ids, ws))
        if not items:
            return []

        rt.disableRefMsgs()
        try:
            for vertIndex, ids, ws in items:
                rt.skinOps.ReplaceVertexWeights(inSkinMod, vertIndex, ids, ws)
        finally:
            rt.enableRefMsgs()
        lastIndex, lastIds, lastWs = items[-1]
        rt.skinOps.ReplaceVertexWeights(inSkinMod, lastIndex, lastIds, lastWs)
        return [vertIndex for vertIndex, _, _ in items]

    def get_bone_nodes(self, inSkinMod: Any) -> List[Any]:
        """본 노드 목록을 **본 ID 순**으로 돌려준다(``result[i]``가 본 ID ``i + 1``).

        ``skinOps.GetBoneNode``(본 ID API)를 쓴다 - 리스트 ID와 섞지 않는다. 노드를 찾지
        못한 본은 None이다. ``activate_skin``이 선행되어야 한다.

        Args:
            inSkinMod: Skin 모디파이어

        Returns:
            본 노드(또는 None) 목록
        """
        return [
            rt.skinOps.GetBoneNode(inSkinMod, boneId)
            for boneId in range(1, int(rt.skinOps.GetNumberBones(inSkinMod)) + 1)
        ]

    def add_bones(self, inNode: Any, inSkinMod: Any, inBones: Iterable[Any]) -> Dict[int, int]:
        """본들을 Skin에 넣고(이미 있으면 건너뜀) **다시 읽은** ``{핸들: 본 ID}``를 돌려준다.

        ``addBone``은 끝에 붙는다는 보장이 없다 - 빈 슬롯이 있으면 가장 낮은 빈 자리를
        차지하고 뒤 본 ID를 민다(``max/skin_bone_id.md`` §2, 2026-10-06 실기 자산에서도
        빈 슬롯 실재 확인). 그래서 추가 뒤 대조표를 다시 읽어 핸들로 ID를 돌려준다.
        **이 호출 전에 읽어 둔 본 ID와 가중치는 전부 무효다.**

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: Skin 모디파이어
            inBones: 넣을 본 노드들

        Returns:
            ``{요청한 본의 핸들: 현재 본 ID}``

        Raises:
            RuntimeError: 추가 뒤에도 요청한 본이 대조표에 없을 때
        """
        bones = [b for b in inBones if b is not None and rt.isValidNode(b)]
        self.activate_skin(inNode, inSkinMod)
        existing = self._bone_ids_by_handle(self.get_bone_table(inSkinMod))
        added = False
        for bone in bones:
            if _node_handle(bone) not in existing:
                rt.skinOps.addBone(inSkinMod, bone, 0)
                existing[_node_handle(bone)] = -1
                added = True
        if added:
            rt.completeRedraw()
        idsByHandle = self._bone_ids_by_handle(self.get_bone_table(inSkinMod))
        result: Dict[int, int] = {}
        for bone in bones:
            handle = _node_handle(bone)
            if handle not in idsByHandle:
                raise RuntimeError(f"'{inNode.name}' Skin에 '{bone.name}' addBone 효과 없음")
            result[handle] = idsByHandle[handle]
        return result

    def remove_bone(
        self, inNode: Any, inSkinMod: Any, inBoneHandle: int, inTransferToParent: bool = True
    ) -> Dict[str, Any]:
        """본 하나를 Skin에서 제거한다. 부모가 같은 Skin에 있으면 가중치를 부모로 옮긴다.

        - 부모가 Skin에 있고 ``inTransferToParent``면 ``transfer_bone_weights``로 이전 +
          제거(사후 검증 포함)한다.
        - 아니면 그 본을 뺀 가중치를 정규화해 먼저 쓰고 제거한다. 그 본에만 묶여 있던
          버텍스는 **무웨이트**가 되므로 ``weightlessVerts``로 돌려준다(호출자가 주변
          가중치로 채운다 - 원본 SkinKit은 Attach를 반복했다).

          원본과의 차이(**결함 수정**): 원본은 그냥 ``removeBone``했다. Max는 남은 가중치를
          재정규화하지 않아 다른 본을 함께 가진 버텍스까지 무웨이트(``b2 0.0``)가 됐고,
          그 버텍스의 남은 가중치는 이웃 Attach로 덮였다.

        본 ID는 제거 후 압축되며 밀린다. 반환값은 이름·핸들 기준이고, 호출자는 이 호출 전
        본 ID를 버린다.

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: Skin 모디파이어
            inBoneHandle: 제거할 본의 노드 핸들
            inTransferToParent: 부모로 가중치를 옮길지. 기본 True

        Returns:
            ``{"removed": 이름, "transferredTo": 부모 이름 | None,
            "weightlessVerts": [1-based], "transfer": transfer_bone_weights 결과 | None}``

        Raises:
            RuntimeError: 본이 Skin에 없거나, 제거 후에도 남아 있을 때
        """
        self.activate_skin(inNode, inSkinMod)
        table = self.get_bone_table(inSkinMod)
        idsByHandle = self._bone_ids_by_handle(table)
        if inBoneHandle not in idsByHandle:
            raise RuntimeError(f"'{inNode.name}' Skin에 핸들 {inBoneHandle} 본이 없습니다.")
        boneName = str(table[idsByHandle[inBoneHandle]]["name"])
        boneNode = _node_by_handle(inBoneHandle)
        parent = boneNode.parent if boneNode is not None else None
        parentHandle = _node_handle(parent) if parent is not None and rt.isValidNode(parent) else None

        transferReport: Optional[Dict[str, Any]] = None
        transferredTo: Optional[str] = None
        if inTransferToParent and parentHandle is not None and parentHandle in idsByHandle:
            transferReport = self.transfer_bone_weights(
                inNode, inSkinMod, {inBoneHandle: parentHandle}, {inBoneHandle}
            )
            transferredTo = str(parent.name)
        else:
            savedSelection = _save_selection()
            try:
                self.activate_skin(inNode, inSkinMod)
                # removeBone은 남은 가중치를 재정규화하지 않는다 - 'b1 0.5 + b2 0.5' 버텍스가
                # 제거 후 'b2 0.0'으로 남아 사실상 무웨이트가 된다(2026-10-06 실측). 그래서
                # 제거 본을 뺀 가중치를 먼저 정규화해 쓰고 제거한다(그 본만 가진 버텍스는
                # 무웨이트로 쓰고 아래에서 보고한다).
                boneId = idsByHandle[inBoneHandle]
                rewrite: Dict[int, Tuple[List[int], List[float]]] = {}
                for vertIndex, entries in self.get_vertex_weights(inSkinMod).items():
                    if not any(b == boneId for b, _ in entries):
                        continue
                    rest = [(b, w) for b, w in entries if b != boneId and w > 0.0]
                    rewrite[vertIndex] = ([b for b, _ in rest], [w for _, w in rest])
                self.set_vertex_weights(inSkinMod, rewrite, inNormalize=True, inWriteEmpty=True)
                rt.skinOps.removeBone(inSkinMod, boneId)
                after = self._bone_ids_by_handle(self.get_bone_table(inSkinMod))
                if inBoneHandle in after:
                    raise RuntimeError(f"'{inNode.name}' Skin에 '{boneName}'이 제거 후에도 남아 있습니다.")
            finally:
                _restore_selection(savedSelection)

        self.activate_skin(inNode, inSkinMod)
        rt.completeRedraw()
        weightless = [
            vertIndex
            for vertIndex, entries in self.get_vertex_weights(inSkinMod).items()
            if sum(weight for _, weight in entries) <= 0.0
        ]
        return {
            "removed": boneName,
            "transferredTo": transferredTo,
            "weightlessVerts": weightless,
            "transfer": transferReport,
        }

    def duplicate_skin(
        self,
        inNode: Any,
        inSkinMod: Any,
        inName: Optional[str] = None,
        inEnabled: bool = False,
    ) -> Any:
        """Skin을 같은 본·가중치의 새 Skin으로 복제한다(백업용, 기본 비활성).

        새 Skin은 원본 SkinKit Backup처럼 ``addModifier ... before:1``로 넣는다. 본은 원본
        본 ID 순서로 넣고, 가중치는 **핸들 기준**으로 옮긴다(복제본 본 ID를 원본과 같다고
        가정하지 않는다). 쓴 뒤 다시 읽어 원본과 핸들 기준으로 대조하고, 편차가 1e-6을 넘으면
        예외를 올린다. 끝나면 원본 Skin을 Modify 패널 현재 객체로 되돌린다.

        새 본의 bind 행렬은 "지금" 트랜스폼이다 - 씬이 bind pose일 때 복제가 정확하다.

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: 복제할 Skin 모디파이어
            inName: 새 Skin 이름. None이면 ``Skin_<localTime>``
            inEnabled: 새 Skin 활성 여부. 기본 False

        Returns:
            새 Skin 모디파이어

        Raises:
            RuntimeError: 노드를 찾지 못한 본이 있거나, 버텍스 수가 다르거나, 대조 편차가 날 때
        """
        self.activate_skin(inNode, inSkinMod)
        table = self.get_bone_table(inSkinMod)
        missing = [e["name"] for e in table.values() if e["handle"] is None]
        if missing:
            raise RuntimeError(f"'{inNode.name}' Skin에 노드를 찾지 못한 본이 있어 복제할 수 없습니다: {missing[:5]}")
        sourceWeights = self.get_vertex_weights(inSkinMod)
        sourceByHandle = self._weights_by_handle(table, sourceWeights)
        boneNodes = [_node_by_handle(table[bid]["handle"]) for bid in sorted(table)]

        copySkin = rt.Skin()
        copySkin.name = inName if inName else f"Skin_{rt.localTime}"
        rt.addModifier(inNode, copySkin, before=1)
        try:
            copySkin.bone_Limit = inSkinMod.bone_Limit
            copySkin.enableDQ = inSkinMod.enableDQ
        except RuntimeError:
            pass
        idsByHandle = self.add_bones(inNode, copySkin, boneNodes)
        if int(rt.skinOps.GetNumberVertices(copySkin)) != len(sourceWeights):
            raise RuntimeError(
                f"'{inNode.name}' 복제 Skin 버텍스 수가 다릅니다: "
                f"{int(rt.skinOps.GetNumberVertices(copySkin))} != {len(sourceWeights)}"
            )
        toWrite = {
            vertIndex: (
                [idsByHandle[table[bid]["handle"]] for bid, _ in entries],
                [weight for _, weight in entries],
            )
            for vertIndex, entries in sourceWeights.items()
        }
        self.set_vertex_weights(copySkin, toWrite, inNormalize=False, inWriteEmpty=True)

        self.activate_skin(inNode, copySkin)
        rt.completeRedraw()
        copyTable = self.get_bone_table(copySkin)
        copyByHandle = self._weights_by_handle(copyTable, self.get_vertex_weights(copySkin))
        deviations = diff_weights_by_handle(sourceByHandle, copyByHandle)
        if deviations:
            raise RuntimeError(f"'{inNode.name}' Skin 복제 결과가 원본과 다릅니다({len(deviations)}건): {deviations[:3]}")

        copySkin.enabled = bool(inEnabled)
        self.activate_skin(inNode, inSkinMod)
        return copySkin

    def mirror_weights(
        self,
        inNode: Any,
        inSkinMod: Any,
        inVertexMap: Dict[int, int],
        inSourceVertices: Iterable[int],
        inBoneMap: Optional[Dict[int, int]] = None,
    ) -> List[int]:
        """원본 쪽 버텍스의 가중치를 대칭 버텍스로 복사한다(본은 대칭 본으로 바꾼다).

        ``inVertexMap[v] = m``이고 ``m``이 원본 집합에 있으면 ``v``는 ``m``의 가중치를 대칭
        본으로 바꿔 받는다(원본 SkinKit Mirror). 버텍스 오름차순으로 처리하고, 앞에서 쓴
        결과를 뒤에서 읽는다 - 원본이 버텍스마다 Skin을 다시 읽던 것과 같다. 그래서 양쪽을
        모두 선택하고 실행해도 L/R이 맞바뀌지 않고 **인덱스가 큰 쪽 가중치가 작은 쪽으로**
        복사된다(원본 동작).

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: Skin 모디파이어
            inVertexMap: ``{버텍스: 대칭 버텍스}`` (1-based). 위치/토폴로지 매핑 결과
            inSourceVertices: 원본 쪽 버텍스(보통 선택)
            inBoneMap: ``{본 ID: 대칭 본 ID}``. None이면 본 이름 패턴으로 만든다
                (``skinWeightMath.build_mirror_bone_map``, 씬 노드 이름으로 존재 확인)

        Returns:
            쓴 버텍스 목록(오름차순)
        """
        from pyjallib.max.skinWeightMath import build_mirror_bone_map

        self.activate_skin(inNode, inSkinMod)
        boneMap = inBoneMap
        if boneMap is None:
            table = self.get_bone_table(inSkinMod)
            ids = sorted(table)
            names = [str(table[bid]["name"]) for bid in ids]
            sceneNames = [str(obj.name) for obj in rt.objects]
            indexMap = build_mirror_bone_map(names, sceneNames)
            boneMap = {ids[i]: ids[indexMap[i]] for i in range(len(ids))}

        sources = {int(v) for v in inSourceVertices}
        targets = sorted(v for v, m in inVertexMap.items() if m in sources and m != v)
        if not targets:
            return []
        needed = set(targets) | {inVertexMap[v] for v in targets}
        work = self.get_vertex_weights(inSkinMod, sorted(needed))
        written: Dict[int, Tuple[List[int], List[float]]] = {}
        for vertIndex in targets:
            merged: Dict[int, float] = {}
            for boneId, weight in work[inVertexMap[vertIndex]]:
                mirrored = boneMap.get(boneId, boneId)
                merged[mirrored] = merged.get(mirrored, 0.0) + weight
            work[vertIndex] = list(merged.items())
            written[vertIndex] = (list(merged.keys()), list(merged.values()))
        self.set_vertex_weights(inSkinMod, written, inNormalize=True, inWriteEmpty=True)
        return sorted(written)

    @staticmethod
    def _weights_by_handle(
        inTable: Dict[int, Dict[str, Any]], inWeights: Dict[int, List[Tuple[int, float]]]
    ) -> Dict[int, Dict[int, float]]:
        """``{버텍스: [(본 ID, w)]}``를 ``{버텍스: {핸들: w}}``로 바꾼다(0 이하 제외)."""
        result: Dict[int, Dict[int, float]] = {}
        for vertIndex, entries in inWeights.items():
            byHandle: Dict[int, float] = {}
            for boneId, weight in entries:
                if weight <= 0.0 or boneId not in inTable:
                    continue
                handle = inTable[boneId]["handle"]
                if handle is None:
                    continue
                byHandle[handle] = byHandle.get(handle, 0.0) + float(weight)
            result[vertIndex] = byHandle
        return result

    def smooth_skin(self, inObj, inVertMode=VertexMode.Edges, inRadius=5.0, inIterNum=3, inKeepMax=False):
        """MAXScript 스무딩 스크립트를 실행해 선택된 버텍스의 스킨 가중치를 부드럽게 한다.

        Args:
            inObj (rt.Node): 스킨이 적용된 대상 객체
            inVertMode (VertexMode): 버텍스 그룹핑 모드 (Edges/Attach/All/Stiff)
            inRadius (float): 스무딩 반경
            inIterNum (int): 반복 횟수
            inKeepMax (bool): True면 본 1개에만 가중치가 있는 버텍스를 건너뛴다.
        """
        maxScriptCode = textwrap.dedent(r'''
            struct _SmoothSkin (
            SmoothSkinMaxUndo = 10,
            UndoWeights = #(),
            SmoothSkinData = #(#(), #(), #(), #(), #(), #(), #()),
            smoothRadius = 5.0,
            iterNum = 1,
            keepMax = false,

            -- vertGroupMode: Edges, Attach, All, Stiff
            vertGroupMode = 1,

            fn make_rigid_skin skin_mod vert_list =
            (
                /*
                Rigidify vertices weights in skin modifier
                */
                WeightArray = #()
                VertCount = 0
                BoneArray = #()
                FinalWeight = #()

                for v in vert_list do
                (
                    for CurBone = 1 to (skinOps.GetVertexWeightCount skin_mod v) do
                    (
                        CurID = (skinOps.GetVertexWeightBoneID skin_mod v CurBone)
                        if WeightArray[CurID] == undefined do WeightArray[CurID] = 0

                        CurWeight = (skinOps.GetVertexWeight skin_mod v CurBone)
                        WeightArray[CurID] += CurWeight
                        VertCount += CurWeight
                    )

                    for i = 1 to WeightArray.count where WeightArray[i] != undefined and WeightArray[i] > 0 do
                    (
                        NewVal = (WeightArray[i] / VertCount)
                        if NewVal > 0.01 do (append BoneArray i; append FinalWeight NewVal)
                    )
                )
                return #(BoneArray, FinalWeight)
            ),
                
            fn smooth_skin = 
            (
                if $selection.count != 1 then return false

                p = 0
                for iter = 1 to iterNum do 
                (
                    p += 1
                    if classOf (modPanel.getCurrentObject()) != Skin then return false

                    obj = $; skinMod = modPanel.getCurrentObject()
                    FinalBoneArray = #(); FinalWeightArray = #(); o = 1
                        
                    UseOldData = (obj == SmoothSkinData[1][1]) and (obj.verts.count == SmoothSkinData[1][2])
                    if not UseOldData do SmoothSkinData = #(#(), #(), #(), #(), #(), #(), #())
                    SmoothSkinData[1][1] = obj; SmoothSkinData[1][2] = obj.verts.count

                    tmpObj = copy Obj
                    tmpObj.modifiers[skinMod.name].enabled = false

                    fn DoNormalizeWeight Weight = 
                    (
                        WeightLength = 0; NormalizeWeight = #()
                        for w = 1 to Weight.count do WeightLength += Weight[w]
                        if WeightLength != 0 then 
                            for w = 1 to Weight.count do NormalizeWeight[w] = Weight[w] * (1 / WeightLength)
                        else 
                            NormalizeWeight[1] = 1.0
                        return NormalizeWeight
                    )
                        
                    skinMod.clearZeroLimit = 0.00
                    skinOps.RemoveZeroWeights skinMod
                        
                    posarray = for a in tmpObj.verts collect a.pos
                        
                    if (SmoothSkinData[8] != smoothRadius) do (SmoothSkinData[6] = #(); SmoothSkinData[7] = #())
                        
                    for v = 1 to obj.verts.count where (skinOps.IsVertexSelected skinMod v == 1) and (not keepMax or (skinOps.GetVertexWeightCount skinmod v != 1)) do 
                    (
                        VertBros = #{}; VertBrosRatio = #()
                        Weightarray = #(); BoneArray = #(); FinalWeight = #()
                        WeightArray.count = skinOps.GetNumberBones skinMod
                            
                        if vertGroupMode == 1 and (SmoothSkinData[2][v] == undefined) do 
                        (
                            if (classof tmpObj == Editable_Poly) or (classof tmpObj == PolyMeshObject) then 
                            (
                                CurEdges = polyop.GetEdgesUsingVert tmpObj v
                                for CE in CurEdges do VertBros += (polyop.getEdgeVerts tmpObj CE) as bitArray
                            )
                            else 
                            (
                                CurEdges = meshop.GetEdgesUsingvert tmpObj v
                                for i in CurEdges do CurEdges[i] = (getEdgeVis tmpObj (1+(i-1)/3)(1+mod (i-1) 3))
                                for CE in CurEdges do VertBros += (meshop.getVertsUsingEdge tmpObj CE) as bitArray
                            )
                                
                            VertBros = VertBros as array
                            SmoothSkinData[2][v] = #()
                            SmoothSkinData[3][v] = #()
                                
                            if VertBros.count > 0 do 
                            (
                                for vb in VertBros do 
                                (
                                    CurDist = distance posarray[v] posarray[vb]
                                    if CurDist == 0 then 
                                        append VertBrosRatio 0 
                                    else 
                                        append VertBrosRatio (1 / CurDist)
                                )
                                
                                VertBrosRatio = DoNormalizeWeight VertBrosRatio
                                VertBrosRatio[finditem VertBros v] = 1
                                SmoothSkinData[2][v] = VertBros
                                SmoothSkinData[3][v] = VertBrosRatio
                            )
                        )
                        
                        if vertGroupMode == 2 do 
                        (
                            SmoothSkinData[4][v] = for vb = 1 to posarray.count where (skinOps.IsVertexSelected skinMod vb == 0) and (distance posarray[v] posarray[vb]) < smoothRadius collect vb
                            SmoothSkinData[5][v] = for vb in SmoothSkinData[4][v] collect
                                (CurDist = distance posarray[v] posarray[vb]; if CurDist == 0 then 0 else (1 / CurDist))
                            SmoothSkinData[5][v] = DoNormalizeWeight SmoothSkinData[5][v]
                            for i = 1 to SmoothSkinData[5][v].count do SmoothSkinData[5][v][i] *= 2
                        )
                            
                        if vertGroupMode == 3 and (SmoothSkinData[6][v] == undefined) do 
                        (
                            SmoothSkinData[6][v] = for vb = 1 to posarray.count where (distance posarray[v] posarray[vb]) < smoothRadius collect vb
                            SmoothSkinData[7][v] = for vb in SmoothSkinData[6][v] collect
                                (CurDist = distance posarray[v] posarray[vb]; if CurDist == 0 then 0 else (1 / CurDist))
                            SmoothSkinData[7][v] = DoNormalizeWeight SmoothSkinData[7][v]
                            for i = 1 to SmoothSkinData[7][v].count do SmoothSkinData[7][v][i] *= 2
                        )
                            
                        if vertGroupMode != 4 do 
                        (        
                            VertBros = SmoothSkinData[vertGroupMode * 2][v]
                            VertBrosRatio = SmoothSkinData[(vertGroupMode * 2) + 1][v]
                                
                            for z = 1 to VertBros.count do 
                                for CurBone = 1 to (skinOps.GetVertexWeightCount skinMod VertBros[z]) do 
                                (
                                    CurID = (skinOps.GetVertexWeightBoneID skinMod VertBros[z] CurBone)
                                    if WeightArray[CurID] == undefined do WeightArray[CurID] = 0
                                    WeightArray[CurID] += (skinOps.GetVertexWeight skinMod VertBros[z] CurBone) * VertBrosRatio[z]
                                )
                            
                            for i = 1 to WeightArray.count where WeightArray[i] != undefined and WeightArray[i] > 0 do 
                            (
                                NewVal = (WeightArray[i] / 2)
                                if NewVal > 0.01 do (append BoneArray i; append FinalWeight NewVal)
                            )
                            FinalBoneArray[v] = BoneArray
                            FinalWeightArray[v] = FinalWeight
                        )
                    )
                        
                    if vertGroupMode == 4 then 
                    (
                        convertTopoly tmpObj
                        polyObj = tmpObj
                            
                        -- Only test selected
                        VertSelection = for v = 1 to obj.verts.count where (skinOps.IsVertexSelected skinMod v == 1) collect v
                        DoneEdge = (polyobj.edges as bitarray) - polyop.getEdgesUsingVert polyObj VertSelection
                        DoneFace = (polyobj.faces as bitarray) - polyop.getFacesUsingVert polyObj VertSelection

                        -- Elements
                        SmallElements = #()
                        for f = 1 to polyobj.faces.count where not DoneFace[f] do 
                        (
                            CurElement = polyop.getElementsUsingFace polyObj #{f}
                                
                            CurVerts = polyop.getVertsUsingFace polyobj CurElement; MaxDist = 0
                            for v1 in CurVerts do 
                                for v2 in CurVerts where MaxDist < (smoothRadius * 2) do 
                                (
                                    dist = distance polyobj.verts[v1].pos polyobj.verts[v2].pos
                                    if dist > MaxDist do MaxDist = dist
                                )
                            if MaxDist < (smoothRadius * 2) do append SmallElements CurVerts
                            DoneFace += CurElement
                        )

                        -- Loops
                        EdgeLoops = #()
                        for ed in SmallElements do DoneEdge += polyop.getEdgesUsingVert polyobj ed
                        for ed = 1 to polyobj.edges.count where not DoneEdge[ed] do 
                        (
                            polyobj.selectedEdges = #{ed}
                            polyobj.ButtonOp #SelectEdgeLoop
                            CurEdgeLoop = (polyobj.selectedEdges as bitarray)
                            if CurEdgeLoop.numberSet > 2 do 
                            (
                                CurVerts = (polyop.getvertsusingedge polyobj CurEdgeLoop); MaxDist = 0
                                for v1 in CurVerts do 
                                    for v2 in CurVerts where MaxDist < (smoothRadius * 2) do 
                                    (
                                        dist = distance polyobj.verts[v1].pos polyobj.verts[v2].pos
                                        if dist > MaxDist do MaxDist = dist
                                    )
                                if MaxDist < (smoothRadius * 2) do append EdgeLoops CurVerts
                            )
                            DoneEdge += CurEdgeLoop
                        )
                            
                        modPanel.setCurrentObject SkinMod; subobjectLevel = 1
                        for z in #(SmallElements, EdgeLoops) do 
                            for i in z do 
                            (
                                VertList = for v3 in i where (skinOps.IsVertexSelected skinMod v3 == 1) collect v3
                                NewWeights = self.make_rigid_skin SkinMod VertList
                                for v3 in VertList do (FinalBoneArray[v3] = NewWeights[1]; FinalWeightArray[v3] = NewWeights[2])
                            )
                    )
                        
                    SmoothSkinData[8] = smoothRadius
                        
                    delete tmpObj
                    OldWeightArray = #(); OldBoneArray = #(); LastWeights = #()
                    for sv = 1 to FinalBoneArray.count where FinalBonearray[sv] != undefined and FinalBoneArray[sv].count != 0 do 
                    (
                        -- Home-Made undo
                        NumItem = skinOps.GetVertexWeightCount skinMod sv
                        OldWeightArray.count = OldBoneArray.count = NumItem
                        for CurBone = 1 to NumItem do 
                        (
                            OldBoneArray[CurBone] = (skinOps.GetVertexWeightBoneID skinMod sv CurBone)
                            OldWeightArray[CurBone] = (skinOps.GetVertexWeight skinMod sv CurBone)
                        )
                        
                        append LastWeights #(skinMod, sv, deepcopy OldBoneArray, deepcopy OldWeightArray)
                        if UndoWeights.count >= SmoothSkinMaxUndo do deleteItem UndoWeights 1
                        
                        skinOps.ReplaceVertexWeights skinMod sv FinalBoneArray[sv] FinalWeightArray[sv]
                    )    
                    
                    append UndoWeights LastWeights
                                
                    prog = ((p as float / iterNum as float) * 100.0)
                    format "Smoothing Progress:%\n" prog
                )
            ),

            fn undo_smooth_skin = (
                CurUndo = UndoWeights[UndoWeights.count]
                try(
                    if modPanel.GetCurrentObject() != CurUndo[1][1] do (modPanel.setCurrentObject CurUndo[1][1]; subobjectLevel = 1)
                    for i in CurUndo do skinOps.ReplaceVertexWeights i[1] i[2] i[3] i[4]
                )
                catch( print "Undo fail")
                deleteitem UndoWeights UndoWeights.count
                if UndoWeights.count == 0 then return false
            ),

            fn setting inVertMode inRadius inIterNum inKeepMax = (
                vertGroupMode = inVertMode
                smoothRadius = inRadius
                iterNum = inIterNum
                keepMax = inKeepMax
            )
        )
        ''')
        
        if rt.isValidNode(inObj):
            rt.select(inObj)
            rt.execute("max modify mode")
            
            targetSkinMod = self.get_skin_mod(inObj)
            rt.modPanel.setCurrentObject(targetSkinMod[0])

            rt.execute(maxScriptCode)
            smooth_skin = rt._SmoothSkin()
            smooth_skin.setting(inVertMode.value, inRadius, inIterNum, inKeepMax)
            smooth_skin.smooth_skin()