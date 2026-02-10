#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 inUnreal 패키지
Unreal Engine 5가 실행 중일 때만 사용 가능한 모듈들

주의: 이 패키지의 모든 모듈은 Unreal Engine이 실행 중일 때만 임포트 가능합니다.

의존성: 파이썬 표준 라이브러리 + unreal 모듈만 사용
"""

# UE5 가용성 확인
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

# 기본적으로 사용 가능한 모듈들
__all__ = ['is_ue5_available']

# UE5가 사용 가능한 경우에만 모듈들을 임포트
if is_ue5_available():
    # pathUtils - 경로 변환 유틸리티
    try:
        from . import pathUtils
        __all__.append('pathUtils')
    except ImportError as e:
        pathUtils = None
        print(f"[PyJalLib] pathUtils 임포트 실패: {e}")

    # Interchange Pipeline Settings
    try:
        from .interchangePipelineSettings import InterchangePipelineSettings, InterchangePipelinePreset
        __all__.append('InterchangePipelineSettings')
        __all__.append('InterchangePipelinePreset')
    except ImportError as e:
        InterchangePipelineSettings = None
        InterchangePipelinePreset = None
        print(f"[PyJalLib] InterchangePipelineSettings 임포트 실패: {e}")

    # Interchange Importer Base
    try:
        from .interchangeImporterBase import InterchangeImporterBase
        __all__.append('InterchangeImporterBase')
    except ImportError as e:
        InterchangeImporterBase = None
        print(f"[PyJalLib] InterchangeImporterBase 임포트 실패: {e}")

    # Interchange Skeleton Importer
    try:
        from .interchangeSkeletonImporter import InterchangeSkeletonImporter
        __all__.append('InterchangeSkeletonImporter')
    except ImportError as e:
        InterchangeSkeletonImporter = None
        print(f"[PyJalLib] InterchangeSkeletonImporter 임포트 실패: {e}")

    # Interchange Skeletal Mesh Importer
    try:
        from .interchangeSkeletalMeshImporter import InterchangeSkeletalMeshImporter
        __all__.append('InterchangeSkeletalMeshImporter')
    except ImportError as e:
        InterchangeSkeletalMeshImporter = None
        print(f"[PyJalLib] InterchangeSkeletalMeshImporter 임포트 실패: {e}")

    # Interchange Animation Importer
    try:
        from .interchangeAnimationImporter import InterchangeAnimationImporter
        __all__.append('InterchangeAnimationImporter')
    except ImportError as e:
        InterchangeAnimationImporter = None
        print(f"[PyJalLib] InterchangeAnimationImporter 임포트 실패: {e}")

    # Legacy Base Importer
    try:
        from .legacyBaseImporter import LegacyBaseImporter
        __all__.append('LegacyBaseImporter')
    except ImportError as e:
        LegacyBaseImporter = None
        print(f"[PyJalLib] LegacyBaseImporter 임포트 실패: {e}")

    # Legacy Importer Settings
    try:
        from .legacyImporterSettings import LegacyImporterSettings
        __all__.append('LegacyImporterSettings')
    except ImportError as e:
        LegacyImporterSettings = None
        print(f"[PyJalLib] LegacyImporterSettings 임포트 실패: {e}")

    # Legacy Skeleton Importer
    try:
        from .legacySkeletonImporter import LegacySkeletonImporter
        __all__.append('LegacySkeletonImporter')
    except ImportError as e:
        LegacySkeletonImporter = None
        print(f"[PyJalLib] LegacySkeletonImporter 임포트 실패: {e}")

    # Legacy Skeletal Mesh Importer
    try:
        from .legacySkeletalMeshImporter import LegacySkeletalMeshImporter
        __all__.append('LegacySkeletalMeshImporter')
    except ImportError as e:
        LegacySkeletalMeshImporter = None
        print(f"[PyJalLib] LegacySkeletalMeshImporter 임포트 실패: {e}")

    # Legacy Animation Importer
    try:
        from .legacyAnimationImporter import LegacyAnimationImporter
        __all__.append('LegacyAnimationImporter')
    except ImportError as e:
        LegacyAnimationImporter = None
        print(f"[PyJalLib] LegacyAnimationImporter 임포트 실패: {e}")

    # Legacy Static Mesh Importer
    try:
        from .legacyStaticMeshImporter import LegacyStaticMeshImporter
        __all__.append('LegacyStaticMeshImporter')
    except ImportError as e:
        LegacyStaticMeshImporter = None
        print(f"[PyJalLib] LegacyStaticMeshImporter 임포트 실패: {e}")

else:
    # UE5가 사용 불가능한 경우 모든 모듈을 None으로 설정
    pathUtils = None
    InterchangePipelineSettings = None
    InterchangePipelinePreset = None
    InterchangeImporterBase = None
    InterchangeSkeletonImporter = None
    InterchangeSkeletalMeshImporter = None
    InterchangeAnimationImporter = None
    LegacyBaseImporter = None
    LegacyImporterSettings = None
    LegacySkeletonImporter = None
    LegacySkeletalMeshImporter = None
    LegacyAnimationImporter = None
    LegacyStaticMeshImporter = None
    print("[PyJalLib] Unreal Engine이 실행되지 않았습니다. inUnreal 모듈들을 사용할 수 없습니다.")

def get_available_modules() -> list:
    """
    현재 사용 가능한 모듈 목록을 반환합니다.

    Returns:
        list: 사용 가능한 모듈 이름 목록
    """
    available = []
    if 'pathUtils' in __all__ and pathUtils is not None:
        available.append('pathUtils')
    if 'InterchangePipelineSettings' in __all__ and InterchangePipelineSettings is not None:
        available.append('InterchangePipelineSettings')
    if 'InterchangePipelinePreset' in __all__ and InterchangePipelinePreset is not None:
        available.append('InterchangePipelinePreset')
    if 'InterchangeImporterBase' in __all__ and InterchangeImporterBase is not None:
        available.append('InterchangeImporterBase')
    if 'InterchangeSkeletonImporter' in __all__ and InterchangeSkeletonImporter is not None:
        available.append('InterchangeSkeletonImporter')
    if 'InterchangeSkeletalMeshImporter' in __all__ and InterchangeSkeletalMeshImporter is not None:
        available.append('InterchangeSkeletalMeshImporter')
    if 'InterchangeAnimationImporter' in __all__ and InterchangeAnimationImporter is not None:
        available.append('InterchangeAnimationImporter')
    if 'LegacyBaseImporter' in __all__ and LegacyBaseImporter is not None:
        available.append('LegacyBaseImporter')
    if 'LegacyImporterSettings' in __all__ and LegacyImporterSettings is not None:
        available.append('LegacyImporterSettings')
    if 'LegacySkeletonImporter' in __all__ and LegacySkeletonImporter is not None:
        available.append('LegacySkeletonImporter')
    if 'LegacySkeletalMeshImporter' in __all__ and LegacySkeletalMeshImporter is not None:
        available.append('LegacySkeletalMeshImporter')
    if 'LegacyAnimationImporter' in __all__ and LegacyAnimationImporter is not None:
        available.append('LegacyAnimationImporter')
    if 'LegacyStaticMeshImporter' in __all__ and LegacyStaticMeshImporter is not None:
        available.append('LegacyStaticMeshImporter')
    return available

# 헬퍼 함수도 __all__에 추가
__all__.append('get_available_modules')
