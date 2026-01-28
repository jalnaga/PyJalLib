# Active PRD

## Title
Logger 핸들러 격리 버그 수정 (logger.remove() 전역 제거 문제)

---

## Background & Intent

**왜 이 버그를 수정하는가?**

현재 `pyjallib.Logger` 클래스는 초기화 시 `logger.remove()`를 호출하여 loguru의 모든 기존 핸들러를 제거합니다. 이로 인해 다음 문제가 발생합니다:

1. **툴 레벨 로거가 무효화됨**: pyjallib를 사용하는 상위 툴에서 자체 Logger 인스턴스를 생성하여 로깅을 구성한 후, pyjallib의 하위 모듈이 새로운 Logger 인스턴스를 생성하면 툴의 로거 핸들러가 전부 제거됩니다.

2. **로그가 의도하지 않은 곳에 기록됨**: 툴의 로그 파일에 기록되어야 할 로그가 모듈 인스턴스 생성 시점의 로그 파일로 변경됩니다.

3. **멀티 인스턴스 환경에서 예측 불가능**: 여러 Logger 인스턴스가 생성될 때마다 이전 핸들러가 파괴되어 로그 추적이 불가능합니다.

**근본 원인**: loguru의 전역 `logger` 객체를 여러 Logger 인스턴스가 공유하면서, `logger.remove()`가 모든 핸들러를 제거하기 때문입니다.

---

## Primary Manual
`.ai_context/manuals/test_process.md`

---

## Technical Decisions & References

### 해결 방안 분석

**Option 1: 핸들러 ID 기반 제거** (초기 선택)
- `_setup_logger()`에서 `logger.remove()`를 제거하고, 자신이 등록한 핸들러 ID만 추적하여 제거
- **장점**:
  - 간단한 구현 (기존 코드 최소 수정)
  - 다른 Logger 인스턴스의 핸들러에 영향 없음
  - 명확한 핸들러 소유권 관리
- **단점**:
  - loguru 기본 핸들러(초기 stderr)는 첫 번째 Logger만 제거 가능
  - 완전한 격리가 아님 (모든 핸들러가 모든 로그를 받음)

**Option 2: 필터 기반 분리** (최종 선택)
- 각 Logger 인스턴스에 고유 ID를 부여하고 `filter` 함수로 로그 격리
- **장점**: 핸들러 충돌 완전 방지
- **단점**: 약간 더 복잡한 구현

**Option 3: loguru.Logger.bind() 사용**
- 컨텍스트 변수로 Logger 분리
- **단점**: 전역 logger 객체 공유 문제 미해결

**최종 결정**: Option 1 + Option 2 조합
- `logger.remove()` 제거 (Option 1)
- UUID + bind() + filter로 완전한 격리 (Option 2)
- 첫 인스턴스에서만 기본 핸들러 제거 (클래스 변수)

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수) ✅ 완료

1. **logger.remove() 제거 + filter 기반 격리**
   - `_setup_logger()` 메서드에서 조건부 `logger.remove()` 호출 (첫 인스턴스만)
   - UUID 기반 instance_id 생성
   - logger.bind()로 인스턴스별 바인딩
   - filter 함수로 핸들러 격리

2. **멀티 인스턴스 테스트 작성** ✅
   - 두 개의 Logger 인스턴스를 생성하여 서로의 핸들러가 유지되는지 확인
   - 각 인스턴스가 의도한 로그 파일에만 기록하는지 검증

3. **기존 기능 회귀 테스트** ✅
   - 단일 Logger 인스턴스의 기본 동작 확인
   - 파일 로깅, 콘솔 로깅, 로그 레벨 필터링 정상 작동 확인

### [Should-Have] (P1 - 권장) ✅ 완료

1. **loguru 기본 핸들러 처리 개선** ✅
   - 첫 번째 Logger 인스턴스 생성 시 기본 핸들러만 제거
   - 클래스 변수 `_default_handler_removed`로 관리

### [Nice-to-Have] (P2 - 부가)

1. **Logger 인스턴스 추적 로깅** ❌ 미구현 (불필요 판단)

### [Non-Goal] (Out of Scope)

1. ~~완전한 핸들러 격리 (필터 기반)~~ → **실제로 구현됨**
2. **loguru 대체**: 기존 loguru 의존성 유지 ✅
3. **Logger 설정 직렬화/역직렬화**: 이번 버그 수정과 무관 ✅

