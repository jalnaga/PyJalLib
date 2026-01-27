#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 파이프라인 설정 관리 모듈

이 모듈은 Interchange Framework의 파이프라인 설정을 관리합니다.
DefaultAssetsPipeline의 서브 파이프라인 속성을 런타임에 설정합니다.
"""

from enum import Enum
from typing import Optional

import unreal


class InterchangePipelinePreset(Enum):
    """
    Interchange 파이프라인 프리셋 타입.

    에셋 타입에 따른 파이프라인 설정을 구분합니다.
    """

    SKELETON = "skeleton"
    SKELETAL_MESH = "skeletal_mesh"
    ANIMATION = "animation"


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
    DEFAULT_PIPELINE_PATH = (
        "/Interchange/Pipelines/DefaultAssetsPipeline.DefaultAssetsPipeline"
    )

    def __init__(self, inAssetType: Optional[str] = None):
        """
        InterchangePipelineSettings 초기화.

        Args:
            inAssetType: 에셋 타입 문자열 (선택적). 예: "Animation", "Skeleton", "SkeletalMesh"
                         기존 코드 호환성을 위해 기본값은 None
        """
        self._assetType = inAssetType
        self._propertyOverrides: dict = {}

    # ========================================================================
    # 속성 오버라이드 관리
    # ========================================================================

    def set_property_override(self, inKey: str, inValue) -> None:
        """
        파이프라인 속성 오버라이드를 설정합니다.

        임포트 시 적용될 속성들을 딕셔너리로 관리합니다.

        Args:
            inKey: 속성 키 (예: "skeleton", "import_animations")
            inValue: 속성 값
        """
        self._propertyOverrides[inKey] = inValue
        unreal.log(
            f"[InterchangePipelineSettings] 속성 오버라이드 설정: {inKey} = {inValue}"
        )

    def get_property_override(self, inKey: str, inDefault=None):
        """
        파이프라인 속성 오버라이드를 가져옵니다.

        Args:
            inKey: 속성 키
            inDefault: 키가 없을 때 반환할 기본값

        Returns:
            저장된 속성 값 또는 기본값
        """
        return self._propertyOverrides.get(inKey, inDefault)

    def clear_property_overrides(self) -> None:
        """모든 속성 오버라이드를 초기화합니다."""
        self._propertyOverrides.clear()
        unreal.log("[InterchangePipelineSettings] 속성 오버라이드 초기화됨")

    # ========================================================================
    # 파이프라인 경로 관리
    # ========================================================================

    def get_pipeline_paths(self, inPreset: InterchangePipelinePreset = None) -> list:
        """
        프리셋에 따라 파이프라인 경로 리스트를 반환합니다.

        현재는 모든 프리셋에 대해 동일한 기본 파이프라인을 사용합니다.
        향후 프리셋별로 다른 파이프라인을 사용할 수 있도록 확장 가능합니다.

        Args:
            inPreset: InterchangePipelinePreset Enum 값 (선택적)

        Returns:
            파이프라인 경로 리스트
        """
        # 현재는 단일 기본 파이프라인만 사용
        return [self.DEFAULT_PIPELINE_PATH]

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
            unreal.log_warning(
                f"[InterchangePipelineSettings] 파이프라인 에셋 로드 실패: {self.DEFAULT_PIPELINE_PATH}"
            )
        return asset

    # ========================================================================
    # 파이프라인 설정 메서드
    # ========================================================================

    def configure_for_skeleton(self, inPipeline: unreal.Object) -> bool:
        """
        스켈레톤 임포트를 위해 파이프라인을 설정합니다.

        스켈레탈 메쉬와 스켈레톤만 임포트하고, 애니메이션/머티리얼/텍스쳐/피직스에셋은 비활성화합니다.

        파이프라인 구조:
        - InterchangeGenericAssetsPipeline
          ├── animation_pipeline.import_animations = False
          ├── material_pipeline.import_materials = False
          │   └── texture_pipeline.import_textures = False
          └── mesh_pipeline.create_physics_asset = False

        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋

        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error(
                "[InterchangePipelineSettings] 파이프라인 에셋이 None입니다"
            )
            return False

        try:
            # 1. 애니메이션 파이프라인 설정 - import_animations = False
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                animationPipeline.set_editor_property("import_animations", False)
                unreal.log(
                    "[InterchangePipelineSettings] animation_pipeline.import_animations = False"
                )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] animation_pipeline이 None입니다"
                )

            # 2. 머티리얼 파이프라인 설정 - import_materials = False
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                materialPipeline.set_editor_property("import_materials", False)
                unreal.log(
                    "[InterchangePipelineSettings] material_pipeline.import_materials = False"
                )

                # 3. 텍스쳐 파이프라인 설정 - import_textures = False
                texturePipeline = materialPipeline.get_editor_property(
                    "texture_pipeline"
                )
                if texturePipeline is not None:
                    texturePipeline.set_editor_property("import_textures", False)
                    unreal.log(
                        "[InterchangePipelineSettings] material_pipeline.texture_pipeline.import_textures = False"
                    )
                else:
                    unreal.log_warning(
                        "[InterchangePipelineSettings] texture_pipeline이 None입니다"
                    )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] material_pipeline이 None입니다"
                )

            # 4. 메쉬 파이프라인 설정 - create_physics_asset = False
            meshPipeline = inPipeline.get_editor_property("mesh_pipeline")
            if meshPipeline is not None:
                meshPipeline.set_editor_property("create_physics_asset", False)
                unreal.log(
                    "[InterchangePipelineSettings] mesh_pipeline.create_physics_asset = False"
                )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] mesh_pipeline이 None입니다"
                )

            unreal.log("[InterchangePipelineSettings] 스켈레톤용 파이프라인 설정 완료")
            return True

        except Exception as e:
            unreal.log_error(
                f"[InterchangePipelineSettings] 스켈레톤용 파이프라인 설정 중 에러: {e}"
            )
            return False

    def configure_for_skeletal_mesh(self, inPipeline: unreal.Object) -> bool:
        """
        스켈레탈 메쉬 임포트를 위해 파이프라인을 설정합니다.

        스켈레탈 메쉬만 임포트하고, 애니메이션/머티리얼/텍스쳐/피직스에셋은 비활성화합니다.
        기존 스켈레톤을 참조합니다.

        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋

        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error(
                "[InterchangePipelineSettings] 파이프라인 에셋이 None입니다"
            )
            return False

        try:
            # 1. 애니메이션 파이프라인 설정 - import_animations = False
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                animationPipeline.set_editor_property("import_animations", False)
                unreal.log(
                    "[InterchangePipelineSettings] animation_pipeline.import_animations = False"
                )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] animation_pipeline이 None입니다"
                )

            # 2. 머티리얼 파이프라인 설정 - import_materials = False
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                materialPipeline.set_editor_property("import_materials", False)
                unreal.log(
                    "[InterchangePipelineSettings] material_pipeline.import_materials = False"
                )

                # 3. 텍스쳐 파이프라인 설정 - import_textures = False
                texturePipeline = materialPipeline.get_editor_property(
                    "texture_pipeline"
                )
                if texturePipeline is not None:
                    texturePipeline.set_editor_property("import_textures", False)
                    unreal.log(
                        "[InterchangePipelineSettings] material_pipeline.texture_pipeline.import_textures = False"
                    )
                else:
                    unreal.log_warning(
                        "[InterchangePipelineSettings] texture_pipeline이 None입니다"
                    )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] material_pipeline이 None입니다"
                )

            # 4. 메쉬 파이프라인 설정 - create_physics_asset = False
            meshPipeline = inPipeline.get_editor_property("mesh_pipeline")
            if meshPipeline is not None:
                meshPipeline.set_editor_property("create_physics_asset", False)
                unreal.log(
                    "[InterchangePipelineSettings] mesh_pipeline.create_physics_asset = False"
                )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] mesh_pipeline이 None입니다"
                )

            # 5. common_skeletal_meshes_and_animations_properties를 통한 스켈레톤 설정
            commonSkeletalProps = inPipeline.get_editor_property(
                "common_skeletal_meshes_and_animations_properties"
            )
            if commonSkeletalProps is not None:
                # skeleton 오버라이드 적용
                skeleton = self.get_property_override("skeleton")
                if skeleton is not None:
                    commonSkeletalProps.set_editor_property("skeleton", skeleton)
                    unreal.log(
                        f"[InterchangePipelineSettings] common_skeletal_meshes_and_animations_properties.skeleton = {skeleton.get_name()}"
                    )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] common_skeletal_meshes_and_animations_properties이 None입니다"
                )

            unreal.log("[InterchangePipelineSettings] 스켈레탈 메쉬용 파이프라인 설정 완료")
            return True

        except Exception as e:
            unreal.log_error(
                f"[InterchangePipelineSettings] 스켈레탈 메쉬용 파이프라인 설정 중 에러: {e}"
            )
            return False

    def configure_for_animation(self, inPipeline: unreal.Object) -> bool:
        """
        애니메이션 임포트를 위해 파이프라인을 설정합니다.

        애니메이션만 임포트하고, 머티리얼/텍스쳐는 비활성화합니다.
        skeleton 오버라이드가 설정된 경우 해당 스켈레톤을 사용합니다.

        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋

        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error(
                "[InterchangePipelineSettings] 파이프라인 에셋이 None입니다"
            )
            return False

        try:
            # 1. 애니메이션 파이프라인 설정 - import_animations = True
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                animationPipeline.set_editor_property("import_animations", True)
                unreal.log(
                    "[InterchangePipelineSettings] animation_pipeline.import_animations = True"
                )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] animation_pipeline이 None입니다"
                )

            # 2. common_skeletal_meshes_and_animations_properties를 통한 스켈레톤 설정
            # UE5.7 공식 문서: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericCommonSkeletalMeshesAndAnimationsProperties
            commonSkeletalProps = inPipeline.get_editor_property(
                "common_skeletal_meshes_and_animations_properties"
            )
            if commonSkeletalProps is not None:
                # skeleton 오버라이드 적용
                skeleton = self.get_property_override("skeleton")
                if skeleton is not None:
                    commonSkeletalProps.set_editor_property("skeleton", skeleton)
                    unreal.log(
                        f"[InterchangePipelineSettings] common_skeletal_meshes_and_animations_properties.skeleton = {skeleton.get_name()}"
                    )

                    # 애니메이션만 임포트 (스켈레톤은 이미 존재하므로)
                    commonSkeletalProps.set_editor_property(
                        "import_only_animations", True
                    )
                    unreal.log(
                        "[InterchangePipelineSettings] common_skeletal_meshes_and_animations_properties.import_only_animations = True"
                    )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] common_skeletal_meshes_and_animations_properties이 None입니다"
                )

            # 2. 머티리얼 파이프라인 설정 - import_materials = False
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                materialPipeline.set_editor_property("import_materials", False)
                unreal.log(
                    "[InterchangePipelineSettings] material_pipeline.import_materials = False"
                )

                # 3. 텍스쳐 파이프라인 설정 - import_textures = False
                texturePipeline = materialPipeline.get_editor_property(
                    "texture_pipeline"
                )
                if texturePipeline is not None:
                    texturePipeline.set_editor_property("import_textures", False)
                    unreal.log(
                        "[InterchangePipelineSettings] material_pipeline.texture_pipeline.import_textures = False"
                    )
                else:
                    unreal.log_warning(
                        "[InterchangePipelineSettings] texture_pipeline이 None입니다"
                    )
            else:
                unreal.log_warning(
                    "[InterchangePipelineSettings] material_pipeline이 None입니다"
                )

            unreal.log(
                "[InterchangePipelineSettings] 애니메이션용 파이프라인 설정 완료"
            )
            return True

        except Exception as e:
            unreal.log_error(
                f"[InterchangePipelineSettings] 애니메이션용 파이프라인 설정 중 에러: {e}"
            )
            return False
