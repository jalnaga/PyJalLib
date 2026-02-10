#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 스태틱 메쉬 임포터 모듈
UE5에서 스태틱 메쉬를 임포트하는 기능을 제공합니다.
"""

import unreal
from pathlib import Path

# UE5 모듈 import
from legacyBaseImporter import LegacyBaseImporter


class LegacyStaticMeshImporter(LegacyBaseImporter):
    """Legacy FBX Importer를 사용한 스태틱 메쉬 임포터

    LegacyBaseImporter를 상속하여 Static Mesh 전용 임포트 로직을 구현합니다.
    LegacyImporterSettings의 StaticMesh 프리셋(FbxImportUI)을 사용합니다.
    """

    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        """LegacyStaticMeshImporter 초기화

        Args:
            inContentRootPrefix: UE5 Content 경로의 루트 접두사
            inFbxRootPrefix: FBX 파일 경로의 루트 접두사
        """
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "StaticMesh")
        unreal.log("[LegacyStaticMeshImporter] 초기화 완료")

    @property
    def asset_type(self) -> str:
        """에셋 타입 반환"""
        return "StaticMesh"

    @staticmethod
    def _set_interchange_fbx_enabled(inEnabled: bool):
        """Interchange FBX 임포트 기능을 활성화/비활성화합니다.

        Args:
            inEnabled: True면 활성화, False면 비활성화
        """
        value = "1" if inEnabled else "0"
        try:
            unreal.SystemLibrary.execute_console_command(
                None, f"Interchange.FeatureFlags.Import.FBX {value}"
            )
            unreal.log(f"[LegacyStaticMeshImporter] CVar 설정 성공: "
                       f"Interchange.FeatureFlags.Import.FBX {value}")
        except Exception as e:
            unreal.log_warning(f"[LegacyStaticMeshImporter] CVar 설정 실패: {e}")

    def create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """스태틱 메쉬 임포트를 위한 태스크 생성

        LegacyImporterSettings의 StaticMesh 프리셋을 사용하여
        FbxImportUI 옵션을 설정합니다.

        Args:
            inFbxFile: FBX 파일의 절대 경로
            inDestinationPath: /Game/... 형식의 Content 목적지 경로

        Returns:
            unreal.AssetImportTask: 생성된 임포트 태스크
        """
        unreal.log(f"[LegacyStaticMeshImporter] 임포트 태스크 생성 시작: {inFbxFile}")

        importOptions = self.importerSettings.load_options()
        unreal.log("[LegacyStaticMeshImporter] StaticMesh 임포트 옵션 로드 완료")

        assetName = Path(inFbxFile).stem

        task = unreal.AssetImportTask()
        task.automated = True
        task.destination_path = inDestinationPath
        task.filename = inFbxFile
        task.destination_name = assetName
        task.replace_existing = True
        task.save = True
        task.options = importOptions

        unreal.log(f"[LegacyStaticMeshImporter] 임포트 태스크 생성 완료: "
                   f"Destination={inDestinationPath}, AssetName={assetName}")
        return task

    def import_static_mesh(self, inFbxFile: str, inAssetName: str = None, inDescription: str = None):
        """스태틱 메쉬를 FBX에서 임포트합니다.

        Interchange를 임시 비활성화하고 Legacy FBX + FbxImportUI로 임포트합니다.

        Args:
            inFbxFile: FBX 파일의 절대 경로
            inAssetName: 에셋 이름 (선택적, None이면 FBX 파일명 사용)
            inDescription: 소스 컨트롤 체크인 설명 (선택적)

        Returns:
            dict: 임포트 결과 딕셔너리 (SourceFile, Path, Name, Type, Success)

        Raises:
            ValueError: 임포트 실패 시
        """
        unreal.log(f"[LegacyStaticMeshImporter] 스태틱 메쉬 임포트 시작: {inFbxFile}")

        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"

        # 기존 에셋이 있는 경우 소스 컨트롤에서 체크아웃
        if unreal.Paths.file_exists(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)

        task = self.create_import_task(inFbxFile, destinationPath)

        # Interchange 비활성화 -> Legacy FBX 임포트 -> Interchange 재활성화
        self._set_interchange_fbx_enabled(False)
        try:
            unreal.log(f"[LegacyStaticMeshImporter] 임포트 실행: "
                       f"{inFbxFile} -> {destinationPath}/{assetName}")
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        finally:
            self._set_interchange_fbx_enabled(True)

        # 임포트된 스태틱 메쉬 에셋 검색
        importedStaticMesh = None

        # 1차: task.get_objects()에서 검색
        result = task.get_objects()
        if result:
            typeNames = [type(a).__name__ for a in result]
            unreal.log(f"[LegacyStaticMeshImporter] task.get_objects(): "
                       f"{len(result)}개 객체, 타입: {typeNames}")
            for asset in result:
                if isinstance(asset, unreal.StaticMesh):
                    importedStaticMesh = asset
                    unreal.log("[LegacyStaticMeshImporter] task.get_objects()에서 StaticMesh 발견")
                    break
        else:
            unreal.log("[LegacyStaticMeshImporter] task.get_objects() 빈 결과")

        # 2차: EditorAssetLibrary 폴백
        if importedStaticMesh is None:
            unreal.log("[LegacyStaticMeshImporter] EditorAssetLibrary 폴백 시도")
            assetData = unreal.EditorAssetLibrary.find_asset_data(assetFullPath)
            if assetData.is_valid():
                loadedAsset = assetData.get_asset()
                if isinstance(loadedAsset, unreal.StaticMesh):
                    importedStaticMesh = loadedAsset
                    unreal.log(f"[LegacyStaticMeshImporter] EditorAssetLibrary에서 StaticMesh 발견: "
                               f"{assetFullPath}")
                else:
                    unreal.log_warning(
                        f"[LegacyStaticMeshImporter] 에셋이 StaticMesh가 아님: "
                        f"{type(loadedAsset).__name__}"
                    )

        if importedStaticMesh is None:
            error_msg = f"스태틱 메쉬 임포트 실패: {inFbxFile} (경로: {assetFullPath})"
            unreal.log_error(f"[LegacyStaticMeshImporter] {error_msg}")
            raise ValueError(error_msg)

        importedObjectPaths = self.get_dirty_deps(assetFullPath)

        staticMeshSystemFullPath = unreal.SystemLibrary.get_system_path(importedStaticMesh)
        importedObjectPaths.append(staticMeshSystemFullPath)

        checkInDescription = f"StaticMesh Imported by {inFbxFile} to {assetFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription

        unreal.SourceControl.check_in_files(importedObjectPaths, checkInDescription, silent=True)

        unreal.log(f"[LegacyStaticMeshImporter] 스태틱 메쉬 임포트 성공: {inFbxFile}")
        return self._create_result_dict(inFbxFile, destinationPath, assetName, True)
