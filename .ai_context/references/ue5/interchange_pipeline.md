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

### 스켈레탈 메시 임포트 (피직스 에셋 포함)

```python
def configure_for_skeletal_mesh(generic_pipeline, with_physics: bool = True):
    """스켈레탈 메시 임포트용 설정"""
    
    # 애니메이션 비활성화
    animation_pipeline = generic_pipeline.get_editor_property("animation_pipeline")
    animation_pipeline.set_editor_property("import_animations", False)
    
    # 피직스 에셋 선택적 활성화
    mesh_pipeline = generic_pipeline.get_editor_property("mesh_pipeline")
    mesh_pipeline.set_editor_property("create_physics_asset", with_physics)
```

---

## 임포트 결과물 비교

| 설정 | 생성되는 에셋 |
|------|-------------|
| 기본값 (필터 없음) | SkeletalMesh, Skeleton, PhysicsAsset, Materials, Textures, AnimSequences |
| 스켈레톤 전용 | SkeletalMesh, Skeleton (2개) |
| 스켈레탈 메시 (피직스 포함) | SkeletalMesh, Skeleton, PhysicsAsset (3개) |

---

## 참고: 발견 경위

- **발견일:** 2026-01-26
- **문제:** 스켈레톤 임포트 시 17개 오브젝트 생성 (애니메이션, 머티리얼 등 불필요한 에셋 포함)
- **해결:** 파이프라인 설정을 통해 2개로 감소
