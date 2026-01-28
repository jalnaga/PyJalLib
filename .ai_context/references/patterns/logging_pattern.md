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

## 참고 자료

- pyjallib Logger 소스 코드: `pyjallib/src/pyjallib/logger.py`
- orvlib pathAndFiles: 개발 모드 확인을 위한 `isDevelopmentMode` 속성 제공
