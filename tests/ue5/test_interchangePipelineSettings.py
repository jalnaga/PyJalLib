#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
interchangePipelineSettings 모듈 테스트 스크립트

이 스크립트는 UE5 에디터에서 실행하여 interchangePipelineSettings 모듈의 기능을 검증합니다.
실행 후 tests/logs/test_ue5_interchangePipelineSettings.log 파일을 확인하세요.
"""

import sys
from pathlib import Path
import importlib
from datetime import datetime

# 프로젝트 루트 경로 (절대 경로 사용)
PROJECT_ROOT = Path(r"J:\My Drive\Programming\Python\PyJalLib-ue5-interchange-framework")

# 로그 파일 경로 설정
LOG_FILE_PATH = PROJECT_ROOT / "tests" / "logs" / "test_ue5_interchangePipelineSettings.log"
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

import interchangePipelineSettings
importlib.reload(interchangePipelineSettings)

from interchangePipelineSettings import InterchangePipelineSettings, InterchangePipelinePreset


def test_initialization():
    """초기화 테스트"""
    logger.info("=== TEST: initialization ===")
    
    # 테스트 케이스 1: 기본 초기화
    settings = InterchangePipelineSettings()
    if settings.presetName is None:
        logger.info("SUCCESS: initialization - 기본 초기화 성공")
    else:
        logger.error(f"FAIL: initialization - 기본 초기화 실패: {settings.presetName}")
    
    # 테스트 케이스 2: 프리셋 이름으로 초기화
    settings2 = InterchangePipelineSettings("Skeleton")
    if settings2.presetName == "Skeleton":
        logger.info("SUCCESS: initialization - 프리셋 이름 초기화 성공")
    else:
        logger.error(f"FAIL: initialization - 프리셋 이름 초기화 실패: {settings2.presetName}")


def test_get_pipeline_path():
    """파이프라인 경로 테스트"""
    logger.info("=== TEST: get_pipeline_path ===")
    
    settings = InterchangePipelineSettings("Skeleton")
    
    # 테스트 케이스 1: Skeleton 프리셋 경로
    path1 = settings.get_pipeline_path(InterchangePipelinePreset.SKELETON)
    if path1 == InterchangePipelineSettings.DEFAULT_GENERIC_PIPELINE_PATH:
        logger.info(f"SUCCESS: get_pipeline_path - Skeleton 경로: {path1}")
    else:
        logger.error(f"FAIL: get_pipeline_path - Skeleton 경로 실패: {path1}")
    
    # 테스트 케이스 2: Animation 프리셋 경로
    path2 = settings.get_pipeline_path(InterchangePipelinePreset.ANIMATION)
    if path2 == InterchangePipelineSettings.DEFAULT_ANIMATION_PIPELINE_PATH:
        logger.info(f"SUCCESS: get_pipeline_path - Animation 경로: {path2}")
    else:
        logger.error(f"FAIL: get_pipeline_path - Animation 경로 실패: {path2}")
    
    # 테스트 케이스 3: 커스텀 경로 설정
    customPath = "/Game/CustomPipeline"
    settings.set_pipeline_path(InterchangePipelinePreset.SKELETON, customPath)
    path3 = settings.get_pipeline_path(InterchangePipelinePreset.SKELETON)
    if path3 == customPath:
        logger.info(f"SUCCESS: get_pipeline_path - 커스텀 경로: {path3}")
    else:
        logger.error(f"FAIL: get_pipeline_path - 커스텀 경로 실패: {path3}")


def test_get_settings():
    """설정 반환 테스트"""
    logger.info("=== TEST: get_settings ===")
    
    settings = InterchangePipelineSettings()
    
    # 테스트 케이스 1: Skeleton 설정
    skeletonSettings = settings.get_settings("Skeleton")
    if skeletonSettings.get("import_skeletal_mesh") == True and skeletonSettings.get("import_animations") == False:
        logger.info("SUCCESS: get_settings - Skeleton 설정 반환 성공")
    else:
        logger.error(f"FAIL: get_settings - Skeleton 설정 반환 실패: {skeletonSettings}")
    
    # 테스트 케이스 2: SkeletalMesh 설정
    meshSettings = settings.get_settings("SkeletalMesh")
    if meshSettings.get("import_morph_targets") == True:
        logger.info("SUCCESS: get_settings - SkeletalMesh 설정 반환 성공")
    else:
        logger.error(f"FAIL: get_settings - SkeletalMesh 설정 반환 실패: {meshSettings}")
    
    # 테스트 케이스 3: Animation 설정
    animSettings = settings.get_settings("Animation")
    if animSettings.get("import_animations") == True and animSettings.get("import_skeletal_mesh") == False:
        logger.info("SUCCESS: get_settings - Animation 설정 반환 성공")
    else:
        logger.error(f"FAIL: get_settings - Animation 설정 반환 실패: {animSettings}")


def test_property_overrides():
    """속성 오버라이드 테스트"""
    logger.info("=== TEST: property_overrides ===")
    
    settings = InterchangePipelineSettings("Skeleton")
    
    # 테스트 케이스 1: 단일 속성 오버라이드
    settings.set_property_override("custom_property", True)
    overrides = settings.get_property_overrides()
    if overrides.get("custom_property") == True:
        logger.info("SUCCESS: property_overrides - 단일 속성 오버라이드 성공")
    else:
        logger.error(f"FAIL: property_overrides - 단일 속성 오버라이드 실패: {overrides}")
    
    # 테스트 케이스 2: 복수 속성 오버라이드
    settings.set_property_overrides({"prop1": "value1", "prop2": 123})
    overrides = settings.get_property_overrides()
    if overrides.get("prop1") == "value1" and overrides.get("prop2") == 123:
        logger.info("SUCCESS: property_overrides - 복수 속성 오버라이드 성공")
    else:
        logger.error(f"FAIL: property_overrides - 복수 속성 오버라이드 실패: {overrides}")
    
    # 테스트 케이스 3: 속성 오버라이드 초기화
    settings.clear_property_overrides()
    overrides = settings.get_property_overrides()
    if len(overrides) == 0:
        logger.info("SUCCESS: property_overrides - 속성 오버라이드 초기화 성공")
    else:
        logger.error(f"FAIL: property_overrides - 속성 오버라이드 초기화 실패: {overrides}")
    
    # 테스트 케이스 4: 설정에 오버라이드 적용 확인
    settings.set_property_override("custom_setting", "custom_value")
    skeletonSettings = settings.get_settings("Skeleton")
    if skeletonSettings.get("custom_setting") == "custom_value":
        logger.info("SUCCESS: property_overrides - 설정에 오버라이드 적용 성공")
    else:
        logger.error(f"FAIL: property_overrides - 설정에 오버라이드 적용 실패: {skeletonSettings}")


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 60)
    logger.info("=== interchangePipelineSettings 모듈 테스트 시작 ===")
    logger.info("=" * 60)
    
    try:
        test_initialization()
        test_get_pipeline_path()
        test_get_settings()
        test_property_overrides()
        
        logger.info("=" * 60)
        logger.info("=== 모든 테스트 완료 ===")
        logger.info("=" * 60)
        
        unreal.log(f"interchangePipelineSettings 테스트 완료. 로그 파일: {LOG_FILE_PATH}")
        
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
