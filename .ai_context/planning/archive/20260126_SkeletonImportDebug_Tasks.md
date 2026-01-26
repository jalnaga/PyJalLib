# Task List - Skeleton Import Debug

## 테스트 유형: Type B - 유저 주도 테스트 (User Action + Log)

**완료일:** 2026-01-26

---

## Tasks

### Phase 1: 테스트 스크립트 생성
- [x] **Task 1.1:** 스켈레톤 임포트 테스트 스크립트 생성기 작성
- [x] **Task 1.2:** 스크립트 생성기 실행
- [x] **Task 1.3:** 템플릿 수정 (loguru 의존성 제거)
- [x] **Task 1.4:** 파이프라인 에셋 검증 로직 추가
- [x] **Task 1.5:** 기본 파이프라인 경로 수정

### Phase 2: 유저 테스트 실행
- [x] **Task 2.1:** 언리얼 에디터에서 테스트 실행
- [x] **Task 2.2:** 유저 완료 응답 대기

### Phase 3: 결과 분석 및 수정
- [x] **Task 3.1:** 오류 분석
  - 문제 1: 애니메이션/머티리얼/텍스쳐가 함께 임포트됨
  - 문제 2: 피직스 에셋이 생성됨
  - 문제 3: 스켈레톤 이름이 SK_..._Skeleton 형식
  - 문제 4: FindAssetData failed 에러

- [x] **Task 3.2:** 코드 수정
  - `interchangePipelineSettings.py`: 파이프라인 설정 적용
  - `interchangeSkeletonImporter.py`: SK_ → SKEL_ 변환
  - `get_system_path()` → `get_path_name()` 변경

### Phase 4: 완료
- [x] **Task 4.1:** 테스트 성공 확인

---

## 최종 수정 파일 목록

1. `src/pyjallib/ue5/inUnreal/interchangePipelineSettings.py`
   - 파이프라인 설정 단순화
   - `configure_for_skeleton()` 메서드 추가
   - 피직스 에셋 비활성화 옵션 추가

2. `src/pyjallib/ue5/inUnreal/interchangeSkeletonImporter.py`
   - 스켈레톤 이름 변환 로직 (SK_ → SKEL_)
   - `get_path_name()` 사용으로 에러 해결

3. `src/pyjallib/ue5/templates/interchangeSkeletonImportTemplate.py`
   - loguru 의존성 제거

---

## 테스트 결과 비교

| 항목 | 초기 상태 | 최종 상태 |
|------|----------|----------|
| 임포트 오브젝트 수 | 17개 | **2개** |
| 애니메이션 | 임포트됨 | **비활성화** |
| 머티리얼 | 임포트됨 | **비활성화** |
| 텍스쳐 | 임포트됨 | **비활성화** |
| 피직스 에셋 | 생성됨 | **비활성화** |
| 스켈레톤 이름 | SK_..._Skeleton | **SKEL_...** |
| 에러 | FindAssetData failed | **없음** |
