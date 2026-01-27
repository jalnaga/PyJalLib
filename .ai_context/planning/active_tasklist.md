# Active Task List

## PRD Reference
`active_prd.md` - InterchangeBatchAnimImportTemplate Import 방식 수정

---

## Tasks

### Task 1: 템플릿 import 방식 수정
- [ ] 1.1 `interchangeBatchAnimImportTemplate.py` 수정
  - sys.path에 inUnreal 디렉토리 직접 추가
  - import 문을 `from interchangeAnimationImporter import InterchangeAnimationImporter`로 변경

### Task 2: async 배치 임포트 메서드 구현
- [ ] 2.1 `InterchangeAnimationImporter.import_animations_async()` 메서드 추가
  - `scripted_import_asset_async` 사용하여 비동기 임포트 구현
  - 파이프라인 설정 및 스켈레톤 오버라이드 적용
  - 기존 `import_animations()` 동기 메서드 유지

### Task 3: 템플릿에서 async 메서드 호출
- [ ] 3.1 `interchangeBatchAnimImportTemplate.py`에서 `import_animations_async()` 호출하도록 수정

### Task 4: 테스트 스크립트 생성
- [ ] 4.1 `tests/ue5/test_batch_animation_import.py` 생성
  - TemplateProcessor를 사용하여 언리얼 에디터용 스크립트 생성
  - PRD에 명시된 테스트 데이터 사용

### Task 5: 언리얼 에디터 테스트
- [ ] 5.1 로컬에서 테스트 스크립트 실행하여 `test_inUnreal_batch_animation_import.py` 생성
- [ ] 5.2 언리얼 에디터에서 생성된 스크립트 실행
- [ ] 5.3 3개 애니메이션 파일이 모두 정상 임포트되는지 확인

---

## Progress Log
(태스크 완료 시 기록)
