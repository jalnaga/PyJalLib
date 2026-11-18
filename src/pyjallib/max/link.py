#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Link 모듈 - 3ds Max 객체 연결 관련 기능
원본 MAXScript의 link.ms를 Python으로 변환
"""

from pymxs import runtime as rt

class Link:
    """3ds Max 객체 간 부모-자식 연결(링크)과 해제 기능을 제공하는 클래스."""
    
    def __init__(self):
        """클래스를 초기화한다."""
        pass
    
    def link_to_last_sel(self):
        """선택된 객체들을 마지막 선택 객체에 링크한다.

        선택이 2개 이상일 때 마지막 객체를 나머지 모든 객체의 부모로 지정한다.
        """
        # 선택된 객체가 2개 이상인 경우에만 처리
        if rt.selection.count > 1:
            # 첫 번째부터 마지막 직전까지의 모든 객체를 마지막 객체에 링크
            for i in range(rt.selection.count - 1):
                rt.selection[i].parent = rt.selection[rt.selection.count - 1]
    
    def link_to_first_sel(self):
        """선택된 객체들을 첫 번째 선택 객체에 링크한다.

        선택이 2개 이상일 때 첫 번째 객체를 나머지 모든 객체의 부모로 지정한다.
        """
        # 선택된 객체가 2개 이상인 경우에만 처리
        if rt.selection.count > 1:
            # 두 번째부터 마지막까지의 모든 객체를 첫 번째 객체에 링크
            for i in range(1, rt.selection.count):
                rt.selection[i].parent = rt.selection[0]
    
    def unlink_selection(self):
        """선택된 모든 객체의 부모 관계를 해제한다."""
        # 선택된 객체가 있는 경우에만 처리
        if rt.selection.count > 0:
            # 모든 선택 객체의 부모 관계 해제
            for item in rt.selection:
                item.parent = None
    
    def unlink_children(self):
        """선택된 객체의 모든 자식 객체의 부모 관계를 해제한다.

        정확히 하나의 객체가 선택된 경우에만 동작한다.
        """
        # 정확히 하나의 객체가 선택된 경우에만 처리
        if rt.selection.count == 1:
            # 선택된 객체의 모든 자식 객체의 부모 관계 해제
            selObjs = rt.getCurrentSelection()
            childrenObjs = selObjs[0].children
            targetChildren = [child for child in childrenObjs]
            for child in targetChildren:
                child.parent = None