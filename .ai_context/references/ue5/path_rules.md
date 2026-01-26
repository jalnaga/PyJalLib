# UE5 Path Manipulation Rules

UE5 환경에서 파일 경로를 다룰 때 반드시 따라야 하는 규칙입니다.

---

## 공식 문서 링크

- **Python API Reference:** https://dev.epicgames.com/documentation/en-us/unreal-engine/PythonAPI
- **Python 스크립팅 가이드:** https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- **EditorAssetLibrary:** https://dev.epicgames.com/documentation/en-us/unreal-engine/PythonAPI/class/EditorAssetLibrary

---

## 핵심 원칙

1. **Content 경로 사용:** 에셋을 다룰 때는 항상 `/Game/...` 형식의 Content 경로를 사용합니다.
2. **절대 경로 변환:** 외부 파일(FBX 등)은 절대 경로를 사용하지만, 프로젝트 내 에셋으로 변환될 때는 Content 경로로 매핑해야 합니다.
3. **pathUtils 사용:** 직접 문자열 조작을 하지 말고 `pyjallib.ue5.inUnreal.pathUtils` 모듈을 사용합니다.

---

## 경로 변환 (Path Normalization)

절대 경로를 Content 경로로 변환할 때 다음 규칙을 따릅니다.

### 1. 절대 경로 -> Content 경로

```python
from pyjallib.ue5.inUnreal import pathUtils

# Input: "D:/Project/Content/Characters/Hero/SK_Hero.uasset"
# Output: "/Game/Characters/Hero/SK_Hero"
content_path = pathUtils.absolute_path_to_content_path(abs_path)
```

### 2. 자동 정규화 (추천)

입력이 절대 경로인지 Content 경로인지 모를 때 사용합니다.

```python
# Input: "D:/Project/..." OR "/Game/..."
# Output: "/Game/..."
normalized_path = pathUtils.normalize_content_path(input_path)
```

---

## 경로 유효성 검사

### 1. Content 경로 형식 확인

```python
if pathUtils.is_content_path(path):
    # /Game/ 또는 /Engine/ 으로 시작함
    pass
```

### 2. 디렉토리 존재 보장

디렉토리가 없으면 생성합니다.

```python
pathUtils.ensure_directory_exists("/Game/New/Path")
```

---

## 소스 컨트롤 (Perforce) 연동

UE5 에디터 내에서는 `unreal.SourceControl`을 사용해야 합니다 (P4Python 직접 사용 금지).

```python
# 파일이 존재하면 체크아웃, 없으면 마크 포 애드
pathUtils.checkout_or_add_file("/Game/Characters/MyAsset")
```

---

## 참고 코드 (`pathUtils.py`)

- `absolute_path_to_content_path()`: 절대 경로 -> Content 경로
- `normalize_content_path()`: 스마트 변환
- `ensure_directory_exists()`: 디렉토리 생성 (EditorAssetLibrary 사용)
