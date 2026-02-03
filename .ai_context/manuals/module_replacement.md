# Module Replacement Manual

이 문서는 기존 모듈을 새로운 구현으로 교체할 때 따르는 표준 절차입니다.

---

## 1. Pre-Analysis (사전 분석)

교체 대상 모듈에 대해 다음을 파악하십시오.

### 1.1 기존 모듈 분석

대상 파일을 읽고 다음을 추출하십시오:

- **공개 클래스**: 외부에서 사용 가능한 클래스 목록
- **공개 함수/메서드**: 외부에서 호출되는 API
- **내부 구현 방식**: 현재 사용 중인 라이브러리, 패턴

### 1.2 의존성 맵 생성

다음을 검색하여 사용처를 파악하십시오:

```
"from {모듈경로} import" 또는 "import {모듈경로}"
```

결과를 다음 형식으로 정리:

| 사용 파일 | 사용 방식 | 사용하는 API |
|-----------|-----------|--------------|
| `path/to/file.py` | import / 상속 / 인스턴스 | `ClassName`, `function_name` |

---

## 2. Interface Contract (인터페이스 계약)

### 2.1 공개 API 목록 작성

유지해야 할 시그니처를 명시하십시오:

```
ClassName
├── __init__(inParam1: Type, inParam2: Type)
├── method_name(inArg: Type) -> ReturnType
└── property_name: Type
```

### 2.2 Breaking Change 결정

다음 중 하나를 선택하고 PRD에 명시하십시오:

- **완전 호환 유지**: 기존 코드 수정 없이 교체 가능
- **Deprecation 전략**: 기존 API는 경고와 함께 유지, 신규 API 추가
- **Breaking Change 허용**: 의존 코드도 함께 수정

---

## 3. Implementation Strategy

### 3.1 구현 방식 선택

| 방식 | 상황 | 장점 |
|------|------|------|
| **In-place 교체** | 인터페이스 동일 | 의존 코드 수정 불필요 |
| **새 파일 생성 후 교체** | 대규모 변경 | 롤백 용이 |
| **Adapter 패턴** | 인터페이스 불일치 | 점진적 마이그레이션 |

### 3.2 구현 순서

1. **테스트 먼저**: 기존 동작을 검증하는 테스트 작성/확인
2. **핵심 구현**: 새로운 내부 로직 작성
3. **API 연결**: 기존 시그니처로 래핑
4. **테스트 통과**: 모든 테스트 green 확인

---

## 4. Migration Checklist

### 4.1 구현 완료 확인

- [ ] 신규 구현 코드 작성 완료
- [ ] 기존 공개 API 시그니처 유지 (또는 의도적 변경 문서화)
- [ ] docstring 작성 (한국어, Google style)

### 4.2 의존성 업데이트

- [ ] 상속 클래스 동작 확인
- [ ] import 경로 변경 필요 시 모든 사용처 수정
- [ ] `__init__.py` export 확인

### 4.3 테스트 실행

- [ ] 해당 모듈 테스트 통과: `uv run pytest tests/test_{module}.py`
- [ ] 전체 테스트 통과: `uv run pytest`

---

## 5. Appendix (참조 문서)

| 필요 정보 | 참조 위치 |
|-----------|-----------|
| 네이밍 규칙, 코드 스타일 | `.ai_context/tech_spec.md` |
| 도메인별 구조/공식 | `.ai_context/references/` 폴더 |
| 테스트 전략 선택 | `.ai_context/manuals/test_process.md` |
| 기획서 작성 | `.ai_context/manuals/planning_guide.md` |
