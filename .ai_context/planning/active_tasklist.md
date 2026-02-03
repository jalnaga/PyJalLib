# Active Task List

## Legacy UE5 Import 기능 복원

### Tasks

#### Phase 1: Legacy 임포터 클래스 복원

- [x] **Task 1:** legacyImporterSettings.py 생성
  - git에서 추출한 importerSettings.py를 기반으로 legacyImporterSettings.py 생성
  - 로거를 `ue5_logger`에서 `unreal.log()`, `unreal.log_error()` 등으로 변경
  - 클래스명: `LegacyImporterSettings`
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacyImporterSettings.py`

- [x] **Task 2:** legacyBaseImporter.py 생성
  - git에서 추출한 baseImporter.py를 기반으로 legacyBaseImporter.py 생성
  - 로거를 Unreal 내장 함수로 변경 (로그 형식: `[LegacyBaseImporter] 메시지`)
  - `from .legacyImporterSettings import LegacyImporterSettings` import 수정
  - 클래스명: `LegacyBaseImporter`
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacyBaseImporter.py`

- [x] **Task 3:** legacySkeletonImporter.py 생성
  - git에서 추출한 skeletonImporter.py를 기반으로 legacySkeletonImporter.py 생성
  - 로거를 Unreal 내장 함수로 변경 (로그 형식: `[LegacySkeletonImporter] 메시지`)
  - `from .legacyBaseImporter import LegacyBaseImporter` import 수정
  - `_create_import_task` → `create_import_task` 메서드명 확인 및 수정
  - 클래스명: `LegacySkeletonImporter`
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacySkeletonImporter.py`

- [x] **Task 4:** legacySkeletalMeshImporter.py 생성
  - git에서 추출한 skeletalMeshImporter.py를 기반으로 legacySkeletalMeshImporter.py 생성
  - 로거를 Unreal 내장 함수로 변경 (로그 형식: `[LegacySkeletalMeshImporter] 메시지`)
  - `from .legacyBaseImporter import LegacyBaseImporter` import 수정
  - 클래스명: `LegacySkeletalMeshImporter`
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacySkeletalMeshImporter.py`

