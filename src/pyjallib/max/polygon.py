#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""폴리곤 모듈 - 3ds Max 메쉬 폴리곤 질의.

현재 기능: **다른 오브젝트에 가려진 면 추출**(``Polygon.find_occluded_faces``). 판정 규칙은 순수 모듈
``polygonMath``에 있고, 이 어댑터는 씬에서 재료(평가 형상의 버텍스·면·법선)를 읽고 레이 질의를 만든다.
**씬을 바꾸지 않는다** - 레이 그리드용 임시 노드는 undo 기록 밖에서 만들고 ``finally``에서 지우며,
씬 저장 필요 플래그도 호출 전 값으로 되돌린다.

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

from typing import Any, Dict, List, Optional, Sequence, Tuple

import pymxs
from pymxs import runtime as rt

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
"""

_TEMP_NODE_NAME = "PyJalPolygon_tmpOccluder"


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
