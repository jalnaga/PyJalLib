# Reference Map & Guide

개발 중 막히는 부분이 있을 때 가장 먼저 찾아봐야 할 문서들의 지도입니다.
상황에 맞는 키워드를 찾아 해당 레퍼런스 문서를 참고하세요.

---

## 🗺️ Quick Navigation

| 상황 (Context) | 핵심 키워드 | 참조 문서 (Link) |
|:---|:---|:---|
| **설계 패턴** | Facade, Singleton, Dependency Injection | `../references/patterns/facade_pattern.md` |
| **로깅 시스템** | Logger, Singleton, 로그 레벨, pyjallib | `../references/patterns/logging_pattern.md` |
| **Logger 멀티 인스턴스 격리** | loguru bind, filter, 핸들러 격리, UUID | `../references/patterns/logging_pattern.md` (멀티 인스턴스 섹션) |
| **UE5 에셋 처리** | 경로 변환, `/Game/...`, 에셋 유효성 | `../references/ue5/path_rules.md` |
| **UE5 Interchange** | 파이프라인 설정, 임포트 필터링 | `../references/ue5/interchange_pipeline.md` |
| **UE5 에셋 경로 메서드** | get_path_name, get_system_path | `../references/ue5/asset_path_methods.md` |
| **UE5 임포트 + Perforce** | 임포트 후 체인지리스트 관리, reopen, 서밋 | `../references/ue5/import_perforce_workflow.md` |
| **3ds Max 스크립트** | pymxs, MaxScript 래핑, Node 조작 | `../references/max/pymxs_layer.md` |
| **3ds Max 애니메이션** | 키프레임, animate on, attime | `../references/max/animation_context.md` |
| **버전 관리 (P4)** | Perforce, 체크아웃, 서브밋, P4Python | `../references/integrations/perforce_pattern.md` |

---

## 📚 상세 가이드

### 1. Design Patterns (공통 아키텍처)
새로운 모듈을 설계하거나 기존 구조를 리팩토링할 때 참고합니다.
- **Facade Pattern:** 복잡한 서브시스템을 단순한 인터페이스로 감쌀 때. (`src/pyjallib/max` 패키지 구조 등)
- **Logging Pattern:** Singleton 패턴으로 전역 Logger 인스턴스를 관리하는 방법. 개발 모드에 따른 로그 레벨 자동 설정. print문 교체 가이드 포함.

### 2. Unreal Engine 5 (UE5)
UE5 Python API(`unreal`)를 사용하는 작업 시 참고합니다.
- **Path Rules:** 절대 경로(Windows Path)와 게임 경로(Package Path) 간의 변환 규칙은 매우 엄격합니다. `pathUtils` 모듈 사용이 필수입니다.
- **Interchange Pipeline:** FBX 임포트 시 파이프라인 설정 방법. 스켈레톤/애니메이션/머티리얼/피직스 에셋 필터링. 애니메이션 임포트 시 `common_skeletal_meshes_and_animations_properties.skeleton` 사용 필수.
- **Asset Path Methods:** `get_path_name()` vs `get_system_path()` 차이. 에셋 레지스트리 조회 시 패키지 경로 사용 필수.

**공식 문서:**
- Python API Reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/?application_version=5.7
- Python 스크립팅 가이드: https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- Interchange Framework: https://dev.epicgames.com/documentation/en-us/unreal-engine/interchange-framework-in-unreal-engine

### 3. 3ds Max (pymxs)
3ds Max 환경에서 `pymxs`를 사용하는 작업 시 참고합니다.
- **Layer & Nodes:** 레이어 생성, 삭제, 노드 이동 등의 패턴.
- **Animation Context:** `with pymxs.animate(True):` 와 같은 컨텍스트 매니저 사용법.

### 4. Integrations (외부 도구)
- **Perforce:** P4Python을 직접 쓰지 않고 `pyjallib.perforce` 래퍼 클래스를 사용하는 표준 패턴. 연결/해제 관리(Transaction)가 핵심입니다.

---

## ➕ 문서 추가 가이드

새로운 지식이나 패턴을 발견했다면 이 폴더에 문서를 추가하고, 이 목록을 업데이트해주세요.

1. **위치:** 주제에 맞는 폴더 (`max/`, `ue5/`, `patterns/` 등) 선택
2. **파일명:** `topic_name.md` (snake_case)
3. **내용:** "Why(왜 쓰는가)", "How(어떻게 쓰는가)", "Example(예제 코드)" 포함
