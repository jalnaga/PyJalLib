#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE5 Interchange 베이스 임포터 모듈

이 모듈은 UE 5.7 Interchange Framework를 사용하여 에셋을 임포트하는 
베이스 클래스를 제공합니다.
"""

from abc import abstractmethod
from typing import List, Dict, Any, Optional, Callable

import unreal

from .baseImporter import BaseImporter
from ..logger import ue5_logger


class InterchangeImporterBase(BaseImporter):
    """
    Interchange Framework 기반 임포터의 베이스 클래스.
    
    BaseImporter를 상속하여 경로 변환 로직을 재사용하고,
    Interchange Manager 래핑 및 동기/비동기 임포트 인프라를 제공합니다.
    """
    
    def __init__(self, inContentRootPrefix: str, inFbxRootPrefix: str, inPresetName: str):
        """
        InterchangeImporterBase 초기화.
        
        Args:
            inContentRootPrefix: UE5 Content 디렉토리의 루트 경로
            inFbxRootPrefix: FBX 파일들이 위치한 루트 경로
            inPresetName: 프리셋 이름 (Skeleton, SkeletalMesh, Animation 등)
        """
        super().__init__(inContentRootPrefix, inFbxRootPrefix, inPresetName)
        
        # 배치 임포트 상태 추적
        self._batchImportResults: List[Dict[str, Any]] = []
        self._batchImportErrors: List[str] = []
        self._batchImportPendingCount: int = 0
        self._batchImportCompletedCount: int = 0
        
        # 사용자 콜백
        self._userOnAssetDone: Optional[Callable] = None
        self._userOnBatchComplete: Optional[Callable] = None
        
        ue5_logger.debug(f"InterchangeImporterBase 초기화: Preset={inPresetName}")
    
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
        ue5_logger.debug(f"SourceData 생성: {inFilePath}")
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
        ue5_logger.debug(f"SoftObjectPath 생성: {inAssetPath}")
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
        """
        importParams = unreal.ImportAssetParameters()
        importParams.is_automated = inIsAutomated
        
        # 파이프라인 오버라이드 설정
        if inOverridePipelines:
            softPaths = [self._create_soft_object_path(path) for path in inOverridePipelines]
            importParams.override_pipelines = softPaths
            ue5_logger.debug(f"파이프라인 오버라이드 설정: {inOverridePipelines}")
        
        # 리임포트 에셋 설정
        if inReimportAsset is not None:
            importParams.reimport_asset = inReimportAsset
            ue5_logger.debug(f"리임포트 에셋 설정: {inReimportAsset.get_name()}")
        
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
        ue5_logger.info(f"Interchange 동기 임포트 시작: {inContentPath}")
        
        interchangeManager = self._get_interchange_manager()
        importedObjects = interchangeManager.import_asset(
            inContentPath,
            inSourceData,
            inImportParams
        )
        
        ue5_logger.info(f"Interchange 임포트 완료: {len(importedObjects)}개 오브젝트")
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
            ue5_logger.debug(f"개별 에셋 임포트 완료: {objectName}")
            
            result = {
                "Name": objectName,
                "Path": objectPath,
                "Object": inObject,
                "Success": True
            }
            self._batchImportResults.append(result)
        else:
            ue5_logger.warning("개별 에셋 임포트 완료: None 오브젝트")
            self._batchImportErrors.append("임포트된 오브젝트가 None입니다")
        
        # 사용자 콜백 호출
        if self._userOnAssetDone is not None:
            try:
                self._userOnAssetDone(inObject)
            except Exception as e:
                ue5_logger.error(f"사용자 콜백 실행 중 에러: {e}")
    
    def _on_batch_complete(self, inObjects: List[unreal.Object]):
        """
        전체 배치 임포트 완료 시 호출되는 내부 콜백.
        
        Args:
            inObjects: 임포트된 모든 오브젝트 리스트
        """
        totalCount = len(inObjects) if inObjects else 0
        ue5_logger.info(f"배치 임포트 완료: 총 {totalCount}개 오브젝트")
        
        # 사용자 콜백 호출
        if self._userOnBatchComplete is not None:
            try:
                self._userOnBatchComplete(inObjects)
            except Exception as e:
                ue5_logger.error(f"사용자 배치 완료 콜백 실행 중 에러: {e}")
    
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
        
        ue5_logger.info(f"비동기 배치 임포트 시작: {len(inSourceDataList)}개 파일")
        
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
    # 결과 딕셔너리 생성 (Interchange 버전)
    # ========================================================================
    
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
        ue5_logger.debug(f"Interchange 결과 딕셔너리 생성: {result}")
        return result
    
    # ========================================================================
    # 추상 메서드 오버라이드 (BaseImporter 호환)
    # ========================================================================
    
    def create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """
        레거시 호환을 위한 임포트 태스크 생성 메서드.
        
        Interchange에서는 사용하지 않지만, BaseImporter의 추상 메서드이므로 구현합니다.
        실제 Interchange 임포트는 _execute_import()를 사용합니다.
        
        Args:
            inFbxFile: FBX 파일 경로
            inDestinationPath: 대상 경로
            
        Returns:
            None (Interchange에서는 사용하지 않음)
        """
        ue5_logger.warning("create_import_task는 Interchange에서 사용하지 않습니다. _execute_import()를 사용하세요.")
        return None
    
    @property
    @abstractmethod
    def asset_type(self) -> str:
        """에셋 타입을 반환하는 추상 프로퍼티 - 하위 클래스에서 구현 필수"""
        pass
