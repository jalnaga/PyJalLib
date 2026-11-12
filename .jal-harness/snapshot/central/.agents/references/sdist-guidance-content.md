---
type: "Reference"
title: "sdist에 포함되는 중앙 지침 사본 점검"
description: "추적된 JalHarness 파일이 clean archive 기반 sdist에도 포함된 관측."
applies_when: "hatchling 프로젝트에서 중앙 지침 사본과 함께 소스 배포를 준비할 때"
read_before: "sdist의 공유 범위와 배포 설정을 결정하기 전"
status: "stable"
generated: "agent:codex; 2026-11-11 및 2026-11-12; 제출 근거 검토 및 문서 정제"
sources: ["https://github.com/jalnaga/PyJalWiki/pull/5", "jal-harness:pyjal3dsmcp:a2a0f90e382f9da4b31185c51763454ef5b8c7f763b682aaab7a31b04034ba2f", ".ai_planning/knowledge/inbox/pyjal3dsmcp/a2a0f90e382f9da4b31185c51763454ef5b8c7f763b682aaab7a31b04034ba2f/evidence/.ai_planning/knowledge/evidence/dlel-v1-20261110.md", "jal-harness:pyjallib:986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db", "https://github.com/jalnaga/PyJalWiki/pull/10", ".ai_planning/knowledge/inbox/pyjallib/986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db/evidence/evidence/20261112-hatchling-native-artifact.md", "https://github.com/jalnaga/PyJalLib-dev/commit/5c868e9bf1d27668bab7ccbd54910a6980dc7567", "https://github.com/jalnaga/PyJalLib-dev/commit/4d559c84964f1288e137046526882f11d2c5d731"]
verified: "human:jalnaga"
---

# sdist에 포함되는 중앙 지침 사본 점검

PyJal3DSMCP `cd2cd83c8749ff3845717c00d1b900c52ce7b0f1`의 clean `git archive` 사본을 uv 0.8.14·hatchling으로 빌드한 프로젝트 기록에서, sdist 1021개 항목에 추적 중인 `.jal-harness-version`과 `.jal-harness/` 설정·resolver·snapshot·중앙 지침 사본이 포함됐다. 같은 빌드의 wheel 486개 항목에는 없었다. 후속 커밋의 wheel 489개 항목도 확인했으나 후속 sdist는 재확인하지 않았다.

이 관측은 해당 프로젝트의 빌드 포함 규칙에 한정한다. 모든 hatchling 프로젝트·다른 backend·현재 버전에 동일하게 적용된다고 단정하지 않는다. wheel에 없다는 사실로 sdist에서도 제외됐다고 판단하지 않는다.

외부 배포를 준비하는 프로젝트는 sdist와 wheel 파일 목록을 각각 확인하고, 중앙 지침 사본의 공유 범위에 맞춰 포함·제외를 결정한다. 추적 파일은 로컬 `info/exclude`로 숨겨도 소스 아카이브에서 사라지지 않는다. PR #5의 후보가 제안한 sdist 제외 설정은 당시 적용·검증되지 않았다. 아래의 별도 후속 관측과 구분한다.

근거는 프로젝트의 빌드 관찰 요약이다. 중앙은 배포물을 빌드하거나 실제 배포하지 않았다. PyJal 환경의 관련 문서는 [패키징 절차](domains/pyjal/processes/python_packaging.md)다.


## 2026-11-12 후속 관측

PyJalLib-dev의 hatchling 1.33.0·uv 0.8.14·CPython 3.10.14·Windows 11 x64 기록에서는 다음 설정으로 sdist 범위를 제한했다.

```toml
[tool.hatch.build.targets.sdist]
only-include = ["src/pyjallib", "native", "LICENSE", "README.md"]
```

추적 파일만 있는 트리에서 실제 빌드한 sdist의 구성원 집합은 위 범위의 추적 파일과 자동 포함 `.gitignore`·`PKG-INFO`·`pyproject.toml` 세 개에 일치했다고 보고됐다. 추적된 하네스 자산·내부 문서·tests·tools는 포함되지 않았다. 이는 PR #5의 미검증 설정을 소급 검증한 결과가 아닌 별도 프로젝트·설정의 관측이다. 다른 프로젝트는 자기 배포물의 구성원 목록을 확인한다.

사용자 승인 후 별도 후속 출처를 sources에 연결했다. 후속 출처는 jal-harness:pyjallib:986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db 이며 [검토 근거](../../.ai_planning/knowledge/inbox/pyjallib/986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db/evidence/evidence/20261112-hatchling-native-artifact.md)와 [네이티브 자산 관측](hatchling-native-artifacts.md)을 함께 본다. 중앙은 빌드를 반복하지 않았다.
