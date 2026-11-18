#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""대칭 포즈를 좌/우 두 포즈로 나누는 순수 연산 코어.

이 모듈은 **pymxs·PySide2를 import하지 않는다.** 입력은 원시 좌표 배열이고 출력도
원시 좌표 배열이다. 그래서 경우의 수를 콘솔 pytest(Type A)에서 전수로 덮을 수 있다.
씬에서 재료를 모으는 일은 어댑터(`meshIO`)가 한다.

알고리즘 (확정 사양):

    x = N[축] - 대칭면 오프셋
    t = clamp((x + b) / (2b), 0, 1)
    w = t^2 * (3 - 2t)                  # smoothstep
    L = N + w * (P - N)
    R = N + (1 - w) * (P - N)

**우 가중치는 좌 가중치의 여수(`1 - w`)로 둔다.** 두 값을 독립으로 계산하지 않으므로
복원 항등식 `(L - N) + (R - N) = P - N`이 구현이 아니라 **정의에 의해** 성립한다.
항등식을 사후 보정으로 맞추는 설계는 밴드 폭·커브를 바꿀 때마다 다시 깨진다.

가중치는 **뉴트럴 위치**로 계산한다(포즈 위치가 아니다). 버텍스가 포즈에서 대칭면을
넘어가도 소속이 흔들리지 않아야 하고, 좌/우 두 계산이 같은 `x`를 봐야 여수 관계가
버텍스 단위로 성립한다.

이 정의에서 다음이 따라 나오며, 그대로 테스트 판정 기준이 된다.

1. 복원 항등식이 밴드 폭·축·오프셋과 무관하게 성립한다 (`w + (1-w) = 1`).
2. `x = 0`에서 `w`가 정확히 0.5다 (`b / (2b)`는 부동소수에서도 정확히 0.5).
3. 밴드 밖에서 `w`가 정확히 0 또는 1이다 (clamp가 경계를 정확히 찍는다).
4. `w(-x) = 1 - w(x)` (smoothstep이 `s(1-t) = 1 - s(t)`를 만족).
5. 대칭 입력이면 우 포즈가 좌 포즈의 정확한 미러가 된다. 그래서 **버텍스 미러쌍
   대응 맵을 만들지 않는다** - 위치 허용오차에 의존하는 취약한 단계를 도입하지 않는다.
6. smoothstep은 밴드 경계에서 도함수가 0이라 `w`가 꺾이지 않는다(C1 연속). 선형
   램프는 경계에 크리스를 남기므로 채택하지 않는다.
