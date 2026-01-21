# Active PRD

## Bug Investigation: Content 경로 검증 실패 - 절대 경로 자동 변환 누락

### 문제 현상

`InterchangeAnimationImporter.import_animation()`에서 `inDestinationPath` 파라미터가 절대 경로 형식으로 전달될 때 "유효하지 않은 Content 경로 형식" 오류 발생.

**오류 메시지:**
```
[pathUtils] 유효하지 않은 Content 경로 형식: D:/root/Omni/Content/Omni/Characters/NPC/Human/NonBinary/Animation/Neutral/Gesture/Default/A_Nc_Human_N_Neutral_Gesture_Default_GetConsolation
```

### 재현 조건

1. `templateProcessor.py`로 애니메이션 임포트 스크립트 생성
2. `inDestinationPath`에 절대 경로 형식 전달 (예: `D:/root/Omni/Content/Omni/Characters/...`)
3. 생성된 스크립트를 언리얼에서 실행

### 기대 동작

- 절대 경로가 Content 디렉토리 내부 경로인 경우, 자동으로 `/Game/...` 형식으로 변환
- 변환 불가능한 경우에만 오류 발생

### 근본 원인

- `interchangeAnimationImporter.py`의 `import_animation()` 메서드가 절대 경로를 Content 경로로 변환하지 않고 바로 검증
- `pathUtils.py`에 `absolute_path_to_content_path()` 함수가 있지만 활용되지 않음

---

## 요구사항 분류

### Must-Have
- [ ] `import_animation()`에서 `inDestinationPath`가 절대 경로일 경우 자동 변환 로직 추가
- [ ] 스켈레톤 경로(`inSkeletonPath`)도 동일하게 처리

### Should-Have
- [ ] 배치 임포트 메서드(`import_animations`)에도 동일 로직 적용
- [ ] 다른 Importer 클래스들(SkeletonImporter, SkeletalMeshImporter)에도 일관된 처리 추가

### Nice-to-Have
- [ ] 경로 변환 시 로그 메시지 추가 (디버깅 용이성)

### Non-Goal
- 경로 형식 자체의 재설계
- 템플릿 시스템 수정

---

## Primary Manual
`.ai_context/manuals/test_process.md`
