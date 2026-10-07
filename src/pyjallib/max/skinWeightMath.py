#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""스킨 웨이트 순수 연산 모듈 - pymxs·외부 패키지 비의존(stdlib만).

다른 스킨 툴이 그대로 부를 수 있는 기본기를 모은다: 정규화, 가중 믹스(+본 제한 절단),
본 잠금 재분배, 강체 평균, 본 이름 대칭 매핑, 버텍스 위치/토폴로지 대칭 매칭, 이웃 탐색
(엣지·반경·깊이), 소프트 셀렉션 가중치.

**pymxs를 import하지 않는다.** 판정·계산을 씬 밖으로 빼면 경우의 수를 콘솔(Type A)에서
전수로 고정할 수 있다(`nodeCollectPolicy`·`missingAssetPolicy`와 같은 분리). 어댑터(`Skin`)는
씬에서 재료(가중치·위치·인접·법선)만 모아 넘긴다. numpy도 쓰지 않는다 - 이 코드는 추가
패키지를 설치할 수 없는 DCC 내장 Python에서 실행된다.

## 데이터 표현

- **버텍스 인덱스는 0-based**다. skinOps의 1-based 인덱스와의 변환은 어댑터 경계에서 한다.
- **본 ID는 불투명한 정수**로 다룬다(skinOps 본 ID를 그대로 넣어도 되고 핸들을 넣어도 된다).
- 버텍스 한 개의 가중치는 ``(boneIds, weights)`` 평행 리스트 쌍(``WeightPair``)이다.
- 위치·법선은 ``(x, y, z)`` 튜플이다.

## 원본 동작과의 관계

