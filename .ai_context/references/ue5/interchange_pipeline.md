# UE5 Interchange Pipeline 설정

Interchange Framework를 사용한 FBX 임포트 시 파이프라인 설정 방법입니다.

---

## 공식 문서 링크

- **Python API Reference:** https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/?application_version=5.7
- **Python 스크립팅 가이드:** https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- **Interchange Framework:** https://dev.epicgames.com/documentation/en-us/unreal-engine/interchange-framework-in-unreal-engine

---

## 기본 파이프라인 경로

```python
# 올바른 기본 파이프라인 경로
PIPELINE_PATH = "/Interchange/Pipelines/DefaultAssetsPipeline.DefaultAssetsPipeline"

# 잘못된 예시 (존재하지 않음)
# "/Interchange/Pipelines/DefaultGenericPipeline"
```

**주의:** 파이프라인 에셋이 존재하는지 확인 후 사용해야 합니다.

```python
import unreal

def is_pipeline_asset_valid(pipeline_path: str) -> bool:
    """파이프라인 에셋 존재 여부 확인"""
    asset_data = unreal.AssetRegistryHelpers.get_asset_registry().get_asset_by_object_path(pipeline_path)
    return asset_data.is_valid()
```

---

## 파이프라인 옵션 구조

`InterchangeAssetImportData`에서 파이프라인을 가져오면 내부에 여러 sub-pipeline이 있습니다.

```python
# 파이프라인 가져오기
pipelines = import_asset_parameters.get_editor_property("pipelines")
generic_pipeline = pipelines[0]  # InterchangeGenericAssetsPipeline

# Sub-pipeline 접근
mesh_pipeline = generic_pipeline.get_editor_property("mesh_pipeline")
animation_pipeline = generic_pipeline.get_editor_property("animation_pipeline")
material_pipeline = generic_pipeline.get_editor_property("material_pipeline")
```

---

## 임포트 필터링 설정

### 스켈레톤만 임포트 (애니메이션/머티리얼/텍스쳐 제외)

```python
def configure_for_skeleton(generic_pipeline):
    """스켈레톤 임포트용 설정"""
    
    # 애니메이션 비활성화
    animation_pipeline = generic_pipeline.get_editor_property("animation_pipeline")
    animation_pipeline.set_editor_property("import_animations", False)
    
    # 머티리얼/텍스쳐 비활성화
    material_pipeline = generic_pipeline.get_editor_property("material_pipeline")
    material_pipeline.set_editor_property("import_materials", False)
    
    texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")
    texture_pipeline.set_editor_property("import_textures", False)
    
    # 피직스 에셋 비활성화
    mesh_pipeline = generic_pipeline.get_editor_property("mesh_pipeline")
    mesh_pipeline.set_editor_property("create_physics_asset", False)
```

### 스켈레탈 메시 임포트 (기존 스켈레톤 참조)

**핵심:** 스켈레탈 메시도 `common_skeletal_meshes_and_animations_properties`를 통해 스켈레톤 설정 필요

```python
def configure_for_skeletal_mesh(generic_pipeline, skeleton: unreal.Skeleton):
    """스켈레탈 메시 임포트용 설정 (기존 스켈레톤 참조)"""
    
    # 1. common_skeletal_meshes_and_animations_properties를 통한 스켈레톤 설정 (핵심!)
    common_skeletal_props = generic_pipeline.get_editor_property(
        "common_skeletal_meshes_and_animations_properties"
    )
    common_skeletal_props.set_editor_property("skeleton", skeleton)
    
    # 2. 애니메이션 비활성화
    animation_pipeline = generic_pipeline.get_editor_property("animation_pipeline")
    animation_pipeline.set_editor_property("import_animations", False)
    
    # 3. 머티리얼/텍스쳐 비활성화
    material_pipeline = generic_pipeline.get_editor_property("material_pipeline")
    material_pipeline.set_editor_property("import_materials", False)
    
    texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")
    texture_pipeline.set_editor_property("import_textures", False)
    
    # 4. 피직스 에셋 비활성화
    mesh_pipeline = generic_pipeline.get_editor_property("mesh_pipeline")
    mesh_pipeline.set_editor_property("create_physics_asset", False)
```

**주의 사항:**
- 스켈레톤 설정 없이 임포트 시 새 스켈레톤이 생성됨
- 의상/소품 등 메시는 반드시 기존 베이스 스켈레톤을 참조해야 함

