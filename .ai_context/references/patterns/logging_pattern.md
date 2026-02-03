# Logging Pattern (pyjallib Logger)

프로젝트 전체에서 일관된 로깅을 제공하기 위한 Singleton 패턴 기반 Logger 관리 가이드입니다.

---

## Why (왜 이 패턴을 사용하는가)

### 문제 상황
- `print()` 문으로 로깅하면 로그 레벨 제어가 불가능
- 각 모듈에서 Logger 인스턴스를 개별 생성하면 파일 핸들러가 중복 생성되어 리소스 낭비
- 개발 환경과 프로덕션 환경에서 로그 레벨을 수동으로 변경해야 하는 불편함

### 솔루션
- **Singleton 패턴**으로 전역 Logger 인스턴스를 제공
- **개발 모드 자동 감지**를 통한 로그 레벨 자동 설정
- **pyjallib.logger.Logger** 사용으로 파일 로깅, 로그 레벨, 로테이션 등의 기능 자동 제공

---

## How (어떻게 사용하는가)

### 1. logger_config.py 모듈 구조

전역 Logger 인스턴스를 관리하는 중앙 설정 모듈을 생성합니다.

```python
# src/logger_config.py
from orvlib import pathAndFiles
from pyjallib.logger import Logger

_logger_instance = None

def get_logger() -> Logger:
    """
    AnimExporter 전역 로거 인스턴스를 반환합니다.

    Singleton 패턴을 사용하여 애플리케이션 전체에서 동일한 Logger 인스턴스를 공유합니다.
    개발 모드에 따라 로그 레벨이 자동으로 설정됩니다:
    - 개발 모드(isDevelopmentMode=True): DEBUG 레벨
    - 프로덕션 모드(isDevelopmentMode=False): INFO 레벨

    Returns:
        Logger: pyjallib Logger 인스턴스

    Example:
        >>> from logger_config import get_logger
        >>> logger = get_logger()
        >>> logger.info("작업 완료")
        >>> logger.debug("디버그 정보")
    """
    global _logger_instance

    if _logger_instance is None:
        logLevel = "DEBUG" if pathAndFiles.default.isDevelopmentMode else "INFO"
        _logger_instance = Logger(
            inLogPath=None,  # 기본 경로 사용 (Documents/PyJalLib/logs/)
            inLogFileName="AnimExporter",  # 프로젝트명으로 로그 파일명 설정
            inEnableConsole=True,  # 콘솔 출력 활성화
            inLogLevel=logLevel  # 개발 모드에 따라 자동 설정
        )

    return _logger_instance
```

### 2. 각 모듈에서 Logger 사용

모든 모듈에서 `get_logger()`를 호출하여 동일한 Logger 인스턴스를 사용합니다.

```python
# src/your_module.py
from logger_config import get_logger

logger = get_logger()

def some_function():
    logger.info("함수 실행 시작")
    try:
        # 작업 수행
        logger.debug("상세 디버그 정보")
        logger.info("작업 완료")
    except Exception as e:
        logger.exception("예외 발생")  # 자동으로 스택 트레이스 포함
```

---

## 로그 레벨 선택 기준

각 상황에 맞는 로그 레벨을 선택하여 사용합니다.

| 로그 레벨 | 사용 상황 | 예시 |
|:---|:---|:---|
| **DEBUG** | 개발/디버깅 용도의 상세 정보 | 파일 경로, 변수 값, 함수 호출 순서 |
| **INFO** | 일반적인 정보성 메시지 | 작업 완료 알림, 사용자 액션 기록 |
| **WARNING** | 잠재적 문제 상황 | 파일을 찾을 수 없음 (기능은 계속 동작) |
| **ERROR** | 에러 상황 (기능 실패) | 파일 저장 실패, API 호출 실패 |
| **EXCEPTION** | 예외 발생 (스택 트레이스 포함) | try-except 블록에서 예외 처리 시 |

### 기존 print문 교체 가이드

```python
# Before (print 사용)
print(f"[DEBUG] 파일 경로: {file_path}")
print(f"[INFO] 작업 완료")
print(f"[WARNING] 파일을 찾을 수 없음: {file}")
print(f"[ERROR] 저장 실패: {error}")
traceback.print_exc()

# After (logger 사용)
logger.debug(f"파일 경로: {file_path}")
logger.info("작업 완료")
logger.warning(f"파일을 찾을 수 없음: {file}")
logger.error(f"저장 실패: {error}")
logger.exception("예외 발생")  # 자동으로 스택 트레이스 포함
```

---

## 자동 제공 기능

pyjallib Logger를 사용하면 다음 기능이 자동으로 제공됩니다:

1. **파일 로깅**
   - 경로: `Documents/PyJalLib/logs/AnimExporter_{YYYYMMDD}.log`
   - 자동 로테이션: 파일 크기 10MB 초과 시
   - 보관 기간: 최근 7일

2. **로그 포맷**
   - 타임스탬프, 로그 레벨, 메시지가 자동으로 포맷팅됨
   - 예: `2026-01-28 14:30:25 [INFO] 작업 완료`

3. **한글 지원**
   - UTF-8 인코딩으로 한글 로그 정상 지원

---

## Best Practices

1. **모듈 최상단에서 logger 획득**
   ```python
   from logger_config import get_logger
   logger = get_logger()  # 모듈 레벨에서 한 번만 호출
   ```

