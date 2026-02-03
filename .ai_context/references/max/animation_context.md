# pymxs Animation Context Managers

pymxs에서 애니메이션 키프레임을 생성할 때 사용하는 컨텍스트 매니저 패턴입니다.

---

## 핵심 개념

| 항목 | 설명 |
|:-----|:-----|
| `pymxs.animate(True)` | 애니메이션 모드 활성화 (키프레임 자동 생성) |
| `pymxs.attime(frame)` | 특정 프레임에서 값 설정 |

**주의:** `rt.animate`는 사용 불가. 반드시 `pymxs` 모듈에서 직접 import해야 함.

---

## 올바른 Import 방법

```python
import pymxs
from pymxs import runtime as rt
```

**잘못된 사용 (오류 발생):**
```python
# AttributeError: 'pymxs.runtime' object has no attribute 'animate'
rt.animate = True  # ❌ 오류
```

---

## 기본 사용법

### 단일 프레임에 키 생성

```python
import pymxs
from pymxs import runtime as rt

obj = rt.getNodeByName("MyObject")

with pymxs.animate(True):
    with pymxs.attime(0):
        obj.pos = rt.Point3(0, 0, 0)
    with pymxs.attime(100):
        obj.pos = rt.Point3(0, 10, 100)
```

### 여러 프레임에 반복 적용

```python
import pymxs
from pymxs import runtime as rt

frames = [0, 25, 50, 75, 100]
positions = [
    rt.Point3(0, 0, 0),
    rt.Point3(10, 0, 0),
    rt.Point3(10, 10, 0),
    rt.Point3(0, 10, 0),
    rt.Point3(0, 0, 0),
]

obj = rt.getNodeByName("MyObject")

with pymxs.animate(True):
    for frame, pos in zip(frames, positions):
        with pymxs.attime(frame):
            obj.pos = pos
```

---

## 컨트롤러 값 직접 설정

```python
import pymxs
from pymxs import runtime as rt

bone = rt.getNodeByName("MyBone")

# Position/Rotation 컨트롤러 가져오기
posController = rt.getPropertyController(bone.controller, "Position")
rotController = rt.getPropertyController(bone.controller, "Rotation")

with pymxs.animate(True):
    with pymxs.attime(50):
        posController.value = rt.Point3(0, 5, 0)
        rotController.value = rt.Quat(0, 0, 0.707, 0.707)
```

---

## 중첩 구조 예시

```python
import pymxs
from pymxs import runtime as rt

bones = [rt.getNodeByName(name) for name in ["Bone01", "Bone02", "Bone03"]]
frames = [0, 30, 60, 90]

with pymxs.animate(True):
    for frame in frames:
        with pymxs.attime(frame):
            for bone in bones:
                # 각 본에 대한 트랜스폼 적용
                bone.pos = rt.Point3(0, frame * 0.1, 0)
```

---

## MaxScript 동등 코드

pymxs 컨텍스트 매니저는 MaxScript의 다음 구문과 동일합니다:

```maxscript
-- MaxScript
animate on (
    at time 0 (
        $MyObject.pos = [0, 0, 0]
    )
    at time 100 (
        $MyObject.pos = [0, 10, 100]
    )
)
```

---

## 참고 사항

1. **컨텍스트 매니저 자동 복원**: `with` 블록을 벗어나면 이전 상태로 자동 복원됨
2. **중첩 가능**: `animate`와 `attime`은 중첩하여 사용 가능
3. **슬라이더 시간과 독립**: `pymxs.attime()`은 `rt.sliderTime`을 변경하지 않음

