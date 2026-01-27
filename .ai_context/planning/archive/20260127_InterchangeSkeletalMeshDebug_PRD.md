# Active PRD

## Title
Interchange SkeletalMesh Import 실사용 테스트 및 오류 수정

---

## Background & Intent

**왜 이 작업을 하는가?**

Interchange Framework 기반의 스켈레탈 메시 임포트 기능(`interchangeSkeletalMeshImporter.py`)이 개발 완료되었으나, 실제 언리얼 엔진 환경에서의 테스트가 필요합니다. 
기존 스켈레톤 임포터(`interchangeSkeletonImporter.py`)와 애니메이션 임포터(`interchangeAnimationImporter.py`)는 성공적으로 디버깅 완료되었으므로, 동일한 패턴으로 스켈레탈 메시 임포터도 검증합니다.

**테스트 환경:**
- 스켈레탈 메시 FBX 파일: `E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BlousonPolo\Upper\SK_Sh_Human_M_BlousonPolo_Upper.fbx`
- 스켈레톤 FBX 파일: `E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx`
- 스켈레톤 Content 경로: `/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3`
- 관련 임포터: `src/pyjallib/ue5/inUnreal/interchangeSkeletalMeshImporter.py`
- 사용 템플릿: `src/pyjallib/ue5/templates/interchangeSkeletalMeshImportTemplate.py`

---

## Primary Manual
`.ai_context/manuals/test_process.md`

---

## Technical Decisions & References

### 적용할 표준 패턴
- **UE5 Path Rules:** 경로 변환 시 `pathUtils` 모듈 사용 필수 (`../references/ue5/path_rules.md`)
- **Interchange Pipeline:** 파이프라인 설정 방법 (`../references/ue5/interchange_pipeline.md`)

### 관련 코드 구조
1. **템플릿 시스템:**
   - `templates/__init__.py`: 템플릿 경로 관리
   - `templates/interchangeSkeletalMeshImportTemplate.py`: 스켈레탈 메시 임포트 템플릿
   - `templateProcessor.py`: 템플릿 처리 및 변수 치환

2. **임포터 시스템:**
   - `inUnreal/interchangeImporterBase.py`: 베이스 임포터 클래스
   - `inUnreal/interchangeSkeletalMeshImporter.py`: 스켈레탈 메시 전용 임포터
   - `inUnreal/interchangePipelineSettings.py`: 파이프라인 설정 관리
   - `inUnreal/pathUtils.py`: 경로 유틸리티

### 테스트 워크플로우 (2단계 방식)

**Step 1: 로컬에서 스크립트 생성**
```powershell
cd "J:\My Drive\Programming\Python\PyJalLib-interchange-skeletal-debug"
uv run python tests/ue5/test_skeletal_mesh_import.py
```
- `TemplateProcessor.process_interchange_skeletal_mesh_import_template()` 사용 (구현 필요 시 직접 생성)
- 출력: `tests/ue5/test_inUnreal_skeletal_mesh_import.py`

**Step 2: 언리얼 에디터에서 실행**
```python
exec(open(r"J:\My Drive\Programming\Python\PyJalLib-interchange-skeletal-debug\tests\ue5\test_inUnreal_skeletal_mesh_import.py").read())
```

### 스켈레탈 메시 임포트 시 핵심 설정

스켈레탈 메시 임포트는 **기존 스켈레톤 참조**가 필수입니다:
- `common_skeletal_meshes_and_animations_properties.skeleton` 사용
- 애니메이션/머티리얼/텍스쳐 비활성화
- 피직스 에셋 생성 비활성화 (`create_physics_asset = False`)

**예상 임포트 결과물:**
- `SkeletalMesh` 에셋 (1개만)
- 스켈레톤은 기존 에셋 참조 (새로 생성하지 않음)
- 피직스 에셋 생성하지 않음

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)
1. **테스트 스크립트 생성기 구현**
   - `tests/ue5/test_skeletal_mesh_import.py` 생성
   - `test_animation_import.py` 패턴 참고
   - 템플릿 기반으로 언리얼용 스크립트 생성

2. **언리얼 에디터용 테스트 스크립트 생성**
   - `tests/ue5/test_inUnreal_skeletal_mesh_import.py` (자동 생성됨)
   - `test_inUnreal_animation_import.py` 패턴 참고
   - `inUnreal` 디렉토리 직접 sys.path 추가 방식

3. **언리얼 에디터에서 테스트 실행**
   - 생성된 스크립트를 언리얼 Python 콘솔에서 실행
   - 오류 로그 수집 및 분석

4. **발견된 오류 수정**
   - 오류 원인 파악 및 코드 수정
   - 수정 후 재테스트

### [Should-Have] (P1 - 권장)
- 배치 임포트 기능 테스트 (여러 스켈레탈 메시 동시 임포트)

### [Nice-to-Have] (P2 - 부가)
- 테스트 결과를 문서화하여 향후 참고용으로 보관

### [Non-Goal] (Out of Scope)
- 새로운 기능 추가 (버그 수정만 진행)
- 유닛 테스트 작성 (실사용 테스트가 주 목적)
- 리팩터링 또는 구조 변경

---

## Notes
- 이 작업은 현재 브랜치(`feature/interchange-skeletal-debug`)에서 직접 수행합니다.
- 실제 언리얼 환경에서의 테스트이므로 사용자의 협력이 필요합니다.
- 기존 스켈레톤/애니메이션 임포터 디버깅 경험을 활용합니다.
