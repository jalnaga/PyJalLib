#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""폴리곤 모듈 - 3ds Max 메쉬 폴리곤 질의.

기능:

- **다른 오브젝트에 가려진 면 추출**(``Polygon.find_occluded_faces``). 판정 규칙은 순수 모듈 ``polygonMath``에
  있고, 이 어댑터는 씬에서 재료(평가 형상의 버텍스·면·법선)를 읽고 레이 질의를 만든다. **씬을 바꾸지 않는다** -
  레이 그리드용 임시 노드는 undo 기록 밖에서 만들고 ``finally``에서 지우며, 씬 저장 필요 플래그도 호출 전 값으로 되돌린다.
- **UV 마스크 베이크**(``read_map_faces`` / ``bake_face_mask``, 순수 규칙 ``uvMask``).
- **클립 메쉬 생성·판정**(``build_clip_mesh`` / ``classify_clip``, 순수 규칙 ``clipMesh``). 덮는 메쉬로 닫힌 클립
  부피 노드를 **하나 만든다**(원본은 바꾸지 않는다). 감축은 순수 모듈의 ``clipMesh.decimate_clip_volume``(닫힘 보존 +
  보호된 성장)이다. Max 감축기(ProOptimizer·MultiRes)는 쓰지 않는다 - 2026-10-22 실기 슬롯에서 F에 따라 닫힘을 들쭉날쭉하게
  깼다(Upper F 250~4000 전부). 덧붙여 모디파이어를 얹고 속성만 쓰면 스택 평가 전까지 **조용히 무동작**이었다.
  ``build_clip_mesh_alpha``(2026-10-23)는 복셀화 대신 기둥 부피를 Alpha Wrap(``pyjallib.native``, C++)으로 감싸고 과다 반복
  제거를 거친다 - 노드 규격·감축·판정은 같다. 두 경로 모두 감축 목표를 "남길 비율 %"(``inKeepRatio``)로 줄 수 있다.

## 레이 엔진 (2026-10-19 실측, 3ds Max 2024)

- ``RayMeshGridIntersect.addNode``는 **첫 노드만 쓴다**(여러 번 넣어도 나머지는 무시된다). 그래서 차폐물은
  ``snapshotAsMesh`` -> ``mesh mesh:`` -> ``meshop.attach``로 **합본 노드 1개**를 만들어 넣는다.
- **빗나간 레이도 ``dist = Infinity`` 히트를 돌려준다.** 유한 거리이면서 시작점 오프셋보다 먼 히트만
  막힘으로 센다. 히트는 진행 방향(양수 거리)만, 거리는 월드 단위, 뒷면도 맞는다(doubleSided).
- ``intersectRayEx``는 Skin 노드에서 히트를 주지 않았다(1,600레이 x 4노드 0건) - 쓰지 않는다.
- 레이 루프는 MAXScript 함수 하나에서 돈다(조기 종료 포함). 그리드 해상도 100에서 약 1.5만 레이/초.

## 인덱스 규약

결과 면 인덱스는 **평가 형상(모디파이어 스택 결과)의 폴리곤 인덱스, 1-based**다. 대상의 스택 결과는
폴리곤 메쉬여야 한다(``polyop``이 노드에 대해 동작해야 한다). 모디파이어가 토폴로지를 바꾸지 않으면
baseObject 인덱스와 같다 - 그 확인과 삭제는 호출자의 몫이다.

## 호출 조건 - Modify 패널 상태

Modify 패널이 스택 **아래** 레벨(예: Skin 밑 baseObject의 서브오브젝트)을 보고 있고 Show End Result가
꺼져 있으면 ``snapshotAsMesh``가 스택 끝이 아니라 **그 레벨의 형상**을 준다(2026-10-20 실측: 포즈 상태에서
보임 면 38 -> 12). 가리는 오브젝트는 스택 끝으로 읽히므로 대상만 어긋난다. 이 모듈은 UI 상태를 바꾸지
않는다 - **호출자가 패널을 벗어난 상태(예: ``max create mode``)에서 부른다.**
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pymxs
from pymxs import runtime as rt

from pyjallib.max import clipMesh as cm
from pyjallib.max import polygonMath as pm
from pyjallib.max import uvMask
from pyjallib.max.polygonMath import OccludedFaceResult, ProgressCallback, Vec3

