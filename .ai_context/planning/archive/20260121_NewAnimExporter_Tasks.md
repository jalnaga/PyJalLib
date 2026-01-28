# NewAnimExporter Task List

**Primary Manual:** `.ai_context/manuals/new_module_creation.md`

---

## Phase 1: 패키지 구조 및 뼈대 생성

- [x] **Task 1.1**: `src/` 디렉토리 생성 및 빈 파일 생성
  - `src/__init__.py` 생성
  - `src/func_animExporter.py` 생성 (빈 클래스 스텁)
  - `src/ui_animExporter.py` 생성 (빈 클래스 스텁)
  - `src/NewAnimExporter.py` 생성 (빈 클래스 스텁)

---

## Phase 2: UI 레이어 구현 (ui_animExporter.py)

- [x] **Task 2.1**: `AnimExporterWidget` 클래스 기본 구조 구현
  - 클래스 정의 및 `__init__` 메서드
  - 시그널 정의 (`load_requested`, `save_requested`, `english_name_changed`)

- [x] **Task 2.2**: UI 컴포넌트 배치 구현
  - `RolloutBaseSkeletonNamePart` 추가
  - `RolloutNamePart` 추가
  - `RolloutFileStatus` 추가
  - 불러오기/저장 버튼 추가

- [x] **Task 2.3**: UI 유틸리티 메서드 구현
  - `update_button_states()`: 버튼 활성화/비활성화 상태 관리
  - `get_current_english_name()`: 현재 영어 이름 반환
  - `get_base_skeleton_path()`: 베이스 스켈레톤 경로 반환
  - `get_file_full_path()`: 파일 전체 경로 반환
  - `does_file_exist()`: 파일 존재 여부 반환
  - `does_base_skeleton_exist()`: 베이스 스켈레톤 존재 여부 반환
  - `get_perforce_status()`: Perforce 상태 반환

---

## Phase 3: 기능 레이어 구현 (func_animExporter.py)

- [x] **Task 3.1**: `AnimationExporterService` 클래스 기본 구조 구현
  - 클래스 정의 및 `__init__` 메서드
  - 필요한 import 문 추가 (pyjallib, orvlib 등)

- [x] **Task 3.2**: MAX/BIP/ANIM 파일 저장 메서드 구현
  - `save_max_file(inFilePath: str) -> str`
  - `save_bip_file(inFilePath: str) -> str`
  - `save_anim_file(inFilePath: str) -> str`

- [x] **Task 3.3**: JSON/FBX 파일 저장 메서드 구현
  - `save_json_file(inFilePath: str, inBaseSkeletonPath: str) -> str`
  - `save_fbx_file(inFilePath: str, inBaseSkeletonPath: str) -> str`

- [x] **Task 3.4**: 경로 변환 유틸리티 메서드 구현
  - `_convert_fbx_to_content_path(inFbxPath: str) -> str`: FBX 경로 → `/Game/...` Content 경로
  - `_convert_skeleton_to_content_path(inSkeletonFbxPath: str) -> str`: 스켈레톤 FBX → 스켈레톤 Content 경로

- [x] **Task 3.5**: `export_to_ue5()` Interchange 버전 구현 (핵심)
  - `add_disabled_plugins_to_uproject` 사용 금지 확인
  - 원본 프로젝트 경로 직접 사용
  - `process_interchange_animation_import_template()` API 호출
  - 임시 스크립트 파일 생성 및 UE5 실행

---

## Phase 4: 메인 윈도우 구현 (NewAnimExporter.py)

- [x] **Task 4.1**: `NewAnimExporter` 클래스 기본 구조 구현
  - 클래스 정의 및 `__init__` 메서드
  - `AnimExporterWidget` 인스턴스 생성
  - `AnimationExporterService` 인스턴스 생성
  - `P4Sync` 인스턴스 생성

- [x] **Task 4.2**: 시그널/슬롯 연결 및 이벤트 핸들러 구현
  - `on_english_name_generated()`: 이름 생성 시 파일 상태 업데이트
  - `connect_signals()`: 모든 시그널 연결

- [x] **Task 4.3**: `load_file()` 메서드 구현
  - Perforce 동기화
  - 파일 존재 여부 확인 및 로드
  - 로드 후 상태 업데이트

- [x] **Task 4.4**: `save_file()` 메서드 구현 (Part 1 - 사전 검증)
  - Base Skeleton 존재 여부 확인
  - Biped 개수 확인
  - Perforce 상태 확인 및 체크아웃

- [x] **Task 4.5**: `save_file()` 메서드 구현 (Part 2 - 파일 저장)
  - 모든 파일 타입 저장 호출 (MAX, BIP, ANIM, JSON, FBX)
  - Perforce에 파일 추가/체크아웃
  - 서밋 처리

- [x] **Task 4.6**: `save_file()` 메서드 구현 (Part 3 - UE5 익스포트)
  - JSON에서 FBX 및 스켈레톤 경로 읽기
  - `export_to_ue5()` 호출
  - 최종 상태 업데이트

- [x] **Task 4.7**: `show_main_window()` 진입점 함수 구현
  - QApplication 인스턴스 확인
  - INI 파일에서 User Role 읽기
  - `jal.toolManager.show_tool()` 호출

---

## 완료 조건

- [x] 모든 Task 완료
- [x] `add_disabled_plugins_to_uproject` 미사용 확인
- [x] 원본 프로젝트 경로 직접 사용 확인
- [x] `process_interchange_animation_import_template()` API 사용 확인
