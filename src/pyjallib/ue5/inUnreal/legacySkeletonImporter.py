#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 스켈레톤 임포터 모듈

이 모듈은 FBX 파일에서 스켈레톤 에셋을 UE5로 임포트하는 기능을 제공합니다.
PyJalLib의 naming 모듈을 사용하여 에셋 이름을 자동 생성합니다.
"""

import unreal
from pathlib import Path

# UE5 모듈 import
from legacyBaseImporter import LegacyBaseImporter


class LegacySkeletonImporter(LegacyBaseImporter):
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "Skeleton")
        unreal.log("[LegacySkeletonImporter] 초기화 완료")

    @property
    def asset_type(self) -> str:
        return "Skeleton"

    def create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """스켈레톤 임포트를 위한 태스크 생성 - 새 스켈레톤 생성"""
        unreal.log(f"[LegacySkeletonImporter] 스켈레톤 임포트 태스크 생성 시작: {inFbxFile}")

        importOptions = self.importerSettings.load_options()
        unreal.log("[LegacySkeletonImporter] 스켈레톤 임포트 옵션 로드 완료")

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

        unreal.log(f"[LegacySkeletonImporter] 스켈레톤 임포트 태스크 생성 완료: Destination={inDestinationPath}, AssetName={assetName}")
        return task

    def import_skeleton(self, inFbxFile: str, inAssetName: str = None, inDescription: str = None):
        unreal.log(f"[LegacySkeletonImporter] 스켈레톤 임포트 시작: {inFbxFile}")

        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        skeletonName = self.naming.replace_name_part("AssetType", assetName, self.naming.get_name_part("AssetType").get_value_by_description("Skeleton"))

        assetFullPath = f"{destinationPath}/{assetName}"
        skeletonFullPath = f"{destinationPath}/{skeletonName}"

        if unreal.Paths.file_exists(assetFullPath) or unreal.Paths.file_exists(skeletonFullPath):
            if unreal.Paths.file_exists(assetFullPath):
                unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)
            if unreal.Paths.file_exists(skeletonFullPath):
                unreal.SourceControl.check_out_or_add_file(skeletonFullPath, silent=True)

        task = self.create_import_task(inFbxFile, destinationPath)

        unreal.log(f"[LegacySkeletonImporter] 스켈레톤 임포트 실행: {inFbxFile} -> {destinationPath}/{assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        result = task.get_objects()
        if len(result) == 0:
            error_msg = f"스켈레톤 임포트 실패: {inFbxFile}"
            unreal.log_error(f"[LegacySkeletonImporter] {error_msg}")
            raise ValueError(error_msg)

        importedSkeletalMesh = None
        for asset in result:
            if isinstance(asset, unreal.SkeletalMesh):
                importedSkeletalMesh = asset
        importedSkeleton = importedSkeletalMesh.skeleton
        skeletonRenameData = unreal.AssetRenameData(importedSkeleton, destinationPath, skeletonName)
        unreal.AssetToolsHelpers.get_asset_tools().rename_assets([skeletonRenameData])

        skeletalMeshSystemFullPath = unreal.SystemLibrary.get_system_path(importedSkeletalMesh)
        skeletonSystemFullPath = unreal.SystemLibrary.get_system_path(importedSkeletalMesh.skeleton)

        importedObjectPaths = self.get_dirty_deps(skeletonSystemFullPath)
        importedObjectPaths.append(skeletonSystemFullPath)

        checkInDescription = f"Skeleton Imported by {inFbxFile} to {assetFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription

        unreal.SourceControl.check_in_files(importedObjectPaths, checkInDescription, silent=True)

        unreal.log(f"[LegacySkeletonImporter] 스켈레톤 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        return self._create_result_dict(inFbxFile, destinationPath, skeletonName, True)
