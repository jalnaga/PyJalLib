#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 베이스 임포터 모듈
UE5 에셋 임포트의 기본 기능을 제공하는 추상 클래스입니다.
"""

from pathlib import Path
from abc import ABC, abstractmethod

import configparser

import unreal

# UE5 모듈 import
from legacyImporterSettings import LegacyImporterSettings


class LegacyBaseImporter(ABC):
    """모든 UE5 임포터의 베이스 클래스"""

    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str, inPresetName: str):
        self.contentRootPrefix = inContentRootPrefix
        self.fbxRootPrefix = inFbxRootPrefix
        self.importerSettings = LegacyImporterSettings(
            inContentRootPrefix=inContentRootPrefix,
            inFbxRootPrefix=inFbxRootPrefix,
            inPresetName=inPresetName
        )
        unreal.log(f"[LegacyBaseImporter] 초기화: ContentRoot={inContentRootPrefix}, FbxRoot={inFbxRootPrefix}, Preset={inPresetName}")

    @staticmethod
    def infer_prefixes_from_paths(inDestinationPath: str, inFbxPath: str) -> tuple[str, str]:
        """
        destinationPath와 fbxPath로부터 contentRootPrefix와 fbxRootPrefix를 자동 추론합니다.

        Args:
            inDestinationPath (str): /Game/... 형식의 UE5 Content 경로
            inFbxPath (str): FBX 파일의 절대 경로

        Returns:
            tuple[str, str]: (contentRootPrefix, fbxRootPrefix) 튜플

        Raises:
            ValueError: prefix 추론에 실패한 경우
        """
        unreal.log("[LegacyBaseImporter] Prefix 자동 추론 시작")
        unreal.log(f"[LegacyBaseImporter] destinationPath: {inDestinationPath}")
        unreal.log(f"[LegacyBaseImporter] fbxPath: {inFbxPath}")

        # 1. destinationPath 검증 및 파싱
        if not inDestinationPath.startswith("/Game/"):
            error_msg = f"destinationPath는 /Game/으로 시작해야 합니다: {inDestinationPath}"
            unreal.log_error(f"[LegacyBaseImporter] {error_msg}")
            raise ValueError(error_msg)

        # /Game/ 제거하여 프로젝트 내 상대 경로 추출
        relative_destination = inDestinationPath.replace("/Game/", "", 1)
        # 끝의 슬래시 제거 (디렉토리 경로인 경우)
        relative_destination = relative_destination.rstrip("/")

        unreal.log(f"[LegacyBaseImporter] 상대 destination 경로: {relative_destination}")

        # 2. fbxPath 검증 및 파싱
        fbx_path_obj = Path(inFbxPath)
        if not fbx_path_obj.exists():
            unreal.log_warning(f"[LegacyBaseImporter] FBX 파일이 존재하지 않습니다: {inFbxPath}")

        fbx_dir = fbx_path_obj.parent
        fbx_filename_no_ext = fbx_path_obj.stem

        unreal.log(f"[LegacyBaseImporter] FBX 디렉토리: {fbx_dir}")
        unreal.log(f"[LegacyBaseImporter] FBX 파일명 (확장자 제외): {fbx_filename_no_ext}")

        # 3. contentRootPrefix 추론
        # UE5 프로젝트의 Content 디렉토리
        content_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
        base_content_root = Path(content_dir).resolve()

        unreal.log(f"[LegacyBaseImporter] 기본 Content 디렉토리: {base_content_root}")

        # 4. fbxRootPrefix 및 contentRootPrefix 추론
        # 방법: fbx_dir에서 relative_destination과 일치하는 suffix를 찾음
        # 예: fbx_dir = E:/DevStorage_root/DevStorage/Characters/NPC
        #     relative_destination = Omni/Characters/NPC
        #     일치하는 suffix = Characters/NPC (인덱스 1)
        #     => fbxRootPrefix = E:/DevStorage_root/DevStorage
        #     => contentRootPrefix = D:/root/Omni/Content/Omni

        fbx_dir_str = str(fbx_dir).replace("\\", "/")

        if relative_destination:
            # relative_destination의 각 세그먼트를 순차적으로 fbx_dir_str에서 찾기
            relative_segments = relative_destination.split("/")
            fbx_root_prefix = None
            content_root_prefix = None
            matched_index = None

            # 가장 긴 일치하는 suffix를 찾기
            for i in range(len(relative_segments)):
                suffix = "/".join(relative_segments[i:])
                if fbx_dir_str.endswith(suffix):
                    # suffix 앞부분이 fbxRootPrefix
                    fbx_root_prefix_str = fbx_dir_str[:-len(suffix)].rstrip("/")
                    fbx_root_prefix = Path(fbx_root_prefix_str).resolve()
                    matched_index = i
                    unreal.log(f"[LegacyBaseImporter] 일치하는 경로 suffix 발견: {suffix} (인덱스: {i})")
                    break

            if fbx_root_prefix is None:
                # 일치하는 부분을 찾지 못함 - Fallback
                unreal.log_warning(
                    "[LegacyBaseImporter] FBX 디렉토리 구조가 destination 구조와 일치하지 않습니다. "
                    "FBX 디렉토리의 부모를 fbxRootPrefix로 사용합니다."
                )
                fbx_root_prefix = fbx_dir.parent.resolve()
                content_root_prefix = base_content_root
            else:
                # contentRootPrefix 계산: 일치하지 않는 앞부분을 base_content_root에 추가
                if matched_index > 0:
                    content_subpath = "/".join(relative_segments[:matched_index])
                    content_root_prefix = base_content_root / content_subpath
                    unreal.log(f"[LegacyBaseImporter] Content 서브경로 추가: {content_subpath}")
                else:
                    content_root_prefix = base_content_root
        else:
            # relative_destination이 비어있으면 (루트 레벨)
            fbx_root_prefix = fbx_dir.parent.resolve()
            content_root_prefix = base_content_root

        unreal.log(f"[LegacyBaseImporter] fbxRootPrefix 추론: {fbx_root_prefix}")
        unreal.log(f"[LegacyBaseImporter] contentRootPrefix 추론: {content_root_prefix}")

        # 5. 추론 결과 검증
        if not base_content_root.exists():
            error_msg = f"UE5 Content 디렉토리가 존재하지 않습니다: {base_content_root}"
            unreal.log_error(f"[LegacyBaseImporter] {error_msg}")
            raise ValueError(error_msg)

        unreal.log("[LegacyBaseImporter] Prefix 자동 추론 완료")
        unreal.log(f"[LegacyBaseImporter] contentRootPrefix: {content_root_prefix}")
        unreal.log(f"[LegacyBaseImporter] fbxRootPrefix: {fbx_root_prefix}")

        return str(content_root_prefix), str(fbx_root_prefix)

    def is_development_mode(self) -> bool:
        """개발 모드 여부를 확인합니다.

        `Documents/ORV/ORV_Setting.ini`의 `[Development]` 섹션 `mode` 키를 읽어
        bool로 반환한다. 섹션/키가 누락되거나 ini 파일 자체가 없으면
        `False`로 fallback (비-개발 모드 가정).

        Note:
            과거에는 이 값이 임포터 내부 자동 서밋(`check_in_files`)의 유일한
            차단 수단이었다. 임포터가 순수화되어 서밋을 하지 않게 된 뒤로는
            **서밋 게이트 역할이 이 메서드에서 툴 프로세스로 이동**했다
            (호출자가 `submit_change_list` 호출 여부를 직접 결정한다).
            머신 전역 ini에 의존하던 차단이 호출 단위 결정으로 바뀐 것이며,
            메서드 자체는 로그/임시파일 보존 등 다른 개발 모드 분기를 위해 유지한다.

        Returns:
            개발 모드이면 True, 아니면 False.
        """
        homeDir = Path.home()
        documentsFolder = homeDir / "Documents"
        userIniFile = documentsFolder / "ORV" / "ORV_Setting.ini"

        config = configparser.ConfigParser()
        if userIniFile.exists():
            config.read(userIniFile, encoding='utf-8')
            try:
                return config.get("Development", "mode").lower() == "true"
            except (configparser.NoSectionError, configparser.NoOptionError):
                return False
        return False

    @property
    @abstractmethod
    def asset_type(self) -> str:
        """에셋 타입을 반환하는 추상 프로퍼티"""
        pass

    def convert_fbx_path_to_absolute_content_path(self, inFbxPath: str) -> str:
        """
        FBX 파일 경로를 UE5 Content 경로로 변환합니다.
        fbxRootPrefix가 inFbxPath의 prefix일 경우, contentRootPrefix로 치환합니다.
        Args:
            inFbxPath (str): 변환할 FBX 파일 경로
        Returns:
            str: 변환된 Content 경로
        """
        unreal.log(f"[LegacyBaseImporter] FBX 경로 변환 시작: {inFbxPath}")

        fbxRoot = Path(self.fbxRootPrefix).resolve()
        contentRoot = Path(self.contentRootPrefix).resolve()
        fbxPath = Path(inFbxPath).resolve()

        if str(fbxPath).startswith(str(fbxRoot)):
            relative_path = fbxPath.relative_to(fbxRoot)
            resultPath = relative_path.with_suffix(".uasset")
            result_path = str(contentRoot / resultPath)
            unreal.log(f"[LegacyBaseImporter] 경로 변환 완료: {inFbxPath} -> {result_path}")
            return result_path
        else:
            unreal.log_error(f"[LegacyBaseImporter] 입력 경로가 fbxRootPrefix로 시작하지 않습니다: {inFbxPath}")
            return ""

    def convert_fbx_path_to_content_path(self, inFbxPath: str) -> str:
        unreal.log(f"[LegacyBaseImporter] Content 경로 변환 시작: {inFbxPath}")

        absoluteContentPath = self.convert_fbx_path_to_absolute_content_path(inFbxPath)
        if absoluteContentPath == "":
            return ""

        # UE5 프로젝트의 Content 디렉토리 경로 가져오기
        contentPath = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())

        absoluteContentPathObj = Path(absoluteContentPath)
        contentPathObj = Path(contentPath)

        # absoluteContentPath가 contentPath로 시작하는지 확인
        if str(absoluteContentPathObj).startswith(str(contentPathObj)):
            # contentPath 부분을 /Game/으로 직접 치환
            relativePath = absoluteContentPathObj.relative_to(contentPathObj)
            # pathlib을 사용하여 경로 정규화
            normalizedPath = Path(relativePath).as_posix()
            result_path = f"/Game/{normalizedPath}"

            # UE5 내장 함수를 사용하여 경로 정규화
            normalizedResultPath = unreal.Paths.normalize_directory_name(result_path)

            unreal.log(f"[LegacyBaseImporter] Content 경로 변환 완료: {inFbxPath} -> {normalizedResultPath}")
            return normalizedResultPath
        else:
            unreal.log_error(f"[LegacyBaseImporter] 절대 경로가 콘텐츠 디렉토리로 시작하지 않습니다: {absoluteContentPath}")
            return ""

    def convert_fbx_path_to_skeleton_path(self, inFbxPath: str) -> str:
        """
        FBX 파일 경로를 스켈레톤 경로로 변환합니다.
        fbxRootPrefix가 inFbxPath의 prefix일 경우, contentRootPrefix로 치환합니다.
        """
        skeletonPath = self.convert_fbx_path_to_content_path(inFbxPath)
        if skeletonPath == "":
            return ""

        destinationPath = unreal.Paths.get_path(skeletonPath)
        assetName = unreal.Paths.get_base_filename(skeletonPath)
        # UE5 네이밍 규칙: SK (SkeletalMesh) -> SKEL (Skeleton)
        skeletonPrefix = "SKEL"
        skeletalPrefix = "SK"
        unreal.log(f"[LegacyBaseImporter] skeletonPrefix: {skeletonPrefix}, skeletalPrefix: {skeletalPrefix}")
        assetName = str(assetName).replace(skeletalPrefix, skeletonPrefix)
        skeletonFullPath = f"{destinationPath}/{assetName}"
        return skeletonFullPath

    def verify_asset_saved(self, inAssetPath: str) -> None:
        """임포트된 에셋이 디스크에 저장되었는지 검증하고, 실패 시 예외를 던진다.

        임포트 태스크(save=True)의 저장이 파일 잠금 등으로 실패해도 파이썬
        예외가 발생하지 않아(silent 실패) 툴이 성공으로 오판한다. 패키지가
        dirty로 남아 있으면 재저장을 1회 시도하고, 그래도 실패하면 ValueError를
        던져 호출 스크립트가 에러로 종료(stdout 에러 마커 감지)되게 한다.

        Args:
            inAssetPath: 검증할 에셋의 Content 경로 (/Game/...)

        Raises:
            ValueError: 에셋 저장에 실패한 경우 (디스크 미반영)
        """
        saved = unreal.EditorAssetLibrary.save_asset(inAssetPath, only_if_is_dirty=True)
        if not saved:
            error_msg = f"에셋 저장 실패 - 디스크에 반영되지 않음 (파일 잠금 등 확인 필요): {inAssetPath}"
            unreal.log_error(f"[LegacyBaseImporter] {error_msg}")
            raise ValueError(error_msg)
        unreal.log(f"[LegacyBaseImporter] 에셋 저장 확인: {inAssetPath}")

    def open_for_source_control(self, inAssetPaths: list[str]) -> list[str]:
        """에셋들을 소스 컨트롤에 열고(체크아웃/추가) 로컬 절대경로 목록을 반환합니다.

        UE5 에디터 내부 Python API에는 체인지리스트를 만들거나 옮기는 수단이
        없다. 그래서 임포터는 파일을 **default 체인지리스트에 열어두기만** 하고,
        이름 붙은 CL로의 이동과 서밋은 에디터 밖 툴 프로세스가 맡는다
        (`pyjallib.perforce.Perforce.move_opened_files_to_new_change_list`).
        여기서 돌려주는 절대경로 목록이 그 핸드오프의 입력이다.

        경로를 사전 계산하지 않고 **실제로 연 파일을 그대로 보고**하므로,
        의존성 부수 체크아웃(dirty deps)이 목록에서 누락되지 않는다.

        Args:
            inAssetPaths: 체크아웃/추가할 에셋의 Content 경로 리스트 (/Game/...)

        Returns:
            list[str]: 연 파일의 로컬 절대경로 리스트. 에셋 로드나 시스템 경로
                해석에 실패한 항목은 경고를 남기고 제외한다.
        """
        openedAbsPaths = []
        for assetPath in inAssetPaths:
            unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)

            assetObj = unreal.EditorAssetLibrary.load_asset(assetPath)
            if assetObj is None:
                unreal.log_warning(f"[LegacyBaseImporter] 에셋 로드 실패로 목록에서 제외: {assetPath}")
                continue

            absPath = unreal.SystemLibrary.get_system_path(assetObj)
            if not absPath:
                unreal.log_warning(f"[LegacyBaseImporter] 시스템 경로 해석 실패로 목록에서 제외: {assetPath}")
                continue

            openedAbsPaths.append(absPath)

        unreal.log(f"[LegacyBaseImporter] 소스 컨트롤에 연 파일: {len(openedAbsPaths)}개")
        return openedAbsPaths

    def _create_result_dict(self, inSourceFile: str, inPath: str, inName: str, inSuccess: bool = True,
                            inOpenedFiles: list[str] = None):
        """결과 딕셔너리를 생성하는 공통 메서드

        Args:
            inSourceFile: 임포트 원본 파일 경로
            inPath: 임포트된 에셋의 Content 목적지 경로
            inName: 임포트된 에셋 이름
            inSuccess: 임포트 성공 여부. 기본값 True.
            inOpenedFiles: 소스 컨트롤에 연 파일의 로컬 절대경로 리스트.
                None이면 빈 리스트로 채운다 (키는 항상 존재).

        Returns:
            dict: 임포트 결과 딕셔너리
        """
        result = {
            "SourceFile": inSourceFile,
            "Path": inPath,
            "Name": inName,
            "Type": self.asset_type,
            "Success": inSuccess,
            "OpenedFiles": list(inOpenedFiles) if inOpenedFiles else []
        }
        unreal.log(f"[LegacyBaseImporter] 결과 딕셔너리 생성: {result}")
        return result

    def _prepare_import_paths(self, inFbxFile: str, inAssetName: str = None):
        """임포트 경로를 준비하는 공통 메서드"""
        unreal.log(f"[LegacyBaseImporter] 임포트 경로 준비 시작: {inFbxFile}")

        assetPath = self.convert_fbx_path_to_content_path(inFbxFile)
        if assetPath == "":
            error_msg = f"FBX 파일 경로가 올바르지 않습니다: {inFbxFile}"
            unreal.log_error(f"[LegacyBaseImporter] {error_msg}")
            raise ValueError(error_msg)

        # 경로에서 파일명 분리
        destinationPath = unreal.Paths.get_path(assetPath)
        assetName = unreal.Paths.get_base_filename(assetPath)

        # 에셋 이름 결정: 입력된 이름이 있으면 사용, 없으면 FBX 파일 이름에서 확장자 제거
        if inAssetName is not None:
            assetName = inAssetName

        unreal.log(f"[LegacyBaseImporter] 임포트 경로 정보: Destination={destinationPath}, AssetName={assetName}")

        if not unreal.Paths.directory_exists(destinationPath):
            unreal.log(f"[LegacyBaseImporter] 디렉토리 생성: {destinationPath}")
            unreal.EditorAssetLibrary.make_directory(destinationPath)

        if unreal.Paths.file_exists(assetPath):
            unreal.log(f"[LegacyBaseImporter] 기존 파일 체크아웃: {assetPath}")
            unreal.SourceControl.check_out_or_add_file(assetPath)

        return destinationPath, assetName

    @abstractmethod
    def create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """임포트 태스크를 생성하는 추상 메서드 - 각 임포터에서 구현"""
        pass

    def get_dirty_deps(self, inAssetPath: str):
        returnList = []

        assetRegistry = unreal.AssetRegistryHelpers.get_asset_registry()
        assetData = unreal.EditorAssetLibrary.find_asset_data(inAssetPath)

        unreal.log(f"[LegacyBaseImporter] assetData: {assetData.asset_name}")

        depPackages = assetRegistry.get_dependencies(
            assetData.package_name,
            unreal.AssetRegistryDependencyOptions(
                include_soft_package_references=False,  # Soft reference 제외
                include_hard_package_references=True,   # Hard reference만
                include_searchable_names=False,
                include_soft_management_references=False,
                include_hard_management_references=False
            )
        )

        if depPackages is not None:
            for dep in depPackages:
                depPathStart = str(dep).split('/')[1]
                assetPathStart = str(assetData.package_name).split('/')[1]
                if depPathStart == assetPathStart:
                    if unreal.EditorAssetLibrary.save_asset(dep, only_if_is_dirty=True):
                        returnList.append(dep)

        return returnList
