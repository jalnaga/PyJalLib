"""
UE5 에셋 임포트 설정 관리 모듈

이 모듈은 UE5 에셋 임포트에 필요한 설정을 관리합니다.
JSON 설정 파일을 로드하고, 프리셋 기반으로 설정을 반환하는 기능을 제공합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import unreal
from ..logger import ue5_logger


class ImporterSettings:
    """UE5 에셋 임포트 설정 관리 클래스"""
    
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str, inPresetName: str):
        """
        ImporterSettings 초기화
        
        Args:
            inContentRootPrefix: UE5 Content 경로의 루트 접두사
            inFbxRootPrefix: FBX 파일 경로의 루트 접두사
            inPresetName: 사용할 프리셋 이름 (Skeleton, SkeletalMesh, Animation 중 하나)
        """
        self.contentRootPrefix = inContentRootPrefix
        self.fbxRootPrefix = inFbxRootPrefix
        self.presetName = inPresetName
        
        self.configPath = Path(__file__).parent / 'ConfigFiles' / 'UE5ImportConfig.json'
        ue5_logger.debug(f"ImporterSettings 초기화: ContentRoot={inContentRootPrefix}, FbxRoot={inFbxRootPrefix}, Preset={inPresetName}")
    
    def load_preset(self, inPresetName: Optional[str] = None):
        if inPresetName is None:
            inPresetName = self.presetName
            
        if inPresetName is None:
            raise ValueError("Preset name is required")
        
        preset_path = Path(__file__).parent / 'ConfigFiles' / f'{inPresetName}.json'
    
    def set_options_for_skeleton_import(self):
        """
        스켈레톤 임포트를 위한 옵션을 설정합니다.
        
        스켈레탈 메쉬는 임포트하고, 애니메이션은 임포트하지 않으며,
        매테리얼이나 텍스처도 임포트하지 않고, 스켈레톤은 새로 생성합니다.
        
        Returns:
            unreal.FbxImportUI: 설정된 임포트 옵션
        """
        # FBX 임포트 옵션 설정
        fbxImportOptions = unreal.FbxImportUI()
        fbxImportOptions.reset_to_default()
        fbxImportOptions.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_SKELETAL_MESH)  # 스켈레탈 메쉬 타입
        
        # 메시 임포트 옵션 설정
        fbxImportOptions.set_editor_property('import_mesh', True)  # 스켈레탈 메쉬 임포트
        fbxImportOptions.set_editor_property('import_textures', False)  # 텍스처 임포트 안함
        fbxImportOptions.set_editor_property('import_materials', False)  # 매테리얼 임포트 안함
        fbxImportOptions.set_editor_property('import_animations', False)  # 애니메이션 임포트 안함
        fbxImportOptions.set_editor_property('import_as_skeletal', True)  # 스켈레탈 메쉬로 임포트
        fbxImportOptions.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)  # 스켈레탈 메쉬로 임포트
        fbxImportOptions.set_editor_property('create_physics_asset', False)  # 피직 애셋 생성 안함
        
        # 스켈레탈 메쉬 임포트 세부 옵션
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('import_morph_targets', False)  # 모프 타겟 임포트 안함
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('import_mesh_lo_ds', False)  # LOD 임포트 안함
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('convert_scene_unit', False)  # 씬 단위 변환 안함
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('force_front_x_axis', False)  # X축 강제 변환 안함
        
        # LOD 임포트 (필요하다면)
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('import_mesh_lo_ds', False)  # LOD를 임포트하지 않음
        
        # 스켈레톤 생성 옵션
        fbxImportOptions.set_editor_property('skeleton', None)  # 새 스켈레톤 생성
        
        return fbxImportOptions

    def set_options_for_skeletal_mesh_import(self):
        """
        스켈레탈 메쉬 임포트를 위한 옵션을 설정합니다.
        
        애니메이션은 임포트하지 않고, 메쉬만 임포트하며, 텍스처와 매테리얼은 임포트하지 않고,
        피직 애셋은 만들지 않고, 스켈레톤은 생성하지 않으며, 모프 타겟은 임포트하고,
        노멀과 탄젠트를 계산하여 Geometry and Skin weights로 임포트합니다.
        
        Returns:
            unreal.FbxImportUI: 설정된 임포트 옵션
        """
        # FBX 임포트 옵션 설정
        fbxImportOptions = unreal.FbxImportUI()
        fbxImportOptions.reset_to_default()
        fbxImportOptions.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_SKELETAL_MESH)  # 스켈레탈 메쉬 타입
        
        # 메시 임포트 옵션 설정
        fbxImportOptions.set_editor_property('import_mesh', True)  # 메쉬 임포트
        fbxImportOptions.set_editor_property('import_textures', False)  # 텍스처 임포트 안함
        fbxImportOptions.set_editor_property('import_materials', False)  # 매테리얼 임포트 안함
        fbxImportOptions.set_editor_property('import_animations', False)  # 애니메이션 임포트 안함
        fbxImportOptions.set_editor_property('import_as_skeletal', True)  # 스켈레탈 메쉬로 임포트
        fbxImportOptions.set_editor_property('create_physics_asset', False)  # 피직 애셋 생성 안함
        
        # 스켈레탈 메쉬 임포트 세부 옵션
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('import_morph_targets', True)  # 모프 타겟 임포트
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)  # 노멀 임포트
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('normal_generation_method', unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)  # 탄젠트 계산
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('preserve_smoothing_groups', True)  # 스무딩 그룹 보존
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('reorder_material_to_fbx_order', True)  # Material 순서 재정렬
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('import_mesh_lo_ds', False)  # LOD 임포트 안함
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('convert_scene_unit', False)  # 씬 단위 변환 안함
        fbxImportOptions.skeletal_mesh_import_data.set_editor_property('force_front_x_axis', False)  # X축 강제 변환 안함
        
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
        if inPresetName.lower() == "skeleton":
            return self.set_options_for_skeleton_import()
        elif inPresetName.lower() == "skeletalmesh":
            return self.set_options_for_skeletal_mesh_import()
        elif inPresetName.lower() == "animation":
            return self.set_options_for_animation_import()
        else:
            ue5_logger.error(f"Unsupported preset name: {inPresetName}. Supported presets: Skeleton, SkeletalMesh, Animation")
            raise None


    