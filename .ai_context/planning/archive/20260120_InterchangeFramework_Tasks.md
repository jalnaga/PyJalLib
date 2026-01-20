# UE 5.7 Interchange Framework 임포터 모듈 Task List

**PRD**: `.ai_context/planning/active_prd.md`
**Primary Manual**: `.ai_context/manuals/new_module_creation.md`

---

## Phase 1: 베이스 인프라

### 1.1 Interchange 베이스 클래스
- [x] `interchangeImporterBase.py` 파일 생성
- [x] `BaseImporter` 상속 구조 설정
- [x] `InterchangeManager` 래핑 메서드 구현 (`_get_interchange_manager()`)
- [x] `InterchangeSourceData` 생성 유틸리티 (`_create_source_data()`)
- [x] `SoftObjectPath` 변환 유틸리티 (`_create_soft_object_path()`)
- [x] `ImportAssetParameters` 생성 헬퍼 (`_create_import_params()`)
- [x] 동기 임포트 실행 메서드 (`_execute_import()`)
- [x] 비동기 배치 임포트 인프라 (`_execute_batch_import_async()`)
- [x] 콜백 핸들러 (`_on_single_asset_done()`, `_on_batch_complete()`)
- [x] 배치 결과 수집 및 반환 형식 구현

### 1.2 파이프라인 설정 클래스
- [x] `interchangePipelineSettings.py` 파일 생성
- [x] 프리셋 타입 Enum 정의 (Skeleton, SkeletalMesh, Animation)
- [x] 기본 파이프라인 에셋 경로 상수 정의
- [x] Skeleton 프리셋 설정 메서드
- [x] SkeletalMesh 프리셋 설정 메서드
- [x] Animation 프리셋 설정 메서드
- [x] 런타임 파이프라인 속성 오버라이드 지원

---

## Phase 2: 개별 임포터 구현

### 2.1 스켈레톤 임포터
- [x] `interchangeSkeletonImporter.py` 파일 생성
- [x] `InterchangeImporterBase` 상속
- [x] `import_skeleton()` 단일 임포트 (동기)
- [x] `import_skeletons()` 배치 임포트 (비동기)
- [x] 스켈레톤 네이밍 로직 (기존 로직 재사용)
- [x] 소스 컨트롤 체크아웃/체크인 통합

### 2.2 스켈레탈 메시 임포터
- [x] `interchangeSkeletalMeshImporter.py` 파일 생성
- [x] `InterchangeImporterBase` 상속
- [x] `import_skeletal_mesh()` 단일 임포트 (동기)
- [x] `import_skeletal_meshes()` 배치 임포트 (비동기)
- [x] 스켈레톤 참조 검증 로직
- [x] 소스 컨트롤 체크아웃/체크인 통합

### 2.3 애니메이션 임포터
- [x] `interchangeAnimationImporter.py` 파일 생성
- [x] `InterchangeImporterBase` 상속
- [x] `import_animation()` 단일 임포트 (동기)
- [x] `import_animations()` 배치 임포트 (비동기)
- [x] 스켈레톤 참조 검증 로직
- [x] 소스 컨트롤 체크아웃/체크인 통합

---

## Phase 3: 패키지 통합

### 3.1 inUnreal 패키지 업데이트
- [x] `inUnreal/__init__.py` 업데이트 - Interchange 모듈 노출

---

## Phase 4: 템플릿 시스템 업데이트

### 4.1 Interchange 템플릿 파일 생성
- [x] `interchangeSkeletonImportTemplate.py` 생성
- [x] `interchangeSkeletalMeshImportTemplate.py` 생성
- [x] `interchangeAnimImportTemplate.py` 생성
- [x] `interchangeBatchAnimImportTemplate.py` 생성

### 4.2 템플릿 시스템 업데이트
- [x] `templates/__init__.py` 업데이트 - 새 템플릿 상수 및 매핑 추가
- [x] `templateProcessor.py` 업데이트 - Interchange 템플릿 처리 메서드 추가

---

## 검증

- [x] `uv run ruff check .` 린트 통과 (신규 Interchange 모듈들)
- [x] 모든 import 경로 확인

**참고:** 기존 레거시 코드에서 발생하는 린트 에러는 이번 태스크 범위에 포함되지 않음

---

## 추가 참고 사항

### UE5 테스트 관련 (별도 이슈)

`pyjallib/__init__.py`에서 외부 의존성 모듈들(`Logger` - loguru, `Perforce` - P4Python)을 import하고 있어 UE5 환경에서 테스트 시 에러 발생.

이 문제는 Interchange 모듈의 범위가 아니며, 별도 이슈로 해결 필요:
- `Logger`: loguru 의존성
- `Perforce`: P4Python 의존성

해결 방안:
1. `__init__.py`에서 try-except로 조건부 import
2. 또는 외부 의존성 있는 모듈들을 별도 서브패키지로 분리
