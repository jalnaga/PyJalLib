# AnimSequence 스켈레톤 변경 방법

## 요약

AnimSequence의 skeleton 속성은 **Python API에서 read-only**입니다. 스켈레톤을 변경하려면 **Consolidate + Rename** 방식을 사용해야 합니다.

---

## 문제 상황

### 증상
- 기존 애니메이션 에셋을 다른 스켈레톤으로 재임포트해도 스켈레톤이 변경되지 않음
- `set_editor_property('skeleton', new_skeleton)` 호출 시 에러 발생

### 에러 메시지
```
AnimSequence: Property 'Skeleton' for attribute 'skeleton' on 'AnimSequence' is read-only and cannot be set
```

### 원인
1. UE5의 `AnimSequence.skeleton` 속성은 Python API에서 완전히 read-only
2. 재임포트(`replace_existing=True`) 시에도 기존 에셋의 스켈레톤이 유지됨
3. FbxImportUI에서 skeleton 설정해도 재임포트 시 무시됨

---

## 실패한 접근법

### 방안 B: set_editor_property
```python
# 실패 - read-only 에러
existing_asset.set_editor_property('skeleton', new_skeleton)
```

### 방안 C: FbxImportUI 옵션만으로 해결
```python
# 실패 - 재임포트 시 기존 스켈레톤 유지
options.set_editor_property('skeleton', new_skeleton)
task.replace_existing = True
```

---

## 성공한 접근법: Consolidate + Rename

### 핵심 API

```python
# 참조 리다이렉트
unreal.EditorAssetLibrary.consolidate_assets(
    asset_to_consolidate_to,   # 새 에셋 (참조 대상)
    assets_to_consolidate      # 기존 에셋 리스트 (참조 원본)
) -> bool

# 에셋 이름 변경
unreal.EditorAssetLibrary.rename_asset(
    source_asset_path,         # 원본 경로
    destination_asset_path     # 대상 경로
) -> bool
```

### 구현 흐름

```
1. 임시 이름으로 새 에셋 임포트 (새 스켈레톤)
   └─> /Game/.../AnimName_temp

2. consolidate_assets()로 참조 리다이렉트
   └─> 기존 에셋의 모든 참조 → 새 에셋으로 변경
   └─> 기존 에셋은 Redirector로 대체됨

3. 기존 경로의 Redirector 삭제

4. rename_asset()으로 이름 복원
   └─> AnimName_temp → AnimName
```

### FBX 임포트 태스크 생성 (핵심)

**중요**: `FbxFactory.import_ui` 속성은 Python API에서 접근 불가. `FbxImportUI`를 직접 생성하고 `task.factory`와 `task.options`를 모두 설정해야 함.

```python
def create_animation_import_task(fbx_file: str, destination_path: str, skeleton) -> unreal.AssetImportTask:
    """스켈레톤이 올바르게 적용되는 애니메이션 임포트 태스크 생성"""

    # FbxImportUI 직접 생성
    import_options = unreal.FbxImportUI()
    import_options.reset_to_default()

    # 중요: import_type을 먼저 설정한 후 skeleton 설정
    import_options.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_ANIMATION)
    import_options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
    import_options.set_editor_property('import_animations', True)
    import_options.set_editor_property('import_mesh', False)
    import_options.set_editor_property('import_textures', False)
    import_options.set_editor_property('import_materials', False)
    import_options.set_editor_property('automated_import_should_detect_type', False)

    # 스켈레톤 설정 (import_type 설정 후에 해야 함)
    import_options.set_editor_property('skeleton', skeleton)

    # 애니메이션 시퀀스 데이터 설정
    import_options.anim_sequence_import_data.set_editor_property('animation_length',
        unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    import_options.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)

    # FbxFactory 생성 (타입 힌트용)
    factory = unreal.FbxFactory()

    # Task 생성 - factory와 options 모두 설정
    task = unreal.AssetImportTask()
    task.automated = True
    task.destination_path = destination_path
    task.filename = fbx_file
    task.replace_existing = True
    task.save = True
    task.factory = factory      # 중요: factory 설정
    task.options = import_options  # 중요: options도 설정

    return task
```

### Consolidate + Rename 전체 코드

