# Test Process Overview

우리는 코드의 품질과 안정성을 보장하기 위해 3가지 테스트 전략을 사용한다. 테스트 대상의 성격에 따라 적절한 전략을 선택하고, 해당 가이드 문서를 로드하여 수행하라.

**우리는 패키지 매니저로 `uv`를 사용하므로, 모든 테스트 명령은 `uv run`을 통해 실행되어야 한다.**

## Strict Rules (필독)
- **Do NOT run:** `pytest ...` (Global 환경 오염 방지)
- **MUST run:** `uv run pytest ...` (격리된 환경 사용)

## 테스트 전략 선택 가이드

현재 테스트하려는 기능이 다음 중 어디에 해당하는지 판단하라.

### Type A. 완전 자동화 테스트 (Console Only)
- **상황:** Unit Test, 간단한 Script 실행 등으로 결과(Pass/Fail)가 터미널 출력에 바로 나타나는 경우.
- **도구:** `pytest`
- **행동 지침:** `.ai_context/manuals/testing/automated_console.md` 참조

### Type B. 유저 주도 테스트 (User Action + Log)
- **상황:** AI가 직접 실행할 수 없는 환경(3DS Max나 Unreal editor등 외부 프로그램에서 실행해야 하는 경우)이거나, 유저의 인터랙션이 필수적인 경우.
- **도구:** 유저의 실행, 지정된 로그 파일 분석
- **행동 지침:** `.ai_context/manuals/testing/user_driven_log.md` 참조

### Type C. 실행 기반 로그 분석 테스트 (Console Trigger + Log File)
- **상황:** AI가 실행은 할 수 있으나, 터미널 출력만으로는 부족하고 생성된 로그 파일이나 데이터 파일을 뜯어봐야 검증이 가능한 경우.
- **도구:** 실행 커맨드 + 테스트 파일에 지정된 로그 파일 분석
- **행동 지침:** `.ai_context/manuals/testing/console_trigger_log.md` 참조

## 일반 원칙
1. **Test Before Commit**: 코드를 수정했으면 반드시 테스트를 통과한 후 커밋하라.
2. **One Strategy**: 한 번에 하나의 전략만 집중해서 수행하라.
3. **Evidence**: 테스트 결과(성공/실패 로그)는 반드시 의사결정의 근거로 남겨라.