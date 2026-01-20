#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
interchangeImporterBase 모듈 테스트 스크립트

이 스크립트는 UE5 에디터에서 실행하여 interchangeImporterBase 모듈의 기능을 검증합니다.
실행 후 tests/logs/test_ue5_interchangeImporterBase.log 파일을 확인하세요.
"""

import sys
from pathlib import Path
import importlib
from datetime import datetime

# 프로젝트 루트 경로 (절대 경로 사용)
PROJECT_ROOT = Path(r"J:\My Drive\Programming\Python\PyJalLib-ue5-interchange-framework")

# 로그 파일 경로 설정
LOG_FILE_PATH = PROJECT_ROOT / "tests" / "logs" / "test_ue5_interchangeImporterBase.log"
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# 직접 파일에 쓰는 간단한 로거
class SimpleLogger:
    def __init__(self, filepath):
        self.filepath = filepath
        # 파일 초기화
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write("")
    
    def _write(self, level, msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"{timestamp} - {level} - {msg}\n"
        with open(self.filepath, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def info(self, msg):
        self._write("INFO", msg)
    
    def error(self, msg):
        self._write("ERROR", msg)

logger = SimpleLogger(str(LOG_FILE_PATH))

import unreal

# 모듈 직접 import (외부 의존성 회피)
INUNREAL_PATH = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal"
if str(INUNREAL_PATH) not in sys.path:
    sys.path.insert(0, str(INUNREAL_PATH))

# pathUtils를 먼저 import하여 interchangeImporterBase의 relative import 문제 해결
import pathUtils
importlib.reload(pathUtils)

import interchangeImporterBase
importlib.reload(interchangeImporterBase)

from interchangeImporterBase import InterchangeImporterBase


# 테스트용 구체 클래스 (추상 클래스를 상속)
class TestImporter(InterchangeImporterBase):
    """테스트를 위한 구체적인 임포터 클래스"""
    
    @property
    def asset_type(self) -> str:
        return "TestAsset"


def test_initialization():
    """초기화 테스트"""
    logger.info("=== TEST: initialization ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: 인스턴스 생성 성공
        if importer is not None:
            logger.info("SUCCESS: initialization - 인스턴스 생성 성공")
        else:
            logger.error("FAIL: initialization - 인스턴스 생성 실패")
        
        # 테스트 케이스 2: asset_type 프로퍼티
        if importer.asset_type == "TestAsset":
            logger.info("SUCCESS: initialization - asset_type 반환 성공")
        else:
            logger.error(f"FAIL: initialization - asset_type 반환 실패: {importer.asset_type}")
        
        # 테스트 케이스 3: 배치 상태 초기화 확인
        if len(importer._batchImportResults) == 0 and len(importer._batchImportErrors) == 0:
            logger.info("SUCCESS: initialization - 배치 상태 초기화 성공")
        else:
            logger.error("FAIL: initialization - 배치 상태 초기화 실패")
            
    except Exception as e:
        logger.error(f"FAIL: initialization - 예외 발생: {e}")


def test_is_development_mode():
    """개발 모드 확인 테스트"""
    logger.info("=== TEST: is_development_mode ===")
    
    try:
        importer = TestImporter()
        
        # is_development_mode는 True 또는 False를 반환해야 함
        result = importer.is_development_mode()
        
        if isinstance(result, bool):
            logger.info(f"SUCCESS: is_development_mode - 결과: {result}")
        else:
            logger.error(f"FAIL: is_development_mode - bool이 아닌 결과: {type(result)}")
            
    except Exception as e:
        logger.error(f"FAIL: is_development_mode - 예외 발생: {e}")


def test_get_interchange_manager():
    """Interchange Manager 획득 테스트"""
    logger.info("=== TEST: _get_interchange_manager ===")
    
    try:
        importer = TestImporter()
        manager = importer._get_interchange_manager()
        
        if manager is not None:
            logger.info(f"SUCCESS: _get_interchange_manager - Manager 획득 성공: {type(manager).__name__}")
        else:
            logger.error("FAIL: _get_interchange_manager - Manager가 None")
            
    except Exception as e:
        logger.error(f"FAIL: _get_interchange_manager - 예외 발생: {e}")


def test_create_soft_object_path():
    """SoftObjectPath 생성 테스트"""
    logger.info("=== TEST: _create_soft_object_path ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: 유효한 경로
        testPath = "/Game/Test/TestPipeline"
        softPath = importer._create_soft_object_path(testPath)
        
        if softPath is not None:
            logger.info(f"SUCCESS: _create_soft_object_path - SoftObjectPath 생성 성공")
        else:
            logger.error("FAIL: _create_soft_object_path - SoftObjectPath가 None")
            
    except Exception as e:
        logger.error(f"FAIL: _create_soft_object_path - 예외 발생: {e}")


def test_create_import_params():
    """ImportAssetParameters 생성 테스트"""
    logger.info("=== TEST: _create_import_params ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: 기본 파라미터
        params1 = importer._create_import_params()
        if params1 is not None and params1.is_automated:
            logger.info("SUCCESS: _create_import_params - 기본 파라미터 생성 성공")
        else:
            logger.error("FAIL: _create_import_params - 기본 파라미터 생성 실패")
        
        # 테스트 케이스 2: 파이프라인 오버라이드
        pipelinePaths = ["/Game/Interchange/TestPipeline"]
        params2 = importer._create_import_params(inOverridePipelines=pipelinePaths)
        if params2 is not None and len(params2.override_pipelines) > 0:
            logger.info("SUCCESS: _create_import_params - 파이프라인 오버라이드 설정 성공")
        else:
            logger.error("FAIL: _create_import_params - 파이프라인 오버라이드 설정 실패")
        
        # 테스트 케이스 3: 자동화 플래그 비활성화
        params3 = importer._create_import_params(inIsAutomated=False)
        if params3 is not None and not params3.is_automated:
            logger.info("SUCCESS: _create_import_params - 자동화 플래그 비활성화 성공")
        else:
            logger.error("FAIL: _create_import_params - 자동화 플래그 비활성화 실패")
            
    except Exception as e:
        logger.error(f"FAIL: _create_import_params - 예외 발생: {e}")


def test_create_result_dict():
    """결과 딕셔너리 생성 테스트"""
    logger.info("=== TEST: _create_result_dict ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: 성공 결과
        result1 = importer._create_result_dict(
            inSourceFile="D:/FBX/Test.fbx",
            inPath="/Game/Test",
            inName="TestAsset",
            inSuccess=True
        )
        
        if (result1.get("SourceFile") == "D:/FBX/Test.fbx" and
            result1.get("Path") == "/Game/Test" and
            result1.get("Name") == "TestAsset" and
            result1.get("Type") == "TestAsset" and
            result1.get("Success") == True):
            logger.info("SUCCESS: _create_result_dict - 성공 결과 생성 성공")
        else:
            logger.error(f"FAIL: _create_result_dict - 성공 결과 생성 실패: {result1}")
        
        # 테스트 케이스 2: 실패 결과
        result2 = importer._create_result_dict(
            inSourceFile="D:/FBX/Test.fbx",
            inPath="/Game/Test",
            inName="TestAsset",
            inSuccess=False
        )
        
        if result2.get("Success") == False:
            logger.info("SUCCESS: _create_result_dict - 실패 결과 생성 성공")
        else:
            logger.error(f"FAIL: _create_result_dict - 실패 결과 생성 실패: {result2}")
            
    except Exception as e:
        logger.error(f"FAIL: _create_result_dict - 예외 발생: {e}")


def test_create_interchange_result_dict():
    """Interchange 결과 딕셔너리 생성 테스트"""
    logger.info("=== TEST: _create_interchange_result_dict ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: ImportedObjects 포함
        result1 = importer._create_interchange_result_dict(
            inSourceFile="D:/FBX/Test.fbx",
            inPath="/Game/Test",
            inName="TestAsset",
            inSuccess=True,
            inImportedObjects=[]
        )
        
        if "ImportedObjects" in result1:
            logger.info("SUCCESS: _create_interchange_result_dict - ImportedObjects 포함 성공")
        else:
            logger.error("FAIL: _create_interchange_result_dict - ImportedObjects 누락")
        
        # 테스트 케이스 2: ImportedObjects가 None일 때
        result2 = importer._create_interchange_result_dict(
            inSourceFile="D:/FBX/Test.fbx",
            inPath="/Game/Test",
            inName="TestAsset",
            inSuccess=True,
            inImportedObjects=None
        )
        
        if result2.get("ImportedObjects") == []:
            logger.info("SUCCESS: _create_interchange_result_dict - None 처리 성공")
        else:
            logger.error(f"FAIL: _create_interchange_result_dict - None 처리 실패: {result2}")
            
    except Exception as e:
        logger.error(f"FAIL: _create_interchange_result_dict - 예외 발생: {e}")


def test_prepare_import_directory():
    """임포트 디렉토리 준비 테스트"""
    logger.info("=== TEST: _prepare_import_directory ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: 유효한 /Game/ 경로
        result1 = importer._prepare_import_directory("/Game/Test/Characters")
        if result1:
            logger.info("SUCCESS: _prepare_import_directory - /Game/ 경로 성공")
        else:
            logger.error("FAIL: _prepare_import_directory - /Game/ 경로 실패")
        
        # 테스트 케이스 2: 무효한 경로
        result2 = importer._prepare_import_directory("Invalid/Path")
        if not result2:
            logger.info("SUCCESS: _prepare_import_directory - 무효한 경로 처리 성공")
        else:
            logger.error("FAIL: _prepare_import_directory - 무효한 경로 처리 실패")
        
        # 테스트 케이스 3: 빈 경로
        result3 = importer._prepare_import_directory("")
        if not result3:
            logger.info("SUCCESS: _prepare_import_directory - 빈 경로 처리 성공")
        else:
            logger.error("FAIL: _prepare_import_directory - 빈 경로 처리 실패")
            
    except Exception as e:
        logger.error(f"FAIL: _prepare_import_directory - 예외 발생: {e}")


def test_prepare_asset_for_import():
    """에셋 임포트 준비 테스트"""
    logger.info("=== TEST: _prepare_asset_for_import ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 케이스 1: 유효한 경로와 이름
        result1 = importer._prepare_asset_for_import("/Game/Test/Characters", "SK_TestCharacter")
        if result1 == "/Game/Test/Characters/SK_TestCharacter":
            logger.info(f"SUCCESS: _prepare_asset_for_import - 경로 생성 성공: {result1}")
        else:
            logger.error(f"FAIL: _prepare_asset_for_import - 경로 생성 실패: {result1}")
        
        # 테스트 케이스 2: 무효한 경로
        result2 = importer._prepare_asset_for_import("Invalid/Path", "TestAsset")
        if result2 is None:
            logger.info("SUCCESS: _prepare_asset_for_import - 무효한 경로 처리 성공")
        else:
            logger.error(f"FAIL: _prepare_asset_for_import - 무효한 경로 처리 실패: {result2}")
            
    except Exception as e:
        logger.error(f"FAIL: _prepare_asset_for_import - 예외 발생: {e}")


def test_reset_batch_state():
    """배치 상태 초기화 테스트"""
    logger.info("=== TEST: _reset_batch_state ===")
    
    try:
        importer = TestImporter()
        
        # 상태 변경
        importer._batchImportResults.append({"test": "data"})
        importer._batchImportErrors.append("test error")
        importer._batchImportPendingCount = 5
        importer._batchImportCompletedCount = 3
        
        # 상태 초기화
        importer._reset_batch_state()
        
        if (len(importer._batchImportResults) == 0 and
            len(importer._batchImportErrors) == 0 and
            importer._batchImportPendingCount == 0 and
            importer._batchImportCompletedCount == 0):
            logger.info("SUCCESS: _reset_batch_state - 배치 상태 초기화 성공")
        else:
            logger.error("FAIL: _reset_batch_state - 배치 상태 초기화 실패")
            
    except Exception as e:
        logger.error(f"FAIL: _reset_batch_state - 예외 발생: {e}")


def test_get_batch_import_result():
    """배치 임포트 결과 수집 테스트"""
    logger.info("=== TEST: _get_batch_import_result ===")
    
    try:
        importer = TestImporter()
        
        # 테스트 데이터 설정
        importer._batchImportPendingCount = 3
        importer._batchImportResults = [
            {"Name": "Asset1", "Success": True},
            {"Name": "Asset2", "Success": True},
            {"Name": "Asset3", "Success": False}
        ]
        importer._batchImportErrors = ["Error1"]
        
        result = importer._get_batch_import_result()
        
        if (result.get("TotalCount") == 3 and
            result.get("SuccessCount") == 2 and
            result.get("FailedCount") == 1):
            logger.info("SUCCESS: _get_batch_import_result - 결과 수집 성공")
        else:
            logger.error(f"FAIL: _get_batch_import_result - 결과 수집 실패: {result}")
            
    except Exception as e:
        logger.error(f"FAIL: _get_batch_import_result - 예외 발생: {e}")


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 60)
    logger.info("=== interchangeImporterBase 모듈 테스트 시작 ===")
    logger.info("=" * 60)
    
    try:
        test_initialization()
        test_is_development_mode()
        test_get_interchange_manager()
        test_create_soft_object_path()
        test_create_import_params()
        test_create_result_dict()
        test_create_interchange_result_dict()
        test_prepare_import_directory()
        test_prepare_asset_for_import()
        test_reset_batch_state()
        test_get_batch_import_result()
        
        logger.info("=" * 60)
        logger.info("=== 모든 테스트 완료 ===")
        logger.info("=" * 60)
        
        unreal.log(f"interchangeImporterBase 테스트 완료. 로그 파일: {LOG_FILE_PATH}")
        
    except Exception as e:
        logger.error(f"테스트 실행 중 예외 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())


# 메인 실행
if __name__ == "__main__":
    run_all_tests()
else:
    # UE5 에디터에서 import 시 자동 실행
    run_all_tests()
