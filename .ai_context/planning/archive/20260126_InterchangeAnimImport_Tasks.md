# Active Task List

## 테스트 유형: Type B - 유저 주도 테스트 (User Action + Log)

---

## 테스트 리소스

**애니메이션 FBX:**
```
E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_HeadShakeThink_Loop-RBr-Enter.fbx
```

**베이스 스켈레톤 FBX:**
```
E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx
```

**예상 UE5 경로:**
- 애니메이션 목적지: `/Game/Omni/Characters/NPC/Human/Male/Animation/Neutral/Storytelling/Default`
- 스켈레톤 경로: `/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3`

---

## Tasks

### Phase 1: InterchangePipelineSettings 확장

- [x] **Task 1.1:** `InterchangePipelinePreset` Enum 추가
  - `interchangePipelineSettings.py`에 Enum 정의
  - SKELETON, SKELETAL_MESH, ANIMATION 값 포함

- [x] **Task 1.2:** `InterchangePipelineSettings` 생성자 수정
  - 선택적 `asset_type` 인자 지원 (기본값: None)
  - 기존 코드 호환성 유지

- [x] **Task 1.3:** `get_pipeline_paths(preset)` 메서드 구현
  - preset에 따라 파이프라인 경로 리스트 반환
  - 현재는 단일 기본 파이프라인만 사용 (리스트로 반환)

- [x] **Task 1.4:** `set_property_override(key, value)` 메서드 구현
  - 파이프라인 속성 오버라이드 저장
  - 임포트 시 적용될 속성들을 딕셔너리로 관리

- [x] **Task 1.5:** 파이프라인 설정 시 오버라이드 적용 로직 추가
  - `configure_for_animation()` 메서드에서 skeleton 오버라이드 처리

### Phase 2: 테스트 스크립트 생성

- [x] **Task 2.1:** `tests/ue5/test_animation_import.py` 작성
  - 로컬 실행용 스크립트 생성기
  - `test_skeleton_import.py` 패턴 참고
  - TemplateProcessor 사용하여 언리얼용 스크립트 생성
  - 테스트 리소스:
    - FBX: `E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_HeadShakeThink_Loop-RBr-Enter.fbx`
    - 스켈레톤: `/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3`

- [x] **Task 2.2:** 스크립트 생성기 실행 테스트
  - `uv run python tests/ue5/test_animation_import.py` 실행
  - `tests/ue5/test_inUnreal_animation_import.py` 생성 확인

### Phase 3: 유저 테스트 실행

- [x] **Task 3.1:** 언리얼 에디터에서 테스트 실행
  - 사용자가 생성된 스크립트를 언리얼에서 실행
  - 오류 로그 수집

- [x] **Task 3.2:** 결과 분석 및 수정
  - 오류 발생 시 원인 분석
  - 코드 수정 후 재테스트
  - 수정 사항: `common_skeletal_meshes_and_animations_properties`를 통한 스켈레톤 설정

### Phase 4: 완료

- [x] **Task 4.1:** 테스트 성공 확인
  - 애니메이션 임포트 정상 동작 확인
  - 임포트된 에셋 검증

---

## 예상 수정 파일 목록

1. `src/pyjallib/ue5/inUnreal/interchangePipelineSettings.py`
   - `InterchangePipelinePreset` Enum 추가
   - 생성자 수정
   - `get_pipeline_paths()` 메서드 추가
   - `set_property_override()` 메서드 추가
   - `configure_for_animation()` 메서드 수정

2. `tests/ue5/test_animation_import.py` (신규)
   - 로컬 실행용 스크립트 생성기

---

## Completion Summary (2026-01-26)

**Status:** All tasks completed successfully

**Key Fix:** Animation skeleton must be set via `common_skeletal_meshes_and_animations_properties.skeleton`, not `animation_pipeline.skeleton` (which doesn't exist in UE5)
