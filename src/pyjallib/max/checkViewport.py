#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckViewport 모듈 - 3ds Max 뷰포트 검사 및 초기화 기능
원본 MAXScript의 ODC_Char_AssetChecks_Struct 중 VIEWPORT 섹션을 Python으로 변환
"""

from pymxs import runtime as rt


class CheckViewport:
    """
    뷰포트 상태 검사 및 초기화를 위한 클래스

    뷰포트 비활성화 여부 확인 및 뷰포트 상태 초기화 기능을 제공합니다.
    """

    def __init__(self):
        """
        초기화 함수
        """
        pass

    def is_viewport_disabled(self):
        """
        뷰포트가 비활성화되어 있는지 확인.

        viewport.IsEnabled()가 True이면 뷰포트가 활성 상태이므로,
        비활성화 여부를 반환합니다.

        Returns:
            bool: 뷰포트가 비활성화되어 있으면 True, 활성 상태이면 False
        """
        return not rt.viewport.IsEnabled()

    def reset_viewport(self):
        """
        뷰포트를 초기 상태로 리셋.

        IsolateSelection 해제, 씬 리드로우 활성화, 전체 언하이드,
        뷰 리셋, 디스플레이 컬러 리셋을 수행합니다.

        Returns:
            None
        """
        rt.IsolateSelection.ExitIsolateSelectionMode()
        rt.redrawViews()
        rt.enableSceneRedraw()
        rt.unhide(rt.objects, dolayer=True)
        rt.viewport.ResetAllViews()
        rt.displayColor.shaded = rt.Name("material")
        rt.redrawViews()
