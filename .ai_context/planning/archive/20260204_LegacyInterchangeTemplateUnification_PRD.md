# Legacy 및 Interchange 템플릿 인터페이스 통일

## Background & Intent

**왜 이 기능이 필요한가?**

현재 Legacy와 Interchange 임포트 방식의 템플릿이 서로 다른 입력 변수를 사용하고 있어, 사용자가 두 방식 간 전환 시 혼란이 발생하고 있습니다. 또한 templateProcessor.py에 8개의 중복 메서드가 존재하여 코드 유지보수성이 저하되고 있습니다.

**해결하고자 하는 목표:**
- Legacy와 Interchange 템플릿이 동일한 입력 변수 키를 사용하도록 통일
- templateProcessor.py의 중복 메서드를 단일 통합 메서드로 리팩토링
- 두 방식의 템플릿 처리 로직을 통합하여 코드 중복 제거

**사용자 시나리오:**
- 외부 툴에서 Legacy/Interchange 방식 선택 시 동일한 변수 형식으로 호출 가능
- templateProcessor 사용자가 단일 메서드로 모든 임포트 타입 처리 가능

**기대 효과:**
- 인터페이스 통일로 사용자 혼란 감소
- 코드 중복 제거로 유지보수성 향상
- 두 방식 간 전환이 쉬워져 사용자 경험 개선

## Primary Manual

`.ai_context/manuals/task_loop.md`

## Technical Decisions & References

**기술적 접근 방법:**

1. **변수 통일 방식: Interchange 방식 채택**
   - 이유: Interchange 방식이 더 직접적이고 명확함 (직접 경로 지정)
   - Legacy는 prefix 기반 변환이 필요하므로 복잡함
   - 통일된 변수:
     - `inFbxPath`: FBX 파일 절대 경로
     - `inDestinationPath`: /Game/... 형식의 목적지 경로
     - `inSkeletonPath`: /Game/... 형식의 스켈레톤 경로
     - `inAssetName`: 에셋 이름 (선택, 빈 문자열이면 자동 생성)
     - `inExtPackagePath`: 외부 패키지 경로

2. **Legacy Importer 확장 전략:**
   - Legacy importer는 여전히 `contentRootPrefix`/`fbxRootPrefix` 기반으로 작동
   - 템플릿 내부에서 또는 importer 내부에서 prefix 자동 추론
   - `import_animation()` 등 메서드에 `inSkeletonContentPath` 매개변수 추가
   - 하위 호환성 유지: 기존 FBX 경로 매개변수도 지원

3. **TemplateProcessor 통합:**
   - 새로운 `process_import_template(asset_type, template_type, ...)` 메서드 추가
   - 기존 8개 메서드는 deprecation wrapper로 유지 (하위 호환성)
   - 템플릿 이름 매핑을 통한 동적 템플릿 선택

4. **파일명으로 모드 구분:**
   - 이유: UE5에서 실행되는 스크립트가 Legacy인지 Interchange인지 불명확
   - 해결책: 파일명 자체로 모드 구분
     - 파일명 형식: `{template_type}_{asset_type}Import.py`
     - 예시: `legacy_skeletonImport.py`, `interchange_animImport.py`
     - TemplateProcessor가 출력 경로 생성 시 자동으로 이 형식 적용
   - 장점:
     - 파일명만 봐도 즉시 모드 식별 가능
     - 외부 툴이 필요한 스크립트를 파일명으로 쉽게 선택
     - 스크립트 내부 수정 불필요 (템플릿 원본 유지)
     - 디스크 상에서 명확한 구분

**대안 검토:**

| 대안 | 장점 | 단점 | 결정 |
|------|------|------|------|
| **Option A: Interchange 방식으로 통일** | 더 직접적, 명확한 인터페이스 | Legacy importer 수정 필요 | ✅ 채택 |
| Option B: Legacy 방식으로 통일 | Legacy importer 수정 불필요 | prefix 개념이 복잡하고 직관적이지 않음 | ❌ |
| Option C: 새로운 공통 변수 세트 | 중립적 | 양쪽 모두 수정 필요, 복잡도 증가 | ❌ |

**참고 문서:**
- 없음 (신규 리팩토링 작업)

## Scope & Prioritization

### [Must-Have]

**핵심 기능 (반드시 구현)**

1. **Legacy Importer 확장**
   - `legacyBaseImporter.py`: prefix 자동 추론 메서드 추가
   - `legacyAnimationImporter.py`: `inSkeletonContentPath` 매개변수 지원
   - `legacySkeletalMeshImporter.py`: `inSkeletonContentPath` 매개변수 지원
   - **성공 기준:** Content 경로를 직접 받아 임포트 가능

2. **Legacy 템플릿 수정**
   - 4개 템플릿 파일 변수를 Interchange 방식으로 변경
   - `legacySkeletonImportTemplate.py`
   - `legacySkeletalMeshImportTemplate.py`
   - `legacyAnimImportTemplate.py`
   - `legacyBatchAnimImportTemplate.py`
   - **성공 기준:** 템플릿이 Interchange와 동일한 변수 키 사용

