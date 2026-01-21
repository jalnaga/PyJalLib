# Active Task List

## Bug Fix: Content 경로 절대 경로 자동 변환

### Tasks

- [x] **Task 1**: `pathUtils.py`에 경로 타입 판별 및 자동 변환 헬퍼 함수 추가
  - `is_content_path()`: Content 경로 형식 여부 확인
  - `normalize_content_path()`: 절대 경로 또는 Content 경로를 `/Game/...` 형식으로 정규화

- [x] **Task 2**: `interchangeAnimationImporter.py` - `import_animation()` 수정
  - `inDestinationPath` 절대 경로 자동 변환
  - `inSkeletonPath` 절대 경로 자동 변환

- [x] **Task 3**: `interchangeAnimationImporter.py` - `import_animations()` 수정
  - 배치 메서드는 내부적으로 `import_animation()` 호출 → 자동 적용됨

- [x] **Task 4**: 다른 Importer 클래스 일관성 수정
  - `interchangeSkeletonImporter.py` - `import_skeleton()` 수정
  - `interchangeSkeletalMeshImporter.py` - `import_skeletal_mesh()` 수정

---

## 진행 상황

| Task | 상태 | 비고 |
|:-----|:-----|:-----|
| Task 1 | 완료 | `is_content_path()`, `normalize_content_path()` 추가 |
| Task 2 | 완료 | 단일 임포트 메서드 수정 |
| Task 3 | 완료 | 배치 메서드는 자동 적용 |
| Task 4 | 완료 | Skeleton, SkeletalMesh Importer 수정 |
