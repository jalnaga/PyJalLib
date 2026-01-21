# PyJalLib UE5 모듈 사용법

## 개요

이 문서는 PyJalLib의 `ue5` 모듈을 사용하여 3DS Max 등 DCC에서 Unreal Engine 5로 에셋을 임포트하는 전체 워크플로우를 설명합니다.

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                         3DS Max (DCC)                               │
│  ┌─────────────────┐    ┌─────────────────────────────────────────┐│
│  │  FBX 익스포트   │───>│  TemplateProcessor                      ││
│  │  (캐릭터/애니)  │    │  - 템플릿 + 데이터 → UE5용 .py 스크립트 ││
│  └─────────────────┘    └──────────────────┬──────────────────────┘│
└────────────────────────────────────────────│────────────────────────┘
                                             │ 생성된 .py 파일
                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Unreal Engine 5 Editor                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Python 스크립트 실행                                           ││
│  │  - InterchangeSkeletonImporter                                  ││
│  │  - InterchangeSkeletalMeshImporter                              ││
│  │  - InterchangeAnimationImporter                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Content Browser에 에셋 임포트 완료                              ││
│  │  /Game/Characters/Hero/SK_Hero, SKM_Hero, A_Hero_Run...         ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 모듈 구조

| 모듈 | 실행 환경 | 역할 |
|------|----------|------|
| `pyjallib.ue5.TemplateProcessor` | **DCC (3DS Max 등)** | UE5용 스크립트 생성 |
| `pyjallib.ue5.templates` | **DCC (3DS Max 등)** | 템플릿 파일 관리 |
| `pyjallib.ue5.inUnreal.*` | **UE5 Editor 내부** | 실제 임포트 실행 |

> **Note:** `inUnreal` 폴더의 모듈들은 `import unreal`이 필요하므로 **UE5 에디터 내에서만** 실행 가능합니다.

---

## Step 1: 3DS Max에서 UE5 스크립트 생성

### 1-1. 스켈레톤 임포트 스크립트 생성

```python
from pyjallib.ue5 import TemplateProcessor

processor = TemplateProcessor()

# 스크립트 출력 경로 설정 (선택적)
processor.set_default_output_directory("D:/UE5_Scripts")

# 템플릿 데이터 설정
templateData = {
    "inExtPackagePath": "D:/PyJalLib/src",           # PyJalLib 패키지 경로
    "inFbxPath": "D:/Export/FBX/Hero/SK_Hero.fbx",   # 익스포트한 FBX 파일
    "inDestinationPath": "/Game/Characters/Hero",    # UE5 Content 경로
    "inAssetName": "SK_Hero"                         # 에셋 이름 (선택적)
}

# UE5용 파이썬 스크립트 생성
processor.process_interchange_skeleton_import_template(
    inTemplateData=templateData,
    inOutputPath="D:/UE5_Scripts/import_hero_skeleton.py"
)
```

### 1-2. 스켈레탈 메쉬 임포트 스크립트 생성

```python
from pyjallib.ue5 import TemplateProcessor

processor = TemplateProcessor()

templateData = {
    "inExtPackagePath": "D:/PyJalLib/src",
    "inFbxPath": "D:/Export/FBX/Hero/SKM_Hero.fbx",
    "inDestinationPath": "/Game/Characters/Hero",
    "inSkeletonPath": "/Game/Characters/Hero/SK_Hero",  # 기존 스켈레톤 경로 (필수)
    "inAssetName": "SKM_Hero"
}

processor.process_interchange_skeletal_mesh_import_template(
    inTemplateData=templateData,
    inOutputPath="D:/UE5_Scripts/import_hero_mesh.py"
)
```

### 1-3. 애니메이션 임포트 스크립트 생성 (단일)

```python
from pyjallib.ue5 import TemplateProcessor

processor = TemplateProcessor()

templateData = {
    "inExtPackagePath": "D:/PyJalLib/src",
    "inFbxPath": "D:/Export/FBX/Hero/A_Hero_Run.fbx",
    "inDestinationPath": "/Game/Characters/Hero/Animations",
    "inSkeletonPath": "/Game/Characters/Hero/SK_Hero",  # 기존 스켈레톤 경로 (필수)
    "inAssetName": "A_Hero_Run"
}

processor.process_interchange_animation_import_template(
    inTemplateData=templateData,
    inOutputPath="D:/UE5_Scripts/import_hero_run.py"
)
```

### 1-4. 애니메이션 배치 임포트 스크립트 생성 (여러 파일)

```python
from pyjallib.ue5 import TemplateProcessor

processor = TemplateProcessor()

# 리스트를 템플릿용 문자열로 변환
fbxPaths = processor.format_list_for_template([
    "D:/Export/FBX/Hero/A_Hero_Run.fbx",
    "D:/Export/FBX/Hero/A_Hero_Walk.fbx",
    "D:/Export/FBX/Hero/A_Hero_Jump.fbx"
])

destPaths = processor.format_list_for_template([
    "/Game/Characters/Hero/Animations",
    "/Game/Characters/Hero/Animations",
    "/Game/Characters/Hero/Animations"
])

skeletonPaths = processor.format_list_for_template([
    "/Game/Characters/Hero/SK_Hero",
    "/Game/Characters/Hero/SK_Hero",
    "/Game/Characters/Hero/SK_Hero"
])

assetNames = processor.format_list_for_template([
    "A_Hero_Run",
    "A_Hero_Walk",
    "A_Hero_Jump"
])

templateData = {
    "inExtPackagePath": "D:/PyJalLib/src",
    "inFbxPaths": fbxPaths,
    "inDestinationPaths": destPaths,
    "inSkeletonPaths": skeletonPaths,
    "inAssetNames": assetNames
}

processor.process_interchange_batch_anim_import_template(
    inTemplateData=templateData,
    inOutputPath="D:/UE5_Scripts/import_hero_animations_batch.py"
)
```