- [x] **Task 5:** legacyAnimationImporter.py 생성
  - git에서 추출한 animationImporter.py를 기반으로 legacyAnimationImporter.py 생성
  - 로거를 Unreal 내장 함수로 변경 (로그 형식: `[LegacyAnimationImporter] 메시지`)
  - `from .legacyBaseImporter import LegacyBaseImporter` import 수정
  - 클래스명: `LegacyAnimationImporter`
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacyAnimationImporter.py`

- [x] **Task 6:** inUnreal/__init__.py 업데이트
  - Legacy 임포터 클래스들을 import 및 __all__에 추가
  - 추가할 클래스: `LegacyBaseImporter`, `LegacyImporterSettings`, `LegacySkeletonImporter`, `LegacySkeletalMeshImporter`, `LegacyAnimationImporter`
  - 파일 위치: `src/pyjallib/ue5/inUnreal/__init__.py`

#### Phase 2: Legacy 템플릿 복원

- [x] **Task 7:** legacySkeletonImportTemplate.py 생성
  - git에서 추출한 skeletonImportTemplate.py를 기반으로 legacySkeletonImportTemplate.py 생성
  - import 경로를 Legacy 임포터로 수정: `from pyjallib.ue5.inUnreal.legacySkeletonImporter import LegacySkeletonImporter`
  - 파일 위치: `src/pyjallib/ue5/templates/legacySkeletonImportTemplate.py`

- [x] **Task 8:** legacySkeletalMeshImportTemplate.py 생성
  - git에서 추출한 skeletalMeshImportTemplate.py를 기반으로 legacySkeletalMeshImportTemplate.py 생성
  - import 경로를 Legacy 임포터로 수정: `from pyjallib.ue5.inUnreal.legacySkeletalMeshImporter import LegacySkeletalMeshImporter`
  - 파일 위치: `src/pyjallib/ue5/templates/legacySkeletalMeshImportTemplate.py`

- [x] **Task 9:** legacyAnimImportTemplate.py 생성
  - git에서 추출한 animImportTemplate.py를 기반으로 legacyAnimImportTemplate.py 생성
  - import 경로를 Legacy 임포터로 수정: `from pyjallib.ue5.inUnreal.legacyAnimationImporter import LegacyAnimationImporter`
  - 파일 위치: `src/pyjallib/ue5/templates/legacyAnimImportTemplate.py`

- [x] **Task 10:** legacyBatchAnimImportTemplate.py 생성
  - git에서 추출한 batchAnimImportTemplate.py를 기반으로 legacyBatchAnimImportTemplate.py 생성
  - import 경로를 Legacy 임포터로 수정: `from pyjallib.ue5.inUnreal.legacyAnimationImporter import LegacyAnimationImporter`
  - 파일 위치: `src/pyjallib/ue5/templates/legacyBatchAnimImportTemplate.py`

- [x] **Task 11:** templates/__init__.py 업데이트
  - Legacy 템플릿 상수 4개 추가:
    - `LEGACY_SKELETON_IMPORT_TEMPLATE`
    - `LEGACY_SKELETAL_MESH_IMPORT_TEMPLATE`
    - `LEGACY_ANIM_IMPORT_TEMPLATE`
    - `LEGACY_BATCH_ANIM_IMPORT_TEMPLATE`
  - `get_template_path()`, `get_all_template_paths()`, `get_available_templates()` 함수에 Legacy 템플릿 추가
  - 파일 위치: `src/pyjallib/ue5/templates/__init__.py`

#### Phase 3: templateProcessor.py 업데이트

- [x] **Task 12:** process_legacy_skeleton_import_template() 메서드 추가
  - `templateProcessor.py`에 Legacy 스켈레톤 템플릿 처리 메서드 추가
  - 기존 `process_interchange_skeleton_import_template()` 메서드와 동일한 패턴 적용
  - 필수 키: `inExtPackagePath`, `inContentRootPrefix`, `inFbxRootPrefix`, `inSkeletonFbxPath`
  - 파일 위치: `src/pyjallib/ue5/templateProcessor.py`

- [x] **Task 13:** process_legacy_skeletal_mesh_import_template() 메서드 추가
  - `templateProcessor.py`에 Legacy 스켈레탈 메시 템플릿 처리 메서드 추가
  - 필수 키: `inExtPackagePath`, `inContentRootPrefix`, `inFbxRootPrefix`, `inSkeletalMeshFbxPath`, `inSkeletonFbxPath`
  - 파일 위치: `src/pyjallib/ue5/templateProcessor.py`

- [x] **Task 14:** process_legacy_animation_import_template() 메서드 추가
  - `templateProcessor.py`에 Legacy 애니메이션 템플릿 처리 메서드 추가
  - 필수 키: `inExtPackagePath`, `inContentRootPrefix`, `inFbxRootPrefix`, `inAnimFbxPath`, `inSkeletonFbxPath`
  - 파일 위치: `src/pyjallib/ue5/templateProcessor.py`

- [x] **Task 15:** process_legacy_batch_anim_import_template() 메서드 추가
  - `templateProcessor.py`에 Legacy 배치 애니메이션 템플릿 처리 메서드 추가
  - 필수 키: `inExtPackagePath`, `inContentRootPrefix`, `inFbxRootPrefix`, `inAnimFbxPaths`, `inSkeletonFbxPaths`
  - 파일 위치: `src/pyjallib/ue5/templateProcessor.py`

#### Phase 4: 통합 테스트

- [x] **Task 16:** Legacy 임포터 import 테스트
  - Python 인터프리터에서 Legacy 임포터 클래스들이 정상적으로 import되는지 확인
  - 테스트 코드: `from pyjallib.ue5.inUnreal import LegacyAnimationImporter, LegacySkeletonImporter, LegacySkeletalMeshImporter`
  - 모든 클래스가 에러 없이 import되면 성공

- [x] **Task 17:** Legacy 템플릿 처리 테스트
  - 각 Legacy 템플릿에 대해 templateProcessor가 정상적으로 스크립트를 생성하는지 확인
  - 테스트 데이터로 스켈레톤, 스켈레탈 메시, 애니메이션, 배치 애니메이션 스크립트 생성
  - 생성된 스크립트가 문법 오류 없이 파이썬으로 파싱되는지 확인

---

## Task 작성 원칙

**작업 단위:**
- 각 태스크는 독립적으로 실행 가능
- 의존성 순서대로 배치 (Settings → Base → 구체적 임포터)

**체크박스 규칙:**
- `[ ]`: 미완료
- `[x]`: 완료

**Task Loop 준수:**
1. Pick: 첫 번째 미완료 작업 선택
2. Execute: 작업 수행
3. Test: 테스트 실행 (import 테스트)
4. Update: 체크박스를 `[x]`로 변경
5. Report & STOP: 사용자에게 보고 후 대기
6. Wait: 사용자 승인 대기
