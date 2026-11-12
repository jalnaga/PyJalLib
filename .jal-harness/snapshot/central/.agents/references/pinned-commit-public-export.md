---
type: "Reference"
title: "고정 커밋과 허용 목록을 이용한 공개 파일 내보내기"
description: "작업 트리 혼입을 피하는 Git 객체 기반 내보내기와 공개 이력 분리의 관측·한계."
applies_when: "개발 저장소와 공개 배포 저장소를 나누어 검토한 파일만 내보낼 때"
read_before: "내보내기 소스·공유 범위·이력 연결 정책을 정하기 전"
status: "stable"
generated: "agent:codex; 2026-11-12; 제출 자료 검토"
sources: ["jal-harness:pyjallib:49253709797f4c1ab1ea0503d677254f71b684d8557f88113eec22bb107d6206", "https://github.com/jalnaga/PyJalWiki/pull/9", ".ai_planning/knowledge/inbox/pyjallib/49253709797f4c1ab1ea0503d677254f71b684d8557f88113eec22bb107d6206/evidence/evidence/20261112-public-private-export.md", "https://github.com/jalnaga/PyJalLib-dev/commit/cd289e8b7cc0678025ab68becf2b0cfed1997c07", "https://github.com/jalnaga/PyJalLib-dev/commit/b9232bd1e462e82a15f070048ee7ed102b6398ec"]
verified: "human:jalnaga"
---

# 고정 커밋과 허용 목록을 이용한 공개 파일 내보내기

PyJalLib-dev의 2026-11-11~12 전환 기록(Windows 11·Git 2.55·Python 3.10.14)을 검토했다. 도구는 프로젝트 고유 구현이며 중앙 공용 도구로 배포하거나 실행하지 않았다.

관측된 구현은 고정 커밋의 `git ls-tree`·`git cat-file`로 허용 목록의 blob만 읽고 정책도 같은 커밋에서 읽는다. 작업 트리의 수정·미추적 파일을 입력으로 삼지 않는다. 별도 공개 checkout에서 기본 dry-run으로 추가·수정·삭제 계획을 확인한 뒤 적용한다. `.git`과 명시적 보존 경로를 유지하며 경로 이탈과 경로상의 junction·symlink는 거부한다.

재현 조건은 입력 커밋·정책·내보내기 구현의 일치다. 기록에는 경로와 바이트의 `tree_sha256`, 정책의 `policy_sha256`, 개발·공개 커밋 대응을 남겼다. 공개 이력은 비공개 이력과 부모로 잇지 않고 대응 기록은 비공개 쪽에 둔다. 이 구조의 도입과 공개 저장소 쓰기는 각각 해당 작업의 승인을 따른다.

제출 요약에서는 작업 트리와 정책 변경의 비혼입, 허용 목록, 링크 거부, 삭제·보존, 재실행 무변경 테스트 통과를 보고했다. 실제 내보내기는 199개 파일·규칙 위반 0·재실행 변경 0, 새 공개 clone의 테스트는 963 passed였다. 중앙은 테스트를 반복하지 않았으며 이 결과를 다른 프로젝트 구현의 보증으로 일반화하지 않는다.

내용 검사는 정해진 패턴만 탐지한다. 규칙에 없는 내부 표현이 통과한 사례도 있으므로 export 집합과 생성 문서·링크·면제 사유를 사람이 검토한다. 경로 허용 목록만으로 공개 적합성을 판정하지 않는다. PyJal 내부 자료는 [공개 범위](domains/pyjal/guides/publication-scope.md)를 함께 따른다.

이력 강제 갱신과 옛 브랜치 삭제 뒤에도 옛 커밋 두 개가 SHA를 통한 GitHub REST API 조회에 응답했다는 프로젝트 기록이 있다. 이는 전환 직후와 다음 날의 제한된 관측이다. GitHub의 영구 보관 여부·정리 시점·Support 처리 결과는 확인되지 않았다. 이력 분리를 이미 배포된 자료의 회수 근거로 삼지 않는다.

대용량 저장소·LFS·서브모듈·다른 Git 호스팅과 DCC 실행은 미검증이다. 상세 근거는 [프로젝트 전환 요약](../../.ai_planning/knowledge/inbox/pyjallib/49253709797f4c1ab1ea0503d677254f71b684d8557f88113eec22bb107d6206/evidence/evidence/20261112-public-private-export.md)다.
