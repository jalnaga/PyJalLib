---
type: "Reference"
title: "hatchling의 네이티브 자산 포함과 wheel 태그 관측"
description: "hatchling 1.33.0에서 고정 artifacts 경로로 .pyd를 포함한 결과와 호환성 검증의 한계."
applies_when: "hatchling으로 미리 빌드한 .pyd를 wheel·sdist에 포함할 때"
read_before: "artifacts 패턴과 설치·배포 검증 범위를 정하기 전"
status: "stable"
generated: "agent:codex; 2026-11-12; 제출 자료 검토"
sources: ["jal-harness:pyjallib:986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db", "https://github.com/jalnaga/PyJalWiki/pull/10", ".ai_planning/knowledge/inbox/pyjallib/986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db/evidence/evidence/20261112-hatchling-native-artifact.md", "https://github.com/jalnaga/PyJalLib-dev/commit/5c868e9bf1d27668bab7ccbd54910a6980dc7567", "https://github.com/jalnaga/PyJalLib-dev/commit/4d559c84964f1288e137046526882f11d2c5d731"]
verified: "human:jalnaga"
---

# hatchling의 네이티브 자산 포함과 wheel 태그 관측

PyJalLib-dev의 Windows 11 x64·CPython 3.10.14·uv 0.8.14·hatchling 1.33.0 관측을 검토했다. 다른 버전·백엔드로 일반화하지 않는다.

추적한 `.pyd`가 `.gitignore`에 걸리지 않아도 wheel·sdist에서 빠졌다. 제출 자료는 hatchling의 기본 전역 제외 `*.py[cdo]`와 `include_path()`의 artifact 우선 판정을 원인으로 제시했다. 고정 경로를 전역 설정에 넣은 결과 두 배포물에 파일 하나가 추가됐다.

```toml
[tool.hatch.build]
artifacts = ["/src/pyjallib/native/alpha_wrap_native.cp310-win_amd64.pyd"]
```

해당 프로젝트의 wheel 구성원은 129→130, sdist는 150→151이었다. 넓은 `*.pyd` 패턴은 무시 위치의 잔여물도 포함했다. `artifacts`에 지정한 파일은 추적 여부와 무관하게 현재 바이트가 들어갈 수 있으므로 검토한 추적 파일만 있는 트리에서 빌드하고 구성원과 바이트를 확인한다. 추적되지 않고 무시되지도 않는 패키지 파일의 혼입도 별도로 확인한다.

`uv build`의 sdist 경유 wheel과 직접 빌드한 wheel에 대해 제출 프로젝트는 구성원·바이트 일치를 보고했다. 보호 테스트는 변경 전 10건 실패, 변경 후 36건 통과였고 통합 커밋 전체 결과는 1509 passed·1 skipped였다. 중앙은 빌드·테스트를 실행하지 않았다.

`.pyd` 포함 뒤에도 관측된 wheel 태그는 `py3-none-any`, `Root-Is-Purelib: true`였다. 이는 artifacts 설정이 태그를 바꾸지 않았다는 관측이다. CPython 3.10용 Windows 바이너리를 모든 Python·플랫폼에서 쓸 수 있다는 뜻이나 배포 태그의 적합성을 검증한 결과로 해석하지 않는다. 저장소 밖 새 CPython 3.10 환경에서 설치본 로드·호출은 보고됐으나 다른 Python·OS·Max 내장 Python과 `twine check`는 미검증이다.

sdist 범위 제한은 [중앙 지침 사본 점검](sdist-guidance-content.md)의 후속 관측을 함께 본다. 상세 근거는 [프로젝트 패키징 요약](../../.ai_planning/knowledge/inbox/pyjallib/986eaae966b50551b3bea963e96c3632385605180da813ec437916ff7b90f7db/evidence/evidence/20261112-hatchling-native-artifact.md)다.
