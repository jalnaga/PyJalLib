# Active PRD

> 이 파일은 현재 개발 중인 기능의 PRD(Product Requirements Document)를 작성하는 공간입니다.
> 기능 완료 후 `archive/YYYYMMDD_FeatureName_PRD.md` 형식으로 아카이빙하고 이 파일을 비웁니다.

## [기능명]

### Background & Intent

**왜 이 기능이 필요한가?**
- 현재 문제점 또는 요구사항 설명
- 해결하고자 하는 비즈니스 목표
- 사용자 시나리오

**기대 효과:**
- 이 기능이 제공하는 가치
- 개선되는 워크플로우

### Primary Manual

`.ai_context/manuals/workflow/new_feature.md`

### Technical Decisions & References

**기술적 접근 방법:**
- 선택한 아키텍처/디자인 패턴
- 대안들과 비교 (장단점)
- 왜 이 방법을 선택했는가?

**참고 파일:**
- 관련 모듈 경로
- 참조할 레퍼런스 문서

**참고 문서:**
- `.ai_context/references/patterns/facade_pattern.md` (예시)
- 기타 관련 레퍼런스

### Scope & Prioritization

#### [Must-Have]

**핵심 기능 (반드시 구현)**
1. 기능 1 설명
   - 구체적인 요구사항
   - 성공 기준

2. 기능 2 설명
   - 구체적인 요구사항
   - 성공 기준

#### [Should-Have]

**중요하지만 필수는 아닌 기능**
1. 기능 3 설명
   - 왜 Should-Have인가?

#### [Nice-to-Have]

**있으면 좋은 기능**
1. 기능 4 설명

#### [Non-Goal]

**명시적으로 하지 않을 것**
1. 범위를 벗어난 작업
2. 나중에 할 작업

---

### Test Strategy

**테스트 방법:**
- Automated Console Test (자동화 가능)
- User-Driven Log Test (수동 실행 필요)
- Console Trigger + Log Test (자동 실행 + 로그 분석)

**테스트 시나리오:**
1. 시나리오 1
2. 시나리오 2

**성공 기준:**
- [ ] 기준 1
- [ ] 기준 2

---

## PRD 작성 가이드

**작성 시점:** 새로운 기능 개발 시작 전
**승인 필요:** 사용자 승인 후 구현 시작
**업데이트:** 요구사항 변경 시 즉시 반영
**아카이빙:** 기능 완료 후 `archive/` 폴더로 이동

**작성 원칙:**
- 구체적이고 명확하게 작성
- "왜"를 명시 (기술적 결정의 이유)
- 대안과 트레이드오프를 기록
- Must-Have에 집중, 나머지는 나중에
