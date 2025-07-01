#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unreal Engine 5 패키지
Unreal Engine 5 작업을 위한 모듈 모음

새로운 구조:
- Unreal Engine이 실행되지 않아도 사용 가능한 기능들 (templates, templateProcessor, logger 등)
- Unreal Engine이 필요한 기능들은 inUnreal 서브모듈에 위치
"""

# Unreal Engine 없이도 사용 가능한 기본 모듈들
__all__ = []

# Logger (조건부 unreal 지원)
try:
    from .logger import (
        ue5_logger,
        set_log_level,
        set_ue5_log_level,
        get_log_file_path,
        set_log_file_path
    )
    __all__.extend([
        'ue5_logger',
        'set_log_level',
        'set_ue5_log_level',
        'get_log_file_path',
        'set_log_file_path'
    ])
except ImportError as e:
    ue5_logger = None
    set_log_level = None
    set_ue5_log_level = None
    get_log_file_path = None
    set_log_file_path = None
    print(f"[PyJalLib] UE5 Logger를 로드할 수 없습니다: {e}")

# TemplateProcessor (Unreal 없이 사용 가능)
try:
    from .templateProcessor import TemplateProcessor
    __all__.append('TemplateProcessor')
except ImportError as e:
    TemplateProcessor = None
    if ue5_logger:
        ue5_logger.error(f"TemplateProcessor를 로드할 수 없습니다: {e}")
    else:
        print(f"[PyJalLib] TemplateProcessor를 로드할 수 없습니다: {e}")

# Templates 모듈 (Unreal 없이 사용 가능)
try:
    from .templates import (
        get_template_path,
        get_all_template_paths,
        get_available_templates,
        validate_template_name,
        ANIM_IMPORT_TEMPLATE,
        SKELETON_IMPORT_TEMPLATE,
        SKELETAL_MESH_IMPORT_TEMPLATE
    )
    __all__.extend([
        'get_template_path',
        'get_all_template_paths',
        'get_available_templates',
        'validate_template_name',
        'ANIM_IMPORT_TEMPLATE',
        'SKELETON_IMPORT_TEMPLATE',
        'SKELETAL_MESH_IMPORT_TEMPLATE'
    ])
except ImportError as e:
    get_template_path = None
    get_all_template_paths = None
    get_available_templates = None
    validate_template_name = None
    ANIM_IMPORT_TEMPLATE = None
    SKELETON_IMPORT_TEMPLATE = None
    SKELETAL_MESH_IMPORT_TEMPLATE = None
    if ue5_logger:
        ue5_logger.error(f"Templates 모듈을 로드할 수 없습니다: {e}")
    else:
        print(f"[PyJalLib] Templates 모듈을 로드할 수 없습니다: {e}")

# disableInterchangeFrameWork (Unreal 없이 사용 가능)
try:
    from .disableInterchangeFrameWork import add_disabled_plugins_to_uproject
    __all__.append('add_disabled_plugins_to_uproject')
except ImportError as e:
    add_disabled_plugins_to_uproject = None
    if ue5_logger:
        ue5_logger.error(f"disableInterchangeFrameWork를 로드할 수 없습니다: {e}")
    else:
        print(f"[PyJalLib] disableInterchangeFrameWork를 로드할 수 없습니다: {e}")

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
        'utils': [],
        'unreal_dependent': []
    }
    
    # Core 모듈들
    if ue5_logger is not None:
        available['core'].append('logger')
    if TemplateProcessor is not None:
        available['core'].append('TemplateProcessor')
    
    # Templates 관련
    if get_template_path is not None:
        available['templates'].append('template_management')
    
    # Utilities
    if add_disabled_plugins_to_uproject is not None:
        available['utils'].append('disableInterchangeFrameWork')
    
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

# 편의 함수들 - 자주 사용되는 기능들을 쉽게 접근할 수 있도록
def create_template_processor():
    """
    TemplateProcessor 인스턴스를 생성합니다.
    
    Returns:
        TemplateProcessor: 새로운 TemplateProcessor 인스턴스
        
    Raises:
        ImportError: TemplateProcessor를 사용할 수 없는 경우
    """
    if TemplateProcessor is None:
        raise ImportError("TemplateProcessor를 사용할 수 없습니다. 모듈 로드에 실패했습니다.")
    return TemplateProcessor()

# 헬퍼 함수들도 __all__에 추가
__all__.extend([
    'is_ue5_available', 
    'get_available_modules', 
    'get_module_status',
    'create_template_processor'
])