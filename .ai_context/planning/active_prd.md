# Active PRD

## InterchangeImporter 자동 Reimport 방지

### Background & Intent

현재 `InterchangeImporterBase`를 사용하여 에셋을 임포트할 때, 동일한 이름의 에셋이 이미 존재하면 UE5가 자동으로 reimport로 전환하는 문제가 발생합니다. 이는 의도하지 않은 동작이며, 사용자는 기존 에셋이 있더라도 **무조건 새로운 임포트를 강제**하고 싶어합니다.

**문제 현상:**
- 같은 이름의 에셋이 존재할 때 자동으로 reimport 모드로 전환됨
- 새 임포트를 원하지만 UE5가 자동으로 리임포트로 판단함

**기대 동작:**
- 기존 에셋 존재 여부와 관계없이 항상 새로운 임포트로 처리
- 임포트 파라미터에서 reimport 자동 전환을 방지

### Primary Manual

`.ai_context/manuals/test_process.md`

### Technical Decisions & References

**문제 원인 분석:**
- `_create_import_params` 메서드에서 `inReimportAsset` 파라미터를 받고 있음
- UE5 InterchangeManager가 기존 에셋을 감지하면 자동으로 reimport로 전환하는 것으로 추정

**해결 방안:**
1. ImportAssetParameters에 reimport 방지 옵션 설정
2. `is_automated=True` 외에 추가 파라미터 확인 필요
3. UE5 Interchange Framework의 reimport 자동 전환 메커니즘 조사

**참고 파일:**
- `src/pyjallib/ue5/inUnreal/interchangeImporterBase.py`

### Scope & Prioritization

#### [Must-Have]

1. **임포트 파라미터에 reimport 방지 설정 추가**
   - ImportAssetParameters에서 reimport 자동 전환을 방지하는 플래그 설정
   - UE5 API 문서 조사하여 적절한 파라미터 확인

2. **_create_import_params 메서드 수정**
   - reimport를 무조건 방지하도록 파라미터 설정
   - 기존 `inReimportAsset` 파라미터는 유지하되, 새로운 옵션 추가

#### [Should-Have]

1. **간단한 테스트로 동작 확인**
   - 같은 이름의 에셋이 있을 때 새 임포트가 강제되는지 확인
   - 수동 테스트로 검증 가능

#### [Nice-to-Have]

- 없음

#### [Non-Goal]

1. **다른 임포트 로직 수정**: 임포트 파라미터 외의 로직은 수정하지 않음
2. **리팩터링**: 코드 구조 변경 없이 파라미터만 수정
3. **자동화 테스트 추가**: 단순 파라미터 설정 변경이므로 수동 테스트로 충분

---

### 수동 테스트 가이드

#### 테스트 목적

`replace_existing=True` 설정이 올바르게 동작하여 같은 이름의 에셋이 있어도 새 임포트로 강제되는지 검증합니다.

#### 테스트 시나리오

**시나리오 1: 기존 에셋이 존재하는 경우**

1. **사전 조건:**
   - UE5 프로젝트에 `/Game/Test/TestAsset` 경로에 에셋이 이미 존재
   - 동일한 이름의 소스 파일(예: FBX)을 다른 내용으로 준비

2. **실행:**
   - `InterchangeImporterBase`를 사용하여 동일한 경로(`/Game/Test/`)에 동일한 이름(`TestAsset`)으로 임포트 실행
   - 임포트 파라미터는 `_create_import_params()` 메서드로 생성 (기본값 사용)

3. **기대 결과:**
   - 로그에 `replace_existing=True: 기존 에셋이 있어도 새 임포트로 강제` 메시지 출력
   - 기존 에셋이 새로운 내용으로 **덮어쓰기**됨
   - Reimport 모드가 아닌 **새 임포트 모드**로 동작
   - 에셋의 타임스탬프 및 메타데이터가 갱신됨

4. **검증 방법:**
   - UE5 Output Log에서 `[InterchangeImporterBase] replace_existing=True` 로그 확인
   - Content Browser에서 에셋의 수정 날짜/시간 확인
   - 에셋을 열어서 내용이 새 파일의 내용으로 변경되었는지 확인

**시나리오 2: 기존 에셋이 없는 경우**

1. **사전 조건:**
   - UE5 프로젝트에 `/Game/Test/NewAsset` 경로에 에셋이 존재하지 않음
   - 소스 파일(예: FBX) 준비

2. **실행:**
   - `InterchangeImporterBase`를 사용하여 `/Game/Test/` 경로에 `NewAsset` 이름으로 임포트 실행

3. **기대 결과:**
   - 로그에 `replace_existing=True` 메시지 출력
   - 새 에셋이 정상적으로 생성됨
   - 에러나 경고 없이 임포트 완료

4. **검증 방법:**
   - Content Browser에서 새 에셋 생성 확인
   - 에셋을 열어서 내용이 올바르게 임포트되었는지 확인

#### 주요 체크포인트

- [ ] Output Log에 `replace_existing=True` 메시지가 출력되는가?
- [ ] 같은 이름의 에셋이 있을 때 reimport가 아닌 새 임포트로 동작하는가?
- [ ] 기존 에셋이 새로운 내용으로 덮어쓰기되는가?
- [ ] 기존 에셋이 없을 때도 정상적으로 임포트되는가?

#### 주의사항

- **백업 필수:** 테스트 전에 기존 에셋을 백업하거나 테스트 전용 에셋 사용
- **로그 확인:** UE5 Output Log 레벨을 `Log` 이상으로 설정하여 모든 로그 메시지 확인
- **재현성:** 같은 소스 파일로 여러 번 반복 테스트하여 일관된 동작 확인
