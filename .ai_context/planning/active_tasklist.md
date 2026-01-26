# Active Task List

## 테스트 유형: Type B - 유저 주도 테스트 (User Action + Log)

**참조:** `.ai_context/manuals/testing/user_driven_log.md`

---

## Tasks

### Phase 1: 테스트 스크립트 생성
- [x] **Task 1.1:** 스켈레톤 임포트 테스트 스크립트 생성기 작성
  - 파일: `temp_scripts/test_skeleton_import.py`
  - `TemplateProcessor.process_interchange_skeleton_import_template()` 사용
  - `NameToPath`로 UE5 Content 경로 동적 생성
  - 필요 변수: `inExtPackagePath`, `inFbxPath`, `inDestinationPath`, `inAssetName`

- [x] **Task 1.2:** 스크립트 생성기 실행
  - 명령: `uv run python temp_scripts/test_skeleton_import.py`
  - 출력: `temp_scripts/test_inUnreal_skeleton_import.py`
  - 생성된 `inDestinationPath`: `/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3`

- [x] **Task 1.3:** 템플릿 수정 (loguru 의존성 제거)
  - 문제: `pyjallib` 패키지 import 시 `loguru` 의존성 오류
  - 해결: `inUnreal` 디렉토리를 직접 `sys.path`에 추가하여 패키지 전체 로드 우회
  - 수정 파일: `src/pyjallib/ue5/templates/interchangeSkeletonImportTemplate.py`

- [x] **Task 1.4:** 파이프라인 에셋 검증 로직 추가
  - 문제: `/Interchange/Pipelines/DefaultGenericPipeline` 에셋이 없어서 임포트 0개
  - 해결: 파이프라인 에셋 존재 여부 확인 후, 없으면 기본 Interchange 설정 사용
  - 수정 파일: `src/pyjallib/ue5/inUnreal/interchangeSkeletonImporter.py`

- [x] **Task 1.5:** 기본 파이프라인 경로 수정
  - 문제: 잘못된 파이프라인 경로 사용
  - 해결: `/Interchange/Pipelines/DefaultAssetsPipeline.DefaultAssetsPipeline`로 수정
  - 수정 파일: `src/pyjallib/ue5/inUnreal/interchangePipelineSettings.py`

### Phase 2: 유저 테스트 실행
- [ ] **Task 2.1:** 언리얼 에디터에서 테스트 실행
  - 언리얼 에디터 실행
  - Output Log 창 열기 (Window > Developer Tools > Output Log)
  - 아래 명령어로 스크립트 실행:
    ```python
    exec(open(r"J:\My Drive\Programming\Python\PyJalLib-interchange-debug\temp_scripts\test_inUnreal_skeleton_import.py").read())
    ```

- [ ] **Task 2.2:** 유저 완료 응답 대기
  - 실행 결과 (성공/실패) 피드백 수신
  - 오류 메시지 또는 로그 수집

### Phase 3: 결과 분석 및 수정
- [ ] **Task 3.1:** 오류 분석
  - 언리얼 Output Log 분석
  - 에러 원인 파악

- [ ] **Task 3.2:** 코드 수정 (오류 발견 시)
  - 관련 모듈 수정
  - Task 1.2로 복귀하여 스크립트 재생성 후 재테스트

### Phase 4: 완료
- [ ] **Task 4.1:** 테스트 성공 확인
  - 스켈레톤 임포트 정상 동작 검증
  - 결과 기록

---

## 생성된 파일 정보

### 스크립트 생성기 (로컬 실행)
- **파일:** `temp_scripts/test_skeleton_import.py`
- **실행:** `uv run python temp_scripts/test_skeleton_import.py`
- **기능:** `TemplateProcessor`와 `NameToPath`를 사용해 언리얼용 스크립트 생성

### 언리얼 에디터 실행용 스크립트 (자동 생성됨)
- **파일:** `temp_scripts/test_inUnreal_skeleton_import.py`
- **실행:** 언리얼 에디터 Python 콘솔에서 `exec(open(r"...").read())`

---

## 변수 정보

| 변수명 | 값 |
|--------|-----|
| `inExtPackagePath` | `J:\My Drive\Programming\Python\PyJalLib-interchange-debug\src` |
| `inFbxPath` | `E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx` |
| `inDestinationPath` | `/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3` (NameToPath로 생성됨) |
| `inAssetName` | `SK_Sh_Human_M_BaseSkeleton3` |

### 경로 생성 로직 (NameToPath 사용)
```python
# Config 파일 경로
namingConfigPath = r"E:\DevStorage_root\DevStorage\Tools\CharNamingConfigFiles\CharModelerNamingConfig.json"
pathConfigPath = r"E:\DevStorage_root\DevStorage\Tools\CharNamingConfigFiles\CharModelerPathConfig.json"

# FBX 파일명에서 상대 경로 생성
skeletonName = Path(inFbxPath).stem  # SK_Sh_Human_M_BaseSkeleton3
nameToPath = NameToPath(namingConfigPath, pathConfigPath)
relativePath = nameToPath.generate_path(skeletonName, inIncludeRealName=True)
# 결과: Shared\Human\Male\Mesh\BaseSkeleton3

# UE5 Content 경로로 변환
ue5Path = f"/Game/Omni/Characters/{relativePath.replace('\\', '/')}"
# 결과: /Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3
```
