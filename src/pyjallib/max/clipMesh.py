#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""클립 메쉬 순수 연산 모듈 - 덮는 메쉬로 "그 아래를 지우는" 닫힌 부피를 만든다. pymxs·외부 패키지 비의존(stdlib만).

**pymxs를 import하지 않는다.** 부피 정의·이산화·검증을 씬 밖에 두어 콘솔(Type A)에서 경우의 수를 고정한다
(``polygonMath``·``uvMask``와 같은 분리). 어댑터(``Polygon.build_clip_mesh``)는 씬에서 월드 삼각형을 모으고, 결과
메쉬를 노드로 만들고, 감축한 뒤 다시 이 모듈로 검증한다. numpy도 쓰지 않는다 - 추가 패키지를 설치할 수 없는 DCC
내장 Python에서 실행된다.

## 소비처 - 부피 클립 (Unreal Mutable ``Clip Mesh With Mesh``)

엔진은 닫힌 클립 메쉬를 받아 **그 부피 안에 든 베이스 메쉬 버텍스의 면을 지운다.** 안팎은 버텍스마다 +Z 방향 레이
하나의 교차 수 홀짝으로 정하고, 닫힘은 "위치가 같은 버텍스를 합친 뒤 모든 엣지가 정확히 면 2개"로 검사한다(닫히지
않아도 경고만 남기고 진행한다). 그래서 이 모듈은 **합집합 하나의 겉면**만 만들고, 결과를 같은 규칙으로 다시 판정한다.
포팅 원본: ``Engine/Plugins/Mutable/Source/MutableRuntime/Private/MuR/OpMeshClipWithMesh.cpp``(UE 5.7.4).

## 부피의 정의 - 푸쉬한 덮는 면을 덮히는 면까지 쓸어내린 기둥의 합집합

1. 덮는 메쉬 버텍스 g마다 덮히는 표면의 최근접점 p와 부드러운 노멀 n, 높이 h = (g - p) . n을 구한다.
2. 푸쉬: g' = g + d * n.
3. 덮는 면: 세 버텍스가 모두 투영되고(최근접 거리 <= Hmax) h + d > 0. h + d <= 0이면 덮히는 쪽이 덮는 쪽을 뚫고
   나온 자리(관통)라 부피를 만들지 않는다 - 그 아래는 지워지지 않는다.
4. 경계 물림: 덮는 메쉬의 열린 엣지 + 덮는 면/안 덮는 면 사이 엣지의 버텍스에서 거리 m 이내 버텍스를 가진 덮는 면은 뺀다.
5. 남은 덮는 면마다 위 g'_i, 아래 p_i - T * n_i인 삼각 기둥. 비틀린 옆면은 **전역 버텍스 번호가 작은 꼭짓점의 위 점에서**
   대각선을 그어 사면체 3개로 나눈다 - 이웃 기둥이 같은 대각선을 공유해 틈·겹침이 생기지 않는다.
6. 부피 = 기둥 합집합. **기대 클립 집합 E** = 그 안에 든 덮히는 메쉬 버텍스.

덮히는 버텍스는 h = 0에 있으므로 위로 d 이상(옷이 붙은 곳 기준), 아래로 T의 여유를 갖는다 - 이산화·감축 오차를 이
여유가 흡수한다.

## 이산화 - 복셀 합집합의 겉면 (구성상 닫힌 2-다양체)

복셀 중심이 부피 안이면 점유 -> 바깥 flood fill로 닿지 않은 빈 칸(내부 공동)을 점유로 -> 2x2x2 블록마다 점유 칸과
빈 칸이 각각 면 이웃으로 하나로 이어지게 빈 칸을 채운다(엣지·꼭짓점만 맞닿는 배치 제거) -> 보정이 막아 새로 생긴
공동을 다시 메운다(``close_grid``) -> 점유/비점유 경계의 정육면체 면을 버텍스 공유 메쉬로 뽑는다.

## 데이터 표현

