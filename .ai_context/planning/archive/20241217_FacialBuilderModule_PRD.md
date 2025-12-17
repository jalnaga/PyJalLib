# PRD: Facial Builder 모듈 아키텍처 리팩토링

## Title
기존 `FacialPoseCalc.py` 함수 기반 코드를 Facade 패턴 클래스 기반 `facialBuilder` 모듈로 전환

---

## Background & Intent

### 왜 이 기능을 만드는가?

3ds Max에서 캐릭터 얼굴 애니메이션 작업을 위한 Facial Builder 모듈이 필요합니다.
현재 `FacialPoseCalc.py`에 함수들이 산발적으로 구현되어 있어 유지보수와 확장이 어렵습니다.

**목표:**
- `pyjallib.max.Header` 스타일의 Facade 패턴으로 구조화
- 관심사 분리: 데이터, 본, 포즈, 애니메이션 각각 담당 클래스로 분리
- UI 모듈에서 쉽게 호출할 수 있는 깔끔한 API 제공

### 현재 상황
- `FacialPoseCalc.py`: 함수 기반 구현 (load/save JSON, 본 관리, 포즈 관리, 트랜스폼 계산)
- `facialBuilder.json`: 기본 데이터 구조 존재 (매우 큰 파일, 실제 데이터 포함)
- pymxs 런타임을 통해 3ds Max와 통신

---

## Primary Manual

`.ai_context/manuals/new_module_creation.md`

새로운 Facade 패턴 기반 모듈을 처음부터 생성하는 작업이므로 신규 모듈 생성 매뉴얼을 따릅니다.

---

## Scope & Prioritization

### [Must-Have] - 핵심 (이번 구현)

#### 아키텍처
| ID | 기능 | 설명 |
|----|------|------|
| ARCH-01 | 패키지 구조 생성 | `src/facialBuilder/` 디렉토리 및 `__init__.py` 생성 |
| ARCH-02 | FacialBuilder 클래스 | Facade 메인 클래스 - 서브 모듈 프로퍼티로 노출 |
| ARCH-03 | 공유 상태 관리 | JSON 데이터를 FacialBuilder에서 관리, 서브 모듈들이 참조 |

#### 설정 파일 관리 (FacialData 클래스)
| ID | 기능 | 설명 |
|----|------|------|
| CFG-01 | 설정 저장 | `save_json()` - facial builder 설정을 JSON 파일로 저장 |
| CFG-02 | 설정 로드 | `load_json(path)` - 저장된 JSON 설정 파일 불러오기 |
| CFG-03 | 설정 초기화 | `reset()` - JSON 설정을 기본값으로 초기화 |
| ROOT-01 | 루트 본 설정 | `set_root_bone(name)` - JSON에 루트 본 설정 |

#### 페이셜 본 관리 (FacialBone 클래스)
| ID | 기능 | 설명 |
|----|------|------|
| BONE-01 | 페이셜 본 추가 | `add_bone(name)` - 페이셜 본을 JSON에 등록 |
| BONE-02 | 페이셜 본 제거 | `remove_bone(name)` - 등록된 페이셜 본 제거 |
| BONE-03 | 전체 초기 트랜스폼 저장 | `save_init_transforms()` - 모든 페이셜 본들의 패어런트 스페이스 트랜스폼 일괄 저장 |
| BONE-04 | 전체 초기 위치 적용 | `apply_init_transforms()` - 모든 페이셜 본들을 초기 트랜스폼으로 일괄 복원 |

#### 페이셜 포즈 관리 (FacialPose 클래스)
| ID | 기능 | 설명 |
|----|------|------|
| POSE-01 | 포즈 추가 | `add_pose(name)` - 새 포즈 생성 + 델타 트랜스폼 저장 |
| POSE-02 | 포즈 제거 | `remove_pose(name)` - 등록된 포즈 삭제 |
| POSE-03 | 포즈 업데이트 | `update_pose(name)` - 기존 포즈의 델타 트랜스폼 재저장 |
| POSE-04 | 포즈 이름 변경 | `rename_pose(old, new)` - 포즈 이름 수정 |

