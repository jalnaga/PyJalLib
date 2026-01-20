# Active Task List

## PRD Reference
`active_prd.md` - Interchange Framework 모듈 외부 의존성 제거 및 경로 입력 단순화

---

## Tasks

### Phase 1: 기반 작업

- [x] **Task 1.1**: `pathUtils.py` 신규 생성
  - 파일: `inUnreal/pathUtils.py`
  - 내용: `absolute_path_to_content_path()`, `ensure_directory_exists()`, `checkout_or_add_file()` 함수 구현
  - 의존성: 파이썬 표준 라이브러리 + unreal 모듈만 사용
  - 추가 구현: `get_asset_name_from_path()`, `get_directory_from_path()`, `validate_fbx_file()`, `validate_content_path()`

- [x] **Task 1.2**: `interchangePipelineSettings.py` 외부 의존성 확인 및 정리
  - 파일: `inUnreal/interchangePipelineSettings.py`
  - 내용: `..logger` 의존성 제거 완료, `unreal.log_warning`/`unreal.log_error` 사용

### Phase 2: Interchange 임포터 리팩토링

- [x] **Task 2.1**: `interchangeImporterBase.py` 리팩토링
  - 파일: `inUnreal/interchangeImporterBase.py`
  - 내용: `baseImporter` 상속 제거, `pathUtils` 사용, 새 인터페이스 적용
  - 의존성: 파이썬 표준 라이브러리 + unreal + pathUtils만 사용
  - 추가: `pathUtils.ensure_directory_exists`에서 `EditorAssetLibrary.does_directory_exist` 사용하도록 수정

- [x] **Task 2.2**: `interchangeSkeletonImporter.py` 리팩토링
  - 파일: `inUnreal/interchangeSkeletonImporter.py`
  - 내용: 새 인터페이스 (`inFbxPath`, `inDestinationPath`, `inAssetName`)
  - 완료: 외부 의존성 제거 (ue5_logger, self.naming), pathUtils 사용, 새 인터페이스 적용

- [x] **Task 2.3**: `interchangeSkeletalMeshImporter.py` 리팩토링
  - 파일: `inUnreal/interchangeSkeletalMeshImporter.py`
  - 내용: 새 인터페이스 (`inFbxPath`, `inDestinationPath`, `inSkeletonPath`, `inAssetName`)
  - 완료: 외부 의존성 제거 (ue5_logger, 레거시 경로 변환), pathUtils 사용, 새 인터페이스 적용

- [x] **Task 2.4**: `interchangeAnimationImporter.py` 리팩토링
  - 파일: `inUnreal/interchangeAnimationImporter.py`
  - 내용: 새 인터페이스 (`inFbxPath`, `inDestinationPath`, `inSkeletonPath`, `inAssetName`)
  - 완료: 외부 의존성 제거 (ue5_logger, 레거시 경로 변환), pathUtils 사용, 새 인터페이스 적용

### Phase 3: 레거시 코드 제거

- [x] **Task 3.1**: 레거시 임포터 파일 삭제
  - 삭제 완료:
    - `inUnreal/baseImporter.py`
    - `inUnreal/importerSettings.py`
    - `inUnreal/skeletonImporter.py`
    - `inUnreal/skeletalMeshImporter.py`
    - `inUnreal/animationImporter.py`

- [x] **Task 3.2**: `inUnreal/__init__.py` 업데이트
  - 파일: `inUnreal/__init__.py`
  - 완료: 레거시 임포터 export 제거, `pathUtils` export 추가

- [x] **Task 3.3**: 레거시 템플릿 파일 삭제
  - 삭제 완료:
    - `templates/skeletonImportTemplate.py`
    - `templates/skeletalMeshImportTemplate.py`
    - `templates/animImportTemplate.py`
    - `templates/batchAnimImportTemplate.py`
  - `templates/__init__.py` 업데이트 완료

### Phase 4: 템플릿 및 프로세서 업데이트

- [ ] **Task 4.1**: Interchange 템플릿 업데이트
  - 파일:
    - `templates/interchangeSkeletonImportTemplate.py`
    - `templates/interchangeSkeletalMeshImportTemplate.py`
    - `templates/interchangeAnimImportTemplate.py`
    - `templates/interchangeBatchAnimImportTemplate.py`
  - 내용: 새 인터페이스에 맞게 수정

- [ ] **Task 4.2**: `templates/__init__.py` 업데이트
  - 파일: `templates/__init__.py`
  - 내용: 레거시 템플릿 상수 및 매핑 제거

- [ ] **Task 4.3**: `templateProcessor.py` 업데이트
  - 파일: `templateProcessor.py`
  - 내용: 레거시 템플릿 관련 메서드 제거, Interchange 템플릿 메서드 수정

---

## Progress Summary

- **Total Tasks**: 12
- **Completed**: 9
- **Remaining**: 3
