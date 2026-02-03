#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TemplateProcessor 통합 메서드 테스트
process_import_template() 메서드 및 파일명 자동 생성 기능 테스트
"""

import pytest
import warnings
from pathlib import Path

from pyjallib.ue5.templateProcessor import TemplateProcessor

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
TEMP_DIR = PROJECT_ROOT / "temp" / "unified_scripts"


@pytest.fixture(scope="session", autouse=True)
def setup_temp_dir():
    """테스트 전에 temp 디렉토리 생성"""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    yield


# === Task 11: 새 통합 메서드 테스트 ===

def test_process_import_template_skeleton_legacy():
    """통합 메서드 - skeleton + legacy 조합 테스트"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'inDestinationPath': '/Game/TestCharacter',
        'inAssetName': ''
    }

    # 스크립트 생성
    result = processor.process_import_template('skeleton', 'legacy', template_data)

    assert result is not None, "템플릿 처리 결과가 None입니다"

    # 필수 내용 확인
    assert 'LegacySkeletonImporter' in result
    assert template_data['inFbxPath'] in result


def test_process_import_template_skeletal_mesh_legacy():
    """통합 메서드 - skeletal_mesh + legacy 조합 테스트"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestMesh.fbx',
        'inDestinationPath': '/Game/TestCharacter',
        'inSkeletonPath': '/Game/TestCharacter/TestSkeleton',
        'inAssetName': ''
    }

    result = processor.process_import_template('skeletal_mesh', 'legacy', template_data)

    assert result is not None
    assert 'LegacySkeletalMeshImporter' in result
    assert template_data['inFbxPath'] in result
    assert template_data['inSkeletonPath'] in result


def test_process_import_template_animation_legacy():
    """통합 메서드 - animation + legacy 조합 테스트"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/Animations/TestAnim.fbx',
        'inDestinationPath': '/Game/TestCharacter/Animations',
        'inSkeletonPath': '/Game/TestCharacter/TestSkeleton',
        'inAssetName': ''
    }

    result = processor.process_import_template('animation', 'legacy', template_data)

    assert result is not None
    assert 'LegacyAnimationImporter' in result
    assert template_data['inFbxPath'] in result


def test_process_import_template_skeleton_interchange():
    """통합 메서드 - skeleton + interchange 조합 테스트"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'inDestinationPath': '/Game/TestCharacter',
        'inAssetName': ''
    }

    result = processor.process_import_template('skeleton', 'interchange', template_data)

    assert result is not None
    assert 'InterchangeSkeletonImporter' in result or 'unreal.InterchangeManager' in result


def test_process_import_template_invalid_asset_type():
    """통합 메서드 - 잘못된 asset_type 에러 테스트"""
    processor = TemplateProcessor()

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'inDestinationPath': '/Game/TestCharacter'
    }

    with pytest.raises(ValueError, match="잘못된 asset_type"):
        processor.process_import_template('invalid_type', 'legacy', template_data)


def test_process_import_template_invalid_template_type():
    """통합 메서드 - 잘못된 template_type 에러 테스트"""
    processor = TemplateProcessor()

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'inDestinationPath': '/Game/TestCharacter'
    }

    with pytest.raises(ValueError, match="잘못된 asset_type"):
        processor.process_import_template('skeleton', 'invalid_template', template_data)


def test_process_import_template_missing_required_keys():
    """통합 메서드 - 필수 키 누락 에러 테스트"""
    processor = TemplateProcessor()

    # inFbxPath 누락
    incomplete_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inDestinationPath': '/Game/TestCharacter'
    }

    with pytest.raises(ValueError, match="필요한 키가 누락"):
        processor.process_import_template('skeleton', 'legacy', incomplete_data)


def test_process_import_template_missing_skeleton_path():
    """통합 메서드 - skeletal_mesh의 inSkeletonPath 누락 에러 테스트"""
    processor = TemplateProcessor()

    # inSkeletonPath 누락
    incomplete_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestMesh.fbx',
        'inDestinationPath': '/Game/TestCharacter'
    }

    with pytest.raises(ValueError, match="필요한 키가 누락"):
        processor.process_import_template('skeletal_mesh', 'legacy', incomplete_data)


# === Task 12: Deprecation Warning 테스트 ===

def test_interchange_skeleton_deprecation_warning():
    """Interchange 스켈레톤 메서드 - DeprecationWarning 발생 확인"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'inDestinationPath': '/Game/TestCharacter',
        'inAssetName': ''
    }

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        processor.process_interchange_skeleton_import_template(template_data)

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()