---

## Step 2: UE5 에디터에서 스크립트 실행

### 방법 A: UE5 Output Log에서 직접 실행

```
py "D:/UE5_Scripts/import_hero_skeleton.py"
```

### 방법 B: Python Editor에서 실행

1. UE5 메뉴: `Window > Developer Tools > Output Log`
2. 또는 `Edit > Editor Preferences > Plugins > Python`에서 Python 스크립트 실행

### 방법 C: Remote Execution (원격 실행)

3DS Max에서 UE5로 직접 스크립트를 전송하여 실행 (별도 설정 필요)

---

## UE5 에디터 내에서 직접 사용 (스크립트 없이)

UE5 에디터 내에서 직접 Python을 실행할 수 있는 경우, `TemplateProcessor` 없이 Importer를 직접 사용할 수 있습니다.

### 스켈레톤 임포트

```python
from pyjallib.ue5.inUnreal import InterchangeSkeletonImporter

importer = InterchangeSkeletonImporter()

result = importer.import_skeleton(
    inFbxPath="D:/Export/FBX/Hero/SK_Hero.fbx",
    inDestinationPath="/Game/Characters/Hero",
    inAssetName="SK_Hero"  # 선택적
)

if result["Success"]:
    print(f"임포트 성공: {result['Name']}")
```

### 스켈레탈 메쉬 임포트

```python
from pyjallib.ue5.inUnreal import InterchangeSkeletalMeshImporter

importer = InterchangeSkeletalMeshImporter()

result = importer.import_skeletal_mesh(
    inFbxPath="D:/Export/FBX/Hero/SKM_Hero.fbx",
    inDestinationPath="/Game/Characters/Hero",
    inSkeletonPath="/Game/Characters/Hero/SK_Hero",  # 필수
    inAssetName="SKM_Hero"  # 선택적
)
```

### 애니메이션 임포트

```python
from pyjallib.ue5.inUnreal import InterchangeAnimationImporter

importer = InterchangeAnimationImporter()

result = importer.import_animation(
    inFbxPath="D:/Export/FBX/Hero/A_Hero_Run.fbx",
    inDestinationPath="/Game/Characters/Hero/Animations",
    inSkeletonPath="/Game/Characters/Hero/SK_Hero",  # 필수
    inAssetName="A_Hero_Run"  # 선택적
)
```

### 애니메이션 배치 임포트

```python
from pyjallib.ue5.inUnreal import InterchangeAnimationImporter

importer = InterchangeAnimationImporter()

result = importer.import_animations(
    inFbxPaths=["D:/FBX/Hero_Run.fbx", "D:/FBX/Hero_Walk.fbx"],
    inDestinationPaths=["/Game/Animations/Hero", "/Game/Animations/Hero"],
    inSkeletonPaths=["/Game/Characters/Hero/SK_Hero", "/Game/Characters/Hero/SK_Hero"],
    inAssetNames=["A_Hero_Run", "A_Hero_Walk"]  # 선택적
)

print(f"성공: {result['SuccessCount']}/{result['TotalCount']}")
```

---

## 공통 사항

| 항목 | 설명 |
|------|------|
| **FBX 경로** | Windows 절대 경로 (예: `D:/Export/FBX/...`) |
| **Content 경로** | `/Game/`으로 시작하는 UE5 Content 경로 |
| **에셋 이름** | 생략 시 FBX 파일명 기반으로 자동 생성 (접두사 자동 추가) |
| **기본 접두사** | Skeleton: `SK_`, SkeletalMesh: `SKM_`, Animation: `A_` |
| **소스 컨트롤** | Perforce 연동 시 자동 체크아웃/체크인 처리 |

---

## 반환값 구조

### 단일 임포트 결과

```python
{
    "SourceFile": "D:/FBX/Hero.fbx",
    "Path": "/Game/Characters/Hero",
    "Name": "SK_Hero",
    "Success": True,
    "ImportedObjects": [<unreal.Object>, ...]
}
```

### 배치 임포트 결과

```python
{
    "TotalCount": 3,
    "SuccessCount": 3,
    "FailedCount": 0,
    "Results": [...],  # 각 파일의 단일 임포트 결과 리스트
    "Errors": []       # 에러 메시지 리스트
}
```

---

## 전체 워크플로우 요약

| 단계 | 환경 | 사용 도구 | 설명 |
|------|------|----------|------|
| 1 | 3DS Max | FBX Exporter | 캐릭터/애니메이션 FBX 익스포트 |
| 2 | 3DS Max | `TemplateProcessor` | UE5용 .py 스크립트 생성 |
| 3 | UE5 Editor | Python 실행 | 생성된 스크립트 실행 |
| 4 | UE5 Editor | `Interchange*Importer` | 실제 에셋 임포트 수행 |
