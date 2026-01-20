#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Phase 3: 레거시 코드 제거 통합 테스트 스크립트

이 스크립트는 UE5 에디터에서 실행하여 Phase 3 작업의 결과를 검증합니다.
- 레거시 임포터 파일 삭제 확인
- inUnreal/__init__.py 업데이트 확인
- 레거시 템플릿 파일 삭제 확인
- templates/__init__.py 업데이트 확인
- Interchange 모듈 정상 import 확인

실행 후 tests/logs/test_ue5_phase3_legacyRemoval.log 파일을 확인하세요.

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
LOG_FILE_PATH = PROJECT_ROOT / "tests" / "logs" / "test_ue5_phase3_legacyRemoval.log"
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


def test_legacy_importer_files_deleted():
    """Task 3.1: 레거시 임포터 파일 삭제 확인"""
    logger.info("=== TEST: legacy_importer_files_deleted ===")
    
    inunreal_dir = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal"
    
    # 삭제되어야 할 레거시 파일들
    legacy_files = [
        "baseImporter.py",
        "importerSettings.py",
        "skeletonImporter.py",
        "skeletalMeshImporter.py",
        "animationImporter.py",
    ]
    
    all_deleted = True
    for filename in legacy_files:
        filepath = inunreal_dir / filename
        if filepath.exists():
            logger.error(f"FAIL: legacy_importer_files_deleted - 파일이 아직 존재: {filename}")
            all_deleted = False
        else:
            logger.info(f"SUCCESS: legacy_importer_files_deleted - 파일 삭제 확인: {filename}")
    
    if all_deleted:
        logger.info("SUCCESS: legacy_importer_files_deleted - 모든 레거시 임포터 파일 삭제 완료")


def test_legacy_template_files_deleted():
    """Task 3.3: 레거시 템플릿 파일 삭제 확인"""
    logger.info("=== TEST: legacy_template_files_deleted ===")
    
    templates_dir = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates"
    
    # 삭제되어야 할 레거시 템플릿 파일들
    legacy_templates = [
        "skeletonImportTemplate.py",
        "skeletalMeshImportTemplate.py",
        "animImportTemplate.py",
        "batchAnimImportTemplate.py",
    ]
    
    all_deleted = True
    for filename in legacy_templates:
        filepath = templates_dir / filename
        if filepath.exists():
            logger.error(f"FAIL: legacy_template_files_deleted - 파일이 아직 존재: {filename}")
            all_deleted = False
        else:
            logger.info(f"SUCCESS: legacy_template_files_deleted - 파일 삭제 확인: {filename}")
    
    if all_deleted:
        logger.info("SUCCESS: legacy_template_files_deleted - 모든 레거시 템플릿 파일 삭제 완료")


def test_interchange_files_exist():
    """Interchange 파일들이 존재하는지 확인"""
    logger.info("=== TEST: interchange_files_exist ===")
    
    inunreal_dir = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal"
    
    # 존재해야 할 Interchange 파일들
    interchange_files = [
        "pathUtils.py",
        "interchangeImporterBase.py",
        "interchangePipelineSettings.py",
        "interchangeSkeletonImporter.py",
        "interchangeSkeletalMeshImporter.py",
        "interchangeAnimationImporter.py",
    ]
    
    all_exist = True
    for filename in interchange_files:
        filepath = inunreal_dir / filename
        if filepath.exists():
            logger.info(f"SUCCESS: interchange_files_exist - 파일 존재 확인: {filename}")
        else:
            logger.error(f"FAIL: interchange_files_exist - 파일이 존재하지 않음: {filename}")
            all_exist = False
    
    if all_exist:
        logger.info("SUCCESS: interchange_files_exist - 모든 Interchange 파일 존재 확인")


def test_interchange_templates_exist():
    """Interchange 템플릿 파일들이 존재하는지 확인"""
    logger.info("=== TEST: interchange_templates_exist ===")
    
    templates_dir = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "templates"
    
    # 존재해야 할 Interchange 템플릿 파일들
    interchange_templates = [
        "interchangeAnimImportTemplate.py",
        "interchangeSkeletonImportTemplate.py",
        "interchangeSkeletalMeshImportTemplate.py",
        "interchangeBatchAnimImportTemplate.py",
    ]
    
    all_exist = True
    for filename in interchange_templates:
        filepath = templates_dir / filename
        if filepath.exists():
            logger.info(f"SUCCESS: interchange_templates_exist - 파일 존재 확인: {filename}")
        else:
            logger.error(f"FAIL: interchange_templates_exist - 파일이 존재하지 않음: {filename}")
            all_exist = False
    
    if all_exist:
        logger.info("SUCCESS: interchange_templates_exist - 모든 Interchange 템플릿 파일 존재 확인")


