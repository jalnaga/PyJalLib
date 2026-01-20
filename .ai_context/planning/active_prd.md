# UE 5.7 Interchange Framework 기반 에셋 임포터 모듈

## Background & Intent

### 왜 이 기능을 만드는가?

현재 PyJalLib의 UE5 임포터 모듈들(`skeletonImporter.py`, `skeletalMeshImporter.py`, `animationImporter.py`)은 레거시 FBX Importer(`unreal.AssetImportTask` + `unreal.FbxImportUI`)를 사용하고 있습니다.

UE 5.7에서는 Interchange Framework가 새로운 표준 에셋 교환 시스템으로 자리잡았으며, 다음과 같은 이점을 제공합니다:

1. **확장 가능한 파이프라인 아키텍처**: 커스텀 파이프라인 에셋을 통한 임포트 설정 관리
2. **더 세밀한 제어**: 파이프라인 속성을 통한 정밀한 임포트 옵션 제어
3. **향후 호환성**: Epic의 공식 로드맵에서 Interchange가 표준으로 확정됨
4. **동기 임포트 지원**: `import_asset()` 메서드를 통한 안정적인 동기 임포트

### 의사 결정 기록

| 결정 사항 | 선택 | 이유 |
|-----------|------|------|
| 모듈 추가 방식 | **기존 inUnreal 패키지에 추가** | 새로운 Interchange 기반 임포터로 완전 대체 |
| BaseImporter 상속 vs 새 베이스 | **상속** | 경로 변환, 네이밍 시스템 재사용 |
| 파이프라인 설정 방식 | **별도 설정 클래스** | 관심사 분리, 프리셋 시스템 확장성 |

---

## Primary Manual

`.ai_context/manuals/new_module_creation.md`

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)

1. **`interchangeImporterBase.py`** - Interchange 베이스 클래스
   - `BaseImporter` 상속
   - `InterchangeManager` 래핑 (동기/비동기 임포트)
   - `InterchangeSourceData` 생성 유틸리티
   - `SoftObjectPath` 변환 유틸리티
   - 비동기 콜백 인프라 (배치 임포트용)
   - 에러 처리 및 로깅

2. **`interchangePipelineSettings.py`** - 파이프라인 설정 관리
   - 프로젝트 표준 파이프라인 에셋 경로 관리
   - Skeleton/SkeletalMesh/Animation 프리셋 설정
   - `InterchangeGenericAssetsPipeline` 속성 설정 헬퍼
   - 런타임 파이프라인 속성 오버라이드 지원

3. **`interchangeSkeletonImporter.py`** - 스켈레톤 임포터
   - 새 스켈레톤 생성 임포트
   - 단일 임포트: `import_skeleton()` (동기)
   - 배치 임포트: `import_skeletons()` (비동기 콜백 방식)
   - `ImportedObjects` 필드 추가

4. **`interchangeSkeletalMeshImporter.py`** - 스켈레탈 메시 임포터
   - 기존 스켈레톤 참조 필수
   - 단일 임포트: `import_skeletal_mesh()` (동기)
   - 배치 임포트: `import_skeletal_meshes()` (비동기 콜백 방식)
   - 메시 임포트 옵션 (노멀, 모프 타겟 등)
   - 소스 컨트롤 체크인 통합

5. **`interchangeAnimationImporter.py`** - 애니메이션 임포터
   - 기존 스켈레톤 참조 필수
   - 단일 임포트: `import_animation()` (동기)
   - 배치 임포트: `import_animations()` (비동기 콜백 방식)
   - 기존 `animationImporter.py`와 동일한 인터페이스

6. **비동기 배치 임포트 인프라** (`interchangeImporterBase.py`에 포함)
   - `on_asset_done` 콜백: 개별 에셋 임포트 완료 시 호출
   - `on_assets_import_done` 콜백: 전체 배치 완료 시 호출
   - 임포트 진행 상태 추적
   - 에러 수집 및 보고

7. **`__init__.py` 업데이트** - 공개 API 노출 (Interchange 임포터 추가)

8. **`templates/` Interchange 버전 업데이트**
   - `interchangeAnimImportTemplate.py` - 애니메이션 임포트 템플릿
   - `interchangeBatchAnimImportTemplate.py` - 배치 애니메이션 임포트 템플릿
   - `interchangeSkeletonImportTemplate.py` - 스켈레톤 임포트 템플릿
   - `interchangeSkeletalMeshImportTemplate.py` - 스켈레탈 메시 임포트 템플릿
   - `templates/__init__.py` 업데이트 - 새 템플릿 상수 및 경로 추가
   - `templateProcessor.py` 업데이트 - Interchange 템플릿 처리 메서드 추가

### [Should-Have] (P1 - 권장)

1. **FBX Interchange 활성화 헬퍼**
   - 콘솔 명령 `Interchange.FeatureFlags.Import.FBX true` 자동 실행
   - 활성화 상태 확인 메서드

2. **파이프라인 에셋 런타임 수정**
   - `InterchangeGenericAssetsPipeline` 속성 직접 수정 API
   - 머티리얼/텍스처 임포트 비활성화 프리셋

### [Nice-to-Have] (P2 - 부가)

1. **리임포트 지원**
   - `reimport_asset` 파라미터 활용
   - 기존 에셋 업데이트 워크플로우

