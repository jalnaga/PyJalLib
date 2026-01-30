#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 베이스 임포터 모듈

이 모듈은 UE 5.7 Interchange Framework를 사용하여 에셋을 임포트하는 
베이스 클래스를 제공합니다.

의존성: 파이썬 표준 라이브러리 + unreal + pathUtils만 사용
"""

import configparser
from abc import abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

import unreal

try:
    from . import pathUtils
except ImportError:
    import pathUtils


class InterchangeImporterBase:
    """
    Interchange Framework 기반 임포터의 베이스 클래스.
    
    Interchange Manager 래핑 및 동기/비동기 임포트 인프라를 제공합니다.
    외부 패키지 의존성 없이 파이썬 표준 라이브러리와 unreal 모듈만 사용합니다.
    """
    
    def __init__(self):
        """
        InterchangeImporterBase 초기화.
        """
        # 배치 임포트 상태 추적
        self._batchImportResults: List[Dict[str, Any]] = []
        self._batchImportErrors: List[str] = []
        self._batchImportPendingCount: int = 0
        self._batchImportCompletedCount: int = 0
        
        # 사용자 콜백
        self._userOnAssetDone: Optional[Callable] = None
        self._userOnBatchComplete: Optional[Callable] = None
        
        unreal.log(f"[InterchangeImporterBase] 초기화 완료: {self.asset_type}")
    
    @property
    @abstractmethod
    def asset_type(self) -> str:
        """에셋 타입을 반환하는 추상 프로퍼티 - 하위 클래스에서 구현 필수"""
        pass
    
    # ========================================================================
    # 개발 모드 확인
    # ========================================================================
    
    def is_development_mode(self) -> bool:
        """
        개발 모드 여부를 확인합니다.
        
        Returns:
            개발 모드이면 True, 아니면 False
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
    
    # ========================================================================
    # Interchange Manager 래핑 메서드
    # ========================================================================
    
    def _get_interchange_manager(self) -> unreal.InterchangeManager:
        """
        Interchange Manager 인스턴스를 획득합니다.
        
        Returns:
            InterchangeManager 인스턴스
        """
        return unreal.InterchangeManager.get_interchange_manager_scripted()
    
    def _create_source_data(self, inFilePath: str) -> unreal.InterchangeSourceData:
        """
        파일 경로로부터 InterchangeSourceData를 생성합니다.
        
        Args:
            inFilePath: 소스 파일 경로 (FBX 등)
            
        Returns:
            InterchangeSourceData 인스턴스
        """
        sourceData = unreal.InterchangeManager.create_source_data(inFilePath)
        unreal.log(f"[InterchangeImporterBase] SourceData 생성: {inFilePath}")
        return sourceData
    
    def _create_soft_object_path(self, inAssetPath: str) -> unreal.SoftObjectPath:
        """
        에셋 경로를 SoftObjectPath로 변환합니다.
        
        Args:
            inAssetPath: UE5 에셋 경로 (예: /Game/MyPipeline)
            
        Returns:
            SoftObjectPath 인스턴스
        """
        softPath = unreal.SoftObjectPath(inAssetPath)
        return softPath
    
    # ========================================================================
    # ImportAssetParameters 생성 헬퍼
    # ========================================================================
    
    def _create_import_params(
        self,
        inOverridePipelines: Optional[List[str]] = None,
        inIsAutomated: bool = True,
        inReimportAsset: Optional[unreal.Object] = None
    ) -> unreal.ImportAssetParameters:
        """
        ImportAssetParameters를 생성합니다.

        Args:
            inOverridePipelines: 오버라이드할 파이프라인 에셋 경로 리스트
            inIsAutomated: 자동화 임포트 여부
            inReimportAsset: 리임포트할 에셋 (None이면 새 임포트)

        Returns:
            ImportAssetParameters 인스턴스

        Note:
            UE5 ImportAssetParameters 주요 속성:
            - reimport_asset (Object): None이면 새 임포트, 기존 에셋 객체 설정 시 리임포트
            - replace_existing (bool): True 설정 시 같은 이름의 기존 에셋을 새 임포트로 덮어씀
            - is_automated (bool): True 설정 시 모달 창 없이 자동 처리
        """
        importParams = unreal.ImportAssetParameters()
        importParams.is_automated = inIsAutomated

        # 기존 에셋 덮어쓰기 강제 - 항상 새 임포트로 처리
        importParams.replace_existing = True
        unreal.log("[InterchangeImporterBase] replace_existing=True: 기존 에셋이 있어도 새 임포트로 강제")

        # 파이프라인 오버라이드 설정
        if inOverridePipelines:
            softPaths = [self._create_soft_object_path(path) for path in inOverridePipelines]
            importParams.override_pipelines = softPaths
            unreal.log(f"[InterchangeImporterBase] 파이프라인 오버라이드 설정: {inOverridePipelines}")

        # 리임포트 에셋 설정
        if inReimportAsset is not None:
            importParams.reimport_asset = inReimportAsset
            unreal.log(f"[InterchangeImporterBase] 리임포트 에셋 설정: {inReimportAsset.get_name()}")
        
        return importParams
    
    # ========================================================================
    # 동기 임포트 실행
    # ========================================================================
    
    def _execute_import(
        self, 
        inContentPath: str, 
        inSourceData: unreal.InterchangeSourceData,
        inImportParams: unreal.ImportAssetParameters
    ) -> List[unreal.Object]:
        """
        Interchange Manager를 통해 동기 임포트를 실행합니다.
        
        Args:
            inContentPath: 임포트 대상 Content 경로 (예: /Game/Characters/)
            inSourceData: InterchangeSourceData 인스턴스
            inImportParams: ImportAssetParameters 인스턴스
            
        Returns:
            임포트된 오브젝트 리스트
        """
        unreal.log(f"[InterchangeImporterBase] Interchange 동기 임포트 시작: {inContentPath}")
        
        interchangeManager = self._get_interchange_manager()
        importedObjects = interchangeManager.import_asset(
            inContentPath,
            inSourceData,
            inImportParams
        )
        
        unreal.log(f"[InterchangeImporterBase] Interchange 임포트 완료: {len(importedObjects)}개 오브젝트")
        return list(importedObjects)
    
    # ========================================================================
    # 비동기 배치 임포트 인프라
    # ========================================================================
    
    def _reset_batch_state(self):
        """배치 임포트 상태를 초기화합니다."""
        self._batchImportResults = []
        self._batchImportErrors = []
        self._batchImportPendingCount = 0
        self._batchImportCompletedCount = 0
        self._userOnAssetDone = None
        self._userOnBatchComplete = None
    
    def _on_single_asset_done(self, inObject: unreal.Object):
        """
        개별 에셋 임포트 완료 시 호출되는 내부 콜백.
        
        Args:
            inObject: 임포트된 오브젝트
        """
        self._batchImportCompletedCount += 1
        
        if inObject is not None:
            objectName = inObject.get_name()
            objectPath = inObject.get_path_name()
            unreal.log(f"[InterchangeImporterBase] 개별 에셋 임포트 완료: {objectName}")
            
            result = {
                "Name": objectName,
                "Path": objectPath,
                "Object": inObject,
                "Success": True
            }
            self._batchImportResults.append(result)
        else:
            unreal.log_warning("[InterchangeImporterBase] 개별 에셋 임포트 완료: None 오브젝트")
            self._batchImportErrors.append("임포트된 오브젝트가 None입니다")
        
        # 사용자 콜백 호출
        if self._userOnAssetDone is not None:
            try:
                self._userOnAssetDone(inObject)
            except Exception as e:
                unreal.log_error(f"[InterchangeImporterBase] 사용자 콜백 실행 중 에러: {e}")
    
    def _on_batch_complete(self, inObjects: List[unreal.Object]):
        """
        전체 배치 임포트 완료 시 호출되는 내부 콜백.
        
        Args:
            inObjects: 임포트된 모든 오브젝트 리스트
        """
        totalCount = len(inObjects) if inObjects else 0
        unreal.log(f"[InterchangeImporterBase] 배치 임포트 완료: 총 {totalCount}개 오브젝트")
        
        # 사용자 콜백 호출
        if self._userOnBatchComplete is not None:
            try:
                self._userOnBatchComplete(inObjects)
            except Exception as e:
                unreal.log_error(f"[InterchangeImporterBase] 사용자 배치 완료 콜백 실행 중 에러: {e}")
    
    def _execute_batch_import_async(
        self,
        inContentPath: str,
        inSourceDataList: List[unreal.InterchangeSourceData],
        inImportParams: unreal.ImportAssetParameters,
        inOnAssetDone: Optional[Callable[[unreal.Object], None]] = None,
        inOnBatchComplete: Optional[Callable[[List[unreal.Object]], None]] = None
    ):
        """
        비동기 배치 임포트를 실행합니다.
        
        Args:
            inContentPath: 임포트 대상 Content 경로
            inSourceDataList: InterchangeSourceData 리스트
            inImportParams: ImportAssetParameters 인스턴스
            inOnAssetDone: 개별 에셋 완료 시 사용자 콜백
            inOnBatchComplete: 전체 배치 완료 시 사용자 콜백
        """
        self._reset_batch_state()
        self._batchImportPendingCount = len(inSourceDataList)
        self._userOnAssetDone = inOnAssetDone
        self._userOnBatchComplete = inOnBatchComplete
        
        # 콜백 설정
        inImportParams.on_asset_done = self._on_single_asset_done
        inImportParams.on_assets_import_done = self._on_batch_complete
        
        unreal.log(f"[InterchangeImporterBase] 비동기 배치 임포트 시작: {len(inSourceDataList)}개 파일")
        
        interchangeManager = self._get_interchange_manager()
        
        # 각 소스 데이터에 대해 임포트 시작
        for sourceData in inSourceDataList:
            interchangeManager.import_asset(
                inContentPath,
                sourceData,
                inImportParams
            )
    
    # ========================================================================
    # 배치 결과 수집 및 반환 형식
    # ========================================================================
    
    def _get_batch_import_result(self) -> Dict[str, Any]:
        """
        배치 임포트 결과를 수집하여 반환합니다.
        
        Returns:
            배치 임포트 결과 딕셔너리
        """
        successCount = len([r for r in self._batchImportResults if r.get("Success", False)])
        failedCount = len(self._batchImportErrors)
        
        return {
            "TotalCount": self._batchImportPendingCount,
            "SuccessCount": successCount,
            "FailedCount": failedCount,
            "Results": self._batchImportResults,
            "Errors": self._batchImportErrors
        }
    
    # ========================================================================
    # 결과 딕셔너리 생성
    # ========================================================================
    
    def _create_result_dict(
        self, 
        inSourceFile: str, 
        inPath: str, 
        inName: str, 
        inSuccess: bool = True
    ) -> Dict[str, Any]:
        """
        결과 딕셔너리를 생성합니다.
        
        Args:
            inSourceFile: 소스 파일 경로
            inPath: 임포트 대상 경로
            inName: 에셋 이름
            inSuccess: 성공 여부
            
        Returns:
            결과 딕셔너리
        """
        result = {
            "SourceFile": inSourceFile,
            "Path": inPath,
            "Name": inName,
            "Type": self.asset_type,
            "Success": inSuccess
        }
        return result
    
    def _create_interchange_result_dict(
        self, 
        inSourceFile: str, 
        inPath: str, 
        inName: str, 
        inSuccess: bool = True,
        inImportedObjects: Optional[List[unreal.Object]] = None
    ) -> Dict[str, Any]:
        """
        Interchange 버전의 결과 딕셔너리를 생성합니다.
        
        Args:
            inSourceFile: 소스 파일 경로
            inPath: 임포트 대상 경로
            inName: 에셋 이름
            inSuccess: 성공 여부
            inImportedObjects: 임포트된 오브젝트 리스트
            
        Returns:
            결과 딕셔너리
        """
        result = self._create_result_dict(inSourceFile, inPath, inName, inSuccess)
        result["ImportedObjects"] = inImportedObjects or []
        return result
    
    # ========================================================================
    # 에셋 저장 및 체인지리스트 관리
    # ========================================================================

    def _save_imported_assets(self, inImportedObjects: List[unreal.Object]) -> bool:
        """
        임포트된 에셋들을 저장합니다.

        Args:
            inImportedObjects: 임포트된 오브젝트 리스트

        Returns:
            저장 성공 여부
        """
        if not inImportedObjects:
            unreal.log("[InterchangeImporterBase] 저장할 에셋이 없습니다")
            return True

        try:
            success = unreal.EditorAssetLibrary.save_loaded_assets(
                inImportedObjects, only_if_is_dirty=True
            )

            if success:
                unreal.log(
                    f"[InterchangeImporterBase] 에셋 저장 완료: {len(inImportedObjects)}개"
                )
            else:
                unreal.log_warning(
                    f"[InterchangeImporterBase] 에셋 저장 실패: {len(inImportedObjects)}개"
                )

            return success

        except Exception as e:
            unreal.log_error(f"[InterchangeImporterBase] 에셋 저장 중 에러: {e}")
            return False

    def _get_asset_local_paths(
        self,
        inImportedObjects: List[unreal.Object]
    ) -> List[str]:
        """
        임포트된 오브젝트들의 로컬 절대 경로를 반환합니다.

        Args:
            inImportedObjects: 임포트된 오브젝트 리스트

        Returns:
            로컬 절대 경로 리스트
        """
        localPaths = []

        for obj in inImportedObjects:
            objPath = obj.get_path_name()
            if objPath:
                # 패키지 경로 추출 (예: /Game/Path/Asset.Asset -> /Game/Path/Asset)
                packagePath = objPath.split(".")[0]
                # Content 경로를 시스템 경로로 변환
                systemPath = unreal.SystemLibrary.convert_to_absolute_path(
                    unreal.Paths.project_content_dir()
                )
                # /Game/ 를 Content 디렉토리로 변환
                if packagePath.startswith("/Game/"):
                    relativePath = packagePath[6:]  # "/Game/" 제거
                    fullPath = str(Path(systemPath) / relativePath) + ".uasset"
                    localPaths.append(fullPath)
                    unreal.log(
                        f"[InterchangeImporterBase] 로컬 경로: {fullPath}"
                    )

        return localPaths

    # ========================================================================
    # 에셋 의존성 확인 (소스 컨트롤용)
    # ========================================================================
    
    def get_dirty_deps(self, inAssetPath: str) -> List[str]:
        """
        에셋의 더티 종속성을 확인하고 저장합니다.
        
        Args:
            inAssetPath: 에셋 경로
            
        Returns:
            저장된 종속성 경로 리스트
        """
        returnList = []
        
        assetRegistry = unreal.AssetRegistryHelpers.get_asset_registry()
        assetData = unreal.EditorAssetLibrary.find_asset_data(inAssetPath)
        
        unreal.log(f"[InterchangeImporterBase] 에셋 의존성 확인: {assetData.asset_name}")
        
        depPackages = assetRegistry.get_dependencies(
            assetData.package_name,  
            unreal.AssetRegistryDependencyOptions(
                include_soft_package_references=False,
                include_hard_package_references=True,
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
    
    # ========================================================================
    # 임포트 경로 준비 (pathUtils 사용)
    # ========================================================================
    
    def _prepare_import_directory(self, inDestinationPath: str) -> bool:
        """
        임포트 대상 디렉토리를 준비합니다.
        
        Args:
            inDestinationPath: /Game/... 형식의 Content 경로 (정규화된 경로)
            
        Returns:
            준비 성공 여부
        """
        if not pathUtils.ensure_directory_exists(inDestinationPath):
            unreal.log_error(f"[InterchangeImporterBase] 디렉토리 생성 실패: {inDestinationPath}")
            return False
        
        return True
    
    def _prepare_asset_for_import(
        self, 
        inDestinationPath: str, 
        inAssetName: str
    ) -> Optional[str]:
        """
        임포트할 에셋 경로를 준비하고, 기존 파일이 있으면 체크아웃합니다.
        
        Args:
            inDestinationPath: /Game/... 형식의 Content 디렉토리 경로
            inAssetName: 에셋 이름
            
        Returns:
            에셋 전체 경로 (/Game/Path/AssetName), 실패 시 None
        """
        if not self._prepare_import_directory(inDestinationPath):
            return None
        
        assetFullPath = f"{inDestinationPath}/{inAssetName}"
        
        # 기존 파일이 있으면 체크아웃
        pathUtils.checkout_or_add_file(assetFullPath)
        
        unreal.log(f"[InterchangeImporterBase] 임포트 준비 완료: {assetFullPath}")
        return assetFullPath
