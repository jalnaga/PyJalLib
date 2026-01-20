# New Feature Development Workflow

새로운 기능을 개발할 때 따라야 하는 표준 워크플로우입니다.

---

## 전제 조건

- **워크트리가 이미 생성된 상태**여야 합니다.
- 워크트리가 없으면 먼저 `manuals/workflow/worktree_creation.md`를 따르십시오.
- **대규모 버그 수정**도 이 워크플로우로 취급합니다. (규모 기준은 `AGENTS.md` 참고)

---

## 워크플로우

### STEP 1: Check PRD/Task Status

`.ai_context/planning/active_prd.md`와 `active_tasklist.md`를 확인합니다.

| 상태 | 행동 |
|:-----|:-----|
| 파일에 내용이 있음 | STEP 4로 건너뛰어 태스크 실행 계속 |
| 파일이 비어 있음 | STEP 2로 진행하여 새 기능 시작 |

---

### STEP 2: Write PRD & Wait for Approval

**Manual:** `.ai_context/manuals/planning_guide.md`

1. 사용자의 요구사항을 분석하여 `active_prd.md` 작성
2. 모든 요구사항을 **Must-Have / Should-Have / Nice-to-Have / Non-Goal**로 분류
3. **Primary Manual** 지정: 구현 시 참조할 매뉴얼 경로 명시
4. **STOP: 사용자 승인 요청**

```
[Planning Complete]
PRD를 작성했습니다. 다음 우선순위 분류를 확인해주세요:

- **Must-Have:** (summary)
- **Should-Have:** (summary)
- **Nice-to-Have:** (summary)
- **Non-Goal:** (summary)
- **Primary Manual:** (selected manual path)

승인하시면 Task List를 작성하고 구현을 시작하겠습니다.
```

**사용자가 승인할 때까지 코드 작성 금지.**

---

### STEP 3: Create Task List & Wait for Approval

**Manual:** `.ai_context/manuals/planning_guide.md` (Section 3)

1. PRD의 **Must-Have 항목만** `active_tasklist.md`로 분해
2. **Code-First:** 구현 태스크 → 테스트 태스크 순서로 배치
3. **STOP: 사용자 승인 요청**

```
[Task List Complete]
태스크 리스트를 작성했습니다. 확인해주세요:

- **총 태스크 수:** (N)개
- **구현 태스크:** (summary)
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

---

### STEP 5: Verify All Tasks Complete

아카이빙 전에 다음을 확인합니다:

- [ ] `active_tasklist.md`의 모든 항목이 `[x]`로 체크됨
- [ ] `uv run pytest` 통과
- [ ] `uv run ruff check .` 통과

모든 검증 통과 시 STEP 6으로 진행.

---

### STEP 6: Archive

**Manual:** `.ai_context/manuals/archiving_process.md`

1. **Knowledge Consolidation:** `manuals/` 또는 `references/`에 새로운 지식 반영
2. **파일 아카이빙:**
   - `active_prd.md` → `archive/YYYYMMDD_{FeatureName}_PRD.md`
   - `active_tasklist.md` → `archive/YYYYMMDD_{FeatureName}_Tasks.md`
   - Active 파일 내용 비움

3. **완료 보고:**

```
[Feature Complete]
기능 개발이 완료되었습니다.
- 문서: archive/YYYYMMDD_{FeatureName}_*.md
```
