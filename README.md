# pyjallib

pyjallib Package is a Python library designed to streamline the game character development pipeline. It provides tools and utilities to assist game developers in creating, managing, and optimizing character assets.

## Features
- Character asset management
- Pipeline automation tools
- Asset optimization utilities
- Easy integration with common game engines

## Installation
```bash
pip install pyjallib
```

## Documentation
The API documentation is published at https://jalnaga.github.io/PyJalLib/.

### 모프 포즈 분리

NumPy>=1.26은 정식 의존성이며, 3ds Max 내장 Python 환경에도 설치되어 있어야 한다.
3ds Max에서는 기존 `Morph` API로 뉴트럴과 포즈의 오브젝트 공간 델타를 분리한다.

```python
from pyjallib.max import Morph

result = Morph().split_pose(neutralNode, poseNode, inAxis="X", inBandRatio=0.10)
leftNode, rightNode = result.leftNode, result.rightNode
```

`inPlaneOffset`은 대칭면 오프셋이며 `inBandHalfWidth`를 지정하면 비율보다 우선한다.
기본 출력 접미사는 `_L`·`_R`이다. 입력 노드와 선택을 보존하고, 이름 충돌이나
유효하지 않은 입력은 `pyjallib.max.morphSplitService.SplitError`로 보고한다.
`SplitResult.as_report()`는 실제 밴드 폭과 복원 편차를 반환한다.

`morphMath`, `morphSpaceTransform`, `morphValidation`, `morphNaming`,
`morphSplitService`, `morphMeshIO`는 콘솔에서 pymxs·Qt 없이 import할 수 있다.
`morphMeshIO.SceneOps`의 실제 씬 접근과 `Morph` 사용에는 3ds Max가 필요하다.
순수 연산은 `pyjallib.max.morphMath.split_pose_deltas`를 사용한다.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
