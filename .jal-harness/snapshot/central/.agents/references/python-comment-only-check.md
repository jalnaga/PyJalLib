---
type: "Reference"
title: "Python 주석·docstring 변경의 AST 비교"
description: "docstring 값을 비운 AST로 코드 구조 변경을 가려내는 방법과 판정 한계."
applies_when: "Python 주석·docstring 정리에서 실행 코드 변경 여부를 검토할 때"
read_before: "주석 정리의 동작 불변 여부를 판정하기 전"
status: "stable"
generated: "agent:codex; 2026-11-12; 제출 자료 검토"
sources: ["jal-harness:pyjallib:f253f395f38b616117bc980a9d59b7612c35b71b909e58fb800e1287035a92ca", "https://github.com/jalnaga/PyJalWiki/pull/8", ".ai_planning/knowledge/inbox/pyjallib/f253f395f38b616117bc980a9d59b7612c35b71b909e58fb800e1287035a92ca/evidence/evidence/20261112-comment-only-verify/result.md", ".ai_planning/knowledge/inbox/pyjallib/f253f395f38b616117bc980a9d59b7612c35b71b909e58fb800e1287035a92ca/evidence/evidence/20261112-comment-only-verify/verify_comment_only.py", "https://github.com/jalnaga/PyJalLib-dev/commit/cd289e8b7cc0678025ab68becf2b0cfed1997c07"]
verified: "human:jalnaga"
---

# Python 주석·docstring 변경의 AST 비교

PyJalLib-dev가 제출한 Windows 11·CPython 3.10.14의 관측과 비교 스크립트를 자료 수준에서 검토했다. 중앙에서 스크립트나 제품 테스트를 실행하지 않았다.

두 Git 리비전의 수정된 `.py` blob을 같은 Python 버전의 `ast.parse`로 읽는다. 모듈·클래스·동기/비동기 함수의 첫 문장이 문자열 상수인 경우 그 값만 빈 문자열로 바꾸고 `ast.dump(..., include_attributes=False)`를 비교한다. 자리 자체는 남기므로 docstring 추가·삭제는 차이로 나타날 수 있다.

같은 결과는 이 정규화에서 남긴 코드 구조가 같다는 뜻이다. 제출 자료에서는 주석 정리 대상 66개가 같았고, 의도적으로 실행 코드를 바꾼 수정 파일 4개는 모두 달랐다. 이는 해당 비교 범위의 관측이며 임의의 Python 프로그램에 대한 동작 불변 증명은 아니다.

검토에는 다음 조건을 함께 적용한다.

- `__doc__`, `inspect.getdoc`, `help`, `pydoc` 등 문서 문자열 소비처를 별도로 확인한다. 제출 프로젝트는 해당 참조가 없다고 보고했다.
- 주석 지시문(`noqa`, `type: ignore`, 인코딩 선언)은 AST 밖이다. 제출 스크립트는 인코딩 선언 자체를 비교하지 않는다. BOM·CRLF/LF·끝 줄바꿈 검사는 이 누락을 대신하지 않는다.
- 위치 속성을 뺀 비교는 줄 번호·추적 정보 차이를 보존하지 않는다. 소스나 위치를 읽는 소비처도 별도 검토한다.
- 추가·삭제·이름 변경 파일은 수정 파일 비교와 분리해 diff를 읽는다. 비 Python 파일은 별도 검토하며 `pyproject.toml`의 파싱 데이터 비교도 패키징 동작 전체의 보증은 아니다.
- AST 차이는 검토할 코드 차이를 뜻한다. 곧바로 결함이라는 뜻은 아니다. 반대로 AST가 같아도 위 예외와 필요한 검증은 남는다.

줄바꿈·BOM·끝 줄바꿈은 원본 바이트로 함께 대조한다. 제출 스크립트는 줄바꿈 종류의 존재 여부를 비교하며 각 줄의 정확한 위치까지 같다고 보증하지 않는다.

프로젝트 보고의 전체 테스트 1473 passed·1 skipped와 배포본 40개 동일은 보조 근거다. Max·UE 실행 검증은 없었다. 기존 PyJal [배포 문서](domains/pyjal/processes/p4_deploy.md)의 4단 비교도 같은 한계 안에서 해석한다.

근거: [프로젝트 결과 요약](../../.ai_planning/knowledge/inbox/pyjallib/f253f395f38b616117bc980a9d59b7612c35b71b909e58fb800e1287035a92ca/evidence/evidence/20261112-comment-only-verify/result.md), [제출 비교 스크립트](../../.ai_planning/knowledge/inbox/pyjallib/f253f395f38b616117bc980a9d59b7612c35b71b909e58fb800e1287035a92ca/evidence/evidence/20261112-comment-only-verify/verify_comment_only.py). 스크립트는 검토 자료이며 중앙의 실행 도구로 설치하지 않는다.
