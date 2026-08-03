"""
UE5 에셋 임포트 설정 관리 모듈

이 모듈은 UE5 에셋 임포트에 필요한 설정을 관리합니다.
JSON 설정 파일을 로드하고, 프리셋 기반으로 설정을 반환하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional

import unreal


class LegacyImporterSettings:
    """UE5 에셋 임포트 설정 관리 클래스"""

    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str, inPresetName: str):
        """
        LegacyImporterSettings 초기화

        Args:
            inContentRootPrefix: UE5 Content 경로의 루트 접두사
            inFbxRootPrefix: FBX 파일 경로의 루트 접두사
            inPresetName: 사용할 프리셋 이름 (Skeleton, SkeletalMesh, Animation 중 하나)
        """
        self.contentRootPrefix = inContentRootPrefix
        self.fbxRootPrefix = inFbxRootPrefix
        self.presetName = inPresetName

        self.configPath = Path(__file__).parent / 'ConfigFiles' / 'UE5ImportConfig.json'
        unreal.log(f"[LegacyImporterSettings] 초기화: ContentRoot={inContentRootPrefix}, FbxRoot={inFbxRootPrefix}, Preset={inPresetName}")

    def load_preset(self, inPresetName: Optional[str] = None):
        if inPresetName is None:
            inPresetName = self.presetName

        if inPresetName is None:
            raise ValueError("Preset name is required")

        preset_path = Path(__file__).parent / 'ConfigFiles' / f'{inPresetName}.json'

    def set_options_for_static_mesh_import(self):
        """
        스태틱 메쉬 임포트를 위한 옵션을 설정합니다.

        메쉬만 임포트하고, 애니메이션/텍스처/매테리얼은 임포트하지 않으며,
        스켈레탈이 아닌 스태틱 메쉬로 임포트합니다.

        Returns:
            unreal.FbxImportUI: 설정된 임포트 옵션
        """
        fbxImportOptions = unreal.FbxImportUI()
        fbxImportOptions.reset_to_default()
        fbxImportOptions.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_STATIC_MESH)
        fbxImportOptions.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)

        # 메시 임포트 옵션
        fbxImportOptions.set_editor_property('import_mesh', True)
        fbxImportOptions.set_editor_property('import_as_skeletal', False)
        fbxImportOptions.set_editor_property('import_textures', False)
        fbxImportOptions.set_editor_property('import_materials', False)
        fbxImportOptions.set_editor_property('import_animations', False)

        # Static Mesh 세부 옵션
        fbxImportOptions.static_mesh_import_data.set_editor_property('combine_meshes', True)
        fbxImportOptions.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
        fbxImportOptions.static_mesh_import_data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        fbxImportOptions.static_mesh_import_data.set_editor_property('normal_generation_method', unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
        fbxImportOptions.static_mesh_import_data.set_editor_property('reorder_material_to_fbx_order', True)
        fbxImportOptions.static_mesh_import_data.set_editor_property('convert_scene_unit', False)
        fbxImportOptions.static_mesh_import_data.set_editor_property('force_front_x_axis', False)

        return fbxImportOptions

    def set_options_for_animation_import(self):
        """
        애니메이션 임포트를 위한 옵션을 설정합니다.

        애니메이션은 임포트하고, 메쉬는 임포트하지 않으며, 텍스처와 매테리얼은 임포트하지 않고,
        피직 애셋은 만들지 않고, 스켈레톤은 생성하지 않으며, Animation Length는 Source와 같게 설정합니다.

        Returns:
            unreal.FbxImportUI: 설정된 임포트 옵션
        """
        # FBX 임포트 옵션 설정
        fbxImportOptions = unreal.FbxImportUI()
        fbxImportOptions.reset_to_default()
        fbxImportOptions.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_ANIMATION)  # 애니메이션 타입

        # 메시 임포트 옵션 설정
        fbxImportOptions.set_editor_property('import_animations', True)  # 애니메이션 임포트
        fbxImportOptions.set_editor_property('import_mesh', False)  # 메쉬 임포트 안함
        fbxImportOptions.set_editor_property('import_textures', False)  # 텍스처 임포트 안함
        fbxImportOptions.set_editor_property('import_materials', False)  # 매테리얼 임포트 안함

        fbxImportOptions.anim_sequence_import_data.set_editor_property('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        fbxImportOptions.anim_sequence_import_data.set_editor_property('do_not_import_curve_with_zero', True)
        fbxImportOptions.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
        fbxImportOptions.anim_sequence_import_data.set_editor_property('import_custom_attribute', True)
        fbxImportOptions.anim_sequence_import_data.set_editor_property('import_meshes_in_bone_hierarchy', True)

        return fbxImportOptions

    def load_options(self, inPresetName: Optional[str] = None) -> unreal.FbxImportUI:
        """
        PresetName에 따라 적절한 임포트 옵션을 로드합니다.

        Args:
            inPresetName (Optional[str]): 프리셋 이름. None인 경우 self.presetName 사용

        Returns:
            unreal.FbxImportUI: 설정된 임포트 옵션

        Raises:
            ValueError: 지원하지 않는 프리셋 이름인 경우
        """
        if inPresetName is None:
            inPresetName = self.presetName

        if inPresetName is None:
            raise ValueError("Preset name is required")

        # PresetName에 따라 적절한 메소드 호출
        if inPresetName.lower() == "staticmesh":
            return self.set_options_for_static_mesh_import()
        elif inPresetName.lower() == "animation":
            return self.set_options_for_animation_import()
        else:
            unreal.log_error(f"[LegacyImporterSettings] Unsupported preset name: {inPresetName}. Supported presets: StaticMesh, Animation")
            return None