def test_inunreal_init_no_legacy():
    """Task 3.2: inUnreal/__init__.py에서 레거시 import 제거 확인"""
    logger.info("=== TEST: inunreal_init_no_legacy ===")
    
    init_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal" / "__init__.py"
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 제거되어야 할 레거시 import들 (정확한 패턴 사용)
    # Interchange 모듈 이름과 혼동을 피하기 위해 정확한 패턴 검사
    legacy_imports = [
        "from .importerSettings",
        "from .baseImporter",
        "from .skeletonImporter",
        "from .skeletalMeshImporter",
        "from .animationImporter",
        "'ImporterSettings'",
        "'BaseImporter'",
        # SkeletonImporter 등은 Interchange 이름에 포함되어 있으므로 from 패턴으로만 검사
    ]
    
    legacy_found = []
    for legacy in legacy_imports:
        if legacy in content:
            legacy_found.append(legacy)
    
    if len(legacy_found) == 0:
        logger.info("SUCCESS: inunreal_init_no_legacy - 모든 레거시 import 제거 확인")
    else:
        for legacy in legacy_found:
            logger.error(f"FAIL: inunreal_init_no_legacy - 레거시 import 발견: {legacy}")


def test_inunreal_init_has_pathutils():
    """Task 3.2: inUnreal/__init__.py에 pathUtils export 확인"""
    logger.info("=== TEST: inunreal_init_has_pathutils ===")
    
    init_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal" / "__init__.py"
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'pathUtils' in content:
        logger.info("SUCCESS: inunreal_init_has_pathutils - pathUtils export 확인")
    else:
        logger.error("FAIL: inunreal_init_has_pathutils - pathUtils export 없음")


def test_inunreal_init_has_interchange():
    """inUnreal/__init__.py에 Interchange 모듈 export 확인"""
    logger.info("=== TEST: inunreal_init_has_interchange ===")
    
    init_file = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal" / "__init__.py"
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    interchange_exports = [
        "InterchangeImporterBase",
        "InterchangePipelineSettings",
        "InterchangePipelinePreset",
        "InterchangeSkeletonImporter",
        "InterchangeSkeletalMeshImporter",
        "InterchangeAnimationImporter",
    ]
    
    all_found = True
    for export in interchange_exports:
        if export in content:
            logger.info(f"SUCCESS: inunreal_init_has_interchange - export 확인: {export}")
        else:
            logger.error(f"FAIL: inunreal_init_has_interchange - export 없음: {export}")
            all_found = False
    
    if all_found:
        logger.info("SUCCESS: inunreal_init_has_interchange - 모든 Interchange export 확인")


def test_templates_init_no_legacy():
    """Task 3.3: templates/__init__.py에서 레거시 상수 제거 확인"""
    logger.info("=== TEST: templates_init_no_legacy ===")
    
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
        logger.info("SUCCESS: templates_init_no_legacy - 모든 레거시 상수 및 매핑 제거 확인")
    else:
        for legacy in legacy_found:
            logger.error(f"FAIL: templates_init_no_legacy - 레거시 상수/매핑 발견: {legacy}")


def test_templates_init_has_interchange():
    """templates/__init__.py에 Interchange 상수 확인"""
    logger.info("=== TEST: templates_init_has_interchange ===")
    
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
            logger.info(f"SUCCESS: templates_init_has_interchange - 상수 확인: {constant}")
        else:
            logger.error(f"FAIL: templates_init_has_interchange - 상수 없음: {constant}")
            all_found = False
    
    if all_found:
        logger.info("SUCCESS: templates_init_has_interchange - 모든 Interchange 상수 확인")


