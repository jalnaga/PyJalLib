#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
경로 변환 유틸리티 모듈

이 모듈은 절대 경로와 UE5 Content 경로 간의 변환 및
경로 관련 유틸리티 함수를 제공합니다.

의존성: 파이썬 표준 라이브러리 + unreal 모듈만 사용
"""

from pathlib import Path
from typing import Optional

import unreal


def absolute_path_to_content_path(inAbsolutePath: str) -> Optional[str]:
    """
    절대 경로를 /Game/... Content 경로로 변환합니다.
    
    Args:
        inAbsolutePath: 변환할 절대 경로 (UE5 프로젝트 Content 디렉토리 하위 경로)
        
    Returns:
        /Game/...  형식의 Content 경로. 변환 실패 시 None 반환.
        
    Example:
        >>> absolute_path_to_content_path("D:/UE5Project/Content/Characters/Hero.uasset")
        "/Game/Characters/Hero"
    """
    if not inAbsolutePath:
        return None
    
    # UE5 프로젝트의 Content 디렉토리 경로 가져오기
    contentDir = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_content_dir()
    )
    
    absolutePathObj = Path(inAbsolutePath).resolve()
    contentDirObj = Path(contentDir).resolve()
    
    # 절대 경로가 Content 디렉토리로 시작하는지 확인
    try:
        relativePath = absolutePathObj.relative_to(contentDirObj)
    except ValueError:
        # Content 디렉토리 하위 경로가 아님
        unreal.log_error(f"[pathUtils] 절대 경로가 Content 디렉토리 내에 없습니다: {inAbsolutePath}")
        return None
    
    # pathlib을 사용하여 경로 정규화 (백슬래시 → 슬래시)
    normalizedPath = relativePath.as_posix()
    
    # 확장자 제거 (.uasset 등)
    if normalizedPath.endswith('.uasset'):
        normalizedPath = normalizedPath[:-7]  # len('.uasset') == 7
    
    # /Game/ 접두사 추가
    contentPath = f"/Game/{normalizedPath}"
    
    # UE5 내장 함수를 사용하여 경로 정규화
    normalizedContentPath = unreal.Paths.normalize_directory_name(contentPath)
    
    return normalizedContentPath


def ensure_directory_exists(inContentPath: str) -> bool:
    """
    Content 경로의 디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
    
    Args:
        inContentPath: /Game/... 형식의 Content 경로 (파일 또는 디렉토리)
        
    Returns:
        디렉토리가 존재하거나 생성에 성공하면 True, 실패하면 False
        
    Example:
        >>> ensure_directory_exists("/Game/Characters/Hero/SK_Hero")
        True  # /Game/Characters/Hero 디렉토리 생성/확인
    """
    if not inContentPath:
        return False
    
    # 경로에서 디렉토리 부분만 추출 (파일 경로인 경우)
    directoryPath = unreal.Paths.get_path(inContentPath)
    
    if not directoryPath:
        # 루트 경로이거나 유효하지 않은 경로
        return True
    
    # /Game 또는 /Engine 루트 경로는 항상 존재하는 것으로 간주
    if directoryPath in ("/Game", "/Engine"):
        return True
    
    # Content 경로에 대해서는 EditorAssetLibrary 사용
    if unreal.EditorAssetLibrary.does_directory_exist(directoryPath):
        return True
    
    # 디렉토리 생성
    success = unreal.EditorAssetLibrary.make_directory(directoryPath)
    
    if success:
        unreal.log(f"[pathUtils] 디렉토리 생성 완료: {directoryPath}")
    else:
        unreal.log_error(f"[pathUtils] 디렉토리 생성 실패: {directoryPath}")
    
    return success


def checkout_or_add_file(inContentPath: str) -> bool:
    """
    소스 컨트롤에서 파일을 체크아웃하거나 추가합니다.
    파일이 존재하지 않으면 아무 작업도 하지 않습니다.
    
    Args:
        inContentPath: /Game/... 형식의 Content 경로
        
    Returns:
        체크아웃/추가 성공 시 True, 실패 또는 파일 미존재 시 False
        
    Example:
        >>> checkout_or_add_file("/Game/Characters/Hero/SK_Hero")
        True  # 기존 파일 체크아웃 성공
    """
    if not inContentPath:
        return False
    
    # 파일 존재 여부 확인
    if not unreal.EditorAssetLibrary.does_asset_exist(inContentPath):
        # 파일이 없으면 체크아웃할 필요 없음 (새 파일로 생성됨)
        return False
    
    # 소스 컨트롤 체크아웃
    success = unreal.SourceControl.check_out_or_add_file(inContentPath)
    
    if success:
        unreal.log(f"[pathUtils] 파일 체크아웃 완료: {inContentPath}")
    else:
        unreal.log_warning(f"[pathUtils] 파일 체크아웃 실패: {inContentPath}")
    
    return success


def get_asset_name_from_path(inContentPath: str) -> Optional[str]:
    """
    Content 경로에서 에셋 이름을 추출합니다.
    
    Args:
        inContentPath: /Game/... 형식의 Content 경로
        
    Returns:
        에셋 이름 (확장자 제외)
        
    Example:
        >>> get_asset_name_from_path("/Game/Characters/Hero/SK_Hero")
        "SK_Hero"
    """
    if not inContentPath:
        return None
    
    return unreal.Paths.get_base_filename(inContentPath)


def get_directory_from_path(inContentPath: str) -> Optional[str]:
    """
    Content 경로에서 디렉토리 경로를 추출합니다.
    
    Args:
        inContentPath: /Game/... 형식의 Content 경로
        
    Returns:
        디렉토리 경로
        
    Example:
        >>> get_directory_from_path("/Game/Characters/Hero/SK_Hero")
        "/Game/Characters/Hero"
    """
    if not inContentPath:
        return None
    
    return unreal.Paths.get_path(inContentPath)


def validate_fbx_file(inFbxPath: str) -> bool:
    """
    FBX 파일 경로가 유효한지 확인합니다.
    
    Args:
        inFbxPath: FBX 파일의 절대 경로
        
    Returns:
        파일이 존재하고 .fbx 확장자를 가지면 True
    """
    if not inFbxPath:
        return False
    
    fbxPath = Path(inFbxPath)
    
    if not fbxPath.exists():
        unreal.log_error(f"[pathUtils] FBX 파일이 존재하지 않습니다: {inFbxPath}")
        return False
    
    if fbxPath.suffix.lower() != '.fbx':
        unreal.log_error(f"[pathUtils] FBX 파일이 아닙니다: {inFbxPath}")
        return False
    
    return True


def validate_content_path(inContentPath: str) -> bool:
    """
    Content 경로가 유효한 형식인지 확인합니다.
    
    Args:
        inContentPath: /Game/... 형식의 Content 경로
        
    Returns:
        유효한 형식이면 True
    """
    if not inContentPath:
        return False
    
    # /Game/ 또는 /Engine/으로 시작해야 함
    if not (inContentPath.startswith('/Game/') or inContentPath.startswith('/Engine/')):
        unreal.log_error(f"[pathUtils] 유효하지 않은 Content 경로 형식: {inContentPath}")
        return False
    
    return True
