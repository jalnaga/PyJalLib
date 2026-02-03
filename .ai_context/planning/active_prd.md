# Active PRD

## Legacy UE5 Import 기능 복원

### Background & Intent

**왜 이 기능이 필요한가?**

- **현재 문제점:** Interchange Framework의 한계로 인해 일부 임포트 시나리오에서 Legacy FBX 임포트 방식이 필요함
- **해결하고자 하는 목표:**
  - 과거 commit (e8f6776)에서 삭제된 Legacy 임포트 방식을 복원
  - 기존 Interchange Framework 기반 코드와 공존하도록 새로운 LegacyImport 코드로 재구성
  - 템플릿 프로세서가 Legacy 템플릿을 처리할 수 있도록 업데이트
- **사용자 시나리오:**
  - Interchange Framework로 처리할 수 없는 특정 FBX 임포트 요구사항 발생 시
  - Legacy FBX 임포터를 통해 스켈레톤, 스켈레탈 메시, 애니메이션 임포트 가능

**기대 효과:**
- Interchange Framework와 Legacy Import 방식을 모두 사용할 수 있는 유연성 확보
- 기존 Interchange 코드는 유지하면서 Legacy 방식 선택 가능
- 템플릿 프로세서를 통한 통합된 인터페이스 제공

### Primary Manual

`.ai_context/manuals/task_loop.md`

### Technical Decisions & References

**기술적 접근 방법:**

1. **코드 복원 방식:**
   - Git history에서 삭제된 Legacy 임포터 코드 추출 (commit e8f6776^ 이전)
   - 파일명에 "legacy" 접두사를 추가하여 Interchange 코드와 명확히 구분
   - 기존 구조를 최대한 유지하되, 현재 코드베이스와 호환되도록 필요한 부분만 수정

2. **파일 구조:**
   - **inUnreal 디렉토리:**
     - `legacyBaseImporter.py` - 기본 임포터 클래스
     - `legacyImporterSettings.py` - 임포트 설정 관리
     - `legacyAnimationImporter.py` - 애니메이션 임포터
     - `legacySkeletalMeshImporter.py` - 스켈레탈 메시 임포터
     - `legacySkeletonImporter.py` - 스켈레톤 임포터

   - **templates 디렉토리:**
     - `legacyAnimImportTemplate.py` - 단일 애니메이션 임포트 템플릿
     - `legacyBatchAnimImportTemplate.py` - 배치 애니메이션 임포트 템플릿
     - `legacySkeletalMeshImportTemplate.py` - 스켈레탈 메시 임포트 템플릿
     - `legacySkeletonImportTemplate.py` - 스켈레톤 임포트 템플릿

3. **템플릿 프로세서 업데이트:**
   - `templateProcessor.py`에 Legacy 템플릿 처리 메서드 추가
   - 기존 Interchange 템플릿 처리 메서드와 동일한 패턴 적용
   - `templates/__init__.py`에 Legacy 템플릿 상수 추가

**대안과 비교:**
- **대안 1: Interchange Framework만 사용**
  - 장점: 단일 시스템으로 코드 복잡도 감소
  - 단점: Interchange Framework의 한계로 인해 일부 시나리오 처리 불가
  - 결론: 채택하지 않음 (요구사항 충족 불가)

- **대안 2 (선택): Legacy와 Interchange 병행 사용**
  - 장점: 두 방식의 장점을 모두 활용 가능, 유연성 확보
  - 단점: 코드베이스가 복잡해질 수 있음
  - 결론: 채택 (파일명 접두사로 명확히 구분하여 복잡도 관리)

**참고 문서:**
- `.ai_context/references/ue5/path_rules.md` - UE5 경로 변환 규칙
- `.ai_context/references/ue5/interchange_pipeline.md` - Interchange Framework 참고

**로거 처리:**
- Legacy 코드는 `..logger import ue5_logger`를 사용했으나, 해당 logger.py도 삭제됨
- **Interchange Framework와 동일한 로깅 방식 사용:**
  - `unreal.log()` - 일반 정보 로그
  - `unreal.log_warning()` - 경고 로그
  - `unreal.log_error()` - 에러 로그
  - 로그 메시지에 클래스 이름 포함: `[LegacyAnimationImporter]`, `[LegacyBaseImporter]` 등
- 이 방식은 Unreal 내장 모듈만으로 실행 가능하며, 외부 의존성 없음

### Scope & Prioritization

#### [Must-Have]

**핵심 기능 (반드시 구현)**

1. **Legacy 임포터 클래스 복원 (inUnreal 디렉토리)**
   - `legacyBaseImporter.py` 생성
   - `legacyImporterSettings.py` 생성
   - `legacyAnimationImporter.py` 생성
   - `legacySkeletalMeshImporter.py` 생성
   - `legacySkeletonImporter.py` 생성
   - **성공 기준:** 모든 임포터 클래스가 생성되고, 기본 구조가 정상적으로 로드됨

