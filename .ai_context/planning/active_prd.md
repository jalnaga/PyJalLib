# PRD: UE5Logger 독립 클래스 리팩토링

## Background & Intent

**왜 이 작업을 하는가?**

- `pyjallib.logger.Logger`가 최근 loguru 기반으로 변경됨
- 언리얼 에디터 내부에서는 Python 표준 라이브러리만 사용 가능 (외부 패키지 설치 불가)
- 언리얼 에디터의 Python 버전이 외부 환경과 달라서 sys.path 추가 방식도 불가
- 현재 `pyjallib.ue5.logger.UE5Logger`는 `pyjallib.Logger`를 상속받아 존재하지 않는 속성(`self._logger`, `self._get_formatter()`)에 접근하므로 동작하지 않음

**해결 방향:**

UE5Logger를 pyjallib.Logger 상속 없이 완전히 독립적인 클래스로 재작성하여, Python 표준 logging 모듈만으로 동작하도록 함.

---

## Primary Manual

`.ai_context/manuals/module_replacement.md`

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)

1. **UE5Logger 독립 클래스 재작성**
   - `pyjallib.Logger` 상속 제거
   - Python 표준 `logging` 모듈만 사용 (loguru 의존성 완전 제거)

2. **pyjallib.Logger와 동일한 API 제공**
   - `debug(inMessage)`, `info(inMessage)`, `warning(inMessage)`
   - `error(inMessage)`, `critical(inMessage)`, `exception(inMessage)`
   - `remove_handlers()`

3. **pyjallib.Logger와 동일한 로그 파일 설정**
   - 기본 경로: `Documents/PyJalLib/logs/`
   - 파일명 패턴: `{파일명}_{YYYYMMDD}.log` (기본 파일명: `ue5`)
   - 인코딩: `utf-8`

4. **기존 UE5 전용 기능 유지**
   - `UE5LogHandler` 클래스 (unreal.log 연동)
   - `set_ue5_log_level(inLevel)` 메서드
   - `enable_ue5_output(inEnable)` 메서드

5. **기존 하위 호환 함수 유지**
   - `set_log_level(inLevel)` - 모듈 레벨 함수
   - `set_ue5_log_level(inLevel)` - 모듈 레벨 함수
   - `get_log_file_path()` - 모듈 레벨 함수
   - `set_log_file_path(inLogFolder, inLogFilename)` - 모듈 레벨 함수

6. **전역 인스턴스 유지**
   - `ue5_logger` 전역 인스턴스

### [Should-Have] (P1 - 권장)

1. **표준 logging으로 가능한 범위 내에서 rotation 고려**
   - `logging.handlers.RotatingFileHandler` 또는 `TimedRotatingFileHandler` 활용 검토
   - 단, 필수 요구사항은 아니며 구현 복잡도가 높으면 생략

### [Nice-to-Have] (P2 - 부가)

- 없음

### [Non-Goal] (Out of Scope)

1. **loguru 기능 완전 동일 구현**
   - rotation, retention, compression 등 loguru 고급 기능은 표준 logging의 한계 내에서만 구현
   
2. **pyjallib.Logger와의 상속 관계 유지**
   - 완전한 독립 클래스로 구현 (상속 불필요)

3. **기존 pyjallib.Logger 수정**
   - pyjallib.Logger는 현재 상태 유지

---

## Interface Contract

### UE5Logger 클래스

```
UE5Logger
├── __init__(inLogPath: Optional[str], inLogFileName: Optional[str], 
│            inEnableConsole: bool, inEnableUE5: bool, inLogLevel: str)
├── debug(inMessage: str) -> None
├── info(inMessage: str) -> None
├── warning(inMessage: str) -> None
├── error(inMessage: str) -> None
├── critical(inMessage: str) -> None
├── exception(inMessage: str) -> None
├── remove_handlers() -> None
├── set_ue5_log_level(inLevel: str) -> None
└── enable_ue5_output(inEnable: bool) -> None
```

### UE5LogHandler 클래스

```
UE5LogHandler (extends logging.Handler)
└── emit(record: logging.LogRecord) -> None
```

### 모듈 레벨 함수

```
set_log_level(inLevel: str) -> None
set_ue5_log_level(inLevel: str) -> None
get_log_file_path() -> str
set_log_file_path(inLogFolder: Optional[str], inLogFilename: Optional[str]) -> None
```

### 전역 인스턴스

```
ue5_logger: UE5Logger
```

---

## Breaking Change 결정

**완전 호환 유지** - 기존 코드 수정 없이 교체 가능

- 기존 API 시그니처 100% 유지
- import 경로 동일 (`from pyjallib.ue5.logger import ...`)

---

## Technical Notes

### 구현 방식

- **In-place 교체**: 기존 `src/pyjallib/ue5/logger.py` 파일을 직접 수정
- 내부 구현만 변경하고 외부 인터페이스는 유지

### 주요 변경점

| 항목 | 기존 | 변경 후 |
|------|------|---------|
| 상속 | `class UE5Logger(Logger)` | `class UE5Logger` (독립) |
| 의존성 | loguru (간접) | 표준 logging만 |
| 내부 로거 | loguru.logger | logging.Logger |


