# Active PRD

## Title
임포트된 UE5 애셋을 새로운 Perforce 체인지리스트로 이동 및 서밋

---

## Background & Intent

**왜 이 기능을 만드는가?**

현재 언리얼로 애니메이션을 임포트하면 생성된 .uasset 파일들이 Perforce의 Default 체인지리스트에 자동으로 체크아웃됩니다. 아티스트들이 여러 애니메이션을 임포트하다 보면 Default 체인지리스트에 많은 파일이 섞이게 되어 관리가 어려워집니다.

**문제점:**
- Default 체인지리스트에 임포트된 애셋들이 누적됨
- 특정 작업 단위로 그룹핑하여 서밋하기 어려움
- 언리얼 에디터 내부에는 체인지리스트를 조작하는 Python API가 없음

**해결 방안:**
- 언리얼 에디터 외부에서 실행되는 Python 스크립트 제공
- 임포트된 .uasset 파일들의 로컬 절대 경로를 받아서
- 새로운 Perforce 체인지리스트를 생성하고
- 파일들을 새 체인지리스트로 이동(reopen)한 후 서밋

**사용 시나리오:**
1. 아티스트가 언리얼에서 여러 애니메이션을 임포트
2. 임포트 완료 후 Python 스크립트 실행
3. 스크립트가 임포트된 파일 경로를 받아 새 체인지리스트로 이동 및 서밋
4. Default 체인지리스트는 깨끗하게 유지됨

---

## Primary Manual
`.ai_context/manuals/task_loop.md`

---

## Technical Decisions & References

### 적용할 표준 패턴
- **Service Pattern**: `UE5ImportService` 클래스에 메서드 추가 (비즈니스 로직 분리)
- **Perforce Integration Pattern**: PyJalLib의 `Perforce` 클래스 사용 (`.ai_context/references/integrations/perforce_pattern.md`)

### Perforce API 사용
**참조:** `D:\Dropbox\Programing\Python\PyJalLib\src\pyjallib\perforce.py`

필요한 메서드:
1. `create_change_list(description: str) -> Dict`: 새 체인지리스트 생성
2. `edit_change_list(change_list_number, add_file_paths=[...])`: 파일을 체인지리스트로 reopen
3. `submit_change_list(change_list_number: int) -> bool`: 체인지리스트 서밋

### P4Sync 통합
**참조:** `orvlib.p4Sync.P4Sync` (d:\Work\00_Scripting\orvlib\src\orvlib\p4Sync.py)

- `P4Sync` 클래스는 `omniP4`와 `devStorageP4` 두 개의 `Perforce` 인스턴스를 관리
- 임포트된 UE5 애셋은 `omniP4` 워크스페이스에 속함
- `P4Sync.omniP4` 인스턴스를 사용하여 체인지리스트 조작

### 경로 처리
- 입력: 임포트된 .uasset 파일들의 로컬 절대 경로 리스트
  - 예: `E:\OmniP4_root\Omni\Content\...\AnimName.uasset`
- Perforce API는 로컬 절대 경로를 받아서 내부적으로 정규화 처리

### 에러 처리
- 다른 사용자가 파일을 체크아웃한 경우: `P4Exception` 발생
- 빈 체인지리스트 서밋 시: `submit_change_list()`가 False 반환하고 자동 삭제
- 파일이 이미 다른 체인지리스트에 있는 경우: `P4Exception` 발생

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)
1. **`UE5ImportService`에 `move_assets_to_new_changelist()` 메서드 추가**
   - 파라미터: `asset_paths: List[str]`, `description: str`
   - 반환값: `Tuple[bool, str]` (성공 여부, 메시지 또는 에러)
   - 로직:
     1. `P4Sync` 인스턴스 생성 및 `omniP4` 획득
     2. 새 체인지리스트 생성
     3. 파일들을 새 체인지리스트로 reopen
     4. 체인지리스트 서밋
     5. 리소스 정리 (`P4Sync.close()`)

2. **에러 처리**
   - P4Exception 캐치 및 사용자 친화적 메시지 반환
   - 빈 파일 목록 처리
   - 연결 실패 처리

3. **테스트 코드 작성**
   - `tests/test_max_func_ue5Import.py`에 테스트 추가
   - Mock을 사용한 단위 테스트 (실제 Perforce 연결 없이)

### [Should-Have] (P1 - 권장)
1. **파일 상태 사전 확인**
   - 다른 사용자가 체크아웃한 파일이 있는지 확인
   - 있으면 경고 메시지와 함께 해당 파일 목록 반환

2. **로깅**
   - 각 단계별 로그 출력
   - 실패한 파일 목록 기록

### [Nice-to-Have] (P2 - 부가)
1. **UI 통합**
   - 언리얼 임포트 후 자동으로 다이얼로그 표시
   - 체인지리스트 설명 입력 UI

2. **자동 파일 탐지**
   - 최근 임포트된 파일을 자동으로 찾는 기능

### [Non-Goal] (Out of Scope)
- 언리얼 에디터 내부에서 실행되는 버전 (Python API 제약)
- 다른 타입의 애셋 처리 (애니메이션 외)
- 체인지리스트 병합 기능
- 자동 리뷰 요청 기능

---

## Implementation Details

### 메서드 시그니처
```python
def move_assets_to_new_changelist(
    self,
    inAssetPaths: List[str],
    inDescription: str
) -> Tuple[bool, str]:
    """
    임포트된 UE5 애셋들을 새로운 Perforce 체인지리스트로 이동하고 서밋합니다.

    Args:
        inAssetPaths: 이동할 .uasset 파일들의 로컬 절대 경로 리스트
        inDescription: 새 체인지리스트의 설명

    Returns:
        (성공 여부, 메시지) 튜플
        - 성공 시: (True, "Submitted as changelist {cl_number}")
        - 실패 시: (False, 에러 메시지)
    """
```

### 구현 순서
1. `func_ue5Import.py`에 메서드 추가
2. 단위 테스트 작성 (Mock 사용)
3. 수동 통합 테스트 (실제 Perforce 환경)

---

## Test Plan

### 단위 테스트 (`tests/test_max_func_ue5Import.py`)
- Mock을 사용하여 Perforce API 호출 시뮬레이션
- 정상 케이스: 파일 이동 및 서밋 성공
- 에러 케이스: 빈 파일 목록, 연결 실패, P4Exception

### 통합 테스트 (수동)
- 실제 언리얼에서 애니메이션 임포트
- 임포트된 파일 경로 수집
- `move_assets_to_new_changelist()` 호출
- Perforce 클라이언트에서 결과 확인

---

## Notes
- 이 작업은 현재 브랜치(`feature/move-asset-checklist`)에서 수행합니다.
- PyJalLib의 Perforce 클래스는 이미 완성되어 있어 추가 작업 불필요
- orvlib의 P4Sync 클래스도 기존 코드 그대로 사용
