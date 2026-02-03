# 3ds Max Layer Manipulation Pattern

3ds Max에서 레이어를 관리할 때 따르는 표준 패턴입니다. `pyjallib` 라이브러리 사용을 최우선으로 합니다.

---

## 핵심 원칙

1. **라이브러리 우선 (Library First):** 직접 `pymxs`를 조작하기 전에 반드시 `pyjallib.max.layer.Layer` 클래스에서 제공하는 메서드가 있는지 확인하고 이를 우선 사용합니다.
2. **패키지 캡슐화:** 레이어 관련 로직은 가능한 한 `Layer` 클래스 내부로 캡슐화하여 코드 중복을 방지합니다.
3. **Low-level 접근 제약:** 라이브러리에서 지원하지 않는 특수한 기능이나 성능 최적화가 필요한 경우에만 `pymxs` 직접 조작을 허용합니다.

---

## 🏆 Primary Pattern (`pyjallib.max.Layer` 활용)

가장 권장되는 사용 방식입니다. 대부분의 레이어 작업은 이 클래스 하나로 해결됩니다.

### 1. 초기화 및 기본 조회

```python
from pyjallib.max.layer import Layer

layer_tool = Layer()

# 레이어 유효성 확인
if layer_tool.is_valid_layer("MyLayer"):
    # 레이어 이름으로 노드 가져오기
    nodes = layer_tool.get_nodes_by_layername("MyLayer")
```

### 2. 레이어 생성 및 객체 정리

```python
# 객체 배열을 특정 레이어로 이동 (레이어 없으면 자동 생성)
objs = rt.selection
layer_tool.create_layer_from_array(objs, "Characters_Hero")

# 빈 레이어 일괄 삭제 (정리 작업)
layer_tool.del_empty_layer(showLog=True)
```

### 3. 레이어 삭제 및 계층 구조

```python
# 레이어 삭제 (내부 객체는 기본 레이어로 안전하게 이동됨)
layer_tool.delete_layer("Temp_Layer")

# 부모 레이어 설정 (계층 구조 관리)
layer_tool.set_parent_layer("Child_Layer", "Parent_Layer")
```

---

## 🛠️ Low-level Pattern (직접 조작 시)

라이브러리를 확장하거나 지원되지 않는 기능을 구현할 때만 참고합니다.

### 1. 핵심 Import 및 접근

```python
import pymxs
from pymxs import runtime as rt

# 모든 레이어 순회
for i in range(rt.LayerManager.count):
    layer = rt.LayerManager.getLayer(i)
    # ... 작업 수행 ...
```

### 2. 레이어 삭제 시 주의사항

레이어를 직접 삭제할 때는 반드시 내부 노드들을 먼저 이동시켜야 안전합니다. (그렇지 않으면 노드도 함께 유실되거나 인덱스 오류가 발생할 수 있습니다.)

```python
def delete_layer_manually(layerName):
    layer = rt.LayerManager.getLayerFromName(layerName)
    if not layer: return

    # 기본 레이어로 이동 로직 필수
    defaultLayer = rt.LayerManager.getLayer(0)
    layerNodes = rt.refs.dependents(layer) # 레이어 소속 노드 찾기
    for node in layerNodes:
        if rt.isValidNode(node):
            defaultLayer.addNode(node)
            
    rt.LayerManager.deleteLayerByName(layerName)
```

---

## 참고 문서
- `src/pyjallib/max/layer.py`: `Layer` 클래스 실제 구현부
- `.ai_context/manuals/reference_map.md`: 전체 기술 지도