_MXS_DEFINITIONS = """
fn pyjal_polygon_mesh_data node = (
    local m = snapshotAsMesh node
    local nv = m.numverts
    local pts = for i = 1 to nv collect getVert m i
    local nrms = for i = 1 to nv collect (getNormal m i)
    local faces = for f = 1 to (polyop.getNumFaces node) collect (polyop.getFaceVerts node f)
    local pv = polyop.getNumVerts node
    local tris = for t = 1 to m.numfaces collect (getFace m t)
    #(pts, nrms, faces, nv, pv, tris)
)
fn pyjal_polygon_map_data node ch = (
    if not (polyop.getMapSupport node ch) then #(false, #(), #())
    else (
        local nmv = polyop.getNumMapVerts node ch
        local mv = for i = 1 to nmv collect (polyop.getMapVert node ch i)
        local nf = polyop.getNumFaces node
        local mf = for f = 1 to nf collect (polyop.getMapFace node ch f)
        #(true, mv, mf)
    )
)
fn pyjal_polygon_merge nodes tmpName = (
    local tmp = mesh mesh:(snapshotAsMesh nodes[1])
    tmp.name = tmpName
    for i = 2 to nodes.count do (
        local part = mesh mesh:(snapshotAsMesh nodes[i])
        part.name = tmpName
        meshop.attach tmp part
    )
    tmp.isHidden = true
    tmp
)
fn pyjal_polygon_grid node resolution = (
    local rm = RayMeshGridIntersect()
    rm.Initialize resolution
    rm.addNode node
    rm.buildGrid()
    rm
)
fn pyjal_polygon_cast rm pts nrms dirsLocal eps = (
    local res = #()
    for i = 1 to pts.count do (
        local n = normalize nrms[i]
        local up = if (abs n.z) < 0.9 then [0,0,1] else [1,0,0]
        local t = normalize (cross up n)
        local b = cross n t
        local p = pts[i] + n * eps
        local escaped = false
        for k = 1 to dirsLocal.count while not escaped do (
            local d = dirsLocal[k]
            local w = t * d.x + b * d.y + n * d.z
            local cnt = rm.intersectRay p w true
            local blocked = false
            for h = 1 to cnt while not blocked do (
                local dist = rm.getHitDist h
                if dist > eps and dist < 1.0e30 do blocked = true
            )
            if not blocked do escaped = true
        )
        append res escaped
    )
    res
)
fn pyjal_clip_tri_data node = (
    local m = snapshotAsMesh node
    local nv = m.numverts
    local nf = m.numfaces
    local vs = #()
    if nv > 0 do vs[nv * 3] = 0.0
    for i = 1 to nv do (
        local p = getVert m i
        vs[i * 3 - 2] = p.x
        vs[i * 3 - 1] = p.y
        vs[i * 3] = p.z
    )
    local fs = #()
    if nf > 0 do fs[nf * 3] = 0
    for i = 1 to nf do (
        local f = getFace m i
        fs[i * 3 - 2] = f.x as integer
        fs[i * 3 - 1] = f.y as integer
        fs[i * 3] = f.z as integer
    )
    #(vs, fs)
)
fn pyjal_clip_make_mesh nm vs fs = (
    local nv = vs.count / 3
    local nf = fs.count / 3
    local pts = for i = 1 to nv collect [vs[i * 3 - 2], vs[i * 3 - 1], vs[i * 3]]
    local tris = for i = 1 to nf collect [fs[i * 3 - 2], fs[i * 3 - 1], fs[i * 3]]
    local m = mesh vertices:pts faces:tris name:nm
    m.wireColor = color 255 128 0
    m
)
fn pyjal_clip_finalize node = (
    convertToMesh node
    meshop.setMapSupport node 1 true
    meshop.setNumMapVerts node 1 1
    meshop.setMapVert node 1 1 [1, 1, 0]
    for i = 1 to node.numfaces do meshop.setMapFace node 1 i [1, 1, 1]
    update node
    node.numfaces
)
"""

_TEMP_NODE_NAME = "PyJalPolygon_tmpOccluder"

#: 클립 메쉬 생성 경로(``ClipMeshResult.algorithm``).
ALGORITHM_VOXEL = "voxel"
ALGORITHM_ALPHA_WRAP = "alphaWrap"


@dataclass
class ClipMeshResult:
    """``Polygon.build_clip_mesh`` 결과.

    Attributes:
        node: 만든 클립 메쉬 노드(씬에 남는다 - 지우는 것은 호출자의 몫)
        name: 노드 이름
        voxelTriangles: 감축 전 삼각형 수(복셀 경로 = 복셀 겉면, Alpha Wrap 경로 = 감싼 메쉬 W)
        triangles: 최종 삼각형 수
        faceBudget: 목표 삼각형 수(0이면 감축 안 함). 남길 비율을 줬으면 그 환산값
        coverCounts: 덮는 면 분류별 삼각형 수(``clipMesh.COVER_*``)
        stats: 부피 통계(복셀: 사면체·점유 칸·공동 메움·비다양체 보정 / Alpha Wrap: 기둥·제거 횟수·남은 과다·``wrap_*``)
        check: 최종 메쉬의 엔진 판정(``clipMesh.ClipCheck``)
        timings: 단계별 초
        reasons: 실패 사유(감축 무동작 등). 비어 있고 ``check.passed()``면 통과
        decimate: 감축 통계(``clipMesh.DecimateStats.as_dict()``, 감축하지 않았으면 None) - 목표 미달은 실패가 아니라 기록이다
        algorithm: ``ALGORITHM_VOXEL`` 또는 ``ALGORITHM_ALPHA_WRAP``
        keepRatio: 요청한 남길 비율 %(절대값 목표로 불렀으면 None)
        iterations: Alpha Wrap 과다 반복 제거 회차별 ``{prisms, triangles, over}``(복셀 경로는 빈 목록)
    """

    node: Any
    name: str
    voxelTriangles: int
    triangles: int
    faceBudget: int
    coverCounts: Dict[str, int]
    stats: Dict[str, int]
    check: cm.ClipCheck
    timings: Dict[str, float] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    decimate: Optional[Dict[str, Any]] = None
    algorithm: str = ALGORITHM_VOXEL
    keepRatio: Optional[float] = None
    iterations: List[Dict[str, int]] = field(default_factory=list)

    def passed(self) -> bool:
        """닫힘 + 과다 클립 0 + 실패 사유 없음 (fail-closed 축)."""
        return not self.reasons and self.check.passed()

    def summary(self) -> Dict[str, Any]:
        """로그·리포트용 요약(대상별 |E|·|C|·과다·과소, 덮는 메쉬 포함률 ``guardRatio`` - 기록 축)."""
        targets = {}
        for name, t in self.check.targets.items():
            targets[name] = {
                "vertices": t.vertexCount,
                "expected": len(t.expected or ()),
                "clipped": len(t.clipped),
                "over": len(t.over),
                "under": len(t.under),
                "underRatio": round(t.under_ratio(), 4),
                "overDistanceMax": round(t.overDistanceMax, 3),
                "facesAll": t.facesAll,
                "facesOne": t.facesOne,
            }
        return {
            "name": self.name,
            "algorithm": self.algorithm,
            "keepRatio": self.keepRatio,
            "iterations": [dict(it) for it in self.iterations],
            "passed": self.passed(),
            "closed": self.check.closed,
            "voxelTriangles": self.voxelTriangles,
            "triangles": self.triangles,
            "faceBudget": self.faceBudget,
            "coverCounts": dict(self.coverCounts),
            "stats": dict(self.stats),
            "guardRatio": round(self.check.guard_ratio(), 4),
            "targets": targets,
            "reasons": list(self.reasons),
            "decimate": dict(self.decimate) if self.decimate else None,
            "timings": {k: round(v, 3) for k, v in self.timings.items()},
        }


