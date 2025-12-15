# PRD: PyJalLib 코어 Logger를 loguru 기반으로 리팩토링

## 1. 개요

### 1.1 목적
기존 Python standard logging 기반의 코어 `logger.py`를 loguru 기반으로 완전히 새로 설계한다.

### 1.2 배경
- 기존 logger는 Python 표준 logging 모듈 사용
- loguru는 더 간결한 API와 강력한 기능 제공 (자동 rotation, retention, 포매팅 등)
- 코드 간소화 및 유지보수성 향상 목적

### 1.3 작업 대상
- `src/pyjallib/logger.py` (코어만)
- UE5 logger (`src/pyjallib/ue5/logger.py`)는 수정하지 않음

---

## 2. 요구사항 분류

### 2.1 Must-Have (필수)

#### M1. 의존성 추가
- `uv add loguru`로 loguru 패키지 추가

#### M2. Logger 클래스 재설계
```python
from loguru import logger

class Logger:
    """PyJalLib 로깅 클래스 - loguru 래퍼"""
```

#### M3. 생성자 파라미터
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| inLogPath | Optional[str] | None | 로그 파일 경로. None이면 `Documents/PyJalLib/logs/` |
| inLogFileName | Optional[str] | None | 로그 파일명. None이면 `"pyjallib"` |
| inEnableConsole | bool | True | 콘솔(stderr) 출력 활성화 |
| inLogLevel | str | "DEBUG" | 로깅 레벨 |

#### M4. 파일 로깅 설정
- 파일명 패턴: `{로그경로}/{파일명}_{time:YYYYMMDD}.log`
- rotation: 10 MB
- retention: 7 days
- 포맷: loguru 기본 포맷 사용

#### M5. 제공 메서드
- `debug(inMessage: str)` 
- `info(inMessage: str)`
- `warning(inMessage: str)`
- `error(inMessage: str)`
- `critical(inMessage: str)`
- `exception(inMessage: str)` - 예외 traceback 포함 로깅

#### M6. 콘솔 출력 제어
- 생성자의 `inEnableConsole` 파라미터로 초기 설정
- loguru 기본 stderr 핸들러를 제거/추가하는 방식으로 구현

### 2.2 Should-Have (권장)

#### S1. 타입 힌트
- 모든 메서드에 완전한 타입 힌트 제공

#### S2. Docstring
- Google style docstring
- 한국어로 작성

### 2.3 Nice-to-Have (선택)

- 없음 (최소한의 기능만 구현)

### 2.4 Non-Goal (비목표)

#### NG1. UE5 Logger 수정 안 함
- `src/pyjallib/ue5/logger.py`는 이 작업에서 수정하지 않음

#### NG2. 기존 세션 기능 제외
- 기존 Logger의 `set_session()`, `end_session()` 메서드는 새 설계에서 제외

#### NG3. 기존 코드 호환성
- 완전 새 설계이므로 기존 API와의 하위 호환성은 고려하지 않음

---

## 3. 기술 결정 사항

### 3.1 loguru 선택 이유
**장점:**
- 간결한 API (별도 핸들러 설정 불필요)
- 자동 rotation/retention 지원
- 예외 traceback 자동 포맷팅
- 컬러 출력 기본 지원

**단점:**
- 추가 의존성 발생
- 표준 logging과 완전히 다른 API

### 3.2 콘솔 출력 제어 방식
- loguru는 기본적으로 stderr에 출력하는 핸들러가 있음
- `inEnableConsole=False`일 때 이 기본 핸들러를 제거
- `logger.remove()` → 모든 핸들러 제거 후 필요한 것만 추가하는 방식

---

## 4. 코딩 스타일

- 클래스: PascalCase
- 함수: snake_case  
- 변수: camelCase
- 파라미터: in* prefix
- 주석/docstring: 한국어
- docstring 스타일: Google style

---

## 5. 작업 순서 (예상)

1. `uv add loguru`로 의존성 추가
2. 테스트 파일 작성 (TDD)
3. `pyjallib/logger.py` 완전히 새로 작성
4. 테스트 통과 확인
5. 린트 검사

---

## 6. 검증 기준

- [ ] `uv run pytest` 통과
- [ ] `uv run ruff check .` 통과
- [ ] Logger 클래스 정상 동작 확인

