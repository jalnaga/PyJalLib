# Worktree Merge Workflow

기능 개발이 완료된 워크트리를 메인 브랜치에 병합하고 정리하는 워크플로우입니다.

---

## 진입 조건

- 기능 개발이 완료된 상태
- `new_feature.md` 워크플로우의 Archive까지 완료된 상태
- 사용자가 워크트리 병합을 요청할 때

---

## 워크플로우

### STEP 1: 머지 전 최종 검증

병합 전에 다음을 확인합니다:

```bash
uv run pytest
uv run ruff check .
```

| 상황 | 행동 |
|:-----|:-----|
| 모두 통과 | STEP 2로 진행 |
| 실패 | 문제 해결 후 재검증 |

---

### STEP 2: Git Merge 실행 (AI 직접 실행)

다음 명령들을 **AI가 직접 순차 실행**합니다:

```bash
# 1. 메인 브랜치로 전환
git checkout master

# 2. 기능 브랜치 병합
git merge feature/<feature-name>
```

**예시:**
```bash
git checkout master
git merge feature/facial-builder
```

---

### STEP 3: 워크트리 정리 (AI 직접 실행)

병합 완료 후 워크트리와 브랜치를 정리합니다:

```bash
# 워크트리 제거
git worktree remove ../<project>-<feature-name>

# 기능 브랜치 삭제
git branch -d feature/<feature-name>
```

**예시:**
```bash
git worktree remove ../PyJalFacial-facial-builder
git branch -d feature/facial-builder
```

---

### STEP 4: 완료 보고

```
[Merge Complete]
워크트리 병합이 완료되었습니다:
- 병합된 브랜치: feature/<feature-name>
- 대상 브랜치: master
- 워크트리 정리: 완료
```

---

## 에러 대응

### 머지 충돌 발생 시

```
[Merge Conflict]
머지 충돌이 발생했습니다:
- 충돌 파일: (list)

충돌을 해결한 후 다음 명령을 실행하겠습니다:
git add .
git commit
```

### 워크트리 제거 실패 시

```bash
# 강제 제거
git worktree remove --force ../<project>-<feature-name>
```
