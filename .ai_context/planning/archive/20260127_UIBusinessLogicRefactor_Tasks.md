# Active Task List

## Phase 1: func_animValidation.py 생성

- [x] 1.1 `func_animValidation.py` 파일 생성 및 기본 구조 작성
- [x] 1.2 `get_biped_count()` 함수 구현 (기존 코드에서 이동)
- [x] 1.3 `validate_biped_count()` 함수 구현
- [x] 1.4 `validate_base_skeleton_exists()` 함수 구현
- [x] 1.5 `validate_save_prerequisites()` 함수 구현 (통합 검증)

## Phase 2: func_animExport.py 생성

- [x] 2.1 `func_animExporter.py` → `func_animExport.py` 리네임
- [x] 2.2 UE5 관련 메서드 제거 (`export_to_ue5`, `_convert_*_path`, `does_base_skeleton_exist_in_ue5`)
- [x] 2.3 `sync_directory()` 함수 구현 (P4 디렉토리 동기화)
- [x] 2.4 `prepare_checkout()` 함수 구현 (Changelist 생성, 체크아웃)
- [x] 2.5 `submit_files()` 함수 구현 (파일 추가/체크아웃 후 서밋)
- [x] 2.6 `load_max_file()` 함수 구현 (P4 동기화 후 MAX 파일 로드)

## Phase 3: func_ue5Import.py 생성

- [x] 3.1 `func_ue5Import.py` 파일 생성 및 기본 구조 작성
- [x] 3.2 `_convert_fbx_to_content_path()` 함수 이동
- [x] 3.3 `_convert_skeleton_to_content_path()` 함수 이동
- [x] 3.4 `does_base_skeleton_exist_in_ue5()` 함수 이동
- [x] 3.5 `import_animation_to_ue5()` 함수 구현 (TemplateProcessor + subprocess)
- [x] 3.6 `import_animation_from_json()` 함수 구현 (JSON 파싱 후 import 호출)

## Phase 4: ui_animExporter.py 확장

- [x] 4.1 `func_animValidation`, `func_animExport`, `func_ue5Import` import 추가
- [x] 4.2 `load_file()` 메서드 구현 (NewAnimExporter.py에서 로직 이동)
- [x] 4.3 `save_file()` 메서드 구현 - Part 1: 사전 검증 호출
- [x] 4.4 `save_file()` 메서드 구현 - Part 2: Perforce 체크아웃 준비
- [x] 4.5 `save_file()` 메서드 구현 - Part 3: 파일 저장 호출
- [x] 4.6 `save_file()` 메서드 구현 - Part 4: Perforce 서밋
- [x] 4.7 `save_file()` 메서드 구현 - Part 5: UE5 임포트 호출

## Phase 5: NewAnimExporter.py 최소화

- [x] 5.1 비즈니스 로직 메서드 제거 (`_validate_*`, `_prepare_*`, `_save_*`, `_submit_*`, `_export_*`)
- [x] 5.2 `load_file()`, `save_file()` 메서드를 `ui_animExporter` 호출로 변경
- [x] 5.3 `P4Sync` 직접 사용 제거, import 정리
- [x] 5.4 최종 코드 정리 (시작점 + 툴 등록만 유지)

## Phase 6: 테스트 및 검증

- [x] 6.1 pyproject.toml에 pytest 설정 추가 (tests/ue5/ 제외)
- [x] 6.2 테스트 파일 작성 (User-Driven 방식)
  - [x] test_max_func_animValidation.py
  - [x] test_max_func_animExport.py
  - [x] test_max_func_ue5Import.py
- [x] 6.3 `uv run ruff check .` 통과 확인
- [x] 6.4 3DS Max에서 테스트 실행 (유저 주도) - **19/19 PASSED**
- [x] 6.5 `__init__.py` import 경로 수정 (`func_animExporter` → `func_animExport`)
- [x] 6.6 기존 `func_animExporter.py` 파일 삭제 완료
