#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FBXHandler 모듈
3ds Max에서 FBX 파일을 익스포트/임포트하는 기능을 제공
이 모듈은 pymxs를 사용하여 3ds Max와 통신하며, FBX 익스포트 및 임포트 옵션을 설정하고 파일을 처리합니다.
"""

from pymxs import runtime as rt
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

class FBXHandler:
    """
    3ds Max FBX 파일 익스포트/임포트를 위한 클래스
    pymxs를 사용하여 3ds Max와 통신
    """
    
    def __init__(self):
        """FBX 핸들러 초기화"""
        self._setup_fbx_plugin()
    
    def _setup_fbx_plugin(self):
        """FBX 플러그인 로드 및 초기화"""
        rt.pluginManager.loadClass(rt.FbxExporter)
        rt.pluginManager.loadClass(rt.FbxImporter)
    
    def _get_export_fbx_class_index(self) -> int:
        """FBX 익스포터 클래스 인덱스 가져오기"""
        exporterPlugin = rt.exporterPlugin
        for i, cls in enumerate(exporterPlugin.classes):
            if "FBX" in str(cls):
                return i + 1  # 1-based index
        return 0
    
    def _set_export_options(self):
        """FBX 익스포트 옵션 설정"""
        # FBX 익스포트 프리셋 리셋
        rt.FBXExporterSetParam("ResetExport")
        
        # 지오메트리 옵션
        rt.FBXExporterSetParam("SmoothingGroups", True)
        rt.FBXExporterSetParam("NormalsPerPoly", False)
        rt.FBXExporterSetParam("TangentSpaceExport", True)
        rt.FBXExporterSetParam("SmoothMeshExport", False)
        rt.FBXExporterSetParam("Preserveinstances", False)
        rt.FBXExporterSetParam("SelectionSetExport", False)
        rt.FBXExporterSetParam("GeomAsBone", False)
        rt.FBXExporterSetParam("Triangulate", False)
        rt.FBXExporterSetParam("PreserveEdgeOrientation", True)
        
        # 애니메이션 옵션
        rt.FBXExporterSetParam("Animation", True)
        rt.FBXExporterSetParam("UseSceneName", True)
        rt.FBXExporterSetParam("Removesinglekeys", False)
        rt.FBXExporterSetParam("BakeAnimation", True)
        rt.FBXExporterSetParam("Skin", True)
        rt.FBXExporterSetParam("Shape", True)
        
        # 포인트 캐시
        rt.FBXExporterSetParam("PointCache", False)
        
        # 카메라 및 라이트
        rt.FBXExporterSetParam("Cameras", False)
        rt.FBXExporterSetParam("Lights", False)
        
        # 텍스처
        rt.FBXExporterSetParam("EmbedTextures", False)
        
        # 기타 옵션
        rt.FBXExporterSetParam("UpAxis", "Z")
        rt.FBXExporterSetParam("GenerateLog", False)
        rt.FBXExporterSetParam("ShowWarnings", False)
        rt.FBXExporterSetParam("ASCII", False)
        rt.FBXExporterSetParam("FileVersion", "FBX202031")
    
    def _set_import_options(self, **options):
        """FBX 임포트 옵션 설정"""
        rt.FBXResetImport()
        
        if 'animation' in options:
            rt.FBXImportAnimation = options['animation']
        
        if 'cameras' in options:
            rt.FBXImportCameras = options['cameras']
        
        if 'lights' in options:
            rt.FBXImportLights = options['lights']
        
        if 'materials' in options:
            rt.FBXImportMaterials = options['materials']
        
        if 'convert_units' in options:
            rt.FBXImportConvertUnit = options['convert_units']
        
        if 'import_mode' in options:
            mode = options['import_mode'].lower()
            if mode == 'add':
                rt.FBXImportMode = rt.Name("exmerge")
            elif mode == 'add_and_update_animation':
                rt.FBXImportMode = rt.Name("exupdate")
            elif mode == 'update_animation':
                rt.FBXImportMode = rt.Name("exupdate")
            else:
                rt.FBXImportMode = rt.Name("exmerge")  # 기본값
        else:
            rt.FBXImportMode = rt.Name("exmerge")  # 기본값
    
    def set_fbx_exporting_anim_range(self, inStartFrame: Optional[int] = None, inEndFrame: Optional[int] = None):
        """애니메이션 범위 설정
        
        Args:
            inStartFrame: 시작 프레임 (None이면 현재 애니메이션 범위 사용)
            inEndFrame: 끝 프레임 (None이면 현재 애니메이션 범위 사용)
        """
        if inStartFrame is None or inEndFrame is None:
            # 매개변수가 없으면 현재 Max 파일의 애니메이션 범위 사용
            animRange = rt.animationrange
            startFrame = inStartFrame if inStartFrame is not None else animRange.start
            endFrame = inEndFrame if inEndFrame is not None else animRange.end
        else:
            # 매개변수가 있으면 해당 값 사용
            startFrame = inStartFrame
            endFrame = inEndFrame
        
        rt.FBXExporterSetParam("BakeFrameStart", startFrame)
        rt.FBXExporterSetParam("BakeFrameEnd", endFrame)
    
    def export_selection(self, inExportFile: str, inMatchAnimRange: bool = True, inStartFrame: Optional[int] = None, inEndFrame: Optional[int] = None) -> bool:
        """
        선택된 오브젝트를 FBX로 익스포트
        
        Args:
            inExportFile: 익스포트할 파일 경로
            inMatchAnimRange: 현재 애니메이션 범위에 맞출지 여부
            inStartFrame: 시작 프레임 (None이면 현재 애니메이션 범위 사용)
            inEndFrame: 끝 프레임 (None이면 현재 애니메이션 범위 사용)
            
        Returns:
            bool: 익스포트 성공 여부
        """
        # 파일 경로 검증 및 디렉토리 생성
        filePath = Path(inExportFile)
        filePath.parent.mkdir(parents=True, exist_ok=True)
        
        # 선택된 오브젝트가 있는지 확인
        if len(rt.selection) == 0:
            return False
        
        # FBX 익스포터 클래스 인덱스 가져오기
        exportClassIndex = self._get_export_fbx_class_index()
        if exportClassIndex == 0:
            return False
        
        # FBX 익스포트 옵션 설정
        self._set_export_options()
        
        # 애니메이션 범위 설정
        if inMatchAnimRange:
            self.set_fbx_exporting_anim_range(inStartFrame, inEndFrame)
        
        # 익스포트 실행
        exporterPlugin = rt.exporterPlugin
        result = rt.exportFile(
            str(filePath),
            rt.Name("noPrompt"),
            using=exporterPlugin.classes[exportClassIndex - 1],  # 0-based index로 변환
            selectedOnly=True
        )
        
        return result
    
    def import_fbx(self, inImportFile: str, **inOptions) -> bool:
        """
        FBX 파일을 임포트
        
        Args:
            inImportFile: 임포트할 파일 경로
            **inOptions: 임포트 옵션
                - animation: 애니메이션 임포트 여부 (기본값: True)
                - cameras: 카메라 임포트 여부 (기본값: False)
                - lights: 라이트 임포트 여부 (기본값: False)
                - materials: 머티리얼 임포트 여부 (기본값: True)
                - convert_units: 유닛 변환 여부 (기본값: True)
                - import_mode: 임포트 모드 ('add', 'add_and_update_animation', 'update_animation')
                
        Returns:
            bool: 임포트 성공 여부
        """
        # 파일 존재 여부 확인
        filePath = Path(inImportFile)
        if not filePath.exists():
            return False
        
        # 기본 옵션 설정
        defaultOptions = {
            'animation': True,
            'cameras': False,
            'lights': False,
            'materials': True,
            'convert_units': True,
            'import_mode': 'add'
        }
        
        # 사용자 옵션으로 기본값 덮어쓰기
        defaultOptions.update(inOptions)
        
        # FBX 임포트 옵션 설정
        self._set_import_options(**defaultOptions)
        
        # 임포트 실행
        result = rt.importFile(
            str(filePath),
            rt.Name("noPrompt"),
            using=rt.FBXIMP
        )
        
        return result
    
    def reset_import_options(self):
        """FBX 임포트 옵션을 기본값으로 리셋"""
        rt.FBXResetImport()
