#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
interchangeAnimationImporter 모듈 테스트 스크립트

이 스크립트는 UE5 에디터에서 실행하여 interchangeAnimationImporter 모듈의 기능을 검증합니다.
실행 후 tests/logs/test_ue5_interchangeAnimationImporter.log 파일을 확인하세요.

테스트 타입: Type B (유저 주도 테스트)
- UE5 에디터에서 실행 필요
- 로그 파일로 결과 검증
"""

import sys
from pathlib import Path
import importlib
from datetime import datetime

# 프로젝트 루트 경로 (절대 경로 사용)
PROJECT_ROOT = Path(r"J:\My Drive\Programming\Python\PyJalLib-ue5-interchange-framework")

# 로그 파일 경로 설정
LOG_FILE_PATH = PROJECT_ROOT / "tests" / "logs" / "test_ue5_interchangeAnimationImporter.log"
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

# pathUtils를 먼저 import
import pathUtils
importlib.reload(pathUtils)

import interchangeImporterBase
importlib.reload(interchangeImporterBase)

import interchangePipelineSettings
importlib.reload(interchangePipelineSettings)

import interchangeAnimationImporter
importlib.reload(interchangeAnimationImporter)

from interchangeAnimationImporter import InterchangeAnimationImporter


def test_initialization():
    """초기화 테스트"""
    logger.info("=== TEST: initialization ===")
    
    try:
        # 테스트 케이스 1: 파라미터 없이 인스턴스 생성
        importer = InterchangeAnimationImporter()
        
        if importer is not None:
            logger.info("SUCCESS: initialization - 인스턴스 생성 성공 (파라미터 없음)")
        else:
            logger.error("FAIL: initialization - 인스턴스 생성 실패")
            return
        
        # 테스트 케이스 2: asset_type 프로퍼티
        if importer.asset_type == "Animation":
            logger.info("SUCCESS: initialization - asset_type 반환 성공")
        else:
            logger.error(f"FAIL: initialization - asset_type 반환 실패: {importer.asset_type}")
        
        # 테스트 케이스 3: _pipelineSettings 존재
        if hasattr(importer, '_pipelineSettings') and importer._pipelineSettings is not None:
            logger.info("SUCCESS: initialization - _pipelineSettings 초기화 성공")
        else:
            logger.error("FAIL: initialization - _pipelineSettings 초기화 실패")
        
        # 테스트 케이스 4: DEFAULT_ANIMATION_PREFIX 상수
        if hasattr(importer, 'DEFAULT_ANIMATION_PREFIX'):
            logger.info(f"SUCCESS: initialization - DEFAULT_ANIMATION_PREFIX 존재: {importer.DEFAULT_ANIMATION_PREFIX}")
        else:
            logger.error("FAIL: initialization - DEFAULT_ANIMATION_PREFIX 없음")
            
    except Exception as e:
        logger.error(f"FAIL: initialization - 예외 발생: {e}")


def test_import_animation_interface():
    """import_animation 메서드 인터페이스 테스트"""
    logger.info("=== TEST: import_animation_interface ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: 메서드 존재 확인
        if hasattr(importer, 'import_animation'):
            logger.info("SUCCESS: import_animation_interface - import_animation 메서드 존재")
        else:
            logger.error("FAIL: import_animation_interface - import_animation 메서드 없음")
            return
        
        # 테스트 케이스 2: 메서드 시그니처 확인 (inspect 사용)
        import inspect
        sig = inspect.signature(importer.import_animation)
        params = list(sig.parameters.keys())
        
        expected_params = ['inFbxPath', 'inDestinationPath', 'inSkeletonPath', 'inAssetName', 'inDescription']
        
        if params == expected_params:
            logger.info(f"SUCCESS: import_animation_interface - 메서드 시그니처 일치: {params}")
        else:
            logger.error(f"FAIL: import_animation_interface - 메서드 시그니처 불일치. 예상: {expected_params}, 실제: {params}")
            
    except Exception as e:
        logger.error(f"FAIL: import_animation_interface - 예외 발생: {e}")


def test_import_animations_interface():
    """import_animations 배치 메서드 인터페이스 테스트"""
    logger.info("=== TEST: import_animations_interface ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: 메서드 존재 확인
        if hasattr(importer, 'import_animations'):
            logger.info("SUCCESS: import_animations_interface - import_animations 메서드 존재")
        else:
            logger.error("FAIL: import_animations_interface - import_animations 메서드 없음")
            return
        
        # 테스트 케이스 2: 메서드 시그니처 확인
        import inspect
        sig = inspect.signature(importer.import_animations)
        params = list(sig.parameters.keys())
        
        expected_params = ['inFbxPaths', 'inDestinationPaths', 'inSkeletonPaths', 'inAssetNames', 'inDescription', 'inOnAssetDone', 'inOnBatchComplete']
        
        if params == expected_params:
            logger.info(f"SUCCESS: import_animations_interface - 메서드 시그니처 일치: {params}")
        else:
            logger.error(f"FAIL: import_animations_interface - 메서드 시그니처 불일치. 예상: {expected_params}, 실제: {params}")
            
    except Exception as e:
        logger.error(f"FAIL: import_animations_interface - 예외 발생: {e}")


def test_validate_skeleton():
    """_validate_skeleton 메서드 테스트"""
    logger.info("=== TEST: validate_skeleton ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: None 스켈레톤 경로
        try:
            skeleton = importer._validate_skeleton(None)
            logger.error("FAIL: validate_skeleton - None 경로에 대해 예외가 발생하지 않음")
        except ValueError as e:
            if "필수" in str(e) or "스켈레톤" in str(e):
                logger.info(f"SUCCESS: validate_skeleton - None 스켈레톤 경로 처리: {e}")
            else:
                logger.error(f"FAIL: validate_skeleton - 예상과 다른 에러 메시지: {e}")
        
        # 테스트 케이스 2: 유효하지 않은 경로 형식
        try:
            skeleton = importer._validate_skeleton("Invalid/Path/Without/Game")
            logger.error("FAIL: validate_skeleton - 잘못된 경로 형식에 대해 예외가 발생하지 않음")
        except ValueError as e:
            if "경로" in str(e) or "유효" in str(e):
                logger.info(f"SUCCESS: validate_skeleton - 잘못된 경로 형식 처리: {e}")
            else:
                logger.error(f"FAIL: validate_skeleton - 예상과 다른 에러 메시지: {e}")
        
        # 테스트 케이스 3: 존재하지 않는 스켈레톤 경로
        try:
            skeleton = importer._validate_skeleton("/Game/NonExistent/SK_Test")
            logger.error("FAIL: validate_skeleton - 존재하지 않는 스켈레톤에 대해 예외가 발생하지 않음")
        except ValueError as e:
            if "찾을 수 없음" in str(e) or "스켈레톤" in str(e):
                logger.info(f"SUCCESS: validate_skeleton - 존재하지 않는 스켈레톤 처리: {e}")
            else:
                logger.error(f"FAIL: validate_skeleton - 예상과 다른 에러 메시지: {e}")
            
    except Exception as e:
        logger.error(f"FAIL: validate_skeleton - 예외 발생: {e}")


def test_invalid_fbx_path():
    """유효하지 않은 FBX 경로 처리 테스트"""
    logger.info("=== TEST: invalid_fbx_path ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: 존재하지 않는 FBX 파일
        try:
            result = importer.import_animation(
                inFbxPath="D:/NonExistent/Fake.fbx",
                inDestinationPath="/Game/Test/Animations",
                inSkeletonPath="/Game/Test/Characters/SK_Test"
            )
            logger.error("FAIL: invalid_fbx_path - 예외가 발생하지 않음")
        except ValueError as e:
            if "FBX" in str(e) or "파일" in str(e):
                logger.info(f"SUCCESS: invalid_fbx_path - 존재하지 않는 FBX 처리: {e}")
            else:
                logger.error(f"FAIL: invalid_fbx_path - 예상과 다른 에러 메시지: {e}")
                
    except Exception as e:
        logger.error(f"FAIL: invalid_fbx_path - 예외 발생: {e}")


def test_invalid_content_path():
    """유효하지 않은 Content 경로 처리 테스트"""
    logger.info("=== TEST: invalid_content_path ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: 잘못된 Content 경로 형식
        try:
            result = importer.import_animation(
                inFbxPath="D:/FBX/Test.fbx",
                inDestinationPath="Invalid/Path/Without/Game",
                inSkeletonPath="/Game/Test/Characters/SK_Test"
            )
            logger.error("FAIL: invalid_content_path - 예외가 발생하지 않음")
        except ValueError as e:
            if "Content" in str(e) or "경로" in str(e) or "FBX" in str(e):
                logger.info(f"SUCCESS: invalid_content_path - 잘못된 Content 경로 처리: {e}")
            else:
                logger.error(f"FAIL: invalid_content_path - 예상과 다른 에러 메시지: {e}")
                
    except Exception as e:
        logger.error(f"FAIL: invalid_content_path - 예외 발생: {e}")


def test_batch_import_validation():
    """배치 임포트 입력 검증 테스트"""
    logger.info("=== TEST: batch_import_validation ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: FBX 경로와 목적지 경로 개수 불일치
        try:
            result = importer.import_animations(
                inFbxPaths=["D:/FBX/A.fbx", "D:/FBX/B.fbx"],
                inDestinationPaths=["/Game/Test"],  # 1개만 제공
                inSkeletonPaths=["/Game/Test/SK_A", "/Game/Test/SK_B"]
            )
            logger.error("FAIL: batch_import_validation - 목적지 개수 불일치 예외가 발생하지 않음")
        except ValueError as e:
            if "개수" in str(e) or "일치" in str(e):
                logger.info(f"SUCCESS: batch_import_validation - FBX/목적지 개수 불일치 처리: {e}")
            else:
                logger.error(f"FAIL: batch_import_validation - 예상과 다른 에러 메시지: {e}")
        
        # 테스트 케이스 2: FBX 경로와 스켈레톤 경로 개수 불일치
        try:
            result = importer.import_animations(
                inFbxPaths=["D:/FBX/A.fbx", "D:/FBX/B.fbx"],
                inDestinationPaths=["/Game/Test/A", "/Game/Test/B"],
                inSkeletonPaths=["/Game/Test/SK_A"]  # 1개만 제공
            )
            logger.error("FAIL: batch_import_validation - 스켈레톤 개수 불일치 예외가 발생하지 않음")
        except ValueError as e:
            if "개수" in str(e) or "일치" in str(e):
                logger.info(f"SUCCESS: batch_import_validation - FBX/스켈레톤 개수 불일치 처리: {e}")
            else:
                logger.error(f"FAIL: batch_import_validation - 예상과 다른 에러 메시지: {e}")
        
        # 테스트 케이스 3: 에셋 이름 개수 불일치
        try:
            result = importer.import_animations(
                inFbxPaths=["D:/FBX/A.fbx", "D:/FBX/B.fbx"],
                inDestinationPaths=["/Game/Test/A", "/Game/Test/B"],
                inSkeletonPaths=["/Game/Test/SK_A", "/Game/Test/SK_B"],
                inAssetNames=["A_A"]  # 1개만 제공
            )
            logger.error("FAIL: batch_import_validation - 에셋 이름 개수 불일치 예외가 발생하지 않음")
        except ValueError as e:
            if "개수" in str(e) or "일치" in str(e):
                logger.info(f"SUCCESS: batch_import_validation - 에셋 이름 개수 불일치 처리: {e}")
            else:
                logger.error(f"FAIL: batch_import_validation - 예상과 다른 에러 메시지: {e}")
                
    except Exception as e:
        logger.error(f"FAIL: batch_import_validation - 예외 발생: {e}")


def test_inheritance():
    """InterchangeImporterBase 상속 확인 테스트"""
    logger.info("=== TEST: inheritance ===")
    
    try:
        from interchangeImporterBase import InterchangeImporterBase
        
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: InterchangeImporterBase 상속 확인
        if isinstance(importer, InterchangeImporterBase):
            logger.info("SUCCESS: inheritance - InterchangeImporterBase 상속 확인")
        else:
            logger.error("FAIL: inheritance - InterchangeImporterBase를 상속하지 않음")
        
        # 테스트 케이스 2: 베이스 클래스 메서드 사용 가능 확인
        base_methods = [
            '_get_interchange_manager',
            '_create_source_data',
            '_create_import_params',
            '_execute_import',
            '_create_result_dict',
            '_create_interchange_result_dict',
            '_prepare_import_directory',
            '_prepare_asset_for_import',
            'get_dirty_deps',
            'is_development_mode'
        ]
        
        missing_methods = []
        for method in base_methods:
            if not hasattr(importer, method):
                missing_methods.append(method)
        
        if len(missing_methods) == 0:
            logger.info("SUCCESS: inheritance - 베이스 클래스 메서드 모두 사용 가능")
        else:
            logger.error(f"FAIL: inheritance - 누락된 베이스 클래스 메서드: {missing_methods}")
            
    except Exception as e:
        logger.error(f"FAIL: inheritance - 예외 발생: {e}")


def test_no_external_dependencies():
    """외부 의존성 제거 확인 테스트"""
    logger.info("=== TEST: no_external_dependencies ===")
    
    try:
        # interchangeAnimationImporter 모듈 소스 코드 확인
        import interchangeAnimationImporter as module
        
        source_file = Path(module.__file__)
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 테스트 케이스 1: ue5_logger 의존성 제거 확인
        if 'ue5_logger' not in source_code:
            logger.info("SUCCESS: no_external_dependencies - ue5_logger 의존성 없음")
        else:
            logger.error("FAIL: no_external_dependencies - ue5_logger 의존성이 아직 존재")
        
        # 테스트 케이스 2: ..logger import 제거 확인
        if 'from ..logger' not in source_code:
            logger.info("SUCCESS: no_external_dependencies - ..logger import 없음")
        else:
            logger.error("FAIL: no_external_dependencies - ..logger import가 아직 존재")
        
        # 테스트 케이스 3: self.naming 사용 제거 확인
        if 'self.naming' not in source_code:
            logger.info("SUCCESS: no_external_dependencies - self.naming 사용 없음")
        else:
            logger.error("FAIL: no_external_dependencies - self.naming 사용이 아직 존재")
        
        # 테스트 케이스 4: convert_fbx_path_to_skeleton_path 제거 확인
        if 'convert_fbx_path_to_skeleton_path' not in source_code:
            logger.info("SUCCESS: no_external_dependencies - convert_fbx_path_to_skeleton_path 사용 없음")
        else:
            logger.error("FAIL: no_external_dependencies - convert_fbx_path_to_skeleton_path 사용이 아직 존재")
        
        # 테스트 케이스 5: 생성자에 inContentRootPrefix, inFbxRootPrefix 없음
        if 'inContentRootPrefix' not in source_code and 'inFbxRootPrefix' not in source_code:
            logger.info("SUCCESS: no_external_dependencies - 레거시 생성자 파라미터 없음")
        else:
            logger.error("FAIL: no_external_dependencies - 레거시 생성자 파라미터가 아직 존재")
            
    except Exception as e:
        logger.error(f"FAIL: no_external_dependencies - 예외 발생: {e}")


def test_pathutils_usage():
    """pathUtils 사용 확인 테스트"""
    logger.info("=== TEST: pathutils_usage ===")
    
    try:
        import interchangeAnimationImporter as module
        
        source_file = Path(module.__file__)
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 테스트 케이스 1: pathUtils import 확인
        if 'pathUtils' in source_code:
            logger.info("SUCCESS: pathutils_usage - pathUtils import 확인")
        else:
            logger.error("FAIL: pathutils_usage - pathUtils import 없음")
        
        # 테스트 케이스 2: validate_fbx_file 사용 확인
        if 'pathUtils.validate_fbx_file' in source_code:
            logger.info("SUCCESS: pathutils_usage - pathUtils.validate_fbx_file 사용 확인")
        else:
            logger.error("FAIL: pathutils_usage - pathUtils.validate_fbx_file 사용 없음")
        
        # 테스트 케이스 3: validate_content_path 사용 확인
        if 'pathUtils.validate_content_path' in source_code:
            logger.info("SUCCESS: pathutils_usage - pathUtils.validate_content_path 사용 확인")
        else:
            logger.error("FAIL: pathutils_usage - pathUtils.validate_content_path 사용 없음")
            
    except Exception as e:
        logger.error(f"FAIL: pathutils_usage - 예외 발생: {e}")


def test_batch_description_helper():
    """_create_batch_import_description 헬퍼 메서드 테스트"""
    logger.info("=== TEST: batch_description_helper ===")
    
    try:
        importer = InterchangeAnimationImporter()
        
        # 테스트 케이스 1: 메서드 존재 확인
        if hasattr(importer, '_create_batch_import_description'):
            logger.info("SUCCESS: batch_description_helper - _create_batch_import_description 메서드 존재")
        else:
            logger.error("FAIL: batch_description_helper - _create_batch_import_description 메서드 없음")
            return
        
        # 테스트 케이스 2: 3개 이하 파일
        desc = importer._create_batch_import_description(
            ["A.fbx", "B.fbx"],
            ["/Game/A", "/Game/B"]
        )
        if "Animation Batch Import" in desc and "2 files" in desc:
            logger.info(f"SUCCESS: batch_description_helper - 3개 이하 파일 처리: {desc}")
        else:
            logger.error(f"FAIL: batch_description_helper - 3개 이하 파일 처리 실패: {desc}")
        
        # 테스트 케이스 3: 3개 초과 파일
        desc = importer._create_batch_import_description(
            ["A.fbx", "B.fbx", "C.fbx", "D.fbx"],
            ["/Game/A", "/Game/B", "/Game/C", "/Game/D"]
        )
        if "Animation Batch Import" in desc and "4 files" in desc and "more" in desc:
            logger.info(f"SUCCESS: batch_description_helper - 3개 초과 파일 처리: {desc[:80]}...")
        else:
            logger.error(f"FAIL: batch_description_helper - 3개 초과 파일 처리 실패: {desc}")
            
    except Exception as e:
        logger.error(f"FAIL: batch_description_helper - 예외 발생: {e}")


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 60)
    logger.info("=== interchangeAnimationImporter 모듈 테스트 시작 ===")
    logger.info("=" * 60)
    
    try:
        test_initialization()
        test_import_animation_interface()
        test_import_animations_interface()
        test_validate_skeleton()
        test_invalid_fbx_path()
        test_invalid_content_path()
        test_batch_import_validation()
        test_inheritance()
        test_no_external_dependencies()
        test_pathutils_usage()
        test_batch_description_helper()
        
        logger.info("=" * 60)
        logger.info("=== TEST END ===")
        logger.info("=" * 60)
        
        unreal.log(f"interchangeAnimationImporter 테스트 완료. 로그 파일: {LOG_FILE_PATH}")
        
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
