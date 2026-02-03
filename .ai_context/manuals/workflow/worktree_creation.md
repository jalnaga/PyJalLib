# Worktree Creation Workflow

워크트리를 생성하여 새로운 기능 개발을 위한 독립적인 작업 환경을 만듭니다.

---

## 진입 조건

- 사용자가 워크트리 생성을 요청할 때
- 새 기능 개발 전 워크트리가 필요할 때

---

## 워크플로우

### STEP 1: Feature Name 확인

사용자로부터 기능 이름을 확인합니다. 명확하지 않으면 질문하십시오.

```
[Worktree Creation]
워크트리를 생성합니다. 기능 이름을 확인해주세요:

예: facial-builder, bone-validation, pose-calculator
```

### STEP 2: Git Worktree 생성 (AI 직접 실행)

다음 명령을 **AI가 직접 실행**합니다:

```bash
git worktree add ../<project>-<feature-name> -b feature/<feature-name>
```

**예시:**
```bash
git worktree add ../PyJalFacial-facial-builder -b feature/facial-builder
```

### STEP 3: 완료 보고

```
[Worktree Created]
워크트리가 생성되었습니다:
- 경로: ../<project>-<feature-name>
- 브랜치: feature/<feature-name>
```
