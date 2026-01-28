# Active PRD

## Title
로깅 시스템 개선: print문을 pyjallib Logger로 교체

---

## Background & Intent

**왜 이 기능을 만드는가?**

현재 AnimExporter 프로젝트의 대부분의 로깅이 `print()` 문으로 되어 있어 다음과 같은 문제가 있습니다:

1. **로그 레벨 제어 불가:** 디버그 메시지와 에러 메시지가 동일하게 출력되어 중요한 정보를 찾기 어려움
2. **파일 로깅 부재:** 콘솔 출력만 가능하고 파일로 기록되지 않아 사후 분석이 어려움
3. **개발/프로덕션 환경 구분 불가:** 개발 중에는 상세한 로그가 필요하지만 실제 사용 시에는 필요한 정보만 표시해야 함
4. **표준화 부재:** pyjallib의 표준 Logger 모듈이 있음에도 사용하지 않아 일관성이 부족함

AGENTS.md의 지침에 따라 pyjallib.logger 모듈을 사용하여 로깅을 표준화하고, 개발 모드에 따라 적절한 로그 레벨을 자동으로 설정합니다.

---

## Primary Manual
`.ai_context/manuals/task_loop.md`

---

## Technical Decisions & References

### 1. Logger 인스턴스 관리 (Singleton Pattern)
- **결정:** logger_config.py 모듈을 생성하여 전역 Logger 인스턴스를 제공
- **이유:**
  - 모든 모듈에서 동일한 Logger 인스턴스를 공유하여 일관된 로깅 설정 보장
  - 각 모듈에서 Logger 인스턴스를 개별 생성하면 파일 핸들러가 중복 생성되어 리소스 낭비
- **대안 고려:**
  - ❌ 각 모듈에서 Logger 인스턴스 개별 생성 → 파일 핸들러 중복, 설정 불일치
  - ✅ Singleton 패턴으로 전역 인스턴스 제공 → 일관성 보장, 리소스 효율적

### 2. 로그 레벨 자동 설정
- **결정:** `pathAndFiles.default.isDevelopmentMode` 값에 따라 자동으로 로그 레벨 설정
- **개발 모드:** DEBUG 레벨 (모든 로그 출력)
- **프로덕션 모드:** INFO 레벨 (INFO, WARNING, ERROR, CRITICAL만 출력)
- **이유:** 환경에 따라 자동으로 적절한 로그 레벨을 설정하여 개발자가 수동으로 변경할 필요 없음

### 3. print문 교체 원칙
- **DEBUG 레벨로 교체할 대상:**
  - `[DEBUG]`, `[INFO]` 접두사가 있는 print문
  - 상세한 진행 상황, 파일 경로, 변수 값 출력
  - 개발/디버깅 용도의 출력

- **INFO 레벨로 교체할 대상:**
  - 일반적인 정보성 메시지
  - 작업 완료 알림 (`[SUCCESS]`, `[INFO]` 접두사)
  - 사용자가 알아야 할 진행 상황

- **WARNING 레벨로 교체할 대상:**
  - `[WARNING]` 접두사가 있는 print문
  - 잠재적 문제 상황 알림

- **ERROR 레벨로 교체할 대상:**
  - `[ERROR]` 접두사가 있는 print문
  - 예외 상황, 실패 메시지
  - traceback.print_exc() 호출 → logger.exception() 사용

### 4. 로그 파일 위치
- **경로:** `Documents/PyJalLib/logs/AnimExporter_{YYYYMMDD}.log`
- **관리:** pyjallib Logger가 자동으로 로테이션 (10MB, 7일 보관)

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)

1. **logger_config.py 모듈 생성**
   - Singleton 패턴으로 전역 Logger 인스턴스 제공
   - isDevelopmentMode에 따라 DEBUG/INFO 레벨 자동 설정
   - 파일명: AnimExporter

2. **NewAnimExporter.py 로깅 교체**
   - print문을 logger.info/error로 교체

3. **ui_animExporter.py 로깅 교체**
   - print문을 logger.debug/info/warning/error로 교체
   - traceback.print_exc()를 logger.exception()으로 교체

4. **func_animExport.py 로깅 교체**
   - print문을 logger.info로 교체

5. **func_ue5Import.py 로깅 교체**
   - print문을 logger.debug/info/error로 교체
   - traceback.print_exc()를 logger.exception()으로 교체

### [Should-Have] (P1 - 권장)

1. **로깅 가이드 문서 작성**
   - 각 로그 레벨의 사용 기준 문서화
   - reference 폴더에 logging_guide.md 추가

### [Nice-to-Have] (P2 - 부가)

1. **로그 포맷 커스터마이징**
   - 로그 메시지에 컨텍스트 정보 추가 (함수명, 라인 번호 등)
   - 컬러 로그 출력 (개발 모드에서만)

### [Non-Goal] (Out of Scope)

1. **기존 orvlib 또는 pyjallib 라이브러리의 로깅 변경**
   - 외부 라이브러리는 수정하지 않음
   - AnimExporter 프로젝트 내부만 변경

