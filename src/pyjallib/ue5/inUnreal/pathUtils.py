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


def to_package_path(inPath: str) -> Optional[str]:
    """소스 컨트롤에 넘길 경로를 패키지 경로(`/Game/A/B`)로 정규화합니다.

    **소스 컨트롤 API는 패키지 경로를 받는다.** 오브젝트 경로(`/Game/A/B.B`)를
    넘기면 `unreal.SourceControl.check_out_or_add_file()`이 이것을 패키지 파일명으로
    변환하지 못하고 문자열을 그대로 절대경로화해, 클라이언트 루트 밖 경로로 조회한 뒤
    `False`를 돌려준다(2026-09-17 실측 - `Path 'D:/Game/Omni/.../A.A' is not under
    client's root 'D:\\root'`, `Could not determine revision control state of file`).

    오브젝트 경로는 임포트 태스크에서 자연스럽게 흘러든다
    (`unreal.AssetImportTask.imported_object_paths`, `UObject.get_path_name()`은
    둘 다 `.에셋이름`이 붙은 형식을 돌려준다). 그래서 **호출부마다 고치지 않고
    소스 컨트롤 진입점에서 정규화한다** - 정적 메쉬 임포터만 고치고 애니메이션
    임포터를 놓쳤던 직전 사이클이 호출부별 수정의 한계를 보여준다.

    Args:
        inPath: 정규화할 경로. 오브젝트 경로(`/Game/A/B.B`), 패키지 경로
            (`/Game/A/B`), `.uasset` 절대경로 중 무엇이 와도 된다.

    Returns:
        `/Game/...` 형식의 패키지 경로. 입력이 비었거나 Content 경로로 해석할 수
        없으면 None.

    Example:
        >>> to_package_path("/Game/Characters/Hero/SK_Hero.SK_Hero")
        "/Game/Characters/Hero/SK_Hero"
        >>> to_package_path("/Game/Characters/Hero/SK_Hero")
        "/Game/Characters/Hero/SK_Hero"
    """
    if not inPath:
        return None

    normalizedPath = inPath.replace("\\", "/")

    if not is_content_path(normalizedPath):
        # Content 경로가 아니면 절대 경로로 간주하고 변환을 시도한다
        # (`.uasset` 확장자 제거는 그쪽이 담당한다).
        convertedPath = absolute_path_to_content_path(normalizedPath)
        if not convertedPath:
            return None
        normalizedPath = convertedPath

    # 오브젝트 경로의 `.에셋이름`을 떼어낸다. 자르기는 **마지막 `/` 뒤 세그먼트에
    # 한정**한다 - 폴더 이름에 `.`이 들어 있어도 경로 중간이 잘리면 안 된다.
    separatorIndex = normalizedPath.rfind("/")
    lastSegment = normalizedPath[separatorIndex + 1:]
    dotIndex = lastSegment.find(".")
    if dotIndex > 0:
        normalizedPath = normalizedPath[:separatorIndex + 1] + lastSegment[:dotIndex]

    return normalizedPath


def checkout_or_add_file(inContentPath: str) -> bool:
    """
    소스 컨트롤에서 파일을 체크아웃하거나 추가합니다.
    파일이 존재하지 않으면 아무 작업도 하지 않습니다.
    
    입력 경로는 `to_package_path()`로 정규화한다 - 오브젝트 경로를 그대로 넘기면
    체크아웃이 실패한다(사유는 `to_package_path` docstring).

    Args:
        inContentPath: 에셋 경로. 패키지 경로·오브젝트 경로·`.uasset` 절대경로 가능.

    Returns:
        체크아웃/추가 성공 시 True, 실패 또는 파일 미존재 시 False

    Example:
        >>> checkout_or_add_file("/Game/Characters/Hero/SK_Hero")
        True  # 기존 파일 체크아웃 성공
    """
    if not inContentPath:
        return False

    packagePath = to_package_path(inContentPath)
    if not packagePath:
        unreal.log_warning(f"[pathUtils] 패키지 경로로 정규화할 수 없음: {inContentPath}")
        return False

    # 파일 존재 여부 확인
    if not unreal.EditorAssetLibrary.does_asset_exist(packagePath):
        # 파일이 없으면 체크아웃할 필요 없음 (새 파일로 생성됨)
        return False

    # 소스 컨트롤 체크아웃
    success = unreal.SourceControl.check_out_or_add_file(packagePath)

    if success:
        unreal.log(f"[pathUtils] 파일 체크아웃 완료: {packagePath}")
    else:
        unreal.log_warning(f"[pathUtils] 파일 체크아웃 실패: {packagePath}")

    return success


