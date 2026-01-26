# Active Task List

## PRD Reference
`active_prd.md` - Interchange SkeletalMesh Import 실사용 테스트 및 오류 수정

---

## Tasks (Must-Have Only)

### Task 1: 테스트 스크립트 생성기 구현
- [ ] 1.1 `tests/ue5/test_skeletal_mesh_import.py` 파일 생성
- [ ] 1.2 `test_animation_import.py` 패턴 참고하여 구조 작성
- [ ] 1.3 테스트용 경로 상수 설정 (FBX 경로, 스켈레톤 경로, 목적지 경로)
- [ ] 1.4 템플릿 처리 로직 구현 (직접 파일 생성 방식)

### Task 2: 언리얼 에디터용 테스트 스크립트 생성
- [ ] 2.1 `test_skeletal_mesh_import.py` 실행하여 `test_inUnreal_skeletal_mesh_import.py` 생성
- [ ] 2.2 생성된 스크립트 내용 검증

### Task 3: 언리얼 에디터에서 테스트 실행
- [ ] 3.1 언리얼 에디터에서 생성된 스크립트 실행
- [ ] 3.2 오류 로그 수집 및 분석

### Task 4: 발견된 오류 수정
- [ ] 4.1 오류 원인 파악
- [ ] 4.2 `interchangeSkeletalMeshImporter.py` 또는 관련 코드 수정
- [ ] 4.3 수정 후 재테스트

---

## Progress Notes
(태스크 진행 시 메모 기록)
