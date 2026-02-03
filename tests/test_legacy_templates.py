#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Legacy 템플릿 처리 테스트
각 Legacy 템플릿에 대해 templateProcessor가 정상적으로 스크립트를 생성하는지 확인
"""

import ast
import pytest
from pathlib import Path

from pyjallib.ue5.templateProcessor import TemplateProcessor

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
TEMP_DIR = PROJECT_ROOT / "temp" / "generated_scripts"


@pytest.fixture(scope="session", autouse=True)
def setup_temp_dir():
    """테스트 전에 temp 디렉토리 생성"""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # 테스트 후 정리는 하지 않음 (사용자가 확인할 수 있도록)


def test_legacy_skeleton_import_template():
    """Legacy 스켈레톤 임포트 템플릿 테스트"""
    processor = TemplateProcessor()

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': 'D:/FBX',
        'inSkeletonFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx'
    }

    output_path = str(TEMP_DIR / "test_legacy_skeleton_import.py")

    # 스크립트 생성
    result = processor.process_legacy_skeleton_import_template(template_data, output_path)

    assert result is not None, "템플릿 처리 결과가 None입니다"
    assert Path(output_path).exists(), f"출력 파일이 생성되지 않았습니다: {output_path}"

    # 생성된 스크립트를 파이썬으로 파싱하여 문법 검증
    with open(output_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    # 문법 오류가 있으면 ast.parse가 예외를 발생시킴
    ast.parse(script_content)

    # 필수 내용이 포함되어 있는지 확인
    assert 'LegacySkeletonImporter' in script_content
    assert template_data['inSkeletonFbxPath'] in script_content


def test_legacy_skeletal_mesh_import_template():
    """Legacy 스켈레탈 메시 임포트 템플릿 테스트"""
    processor = TemplateProcessor()

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': 'D:/FBX',
        'inSkeletalMeshFbxPath': 'D:/FBX/TestCharacter/TestMesh.fbx',
        'inSkeletonFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx'
    }

    output_path = str(TEMP_DIR / "test_legacy_skeletal_mesh_import.py")

    # 스크립트 생성
    result = processor.process_legacy_skeletal_mesh_import_template(template_data, output_path)

    assert result is not None, "템플릿 처리 결과가 None입니다"
    assert Path(output_path).exists(), f"출력 파일이 생성되지 않았습니다: {output_path}"

    # 생성된 스크립트를 파이썬으로 파싱하여 문법 검증
    with open(output_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    ast.parse(script_content)

    # 필수 내용이 포함되어 있는지 확인
    assert 'LegacySkeletalMeshImporter' in script_content
    assert template_data['inSkeletalMeshFbxPath'] in script_content
    assert template_data['inSkeletonFbxPath'] in script_content


def test_legacy_animation_import_template():
    """Legacy 애니메이션 임포트 템플릿 테스트"""
    processor = TemplateProcessor()

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': 'D:/FBX',
        'inAnimFbxPath': 'D:/FBX/TestCharacter/Animations/TestAnim.fbx',
        'inSkeletonFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx'
    }

    output_path = str(TEMP_DIR / "test_legacy_animation_import.py")

    # 스크립트 생성
    result = processor.process_legacy_animation_import_template(template_data, output_path)

    assert result is not None, "템플릿 처리 결과가 None입니다"
    assert Path(output_path).exists(), f"출력 파일이 생성되지 않았습니다: {output_path}"

    # 생성된 스크립트를 파이썬으로 파싱하여 문법 검증
    with open(output_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    ast.parse(script_content)

    # 필수 내용이 포함되어 있는지 확인
    assert 'LegacyAnimationImporter' in script_content
    assert template_data['inAnimFbxPath'] in script_content
    assert template_data['inSkeletonFbxPath'] in script_content


def test_legacy_batch_anim_import_template():
    """Legacy 배치 애니메이션 임포트 템플릿 테스트"""
    processor = TemplateProcessor()

    # 배치 임포트는 리스트를 문자열로 전달
    anim_paths = [
        'D:/FBX/TestCharacter/Animations/Walk.fbx',
        'D:/FBX/TestCharacter/Animations/Run.fbx',
        'D:/FBX/TestCharacter/Animations/Jump.fbx'
    ]
    skeleton_paths = [
        'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'D:/FBX/TestCharacter/TestSkeleton.fbx',
        'D:/FBX/TestCharacter/TestSkeleton.fbx'
    ]

    template_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': 'D:/FBX',
        'inAnimFbxPaths': str(anim_paths),
        'inSkeletonFbxPaths': str(skeleton_paths)
    }

    output_path = str(TEMP_DIR / "test_legacy_batch_anim_import.py")

    # 스크립트 생성
    result = processor.process_legacy_batch_anim_import_template(template_data, output_path)

    assert result is not None, "템플릿 처리 결과가 None입니다"
    assert Path(output_path).exists(), f"출력 파일이 생성되지 않았습니다: {output_path}"

    # 생성된 스크립트를 파이썬으로 파싱하여 문법 검증
    with open(output_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    ast.parse(script_content)

    # 필수 내용이 포함되어 있는지 확인
    assert 'LegacyAnimationImporter' in script_content
    assert 'Walk.fbx' in script_content
    assert 'Run.fbx' in script_content
    assert 'Jump.fbx' in script_content


def test_legacy_skeleton_import_template_missing_keys():
    """Legacy 스켈레톤 임포트 템플릿 - 필수 키 누락 테스트"""
    processor = TemplateProcessor()

    # inSkeletonFbxPath 누락
    incomplete_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': 'D:/FBX'
    }

    output_path = str(TEMP_DIR / "test_invalid.py")

    # ValueError 예외가 발생해야 함
    with pytest.raises(ValueError, match="필요한 키가 누락"):
        processor.process_legacy_skeleton_import_template(incomplete_data, output_path)


def test_legacy_skeletal_mesh_import_template_missing_keys():
    """Legacy 스켈레탈 메시 임포트 템플릿 - 필수 키 누락 테스트"""
    processor = TemplateProcessor()

    # inSkeletalMeshFbxPath 누락
    incomplete_data = {
        'inExtPackagePath': 'D:/TestProject/Content',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': 'D:/FBX',
        'inSkeletonFbxPath': 'D:/FBX/TestCharacter/TestSkeleton.fbx'
    }

    output_path = str(TEMP_DIR / "test_invalid.py")

    # ValueError 예외가 발생해야 함
    with pytest.raises(ValueError, match="필요한 키가 누락"):
        processor.process_legacy_skeletal_mesh_import_template(incomplete_data, output_path)
