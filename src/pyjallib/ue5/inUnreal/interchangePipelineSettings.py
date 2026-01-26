#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 파이프라인 설정 관리 모듈

이 모듈은 Interchange Framework의 파이프라인 설정을 관리합니다.
DefaultAssetsPipeline의 서브 파이프라인 속성을 런타임에 설정합니다.
"""

from typing import Dict, Any, Optional

import unreal


class InterchangePipelineSettings:
    """
    Interchange 파이프라인 설정 관리 클래스.
    
    UE5 기본 제공 DefaultAssetsPipeline을 사용하여
    임포트 옵션을 런타임에 설정합니다.
    """
    
    # ========================================================================
    # 기본 파이프라인 에셋 경로 상수
    # ========================================================================
    
    # UE5 기본 제공 파이프라인 (하나만 사용)
    DEFAULT_PIPELINE_PATH = "/Interchange/Pipelines/DefaultAssetsPipeline.DefaultAssetsPipeline"
    
    def __init__(self):
        """InterchangePipelineSettings 초기화."""
        pass
    
    # ========================================================================
    # 파이프라인 로드
    # ========================================================================
    
    def get_pipeline_path(self) -> str:
        """기본 파이프라인 경로를 반환합니다."""
        return self.DEFAULT_PIPELINE_PATH
    
    def load_pipeline(self) -> Optional[unreal.Object]:
        """
        기본 파이프라인 에셋을 로드합니다.
        
        Returns:
            로드된 파이프라인 에셋, 실패 시 None
        """
        asset = unreal.EditorAssetLibrary.load_asset(self.DEFAULT_PIPELINE_PATH)
        if asset is None:
            unreal.log_warning(f"[InterchangePipelineSettings] 파이프라인 에셋 로드 실패: {self.DEFAULT_PIPELINE_PATH}")
        return asset
    
    # ========================================================================
    # 파이프라인 설정 메서드
    # ========================================================================
    
    def configure_for_skeleton(self, inPipeline: unreal.Object) -> bool:
        """
        스켈레톤 임포트를 위해 파이프라인을 설정합니다.
        
        스켈레탈 메쉬와 스켈레톤만 임포트하고, 애니메이션/머티리얼/텍스쳐는 비활성화합니다.
        
        파이프라인 구조:
        - InterchangeGenericAssetsPipeline
          ├── animation_pipeline.import_animations = False
          ├── material_pipeline.import_materials = False
          │   └── texture_pipeline.import_textures = False
          └── mesh_pipeline (유지)
        
        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋
            
        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error("[InterchangePipelineSettings] 파이프라인 에셋이 None입니다")
            return False
        
        try:
            # 1. 애니메이션 파이프라인 설정 - import_animations = False
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                animationPipeline.set_editor_property("import_animations", False)
                unreal.log("[InterchangePipelineSettings] animation_pipeline.import_animations = False")
            else:
                unreal.log_warning("[InterchangePipelineSettings] animation_pipeline이 None입니다")
            
            # 2. 머티리얼 파이프라인 설정 - import_materials = False
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                materialPipeline.set_editor_property("import_materials", False)
                unreal.log("[InterchangePipelineSettings] material_pipeline.import_materials = False")
                
                # 3. 텍스쳐 파이프라인 설정 - import_textures = False
                texturePipeline = materialPipeline.get_editor_property("texture_pipeline")
                if texturePipeline is not None:
                    texturePipeline.set_editor_property("import_textures", False)
                    unreal.log("[InterchangePipelineSettings] material_pipeline.texture_pipeline.import_textures = False")
                else:
                    unreal.log_warning("[InterchangePipelineSettings] texture_pipeline이 None입니다")
            else:
                unreal.log_warning("[InterchangePipelineSettings] material_pipeline이 None입니다")
            
            unreal.log("[InterchangePipelineSettings] 스켈레톤용 파이프라인 설정 완료")
            return True
            
        except Exception as e:
            unreal.log_error(f"[InterchangePipelineSettings] 스켈레톤용 파이프라인 설정 중 에러: {e}")
            return False
    
    def configure_for_skeletal_mesh(self, inPipeline: unreal.Object) -> bool:
        """
        스켈레탈 메쉬 임포트를 위해 파이프라인을 설정합니다.
        (스켈레톤과 동일한 설정)
        
        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋
            
        Returns:
            성공 여부
        """
        return self.configure_for_skeleton(inPipeline)
    
    def configure_for_animation(self, inPipeline: unreal.Object) -> bool:
        """
        애니메이션 임포트를 위해 파이프라인을 설정합니다.
        
        애니메이션만 임포트하고, 머티리얼/텍스쳐는 비활성화합니다.
        
        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋
            
        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error("[InterchangePipelineSettings] 파이프라인 에셋이 None입니다")
            return False
        
        try:
            # 1. 애니메이션 파이프라인 설정 - import_animations = True
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                animationPipeline.set_editor_property("import_animations", True)
                unreal.log("[InterchangePipelineSettings] animation_pipeline.import_animations = True")
            else:
                unreal.log_warning("[InterchangePipelineSettings] animation_pipeline이 None입니다")
            
            # 2. 머티리얼 파이프라인 설정 - import_materials = False
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                materialPipeline.set_editor_property("import_materials", False)
                unreal.log("[InterchangePipelineSettings] material_pipeline.import_materials = False")
                
                # 3. 텍스쳐 파이프라인 설정 - import_textures = False
                texturePipeline = materialPipeline.get_editor_property("texture_pipeline")
                if texturePipeline is not None:
                    texturePipeline.set_editor_property("import_textures", False)
                    unreal.log("[InterchangePipelineSettings] material_pipeline.texture_pipeline.import_textures = False")
                else:
                    unreal.log_warning("[InterchangePipelineSettings] texture_pipeline이 None입니다")
            else:
                unreal.log_warning("[InterchangePipelineSettings] material_pipeline이 None입니다")
            
            unreal.log("[InterchangePipelineSettings] 애니메이션용 파이프라인 설정 완료")
            return True
            
        except Exception as e:
            unreal.log_error(f"[InterchangePipelineSettings] 애니메이션용 파이프라인 설정 중 에러: {e}")
            return False
