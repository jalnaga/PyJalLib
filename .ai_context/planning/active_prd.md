# Active PRD

## Title
Interchange Framework 모듈 외부 의존성 제거 및 경로 입력 단순화

---

## Background & Intent

### 현재 상태
- `inUnreal/` 모듈들이 `pyjallib.naming.Naming` 외부 패키지에 의존함
- FBX 경로를 Content 경로로 변환하는 복잡한 로직 사용 (`fbxRootPrefix` → `contentRootPrefix` 치환)
- Interchange Framework를 사용하지 않는 레거시 임포터 코드가 혼재
- `baseImporter.py`가 추상 클래스로 복잡한 상속 구조를 강제함

### 목표
- `inUnreal/` 폴더의 모든 코드를 **파이썬 표준 라이브러리 + unreal 모듈**만 사용하도록 변경
- 사용자가 **소스 FBX 절대 경로 + 목적지 Content 경로**를 직접 입력하는 단순한 인터페이스
- `baseImporter.py` 제거 → `pathUtils.py` 유틸리티 모듈로 대체
- Interchange Framework를 사용하지 않는 레거시 코드 제거

### 왜 이 작업이 필요한가?
- 언리얼 에디터 환경에서는 외부 파이썬 패키지 설치가 어렵고 불안정함
- 경로 변환 로직의 단순화로 유지보수성 향상
- 불필요한 추상 클래스 상속 제거로 코드 명확성 향상
- 불필요한 레거시 코드 제거로 코드베이스 정리

---

## Primary Manual

`.ai_context/manuals/task_loop.md`

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)

1. **새 유틸리티 모듈 생성: `pathUtils.py`**
   - 절대 경로 → `/Game/...` Content 경로 변환
   - 디렉토리 존재 확인/생성
   - 파이썬 표준 라이브러리 + `unreal` 모듈만 사용

2. **레거시 코드 제거**
   - `baseImporter.py` 제거
   - `importerSettings.py` 제거 (FBX UI 옵션 - Interchange에서 불필요)
   - `skeletonImporter.py` 제거
   - `skeletalMeshImporter.py` 제거
   - `animationImporter.py` 제거
   - 레거시 템플릿 제거:
     - `skeletonImportTemplate.py`
     - `skeletalMeshImportTemplate.py`
     - `animImportTemplate.py`
     - `batchAnimImportTemplate.py`

3. **Interchange 임포터 리팩토링**
   - `InterchangeImporterBase` - baseImporter 상속 제거, pathUtils 사용
   - `InterchangeSkeletonImporter` - 새 인터페이스 (경로 직접 입력)
   - `InterchangeSkeletalMeshImporter` - 새 인터페이스 (스켈레톤 경로 직접 입력)
   - `InterchangeAnimationImporter` - 새 인터페이스 (스켈레톤 경로 직접 입력)

4. **`interchangePipelineSettings.py` 정리**
   - 외부 의존성 확인 및 제거 (있다면)

5. **`inUnreal/__init__.py` 업데이트**
   - 레거시 임포터 export 제거
   - `pathUtils` export 추가

6. **`templates/__init__.py` 업데이트**
   - 레거시 템플릿 상수 및 매핑 제거

7. **`templateProcessor.py` 업데이트**
   - 레거시 템플릿 관련 메서드 제거
   - Interchange 템플릿만 지원

8. **Interchange 템플릿 업데이트**
   - 새로운 인터페이스에 맞게 템플릿 수정

### [Should-Have] (P1 - 권장)

1. **로깅 시스템 단순화**
   - `logger.py`의 UE5Logger를 더 가벼운 형태로 리팩토링 가능
   - 현재도 표준 라이브러리만 사용하므로 우선순위 낮음

### [Nice-to-Have] (P2 - 부가)

1. 임포트 결과 형식 개선
2. 에러 메시지 국제화

### [Non-Goal] (Out of Scope)

1. **UE5 API 변경** - `unreal` 모듈 의존성은 유지 (UE5 환경에서 필수)
2. **새로운 임포트 타입 추가** - 기존 3가지 타입(Skeleton, SkeletalMesh, Animation)만 지원
3. **소스 컨트롤 통합 제거** - 기존 체크아웃/체크인 로직 유지
4. **`inUnreal/` 폴더 외부 코드 변경** - templateProcessor.py 외부의 의존성 구조는 변경하지 않음

---

## Technical Decisions

### 아키텍처 변경: 상속 → 구성(Composition)