class Polygon:
    """메쉬 폴리곤 질의 서비스(가려진 면 추출).

    Attributes:
        DEFAULT_RAY_COUNT: 샘플당 레이 수 기본값
        DEFAULT_CONE_ANGLE: 레이 반원뿔 반각(도) 기본값 - 90은 반구
        DEFAULT_EPSILON: 레이 시작점 법선 오프셋 = 최소 히트 거리(씬 단위)
        GRID_RESOLUTION: ``RayMeshGridIntersect.Initialize`` 해상도
    """

    DEFAULT_RAY_COUNT = 32
    DEFAULT_CONE_ANGLE = 90.0
    DEFAULT_EPSILON = 0.01
    GRID_RESOLUTION = 100

    def __init__(self, inLogger: Optional[Any] = None) -> None:
        """서비스를 만든다. MAXScript 함수 정의는 첫 사용 시 한 번 등록한다.

        Args:
            inLogger: ``info``/``warning`` 메서드를 가진 로거. None이면 기록하지 않는다
        """
        self._logger = inLogger
        self._fnReady = False

    # -----------------------------------------------------------------
    # 내부 헬퍼
    # -----------------------------------------------------------------

    def _ensure_functions(self) -> None:
        if not self._fnReady:
            rt.execute(_MXS_DEFINITIONS)
            self._fnReady = True

    def _log(self, inLevel: str, inMessage: str) -> None:
        if self._logger is not None:
            getattr(self._logger, inLevel)(inMessage)

    @staticmethod
    def _handle(inNode: Any) -> int:
        return int(rt.getHandleByAnim(inNode))

    @staticmethod
    def _is_geometry(inNode: Any) -> bool:
        try:
            return rt.isValidNode(inNode) and rt.superClassOf(inNode) == rt.GeometryClass
        except Exception:  # noqa: BLE001 - 판정 불가는 지오메트리 아님으로 본다
            return False

    def _read_target(self, inTarget: Any):
        """평가 형상의 버텍스(월드)·법선·면·삼각분할(0-based)을 읽는다.

        삼각분할은 레이 그리드가 실제로 보는 표면이다 - 면 대표점을 그 위에 두는 데 쓴다
        (``polygonMath.face_surface_samples``).
        """
        try:
            data = rt.pyjal_polygon_mesh_data(inTarget)
        except RuntimeError as exc:
            raise ValueError(
                f"'{inTarget.name}'의 스택 결과가 폴리곤 메쉬가 아니라 면을 읽을 수 없다: {exc}"
            ) from exc
        meshVerts, polyVerts = int(data[3]), int(data[4])
        if meshVerts != polyVerts:
            raise ValueError(
                f"'{inTarget.name}': 메쉬 스냅샷 버텍스 수({meshVerts})와 폴리곤 버텍스 수({polyVerts})가 달라 "
                "좌표를 면에 맞출 수 없다"
            )
        verts: List[Vec3] = [(float(p.x), float(p.y), float(p.z)) for p in data[0]]
        normals: List[Vec3] = [(float(p.x), float(p.y), float(p.z)) for p in data[1]]
        faces: List[List[int]] = [[int(v) - 1 for v in fv] for fv in data[2]]
        triangles: List[List[int]] = [[int(t.x) - 1, int(t.y) - 1, int(t.z) - 1] for t in data[5]]
        return verts, normals, faces, triangles

    def _make_query(self, inGrid: Any, inLocalDirs: Any, inEpsilon: float) -> pm.SampleQuery:
        def _query(inPoints: Sequence[Vec3], inNormals: Sequence[Vec3]) -> List[bool]:
            pts = rt.Array(*[rt.Point3(p[0], p[1], p[2]) for p in inPoints])
            nrms = rt.Array(*[rt.Point3(n[0], n[1], n[2]) for n in inNormals])
            return [bool(x) for x in rt.pyjal_polygon_cast(inGrid, pts, nrms, inLocalDirs, inEpsilon)]

        return _query

    @staticmethod
    def _to_one_based(inResult: OccludedFaceResult) -> OccludedFaceResult:
        def shift(inList: List[int]) -> List[int]:
            return [i + 1 for i in inList]

        return OccludedFaceResult(
            faceCount=inResult.faceCount,
            sampleCount=inResult.sampleCount,
            test1BlockedSamples=inResult.test1BlockedSamples,
            selfBlockedSamples=inResult.selfBlockedSamples,
            visibleFaces=shift(inResult.visibleFaces),
            selfOccludedFaces=shift(inResult.selfOccludedFaces),
            marginKeptFaces=shift(inResult.marginKeptFaces),
            occludedFaces=shift(inResult.occludedFaces),
        )

    # -----------------------------------------------------------------
    # 공개 API
    # -----------------------------------------------------------------

    def find_occluded_faces(
        self,
        inTarget: Any,
        inOccluders: Sequence[Any],
        inRayCount: int = DEFAULT_RAY_COUNT,
        inConeAngle: float = DEFAULT_CONE_ANGLE,
        inMargin: float = 0.0,
        inProgressCallback: Optional[ProgressCallback] = None,
        inEpsilon: float = DEFAULT_EPSILON,
    ) -> OccludedFaceResult:
        """대상에서 가리는 오브젝트들에 가려진 면을 찾는다(씬 무변경).

        판정 정의는 ``polygonMath`` 모듈 docstring의 두 시험이다. 시험 1 차폐물 = 대상 + 가리는 오브젝트,
        시험 2 차폐물 = 대상만. 모든 좌표는 현재 시점의 스택 평가 결과(월드)다.

        Args:
            inTarget: 면을 판정할 노드(스택 결과가 폴리곤 메쉬)
            inOccluders: 가리는 노드 목록(1개 이상, 대상과 겹치면 안 된다)
            inRayCount: 샘플당 레이 수
            inConeAngle: 레이 반원뿔 반각(도, 0 초과 90 이하)
            inMargin: 여유 거리(씬 단위). 보임 면 버텍스로부터 이 거리 안의 가려진 면은 보존한다
            inProgressCallback: (작업명, 현재, 전체) 콜백
            inEpsilon: 레이 시작점 오프셋 = 최소 히트 거리

        Returns:
            ``OccludedFaceResult`` - 면 인덱스는 평가 형상 기준 **1-based**

        Raises:
            ValueError: 노드가 유효한 지오메트리가 아님, 가리개가 없음, 대상과 가리개가 겹침,
                스택 결과가 폴리곤 메쉬가 아님, 파라미터 범위 밖
        """
        if not self._is_geometry(inTarget):
            raise ValueError("대상이 유효한 지오메트리 노드가 아니다")
        occluders = list(inOccluders)
        if not occluders:
            raise ValueError("가리는 오브젝트가 1개 이상 필요하다")
        targetHandle = self._handle(inTarget)
        seen = set()
        for node in occluders:
            if not self._is_geometry(node):
                raise ValueError("가리는 오브젝트 중 유효한 지오메트리 노드가 아닌 것이 있다")
            handle = self._handle(node)
            if handle == targetHandle:
                raise ValueError(f"'{inTarget.name}'이(가) 대상과 가리는 오브젝트 양쪽에 있다")
            if handle in seen:
                raise ValueError(f"가리는 오브젝트 '{node.name}'이(가) 중복됐다")
            seen.add(handle)
        localDirs = pm.cone_directions(inRayCount, inConeAngle)
        if inMargin < 0.0:
            raise ValueError(f"여유 거리는 0 이상이어야 한다: {inMargin}")

        self._ensure_functions()
        verts, normals, faces, triangles = self._read_target(inTarget)
        if not faces:
            return OccludedFaceResult()

        saveRequired = bool(rt.getSaveRequired())
        merged = None
        gridAll = None
        gridSelf = None
        try:
            with pymxs.undo(False):
                merged = rt.pyjal_polygon_merge(rt.Array(inTarget, *occluders), _TEMP_NODE_NAME)
            gridAll = rt.pyjal_polygon_grid(merged, self.GRID_RESOLUTION)
            gridSelf = rt.pyjal_polygon_grid(inTarget, self.GRID_RESOLUTION)
            mxDirs = rt.Array(*[rt.Point3(d[0], d[1], d[2]) for d in localDirs])
            result = pm.find_occluded_faces(
                verts,
                faces,
                normals,
                self._make_query(gridAll, mxDirs, inEpsilon),
                self._make_query(gridSelf, mxDirs, inEpsilon),
                inMargin,
                inProgressCallback=inProgressCallback,
                inTriangles=triangles,
            )
        finally:
            for grid in (gridAll, gridSelf):
                if grid is not None:
                    try:
                        grid.free()
                    except Exception:  # noqa: BLE001 - 정리 실패가 원래 예외를 덮지 않게 한다
                        pass
            if merged is not None and rt.isValidNode(merged):
                with pymxs.undo(False):
                    rt.delete(merged)
            rt.setSaveRequired(saveRequired)

        oneBased = self._to_one_based(result)
        self._log(
            "info",
            f"[Polygon] '{inTarget.name}' 가려진 면 판정 (가리개 {[str(n.name) for n in occluders]}, "
            f"N={inRayCount}, θ={inConeAngle}, 여유={inMargin}): {oneBased.counts()}",
        )
        return oneBased

    # -----------------------------------------------------------------
    # UV 마스크 (2026-10-21 가산 - 순수 규칙은 pyjallib.max.uvMask)
    # -----------------------------------------------------------------

    def read_map_faces(self, inNode: Any, inChannel: int = 1) -> Tuple[List[Tuple[float, float]], List[List[int]]]:
        """맵 채널의 맵 버텍스 (u, v)와 면별 맵 버텍스 인덱스(**0-based**)를 벌크로 읽는다(씬 무변경).

        MAXScript 함수 하나가 ``polyop.getMapVert``/``getMapFace``를 돌려 Python 루프의 IPC를 피한다.
        면 순서는 ``polyop`` 폴리곤 인덱스와 같다(``find_occluded_faces`` 결과의 1-based 인덱스 - 1).

        Args:
            inNode: 스택 결과가 폴리곤 메쉬인 지오메트리 노드
            inChannel: 맵 채널(기본 1)

        Returns:
            (맵 버텍스 목록, 면별 맵 버텍스 인덱스 목록)

        Raises:
            ValueError: 지오메트리가 아님, 스택 결과가 폴리곤이 아님, 맵 채널 미지원
        """
        if not self._is_geometry(inNode):
            raise ValueError("대상이 유효한 지오메트리 노드가 아니다")
        self._ensure_functions()
        try:
            data = rt.pyjal_polygon_map_data(inNode, int(inChannel))
        except RuntimeError as exc:
            raise ValueError(f"'{inNode.name}'의 스택 결과가 폴리곤 메쉬가 아니라 맵 면을 읽을 수 없다: {exc}") from exc
        if not bool(data[0]):
            raise ValueError(f"'{inNode.name}'에 맵 채널 {inChannel}이(가) 없다")
        mapVerts = [(float(p.x), float(p.y)) for p in data[1]]
        mapFaces = [[int(i) - 1 for i in face] for face in data[2]]
        return mapVerts, mapFaces

    def bake_face_mask(
        self,
        inNode: Any,
        inFaces: Sequence[int],
        inSize: int,
        inPath: str,
        inChannel: int = 1,
        inPadding: int = 0,
        inFill: int = uvMask.DEFAULT_FILL,
        inValue: int = uvMask.DEFAULT_VALUE,
    ) -> Dict[str, Any]:
        """면 집합을 대상 UV 공간에 래스터화해 TGA로 저장한다(씬 무변경).

        Args:
            inNode: 대상 노드
            inFaces: 칠할 면 인덱스(**1-based**, ``find_occluded_faces``의 ``occludedFaces`` 그대로)
            inSize: 정사각 해상도
            inPath: 출력 TGA 경로(부모 폴더는 만든다)
            inChannel: 맵 채널
            inPadding: 칠한 값의 팽창 픽셀 수
            inFill: 바탕값(기본 255)
            inValue: 칠할 값(기본 0)

        Returns:
            ``{"path", "width", "height", "faceCount", "paintedPixels", "zeroPixelFaces"}``

        Raises:
            ValueError: ``read_map_faces``의 사유, 면 인덱스 범위 밖, 크기·값 범위 밖
            OSError: 파일을 쓸 수 없음
        """
        mapVerts, mapFaces = self.read_map_faces(inNode, inChannel)
        faces0 = [int(f) - 1 for f in inFaces]
        image, stats = uvMask.bake_face_mask(mapVerts, mapFaces, faces0, inSize, inPadding, inFill, inValue)
        uvMask.write_tga(inPath, image)
        result: Dict[str, Any] = {"path": inPath, "width": image.width, "height": image.height}
        result.update(stats.as_dict())
        self._log(
            "info",
            f"[Polygon] '{inNode.name}' UV 마스크 {image.width}x{image.height}: 면 {stats.faceCount}, "
            f"칠한 픽셀 {stats.paintedPixels}, 0픽셀 면 {stats.zeroPixelFaces} -> {inPath}",
        )
        return result

    # -----------------------------------------------------------------
    # 클립 메쉬 (2026-10-22 가산 - 순수 규칙은 pyjallib.max.clipMesh)
    # -----------------------------------------------------------------

    def read_world_triangles(self, inNode: Any) -> Tuple[List[Vec3], List[Tuple[int, int, int]]]:
        """노드의 평가된 월드 삼각형 메쉬를 벌크로 읽는다(``snapshotAsMesh``, 0-based, 씬 무변경).

        Modify 패널 함정(모듈 docstring "호출 조건")은 여기에도 그대로 걸린다 - 호출자가 패널을 벗어나 부른다.

        Args:
            inNode: 지오메트리 노드

        Returns:
            (버텍스 월드 좌표, 삼각형)

        Raises:
            ValueError: 지오메트리 노드가 아님
        """
        if not self._is_geometry(inNode):
            raise ValueError("유효한 지오메트리 노드가 아니다")
        self._ensure_functions()
        data = rt.pyjal_clip_tri_data(inNode)
        flat = list(data[0])
        idx = list(data[1])
        verts = [(float(flat[i]), float(flat[i + 1]), float(flat[i + 2])) for i in range(0, len(flat), 3)]
        tris = [(int(idx[i]) - 1, int(idx[i + 1]) - 1, int(idx[i + 2]) - 1) for i in range(0, len(idx), 3)]
        return verts, tris

    def _check_node_sets(self, inOccluders: Sequence[Any], inTargets: Sequence[Any]) -> None:
        if not inOccluders:
            raise ValueError("가리는 오브젝트가 1개 이상 필요하다")
        if not inTargets:
            raise ValueError("대상이 1개 이상 필요하다")
        seen: Dict[int, str] = {}
        for role, nodes in (("가리는 오브젝트", inOccluders), ("대상", inTargets)):
            for node in nodes:
                if not self._is_geometry(node):
                    raise ValueError(f"{role} 중 유효한 지오메트리 노드가 아닌 것이 있다")
                handle = self._handle(node)
                if handle in seen:
                    raise ValueError(f"'{node.name}'이(가) {seen[handle]}와 {role}에 중복됐다")
                seen[handle] = role

    @staticmethod
    def _target_names(inTargets: Sequence[Any]) -> List[str]:
        names: List[str] = []
        for node in inTargets:
            base = str(node.name)
            name = base
            n = 2
            while name in names:
                name = f"{base}#{n}"
                n += 1
            names.append(name)
        return names

    def build_clip_mesh(
        self,
        inOccluders: Sequence[Any],
        inTargets: Sequence[Any],
        inPush: float,
        inVoxelSize: float,
        inInset: float,
        inInnerDepth: float,
        inMaxHeight: float,
        inFaceBudget: int,
        inName: Optional[str] = None,
        inProgressCallback: Optional[ProgressCallback] = None,
        inMaxShrink: float = float("inf"),
        inKeepRatio: Optional[float] = None,
    ) -> ClipMeshResult:
        """덮는 오브젝트로 닫힌 클립 메쉬 노드를 만들고 엔진 규칙으로 판정한다(원본 무변경).

        부피 정의·이산화·감축은 ``clipMesh`` 모듈 docstring(감축 = ``decimate_clip_volume``, 보호된 성장). 노드를 만든 뒤
        결과 메쉬를 **씬에서 다시 읽어** 판정한다 - 노드 왕복이 좌표·면을 바꾸지 않았는지까지 포함해, 벽끼리 지나쳐 홀짝이
        깨진 경우도 여기서 드러난다. 감축을 요청했는데 붕괴가 0번이면 실패 사유로 남긴다(목표 미달 자체는 기록). 노드는 통과
        여부와 무관하게 씬에 남는다(눈으로 보게).

        Args:
            inOccluders: 덮는 노드 목록(옷)
            inTargets: 덮히는 노드 목록(바디 등) - 표면은 합쳐 하나로 본다
            inPush: 푸쉬 거리 d
            inVoxelSize: 복셀 크기 s
            inInset: 경계 물림 거리 m
            inInnerDepth: 바디 안쪽 깊이 T
            inMaxHeight: 덮임 최대 거리 Hmax
            inFaceBudget: 목표 삼각형 수(0이면 감축하지 않는다)
            inName: 노드 이름. None이면 ``{첫 덮는 노드}_Clip``
            inProgressCallback: (작업명, 현재, 전체) 콜백
            inMaxShrink: 감축 붕괴 하나의 최대 이동 거리(기본 제한 없음 - 과다·과소는 보호된 성장이 버텍스 단위로 막는다)
            inKeepRatio: 남길 비율 %(0 초과 100 이하). 주면 ``inFaceBudget`` 대신 감축 전 삼각형 수로 목표를 정한다
                (``clipMesh.face_budget_from_ratio`` - 100이면 감축 안 함). None이면 ``inFaceBudget`` 그대로(기존 동작)

        Returns:
            ``ClipMeshResult``

        Raises:
            ValueError: 노드가 지오메트리가 아님·비었음·중복, 파라미터 범위 밖(``clipMesh.build_clip_volume``, 비율), 덮는 면이
                없어 부피가 빔(노드를 만들지 않는다)
        """
        occluders = list(inOccluders)
        targets = list(inTargets)
        self._check_node_sets(occluders, targets)
        if inFaceBudget < 0:
            raise ValueError(f"목표 삼각형 수는 0 이상이어야 한다: {inFaceBudget}")
        if inKeepRatio is not None:
            cm.face_budget_from_ratio(1, inKeepRatio)  # 무거운 단계 전에 범위를 거부한다
        timings: Dict[str, float] = {}
        t0 = time.perf_counter()
        occMeshes = [self.read_world_triangles(n) for n in occluders]
        names = self._target_names(targets)
        tgtMeshes = {name: self.read_world_triangles(n) for name, n in zip(names, targets)}
        timings["read"] = time.perf_counter() - t0

        volume = cm.build_clip_volume(
            occMeshes, tgtMeshes, inPush, inVoxelSize, inInset, inInnerDepth, inMaxHeight,
            inProgressCallback=inProgressCallback,
        )
        budget = inFaceBudget if inKeepRatio is None else cm.face_budget_from_ratio(len(volume.tris), inKeepRatio)
        result = self._finish_clip_mesh(
            volume, tgtMeshes, timings, inName or f"{occluders[0].name}_Clip", budget, inMaxShrink,
            ALGORITHM_VOXEL, inKeepRatio,
        )
        summary = result.summary()
        self._log(
            "info",
            f"[Polygon] 클립 메쉬 '{result.name}' (가리개 {[str(n.name) for n in occluders]}, 대상 {names}, "
            f"d={inPush}, s={inVoxelSize}, m={inInset}, T={inInnerDepth}, Hmax={inMaxHeight}, F={budget}, "
            f"r={inKeepRatio}): passed={summary['passed']} closed={summary['closed']} "
            f"tris {summary['voxelTriangles']}->{summary['triangles']} targets={summary['targets']} reasons={summary['reasons']}",
        )
        return result

    def build_clip_mesh_alpha(
        self,
        inOccluders: Sequence[Any],
        inTargets: Sequence[Any],
        inPush: float,
        inInset: float,
        inInnerDepth: float,
        inMaxHeight: float,
        inAlpha: float,
        inOffset: float,
        inPruneMargin: float,
        inMaxPruneIterations: int,
        inKeepRatio: float,
        inName: Optional[str] = None,
        inProgressCallback: Optional[ProgressCallback] = None,
        inMaxShrink: float = float("inf"),
    ) -> ClipMeshResult:
        """덮는 오브젝트의 기둥 부피를 **Alpha Wrap으로 감싸** 닫힌 클립 메쉬 노드를 만들고 판정한다(원본 무변경).

        ``build_clip_mesh``와 부피 정의·기대 집합·감축·노드 규격·판정이 같고 복셀화 대신 감싸기를 쓴다(``clipMesh`` 모듈 docstring
        "Alpha Wrap 경로"). 감싸기가 삼킨 보호 점은 과다 반복 제거로 없앤다 - 그 자리 기대 집합은 과소가 된다(기록). 반복 제거
        뒤에도 남은 과다는 판정이 fail-closed로 잡는다(``passed`` False). 감싸기는 ``pyjallib.native.alpha_wrap``(C++)이다.

        Args:
            inOccluders: 덮는 노드 목록(옷)
            inTargets: 덮히는 노드 목록(바디 등)
            inPush: 푸쉬 거리 d
            inInset: 경계 물림 거리 m
            inInnerDepth: 바디 안쪽 깊이 T
            inMaxHeight: 덮임 최대 거리 Hmax
            inAlpha: 감싸는 공 반지름(> 0, 씬 단위) - 이보다 좁은 틈은 메워진다
            inOffset: 기둥에서 띄우는 거리(> 0)
            inPruneMargin: 반복 제거 반경 여유(>= 0) - 반경 = alpha + offset + 여유
            inMaxPruneIterations: 최대 제거 횟수(>= 0)
            inKeepRatio: 남길 비율 %(0 초과 100 이하, 감싼 메쉬 삼각형 수 기준, 100이면 감축 안 함)
            inName: 노드 이름. None이면 ``{첫 덮는 노드}_Clip``
            inProgressCallback: (작업명, 현재, 전체) 콜백
            inMaxShrink: 감축 붕괴 하나의 최대 이동 거리

        Returns:
            ``ClipMeshResult`` (``algorithm == ALGORITHM_ALPHA_WRAP``, ``iterations``에 반복 제거 회차)

        Raises:
            RuntimeError: ``pyjallib.native``의 Alpha Wrap 모듈이 없음(사유 포함, 노드를 만들지 않는다)
            ValueError: 노드 집합·파라미터 범위 밖, 덮는 면이 없어 부피가 빔(노드를 만들지 않는다)
        """
        from pyjallib import native

        if not native.HAS_ALPHA_WRAP:
            raise RuntimeError(f"Alpha Wrap 네이티브 모듈을 쓸 수 없다: {native.ALPHA_WRAP_IMPORT_ERROR}")
        occluders = list(inOccluders)
        targets = list(inTargets)
        self._check_node_sets(occluders, targets)
        cm.face_budget_from_ratio(1, inKeepRatio)
        if inAlpha <= 0.0 or inOffset <= 0.0 or inPruneMargin < 0.0 or inMaxPruneIterations < 0:
            raise ValueError(
                f"파라미터 범위 밖: alpha={inAlpha}, offset={inOffset}, margin={inPruneMargin}, "
                f"iterations={inMaxPruneIterations}"
            )
        timings: Dict[str, float] = {}
        t0 = time.perf_counter()
        occMeshes = [self.read_world_triangles(n) for n in occluders]
        names = self._target_names(targets)
        tgtMeshes = {name: self.read_world_triangles(n) for name, n in zip(names, targets)}
        timings["read"] = time.perf_counter() - t0

        def _progress(inName: str, inStep: int, _inTotal: int) -> None:
            if inProgressCallback is not None:
                inProgressCallback(inName, inStep, 5)

        prism = cm.build_prism_volume(
            occMeshes, tgtMeshes, inPush, inInset, inInnerDepth, inMaxHeight, inProgressCallback=_progress
        )
        _progress("wrap", 4, 5)
        volume = cm.wrap_clip_volume(prism, inAlpha, inOffset, native.alpha_wrap, inPruneMargin, inMaxPruneIterations)
        _progress("done", 5, 5)
        budget = cm.face_budget_from_ratio(len(volume.tris), inKeepRatio)
        result = self._finish_clip_mesh(
            volume, tgtMeshes, timings, inName or f"{occluders[0].name}_Clip", budget, inMaxShrink,
            ALGORITHM_ALPHA_WRAP, inKeepRatio,
        )
        summary = result.summary()
        self._log(
            "info",
            f"[Polygon] 클립 메쉬(Alpha Wrap) '{result.name}' (가리개 {[str(n.name) for n in occluders]}, 대상 {names}, "
            f"d={inPush}, m={inInset}, T={inInnerDepth}, Hmax={inMaxHeight}, alpha={inAlpha}, offset={inOffset}, "
            f"margin={inPruneMargin}, r={inKeepRatio}): passed={summary['passed']} closed={summary['closed']} "
            f"tris {summary['voxelTriangles']}->{summary['triangles']} iterations={summary['iterations']} "
            f"targets={summary['targets']} reasons={summary['reasons']}",
        )
        return result

    def _finish_clip_mesh(
        self,
        inVolume: cm.ClipVolume,
        inTargetMeshes: Dict[str, Any],
        inTimings: Dict[str, float],
        inNodeName: str,
        inFaceBudget: int,
        inMaxShrink: float,
        inAlgorithm: str,
        inKeepRatio: Optional[float],
    ) -> ClipMeshResult:
        """감축 -> 노드 생성 -> 씬에서 다시 읽어 판정(두 경로 공통). 빈 부피는 노드를 만들지 않고 ValueError."""
        timings = inTimings
        timings.update(inVolume.timings)
        reasons: List[str] = []
        if not inVolume.tris:
            # 빈 메쉬 노드는 만들 의미가 없다 - 덮는 면 분류를 사유에 실어 던진다(관통·Hmax 초과·경계 물림으로 전부 빠진 경우)
            raise ValueError(f"덮는 면이 없어 클립 부피가 비었다(덮는 면 분류 {inVolume.coverCounts})")

        meshVerts, meshTris = inVolume.verts, inVolume.tris
        decimateStats = None
        beforeTris = len(inVolume.tris)
        if inFaceBudget > 0 and beforeTris > inFaceBudget:
            meshVerts, meshTris, stats = cm.decimate_clip_volume(inVolume, inTargetMeshes, inFaceBudget, inMaxShrink)
            decimateStats = stats.as_dict()
            timings["decimate"] = stats.seconds
            if stats.collapses == 0:
                reasons.append(f"감축이 동작하지 않았다(삼각형 {beforeTris}, 목표 {inFaceBudget})")

        node = None
        try:
            t0 = time.perf_counter()
            flatVerts = [c for p in meshVerts for c in p]
            flatTris = [i + 1 for t in meshTris for i in t]
            node = rt.pyjal_clip_make_mesh(inNodeName, rt.Array(*flatVerts), rt.Array(*flatTris))
            timings["makeNode"] = time.perf_counter() - t0
            rt.pyjal_clip_finalize(node)
            t0 = time.perf_counter()
            clipVerts, clipTris = self.read_world_triangles(node)
            check = cm.verify_clip(clipVerts, clipTris, inTargetMeshes, inVolume.expected, inVolume.guardPoints)
            timings["verify"] = time.perf_counter() - t0
        except Exception:
            if node is not None and rt.isValidNode(node):
                rt.delete(node)
            raise

        return ClipMeshResult(
            node=node,
            name=str(node.name),
            voxelTriangles=beforeTris,
            triangles=len(clipTris),
            faceBudget=int(inFaceBudget),
            coverCounts=dict(inVolume.coverCounts),
            stats=dict(inVolume.stats),
            check=check,
            timings=timings,
            reasons=reasons,
            decimate=decimateStats,
            algorithm=inAlgorithm,
            keepRatio=inKeepRatio,
            iterations=[dict(it) for it in inVolume.iterations],
        )

    def classify_clip(self, inClipNode: Any, inTargets: Sequence[Any]) -> cm.ClipCheck:
        """기존 클립 메쉬(수작업 포함)를 엔진 규칙으로 판정한다(기대 집합 없이 C·닫힘·면 제거 수, 씬 무변경).

        Args:
            inClipNode: 클립 메쉬 노드
            inTargets: 판정할 대상 노드 목록

        Returns:
            ``clipMesh.ClipCheck`` (대상 이름 = 노드 이름)

        Raises:
            ValueError: 노드가 지오메트리가 아님·대상이 비었음
        """
        targets = list(inTargets)
        if not targets:
            raise ValueError("대상이 1개 이상 필요하다")
        clipVerts, clipTris = self.read_world_triangles(inClipNode)
        names = self._target_names(targets)
        tgtMeshes = {name: self.read_world_triangles(n) for name, n in zip(names, targets)}
        return cm.verify_clip(clipVerts, clipTris, tgtMeshes, None)
