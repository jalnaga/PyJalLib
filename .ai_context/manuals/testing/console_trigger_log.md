# Type C: 실행 기반 로그 분석 테스트 (Console Trigger + Log File)

> **적용 상황:** AI가 실행은 할 수 있으나, 터미널 출력만으로는 부족하고 생성된 로그 파일이나 데이터 파일을 뜯어봐야 검증이 가능한 경우.

## 핵심 원칙

1. **터미널에서 실행하고, 로그 파일로 검증한다.**
2. **로그 파일 경로를 테스트 코드에 명시한다.**
3. **실행 완료 후 반드시 로그 파일을 분석한다.**

---

## 실행 절차

### Step 1: 테스트 스크립트 확인

테스트 스크립트에서 로그 파일 경로를 확인한다.

```python
"""
test_perforce_integration.py - Perforce 통합 테스트
로그 파일: tests/logs/perforce_test.log
"""
import logging

# 로그 파일 경로 (이 경로를 확인할 것)
LOG_PATH = "tests/logs/perforce_test.log"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Step 2: 테스트 실행

```bash
# 테스트 스크립트 실행
uv run python tests/test_perforce_integration.py

# 또는 pytest로 실행 (출력은 로그 파일에)
uv run pytest tests/test_perforce_integration.py -v
```

**주의:** 터미널 출력은 실행 성공 여부만 확인한다. 실제 검증은 로그 파일에서 수행.

### Step 3: 로그 파일 분석

```bash
# 로그 파일 읽기
cat tests/logs/perforce_test.log

# 특정 패턴 검색
grep "ERROR" tests/logs/perforce_test.log
grep "SUCCESS" tests/logs/perforce_test.log

# 최근 N줄만 확인
tail -50 tests/logs/perforce_test.log
```

### Step 4: 결과 판정

#### 성공 기준

```log
2024-01-15 10:30:00 - test - INFO - === TEST START ===
2024-01-15 10:30:01 - test - INFO - SUCCESS: Connection established
2024-01-15 10:30:02 - test - INFO - SUCCESS: Changelist created (id: 12345)
2024-01-15 10:30:03 - test - INFO - SUCCESS: File checked out
2024-01-15 10:30:04 - test - INFO - === TEST END ===
```

- `ERROR` 또는 `FAIL` 패턴 없음
- `=== TEST END ===` 마커 존재 (정상 종료)
- 모든 단계에 `SUCCESS` 로그

#### 실패 기준

```log
2024-01-15 10:30:00 - test - INFO - === TEST START ===
2024-01-15 10:30:01 - test - INFO - SUCCESS: Connection established
2024-01-15 10:30:02 - test - ERROR - FAIL: Cannot create changelist
2024-01-15 10:30:02 - test - ERROR - P4Exception: Access denied
```

- `ERROR` 또는 `FAIL` 패턴 존재
- 예외 스택 트레이스 존재
- `=== TEST END ===` 없이 중단

---

## 테스트 스크립트 작성 가이드

### 기본 템플릿

```python
"""
test_template.py - 테스트 템플릿
로그 파일: tests/logs/template_test.log
"""
import logging
import os

# 로그 디렉토리 생성
LOG_DIR = "tests/logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "template_test.log")

# 기존 로그 초기화 (선택)
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)

# 로그 설정
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_function():
    """테스트 함수."""
    logger.info("=== TEST START ===")
    
    try:
        # Step 1
        logger.info("Step 1: Initializing...")
        # ... 초기화 코드 ...
        logger.info("SUCCESS: Step 1 completed")
        
        # Step 2
        logger.info("Step 2: Processing...")
        # ... 처리 코드 ...
        logger.info("SUCCESS: Step 2 completed")
        
        # Step 3: Verification
        logger.info("Step 3: Verifying...")
        result = True  # 검증 로직
        if result:
            logger.info("SUCCESS: Verification passed")
        else:
            logger.error("FAIL: Verification failed")
            
    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
    
    logger.info("=== TEST END ===")


if __name__ == "__main__":
    test_function()
    print(f"Test completed. Check log at: {LOG_PATH}")
```

### 복잡한 데이터 검증

```python
import json

def test_with_data_verification():
    """데이터 파일 검증 테스트."""
    logger.info("=== TEST START ===")
    
    try:
        # 데이터 생성
        output_path = "tests/output/result.json"
        generate_data(output_path)
        
        # 데이터 검증
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        # 검증 로직
        assert "expected_key" in data
        assert len(data["items"]) > 0
        
        logger.info(f"SUCCESS: Data verified - {len(data['items'])} items found")
        
    except AssertionError as e:
        logger.error(f"FAIL: Assertion failed - {e}")
    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
    
    logger.info("=== TEST END ===")
```

---

## 로그 분석 자동화

### 분석 스크립트

```python
"""
analyze_log.py - 로그 분석 유틸리티
"""
import re
import sys

def analyze_log(log_path):
    """로그 파일 분석."""
    with open(log_path, 'r') as f:
        content = f.read()
    
    # 통계 수집
    success_count = len(re.findall(r'SUCCESS:', content))
    fail_count = len(re.findall(r'FAIL:', content))
    error_count = len(re.findall(r'ERROR:', content))
    
    # 테스트 완료 여부
    completed = "=== TEST END ===" in content
    
    print(f"=== Log Analysis: {log_path} ===")
    print(f"Success: {success_count}")
    print(f"Fail: {fail_count}")
    print(f"Error: {error_count}")
    print(f"Completed: {completed}")
    
    # 결과 판정
    if fail_count == 0 and error_count == 0 and completed:
        print("Result: PASS")
        return True
    else:
        print("Result: FAIL")
        return False

if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else "tests/logs/test.log"
    analyze_log(log_path)
```

### 사용법

```bash
# 로그 분석
uv run python tests/analyze_log.py tests/logs/perforce_test.log
```

---

## 실패 시 행동 지침

### 1. 에러 패턴별 조치

| 로그 패턴 | 가능한 원인 | 조치 |
|----------|------------|------|
| `ConnectionError` | 네트워크/서비스 문제 | 서비스 상태 확인 |
| `FileNotFoundError` | 경로 오류 | 경로 확인 |
| `PermissionError` | 권한 부족 | 권한 설정 확인 |
| `AssertionError` | 검증 실패 | 기대값 vs 실제값 비교 |

### 2. 디버깅 절차

1. **로그에서 마지막 SUCCESS 확인** → 어디까지 정상 동작했는지 파악
2. **ERROR 직전 로그 확인** → 실패 컨텍스트 파악
3. **exc_info 스택 트레이스 분석** → 정확한 실패 위치 확인

### 3. 재실행 전 정리

```bash
# 로그 파일 삭제 (깨끗한 재실행)
rm tests/logs/*.log

# 출력 파일 삭제
rm tests/output/*

# 재실행
uv run python tests/test_script.py
```

---

## 체크리스트

- [ ] 테스트 스크립트에 로그 경로 명시 확인
- [ ] `uv run` 명령어로 실행
- [ ] 터미널 출력으로 실행 완료 확인
- [ ] 로그 파일 존재 확인
- [ ] 로그 파일에서 `ERROR`/`FAIL` 패턴 검색
- [ ] `=== TEST END ===` 마커 존재 확인
- [ ] 최종 결과 판정 및 기록

---

## Appendix

- **테스트 로그 디렉토리:** `tests/logs/`
- **테스트 출력 디렉토리:** `tests/output/`
- **테스트 프로세스 개요:** `.ai_context/manuals/test_process.md`
- **디버깅 프로토콜:** `.ai_context/manuals/debug_process.md`
