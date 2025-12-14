# Type B: 유저 주도 테스트 (User Action + Log)

> **적용 상황:** AI가 직접 실행할 수 없는 환경(3DS Max, Unreal Engine 5, 특정 하드웨어 등)이거나, 유저의 인터랙션이 필수적인 경우.

## 핵심 원칙

1. **AI는 절대 직접 실행하지 않는다.** 유저에게 명확한 지시를 제공한다.
2. **로그 파일 위치를 사전에 지정한다.** 결과 분석을 위해 필수.
3. **유저 피드백을 기다린 후 다음 단계로 진행한다.**

---

## 로그 파일 경로

| 환경 | 기본 로그 경로 |
|------|---------------|
| 3DS Max | `tests/logs/test_max_*.log` |
| Unreal Engine 5 | `tests/logs/test_ue5_*.log` |
| 일반 | `tests/logs/*.log` |

---

## 실행 절차

### Step 1: 테스트 스크립트 작성

환경에 맞는 템플릿을 사용한다.

**3DS Max:**
```python
from pymxs import runtime as rt
import logging

logging.basicConfig(filename='tests/logs/test_max.log', level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    logger.info("=== TEST START ===")
    try:
        nodes = rt.selection
        logger.info(f"SUCCESS: Selected {len(nodes)} nodes")
    except Exception as e:
        logger.error(f"ERROR: {e}")
    logger.info("=== TEST END ===")

run_test()
```

**Unreal Engine 5:**
```python
import unreal
import logging

logging.basicConfig(filename='tests/logs/test_ue5.log', level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    logger.info("=== TEST START ===")
    try:
        assets = unreal.EditorAssetLibrary.list_assets('/Game/')
        logger.info(f"SUCCESS: Found {len(assets)} assets")
    except Exception as e:
        logger.error(f"ERROR: {e}")
    logger.info("=== TEST END ===")

run_test()
```

### Step 2: 유저에게 실행 요청

```
## 테스트 실행 요청

**환경:** 3DS Max 2024
**스크립트 위치:** `tests/max/test_skeleton_max.py`
**로그 파일:** `tests/logs/test_max.log`

### 실행 방법
1. 3DS Max를 실행합니다.
2. MAXScript > Script Editor를 엽니다.
3. 위 스크립트 파일을 열고 실행합니다.
4. 완료 후 알려주세요.
```

### Step 3: 결과 대기

**중요:** 유저가 실행 완료를 알릴 때까지 다음 단계로 진행하지 않는다.

### Step 4: 로그 파일 분석

```bash
cat tests/logs/test_max.log
```

| 로그 패턴 | 의미 | 조치 |
|----------|------|------|
| `SUCCESS:` | 테스트 통과 | 다음 단계 진행 |
| `FAIL:` | 테스트 실패 | 원인 분석 |
| `ERROR:` | 예외 발생 | 스택 트레이스 확인 |

---

## 실패 시 행동 지침

| 유저 피드백 | 가능한 원인 | 조치 |
|------------|------------|------|
| "모듈을 찾을 수 없습니다" | 패키지 미설치 | `uv pip install -e .` 안내 |
| "MaxScript 에러" | pymxs 문법 오류 | 코드 검토 |
| "실행은 됐는데 결과가 없어요" | 로그 경로 오류 | 로그 경로 확인 |

---

## 체크리스트

- [ ] 테스트 스크립트에 로그 설정 포함
- [ ] 로그 파일 경로 명확히 지정
- [ ] 유저에게 명확한 실행 지침 제공
- [ ] 유저 완료 응답 대기
- [ ] 로그 파일 분석 완료
- [ ] 결과 기록