3. **TemplateProcessor 통합 메서드 추가 및 파일명 자동 생성**
   - `process_import_template(asset_type, template_type, template_data, ...)` 구현
   - 템플릿 이름 매핑 로직
   - 통일된 키 검증 로직
   - 출력 파일명 자동 생성: `{template_type}_{asset_type}Import.py` 형식
   - **성공 기준:** 단일 메서드로 모든 템플릿 처리 가능하며, 파일명으로 모드 구분 가능

4. **테스트 업데이트**
   - `test_legacy_templates.py`: 통일된 변수 사용
   - 새 통합 메서드 테스트 추가
   - **성공 기준:** 모든 테스트 통과

### [Should-Have]

**중요하지만 필수는 아닌 기능**

1. **Deprecation Wrapper 유지**
   - 기존 8개 메서드를 deprecation warning과 함께 유지
   - 왜 Should-Have인가? 하위 호환성이 중요하지만, 완전히 제거해도 기능은 동작함

2. **상세한 에러 메시지**
   - prefix 자동 추론 실패 시 명확한 에러 메시지
   - 왜 Should-Have인가? 기본 동작에는 영향 없지만 디버깅 용이성 향상

### [Nice-to-Have]

**있으면 좋은 기능**

1. **마이그레이션 가이드 문서**
   - 기존 사용자를 위한 변경 사항 문서
   - 예제 코드

2. **성능 비교 테스트**
   - Legacy vs Interchange 처리 시간 측정

### [Non-Goal]

**명시적으로 하지 않을 것**

1. **Interchange 템플릿 수정**
   - Interchange 템플릿은 이미 올바른 형식이므로 수정하지 않음

2. **Legacy Importer 완전 재작성**
   - 기존 동작 방식은 유지하고, 새로운 인터페이스만 추가
   - 내부 로직은 변경하지 않음

3. **자동화된 마이그레이션 도구**
   - 기존 코드 자동 변환 도구는 제공하지 않음

4. **기존 메서드 완전 제거**
   - Deprecation wrapper는 유지하여 점진적 마이그레이션 지원

---

## Test Strategy

**테스트 방법:**

1. **단위 테스트**
   ```bash
   uv run pytest tests/test_legacy_templates.py -v
   ```
   - 통일된 변수로 템플릿 생성 확인
   - 새 통합 메서드 동작 확인
   - Deprecation warning 발생 확인

2. **통합 테스트 (UE5 환경)**
   - 생성된 스크립트를 UE5에서 실행
   - 실제 FBX 임포트 동작 검증

**검증 항목:**
- [ ] Legacy 템플릿이 Interchange 변수 사용
- [ ] 새 통합 메서드가 정상 동작
- [ ] Legacy importer가 Content 경로 직접 수신 가능
- [ ] 모든 단위 테스트 통과
- [ ] UE5에서 실제 임포트 성공

---

## Implementation Notes

### 구현 순서 (Must-Have 항목 순서)

1. **Step 1: Legacy Importer 확장** (선행 작업)
2. **Step 2: Legacy 템플릿 수정**
3. **Step 3: TemplateProcessor 통합 메서드 추가** (파일명 자동 생성 포함)
4. **Step 4: 테스트 업데이트**
5. **Step 5: 검증** (pytest + ruff + UE5 수동 테스트)

### 주요 파일 목록

**수정 필요:**
1. `src/pyjallib/ue5/inUnreal/legacyBaseImporter.py` - prefix 자동 추론
2. `src/pyjallib/ue5/inUnreal/legacyAnimationImporter.py` - Content 경로 지원
3. `src/pyjallib/ue5/inUnreal/legacySkeletalMeshImporter.py` - Content 경로 지원
4. `src/pyjallib/ue5/templates/legacySkeletonImportTemplate.py` - 변수 통일
5. `src/pyjallib/ue5/templates/legacySkeletalMeshImportTemplate.py` - 변수 통일
6. `src/pyjallib/ue5/templates/legacyAnimImportTemplate.py` - 변수 통일
7. `src/pyjallib/ue5/templates/legacyBatchAnimImportTemplate.py` - 변수 통일
8. `src/pyjallib/ue5/templateProcessor.py` - 통합 메서드 추가 및 파일명 자동 생성 로직
9. `tests/test_legacy_templates.py` - 테스트 업데이트

### 기술적 난제 및 해결책

**문제 1: prefix 자동 추론의 정확도**
- 증상: destinationPath와 fbxPath만으로 정확한 prefix 추론이 어려울 수 있음
- 해결책: 경로 패턴 매칭 휴리스틱 사용, 실패 시 fallback 로직

**문제 2: 스켈레톤 경로 불일치**
- 증상: Legacy는 FBX 경로, Interchange는 Content 경로 사용
- 해결책: Legacy importer에 `inSkeletonContentPath` 매개변수 추가

**문제 3: 하위 호환성**
- 증상: 기존 사용자 코드 깨짐 가능성
- 해결책: 기존 메서드를 deprecation wrapper로 유지
