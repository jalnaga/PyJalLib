# New Module Creation Manual

이 문서는 새로운 Python 모듈(패키지)을 처음부터 생성할 때 따르는 표준 절차입니다.

---

## 1. Pre-Design (사전 설계)

### 1.1 요구사항 분석

새 모듈 생성 전 다음을 명확히 하십시오:

- **목적**: 이 모듈이 해결하는 문제는 무엇인가?
- **사용자**: 이 모듈을 호출하는 코드/사람은 누구인가?
- **의존성**: 필요한 외부 라이브러리는 무엇인가?
- **참조 코드**: 기존에 유사한 구현이 있는가?

### 1.2 아키텍처 패턴 선택

| 패턴 | 사용 상황 | 예시 |
|------|----------|------|
| **Facade** | 복잡한 서브시스템을 단순한 인터페이스로 제공 | `pyjallib.max.Header` |
| **Service** | 단일 책임의 비즈니스 로직 | `PerforceService` |
| **Utility** | 상태 없는 헬퍼 함수 모음 | `pyjallib.nameService` |
| **Data Class** | 데이터 구조 및 직렬화 | `ChangeListInfo` |

---

## 2. Package Structure (패키지 구조)

### 2.1 기본 구조

```
src/{module_name}/
├── __init__.py           # 공개 API 노출
├── {module_name}.py      # 메인 클래스 (Facade인 경우)
├── {sub_module1}.py      # 서브 모듈 1
├── {sub_module2}.py      # 서브 모듈 2
└── ...
```

### 2.2 `__init__.py` 작성 규칙

```python
"""
{ModuleName} - 모듈 설명 (한 줄)

상세 설명 (필요 시)
"""

from .{module_name} import {MainClass}

__all__ = ["{MainClass}"]
```

---

## 3. Implementation Strategy (구현 전략)

### 3.1 구현 순서 (Code-First)

1. **패키지 뼈대 생성**: `__init__.py` 및 빈 클래스 파일들
2. **메인 클래스 구현**: Facade 또는 Entry Point
3. **서브 모듈 구현**: 의존성 순서대로 (독립적인 것 먼저)
4. **통합 테스트**: 모듈 전체 동작 확인

### 3.2 클래스 설계 원칙

- **의존성 주입**: 서브 모듈 생성 시 부모 참조 전달
- **공유 상태 최소화**: 필요한 경우에만 부모를 통해 공유
- **단일 책임**: 각 클래스는 하나의 역할만 담당

```python
# 의존성 주입 예시
class MainClass:
    def __init__(self):
        self._sharedData = {}
        self.subModule1 = SubModule1(self)
        self.subModule2 = SubModule2(self)

class SubModule1:
    def __init__(self, inParent: MainClass):
        self._parent = inParent
    
    @property
    def _data(self):
        return self._parent._sharedData
```

---

## 4. Coding Standards (코딩 표준)

### 4.1 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 클래스 | PascalCase | `FacialBuilder`, `FacialData` |
| 메서드 | snake_case | `add_bone()`, `save_json()` |
| 변수 | camelCase | `boneList`, `configPath` |
| 파라미터 | in + CamelCase | `inBoneName`, `inFilePath` |
| private 멤버 | _ 접두사 | `_jsonData`, `_parent` |

### 4.2 Docstring (Google Style, 한국어)

```python
def method_name(self, inParam1: str, inParam2: int = 0) -> bool:
    """
    메서드 설명 (한 줄).
    
    상세 설명 (필요 시 여러 줄).
    
    Args:
        inParam1: 파라미터1 설명
        inParam2: 파라미터2 설명. 기본값 0.
        
    Returns:
        반환값 설명
        
    Raises:
        ValueError: 발생 조건
    """
```

---

## 5. Implementation Checklist

### 5.1 패키지 생성

- [ ] `src/{module_name}/` 디렉토리 생성
- [ ] `__init__.py` 작성 (공개 API 노출)
- [ ] 메인 클래스 파일 생성

### 5.2 클래스 구현

- [ ] 메인 클래스 `__init__` 구현
- [ ] 서브 모듈 클래스들 구현
- [ ] 의존성 주입 연결
- [ ] 타입 힌트 추가

### 5.3 품질 확인

- [ ] `uv run ruff check .` 린트 통과
- [ ] `uv run pytest` 테스트 통과 (테스트 작성 시)
- [ ] Docstring 작성 완료

---

## 6. Appendix (참조 문서)

| 필요 정보 | 참조 위치 |
|-----------|-----------|
| 네이밍 규칙, 코드 스타일 | `.ai_context/tech_spec.md` |
| 테스트 전략 | `.ai_context/manuals/test_process.md` |
| 기획서 작성 | `.ai_context/manuals/planning_guide.md` |
| Facade 패턴 구현 가이드 | `.ai_context/references/facade_pattern.md` |

