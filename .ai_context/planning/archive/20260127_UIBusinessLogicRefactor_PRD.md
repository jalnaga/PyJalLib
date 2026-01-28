# Active PRD

## Title
NewAnimExporter UI/비즈니스 로직 분리 리팩토링

## Background & Intent

**왜 이 리팩토링이 필요한가?**

현재 `NewAnimExporter.py`는 다음 두 가지 역할을 동시에 수행하고 있습니다:
1. UI 메인 윈도우 구성 및 pyjallib 헤더 툴 등록
2. 복잡한 비즈니스 로직 (사전 검증, Perforce 체크아웃/서밋, 파일 저장 조율, UE5 익스포트)

이로 인해:
- 책임 분리(SRP)가 되어있지 않음
- `func_animExporter.py`와 역할이 겹침
- 유지보수 시 어디를 수정해야 할지 모호함

**목표:**
- `NewAnimExporter.py`는 순수하게 **UI 메인 윈도우** 역할만 담당
- **pyjallib 헤더 툴 등록**만 수행
- 모든 비즈니스 로직은 `func_*` 파일로 이동

## Primary Manual
`.ai_context/manuals/task_loop.md`

## Technical Decisions & References

### 설계 결정: 파일 역할 분리

**레이어 구조:**
```
NewAnimExporter.py (시작점)
    ↓ 툴 등록
ui_animExporter.py (UI 레이어)
    ↓ 함수 호출
func_*.py (비즈니스 로직)
```

| 파일명 | 역할 | 비고 |
|:-------|:-----|:-----|
| `NewAnimExporter.py` | 프로그램 시작점 | pyjallib 헤더 툴 등록만 |
| `ui_animExporter.py` | UI 레이어 | 위젯 구성 + func_* 함수 호출 |
| `func_animValidation.py` | 유효성 검사 | 저장 전 검증 |
| `func_animExport.py` | 3DS Max → DevStorage (P4) | 파일 익스포트 + Perforce 등록 |
| `func_ue5Import.py` | DevStorage → UE5 | FBX → UE5 임포트 |

**분리 기준:**
- `NewAnimExporter.py`: 시작점 역할만 (최소화)
- `ui_animExporter.py`: UI 구성 + 시그널/슬롯 + func_* 함수 호출
- `func_*.py`: 순수 비즈니스 로직 (UI 의존성 없음)

## Scope & Prioritization

### [Must-Have] (P0 - 필수)

1. **`func_animValidation.py` 생성**
   - 유효성 검사 전용 모듈
   - `get_biped_count()` - Biped 개수 반환
   - `validate_biped_count()` - Biped 개수 검증 (1개인지 확인)
   - `validate_base_skeleton_exists()` - Base Skeleton 파일 존재 확인
   - `validate_save_prerequisites()` - 저장 전 모든 검증 수행

2. **`func_animExport.py` 생성 (기존 func_animExporter.py 리네임 + 확장)**
   - 3DS Max 파일 익스포트 + Perforce 등록
   - 기존 저장 메서드 유지: `save_max_file()`, `save_bip_file()`, `save_anim_file()`, `save_json_file()`, `save_fbx_file()`
   - Perforce 메서드 추가:
     - `sync_directory()` - P4 디렉토리 동기화
     - `prepare_checkout()` - Changelist 생성, 체크아웃 준비
     - `submit_files()` - 파일 추가/체크아웃 후 서밋
   - `load_max_file()` - P4 동기화 후 MAX 파일 로드
   - UE5 관련 메서드 제거 (func_ue5Import.py로 이동)

3. **`func_ue5Import.py` 생성**
   - DevStorage FBX → UE5 임포트 전용 모듈
   - `_convert_fbx_to_content_path()` - FBX 경로 → Content 경로 변환
   - `_convert_skeleton_to_content_path()` - 스켈레톤 Content 경로 변환
   - `does_base_skeleton_exist_in_ue5()` - UE5 스켈레톤 존재 확인
   - `import_animation_to_ue5()` - Interchange 기반 임포트
   - `import_animation_from_json()` - JSON 파싱 후 임포트
   
   **구현 방식 (테스트 파일 참조):**
   - `tests/ue5/test_animation_import.py` 패턴 참조
   - `TemplateProcessor`로 언리얼용 스크립트 생성
   - `subprocess.Popen`으로 언리얼 에디터 실행
   - `tempOmniProjectPath` 대신 직접 `OmniProjectPath` 사용
   ```python
   # 예시 구현 패턴
   cmd = f'{pathAndFiles.ue5.editorPath} "{pathAndFiles.ue5.projectPath}" -run=pythonscript -script="{scriptPath}"'
   process = subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
   process.wait()
   ```

4. **`ui_animExporter.py` 확장**
   - `NewAnimExporter.py`에서 비즈니스 로직 호출 부분 이동
   - `func_animValidation`, `func_animExport`, `func_ue5Import` 함수 호출
   - `load_file()`, `save_file()` 로직을 여기서 구현
   - UI 위젯 구성 + 시그널/슬롯 연결 유지

5. **`NewAnimExporter.py` 최소화**
   - 시작점 역할만 유지
   - pyjallib 헤더 툴 등록
   - `show_main_window()` 함수만 유지
   - 모든 비즈니스 로직, P4Sync 직접 사용 제거

6. **테스트 수정 및 통과 확인**
   - import 경로 수정 (`func_animExporter` → `func_animExport`)
   - `uv run pytest` 통과
   - `uv run ruff check .` 통과

### [Should-Have] (P1 - 권장)

- 에러 처리 개선: 서비스 레이어에서 예외를 발생시키고 UI 레이어에서 메시지 박스 표시
- 반환 타입 명시: 서비스 메서드에 명확한 반환 타입 및 예외 타입 정의

### [Nice-to-Have] (P2 - 부가)

- 로깅 개선: 서비스 레이어에 로깅 추가
- 진행 상황 콜백: 저장 진행 상황을 UI에 표시하는 콜백 시그널

### [Non-Goal] (Out of Scope)

- UI 디자인 변경
- 새로운 기능 추가
- 테스트 코드 리팩토링 (기존 테스트 통과만 확인)
