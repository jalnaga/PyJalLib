# Active Task List

## 구현 태스크

### Task 1: dependent.py 모듈 생성 및 기본 클래스 구조
- [x] `src/pyjallib/max/dependent.py` 파일 생성
- [x] `Dependent` 클래스 기본 구조 작성 (docstring, `__init__` with Layer 서비스 주입)

### Task 2: get_all_dependencies 메서드 구현
- [x] `get_all_dependencies(inObjArray, inVisited=None)` 메서드 구현
- [x] 재귀적 dependency 탐색 (controller, skin, parent chain)
- [x] pymxs 함수 로컬 참조를 통한 성능 최적화

### Task 3: get_dependents 메서드 구현
- [x] `get_dependents(inObjs)` 메서드 구현
- [x] children 수집 (원본 리스트 확장 방식)
- [x] DependentNodes 수집

### Task 4: get_all_related_to_export 메서드 구현
- [x] `get_all_related_to_export(inObjs)` 메서드 구현
- [x] get_dependents, get_all_dependencies 조합
- [x] AddOn Helper 레이어 탐색 및 포함
- [x] 결과 선택(rt.select) 및 반환

### Task 5: header.py에 Dependent 클래스 등록
- [x] import 문 추가
- [x] Header 클래스에 `dependent` 속성 초기화 (Layer 서비스 주입)

### Task 6: __init__.py에 export 추가
- [x] `Dependent` 클래스 export 추가

---

## 테스트 계획

### 수동 테스트 (3ds Max 환경)

> 3ds Max Python 환경 의존성으로 인해 자동화 테스트 대신 수동 테스트를 수행합니다.

#### 테스트 케이스 1: get_all_dependencies
```python
from pyjallib.max.header import get_pyjallibmaxheader
jal = get_pyjallibmaxheader()

# 테스트: 스킨이 적용된 메시 선택 후 실행
sel = list(rt.getCurrentSelection())
deps, visited = jal.dependent.get_all_dependencies(sel)
print(f"Dependencies: {len(deps)}개")
# 예상: 스킨 본들, 컨트롤러 타겟 노드들이 포함되어야 함
```

#### 테스트 케이스 2: get_dependents
```python
# 테스트: 부모 노드 선택 후 실행
sel = list(rt.getCurrentSelection())
dependents = jal.dependent.get_dependents(sel)
print(f"Dependents: {len(dependents)}개")
# 예상: 자식 노드들, DependentNodes가 포함되어야 함
```

#### 테스트 케이스 3: get_all_related_to_export
```python
# 테스트: 캐릭터 메시 선택 후 실행
sel = list(rt.getCurrentSelection())
result = jal.dependent.get_all_related_to_export(sel)
print(f"Export Related: {len(result)}개")
# 예상: 선택 변경됨, 모든 관련 노드(본, 헬퍼, AddOn 등) 포함
```

#### 검증 항목
- [x] 빈 선택에서 오류 없이 빈 결과 반환
- [x] Biped 오브젝트가 결과에서 제외되는지 확인
- [x] 순환 참조 시 무한 루프 없이 처리되는지 확인
- [x] AddOn 레이어의 Helper들이 올바르게 포함되는지 확인 (23개 레이어, 141개 Helper)
