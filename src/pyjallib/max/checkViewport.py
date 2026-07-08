#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckViewport 모듈 - 3ds Max 뷰포트 검사 및 초기화 기능
원본 MAXScript의 ODC_Char_AssetChecks_Struct 중 VIEWPORT 섹션을 Python으로 변환
"""

from pymxs import runtime as rt


class CheckViewport:
    """3ds Max 뷰포트의 비활성화 여부를 검사하고 뷰포트 상태를 초기화하는 클래스."""

    def __init__(self):
        """CheckViewport를 초기화한다."""
        pass

    def is_viewport_disabled(self):
        """뷰포트가 비활성화되어 있는지 확인한다.

        viewport.IsEnabled()의 결과를 반전하여 반환한다.

        Returns:
            bool: 뷰포트가 비활성화되어 있으면 True, 활성 상태이면 False
        """
        return not rt.viewport.IsEnabled()

    def reset_viewport(self):
        """뷰포트를 초기 상태로 리셋한다.

        IsolateSelection 해제, 씬 리드로우 활성화, 전체 언하이드,
        전체 뷰 리셋, 셰이딩 디스플레이 컬러 리셋(material)을 수행한다.
        """
        rt.IsolateSelection.ExitIsolateSelectionMode()
        rt.redrawViews()
        rt.enableSceneRedraw()
        rt.unhide(rt.objects, dolayer=True)
        rt.viewport.ResetAllViews()
        rt.displayColor.shaded = rt.Name("material")
        rt.redrawViews()
