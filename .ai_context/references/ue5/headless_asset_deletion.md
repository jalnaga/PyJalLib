# UE5 Headless 모드에서 에셋 삭제

Headless 모드(`-nullrhi`, `-unattended`)에서 에셋을 완전히 삭제하는 방법입니다.

---

## 문제

`unreal.EditorAssetLibrary.delete_asset()`은 Headless 모드에서 **에디터 메모리에서만** 에셋을 삭제합니다.
실제 디스크의 `.uasset` 파일은 삭제되지 않습니다.

이로 인해 `rename_asset()` 등의 후속 작업이 "An asset already exists at this location" 오류로 실패합니다.

---

## 해결 방법

디스크 파일을 직접 삭제하고 AssetRegistry를 동기화해야 합니다.

```python
import os
import unreal

def delete_asset_headless_safe(assetPath: str, parentFolder: str):
    """
    Headless 모드에서 에셋을 완전히 삭제합니다.

    Args:
        assetPath: 에셋 콘텐츠 경로 (예: /Game/Characters/Animations/Walk)
        parentFolder: 부모 폴더 경로 (예: /Game/Characters/Animations)
    """
    # 1. 에디터에서 에셋 삭제 (메모리에서 제거)
    deleteResult = unreal.EditorAssetLibrary.delete_asset(assetPath)
    unreal.log(f"delete_asset() 결과: {deleteResult}")

    # 2. 디스크 파일 직접 삭제
    contentDir = unreal.Paths.project_content_dir()
    # /Game/... -> Content/... 경로로 변환
    relativePath = assetPath.replace("/Game/", "")
    diskPath = os.path.join(contentDir, relativePath + ".uasset")
    diskPath = os.path.normpath(diskPath)

    if os.path.exists(diskPath):
        try:
            os.remove(diskPath)
            unreal.log(f"디스크 파일 삭제 성공: {diskPath}")
        except OSError as e:
            unreal.log_error(f"디스크 파일 삭제 실패: {e}")

    # 3. AssetRegistry 동기화 (디스크 상태 반영)
    assetRegistry = unreal.AssetRegistryHelpers.get_asset_registry()
    assetRegistry.scan_paths_synchronous([parentFolder], force_rescan=True)
    unreal.log("AssetRegistry 갱신 완료")

    # 4. Garbage Collection (메모리 참조 정리)
    unreal.SystemLibrary.collect_garbage()
    unreal.log("Garbage Collection 완료")

    # 5. 삭제 확인
    stillExists = unreal.EditorAssetLibrary.does_asset_exist(assetPath)
    if stillExists:
        unreal.log_error(f"에셋이 여전히 존재함: {assetPath}")
    else:
        unreal.log(f"에셋 완전 삭제 완료: {assetPath}")
```

---

## 경로 변환

| 콘텐츠 경로 | 디스크 경로 |
|------------|------------|
| `/Game/Characters/Anim/Walk` | `{ProjectDir}/Content/Characters/Anim/Walk.uasset` |
| `/Game/Test/MyAsset` | `{ProjectDir}/Content/Test/MyAsset.uasset` |

```python
# 콘텐츠 경로 → 디스크 경로 변환
contentDir = unreal.Paths.project_content_dir()  # D:/root/Project/Content/
relativePath = assetPath.replace("/Game/", "")   # Characters/Anim/Walk
diskPath = os.path.join(contentDir, relativePath + ".uasset")
diskPath = os.path.normpath(diskPath)  # 경로 정규화
```

---

## 사용 사례: Consolidate + Rename 패턴

스켈레톤 변경 시 Consolidate로 생성된 Redirector를 삭제하고 Rename하는 패턴:

```python
# 1. Consolidate 실행 (참조 리다이렉트)
unreal.EditorAssetLibrary.consolidate_assets(newAsset, [oldAsset])

# 2. Redirector(기존 경로) 삭제 - Headless Safe
delete_asset_headless_safe(oldAssetPath, parentFolder)

# 3. Rename으로 원래 경로 복원
unreal.EditorAssetLibrary.rename_asset(tempPath, oldAssetPath)
```

---

## 주의사항

1. **GUI 모드에서는 불필요**: GUI 모드에서는 `delete_asset()`이 디스크 파일도 삭제함
2. **AssetRegistry 동기화 필수**: `os.remove()` 후 `scan_paths_synchronous()` 없이는 `does_asset_exist()`가 여전히 True 반환
3. **GC 실행 권장**: 메모리 참조가 남아있으면 후속 작업에서 문제 발생 가능

---

## 관련 API

| API | 설명 |
|-----|------|
| `EditorAssetLibrary.delete_asset()` | 에디터에서 에셋 삭제 (Headless: 메모리만) |
| `Paths.project_content_dir()` | 프로젝트 Content 폴더 경로 |
| `AssetRegistryHelpers.get_asset_registry()` | AssetRegistry 인스턴스 |
| `IAssetRegistry.scan_paths_synchronous()` | 지정 경로 동기 스캔 |
| `SystemLibrary.collect_garbage()` | Garbage Collection 실행 |

---

## 참고

- [headless_execution.md](./headless_execution.md) - Headless 모드 실행 가이드
