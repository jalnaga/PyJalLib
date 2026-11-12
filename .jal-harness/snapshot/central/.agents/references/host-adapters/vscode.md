---
type: "Host Adapter"
title: "VS Code Agent Sessions 어댑터"
description: "vscode 호스트 생성·역할 실행·질문·종료와 지원 한계"
applies_when: "VS Code에서 작업공간·역할 에이전트 실행을 선택·조정할 때"
read_before: "VS Code 작업공간 생성·역할 실행·종료 결정 전"
status: "stable"
---

# VS Code Agent Sessions 어댑터

근거: [세션 관리](https://code.visualstudio.com/docs/agents/run/sessions/manage-sessions), [에이전트 하네스](https://code.visualstudio.com/docs/agents/run/agent-harnesses). 문서 기반이며 이번 작업에서는 직접 실행하지 않았다. 설치 버전과 선택 하네스별 기능·승인 정책을 확인하며 모든 세션을 Bypass Approvals라고 일반화하지 않는다.

코디네이터가 지원되는 Git 기능으로 전용 worktree를 먼저 만들고 환경·지시서·exclude·공용 안내를 준비한 뒤 사용자가 해당 폴더에서 테스터 세션을 연다. New Worktree UI가 생성과 시작을 결합하면 준비 전 작업하지 않는 대기 방식을 실증하기 전에는 사용하지 않는다. 코디네이터의 프로그램적 세션 생성 기능은 미실증이므로 사용자 실행이 필요한 반자동 흐름으로 안내한다.

테스터의 종료·결과를 세션 목록의 공식 상태와 사용자 확인으로 확보하고 같은 폴더의 별도 구현자 세션을 연다. 새 세션이 실제 같은 worktree와 프로젝트 AGENTS.md·CLAUDE.md 시작 분기를 적용하는지는 확인이 필요하다. 세션의 입력 요청은 사용자가 확인하며 직접 코디네이터 채널이 없으면 질문·재개 정보 반환·종료·답변 후 재실행한다. 개입형은 그 세션에서 사용자에게 직접 질문한다.

코디네이터는 작업 절대 경로의 터미널에서 검사한다. 결과는 세션 응답·커밋과 사용자 전달로 확인하고 별도 상태 장부를 만들지 않는다. 세션 선택·대화로 가시성과 개입을 제공할 수 있으나 이번 환경에서는 미실증이다. ignore 파일을 자동 복사한다고 가정하지 않고 필요한 setup 자료만 프로젝트 정책에 맞게 준비한다. 세션·하네스 권한을 사용자 승인 없이 확대하지 않는다.
