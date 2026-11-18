#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ToolManager 모듈 - 3DS Max에서 실행되는 도구들을 관리
도구 인스턴스 생성, 닫기 등을 담당
"""

from PySide2 import QtWidgets, QtCore
import gc

class ToolManager:
    """3DS Max에서 실행되는 도구(툴) 인스턴스의 등록·닫기·표시 등 라이프사이클을 통합 관리한다."""
    def __init__(self):
        """ToolManager 클래스를 초기화한다."""
        self.tools = {}  # {tool_class_name: [instances]} 형태로 관리
    
    def register_tool(self, tool_instance):
        """도구 인스턴스를 클래스 이름 기준으로 등록한다.

        Args:
            tool_instance (object): 등록할 도구 인스턴스
        """
        class_name = tool_instance.__class__.__name__
        
        if class_name not in self.tools:
            self.tools[class_name] = []
            
        self.tools[class_name].append(tool_instance)
    
    def close_tool_by_type(self, tool_class):
        """특정 클래스의 모든 도구 인스턴스를 닫고 정리한다.

        등록된 인스턴스를 close·deleteLater로 정리하고, QApplication의
        전체 위젯에서도 동일 클래스/타이틀의 QDialog를 찾아 닫은 뒤
        가비지 컬렉션을 수행한다.

        Args:
            tool_class (type): 닫을 도구의 클래스
        """
        class_name = tool_class.__name__
        
        if class_name not in self.tools:
            return
            
        # 해당 클래스의 모든 인스턴스 정리
        for tool in self.tools[class_name]:
            try:
                if hasattr(tool, 'close'):
                    tool.close()
                if hasattr(tool, 'deleteLater'):
                    tool.deleteLater()
            except (RuntimeError, AttributeError) as e:
                print(f"도구 닫기 오류: {e}")
                
        # 목록 비우기
        self.tools[class_name] = []
        
        # 추가적으로 QApplication.allWidgets()를 통한 검사
        try:
            window_title = None
            if hasattr(tool_class, 'windowTitle'):
                window_title = tool_class.windowTitle
            
            for widget in QtWidgets.QApplication.allWidgets():
                if (isinstance(widget, QtWidgets.QDialog) and 
                    ((window_title and hasattr(widget, 'windowTitle') and widget.windowTitle() == window_title) or
                     widget.__class__.__name__ == class_name)):
                    try:
                        widget.close()
                        widget.deleteLater()
                    except:
                        pass
        except Exception as e:
            print(f"위젯 검색 오류: {e}")
            
        # 가비지 컬렉션 수행
        gc.collect()
    
    def show_tool(self, tool_class, **kwargs):
        """기존 인스턴스를 모두 닫고 도구의 새 인스턴스를 생성하여 표시한다.

        중복 실행을 방지하며 항상 새 인스턴스를 생성한다.

        Args:
            tool_class (type): 표시할 도구 클래스
            **kwargs: 도구 클래스 생성자에 전달할 인자들

        Returns:
            object: 새로 생성된 도구 인스턴스
        """
        # 기존 인스턴스 모두 정리
        self.close_tool_by_type(tool_class)
        
        # 약간의 지연을 두어 정리 완료를 기다림
        QtCore.QTimer.singleShot(50, lambda: None)
        
        # 새 인스턴스 생성
        tool_instance = tool_class(**kwargs)
        
        # 도구 등록
        self.register_tool(tool_instance)
        
        # 도구 표시
        tool_instance.show()
        
        return tool_instance 