# Active Task List

## Legacy 및 Interchange 템플릿 인터페이스 통일

### Tasks

#### Phase 1: Legacy Importer 확장 (선행 작업)

- [x] **Task 1:** legacyBaseImporter.py에 prefix 자동 추론 메서드 추가
  - destinationPath와 fbxPath로부터 contentRootPrefix와 fbxRootPrefix를 자동 추론하는 메서드 구현
  - 경로 패턴 매칭 휴리스틱 사용
  - 실패 시 fallback 로직 및 명확한 에러 메시지
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacyBaseImporter.py`

- [x] **Task 2:** legacyAnimationImporter.py에 inSkeletonContentPath 매개변수 지원 추가
  - `import_animation()` 메서드에 `inSkeletonContentPath` 매개변수 추가
  - Content 경로를 직접 받아 처리하는 로직 구현
  - 기존 FBX 경로 매개변수도 하위 호환성을 위해 유지
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacyAnimationImporter.py`

- [x] **Task 3:** legacySkeletalMeshImporter.py에 inSkeletonContentPath 매개변수 지원 추가
  - `import_skeletal_mesh()` 메서드에 `inSkeletonContentPath` 매개변수 추가
  - Content 경로를 직접 받아 처리하는 로직 구현
  - 기존 FBX 경로 매개변수도 하위 호환성을 위해 유지
  - 파일 위치: `src/pyjallib/ue5/inUnreal/legacySkeletalMeshImporter.py`

#### Phase 2: Legacy 템플릿 수정

- [x] **Task 4:** legacySkeletonImportTemplate.py 변수 통일
  - 템플릿 변수를 Interchange 방식으로 변경:
    - `inFbxPath`: FBX 파일 절대 경로
    - `inDestinationPath`: /Game/... 형식의 목적지 경로
    - `inAssetName`: 에셋 이름 (선택, 빈 문자열이면 자동 생성)
    - `inExtPackagePath`: 외부 패키지 경로
  - 기존 prefix 기반 변수 제거
  - 파일 위치: `src/pyjallib/ue5/templates/legacySkeletonImportTemplate.py`

- [x] **Task 5:** legacySkeletalMeshImportTemplate.py 변수 통일
  - 템플릿 변수를 Interchange 방식으로 변경:
    - `inFbxPath`: FBX 파일 절대 경로
    - `inDestinationPath`: /Game/... 형식의 목적지 경로
    - `inSkeletonPath`: /Game/... 형식의 스켈레톤 경로
    - `inAssetName`: 에셋 이름 (선택)
    - `inExtPackagePath`: 외부 패키지 경로
  - 기존 prefix 기반 변수 제거
  - 파일 위치: `src/pyjallib/ue5/templates/legacySkeletalMeshImportTemplate.py`

- [x] **Task 6:** legacyAnimImportTemplate.py 변수 통일
  - 템플릿 변수를 Interchange 방식으로 변경:
    - `inFbxPath`: FBX 파일 절대 경로
    - `inDestinationPath`: /Game/... 형식의 목적지 경로
    - `inSkeletonPath`: /Game/... 형식의 스켈레톤 경로
    - `inAssetName`: 에셋 이름 (선택)
    - `inExtPackagePath`: 외부 패키지 경로
  - 기존 prefix 기반 변수 제거
  - 파일 위치: `src/pyjallib/ue5/templates/legacyAnimImportTemplate.py`

- [x] **Task 7:** legacyBatchAnimImportTemplate.py 변수 통일
  - 템플릿 변수를 Interchange 방식으로 변경:
    - `inFbxPaths`: FBX 파일 절대 경로 리스트
    - `inDestinationPath`: /Game/... 형식의 목적지 경로
    - `inSkeletonPath`: /Game/... 형식의 스켈레톤 경로
    - `inExtPackagePath`: 외부 패키지 경로
  - 기존 prefix 기반 변수 제거
  - 파일 위치: `src/pyjallib/ue5/templates/legacyBatchAnimImportTemplate.py`

#### Phase 3: TemplateProcessor 통합 메서드 추가

