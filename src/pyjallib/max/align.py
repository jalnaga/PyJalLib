#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
정렬 모듈 - 3ds Max용 객체 정렬 관련 기능 제공
원본 MAXScript의 align.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt


class Align:
    """
    객체 정렬 관련 기능을 제공하는 클래스.
    MAXScript의 _Align 구조체 개념을 Python으로 재구현한 클래스이며, 3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self):
        """클래스 초기화 (현재 특별한 초기화 동작은 없음)"""
        pass
    
    def align_to_last_sel_center(self):
        """
        선택된 객체들을 마지막 선택된 객체의 중심점으로 정렬.
        
        모든 객체의 트랜스폼은 마지막 선택된 객체의 트랜스폼을 가지며,
        위치는 마지막 선택된 객체의 중심점(center)으로 설정됩니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
                rt.setProperty(rt.selection[i], "transform", rt.selection[selection_count-1].transform)
                rt.setProperty(rt.selection[i], "position", rt.selection[selection_count-1].center)
    
    def align_to_last_sel(self):
        """
        선택된 객체들을 마지막 선택된 객체의 트랜스폼으로 정렬.
        
        모든 객체의 트랜스폼은 마지막 선택된 객체의 트랜스폼을 가지게 됩니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
                # 인덱스가 0부터 시작하는 Python과 달리 MAXScript는 1부터 시작하므로 i+1 사용
                rt.selection[i].transform = rt.selection[selection_count-1].transform
    
    def align_to_last_sel_pos(self):
        """
        선택된 객체들을 마지막 선택된 객체의 위치로 정렬 (회전은 유지).
        
        위치는 마지막 선택된 객체를 따르고,
        회전은 원래 객체의 회전을 유지합니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
                # 임시 포인트 객체 생성
                pos_dum_point = rt.Point()
                # 위치와 회전 제약 컨트롤러 생성
                pos_const = rt.Position_Constraint()
                rot_const = rt.Orientation_Constraint()
                
                # 포인트에 컨트롤러 할당
                rt.setPropertyController(pos_dum_point.controller, "Position", pos_const)
                rt.setPropertyController(pos_dum_point.controller, "Rotation", rot_const)
                
                # 위치는 마지막 선택된 객체 기준, 회전은 현재 처리 중인 객체 기준
                pos_const.appendTarget(rt.selection[selection_count-1], 100.0)
                rot_const.appendTarget(rt.selection[i], 100.0)
                
                # 계산된 변환 행렬을 객체에 적용
                rt.setProperty(rt.selection[i], "transform", pos_dum_point.transform)
                
                # 임시 객체 삭제
                rt.delete(pos_dum_point)
    
    def align_to_last_sel_rot(self):
        """
        선택된 객체들을 마지막 선택된 객체의 회전으로 정렬 (위치는 유지).
        
        회전은 마지막 선택된 객체를 따르고,
        위치는 원래 객체의 위치를 유지합니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
                # 인덱스가 0부터 시작하는 Python과 달리 MAXScript는 1부터 시작하므로 i+1 사용
                # 임시 포인트 객체 생성
                rot_dum_point = rt.Point()
                # 위치와 회전 제약 컨트롤러 생성
                pos_const = rt.Position_Constraint()
                rot_const = rt.Orientation_Constraint()
                
                # 포인트에 컨트롤러 할당
                rot_dum_point.position.controller = pos_const
                rot_dum_point.rotation.controller = rot_const
                rt.setPropertyController(rot_dum_point.controller, "Position", pos_const)
                rt.setPropertyController(rot_dum_point.controller, "Rotation", rot_const)
                
                # 위치는 현재 처리 중인 객체 기준, 회전은 마지막 선택된 객체 기준
                pos_const.appendTarget(rt.selection[i], 100.0)
                rot_const.appendTarget(rt.selection[selection_count-1], 100.0)
                
                # 계산된 변환 행렬을 객체에 적용
                rt.setProperty(rt.selection[i], "transform", rot_dum_point.transform)
                
                # 임시 객체 삭제
                rt.delete(rot_dum_point)
