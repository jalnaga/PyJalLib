#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
스킨 모듈 - 3ds Max용 고급 스킨 관련 기능 제공
원본 MAXScript의 skin2.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

import os
from enum import IntEnum
import textwrap
from pymxs import runtime as rt

class VertexMode(IntEnum):
    """
    버텍스 모드 열거형
    """
    Edges = 1
    Attach = 2
    All = 3
    Stiff = 4

class Skin:
    """
    고급 스킨 관련 기능을 제공하는 클래스.
    MAXScript의 ODC_Char_Skin 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self):
        """
        클래스 초기화
        """
        self.skin_match_list = []
    
    def has_skin(self, obj=None):
        """
        객체에 스킨 모디파이어가 있는지 확인
        
        Args:
            obj: 확인할 객체 (기본값: 현재 선택된 객체)
            
        Returns:
            True: 스킨 모디파이어가 있는 경우
            False: 없는 경우
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
        """
        노드가 유효한 스킨 본인지 확인
        
        Args:
            inNode: 확인할 노드
            
        Returns:
            True: 유효한 본인 경우
            False: 아닌 경우
        """
        return (rt.superClassOf(inNode) == rt.GeometryClass or 
                rt.classOf(inNode) == rt.BoneGeometry or 
                rt.superClassOf(inNode) == rt.Helper)
    
    def get_skin_mod(self, obj=None):
        """
        객체의 스킨 모디파이어 배열 반환
        
        Args:
            obj: 모디파이어를 가져올 객체 (기본값: 현재 선택된 객체)
            
        Returns:
            스킨 모디파이어 배열
        """
        if obj is None:
            if len(rt.selection) > 0:
                obj = rt.selection[0]
            else:
                return []
        
        return [mod for mod in obj.modifiers if rt.classOf(mod) == rt.Skin]
    
    def bind_skin(self, obj, bone_array):
        """
        객체에 스킨 모디파이어 바인딩
        
        Args:
            obj: 바인딩할 객체
            bone_array: 바인딩할 본 배열
            
        Returns:
            True: 성공한 경우
            False: 실패한 경우
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
        """
        스킨 모디파이어 최적화
        
        Args:
            skin_mod: 스킨 모디파이어
            bone_limit: 본 제한 수 (기본값: 8)
            skin_tolerance: 스킨 가중치 허용 오차 (기본값: 0.01)
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
        """
        여러 객체의 스킨 최적화 프로세스
        
        Args:
            objs: 최적화할 객체 배열 (기본값: 현재 선택된 객체들)
            optim_all_skin_mod: 모든 스킨 모디파이어 최적화 여부 (기본값: False)
            bone_limit: 본 제한 수 (기본값: 8)
            skin_tolerance: 스킨 가중치 허용 오차 (기본값: 0.01)
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
        """
        스킨 데이터 로드
        
        Args:
            obj: 로드할 객체
            file_path: 스킨 파일 경로
            load_bind_pose: 바인드 포즈 로드 여부
            keep_skin: 기존 스킨 유지 여부
            
        Returns:
            누락된 본 배열
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
        """
        스킨 데이터 저장
        MAXScript의 saveskin.ms 를 Python으로 변환한 함수
        
        Args:
            obj: 저장할 객체 (기본값: 현재 선택된 객체)
            file_path: 저장할 파일 경로 (기본값: None, 자동 생성)
            
        Returns:
            저장된 파일 경로
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
        """
        스킨 모디파이어에서 본 ID 가져오기
        
        Args:
            skin_mod: 스킨 모디파이어
            b_array: 본 배열
            type: 0=객체, 1=객체 이름
            refresh: 인터페이스 업데이트 여부
            
        Returns:
            본 ID 배열
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
        """
        본 이름으로 본 ID 가져오기
        
        Args:
            in_skin_mod: 스킨 모디파이어를 가진 객체
            bone_name: 본 이름
            
        Returns:
            본 ID
        """
        for i in range(1, rt.skinOps.GetNumberBones(in_skin_mod) + 1):
            if rt.skinOps.GetBoneName(in_skin_mod, i, 1) == bone_name:
                return i
        return None
    
    def get_bones_from_skin(self, objs, skin_mod_index):
        """
        스킨 모디파이어에서 사용된 본 배열 가져오기
        
        Args:
            objs: 객체 배열
            skin_mod_index: 스킨 모디파이어 인덱스
            
        Returns:
            본 배열
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
        """
        객체에서 스킨 모디파이어 인덱스 찾기
        
        Args:
            obj: 대상 객체
            
        Returns:
            스킨 모디파이어 인덱스 배열
        """
        return [i+1 for i in range(len(obj.modifiers)) if rt.classOf(obj.modifiers[i]) == rt.Skin]
    
    def sel_vert_from_bones(self, skin_mod, threshold=0.01):
        """
        선택된 본에 영향 받는 버텍스 선택
        
        Args:
            skin_mod: 스킨 모디파이어
            threshold: 가중치 임계값 (기본값: 0.01)
            
        Returns:
            선택된 버텍스 배열
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
        """
        스킨 모디파이어의 모든 버텍스 선택
        
        Args:
            skin_mod: 스킨 모디파이어
            
        Returns:
            선택된 버텍스 배열
        """
        verts_to_sel = []
        
        if skin_mod is not None:
            svc = rt.skinOps.GetNumberVertices(skin_mod)
            
            for o in range(1, svc + 1):
                verts_to_sel.append(o)
                
            rt.skinOps.SelectVertices(skin_mod, verts_to_sel)
            
        return verts_to_sel
    
    def make_rigid_skin(self, skin_mod, vert_list):
        """
        버텍스 가중치를 경직화(rigid) 처리
        
        Args:
            skin_mod: 스킨 모디파이어
            vert_list: 버텍스 리스트
            
        Returns:
            [본 ID 배열, 가중치 배열]
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
    
    def transfert_skin_data(self, obj, source_bones, target_bones, vtx_list):
        """
        스킨 가중치 데이터 이전
        
        Args:
            obj: 대상 객체
            source_bones: 원본 본 배열
            target_bones: 대상 본
            vtx_list: 버텍스 리스트
        """
        skin_data = []
        new_skin_data = []
        
        # 본 ID 가져오기
        source_bones_id = [self.get_bone_id_from_name(obj, b.name) for b in source_bones]
        target_bone_id = self.get_bone_id_from_name(obj, target_bones.name)
        
        bone_list = [n for n in rt.refs.dependsOn(obj.skin) if rt.isValidNode(n) and self.is_valid_bone(n)]
        bone_id_map = {self.get_bone_id_from_name(obj, b.name): i for i, b in enumerate(bone_list)}
        
        # 스킨 데이터 수집
        for vtx in vtx_list:
            bone_array = []
            weight_array = []
            bone_weight = [0] * len(bone_list)
            
            for b in range(1, rt.skinOps.GetVertexWeightCount(obj.skin, vtx) + 1):
                bone_idx = rt.skinOps.GetVertexWeightBoneID(obj.skin, vtx, b)
                bone_weight[bone_id_map[bone_idx]] += rt.skinOps.GetVertexWeight(obj.skin, vtx, b)
                
            for b in range(len(bone_weight)):
                if bone_weight[b] > 0:
                    bone_array.append(b+1)
                    weight_array.append(bone_weight[b])
                    
            skin_data.append([bone_array, weight_array])
            new_skin_data.append([bone_array[:], weight_array[:]])
            
        # 스킨 데이터 이전
        for b, source_bone_id in enumerate(source_bones_id):
            vtx_id = []
            vtx_weight = []
            
            # 원본 본의 가중치 추출
            for vtx in range(len(skin_data)):
                for i in range(len(skin_data[vtx][0])):
                    if skin_data[vtx][0][i] == source_bone_id:
                        vtx_id.append(vtx)
                        vtx_weight.append(skin_data[vtx][1][i])
                        
            # 원본 본 영향력 제거
            for vtx in range(len(vtx_id)):
                for i in range(len(new_skin_data[vtx_id[vtx]][0])):
                    if new_skin_data[vtx_id[vtx]][0][i] == source_bone_id:
                        new_skin_data[vtx_id[vtx]][1][i] = 0.0
                        
            # 타겟 본에 영향력 추가
            for vtx in range(len(vtx_id)):
                id = new_skin_data[vtx_id[vtx]][0].index(target_bone_id) if target_bone_id in new_skin_data[vtx_id[vtx]][0] else -1
                
                if id == -1:
                    new_skin_data[vtx_id[vtx]][0].append(target_bone_id)
                    new_skin_data[vtx_id[vtx]][1].append(vtx_weight[vtx])
                else:
                    new_skin_data[vtx_id[vtx]][1][id] += vtx_weight[vtx]
                    
        # 스킨 데이터 적용
        for i in range(len(vtx_list)):
            rt.skinOps.ReplaceVertexWeights(obj.skin, vtx_list[i], 
                                           skin_data[i][0], new_skin_data[i][1])
            
    def smooth_skin(self, inObj, inVertMode=VertexMode.Edges, inRadius=5.0, inIterNum=3, inKeepMax=False):
        """
        스킨 가중치 부드럽게 하기
        
        Args:
            inObj: 대상 객체
            inVertMode: 버텍스 모드 (기본값: 1)
            inRadius: 반경 (기본값: 5.0)
            inIterNum: 반복 횟수 (기본값: 3)
            inKeepMax: 최대 가중치 유지 여부 (기본값: False)
            
        Returns:
            None
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