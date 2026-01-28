# NewAnimExporter PRD

## Title
AnimNameSelector를 대체하는 새로운 애니메이션 익스포터 개발 (UI/기능 분리 + Interchange Framework 적용)

---

## Background & Intent

### 배경
- 기존 `AnimNameSelector.py`는 UI와 기능 로직이 하나의 클래스에 혼합되어 있어 유지보수가 어려움
- 기존 코드는 `add_disabled_plugins_to_uproject()`를 사용하여 Interchange Framework를 **비활성화**한 임시 프로젝트 파일로 UE5를 실행함
- PyJalLib의 `TemplateProcessor`가 Interchange Framework 기반 API로 업데이트되어, 새 API 적용이 필요함

### 목적
1. **UI/기능 분리**: `BatchAnimExporter` 패턴을 따라 관심사를 분리하여 유지보수성 향상
2. **Interchange Framework 활성화**: 새로운 `process_interchange_animation_import_template()` API 사용
3. **기존 사용자 경험 유지**: AnimNameSelector와 동일한 워크플로우 제공

---

## Primary Manual
`.ai_context/manuals/new_module_creation.md`

---

## Scope & Prioritization

### [Must-Have] - 필수 구현 항목

#### 1. 파일 구조 생성
- `src/func_animExporter.py`: 기능 레이어 (AnimationExporterService 클래스)
- `src/ui_animExporter.py`: UI 레이어 (AnimExporterWidget 클래스)
- `src/NewAnimExporter.py`: 메인 윈도우 진입점

#### 2. UI 레이어 구현 (ui_animExporter.py)
- `AnimExporterWidget` 클래스 구현
- 기존 롤아웃 컴포넌트 재사용:
  - `RolloutBaseSkeletonNamePart`: Base Skeleton 선택
  - `RolloutNamePart`: Animation Name 선택
  - `RolloutFileStatus`: 파일 상태 표시
- 불러오기/저장 버튼 및 시그널 정의

#### 3. 기능 레이어 구현 (func_animExporter.py)
- `AnimationExporterService` 클래스 구현
- 파일 저장 메서드 마이그레이션:
  - `save_max_file()`
  - `save_bip_file()`
  - `save_anim_file()`
  - `save_json_file()`
  - `save_fbx_file()`
- **핵심**: `export_to_ue5()` Interchange 버전 구현
  - `add_disabled_plugins_to_uproject` 임포트 제거
  - 원본 프로젝트 파일 직접 사용
  - `process_interchange_animation_import_template()` API 사용
- 경로 변환 로직:
  - FBX 로컬 경로 → UE5 Content 경로 (`/Game/...`)
  - 스켈레톤 FBX 경로 → 스켈레톤 Content 경로

#### 4. 메인 윈도우 구현 (NewAnimExporter.py)
- UI와 기능 서비스 연결
- Perforce 연동 (`P4Sync`)
- 이벤트 핸들링 및 시그널/슬롯 연결

### [Should-Have] - 권장 항목 (현재 스프린트에서 제외 가능)
- UE5 스켈레톤 존재 여부 사전 검증 (`does_base_skeleton_exist_in_ue5`)
- 상세 에러 핸들링 및 사용자 피드백 메시지 개선

### [Nice-to-Have] - 부가 항목
- 프로그레스바 추가
- 저장 옵션 커스터마이징 UI

### [Non-Goal] - 명시적 제외 항목
- 배치 익스포트 기능 (BatchAnimExporter가 담당)
- 새로운 UI 디자인 (기존 AnimNameSelector UI 유지)
- Legacy 템플릿 API 지원 (`process_animation_import_template`)
- `add_disabled_plugins_to_uproject()` 사용 (반드시 제거)

---

## Technical Constraints

### Interchange Framework 필수 변경사항
1. **제거해야 할 코드:**
   ```python
   # 사용 금지
   from pyjallib.ue5 import add_disabled_plugins_to_uproject
   tempOmniProjectPath = add_disabled_plugins_to_uproject(omniProjectPath)
   ```

2. **사용해야 할 코드:**
   ```python
   # 올바른 방식
   from pyjallib.ue5 import TemplateProcessor
   projectPath = pathAndFiles.ue5.projectPath  # 원본 프로젝트 직접 사용
   templateProcessor.process_interchange_animation_import_template(...)
   ```

### 새 템플릿 API 필수 키
```python
templateData = {
    "inExtPackagePath": str,        # 외부 패키지 경로
    "inFbxPath": str,               # FBX 파일 절대 경로
    "inDestinationPath": str,       # /Game/... 형식의 Content 목적지 경로
    "inSkeletonPath": str,          # /Game/... 형식의 스켈레톤 Content 경로
    "inAssetName": str              # 선택적 (빈 문자열이면 자동 생성)
}
```

---

## Dependencies

### 외부 라이브러리
- `PySide2`: Qt UI
- `pymxs`: 3DS Max Python API

### 내부 라이브러리
- `pyjallib.ue5.TemplateProcessor`: 템플릿 처리기
- `pyjallib.max.header`: 3DS Max 헤더
- `orvlib.pathAndFiles`: 경로 설정
- `orvlib.p4Sync.P4Sync`: Perforce 연동
- `orvlib.nameToPath.NameToPath`: 이름→경로 변환
- `orvlib.max.ui.*`: 롤아웃 UI 컴포넌트

---

## Reference Files
- 대체 대상: `D:\Work\00_Scripting\20250627_AnimExporter\src\AnimNameSelector.py`
- 참고 패턴: `D:\Work\00_Scripting\20250702_BatchAnimExporter\src\` (BatchAnimExporter.py, ui_fileList.py, func_fileList.py)
- 템플릿 API: `J:\My Drive\Programming\Python\PyJalLib\src\pyjallib\ue5\templateProcessor.py`
