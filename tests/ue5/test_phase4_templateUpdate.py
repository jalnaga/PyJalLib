#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Phase 4: 템플릿 및 프로세서 업데이트 통합 테스트 스크립트

이 스크립트는 UE5 에디터에서 실행하여 Phase 4 작업의 결과를 검증합니다.
- Task 4.1: Interchange 템플릿 4개 새 인터페이스 적용 확인
- Task 4.2: templates/__init__.py 레거시 상수 제거 확인
- Task 4.3: templateProcessor.py 레거시 메서드 제거 및 새 인터페이스 확인

실행 후 tests/logs/test_ue5_phase4_templateUpdate.log 파일을 확인하세요.

테스트 타입: Type B (유저 주도 테스트)
- UE5 에디터에서 실행 필요
- 로그 파일로 결과 검증
"""

import sys
import re
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 (절대 경로 사용)
PROJECT_ROOT = Path(r"J:\My Drive\Programming\Python\PyJalLib-ue5-interchange-framework")

# 로그 파일 경로 설정
LOG_FILE_PATH = PROJECT_ROOT / "tests" / "logs" / "test_ue5_phase4_templateUpdate.log"
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


# ============================================================================
# Task 4.1: Interchange 템플릿 새 인터페이스 확인
# ============================================================================

def test_skeleton_template_new_interface():
    """Task 4.1: interchangeSkeletonImportTemplate.py 새 인터페이스 확인"""
    logger.info("=== TEST: skeleton_template_new_interface ===")
    
    template_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "interchangeSkeletonImportTemplate.py"
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 새 인터페이스 플레이스홀더 확인
    new_placeholders = [
        "{inExtPackagePath}",
        "{inFbxPath}",
        "{inDestinationPath}",
        "{inAssetName}",
    ]
    
    # 레거시 인터페이스 플레이스홀더 (없어야 함)
    legacy_placeholders = [
        "{inContentRootPrefix}",
        "{inFbxRootPrefix}",
        "{inSkeletonFbxPath}",
    ]
    
    all_new_found = True
    for placeholder in new_placeholders:
        if placeholder in content:
            logger.info(f"SUCCESS: skeleton_template - 새 플레이스홀더 확인: {placeholder}")
        else:
            logger.error(f"FAIL: skeleton_template - 새 플레이스홀더 없음: {placeholder}")
            all_new_found = False
    
    no_legacy = True
    for placeholder in legacy_placeholders:
        if placeholder in content:
            logger.error(f"FAIL: skeleton_template - 레거시 플레이스홀더 발견: {placeholder}")
            no_legacy = False
    
    if all_new_found and no_legacy:
        logger.info("SUCCESS: skeleton_template_new_interface - 스켈레톤 템플릿 새 인터페이스 확인 완료")


def test_skeletal_mesh_template_new_interface():
    """Task 4.1: interchangeSkeletalMeshImportTemplate.py 새 인터페이스 확인"""
    logger.info("=== TEST: skeletal_mesh_template_new_interface ===")
    
    template_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "interchangeSkeletalMeshImportTemplate.py"
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 새 인터페이스 플레이스홀더 확인
    new_placeholders = [
        "{inExtPackagePath}",
        "{inFbxPath}",
        "{inDestinationPath}",
        "{inSkeletonPath}",
        "{inAssetName}",
    ]
    
    # 레거시 인터페이스 플레이스홀더 (없어야 함)
    legacy_placeholders = [
        "{inContentRootPrefix}",
        "{inFbxRootPrefix}",
        "{inSkeletalMeshFbxPath}",
        "{inSkeletonFbxPath}",
    ]
    
    all_new_found = True
    for placeholder in new_placeholders:
        if placeholder in content:
            logger.info(f"SUCCESS: skeletal_mesh_template - 새 플레이스홀더 확인: {placeholder}")
        else:
            logger.error(f"FAIL: skeletal_mesh_template - 새 플레이스홀더 없음: {placeholder}")
            all_new_found = False
    
    no_legacy = True
    for placeholder in legacy_placeholders:
        if placeholder in content:
            logger.error(f"FAIL: skeletal_mesh_template - 레거시 플레이스홀더 발견: {placeholder}")
            no_legacy = False
    
    if all_new_found and no_legacy:
        logger.info("SUCCESS: skeletal_mesh_template_new_interface - 스켈레탈 메시 템플릿 새 인터페이스 확인 완료")


def test_anim_template_new_interface():
    """Task 4.1: interchangeAnimImportTemplate.py 새 인터페이스 확인"""
    logger.info("=== TEST: anim_template_new_interface ===")
    
    template_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "interchangeAnimImportTemplate.py"
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 새 인터페이스 플레이스홀더 확인
    new_placeholders = [
        "{inExtPackagePath}",
        "{inFbxPath}",
        "{inDestinationPath}",
        "{inSkeletonPath}",
        "{inAssetName}",
    ]
    
    # 레거시 인터페이스 플레이스홀더 (없어야 함)
    legacy_placeholders = [
        "{inContentRootPrefix}",
        "{inFbxRootPrefix}",
        "{inAnimFbxPath}",
        "{inSkeletonFbxPath}",
    ]
    
    all_new_found = True
    for placeholder in new_placeholders:
        if placeholder in content:
            logger.info(f"SUCCESS: anim_template - 새 플레이스홀더 확인: {placeholder}")
        else:
            logger.error(f"FAIL: anim_template - 새 플레이스홀더 없음: {placeholder}")
            all_new_found = False
    
    no_legacy = True
    for placeholder in legacy_placeholders:
        if placeholder in content:
            logger.error(f"FAIL: anim_template - 레거시 플레이스홀더 발견: {placeholder}")
            no_legacy = False
    
    if all_new_found and no_legacy:
        logger.info("SUCCESS: anim_template_new_interface - 애니메이션 템플릿 새 인터페이스 확인 완료")


def test_batch_anim_template_new_interface():
    """Task 4.1: interchangeBatchAnimImportTemplate.py 새 인터페이스 확인"""
    logger.info("=== TEST: batch_anim_template_new_interface ===")
    
    template_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "interchangeBatchAnimImportTemplate.py"
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 새 인터페이스 플레이스홀더 확인
    new_placeholders = [
        "{inExtPackagePath}",
        "{inFbxPaths}",
        "{inDestinationPaths}",
        "{inSkeletonPaths}",
        "{inAssetNames}",
    ]
    
    # 레거시 인터페이스 플레이스홀더 (없어야 함)
    legacy_placeholders = [
        "{inContentRootPrefix}",
        "{inFbxRootPrefix}",
        "{inAnimFbxPaths}",
        "{inSkeletonFbxPaths}",
    ]
    
    all_new_found = True
    for placeholder in new_placeholders:
        if placeholder in content:
            logger.info(f"SUCCESS: batch_anim_template - 새 플레이스홀더 확인: {placeholder}")
        else:
            logger.error(f"FAIL: batch_anim_template - 새 플레이스홀더 없음: {placeholder}")
            all_new_found = False
    
    no_legacy = True
    for placeholder in legacy_placeholders:
        if placeholder in content:
            logger.error(f"FAIL: batch_anim_template - 레거시 플레이스홀더 발견: {placeholder}")
            no_legacy = False
    
    if all_new_found and no_legacy:
        logger.info("SUCCESS: batch_anim_template_new_interface - 배치 애니메이션 템플릿 새 인터페이스 확인 완료")


# ============================================================================
# Task 4.2: templates/__init__.py 레거시 상수 제거 확인
# ============================================================================

def test_templates_init_no_legacy_constants():
    """Task 4.2: templates/__init__.py에서 레거시 상수 제거 확인"""
    logger.info("=== TEST: templates_init_no_legacy_constants ===")
    
    init_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "__init__.py"
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 제거되어야 할 레거시 상수들
    legacy_constants = [
        'ANIM_IMPORT_TEMPLATE = "animImport"',
        'SKELETON_IMPORT_TEMPLATE = "skeletonImport"',
        'SKELETAL_MESH_IMPORT_TEMPLATE = "skeletalMeshImport"',
        'BATCH_ANIM_IMPORT_TEMPLATE = "batchAnimImport"',
        '"animImportTemplate.py"',
        '"skeletonImportTemplate.py"',
        '"skeletalMeshImportTemplate.py"',
        '"batchAnimImportTemplate.py"',
    ]
    
    legacy_found = []
    for legacy in legacy_constants:
        if legacy in content:
            legacy_found.append(legacy)
    
    if len(legacy_found) == 0:
        logger.info("SUCCESS: templates_init_no_legacy_constants - 모든 레거시 상수 제거 확인")
    else:
        for legacy in legacy_found:
            logger.error(f"FAIL: templates_init_no_legacy_constants - 레거시 상수 발견: {legacy}")


def test_templates_init_has_interchange_constants():
    """Task 4.2: templates/__init__.py에 Interchange 상수 확인"""
    logger.info("=== TEST: templates_init_has_interchange_constants ===")
    
    init_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "__init__.py"
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    interchange_constants = [
        "INTERCHANGE_ANIM_IMPORT_TEMPLATE",
        "INTERCHANGE_SKELETON_IMPORT_TEMPLATE",
        "INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE",
        "INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE",
    ]
    
    all_found = True
    for constant in interchange_constants:
        if constant in content:
            logger.info(f"SUCCESS: templates_init - Interchange 상수 확인: {constant}")
        else:
            logger.error(f"FAIL: templates_init - Interchange 상수 없음: {constant}")
            all_found = False
    
    if all_found:
        logger.info("SUCCESS: templates_init_has_interchange_constants - 모든 Interchange 상수 확인")


# ============================================================================
# Task 4.3: templateProcessor.py 레거시 메서드 제거 확인
# ============================================================================

def test_template_processor_no_legacy_imports():
    """Task 4.3: templateProcessor.py에서 레거시 import 제거 확인"""
    logger.info("=== TEST: template_processor_no_legacy_imports ===")
    
    processor_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templateProcessor.py"
    
    with open(processor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 제거되어야 할 레거시 import (독립적인 상수, INTERCHANGE_ 접두사 없음)
    # 줄 단위로 검사하여 INTERCHANGE_ 접두사 없는 레거시 상수 찾기
    import re
    
    legacy_patterns = [
        r"^\s+ANIM_IMPORT_TEMPLATE\s*[,)]",  # INTERCHANGE_가 없는 ANIM_IMPORT_TEMPLATE
        r"^\s+SKELETON_IMPORT_TEMPLATE\s*[,)]",
        r"^\s+SKELETAL_MESH_IMPORT_TEMPLATE\s*[,)]",
        r"^\s+BATCH_ANIM_IMPORT_TEMPLATE\s*[,)]",
    ]
    
    legacy_found = []
    for line in content.split('\n'):
        # INTERCHANGE_ 접두사가 있는 줄은 건너뛰기
        if 'INTERCHANGE_' in line:
            continue
        
        for pattern in legacy_patterns:
            if re.search(pattern, line):
                legacy_found.append(line.strip())
    
    if len(legacy_found) == 0:
        logger.info("SUCCESS: template_processor_no_legacy_imports - 모든 레거시 import 제거 확인")
    else:
        for legacy in legacy_found:
            logger.error(f"FAIL: template_processor_no_legacy_imports - 레거시 import 발견: {legacy}")


def test_template_processor_no_legacy_methods():
    """Task 4.3: templateProcessor.py에서 레거시 메서드 제거 확인"""
    logger.info("=== TEST: template_processor_no_legacy_methods ===")
    
    processor_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templateProcessor.py"
    
    with open(processor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 제거되어야 할 레거시 메서드
    legacy_methods = [
        "def process_animation_import_template",
        "def process_skeleton_import_template",
        "def process_skeletal_mesh_import_template",
        "def process_batch_anim_import_template",
    ]
    
    legacy_found = []
    for method in legacy_methods:
        if method in content:
            legacy_found.append(method)
    
    if len(legacy_found) == 0:
        logger.info("SUCCESS: template_processor_no_legacy_methods - 모든 레거시 메서드 제거 확인")
    else:
        for method in legacy_found:
            logger.error(f"FAIL: template_processor_no_legacy_methods - 레거시 메서드 발견: {method}")


def test_template_processor_has_interchange_methods():
    """Task 4.3: templateProcessor.py에 Interchange 메서드 확인"""
    logger.info("=== TEST: template_processor_has_interchange_methods ===")
    
    processor_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templateProcessor.py"
    
    with open(processor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    interchange_methods = [
        "def process_interchange_skeleton_import_template",
        "def process_interchange_skeletal_mesh_import_template",
        "def process_interchange_animation_import_template",
        "def process_interchange_batch_anim_import_template",
    ]
    
    all_found = True
    for method in interchange_methods:
        if method in content:
            logger.info(f"SUCCESS: template_processor - Interchange 메서드 확인: {method}")
        else:
            logger.error(f"FAIL: template_processor - Interchange 메서드 없음: {method}")
            all_found = False
    
    if all_found:
        logger.info("SUCCESS: template_processor_has_interchange_methods - 모든 Interchange 메서드 확인")


def test_template_processor_has_utility_methods():
    """Task 4.3: templateProcessor.py에 유틸리티 메서드 확인"""
    logger.info("=== TEST: template_processor_has_utility_methods ===")
    
    processor_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templateProcessor.py"
    
    with open(processor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    utility_methods = [
        "def format_list_for_template",
        "def validate_template_data",
        "def get_default_output_path",
    ]
    
    all_found = True
    for method in utility_methods:
        if method in content:
            logger.info(f"SUCCESS: template_processor - 유틸리티 메서드 확인: {method}")
        else:
            logger.error(f"FAIL: template_processor - 유틸리티 메서드 없음: {method}")
            all_found = False
    
    if all_found:
        logger.info("SUCCESS: template_processor_has_utility_methods - 모든 유틸리티 메서드 확인")


# ============================================================================
# 모듈 import 및 기능 테스트
# ============================================================================
# 참고: templateProcessor.py는 logger.py를 사용하고, logger.py는 loguru를 필요로 합니다.
# UE5 환경에는 loguru가 설치되어 있지 않으므로 import 테스트는 건너뜁니다.
# templateProcessor.py는 inUnreal 외부 모듈이므로 PRD 범위 밖입니다.
# ============================================================================

def test_template_processor_import():
    """templateProcessor 모듈 import 테스트 (loguru 의존성으로 UE5에서 건너뜀)"""
    logger.info("=== TEST: template_processor_import ===")
    logger.info("SKIP: template_processor_import - templateProcessor는 loguru 의존성이 있어 UE5에서 테스트 불가 (PRD 범위 밖)")
    logger.info("NOTE: templateProcessor.py 파일 내용 검증은 이전 테스트에서 완료됨")


def test_templates_module_import():
    """templates 모듈 import 테스트"""
    logger.info("=== TEST: templates_module_import ===")
    
    # templates/__init__.py는 외부 의존성이 없으므로 직접 import 가능
    templates_init = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates" / "__init__.py"
    
    try:
        # 직접 exec으로 templates 모듈 실행하여 테스트
        with open(templates_init, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 간단한 구문 검증
        compile(content, str(templates_init), 'exec')
        logger.info("SUCCESS: templates_module_import - templates/__init__.py 구문 검증 통과")
        
        # 상수 존재 확인 (파일 내용 기반)
        required_constants = [
            "INTERCHANGE_ANIM_IMPORT_TEMPLATE",
            "INTERCHANGE_SKELETON_IMPORT_TEMPLATE",
            "INTERCHANGE_SKELETAL_MESH_IMPORT_TEMPLATE",
            "INTERCHANGE_BATCH_ANIM_IMPORT_TEMPLATE",
        ]
        
        all_found = True
        for const in required_constants:
            if const in content:
                logger.info(f"SUCCESS: templates_module_import - 상수 확인: {const}")
            else:
                logger.error(f"FAIL: templates_module_import - 상수 없음: {const}")
                all_found = False
        
        if all_found:
            logger.info("SUCCESS: templates_module_import - 모든 상수 확인 완료")
        
    except SyntaxError as e:
        logger.error(f"FAIL: templates_module_import - 구문 오류: {e}")
    except Exception as e:
        logger.error(f"FAIL: templates_module_import - 오류 발생: {e}")


def test_template_processor_skeleton_method():
    """TemplateProcessor 스켈레톤 템플릿 처리 테스트 (loguru 의존성으로 UE5에서 건너뜀)"""
    logger.info("=== TEST: template_processor_skeleton_method ===")
    logger.info("SKIP: template_processor_skeleton_method - templateProcessor는 loguru 의존성이 있어 UE5에서 테스트 불가")
    logger.info("NOTE: 템플릿 플레이스홀더 검증은 Task 4.1 테스트에서 완료됨")


def test_template_processor_batch_anim_method():
    """TemplateProcessor 배치 애니메이션 템플릿 처리 테스트 (loguru 의존성으로 UE5에서 건너뜀)"""
    logger.info("=== TEST: template_processor_batch_anim_method ===")
    logger.info("SKIP: template_processor_batch_anim_method - templateProcessor는 loguru 의존성이 있어 UE5에서 테스트 불가")
    logger.info("NOTE: 배치 템플릿 플레이스홀더 검증은 Task 4.1 테스트에서 완료됨")


def test_format_list_for_template():
    """format_list_for_template 유틸리티 메서드 테스트 (파일 내용 기반)"""
    logger.info("=== TEST: format_list_for_template ===")
    
    processor_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templateProcessor.py"
    
    with open(processor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # format_list_for_template 메서드가 존재하고 올바른 구현인지 확인
    if "def format_list_for_template" in content:
        logger.info("SUCCESS: format_list_for_template - 메서드 존재 확인")
        
        # 구현 내용 확인 (r' 접두사 사용하는지)
        if "r'" in content and "formatted_items" in content:
            logger.info("SUCCESS: format_list_for_template - raw 문자열 포맷팅 구현 확인")
        else:
            logger.error("FAIL: format_list_for_template - 구현 내용 확인 필요")
    else:
        logger.error("FAIL: format_list_for_template - 메서드 없음")


# ============================================================================
# 전체 테스트 실행
# ============================================================================

def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 70)
    logger.info("=== Phase 4: 템플릿 및 프로세서 업데이트 통합 테스트 시작 ===")
    logger.info("=" * 70)
    
    try:
        # Task 4.1: Interchange 템플릿 새 인터페이스 확인
        logger.info("\n--- Task 4.1: Interchange 템플릿 새 인터페이스 확인 ---")
        test_skeleton_template_new_interface()
        test_skeletal_mesh_template_new_interface()
        test_anim_template_new_interface()
        test_batch_anim_template_new_interface()
        
        # Task 4.2: templates/__init__.py 업데이트 확인
        logger.info("\n--- Task 4.2: templates/__init__.py 업데이트 확인 ---")
        test_templates_init_no_legacy_constants()
        test_templates_init_has_interchange_constants()
        
        # Task 4.3: templateProcessor.py 업데이트 확인
        logger.info("\n--- Task 4.3: templateProcessor.py 업데이트 확인 ---")
        test_template_processor_no_legacy_imports()
        test_template_processor_no_legacy_methods()
        test_template_processor_has_interchange_methods()
        test_template_processor_has_utility_methods()
        
        # 모듈 import 및 기능 테스트
        logger.info("\n--- 모듈 import 및 기능 테스트 ---")
        test_templates_module_import()
        test_template_processor_import()
        test_format_list_for_template()
        test_template_processor_skeleton_method()
        test_template_processor_batch_anim_method()
        
        logger.info("\n" + "=" * 70)
        logger.info("=== Phase 4 테스트 완료 ===")
        logger.info("=" * 70)
        
        unreal.log(f"Phase 4 템플릿 및 프로세서 업데이트 테스트 완료. 로그 파일: {LOG_FILE_PATH}")
        
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
