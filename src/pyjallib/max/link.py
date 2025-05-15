#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# Link 모듈

3ds Max에서 객체 간 계층 구조(부모-자식 관계)를 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 선택된 객체들 간 링크 생성
- 첫 번째 또는 마지막 선택 객체를 기준으로 링크
- 객체의 부모 연결 해제
- 자식 객체들의 부모 연결 해제

## 구현 정보
- 원본 MAXScript의 link.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
"""

from pymxs import runtime as rt

class Link:
    """
    # Link 클래스
    
    3ds Max에서 객체 간 계층 구조(부모-자식 관계)를 관리하는 기능을 제공합니다.
    
    ## 주요 기능
    - 선택된 객체들을 첫 번째 또는 마지막 선택 객체에 링크
    - 선택된 객체들의 부모 관계 해제
    - 선택된 객체의 모든 자식 객체의 부모 관계 해제
    
    ## 구현 정보
    - MAXScript의 _Link 구조체를 Python 클래스로 재구현
    - pymxs 모듈을 통해 3ds Max의 부모-자식 관계 직접 제어
    
    ## 사용 예시
    ```python
    # Link 객체 생성
    link_mgr = Link()
    
    # 선택된 객체들을 첫 번째 선택 객체에 링크
    link_mgr.link_to_first_sel()
    
    # 선택된 객체들의 부모 관계 해제
    link_mgr.unlink_selection()
    ```
    """
    
    def __init__(self):
        """
        Link 클래스를 초기화합니다.
        """
        pass
    
    def link_to_last_sel(self):
        """
        선택된 객체들을 마지막 선택 객체에 링크(부모로 지정)합니다.
        
        ## 동작 방식
        1. 선택된 객체가 2개 이상인지 확인
        2. 첫 번째부터 마지막 직전까지의 모든 객체의 부모를 마지막 객체로 설정
        """
        # 선택된 객체가 2개 이상인 경우에만 처리
        if rt.selection.count > 1:
            # 첫 번째부터 마지막 직전까지의 모든 객체를 마지막 객체에 링크
            for i in range(rt.selection.count - 1):
                rt.selection[i].parent = rt.selection[rt.selection.count - 1]
    
    def link_to_first_sel(self):
        """
        선택된 객체들을 첫 번째 선택 객체에 링크(부모로 지정)합니다.
        
        ## 동작 방식
        1. 선택된 객체가 2개 이상인지 확인
        2. 두 번째부터 마지막까지의 모든 객체의 부모를 첫 번째 객체로 설정
        """
        # 선택된 객체가 2개 이상인 경우에만 처리
        if rt.selection.count > 1:
            # 두 번째부터 마지막까지의 모든 객체를 첫 번째 객체에 링크
            for i in range(1, rt.selection.count):
                rt.selection[i].parent = rt.selection[0]
    
    def unlink_selection(self):
        """
        선택된 모든 객체의 부모 관계를 해제합니다.
        
        ## 동작 방식
        선택된 각 객체의 부모 속성을 None으로 설정하여 부모 관계 해제
        """
        # 선택된 객체가 있는 경우에만 처리
        if rt.selection.count > 0:
            # 모든 선택 객체의 부모 관계 해제
            for item in rt.selection:
                item.parent = None
    
    def unlink_children(self):
        """
        선택된 객체의 모든 자식 객체의 부모 관계를 해제합니다.
        
        ## 동작 방식
        1. 정확히 하나의 객체가 선택되었는지 확인
        2. 선택된 객체의 모든 직계 자식 객체를 가져옴
        3. 각 자식 객체의 부모 속성을 None으로 설정
        """
        # 정확히 하나의 객체가 선택된 경우에만 처리
        if rt.selection.count == 1:
            # 선택된 객체의 모든 자식 객체의 부모 관계 해제
            selObjs = rt.getCurrentSelection()
            childrenObjs = selObjs[0].children
            targetChildren = [child for child in childrenObjs]
            for child in targetChildren:
                child.parent = None