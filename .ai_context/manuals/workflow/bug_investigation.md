# Bug Investigation Test Workflow

개발 완료된 기능을 실제 사용하면서 발견된 버그나 문제를 조사하고 수정하는 워크플로우입니다.

---

## 진입 조건

- **개발 완료된 기능**의 실사용 중 발견된 오류
- 기능상의 문제 파악이 필요한 경우
- 프로덕션/실사용 환경에서 발견된 버그 재현 및 수정

**Note:** 새 기능 개발 중 테스트는 이 워크플로우가 아닌 `.ai_context/manuals/workflow/new_feature.md`를 따릅니다.

**Note:** 이 워크플로우는 워크트리 생성 없이 현재 브랜치에서 직접 작업합니다.

---

## 워크플로우

### STEP 1: Check PRD/Task Status

`.ai_context/planning/active_prd.md`와 `active_tasklist.md`를 확인합니다.

| 상태 | 행동 |
|:-----|:-----|
| 파일에 내용이 있음 | STEP 4로 건너뛰어 태스크 실행 계속 |
| 파일이 비어 있음 | STEP 2로 진행하여 버그 조사 시작 |

---

### STEP 2: Write PRD & Wait for Approval

**Manual:** `.ai_context/manuals/planning_guide.md`

1. 사용자의 문제 상황을 분석하여 `active_prd.md` 작성
2. 다음 정보를 포함:
   - **문제 현상:** 무엇이 잘못되었는가?
   - **재현 조건:** 어떤 상황에서 발생하는가?
   - **기대 동작:** 원래 어떻게 동작해야 하는가?
3. 조사/수정 사항을 **Must-Have / Should-Have / Nice-to-Have / Non-Goal**로 분류
4. **Primary Manual:** `.ai_context/manuals/test_process.md` (고정)
5. **STOP: 사용자 승인 요청**

```
[Planning Complete]
버그 조사 PRD를 작성했습니다. 다음 우선순위 분류를 확인해주세요:

- **문제 현상:** (summary)
- **Must-Have:** (summary)
- **Should-Have:** (summary)
- **Nice-to-Have:** (summary)
- **Non-Goal:** (summary)
- **Primary Manual:** `.ai_context/manuals/test_process.md`

승인하시면 Task List를 작성하고 조사/수정을 시작하겠습니다.
```

**사용자가 승인할 때까지 코드 작성 금지.**

---

### STEP 3: Create Task List & Wait for Approval

**Manual:** `.ai_context/manuals/planning_guide.md` (Section 3)

1. PRD의 **Must-Have 항목만** `active_tasklist.md`로 분해
2. 일반적인 태스크 순서:
   - 버그 재현 테스트 작성
   - 근본 원인 분석
   - 구현 코드 수정
   - 테스트 검증
3. **STOP: 사용자 승인 요청**

```
[Task List Complete]
태스크 리스트를 작성했습니다. 확인해주세요:

- **총 태스크 수:** (N)개
- **조사 태스크:** (summary)
- **수정 태스크:** (summary)
- **테스트 태스크:** (summary)

승인하시면 태스크 실행을 시작하겠습니다.
```

**사용자가 승인할 때까지 태스크 실행 금지.**

---

### STEP 4: Execute Tasks

**Manual:** `.ai_context/manuals/task_loop.md`

1. 태스크를 하나씩 실행 (Task Loop 매뉴얼 준수)
2. 각 태스크 완료 시 `active_tasklist.md`를 `[x]`로 업데이트
3. 태스크마다 진행 상황 보고

**버그 수정 시 주의사항:**
- 테스트 코드가 실패해야 버그가 재현된 것
- 구현 코드 수정 후 테스트 통과 확인
- 테스트 코드 자체는 수정하지 않음 (버그 재현 목적)

---

### STEP 5: Verify All Tasks Complete

아카이빙 전에 다음을 확인합니다:

- [ ] `active_tasklist.md`의 모든 항목이 `[x]`로 체크됨

모든 검증 통과 시 STEP 6으로 진행.

---

### STEP 6: Archive

**Manual:** `.ai_context/manuals/archiving_process.md`

1. **Knowledge Consolidation:** `manuals/` 또는 `references/`에 새로운 지식 반영
2. **파일 아카이빙:**
   - `active_prd.md` → `archive/YYYYMMDD_{BugName}_PRD.md`
   - `active_tasklist.md` → `archive/YYYYMMDD_{BugName}_Tasks.md`
   - Active 파일 내용 비움

3. **완료 보고:**

```
[Bug Investigation Complete]
버그 조사/수정이 완료되었습니다.
- 원인: (root cause)
- 수정 내용: (fix description)
- 문서: archive/YYYYMMDD_{BugName}_*.md
```

---

## Appendix: 디버깅 프로토콜

테스트가 반복 실패하면:

1. 실패 로그 분석
2. 근본 원인 파악 (환경? 로직? 의존성?)
3. 수정 후 재테스트
4. **3회 이상 실패 시 사용자에게 보고**