# === Task 13: 생성된 스크립트 파일명 검증 테스트 ===

def test_output_filename_generation_legacy_skeleton():
    """파일명 자동 생성 - legacy_skeletonImport.py 형식 확인"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'inDestinationPath': '/Game/TestCharacter',
        'inAssetName': ''
    }

    processor.process_import_template('skeleton', 'legacy', template_data)

    expected_filename = TEMP_DIR / "legacy_skeletonImport.py"
    assert expected_filename.exists(), f"파일명이 예상과 다릅니다: {expected_filename}"


def test_output_filename_generation_interchange_animation():
    """파일명 자동 생성 - interchange_animationImport.py 형식 확인"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/Animations/TestAnim.fbx',
        'inDestinationPath': '/Game/TestCharacter/Animations',
        'inSkeletonPath': '/Game/TestCharacter/TestSkeleton',
        'inAssetName': ''
    }

    processor.process_import_template('animation', 'interchange', template_data)

    expected_filename = TEMP_DIR / "interchange_animationImport.py"
    assert expected_filename.exists(), f"파일명이 예상과 다릅니다: {expected_filename}"


def test_output_filename_generation_legacy_skeletal_mesh():
    """파일명 자동 생성 - legacy_skeletal_meshImport.py 형식 확인"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPath': 'D:/FBX/TestCharacter/TestMesh.fbx',
        'inDestinationPath': '/Game/TestCharacter',
        'inSkeletonPath': '/Game/TestCharacter/TestSkeleton',
        'inAssetName': ''
    }

    processor.process_import_template('skeletal_mesh', 'legacy', template_data)

    expected_filename = TEMP_DIR / "legacy_skeletal_meshImport.py"
    assert expected_filename.exists(), f"파일명이 예상과 다릅니다: {expected_filename}"


def test_output_filename_generation_interchange_batch_animation():
    """파일명 자동 생성 - interchange_batch_animationImport.py 형식 확인"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    anim_paths = [
        'D:/FBX/TestCharacter/Animations/Walk.fbx',
        'D:/FBX/TestCharacter/Animations/Run.fbx'
    ]

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inFbxPaths': str(anim_paths),
        'inDestinationPath': '/Game/TestCharacter/Animations',
        'inSkeletonPath': '/Game/TestCharacter/TestSkeleton'
    }

    processor.process_import_template('batch_animation', 'interchange', template_data)

    expected_filename = TEMP_DIR / "interchange_batch_animationImport.py"
    assert expected_filename.exists(), f"파일명이 예상과 다릅니다: {expected_filename}"


def test_all_template_combinations_filenames():
    """모든 template_type과 asset_type 조합의 파일명 생성 확인"""
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(TEMP_DIR))

    combinations = [
        ('skeleton', 'legacy'),
        ('skeleton', 'interchange'),
        ('skeletal_mesh', 'legacy'),
        ('skeletal_mesh', 'interchange'),
        ('animation', 'legacy'),
        ('animation', 'interchange'),
        ('batch_animation', 'legacy'),
        ('batch_animation', 'interchange'),
    ]

    for asset_type, template_type in combinations:
        # 기본 템플릿 데이터
        template_data = {
            'inExtPackagePath': 'D:/TestProject/Content',
            'inDestinationPath': '/Game/TestCharacter'
        }

        # asset_type에 따라 필수 키 추가
        if asset_type == 'batch_animation':
            template_data['inFbxPaths'] = str(['D:/FBX/Test.fbx'])
        else:
            template_data['inFbxPath'] = 'D:/FBX/Test.fbx'

        if asset_type in ['skeletal_mesh', 'animation', 'batch_animation']:
            template_data['inSkeletonPath'] = '/Game/TestCharacter/TestSkeleton'

        # 스크립트 생성
        processor.process_import_template(asset_type, template_type, template_data)

        # 예상 파일명 검증
        expected_filename = TEMP_DIR / f"{template_type}_{asset_type}Import.py"
        assert expected_filename.exists(), f"파일명 생성 실패: {expected_filename}"
