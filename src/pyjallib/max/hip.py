#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hip 모듈 - 3ds Max용 Hip 관련 기능 제공
원본 MAXScript의 hip.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt
from .header import jal


class Hip:
    """
    Hip 관련 기능을 제공하는 클래스.
    MAXScript의 _Hip 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 관련 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 관련 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 관련 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 관련 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 초기화
        self.name = jal.name
        self.anim = jal.anim
        self.helper = jal.helper
        self.bone = jal.bone
        self.const = jal.constraint
        self.bip = jal.bip
        
        # 기본 속성 초기화
        self.bone_size = 2.0
        self.bone_array = []
        self.pelvis_weight = 60.0
        self.thigh_weight = 40.0
        self.x_axis_offset = 0.1
        
        # 객체 참조 초기화
        self.spine_dummy = None
        self.l_hip_dummy = None
        self.l_hip_target_dummy = None
        self.l_hip_exp = None
        self.r_hip_dummy = None
        self.r_hip_target_dummy = None
        self.r_hip_exp = None
        
        self.pelvis = None
        self.spine = None
        self.l_thigh = None
        self.l_thigh_twist = None
        self.r_thigh = None
        self.r_thigh_twist = None
        
        self.helper_array = []
    
    def init(self, in_bip, in_l_thigh_twist, in_r_thigh_twist, 
             in_x_axis_offset=0.1,
             in_pelvis_weight=60.0, in_thigh_weight=40.0,
             in_bone_size=2.0):
        
        self.bone_size = in_bone_size
        self.x_axis_offset = in_x_axis_offset
        
        self.pelvis_weight = in_pelvis_weight
        self.thigh_weight = in_thigh_weight
        
        self.pelvis = self.bip.get_grouped_nodes(in_bip, "pelvis")[0]
        self.spine = rt.biped.getNode(in_bip, rt.Name("spine"), link=1)
        self.l_thigh = rt.biped.getNode(in_bip, rt.Name("lleg"), link=1)
        self.r_thigh = rt.biped.getNode(in_bip, rt.Name("rleg"), link=1)
        self.l_thigh_twist = in_l_thigh_twist
        self.r_thigh_twist = in_r_thigh_twist
        
        self.bone_array = []
        self.helper_array = []
    
    def assign_position_script(self, in_obj, in_exp, in_scale="0.1"):
        """
        위치 스크립트 컨트롤러 할당
        
        Args:
            in_obj: 대상 객체
            in_exp: 표현식 객체 (ExposeTm)
            in_scale: 스케일 값 (문자열)
        """
        # 위치 리스트 컨트롤러 할당
        pos_list = self.const.assign_pos_list(in_obj)
        
        # 위치 스크립트 컨트롤러 생성
        pos_script = rt.position_script()
        rt.setPropertyController(pos_list, "Available", pos_script)
        pos_list.setActive(pos_list.count)
        
        # 표현식 객체 추가 및 스크립트 설정
        pos_script.AddNode("exp", in_exp)
        script_str = ""
        script_str += "zRotValue = amin 0.0 exp.localEulerZ\n"
        script_str += f"result = [0, zRotValue * {in_scale}, 0]\n"
        script_str += "result"
        
        pos_script.SetExpression(script_str)
        pos_script.Update()
        
        # 마지막 컨트롤러 활성화
        self.const.set_active_last(in_obj)
    
    def update_position_script_scale_value(self, in_obj, in_val):
        """
        위치 스크립트 스케일 값 업데이트
        
        Args:
            in_obj: 대상 객체
            in_val: 새 스케일 값
        """
        # 위치 리스트 컨트롤러 가져오기
        pos_list = self.const.get_pos_list_controller(in_obj)
        
        if pos_list is not None and pos_list.count >= 3:
            # 위치 스크립트 컨트롤러 가져오기
            pos_script = rt.getPropertyController(pos_list, "Controller3")
            
            # pos_script가 Position_Script 형태인지 확인
            if rt.classOf(pos_script) == rt.Position_Script:
                new_scale = str(in_val)
                script_str = ""
                script_str += "zRotValue = amin 0.0 exp.localEulerZ\n"
                script_str += f"result = [0, zRotValue * {new_scale}, 0]\n"
                script_str += "result"
                
                pos_script.SetExpression(script_str)
                pos_script.Update()
    
    def gen_helpers(self):
        """
        헬퍼 객체 생성
        
        Returns:
            생성된 헬퍼 객체 배열
        """
        self.spine_dummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_real_name="HipSpine", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=True, cross_toggle=False, axis_toggle=False
        )
        
        self.l_hip_dummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_leftStr(), 
                             in_real_name="Hip", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=True, cross_toggle=False, axis_toggle=False
        )
        
        self.l_hip_target_dummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_leftStr(), 
                             in_real_name="HipTgt", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=False, cross_toggle=True, axis_toggle=False
        )
        
        # ExposeTm 객체 생성
        self.l_hip_exp = rt.ExposeTm(
            name=self.name.combine(in_base=self.base_name, 
                                  in_type=self.name.get_exposeTMStr(), 
                                  in_side=self.name.get_leftStr(), 
                                  in_real_name="Hip", 
                                  in_index="0", 
                                  in_fil_char=self.filtering_char),
            size=1, 
            boxToggle=True, 
            crossToggle=False, 
            wirecolor=rt.color(14, 255, 2)
        )
        
        self.r_hip_dummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_rightStr(), 
                             in_real_name="Hip", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=True, cross_toggle=False, axis_toggle=False
        )
        
        self.r_hip_target_dummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_rightStr(), 
                             in_real_name="HipTgt", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=False, cross_toggle=True, axis_toggle=False
        )
        
        # ExposeTm 객체 생성
        self.r_hip_exp = rt.ExposeTm(
            name=self.name.combine(in_base=self.base_name, 
                                  in_type=self.name.get_exposeTMStr(), 
                                  in_side=self.name.get_rightStr(), 
                                  in_real_name="Hip", 
                                  in_index="0", 
                                  in_fil_char=self.filtering_char),
            size=1, 
            boxToggle=True, 
            crossToggle=False, 
            wirecolor=rt.color(14, 255, 2)
        )
        
        self.helper_array = []
        self.helper_array.append(self.spine_dummy)
        self.helper_array.append(self.l_hip_dummy)
        self.helper_array.append(self.l_hip_target_dummy)
        self.helper_array.append(self.l_hip_exp)
        self.helper_array.append(self.r_hip_dummy)
        self.helper_array.append(self.r_hip_target_dummy)
        self.helper_array.append(self.r_hip_exp)
        
        return self.helper_array
    
    def create(self):
        """
        Hip 리깅 생성
        """
        self.gen_helpers()
        
        self.l_hip_dummy.transform = self.l_thigh_twist.transform
        self.r_hip_dummy.transform = self.r_thigh_twist.transform
        
        self.const.assign_pos_const(self.spine_dummy, self.spine)
        self.const.assign_rot_const_multi(self.spine_dummy, [self.l_thigh_twist, self.r_thigh_twist])
        self.const.collapse(self.spine_dummy)
        
        self.l_hip_dummy.parent = self.pelvis
        self.l_hip_target_dummy.parent = self.pelvis
        self.l_hip_exp.parent = self.pelvis
        self.r_hip_dummy.parent = self.pelvis
        self.r_hip_target_dummy.parent = self.pelvis
        self.r_hip_exp.parent = self.pelvis
        self.spine_dummy.parent = self.pelvis
        
        # 왼쪽 hip dummy의 rotation constraint 설정
        self.const.assign_rot_list(self.l_hip_dummy)
        rot_const = rt.Orientation_Constraint()
        rot_list = self.const.get_rot_list_controller(self.l_hip_dummy)
        rt.setPropertyController(rot_list, "Available", rot_const)
        rot_list.setActive(rot_list.count)
        
        # Constraint 타겟 추가
        rot_const.appendTarget(self.spine_dummy, self.pelvis_weight)
        rot_const.appendTarget(self.l_thigh_twist, self.thigh_weight)
        rot_const.relative = True
        
        # 오른쪽 hip dummy의 rotation constraint 설정
        self.const.assign_rot_list(self.r_hip_dummy)
        rot_const = rt.Orientation_Constraint()
        rot_list = self.const.get_rot_list_controller(self.r_hip_dummy)
        rt.setPropertyController(rot_list, "Available", rot_const)
        rot_list.setActive(rot_list.count)
        
        # Constraint 타겟 추가
        rot_const.appendTarget(self.spine_dummy, self.pelvis_weight)
        rot_const.appendTarget(self.r_thigh_twist, self.thigh_weight)
        rot_const.relative = True
        
        self.l_hip_target_dummy.transform = self.l_hip_dummy.transform
        self.l_hip_exp.transform = self.l_hip_dummy.transform
        self.r_hip_target_dummy.transform = self.r_hip_dummy.transform
        self.r_hip_exp.transform = self.r_hip_dummy.transform
        
        self.l_hip_exp.exposeNode = self.l_hip_dummy
        self.l_hip_exp.localReferenceNode = self.l_hip_target_dummy
        self.l_hip_exp.useParent = False
        
        self.r_hip_exp.exposeNode = self.r_hip_dummy
        self.r_hip_exp.localReferenceNode = self.r_hip_target_dummy
        self.r_hip_exp.useParent = False
        
        self.bone_array = []
        
        # 왼쪽 Hip 본 생성
        l_hip_bone = self.bone.create_simple_bone(
            (self.bone_size * 2),
            self.name.combine(
                in_base=self.base_name,
                in_side=self.name.get_leftStr(),
                in_real_name="Hip",
                in_fil_char=self.filtering_char
            ),
            size=self.bone_size
        )
        
        l_hip_bone[0].transform = self.l_thigh.transform
        self.anim.rotate_local(
            l_hip_bone[0], 
            (self.rot_dir[0] * 0), 
            (self.rot_dir[1] * 0), 
            (self.rot_dir[2] * 90)
        )
        l_hip_bone[0].parent = self.l_hip_dummy
        self.bone_array.append(l_hip_bone[0])
        self.bone_array.append(l_hip_bone[1])
        
        # 오른쪽 Hip 본 생성
        r_hip_bone = self.bone.create_simple_bone(
            (self.bone_size * 2),
            self.name.combine(
                in_base=self.base_name,
                in_side=self.name.get_rightStr(),
                in_real_name="Hip",
                in_fil_char=self.filtering_char
            ),
            size=self.bone_size
        )
        
        r_hip_bone[0].transform = self.r_thigh.transform
        self.anim.rotate_local(
            r_hip_bone[0], 
            (self.rot_dir[0] * 0), 
            (self.rot_dir[1] * 0), 
            (self.rot_dir[2] * 90)
        )
        r_hip_bone[0].parent = self.r_hip_dummy
        self.bone_array.append(r_hip_bone[0])
        self.bone_array.append(r_hip_bone[1])
        
        # 위치 스크립트 설정
        self.assign_position_script(l_hip_bone[0], self.l_hip_exp, in_scale=str(self.x_axis_offset))
        self.assign_position_script(r_hip_bone[0], self.r_hip_exp, in_scale=str(self.x_axis_offset))
    
    def del_all(self):
        """
        모든 생성된 본과 헬퍼 객체 삭제
        """
        self.bone.delete_bones_safely(self.bone_array)
        self.bone.delete_bones_safely(self.helper_array)
    
    def set_weight(self, in_pelvis_weight, in_thigh_weight):
        """
        골반과 허벅지 가중치 설정
        
        Args:
            in_pelvis_weight: 골반 가중치
            in_thigh_weight: 허벅지 가중치
        """
        self.del_all()
        self.pelvis_weight = in_pelvis_weight
        self.thigh_weight = in_thigh_weight
        
        self.create()