### [Non-Goal] (범위 제외)

1. **레거시 임포터 삭제** - 기존 `skeletonImporter.py`, `skeletalMeshImporter.py`, `animationImporter.py`, `importerSettings.py` 유지
2. **레거시 템플릿 삭제** - 기존 템플릿 파일들 유지
3. **StaticMesh 임포터** - 이번 스코프 제외
4. **머티리얼/텍스처 파이프라인 상세 구현** - 기본 비활성화로 처리
5. **Scene 임포트** - 에셋 단위 임포트만 지원
6. **파이프라인 에셋 파일 생성** - 런타임 설정만 지원 (에디터에서 미리 생성 필요)

---

## Technical Constraints

### UE 5.7 Interchange Python API 스펙

```python
# Manager 획득
interchange_manager = unreal.InterchangeManager.get_interchange_manager_scripted()

# SourceData 생성
source_data = unreal.InterchangeManager.create_source_data(file_name)

# 동기 임포트
imported_objects = interchange_manager.import_asset(
    content_path,
    source_data,
    import_asset_parameters
)
```

### 핵심 구현 포인트

1. **SoftObjectPath 변환 필수**
```python
# 올바른 방식
soft_path = unreal.SoftObjectPath(pipeline_asset_path)
import_params.override_pipelines = [soft_path]
```

2. **기존 인터페이스 스타일 유지**
```python
# 메서드명 및 파라미터 네이밍 컨벤션 유지
def import_skeleton(self, inFbxFile: str, inAssetName: str = None, inDescription: str = None) -> dict
def import_skeletal_mesh(self, inFbxFile: str, inFbxSkeletonPath: str, inAssetName: str = None, inDescription: str = None) -> dict
def import_animation(self, inFbxFile: str, inFbxSkeletonPath: str, inAssetName: str = None, inDescription: str = None) -> dict
def import_animations(self, inFbxFiles: list[str], inFbxSkeletonPaths: list[str], inAssetNames: list[str] = None, inDescription: str = None)
```

3. **반환 형식 (단일 임포트)**
```python
{
    "SourceFile": str,
    "Path": str,
    "Name": str,
    "Type": str,
    "Success": bool,
    "ImportedObjects": List[Object]  # Interchange 버전 추가
}
```

4. **비동기 배치 임포트 콜백**
```python
# ImportAssetParameters 콜백 설정
import_params.on_asset_done = self._on_single_asset_done      # 개별 완료
import_params.on_assets_import_done = self._on_batch_complete  # 전체 완료

# 콜백 시그니처 (UE5 API)
def on_asset_done(obj: Object) -> None
def on_assets_import_done(objects: Array[Object]) -> None
```

5. **배치 임포트 반환 형식**
```python
{
    "TotalCount": int,
    "SuccessCount": int,
    "FailedCount": int,
    "Results": List[dict],  # 개별 결과 딕셔너리 리스트
    "Errors": List[str]     # 에러 메시지 리스트
}
```

---

## File Structure

```
src/pyjallib/ue5/
├── inUnreal/
│   ├── __init__.py                         # 업데이트: Interchange 모듈 노출 추가
│   ├── baseImporter.py                     # 기존 유지 (경로 변환 로직 재사용)
│   ├── importerSettings.py                 # 기존 유지 (레거시)
│   ├── skeletonImporter.py                 # 기존 유지 (레거시)
│   ├── skeletalMeshImporter.py             # 기존 유지 (레거시)
│   ├── animationImporter.py                # 기존 유지 (레거시)
│   ├── interchangeImporterBase.py          # [신규] Interchange 베이스 클래스
│   ├── interchangePipelineSettings.py      # [신규] 파이프라인 설정 관리
│   ├── interchangeSkeletonImporter.py      # [신규] 스켈레톤 임포터
│   ├── interchangeSkeletalMeshImporter.py  # [신규] 스켈레탈 메시 임포터
│   └── interchangeAnimationImporter.py     # [신규] 애니메이션 임포터
│
├── templates/
│   ├── __init__.py                              # 업데이트: Interchange 템플릿 상수 추가
│   ├── animImportTemplate.py                    # 기존 유지 (레거시)
│   ├── batchAnimImportTemplate.py               # 기존 유지 (레거시)
│   ├── skeletonImportTemplate.py                # 기존 유지 (레거시)
│   ├── skeletalMeshImportTemplate.py            # 기존 유지 (레거시)
│   ├── interchangeAnimImportTemplate.py         # [신규]
│   ├── interchangeBatchAnimImportTemplate.py    # [신규]
│   ├── interchangeSkeletonImportTemplate.py     # [신규]
│   └── interchangeSkeletalMeshImportTemplate.py # [신규]
│
└── templateProcessor.py                    # 업데이트: Interchange 템플릿 처리 메서드 추가
```

---

## Success Criteria

1. 모든 신규 임포터가 기존 메서드명 및 `inCamelCase` 파라미터 컨벤션 유지
2. 내부적으로 UE5 `InterchangeManager.import_asset()` API를 사용하여 동기 임포트 수행
3. 기존 `baseImporter.py`의 경로 변환 로직 정상 재사용
4. 소스 컨트롤 체크아웃/체크인 정상 동작
5. 린트 통과 (`uv run ruff check .`)