알고리즘은 SkinKit(MaxScript)의 동작을 기준으로 옮겼다. 의도적으로 달라진 곳은 각 함수
docstring의 "원본과의 차이"에 적는다(입력이 정상 범위일 때는 결과가 같다).
"""

import math
import re
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

Vec3 = Tuple[float, float, float]
WeightPair = Tuple[List[int], List[float]]

#: 믹스 결과에서 버리는 미소 가중치 하한(원본 MixSkin의 0.001).
DEFAULT_MIN_WEIGHT = 0.001

#: 본 이름 대칭 패턴 표(원본 FindBoneSymmetry 순서). MaxScript ``matchPattern`` 와일드카드다.
DEFAULT_MIRROR_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("*Left*", "*Right*"),
    ("*_L_*", "*_R_*"),
    ("*_L", "*_R"),
    ("L_*", "R_*"),
    ("L *", "R *"),
)


# =====================================================================
# 벡터 보조
# =====================================================================


def _sub(inA: Vec3, inB: Vec3) -> Vec3:
    return (inA[0] - inB[0], inA[1] - inB[1], inA[2] - inB[2])


def _dot(inA: Vec3, inB: Vec3) -> float:
    return inA[0] * inB[0] + inA[1] * inB[1] + inA[2] * inB[2]


def _length(inA: Vec3) -> float:
    return math.sqrt(_dot(inA, inA))


def _normalize_vec(inA: Vec3) -> Vec3:
    length = _length(inA)
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return (inA[0] / length, inA[1] / length, inA[2] / length)


def distance(inA: Vec3, inB: Vec3) -> float:
    """두 점 사이 거리."""
    return _length(_sub(inA, inB))


# =====================================================================
# 정규화 / 믹스 / 잠금 / 강체
# =====================================================================


def normalize_weights(inWeights: Sequence[float]) -> List[float]:
    """가중치 목록을 합 1로 정규화한다.

    합이 0 이하이면 첫 항목에 1.0을 준다(원본 DoNormalizeWeight). 빈 입력은 빈 목록.

    원본과의 차이: 원본은 합 0일 때 길이 1짜리 ``#(1.0)``을 돌려줬다. 여기서는 입력과
    **같은 길이**를 유지하고 나머지를 0.0으로 채운다(평행 리스트가 어긋나지 않게).

    Args:
        inWeights: 가중치 목록

    Returns:
        정규화된 새 목록
    """
    if not inWeights:
        return []
    total = float(sum(inWeights))
    if total <= 0.0:
        return [1.0] + [0.0] * (len(inWeights) - 1)
    return [float(w) / total for w in inWeights]


def normalize_pair(inPair: WeightPair) -> WeightPair:
    """``(boneIds, weights)``의 가중치만 정규화한 새 쌍을 돌려준다."""
    return (list(inPair[0]), normalize_weights(inPair[1]))


def mix_weights(
    inPairs: Sequence[WeightPair],
    inRatios: Sequence[float],
    inMinWeight: float = DEFAULT_MIN_WEIGHT,
    inBoneLimit: Optional[int] = None,
) -> WeightPair:
    """여러 버텍스 가중치를 비율로 섞는다(원본 MixSkin).

    ``ratio > 0``인 입력만 더한다. 결과에서 ``inMinWeight`` 이하인 본은 버리고, 본 ID
    **오름차순**으로 돌려준다. **정규화하지 않는다** - 비율 합이 1이고 입력이 정규화돼
    있으면 결과 합은 1에서 버린 미소 가중치만큼만 모자란다(원본과 같음. skinOps 쓰기가
    재정규화한다).

    ``inBoneLimit``이 주어지고 결과 본 수가 그보다 많으면 가장 작은 가중치부터 잘라
    본 수를 맞춘 뒤 남은 합으로 재정규화한다. 잘라낼 경계값과 같은 가중치는 뒤(큰 본 ID)
    부터 잘린다(원본 순서).

    원본과의 차이: 원본은 절단 후 ``1 / (1 - 잘린 합)``으로 재정규화해 입력 합이 1이라고
    가정했다. 여기서는 **실제 남은 합**으로 나눈다(입력 합이 1이면 같다).

    Args:
        inPairs: 버텍스별 ``(boneIds, weights)``
        inRatios: 입력별 섞는 비율(같은 길이)
        inMinWeight: 이 값 이하의 결과 가중치는 버린다. 기본 0.001
        inBoneLimit: 버텍스당 최대 본 수. None이면 자르지 않는다

    Returns:
        ``(boneIds 오름차순, weights)``

    Raises:
        ValueError: 입력과 비율의 길이가 다를 때
    """
    if len(inPairs) != len(inRatios):
        raise ValueError(f"가중치 {len(inPairs)}개와 비율 {len(inRatios)}개의 길이가 다르다")
    accum: Dict[int, float] = {}
    for pair, ratio in zip(inPairs, inRatios):
        if ratio <= 0.0:
            continue
        for boneId, weight in zip(pair[0], pair[1]):
            accum[boneId] = accum.get(boneId, 0.0) + float(weight) * float(ratio)
    boneIds = sorted(b for b, w in accum.items() if w > inMinWeight)
    weights = [accum[b] for b in boneIds]

    if inBoneLimit is None or len(boneIds) <= inBoneLimit:
        return (boneIds, weights)

    # 원본: MaxDist = 정렬된 가중치의 (count - limit)번째(1-based) = 잘라낼 개수번째로 작은 값.
    cutCount = len(boneIds) - inBoneLimit
    threshold = sorted(weights)[cutCount - 1]
    keepIds = list(boneIds)
    keepWeights = list(weights)
    for i in range(len(keepWeights) - 1, -1, -1):
        if len(keepWeights) <= inBoneLimit:
            break
        if keepWeights[i] <= threshold:
            del keepIds[i]
            del keepWeights[i]
    total = sum(keepWeights)
    if total > 0.0:
        keepWeights = [w / total for w in keepWeights]
    return (keepIds, keepWeights)


def solve_locked_weights(
    inOriginal: WeightPair,
    inNew: WeightPair,
    inLockedBones: Set[int],
    inPinnedBone: Optional[int] = None,
) -> WeightPair:
    """잠긴 본은 원래 값으로 되돌리고 나머지(비잠금) 본을 재분배한다(원본 SolveLock).

    1. 잠긴 본(``inPinnedBone`` 제외)의 값은 ``inOriginal``에서 가져온다.
    2. ``inPinnedBone``이 있으면 그 본의 **새 값**을 고정값으로 취급한다(0 미만은 0, 잠긴
       합과 더해 1을 넘으면 넘는 만큼 깎는다). 새 값에 그 본이 없으면 0으로 고정된다.
    3. 비잠금 본은 ``inNew``의 값을 ``(1 - 고정 합)``에 맞게 비례 조정한다. 새 값에 비잠금
       가중치가 하나도 없으면 ``inOriginal``의 비잠금 본을 대신 쓴다.

    결과 순서는 ``비잠금 본들 + 잠긴 본들 + 고정 본``이다(원본 순서).

    Args:
        inOriginal: 편집 전 가중치
        inNew: 편집 후(솔버 결과) 가중치
        inLockedBones: 잠긴 본 ID 집합
        inPinnedBone: 사용자가 직접 조작 중이라 값을 고정할 본 ID. None이면 없음

    Returns:
        ``(boneIds, weights)``
    """
    pinned = inPinnedBone
    pinValue = 0.0
    if pinned is not None:
        for boneId, weight in zip(inNew[0], inNew[1]):
            if boneId == pinned:
                pinValue = float(weight)

    locked = [
        (b, float(w))
        for b, w in zip(inOriginal[0], inOriginal[1])
        if b in inLockedBones and b != pinned
    ]
    unlocked = [
        (b, float(w))
        for b, w in zip(inNew[0], inNew[1])
        if b not in inLockedBones and b != pinned
    ]
    lockedSum = sum(w for _, w in locked)
    unlockedSum = sum(w for _, w in unlocked)

    if pinned is not None:
        if pinValue < 0.0:
            pinValue = 0.0
        if lockedSum + pinValue > 1.0:
            pinValue -= lockedSum + pinValue - 1.0
        locked.append((pinned, pinValue))
        lockedSum += pinValue

    if unlockedSum == 0.0:
        unlocked = [
            (b, float(w))
            for b, w in zip(inOriginal[0], inOriginal[1])
            if b not in inLockedBones and b != pinned
        ]
        unlockedSum = sum(w for _, w in unlocked)

    scale = (1.0 - lockedSum) / unlockedSum if unlockedSum > 0.0 else 0.0
    merged = [(b, w * scale) for b, w in unlocked] + locked
    return ([b for b, _ in merged], [w for _, w in merged])


def rigid_average(
    inPairs: Sequence[WeightPair], inMinWeight: float = DEFAULT_MIN_WEIGHT
) -> WeightPair:
    """버텍스들의 가중치를 균등 평균한다(원본 SolveStiff/Stiff의 강체화).

    Args:
        inPairs: 평균할 버텍스 가중치들
        inMinWeight: ``mix_weights``의 미소 가중치 하한

    Returns:
        평균 ``(boneIds, weights)``. 입력이 비면 빈 쌍
    """
    if not inPairs:
        return ([], [])
    ratio = 1.0 / len(inPairs)
    return mix_weights(inPairs, [ratio] * len(inPairs), inMinWeight=inMinWeight)


# =====================================================================
# 본 이름 대칭
# =====================================================================


def _wildcard_regex(inPattern: str) -> "re.Pattern[str]":
    """MaxScript ``matchPattern`` 와일드카드(``*``, ``?``)를 대소문자 무시 정규식으로."""
    body = "".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in inPattern)
    return re.compile(f"^{body}$", re.IGNORECASE | re.DOTALL)


def mirror_bone_name_candidates(
    inName: str, inPatterns: Sequence[Tuple[str, str]] = DEFAULT_MIRROR_PATTERNS
) -> List[str]:
    """이름 하나에 대해 패턴 표 순서대로 대칭 이름 후보를 만든다.

    - 양쪽이 ``*``인 패턴(``*Left*``): 이름 속 첫 표지(대소문자 무시)를 반대쪽 표지로 바꾼다.
    - 접두 패턴(``L_*``): 앞 표지를 바꾼다.
    - 접미 패턴(``*_L``): 뒤 표지를 바꾼다.

    원본과의 차이(**결함 수정**): 원본 접두 패턴은 ``substring b CurSide.count -1``로 표지
    마지막 글자를 남겨 ``L_Arm -> R__Arm``을 만들었다 - 접두 패턴 대칭이 한 번도 성립하지
    않았다. 여기서는 표지 전체를 바꾼다(``L_Arm -> R_Arm``).

    Args:
        inName: 본 이름
        inPatterns: ``(왼쪽 패턴, 오른쪽 패턴)`` 쌍의 목록

    Returns:
        패턴 표 순서의 후보 이름 목록(매치되는 패턴이 없으면 빈 목록)
    """
    candidates: List[str] = []
    for pair in inPatterns:
        for side in (0, 1):
            pattern = pair[side]
            if not _wildcard_regex(pattern).match(inName):
                continue
            curMark = pattern.strip("*")
            otherMark = pair[1 - side].strip("*")
            starts = pattern.startswith("*")
            ends = pattern.endswith("*")
            if starts and ends:
                idx = inName.lower().find(curMark.lower())
                if idx < 0:
                    continue
                candidates.append(inName[:idx] + otherMark + inName[idx + len(curMark):])
            elif ends:
                candidates.append(otherMark + inName[len(curMark):])
            elif starts:
                candidates.append(inName[: len(inName) - len(curMark)] + otherMark)
    return candidates


def build_mirror_bone_map(
    inBoneNames: Sequence[str],
    inSceneNames: Optional[Iterable[str]] = None,
    inPatterns: Sequence[Tuple[str, str]] = DEFAULT_MIRROR_PATTERNS,
) -> List[int]:
    """본 목록의 각 본에 대해 대칭 본의 **인덱스**를 돌려준다(원본 FindBoneSymmetry).

    후보 이름이 씬에 실제로 있는 첫 패턴을 채택한다(이름 대조는 대소문자 무시, 원본
    ``getNodeByName``과 같다). 채택된 이름이 본 목록에 없거나 후보가 없으면 자기 자신이다.

    Args:
        inBoneNames: Skin 본 이름 목록(인덱스 i가 본 i)
        inSceneNames: 씬 노드 이름 전체. None이면 ``inBoneNames``만 존재한다고 본다
        inPatterns: 패턴 표

    Returns:
        같은 길이의 인덱스 목록(0-based). ``result[i]``가 본 i의 대칭 본
    """
    scene = list(inSceneNames) if inSceneNames is not None else list(inBoneNames)
    sceneByLower: Dict[str, str] = {}
    for name in scene:
        sceneByLower.setdefault(name.lower(), name)
    indexByName: Dict[str, int] = {}
    for i, name in enumerate(inBoneNames):
        indexByName.setdefault(name, i)

    result: List[int] = []
    for i, name in enumerate(inBoneNames):
        mirrorName = name
        for candidate in mirror_bone_name_candidates(name, inPatterns):
            actual = sceneByLower.get(candidate.lower())
            if actual is not None:
                mirrorName = actual
                break
        result.append(indexByName.get(mirrorName, i))
    return result


# =====================================================================
# 공간 격자 / 위치 대칭
# =====================================================================


class SpatialGrid:
    """균일 격자 버킷(원본 SliceAndDice). 셀 크기 기본 1.0(씬 단위).

    Attributes:
        cellSize: 셀 한 변 길이
        origin: 최소 좌표(셀 0의 시작)
        cells: ``{(ix, iy, iz): [버텍스 인덱스...]}``
    """

    def __init__(self, inPositions: Sequence[Vec3], inCellSize: float = 1.0) -> None:
        """위치 목록으로 격자를 만든다.

        Args:
            inPositions: 버텍스 위치(0-based 인덱스)
            inCellSize: 셀 크기. 0 이하이면 ValueError
        """
        if inCellSize <= 0.0:
            raise ValueError(f"셀 크기는 0보다 커야 한다: {inCellSize}")
        self.cellSize = float(inCellSize)
        self.positions = list(inPositions)
        if self.positions:
            self.origin: Vec3 = (
                min(p[0] for p in self.positions),
                min(p[1] for p in self.positions),
                min(p[2] for p in self.positions),
            )
        else:
            self.origin = (0.0, 0.0, 0.0)
        self.cells: Dict[Tuple[int, int, int], List[int]] = defaultdict(list)
        for i, p in enumerate(self.positions):
            self.cells[self.cell_of(p)].append(i)

    def cell_of(self, inPos: Vec3) -> Tuple[int, int, int]:
        """좌표의 셀 키. 원본 ``(p - min) as integer``(0 쪽 절단)과 같다."""
        return (
            int((inPos[0] - self.origin[0]) / self.cellSize),
            int((inPos[1] - self.origin[1]) / self.cellSize),
            int((inPos[2] - self.origin[2]) / self.cellSize),
        )

    def query_cube(self, inCell: Tuple[int, int, int], inRange: int) -> List[int]:
        """셀 중심 ``±inRange`` 정육면체 안의 버텍스 인덱스(오름차순)."""
        found: List[int] = []
        cx, cy, cz = inCell
        for x in range(cx - inRange, cx + inRange + 1):
            for y in range(cy - inRange, cy + inRange + 1):
                for z in range(cz - inRange, cz + inRange + 1):
                    bucket = self.cells.get((x, y, z))
                    if bucket:
                        found.extend(bucket)
        found.sort()
        return found


def build_spatial_grid(inPositions: Sequence[Vec3], inCellSize: float = 1.0) -> SpatialGrid:
    """``SpatialGrid`` 생성 함수형 별칭."""
    return SpatialGrid(inPositions, inCellSize)


def mirror_vertex_map_by_position(
    inPositions: Sequence[Vec3],
    inAxis: int = 0,
    inGrid: Optional[SpatialGrid] = None,
    inMaxRange: int = 10,
) -> List[int]:
    """각 버텍스의 대칭 위치에 가장 가까운 버텍스를 찾는다(원본 FindVertSymmetryPos).

    대칭 위치(축 성분 부호 반전)의 셀에서 범위를 0부터 넓혀 가며 후보가 생기는 첫 범위의
    후보 중 최근접을 고른다(거리가 같으면 작은 인덱스). ``inMaxRange`` 셀까지 후보가 없으면
    자기 자신이다.

    Args:
        inPositions: 버텍스 위치
        inAxis: 대칭 축(0=X, 1=Y, 2=Z). 원본은 X 고정
        inGrid: 재사용할 격자. None이면 셀 1.0으로 만든다
        inMaxRange: 탐색 최대 셀 범위(원본 10)

    Returns:
        같은 길이의 대칭 버텍스 인덱스 목록

    Raises:
        ValueError: 축이 0~2가 아닐 때
    """
    if inAxis not in (0, 1, 2):
        raise ValueError(f"축은 0, 1, 2 중 하나여야 한다: {inAxis}")
    grid = inGrid if inGrid is not None else SpatialGrid(inPositions)
    result: List[int] = []
    for v, pos in enumerate(inPositions):
        mirrored = list(pos)
        mirrored[inAxis] = -mirrored[inAxis]
        target: Vec3 = (mirrored[0], mirrored[1], mirrored[2])
        cell = grid.cell_of(target)
        candidates: List[int] = []
        searchRange = 0
        while searchRange < inMaxRange and not candidates:
            candidates = grid.query_cube(cell, searchRange)
            searchRange += 1
        if not candidates:
            result.append(v)
            continue
        best = candidates[0]
        bestDist = distance(target, inPositions[best])
        for c in candidates[1:]:
            d = distance(target, inPositions[c])
            if d < bestDist:
                best, bestDist = c, d
        result.append(best)
    return result


def build_adjacency(inVertexCount: int, inEdges: Sequence[Tuple[int, int]]) -> List[List[int]]:
    """엣지 목록으로 인접 리스트를 만든다. 이웃 순서는 **엣지 인덱스 순**이다.

    원본 토폴로지 대칭은 ``polyOp.getEdgesUsingVert``(엣지 인덱스 오름차순)를 따라 이웃을
    나열하므로, 같은 순서를 보존해야 결과가 같다. 중복 이웃은 첫 등장만 남긴다.

    Args:
        inVertexCount: 버텍스 수
        inEdges: ``(a, b)`` 0-based 엣지 목록(엣지 인덱스 순)

    Returns:
        버텍스별 이웃 목록
    """
    adjacency: List[List[int]] = [[] for _ in range(inVertexCount)]
    for a, b in inEdges:
        if a == b:
            continue
        if b not in adjacency[a]:
            adjacency[a].append(b)
        if a not in adjacency[b]:
            adjacency[b].append(a)
    return adjacency


def mirror_vertex_map_by_topology(
    inAdjacency: Sequence[Sequence[int]],
    inPositions: Sequence[Vec3],
    inCenterVertex: int,
    inAxis: int = 0,
) -> Dict[int, int]:
    """중심 버텍스에서 BFS로 퍼지며 토폴로지 대칭을 매칭한다(원본 FindVertSymmetryTopo).

    프런티어의 각 버텍스 s와 그 짝 e에 대해, 이웃 수가 같으면 s의 이웃 방향을 e의 이웃
    방향(대칭 위치 기준)과 비교해 가장 같은 방향(내적 최대)끼리 짝짓는다. 한 팬 안에서
    같은 짝을 두 이웃이 원하면 **둘 다 버린다**(중복 매칭 배제). 이미 짝이 있는 버텍스도
    덮어쓴다(원본 동작). 새로 짝이 생긴 버텍스가 다음 프런티어다.

    어댑터는 원본처럼 Relax로 펴진 위치를 넘기는 편이 매칭이 안정적이다.

    Args:
        inAdjacency: 이웃 목록(``build_adjacency`` - 엣지 인덱스 순)
        inPositions: 버텍스 위치
        inCenterVertex: 대칭 중심에 놓인 버텍스(자기 자신과 짝)
        inAxis: 대칭 축

    Returns:
        ``{버텍스: 대칭 버텍스}`` - 도달하지 못한 버텍스는 빠진다

    Raises:
        ValueError: 중심 버텍스가 범위 밖이거나 축이 잘못됐을 때
    """
    if inAxis not in (0, 1, 2):
        raise ValueError(f"축은 0, 1, 2 중 하나여야 한다: {inAxis}")
    if not 0 <= inCenterVertex < len(inPositions):
        raise ValueError(f"중심 버텍스 {inCenterVertex}가 범위 밖이다(0..{len(inPositions) - 1})")

    def mirrored(inP: Vec3) -> Vec3:
        out = list(inP)
        out[inAxis] = -out[inAxis]
        return (out[0], out[1], out[2])

    pos2 = [mirrored(p) for p in inPositions]
    checked: Dict[int, int] = {inCenterVertex: inCenterVertex}
    frontier = [inCenterVertex]
    while frontier:
        before = set(checked)
        for start in frontier:
            end = checked[start]
            nextStart = list(inAdjacency[start])
            nextEnd = list(inAdjacency[end])
            if len(nextStart) != len(nextEnd) or not nextStart:
                continue
            snap: List[int] = []
            for s in nextStart:
                a = _normalize_vec(_sub(inPositions[s], inPositions[start]))
                bestJ = 0
                bestScore = -_dot(a, _normalize_vec(_sub(pos2[nextEnd[0]], pos2[end])))
                for j in range(1, len(nextEnd)):
                    score = -_dot(a, _normalize_vec(_sub(pos2[nextEnd[j]], pos2[end])))
                    if score < bestScore:
                        bestScore, bestJ = score, j
                snap.append(bestJ)
            counts: Dict[int, int] = defaultdict(int)
            for j in snap:
                counts[j] += 1
            for s, j in zip(nextStart, snap):
                if counts[j] == 1:
                    checked[s] = nextEnd[j]
        frontier = sorted(set(checked) - before)
    return checked


# =====================================================================
# 이웃 탐색
# =====================================================================


def edge_neighbor_weights(
    inVertex: int, inNeighbors: Sequence[int], inPositions: Sequence[Vec3]
) -> Tuple[List[int], List[float], List[float]]:
    """엣지로 연결된 이웃과 역거리 가중치(원본 FindBro).

    목록은 자기 자신을 포함해 인덱스 오름차순이다. 자기 자신 0.5, 이웃들은 역거리 비율로
    나머지 0.5를 나눈다(거리 0인 이웃은 0). 이웃이 없으면 빈 목록이다.

    Args:
        inVertex: 대상 버텍스
        inNeighbors: 엣지 이웃(자기 자신 제외)
        inPositions: 버텍스 위치

    Returns:
        ``(verts, ratios, distances)`` 평행 리스트
    """
    if not inNeighbors:
        return ([], [], [])
    verts = sorted(set(inNeighbors) | {inVertex})
    dists = [distance(inPositions[inVertex], inPositions[v]) for v in verts]
    inverse = [0.0 if d == 0.0 else 1.0 / d for d in dists]
    ratios = normalize_weights(inverse)
    ratios[verts.index(inVertex)] = 1.0
    ratios = [r * 0.5 for r in ratios]
    return (verts, ratios, dists)


def radius_neighbor_weights(
    inVertex: int,
    inPositions: Sequence[Vec3],
    inGrid: SpatialGrid,
    inRadius: float,
    inMaxCount: int = 10,
    inExclude: Optional[Set[int]] = None,
    inBlendSelf: bool = True,
) -> Tuple[List[int], List[float]]:
    """반경 안의 이웃(엣지 무관)과 역거리 가중치(원본 findNear).

    격자에서 ``ceil(반경 / 셀)`` 범위를 모아 반경 **미만**인 버텍스를 고른다. 후보가
    ``inMaxCount``보다 많으면 ``inMaxCount``번째로 가까운 거리 이하만 남긴다(동률은 함께
    남는다). 역거리로 정규화한다.

    - ``inBlendSelf=True``(스무스): 자기 자신에 1.0을 주고 전체를 절반으로 - 자기 0.5
    - ``inBlendSelf=False``(Attach): 비율만 정규화. 자기 자신은 ``inExclude``로 빼는 것이 보통

    Args:
        inVertex: 대상 버텍스
        inPositions: 버텍스 위치
        inGrid: 같은 위치로 만든 격자
        inRadius: 탐색 반경
        inMaxCount: 남길 최근접 개수 기준(원본 10)
        inExclude: 후보에서 뺄 버텍스(Attach에서 선택 버텍스)
        inBlendSelf: 자기 자신 0.5 섞기 여부

    Returns:
        ``(verts 오름차순, ratios)``. 후보가 없으면 빈 쌍
    """
    exclude = inExclude or set()
    origin = inPositions[inVertex]
    searchRange = int(math.ceil(inRadius / inGrid.cellSize))
    candidates = [
        v for v in inGrid.query_cube(inGrid.cell_of(origin), searchRange) if v not in exclude
    ]
    pairs = [(v, distance(origin, inPositions[v])) for v in candidates]
    pairs = [(v, d) for v, d in pairs if d < inRadius]
    if len(pairs) > inMaxCount:
        cutoff = sorted(d for _, d in pairs)[inMaxCount - 1]
        pairs = [(v, d) for v, d in pairs if d <= cutoff]
    if not pairs:
        return ([], [])
    verts = [v for v, _ in pairs]
    ratios = normalize_weights([1.0 / d if d > 0.0 else 0.0 for _, d in pairs])
    if inBlendSelf and inVertex in verts:
        ratios[verts.index(inVertex)] = 1.0
        ratios = [r * 0.5 for r in ratios]
    return (verts, ratios)


def depth_distances(
    inVertex: int,
    inNeighborFn: Callable[[int], Tuple[Sequence[int], Sequence[float]]],
    inDepth: int,
) -> Tuple[List[int], List[float]]:
    """엣지 깊이 ``inDepth``까지 퍼지며 경로 길이 최단 거리를 구한다(원본 findDepth2).

    깊이마다 직전 깊이에서 처음 닿았거나 거리가 줄어든 버텍스만 다시 퍼뜨린다. 결과는
    발견 순서(자기 자신이 첫 항목, 거리 0)다.

    Args:
        inVertex: 시작 버텍스
        inNeighborFn: ``v -> (이웃 버텍스들, 각 이웃까지 엣지 길이)``. 자기 자신이 섞여
            있어도 건너뛴다(``edge_neighbor_weights``의 결과를 그대로 넘길 수 있다)
        inDepth: 엣지 깊이

    Returns:
        ``(verts, distances)``
    """
    found: Dict[int, float] = {inVertex: 0.0}
    order: List[int] = [inVertex]
    level: Dict[int, float] = {inVertex: 0.0}
    levelOrder: List[int] = [inVertex]
    for _ in range(inDepth):
        nextLevel: Dict[int, float] = {}
        nextOrder: List[int] = []
        for v in levelOrder:
            curDist = level[v]
            neighbors, lengths = inNeighborFn(v)
            for n, length in zip(neighbors, lengths):
                if n == v:
                    continue
                newDist = curDist + float(length)
                if n not in found:
                    found[n] = newDist
                    order.append(n)
                    nextLevel[n] = newDist
                    nextOrder.append(n)
                elif found[n] > newDist:
                    found[n] = newDist
                    if n not in nextLevel:
                        nextOrder.append(n)
                    nextLevel[n] = newDist
        level, levelOrder = nextLevel, nextOrder
    return (order, [found[v] for v in order])


# =====================================================================
# 소프트 셀렉션
# =====================================================================


def affect_region(inDistance: float, inFalloff: float, inPinch: float, inBubble: float) -> float:
    """3ds Max 소프트 셀렉션 감쇠 곡선(SDK ``AffectRegionFunction``).

    2026-10-06 Phase 0 실측: Max가 계산한 소프트 셀렉션 값과 소수 4자리까지 일치했다
    (pinch 0.5 / bubble 0.7 포함, 최대 편차 0).

    Args:
        inDistance: 선택까지의 거리
        inFalloff: 감쇠 반경. 0 이하면 0
        inPinch: 핀치
        inBubble: 버블

    Returns:
        0~1(핀치·버블에 따라 범위를 넘을 수 있다 - Max와 같다)
    """
    if inFalloff <= 0.0 or inDistance > inFalloff:
        return 0.0
    u = (inFalloff - inDistance) / inFalloff
    u2 = u * u
    s = 1.0 - u
    return (3.0 * u * inBubble * s + 3.0 * u2 * (1.0 - inPinch)) * s + u * u2


def _euclid_nearest_distances(
    inSelected: Sequence[int], inPositions: Sequence[Vec3], inFalloff: float
) -> Dict[int, float]:
    """선택 버텍스까지의 최단 직선 거리(``inFalloff`` 이내만). 격자로 후보를 좁힌다."""
    result: Dict[int, float] = {}
    if inFalloff <= 0.0 or not inSelected:
        return result
    grid = SpatialGrid(inPositions, inFalloff)
    for s in inSelected:
        origin = inPositions[s]
        for v in grid.query_cube(grid.cell_of(origin), 1):
            d = distance(origin, inPositions[v])
            if d <= inFalloff and d < result.get(v, math.inf):
                result[v] = d
    return result


def _edge_path_distances(
    inSelected: Sequence[int],
    inPositions: Sequence[Vec3],
    inAdjacency: Sequence[Sequence[int]],
    inMaxEdges: int,
) -> Dict[int, float]:
    """엣지 ``inMaxEdges``개 이하 경로의 최단 길이(다중 출발, 홉 제한 완화)."""
    dist: Dict[int, float] = {s: 0.0 for s in inSelected}
    frontier = set(inSelected)
    for _ in range(max(0, inMaxEdges)):
        updates: Dict[int, float] = {}
        for u in frontier:
            du = dist[u]
            for v in inAdjacency[u]:
                nd = du + distance(inPositions[u], inPositions[v])
                if nd < dist.get(v, math.inf) and nd < updates.get(v, math.inf):
                    updates[v] = nd
        if not updates:
            break
        dist.update(updates)
        frontier = set(updates)
    return dist


def soft_selection_weights(
    inSelected: Iterable[int],
    inPositions: Sequence[Vec3],
    inFalloff: float,
    inPinch: float = 0.0,
    inBubble: float = 0.0,
    inAdjacency: Optional[Sequence[Sequence[int]]] = None,
    inEdgeDistance: Optional[int] = None,
    inNormals: Optional[Sequence[Vec3]] = None,
    inAffectBackfacing: bool = True,
) -> List[float]:
    """3ds Max 소프트 셀렉션과 같은 버텍스 가중치를 계산한다.

    2026-10-06 Phase 0 실측으로 정한 규칙:

    - 선택 버텍스는 1.0, 나머지는 ``affect_region(선택까지 최단 거리)``.
    - ``inEdgeDistance``가 있으면 거리는 **엣지 경로 길이**이고 그 엣지 수 이내만 닿는다
      (Max Edge Distance - 직선 거리가 아니다. 대각 이웃 직선 3.54 / 경로 5.0에서 0.0741로
      경로 쪽이 일치했다).
    - ``inAffectBackfacing=False``면 선택 법선 평균과 **내적 < 0**인 버텍스를 0으로 둔다
      (내적 0인 옆면은 포함 - 닫힌 박스 실측).

    Max의 값을 직접 읽으려면 메쉬를 선택하고 버텍스 레벨에 둬야 해서 사용자 선택을
    건드린다. 그래서 같은 공식을 여기서 계산한다.

    Args:
        inSelected: 선택 버텍스
        inPositions: 버텍스 위치
        inFalloff: 감쇠 반경
        inPinch: 핀치
        inBubble: 버블
        inAdjacency: 인접 리스트(``inEdgeDistance``를 쓸 때 필수)
        inEdgeDistance: 엣지 거리 제한. None이면 직선 거리
        inNormals: 버텍스 법선(``inAffectBackfacing=False``일 때 필수)
        inAffectBackfacing: 뒷면 포함 여부

    Returns:
        버텍스별 가중치(길이 = 위치 수)

    Raises:
        ValueError: 필요한 인접·법선이 없을 때
    """
    selected = sorted(set(inSelected))
    weights = [0.0] * len(inPositions)
    if not selected:
        return weights

    if inEdgeDistance is not None:
        if inAdjacency is None:
            raise ValueError("엣지 거리 모드에는 인접 리스트가 필요하다")
        dists = _edge_path_distances(selected, inPositions, inAdjacency, inEdgeDistance)
    else:
        dists = _euclid_nearest_distances(selected, inPositions, inFalloff)

    facing: Optional[Vec3] = None
    if not inAffectBackfacing:
        if inNormals is None:
            raise ValueError("뒷면 제외 모드에는 버텍스 법선이 필요하다")
        sx = sum(inNormals[s][0] for s in selected)
        sy = sum(inNormals[s][1] for s in selected)
        sz = sum(inNormals[s][2] for s in selected)
        facing = _normalize_vec((sx, sy, sz))

    selectedSet = set(selected)
    for v, d in dists.items():
        if v in selectedSet:
            weights[v] = 1.0
            continue
        if facing is not None and inNormals is not None and _dot(inNormals[v], facing) < 0.0:
            continue
        weights[v] = affect_region(d, inFalloff, inPinch, inBubble)
    return weights
