# Active PRD

## Title
InterchangeAnimationImporter 동작을 위한 InterchangePipelineSettings 확장

---

## Background & Intent

**왜 이 작업을 하는가?**

`interchangeAnimationImporter.py`는 이미 작성되어 있지만, 필요한 인터페이스(`InterchangePipelinePreset`, `get_pipeline_paths()`, `set_property_override()`)가 `InterchangePipelineSettings` 클래스에 구현되어 있지 않아 동작하지 않습니다.

스켈레톤 임포터(`interchangeSkeletonImporter.py`)가 성공적으로 완료된 후, 동일한 패턴으로 애니메이션 임포터가 작동하도록 해야 합니다.

**현재 상태:**
- `interchangeAnimationImporter.py`는 완성된 코드 구조를 가지고 있음
- 하지만 필요한 `InterchangePipelineSettings` 메서드/클래스가 없음
- 테스트 코드가 없음

---

## Primary Manual
`.ai_context/manuals/test_process.md`

---

## Technical Decisions & References

### 적용할 표준 패턴
- **UE5 Path Rules:** 경로 변환 시 `pathUtils` 모듈 사용 필수 (`../references/ue5/path_rules.md`)
- **Interchange Pipeline:** 파이프라인 설정 방법 (`../references/ue5/interchange_pipeline.md`)

### 필요한 구현 사항

**1. `InterchangePipelinePreset` Enum 추가:**
```python
from enum import Enum

class InterchangePipelinePreset(Enum):
    SKELETON = "skeleton"
    SKELETAL_MESH = "skeletal_mesh"
    ANIMATION = "animation"
```

**2. `InterchangePipelineSettings` 확장:**
- 생성자에서 에셋 타입 인자 지원
- `get_pipeline_paths(preset)` 메서드 추가
- `set_property_override(key, value)` 메서드 추가

### 테스트 워크플로우 (2단계 방식)

**Step 1: 로컬에서 스크립트 생성**
```powershell
cd "J:\My Drive\Programming\Python\PyJalLib-interchange-anim-debug"
uv run python tests/ue5/test_animation_import.py
```

**Step 2: 언리얼 에디터에서 실행**
```python
exec(open(r"J:\My Drive\Programming\Python\PyJalLib-interchange-anim-debug\tests\ue5\test_inUnreal_animation_import.py").read())
```

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)
1. **`InterchangePipelinePreset` Enum 추가**
   - `interchangePipelineSettings.py`에 Enum 정의
   - SKELETON, SKELETAL_MESH, ANIMATION 값 포함

2. **`InterchangePipelineSettings` 클래스 확장**
   - 생성자에서 선택적 에셋 타입 인자 지원
   - `get_pipeline_paths(preset)` 메서드 구현
   - `set_property_override(key, value)` 메서드 구현

3. **애니메이션 임포트 테스트 스크립트 생성**
   - `tests/ue5/test_animation_import.py`: 로컬 실행용 스크립트 생성기
   - `tests/ue5/test_inUnreal_animation_import.py`: 언리얼 에디터 실행용 (생성됨)

### [Should-Have] (P1 - 권장)
- 기존 `interchangeSkeletonImporter.py`도 새 인터페이스 사용하도록 업데이트

### [Nice-to-Have] (P2 - 부가)
- 배치 애니메이션 임포트 테스트

### [Non-Goal] (Out of Scope)
- 새로운 임포터 타입 추가
- 리팩터링 또는 구조 변경 (기존 인터페이스 유지)
- 스켈레톤 임포터 수정 (이미 동작함)

---

## Notes
- 이 작업은 현재 브랜치(`feature/interchange-anim-debug`)에서 직접 수행합니다.
- 실제 언리얼 환경에서의 테스트이므로 사용자의 협력이 필요합니다.

---

## Completion Notes (2026-01-26)

### 해결된 핵심 문제
- `animation_pipeline.skeleton` 속성이 UE5에 존재하지 않음
- 해결: `common_skeletal_meshes_and_animations_properties.skeleton` 사용 (UE5.7 공식 문서 참조)

### 참조 문서
- https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericCommonSkeletalMeshesAndAnimationsProperties?application_version=5.7
