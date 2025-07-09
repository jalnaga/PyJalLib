#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 템플릿 관리 모듈
템플릿 파일 경로를 쉽게 가져올 수 있는 기능 제공
"""

import os
from pathlib import Path
from typing import Dict, Optional

# 템플릿 이름 상수
ANIM_IMPORT_TEMPLATE = "animImport"
SKELETON_IMPORT_TEMPLATE = "skeletonImport" 
SKELETAL_MESH_IMPORT_TEMPLATE = "skeletalMeshImport"
BATCH_ANIM_IMPORT_TEMPLATE = "batchAnimImport"

# 템플릿 파일 매핑
_TEMPLATE_FILE_MAP = {
    ANIM_IMPORT_TEMPLATE: "animImportTemplate.py",
    SKELETON_IMPORT_TEMPLATE: "skeletonImportTemplate.py",
    SKELETAL_MESH_IMPORT_TEMPLATE: "skeletalMeshImportTemplate.py",
    BATCH_ANIM_IMPORT_TEMPLATE: "batchAnimImportTemplate.py"
}

def get_template_path(template_name: str) -> str:
    """
    템플릿 이름으로 템플릿 파일 경로 반환
    
    Args:
        template_name (str): 'animImport', 'skeletonImport', 'skeletalMeshImport', 'batchAnimImport' 중 하나
    
    Returns:
        str: 템플릿 파일의 절대 경로
        
    Raises:
        ValueError: 지원하지 않는 템플릿 이름인 경우
        FileNotFoundError: 템플릿 파일이 존재하지 않는 경우
    """
    if template_name not in _TEMPLATE_FILE_MAP:
        supported_templates = list(_TEMPLATE_FILE_MAP.keys())
        raise ValueError(f"지원하지 않는 템플릿 이름: {template_name}. 지원되는 템플릿: {supported_templates}")
    
    template_filename = _TEMPLATE_FILE_MAP[template_name]
    templates_dir = Path(__file__).parent
    template_path = templates_dir / template_filename
    
    if not template_path.exists():
        raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {template_path}")
    
    return str(template_path.resolve())

def get_all_template_paths() -> Dict[str, str]:
    """
    모든 템플릿 경로를 딕셔너리로 반환
    
    Returns:
        Dict[str, str]: 템플릿 이름을 키로 하고 파일 경로를 값으로 하는 딕셔너리
    """
    template_paths = {}
    for template_name in _TEMPLATE_FILE_MAP.keys():
        try:
            template_paths[template_name] = get_template_path(template_name)
        except (ValueError, FileNotFoundError):
            # 존재하지 않는 템플릿은 건너뛰기
            continue
    
    return template_paths

def get_available_templates() -> list:
    """
    사용 가능한 템플릿 목록 반환
    
    Returns:
        list: 사용 가능한 템플릿 이름 목록
    """
    available = []
    templates_dir = Path(__file__).parent
    
    for template_name, filename in _TEMPLATE_FILE_MAP.items():
        template_path = templates_dir / filename
        if template_path.exists():
            available.append(template_name)
    
    return available

def validate_template_name(template_name: str) -> bool:
    """
    템플릿 이름이 유효한지 확인
    
    Args:
        template_name (str): 확인할 템플릿 이름
        
    Returns:
        bool: 유효한 템플릿 이름이면 True, 그렇지 않으면 False
    """
    return template_name in _TEMPLATE_FILE_MAP

__all__ = [
    'get_template_path',
    'get_all_template_paths',
    'get_available_templates',
    'validate_template_name',
    'ANIM_IMPORT_TEMPLATE',
    'SKELETON_IMPORT_TEMPLATE',
    'SKELETAL_MESH_IMPORT_TEMPLATE',
    'BATCH_ANIM_IMPORT_TEMPLATE'
] 