def _describe_source_control_error() -> str:
    """직전 소스 컨트롤 작업의 실패 사유를 문자열로 가져옵니다.

    `unreal.SourceControl.last_error_msg()`는 `FText`를 돌려주므로 문자열로
    변환한다. 사유 조회 자체가 실패해도(엔진 버전에 따라 노출이 다를 수 있다)
    호출자가 죽지 않도록 대체 문구를 돌려준다 - 실패를 **보고**하는 것이
    이 경로의 목적이므로, 사유가 비더라도 실패 사실은 남아야 한다.

    Returns:
        str: 실패 사유 문자열. 조회 불가 시 대체 문구.
    """
    try:
        errorMsg = str(unreal.SourceControl.last_error_msg())
    except Exception as e:  # noqa: BLE001 - 사유 조회 실패가 보고를 막으면 안 된다
        return f"실패 사유 조회 불가 ({e})"

    if not errorMsg:
        return "실패 사유 없음 (소스 컨트롤이 사유를 남기지 않음)"
    return errorMsg


def open_for_source_control_checked(inContentPaths: list) -> dict:
    """에셋들을 소스 컨트롤에 열고, 성공분과 실패분을 갈라서 반환합니다.

    UE5 에디터 내부 Python API에는 체인지리스트를 만들거나 옮기는 수단이 없다.
    그래서 에디터 안에서는 파일을 **default 체인지리스트에 열어두기만** 하고,
    이름 붙은 CL로의 이동과 서밋은 에디터 밖 툴 프로세스가 맡는다
    (`pyjallib.perforce.Perforce.move_opened_files_to_new_change_list`).
    여기서 돌려주는 `opened` 목록이 그 핸드오프의 입력이다.

    **성공 판정은 "예외가 나지 않았다"가 아니라 API의 반환값이다.**
    `unreal.SourceControl.check_out_or_add_file()`은 실패해도 예외를 던지지
    않고 `False`를 돌려준다(엔진 `SourceControlHelpers.h`: "true if succeeded,
    false if failed and can call LastErrorMsg()"). 반환값을 버리면 배타 락으로
    열리지 않은 파일이 "연 파일"로 보고되어, 그 목록이 그대로 `p4 reopen`의
    입력이 되고 부분 실패를 낸다(2026-09-17 실측 - `p4 add` 8건 전부 실패했으나
    8건 모두 연 파일로 보고됐다).

    에셋 로드 실패·시스템 경로 해석 실패도 같은 `failed` 목록으로 합류시킨다.
    제외만 하고 보고하지 않으면 **디스크에는 바뀐 에셋이 있는데 어느 CL에도
    없는 상태가 무증상**이 되기 때문이다.

    입력 경로는 `to_package_path()`로 정규화한 뒤 소스 컨트롤에 넘긴다. 호출부가
    오브젝트 경로(`imported_object_paths` 등)를 그대로 넘겨도 되게 하기 위해서다.
    **실패 항목의 `contentPath`에는 정규화 전 입력 원본을 싣는다** - 호출자가 자기가
    넘긴 것으로 대조할 수 있어야 한다.

    Args:
        inContentPaths: 체크아웃/추가할 에셋의 경로 리스트. 패키지 경로
            (`/Game/A/B`), 오브젝트 경로(`/Game/A/B.B`), `.uasset` 절대경로 혼재 가능.

    Returns:
        dict: `{"opened": [로컬 절대경로...], "failed": [{"contentPath": ...,
            "reason": ...}, ...]}`. 두 목록은 서로소이며 입력 순서를 보존한다.
    """
    openedAbsPaths = []
    failedEntries = []

    for assetPath in inContentPaths:
        packagePath = to_package_path(assetPath)
        if not packagePath:
            reason = "패키지 경로로 정규화할 수 없음"
            unreal.log_warning(f"[pathUtils] {reason}으로 목록에서 제외: {assetPath}")
            failedEntries.append({"contentPath": assetPath, "reason": reason})
            continue

        if packagePath != assetPath:
            unreal.log(f"[pathUtils] 소스 컨트롤 경로 정규화: {assetPath} -> {packagePath}")

        checkedOut = unreal.SourceControl.check_out_or_add_file(packagePath, silent=True)
        if not checkedOut:
            reason = _describe_source_control_error()
            unreal.log_warning(f"[pathUtils] 체크아웃 실패로 목록에서 제외: {assetPath} - {reason}")
            failedEntries.append({"contentPath": assetPath, "reason": reason})
            continue

        assetObj = unreal.EditorAssetLibrary.load_asset(packagePath)
        if assetObj is None:
            reason = "에셋 로드 실패"
            unreal.log_warning(f"[pathUtils] {reason}로 목록에서 제외: {assetPath}")
            failedEntries.append({"contentPath": assetPath, "reason": reason})
            continue

        absPath = unreal.SystemLibrary.get_system_path(assetObj)
        if not absPath:
            reason = "시스템 경로 해석 실패"
            unreal.log_warning(f"[pathUtils] {reason}로 목록에서 제외: {assetPath}")
            failedEntries.append({"contentPath": assetPath, "reason": reason})
            continue

        openedAbsPaths.append(absPath)

    unreal.log(
        f"[pathUtils] 소스 컨트롤에 연 파일: {len(openedAbsPaths)}개, "
        f"실패 {len(failedEntries)}개"
    )
    return {"opened": openedAbsPaths, "failed": failedEntries}


