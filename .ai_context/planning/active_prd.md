# Active PRD

## Title
Import Asset Save & Changelist 기능 추가

## Background & Intent

### 문제 상황
현재 `src/pyjallib/ue5/inUnreal/` 모듈의 Interchange 임포터들(Animation, SkeletalMesh, Skeleton)이 FBX 파일을 임포트한 후 **에셋을 저장하지 않는 버그**가 있습니다.

### 원인 분석
코드 분석 결과:
1. `_execute_import()` 이후 `unreal.EditorAssetLibrary.save_asset()` 호출이 없음
2. `check_in_files()`는 **바로 체크인**을 시도하지만, 에셋이 저장되지 않은 상태에서 체크인이 실패하거나 의도하지 않은 동작 발생
3. 새로운 체인지리스트에 파일을 **할당만** 하는 기능이 없음 (check_out_or_add_file은 default changelist 사용)
4. `InterchangePipelineSettings`가 DefaultAssetsPipeline 에셋을 수정하지만, **원래 상태로 복원하지 않음** - 임포트 후 파이프라인 에셋이 dirty 상태로 남음

### 해결 목표
1. 임포트된 에셋을 명시적으로 저장하는 기능 추가
2. 새로운 체인지리스트를 생성하고 임포트된 에셋을 해당 리스트에 할당하는 기능 추가
3. 파이프라인 에셋을 임포트 전 상태로 복원 (저장하지 않음)

## Primary Manual
`.ai_context/manuals/task_loop.md`

## Technical Decisions & References

### 참조 문서
- `references/ue5/asset_path_methods.md` - `get_path_name()` vs `get_system_path()` 차이
- `references/ue5/path_rules.md` - 경로 변환 규칙
- [UE5 Python API - EditorAssetLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorAssetLibrary?application_version=5.7)

### 기술적 결정

#### 1. 에셋 저장 방식
**선택: `unreal.EditorAssetLibrary.save_loaded_assets()`**
- 이미 로드된 오브젝트 리스트를 직접 저장
- `only_if_is_dirty=True` 옵션으로 변경된 에셋만 저장

```python
# 임포트된 오브젝트 리스트 저장
unreal.EditorAssetLibrary.save_loaded_assets(importedObjects, only_if_is_dirty=True)
```

#### 2. 체인지리스트 이동 방식
**선택: `unreal.SourceControl.execute_source_control_command()` 사용**
- Perforce `reopen -c {changelist_id}` 명령 실행
- 새 체인지리스트 생성 후 파일 이동

```python
# 파일을 특정 체인지리스트로 이동
unreal.SourceControl.execute_source_control_command(
    command_name="reopen",
    files=[file_path],
    parameters=["-c", changelist_id]
)
```

#### 3. 파이프라인 복원 방식
**선택: 설정 전 원본 값 저장 → 임포트 후 복원**
- `InterchangePipelineSettings`에서 `configure_for_*` 호출 전에 원본 속성 값 저장
- 임포트 완료 후 `restore_pipeline()` 메서드로 원래 값 복원
- 파이프라인 에셋은 **저장하지 않음** (dirty 상태 유지 방지)

#### 4. 저장/체인지리스트 위치
**선택: 베이스 클래스(`InterchangeImporterBase`)에 헬퍼 메서드 추가**
- 모든 임포터에서 공통으로 사용
- 개별 임포터는 헬퍼 메서드 호출만 수행

## Scope & Prioritization

### [Must-Have] - P0 (필수)

1. **파이프라인 복원 기능 추가** (`InterchangePipelineSettings`)
   - `_store_original_values()` - 설정 전 원본 값 저장
   - `restore_pipeline()` - 원본 값으로 복원
   - `configure_for_*` 메서드에서 자동으로 원본 저장 호출

2. **에셋 저장 기능 추가** (`InterchangeImporterBase`)
   - `_save_imported_assets()` 헬퍼 메서드 추가
   - `unreal.EditorAssetLibrary.save_loaded_assets()` 사용
   - 임포트 성공 후 모든 임포트된 오브젝트 저장

3. **새 체인지리스트 생성 및 할당 기능 추가** (`InterchangeImporterBase`)
   - `_move_to_changelist()` 헬퍼 메서드 추가
   - `execute_source_control_command("reopen", ...)` 사용
   - 임포트된 에셋들을 지정된 체인지리스트로 이동

4. **기존 임포터 메서드 수정**
   - `import_animation()`, `import_animations()` 수정
   - `import_skeletal_mesh()`, `import_skeletal_meshes()` 수정  
   - `import_skeleton()`, `import_skeletons()` 수정
   - 워크플로우: 임포트 → 파이프라인 복원 → 저장 → 체인지리스트 할당
   - 기존 `check_in_files()` 호출 제거

5. **테스트 코드 호환성 확인**
   - 기존 테스트가 새 기능과 호환되는지 확인

### [Should-Have] - P1 (권장)
1. **옵션 파라미터 추가**
   - `inAutoSave: bool = True` - 자동 저장 여부 제어
   - `inChangelistId: str = None` - 체인지리스트 ID 지정 (None이면 체인지리스트 할당 생략)

### [Nice-to-Have] - P2 (부가)
1. **저장 실패 시 롤백 로직**
   - 임포트 성공 후 저장 실패 시 에셋 삭제 및 정리

### [Non-Goal] - 범위 외
1. **새 체인지리스트 생성 기능** - 외부에서 생성된 체인지리스트 ID를 받아서 사용
2. **비동기 임포트 메서드 수정** - 동기 메서드만 수정 대상
3. **P4Python 직접 사용** - `unreal.SourceControl` API만 사용
