#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unreal Engine 5 패키지
Unreal Engine 5 작업을 위한 모듈 모음

구조:
- Unreal Engine이 실행되지 않아도 사용 가능한 기능들 (templates, templateProcessor)
- Unreal Engine이 필요한 기능들은 inUnreal 서브모듈에 위치
"""

# Unreal Engine 없이도 사용 가능한 기본 모듈들
__all__ = []

# TemplateProcessor (Unreal 없이 사용 가능)
try:
    from .templateProcessor import TemplateProcessor
    __all__.append('TemplateProcessor')
except ImportError as e:
    TemplateProcessor = None
    print(f"[PyJalLib] TemplateProcessor를 로드할 수 없습니다: {e}")

# Templates 모듈 (Unreal 없이 사용 가능)
try:
    from .templates import (
        get_template_path,
        get_all_template_paths,
        get_available_templates,
        validate_template_name,
        INTERCHANGE_ANIM_IMPORT_TEMPLATE,
        INTERCHANGE_SKELETON_IMPORT_TEMPLATE,
        INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE,
        INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE
    )
    __all__.extend([
        'get_template_path',
        'get_all_template_paths',
        'get_available_templates',
        'validate_template_name',
        'INTERCHANGE_ANIM_IMPORT_TEMPLATE',
        'INTERCHANGE_SKELETON_IMPORT_TEMPLATE',
        'INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE',
        'INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE'
    ])
except ImportError as e:
    get_template_path = None
    get_all_template_paths = None
    get_available_templates = None
    validate_template_name = None
    INTERCHANGE_ANIM_IMPORT_TEMPLATE = None
    INTERCHANGE_SKELETON_IMPORT_TEMPLATE = None
    INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE = None
    INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE = None
    print(f"[PyJalLib] Templates 모듈을 로드할 수 없습니다: {e}")

# UE5 의존성 상태를 확인할 수 있는 함수
def is_ue5_available() -> bool:
    """
    Unreal Engine 5가 사용 가능한지 확인합니다.
    
    Returns:
        bool: UE5가 사용 가능하면 True, 그렇지 않으면 False
    """
    try:
        import unreal
        return True
    except ImportError:
        return False

def get_available_modules() -> dict:
    """
    현재 사용 가능한 모듈 목록을 반환합니다.
    
    Returns:
        dict: 모듈 카테고리별 사용 가능한 모듈 정보
    """
    available = {
        'core': [],
        'templates': [],
        'unreal_dependent': []
    }
    
    # Core 모듈들
    if TemplateProcessor is not None:
        available['core'].append('TemplateProcessor')
    
    # Templates 관련
    if get_template_path is not None:
        available['templates'].append('template_management')
    
    # Unreal 의존성 모듈들 (inUnreal 서브모듈에서 가져오기)
    try:
        from . import inUnreal
        if hasattr(inUnreal, 'get_available_modules'):
            available['unreal_dependent'] = inUnreal.get_available_modules()
    except ImportError:
        available['unreal_dependent'] = []
    
    return available

def get_module_status() -> dict:
    """
    모듈 상태 정보를 반환합니다.
    
    Returns:
        dict: 모듈 상태 정보
    """
    status = {
        'ue5_available': is_ue5_available(),
        'available_modules': get_available_modules(),
        'structure': {
            'core_modules': 'Unreal Engine 없이 사용 가능',
            'inUnreal_modules': 'Unreal Engine 필요',
            'templates': '템플릿 파일 관리'
        }
    }
    return status

# 헬퍼 함수들도 __all__에 추가
__all__.extend([
    'is_ue5_available', 
    'get_available_modules', 
    'get_module_status'
])