**Before (상속 기반):**
```
baseImporter.py (ABC)
    └── interchangeImporterBase.py
            ├── interchangeSkeletonImporter.py
            ├── interchangeSkeletalMeshImporter.py
            └── interchangeAnimationImporter.py
```

**After (구성 기반):**
```
pathUtils.py (순수 유틸리티 함수)
    ↑ 사용
interchangeImporterBase.py (독립 클래스)
    ├── interchangeSkeletonImporter.py
    ├── interchangeSkeletalMeshImporter.py
    └── interchangeAnimationImporter.py
```

### 새 파일 구조

```
inUnreal/
├── pathUtils.py                    # NEW: 경로 변환 유틸리티
├── interchangeImporterBase.py      # 리팩토링
├── interchangeSkeletonImporter.py  # 리팩토링
├── interchangeSkeletalMeshImporter.py  # 리팩토링
├── interchangeAnimationImporter.py # 리팩토링
├── interchangePipelineSettings.py  # 정리
└── __init__.py                     # 업데이트
```

### `pathUtils.py` 설계

```python
"""경로 변환 유틸리티 - 파이썬 표준 라이브러리 + unreal만 사용"""
from pathlib import Path
import unreal

def absolute_path_to_content_path(inAbsolutePath: str) -> str:
    """절대 경로를 /Game/... Content 경로로 변환"""
    pass

def ensure_directory_exists(inContentPath: str) -> bool:
    """Content 경로의 디렉토리가 존재하는지 확인하고 생성"""
    pass

def checkout_or_add_file(inContentPath: str) -> bool:
    """소스 컨트롤 체크아웃"""
    pass
```

### 인터페이스 변경

**Before:**
```python
importer = InterchangeSkeletonImporter(
    inContentRootPrefix="D:/UE5/Content/Characters",
    inFbxRootPrefix="D:/Export/FBX"
)
result = importer.import_skeleton("D:/Export/FBX/Hero/SK_Hero.fbx")
```

**After:**
```python
importer = InterchangeSkeletonImporter()
result = importer.import_skeleton(
    inFbxPath="D:/Export/FBX/Hero/SK_Hero.fbx",
    inDestinationPath="/Game/Characters/Hero",
    inAssetName="SK_Hero"  # 선택적
)
```

**SkeletalMesh/Animation (스켈레톤 경로 직접 입력):**
```python
importer = InterchangeSkeletalMeshImporter()
result = importer.import_skeletal_mesh(
    inFbxPath="D:/Export/FBX/Hero/SKM_Hero.fbx",
    inDestinationPath="/Game/Characters/Hero",
    inSkeletonPath="/Game/Characters/Hero/SK_Hero",  # 직접 입력
    inAssetName="SKM_Hero"
)
```

---

## File Change Summary

| 파일 | 변경 내용 |
|------|----------|
| `inUnreal/pathUtils.py` | **신규 생성** - 경로 변환 유틸리티 |
| `inUnreal/baseImporter.py` | **삭제** |
| `inUnreal/importerSettings.py` | **삭제** |
| `inUnreal/skeletonImporter.py` | **삭제** |
| `inUnreal/skeletalMeshImporter.py` | **삭제** |
| `inUnreal/animationImporter.py` | **삭제** |
| `inUnreal/interchangeImporterBase.py` | 리팩토링 (상속 제거, pathUtils 사용) |
| `inUnreal/interchangeSkeletonImporter.py` | 리팩토링 (새 인터페이스) |
| `inUnreal/interchangeSkeletalMeshImporter.py` | 리팩토링 (새 인터페이스) |
| `inUnreal/interchangeAnimationImporter.py` | 리팩토링 (새 인터페이스) |
| `inUnreal/interchangePipelineSettings.py` | 정리 (외부 의존성 제거) |
| `inUnreal/__init__.py` | 업데이트 (레거시 제거, pathUtils 추가) |
| `templates/skeletonImportTemplate.py` | **삭제** |
| `templates/skeletalMeshImportTemplate.py` | **삭제** |
| `templates/animImportTemplate.py` | **삭제** |
| `templates/batchAnimImportTemplate.py` | **삭제** |
| `templates/interchangeSkeletonImportTemplate.py` | 업데이트 (새 인터페이스) |
| `templates/interchangeSkeletalMeshImportTemplate.py` | 업데이트 (새 인터페이스) |
| `templates/interchangeAnimImportTemplate.py` | 업데이트 (새 인터페이스) |
| `templates/interchangeBatchAnimImportTemplate.py` | 업데이트 (새 인터페이스) |
| `templates/__init__.py` | 레거시 상수 제거 |
| `templateProcessor.py` | 레거시 메서드 제거 |
