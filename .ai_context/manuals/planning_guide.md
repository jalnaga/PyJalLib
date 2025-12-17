# Planning & Decomposition Manual

이 문서는 사용자의 **모호한 요구사항(회의록, 대화, 아이디어)**을 분석하여 **실행 가능한 계획(PRD & Tasks)**으로 변환하는 표준 절차입니다.

---

## 1. Input Analysis Protocol (입력 분석)

사용자가 회의록이나 줄글 형태의 요구사항을 입력하면, 바로 `active_prd.md`를 작성하지 말고 먼저 **"의도(Intent)"**와 **"우선순위(Priority)"**를 분석하십시오.

### **분석 원칙 (The 4-Tier Priority)**

모든 요구사항을 4단계로 철저히 분리하여 PRD에 배치해야 합니다.

1. **Must-Have (P0 - 필수):**
    - 이번 작업의 핵심 목표. 이것이 없으면 기능이 동작하지 않거나 의미가 없음.
    - *Action:* 즉시 `active_tasklist.md`로 분해되어 구현됨.
2. **Should-Have (P1 - 권장):**
    - 중요한 기능이지만, 시간 제약이 있거나 기술적 난이도가 높을 경우 다음 스프린트로 미룰 수 있음.
    - *Action:* PRD에는 기록하되, 초기 태스크 리스트에는 포함하지 않음 (유저 요청 시 포함).
3. **Nice-to-Have (P2 - 부가):**
    - 있으면 좋고 없어도 그만인 기능 (UI 폴리싱, 사소한 편의 기능).
    - *Action:* 핵심 기능이 완벽하게 돌아간 후에만 고려함.
4. **Non-Goal (Out of Scope):**
    - 이번 작업에서는 **절대** 건드리지 말아야 할 것.
    - AI가 자의적으로 범위를 확장하거나 오버 엔지니어링 하는 것을 방지하는 경계선.

---

## 2. Writing `active_prd.md`

분석된 내용을 바탕으로 `.ai_context/planning/active_prd.md`를 작성하십시오.

### **PRD 필수 섹션**

PRD에는 반드시 다음 섹션들이 포함되어야 합니다:

- **Title:** 작업의 핵심을 한 줄로 요약
- **Background & Intent:** "왜 이 기능을 만드는가?" (회의록의 맥락 반영)
- **Primary Manual (필수):** 이 작업을 수행할 때 참조할 매뉴얼 경로
- **Scope & Prioritization:**
    - `[Must-Have]`: 구현 대상. (테스트 코드 필수)
    - `[Should-Have]`: 중요하지만 2순위.
    - `[Nice-to-Have]`: 여유가 될 때만 고려하는 보너스 요소.
    - `[Non-Goal]`: 명시적 제외 대상.

### **Primary Manual 선택 절차**

1. **매뉴얼 목록 확인:** `.ai_context/manuals/` 폴더의 파일 목록을 확인
2. **적합한 매뉴얼 선택:** 작업 성격에 맞는 매뉴얼을 선택하여 PRD에 기재
3. **사용자 승인:** PRD 승인 시 Primary Manual 선택도 함께 확인받음

**적합한 매뉴얼이 없는 경우:**

```
[Manual Required]
이 작업에 적합한 매뉴얼이 없습니다.
작업 성격: (작업 유형 설명)

새 매뉴얼을 생성해주시거나, 기존 매뉴얼 중 사용할 것을 지정해주세요.
```

**STOP: 매뉴얼이 지정될 때까지 PRD 작성을 진행하지 마십시오.**

---

## 3. Creating `active_tasklist.md` (Extreme Decomposition)

작성된 PRD의 **`Must-Have` 항목만**을 대상으로, 실패할 수 없을 만큼 작은 단위로 쪼개어 `.ai_context/planning/active_tasklist.md`를 작성하십시오.

### **Decomposition Rules**

1. **Atomic Unit:** 하나의 태스크는 코드 50줄 내외, 혹은 함수 1~2개 분량이어야 합니다.
2. **Code-First Approach:** 기능 구현 태스크를 먼저 배치하고, 그 뒤에 **"해당 기능의 테스트 작성"** 태스크를 배치합니다.
3. **Checkbox Format:** 모든 태스크는 `- [ ]` 형식으로 작성하고, 완료 시 `- [x]`로 업데이트합니다.

---

## 4. Verification & Approval (승인 절차)

PRD 작성 전 다음 체크리스트를 확인하십시오:

- [ ] Primary Manual이 지정되어 있는가?
- [ ] Must-Have / Should-Have / Nice-to-Have / Non-Goal이 명확히 분리되어 있는가?
- [ ] Background & Intent에 "왜"가 기록되어 있는가?

**모든 항목이 충족되면** 사용자에게 승인을 요청하십시오.

**STOP: 사용자의 승인(`진행해`, `OK`)이 있어야만 Task List 작성 및 실행 단계로 넘어갑니다.**
