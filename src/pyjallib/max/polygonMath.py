#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""폴리곤 순수 연산 모듈 - 다른 오브젝트에 가려진 면 판정. pymxs·외부 패키지 비의존(stdlib만).

**pymxs를 import하지 않는다.** 판정 규칙을 씬 밖으로 빼면 경우의 수를 콘솔(Type A)에서 고정할 수
있다(``skinWeightMath``·``nodeCollectPolicy``와 같은 분리). 어댑터(``Polygon``)는 씬에서 재료(버텍스·면·
법선)를 모으고 레이 질의를 콜러블로 주입한다. numpy도 쓰지 않는다 - 추가 패키지를 설치할 수 없는 DCC
내장 Python에서 실행된다.

## "가려진 면"의 정의 (두 번의 가시성 시험)

대상 면 F를 **가려진 면(삭제 후보)**으로 판정한다 ⇔ 다음 두 조건이 모두 참이다.

- **시험 1:** 대상 자신 + 가리는 오브젝트를 차폐물로 두고 쏜 레이가 **전부** 막힌다(옷을 포함해 안 보인다).
- **시험 2:** 대상 자신만 차폐물로 두고 쏜 레이 중 **하나라도** 빠져나간다(옷이 없으면 보인다).

시험 2가 없으면 "대상이 대상을 가리는 곳"(깊은 주름·겨드랑이 등)까지 지워진다. 시험 1에서 대상 자신을
차폐물에서 빼면, 열린 옷(바지 허리·밑단) 안에서 비스듬한 레이가 몸과 옷 사이 틈을 따라 구멍으로
빠져나가 덮인 면이 "보임"이 된다 - 실제로는 몸이 그 시선을 막는다. 두 시험이 이 둘을 함께 막는다.

샘플점은 면의 버텍스 + 면 중심이다. 버텍스 결과는 그 버텍스를 쓰는 면들이 공유한다. 면 집계는 보존
쪽으로 기운다.

- 샘플 하나라도 시험 1에서 보이면 면은 **보임** - 가리는 오브젝트의 경계를 가로지르는 면은 남는다.
- (보임이 아니고) 샘플 하나라도 시험 2에서 전부 막히면 **자기 가림**(보존).
- 나머지가 **가려짐 후보**이고, 여유 거리(margin) 안에 보임 면 버텍스가 있으면 **여유 보존**으로 옮긴다.

## 데이터 표현

- **인덱스는 0-based**다. 3ds Max의 1-based 인덱스와의 변환은 어댑터 경계에서 한다.
- 위치·법선·방향은 ``(x, y, z)`` 튜플(월드 공간)이다.
- 레이 방향은 법선을 +z로 둔 국소 좌표로 만들고 ``local_frame``으로 월드로 돌린다. 어댑터의 MAXScript
  구현은 **같은 프레임 규칙**을 써야 한다(``local_frame`` docstring).
