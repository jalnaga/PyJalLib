#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 파이프라인 설정 관리 모듈

이 모듈은 Interchange Framework의 파이프라인 설정을 관리합니다.
프리셋 기반 설정 및 런타임 속성 오버라이드를 지원합니다.
"""

from enum import Enum
from typing import Dict, Any, Optional, List

import unreal


class InterchangePipelinePreset(Enum):
    """Interchange 파이프라인 프리셋 타입"""
    SKELETON = "Skeleton"
    SKELETAL_MESH = "SkeletalMesh"
    ANIMATION = "Animation"


class InterchangePipelineSettings:
    """
    Interchange 파이프라인 설정 관리 클래스.
    
    프로젝트 표준 파이프라인 에셋 경로를 관리하고,
    각 프리셋별 설정 및 런타임 속성 오버라이드를 지원합니다.
    """
    
    # ========================================================================
    # 기본 파이프라인 에셋 경로 상수
    # ========================================================================
    
    # 프로젝트에서 미리 생성해야 하는 파이프라인 에셋 경로
    # 실제 프로젝트에서 이 경로를 커스터마이징하여 사용
    DEFAULT_GENERIC_PIPELINE_PATH = "/Interchange/Pipelines/DefaultGenericPipeline"
    DEFAULT_ANIMATION_PIPELINE_PATH = "/Interchange/Pipelines/DefaultAnimationPipeline"
    
    # 프리셋별 파이프라인 경로 매핑
    PRESET_PIPELINE_PATHS: Dict[InterchangePipelinePreset, str] = {
        InterchangePipelinePreset.SKELETON: DEFAULT_GENERIC_PIPELINE_PATH,
        InterchangePipelinePreset.SKELETAL_MESH: DEFAULT_GENERIC_PIPELINE_PATH,
        InterchangePipelinePreset.ANIMATION: DEFAULT_ANIMATION_PIPELINE_PATH,
    }
    
    def __init__(self, inPresetName: str = None):
        """
        InterchangePipelineSettings 초기화.
        
        Args:
            inPresetName: 프리셋 이름 (Skeleton, SkeletalMesh, Animation)
        """
        self.presetName = inPresetName
        self._customPipelinePaths: Dict[InterchangePipelinePreset, str] = {}
        self._propertyOverrides: Dict[str, Any] = {}
        
        # Debug 로그는 생략 (unreal.log는 항상 출력되므로)
    
    # ========================================================================
    # 파이프라인 경로 관리
    # ========================================================================
    
    def set_pipeline_path(self, inPreset: InterchangePipelinePreset, inPath: str):
        """
        특정 프리셋의 파이프라인 에셋 경로를 설정합니다.
        
        Args:
            inPreset: 프리셋 타입
            inPath: 파이프라인 에셋 경로
        """
        self._customPipelinePaths[inPreset] = inPath
    
    def get_pipeline_path(self, inPreset: InterchangePipelinePreset = None) -> str:
        """
        프리셋에 해당하는 파이프라인 에셋 경로를 반환합니다.
        
        Args:
            inPreset: 프리셋 타입. None이면 현재 presetName 사용
            
        Returns:
            파이프라인 에셋 경로
        """
        if inPreset is None:
            inPreset = self._get_preset_from_name()
        
        # 커스텀 경로가 있으면 우선 사용
        if inPreset in self._customPipelinePaths:
            return self._customPipelinePaths[inPreset]
        
        # 기본 경로 반환
        return self.PRESET_PIPELINE_PATHS.get(inPreset, self.DEFAULT_GENERIC_PIPELINE_PATH)
    
    def get_pipeline_paths(self, inPreset: InterchangePipelinePreset = None) -> List[str]:
        """
        프리셋에 해당하는 파이프라인 에셋 경로 리스트를 반환합니다.
        
        Args:
            inPreset: 프리셋 타입. None이면 현재 presetName 사용
            
        Returns:
            파이프라인 에셋 경로 리스트
        """
        return [self.get_pipeline_path(inPreset)]
    
    def _get_preset_from_name(self) -> InterchangePipelinePreset:
        """현재 presetName을 프리셋 Enum으로 변환합니다."""
        if self.presetName is None:
            return InterchangePipelinePreset.SKELETON
        
        nameMap = {
            "skeleton": InterchangePipelinePreset.SKELETON,
            "skeletalmesh": InterchangePipelinePreset.SKELETAL_MESH,
            "animation": InterchangePipelinePreset.ANIMATION,
        }
        return nameMap.get(self.presetName.lower(), InterchangePipelinePreset.SKELETON)
    
    # ========================================================================
    # 프리셋별 설정 메서드
    # ========================================================================
    
    def get_skeleton_import_settings(self) -> Dict[str, Any]:
        """
        스켈레톤 임포트를 위한 Interchange 설정을 반환합니다.
        
        스켈레탈 메쉬 임포트 (스켈레톤 생성 목적), 애니메이션/머티리얼/텍스처 비활성화
        
        Returns:
            설정 딕셔너리
        """
        settings = {
            "import_skeletal_mesh": True,
            "import_animations": False,
            "import_materials": False,
            "import_textures": False,
            "create_physics_asset": False,
            "skeleton": None,  # 새 스켈레톤 생성
            "import_morph_targets": False,
        }
        settings.update(self._propertyOverrides)
        return settings
    
    def get_skeletal_mesh_import_settings(self) -> Dict[str, Any]:
        """
        스켈레탈 메시 임포트를 위한 Interchange 설정을 반환합니다.
        
        스켈레탈 메쉬 임포트, 애니메이션/머티리얼/텍스처 비활성화, 모프 타겟 활성화
        
        Returns:
            설정 딕셔너리
        """
        settings = {
            "import_skeletal_mesh": True,
            "import_animations": False,
            "import_materials": False,
            "import_textures": False,
            "create_physics_asset": False,
            "import_morph_targets": True,
            "import_vertex_colors": True,
        }
        settings.update(self._propertyOverrides)
        return settings
    
    def get_animation_import_settings(self) -> Dict[str, Any]:
        """
        애니메이션 임포트를 위한 Interchange 설정을 반환합니다.
        
        애니메이션만 임포트, 메쉬/머티리얼/텍스처 비활성화
        
        Returns:
            설정 딕셔너리
        """
        settings = {
            "import_skeletal_mesh": False,
            "import_animations": True,
            "import_materials": False,
            "import_textures": False,
            "import_bone_tracks": True,
            "import_custom_attributes": True,
        }
        settings.update(self._propertyOverrides)
        return settings
    
    def get_settings(self, inPresetName: Optional[str] = None) -> Dict[str, Any]:
        """
        프리셋 이름에 따른 설정을 반환합니다.
        
        Args:
            inPresetName: 프리셋 이름. None이면 self.presetName 사용
            
        Returns:
            설정 딕셔너리
        """
        if inPresetName is None:
            inPresetName = self.presetName
        
        if inPresetName is None:
            unreal.log_warning("[InterchangePipelineSettings] 프리셋 이름이 지정되지 않았습니다. 기본 Skeleton 설정 반환")
            return self.get_skeleton_import_settings()
        
        presetLower = inPresetName.lower()
        if presetLower == "skeleton":
            return self.get_skeleton_import_settings()
        elif presetLower == "skeletalmesh":
            return self.get_skeletal_mesh_import_settings()
        elif presetLower == "animation":
            return self.get_animation_import_settings()
        else:
            unreal.log_warning(f"[InterchangePipelineSettings] 알 수 없는 프리셋: {inPresetName}. 기본 Skeleton 설정 반환")
            return self.get_skeleton_import_settings()
    
    # ========================================================================
    # 런타임 파이프라인 속성 오버라이드
    # ========================================================================
    
    def set_property_override(self, inPropertyName: str, inValue: Any):
        """
        파이프라인 속성을 오버라이드합니다.
        
        Args:
            inPropertyName: 속성 이름
            inValue: 속성 값
        """
        self._propertyOverrides[inPropertyName] = inValue
    
    def set_property_overrides(self, inOverrides: Dict[str, Any]):
        """
        여러 파이프라인 속성을 한번에 오버라이드합니다.
        
        Args:
            inOverrides: 속성 이름-값 딕셔너리
        """
        self._propertyOverrides.update(inOverrides)
    
    def clear_property_overrides(self):
        """모든 속성 오버라이드를 초기화합니다."""
        self._propertyOverrides.clear()
    
    def get_property_overrides(self) -> Dict[str, Any]:
        """현재 설정된 속성 오버라이드를 반환합니다."""
        return self._propertyOverrides.copy()
    
    # ========================================================================
    # 파이프라인 에셋 로드 및 설정 적용
    # ========================================================================
    
    def load_pipeline_asset(self, inPipelinePath: str) -> Optional[unreal.Object]:
        """
        파이프라인 에셋을 로드합니다.
        
        Args:
            inPipelinePath: 파이프라인 에셋 경로
            
        Returns:
            로드된 파이프라인 에셋, 실패 시 None
        """
        asset = unreal.EditorAssetLibrary.load_asset(inPipelinePath)
        if asset is None:
            unreal.log_warning(f"[InterchangePipelineSettings] 파이프라인 에셋 로드 실패: {inPipelinePath}")
        return asset
    
    def apply_settings_to_pipeline(
        self, 
        inPipeline: unreal.Object, 
        inSettings: Dict[str, Any]
    ) -> bool:
        """
        파이프라인 에셋에 설정을 적용합니다.
        
        Args:
            inPipeline: 파이프라인 에셋
            inSettings: 적용할 설정 딕셔너리
            
        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error("[InterchangePipelineSettings] 파이프라인 에셋이 None입니다")
            return False
        
        try:
            for propName, propValue in inSettings.items():
                if hasattr(inPipeline, 'set_editor_property'):
                    try:
                        inPipeline.set_editor_property(propName, propValue)
                    except Exception as e:
                        unreal.log_warning(f"[InterchangePipelineSettings] 파이프라인 속성 설정 실패: {propName} = {propValue}, 에러: {e}")
            return True
        except Exception as e:
            unreal.log_error(f"[InterchangePipelineSettings] 파이프라인 설정 적용 중 에러: {e}")
            return False
