# Active Task List

## InterchangeImporter 자동 Reimport 방지

### Tasks

- [x] **Task 1:** UE5 ImportAssetParameters API 조사
  - ImportAssetParameters의 reimport 관련 속성 확인
  - reimport 자동 전환을 방지할 수 있는 파라미터 파악
  - 코드 주석에 조사 결과 기록

- [x] **Task 2:** _create_import_params 메서드 수정
  - reimport 방지를 위한 파라미터 설정 추가
  - 기존 `inReimportAsset` 파라미터 처리 로직은 유지
  - 무조건 새 임포트로 강제하도록 설정

- [x] **Task 3:** 수동 테스트 가이드 작성
  - 같은 이름의 에셋이 있을 때 테스트 시나리오 작성
  - 새 임포트가 강제되는지 확인하는 방법 문서화
