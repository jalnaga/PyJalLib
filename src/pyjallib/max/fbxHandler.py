#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FBXHandler 모듈
3ds Max에서 FBX 파일을 익스포트/임포트하는 기능을 제공
이 모듈은 pymxs를 사용하여 3ds Max와 통신하며, FBX 익스포트 및 임포트 옵션을 설정하고 파일을 처리합니다.
"""

from pymxs import runtime as rt
from pathlib import Path
from typing import Optional

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
    
    def _get_import_fbx_class_index(self) -> int:
        """FBX 임포터 클래스 인덱스 가져오기"""
        importerPlugin = rt.importerPlugin
        for i, cls in enumerate(importerPlugin.classes):
            if "FBX" in str(cls):
                return i + 1  # 1-based index
        return 0
    
    def _set_export_options(self, inSmoothingGroups: bool = True):
        """FBX 익스포트 옵션 설정

        Args:
            inSmoothingGroups: SmoothingGroups 익스포트 여부. 기본값 True.
        """
        # FBX 익스포트 프리셋 리셋
        rt.FBXExporterSetParam("ResetExport")

        # 지오메트리 옵션
        rt.FBXExporterSetParam("SmoothingGroups", inSmoothingGroups)
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
    
    def _set_import_options(self, inImportMode: str = "add_and_update_animation", inUpAxis: str = "Z"):
        """FBX 임포트 옵션 설정
        
        Args:
            inImportMode: 임포트 모드 ('add_and_update_animation' 또는 'update_animation')
        """
        # FBX 임포트 프리셋 리셋
        rt.FBXImporterSetParam("ResetImport")
        
        # 임포트 모드 설정
        if inImportMode == "update_animation":
            rt.FBXImporterSetParam("Mode", rt.Name("exmerge"))  # Update Animation 모드
        else:  # "add_and_update_animation" (기본값)
            rt.FBXImporterSetParam("Mode", rt.Name("merge"))  # Add and Update Animation 모드
        
        rt.FBXImporterSetParam("SmoothingGroups", True)
        rt.FBXImporterSetParam("Animation", True)
        rt.FBXImporterSetParam("BakeAnimationLayers", True)
        rt.FBXImporterSetParam("FillTimeline", True)
        rt.FBXImporterSetParam("Skin", True)
        rt.FBXImporterSetParam("Shape", True)
        rt.FBXImporterSetParam("Cameras", False)
        rt.FBXImporterSetParam("Lights", False)
        rt.FBXImporterSetParam("GenerateLog", False)
        rt.FBXImporterSetParam("GenerateLog", False)
        rt.FBXImporterSetParam("ImportBoneAsDummy", True)
        rt.FBXImporterSetParam("UpAxis", inUpAxis)
    
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
    
    def export_selection(
        self,
        inExportFile: str,
        inMatchAnimRange: bool = True,
        inStartFrame: Optional[int] = None,
        inEndFrame: Optional[int] = None,
        inSmoothingGroups: bool = True,
    ) -> bool:
        """
        선택된 오브젝트를 FBX로 익스포트

        Args:
            inExportFile: 익스포트할 파일 경로
            inMatchAnimRange: 현재 애니메이션 범위에 맞출지 여부
            inStartFrame: 시작 프레임 (None이면 현재 애니메이션 범위 사용)
            inEndFrame: 끝 프레임 (None이면 현재 애니메이션 범위 사용)
            inSmoothingGroups: SmoothingGroups 익스포트 여부. 기본값 True.

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
        self._set_export_options(inSmoothingGroups=inSmoothingGroups)
        
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
    
    def import_fbx(self, inImportFile: str, inImportMode: str = "add_and_update_animation", inUpAxis: str = "Z") -> bool:
        """
        FBX 파일을 임포트
        
        Args:
            inImportFile: 임포트할 파일 경로
            inImportMode: 임포트 모드 ('add_and_update_animation' 또는 'update_animation')
                
        Returns:
            bool: 임포트 성공 여부
        """
        # 파일 존재 여부 확인
        filePath = Path(inImportFile)
        if not filePath.exists():
            return False
        
        # FBX 임포터 클래스 인덱스 가져오기
        importClassIndex = self._get_import_fbx_class_index()
        if importClassIndex == 0:
            return False
        
        # FBX 임포트 옵션 설정
        self._set_import_options(inImportMode, inUpAxis)
        
        # 임포트 실행
        importerPlugin = rt.importerPlugin
        result = rt.importFile(
            str(filePath),
            rt.Name("noPrompt"),
            using=importerPlugin.classes[importClassIndex - 1]  # 0-based index로 변환
        )
        
        return result
    
    def reset_import_options(self):
        """FBX 임포트 옵션을 기본값으로 리셋"""
        rt.FBXImporterSetParam("ResetImport")
