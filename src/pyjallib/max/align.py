#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 정렬 모듈

3ds Max에서 객체 정렬을 위한 기능을 제공하는 모듈입니다.

## 주요 기능
- 선택된 객체들을 마지막 선택된 객체 기준으로 정렬
- 위치만 정렬하거나 회전만 정렬하는 기능
- 중심점 기준 정렬 기능

## 구현 정보
- 원본 MAXScript의 align.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt


class Align:
    """
    # Align 클래스
    
    3ds Max에서 객체 정렬 기능을 제공하는 클래스입니다.
    
    ## 주요 기능
    - 마지막 선택된 객체로 정렬 (위치, 회전, 모두)
    - 마지막 선택된 객체의 중심점으로 정렬
    - 위치만 정렬하거나 회전만 정렬하는 기능
    
    ## 구현 정보
    - MAXScript의 _Align 구조체를 Python 클래스로 재구현
    - pymxs API를 통해 3ds Max 객체 트랜스폼 조작
    
    ## 사용 예시
    ```python
    # 정렬 객체 생성
    aligner = Align()
    
    # 마지막 선택된 객체의 트랜스폼으로 정렬
    aligner.align_to_last_sel()
    
    # 마지막 선택된 객체의 위치만 적용 (회전은 유지)
    aligner.align_to_last_sel_pos()
    ```
    """
    
    def __init__(self):
        """
        Align 클래스 초기화
        
        현재는 특별한 초기화 작업이 필요하지 않습니다.
        """
        pass
    
    def align_to_last_sel_center(self):
        """
        선택된 객체들을 마지막 선택된 객체의 중심점으로 정렬합니다.
        
        ## 동작 방식
        - 모든 객체의 트랜스폼은 마지막 선택된 객체의 트랜스폼을 적용받습니다.
        - 위치는 마지막 선택된 객체의 중심점(center)으로 설정됩니다.
        
        ## 주의사항
        - 2개 이상의 객체가 선택되어 있어야 작동합니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
                rt.setProperty(rt.selection[i], "transform", rt.selection[selection_count-1].transform)
                rt.setProperty(rt.selection[i], "position", rt.selection[selection_count-1].center)
    
    def align_to_last_sel(self):
        """
        선택된 객체들을 마지막 선택된 객체의 트랜스폼으로 정렬합니다.
        
        ## 동작 방식
        - 모든 객체의 위치와 회전이 마지막 선택된 객체의 트랜스폼과 동일하게 설정됩니다.
        - 객체의 크기(스케일)는 변경되지 않습니다.
        
        ## 주의사항
        - 2개 이상의 객체가 선택되어 있어야 작동합니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
                # 인덱스가 0부터 시작하는 Python과 달리 MAXScript는 1부터 시작하므로 i+1 사용
                rt.selection[i].transform = rt.selection[selection_count-1].transform
    
    def align_to_last_sel_pos(self):
        """
        선택된 객체들을 마지막 선택된 객체의 위치로만 정렬합니다.
        
        ## 동작 방식
        - 위치만 마지막 선택된 객체를 따르고 회전은 원래 객체의 회전 유지
        - Position_Constraint와 Orientation_Constraint를 사용하여 구현
        - 임시 포인트 객체를 생성하여 변환 계산 후 적용
        
        ## 주의사항
        - 2개 이상의 객체가 선택되어 있어야 작동합니다.
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
        선택된 객체들을 마지막 선택된 객체의 회전으로만 정렬합니다.
        
        ## 동작 방식
        - 회전만 마지막 선택된 객체를 따르고 위치는 원래 객체의 위치 유지
        - Position_Constraint와 Orientation_Constraint를 사용하여 구현
        - 임시 포인트 객체를 생성하여 변환 계산 후 적용
        
        ## 주의사항
        - 2개 이상의 객체가 선택되어 있어야 작동합니다.
        """
        selection_count = rt.selection.count
        
        if selection_count > 1:
            for i in range(selection_count):
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
                


                rt.delete(rot_dum_point)                # 임시 객체 삭제                rt.delete(rot_dum_point)
