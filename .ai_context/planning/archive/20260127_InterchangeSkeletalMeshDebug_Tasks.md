# Active Task List

## PRD Reference
`active_prd.md` - Interchange SkeletalMesh Import 실사용 테스트 및 오류 수정

---

## Tasks (Must-Have Only)

### Task 1: 테스트 스크립트 생성기 구현
- [x] 1.1 `tests/ue5/test_skeletal_mesh_import.py` 파일 생성
- [x] 1.2 `test_animation_import.py` 패턴 참고하여 구조 작성
- [x] 1.3 테스트용 경로 상수 설정 (FBX 경로, 스켈레톤 경로, 목적지 경로)
- [x] 1.4 템플릿 처리 로직 구현 (직접 파일 생성 방식)

### Task 2: 언리얼 에디터용 테스트 스크립트 생성
- [x] 2.1 `test_skeletal_mesh_import.py` 실행하여 `test_inUnreal_skeletal_mesh_import.py` 생성
- [x] 2.2 생성된 스크립트 내용 검증

### Task 3: 언리얼 에디터에서 테스트 실행
- [x] 3.1 언리얼 에디터에서 생성된 스크립트 실행
- [x] 3.2 오류 로그 수집 및 분석

### Task 4: 발견된 오류 수정
- [x] 4.1 오류 원인 파악 (파이프라인 설정 미적용 문제)
- [x] 4.2 `interchangeSkeletalMeshImporter.py` 및 `interchangePipelineSettings.py` 수정
- [x] 4.3 수정 후 재테스트 (성공: 1개 오브젝트만 임포트됨)

---

## Progress Notes
- **2026-01-27**: Task 1, 2 완료
  - `test_skeletal_mesh_import.py` 생성기 구현 완료 (`test_animation_import.py` 패턴 기반)
  - `test_inUnreal_skeletal_mesh_import.py` 생성 완료 및 내용 검증 완료
  - 테스트 경로: FBX(`SK_Sh_Human_M_BlousonPolo_Upper.fbx`), 스켈레톤(`SKEL_Sh_Human_M_BaseSkeleton3`)
- **2026-01-27**: Task 3, 4 완료
  - 1차 테스트: loguru 의존성 오류 → 템플릿을 inUnreal 직접 import 방식으로 수정
  - 2차 테스트: 머티리얼/텍스쳐/피직스에셋 생성됨 → 파이프라인 설정 미적용 문제 발견
  - 수정 내용:
    - `interchangeSkeletalMeshImporter.py`: 파이프라인 로드 및 `configure_for_skeletal_mesh()` 호출 추가
    - `interchangePipelineSettings.py`: `configure_for_skeletal_mesh()` 완전 재구현 (스켈레톤 설정 포함)
  - 3차 테스트: 성공 (1개 오브젝트만 임포트)
  - 스켈레톤 본 경고: FBX 데이터와 기존 스켈레톤 간 차이 (의상 전용 본). 코드 버그 아님, 언리얼이 자동 처리
