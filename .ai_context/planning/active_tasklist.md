# Active Task List

## Feature: Import Asset Save & Changelist

**PRD:** `active_prd.md`
**Primary Manual:** `.ai_context/manuals/task_loop.md`

---

## Tasks

### Phase 1: InterchangePipelineSettings - 파이프라인 복원 기능

- [ ] **Task 1.1:** 원본 값 저장 변수 및 `_store_original_values()` 메서드 추가
  - `_originalValues: dict` 인스턴스 변수 추가
  - `_store_original_values(inPipeline)` 메서드 구현
  - 저장 대상: animation_pipeline.import_animations, material_pipeline.import_materials, texture_pipeline.import_textures, mesh_pipeline.create_physics_asset, common_skeletal_meshes_and_animations_properties (skeleton, import_only_animations)

- [ ] **Task 1.2:** `restore_pipeline()` 메서드 구현
  - 저장된 원본 값으로 파이프라인 속성 복원
  - 복원 후 `_originalValues` 초기화
  - 파이프라인 에셋은 저장하지 않음 (dirty 상태 방지)

- [ ] **Task 1.3:** `configure_for_*` 메서드에서 자동 원본 저장 호출
  - `configure_for_skeleton()` 시작 시 `_store_original_values()` 호출
  - `configure_for_skeletal_mesh()` 시작 시 `_store_original_values()` 호출
  - `configure_for_animation()` 시작 시 `_store_original_values()` 호출

### Phase 2: InterchangeImporterBase - 저장/체인지리스트 헬퍼

- [ ] **Task 2.1:** `_save_imported_assets()` 헬퍼 메서드 추가
  - `unreal.EditorAssetLibrary.save_loaded_assets()` 사용
  - `only_if_is_dirty=True` 옵션 적용
  - 저장 성공/실패 로깅

- [ ] **Task 2.2:** `_move_to_changelist()` 헬퍼 메서드 추가
  - 에셋 경로 리스트와 체인지리스트 ID를 인자로 받음
  - `unreal.SourceControl.execute_source_control_command("reopen", ...)` 사용
  - 파라미터: `["-c", changelist_id]`
  - 체인지리스트 ID가 None이면 작업 생략

### Phase 3: 임포터 메서드 수정

- [ ] **Task 3.1:** `InterchangeSkeletonImporter.import_skeleton()` 수정
  - 기존 `check_in_files()` 호출 제거
  - 임포트 후 `_pipelineSettings.restore_pipeline()` 호출
  - `_save_imported_assets()` 호출
  - `_move_to_changelist()` 호출 (inChangelistId 파라미터 추가)

- [ ] **Task 3.2:** `InterchangeSkeletonImporter.import_skeletons()` 수정
  - 배치 임포트 완료 후 파이프라인 복원
  - 저장 및 체인지리스트 할당 로직 추가

- [ ] **Task 3.3:** `InterchangeSkeletalMeshImporter.import_skeletal_mesh()` 수정
  - Task 3.1과 동일한 패턴 적용

- [ ] **Task 3.4:** `InterchangeSkeletalMeshImporter.import_skeletal_meshes()` 수정
  - Task 3.2와 동일한 패턴 적용

- [ ] **Task 3.5:** `InterchangeAnimationImporter.import_animation()` 수정
  - Task 3.1과 동일한 패턴 적용

- [ ] **Task 3.6:** `InterchangeAnimationImporter.import_animations()` 수정
  - Task 3.2와 동일한 패턴 적용

### Phase 4: 검증

- [ ] **Task 4.1:** 린터 검사 실행 (`uv run ruff check .`)
  - 모든 수정된 파일에 대해 린터 오류 없음 확인

- [ ] **Task 4.2:** 기존 테스트 호환성 확인
  - `uv run pytest` 실행
  - 테스트 실패 시 구현 코드 수정

---

## Summary

- **총 태스크 수:** 12개
- **구현 태스크:** 10개 (Phase 1-3)
- **검증 태스크:** 2개 (Phase 4)