2. **Legacy 템플릿 복원 (templates 디렉토리)**
   - `legacyAnimImportTemplate.py` 생성
   - `legacyBatchAnimImportTemplate.py` 생성
   - `legacySkeletalMeshImportTemplate.py` 생성
   - `legacySkeletonImportTemplate.py` 생성
   - `templates/__init__.py`에 Legacy 템플릿 상수 추가
   - **성공 기준:** 모든 템플릿 파일이 생성되고, import 경로가 legacy 임포터를 참조함

3. **템플릿 프로세서 업데이트**
   - `templateProcessor.py`에 Legacy 템플릿 처리 메서드 4개 추가:
     - `process_legacy_skeleton_import_template()`
     - `process_legacy_skeletal_mesh_import_template()`
     - `process_legacy_animation_import_template()`
     - `process_legacy_batch_anim_import_template()`
   - **성공 기준:** 각 메서드가 정상적으로 템플릿을 처리하고 출력 파일 생성

4. **inUnreal/__init__.py 업데이트**
   - Legacy 임포터 클래스를 export에 추가
   - **성공 기준:** `from pyjallib.ue5.inUnreal import LegacyAnimationImporter` 형태로 import 가능

#### [Should-Have]

**중요하지만 필수는 아닌 기능**

1. **로깅 개선**
   - Legacy 임포터에서 더 구조화된 로깅 추가
   - 왜 Should-Have인가? 기본 unreal.log()로도 동작은 하지만, 구조화된 로깅이 있으면 디버깅이 용이함

2. **에러 처리 강화**
   - 더 상세한 에러 메시지와 예외 처리
   - 왜 Should-Have인가? 기본 기능 동작에는 영향 없지만 사용성 향상에 도움

#### [Nice-to-Have]

**있으면 좋은 기능**

1. **사용 예제 또는 테스트 스크립트**
   - Legacy 임포터 사용 방법을 보여주는 예제 코드
   - 실제 UE5 환경에서 테스트 필요

2. **문서화**
   - Legacy vs Interchange 선택 가이드 문서

#### [Non-Goal]

**명시적으로 하지 않을 것**

1. **기존 Interchange 코드 수정**
   - 기존 Interchange 임포터나 템플릿을 수정하지 않음
   - 완전히 독립적인 Legacy 시스템으로 구현

2. **Legacy 코드 개선 또는 리팩토링**
   - 삭제된 원본 코드를 최대한 그대로 복원 (로거 부분 제외)
   - 새로운 기능 추가나 구조 변경 없음

3. **자동화된 단위 테스트**
   - UE5 환경에서만 동작하는 코드이므로 단위 테스트 작성 어려움
   - 실제 UE5 환경에서 수동 테스트 필요

4. **logger.py 복원**
   - 삭제된 `ue5/logger.py`는 복원하지 않음
   - Unreal 내장 로깅 함수로 대체

---

### Test Strategy

**테스트 방법:**
- User-Driven Log Test (수동 실행 필요)
  - UE5 에디터에서 실제로 템플릿 프로세서를 통해 스크립트 생성
  - 생성된 스크립트를 UE5에서 실행하여 임포트 동작 확인

**테스트 실행 명령어:**
```bash
cmd = f'"D:\root\UE5\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\root\Omni\Omni.uproject" -run=pythonscript -script="{테스트_스크립트_경로}"'
```

**테스트 데이터:**
- **FBX 파일:** `E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_GripCry_RBr-Enter-A.fbx`
- **BIP 파일:** `E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_GripCry_RBr-Enter-A.bip`
- **JSON 메타데이터:** `E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_GripCry_RBr-Enter-A.json`
- **Max 파일:** `E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_GripCry_RBr-Enter-A.max`

**테스트 시나리오:**
1. **스켈레톤 임포트 테스트**
   - 테스트 FBX: 위 애니메이션 FBX 파일 사용
   - Legacy 스켈레톤 템플릿 처리 → 스크립트 생성 → UE5에서 실행

2. **스켈레탈 메시 임포트 테스트**
   - 테스트 FBX: 위 애니메이션 FBX 파일 사용 (스켈레탈 메시 포함)
   - Legacy 스켈레탈 메시 템플릿 처리 → 스크립트 생성 → UE5에서 실행

3. **애니메이션 임포트 테스트**
   - 테스트 FBX: 위 애니메이션 FBX 파일
   - Legacy 애니메이션 템플릿 처리 → 스크립트 생성 → UE5에서 실행

4. **배치 애니메이션 임포트 테스트**
   - 테스트 FBX: 위 애니메이션 FBX 파일 (단일 파일을 리스트로)
   - Legacy 배치 애니메이션 템플릿 처리 → 스크립트 생성 → UE5에서 실행

**성공 기준:**
- [ ] 모든 Legacy 임포터 클래스가 정상적으로 import됨
- [ ] 모든 Legacy 템플릿이 정상적으로 처리됨
- [ ] templateProcessor의 Legacy 메서드가 정상적으로 스크립트를 생성함
- [ ] 생성된 스크립트가 UE5 환경에서 문법 오류 없이 실행됨
- [ ] 테스트 FBX 파일이 UE5에 정상적으로 임포트됨
