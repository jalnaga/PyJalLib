# PyJalLib

[English](README.md) · [API 문서](https://jalnaga.github.io/PyJalLib/) · [PyPI](https://pypi.org/project/pyjallib/)

PyJalLib는 3D 게임 캐릭터 제작 파이프라인을 구축하기 위한 Python 라이브러리입니다. 테크니컬 아티스트와 파이프라인 개발자가 Autodesk 3ds Max에서 캐릭터 리깅을 하고, Unreal Engine 5로 에셋을 가져오고, Perforce 작업을 자동화할 수 있습니다.

## 주요 기능

- **3ds Max** — `pyjallib.max`로 캐릭터 리그를 구성하고, 스킨 웨이트를 편집하고, 모프 타깃을 분리하고, FBX 작업을 자동화합니다.
- **Unreal Engine 5** — `pyjallib.ue5`로 Interchange 또는 레거시 임포트 도구를 사용해 스켈레탈 메시와 애니메이션을 가져오고, 헤드리스 임포트를 실행합니다.
- **Perforce** — `pyjallib.perforce`로 체크아웃, 체인지리스트 관리, 워크스페이스 동기화를 처리합니다.
- **공통 유틸리티** — 이름 규칙을 적용하고 에셋 경로를 생성합니다. 3ds Max를 열지 않고 `.max` 파일을 스캔해 노드와 레이어 이름 후보를 찾을 수 있습니다.

## 설치

Python 3.10 이상이 필요합니다. PyPI에 등록된 배포판은 아래 명령으로 설치할 수 있습니다.

```bash
python -m pip install pyjallib
```

3ds Max 씬(`pymxs`)이나 Unreal Editor 에셋(`unreal`)을 다루는 도구는 해당 애플리케이션의 Python 환경에서 실행합니다. 모프 분리에는 3ds Max의 Python 환경에 NumPy 1.26 이상이 설치되어 있어야 합니다. 기본 제공되는 알파 래핑 확장은 64비트 Windows의 CPython 3.10용으로 빌드되어 있습니다.

## 예제

모프 포즈를 좌우 타깃으로 분리합니다. 3ds Max 씬에 `Neutral`이라는 뉴트럴 메시와 `Smile`이라는 포즈 메시를 준비합니다. 두 메시는 토폴로지와 버텍스 순서가 같아야 합니다.

```python
from pymxs import runtime as rt

from pyjallib.max import Morph

neutral_node = rt.getNodeByName("Neutral")
pose_node = rt.getNodeByName("Smile")
result = Morph().split_pose(neutral_node, pose_node, inAxis="X", inBandRatio=0.10)
left_node, right_node = result.leftNode, result.rightNode
```

오브젝트 공간의 델타를 분리해 `_L`과 `_R` 접미사가 붙은 타깃을 생성하고, 입력 메시와 선택 상태를 보존합니다. `inPlaneOffset`으로 대칭면을 이동할 수 있으며, `inBandHalfWidth`로 블렌딩 구간의 반폭을 직접 지정하면 비율보다 우선합니다. 이름 충돌이나 유효하지 않은 입력은 `pyjallib.max.morphSplitService.SplitError`로 보고합니다. `result.as_report()`로 실제 적용된 반폭과 최대 복원 오차를 확인할 수 있습니다. 3ds Max 외부에서 NumPy 배열을 처리하려면 `pyjallib.max.morphMath.split_pose_deltas`를 사용합니다.

## 기여하기

개발 환경 설정과 테스트 방법은 [기여 가이드(영어)](CONTRIBUTING.md)를 참고하세요. 버그를 제보하거나 변경을 제안하려면 [GitHub Issues](https://github.com/jalnaga/PyJalLib/issues)를 이용하세요.

## 라이선스

[MIT 라이선스](LICENSE).
