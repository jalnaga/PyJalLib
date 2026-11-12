---
type: "Reference"
title: "PowerShell 호출 스크립트의 변수 충돌"
description: "대소문자만 다른 변수 이름으로 고정 인수가 응답 객체에 덮이는 사례."
applies_when: "PowerShell로 앱·서버 호출용 임시 검증 스크립트를 작성할 때"
read_before: "고정 인수와 응답 객체의 변수 이름을 정하기 전"
status: "stable"
generated: "agent:codex; 2026-11-11; 제출 근거 검토 및 문서 정제"
sources: ["https://github.com/jalnaga/PyJalWiki/pull/4", "jal-harness:pyjal3dsmcp:83d157c4ed75fcce71cd789fee6b68d355528270cf64ed1ed482341c509a6482", ".ai_planning/knowledge/inbox/pyjal3dsmcp/83d157c4ed75fcce71cd789fee6b68d355528270cf64ed1ed482341c509a6482/evidence/.ai_planning/knowledge/evidence/dlel-v1-20261110.md"]
verified: "human:jalnaga"
---

# PowerShell 호출 스크립트의 변수 충돌

프로젝트의 Windows 11·PowerShell 7 실기 기록에서 revision 문자열 `$R`이 응답을 담은 `$r` 대입으로 덮였다. 이어진 `library_execute` 3건은 문자열 인수에 객체가 들어가 서버의 인수 검증에서 거절됐다. 호출 기록과 `last_operation`으로 Max에 전송되지 않았음을 확인했고, 변수 이름을 분리한 재실행은 통과했다고 보고했다.

대소문자만 다른 이름으로 서로 다른 값을 구분하지 않는다. `$sourceRevision`과 `$callResult`처럼 역할이 다른 이름을 쓰고, 호출 직전에 고정 인수의 문자열 형식과 대상 값을 확인한다. 자동 변수·시스템 변수 이름도 임시 변수로 재사용하지 않는다.

제출 자료의 실행 환경은 PowerShell 7이다. 후보에 언급된 PowerShell 5의 실행 결과는 제출되지 않았으며 이번 검토에서 실측 범위를 확대하지 않는다. 중앙은 제출된 UAT 요약을 검토했으며 스크립트를 실행하지 않았다.
