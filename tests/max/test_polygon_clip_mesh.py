#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Polygon.build_clip_mesh / classify_clip 테스트 - 3ds Max 환경에서 실행 (Type C).

픽스처: ``_legPantsFixture``(다리 + 엉덩이·발 박스 + 양끝이 묻힌 관 바지)를 import로 쓴다. 클립 메쉬는 바지
버텍스가 관 가운데에도 있어야 덮는 면이 생기므로 높이 분할 17(2 cm)로 만든다.

단정은 해석적으로 참인 영역만 한다.

- 관 가운데(z 10..25)의 다리 측면 버텍스 -> 클립된다
- 박스 모서리 버텍스(엉덩이·발 박스 겉) -> 클립되지 않는다
- 관통(다리를 x로 9.5 밀어 관 벽을 뚫고 나오게 함): 관 축 거리 r_t > 13.5 인 다리 버텍스 -> 클립되지 않는다,
  r_t < 11.0 이고 z 10..25 -> 클립된다
- 결과 노드는 닫힘·과다 클립 0(``passed``), 목표 삼각형 수 F ±10%, 형식상 맵 채널 1, 매테리얼 없음
- 원본 노드의 면·버텍스 수·선택 불변, 새 노드는 클립 노드 하나뿐
- ``classify_clip``: 손으로 만든 박스 클립이 그 안의 버텍스만 자른다
- 입력 거부: 가리개 == 대상, 빈 목록

기대 TC 수: 12 (TC00~TC11)

실행:
    uv run python tests/run_max_tests.py test_polygon_clip_mesh.py
