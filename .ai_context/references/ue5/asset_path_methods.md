# UE5 에셋 경로 메서드 비교

언리얼 에셋의 경로를 가져오는 여러 메서드의 차이점입니다.

---

## 공식 문서 링크

- **Python API Reference:** https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/?application_version=5.7
- **Asset Registry:** https://dev.epicgames.com/documentation/en-us/unreal-engine/asset-registry-in-unreal-engine
- **EditorAssetLibrary:** https://dev.epicgames.com/documentation/en-us/unreal-engine/PythonAPI/class/EditorAssetLibrary

---

## 메서드 비교

### `get_path_name()` - 패키지 경로 (권장)

```python
asset = unreal.load_asset("/Game/Characters/SK_Hero")
path = asset.get_path_name()
# 결과: "/Game/Characters/SK_Hero.SK_Hero"
```

**용도:**
- 에셋 레지스트리 조회
- 에셋 의존성 확인
- `EditorAssetLibrary` 함수에 전달

### `get_system_path()` - 파일 시스템 경로 (주의 필요)

```python
asset = unreal.load_asset("/Game/Characters/SK_Hero")
path = asset.get_system_path()
# 결과: "D:/Project/Content/Characters/SK_Hero.uasset"
# 또는 None (런타임 에셋의 경우)
```

**문제점:**
- 에셋이 아직 저장되지 않은 경우 `None` 반환
- `FindAssetData failed` 에러 발생 가능
- 런타임에서 생성된 에셋은 시스템 경로가 없음

---

## 일반적인 에러 패턴

### 잘못된 사용 (에러 발생)

```python
# FindAssetData failed 에러 발생 가능
imported_objects = importer.import_asset(...)
for obj in imported_objects:
    system_path = obj.get_system_path()  # None일 수 있음
    asset_data = registry.get_asset_by_object_path(system_path)  # 실패
```

### 올바른 사용

```python
# 패키지 경로 사용
imported_objects = importer.import_asset(...)
for obj in imported_objects:
    package_path = obj.get_path_name()
    asset_data = registry.get_asset_by_object_path(package_path)  # 성공
```

---

## 경로 형식 정리

| 메서드 | 반환 형식 | 예시 |
|--------|----------|------|
| `get_path_name()` | 패키지 경로 | `/Game/Characters/SK_Hero.SK_Hero` |
| `get_system_path()` | 절대 파일 경로 | `D:/Project/Content/Characters/SK_Hero.uasset` |
| `get_outer()` | 패키지 오브젝트 | `<Package /Game/Characters/SK_Hero>` |
| `get_name()` | 에셋 이름만 | `SK_Hero` |

---

## 권장 사항

1. **에셋 레지스트리 조회:** `get_path_name()` 사용
2. **파일 복사/이동:** `get_system_path()` 사용 (None 체크 필수)
3. **로깅/디버깅:** `get_name()` 또는 `get_path_name()` 사용

---

## 참고: 발견 경위

- **발견일:** 2026-01-26
- **문제:** 임포트 후 에셋 의존성 확인 시 `FindAssetData failed` 에러
- **원인:** `get_system_path()` 사용으로 None 또는 잘못된 경로 전달
- **해결:** `get_path_name()` 사용으로 패키지 경로 전달
