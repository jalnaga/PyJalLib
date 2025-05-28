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
        rt.FBXExporterSetParam("Triangulate", True)
        
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
        rt.FBXExporterSetParam("UpAxis", "Y")
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
        
        rt.FBXImportGenerateLog = False
        rt.FBXImportMode = rt.name("exmerge")
    
    def set_fbx_exporting_anim_range(self):
        """애니메이션 범위를 현재 타임라인에 맞게 설정"""
        animRange = rt.animationrange
        rt.FBXExporterSetParam("BakeFrameStart", animRange.start)
        rt.FBXExporterSetParam("BakeFrameEnd", animRange.end)
    
    def export_selection(self, exportFile: str, matchAnimRange: bool = True) -> bool:
        """
        선택된 오브젝트를 FBX로 익스포트
        
        Args:
            exportFile: 익스포트할 파일 경로
            matchAnimRange: 현재 애니메이션 범위에 맞출지 여부
            
        Returns:
            bool: 익스포트 성공 여부
        """
        # 파일 경로 검증 및 디렉토리 생성
        filePath = Path(exportFile)
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
        if matchAnimRange:
            self.set_fbx_exporting_anim_range()
        
        # 익스포트 실행
        exporterPlugin = rt.exporterPlugin
        result = rt.exportFile(
            str(filePath),
            rt.noPrompt,
            using=exporterPlugin.classes[exportClassIndex - 1],  # 0-based index로 변환
            selectedOnly=True
        )
        
        return result
