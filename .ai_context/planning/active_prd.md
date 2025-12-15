# PRD: PyJalLib Logger loguru 기반 리팩토링

## Background & Intent
기존 standard logging 기반의 Logger 클래스를 loguru 기반으로 완전히 새로 설계한다.
- **이유:** loguru는 더 직관적인 API, 자동 rotation, 강력한 포맷팅을 제공
- **장점:** 코드 간소화, 파일 관리 자동화, 더 나은 예외 traceback 지원
- **단점:** 외부 의존성 추가 (loguru 패키지)

## Scope & Prioritization

### [Must-Have] (P0 - 이번 구현 대상)
1. `uv add loguru`로 loguru 패키지 추가
2. `pyjallib/logger.py` 완전히 새로 작성
   - loguru 래퍼 클래스로 설계
   - 생성자: `inLogPath`, `inLogFileName`, `inEnableConsole`, `inLogLevel`
   - 파일명 패턴: `{로그경로}/{파일명}_{time:YYYYMMDD}.log`
   - rotation: 10 MB, retention: 7 days
   - 메서드: `debug()`, `info()`, `warning()`, `error()`, `critical()`, `exception()`
3. `pyjallib/ue5/logger.py` 완전히 새로 작성
   - Logger 상속
   - 추가 파라미터: `inEnableUE5`
   - UE5 sink 구현 (unreal.log, log_warning, log_error)
   - 기본 파일명: `"ue5_module"`
4. ue5 모듈에서 `ue5_logger` 전역 인스턴스를 사용하는 파일들 수정
   - **수정 방침:** 전역 인스턴스 제거 후, 각 모듈에서 자체 logger 인스턴스 생성
   - 수정 대상 파일:
     - `pyjallib/ue5/__init__.py` - 전역 함수/인스턴스 export 제거, UE5Logger 클래스만 export
     - `pyjallib/ue5/templateProcessor.py` - 모듈 레벨 logger 인스턴스 생성
     - `pyjallib/ue5/disableInterchangeFrameWork.py` - 모듈 레벨 logger 인스턴스 생성
     - `pyjallib/ue5/inUnreal/baseImporter.py` - 모듈 레벨 logger 인스턴스 생성
     - `pyjallib/ue5/inUnreal/animationImporter.py` - 모듈 레벨 logger 인스턴스 생성
     - `pyjallib/ue5/inUnreal/skeletonImporter.py` - 모듈 레벨 logger 인스턴스 생성
     - `pyjallib/ue5/inUnreal/skeletalMeshImporter.py` - 모듈 레벨 logger 인스턴스 생성

### [Non-Goal] (제외 대상)
- 기존 자동 메시지 생성 기능 (`_generate_auto_message`)
- 세션 관리 기능 (`set_session`, `end_session`)
- `log_exception`, `log_pyjallib_error`, `log_function_error` 메서드
- `UE5LogHandler` 클래스 (loguru sink로 대체)
- `set_log_level()`, `set_ue5_log_level()`, `get_log_file_path()`, `set_log_file_path()` 전역 함수
- `ue5_logger` 전역 인스턴스
- 모듈 로드 시 자동 초기화 메시지

## Manual Selection
표준 코딩 워크플로우 (test 없이 진행 - UE5/3ds Max 런타임 환경 의존)

## Technical Decisions

### loguru 사용 이유
- **장점:**
  - 직관적인 API (`logger.add()`, `logger.remove()`)
  - 자동 rotation/retention 지원
  - 풍부한 traceback 정보 (`exception()` 메서드)
  - 쉬운 포맷 커스터마이징
- **단점:**
  - 외부 의존성 추가
  - 기존 standard logging과 호환성 고려 필요

### 콘솔 출력 제어 방식
loguru의 기본 stderr 핸들러(handler_id=0)를 `logger.remove()`로 제거하고, 필요시 `logger.add(sys.stderr)`로 추가하는 방식으로 구현

### ue5 모듈 logger 사용 방식 변경
- **기존:** `ue5_logger` 전역 인스턴스를 import하여 사용
- **변경:** 각 모듈에서 `UE5Logger()` 인스턴스를 모듈 레벨에서 생성하여 사용
- **이유:** 전역 인스턴스 제거로 인한 필수 변경, 각 모듈의 독립성 향상