---

## Implementation Details

### 수정 대상 파일
- `src/pyjallib/logger.py` ✅

### 핵심 변경 사항

1. **클래스 변수 추가**:
   ```python
   class Logger:
       _default_handler_removed = False  # 기본 핸들러 제거 추적
   ```

2. **인스턴스 ID 생성 및 바인딩**:
   ```python
   import uuid

   def __init__(self, ...):
       self._instanceId = str(uuid.uuid4())
       self._logger = logger.bind(instance_id=self._instanceId)
   ```

3. **조건부 기본 핸들러 제거**:
   ```python
   def _setup_logger(self):
       if not Logger._default_handler_removed:
           logger.remove()  # 첫 인스턴스만 기본 핸들러 제거
           Logger._default_handler_removed = True
   ```

4. **Filter 함수 적용**:
   ```python
   fileHandlerId = logger.add(
       str(logFilePath),
       filter=lambda record: record["extra"].get("instance_id") == self._instanceId
   )
   ```

5. **바인딩된 logger 사용**:
   ```python
   def info(self, inMessage: str):
       self._logger.info(inMessage)  # 전역 logger 대신 self._logger 사용
   ```

### 테스트 전략
1. **Unit Test**: 멀티 인스턴스 시나리오 ✅
2. **Integration Test**: 툴-모듈 간 Logger 상호작용 (수동 검증) ✅

---

## Test Plan

### 테스트 케이스

#### TC1: 멀티 인스턴스 핸들러 격리 ✅ PASSED
```python
logger1 = Logger(inLogPath="path1", inLogFileName="log1")
logger2 = Logger(inLogPath="path2", inLogFileName="log2")

logger1.info("Message from logger1")
logger2.info("Message from logger2")

# 검증: log1 파일에 "Message from logger1"만 존재 ✅
# 검증: log2 파일에 "Message from logger2"만 존재 ✅
```

#### TC2: 콘솔 출력 격리 ✅ PASSED
```python
logger1 = Logger(inEnableConsole=True)
logger2 = Logger(inEnableConsole=False)

# 검증: logger1의 콘솔 핸들러가 logger2 생성 후에도 유지됨 ✅
# 검증: logger1 메시지가 콘솔에 정확히 한 번만 출력됨 ✅
```

#### TC3: 기존 기능 회귀 테스트 ✅ PASSED
```python
logger = Logger()
logger.debug("debug")
logger.info("info")
logger.error("error")

# 검증: 모든 레벨의 로그가 정상 기록됨 ✅
```

#### TC4: 로그 레벨 필터링 ✅ PASSED
```python
logger = Logger(inLogLevel="INFO")
logger.debug("should not appear")
logger.info("should appear")

# 검증: DEBUG 메시지는 기록 안 됨 ✅
# 검증: INFO 메시지는 기록됨 ✅
```

---

## Notes

### 의사결정 근거
- **Option 2 추가 구현 이유**: Option 1만으로는 완전한 격리가 불가능 (모든 핸들러가 모든 로그 수신)
- **loguru bind() + filter 선택 이유**: loguru의 네이티브 기능을 활용하여 안정적이고 명확한 격리 구현

### 리스크 및 완화
- **기존 코드 영향**: `logger.remove()` 조건부 실행으로 기본 핸들러 남을 수 있음
  - **완화 방안**: 첫 번째 Logger 인스턴스가 기본 핸들러를 제거하도록 구현 ✅

### 참고
- loguru 문서: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.bind
- loguru 문서: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.remove

---

## Final Results

### 구현 완료 사항
1. ✅ UUID 기반 인스턴스 ID 생성
2. ✅ logger.bind()로 인스턴스별 바인딩
3. ✅ filter 함수로 핸들러 완전 격리
4. ✅ 클래스 변수로 기본 핸들러 제거 추적
5. ✅ 모든 테스트 통과 (4/4)
6. ✅ 콘솔 중복 출력 문제 해결

### 테스트 결과
```
✅ test_multi_instance_handler_isolation PASSED
✅ test_console_handler_isolation PASSED
✅ test_single_logger_basic_logging PASSED
✅ test_log_level_filtering PASSED
```

### 지식 자산화
- `logging_pattern.md`에 "멀티 인스턴스 환경에서의 격리" 섹션 추가
- `reference_map.md`에 새로운 키워드 항목 추가
