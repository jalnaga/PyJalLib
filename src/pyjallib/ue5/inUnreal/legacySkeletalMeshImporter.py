#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 스켈레탈 메쉬 임포터 모듈
UE5에서 스켈레탈 메쉬를 임포트하는 기능을 제공합니다.
"""

import unreal
from pathlib import Path

# UE5 모듈 import
from legacyBaseImporter import LegacyBaseImporter


class LegacySkeletalMeshImporter(LegacyBaseImporter):
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "SkeletalMesh")
        unreal.log("[LegacySkeletalMeshImporter] 초기화 완료")

    @property
    def asset_type(self) -> str:
        return "SkeletalMesh"

    def create_import_task(self, inFbxFile: str, inDestinationPath: str, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None):
        """스켈레탈 메시 임포트를 위한 태스크 생성 - 스켈레톤 필수 지정"""
        unreal.log(f"[LegacySkeletalMeshImporter] 스켈레탈 메시 임포트 태스크 생성 시작: {inFbxFile}")

        importOptions = self.importerSettings.load_options()
        unreal.log("[LegacySkeletalMeshImporter] 스켈레탈 메시 임포트 옵션 로드 완료")

        # 스켈레톤 경로 결정: inSkeletonContentPath 우선, 없으면 FBX 경로 변환
        if inSkeletonContentPath is not None:
            skeletonPath = inSkeletonContentPath
            unreal.log(f"[LegacySkeletalMeshImporter] Content 경로를 직접 사용: {skeletonPath}")
        elif inFbxSkeletonPath is not None:
            skeletonPath = self.convert_fbx_path_to_skeleton_path(inFbxSkeletonPath)
            unreal.log(f"[LegacySkeletalMeshImporter] FBX 경로를 Content 경로로 변환: {inFbxSkeletonPath} -> {skeletonPath}")
        else:
            error_msg = "스켈레탈 메시 임포트에는 스켈레톤이 필수입니다 (inSkeletonContentPath 또는 inFbxSkeletonPath 중 하나 제공 필요)"
            unreal.log_error(f"[LegacySkeletalMeshImporter] {error_msg}")
            raise ValueError(error_msg)

        skeletonAssetData = unreal.EditorAssetLibrary.find_asset_data(skeletonPath)
        if not skeletonAssetData.is_valid():
            error_msg = f"스켈레톤 에셋을 찾을 수 없음: {skeletonPath}"
            unreal.log_error(f"[LegacySkeletalMeshImporter] {error_msg}")
            raise ValueError(error_msg)

        skeletalSkeleton = skeletonAssetData.get_asset()
        importOptions.set_editor_property('skeleton', skeletalSkeleton)
        unreal.log(f"[LegacySkeletalMeshImporter] 스켈레톤 설정됨: {skeletalSkeleton.get_name()}")

        # 에셋 이름 결정: FBX 파일 이름에서 확장자 제거
        assetName = Path(inFbxFile).stem

        task = unreal.AssetImportTask()
        task.automated = True
        task.destination_path = inDestinationPath
        task.filename = inFbxFile
        task.destination_name = assetName
        task.replace_existing = True
        task.save = True
        task.options = importOptions

        unreal.log(f"[LegacySkeletalMeshImporter] 스켈레탈 메시 임포트 태스크 생성 완료: Destination={inDestinationPath}, AssetName={assetName}")
        return task

    def import_skeletal_mesh(self, inFbxFile: str, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None, inAssetName: str = None, inDescription: str = None):
        """스켈레탈 메시 FBX를 임포트하고 연 파일 목록을 결과에 담아 반환합니다.

        임포트와 체크아웃만 수행한다. 서밋(`check_in_files`)은 하지 않으며,
        연 파일은 default 체인지리스트에 남는다. 이름 붙은 CL로의 이동과 서밋은
        호출자(에디터 밖 툴 프로세스)가 `pyjallib.perforce.Perforce`로 처리한다.

        Args:
            inFbxFile: 스켈레탈 메시 FBX 파일의 절대 경로
            inFbxSkeletonPath: 스켈레톤 FBX 경로 (Content 경로로 변환됨)
            inSkeletonContentPath: 스켈레톤 Content 경로 (직접 사용, 우선)
            inAssetName: 에셋 이름 (선택적, None이면 FBX 파일명 사용)
            inDescription: 호출부 호환을 위해 유지되는 인자. 서밋이 임포터에서
                제거되어 더 이상 사용하지 않는다 (CL 설명은 툴 프로세스가 구성).

        Returns:
            dict: 임포트 결과 딕셔너리. `OpenedFiles`에 연 파일의 로컬 절대경로
                (임포트 결과 + dirty deps)가 들어간다.

        Raises:
            ValueError: 스켈레톤 미존재 또는 임포트 실패 시
        """
        unreal.log(f"[LegacySkeletalMeshImporter] 스켈레탈 메시 임포트 시작: {inFbxFile}")

        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"

        # 기존 에셋이 있는 경우 소스 컨트롤에서 체크아웃
        if unreal.Paths.file_exists(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)

        task = self.create_import_task(inFbxFile, destinationPath, inFbxSkeletonPath, inSkeletonContentPath)

        unreal.log(f"[LegacySkeletalMeshImporter] 스켈레탈 메시 임포트 실행: {inFbxFile} -> {destinationPath}/{assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        result = task.get_objects()
        if len(result) == 0:
            error_msg = f"스켈레탈 메시 임포트 실패: {inFbxFile}"
            unreal.log_error(f"[LegacySkeletalMeshImporter] {error_msg}")
            raise ValueError(error_msg)

        # 임포트된 스켈레탈 메시 에셋의 시스템 경로 가져오기
        importedSkeletalMesh = None
        for asset in result:
            if isinstance(asset, unreal.SkeletalMesh):
                importedSkeletalMesh = asset
                break

        if importedSkeletalMesh is None:
            error_msg = f"스켈레탈 메시 에셋을 찾을 수 없음: {inFbxFile}"
            unreal.log_error(f"[LegacySkeletalMeshImporter] {error_msg}")
            raise ValueError(error_msg)

        # 임포트 결과 + dirty deps를 소스 컨트롤에 연다 (체크아웃까지만 - 서밋 없음).
        # 경로는 Content 경로로 통일해 넘긴다 (open_for_source_control이 절대경로로 해석).
        refObjectPaths = self.get_dirty_deps(assetFullPath)
        allImportRelatedPaths = list(dict.fromkeys([assetFullPath] + refObjectPaths))
        allImportAbsPaths = self.open_for_source_control(allImportRelatedPaths)

        unreal.log(f"[LegacySkeletalMeshImporter] 스켈레탈 메시 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        return self._create_result_dict(
            inFbxFile, destinationPath, assetName, True, allImportAbsPaths
        )