### 애니메이션만 임포트 (기존 스켈레톤 사용)

**핵심:** 스켈레톤은 `common_skeletal_meshes_and_animations_properties`를 통해 설정

**공식 문서:**
- https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericCommonSkeletalMeshesAndAnimationsProperties?application_version=5.7

```python
def configure_for_animation(generic_pipeline, skeleton: unreal.Skeleton):
    """애니메이션 임포트용 설정 (기존 스켈레톤 참조)"""
    
    # 1. 애니메이션 임포트 활성화
    animation_pipeline = generic_pipeline.get_editor_property("animation_pipeline")
    animation_pipeline.set_editor_property("import_animations", True)
    
    # 2. common_skeletal_meshes_and_animations_properties를 통한 스켈레톤 설정 (핵심!)
    # 주의: animation_pipeline.skeleton 속성은 UE5에 존재하지 않음
    common_skeletal_props = generic_pipeline.get_editor_property(
        "common_skeletal_meshes_and_animations_properties"
    )
    common_skeletal_props.set_editor_property("skeleton", skeleton)
    common_skeletal_props.set_editor_property("import_only_animations", True)
    
    # 3. 머티리얼/텍스쳐 비활성화
    material_pipeline = generic_pipeline.get_editor_property("material_pipeline")
    material_pipeline.set_editor_property("import_materials", False)
    
    texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")
    texture_pipeline.set_editor_property("import_textures", False)
```

**주의 사항:**
- `animation_pipeline.skeleton` 속성은 **존재하지 않음** (Failed to find property 'skeleton' 에러 발생)
- 반드시 `common_skeletal_meshes_and_animations_properties.skeleton`을 사용해야 함
- `import_only_animations=True` 설정 시 스켈레탈 메시/스켈레톤 생성 없이 애니메이션만 임포트

---

## 임포트 결과물 비교

| 설정 | 생성되는 에셋 |
|------|-------------|
| 기본값 (필터 없음) | SkeletalMesh, Skeleton, PhysicsAsset, Materials, Textures, AnimSequences |
| 스켈레톤 전용 | SkeletalMesh, Skeleton (2개) |
| 스켈레탈 메시 (기존 스켈레톤 참조) | SkeletalMesh (1개) - 스켈레톤은 기존 에셋 참조 |
| 애니메이션 전용 | AnimSequence (1개) |

---

## 파이프라인 로드 및 설정 적용 순서

**중요:** 파이프라인 설정이 적용되려면 다음 순서를 따라야 합니다.

```python
import unreal

# 1. 파이프라인 로드 (반드시 필요!)
pipeline = unreal.load_asset(PIPELINE_PATH)

# 2. ImportAssetParameters에 파이프라인 설정
import_params = unreal.ImportAssetParameters()
import_params.set_editor_property("is_automated", True)

# 3. 파이프라인 배열 가져와서 설정 적용
pipelines = import_params.get_editor_property("pipelines")
generic_pipeline = pipelines[0]  # InterchangeGenericAssetsPipeline

# 4. 원하는 설정 적용 (예: 스켈레탈 메시용)
configure_for_skeletal_mesh(generic_pipeline, skeleton)

# 5. 임포트 실행
manager = unreal.InterchangeManager.get_interchange_manager_scripted(unreal.get_engine_subsystem(unreal.InterchangeManager))
result = manager.import_asset(source_data, import_params)
```

**주의 사항:**
- 파이프라인을 로드하지 않으면 설정이 기본값으로 유지됨
- `configure_*` 함수 호출만으로는 부족, 반드시 파이프라인 로드 후 적용해야 함

---

## 참고: 발견 경위

- **발견일:** 2026-01-26
- **문제:** 스켈레톤 임포트 시 17개 오브젝트 생성 (애니메이션, 머티리얼 등 불필요한 에셋 포함)
- **해결:** 파이프라인 설정을 통해 2개로 감소

- **발견일:** 2026-01-26
- **문제:** 애니메이션 임포트 시 `animation_pipeline.skeleton` 속성 없음 에러
- **해결:** `common_skeletal_meshes_and_animations_properties.skeleton` 사용

- **발견일:** 2026-01-27
- **문제:** 스켈레탈 메시 임포트 시 머티리얼/텍스쳐/피직스 에셋 생성됨 (설정 미적용)
- **원인:** 파이프라인 로드 없이 설정 함수만 호출
- **해결:** 파이프라인 명시적 로드 후 `configure_for_skeletal_mesh()` 호출
