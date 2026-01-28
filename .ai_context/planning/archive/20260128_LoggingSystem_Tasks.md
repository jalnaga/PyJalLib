# Active Task List

## Feature: 로깅 시스템 개선 - print문을 pyjallib Logger로 교체

### 구현 태스크

#### Phase 1: 로거 설정 모듈 생성
- [x] **Task 1-1**: logger_config.py 파일 생성 및 기본 구조 작성
  - 파일 생성: `src/logger_config.py`
  - 모듈 docstring 작성
  - 필요한 import 추가 (orvlib.pathAndFiles, pyjallib.logger.Logger)

- [x] **Task 1-2**: get_logger() 함수 구현
  - Singleton 패턴으로 전역 _logger_instance 관리
  - isDevelopmentMode에 따라 로그 레벨 설정 (DEBUG/INFO)
  - Logger 인스턴스 생성 및 반환
  - docstring 작성 (사용 예제 포함)

#### Phase 2: NewAnimExporter.py 로깅 교체
- [x] **Task 2-1**: NewAnimExporter.py에 logger import 추가
  - logger_config.get_logger import 추가
  - 파일 상단에 logger 인스턴스 생성 코드 추가

- [x] **Task 2-2**: NewAnimExporter.py의 print문을 logger로 교체
  - Line 108: User Role 읽기 실패 메시지를 logger.error()로 변경

#### Phase 3: func_animExport.py 로깅 교체
- [x] **Task 3-1**: func_animExport.py에 logger import 추가
  - logger_config.get_logger import 추가
  - AnimationExportService.__init__에 logger 인스턴스 저장

- [x] **Task 3-2**: func_animExport.py의 submit_files 메서드 로깅 교체
  - Line 343: Changelist 생성 메시지를 logger.info()로 변경
  - Line 346: CheckOut files 메시지를 logger.info()로 변경
  - Line 350: Adding new files 메시지를 logger.info()로 변경

#### Phase 4: ui_animExporter.py 로깅 교체 (Part 1: save_file 메서드)
- [x] **Task 4-1**: ui_animExporter.py에 logger import 추가
  - logger_config.get_logger import 추가
  - AnimExporterWidget.__init__에 logger 인스턴스 저장

- [x] **Task 4-2**: ui_animExporter.py의 save_file 메서드 로깅 교체
  - Line 305: 원래 MAX 파일 다시 열기 메시지를 logger.info()로 변경

#### Phase 5: ui_animExporter.py 로깅 교체 (Part 2: _move_imported_assets_to_changelist 메서드)
- [x] **Task 5-1**: _move_imported_assets_to_changelist 메서드 로깅 교체 (정보성 메시지)
  - Line 338: UE5 임포트된 파일 (direct) 메시지를 logger.debug()로 변경
  - Line 353: UE5 임포트된 파일 (folder) 메시지를 logger.debug()로 변경
  - Line 355: UE5 임포트된 파일 최종 메시지를 logger.info()로 변경
  - Line 367: SUCCESS 메시지를 logger.info()로 변경

- [x] **Task 5-2**: _move_imported_assets_to_changelist 메서드 로깅 교체 (경고/에러 메시지)
  - Line 346-348: .uasset 파일 찾을 수 없음 경고를 logger.warning()으로 변경
  - Line 369: 체인지리스트 이동 실패 에러를 logger.error()로 변경
  - Line 373: 예외 메시지를 logger.error()로 변경
  - Line 375: traceback.print_exc()를 logger.exception()으로 변경
  - import traceback 제거

#### Phase 6: func_ue5Import.py 로깅 교체 (Part 1: 기본 메시지)
- [x] **Task 6-1**: func_ue5Import.py에 logger import 추가
  - logger_config.get_logger import 추가
  - UE5ImportService.__init__에 logger 인스턴스 저장

- [x] **Task 6-2**: import_animation_to_ue5 메서드 로깅 교체
  - Line 199: 임시 스크립트 파일 삭제 중 오류 메시지를 logger.warning()으로 변경

