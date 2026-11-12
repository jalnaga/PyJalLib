---
type: "Guideline"
title: "PyJal 지식 연결"
description: "PyJal 지식 선택·적용·후보 수집과 중앙 사본 범위"
applies_when: "PyJal·ORV 기술 지식을 사용하거나 새로운 관측을 남길 때"
read_before: "지식 선택·작업 배정·지식 수집 전"
---

# PyJal 지식 연결

JalHarness는 작업 배치·역할·검증·통합 절차를 관리하고, pyjal 도메인 번들(`domains/pyjal/`)은 PyJal·ORV 기술 지식의 정본을 관리한다. 사용자 지시와 프로젝트 자체 지침, 실행 도구의 권한 규칙이 우선한다. 이전 기술 문서 안의 역할·게이트·작업 순서는 현재 JalHarness 운영 규칙을 대체하지 않는다.

## 작업에 적용

1. 코디네이터는 [지식 색인](domains/pyjal/index.md), [공통 작업 규약](domains/pyjal/guides/workspace-contract.md)에서 시작한다. [작업별 길잡이](domains/pyjal/reference_map.md)와 [프로젝트 카드](domains/pyjal/projects/index.md)에서 필요한 기술 문서·규약·교훈만 선택한다.
2. 색인의 설명만으로 구현하지 않는다. 선택한 본문을 읽고 API·호스트·경로·의존성을 현재 소스에서 확인한다. 관련 문서가 없으면 그 사실을 밝히고 조사한다.
3. 읽은 지식의 제약과 재발 방지 항목을 구현·검증에 반영한다. 결과 보고에는 사용한 문서 경로, 적용 내용, 검증 결과와 미확인 사항을 짧게 연결한다.
4. 워커에게는 선택한 본문의 절대 경로와 출처를 지시서로 전달한다. 워커가 중앙 전체를 다시 탐색하도록 요구하지 않는다.

`domains/pyjal/history/`, `domains/pyjal/references/originals/`와 기존 계획 아카이브는 과거 증거다. 현재 명령·승인·권한 규칙으로 실행하지 않는다. 기술 관측의 적용 조건과 검증 여부를 구분한다.

## 새 지식과 기존 학습

- 새 지식 후보는 [JalHarness 지식 체계](knowledge-system.md)를 따른다. 등록 프로젝트의 후보는 해당 프로젝트 outbox에서 중앙으로 수집한다. 중앙에서 직접 발견한 후보는 [중앙 수집함](../../.ai_planning/knowledge/inbox.md)에 근거와 적용 조건을 남긴다.
- 기존 [학습 관측](domains/pyjal/maintenance/inbox.md)은 이전한 미정제 원료로 보존한다. 새 수집함에 같은 원문을 복제하지 않고 링크로 검토한다.
- 정식 반영은 중복·충돌·범위·근거 검토와 묶음 승인 후 `domains/pyjal/`의 해당 개념에 적용하고 [변경 이력](log.md)과 생성 색인을 갱신한다. 도메인 지식을 공통 위치나 다른 도메인에 복제하지 않는다.

## 중앙 연결과 사본 범위

중앙 색인 [index.md](index.md)는 이 연결 문서를 공통 지침으로, [pyjal 도메인 색인](domains/pyjal/index.md)을 도메인 시작점으로 안내한다. 지식 본문 탐색에는 도메인 안의 Markdown 링크와 `domains/pyjal/catalog.json`을 사용한다.

프로젝트의 오프라인 snapshot은 공통 지침과 pyjal 도메인의 index.md만 포함한다. 도메인 본문은 자동으로 복사하지 않는다. 중앙에 접근할 수 없는 작업에서 필요한 본문이 사본에 없으면 이를 알리고 해당 판단을 보류한다. 현재 색인 연결만으로 전체 번들의 오프라인 제공을 보장하지 않는다.
