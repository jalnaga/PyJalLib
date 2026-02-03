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
        homeDir = Path.home()
        documentsFolder = homeDir / "Documents"
        userIniFile = documentsFolder / "ORV" / "ORV_Setting.ini"

        # 기존 파일이 있다면 먼저 읽어오기
        config = configparser.ConfigParser()
        if userIniFile.exists():
            config.read(userIniFile, encoding='utf-8')

        return config.get("Development", "mode")

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

    def _create_result_dict(self, inSourceFile: str, inPath: str, inName: str, inSuccess: bool = True):
        """결과 딕셔너리를 생성하는 공통 메서드"""
        result = {
            "SourceFile": inSourceFile,
            "Path": inPath,
            "Name": inName,
            "Type": self.asset_type,
            "Success": inSuccess
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
