#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""오브젝트 공간 ↔ 월드 공간 변환 (pymxs 무의존 순수 모듈).

**왜 이 모듈이 필요한가 (Phase 0 실측 근거):**

3ds Max의 버텍스 접근자는 공간이 갈린다.

| 접근 | 공간 |
|:---|:---|
| `getVert(node.mesh, i)` | **오브젝트** |
| `polyop.getVert(node, i)` / `meshop.getVert(node, i)` / `getVert(node, i)` | **월드** |
| `snapshotAsMesh(node)` + `getVert` | **월드** |
| `setVert(node, i, p)` | **월드 입력** |

읽기는 오브젝트 공간으로 할 수 있지만 **쓰기는 월드 입력만 측정되었다.** 그래서
연산은 오브젝트 공간에서 하고, 노드에 기록하는 마지막 한 걸음에서만 월드로 바꾼다.

**왜 오브젝트 공간에서 연산하는가.** Morpher는 노드 트랜스폼을 무시하고 타겟의
오브젝트 좌표만 본다 - 그래서 리거가 모프 타겟을 씬 어디에 옮겨 놔도 모프가 정상
동작한다. 월드 공간으로 계산하면 타겟을 옆으로 치워 둔 씬에서 델타에 그 이동량이
섞여 들어가 결과가 통째로 틀린다. 오브젝트 공간은 그 사고에 면역이고, 계산 결과가
Morpher의 의미와 정확히 일치한다.

**현재 프로덕션 경로가 쓰는 것은 `object_to_world` 하나다.** 읽기는 `node.mesh`에서
오브젝트 좌표를 직접 얻으므로 역변환이 필요 없다. `world_to_object`는 그 짝으로
남겨 둔다 - 월드를 주는 접근자(`snapshotAsMesh`, `polyop.getVert`)를 쓰는 경로가
생기면 그때 필요하고, 지금도 왕복 일치가 변환 규약의 근거를 테스트로 못박는다.

MAXScript `matrix3`의 좌표 변환 규약은 **행 벡터 우측 곱**이다.

    p_world = p_object * M = p_object @ basis + origin

`basis`는 `row1..row3`을 행으로 쌓은 3x3, `origin`은 `row4`다.
(Phase 0 섹션 B에서 수치로 확인: 회전 30도 + 이동 노드에서
`getVert(node.mesh,1) * transform == meshop.getVert(node,1)`.)
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Transform:
    """노드 트랜스폼을 basis(3x3) + origin(3,)으로 담는다.

    Attributes:
        basis: `matrix3`의 row1~row3을 행으로 쌓은 3x3 배열
        origin: `matrix3`의 row4 (이동 성분)
    """

    basis: np.ndarray
    origin: np.ndarray

    def is_identity(self, inTol: float = 0.0) -> bool:
        """항등 트랜스폼인지 판정한다.

        Args:
            inTol: 허용 오차. 0이면 완전 등호.

        Returns:
            basis가 단위행렬이고 origin이 0이면 True
        """
        if inTol <= 0.0:
            return bool(
                np.array_equal(self.basis, np.eye(3))
                and np.array_equal(self.origin, np.zeros(3))
            )
        return bool(
            np.allclose(self.basis, np.eye(3), rtol=0.0, atol=inTol)
            and np.allclose(self.origin, np.zeros(3), rtol=0.0, atol=inTol)
        )


IDENTITY_TRANSFORM = Transform(basis=np.eye(3), origin=np.zeros(3))


def make_transform(inRow1, inRow2, inRow3, inRow4) -> Transform:
    """`matrix3`의 네 행으로 Transform을 만든다.

    Args:
        inRow1: row1 (X 기저)
        inRow2: row2 (Y 기저)
        inRow3: row3 (Z 기저)
        inRow4: row4 (이동)

    Returns:
        Transform 인스턴스

    Raises:
        ValueError: 행 하나라도 길이 3이 아닐 때
    """
    rows = [
        np.asarray(r, dtype=np.float64).reshape(-1)
        for r in (inRow1, inRow2, inRow3, inRow4)
    ]
    for i, r in enumerate(rows):
        if r.shape != (3,):
            raise ValueError(f"matrix3 row{i + 1}은 길이 3이어야 한다: {r.shape}")

    return Transform(basis=np.stack(rows[:3], axis=0), origin=rows[3])


def object_to_world(inObjectCoords, inTransform: Transform) -> np.ndarray:
    """오브젝트 공간 좌표를 월드 공간으로 바꾼다 (`p @ basis + origin`).

    항등 트랜스폼에서는 부동소수 오차 없이 입력과 같은 값이 나온다
    (단위행렬 곱과 0 덧셈은 정확하다).

    Args:
        inObjectCoords: `(N, 3)` 오브젝트 공간 좌표
        inTransform: 노드 트랜스폼

    Returns:
        `(N, 3)` 월드 공간 좌표
    """
    coords = _as_coords(inObjectCoords)
    return coords @ inTransform.basis + inTransform.origin


def world_to_object(inWorldCoords, inTransform: Transform) -> np.ndarray:
    """월드 공간 좌표를 오브젝트 공간으로 바꾼다 (`(p - origin) @ inv(basis)`).

    Args:
        inWorldCoords: `(N, 3)` 월드 공간 좌표
        inTransform: 노드 트랜스폼

    Returns:
        `(N, 3)` 오브젝트 공간 좌표

    Raises:
        ValueError: basis가 특이행렬일 때(스케일 0인 축이 있는 노드)
    """
    coords = _as_coords(inWorldCoords)
    try:
        inverseBasis = np.linalg.inv(inTransform.basis)
    except np.linalg.LinAlgError as e:
        raise ValueError(
            f"노드 트랜스폼의 basis가 특이행렬이라 역변환할 수 없다(스케일 0인 축): {e}"
        ) from e
    return (coords - inTransform.origin) @ inverseBasis


def _as_coords(inCoords) -> np.ndarray:
    """좌표 입력을 `(N, 3)` float64 배열로 정규화한다."""
    coords = np.asarray(inCoords, dtype=np.float64)
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise ValueError(f"좌표 배열은 (N, 3) 형태여야 한다: {coords.shape}")
    return coords