"""

import numpy as np

AXIS_X = "X"
AXIS_Y = "Y"
AXIS_Z = "Z"
VALID_AXES = (AXIS_X, AXIS_Y, AXIS_Z)

DEFAULT_BAND_RATIO = 0.10

_AXIS_INDEX = {AXIS_X: 0, AXIS_Y: 1, AXIS_Z: 2}


def normalize_axis(inAxis: str) -> str:
    """축 문자열을 정규화한다.

    Args:
        inAxis: 축 이름. 대소문자를 가리지 않는다.

    Returns:
        "X" / "Y" / "Z" 중 하나

    Raises:
        ValueError: 축 이름이 X/Y/Z가 아닐 때
    """
    if not isinstance(inAxis, str):
        raise ValueError(f"축은 문자열이어야 한다: {type(inAxis).__name__}")

    axis = inAxis.strip().upper()
    if axis not in VALID_AXES:
        raise ValueError(f"축은 {VALID_AXES} 중 하나여야 한다: {inAxis!r}")
    return axis


def axis_index(inAxis: str) -> int:
    """축 이름을 좌표 열 인덱스로 바꾼다.

    Args:
        inAxis: 축 이름

    Returns:
        0(X) / 1(Y) / 2(Z)
    """
    return _AXIS_INDEX[normalize_axis(inAxis)]


def as_coord_array(inCoords) -> np.ndarray:
    """좌표 입력을 `(N, 3)` float64 배열로 정규화한다.

    Args:
        inCoords: `(N, 3)`으로 해석 가능한 배열/시퀀스

    Returns:
        `(N, 3)` float64 배열

    Raises:
        ValueError: 형태가 `(N, 3)`이 아니거나 비어 있을 때
    """
    coords = np.asarray(inCoords, dtype=np.float64)
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise ValueError(f"좌표 배열은 (N, 3) 형태여야 한다: {coords.shape}")
    if coords.shape[0] == 0:
        raise ValueError("좌표 배열이 비어 있다")
    return coords


def measure_axis_extent(inCoords, inAxis: str) -> float:
    """좌표 배열의 **해당 축 방향** 폭 `W`를 재어 반환한다.

    바운딩박스의 최대 변을 쓰지 않는다. 축을 바꾸면 `W`도 그 축 폭으로 다시 계산되어야
    하며, 그렇지 않으면 축을 바꿨는데 밴드가 안 바뀌어 조용히 틀린다.

    Args:
        inCoords: `(N, 3)` 좌표 배열
        inAxis: 대칭축

    Returns:
        해당 축의 최대 − 최소
    """
    coords = as_coord_array(inCoords)
    column = coords[:, axis_index(inAxis)]
    return float(column.max() - column.min())


def resolve_band_half_width(
    inCoords, inAxis: str, inRatio: float = DEFAULT_BAND_RATIO
) -> float:
    """밴드 반폭 비율을 씬 단위 절대값으로 해석한다 (`b = ratio * W`).

    비율을 정본으로 두고 절대값을 결과로 표시한다. 절대 단위를 정본으로 박으면
    캐릭터마다, 씬 단위계마다 다시 맞춰야 한다.

    Args:
        inCoords: `(N, 3)` 뉴트럴 좌표 배열
        inAxis: 대칭축
        inRatio: 비율. 기본값 0.10.

    Returns:
        밴드 반폭 절대값 (씬 단위)

    Raises:
        ValueError: 비율이 0 이하이거나, 축 방향 폭이 0(퇴화 메쉬)일 때
    """
    ratio = float(inRatio)
    if not ratio > 0.0:
        raise ValueError(f"밴드 반폭 비율은 0보다 커야 한다: {ratio}")

    width = measure_axis_extent(inCoords, inAxis)
    if not width > 0.0:
        raise ValueError(
            f"{normalize_axis(inAxis)}축 방향 폭이 0이다(퇴화 메쉬). 밴드 반폭을 비율로 해석할 수 없다."
        )
    return ratio * width


def resolve_band_ratio(inCoords, inAxis: str, inBandHalfWidth: float) -> float:
    """밴드 반폭 절대값을 비율로 되돌린다 (`ratio = b / W`).

    UI가 비율과 절대값을 양방향으로 연동하려면 두 변환이 짝으로 있어야 한다.
    변환을 UI에 묻으면 축 선택 의존성(축을 바꾸면 `W`도 바뀐다)을 Type A로 검증할 수 없다.

    Args:
        inCoords: `(N, 3)` 뉴트럴 좌표 배열
        inAxis: 대칭축
        inBandHalfWidth: 밴드 반폭 절대값

    Returns:
        비율

    Raises:
        ValueError: 반폭이 0 이하이거나, 축 방향 폭이 0일 때
    """
    band = float(inBandHalfWidth)
    if not band > 0.0:
        raise ValueError(f"밴드 반폭은 0보다 커야 한다: {band}")

    width = measure_axis_extent(inCoords, inAxis)
    if not width > 0.0:
        raise ValueError(
            f"{normalize_axis(inAxis)}축 방향 폭이 0이다(퇴화 메쉬). 밴드 반폭을 비율로 되돌릴 수 없다."
        )
    return band / width


def compute_split_weights(
    inCoords,
    inAxis: str,
    inPlaneOffset: float,
    inBandHalfWidth: float,
) -> np.ndarray:
    """버텍스별 **좌** 가중치 `w`를 계산한다.

    우 가중치는 여기서 돌려주지 않는다. 호출부가 `1 - w`로 만든다 - 그것이 복원
    항등식이 정의에 의해 성립하는 지점이므로, 두 값을 각각 계산하는 경로를 만들지 않는다.

    Args:
        inCoords: `(N, 3)` **뉴트럴** 좌표 배열 (포즈 좌표가 아니다)
        inAxis: 대칭축
        inPlaneOffset: 대칭면 오프셋
        inBandHalfWidth: 밴드 반폭 절대값. 0보다 커야 한다.

    Returns:
        `(N,)` float64 가중치 배열. 값은 [0, 1].

    Raises:
        ValueError: 밴드 반폭이 0 이하일 때
    """
    band = float(inBandHalfWidth)
    if not band > 0.0:
        raise ValueError(f"밴드 반폭은 0보다 커야 한다: {band}")

    coords = as_coord_array(inCoords)
    x = coords[:, axis_index(inAxis)] - float(inPlaneOffset)

    t = np.clip((x + band) / (2.0 * band), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def split_pose_deltas(
    inNeutralCoords,
    inPoseCoords,
    inAxis: str = AXIS_X,
    inPlaneOffset: float = 0.0,
    inBandHalfWidth: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """합쳐진 포즈를 좌/우 두 포즈 좌표로 나눈다.

    Args:
        inNeutralCoords: `(N, 3)` 뉴트럴 좌표
        inPoseCoords: `(N, 3)` 합쳐진 포즈 좌표
        inAxis: 대칭축. 기본 "X".
        inPlaneOffset: 대칭면 오프셋. 기본 0.
        inBandHalfWidth: 밴드 반폭 절대값(씬 단위). 0보다 커야 한다.

    Returns:
        `(좌 좌표 배열, 우 좌표 배열)`. 각각 `(N, 3)` float64.

    Raises:
        ValueError: 버텍스 수가 다르거나, 밴드 반폭이 0 이하이거나, 형태가 `(N, 3)`이
            아닐 때. 모프 타겟 전제가 깨진 것이므로 부분 처리하지 않는다.
    """
    neutral = as_coord_array(inNeutralCoords)
    pose = as_coord_array(inPoseCoords)

    if neutral.shape[0] != pose.shape[0]:
        raise ValueError(
            f"뉴트럴과 포즈의 버텍스 수가 다르다: {neutral.shape[0]} vs {pose.shape[0]}. "
            "모프 타겟 전제가 깨진 것이므로 부분 처리하지 않는다."
        )

    weights = compute_split_weights(neutral, inAxis, inPlaneOffset, inBandHalfWidth)
    deltas = pose - neutral

    leftWeights = weights[:, np.newaxis]
    rightWeights = 1.0 - leftWeights

    left = neutral + leftWeights * deltas
    right = neutral + rightWeights * deltas
    return left, right
