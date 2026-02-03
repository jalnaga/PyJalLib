#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 애니메이션 임포터 모듈

이 모듈은 Interchange Framework를 사용하여 FBX 파일에서 애니메이션 에셋을
UE5로 임포트하는 기능을 제공합니다.

의존성: 파이썬 표준 라이브러리 + unreal + pathUtils만 사용
"""

import gc
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

import unreal

try:
    from . import pathUtils
    from .interchangeImporterBase import InterchangeImporterBase
    from .interchangePipelineSettings import InterchangePipelineSettings
except ImportError:
    import pathUtils
    from interchangeImporterBase import InterchangeImporterBase
    from interchangePipelineSettings import InterchangePipelineSettings


class InterchangeAnimationImporter(InterchangeImporterBase):
    """
    Interchange Framework 기반 애니메이션 임포터.

    FBX 파일에서 애니메이션을 추출하여 UE5로 임포트합니다.
    기존 스켈레톤 참조가 필수입니다.
    외부 패키지 의존성 없이 파이썬 표준 라이브러리와 unreal 모듈만 사용합니다.
    """

    # 애니메이션 에셋 접두사 (기본값)
    DEFAULT_ANIMATION_PREFIX = "A_"

    def __init__(self):
        """
        InterchangeAnimationImporter 초기화.
        """
        super().__init__()
        self._pipelineSettings = InterchangePipelineSettings("Animation")
        unreal.log("[InterchangeAnimationImporter] 초기화 완료")

    @property
    def asset_type(self) -> str:
        """에셋 타입을 반환합니다."""
        return "Animation"

    # ========================================================================
    # 스켈레톤 검증
    # ========================================================================

    def _validate_skeleton(self, inSkeletonPath: str) -> unreal.Skeleton:
        """
        스켈레톤 경로를 검증하고 스켈레톤 에셋을 반환합니다.

        Args:
            inSkeletonPath: /Game/... 형식의 스켈레톤 Content 경로 (정규화된 경로)

        Returns:
            스켈레톤 에셋

        Raises:
            ValueError: 스켈레톤을 찾을 수 없는 경우
        """
        if inSkeletonPath is None:
            error_msg = "애니메이션 임포트에는 스켈레톤이 필수입니다"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        skeletonAssetData = unreal.EditorAssetLibrary.find_asset_data(inSkeletonPath)

        if not skeletonAssetData.is_valid():
            error_msg = f"스켈레톤 에셋을 찾을 수 없음: {inSkeletonPath}"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        skeleton = skeletonAssetData.get_asset()
        unreal.log(
            f"[InterchangeAnimationImporter] 스켈레톤 검증 완료: {skeleton.get_name()}"
        )
        return skeleton

    # ========================================================================
    # 배치 디스크립션 생성
    # ========================================================================

    def _create_batch_import_description(
        self, inFbxPaths: List[str], inAssetFullPaths: List[str]
    ) -> str:
        """
        배치 임포트용 간결한 디스크립션을 생성합니다.

        Args:
            inFbxPaths: 임포트된 FBX 파일 목록
            inAssetFullPaths: 임포트된 에셋 전체 경로 목록

        Returns:
            간결한 디스크립션 문자열
        """
        totalCount = len(inFbxPaths)

        if totalCount <= 3:
            # 3개 이하면 모든 경로 표시
            fbxList = ", ".join(inFbxPaths)
            assetList = ", ".join(inAssetFullPaths)
            return (
                f"Animation Batch Import ({totalCount} files): {fbxList} -> {assetList}"
            )
        else:
            # 3개 초과면 처음 3개만 표시하고 나머지는 개수로 표시
            fbxList = ", ".join(inFbxPaths[:3]) + f" ... (and {totalCount - 3} more)"
            assetList = (
                ", ".join(inAssetFullPaths[:3]) + f" ... (and {totalCount - 3} more)"
            )
            return (
                f"Animation Batch Import ({totalCount} files): {fbxList} -> {assetList}"
            )

    # ========================================================================
    # 단일 임포트 (동기)
    # ========================================================================

    def import_animation(
        self,
        inFbxPath: str,
        inDestinationPath: str,
        inSkeletonPath: str,
        inAssetName: str = None,
        inForceReplaceSkeleton: bool = False,
    ) -> Dict[str, Any]:
        """
        FBX 파일에서 애니메이션을 임포트합니다. (동기 방식)

        Args:
            inFbxPath: FBX 파일의 절대 경로
            inDestinationPath: /Game/... 형식의 Content 목적지 경로
            inSkeletonPath: /Game/... 형식의 스켈레톤 Content 경로
            inAssetName: 에셋 이름 (None이면 FBX 파일명 기반 자동 생성)
            inForceReplaceSkeleton: True이면 기존 에셋의 스켈레톤을 강제로 교체
                                    (임시 에셋으로 임포트 후 consolidate_assets 사용)

        Returns:
            임포트 결과 딕셔너리 (LocalPaths 포함)

        Example:
            >>> importer = InterchangeAnimationImporter()
            >>> result = importer.import_animation(
            ...     inFbxPath="D:/Export/FBX/Hero/A_Hero_Run.fbx",
            ...     inDestinationPath="/Game/Characters/Hero/Animations",
            ...     inSkeletonPath="/Game/Characters/Hero/SK_Hero",
            ...     inAssetName="A_Hero_Run",  # 선택적
            ...     inForceReplaceSkeleton=True  # 스켈레톤 강제 교체
            ... )
        """
        unreal.log(
            f"[InterchangeAnimationImporter] 애니메이션 임포트 시작: {inFbxPath}"
        )

        # FBX 파일 검증
        if not pathUtils.validate_fbx_file(inFbxPath):
            error_msg = f"FBX 파일 검증 실패: {inFbxPath}"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        # Content 경로 정규화 (절대 경로 → /Game/... 자동 변환)
        normalizedDestPath = pathUtils.normalize_content_path(inDestinationPath)
        if normalizedDestPath is None:
            error_msg = f"Content 경로 변환 실패: {inDestinationPath}"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)
        inDestinationPath = normalizedDestPath

        # 스켈레톤 경로 정규화
        normalizedSkeletonPath = pathUtils.normalize_content_path(inSkeletonPath)
        if normalizedSkeletonPath is None:
            error_msg = f"스켈레톤 경로 변환 실패: {inSkeletonPath}"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)
        inSkeletonPath = normalizedSkeletonPath

        # 스켈레톤 검증
        skeleton = self._validate_skeleton(inSkeletonPath)

        # 에셋 이름 결정 (제공되지 않으면 FBX 파일명에서 생성)
        if inAssetName is None:
            fbxFileName = Path(inFbxPath).stem
            # 애니메이션 접두사가 없으면 추가
            if not fbxFileName.startswith(self.DEFAULT_ANIMATION_PREFIX):
                inAssetName = f"{self.DEFAULT_ANIMATION_PREFIX}{fbxFileName}"
            else:
                inAssetName = fbxFileName

        # 임포트 준비 (디렉토리 생성 + 기존 파일 체크아웃)
        assetFullPath = self._prepare_asset_for_import(inDestinationPath, inAssetName)
        if assetFullPath is None:
            error_msg = f"임포트 준비 실패: {inDestinationPath}/{inAssetName}"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        # 기존 에셋 확인
        existingAsset = unreal.EditorAssetLibrary.load_asset(assetFullPath)

        # 스켈레톤 강제 교체 모드: 임시 폴더에 임포트 후 consolidate_assets 사용
        useConsolidateMode = inForceReplaceSkeleton and existingAsset is not None

        if useConsolidateMode:
            # 임시 서브폴더에 임포트 (Interchange는 FBX 파일 이름으로 에셋 이름을 결정)
            tempImportPath = f"{inDestinationPath}/_TEMP_IMPORT_"
            actualImportPath = tempImportPath
            unreal.log(
                f"[InterchangeAnimationImporter] 스켈레톤 강제 교체 모드: 임시 폴더에 임포트 -> {tempImportPath}/{inAssetName}"
            )
        else:
            actualImportPath = inDestinationPath

            # 기존 애니메이션이 있으면 AssetImportData를 제거하여 리임포트 정보 초기화
            if existingAsset is not None:
                try:
                    existingAsset.set_editor_property("asset_import_data", None)
                    unreal.log(
                        f"[InterchangeAnimationImporter] 기존 애니메이션의 AssetImportData 제거: {assetFullPath}"
                    )
                except Exception as e:
                    unreal.log_warning(
                        f"[InterchangeAnimationImporter] AssetImportData 제거 실패: {e}"
                    )

        # Interchange 임포트 실행
        sourceData = self._create_source_data(inFbxPath)

        # 파이프라인 에셋 로드 및 애니메이션용 설정 적용
        pipelinePath = self._pipelineSettings.get_pipeline_path()
        pipeline = self._pipelineSettings.load_pipeline()

        if pipeline is not None:
            unreal.log(
                f"[InterchangeAnimationImporter] 파이프라인 로드됨: {pipelinePath}"
            )

            # 스켈레톤 오버라이드 설정 (configure_for_animation에서 적용됨)
            self._pipelineSettings.set_property_override("skeleton", skeleton)

            # 애니메이션 임포트용 설정 적용 (import_animations=True, 머티리얼/텍스쳐 비활성화, 스켈레톤 설정)
            self._pipelineSettings.configure_for_animation(pipeline)

            importParams = self._create_import_params(
                inOverridePipelines=[pipelinePath]
            )
        else:
            unreal.log_warning(
                f"[InterchangeAnimationImporter] 파이프라인 로드 실패: {pipelinePath}"
            )
            importParams = self._create_import_params(inOverridePipelines=None)

        importedObjects = self._execute_import(
            actualImportPath, sourceData, importParams
        )

        if len(importedObjects) == 0:
            error_msg = f"애니메이션 임포트 실패 (임포트된 오브젝트 없음): {inFbxPath}"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        # 파이프라인 복원 (원본 상태로)
        if pipeline is not None:
            self._pipelineSettings.restore_pipeline(pipeline)

        # 임포트된 에셋 저장
        self._save_imported_assets(importedObjects)

        # 스켈레톤 강제 교체 모드: consolidate_assets로 레퍼런스 이전
        if useConsolidateMode:
            # 임포트된 애니메이션 에셋의 경로 찾기
            newAnimAssetPath = None
            for obj in importedObjects:
                if isinstance(obj, unreal.AnimSequence):
                    newAnimAssetPath = obj.get_path_name().split(".")[0]
                    break

            if newAnimAssetPath is not None:
                # 기존 에셋 경로 저장
                existingAssetPath = existingAsset.get_path_name().split(".")[0]

                unreal.log(
                    f"[InterchangeAnimationImporter] consolidate_assets 준비: {existingAssetPath} -> {newAnimAssetPath}"
                )

                # Python 참조 해제 (GC가 에셋을 잡고 있으면 consolidate_assets 실패)
                del importedObjects
                del existingAsset
                gc.collect()
                unreal.log(
                    "[InterchangeAnimationImporter] Python GC 수행 완료"
                )

                # 에셋을 경로로 다시 로드
                newAnimAsset = unreal.EditorAssetLibrary.load_asset(newAnimAssetPath)
                existingAssetForConsolidate = unreal.EditorAssetLibrary.load_asset(existingAssetPath)

                # consolidate_assets: 기존 에셋의 레퍼런스를 새 에셋으로 이전하고 기존 에셋 삭제
                success = unreal.EditorAssetLibrary.consolidate_assets(
                    newAnimAsset, [existingAssetForConsolidate]
                )

                # consolidate 후 참조 해제
                del newAnimAsset
                del existingAssetForConsolidate
                gc.collect()

                if success:
                    unreal.log(
                        "[InterchangeAnimationImporter] consolidate_assets 성공"
                    )

                    # 기존 에셋 삭제 (consolidate_assets는 레퍼런스만 이전하고 에셋을 삭제하지 않음)
                    deleted = unreal.EditorAssetLibrary.delete_asset(existingAssetPath)
                    if deleted:
                        unreal.log(
                            f"[InterchangeAnimationImporter] 기존 에셋 삭제 성공: {existingAssetPath}"
                        )
                    else:
                        unreal.log_warning(
                            f"[InterchangeAnimationImporter] 기존 에셋 삭제 실패: {existingAssetPath}"
                        )

                    # 새 에셋을 원래 위치로 이동 (rename_asset은 이동도 가능)
                    targetPath = assetFullPath
                    renamed = unreal.EditorAssetLibrary.rename_asset(
                        newAnimAssetPath, targetPath
                    )

                    if renamed:
                        unreal.log(
                            f"[InterchangeAnimationImporter] 에셋 이동 성공: {newAnimAssetPath} -> {targetPath}"
                        )
                        # 이동된 에셋 다시 로드
                        importedObjects = [unreal.EditorAssetLibrary.load_asset(targetPath)]

                        # 임시 폴더 삭제
                        if unreal.EditorAssetLibrary.does_directory_exist(tempImportPath):
                            unreal.EditorAssetLibrary.delete_directory(tempImportPath)
                            unreal.log(
                                f"[InterchangeAnimationImporter] 임시 폴더 삭제: {tempImportPath}"
                            )
                    else:
                        unreal.log_warning(
                            f"[InterchangeAnimationImporter] 에셋 이동 실패: {newAnimAssetPath} -> {targetPath}"
                        )
                        importedObjects = [unreal.EditorAssetLibrary.load_asset(newAnimAssetPath)]
                else:
                    unreal.log_error(
                        "[InterchangeAnimationImporter] consolidate_assets 실패"
                    )
                    # 실패 시에도 임포트된 에셋 반환
                    importedObjects = [unreal.EditorAssetLibrary.load_asset(newAnimAssetPath)]
            else:
                unreal.log_warning(
                    "[InterchangeAnimationImporter] 임포트된 AnimSequence를 찾을 수 없음"
                )

        # 로컬 절대 경로 수집
        localPaths = self._get_asset_local_paths(importedObjects)

        unreal.log(
            f"[InterchangeAnimationImporter] 애니메이션 임포트 성공: {inFbxPath} -> {inAssetName}"
        )

        result = self._create_interchange_result_dict(
            inFbxPath, inDestinationPath, inAssetName, True, importedObjects
        )
        result["LocalPaths"] = localPaths
        return result

    # ========================================================================
    # 배치 임포트 (동기)
    # ========================================================================

    def import_animations(
        self,
        inFbxPaths: List[str],
        inDestinationPaths: List[str],
        inSkeletonPaths: List[str],
        inAssetNames: List[str] = None,
        inOnAssetDone: Optional[Callable[[unreal.Object], None]] = None,
        inOnBatchComplete: Optional[Callable[[List[unreal.Object]], None]] = None,
        inForceReplaceSkeleton: bool = False,
    ) -> Dict[str, Any]:
        """
        여러 FBX 파일에서 애니메이션을 배치 임포트합니다. (동기 방식)

        Args:
            inFbxPaths: FBX 파일 절대 경로 리스트
            inDestinationPaths: /Game/... 형식의 Content 목적지 경로 리스트
            inSkeletonPaths: /Game/... 형식의 스켈레톤 Content 경로 리스트
            inAssetNames: 에셋 이름 리스트 (None이면 FBX 파일명 기반 자동 생성)
            inOnAssetDone: 개별 에셋 완료 콜백
            inOnBatchComplete: 전체 배치 완료 콜백
            inForceReplaceSkeleton: True이면 기존 에셋의 스켈레톤을 강제로 교체

        Returns:
            배치 임포트 결과 딕셔너리 (각 결과에 LocalPaths 포함)

        Example:
            >>> importer = InterchangeAnimationImporter()
            >>> result = importer.import_animations(
            ...     inFbxPaths=["D:/FBX/Hero_Run.fbx", "D:/FBX/Hero_Walk.fbx"],
            ...     inDestinationPaths=["/Game/Animations/Hero", "/Game/Animations/Hero"],
            ...     inSkeletonPaths=["/Game/Characters/Hero/SK_Hero", "/Game/Characters/Hero/SK_Hero"],
            ...     inAssetNames=["A_Hero_Run", "A_Hero_Walk"],
            ...     inForceReplaceSkeleton=True  # 스켈레톤 강제 교체
            ... )
        """
        unreal.log(
            f"[InterchangeAnimationImporter] 애니메이션 배치 임포트 시작: {len(inFbxPaths)}개 파일"
        )

        # 입력 검증: FBX 경로, 목적지 경로, 스켈레톤 경로 개수 일치
        if len(inFbxPaths) != len(inDestinationPaths):
            error_msg = "FBX 파일 경로와 목적지 경로의 개수가 일치하지 않습니다"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        if len(inFbxPaths) != len(inSkeletonPaths):
            error_msg = "FBX 파일과 스켈레톤 경로의 개수가 일치하지 않습니다"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        # 입력 검증: 에셋 이름이 제공된 경우 개수 일치
        if inAssetNames is not None and len(inFbxPaths) != len(inAssetNames):
            error_msg = "FBX 파일과 에셋 이름의 개수가 일치하지 않습니다"
            unreal.log_error(f"[InterchangeAnimationImporter] {error_msg}")
            raise ValueError(error_msg)

        results = []

        # 각 파일에 대해 순차적으로 임포트
        for index, fbxPath in enumerate(inFbxPaths):
            try:
                destPath = inDestinationPaths[index]
                skeletonPath = inSkeletonPaths[index]
                assetName = inAssetNames[index] if inAssetNames else None

                result = self.import_animation(
                    inFbxPath=fbxPath,
                    inDestinationPath=destPath,
                    inSkeletonPath=skeletonPath,
                    inAssetName=assetName,
                    inForceReplaceSkeleton=inForceReplaceSkeleton,
                )
                results.append(result)

                # 개별 에셋 완료 콜백 호출
                if inOnAssetDone and result.get("ImportedObjects"):
                    for obj in result["ImportedObjects"]:
                        inOnAssetDone(obj)

            except Exception as e:
                unreal.log_error(
                    f"[InterchangeAnimationImporter] 애니메이션 임포트 실패: {fbxPath}, 에러: {e}"
                )
                results.append(
                    {"SourceFile": fbxPath, "Success": False, "Error": str(e)}
                )

        # 배치 완료 콜백 호출
        if inOnBatchComplete:
            allObjects = []
            for result in results:
                if result.get("ImportedObjects"):
                    allObjects.extend(result["ImportedObjects"])
            inOnBatchComplete(allObjects)

        # 결과 집계
        successCount = len([r for r in results if r.get("Success", False)])
        failedCount = len(results) - successCount

        batchResult = {
            "TotalCount": len(inFbxPaths),
            "SuccessCount": successCount,
            "FailedCount": failedCount,
            "Results": results,
            "Errors": [r.get("Error") for r in results if r.get("Error")],
        }

        unreal.log(
            f"[InterchangeAnimationImporter] 애니메이션 배치 임포트 완료: 성공 {successCount}/{len(inFbxPaths)}"
        )

        return batchResult

    # ========================================================================
    # 배치 임포트 (비동기)
    # ========================================================================

    def import_animations_async(
        self,
        inFbxPaths: List[str],
        inDestinationPaths: List[str],
        inSkeletonPaths: List[str],
        inAssetNames: List[str] = None,
        inForceReplaceSkeleton: bool = False,
    ) -> Dict[str, Any]:
        """
        여러 FBX 파일에서 애니메이션을 배치 임포트합니다.

        Note:
            기존 비동기 방식에서 동기 방식으로 변경되었습니다.
            임포트 완료 후 에셋을 저장하고 결과를 반환합니다.

        Args:
            inFbxPaths: FBX 파일 절대 경로 리스트
            inDestinationPaths: /Game/... 형식의 Content 목적지 경로 리스트
            inSkeletonPaths: /Game/... 형식의 스켈레톤 Content 경로 리스트
            inAssetNames: 에셋 이름 리스트 (None이면 FBX 파일명 기반 자동 생성)
            inForceReplaceSkeleton: True이면 기존 에셋의 스켈레톤을 강제로 교체

        Returns:
            배치 임포트 결과 딕셔너리 (각 결과에 LocalPaths 포함)

        Example:
            >>> importer = InterchangeAnimationImporter()
            >>> result = importer.import_animations_async(
            ...     inFbxPaths=["D:/FBX/Hero_Run.fbx", "D:/FBX/Hero_Walk.fbx"],
            ...     inDestinationPaths=["/Game/Animations/Hero", "/Game/Animations/Hero"],
            ...     inSkeletonPaths=["/Game/Characters/Hero/SK_Hero", "/Game/Characters/Hero/SK_Hero"],
            ...     inAssetNames=["A_Hero_Run", "A_Hero_Walk"],
            ...     inForceReplaceSkeleton=True  # 스켈레톤 강제 교체
            ... )
        """
        # import_animations 메서드에 위임 (코드 중복 제거)
        return self.import_animations(
            inFbxPaths=inFbxPaths,
            inDestinationPaths=inDestinationPaths,
            inSkeletonPaths=inSkeletonPaths,
            inAssetNames=inAssetNames,
            inOnAssetDone=None,
            inOnBatchComplete=None,
            inForceReplaceSkeleton=inForceReplaceSkeleton,
        )
