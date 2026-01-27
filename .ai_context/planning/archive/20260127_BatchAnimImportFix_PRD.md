# Active PRD

## Title
InterchangeBatchAnimImportTemplate Import 방식 수정

---

## Background & Intent

**왜 이 작업을 하는가?**

`interchangeBatchAnimImportTemplate.py` 템플릿이 잘못된 import 방식을 사용하고 있어 언리얼 에디터에서 실행 시 동작하지 않습니다.

**현재 상태:**
- `interchangeAnimImportTemplate.py` (단일 임포트)는 정상 동작
- `interchangeBatchAnimImportTemplate.py` (배치 임포트)는 import 방식이 달라 동작하지 않음

**문제 현상:**
```python
# 현재 (잘못됨) - pyjallib 패키지 전체를 로드하려고 시도
extPackagePath = r'{inExtPackagePath}'
if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)
from pyjallib.ue5.inUnreal.interchangeAnimationImporter import InterchangeAnimationImporter
```

**재현 조건:**
- 배치 애니메이션 임포트 템플릿으로 생성된 스크립트를 언리얼 에디터에서 실행 시
- pyjallib 패키지 로드 과정에서 loguru 등 외부 의존성 에러 발생

**기대 동작:**
```python
# 올바른 방식 - inUnreal 디렉토리만 직접 추가
extPackagePath = r'{inExtPackagePath}'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'
if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)
from interchangeAnimationImporter import InterchangeAnimationImporter
```

---

## Primary Manual
`.ai_context/manuals/test_process.md`

---

## Technical Decisions & References

### 적용할 표준 패턴
- 단일 애니메이션 임포트 템플릿(`interchangeAnimImportTemplate.py`)과 동일한 import 패턴 사용
- inUnreal 디렉토리를 직접 sys.path에 추가하여 외부 의존성 없이 모듈 로드

### Async 배치 임포트 패턴
- **참조:** [InterchangeManager.scripted_import_asset_async](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeManager?application_version=5.7#unreal.InterchangeManager.scripted_import_asset_async)
- 동기 방식(`import_asset`)은 순차적으로 파일을 임포트하여 느림
- 비동기 방식(`scripted_import_asset_async`)을 사용하면 여러 파일을 병렬로 임포트 가능
- `InterchangeManager.get_interchange_manager_scripted()`로 매니저 인스턴스 획득
- `scripted_import_asset_async(content_path, source_data, import_asset_parameters)` 호출

### 테스트 워크플로우 (2단계 방식)

**Step 1: 로컬에서 스크립트 생성**
```powershell
cd "J:\My Drive\Programming\Python\PyJalLib-fix-batch-anim-template"
uv run python tests/ue5/test_batch_animation_import.py
```

**Step 2: 언리얼 에디터에서 실행**
```python
exec(open(r"J:\My Drive\Programming\Python\PyJalLib-fix-batch-anim-template\tests\ue5\test_inUnreal_batch_animation_import.py").read())
```

### 테스트 데이터
**애니메이션 FBX 파일:**
- `E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_RhStop_RBr-Enter.fbx`
- `E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Animation\Neutral\System\Equipment\A_Sh_Human_M_Neutral_System_Equipment_WriteBasic_Loop.fbx`
- `E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\Battle\Action\Fist\A_Nm_GHDtBully_M_Battle_Action_Fist_MonsterSkill_1.fbx`

**스켈레톤 FBX 파일:**
- `E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx`

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)
1. **`interchangeBatchAnimImportTemplate.py` import 방식 수정**
   - sys.path에 inUnreal 디렉토리 직접 추가
   - import 문을 `from interchangeAnimationImporter import InterchangeAnimationImporter`로 변경

2. **`InterchangeAnimationImporter.import_animations_async()` 메서드 추가**
   - `scripted_import_asset_async`를 사용한 비동기 배치 임포트 구현
   - 여러 FBX 파일을 병렬로 임포트하여 속도 향상
   - 기존 `import_animations()` 동기 메서드는 유지 (호환성)

3. **배치 애니메이션 임포트 템플릿에서 async 메서드 사용**
   - `interchangeBatchAnimImportTemplate.py`에서 `import_animations_async()` 호출

4. **배치 애니메이션 임포트 테스트 스크립트 생성**
   - `tests/ue5/test_batch_animation_import.py`: 로컬 실행용 스크립트 생성기
   - `tests/ue5/test_inUnreal_batch_animation_import.py`: 언리얼 에디터 실행용 (생성됨)

### [Should-Have] (P1 - 권장)
- 없음

### [Nice-to-Have] (P2 - 부가)
- 없음

### [Non-Goal] (Out of Scope)
- 기타 템플릿 파일 수정 (단일 임포트 템플릿 등)
- 스켈레톤/스켈레탈 메시 임포터에 async 적용

---

## Notes
- 이 작업은 현재 브랜치(`feature/fix-batch-anim-template`)에서 직접 수행합니다.
- 실제 언리얼 환경에서의 테스트이므로 사용자의 협력이 필요합니다.
