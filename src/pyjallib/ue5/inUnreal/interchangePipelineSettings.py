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

    # 프로젝트 커스텀 파이프라인 (엔진 기본 파이프라인은 읽기 전용이므로 사용하지 않음)
    DEFAULT_PIPELINE_PATH = (
        "/Game/Omni/Tools/InterchangePipeline/ORV_DefaultAssetsPipeline.ORV_DefaultAssetsPipeline"
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
        self._originalValues: dict = {}

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
    # 파이프라인 원본 값 저장/복원
    # ========================================================================

    def _store_original_values(self, inPipeline: unreal.Object) -> bool:
        """
        파이프라인의 원본 속성 값을 저장합니다.

        configure_for_* 메서드 호출 전에 실행되어 원본 값을 보존합니다.
        임포트 완료 후 restore_pipeline()으로 복원합니다.

        저장 대상:
        - animation_pipeline.import_animations
        - material_pipeline.import_materials
        - material_pipeline.texture_pipeline.import_textures
        - mesh_pipeline.create_physics_asset
        - common_skeletal_meshes_and_animations_properties.skeleton
        - common_skeletal_meshes_and_animations_properties.import_only_animations

        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋

        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error(
                "[InterchangePipelineSettings] 원본 값 저장 실패: 파이프라인 에셋이 None입니다"
            )
            return False

        # 이미 저장된 원본 값이 있으면 덮어쓰지 않음 (첫 번째 저장 값 유지)
        if self._originalValues:
            unreal.log(
                "[InterchangePipelineSettings] 원본 값이 이미 저장되어 있음 - 건너뜀"
            )
            return True

        try:
            self._originalValues = {}

            # 1. animation_pipeline.import_animations
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                self._originalValues["animation_pipeline.import_animations"] = (
                    animationPipeline.get_editor_property("import_animations")
                )

            # 2. material_pipeline.import_materials
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                self._originalValues["material_pipeline.import_materials"] = (
                    materialPipeline.get_editor_property("import_materials")
                )

                # 3. texture_pipeline.import_textures
                texturePipeline = materialPipeline.get_editor_property("texture_pipeline")
                if texturePipeline is not None:
                    self._originalValues["texture_pipeline.import_textures"] = (
                        texturePipeline.get_editor_property("import_textures")
                    )

            # 4. mesh_pipeline.create_physics_asset
            meshPipeline = inPipeline.get_editor_property("mesh_pipeline")
            if meshPipeline is not None:
                self._originalValues["mesh_pipeline.create_physics_asset"] = (
                    meshPipeline.get_editor_property("create_physics_asset")
                )

            # 5. common_skeletal_meshes_and_animations_properties
            commonSkeletalProps = inPipeline.get_editor_property(
                "common_skeletal_meshes_and_animations_properties"
            )
            if commonSkeletalProps is not None:
                self._originalValues["common_skeletal_props.skeleton"] = (
                    commonSkeletalProps.get_editor_property("skeleton")
                )
                self._originalValues["common_skeletal_props.import_only_animations"] = (
                    commonSkeletalProps.get_editor_property("import_only_animations")
                )

            unreal.log(
                f"[InterchangePipelineSettings] 원본 값 저장 완료: {len(self._originalValues)}개 속성"
            )
            return True

        except Exception as e:
            unreal.log_error(
                f"[InterchangePipelineSettings] 원본 값 저장 중 에러: {e}"
            )
            self._originalValues = {}
            return False

    def restore_pipeline(self, inPipeline: unreal.Object) -> bool:
        """
        파이프라인을 원본 상태로 복원합니다.

        _store_original_values()로 저장된 원본 값으로 파이프라인 속성을 복원한 후,
        Perforce에서 파일을 리버트하여 디스크 상태도 원본으로 되돌립니다.

        Args:
            inPipeline: InterchangeGenericAssetsPipeline 에셋

        Returns:
            성공 여부
        """
        if inPipeline is None:
            unreal.log_error(
                "[InterchangePipelineSettings] 파이프라인 복원 실패: 파이프라인 에셋이 None입니다"
            )
            return False

        if not self._originalValues:
            unreal.log(
                "[InterchangePipelineSettings] 복원할 원본 값이 없음 - 건너뜀"
            )
            return True

        try:
            # 1. animation_pipeline.import_animations 복원
            animationPipeline = inPipeline.get_editor_property("animation_pipeline")
            if animationPipeline is not None:
                originalImportAnimations = self._originalValues.get(
                    "animation_pipeline.import_animations"
                )
                if originalImportAnimations is not None:
                    animationPipeline.set_editor_property(
                        "import_animations", originalImportAnimations
                    )

            # 2. material_pipeline.import_materials 복원
            materialPipeline = inPipeline.get_editor_property("material_pipeline")
            if materialPipeline is not None:
                originalImportMaterials = self._originalValues.get(
                    "material_pipeline.import_materials"
                )
                if originalImportMaterials is not None:
                    materialPipeline.set_editor_property(
                        "import_materials", originalImportMaterials
                    )

                # 3. texture_pipeline.import_textures 복원
                texturePipeline = materialPipeline.get_editor_property("texture_pipeline")
                if texturePipeline is not None:
                    originalImportTextures = self._originalValues.get(
                        "texture_pipeline.import_textures"
                    )
                    if originalImportTextures is not None:
                        texturePipeline.set_editor_property(
                            "import_textures", originalImportTextures
                        )

            # 4. mesh_pipeline.create_physics_asset 복원
            meshPipeline = inPipeline.get_editor_property("mesh_pipeline")
            if meshPipeline is not None:
                originalCreatePhysicsAsset = self._originalValues.get(
                    "mesh_pipeline.create_physics_asset"
                )
                if originalCreatePhysicsAsset is not None:
                    meshPipeline.set_editor_property(
                        "create_physics_asset", originalCreatePhysicsAsset
                    )

            # 5. common_skeletal_meshes_and_animations_properties 복원
            commonSkeletalProps = inPipeline.get_editor_property(
                "common_skeletal_meshes_and_animations_properties"
            )
            if commonSkeletalProps is not None:
                originalSkeleton = self._originalValues.get(
                    "common_skeletal_props.skeleton"
                )
                # skeleton은 None일 수 있으므로 키 존재 여부로 확인
                if "common_skeletal_props.skeleton" in self._originalValues:
                    commonSkeletalProps.set_editor_property("skeleton", originalSkeleton)

                originalImportOnlyAnimations = self._originalValues.get(
                    "common_skeletal_props.import_only_animations"
                )
                if originalImportOnlyAnimations is not None:
                    commonSkeletalProps.set_editor_property(
                        "import_only_animations", originalImportOnlyAnimations
                    )

            # 원본 값 초기화 (다음 임포트를 위해)
            self._originalValues = {}

            # 파이프라인 에셋 리버트 (Perforce에서 변경 사항 되돌리기)
            pipelinePath = inPipeline.get_path_name()
            if pipelinePath:
                packagePath = pipelinePath.split(".")[0]
                reverted = unreal.SourceControl.revert_files([packagePath])
                if reverted:
                    unreal.log(
                        f"[InterchangePipelineSettings] 파이프라인 에셋 리버트 완료: {packagePath}"
                    )
                    # 리버트 후 에셋 리로드 (메모리 dirty 상태 해제)
                    unreal.EditorAssetLibrary.load_asset(packagePath)
                    unreal.log(
                        f"[InterchangePipelineSettings] 파이프라인 에셋 리로드 완료: {packagePath}"
                    )
                else:
                    unreal.log_warning(
                        f"[InterchangePipelineSettings] 파이프라인 에셋 리버트 실패 (이미 최신 상태이거나 체크아웃 상태 아님): {packagePath}"
                    )

            unreal.log("[InterchangePipelineSettings] 파이프라인 복원 완료")
            return True

        except Exception as e:
            unreal.log_error(
                f"[InterchangePipelineSettings] 파이프라인 복원 중 에러: {e}"
            )
            return False

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

        # 원본 값 저장 (설정 변경 전)
        self._store_original_values(inPipeline)

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

        # 원본 값 저장 (설정 변경 전)
        self._store_original_values(inPipeline)

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

        # 원본 값 저장 (설정 변경 전)
        self._store_original_values(inPipeline)

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