- **인덱스는 0-based**다. 1-based 변환은 어댑터 경계에서 한다.
- 위치·노멀은 ``(x, y, z)`` 튜플(월드 공간, 씬 단위 cm), 삼각형은 ``(a, b, c)`` 버텍스 인덱스 튜플(반시계 = 바깥).
"""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from pyjallib.max.skinWeightMath import SpatialGrid

Vec3 = Tuple[float, float, float]
Tri = Tuple[int, int, int]
MeshData = Tuple[Sequence[Vec3], Sequence[Tri]]

#: 진행 콜백 - ``pyjallib.progressEvent``와 같은 (작업명, 현재 단계, 전체 단계).
ProgressCallback = Callable[[str, int, int], None]

#: 엔진 ``FaceCullStrategy`` - 면의 버텍스가 모두 안 / 하나라도 안이면 지운다.
CULL_ALL_VERTICES = "AllVerticesCulled"
CULL_ONE_VERTEX = "OneVertexCulled"

#: 엔진 float ``TMathUtil<float>::ZeroTolerance``.
ENGINE_ZERO_TOLERANCE = 1e-6

#: 복셀 격자 원점을 칸 크기의 이 비율만큼 어긋나게 둔다(1/pi). 엔진은 레이가 클립 메쉬 꼭짓점을 정확히 지나면
#: 첫 교차를 세지 않는다(``_num_intersections``). 격자선이 0·정수 같은 둥근 좌표에 놓이면 대칭 메쉬 중앙선(x = 0)이나
#: 정렬된 버텍스의 레이가 겉면 꼭짓점을 지나 홀짝이 뒤집힌다 - Type A 정답 도형에서 과소 클립 16으로 드러났다.
LATTICE_OFFSET = 0.3183098861837907

#: 덮는 면 분류.
COVER_COVERED = "covered"
COVER_PENETRATING = "penetrating"
COVER_TOO_FAR = "tooFar"
COVER_INSET = "inset"


# =====================================================================
# 벡터 기본기
# =====================================================================


def _sub(inA: Vec3, inB: Vec3) -> Vec3:
    return (inA[0] - inB[0], inA[1] - inB[1], inA[2] - inB[2])


def _add(inA: Vec3, inB: Vec3) -> Vec3:
    return (inA[0] + inB[0], inA[1] + inB[1], inA[2] + inB[2])


def _scale(inA: Vec3, inS: float) -> Vec3:
    return (inA[0] * inS, inA[1] * inS, inA[2] * inS)


def _dot(inA: Vec3, inB: Vec3) -> float:
    return inA[0] * inB[0] + inA[1] * inB[1] + inA[2] * inB[2]


def _cross(inA: Vec3, inB: Vec3) -> Vec3:
    return (
        inA[1] * inB[2] - inA[2] * inB[1],
        inA[2] * inB[0] - inA[0] * inB[2],
        inA[0] * inB[1] - inA[1] * inB[0],
    )


def _length(inA: Vec3) -> float:
    return math.sqrt(_dot(inA, inA))


def _normalize(inA: Vec3) -> Vec3:
    n = _length(inA)
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (inA[0] / n, inA[1] / n, inA[2] / n)


def merge_meshes(inMeshes: Sequence[MeshData]) -> Tuple[List[Vec3], List[Tri], List[Tuple[int, int]]]:
    """여러 메쉬를 버텍스 인덱스를 밀어 하나로 합친다.

    Args:
        inMeshes: ``(verts, tris)`` 목록

    Returns:
        (합친 버텍스, 합친 삼각형, 메쉬별 버텍스 범위 ``[(시작, 끝)]``)
    """
    verts: List[Vec3] = []
    tris: List[Tri] = []
    ranges: List[Tuple[int, int]] = []
    for meshVerts, meshTris in inMeshes:
        base = len(verts)
        verts.extend(tuple(p) for p in meshVerts)
        tris.extend((a + base, b + base, c + base) for a, b, c in meshTris)
        ranges.append((base, len(verts)))
    return verts, tris, ranges


# =====================================================================
# 표면 최근접 질의
# =====================================================================


def closest_point_on_triangle(inP: Vec3, inA: Vec3, inB: Vec3, inC: Vec3) -> Tuple[Vec3, Vec3]:
    """삼각형 위 최근접점과 바리센트릭 가중치 ``(점, (wa, wb, wc))`` (Ericson, Real-Time Collision Detection 5.1.5).

    Args:
        inP: 질의점
        inA: 꼭짓점 A
        inB: 꼭짓점 B
        inC: 꼭짓점 C

    Returns:
        (최근접점, 세 꼭짓점 가중치)
    """
    ab = _sub(inB, inA)
    ac = _sub(inC, inA)
    ap = _sub(inP, inA)
    d1 = _dot(ab, ap)
    d2 = _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return inA, (1.0, 0.0, 0.0)
    bp = _sub(inP, inB)
    d3 = _dot(ab, bp)
    d4 = _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return inB, (0.0, 1.0, 0.0)
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return _add(inA, _scale(ab, v)), (1.0 - v, v, 0.0)
    cp = _sub(inP, inC)
    d5 = _dot(ab, cp)
    d6 = _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return inC, (0.0, 0.0, 1.0)
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return _add(inA, _scale(ac, w)), (1.0 - w, 0.0, w)
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return _add(inB, _scale(_sub(inC, inB), w)), (0.0, 1.0 - w, w)
    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    return _add(inA, _add(_scale(ab, v), _scale(ac, w))), (1.0 - v - w, v, w)


def vertex_normals(inVerts: Sequence[Vec3], inTris: Sequence[Tri]) -> List[Vec3]:
    """면적 가중 버텍스 노멀(면 노멀 크기 = 면적 2배를 그대로 더해 정규화).

    Args:
        inVerts: 버텍스 위치
        inTris: 삼각형

    Returns:
        버텍스마다 단위 노멀. 면이 없는 버텍스는 (0, 0, 1)
    """
    acc = [[0.0, 0.0, 0.0] for _ in inVerts]
    for a, b, c in inTris:
        fn = _cross(_sub(inVerts[b], inVerts[a]), _sub(inVerts[c], inVerts[a]))
        for i in (a, b, c):
            acc[i][0] += fn[0]
            acc[i][1] += fn[1]
            acc[i][2] += fn[2]
    return [_normalize((n[0], n[1], n[2])) for n in acc]


@dataclass
class SurfaceHit:
    """표면 최근접 질의 결과.

    Attributes:
        point: 표면 위 최근접점
        normal: 그 점의 부드러운 노멀(버텍스 노멀 바리센트릭 보간)
        distance: 질의점까지 거리
        height: (질의점 - point) . normal - 표면 바깥이 +
        triangle: 최근접 삼각형 인덱스
    """

    point: Vec3
    normal: Vec3
    distance: float
    height: float
    triangle: int


class TriangleSurface:
    """삼각형 bbox를 균일 격자에 버킷팅한 최근접점 질의 구조.

    Attributes:
        verts: 버텍스 위치
        tris: 삼각형
        normals: 면적 가중 버텍스 노멀
        cellSize: 격자 셀 크기
    """

    def __init__(self, inVerts: Sequence[Vec3], inTris: Sequence[Tri], inCellSize: float = 2.0) -> None:
        """표면을 만든다.

        Args:
            inVerts: 버텍스 위치
            inTris: 삼각형
            inCellSize: 격자 셀 크기(씬 단위). 0 이하이면 ValueError
        """
        if inCellSize <= 0.0:
            raise ValueError(f"셀 크기는 0보다 커야 한다: {inCellSize}")
        self.verts = [tuple(p) for p in inVerts]
        self.tris = [tuple(t) for t in inTris]
        self.normals = vertex_normals(self.verts, self.tris)
        self.cellSize = float(inCellSize)
        self._buckets: Dict[Tuple[int, int, int], List[int]] = {}
        for ti, (a, b, c) in enumerate(self.tris):
            pa, pb, pc = self.verts[a], self.verts[b], self.verts[c]
            lo = [int(math.floor(min(pa[k], pb[k], pc[k]) / self.cellSize)) for k in range(3)]
            hi = [int(math.floor(max(pa[k], pb[k], pc[k]) / self.cellSize)) for k in range(3)]
            for i in range(lo[0], hi[0] + 1):
                for j in range(lo[1], hi[1] + 1):
                    for k in range(lo[2], hi[2] + 1):
                        self._buckets.setdefault((i, j, k), []).append(ti)

    def nearest(self, inPoint: Vec3, inMaxDistance: Optional[float] = None) -> Optional[SurfaceHit]:
        """질의점의 최근접 표면점을 찾는다.

        셀 링을 0부터 넓혀 가며 찾고, 찾은 거리가 이미 본 링 반경 이하이면 멈춘다.

        Args:
            inPoint: 질의점
            inMaxDistance: 이보다 멀면 None. None이면 표면 전체에서 찾는다

        Returns:
            최근접 결과 또는 None(삼각형이 없거나 inMaxDistance 밖)
        """
        if not self.tris:
            return None
        cell = self.cellSize
        ci = [int(math.floor(inPoint[k] / cell)) for k in range(3)]
        if inMaxDistance is None:
            maxRing = 1 << 20
        else:
            maxRing = int(math.ceil(inMaxDistance / cell)) + 1
        best: Optional[Tuple[float, Vec3, Vec3, int]] = None
        seen: Set[int] = set()
        emptyRings = 0
        for r in range(maxRing + 1):
            touched = False
            for i in range(ci[0] - r, ci[0] + r + 1):
                for j in range(ci[1] - r, ci[1] + r + 1):
                    edge = abs(i - ci[0]) == r or abs(j - ci[1]) == r
                    ks = range(ci[2] - r, ci[2] + r + 1) if edge else (ci[2] - r, ci[2] + r)
                    for k in ks:
                        bucket = self._buckets.get((i, j, k))
                        if not bucket:
                            continue
                        touched = True
                        for ti in bucket:
                            if ti in seen:
                                continue
                            seen.add(ti)
                            a, b, c = self.tris[ti]
                            q, bc = closest_point_on_triangle(inPoint, self.verts[a], self.verts[b], self.verts[c])
                            d = _length(_sub(inPoint, q))
                            if best is None or d < best[0]:
                                best = (d, q, bc, ti)
            if best is not None and best[0] <= r * cell:
                break
            emptyRings = 0 if touched else emptyRings + 1
            if inMaxDistance is None and best is None and len(seen) >= len(self.tris):
                break
        if best is None:
            return None
        d, q, bc, ti = best
        if inMaxDistance is not None and d > inMaxDistance:
            return None
        a, b, c = self.tris[ti]
        na, nb, nc = self.normals[a], self.normals[b], self.normals[c]
        n = _normalize(_add(_add(_scale(na, bc[0]), _scale(nb, bc[1])), _scale(nc, bc[2])))
        return SurfaceHit(point=q, normal=n, distance=d, height=_dot(_sub(inPoint, q), n), triangle=ti)

    def project(self, inPoints: Sequence[Vec3], inMaxDistance: Optional[float] = None) -> List[Optional[SurfaceHit]]:
        """점 목록을 표면에 투영한다.

        Args:
            inPoints: 질의점 목록
            inMaxDistance: ``nearest`` 참조

        Returns:
            점마다 결과 또는 None
        """
        return [self.nearest(p, inMaxDistance) for p in inPoints]


# =====================================================================
# 덮임 - 푸쉬·덮는 면·경계 물림
# =====================================================================


@dataclass
class Coverage:
    """덮는 메쉬의 덮임 판정 결과.

    Attributes:
        tops: 버텍스마다 푸쉬한 위 점 g' (투영 실패면 원점)
        bottoms: 버텍스마다 아래 점 p - T * n (투영 실패면 원점)
        heights: 버텍스마다 높이 h (투영 실패면 None)
        triClass: 삼각형마다 분류(``COVER_*``)
        prismTris: 기둥을 만들 삼각형 인덱스(``COVER_COVERED``)
        boundaryVerts: 덮임 경계 버텍스 인덱스
    """

    tops: List[Vec3]
    bottoms: List[Vec3]
    heights: List[Optional[float]]
    triClass: List[str]
    prismTris: List[int]
    boundaryVerts: Set[int]

    def counts(self) -> Dict[str, int]:
        """분류별 삼각형 수."""
        out = {COVER_COVERED: 0, COVER_PENETRATING: 0, COVER_TOO_FAR: 0, COVER_INSET: 0}
        for c in self.triClass:
            out[c] += 1
        return out


def edge_face_counts(inTris: Sequence[Tri]) -> Dict[Tuple[int, int], int]:
    """무방향 엣지마다 그 엣지를 쓰는 삼각형 수."""
    counts: Dict[Tuple[int, int], int] = {}
    for a, b, c in inTris:
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            counts[key] = counts.get(key, 0) + 1
    return counts


def compute_coverage(
    inVerts: Sequence[Vec3],
    inTris: Sequence[Tri],
    inSurface: TriangleSurface,
    inPush: float,
    inMaxHeight: float,
    inInset: float,
    inInnerDepth: float,
) -> Coverage:
    """덮는 메쉬를 덮히는 표면에 투영해 푸쉬·덮는 면·경계 물림을 판정한다(모듈 docstring 1~4).

    Args:
        inVerts: 덮는 메쉬 버텍스(합친 것)
        inTris: 덮는 메쉬 삼각형
        inSurface: 덮히는 표면
        inPush: 푸쉬 거리 d
        inMaxHeight: 최근접 거리 상한 Hmax. 넘으면 ``COVER_TOO_FAR``
        inInset: 경계 물림 거리 m. 0이면 물리지 않는다
        inInnerDepth: 바디 안쪽 깊이 T

    Returns:
        ``Coverage``
    """
    hits = inSurface.project(inVerts, inMaxHeight)
    origin = (0.0, 0.0, 0.0)
    tops: List[Vec3] = []
    bottoms: List[Vec3] = []
    heights: List[Optional[float]] = []
    for g, hit in zip(inVerts, hits):
        if hit is None:
            tops.append(origin)
            bottoms.append(origin)
            heights.append(None)
            continue
        tops.append(_add(g, _scale(hit.normal, inPush)))
        bottoms.append(_sub(hit.point, _scale(hit.normal, inInnerDepth)))
        heights.append(hit.height)

    triClass: List[str] = []
    for a, b, c in inTris:
        ha, hb, hc = heights[a], heights[b], heights[c]
        if ha is None or hb is None or hc is None:
            triClass.append(COVER_TOO_FAR)
        elif ha + inPush > 0.0 and hb + inPush > 0.0 and hc + inPush > 0.0:
            triClass.append(COVER_COVERED)
        else:
            triClass.append(COVER_PENETRATING)

    # 덮임 경계: 열린 엣지 + 덮는 면과 안 덮는 면 사이 엣지
    edgeCovered: Dict[Tuple[int, int], List[bool]] = {}
    for ti, (a, b, c) in enumerate(inTris):
        isCovered = triClass[ti] == COVER_COVERED
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            edgeCovered.setdefault(key, []).append(isCovered)
    boundary: Set[int] = set()
    for (u, v), flags in edgeCovered.items():
        if len(flags) == 1 or (any(flags) and not all(flags)):
            boundary.add(u)
            boundary.add(v)

    if inInset > 0.0 and boundary:
        boundaryList = sorted(boundary)
        grid = SpatialGrid([inVerts[i] for i in boundaryList], inInset)
        limitSq = inInset * inInset
        near: Dict[int, bool] = {}

        def _near(inIndex: int) -> bool:
            cached = near.get(inIndex)
            if cached is not None:
                return cached
            p = inVerts[inIndex]
            found = False
            for j in grid.query_cube(grid.cell_of(p), 1):
                q = grid.positions[j]
                d = _sub(p, q)
                if _dot(d, d) <= limitSq:
                    found = True
                    break
            near[inIndex] = found
            return found

        for ti, (a, b, c) in enumerate(inTris):
            if triClass[ti] == COVER_COVERED and (_near(a) or _near(b) or _near(c)):
                triClass[ti] = COVER_INSET

    prismTris = [ti for ti, cls in enumerate(triClass) if cls == COVER_COVERED]
    return Coverage(
        tops=tops, bottoms=bottoms, heights=heights, triClass=triClass, prismTris=prismTris, boundaryVerts=boundary
    )


# =====================================================================
# 기둥 합집합 - 사면체 분할과 내부 판정
# =====================================================================

Tet = Tuple[Vec3, Vec3, Vec3, Vec3]


def prism_tetrahedra(inTri: Tri, inTops: Sequence[Vec3], inBottoms: Sequence[Vec3]) -> List[Tet]:
    """삼각 기둥 1개를 사면체 3개로 나눈다.

    세 버텍스를 전역 번호 순서 a < b < c로 놓으면(위 A B C, 아래 A' B' C') 옆면 대각선은 A-B', A-C', B-C'다 -
    "번호가 작은 꼭짓점의 위 점에서 큰 꼭짓점의 아래 점으로". 이 규칙은 엣지의 두 끝 번호만으로 정해지므로 이웃
    기둥이 공유하는 옆면을 같은 두 삼각형으로 나눈다.

    Args:
        inTri: 삼각형(전역 버텍스 인덱스)
        inTops: 버텍스마다 위 점
        inBottoms: 버텍스마다 아래 점

    Returns:
        사면체 3개 ``[(A, B, C, C'), (A, B, B', C'), (A, A', B', C')]``
    """
    a, b, c = sorted(inTri)
    pa, pb, pc = inTops[a], inTops[b], inTops[c]
    qa, qb, qc = inBottoms[a], inBottoms[b], inBottoms[c]
    return [(pa, pb, pc, qc), (pa, pb, qb, qc), (pa, qa, qb, qc)]


def _tet_frame(inTet: Tet):
    """사면체 내부 판정용 (원점, 역행렬 행) - 퇴화(부피 ~0)면 None."""
    p0, p1, p2, p3 = inTet
    e1 = _sub(p1, p0)
    e2 = _sub(p2, p0)
    e3 = _sub(p3, p0)
    det = _dot(e1, _cross(e2, e3))
    if abs(det) < 1e-12:
        return None
    inv = 1.0 / det
    r1 = _scale(_cross(e2, e3), inv)
    r2 = _scale(_cross(e3, e1), inv)
    r3 = _scale(_cross(e1, e2), inv)
    return p0, r1, r2, r3


class TetUnion:
    """사면체 합집합의 점 내부 판정(경계 포함, 허용오차 ``inTolerance``).

    Attributes:
        cellSize: 버킷 격자 셀 크기
        tetCount: 퇴화를 뺀 사면체 수
        bounds: 전체 bbox ``(min, max)`` - 사면체가 없으면 None
    """

    def __init__(self, inTets: Sequence[Tet], inCellSize: float = 2.0, inTolerance: float = 1e-9) -> None:
        """합집합을 만든다.

        Args:
            inTets: 사면체 목록
            inCellSize: 버킷 격자 셀 크기. 0 이하이면 ValueError
            inTolerance: 바리센트릭 허용오차(경계 위 점을 안으로 본다)
        """
        if inCellSize <= 0.0:
            raise ValueError(f"셀 크기는 0보다 커야 한다: {inCellSize}")
        self.cellSize = float(inCellSize)
        self._tol = float(inTolerance)
        self._frames = []
        self._boxes: List[Tuple[Vec3, Vec3]] = []
        self._buckets: Dict[Tuple[int, int, int], List[int]] = {}
        lo = [math.inf, math.inf, math.inf]
        hi = [-math.inf, -math.inf, -math.inf]
        for tet in inTets:
            frame = _tet_frame(tet)
            if frame is None:
                continue
            idx = len(self._frames)
            self._frames.append(frame)
            bmin = tuple(min(p[k] for p in tet) for k in range(3))
            bmax = tuple(max(p[k] for p in tet) for k in range(3))
            self._boxes.append((bmin, bmax))
            for k in range(3):
                lo[k] = min(lo[k], bmin[k])
                hi[k] = max(hi[k], bmax[k])
            c0 = [int(math.floor(bmin[k] / self.cellSize)) for k in range(3)]
            c1 = [int(math.floor(bmax[k] / self.cellSize)) for k in range(3)]
            for i in range(c0[0], c1[0] + 1):
                for j in range(c0[1], c1[1] + 1):
                    for k in range(c0[2], c1[2] + 1):
                        self._buckets.setdefault((i, j, k), []).append(idx)
        self.tetCount = len(self._frames)
        self.bounds = None if not self._frames else ((lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2]))

    def tet_contains(self, inIndex: int, inPoint: Vec3) -> bool:
        """사면체 하나가 점을 포함하는가."""
        p0, r1, r2, r3 = self._frames[inIndex]
        d = _sub(inPoint, p0)
        u = _dot(r1, d)
        v = _dot(r2, d)
        w = _dot(r3, d)
        tol = self._tol
        return u >= -tol and v >= -tol and w >= -tol and (u + v + w) <= 1.0 + tol

    def contains(self, inPoint: Vec3) -> bool:
        """합집합이 점을 포함하는가."""
        key = (
            int(math.floor(inPoint[0] / self.cellSize)),
            int(math.floor(inPoint[1] / self.cellSize)),
            int(math.floor(inPoint[2] / self.cellSize)),
        )
        for idx in self._buckets.get(key, ()):
            bmin, bmax = self._boxes[idx]
            if (
                bmin[0] <= inPoint[0] <= bmax[0]
                and bmin[1] <= inPoint[1] <= bmax[1]
                and bmin[2] <= inPoint[2] <= bmax[2]
                and self.tet_contains(idx, inPoint)
            ):
                return True
        return False

    def tet_boxes(self) -> List[Tuple[Vec3, Vec3]]:
        """퇴화를 뺀 사면체마다 bbox."""
        return list(self._boxes)


def build_prism_union(inCoverage: Coverage, inTris: Sequence[Tri], inCellSize: float = 2.0) -> TetUnion:
    """덮는 면마다 기둥을 만들어 사면체 합집합을 돌려준다.

    Args:
        inCoverage: ``compute_coverage`` 결과
        inTris: 덮는 메쉬 삼각형(``compute_coverage``에 준 것)
        inCellSize: 합집합 버킷 셀 크기

    Returns:
        ``TetUnion``
    """
    tets: List[Tet] = []
    for ti in inCoverage.prismTris:
        tets.extend(prism_tetrahedra(inTris[ti], inCoverage.tops, inCoverage.bottoms))
    return TetUnion(tets, inCellSize)


# =====================================================================
# 복셀 - 점유·공동 메움·비다양체 보정·겉면 추출
# =====================================================================


class VoxelGrid:
    """점유 격자. 칸 (i, j, k)의 중심은 ``origin + (i + 0.5, j + 0.5, k + 0.5) * cellSize``.

    Attributes:
        origin: 격자 최소 모서리
        cellSize: 칸 크기
        dims: 칸 수 ``(nx, ny, nz)``
        occ: 칸마다 0/1 (``bytearray``, 인덱스 = i + nx * (j + ny * k))
    """

    def __init__(self, inOrigin: Vec3, inCellSize: float, inDims: Tuple[int, int, int]) -> None:
        """빈 격자를 만든다.

        Args:
            inOrigin: 격자 최소 모서리
            inCellSize: 칸 크기. 0 이하이면 ValueError
            inDims: 칸 수
        """
        if inCellSize <= 0.0:
            raise ValueError(f"복셀 크기는 0보다 커야 한다: {inCellSize}")
        self.origin = tuple(inOrigin)
        self.cellSize = float(inCellSize)
        self.dims = tuple(int(n) for n in inDims)
        self.occ = bytearray(self.dims[0] * self.dims[1] * self.dims[2])

    def index(self, inI: int, inJ: int, inK: int) -> int:
        """칸 인덱스."""
        return inI + self.dims[0] * (inJ + self.dims[1] * inK)

    def get(self, inI: int, inJ: int, inK: int) -> int:
        """칸 점유(격자 밖은 0)."""
        if 0 <= inI < self.dims[0] and 0 <= inJ < self.dims[1] and 0 <= inK < self.dims[2]:
            return self.occ[self.index(inI, inJ, inK)]
        return 0

    def center(self, inI: int, inJ: int, inK: int) -> Vec3:
        """칸 중심 좌표."""
        s = self.cellSize
        return (
            self.origin[0] + (inI + 0.5) * s,
            self.origin[1] + (inJ + 0.5) * s,
            self.origin[2] + (inK + 0.5) * s,
        )

    def count(self) -> int:
        """점유 칸 수."""
        return sum(self.occ)


def voxelize_union(inUnion: TetUnion, inCellSize: float) -> VoxelGrid:
    """합집합을 복셀화한다 - 칸 중심이 합집합 안이면 점유. 격자는 bbox + 사방 1칸 이상 여백(바깥 flood fill 시작점).

    사면체마다 그 bbox 안의 칸 중심만 시험한다(격자 전체를 돌지 않는다). 격자 원점은 ``LATTICE_OFFSET``만큼 어긋난다.

    Args:
        inUnion: 사면체 합집합
        inCellSize: 복셀 크기

    Returns:
        ``VoxelGrid`` (합집합이 비면 1칸짜리 빈 격자)
    """
    if inUnion.bounds is None:
        return VoxelGrid((0.0, 0.0, 0.0), inCellSize, (1, 1, 1))
    s = float(inCellSize)
    lo, hi = inUnion.bounds
    origin = tuple(math.floor(lo[k] / s) * s - s - s * LATTICE_OFFSET for k in range(3))
    dims = tuple(int(math.ceil((hi[k] - origin[k]) / s)) + 2 for k in range(3))
    grid = VoxelGrid(origin, s, dims)
    occ = grid.occ
    nx, ny = dims[0], dims[1]
    for idx, (bmin, bmax) in enumerate(inUnion.tet_boxes()):
        i0 = max(0, int(math.ceil((bmin[0] - origin[0]) / s - 0.5)))
        i1 = min(dims[0] - 1, int(math.floor((bmax[0] - origin[0]) / s - 0.5)))
        j0 = max(0, int(math.ceil((bmin[1] - origin[1]) / s - 0.5)))
        j1 = min(dims[1] - 1, int(math.floor((bmax[1] - origin[1]) / s - 0.5)))
        k0 = max(0, int(math.ceil((bmin[2] - origin[2]) / s - 0.5)))
        k1 = min(dims[2] - 1, int(math.floor((bmax[2] - origin[2]) / s - 0.5)))
        for k in range(k0, k1 + 1):
            z = origin[2] + (k + 0.5) * s
            for j in range(j0, j1 + 1):
                y = origin[1] + (j + 0.5) * s
                row = nx * (j + ny * k)
                for i in range(i0, i1 + 1):
                    cell = i + row
                    if occ[cell]:
                        continue
                    if inUnion.tet_contains(idx, (origin[0] + (i + 0.5) * s, y, z)):
                        occ[cell] = 1
    return grid


def fill_cavities(inGrid: VoxelGrid) -> int:
    """바깥 테두리에서 6-이웃으로 닿지 않는 빈 칸(내부 공동)을 점유로 바꾼다.

    Args:
        inGrid: 격자(제자리 수정)

    Returns:
        채운 칸 수
    """
    nx, ny, nz = inGrid.dims
    occ = inGrid.occ
    total = nx * ny * nz
    outside = bytearray(total)
    queue: deque = deque()
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if i in (0, nx - 1) or j in (0, ny - 1) or k in (0, nz - 1):
                    idx = i + nx * (j + ny * k)
                    if not occ[idx] and not outside[idx]:
                        outside[idx] = 1
                        queue.append(idx)
    strideY = nx
    strideZ = nx * ny
    while queue:
        idx = queue.popleft()
        i = idx % nx
        j = (idx // nx) % ny
        k = idx // strideZ
        for ni, nj, nk, nidx in (
            (i - 1, j, k, idx - 1),
            (i + 1, j, k, idx + 1),
            (i, j - 1, k, idx - strideY),
            (i, j + 1, k, idx + strideY),
            (i, j, k - 1, idx - strideZ),
            (i, j, k + 1, idx + strideZ),
        ):
            if 0 <= ni < nx and 0 <= nj < ny and 0 <= nk < nz and not occ[nidx] and not outside[nidx]:
                outside[nidx] = 1
                queue.append(nidx)
    filled = 0
    for idx in range(total):
        if not occ[idx] and not outside[idx]:
            occ[idx] = 1
            filled += 1
    return filled


#: 2x2x2 블록의 국소 칸 (dx, dy, dz) 8개와 블록 안 면 이웃 쌍.
_BLOCK_CELLS = [(dx, dy, dz) for dz in (0, 1) for dy in (0, 1) for dx in (0, 1)]
_BLOCK_ADJ = [
    (a, b)
    for a in range(8)
    for b in range(a + 1, 8)
    if sum(abs(_BLOCK_CELLS[a][t] - _BLOCK_CELLS[b][t]) for t in range(3)) == 1
]


def _block_connected(inMask: int, inValue: int) -> bool:
    """블록 8칸 중 값이 inValue인 칸들이 블록 안 면 이웃으로 하나로 이어지는가(0칸·1칸이면 참)."""
    members = [c for c in range(8) if ((inMask >> c) & 1) == inValue]
    if len(members) <= 1:
        return True
    seen = {members[0]}
    stack = [members[0]]
    while stack:
        x = stack.pop()
        for a, b in _BLOCK_ADJ:
            y = b if a == x else (a if b == x else None)
            if y is not None and y not in seen and ((inMask >> y) & 1) == inValue:
                seen.add(y)
                stack.append(y)
    return len(seen) == len(members)


_BLOCK_OK = [_block_connected(m, 1) and _block_connected(m, 0) for m in range(256)]


def fix_nonmanifold(inGrid: VoxelGrid) -> int:
    """엣지·꼭짓점만 맞닿는 점유 배치를 빈 칸을 채워 없앤다(결정론, 변화 없을 때까지).

    2x2x2 블록마다 점유 칸과 빈 칸이 각각 블록 안 면 이웃으로 하나로 이어져야 한다. 아니면 그 블록의 빈 칸 중
    국소 순서가 가장 앞선 칸을 채우고 주변 블록을 다시 본다. 채우기만 하므로(점유 칸 단조 증가) 끝난다.

    Args:
        inGrid: 격자(제자리 수정)

    Returns:
        채운 칸 수
    """
    nx, ny, nz = inGrid.dims
    occ = inGrid.occ

    def mask_at(bi: int, bj: int, bk: int) -> int:
        m = 0
        for c, (dx, dy, dz) in enumerate(_BLOCK_CELLS):
            i, j, k = bi + dx, bj + dy, bk + dz
            if 0 <= i < nx and 0 <= j < ny and 0 <= k < nz and occ[i + nx * (j + ny * k)]:
                m |= 1 << c
        return m

    pending: Set[Tuple[int, int, int]] = set()
    for idx in range(nx * ny * nz):
        if occ[idx]:
            i = idx % nx
            j = (idx // nx) % ny
            k = idx // (nx * ny)
            for dx, dy, dz in _BLOCK_CELLS:
                pending.add((i - dx, j - dy, k - dz))
    filled = 0
    while pending:
        work = sorted(pending)
        pending = set()
        for bi, bj, bk in work:
            m = mask_at(bi, bj, bk)
            if _BLOCK_OK[m]:
                continue
            for c, (dx, dy, dz) in enumerate(_BLOCK_CELLS):
                if (m >> c) & 1:
                    continue
                i, j, k = bi + dx, bj + dy, bk + dz
                if not (0 <= i < nx and 0 <= j < ny and 0 <= k < nz):
                    continue
                occ[i + nx * (j + ny * k)] = 1
                filled += 1
                for ex, ey, ez in _BLOCK_CELLS:
                    pending.add((i - ex, j - ey, k - ez))
                break
    return filled


def close_grid(inGrid: VoxelGrid) -> Tuple[int, int]:
    """공동 메움과 비다양체 보정을 변화가 없을 때까지 번갈아 돌린다.

    **보정이 새 공동을 만든다** - 빈 칸을 채우다 가는 통로를 막으면 그 안쪽이 바깥에서 끊긴다. 남은 공동은
    겉면 추출에서 안쪽 껍질이 되어 엔진 홀짝을 뒤집는다(Type A 정답 도형에서 오일러 지표 6으로 드러났다).
    공동을 메우는 쪽은 새 비다양체를 만들지 않으므로 메움 -> 보정 -> 메움이면 끝나지만, 루프로 둔다.

    Args:
        inGrid: 격자(제자리 수정)

    Returns:
        (메운 공동 칸 수, 보정으로 채운 칸 수)
    """
    cavities = fill_cavities(inGrid)
    nonManifold = 0
    while True:
        fixed = fix_nonmanifold(inGrid)
        if fixed == 0:
            break
        nonManifold += fixed
        cavities += fill_cavities(inGrid)
    return cavities, nonManifold


def extract_surface(inGrid: VoxelGrid) -> Tuple[List[Vec3], List[Tri]]:
    """점유/비점유 경계의 정육면체 면을 버텍스 공유 삼각형 메쉬로 뽑는다(바깥 향 감김).

    Args:
        inGrid: 격자

    Returns:
        (버텍스, 삼각형)
    """
    nx, ny, nz = inGrid.dims
    occ = inGrid.occ
    s = inGrid.cellSize
    ox, oy, oz = inGrid.origin
    vid: Dict[Tuple[int, int, int], int] = {}
    verts: List[Vec3] = []
    tris: List[Tri] = []

    def v(gi: int, gj: int, gk: int) -> int:
        key = (gi, gj, gk)
        found = vid.get(key)
        if found is None:
            found = len(verts)
            vid[key] = found
            verts.append((ox + gi * s, oy + gj * s, oz + gk * s))
        return found

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if not occ[i + nx * (j + ny * k)]:
                    continue
                for axis in range(3):
                    for sign in (1, -1):
                        n = [i, j, k]
                        n[axis] += sign
                        if inGrid.get(n[0], n[1], n[2]):
                            continue
                        base = [i, j, k]
                        if sign == 1:
                            base[axis] += 1
                        u = (axis + 1) % 3
                        w = (axis + 2) % 3
                        corners = []
                        for du, dw in ((0, 0), (1, 0), (1, 1), (0, 1)):
                            p = list(base)
                            p[u] += du
                            p[w] += dw
                            corners.append(v(p[0], p[1], p[2]))
                        if sign == -1:
                            corners.reverse()
                        a, b, c, d = corners
                        tris.append((a, b, c))
                        tris.append((a, c, d))
    return verts, tris


def signed_volume(inVerts: Sequence[Vec3], inTris: Sequence[Tri]) -> float:
    """닫힌 메쉬의 부호 있는 부피(바깥 향 감김이면 +)."""
    total = 0.0
    for a, b, c in inTris:
        total += _dot(inVerts[a], _cross(inVerts[b], inVerts[c]))
    return total / 6.0


# =====================================================================
# 엔진 포팅 - Mutable 닫힘 검사·버텍스 안팎 분류 (OpMeshClipWithMesh.cpp)
# =====================================================================


def collapsed_vertex_map(inVerts: Sequence[Vec3]) -> List[int]:
    """위치가 같은 버텍스를 하나로 합치는 지도(원본 ``MeshCreateCollapsedVertexMap``, 29~77행).

    해시 셀 0.01, 반경 ``ZeroTolerance`` 공 안의 점(거리 제곱 < 반경 제곱)을 먼저 나온 버텍스로 합친다. 원본처럼
    안쪽 루프는 이미 배정된 이웃도 현재 버텍스로 다시 쓴다.

    Args:
        inVerts: 버텍스 위치

    Returns:
        버텍스마다 대표 버텍스 인덱스
    """
    cell = 0.01
    radius = ENGINE_ZERO_TOLERANCE
    buckets: Dict[Tuple[int, int, int], List[int]] = {}
    keys = []
    for idx, p in enumerate(inVerts):
        key = (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)), int(math.floor(p[2] / cell)))
        keys.append(key)
        buckets.setdefault(key, []).append(idx)
    out = [-1] * len(inVerts)
    radiusSq = radius * radius
    for idx, p in enumerate(inVerts):
        if out[idx] != -1:
            continue
        ki, kj, kk = keys[idx]
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for dk in (-1, 0, 1):
                    for other in buckets.get((ki + di, kj + dj, kk + dk), ()):
                        q = inVerts[other]
                        d = _sub(q, p)
                        if _dot(d, d) < radiusSq:
                            out[other] = idx
    return out


def is_mesh_closed(inVerts: Sequence[Vec3], inTris: Sequence[Tri]) -> bool:
    """엔진 닫힘 검사(원본 ``IsMeshClosed``, 81~134행) - 합친 뒤 모든 엣지가 정확히 면 2개, 퇴화 면 없음.

    Args:
        inVerts: 클립 메쉬 버텍스
        inTris: 클립 메쉬 삼각형

    Returns:
        닫혔으면 True. 면이 0개면 True(원본은 메쉬가 없으면 참)
    """
    remap = collapsed_vertex_map(inVerts)
    counts: Dict[Tuple[int, int], int] = {}
    for a, b, c in inTris:
        f = (remap[a], remap[b], remap[c])
        for e in range(3):
            v0 = f[e]
            v1 = f[(e + 1) % 3]
            if v0 == v1:
                return False
            key = (v0, v1) if v0 < v1 else (v1, v0)
            counts[key] = counts.get(key, 0) + 1
    return all(c == 2 for c in counts.values())


def _ray_z_triangle(inOrigin: Vec3, inV0: Vec3, inV1: Vec3, inV2: Vec3) -> Optional[Tuple[float, float, float]]:
    """+Z 레이와 삼각형 교차(원본 ``FIntrRay3Triangle3f::FindIntersection`` 비-watertight 판). 바리센트릭 (X, Y, Z) 또는 None.

    D = (0, 0, 1)이라 ``D . v``는 v의 z 성분이다. 평행(|DdN| <= ZeroTolerance)이면 교차 없음, t < 0이면 교차 없음.
    """
    diff = _sub(inOrigin, inV0)
    edge1 = _sub(inV1, inV0)
    edge2 = _sub(inV2, inV0)
    normal = _cross(edge1, edge2)
    ddn = normal[2]
    if ddn > ENGINE_ZERO_TOLERANCE:
        sign = 1.0
    elif ddn < -ENGINE_ZERO_TOLERANCE:
        sign = -1.0
        ddn = -ddn
    else:
        return None
    ddqxe2 = sign * _cross(diff, edge2)[2]
    if ddqxe2 < 0.0:
        return None
    dde1xq = sign * _cross(edge1, diff)[2]
    if dde1xq < 0.0:
        return None
    if ddqxe2 + dde1xq > ddn:
        return None
    qdn = -sign * _dot(diff, normal)
    if qdn < 0.0:
        return None
    inv = 1.0 / ddn
    by = ddqxe2 * inv
    bz = dde1xq * inv
    return (1.0 - by - bz, by, bz)


def _num_intersections(
    inOrigin: Vec3,
    inVerts: Sequence[Vec3],
    inFaces: Sequence[Tri],
    inRemap: Sequence[int],
    inDynamicEpsilon: float,
) -> int:
    """레이 하나의 교차 수(원본 ``GetNumIntersections``, 229~310행).

    엣지 위 교차는 엣지마다 한 번만 센다. **꼭짓점 위 교차는 원본 그대로 첫 번째를 세지 않고 두 번째부터 센다** -
    원본 287행 ``bIsAlreadyIntersected = InOutVertexAlreadyIntersected[...] == 0``이 엣지 경우(``FindOrAdd``)와 반대
    방향이다. 엔진 결과를 재현하는 것이 목적이므로 고치지 않는다.
    """
    count = 0
    vertexHit: Set[int] = set()
    edgeHit: Set[Tuple[int, int]] = set()
    for f in inFaces:
        v0 = inVerts[inRemap[f[0]]]
        v1 = inVerts[inRemap[f[1]]]
        v2 = inVerts[inRemap[f[2]]]
        bary = _ray_z_triangle(inOrigin, v0, v1, v2)
        if bary is None:
            continue
        e01 = abs(bary[2]) <= inDynamicEpsilon
        e02 = abs(bary[1]) <= inDynamicEpsilon
        e12 = abs(bary[0]) <= inDynamicEpsilon
        vertexId = -1
        if e01 and e02:
            vertexId = 0
        if e01 and e12:
            vertexId = 1
        if e02 and e12:
            vertexId = 2
        already = False
        if vertexId >= 0:
            collapsed = inRemap[f[vertexId]]
            already = collapsed not in vertexHit
            vertexHit.add(collapsed)
        elif e01 or e02 or e12:
            ev0 = 0 if (e01 or e02) else 1
            ev1 = 1 if e01 else 2
            c0 = inRemap[f[ev0]]
            c1 = inRemap[f[ev1]]
            key = (max(c0, c1), min(c0, c1))
            already = key in edgeHit
            edgeHit.add(key)
        if not already:
            count += 1
    return count


def classify_vertices(
    inBaseVerts: Sequence[Vec3], inClipVerts: Sequence[Vec3], inClipTris: Sequence[Tri]
) -> List[bool]:
    """베이스 버텍스마다 클립 부피 안인가(원본 ``MeshClipMeshClassifyVertices``, 514~700행).

    클립 bbox(경계 포함) 밖은 밖. 안이면 XY 8 x 8 격자 칸의 면 목록으로 +Z 레이 교차 수를 세어 홀수면 안.
    ``DynamicEpsilon = 1e-6 * 대각선 * min(대각선, 1)``.

    Args:
        inBaseVerts: 베이스(덮히는) 메쉬 버텍스
        inClipVerts: 클립 메쉬 버텍스
        inClipTris: 클립 메쉬 삼각형

    Returns:
        베이스 버텍스마다 안이면 True
    """
    out = [False] * len(inBaseVerts)
    if not inClipVerts:
        return out
    remap = collapsed_vertex_map(inClipVerts)
    lo = [min(p[k] for p in inClipVerts) for k in range(3)]
    hi = [max(p[k] for p in inClipVerts) for k in range(3)]
    diag = _length(_sub(tuple(hi), tuple(lo)))
    dynEps = 0.000001 * diag * (diag if diag < 1.0 else 1.0)
    gridSize = 8
    width = hi[0] - lo[0]
    height = hi[1] - lo[1]
    cellW = width / gridSize
    cellH = height / gridSize
    cells: List[List[Tri]] = [[] for _ in range(gridSize * gridSize)]
    for i in range(gridSize):
        for j in range(gridSize):
            cminX = lo[0] + cellW * i
            cminY = lo[1] + cellH * j
            cmaxX = cminX + cellW
            cmaxY = cminY + cellH
            bucket = cells[i + j * gridSize]
            for f in inClipTris:
                p0, p1, p2 = inClipVerts[f[0]], inClipVerts[f[1]], inClipVerts[f[2]]
                fminX = min(p0[0], p1[0], p2[0])
                fmaxX = max(p0[0], p1[0], p2[0])
                fminY = min(p0[1], p1[1], p2[1])
                fmaxY = max(p0[1], p1[1], p2[1])
                # FAxisAlignedBox2::Intersects - 맞닿기만 하면 교차 아님
                if not (fmaxX <= cminX or fminX >= cmaxX or fmaxY <= cminY or fminY >= cmaxY):
                    bucket.append(f)
    for vi, p in enumerate(inBaseVerts):
        if not (lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1] and lo[2] <= p[2] <= hi[2]):
            continue
        hx = int(((p[0] - lo[0]) / width) * gridSize) if width > 0.0 else 0
        hy = int(((p[1] - lo[1]) / height) * gridSize) if height > 0.0 else 0
        cx = min(max(hx, 0), gridSize - 1)
        cy = min(max(hy, 0), gridSize - 1)
        n = _num_intersections(p, inClipVerts, cells[cx + cy * gridSize], remap, dynEps)
        out[vi] = n % 2 == 1
    return out


def cull_faces(inBaseTris: Sequence[Tri], inInside: Sequence[bool], inStrategy: str = CULL_ALL_VERTICES) -> List[int]:
    """엔진 면 제거 규칙으로 지워질 면 인덱스(``EFaceCullStrategy``).

    Args:
        inBaseTris: 베이스 삼각형
        inInside: 버텍스마다 안인가
        inStrategy: ``CULL_ALL_VERTICES``(기본, 원본 ``MeshClipWithMesh``) 또는 ``CULL_ONE_VERTEX``

    Returns:
        지워질 면 인덱스 목록
    """
    if inStrategy == CULL_ALL_VERTICES:
        return [fi for fi, (a, b, c) in enumerate(inBaseTris) if inInside[a] and inInside[b] and inInside[c]]
    if inStrategy == CULL_ONE_VERTEX:
        return [fi for fi, (a, b, c) in enumerate(inBaseTris) if inInside[a] or inInside[b] or inInside[c]]
    raise ValueError(f"알 수 없는 면 제거 전략: {inStrategy}")


# =====================================================================
# 조립 - 부피 생성과 검증
# =====================================================================


@dataclass
class ClipVolume:
    """``build_clip_volume`` 결과.

    Attributes:
        verts: 복셀 겉면 버텍스
        tris: 복셀 겉면 삼각형
        expected: 대상 이름마다 기대 클립 버텍스 집합 E(대상 메쉬의 0-based 인덱스)
        coverCounts: 덮는 면 분류별 삼각형 수
        stats: 점유 칸·공동 메움·비다양체 보정 칸·사면체 수
        timings: 단계별 초
    """

    verts: List[Vec3]
    tris: List[Tri]
    expected: Dict[str, Set[int]]
    coverCounts: Dict[str, int]
    stats: Dict[str, int] = field(default_factory=dict)
    timings: Dict[str, float] = field(default_factory=dict)


def build_clip_volume(
    inOccluders: Sequence[MeshData],
    inTargets: Dict[str, MeshData],
    inPush: float,
    inVoxelSize: float,
    inInset: float,
    inInnerDepth: float,
    inMaxHeight: float,
    inSurfaceCell: float = 2.0,
    inProgressCallback: Optional[ProgressCallback] = None,
) -> ClipVolume:
    """덮는 메쉬로 클립 부피를 만들고 대상별 기대 클립 집합을 돌려준다(모듈 docstring의 정의 + 이산화).

    Args:
        inOccluders: 덮는 메쉬 ``(verts, tris)`` 목록(월드)
        inTargets: 대상 이름 -> 덮히는 메쉬 ``(verts, tris)`` (월드). 표면은 전부 합쳐 하나로 본다
        inPush: 푸쉬 거리 d (> 0 권장)
        inVoxelSize: 복셀 크기 s (> 0)
        inInset: 경계 물림 거리 m (>= 0)
        inInnerDepth: 바디 안쪽 깊이 T (>= 0)
        inMaxHeight: 최근접 거리 상한 Hmax (> 0)
        inSurfaceCell: 표면 최근접 격자 셀 크기
        inProgressCallback: 진행 콜백(작업명, 현재, 전체)

    Returns:
        ``ClipVolume``

    Raises:
        ValueError: 덮는 메쉬나 대상이 비었거나 파라미터가 범위 밖
    """
    if not inOccluders or not inTargets:
        raise ValueError("덮는 메쉬와 대상이 모두 있어야 한다")
    if inVoxelSize <= 0.0 or inMaxHeight <= 0.0 or inInset < 0.0 or inInnerDepth < 0.0:
        raise ValueError(
            f"파라미터 범위 밖: voxel={inVoxelSize}, maxHeight={inMaxHeight}, inset={inInset}, innerDepth={inInnerDepth}"
        )
    steps = 6

    def _progress(inStep: int, inName: str) -> None:
        if inProgressCallback is not None:
            inProgressCallback(inName, inStep, steps)

    timings: Dict[str, float] = {}
    t0 = time.perf_counter()
    occVerts, occTris, _occRanges = merge_meshes(inOccluders)
    names = list(inTargets.keys())
    tgtVerts, tgtTris, tgtRanges = merge_meshes([inTargets[n] for n in names])
    surface = TriangleSurface(tgtVerts, tgtTris, inSurfaceCell)
    timings["surface"] = time.perf_counter() - t0
    _progress(1, "coverage")

    t0 = time.perf_counter()
    coverage = compute_coverage(occVerts, occTris, surface, inPush, inMaxHeight, inInset, inInnerDepth)
    timings["coverage"] = time.perf_counter() - t0
    _progress(2, "prisms")

    t0 = time.perf_counter()
    union = build_prism_union(coverage, occTris, max(inVoxelSize * 2.0, 1.0))
    timings["prisms"] = time.perf_counter() - t0
    _progress(3, "expected")

    t0 = time.perf_counter()
    expected: Dict[str, Set[int]] = {}
    for name, (start, end) in zip(names, tgtRanges):
        expected[name] = {i - start for i in range(start, end) if union.contains(tgtVerts[i])}
    timings["expected"] = time.perf_counter() - t0
    _progress(4, "voxelize")

    t0 = time.perf_counter()
    grid = voxelize_union(union, inVoxelSize)
    occupied = grid.count()
    cavities, nonManifold = close_grid(grid)
    timings["voxelize"] = time.perf_counter() - t0
    _progress(5, "surface")

    t0 = time.perf_counter()
    verts, tris = extract_surface(grid)
    timings["extract"] = time.perf_counter() - t0
    _progress(6, "done")

    return ClipVolume(
        verts=verts,
        tris=tris,
        expected=expected,
        coverCounts=coverage.counts(),
        stats={
            "tets": union.tetCount,
            "occupied": occupied,
            "cavityFilled": cavities,
            "nonManifoldFilled": nonManifold,
            "gridCells": grid.dims[0] * grid.dims[1] * grid.dims[2],
        },
        timings=timings,
    )


@dataclass
class TargetCheck:
    """대상 하나의 엔진 판정 결과.

    Attributes:
        vertexCount: 대상 버텍스 수
        clipped: 에뮬레이션 클립 집합 C
        expected: 기대 집합 E (없으면 None)
        over: C - E (지우면 안 되는데 지워지는 버텍스)
        under: E - C (지워야 하는데 남는 버텍스)
        overDistanceMax: 과다 버텍스에서 가장 가까운 E 버텍스까지 거리의 최댓값(E가 없거나 과다 0이면 0)
        facesAll: ``AllVerticesCulled``로 지워질 면 수
        facesOne: ``OneVertexCulled``로 지워질 면 수
    """

    vertexCount: int
    clipped: Set[int]
    expected: Optional[Set[int]]
    over: List[int]
    under: List[int]
    overDistanceMax: float
    facesAll: int
    facesOne: int

    def under_ratio(self) -> float:
        """과소 비율 |E - C| / |E| (E가 비거나 없으면 0)."""
        if not self.expected:
            return 0.0
        return len(self.under) / len(self.expected)


@dataclass
class ClipCheck:
    """``verify_clip`` 결과.

    Attributes:
        closed: 엔진 규칙 닫힘
        triangleCount: 클립 메쉬 삼각형 수
        targets: 대상 이름 -> ``TargetCheck``
    """

    closed: bool
    triangleCount: int
    targets: Dict[str, TargetCheck]

    def over_total(self) -> int:
        """전 대상 과다 클립 버텍스 수."""
        return sum(len(t.over) for t in self.targets.values())

    def passed(self) -> bool:
        """닫힘 + 과다 클립 0 (fail-closed 판정 축)."""
        return self.closed and self.over_total() == 0


def verify_clip(
    inClipVerts: Sequence[Vec3],
    inClipTris: Sequence[Tri],
    inTargets: Dict[str, MeshData],
    inExpected: Optional[Dict[str, Set[int]]] = None,
) -> ClipCheck:
    """클립 메쉬를 엔진 규칙으로 판정한다 - 닫힘, 대상별 에뮬레이션 클립 집합과 기대 집합 비교.

    Args:
        inClipVerts: 클립 메쉬 버텍스(월드)
        inClipTris: 클립 메쉬 삼각형
        inTargets: 대상 이름 -> ``(verts, tris)`` (월드)
        inExpected: 대상 이름 -> 기대 집합 E. None이면 비교하지 않는다(수작업 클립 판정)

    Returns:
        ``ClipCheck``
    """
    closed = is_mesh_closed(inClipVerts, inClipTris)
    results: Dict[str, TargetCheck] = {}
    for name, (verts, tris) in inTargets.items():
        inside = classify_vertices(verts, inClipVerts, inClipTris)
        clipped = {i for i, flag in enumerate(inside) if flag}
        expected = None if inExpected is None else set(inExpected.get(name, set()))
        if expected is None:
            over: List[int] = []
            under: List[int] = []
        else:
            over = sorted(clipped - expected)
            under = sorted(expected - clipped)
        overDist = 0.0
        if over and expected:
            expList = sorted(expected)
            grid = SpatialGrid([verts[i] for i in expList], 2.0)
            for vi in over:
                best = math.inf
                r = 1
                while best == math.inf and r <= 64:
                    for j in grid.query_cube(grid.cell_of(verts[vi]), r):
                        best = min(best, _length(_sub(verts[vi], grid.positions[j])))
                    r *= 2
                overDist = max(overDist, best)
        results[name] = TargetCheck(
            vertexCount=len(verts),
            clipped=clipped,
            expected=expected,
            over=over,
            under=under,
            overDistanceMax=overDist,
            facesAll=len(cull_faces(tris, inside, CULL_ALL_VERTICES)),
            facesOne=len(cull_faces(tris, inside, CULL_ONE_VERTEX)),
        )
    return ClipCheck(closed=closed, triangleCount=len(inClipTris), targets=results)
