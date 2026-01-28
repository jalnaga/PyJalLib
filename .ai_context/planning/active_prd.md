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

**Option 1: 핸들러 ID 기반 제거** (선택됨)
- `_setup_logger()`에서 `logger.remove()`를 제거하고, 자신이 등록한 핸들러 ID만 추적하여 제거
- **장점**:
  - 간단한 구현 (기존 코드 최소 수정)
  - 다른 Logger 인스턴스의 핸들러에 영향 없음
  - 명확한 핸들러 소유권 관리
- **단점**:
  - loguru 기본 핸들러(초기 stderr)는 첫 번째 Logger만 제거 가능

**Option 2: 필터 기반 분리**
- 각 Logger 인스턴스에 고유 ID를 부여하고 `filter` 함수로 로그 격리
- **장점**: 핸들러 충돌 완전 방지
- **단점**: 복잡한 구현, 성능 오버헤드

**Option 3: loguru.Logger.bind() 사용**
- 컨텍스트 변수로 Logger 분리
- **단점**: 전역 logger 객체 공유 문제 미해결

**결정**: Option 1 채택 - 핸들러 ID 기반 제거

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)

1. **logger.remove() 제거**
   - `_setup_logger()` 메서드에서 `logger.remove()` 호출 제거
   - 자신이 추가한 핸들러만 `_handlerIds`에 저장

2. **멀티 인스턴스 테스트 작성**
   - 두 개의 Logger 인스턴스를 생성하여 서로의 핸들러가 유지되는지 확인
   - 각 인스턴스가 의도한 로그 파일에 기록하는지 검증

3. **기존 기능 회귀 테스트**
   - 단일 Logger 인스턴스의 기본 동작 확인
   - 파일 로깅, 콘솔 로깅 정상 작동 확인

### [Should-Have] (P1 - 권장)

1. **loguru 기본 핸들러 처리 개선**
   - 첫 번째 Logger 인스턴스 생성 시 기본 핸들러만 제거하는 로직 추가
   - 플래그 기반 관리 (클래스 변수)

### [Nice-to-Have] (P2 - 부가)

1. **Logger 인스턴스 추적 로깅**
   - 디버그 목적으로 각 인스턴스의 핸들러 등록/제거 로그 추가

### [Non-Goal] (Out of Scope)

1. **완전한 핸들러 격리 (필터 기반)**: 현재 버그 수정 범위를 벗어남
2. **loguru 대체**: 기존 loguru 의존성 유지
3. **Logger 설정 직렬화/역직렬화**: 이번 버그 수정과 무관

---

## Implementation Details

### 수정 대상 파일
- `src/pyjallib/logger.py`

### 핵심 변경 사항
1. `_setup_logger()` 메서드:
   ```python
   # 변경 전
   logger.remove()  # 모든 핸들러 제거

   # 변경 후
   # logger.remove() 제거 → 기존 핸들러 유지
   ```

2. `remove_handlers()` 메서드는 이미 `_handlerIds`만 제거하므로 변경 불필요

### 테스트 전략
1. **Unit Test**: 멀티 인스턴스 시나리오
2. **Integration Test**: 툴-모듈 간 Logger 상호작용

---

## Test Plan

### 테스트 케이스

#### TC1: 멀티 인스턴스 핸들러 격리
```python
logger1 = Logger(inLogPath="path1", inLogFileName="log1")
logger2 = Logger(inLogPath="path2", inLogFileName="log2")

logger1.info("Message from logger1")
logger2.info("Message from logger2")

# 검증: log1 파일에 "Message from logger1"만 존재
# 검증: log2 파일에 "Message from logger2"만 존재
```

#### TC2: 콘솔 출력 격리
```python
logger1 = Logger(inEnableConsole=True)
logger2 = Logger(inEnableConsole=False)

# 검증: logger1의 콘솔 핸들러가 logger2 생성 후에도 유지됨
```

#### TC3: 기존 기능 회귀 테스트
```python
logger = Logger()
logger.debug("debug")
logger.info("info")
logger.error("error")

# 검증: 모든 레벨의 로그가 정상 기록됨
```

---

## Notes

### 의사결정 근거
- **Option 1 선택 이유**: 최소 침습적 수정으로 버그 해결 가능
- **loguru 기본 핸들러 처리**: Should-Have로 분류 (필수 아님, 첫 Logger가 제거하면 이후 Logger는 영향 없음)

### 리스크
- **기존 코드 영향**: `logger.remove()` 제거로 loguru 기본 stderr 핸들러가 남을 수 있음
  - **완화 방안**: 첫 번째 Logger 인스턴스가 기본 핸들러를 제거하도록 개선 (Should-Have)

### 참고
- loguru 문서: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.remove
