#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 애니메이션 임포터 모듈

이 모듈은 FBX 파일에서 애니메이션 에셋을 UE5로 임포트하는 기능을 제공합니다.
PyJalLib의 naming 모듈을 사용하여 에셋 이름을 자동 생성합니다.
"""

import unreal
from pathlib import Path

# UE5 모듈 import
from legacyBaseImporter import LegacyBaseImporter


class LegacyAnimationImporter(LegacyBaseImporter):
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str):
        super().__init__(inContentRootPrefix, inFbxRootPrefix, "Animation")
        unreal.log("[LegacyAnimationImporter] 초기화 완료")

    @property
    def asset_type(self) -> str:
        return "Animation"

    def _create_batch_import_description(self, inFbxFiles: list[str], inAssetFullPaths: list[str]) -> str:
        """
        배치 임포트용 간결한 디스크립션 생성

        Args:
            inFbxFiles (list[str]): 임포트된 FBX 파일 목록
            inAssetFullPaths (list[str]): 임포트된 에셋 전체 경로 목록

        Returns:
            str: 간결한 디스크립션
        """
        totalCount = len(inFbxFiles)

        if totalCount <= 3:
            # 3개 이하면 모든 경로 표시
            fbxList = ", ".join(inFbxFiles)
            assetList = ", ".join(inAssetFullPaths)
            return f"Animation Batch Import ({totalCount} files): {fbxList} -> {assetList}"
        else:
            # 3개 초과면 처음 3개만 표시하고 나머지는 개수로 표시
            fbxList = ", ".join(inFbxFiles[:3]) + f" ... (and {totalCount - 3} more)"
            assetList = ", ".join(inAssetFullPaths[:3]) + f" ... (and {totalCount - 3} more)"
            return f"Animation Batch Import ({totalCount} files): {fbxList} -> {assetList}"

    def create_import_task(self, inFbxFile: str, inDestinationPath: str, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None):
        """애니메이션 임포트를 위한 태스크 생성 - 스켈레톤 필수 지정"""
        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 태스크 생성 시작: {inFbxFile}")

        # 스켈레톤 경로 결정: inSkeletonContentPath 우선, 없으면 FBX 경로 변환
        if inSkeletonContentPath is not None:
            skeletonPath = inSkeletonContentPath
            unreal.log(f"[LegacyAnimationImporter] Content 경로를 직접 사용: {skeletonPath}")
        elif inFbxSkeletonPath is not None:
            skeletonPath = self.convert_fbx_path_to_skeleton_path(inFbxSkeletonPath)
            unreal.log(f"[LegacyAnimationImporter] FBX 경로를 Content 경로로 변환: {inFbxSkeletonPath} -> {skeletonPath}")
        else:
            error_msg = "애니메이션 임포트에는 스켈레톤이 필수입니다 (inSkeletonContentPath 또는 inFbxSkeletonPath 중 하나 제공 필요)"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        skeletonAssetData = unreal.EditorAssetLibrary.find_asset_data(skeletonPath)
        if not skeletonAssetData.is_valid():
            error_msg = f"스켈레톤 에셋을 찾을 수 없음: {skeletonPath}"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        animSkeleton = skeletonAssetData.get_asset()
        unreal.log(f"[LegacyAnimationImporter] 스켈레톤 로드됨: {animSkeleton.get_name()}")

        # FbxImportUI 직접 생성 및 설정
        importOptions = unreal.FbxImportUI()
        importOptions.reset_to_default()

        # 애니메이션 임포트 옵션 설정 (skeleton 설정 전에 타입 먼저 설정)
        importOptions.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_ANIMATION)
        importOptions.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        importOptions.set_editor_property('import_animations', True)
        importOptions.set_editor_property('import_mesh', False)
        importOptions.set_editor_property('import_textures', False)
        importOptions.set_editor_property('import_materials', False)
        importOptions.set_editor_property('automated_import_should_detect_type', False)

        # 스켈레톤 설정 (import_type 설정 후에 해야 함)
        importOptions.set_editor_property('skeleton', animSkeleton)
        unreal.log(f"[LegacyAnimationImporter] 스켈레톤 설정됨: {animSkeleton.get_name()}")

        # 설정 후 스켈레톤 확인
        setSkeleton = importOptions.get_editor_property('skeleton')
        if setSkeleton:
            unreal.log(f"[LegacyAnimationImporter] 스켈레톤 설정 확인: {setSkeleton.get_name()}")
        else:
            unreal.log_warning("[LegacyAnimationImporter] 경고: 스켈레톤이 설정되지 않음!")

        # 애니메이션 시퀀스 임포트 데이터 설정
        importOptions.anim_sequence_import_data.set_editor_property('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        importOptions.anim_sequence_import_data.set_editor_property('do_not_import_curve_with_zero', True)
        importOptions.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
        importOptions.anim_sequence_import_data.set_editor_property('import_custom_attribute', True)
        importOptions.anim_sequence_import_data.set_editor_property('import_meshes_in_bone_hierarchy', True)

        unreal.log("[LegacyAnimationImporter] FbxImportUI 옵션 적용 완료")

        # 에셋 이름 결정: FBX 파일 이름에서 확장자 제거
        assetName = Path(inFbxFile).stem

        # FbxFactory 생성 (타입 힌트용)
        factory = unreal.FbxFactory()

        task = unreal.AssetImportTask()
        task.automated = True
        task.destination_path = inDestinationPath
        task.filename = inFbxFile
        task.destination_name = assetName
        task.replace_existing = True
        task.save = True
        task.factory = factory
        task.options = importOptions

        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 태스크 생성 완료: Destination={inDestinationPath}, AssetName={assetName}")
        return task

    def _get_target_skeleton(self, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None):
        """
        스켈레톤 경로를 결정하고 스켈레톤 에셋을 로드합니다.

        Args:
            inFbxSkeletonPath: FBX 스켈레톤 경로 (Content 경로로 변환됨)
            inSkeletonContentPath: Content 스켈레톤 경로 (직접 사용)

        Returns:
            tuple: (skeletonPath, skeletonAsset)
        """
        if inSkeletonContentPath is not None:
            skeletonPath = inSkeletonContentPath
        elif inFbxSkeletonPath is not None:
            skeletonPath = self.convert_fbx_path_to_skeleton_path(inFbxSkeletonPath)
        else:
            raise ValueError("스켈레톤 경로가 필요합니다")

        skeletonAssetData = unreal.EditorAssetLibrary.find_asset_data(skeletonPath)
        if not skeletonAssetData.is_valid():
            raise ValueError(f"스켈레톤 에셋을 찾을 수 없음: {skeletonPath}")

        return skeletonPath, skeletonAssetData.get_asset()

    def _needs_skeleton_swap(self, assetFullPath: str, targetSkeleton) -> bool:
        """
        기존 에셋의 스켈레톤이 변경되어야 하는지 확인합니다.

        Args:
            assetFullPath: 에셋 전체 경로
            targetSkeleton: 새로 임포트할 스켈레톤

        Returns:
            bool: 스켈레톤 변경이 필요하면 True
        """
        existingAsset = unreal.EditorAssetLibrary.load_asset(assetFullPath)
        if existingAsset is None or not isinstance(existingAsset, unreal.AnimSequence):
            return False

        currentSkeleton = existingAsset.get_editor_property('skeleton')
        if currentSkeleton is None:
            return True

        return currentSkeleton != targetSkeleton

    def _swap_skeleton_via_consolidate(self, inFbxFile: str, assetFullPath: str, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None):
        """
        Consolidate + Rename 방식으로 스켈레톤을 변경합니다.

        기존 에셋의 스켈레톤을 변경하기 위해:
        1. 임시 폴더에 새 에셋 임포트 (새 스켈레톤)
        2. consolidate_assets()로 참조 리다이렉트
        3. Redirector 삭제
        4. rename_asset()으로 원래 경로로 이동

        Args:
            inFbxFile: FBX 파일 경로
            assetFullPath: 에셋 전체 경로
            inFbxSkeletonPath: FBX 스켈레톤 경로
            inSkeletonContentPath: Content 스켈레톤 경로

        Returns:
            bool: 성공 여부
        """
        # 1. 경로 분해
        destinationPath = str(Path(assetFullPath).parent).replace("\\", "/")
        assetName = Path(assetFullPath).stem

        # 임시 폴더 경로: 원본 에셋과 같은 폴더 내에 _Temp 서브폴더 사용
        # 이렇게 하면 Asset Reference Restriction을 우회할 수 있음
        tempFolder = f"{destinationPath}/_SkeletonSwapTemp"
        tempPath = f"{tempFolder}/{assetName}"

        unreal.log(f"[LegacyAnimationImporter] Consolidate+Rename 시작: {assetFullPath}")
        unreal.log(f"[LegacyAnimationImporter] 임시 경로: {tempPath}")

        # 2. 임시 폴더 생성
        if not unreal.EditorAssetLibrary.does_directory_exist(tempFolder):
            unreal.log(f"[LegacyAnimationImporter] 임시 폴더 생성: {tempFolder}")
            unreal.EditorAssetLibrary.make_directory(tempFolder)

        # 3. 기존 임시 에셋 정리
        if unreal.EditorAssetLibrary.does_asset_exist(tempPath):
            unreal.log(f"[LegacyAnimationImporter] 기존 임시 에셋 삭제: {tempPath}")
            unreal.EditorAssetLibrary.delete_asset(tempPath)

        # 4. 새 스켈레톤으로 임시 폴더에 에셋 임포트 (파일명 그대로)
        task = self.create_import_task(inFbxFile, tempFolder, inFbxSkeletonPath, inSkeletonContentPath)
        task.replace_existing = True
        unreal.log(f"[LegacyAnimationImporter] 임시 에셋 임포트 시작: destination={tempFolder}, name={assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        result = task.get_objects()
        importedPaths = task.imported_object_paths
        unreal.log(f"[LegacyAnimationImporter] 임포트 결과: objects={len(result)}, paths={importedPaths}")

        if len(result) == 0:
            # 임포트 실패 상세 정보 로깅
            unreal.log_error(f"[LegacyAnimationImporter] 임시 에셋 임포트 실패 - FBX: {inFbxFile}")
            unreal.log_error(f"[LegacyAnimationImporter] 임시 에셋 임포트 실패 - 예상 경로: {tempPath}")
            unreal.log_error(f"[LegacyAnimationImporter] 임시 에셋 임포트 실패 - imported_object_paths: {importedPaths}")
            raise ValueError(f"임시 에셋 임포트 실패: {inFbxFile}")

        # 4. 에셋 로드
        newAsset = unreal.EditorAssetLibrary.load_asset(tempPath)
        oldAsset = unreal.EditorAssetLibrary.load_asset(assetFullPath)

        if not newAsset or not oldAsset:
            raise ValueError(f"에셋 로드 실패: newAsset={newAsset}, oldAsset={oldAsset}")

        unreal.log(f"[LegacyAnimationImporter] 에셋 로드 완료: new={tempPath}, old={assetFullPath}")

        # 5. Consolidate (참조 리다이렉트)
        success = unreal.EditorAssetLibrary.consolidate_assets(newAsset, [oldAsset])
        if not success:
            # 임시 에셋 정리
            unreal.EditorAssetLibrary.delete_asset(tempPath)
            raise ValueError(f"Consolidate 실패: {assetFullPath}")

        unreal.log(f"[LegacyAnimationImporter] Consolidate 완료: 참조가 {tempPath}로 리다이렉트됨")

        # 6. 기존 경로의 Redirector 삭제
        if unreal.EditorAssetLibrary.does_asset_exist(assetFullPath):
            unreal.log(f"[LegacyAnimationImporter] Redirector 삭제: {assetFullPath}")
            unreal.EditorAssetLibrary.delete_asset(assetFullPath)

        # 7. Rename으로 이름 복원
        success = unreal.EditorAssetLibrary.rename_asset(tempPath, assetFullPath)
        if not success:
            raise ValueError(f"Rename 실패: {tempPath} -> {assetFullPath}")

        unreal.log(f"[LegacyAnimationImporter] Rename 완료: {tempPath} -> {assetFullPath}")

        # 8. 임시 폴더 정리 (비어있으면 삭제)
        if unreal.EditorAssetLibrary.does_directory_exist(tempFolder):
            assetsInTemp = unreal.EditorAssetLibrary.list_assets(tempFolder)
            if len(assetsInTemp) == 0:
                unreal.EditorAssetLibrary.delete_directory(tempFolder)
                unreal.log(f"[LegacyAnimationImporter] 임시 폴더 삭제: {tempFolder}")

        unreal.log(f"[LegacyAnimationImporter] 스켈레톤 변경 성공 (Consolidate+Rename): {assetFullPath}")

        return True

    def import_animation(self, inFbxFile: str, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None, inAssetName: str = None, inDescription: str = None):
        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 시작: {inFbxFile}")

        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"

        # 스켈레톤 로드 및 스켈레톤 변경 필요 여부 확인
        _, targetSkeleton = self._get_target_skeleton(inFbxSkeletonPath, inSkeletonContentPath)
        needsSwap = self._needs_skeleton_swap(assetFullPath, targetSkeleton)

        if needsSwap:
            # Consolidate + Rename 방식으로 스켈레톤 변경
            unreal.log(f"[LegacyAnimationImporter] 스켈레톤 변경 필요 - Consolidate+Rename 플로우 진입")
            self._swap_skeleton_via_consolidate(inFbxFile, assetFullPath, inFbxSkeletonPath, inSkeletonContentPath)

            # 변경된 에셋에 대해 소스 컨트롤 처리
            importedObjectPaths = [assetFullPath]
            refObjectPaths = self.get_dirty_deps(assetFullPath)
            allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))

            for assetPath in allImportRelatedPaths:
                unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)

            checkInDescription = f"Animation Skeleton Changed via Consolidate+Rename: {inFbxFile} to {assetFullPath}"
            if inDescription is not None:
                checkInDescription = inDescription

            allImportAbsPaths = []
            for assetPath in allImportRelatedPaths:
                assetObj = unreal.EditorAssetLibrary.load_asset(assetPath)
                if assetObj is not None:
                    absPath = unreal.SystemLibrary.get_system_path(assetObj)
                    allImportAbsPaths.append(absPath)

            if self.is_development_mode():
                unreal.log(f"[LegacyAnimationImporter] 개발 모드 - 스켈레톤 변경 완료: {assetFullPath}")
            else:
                unreal.SourceControl.check_in_files(allImportAbsPaths, checkInDescription, silent=True)
                unreal.log(f"[LegacyAnimationImporter] 스켈레톤 변경 완료: {assetFullPath}")

            return self._create_result_dict(inFbxFile, destinationPath, assetName, True)

        # 기존 방식: 일반 임포트 (스켈레톤 동일 또는 새 에셋)
        # 기존 에셋이 있는 경우 소스 컨트롤에서 체크아웃
        if unreal.EditorAssetLibrary.does_asset_exist(assetFullPath):
            unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)

        task = self.create_import_task(inFbxFile, destinationPath, inFbxSkeletonPath, inSkeletonContentPath)

        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 실행: {inFbxFile} -> {destinationPath}/{assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        result = task.get_objects()
        if len(result) == 0:
            error_msg = f"애니메이션 임포트 실패: {inFbxFile}"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        importedObjectPaths = task.imported_object_paths
        refObjectPaths = self.get_dirty_deps(assetFullPath)

        allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))
        for assetPath in allImportRelatedPaths:
            unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)

        checkInDescription = f"Animation Imported by {inFbxFile} to {assetFullPath}"
        if inDescription is not None:
            checkInDescription = inDescription

        allImportAbsPaths = []
        for assetPath in allImportRelatedPaths:
            assetObj = unreal.EditorAssetLibrary.load_asset(assetPath)
            if assetObj is not None:
                absPath = unreal.SystemLibrary.get_system_path(assetObj)
                allImportAbsPaths.append(absPath)

        if self.is_development_mode():
            unreal.log(f"[LegacyAnimationImporter] 개발 모드 - 애니메이션 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")
        else:
            unreal.SourceControl.check_in_files(allImportAbsPaths, checkInDescription, silent=True)
            unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")

        return self._create_result_dict(inFbxFile, destinationPath, assetName, True)

    def import_animations(self, inFbxFiles: list[str], inFbxSkeletonPaths: list[str] = None, inSkeletonContentPaths: list[str] = None, inAssetNames: list[str] = None, inDescription: str = None):
        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 시작: {inFbxFiles}")

        # 스켈레톤 경로 검증: 하나는 반드시 제공되어야 함
        if inSkeletonContentPaths is None and inFbxSkeletonPaths is None:
            error_msg = "애니메이션 임포트에는 스켈레톤 경로가 필요합니다 (inSkeletonContentPaths 또는 inFbxSkeletonPaths 중 하나)"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        # inSkeletonContentPaths가 제공되었으면 길이 검증
        if inSkeletonContentPaths is not None and len(inFbxFiles) != len(inSkeletonContentPaths):
            error_msg = "애니메이션 임포트에는 파일과 스켈레톤이 같은 개수여야 합니다"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        # inFbxSkeletonPaths가 제공되었으면 길이 검증
        if inFbxSkeletonPaths is not None and len(inFbxFiles) != len(inFbxSkeletonPaths):
            error_msg = "애니메이션 임포트에는 파일과 스켈레톤이 같은 개수여야 합니다"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        if inAssetNames is not None and len(inFbxFiles) != len(inAssetNames):
            error_msg = "애니메이션 임포트에는 파일과 에셋 이름이 같은 개수여야 합니다"
            unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        destinationPaths = []
        assetNames = []
        assetFullPaths = []
        tasks = []
        for index, fbxFile in enumerate(inFbxFiles):
            cusAssetName = None
            if inAssetNames is not None:
                cusAssetName = inAssetNames[index]
            destinationPath, assetName = self._prepare_import_paths(fbxFile, cusAssetName)

            destinationPaths.append(destinationPath)
            assetNames.append(assetName)
            assetFullPath = f"{destinationPath}/{assetName}"
            assetFullPaths.append(assetFullPath)

            if unreal.Paths.file_exists(assetFullPath):
                unreal.SourceControl.check_out_or_add_file(assetFullPath, silent=True)

            # 스켈레톤 경로 결정
            fbxSkeletonPath = inFbxSkeletonPaths[index] if inFbxSkeletonPaths is not None else None
            skeletonContentPath = inSkeletonContentPaths[index] if inSkeletonContentPaths is not None else None

            task = self.create_import_task(fbxFile, destinationPath, fbxSkeletonPath, skeletonContentPath)
            tasks.append(task)

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

        batchImportedAssetPaths = []
        batchImporteAbsPaths = []
        for index, task in enumerate(tasks):
            result = task.get_objects()
            if len(result) == 0:
                error_msg = f"애니메이션 임포트 실패: {inFbxFiles[index]}"
                unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
                raise ValueError(error_msg)

            importedObjectPaths = task.imported_object_paths
            refObjectPaths = self.get_dirty_deps(assetFullPaths[index])


            allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))
            for assetPath in allImportRelatedPaths:
                unreal.SourceControl.check_out_or_add_file(assetPath, silent=True)
                batchImportedAssetPaths.append(assetPath)

        batchImportedAssetPaths = list(dict.fromkeys(batchImportedAssetPaths))
        for assetPath in batchImportedAssetPaths:
            assetObj = unreal.EditorAssetLibrary.load_asset(assetPath)
            if assetObj is not None:
                absPath = unreal.SystemLibrary.get_system_path(assetObj)
                batchImporteAbsPaths.append(absPath)

        # 배치 임포트용 간결한 디스크립션 생성
        if inDescription is not None:
            checkInDescription = inDescription
        else:
            checkInDescription = self._create_batch_import_description(inFbxFiles, assetFullPaths)

        if self.is_development_mode():
            unreal.log(f"[LegacyAnimationImporter] 개발 모드 - 배치 임포트 체크인 결과: {checkInDescription}")
        else:
            checkinResult = unreal.SourceControl.check_in_files(batchImporteAbsPaths, checkInDescription, silent=True)
            unreal.log(f"[LegacyAnimationImporter] 배치 임포트 체크인 결과: {checkinResult}")

        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 완료: {inFbxFiles}")
