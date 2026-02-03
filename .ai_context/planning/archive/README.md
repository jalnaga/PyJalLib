# Archive 폴더

이 폴더는 완료된 기능의 PRD와 Task List를 아카이빙하는 공간입니다.

## 아카이빙 규칙

### 파일명 형식

```
YYYYMMDD_FeatureName_PRD.md
YYYYMMDD_FeatureName_Tasks.md
```

**예시:**
```
20250121_InterchangeReimportFix_PRD.md
20250121_InterchangeReimportFix_Tasks.md
```

### 아카이빙 시점

기능 개발이 완료되고 다음 조건을 모두 만족할 때 아카이빙합니다:

- [ ] 모든 태스크가 완료됨 (`[x]`)
- [ ] 모든 테스트가 통과됨 (`uv run pytest`)
- [ ] 코드 품질 검사 통과 (`uv run ruff check .`)
- [ ] 필요한 문서 업데이트 완료
- [ ] 사용자 최종 승인 완료

### 아카이빙 절차

1. **날짜 확인:** 완료 날짜를 YYYYMMDD 형식으로 준비
2. **파일 이동:**
   - `active_prd.md` → `archive/YYYYMMDD_FeatureName_PRD.md`
   - `active_tasklist.md` → `archive/YYYYMMDD_FeatureName_Tasks.md`
3. **활성 파일 초기화:**
   - `active_prd.md` 비우기 (템플릿 유지)
   - `active_tasklist.md` 비우기 (템플릿 유지)
4. **지식 통합 (선택):**
   - 새로운 패턴 발견 시 `.ai_context/references/` 업데이트
   - 워크플로우 개선 사항 `.ai_context/manuals/` 반영

### 아카이빙된 문서의 용도

- **히스토리 추적:** 과거 기능 개발 과정 참고
- **의사결정 기록:** 왜 그렇게 구현했는지 확인
- **패턴 재사용:** 유사한 기능 개발 시 참조
- **온보딩:** 신규 팀원 학습 자료

### 주의사항

- 아카이빙 후 active 파일은 반드시 비우기 (다음 기능과 혼동 방지)
- 날짜는 기능 완료 날짜 기준 (시작 날짜 아님)
- Feature Name은 간결하고 명확하게 (CamelCase 또는 snake_case)

## 예제

### 정상적인 아카이브 파일 목록

```
archive/
├── README.md (이 파일)
├── 20250115_LoggerRefactoring_PRD.md
├── 20250115_LoggerRefactoring_Tasks.md
├── 20250121_InterchangeReimportFix_PRD.md
└── 20250121_InterchangeReimportFix_Tasks.md
```

### 파일 내용 예시

**20250121_InterchangeReimportFix_PRD.md:**
- 원본 `active_prd.md` 내용 그대로 보존
- 날짜와 기능명만 파일명에 반영

**20250121_InterchangeReimportFix_Tasks.md:**
- 모든 태스크가 `[x]` 완료 상태
- 작업 순서와 결과 그대로 보존