def test_interchange_module_import():
    """Interchange 모듈 import 테스트"""
    logger.info("=== TEST: interchange_module_import ===")
    
    # 모듈 직접 import (외부 의존성 회피)
    INUNREAL_PATH = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal"
    if str(INUNREAL_PATH) not in sys.path:
        sys.path.insert(0, str(INUNREAL_PATH))
    
    modules_to_test = [
        ("pathUtils", "pathUtils"),
        ("interchangeImporterBase", "InterchangeImporterBase"),
        ("interchangePipelineSettings", "InterchangePipelineSettings"),
        ("interchangeSkeletonImporter", "InterchangeSkeletonImporter"),
        ("interchangeSkeletalMeshImporter", "InterchangeSkeletalMeshImporter"),
        ("interchangeAnimationImporter", "InterchangeAnimationImporter"),
    ]
    
    all_imported = True
    for module_name, class_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            importlib.reload(module)
            
            if class_name == "pathUtils":
                # pathUtils는 모듈 자체
                logger.info(f"SUCCESS: interchange_module_import - {module_name} import 성공")
            else:
                # 클래스가 있는지 확인
                if hasattr(module, class_name):
                    logger.info(f"SUCCESS: interchange_module_import - {module_name}.{class_name} import 성공")
                else:
                    logger.error(f"FAIL: interchange_module_import - {module_name}에 {class_name} 클래스 없음")
                    all_imported = False
        except Exception as e:
            logger.error(f"FAIL: interchange_module_import - {module_name} import 실패: {e}")
            all_imported = False
    
    if all_imported:
        logger.info("SUCCESS: interchange_module_import - 모든 Interchange 모듈 import 성공")


def test_interchange_importer_instantiation():
    """Interchange 임포터 인스턴스 생성 테스트"""
    logger.info("=== TEST: interchange_importer_instantiation ===")
    
    # 모듈 직접 import
    INUNREAL_PATH = PROJECT_ROOT / "src" / "pyjallib" / "ue5" / "inUnreal"
    if str(INUNREAL_PATH) not in sys.path:
        sys.path.insert(0, str(INUNREAL_PATH))
    
    importers = [
        ("interchangeSkeletonImporter", "InterchangeSkeletonImporter"),
        ("interchangeSkeletalMeshImporter", "InterchangeSkeletalMeshImporter"),
        ("interchangeAnimationImporter", "InterchangeAnimationImporter"),
    ]
    
    all_created = True
    for module_name, class_name in importers:
        try:
            module = importlib.import_module(module_name)
            importlib.reload(module)
            
            importer_class = getattr(module, class_name)
            importer = importer_class()  # 파라미터 없이 생성
            
            if importer is not None:
                logger.info(f"SUCCESS: interchange_importer_instantiation - {class_name}() 인스턴스 생성 성공")
            else:
                logger.error(f"FAIL: interchange_importer_instantiation - {class_name}() 인스턴스 생성 실패")
                all_created = False
        except Exception as e:
            logger.error(f"FAIL: interchange_importer_instantiation - {class_name}() 생성 실패: {e}")
            all_created = False
    
    if all_created:
        logger.info("SUCCESS: interchange_importer_instantiation - 모든 Interchange 임포터 인스턴스 생성 성공")


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 60)
    logger.info("=== Phase 3: 레거시 코드 제거 통합 테스트 시작 ===")
    logger.info("=" * 60)
    
    try:
        # Task 3.1: 레거시 임포터 파일 삭제
        test_legacy_importer_files_deleted()
        
        # Task 3.3: 레거시 템플릿 파일 삭제
        test_legacy_template_files_deleted()
        
        # Interchange 파일 존재 확인
        test_interchange_files_exist()
        test_interchange_templates_exist()
        
        # Task 3.2: inUnreal/__init__.py 업데이트
        test_inunreal_init_no_legacy()
        test_inunreal_init_has_pathutils()
        test_inunreal_init_has_interchange()
        
        # Task 3.3: templates/__init__.py 업데이트
        test_templates_init_no_legacy()
        test_templates_init_has_interchange()
        
        # Interchange 모듈 import 및 인스턴스 생성 테스트
        test_interchange_module_import()
        test_interchange_importer_instantiation()
        
        logger.info("=" * 60)
        logger.info("=== TEST END ===")
        logger.info("=" * 60)
        
        unreal.log(f"Phase 3 레거시 코드 제거 테스트 완료. 로그 파일: {LOG_FILE_PATH}")
        
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