"""

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from pyjallib.max.skinWeightMath import SpatialGrid

Vec3 = Tuple[float, float, float]

#: 샘플 묶음 질의: (시작점 목록, 법선 목록) -> 샘플마다 "레이 하나라도 빠져나갔는가".
#: 시작점 오프셋(ε)과 조기 종료는 질의 구현의 몫이다(``make_sample_query`` 참조).
SampleQuery = Callable[[Sequence[Vec3], Sequence[Vec3]], List[bool]]

#: 레이 하나 질의: (시작점, 월드 방향) -> 막혔는가.
RayBlocked = Callable[[Vec3, Vec3], bool]

#: 진행 콜백 - ``pyjallib.progressEvent``와 같은 (작업명, 현재 단계, 전체 단계).
ProgressCallback = Callable[[str, int, int], None]

DEFAULT_CHUNK_SIZE = 2000


# =====================================================================
# 벡터 기본기
# =====================================================================


def _sub(inA: Vec3, inB: Vec3) -> Vec3:
    return (inA[0] - inB[0], inA[1] - inB[1], inA[2] - inB[2])


def _cross(inA: Vec3, inB: Vec3) -> Vec3:
    return (
        inA[1] * inB[2] - inA[2] * inB[1],
        inA[2] * inB[0] - inA[0] * inB[2],
        inA[0] * inB[1] - inA[1] * inB[0],
    )


def normalize(inVec: Vec3, inFallback: Optional[Vec3] = None) -> Vec3:
    """단위 벡터로 만든다.

    Args:
        inVec: 입력 벡터
        inFallback: 길이가 0에 가까울 때 돌려줄 값. None이면 (0, 0, 1)

    Returns:
        단위 벡터 또는 폴백
    """
    length = math.sqrt(inVec[0] * inVec[0] + inVec[1] * inVec[1] + inVec[2] * inVec[2])
    if length < 1e-12:
        return inFallback if inFallback is not None else (0.0, 0.0, 1.0)
    return (inVec[0] / length, inVec[1] / length, inVec[2] / length)


def newell_normal(inPoints: Sequence[Vec3]) -> Vec3:
    """다각형의 뉴웰 법선(비평면 다각형에도 안정적). 퇴화면 (0, 0, 0)을 단위화하지 않고 돌려준다.

    Args:
        inPoints: 다각형 꼭짓점(감김 순서대로)

    Returns:
        정규화한 법선. 넓이가 0이면 (0.0, 0.0, 0.0)
    """
    nx = ny = nz = 0.0
    count = len(inPoints)
    for i in range(count):
        cur = inPoints[i]
        nxt = inPoints[(i + 1) % count]
        nx += (cur[1] - nxt[1]) * (cur[2] + nxt[2])
        ny += (cur[2] - nxt[2]) * (cur[0] + nxt[0])
        nz += (cur[0] - nxt[0]) * (cur[1] + nxt[1])
    return normalize((nx, ny, nz), (0.0, 0.0, 0.0))


# =====================================================================
# 레이 방향
# =====================================================================


def cone_directions(inCount: int, inConeAngle: float = 90.0) -> List[Vec3]:
    """+z를 축으로 하는 반원뿔(반각 inConeAngle도) 안에 고르게 분포한 단위 방향(결정론적).

    피보나치(황금각) 나선으로 원뿔 캡의 넓이를 균등 분할한다. 같은 인자면 항상 같은 목록이다.

    Args:
        inCount: 방향 수(1 이상)
        inConeAngle: 반각(도). 0 초과 90 이하. 90이면 반구

    Returns:
        국소 좌표(+z = 법선) 단위 방향 목록

    Raises:
        ValueError: 개수나 각도가 범위를 벗어날 때
    """
    if inCount < 1:
        raise ValueError(f"방향 수는 1 이상이어야 한다: {inCount}")
    if not (0.0 < inConeAngle <= 90.0):
        raise ValueError(f"반각은 0 초과 90 이하여야 한다: {inConeAngle}")
    cosMin = math.cos(math.radians(inConeAngle))
    golden = math.pi * (3.0 - math.sqrt(5.0))
    dirs: List[Vec3] = []
    for i in range(inCount):
        z = 1.0 - (i + 0.5) / inCount * (1.0 - cosMin)
        r = math.sqrt(max(0.0, 1.0 - z * z))
        phi = golden * i
        dirs.append((r * math.cos(phi), r * math.sin(phi), z))
    return dirs


def local_frame(inNormal: Vec3) -> Tuple[Vec3, Vec3, Vec3]:
    """법선 기준 정규직교 프레임 (t, b, n).

    규칙: ``up = (0,0,1) if |n.z| < 0.9 else (1,0,0)``, ``t = normalize(up x n)``, ``b = n x t``.
    어댑터의 MAXScript 레이 루프도 이 규칙을 그대로 쓴다 - 두 구현의 방향 집합이 같아야 Type A
    판정과 씬 판정이 같은 질문을 한다.

    Args:
        inNormal: 법선(정규화하지 않아도 된다)

    Returns:
        (접선 t, 종법선 b, 법선 n)
    """
    n = normalize(inNormal)
    up = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    t = normalize(_cross(up, n))
    b = _cross(n, t)
    return t, b, n


def to_world(inLocalDir: Vec3, inFrame: Tuple[Vec3, Vec3, Vec3]) -> Vec3:
    """국소 방향을 프레임으로 월드 방향으로 돌린다."""
    t, b, n = inFrame
    x, y, z = inLocalDir
    return (
        t[0] * x + b[0] * y + n[0] * z,
        t[1] * x + b[1] * y + n[1] * z,
        t[2] * x + b[2] * y + n[2] * z,
    )


def sample_escapes(
    inPoint: Vec3,
    inNormal: Vec3,
    inLocalDirs: Sequence[Vec3],
    inEpsilon: float,
    inRayBlocked: RayBlocked,
) -> bool:
    """샘플점 하나에서 레이 하나라도 빠져나가는가(조기 종료).

    시작점은 법선 방향으로 inEpsilon만큼 띄운다. 첫 탈출에서 나머지 레이를 쏘지 않는다.

    Args:
        inPoint: 샘플점
        inNormal: 샘플 법선
        inLocalDirs: ``cone_directions`` 결과
        inEpsilon: 시작점 오프셋
        inRayBlocked: (시작점, 월드 방향) -> 막혔는가

    Returns:
        하나라도 빠져나가면 True
    """
    frame = local_frame(inNormal)
    n = frame[2]
    origin = (inPoint[0] + n[0] * inEpsilon, inPoint[1] + n[1] * inEpsilon, inPoint[2] + n[2] * inEpsilon)
    for localDir in inLocalDirs:
        if not inRayBlocked(origin, to_world(localDir, frame)):
            return True
    return False


def make_sample_query(inLocalDirs: Sequence[Vec3], inEpsilon: float, inRayBlocked: RayBlocked) -> SampleQuery:
    """레이 하나 질의로 샘플 묶음 질의를 만든다(순수 구현 - 테스트·소규모용).

    어댑터의 MAXScript 일괄 루프와 의미가 같다: 같은 프레임 규칙, 같은 시작점 오프셋, 조기 종료.

    Args:
        inLocalDirs: ``cone_directions`` 결과
        inEpsilon: 시작점 오프셋
        inRayBlocked: (시작점, 월드 방향) -> 막혔는가

    Returns:
        ``SampleQuery``
    """
    dirs = list(inLocalDirs)

    def _query(inPoints: Sequence[Vec3], inNormals: Sequence[Vec3]) -> List[bool]:
        return [sample_escapes(p, n, dirs, inEpsilon, inRayBlocked) for p, n in zip(inPoints, inNormals)]

    return _query


# =====================================================================
# 샘플 구성 / 면 판정
# =====================================================================


@dataclass
class FaceSamples:
    """면 판정용 샘플 묶음.

    Attributes:
        points: 샘플 위치(버텍스 샘플이 먼저, 면 중심 샘플이 뒤)
        normals: 샘플 법선
        faceSampleIds: 면마다 그 면이 쓰는 샘플 인덱스(버텍스 샘플들 + 자기 중심 샘플)
        vertexSampleIndex: 버텍스 인덱스 -> 샘플 인덱스(면이 쓰는 버텍스만)
    """

    points: List[Vec3]
    normals: List[Vec3]
    faceSampleIds: List[List[int]]
    vertexSampleIndex: Dict[int, int]


def build_face_samples(
    inVerts: Sequence[Vec3],
    inFaces: Sequence[Sequence[int]],
    inVertNormals: Sequence[Vec3],
) -> FaceSamples:
    """면이 쓰는 버텍스 + 면 중심으로 샘플을 만든다. 면에 안 쓰이는 버텍스는 샘플하지 않는다.

    면 중심 법선은 뉴웰 법선이고, 퇴화면이면 버텍스 법선 평균, 그것도 0이면 (0, 0, 1)이다.

    Args:
        inVerts: 버텍스 위치(월드)
        inFaces: 면마다 버텍스 인덱스 목록(0-based, 3개 이상)
        inVertNormals: 버텍스 법선(inVerts와 같은 길이)

    Returns:
        ``FaceSamples``

    Raises:
        ValueError: 길이 불일치, 꼭짓점 3개 미만, 인덱스 범위 밖
    """
    vertCount = len(inVerts)
    if len(inVertNormals) != vertCount:
        raise ValueError(f"버텍스 법선 수({len(inVertNormals)})가 버텍스 수({vertCount})와 다르다")
    vertexSampleIndex: Dict[int, int] = {}
    points: List[Vec3] = []
    normals: List[Vec3] = []
    for f, face in enumerate(inFaces):
        if len(face) < 3:
            raise ValueError(f"면 {f}의 꼭짓점이 3개 미만이다: {list(face)}")
        for v in face:
            if not (0 <= v < vertCount):
                raise ValueError(f"면 {f}의 버텍스 인덱스 {v}가 범위 밖이다(0..{vertCount - 1})")
            if v not in vertexSampleIndex:
                vertexSampleIndex[v] = len(points)
                points.append(tuple(inVerts[v]))
                normals.append(normalize(inVertNormals[v]))
    faceSampleIds: List[List[int]] = []
    for face in inFaces:
        ps = [inVerts[v] for v in face]
        center = (
            sum(p[0] for p in ps) / len(ps),
            sum(p[1] for p in ps) / len(ps),
            sum(p[2] for p in ps) / len(ps),
        )
        nrm = newell_normal(ps)
        if nrm == (0.0, 0.0, 0.0):
            summed = [0.0, 0.0, 0.0]
            for v in face:
                vn = inVertNormals[v]
                summed[0] += vn[0]
                summed[1] += vn[1]
                summed[2] += vn[2]
            nrm = normalize((summed[0], summed[1], summed[2]))
        ids = [vertexSampleIndex[v] for v in face]
        ids.append(len(points))
        points.append(center)
        normals.append(nrm)
        faceSampleIds.append(ids)
    return FaceSamples(points, normals, faceSampleIds, vertexSampleIndex)


def classify_faces(
    inFaceSampleIds: Sequence[Sequence[int]],
    inTest1Escaped: Sequence[bool],
    inSelfBlocked: Set[int],
) -> Tuple[Set[int], Set[int], Set[int]]:
    """샘플 결과로 면을 (보임, 자기 가림, 가려짐 후보)로 나눈다.

    - 샘플 하나라도 시험 1에서 빠져나가면 보임.
    - 아니면 샘플 하나라도 시험 2에서 전부 막혔으면(inSelfBlocked) 자기 가림.
    - 나머지가 가려짐 후보.

    Args:
        inFaceSampleIds: 면마다 샘플 인덱스
        inTest1Escaped: 샘플마다 시험 1 탈출 여부
        inSelfBlocked: 시험 2에서 레이가 전부 막힌 샘플 인덱스 집합

    Returns:
        (보임 면, 자기 가림 면, 가려짐 후보 면) 집합
    """
    visible: Set[int] = set()
    selfOccluded: Set[int] = set()
    candidates: Set[int] = set()
    for f, ids in enumerate(inFaceSampleIds):
        if any(inTest1Escaped[s] for s in ids):
            visible.add(f)
        elif any(s in inSelfBlocked for s in ids):
            selfOccluded.add(f)
        else:
            candidates.add(f)
    return visible, selfOccluded, candidates


def margin_keep(
    inVerts: Sequence[Vec3],
    inFaces: Sequence[Sequence[int]],
    inVisibleFaces: Set[int],
    inCandidateFaces: Set[int],
    inMargin: float,
) -> Set[int]:
    """보임 면 버텍스로부터 여유 거리 이내 버텍스를 가진 후보 면을 고른다(유클리드).

    여유 0이면 아무것도 고르지 않는다. 여유가 0보다 크면 보임 면과 버텍스를 공유하는 후보 면(거리 0)은
    항상 고른다 - 보임 영역 둘레 한 고리는 여유 값과 무관하게 남는다.

    Args:
        inVerts: 버텍스 위치
        inFaces: 면의 버텍스 인덱스
        inVisibleFaces: 보임 면
        inCandidateFaces: 가려짐 후보 면
        inMargin: 여유 거리(0 이상)

    Returns:
        여유로 보존할 후보 면 집합

    Raises:
        ValueError: 여유가 음수일 때
    """
    if inMargin < 0.0:
        raise ValueError(f"여유 거리는 0 이상이어야 한다: {inMargin}")
    if inMargin == 0.0 or not inVisibleFaces or not inCandidateFaces:
        return set()
    sourceIds = sorted({v for f in inVisibleFaces for v in inFaces[f]})
    sourcePos = [inVerts[v] for v in sourceIds]
    grid = SpatialGrid(sourcePos, inMargin)
    marginSq = inMargin * inMargin
    nearCache: Dict[int, bool] = {}
    kept: Set[int] = set()
    for f in inCandidateFaces:
        for v in inFaces[f]:
            near = nearCache.get(v)
            if near is None:
                p = inVerts[v]
                near = False
                for k in grid.query_cube(grid.cell_of(p), 1):
                    q = sourcePos[k]
                    d = _sub(p, q)
                    if d[0] * d[0] + d[1] * d[1] + d[2] * d[2] <= marginSq:
                        near = True
                        break
                nearCache[v] = near
            if near:
                kept.add(f)
                break
    return kept


# =====================================================================
# 결과 / 오케스트레이터
# =====================================================================


@dataclass
class OccludedFaceResult:
    """가려진 면 판정 결과(0-based 면 인덱스).

    Attributes:
        faceCount: 전체 면 수
        sampleCount: 샘플 수(면이 쓰는 버텍스 + 면 중심)
        test1BlockedSamples: 시험 1에서 레이가 전부 막힌 샘플 수
        selfBlockedSamples: 그중 시험 2에서도 전부 막힌 샘플 수
        visibleFaces: 보임 면
        selfOccludedFaces: 자기 가림으로 보존한 면
        marginKeptFaces: 여유 거리로 보존한 면
        occludedFaces: 가려진 면(삭제 후보)
    """

    faceCount: int = 0
    sampleCount: int = 0
    test1BlockedSamples: int = 0
    selfBlockedSamples: int = 0
    visibleFaces: List[int] = field(default_factory=list)
    selfOccludedFaces: List[int] = field(default_factory=list)
    marginKeptFaces: List[int] = field(default_factory=list)
    occludedFaces: List[int] = field(default_factory=list)

    def counts(self) -> Dict[str, int]:
        """분류별 면 수(리포트·로그용)."""
        return {
            "faces": self.faceCount,
            "visible": len(self.visibleFaces),
            "selfOccluded": len(self.selfOccludedFaces),
            "marginKept": len(self.marginKeptFaces),
            "occluded": len(self.occludedFaces),
        }


def _run_chunked(
    inQuery: SampleQuery,
    inPoints: Sequence[Vec3],
    inNormals: Sequence[Vec3],
    inChunkSize: int,
    inTaskName: str,
    inProgress: Optional[ProgressCallback],
) -> List[bool]:
    total = len(inPoints)
    result: List[bool] = []
    if inProgress is not None:
        inProgress(inTaskName, 0, total)
    for start in range(0, total, inChunkSize):
        part = inQuery(inPoints[start:start + inChunkSize], inNormals[start:start + inChunkSize])
        part = list(part)
        expected = min(inChunkSize, total - start)
        if len(part) != expected:
            raise ValueError(f"{inTaskName}: 질의 결과 수 {len(part)} != 샘플 수 {expected}")
        result.extend(bool(x) for x in part)
        if inProgress is not None:
            inProgress(inTaskName, len(result), total)
    return result


def find_occluded_faces(
    inVerts: Sequence[Vec3],
    inFaces: Sequence[Sequence[int]],
    inVertNormals: Sequence[Vec3],
    inTest1Query: SampleQuery,
    inTest2Query: SampleQuery,
    inMargin: float,
    inProgressCallback: Optional[ProgressCallback] = None,
    inChunkSize: int = DEFAULT_CHUNK_SIZE,
) -> OccludedFaceResult:
    """가려진 면을 판정한다(모듈 docstring의 두 시험 정의).

    시험 1은 전 샘플에, 시험 2는 시험 1에서 전부 막힌 샘플에만 질의한다. 질의는 inChunkSize 단위로
    나눠 부르고 묶음마다 진행 콜백을 부른다.

    Args:
        inVerts: 버텍스 위치(월드)
        inFaces: 면마다 버텍스 인덱스(0-based)
        inVertNormals: 버텍스 법선
        inTest1Query: 대상 + 가리는 오브젝트 차폐 질의
        inTest2Query: 대상만 차폐 질의
        inMargin: 여유 거리(0 이상)
        inProgressCallback: (작업명, 현재, 전체) 콜백. None이면 부르지 않는다
        inChunkSize: 질의 묶음 크기(1 이상)

    Returns:
        ``OccludedFaceResult``

    Raises:
        ValueError: 입력 형식 오류, 음수 여유, 질의 결과 수 불일치
    """
    if inChunkSize < 1:
        raise ValueError(f"묶음 크기는 1 이상이어야 한다: {inChunkSize}")
    if inMargin < 0.0:
        raise ValueError(f"여유 거리는 0 이상이어야 한다: {inMargin}")
    samples = build_face_samples(inVerts, inFaces, inVertNormals)
    test1 = _run_chunked(
        inTest1Query, samples.points, samples.normals, inChunkSize, "시험 1 (가리는 오브젝트 포함)", inProgressCallback
    )
    blocked = [i for i, escaped in enumerate(test1) if not escaped]
    test2 = _run_chunked(
        inTest2Query,
        [samples.points[i] for i in blocked],
        [samples.normals[i] for i in blocked],
        inChunkSize,
        "시험 2 (대상만)",
        inProgressCallback,
    )
    selfBlocked = {blocked[k] for k, escaped in enumerate(test2) if not escaped}
    visible, selfOccluded, candidates = classify_faces(samples.faceSampleIds, test1, selfBlocked)
    kept = margin_keep(inVerts, inFaces, visible, candidates, inMargin)
    return OccludedFaceResult(
        faceCount=len(inFaces),
        sampleCount=len(samples.points),
        test1BlockedSamples=len(blocked),
        selfBlockedSamples=len(selfBlocked),
        visibleFaces=sorted(visible),
        selfOccludedFaces=sorted(selfOccluded),
        marginKeptFaces=sorted(kept),
        occludedFaces=sorted(candidates - kept),
    )