#### 애니메이션 (FacialAnimation 클래스)
| ID | 기능 | 설명 |
|----|------|------|
| ANIM-01 | 포즈 블렌딩 | `blend_poses(weights_dict)` - 여러 포즈를 가중치로 블렌딩하여 적용 |

---

### [Should-Have] - 중요 (1차 완료 후)

#### 포즈 그룹 관리
| ID | 기능 | 설명 |
|----|------|------|
| GRP-01 | 포즈 그룹 생성 | 새 포즈 그룹 생성 |
| GRP-02 | 그룹 이름 변경 | 포즈 그룹 이름 수정 |
| GRP-03 | 포즈 그룹 할당 | 포즈를 특정 그룹에 할당 |
| GRP-04 | 포즈 그룹 해제 | 포즈를 그룹에서 제거 |

---

### [Nice-to-Have] - 부가 (여유 시)

#### 미러링 관리
| ID | 기능 | 설명 |
|----|------|------|
| MIR-01 | 미러 포즈 페어링 | L/R 페어 연결 |
| ANIM-02 | 미러 포즈 블렌딩 | 미러링 포즈 페어를 가중치대로 블렌딩 |

---

### [Non-Goal] - 범위 제외

- UI 구현 (별도 모듈에서 처리)
- 언리얼 엔진 익스포트 기능
- 기존 `FacialPoseCalc.py` 파일 삭제 (추후 별도 작업)

---

## Technical Specifications

### 트랜스폼 계산 공식

#### 초기 패어런트 스페이스 트랜스폼 저장
```python
parentSpaceTr = bone.transform × inverse(bone.parent.transform)
```

#### 포즈 델타 트랜스폼 계산
```python
deltaTransform = currentParentSpaceTr × inverse(initParentSpaceTr)
```

#### 포즈 적용
```python
posController.value = initTransform.position + deltaTransform.position
rotController.value = initTransform.rotation + deltaTransform.rotation
```

#### 블렌딩 적용
```python
finalDelta = Σ(poseDeltas[i] × weight[i])
result = initTransform + finalDelta
```

### JSON 스키마 (v1.0)
```json
{
    "version": "1.0",
    "rootBone": "facialroot",
    "facialBones": ["bone1", "bone2"],
    "initTransforms": {
        "bone1": { "position": "...", "rotation": "..." }
    },
    "poseList": ["Neutral", "Smile_L"],
    "poseGroups": {},
    "mirrorPairs": {},
    "poseDeltas": {
        "Smile_L": {
            "bone1": { "position": "...", "rotation": "..." }
        }
    }
}
```

### 의존성
- `pymxs`: 3ds Max Python API
- `pyjallib`: 유틸리티 (`bone.sort_bones_as_hierarchy()`)

---

## Architecture

```
src/facialBuilder/
├── __init__.py           # FacialBuilder 클래스 노출
├── facialBuilder.py      # FacialBuilder 메인 클래스 (Facade)
├── data.py               # FacialData 클래스 - JSON 설정 관리
├── bone.py               # FacialBone 클래스 - 페이셜 본 관리
├── pose.py               # FacialPose 클래스 - 포즈 관리
└── animation.py          # FacialAnimation 클래스 - 애니메이션 처리
```

### 클래스 의존성
```
FacialBuilder (Facade)
├── _jsonData: dict (공유 상태)
├── configPath: str
├── data: FacialData(self)
├── bone: FacialBone(self)
├── pose: FacialPose(self)
└── animation: FacialAnimation(self)
```

---

## References

| 기능 | 참조 위치 |
|------|----------|
| 초기 패어런트 스페이스 트랜스폼 계산 | `FacialPoseCalc.py:259-298` |
| 델타 트랜스폼 적용 | `FacialPoseCalc.py:418-436` |
| 델타 트랜스폼 계산 | `FacialPoseCalc.py:337-340` |
| 포즈 델타 저장 | `FacialPoseCalc.py:369-416` |
| Facade 패턴 구현 가이드 | `.ai_context/references/facade_pattern.md` |

