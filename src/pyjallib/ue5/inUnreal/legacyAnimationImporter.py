#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 애니메이션 임포터 모듈

이 모듈은 FBX 파일에서 애니메이션 에셋을 UE5로 임포트하는 기능을 제공합니다.
PyJalLib의 naming 모듈을 사용하여 에셋 이름을 자동 생성합니다.
"""

import os
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

    def _resolve_skeleton_object(self, inSkeletonAsset, inSkeletonPath: str):
        """로드된 스켈레톤 에셋에서 실제 unreal.Skeleton 오브젝트를 해석합니다.

        스켈레톤 경로가 SkeletalMesh 에셋을 가리키는 경우(신 스킴 폴더에는
        SK_ SkeletalMesh만 있고 Skeleton 에셋이 없음), 그 메시의 skeleton
        프로퍼티에서 실제 Skeleton을 추출한다. Skeleton 에셋이 직접 오면
        그대로 반환한다 (기존 동작 호환).

        Args:
            inSkeletonAsset: 로드된 에셋 (unreal.Skeleton 또는 unreal.SkeletalMesh)
            inSkeletonPath: 로그/에러용 원본 Content 경로

        Returns:
            unreal.Skeleton: 해석된 스켈레톤 오브젝트

        Raises:
            ValueError: Skeleton으로 해석할 수 없는 에셋 타입이거나
                SkeletalMesh에 skeleton이 설정되어 있지 않은 경우
        """
        if isinstance(inSkeletonAsset, unreal.Skeleton):
            return inSkeletonAsset

        if isinstance(inSkeletonAsset, unreal.SkeletalMesh):
            resolvedSkeleton = inSkeletonAsset.get_editor_property('skeleton')
            if resolvedSkeleton is None:
                error_msg = f"SkeletalMesh에 skeleton이 설정되어 있지 않음: {inSkeletonPath}"
                unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
                raise ValueError(error_msg)
            unreal.log(
                f"[LegacyAnimationImporter] SkeletalMesh에서 Skeleton 해석: "
                f"{inSkeletonPath} -> {resolvedSkeleton.get_path_name()}"
            )
            return resolvedSkeleton

        error_msg = (
            f"Skeleton으로 해석할 수 없는 에셋 타입: {inSkeletonPath} "
            f"(type={type(inSkeletonAsset).__name__})"
        )
        unreal.log_error(f"[LegacyAnimationImporter] {error_msg}")
        raise ValueError(error_msg)

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

        # SkeletalMesh 경로가 와도 실제 Skeleton 오브젝트로 해석 (신 스킴 대응)
        animSkeleton = self._resolve_skeleton_object(
            skeletonAssetData.get_asset(), skeletonPath
        )
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

        # SkeletalMesh 경로가 와도 실제 Skeleton 오브젝트로 해석 (신 스킴 대응)
        return skeletonPath, self._resolve_skeleton_object(
            skeletonAssetData.get_asset(), skeletonPath
        )

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

        unreal.log("[LegacyAnimationImporter] ========== Consolidate+Rename 시작 ==========")
        unreal.log(f"[LegacyAnimationImporter] 대상 에셋: {assetFullPath}")
        unreal.log(f"[LegacyAnimationImporter] 임시 경로: {tempPath}")
        unreal.log(f"[LegacyAnimationImporter] FBX 파일: {inFbxFile}")

        # 2. 임시 폴더 생성
        tempFolderExists = unreal.EditorAssetLibrary.does_directory_exist(tempFolder)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] 임시 폴더 존재 여부: {tempFolderExists}")
        if not tempFolderExists:
            unreal.log(f"[LegacyAnimationImporter] 임시 폴더 생성: {tempFolder}")
            unreal.EditorAssetLibrary.make_directory(tempFolder)

        # 3. 기존 임시 에셋 정리
        tempAssetExists = unreal.EditorAssetLibrary.does_asset_exist(tempPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] 기존 임시 에셋 존재 여부: {tempAssetExists}")
        if tempAssetExists:
            unreal.log(f"[LegacyAnimationImporter] 기존 임시 에셋 삭제 시도: {tempPath}")
            deleteResult = unreal.EditorAssetLibrary.delete_asset(tempPath)
            unreal.log(f"[LegacyAnimationImporter] [반환값] 기존 임시 에셋 삭제 결과: {deleteResult}")

        # 4. 새 스켈레톤으로 임시 폴더에 에셋 임포트 (파일명 그대로)
        task = self.create_import_task(inFbxFile, tempFolder, inFbxSkeletonPath, inSkeletonContentPath)
        task.replace_existing = True
        unreal.log(f"[LegacyAnimationImporter] 임시 에셋 임포트 시작: destination={tempFolder}, name={assetName}")
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        result = task.get_objects()
        importedPaths = task.imported_object_paths
        unreal.log(f"[LegacyAnimationImporter] [반환값] 임포트 결과: objects={len(result)}, paths={importedPaths}")

        if len(result) == 0:
            # 임포트 실패 상세 정보 로깅
            unreal.log_error(f"[LegacyAnimationImporter] 임시 에셋 임포트 실패 - FBX: {inFbxFile}")
            unreal.log_error(f"[LegacyAnimationImporter] 임시 에셋 임포트 실패 - 예상 경로: {tempPath}")
            unreal.log_error(f"[LegacyAnimationImporter] 임시 에셋 임포트 실패 - imported_object_paths: {importedPaths}")
            raise ValueError(f"임시 에셋 임포트 실패: {inFbxFile}")

        # 임포트 후 에셋 존재 여부 확인
        tempAssetExistsAfterImport = unreal.EditorAssetLibrary.does_asset_exist(tempPath)
        oldAssetExistsBeforeConsolidate = unreal.EditorAssetLibrary.does_asset_exist(assetFullPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] 임포트 후 임시 에셋 존재: {tempAssetExistsAfterImport}")
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Consolidate 전 기존 에셋 존재: {oldAssetExistsBeforeConsolidate}")

        # 5. 에셋 로드
        newAsset = unreal.EditorAssetLibrary.load_asset(tempPath)
        oldAsset = unreal.EditorAssetLibrary.load_asset(assetFullPath)

        unreal.log(f"[LegacyAnimationImporter] [상태체크] newAsset 로드됨: {newAsset is not None}")
        unreal.log(f"[LegacyAnimationImporter] [상태체크] oldAsset 로드됨: {oldAsset is not None}")

        if not newAsset or not oldAsset:
            raise ValueError(f"에셋 로드 실패: newAsset={newAsset}, oldAsset={oldAsset}")

        unreal.log(f"[LegacyAnimationImporter] 에셋 로드 완료: new={tempPath}, old={assetFullPath}")

        # 6. Consolidate (참조 리다이렉트)
        unreal.log(f"[LegacyAnimationImporter] Consolidate 시도: newAsset={newAsset.get_path_name()}, oldAsset={oldAsset.get_path_name()}")
        consolidateSuccess = unreal.EditorAssetLibrary.consolidate_assets(newAsset, [oldAsset])
        unreal.log(f"[LegacyAnimationImporter] [반환값] consolidate_assets() 결과: {consolidateSuccess}")

        if not consolidateSuccess:
            unreal.log_error("[LegacyAnimationImporter] Consolidate 실패!")
            # 임시 에셋 정리
            unreal.EditorAssetLibrary.delete_asset(tempPath)
            raise ValueError(f"Consolidate 실패: {assetFullPath}")

        # Consolidate 후 상태 체크
        tempAssetExistsAfterConsolidate = unreal.EditorAssetLibrary.does_asset_exist(tempPath)
        oldPathExistsAfterConsolidate = unreal.EditorAssetLibrary.does_asset_exist(assetFullPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Consolidate 후 임시 에셋 존재: {tempAssetExistsAfterConsolidate}")
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Consolidate 후 기존 경로 존재 (Redirector?): {oldPathExistsAfterConsolidate}")

        # Redirector 여부 확인
        if oldPathExistsAfterConsolidate:
            oldPathAssetData = unreal.EditorAssetLibrary.find_asset_data(assetFullPath)
            if oldPathAssetData.is_valid():
                assetClass = oldPathAssetData.asset_class_path.asset_name
                unreal.log(f"[LegacyAnimationImporter] [상태체크] 기존 경로의 에셋 클래스: {assetClass}")

        unreal.log(f"[LegacyAnimationImporter] Consolidate 완료: 참조가 {tempPath}로 리다이렉트됨")

        # 7. Redirector 삭제 (Consolidate로 생성된 Redirector 정리)
        # delete_asset()은 Headless 모드에서 디스크 파일을 삭제하지 않으므로
        # delete_asset() 후 디스크 파일을 직접 삭제
        redirectorExists = unreal.EditorAssetLibrary.does_asset_exist(assetFullPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Redirector 삭제 전 기존 경로 존재: {redirectorExists}")

        if redirectorExists:
            unreal.log(f"[LegacyAnimationImporter] Redirector 삭제 시도: {assetFullPath}")
            deleteRedirectorResult = unreal.EditorAssetLibrary.delete_asset(assetFullPath)
            unreal.log(f"[LegacyAnimationImporter] [반환값] Redirector delete_asset() 결과: {deleteRedirectorResult}")

            # 디스크 파일 직접 삭제 (Headless 모드에서 delete_asset()이 디스크 파일을 삭제하지 않는 경우 대비)
            contentDir = unreal.Paths.project_content_dir()
            # /Game/... -> Content/... 경로로 변환
            relativePath = assetFullPath.replace("/Game/", "")
            diskPath = os.path.join(contentDir, relativePath + ".uasset")
            diskPath = os.path.normpath(diskPath)

            unreal.log(f"[LegacyAnimationImporter] [상태체크] 디스크 경로: {diskPath}")
            if os.path.exists(diskPath):
                unreal.log(f"[LegacyAnimationImporter] 디스크 파일 직접 삭제 시도: {diskPath}")
                try:
                    os.remove(diskPath)
                    unreal.log("[LegacyAnimationImporter] [반환값] 디스크 파일 삭제 성공")
                except OSError as e:
                    unreal.log_error(f"[LegacyAnimationImporter] 디스크 파일 삭제 실패: {e}")

            # AssetRegistry 갱신 - 디스크 삭제 후 레지스트리 동기화
            unreal.log(f"[LegacyAnimationImporter] AssetRegistry 갱신 시도: {destinationPath}")
            assetRegistry = unreal.AssetRegistryHelpers.get_asset_registry()
            assetRegistry.scan_paths_synchronous([destinationPath], force_rescan=True)
            unreal.log("[LegacyAnimationImporter] [반환값] AssetRegistry 갱신 완료")

            # Garbage Collection 실행
            unreal.SystemLibrary.collect_garbage()
            unreal.log("[LegacyAnimationImporter] Garbage Collection 완료")

        # 삭제 후 상태 체크
        oldPathExistsAfterDelete = unreal.EditorAssetLibrary.does_asset_exist(assetFullPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Redirector 삭제 후 기존 경로 존재: {oldPathExistsAfterDelete}")

        # 8. Rename으로 이름 복원
        unreal.log(f"[LegacyAnimationImporter] Rename 시도: {tempPath} -> {assetFullPath}")
        renameSuccess = unreal.EditorAssetLibrary.rename_asset(tempPath, assetFullPath)
        unreal.log(f"[LegacyAnimationImporter] [반환값] rename_asset() 결과: {renameSuccess}")

        if not renameSuccess:
            # Rename 실패 시 상태 체크
            tempStillExists = unreal.EditorAssetLibrary.does_asset_exist(tempPath)
            targetExists = unreal.EditorAssetLibrary.does_asset_exist(assetFullPath)
            unreal.log_error(f"[LegacyAnimationImporter] Rename 실패! 임시 에셋 존재: {tempStillExists}, 대상 경로 존재: {targetExists}")
            raise ValueError(f"Rename 실패: {tempPath} -> {assetFullPath}")

        # 9. 임시 경로의 Redirector 삭제 (Rename으로 생성된 Redirector 정리)
        tempRedirectorExists = unreal.EditorAssetLibrary.does_asset_exist(tempPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Rename 후 임시 경로 Redirector 존재: {tempRedirectorExists}")

        if tempRedirectorExists:
            unreal.log(f"[LegacyAnimationImporter] 임시 경로 Redirector 삭제 시도: {tempPath}")
            deleteTempRedirectorResult = unreal.EditorAssetLibrary.delete_asset(tempPath)
            unreal.log(f"[LegacyAnimationImporter] [반환값] 임시 Redirector delete_asset() 결과: {deleteTempRedirectorResult}")

            # 디스크 파일 직접 삭제
            tempRelativePath = tempPath.replace("/Game/", "")
            tempDiskPath = os.path.join(unreal.Paths.project_content_dir(), tempRelativePath + ".uasset")
            tempDiskPath = os.path.normpath(tempDiskPath)

            if os.path.exists(tempDiskPath):
                unreal.log(f"[LegacyAnimationImporter] 임시 디스크 파일 직접 삭제 시도: {tempDiskPath}")
                try:
                    os.remove(tempDiskPath)
                    unreal.log("[LegacyAnimationImporter] [반환값] 임시 디스크 파일 삭제 성공")
                except OSError as e:
                    unreal.log_error(f"[LegacyAnimationImporter] 임시 디스크 파일 삭제 실패: {e}")

        # Rename 후 상태 체크
        finalAssetExists = unreal.EditorAssetLibrary.does_asset_exist(assetFullPath)
        tempAssetExistsAfterRename = unreal.EditorAssetLibrary.does_asset_exist(tempPath)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Rename 후 최종 에셋 존재: {finalAssetExists}")
        unreal.log(f"[LegacyAnimationImporter] [상태체크] Rename 후 임시 에셋 존재: {tempAssetExistsAfterRename}")
        unreal.log(f"[LegacyAnimationImporter] Rename 완료: {tempPath} -> {assetFullPath}")

        # 10. 임시 폴더 정리 (비어있으면 삭제)
        tempFolderExistsForCleanup = unreal.EditorAssetLibrary.does_directory_exist(tempFolder)
        unreal.log(f"[LegacyAnimationImporter] [상태체크] 정리 단계 - 임시 폴더 존재: {tempFolderExistsForCleanup}")
        if tempFolderExistsForCleanup:
            assetsInTemp = unreal.EditorAssetLibrary.list_assets(tempFolder)
            unreal.log(f"[LegacyAnimationImporter] [상태체크] 임시 폴더 내 에셋 수: {len(assetsInTemp)}")
            if len(assetsInTemp) > 0:
                unreal.log(f"[LegacyAnimationImporter] [상태체크] 임시 폴더 내 에셋 목록: {assetsInTemp}")
            if len(assetsInTemp) == 0:
                deleteFolderResult = unreal.EditorAssetLibrary.delete_directory(tempFolder)
                unreal.log(f"[LegacyAnimationImporter] [반환값] 임시 폴더 삭제 결과: {deleteFolderResult}")

        # 저장 실패 silent success 방지: 최종 에셋의 디스크 반영 명시 검증 (실패 시 예외 전파)
        self.verify_asset_saved(assetFullPath)

        unreal.log("[LegacyAnimationImporter] ========== Consolidate+Rename 완료 ==========")
        unreal.log(f"[LegacyAnimationImporter] 스켈레톤 변경 성공: {assetFullPath}")

        return True

    def import_animation(self, inFbxFile: str, inFbxSkeletonPath: str = None, inSkeletonContentPath: str = None, inAssetName: str = None, inDescription: str = None):
        """애니메이션 FBX를 임포트하고 연 파일 목록을 결과에 담아 반환합니다.

        이 메서드는 **임포트와 체크아웃만** 수행한다. 서밋(`check_in_files`)은
        하지 않는다 - 에디터 안에는 체인지리스트 API가 없어 자동 서밋이
        바깥 툴의 CL 관리를 무력화시켰기 때문이다. 연 파일은 default
        체인지리스트에 남고, 이름 붙은 CL로의 이동과 서밋은 호출자(툴 프로세스)가
        `pyjallib.perforce.Perforce`로 처리한다.

        Args:
            inFbxFile: 애니메이션 FBX 파일의 절대 경로
            inFbxSkeletonPath: 스켈레톤 FBX 경로 (Content 경로로 변환됨)
            inSkeletonContentPath: 스켈레톤 Content 경로 (직접 사용, 우선)
            inAssetName: 에셋 이름 (선택적, None이면 FBX 파일명 사용)
            inDescription: 호출부 호환을 위해 유지되는 인자. 서밋이 임포터에서
                제거되어 더 이상 사용하지 않는다 (CL 설명은 툴 프로세스가 구성).

        Returns:
            dict: 임포트 결과 딕셔너리. `OpenedFiles`에 연 파일의 로컬 절대경로
                (임포트 결과 + dirty deps)가 들어간다.

        Raises:
            ValueError: 스켈레톤 해석 실패, 임포트 실패, 디스크 저장 실패 시
        """
        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 시작: {inFbxFile}")

        destinationPath, assetName = self._prepare_import_paths(inFbxFile, inAssetName)
        assetFullPath = f"{destinationPath}/{assetName}"

        # 스켈레톤 로드 및 스켈레톤 변경 필요 여부 확인
        _, targetSkeleton = self._get_target_skeleton(inFbxSkeletonPath, inSkeletonContentPath)
        needsSwap = self._needs_skeleton_swap(assetFullPath, targetSkeleton)

        if needsSwap:
            # Consolidate + Rename 방식으로 스켈레톤 변경
            unreal.log("[LegacyAnimationImporter] 스켈레톤 변경 필요 - Consolidate+Rename 플로우 진입")
            self._swap_skeleton_via_consolidate(inFbxFile, assetFullPath, inFbxSkeletonPath, inSkeletonContentPath)

            # 변경된 에셋에 대해 소스 컨트롤 처리 (체크아웃까지만 - 서밋 없음)
            importedObjectPaths = [assetFullPath]
            refObjectPaths = self.get_dirty_deps(assetFullPath)
            allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))

            allImportAbsPaths = self.open_for_source_control(allImportRelatedPaths)

            unreal.log(f"[LegacyAnimationImporter] 스켈레톤 변경 완료: {assetFullPath}")

            return self._create_result_dict(
                inFbxFile, destinationPath, assetName, True, allImportAbsPaths
            )

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

        # 임포트 태스크의 저장이 파일 잠금 등으로 실패해도 예외가 없어(silent)
        # 성공으로 오판되므로, 디스크 반영을 명시 검증한다 (실패 시 예외 전파)
        self.verify_asset_saved(assetFullPath)

        importedObjectPaths = task.imported_object_paths
        refObjectPaths = self.get_dirty_deps(assetFullPath)

        # 임포트 결과 + dirty deps를 소스 컨트롤에 연다 (체크아웃까지만 - 서밋 없음)
        allImportRelatedPaths = list(dict.fromkeys(importedObjectPaths + refObjectPaths))
        allImportAbsPaths = self.open_for_source_control(allImportRelatedPaths)

        unreal.log(f"[LegacyAnimationImporter] 애니메이션 임포트 성공: {inFbxFile} -> {len(result)}개 객체 생성")

        return self._create_result_dict(
            inFbxFile, destinationPath, assetName, True, allImportAbsPaths
        )