"""

import math
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import assert_loaded_from_checkout, bootstrap_pyjallib

bootstrap_pyjallib()

from pymxs import runtime as rt

import pyjallib
from pyjallib.max import clipMesh as cm
from pyjallib.max.polygon import ClipMeshResult, Polygon
from pyjallib.testKit import TestReporter

from _legPantsFixture import make_body, make_pants, poly, reset  # noqa: E402 - 공유 픽스처

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("PolygonClipMesh", LOG_DIR)

PARAMS = dict(inPush=1.0, inVoxelSize=1.0, inInset=1.0, inInnerDepth=3.0, inMaxHeight=10.0)
BUDGET = 500


def _verts(inNode):
    return [(float(p.x), float(p.y), float(p.z)) for p in (rt.polyop.getVert(inNode, i) for i in range(1, int(rt.polyop.getNumVerts(inNode)) + 1))]


def _leg_side(inPts, inOffsetX):
    """다리 원기둥 측면 버텍스 인덱스(0-based)."""
    return [i for i, p in enumerate(inPts) if abs(math.hypot(p[0] - inOffsetX, p[1]) - 5.0) < 1e-3]


polygon = Polygon()

# ============================================================
# TC00: 로드 출처
# ============================================================
try:
    reporter.assert_test(
        assert_loaded_from_checkout(pyjallib),
        "TC00 pyjallib 로드 출처가 검증 대상 체크아웃",
        f"pyjallib.__file__={pyjallib.__file__}",
    )
except Exception:  # noqa: BLE001
    reporter.error("TC00 로드 출처", traceback.format_exc())

# ============================================================
# TC01~TC06: 열린 관 - 생성·통과·해석 영역·규격·원본 무변경
# ============================================================
try:
    reset()
    body = make_body()
    pants = make_pants(inHeightSegs=17)
    bodyFaces, bodyVerts = int(rt.polyop.getNumFaces(body)), int(rt.polyop.getNumVerts(body))
    rt.select(pants)
    handlesBefore = {int(rt.getHandleByAnim(n)) for n in rt.objects}
    result = polygon.build_clip_mesh([pants], [body], inFaceBudget=BUDGET, **PARAMS)
    summary = result.summary()
    reporter.assert_test(
        isinstance(result, ClipMeshResult) and result.passed() and result.check.closed,
        "TC01 열린 관 클립 메쉬가 닫히고 과다 클립 0",
        f"{summary}",
    )
    pts = _verts(body)
    clipped = result.check.targets["Body"].clipped
    mid = [i for i in _leg_side(pts, 0.0) if 10.0 <= pts[i][2] <= 25.0]
    reporter.assert_test(
        len(mid) > 0 and all(i in clipped for i in mid),
        "TC02 관 가운데 다리 측면 버텍스가 전부 클립된다",
        f"mid {len(mid)} / clipped {len([i for i in mid if i in clipped])}",
    )
    corners = [i for i, p in enumerate(pts) if max(abs(p[0]), abs(p[1])) > 14.99]
    reporter.assert_test(
        len(corners) == 16 and not any(i in clipped for i in corners),
        "TC03 박스 모서리 버텍스는 클립되지 않는다",
        f"corners {len(corners)} clipped {[i for i in corners if i in clipped]}",
    )
    node = result.node
    tris = int(node.mesh.numfaces)
    reporter.assert_test(
        abs(tris - BUDGET) <= BUDGET * 0.1 and result.voxelTriangles > tris and result.triangles == tris,
        "TC04 목표 삼각형 수로 감축된다(±10%)",
        f"voxel {result.voxelTriangles} -> {tris} (F {BUDGET}) reasons={result.reasons}",
    )
    reporter.assert_test(
        str(rt.classOf(node)) == "Editable_mesh"
        and bool(rt.meshop.getMapSupport(node, 1))
        and node.material is None
        and str(node.name) == "Pants_Clip",
        "TC05 노드 규격 - Editable_mesh, 맵 채널 1, 매테리얼 없음, 이름 {가리개}_Clip",
        f"class={rt.classOf(node)} map1={rt.meshop.getMapSupport(node, 1)} mat={node.material} name={node.name}",
    )
    handlesAfter = {int(rt.getHandleByAnim(n)) for n in rt.objects}
    reporter.assert_test(
        handlesAfter - handlesBefore == {int(rt.getHandleByAnim(node))}
        and int(rt.polyop.getNumFaces(body)) == bodyFaces
        and int(rt.polyop.getNumVerts(body)) == bodyVerts
        and [str(n.name) for n in rt.selection] == ["Pants"],
        "TC06 원본 무변경 - 새 노드는 클립 노드 하나, 몸 면·버텍스 수와 선택 그대로",
        f"new={len(handlesAfter - handlesBefore)} faces {bodyFaces}->{rt.polyop.getNumFaces(body)} sel={[str(n.name) for n in rt.selection]}",
    )
except Exception:
    reporter.error("TC01~06 열린 관", traceback.format_exc())

# ============================================================
# TC07~TC08: 관통 - 뚫고 나온 다리는 남고 관 안 다리는 잘린다
# ============================================================
try:
    reset()
    offset = 9.5
    body = make_body(inOffsetX=offset)
    pants = make_pants(inHeightSegs=17)
    result = polygon.build_clip_mesh([pants], [body], inFaceBudget=BUDGET, **PARAMS)
    pts = _verts(body)
    clipped = result.check.targets["Body"].clipped
    side = _leg_side(pts, offset)
    outside = [i for i in side if math.hypot(pts[i][0], pts[i][1]) > 13.5 and 3.0 <= pts[i][2] <= 33.0]
    inside = [i for i in side if math.hypot(pts[i][0], pts[i][1]) < 11.0 and 10.0 <= pts[i][2] <= 25.0]
    reporter.assert_test(
        len(outside) > 0 and not any(i in clipped for i in outside),
        "TC07 관을 뚫고 나온 다리 버텍스는 클립되지 않는다",
        f"outside {len(outside)} clipped {[i for i in outside if i in clipped]} cover={result.coverCounts}",
    )
    reporter.assert_test(
        len(inside) > 0 and all(i in clipped for i in inside) and result.passed(),
        "TC08 관 안 다리 버텍스는 클립되고 결과가 통과한다",
        f"inside {len(inside)} / clipped {len([i for i in inside if i in clipped])} summary={result.summary()}",
    )
except Exception:
    reporter.error("TC07~08 관통", traceback.format_exc())

# ============================================================
# TC09: classify_clip - 손으로 만든 박스 클립
# ============================================================
try:
    reset()
    body = make_body()
    # x,y -10..10, z 16..24 - 면이 다리 버텍스 고리(2.5 간격)와 겹치지 않게 둔다. 경계 위 점은 엔진 규칙상 안이다
    # (bbox 경계 포함, t = 0 교차도 센다) - 경계에 고리를 두면 기대가 규칙이 아니라 부등호 선택이 된다
    clipBox = poly(rt.Box(length=20.0, width=20.0, height=8.0))
    clipBox.pos = rt.Point3(0.0, 0.0, 16.0)
    check = polygon.classify_clip(clipBox, [body])
    pts = _verts(body)
    expect = {i for i, p in enumerate(pts) if abs(p[0]) < 10 and abs(p[1]) < 10 and 16.0 < p[2] < 24.0}
    got = check.targets["Body"].clipped
    reporter.assert_test(
        check.closed and got == expect and check.targets["Body"].expected is None,
        "TC09 classify_clip이 박스 안 버텍스만 자른다(기대 집합 없음)",
        f"closed={check.closed} expect {len(expect)} got {len(got)} diff {sorted(got ^ expect)[:10]}",
    )
except Exception:
    reporter.error("TC09 classify_clip", traceback.format_exc())

# ============================================================
# TC10~TC11: 입력 거부
# ============================================================
try:
    reset()
    body = make_body()
    raised = False
    try:
        polygon.build_clip_mesh([body], [body], inFaceBudget=0, **PARAMS)
    except ValueError:
        raised = True
    reporter.assert_test(raised and len(list(rt.objects)) == 1, "TC10 가리개 == 대상이면 ValueError, 노드 생성 없음")
except Exception:
    reporter.error("TC10 겹침 거부", traceback.format_exc())

try:
    raised = 0
    for occ, tgt in (([], [body]), ([body], [])):
        try:
            polygon.build_clip_mesh(occ, tgt, inFaceBudget=0, **PARAMS)
        except ValueError:
            raised += 1
    reporter.assert_test(raised == 2, "TC11 빈 가리개·빈 대상은 ValueError")
except Exception:
    reporter.error("TC11 빈 목록 거부", traceback.format_exc())

reset()
reporter.summary()
reporter.close()
