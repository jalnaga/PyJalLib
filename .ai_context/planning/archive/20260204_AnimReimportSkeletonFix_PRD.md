# Active PRD

## Title
애니메이션 재임포트 시 스켈레톤 변경 불가 버그 수정

---

## Background & Intent

### 왜 이 수정이 필요한가?
`LegacyAnimationImporter`를 사용하여 이미 존재하는 애니메이션 에셋을 다른 스켈레톤으로 재임포트할 때, 스켈레톤이 변경되지 않는 버그가 발생합니다.

### 문제 현상
- 애니메이션 A가 스켈레톤 X를 참조하여 이미 임포트되어 있음
- 동일한 애니메이션 A를 스켈레톤 Y로 재임포트 시도
- **결과**: 애니메이션 A는 여전히 스켈레톤 X를 참조 (변경되지 않음)

### 기대 동작
재임포트 시 새로 지정한 스켈레톤(Y)으로 애니메이션이 연결되어야 함

---

## Technical Decisions

### 근본 원인
- `AnimSequence.skeleton` 속성은 Python API에서 **read-only**
- 재임포트(`replace_existing=True`) 시에도 기존 스켈레톤이 유지됨
- 상세 내용: `.ai_context/references/ue5/animsequence_skeleton_change.md`

### 해결 방안

| 방안 | 상태 | 비고 |
|:-----|:-----|:-----|
| B. set_editor_property | ❌ 실패 | read-only |
| C. FbxImportUI 옵션 | ❌ 실패 | 단독 효과 없음 |
| **D. Consolidate + Rename** | ✅ 채택 | 참조 무결성 유지 |

### 선택한 해결 방안: 방안 D

**구현 흐름:**
1. 임시 이름으로 새 에셋 임포트 (새 스켈레톤)
2. `consolidate_assets()`로 참조 리다이렉트
3. Redirector 삭제
4. `rename_asset()`으로 이름 복원

**상세 구현 가이드:** `.ai_context/references/ue5/animsequence_skeleton_change.md`

---

## 참조 문서
- `.ai_context/references/ue5/animsequence_skeleton_change.md` ← **핵심 레퍼런스**
- `.ai_context/references/ue5/path_rules.md`
- [EditorAssetLibrary Python API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorAssetLibrary)

---

## Primary Manual
`.ai_context/manuals/test_process.md`

---

## Scope & Prioritization

### Must-Have (P0)
1. **Consolidate + Rename 방식으로 스켈레톤 변경 구현**
2. 재임포트 시 새로운 스켈레톤으로 정상 변경 확인
3. 기존 에셋 참조가 유지되는지 검증

### Should-Have (P1)
1. 스켈레톤 변경 성공/실패 시 로그 메시지 출력
2. 스켈레톤 동일 시 기존 방식(일반 재임포트) 유지

### Non-Goal
- 배치 임포트 `import_animations()` 수정 (단일 임포트 검증 후)
- Redirector 정리 (Fixup Redirects)
- 다른 임포터에 동일 기능 적용

---

## 완료 일자
2026-02-04
