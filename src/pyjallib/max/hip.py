#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hip 모듈 - 3ds Max용 Hip 관련 기능 제공
원본 MAXScript의 hip.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint


class Hip:
    """
    Hip 관련 기능을 제공하는 클래스.
    MAXScript의 _Hip 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None):
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
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.const = constraintService if constraintService else Constraint(nameService=self.name, helperService=self.helper)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim, helperService=self.helper, constraintService=self.const)
        
        # 기본 속성 초기화
        self.boneSize = 2.0
        self.boneArray = []
        self.pelvisWeight = 60.0
        self.thighWeight = 40.0
        self.xAxisOffset = 0.1
        
        # 객체 참조 초기화
        self.spineDummy = None
        self.lHipDummy = None
        self.lHipTargetDummy = None
        self.lHipExp = None
        self.rHipDummy = None
        self.rHipTargetDummy = None
        self.rHipExp = None
        
        self.pelvis = None
        self.spine = None
        self.lThigh = None
        self.lThighTwist = None
        self.rThigh = None
        self.rThighTwist = None
        
        self.helperArray = []
    
    def init(self, in_pelvis, in_spine, in_l_thigh, in_r_thigh, in_l_thigh_twist, in_r_thigh_twist, 
             in_x_axis_offset=0.1,
             in_pelvis_weight=60.0, in_thigh_weight=40.0,
             in_bone_size=2.0):
        
        self.boneSize = in_bone_size
        self.xAxisOffset = in_x_axis_offset
        
        self.pelvisWeight = in_pelvis_weight
        self.thighWeight = in_thigh_weight
        
        self.pelvis = in_pelvis
        self.spine = in_spine
        self.lThigh = in_l_thigh
        self.rThigh = in_r_thigh
        self.lThighTwist = in_l_thigh_twist
        self.rThighTwist = in_r_thigh_twist
        
        self.boneArray = []
        self.helperArray = []
    
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
        pos_script.addNode("exp", in_exp)
        pos_script.addConstant("xOffsetScale", in_scale)
        script_str = ""
        script_str += "zRotValue = amin 0.0 exp.localEulerZ\n"
        script_str += f"result = [0, zRotValue * xOffsetScale, 0]\n"
        script_str += "result"
        
        pos_script.setExpession(script_str)
        pos_script.update()
        
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
        self.spineDummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_real_name="HipSpine", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=True, cross_toggle=False, axis_toggle=False
        )
        
        self.lHipDummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_leftStr(), 
                             in_real_name="Hip", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=True, cross_toggle=False, axis_toggle=False
        )
        
        self.lHipTargetDummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_leftStr(), 
                             in_real_name="HipTgt", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=False, cross_toggle=True, axis_toggle=False
        )
        
        # ExposeTm 객체 생성
        self.lHipExp = rt.ExposeTm(
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
        
        self.rHipDummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_rightStr(), 
                             in_real_name="Hip", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=True, cross_toggle=False, axis_toggle=False
        )
        
        self.rHipTargetDummy = self.helper.create_point(
            self.name.combine(in_base=self.base_name, 
                             in_type=self.name.get_dummyStr(), 
                             in_side=self.name.get_rightStr(), 
                             in_real_name="HipTgt", 
                             in_index="0", 
                             in_fil_char=self.filtering_char),
            box_toggle=False, cross_toggle=True, axis_toggle=False
        )
        
        # ExposeTm 객체 생성
        self.rHipExp = rt.ExposeTm(
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
        
        self.helperArray = []
        self.helperArray.append(self.spineDummy)
        self.helperArray.append(self.lHipDummy)
        self.helperArray.append(self.lHipTargetDummy)
        self.helperArray.append(self.lHipExp)
        self.helperArray.append(self.rHipDummy)
        self.helperArray.append(self.rHipTargetDummy)
        self.helperArray.append(self.rHipExp)
        
        return self.helperArray
    
    def create(self):
        """
        Hip 리깅 생성
        """
        self.gen_helpers()
        
        self.lHipDummy.transform = self.lThighTwist.transform
        self.rHipDummy.transform = self.rThighTwist.transform
        
        self.const.assign_pos_const(self.spineDummy, self.spine)
        self.const.assign_rot_const_multi(self.spineDummy, [self.lThighTwist, self.rThighTwist])
        self.const.collapse(self.spineDummy)
        
        self.lHipDummy.parent = self.pelvis
        self.lHipTargetDummy.parent = self.pelvis
        self.lHipExp.parent = self.pelvis
        self.rHipDummy.parent = self.pelvis
        self.rHipTargetDummy.parent = self.pelvis
        self.rHipExp.parent = self.pelvis
        self.spineDummy.parent = self.pelvis
        
        # 왼쪽 hip dummy의 rotation constraint 설정
        self.const.assign_rot_list(self.lHipDummy)
        rot_const = rt.Orientation_Constraint()
        rot_list = self.const.get_rot_list_controller(self.lHipDummy)
        rt.setPropertyController(rot_list, "Available", rot_const)
        rot_list.setActive(rot_list.count)
        
        # Constraint 타겟 추가
        rot_const.appendTarget(self.spineDummy, self.pelvisWeight)
        rot_const.appendTarget(self.lThighTwist, self.thighWeight)
        rot_const.relative = True
        
        # 오른쪽 hip dummy의 rotation constraint 설정
        self.const.assign_rot_list(self.rHipDummy)
        rot_const = rt.Orientation_Constraint()
        rot_list = self.const.get_rot_list_controller(self.rHipDummy)
        rt.setPropertyController(rot_list, "Available", rot_const)
        rot_list.setActive(rot_list.count)
        
        # Constraint 타겟 추가
        rot_const.appendTarget(self.spineDummy, self.pelvisWeight)
        rot_const.appendTarget(self.rThighTwist, self.thighWeight)
        rot_const.relative = True
        
        self.lHipTargetDummy.transform = self.lHipDummy.transform
        self.lHipExp.transform = self.lHipDummy.transform
        self.rHipTargetDummy.transform = self.rHipDummy.transform
        self.rHipExp.transform = self.rHipDummy.transform
        
        self.lHipExp.exposeNode = self.lHipDummy
        self.lHipExp.localReferenceNode = self.lHipTargetDummy
        self.lHipExp.useParent = False
        
        self.rHipExp.exposeNode = self.rHipDummy
        self.rHipExp.localReferenceNode = self.rHipTargetDummy
        self.rHipExp.useParent = False
        
        self.boneArray = []
        
        # 왼쪽 Hip 본 생성
        l_hip_bone = self.bone.create_simple_bone(
            (self.boneSize * 2),
            self.name.combine(
                in_base=self.base_name,
                in_side=self.name.get_leftStr(),
                in_real_name="Hip",
                in_fil_char=self.filtering_char
            ),
            size=self.boneSize
        )
        
        l_hip_bone[0].transform = self.lThigh.transform
        self.anim.rotate_local(
            l_hip_bone[0], 
            (self.rot_dir[0] * 0), 
            (self.rot_dir[1] * 0), 
            (self.rot_dir[2] * 90)
        )
        l_hip_bone[0].parent = self.lHipDummy
        self.boneArray.append(l_hip_bone[0])
        self.boneArray.append(l_hip_bone[1])
        
        # 오른쪽 Hip 본 생성
        r_hip_bone = self.bone.create_simple_bone(
            (self.boneSize * 2),
            self.name.combine(
                in_base=self.base_name,
                in_side=self.name.get_rightStr(),
                in_real_name="Hip",
                in_fil_char=self.filtering_char
            ),
            size=self.boneSize
        )
        
        r_hip_bone[0].transform = self.rThigh.transform
        self.anim.rotate_local(
            r_hip_bone[0], 
            (self.rot_dir[0] * 0), 
            (self.rot_dir[1] * 0), 
            (self.rot_dir[2] * 90)
        )
        r_hip_bone[0].parent = self.rHipDummy
        self.boneArray.append(r_hip_bone[0])
        self.boneArray.append(r_hip_bone[1])
        
        # 위치 스크립트 설정
        self.assign_position_script(l_hip_bone[0], self.lHipExp, in_scale=str(self.xAxisOffset))
        self.assign_position_script(r_hip_bone[0], self.rHipExp, in_scale=str(self.xAxisOffset))
    
    def del_all(self):
        """
        모든 생성된 본과 헬퍼 객체 삭제
        """
        self.bone.delete_bones_safely(self.boneArray)
        self.bone.delete_bones_safely(self.helperArray)
    
    def set_weight(self, in_pelvis_weight, in_thigh_weight):
        """
        골반과 허벅지 가중치 설정
        
        Args:
            in_pelvis_weight: 골반 가중치
            in_thigh_weight: 허벅지 가중치
        """
        self.del_all()
        self.pelvisWeight = in_pelvis_weight
        self.thighWeight = in_thigh_weight
        
        self.create()