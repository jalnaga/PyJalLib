# Task List: UE5Logger 독립 클래스 리팩토링

**PRD:** UE5Logger 독립 클래스 리팩토링  
**Primary Manual:** `.ai_context/manuals/module_replacement.md`

---

## Implementation Tasks

### Phase 1: 클래스 독립화

- [ ] **Task 1.1**: `pyjallib.Logger` import 제거 및 UE5Logger 클래스 선언부 독립화
  - `from pyjallib.logger import Logger` 제거
  - `class UE5Logger(Logger)` → `class UE5Logger` 변경
  - 필요한 표준 라이브러리 import 추가

- [ ] **Task 1.2**: `UE5Logger.__init__` 구현
  - 로그 경로 설정 (기본: `Documents/PyJalLib/logs/`)
  - 로그 파일명 설정 (기본: `ue5`)
  - 로그 디렉토리 생성
  - 콘솔/UE5 출력 옵션 설정
  - 로그 레벨 설정

- [ ] **Task 1.3**: `UE5Logger._setup_logger` 내부 로거 설정 메서드 구현
  - 표준 `logging.Logger` 인스턴스 생성
  - 파일 핸들러 설정 (파일명 패턴: `{파일명}_{YYYYMMDD}.log`, utf-8)
  - 콘솔 핸들러 설정 (선택적)
  - 포매터 설정

### Phase 2: 로깅 API 구현

- [ ] **Task 2.1**: 로깅 메서드 구현
  - `debug(inMessage)`, `info(inMessage)`, `warning(inMessage)`
  - `error(inMessage)`, `critical(inMessage)`, `exception(inMessage)`

- [ ] **Task 2.2**: `remove_handlers()` 메서드 구현
  - 등록된 모든 핸들러 제거
  - 핸들러 close 처리

### Phase 3: UE5 전용 기능

- [ ] **Task 3.1**: UE5 전용 메서드 수정
  - `set_ue5_log_level(inLevel)` - 내부 구현 수정
  - `enable_ue5_output(inEnable)` - 내부 구현 수정
  - `_add_ue5_handler()`, `_remove_ue5_handler()` - 내부 구현 수정

### Phase 4: 하위 호환 함수

- [ ] **Task 4.1**: 모듈 레벨 함수 수정
  - `set_log_level(inLevel)` - UE5Logger 내부 로거 접근 방식 수정
  - `get_log_file_path()` - 현재 로그 파일 경로 반환 로직 수정
  - `set_log_file_path()` - 새 인스턴스 생성 로직 유지

### Phase 5: 검증

- [ ] **Task 5.1**: UE5Logger 테스트 작성
  - 독립 클래스 인스턴스 생성 테스트
  - 로깅 메서드 동작 테스트
  - 파일 출력 테스트
  - remove_handlers 테스트

- [ ] **Task 5.2**: 전체 테스트 실행 및 린트 확인
  - `uv run pytest` 통과
  - `uv run ruff check .` 통과

---

## Progress

- **Total Tasks:** 9
- **Completed:** 0
- **In Progress:** 0
- **Remaining:** 9


