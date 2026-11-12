---
okf_version: "0.2"
---

# 중앙 지식 색인

이 파일은 `project-workflow.py index`가 concept frontmatter로 생성한다. 직접 고치지 말고 문서 frontmatter를 갱신한 뒤 다시 생성한다.

## 공통 지침

* [에이전트 협업과 인수 검증](agent-collaboration.md) - 코디네이터·테스터·구현자 역할, ATDD·TDD·UAT와 편집 소유권
* [설계 원칙](design-principles.md) - 최소 변경, 근거 기반 설계와 외부 계약 보존 원칙
* [hatchling의 네이티브 자산 포함과 wheel 태그 관측](hatchling-native-artifacts.md) - hatchling 1.33.0에서 고정 artifacts 경로로 .pyd를 포함한 결과와 호환성 검증의 한계.
* [중앙 지식 체계](knowledge-system.md) - 재사용 지식 후보의 근거·민감 정보 검토, 수집과 정식 승격
* [고정 커밋과 허용 목록을 이용한 공개 파일 내보내기](pinned-commit-public-export.md) - 작업 트리 혼입을 피하는 Git 객체 기반 내보내기와 공개 이력 분리의 관측·한계.
* [PowerShell 호출 스크립트의 변수 충돌](powershell-variable-names.md) - 대소문자만 다른 변수 이름으로 고정 인수가 응답 객체에 덮이는 사례.
* [프로젝트 공통 개발 지침](project-guidance.md) - 프로젝트 개발의 계획·작업 위치·검증과 통합 판단 기준
* [PyJal 지식 연결](pyjal-knowledge.md) - PyJal 지식 선택·적용·후보 수집과 중앙 사본 범위
* [Python 주석·docstring 변경의 AST 비교](python-comment-only-check.md) - docstring 값을 비운 AST로 코드 구조 변경을 가려내는 방법과 판정 한계.
* [sdist에 포함되는 중앙 지침 사본 점검](sdist-guidance-content.md) - 추적된 JalHarness 파일이 clean archive 기반 sdist에도 포함된 관측.
* [워커 지시서와 실행 계약](worker-task-contract.md) - 워커 지시서·읽기·질문·보호 테스트 계약
* [중앙·프로젝트 작업 흐름](workflow.md) - 작업 시작·재개·인계, 통합 승인과 안전한 종료 절차
* [호스트 어댑터](host-adapters/index.md) - 호스트별 작업공간·역할 실행·질문·종료와 지원 한계

## 도메인

* [PyJal 지식 번들](domains/pyjal/index.md) - pyjal 도메인 지식 색인