#### Phase 7: func_ue5Import.py 로깅 교체 (Part 2: move_assets_to_new_changelist 메서드)
- [x] **Task 7-1**: move_assets_to_new_changelist 메서드 DEBUG 로깅 교체 (1-5)
  - Line 290: 시작 메시지를 logger.debug()로 변경
  - Line 291: 파일 수 메시지를 logger.debug()로 변경
  - Line 292: 설명 메시지를 logger.debug()로 변경
  - Line 295: P4Sync 인스턴스 생성 시작을 logger.debug()로 변경
  - Line 298: P4Sync 인스턴스 생성 완료를 logger.debug()로 변경

- [x] **Task 7-2**: move_assets_to_new_changelist 메서드 DEBUG 로깅 교체 (6-10)
  - Line 306-308: omniP4 인스턴스 획득 관련 메시지를 logger.debug()로 변경
  - Line 311: 체인지리스트 생성 시작을 logger.debug()로 변경
  - Line 314-316: create_change_list 반환값 관련 메시지를 logger.debug()로 변경
  - Line 323: 체인지리스트 생성 완료를 logger.debug()로 변경
  - Line 327: 체인지리스트 생성 실패를 logger.debug()로 변경

- [x] **Task 7-3**: move_assets_to_new_changelist 메서드 DEBUG 로깅 교체 (11-15)
  - Line 331-334: 파일 reopen 관련 메시지를 logger.debug()로 변경
  - Line 336: 파일 reopen 실패를 logger.debug()로 변경
  - Line 339: 체인지리스트 삭제 시도를 logger.debug()로 변경
  - Line 347: 개발 모드 서밋 건너뜀을 logger.debug()로 변경
  - Line 350-353: 서밋 관련 메시지를 logger.debug()로 변경

- [x] **Task 7-4**: move_assets_to_new_changelist 메서드 DEBUG 로깅 교체 (16-20) 및 예외 처리
  - Line 357: 서밋 성공을 logger.debug()로 변경
  - Line 360: 서밋 실패를 logger.debug()로 변경
  - Line 364: 예외 발생을 logger.debug()로 변경
  - Line 365-366: traceback을 logger.exception()으로 변경
  - Line 370-375: 리소스 정리 관련 메시지를 logger.debug()로 변경
  - import traceback 제거

### 테스트 태스크

- [x] **Task 8-1**: logger_config 모듈 단위 테스트
  - get_logger() 함수가 Singleton으로 동작하는지 확인
  - Logger 인스턴스 생성 확인
  - Logger 필수 메서드 확인 (debug, info, warning, error, exception)

- [x] **Task 8-2**: 통합 테스트 - NewAnimExporter 실행
  - NewAnimExporter 실행 시 logger 초기화 확인
  - User Role 읽기 실패 시 logger.error 출력 확인

- [x] **Task 8-3**: 통합 테스트 - 파일 저장 프로세스
  - 파일 저장 프로세스 실행하여 모든 로그 정상 출력 확인
  - Perforce 체크아웃/서밋 메시지 확인
  - 로그 파일에 기록되는지 확인

- [x] **Task 8-4**: 통합 테스트 - UE5 임포트 프로세스
  - UE5 임포트 프로세스의 DEBUG 로그 출력 확인
  - 예외 발생 시 logger.exception() 동작 확인
  - 체인지리스트 이동 로그 확인

### 검증 태스크

- [x] **Task 9-1**: 로그 레벨 검증
  - 개발 모드(isDevelopmentMode=True)에서 DEBUG 로그 출력 확인
  - INFO, WARNING, ERROR 로그는 항상 출력되는지 확인

- [x] **Task 9-2**: 로그 파일 검증
  - Documents/PyJalLib/logs/ 경로에 로그 파일 생성 확인
  - 로그 파일명이 AnimExporter_{YYYYMMDD}.log 형식인지 확인
  - 로그 파일에 한글이 정상 출력되는지 확인

- [x] **Task 9-3**: 회귀 테스트
  - 기존 기능이 모두 정상 동작하는지 확인
  - 에러 메시지가 사용자에게 정상적으로 표시되는지 확인
  - UI 다이얼로그(QMessageBox)가 정상 동작하는지 확인

---

**총 태스크 수:** 26개
**현재 진행:** 26/26 (완료)

**태스크 실행 원칙:**
- 각 태스크는 순차적으로 실행
- 태스크 완료 시 즉시 `[x]`로 체크
- Phase 단위로 커밋 권장