```python
def swap_skeleton_via_consolidate(
    fbx_file: str,
    asset_full_path: str,
    new_skeleton,
    importer
):
    """Consolidate + Rename 방식으로 스켈레톤 변경"""
    from pathlib import Path

    # 1. 경로 분해
    destination_path = str(Path(asset_full_path).parent).replace("\\", "/")
    asset_name = Path(asset_full_path).stem

    # 임시 폴더: 원본과 같은 경로의 서브폴더 (Asset Reference Restriction 우회)
    temp_folder = f"{destination_path}/_SkeletonSwapTemp"
    temp_path = f"{temp_folder}/{asset_name}"

    # 2. 임시 폴더 생성
    if not unreal.EditorAssetLibrary.does_directory_exist(temp_folder):
        unreal.EditorAssetLibrary.make_directory(temp_folder)

    # 3. 기존 임시 에셋 정리
    if unreal.EditorAssetLibrary.does_asset_exist(temp_path):
        unreal.EditorAssetLibrary.delete_asset(temp_path)

    # 4. 새 스켈레톤으로 임시 폴더에 에셋 임포트
    task = create_animation_import_task(fbx_file, temp_folder, new_skeleton)
    task.destination_name = asset_name
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    result = task.get_objects()
    if len(result) == 0:
        raise ValueError(f"임시 에셋 임포트 실패: {fbx_file}")

    # 5. 에셋 로드
    new_asset = unreal.EditorAssetLibrary.load_asset(temp_path)
    old_asset = unreal.EditorAssetLibrary.load_asset(asset_full_path)

    if not new_asset or not old_asset:
        raise ValueError("에셋 로드 실패")

    # 6. Consolidate (참조 리다이렉트)
    success = unreal.EditorAssetLibrary.consolidate_assets(new_asset, [old_asset])
    if not success:
        raise ValueError("Consolidate 실패")

    # 7. Redirector 삭제
    if unreal.EditorAssetLibrary.does_asset_exist(asset_full_path):
        unreal.EditorAssetLibrary.delete_asset(asset_full_path)

    # 8. Rename으로 원래 경로로 이동
    success = unreal.EditorAssetLibrary.rename_asset(temp_path, asset_full_path)
    if not success:
        raise ValueError("Rename 실패")

    # 9. 임시 폴더 정리
    if unreal.EditorAssetLibrary.does_directory_exist(temp_folder):
        assets_in_temp = unreal.EditorAssetLibrary.list_assets(temp_folder)
        if len(assets_in_temp) == 0:
            unreal.EditorAssetLibrary.delete_directory(temp_folder)

    return True
```

---

## 디버깅 중 발견한 중요 사항

### 1. FbxFactory.import_ui 접근 불가

```python
# 에러 발생 - import_ui 속성이 Python에서 노출되지 않음
factory = unreal.FbxFactory()
import_options = factory.get_editor_property('import_ui')  # Exception!
```

**해결책**: `FbxImportUI`를 직접 생성하고 `task.options`에 할당

### 2. 스켈레톤 설정 순서 중요

```python
# 올바른 순서: import_type 먼저, skeleton 나중
import_options.set_editor_property('original_import_type', unreal.FBXImportType.FBXIT_ANIMATION)
import_options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
import_options.set_editor_property('skeleton', skeleton)  # import_type 설정 후에 해야 함
```

### 3. task.factory와 task.options 모두 필요

```python
task = unreal.AssetImportTask()
task.factory = unreal.FbxFactory()  # 필수: 어떤 factory 사용할지 지정
task.options = import_options        # 필수: 임포트 옵션
```

`task.options`만 설정하면 스켈레톤이 대화상자에 표시되지 않음 (자동 모드에서 무시됨)

### 4. Asset Reference Restriction

임시 폴더를 `/Game/_Temp` 같은 루트 레벨에 생성하면 프로젝트의 Asset Reference Restriction 규칙에 위반될 수 있음.

```python
# 나쁜 예: 루트 레벨 임시 폴더
temp_folder = "/Game/_SkeletonSwapTemp"  # Asset Reference Restriction 위반 가능

# 좋은 예: 원본 에셋과 같은 경로의 서브폴더
temp_folder = f"{destination_path}/_SkeletonSwapTemp"  # 같은 참조 규칙 적용
```

### 5. 스켈레톤 설정 확인

```python
# 설정 후 확인하면 디버깅에 도움됨
set_skeleton = import_options.get_editor_property('skeleton')
if set_skeleton:
    unreal.log(f"스켈레톤 설정 확인: {set_skeleton.get_name()}")
else:
    unreal.log_warning("경고: 스켈레톤이 설정되지 않음!")
```

---

## 주의사항

1. **Redirector 생성**: consolidate 후 기존 경로에 Redirector가 생성됨
2. **저장 필요**: consolidate 후 관련 에셋 저장 권장
3. **에디터 상태**: PIE(Play In Editor) 모드에서는 작동하지 않음
4. **성능**: 단순 재임포트보다 느림 (참조 검색 + 리다이렉트)
5. **임시 폴더 정리**: 작업 완료 후 빈 임시 폴더는 삭제하는 것이 좋음

---

## 참조 문서

- [EditorAssetLibrary Python API (UE5.1)](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorAssetLibrary?application_version=5.1)
- [Consolidating Assets in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/consolidating-assets-in-unreal-engine)
- [AnimSequence Python API](https://docs.unrealengine.com/5.1/en-US/PythonAPI/class/AnimSequence.html)
- [How to change skeleton of animation sequence (Forum)](https://forums.unrealengine.com/t/how-to-change-the-skeleton-of-an-animation-sequence/1338184)

---

## 조사 및 검증 일자

- **최초 조사**: 2026-02-04
- **검증 완료**: 2026-02-04
  - SKEL_Sh_Human_M_BaseSkeleton → SKEL_Sh_Human_F_BaseSkeleton 변경 성공
  - Consolidate+Rename 방식 작동 확인
  - 참조 무결성 유지 확인