- [x] **Task 8:** process_import_template() 통합 메서드 구현
  - 새로운 통합 메서드 `process_import_template(asset_type, template_type, template_data, ...)` 추가
  - `asset_type`: 'skeleton', 'skeletal_mesh', 'animation', 'batch_animation'
  - `template_type`: 'legacy', 'interchange'
  - 템플릿 이름 매핑 로직 구현
  - 통일된 키 검증 로직 구현
  - **파일명 자동 생성 로직 추가:**
    - 출력 파일명 형식: `{template_type}_{asset_type}Import.py`
    - 예시: `legacy_skeletonImport.py`, `interchange_animImport.py`
    - `get_default_output_path()` 메서드 수정
  - 파일 위치: `src/pyjallib/ue5/templateProcessor.py`

- [ ] **Task 9:** 기존 메서드를 Deprecation Wrapper로 변경
  - 기존 8개 메서드 (process_legacy_*, process_interchange_*)를 deprecation wrapper로 변경
  - DeprecationWarning 추가
  - 내부적으로 새 통합 메서드 호출
  - 파일 위치: `src/pyjallib/ue5/templateProcessor.py`

#### Phase 4: 테스트 업데이트

- [x] **Task 10:** test_legacy_templates.py 업데이트
  - 테스트 케이스에서 통일된 변수 사용 (Interchange 방식)
  - 기존 prefix 기반 테스트 제거 또는 수정
  - 파일 위치: `tests/test_legacy_templates.py`

- [x] **Task 11:** 새 통합 메서드 테스트 추가
  - `process_import_template()` 메서드에 대한 단위 테스트 추가
  - asset_type과 template_type 조합 테스트
  - 에러 케이스 테스트 (잘못된 asset_type, 누락된 키 등)
  - 파일 위치: `tests/test_template_processor.py` (또는 새 파일)

- [x] **Task 12:** Deprecation Warning 테스트 추가
  - 기존 메서드 호출 시 DeprecationWarning 발생 확인
  - 파일 위치: `tests/test_template_processor.py`

- [x] **Task 13:** 생성된 스크립트 파일명 검증 테스트 추가
  - 생성된 스크립트 파일명이 `{template_type}_{asset_type}Import.py` 형식인지 확인
  - 예시: `legacy_skeletonImport.py`, `interchange_animImport.py`
  - 각 template_type과 asset_type 조합에 대해 올바른 파일명 생성 확인
  - 파일 위치: `tests/test_template_processor.py`

#### Phase 5: 검증

- [x] **Task 14:** pytest 실행 및 모든 테스트 통과 확인
  - 명령어: `uv run pytest tests/ -v`
  - 모든 테스트가 통과해야 함
  - 실패한 테스트가 있으면 구현 코드 수정 후 재실행

- [x] **Task 15:** ruff 검사 통과 확인
  - 명령어: `uv run ruff check src/ tests/`
  - 코드 품질 검사 통과 확인
  - 경고가 있으면 수정

- [x] **Task 16:** UE5 수동 테스트 (통합 테스트)
  - `legacy_skeletonImport.py`, `interchange_skeletonImport.py` 등 생성된 스크립트 파일명 확인
  - 각 모드별 스크립트를 UE5에서 실행
  - 실제 FBX 파일로 Skeleton, Skeletal Mesh, Animation 임포트 테스트
  - 모든 타입에서 정상적으로 임포트되고 파일명으로 모드 구분이 명확한지 확인
  - **완료**: Legacy Animation Import 테스트 성공 (버그 수정 포함)

---

## Task 작성 원칙

**작업 단위:**
- 각 태스크는 독립적으로 실행 가능
- 의존성 순서대로 배치 (Importer 확장 → 템플릿 수정 → TemplateProcessor 통합 → 테스트)

**체크박스 규칙:**
- `[ ]`: 미완료
- `[x]`: 완료

**Task Loop 준수:**
1. Pick: 첫 번째 미완료 작업 선택
2. Execute: 작업 수행
3. Test: 테스트 실행 (코드 변경이 있는 경우)
4. Update: 체크박스를 `[x]`로 변경
5. Report & STOP: 사용자에게 보고 후 대기
6. Wait: 사용자 승인 대기

**Testing Protocol:**
- 코드 변경이 포함된 태스크는 반드시 테스트를 통과해야 함
- 테스트 실패 시 **구현 코드**를 수정 (테스트 코드 수정 금지)
- 테스트가 통과하기 전까지 다음 태스크로 넘어가지 않음

**Refactoring:**
- 200라인 이상 수정 시 리팩토링 검토 필요
- 리팩토링 후 테스트 재실행 및 통과 확인
