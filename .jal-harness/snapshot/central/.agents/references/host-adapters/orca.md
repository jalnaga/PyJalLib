---
type: "Host Adapter"
title: "Orca 어댑터"
description: "orca 호스트 생성·역할 실행·질문·종료와 지원 한계"
applies_when: "Orca에서 작업공간·역할 에이전트 실행을 선택·조정할 때"
read_before: "Orca 작업공간 생성·역할 실행·종료 결정 전"
status: "stable"
sources: ["jal-harness:pyjal3dsmcp:c3cfb31c8a45bccb156e144db069c77d557bc24c3a7a3664e0217ed6b6a3c959", ".ai_planning/knowledge/inbox/pyjal3dsmcp/c3cfb31c8a45bccb156e144db069c77d557bc24c3a7a3664e0217ed6b6a3c959/evidence/.ai_planning/knowledge/evidence/dlel-v1-20261110.md"]
verified: "human:jalnaga"
generated: "agent:codex; 2026-11-11; 제출 근거 검토 및 문서 정제"
---

# Orca 어댑터

근거: 기존 표는 Orca 1.4.235 사용자 관찰과 후보 명령이며 전체 수명주기는 당시 미실증이었다. 아래 1.4.253 관찰은 사용자 승인으로 반영하되 당시 환경과 검증 수준을 별도 구분한다. 실제 적용 시 설치 버전의 공식 CLI·orchestration 스킬을 읽어 지원과 권한을 확인한다. 사용자 금지 환경에서는 호출하지 않는다.

| 단계 | 후보와 검증할 조건 |
|---|---|
| 생성 | `orca worktree create --repo id:<repoId> --name <작업명> --parent-worktree active --setup <run 또는 skip> --json`, agent 옵션 없이 생성; base ref·부모·setup 성공 및 에이전트 미실행 확인 필요 |
| 첫 역할 | 지시서·exclude·ACTIVE_WORK 준비 후 `orca agent launch --agent <이름> --worktree path:<절대경로> --prompt <지시서 배정>`; 실제 프롬프트·사이드바 표시 확인 필요 |
| 다음 역할 | 테스터 종료 확인 후 같은 path에 별도 agent launch; 독립 세션·같은 공간 확인 필요 |
| 질문·완료 | orchestration 사용 시 ask·check·worker_done 계약 확인; 기존 worktree의 다음 worker 연결 가능 여부 미확인. 미지원이면 질문·재개 정보 반환 후 종료·재실행 |
| 검사 | `orca terminal create --worktree path:<절대경로> --command <검사명령> --json`과 terminal read의 결과·코드 위치 확인 필요 |
| 사용자 개입 | 사용자가 워크스페이스·역할 탭 선택; 브라우저·Design Mode의 작업 환경 연결은 직접 확인 필요 |

worktree ps·terminal read만으로 종료가 확정되는지 공식 상태 계약으로 확인한다. active/current는 호출 위치에 의존하므로 자식은 path 또는 id로 지정한다. repo base-ref 설정이 필요하면 기존 사용자 설정과 다른 작업 영향을 확인해 조율한다. 각 자원은 하나의 관리 주체로만 추적한다. CLI 등록·실험 기능을 임의 활성화하지 않고 사용자 설정의 에이전트 권한을 따른다. 가시성과 개입은 관찰 사례가 있으나 setup 실패·역할 교체·질문·중복 실행 방지 전체의 보장은 아니다.

## 2026-11-10 Orca 1.4.253 관찰 (적용 환경 한정)

[PyJal3DSMCP PR #3](https://github.com/jalnaga/PyJalWiki/pull/3)의 프로젝트 근거 요약을 검토했다. 환경은 Windows 11, 코디네이터·워커 모두 Claude Code의 터미널 표면이다. Codex·chat·다른 버전과 직접 ask/reply 채널은 확인하지 않았다.

- `--agent` 없는 worktree 생성 후 지시서를 준비하고 `agent launch`로 시작했다. 5개 작업에서 테스터·구현자 10회 모두 `prompt.outcome=handed-to-terminal`과 실제 커밋·보고서 작성을 관찰했다. prompt 전달 결과 하나만으로 작업 시작·완료를 보장한다는 의미는 아니다.
- 같은 worktree의 다음 역할은 별도 launch의 독립 터미널 세션이었다. `terminal wait --for tui-idle` 반환, `worktree ps`의 `done`, Git 제외 보고서와 clean 상태를 함께 관측했다. idle/done은 프로세스 종료의 증명이 아니므로 편집 중단·소유권 교체 판단에는 현재 호스트의 상태 계약과 명시적 결과를 확인한다.
- `terminal close`의 `tab_not_found` 실패가 4회 기록됐다. 이 오류로 종료 성공을 추정하거나 다른 터미널을 닫지 않는다. 현재 핸들과 실행 상태를 다시 확인한다.
- clean·통합된 worktree 5개를 `worktree rm --force`로 정리한 관찰이 있다. 이 플래그를 일반 정리 지침으로 승격하지 않는다. 제외된 파일·프로세스·현재 사용 여부까지 현재 작업 흐름에 따라 확인한다.

원본 호출 로그와 보고서는 로컬 임시 위치에만 있었다는 제출 한계가 있다. 이 요약은 당시 관찰의 적용 범위를 보충하며, 설치 버전의 공식 CLI 계약과 현재 AGENTS.md의 역할·승인 규칙을 대체하지 않는다.