2. **개발 모드에서만 보고 싶은 정보는 DEBUG 사용**
   ```python
   logger.debug(f"내부 변수 값: {variable}")  # 프로덕션에서는 출력 안 됨
   ```

3. **예외 처리 시 logger.exception() 사용**
   ```python
   try:
       # 작업 수행
   except Exception as e:
       logger.exception("작업 실패")  # 자동으로 스택 트레이스 포함
   ```

4. **사용자에게 보여줄 정보는 INFO 이상 사용**
   ```python
   logger.info("파일 저장 완료")  # 개발/프로덕션 모두 출력
   ```

---

## 멀티 인스턴스 환경에서의 격리

**업데이트: 2026-01-28**

### 문제 상황

여러 Logger 인스턴스를 생성하는 환경(예: 툴이 pyjallib를 사용하고, pyjallib 내부 모듈도 각자 Logger를 생성)에서 다음 문제가 발생할 수 있습니다:

1. **핸들러 간섭**: 새로운 Logger 인스턴스 생성 시 기존 인스턴스의 핸들러가 영향을 받음
2. **로그 혼선**: 한 Logger의 로그가 다른 Logger의 파일에 기록됨
3. **콘솔 중복 출력**: loguru 기본 핸들러로 인한 중복 출력

### 솔루션: 인스턴스별 격리

pyjallib Logger는 다음 기법을 사용하여 완전한 인스턴스 격리를 보장합니다:

#### 1. UUID 기반 인스턴스 식별

```python
import uuid
from loguru import logger

class Logger:
    def __init__(self, ...):
        # 인스턴스 고유 ID 생성
        self._instanceId = str(uuid.uuid4())

        # 인스턴스별 바인딩된 logger 생성
        self._logger = logger.bind(instance_id=self._instanceId)
```

#### 2. Filter 기반 핸들러 격리

각 핸들러에 filter 함수를 적용하여 자신의 instance_id를 가진 로그만 처리합니다:

```python
def _setup_logger(self):
    # 파일 핸들러 - 자신의 instance_id만 처리
    fileHandlerId = logger.add(
        str(logFilePath),
        level=self._logLevel,
        filter=lambda record: record["extra"].get("instance_id") == self._instanceId
    )

    # 콘솔 핸들러 - 자신의 instance_id만 처리
    if self._enableConsole:
        consoleHandlerId = logger.add(
            sys.stderr,
            level=self._logLevel,
            filter=lambda record: record["extra"].get("instance_id") == self._instanceId
        )
```

#### 3. 기본 핸들러 관리

loguru는 기본적으로 stderr 핸들러를 가지고 있습니다. 첫 번째 Logger 인스턴스에서만 이를 제거하여 중복 출력을 방지합니다:

```python
class Logger:
    # 클래스 변수: 기본 핸들러 제거 여부 추적
    _default_handler_removed = False

    def _setup_logger(self):
        # 첫 번째 Logger 인스턴스인 경우에만 기본 핸들러 제거
        if not Logger._default_handler_removed:
            logger.remove()  # 기본 stderr 핸들러 제거
            Logger._default_handler_removed = True
```

### 동작 원리

1. **logger1 생성**:
   - instance_id = "uuid-1" 생성
   - 기본 핸들러 제거 (첫 인스턴스)
   - file1 핸들러 추가 (filter: instance_id == "uuid-1")
   - console1 핸들러 추가 (filter: instance_id == "uuid-1")

2. **logger2 생성**:
   - instance_id = "uuid-2" 생성
   - 기본 핸들러는 이미 제거됨 (스킵)
   - file2 핸들러 추가 (filter: instance_id == "uuid-2")
   - console2 핸들러 추가 (filter: instance_id == "uuid-2")

3. **logger1.info("message")**:
   - self._logger.info("message") 호출 → instance_id="uuid-1"로 바인딩됨
   - 전역 logger에 전달
   - file1, console1만 filter 통과하여 처리 ✅
   - file2, console2는 filter에서 차단됨 ❌

### 결과

- ✅ 각 Logger가 자신의 로그 파일에만 기록
- ✅ 콘솔 출력이 정확히 한 번만 발생
- ✅ 다른 Logger 인스턴스에 영향 없음

### 테스트 케이스

```python
# 멀티 인스턴스 격리 테스트
logger1 = Logger(inLogPath="path1", inLogFileName="log1", inEnableConsole=True)
logger2 = Logger(inLogPath="path2", inLogFileName="log2", inEnableConsole=True)

logger1.info("Message from logger1")  # → path1/log1_*.log에만 기록
logger2.info("Message from logger2")  # → path2/log2_*.log에만 기록

# logger1의 핸들러는 logger2 생성 후에도 정상 작동
logger1.info("Still working")  # ✅ 정상 출력
```

### 주의사항

1. **logger.remove() 직접 호출 금지**: 다른 인스턴스의 핸들러가 제거됩니다
2. **전역 logger 직접 사용 금지**: 반드시 `self._logger` (바인딩된 logger) 사용
3. **테스트 환경에서 격리 검증**: 멀티 인스턴스 시나리오 테스트 필수

---

## 참고 자료

- pyjallib Logger 소스 코드: `pyjallib/src/pyjallib/logger.py`
- orvlib pathAndFiles: 개발 모드 확인을 위한 `isDevelopmentMode` 속성 제공
- loguru 공식 문서: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.bind