def open_for_source_control(inContentPaths: list) -> list:
    """에셋들을 소스 컨트롤에 열고(체크아웃/추가) 로컬 절대경로 목록을 반환합니다.

    구현은 `open_for_source_control_checked`에 위임하는 얇은 래퍼다.
    **체크아웃에 실패한 경로는 목록에서 빠지며**, 실패 사유가 필요하면
    `open_for_source_control_checked`를 직접 써서 `failed`를 받는다.

    Args:
        inContentPaths: 체크아웃/추가할 에셋의 Content 경로 리스트 (/Game/...)

    Returns:
        list: 실제로 연 파일의 로컬 절대경로 리스트.
    """
    return open_for_source_control_checked(inContentPaths)["opened"]


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


def is_content_path(inPath: str) -> bool:
    """
    주어진 경로가 Content 경로 형식(/Game/... 또는 /Engine/...)인지 확인합니다.
    
    Args:
        inPath: 확인할 경로
        
    Returns:
        Content 경로 형식이면 True, 아니면 False
    """
    if not inPath:
        return False
    
    return inPath.startswith('/Game/') or inPath.startswith('/Engine/')


def normalize_content_path(inPath: str) -> Optional[str]:
    """
    절대 경로 또는 Content 경로를 /Game/... 형식으로 정규화합니다.
    
    이미 Content 경로 형식이면 그대로 반환하고,
    절대 경로면 Content 경로로 변환을 시도합니다.
    
    Args:
        inPath: 절대 경로 또는 /Game/... 형식의 Content 경로
        
    Returns:
        /Game/... 형식의 Content 경로. 변환 실패 시 None 반환.
        
    Example:
        >>> normalize_content_path("/Game/Characters/Hero")
        "/Game/Characters/Hero"
        >>> normalize_content_path("D:/UE5Project/Content/Characters/Hero")
        "/Game/Characters/Hero"
    """
    if not inPath:
        return None
    
    # 이미 Content 경로 형식이면 그대로 반환
    if is_content_path(inPath):
        return inPath
    
    # 절대 경로로 간주하고 변환 시도
    convertedPath = absolute_path_to_content_path(inPath)
    
    if convertedPath:
        unreal.log(f"[pathUtils] 절대 경로를 Content 경로로 변환: {inPath} -> {convertedPath}")
    
    return convertedPath
