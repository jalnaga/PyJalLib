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
        """스켈레톤 FBX를 임포트하고 연 파일 목록을 결과에 담아 반환합니다.

        임포트와 체크아웃만 수행한다. 서밋(`check_in_files`)은 하지 않으며,
        연 파일은 default 체인지리스트에 남는다. 이름 붙은 CL로의 이동과 서밋은
        호출자(에디터 밖 툴 프로세스)가 `pyjallib.perforce.Perforce`로 처리한다.

        Args:
            inFbxFile: 스켈레톤 FBX 파일의 절대 경로
            inAssetName: 에셋 이름 (선택적, None이면 FBX 파일명 사용)
            inDescription: 호출부 호환을 위해 유지되는 인자. 서밋이 임포터에서
                제거되어 더 이상 사용하지 않는다 (CL 설명은 툴 프로세스가 구성).

        Returns:
            dict: 임포트 결과 딕셔너리. `OpenedFiles`에 연 파일의 로컬 절대경로
                (임포트된 스켈레톤 + dirty deps)가 들어간다.

        Raises:
            ValueError: 임포트 실패 시
        """
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

        # 임포트 결과 + dirty deps를 소스 컨트롤에 연다 (체크아웃까지만 - 서밋 없음).
        # get_dirty_deps는 Content 경로를 받으므로 시스템 경로가 아닌 Content 경로를 넘긴다.
        refObjectPaths = self.get_dirty_deps(skeletonFullPath)
        allImportRelatedPaths = list(dict.fromkeys([skeletonFullPath] + refObjectPaths))
        allImportAbsPaths = self.open_for_source_control(allImportRelatedPaths)

        unreal.log(f"[LegacySkeletonImporter] 스켈레톤 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        return self._create_result_dict(
            inFbxFile, destinationPath, skeletonName, True, allImportAbsPaths
        )
