# Task List: Facial Builder 모듈 아키텍처 리팩토링

## 참조
- **PRD:** `active_prd.md`
- **Primary Manual:** `.ai_context/manuals/new_module_creation.md`

---

## Phase 1: 패키지 뼈대 생성 (ARCH-01)

- [x] **TASK-01**: `src/facialBuilder/` 디렉토리 생성
- [x] **TASK-02**: `__init__.py` 작성 - FacialBuilder 클래스 노출

---

## Phase 2: FacialBuilder Facade 클래스 (ARCH-02, ARCH-03)

- [x] **TASK-03**: `facialBuilder.py` - FacialBuilder 클래스 뼈대 구현
  - `__init__`: 공유 상태(`_jsonData`) 초기화, 서브 모듈 인스턴스 생성
  - 서브 모듈들을 프로퍼티로 노출 (`data`, `bone`, `pose`, `animation`)

---

## Phase 3: FacialData 클래스 (CFG-01, CFG-02, CFG-03, ROOT-01)

- [x] **TASK-04**: `data.py` - FacialData 클래스 구현
  - `save_json()`: JSON 파일로 저장
  - `load_json(path)`: JSON 파일 로드
  - `reset()`: 기본값으로 초기화
  - `set_root_bone(name)`: 루트 본 설정

---

## Phase 4: FacialBone 클래스 (BONE-01, BONE-02, BONE-03, BONE-04)

- [x] **TASK-05**: `bone.py` - FacialBone 클래스 구현
  - `add_bone(name)`: 페이셜 본 추가
  - `remove_bone(name)`: 페이셜 본 제거
  - `save_init_transforms()`: 모든 본 초기 트랜스폼 저장
  - `apply_init_transforms()`: 모든 본 초기 트랜스폼 적용

---

## Phase 5: FacialPose 클래스 (POSE-01, POSE-02, POSE-03, POSE-04)

- [x] **TASK-06**: `pose.py` - FacialPose 클래스 구현
  - `add_pose(name)`: 포즈 추가 + 델타 트랜스폼 저장
  - `remove_pose(name)`: 포즈 제거
  - `update_pose(name)`: 포즈 업데이트
  - `rename_pose(old, new)`: 포즈 이름 변경

---

## Phase 6: FacialAnimation 클래스 (ANIM-01)

- [x] **TASK-07**: `animation.py` - FacialAnimation 클래스 구현
  - `blend_poses(weights_dict)`: 여러 포즈 가중치 블렌딩 적용

---

## Phase 7: 통합 및 검증

- [x] **TASK-08**: FacialBuilder에 서브 모듈 연결 완료 및 import 정리
- [x] **TASK-09**: 린트 검사 (`uv run ruff check .`) 통과 확인
  - 참고: 기존 `FacialPoseCalc.py`의 린트 오류는 Non-Goal로 제외

---

## Summary

| Phase | Task Count | 설명 |
|-------|------------|------|
| 1 | 2 | 패키지 뼈대 생성 |
| 2 | 1 | Facade 메인 클래스 |
| 3 | 1 | 설정 파일 관리 |
| 4 | 1 | 페이셜 본 관리 |
| 5 | 1 | 포즈 관리 |
| 6 | 1 | 애니메이션 |
| 7 | 2 | 통합 및 검증 |
| **Total** | **9** | - |

---

## Completion Note

**완료일:** 2024-12-17
**결과:** 모든 Must-Have 항목 구현 완료

