# Active Task List

## Feature: 임포트된 UE5 애셋을 새로운 Perforce 체인지리스트로 이동 및 서밋

### 구현 태스크

- [x] **Task 1**: `func_ue5Import.py`에 `move_assets_to_new_changelist()` 메서드 스켈레톤 작성
  - 메서드 시그니처 정의 (타입 힌트 포함)
  - Docstring 작성 (Google Style, 한국어)
  - 빈 구현 (pass)

- [x] **Task 2**: 입력 유효성 검증 로직 구현
  - `inAssetPaths`가 빈 리스트인 경우 에러 반환
  - `inDescription`이 빈 문자열인 경우 에러 반환

- [x] **Task 3**: P4Sync 인스턴스 생성 및 omniP4 획득
  - `P4Sync()` 인스턴스 생성
  - `p4sync.omniP4` 접근
  - try-finally 블록 구조 준비 (리소스 정리 보장)

- [x] **Task 4**: 새 체인지리스트 생성 로직 구현
  - `omniP4.create_change_list(inDescription)` 호출
  - 반환된 체인지리스트 ID 저장
  - P4Exception 캐치 및 에러 메시지 반환

- [x] **Task 5**: 파일을 새 체인지리스트로 reopen 구현
  - `omniP4.edit_change_list(cl_number, add_file_paths=inAssetPaths)` 호출
  - P4Exception 캐치 (파일이 다른 CL에 있거나, 다른 사용자가 체크아웃한 경우)
  - 에러 발생 시 생성된 체인지리스트 삭제 (rollback)

- [x] **Task 6**: 체인지리스트 서밋 로직 구현
  - `omniP4.submit_change_list(cl_number)` 호출
  - 서밋 성공 시 성공 메시지 반환
  - 빈 체인지리스트 처리 (False 반환 시)
  - P4Exception 캐치 및 에러 메시지 반환

- [x] **Task 7**: 리소스 정리 (finally 블록)
  - `p4sync.close()` 호출
  - 예외 발생 여부와 관계없이 항상 실행 보장

### 테스트 태스크

- [x] **Task 8**: `tests/test_max_func_ue5Import.py`에 테스트 스켈레톤 추가
  - `test_move_assets_to_new_changelist_method_exists` 함수 정의
  - `test_move_assets_to_new_changelist_empty_paths` 함수 정의
  - `test_move_assets_to_new_changelist_empty_description` 함수 정의

- [x] **Task 9**: 메서드 존재 및 정상 케이스 테스트 작성
  - `move_assets_to_new_changelist` 메서드 존재 여부 확인
  - callable 여부 확인
  - 메서드 시그니처 확인

- [x] **Task 10**: 입력 유효성 검증 테스트 작성
  - 빈 파일 목록 테스트 (에러 메시지 확인)
  - 빈 설명 테스트 (에러 메시지 확인)
  - 공백 문자열 테스트 추가

- [x] **Task 11**: 모든 테스트 실행 및 통과 확인
  - `uv run python tests/test_max_func_ue5Import.py` 실행
  - 모든 테스트 통과 확인 (10/10 통과)
  - 실패 시 구현 코드 수정

### 검증 태스크

- [x] **Task 12**: 린트 및 타입 체크 통과
  - `uv run ruff check .` 실행 및 통과 확인
  - 경고 및 에러 수정 - All checks passed!

---

**총 태스크 수:** 12개
**현재 진행:** 12/12 완료 ✓
