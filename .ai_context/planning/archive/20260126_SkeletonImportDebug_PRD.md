# Active PRD

## Title
Interchange Skeleton Import 실사용 테스트 및 오류 수정

---

## Background & Intent

**왜 이 작업을 하는가?**

Interchange Framework 기반의 스켈레톤 임포트 기능이 개발 완료되었으나, 실제 언리얼 엔진 환경에서의 테스트가 필요합니다. 
실제 FBX 파일(`SK_Sh_Human_M_BaseSkeleton3.fbx`)을 사용하여 임포트 기능을 검증하고, 발견되는 오류를 수정하여 프로덕션 환경에서 안정적으로 동작하도록 합니다.

**테스트 환경:**
- 테스트 FBX 파일: `E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx`
- 사용 템플릿: `src/pyjallib/ue5/templates/interchangeSkeletonImportTemplate.py`
- 관련 임포터: `src/pyjallib/ue5/inUnreal/interchangeSkeletonImporter.py`

---

## Primary Manual
`.ai_context/manuals/test_process.md`

---

## Technical Decisions & References

### 적용할 표준 패턴
- **UE5 Path Rules:** 경로 변환 시 `pathUtils` 모듈 사용 필수 (`../references/ue5/path_rules.md`)

### 관련 코드 구조
1. **템플릿 시스템:**
   - `templates/__init__.py`: 템플릿 경로 관리
   - `templates/interchangeSkeletonImportTemplate.py`: 스켈레톤 임포트 템플릿
   - `templateProcessor.py`: 템플릿 처리 및 변수 치환

2. **임포터 시스템:**
   - `inUnreal/interchangeImporterBase.py`: 베이스 임포터 클래스
   - `inUnreal/interchangeSkeletonImporter.py`: 스켈레톤 전용 임포터
   - `inUnreal/pathUtils.py`: 경로 유틸리티

3. **경로 생성:**
   - `nameToPath.py`: FBX 파일명에서 UE5 Content 경로 자동 생성

### 테스트 워크플로우 (2단계 방식)

**Step 1: 로컬에서 스크립트 생성**
```powershell
cd "J:\My Drive\Programming\Python\PyJalLib-interchange-debug"
uv run python temp_scripts/test_skeleton_import.py
```
- `TemplateProcessor.process_interchange_skeleton_import_template()` 사용
- `NameToPath`로 UE5 Content 경로 동적 생성
- 출력: `temp_scripts/test_inUnreal_skeleton_import.py`

**Step 2: 언리얼 에디터에서 실행**
```python
exec(open(r"J:\My Drive\Programming\Python\PyJalLib-interchange-debug\temp_scripts\test_inUnreal_skeleton_import.py").read())
```

---

## Scope & Prioritization

### [Must-Have] (P0 - 필수)
1. **스켈레톤 임포트 템플릿 기반 테스트 스크립트 생성**
   - `TemplateProcessor.process_interchange_skeleton_import_template()` 사용
   - 필요한 변수: `inExtPackagePath`, `inFbxPath`, `inDestinationPath`, `inAssetName`
   - `NameToPath`로 `inDestinationPath` 동적 생성

2. **언리얼 에디터에서 테스트 실행**
   - 생성된 스크립트를 언리얼 Python 콘솔에서 실행
   - 오류 로그 수집 및 분석

3. **발견된 오류 수정**
   - 오류 원인 파악 및 코드 수정
   - 수정 후 재테스트

### [Should-Have] (P1 - 권장)
- 테스트 성공 시 다른 템플릿(SkeletalMesh, Animation)도 추가 검증

### [Nice-to-Have] (P2 - 부가)
- 테스트 결과를 문서화하여 향후 참고용으로 보관

### [Non-Goal] (Out of Scope)
- 새로운 기능 추가 (버그 수정만 진행)
- 유닛 테스트 작성 (실사용 테스트가 주 목적)
- 리팩터링 또는 구조 변경

---

## Completion Summary

**완료일:** 2026-01-26

**수정된 문제:**
1. 애니메이션/머티리얼/텍스쳐가 불필요하게 임포트되던 문제
2. 피직스 에셋이 자동 생성되던 문제
3. 스켈레톤 이름이 `SK_..._Skeleton` 형식이던 문제 → `SKEL_...` 형식으로 변경
4. `FindAssetData failed` 에러 (경로 처리 문제)

**최종 결과:**
- 임포트 오브젝트: 17개 → 2개 (SkeletalMesh + Skeleton만)
- 스켈레톤 이름: `SKEL_Sh_Human_M_BaseSkeleton3`
- 에러 없음

---

## Notes
- 이 작업은 현재 브랜치(`feature/interchange-debug`)에서 직접 수행합니다.
- 실제 언리얼 환경에서의 테스트이므로 사용자의 협력이 필요합니다.
