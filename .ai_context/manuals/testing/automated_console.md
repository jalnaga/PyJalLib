# Type A: 완전 자동화 테스트 (Console Only)

> **적용 상황:** Unit Test, 간단한 Script 실행 등으로 결과(Pass/Fail)가 터미널 출력에 바로 나타나는 경우.

## 핵심 원칙

1. **반드시 `uv run pytest`를 사용하라.** (Global 환경 오염 방지)
2. **테스트는 독립적이고 재현 가능해야 한다.**
3. **결과 로그는 의사결정의 근거로 남겨라.**

---

## 실행 절차

### Step 1: 테스트 대상 확인

```bash
# 테스트 파일 위치 확인
ls tests/
```

테스트 파일 네이밍 규칙:
- `test_*.py` 또는 `*_test.py`
- 예: `test_naming.py`, `test_perforce_adapter.py`

### Step 2: 테스트 실행

```bash
# 전체 테스트 실행
uv run pytest tests/

# 특정 파일만 실행
uv run pytest tests/test_naming.py

# 특정 함수만 실행
uv run pytest tests/test_naming.py::test_parse_name

# 상세 출력 (-v)
uv run pytest tests/test_naming.py -v

# 실패 시 바로 중단 (-x)
uv run pytest tests/ -x

# 출력 캡처 비활성화 (-s)
uv run pytest tests/test_naming.py -s
```

### Step 3: 결과 해석

#### 성공 케이스
```
==================== test session starts ====================
collected 5 items

tests/test_naming.py .....                              [100%]

==================== 5 passed in 0.12s ====================
```
- `.` = 통과
- `F` = 실패
- `E` = 에러 (테스트 자체의 문제)
- `s` = 스킵

#### 실패 케이스
```
==================== FAILURES ====================
________________________ test_parse_name ________________________

    def test_parse_name():
>       assert result == expected
E       AssertionError: assert 'Wrong' == 'Expected'

tests/test_naming.py:15: AssertionError
==================== 1 failed in 0.05s ====================
```

---

## 테스트 작성 가이드

### 기본 구조

```python
"""
test_example.py - Example 모듈 테스트
"""
import pytest
from pyjallib.naming import Naming


class TestNaming:
    """Naming 클래스 테스트 그룹."""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 초기화."""
        self.naming = Naming()
    
    def test_parse_name_basic(self):
        """기본 이름 파싱 테스트."""
        # Arrange (준비)
        inputName = "Chr_Hero_Sword_L_01"
        
        # Act (실행)
        result = self.naming.parse(inputName)
        
        # Assert (검증)
        assert result.realName == "Sword"
        assert result.side == "L"
    
    def test_parse_name_invalid_raises_error(self):
        """잘못된 입력 시 예외 발생 테스트."""
        with pytest.raises(ValueError):
            self.naming.parse("")
```

### Fixture 사용

```python
import pytest

@pytest.fixture
def sample_naming():
    """Naming 인스턴스 fixture."""
    return Naming()

def test_with_fixture(sample_naming):
    """Fixture를 사용한 테스트."""
    result = sample_naming.parse("Chr_Hero_01")
    assert result is not None
```

### Parametrized 테스트

```python
@pytest.mark.parametrize("input_name,expected_side", [
    ("Chr_Hero_L_01", "L"),
    ("Chr_Hero_R_01", "R"),
    ("Chr_Hero_01", None),
])
def test_side_parsing(input_name, expected_side):
    """여러 케이스를 한 번에 테스트."""
    naming = Naming()
    result = naming.parse(input_name)
    assert result.side == expected_side
```

---

## 실패 시 행동 지침

### 1. 에러 메시지 분석
- `AssertionError`: 기대값과 실제값 불일치 → 로직 확인
- `ImportError`: 모듈 임포트 실패 → 의존성 확인
- `AttributeError`: 존재하지 않는 속성 → 코드 변경 확인

### 2. 디버깅 옵션

```bash
# 실패한 테스트만 재실행
uv run pytest --lf

# 디버거 진입 (pdb)
uv run pytest --pdb

# 로컬 변수 출력
uv run pytest -l
```

### 3. 원인 파악 후 조치

| 원인 | 조치 |
|------|------|
| 테스트 코드 오류 | 테스트 수정 |
| 프로덕션 코드 버그 | `.ai_context/manuals/test_process.md` → Debug Protocol |
| 환경 문제 | `uv sync` 실행 후 재시도 |

---

## 체크리스트

- [ ] `uv run pytest` 명령어 사용 (pip/pytest 직접 사용 금지)
- [ ] 테스트 결과 로그 확인
- [ ] 모든 테스트 통과 확인
- [ ] 실패 시 원인 분석 및 기록

---

## Appendix

- **pytest 공식 문서:** https://docs.pytest.org/
- **디버깅 프로토콜:** `.ai_context/manuals/test_process.md`
- **프로젝트 테스트 디렉토리:** `tests/`
