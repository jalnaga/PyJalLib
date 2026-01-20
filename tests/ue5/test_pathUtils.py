#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pathUtils 모듈 테스트 스크립트

이 스크립트는 UE5 에디터에서 실행하여 pathUtils 모듈의 기능을 검증합니다.
실행 후 tests/logs/test_ue5_pathUtils.log 파일을 확인하세요.
"""

import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 (절대 경로 사용)
PROJECT_ROOT = Path(r"J:\My Drive\Programming\Python\PyJalLib-ue5-interchange-framework")

# 로그 파일 경로 설정
LOG_FILE_PATH = PROJECT_ROOT / "tests" / "logs" / "test_ue5_pathUtils.log"
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    filename=str(LOG_FILE_PATH),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)
logger = logging.getLogger(__name__)

import unreal

# pathUtils 모듈 직접 import (외부 의존성 회피)
import importlib
INUNREAL_PATH = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal"
if str(INUNREAL_PATH) not in sys.path:
    sys.path.insert(0, str(INUNREAL_PATH))

import pathUtils
# 모듈 리로드 (코드 변경 반영)
importlib.reload(pathUtils)


def test_absolute_path_to_content_path():
    """absolute_path_to_content_path 함수 테스트"""
    logger.info("=== TEST: absolute_path_to_content_path ===")
    
    # UE5 Content 디렉토리 경로 가져오기
    contentDir = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_content_dir()
    )
    logger.info(f"Content 디렉토리: {contentDir}")
    
    # 테스트 케이스 1: 유효한 절대 경로
    testAbsPath1 = os.path.join(contentDir, "Characters", "Hero", "SK_Hero.uasset")
    result1 = pathUtils.absolute_path_to_content_path(testAbsPath1)
    logger.info(f"Input: {testAbsPath1}")
    logger.info(f"Output: {result1}")
    
    if result1 and result1.startswith("/Game/"):
        logger.info("SUCCESS: absolute_path_to_content_path - 유효한 경로 변환 성공")
    else:
        logger.error(f"FAIL: absolute_path_to_content_path - 경로 변환 실패: {result1}")
    
    # 테스트 케이스 2: 빈 경로
    result2 = pathUtils.absolute_path_to_content_path("")
    if result2 is None:
        logger.info("SUCCESS: absolute_path_to_content_path - 빈 경로 처리 성공")
    else:
        logger.error(f"FAIL: absolute_path_to_content_path - 빈 경로 처리 실패: {result2}")
    
    # 테스트 케이스 3: Content 디렉토리 외부 경로
    result3 = pathUtils.absolute_path_to_content_path("C:/Invalid/Path/Test.uasset")
    if result3 is None:
        logger.info("SUCCESS: absolute_path_to_content_path - 외부 경로 처리 성공")
    else:
        logger.error(f"FAIL: absolute_path_to_content_path - 외부 경로 처리 실패: {result3}")


def test_validate_content_path():
    """validate_content_path 함수 테스트"""
    logger.info("=== TEST: validate_content_path ===")
    
    # 테스트 케이스 1: 유효한 /Game/ 경로
    result1 = pathUtils.validate_content_path("/Game/Characters/Hero/SK_Hero")
    if result1:
        logger.info("SUCCESS: validate_content_path - /Game/ 경로 유효성 검증 성공")
    else:
        logger.error("FAIL: validate_content_path - /Game/ 경로 유효성 검증 실패")
    
    # 테스트 케이스 2: 유효한 /Engine/ 경로
    result2 = pathUtils.validate_content_path("/Engine/Content/Test")
    if result2:
        logger.info("SUCCESS: validate_content_path - /Engine/ 경로 유효성 검증 성공")
    else:
        logger.error("FAIL: validate_content_path - /Engine/ 경로 유효성 검증 실패")
    
    # 테스트 케이스 3: 무효한 경로
    result3 = pathUtils.validate_content_path("Invalid/Path")
    if not result3:
        logger.info("SUCCESS: validate_content_path - 무효한 경로 처리 성공")
    else:
        logger.error("FAIL: validate_content_path - 무효한 경로 처리 실패")
    
    # 테스트 케이스 4: 빈 경로
    result4 = pathUtils.validate_content_path("")
    if not result4:
        logger.info("SUCCESS: validate_content_path - 빈 경로 처리 성공")
    else:
        logger.error("FAIL: validate_content_path - 빈 경로 처리 실패")


def test_get_asset_name_from_path():
    """get_asset_name_from_path 함수 테스트"""
    logger.info("=== TEST: get_asset_name_from_path ===")
    
    # 테스트 케이스 1: 정상적인 경로
    result1 = pathUtils.get_asset_name_from_path("/Game/Characters/Hero/SK_Hero")
    if result1 == "SK_Hero":
        logger.info(f"SUCCESS: get_asset_name_from_path - 에셋 이름 추출 성공: {result1}")
    else:
        logger.error(f"FAIL: get_asset_name_from_path - 에셋 이름 추출 실패: {result1}")
    
    # 테스트 케이스 2: 빈 경로
    result2 = pathUtils.get_asset_name_from_path("")
    if result2 is None:
        logger.info("SUCCESS: get_asset_name_from_path - 빈 경로 처리 성공")
    else:
        logger.error(f"FAIL: get_asset_name_from_path - 빈 경로 처리 실패: {result2}")


def test_get_directory_from_path():
    """get_directory_from_path 함수 테스트"""
    logger.info("=== TEST: get_directory_from_path ===")
    
    # 테스트 케이스 1: 정상적인 경로
    result1 = pathUtils.get_directory_from_path("/Game/Characters/Hero/SK_Hero")
    if result1 == "/Game/Characters/Hero":
        logger.info(f"SUCCESS: get_directory_from_path - 디렉토리 추출 성공: {result1}")
    else:
        logger.error(f"FAIL: get_directory_from_path - 디렉토리 추출 실패: {result1}")
    
    # 테스트 케이스 2: 빈 경로
    result2 = pathUtils.get_directory_from_path("")
    if result2 is None:
        logger.info("SUCCESS: get_directory_from_path - 빈 경로 처리 성공")
    else:
        logger.error(f"FAIL: get_directory_from_path - 빈 경로 처리 실패: {result2}")


def test_ensure_directory_exists():
    """ensure_directory_exists 함수 테스트"""
    logger.info("=== TEST: ensure_directory_exists ===")
    
    # 테스트 케이스 1: /Game/ 루트 경로 (항상 존재)
    result1 = pathUtils.ensure_directory_exists("/Game/")
    if result1:
        logger.info("SUCCESS: ensure_directory_exists - /Game/ 경로 확인 성공")
    else:
        logger.error("FAIL: ensure_directory_exists - /Game/ 경로 확인 실패")
    
    # 테스트 케이스 2: 빈 경로
    result2 = pathUtils.ensure_directory_exists("")
    if not result2:
        logger.info("SUCCESS: ensure_directory_exists - 빈 경로 처리 성공")
    else:
        logger.error("FAIL: ensure_directory_exists - 빈 경로 처리 실패")


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 60)
    logger.info("=== pathUtils 모듈 테스트 시작 ===")
    logger.info("=" * 60)
    
    try:
        test_absolute_path_to_content_path()
        test_validate_content_path()
        test_get_asset_name_from_path()
        test_get_directory_from_path()
        test_ensure_directory_exists()
        
        logger.info("=" * 60)
        logger.info("=== 모든 테스트 완료 ===")
        logger.info("=" * 60)
        
        unreal.log(f"pathUtils 테스트 완료. 로그 파일: {LOG_FILE_PATH}")
        
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
