# Type B: 유저 주도 테스트 (User Action + Log)

> **적용 상황:** AI가 직접 실행할 수 없는 환경(3DS Max, Unreal Engine 5, 특정 하드웨어 등)이거나, 유저의 인터랙션이 필수적인 경우.

## 핵심 원칙

1. **AI는 절대 직접 실행하지 않는다.** 유저에게 명확한 지시를 제공한다.
2. **로그 파일 위치를 사전에 지정한다.** 결과 분석을 위해 필수.
3. **유저 피드백을 기다린 후 다음 단계로 진행한다.**

---

## 실행 절차

### Step 1: 테스트 준비

#### 1-1. 테스트 스크립트 작성

테스트 대상 환경에 맞는 스크립트를 작성한다.

**3DS Max 예시:**
```python
"""
test_skeleton_max.py - 3DS Max 환경 테스트 스크립트
유저가 3DS Max Script Editor에서 실행
"""
from pyjallib.max import Skeleton, Name
import logging

# 로그 설정 (분석을 위해 파일로 저장)
logging.basicConfig(
    filename='D:/logs/test_skeleton_result.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_test():
    """테스트 실행 함수."""
    logger.info("=== TEST START ===")
    
    try:
        # Arrange
        skeleton = Skeleton()
        
        # Act
        result = skeleton.get_bones()
        
        # Assert & Log
        if result is not None:
            logger.info(f"SUCCESS: get_bones returned {len(result)} bones")
        else:
            logger.error("FAIL: get_bones returned None")
            
    except Exception as e:
        logger.error(f"ERROR: {e}")
    
    logger.info("=== TEST END ===")

if __name__ == "__main__":
    run_test()
```

#### 1-2. 로그 파일 경로 지정

| 환경 | 기본 로그 경로 |
|------|---------------|
| 3DS Max | `D:/logs/test_max_*.log` |
| Unreal Engine 5 | `D:/logs/test_ue5_*.log` |
| 일반 | `./tests/logs/*.log` |

### Step 2: 유저에게 실행 요청

**요청 템플릿:**

```
## 테스트 실행 요청

**환경:** 3DS Max 2024
**스크립트 위치:** `tests/max/test_skeleton_max.py`
**로그 파일:** `D:/logs/test_skeleton_result.log`

### 실행 방법
1. 3DS Max를 실행합니다.
2. MAXScript > Script Editor를 엽니다.
3. 위 스크립트 파일을 열고 실행합니다.
4. 완료 후 알려주세요.

### 확인 사항
- 실행 중 에러 메시지가 있었나요?
- 예상한 결과가 나왔나요?
```

### Step 3: 결과 대기

**중요:** 유저가 실행 완료를 알릴 때까지 다음 단계로 진행하지 않는다.

유저 응답 예시:
- "완료했습니다."
- "에러가 발생했습니다: [에러 내용]"
- "결과가 예상과 다릅니다: [상세 내용]"

### Step 4: 로그 파일 분석

유저가 완료를 알리면 로그 파일을 읽어 분석한다.

```bash
# 로그 파일 읽기
cat D:/logs/test_skeleton_result.log
```

#### 로그 분석 기준

| 로그 패턴 | 의미 | 조치 |
|----------|------|------|
| `SUCCESS:` | 테스트 통과 | 다음 단계 진행 |
| `FAIL:` | 테스트 실패 | 원인 분석 |
| `ERROR:` | 예외 발생 | 스택 트레이스 확인 |
| `WARNING:` | 경고 | 심각도 판단 |

---

## 테스트 스크립트 작성 가이드

### 필수 구성 요소

```python
import logging

# 1. 로그 설정 (필수)
logging.basicConfig(
    filename='지정된_로그_경로.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. 테스트 시작/종료 마커 (필수)
logger.info("=== TEST START ===")
# ... 테스트 코드 ...
logger.info("=== TEST END ===")

# 3. 명확한 결과 로깅 (필수)
logger.info("SUCCESS: 설명")  # 성공
logger.error("FAIL: 설명")    # 실패
logger.error("ERROR: 설명")   # 에러
```

### 환경별 템플릿

#### 3DS Max

```python
from pymxs import runtime as rt
import logging

logging.basicConfig(filename='D:/logs/test_max.log', level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    logger.info("=== TEST START ===")
    try:
        # 3DS Max 특화 테스트
        nodes = rt.selection
        logger.info(f"Selected nodes: {len(nodes)}")
    except Exception as e:
        logger.error(f"ERROR: {e}")
    logger.info("=== TEST END ===")

run_test()
```

#### Unreal Engine 5

```python
import unreal
import logging

logging.basicConfig(filename='D:/logs/test_ue5.log', level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    logger.info("=== TEST START ===")
    try:
        # UE5 특화 테스트
        assets = unreal.EditorAssetLibrary.list_assets('/Game/')
        logger.info(f"SUCCESS: Found {len(assets)} assets")
    except Exception as e:
        logger.error(f"ERROR: {e}")
    logger.info("=== TEST END ===")

run_test()
```

---

## 실패 시 행동 지침

### 1. 유저 피드백 기반 분석

| 유저 피드백 | 가능한 원인 | 조치 |
|------------|------------|------|
| "모듈을 찾을 수 없습니다" | 패키지 미설치 | `uv pip install -e .` 안내 |
| "MaxScript 에러" | pymxs 문법 오류 | 코드 검토 |
| "실행은 됐는데 결과가 없어요" | 로그 경로 오류 | 로그 경로 확인 |

### 2. 추가 정보 요청

필요시 유저에게 추가 정보를 요청한다:

```
추가 정보가 필요합니다:
1. 3DS Max 버전이 어떻게 되나요?
2. 스크립트 실행 시 콘솔에 출력된 내용이 있나요?
3. 로그 파일이 생성되었나요?
```

---

## 체크리스트

- [ ] 테스트 스크립트에 로그 설정 포함
- [ ] 로그 파일 경로 명확히 지정
- [ ] 유저에게 명확한 실행 지침 제공
- [ ] 유저 완료 응답 대기
- [ ] 로그 파일 분석 완료
- [ ] 결과 기록

---

## Appendix

- **3DS Max pymxs 문서:** 3DS Max 내장 Help
- **UE5 Python API:** https://docs.unrealengine.com/5.0/en-US/PythonAPI/
- **테스트 프로세스 개요:** `.ai_context/manuals/test_process.md`
