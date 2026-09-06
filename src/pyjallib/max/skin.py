#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
스킨 모듈 - 3ds Max용 고급 스킨 관련 기능 제공
원본 MAXScript의 skin2.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

import os
from enum import IntEnum
import textwrap
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
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
    
    def load_skin(self, obj, file_path, load_bind_pose=False, keep_skin=False):
        """스킨 데이터 파일을 읽어 객체에 새 스킨 모디파이어를 생성하고 가중치를 적용한다.

        파일에 기록된 본이 씬에 없으면 같은 이름의 Dummy를 생성해 대체한다.

        Args:
            obj (rt.Node): 스킨을 적용할 객체
            file_path (str): 스킨 데이터 파일 경로
            load_bind_pose (bool): 바인드 포즈 파일을 함께 로드해 적용할지 여부
            keep_skin (bool): 기존 스킨 모디파이어 유지 여부. False면 기존 스킨을 모두 삭제한다.

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
        rt.addModifier(obj, new_skin, before=1 if keep_skin else 0)
        
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
        3. 이전 대상 본이 이 Skin에 없으면 ``addBone(skin, node, 0)``으로 먼저 넣고 대조표를
           다시 만든다(기존 본 ID는 유지된다). 새 본의 bind 행렬은 "지금" 트랜스폼이므로
           씬이 bind pose여야 정확하다 - 이 경우 ``warnings``에 경고를 넣는다.
        4. 원본 본에 가중치가 있는 버텍스만 ``merge_vertex_weights``로 합산해
           ``ReplaceVertexWeights``로 쓴다. 쓴 직후 앞쪽 표본(``inVerifySampleLimit``개)을
           재조회해 원본 본 잔여 가중치가 0인지 확인한다(호출 성공 ≠ 효과).
        5. ``inRemoveHandles``의 본을 ``removeBone``으로 **ID 내림차순** 제거한다(제거 시 ID가
           밀린다). ``inRemoveHandles``가 비어 있으면 이 단계와 6을 건너뛴다.
        6. 제거 후 대조표를 재조회해 제거 본이 남아 있지 않음을 단정한다.
        7. 선택을 복원한다(예외 시에도).

        **``ReplaceVertexWeights``는 버텍스를 재정규화한다.** 이전과 무관한 본의 가중치도
        float32 ULP 수준(약 4.5e-8)으로 바뀔 수 있으므로 "바이트 동일"을 기대하지 않는다.

        Args:
            inNode: Skin이 붙은 노드
            inSkinMod: Skin 모디파이어
            inTransferByHandle: ``{원본 본 핸들: 대상 본 핸들}``. 여러 원본이 한 대상을 가리켜도 된다
            inRemoveHandles: Skin에서 제거할 본 핸들 집합. 빈 집합이면 이전만 한다
            inVertexWeights: 미리 읽어 둔 ``get_vertex_weights`` 결과. None이면 여기서 읽는다
            inVertexIndices: 대상 버텍스(1-based). None이면 전 버텍스. ``inVertexWeights``가 함께
                주어지면 그 안에서 이 인덱스만 쓴다
            inVerifySampleLimit: 쓰기 직후 재조회 검증할 버텍스 수 상한. 기본 64

        Returns:
            ``{"transferred": {원본 본 핸들: {"target": 대상 핸들, "verts": int, "weightSum": float}},
            "removedBones": [이름 정렬], "addedBones": [이름], "touchedVerts": int,
            "warnings": [str]}``

        Raises:
            RuntimeError: ① ``inRemoveHandles`` 중 가중치가 있는 본에 이전 대상이 없다
                ② 이전 대상 본이 씬에 없거나 ``addBone`` 효과가 없다
                ③ 표본 재조회에서 원본 본 잔여 가중치가 남았다
                ④ 제거 후 제거 본이 Skin에 남아 있다
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

            # 대상 본이 Skin에 없으면 addBone 후 대조표 재구성
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
                sourceBoneIds = {
                    bid for bid in usedBoneIds if table[bid]["handle"] in transferByHandle
                }

            remap: Dict[int, int] = {
                bid: idsByHandle[transferByHandle[table[bid]["handle"]]] for bid in sourceBoneIds
            }

            # 버텍스별 합산 → ReplaceVertexWeights
            transferred: Dict[int, Dict[str, Any]] = {}
            touchedCount = 0
            verified = 0
            for vertIndex, entries in weights.items():
                ids, ws, touched = merge_vertex_weights(entries, remap)
                if not touched:
                    continue
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

            return {
                "transferred": transferred,
                "removedBones": removedBones,
                "addedBones": addedBones,
                "touchedVerts": touchedCount,
                "warnings": warnings,
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