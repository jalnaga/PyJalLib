
# Archiving & Cleanup Manual

이 문서는 하나의 작업 사이클(PRD 작성 -> 구현 -> 테스트 통과)이 완전히 끝났을 때, 작업 내역을 보존하고 다음 작업을 준비하는 절차입니다.

---

## 1. Pre-Archiving Checklist (최종 점검)

아카이빙을 수행하기 전에 다음 항목을 반드시 확인하십시오.

1. **Task Completion:** `active_tasks.md`의 모든 항목이 `[x]`로 체크되어 있는가?
2. **Test Verification:** `uv run pytest`를 실행하여 모든 테스트가 통과하는지 마지막으로 확인했는가?
3. **User Approval:** 사용자가 결과물에 대해 최종 승인(Confirm)을 했는가?
4. **Linting:** `uv run ruff check .` 및 `format`을 수행하여 코드 스타일을 정리했는가?

---

## 2. Knowledge Consolidation (지식 자산화)

**이 단계가 가장 중요합니다.** 파일을 치우기 전에, 이번 작업에서 얻은 '새로운 지식'을 시스템에 반영하십시오.

- **Rule Update:** 작업 중 사용자가 지적한 코딩 스타일이나 규칙이 있다면 `manuals/` 폴더의 해당 문서를 업데이트하십시오.
- **Domain Knowledge:** 새로 알게 된 게임 공식, 데이터 구조, 비즈니스 로직이 있다면 `references/` 폴더의 문서에 추가하십시오.
    - *예: 데미지 계산식이 변경되었다면 `references/game_formulas.md` 업데이트*

---

## 3. File Archiving (파일 이동)

현재의 `active` 문서들을 `archive` 폴더로 이동하여 역사를 보존합니다.

### **Naming Convention**

파일 이름은 **날짜**와 **기능명**을 조합하여 유니크하게 만듭니다.

- **Format:** `YYYYMMDD_{FeatureName}_{Type}.md`
- **Example:**
    - `20240520_StatSystem_PRD.md`
    - `20240520_StatSystem_Tasks.md`

### **Action**

다음 명령을 수행(또는 파일 시스템 조작)하여 파일을 이동하십시오.

1. `.ai_context/planning/active_prd.md`
    → `.ai_context/planning/archive/YYYYMMDD_{FeatureName}_PRD.md`
2. `.ai_context/planning/active_tasks.md`
    → `.ai_context/planning/archive/YYYYMMDD_{FeatureName}_Tasks.md`

---

## 4. Reset & Ready (다음 작업 준비)

다음 작업을 위해 작업 공간을 초기화합니다.

1. **Clear Active Files:**
    - `.ai_context/planning/active_prd.md`를 내용을 비우거나 기본 템플릿 상태로 만드십시오.
    - `.ai_context/planning/active_tasks.md`를 내용을 비우십시오.
2. **Report:**
    - 사용자에게 아카이빙 완료를 보고하십시오.
    - > "작업이 완료되어 문서(PRD, Tasks)를 아카이빙했습니다. 참고 문헌(References) 업데이트도 완료했습니다. 다음 지시를 내려주세요."