2. **로그 분석 도구 개발**
   - 로그 파일을 분석하는 별도 도구는 개발하지 않음

3. **로그 서버 연동**
   - 원격 로그 서버나 중앙 집중식 로그 관리는 범위 밖

4. **성능 프로파일링 로깅**
   - 실행 시간 측정이나 성능 메트릭은 별도 작업

---

## Implementation Details

### 파일 구조
```
src/
├── logger_config.py          # 신규 생성
├── NewAnimExporter.py         # 수정
├── ui_animExporter.py         # 수정
├── func_animExport.py         # 수정
├── func_ue5Import.py          # 수정
└── func_animValidation.py     # 변경 없음 (print문 없음)
```

### logger_config.py 설계
```python
from orvlib import pathAndFiles
from pyjallib.logger import Logger

_logger_instance = None

def get_logger() -> Logger:
    """AnimExporter 전역 로거 인스턴스를 반환합니다."""
    global _logger_instance

    if _logger_instance is None:
        logLevel = "DEBUG" if pathAndFiles.default.isDevelopmentMode else "INFO"
        _logger_instance = Logger(
            inLogPath=None,  # 기본 경로 사용
            inLogFileName="AnimExporter",
            inEnableConsole=True,
            inLogLevel=logLevel
        )

    return _logger_instance
```

### 각 파일별 변경 사항

**NewAnimExporter.py:**
- Line 108: `print(f"User Role 읽기 실패...")` → `logger.error(...)`

**ui_animExporter.py:**
- Line 305: `print(f"[INFO] 원래 MAX 파일...")` → `logger.info(...)`
- Line 338: `print("[INFO] UE5 임포트된 파일...")` → `logger.debug(...)`
- Line 346-348: `print("[WARNING] .uasset 파일...")` → `logger.warning(...)`
- Line 355: `print(f"[INFO] UE5 임포트된 파일...")` → `logger.info(...)`
- Line 367: `print(f"[SUCCESS] {message}")` → `logger.info(...)`
- Line 369: `print(f"[ERROR] 체인지리스트...")` → `logger.error(...)`
- Line 373: `print(f"[ERROR] _move_imported_assets...")` → `logger.error(...)`
- Line 375: `traceback.print_exc()` → `logger.exception(...)`

**func_animExport.py:**
- Line 343: `print(f"Changelist 생성...")` → `logger.info(...)`
- Line 346: `print(f"CheckOut files...")` → `logger.info(...)`
- Line 350: `print(f"Adding new files...")` → `logger.info(...)`

**func_ue5Import.py:**
- Line 199: `print(f"임시 스크립트 파일...")` → `logger.warning(...)`
- Line 290-292: `print("[DEBUG] move_assets...")` → `logger.debug(...)`
- Line 295-375: 모든 `[DEBUG]` print문을 `logger.debug(...)`로 교체
- Line 365-366: `traceback.format_exc()` → `logger.exception(...)`

---

## Test Plan

### 1. 기능 테스트
- [ ] 개발 모드에서 DEBUG 레벨 로그가 출력되는지 확인
- [ ] 프로덕션 모드에서 INFO 이상 로그만 출력되는지 확인
- [ ] 로그 파일이 `Documents/PyJalLib/logs/`에 생성되는지 확인

### 2. 통합 테스트
- [ ] NewAnimExporter 실행 시 에러 없이 로거가 초기화되는지 확인
- [ ] 파일 저장 프로세스 전체를 실행하여 모든 로그가 정상 출력되는지 확인
- [ ] UE5 임포트 프로세스에서 예외 발생 시 logger.exception()이 정상 동작하는지 확인

### 3. 회귀 테스트
- [ ] 기존 기능이 모두 정상 동작하는지 확인 (print문 교체로 인한 부작용 없음)
- [ ] 에러 메시지가 사용자에게 정상적으로 표시되는지 확인

---

## Notes

### 고려 사항
1. **pyjallib.logger 의존성:** pyjallib 패키지가 이미 설치되어 있으므로 추가 의존성 없음
2. **orvlib.pathAndFiles 의존성:** 개발 모드 확인을 위해 필요하며 이미 사용 중
3. **기존 코드 호환성:** print문 교체이므로 기존 로직에 영향 없음
4. **한글 로그 지원:** pyjallib Logger가 UTF-8 인코딩을 사용하므로 한글 로그 지원

### 의사결정 근거
- **왜 Singleton 패턴?**
  - 대안: 각 모듈에서 Logger 인스턴스 생성 → ❌ 파일 핸들러 중복, 설정 불일치
  - 선택: 전역 인스턴스 사용 → ✅ 리소스 효율적, 일관된 설정

- **왜 자동 로그 레벨 설정?**
  - 대안: 수동으로 로그 레벨 설정 → ❌ 개발자가 매번 변경 필요, 실수 가능
  - 선택: isDevelopmentMode 기반 자동 설정 → ✅ 환경에 맞는 로그 자동 적용
