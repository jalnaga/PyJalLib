# Active PRD

## Title
3ds Max Dependency 관련 노드 탐색 모듈 추가

## Background & Intent
3ds Max에서 특정 오브젝트를 선택했을 때, 해당 오브젝트와 관련된 모든 의존성 노드들을 찾아내는 기능이 필요합니다. 이는 특히 FBX 익스포트 시 필요한 모든 관련 노드들(컨트롤러, 스킨, 부모 체인, 자식 노드, AddOn Helper 등)을 자동으로 선택하기 위함입니다.

## Primary Manual
`.ai_context/manuals/task_loop.md` - 구현 태스크 실행 시 참조

## Technical Decisions & References

### 적용 패턴
- **기존 모듈 패턴**: `layer.py`와 같이 `__init__` 메서드만 가지는 독립 클래스로 구현
- **Dependency Injection**: `Layer` 서비스를 주입받아 사용
- **함수 로컬 참조**: pymxs 함수들을 로컬 변수로 캐싱하여 성능 최적화

### 참고 문서
- `.ai_context/references/max/pymxs_layer.md` - pymxs 사용 패턴

## Scope & Prioritization

### Must-Have (P0 - 필수)
1. `dependent.py` 모듈 생성
2. `Dependent` 클래스 구현 (Layer 서비스 주입)
3. `get_all_dependencies(inObjArray, inVisited=None)` 메서드 구현
   - 재귀적으로 모든 dependency 노드 수집
   - controller, skin, parent chain 추적
4. `get_dependents(inObjs)` 메서드 구현
   - children과 DependentNodes 수집
5. `get_all_related_to_export(inObjs)` 메서드 구현
   - 선택된 오브젝트 기반으로 익스포트에 필요한 모든 관련 노드 반환
   - AddOn Helper 포함
   - 로그 출력 없이 결과만 선택 및 반환
6. `header.py`에 `Dependent` 클래스 등록
7. `__init__.py`에 export 추가

### Should-Have (P1 - 권장)
- 없음

### Nice-to-Have (P2 - 부가)
- 성능 테스트 및 벤치마크

### Non-Goal (Out of Scope)
- GUI/UI 구현
- 테스트 코드 작성 (3ds Max 환경 의존성으로 인해 제외)
- 기존 모듈 리팩토링
