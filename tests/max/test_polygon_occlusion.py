#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Polygon.find_occluded_faces 테스트 - 3ds Max 환경에서 실행 (Type C).

합성 픽스처의 **해석적으로 참인 영역**만 단정한다(경계 근처는 판정 대상에서 뺀다).

픽스처 1 - 열린 관 + 자기 가림 (몸 = 다리 원기둥 + 엉덩이 박스 + 발 박스, 한 Editable Poly):

    다리  Cylinder r=5, z 0..40, 16변 x 16단(2.5)
    엉덩이 Box 30x30, z 34..42 (다리 위끝 z 34..40을 감싼다)
    발    Box 30x30, z -4..2  (다리 아래끝 z 0..2를 감싼다)
    바지  Tube r 12..12.5(헐렁한 바지), z 1..35 - 위아래가 열린 관이지만 양끝이 박스 안으로 1씩 묻힌다

  - 관 가운데 띠(면 버텍스 z 전부 14..26)의 다리 측면 -> 가려짐
  - 박스 면(옆면 8 + 위아래 4 = 12)은 가려짐이 아니다
  - 엉덩이 박스 안에 묻힌 다리 측면(z 전부 35..39) -> 자기 가림(A7)
  - **초안 정의(시험 1에서 몸을 뺌)로 돌리면 가운데 띠에서 누출이 난다** - 축에 가까운 레이가
    다리와 관 사이 틈을 따라 관 끝으로 빠져나간다. 두 시험 정의에서는 엉덩이·발(몸)이 그 시선을 막는다.

  배치 근거(2026-10-19 실행 이력):
  - 관 끝과 박스 사이에 **틈을 두면** 바깥에서 바짓가랑이 안을 비스듬히 들여다보는 시선이 실제로 생겨
    깊은 면도 정의상 "보임"이다(1차: 아래 틈 6에서 다리 64면 중 28면 보임) - 그래서 양끝을 묻는다.
  - 틈을 막아도 관이 **꽉 끼면**(관 안쪽 7.5, 틈 2.5) N=32 방향 중 관 끝까지 빠질 만큼 축에 가까운
    레이가 없어 초안 정의도 누출 0이었다(2차) - 대조군이 판별력을 가지려면 헐렁한 관이 필요하다.

픽스처 2 - 관통 (A9): 같은 몸·관에서 다리만 x로 9.5 밀어 관 벽을 뚫고 나오게 한다(박스는 원점 중심 그대로).

  - 관 축 거리 r_t > 12.8 인 버텍스를 가진 면(z 3..33) -> 보임(뚫고 나온 부분)
  - 버텍스가 전부 r_t < 11.7 이고 z 14..26 인 면 -> 가려짐

기대 TC 수: 16 (TC00~TC15)

실행:
    uv run python tests/run_max_tests.py test_polygon_occlusion.py
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
from pyjallib.max import polygonMath as pm
from pyjallib.max.header import Header
from pyjallib.max.polygon import Polygon
from pyjallib.testKit import TestReporter

from _legPantsFixture import make_body as _make_body  # noqa: E402 - 공유 픽스처(복붙 금지, 모듈 docstring)
from _legPantsFixture import make_pants as _make_pants  # noqa: E402
from _legPantsFixture import reset as _reset  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("PolygonOcclusion", LOG_DIR)


def _is_box_outer(inPts):
    """박스 면인가(모서리만 쓰는 면 - 옆면·위아래 면, 또는 엉덩이 윗면 z = 42, 발 아랫면 z = -4)."""
    return (
        all(max(abs(p[0]), abs(p[1])) > 14.99 for p in inPts)
        or all(p[2] > 41.99 for p in inPts)
        or all(p[2] < -3.99 for p in inPts)
    )


def _faces_world(inNode):
    """1-based 면 번호 -> 버텍스 월드 좌표 목록."""
    out = {}
    for f in range(1, int(rt.polyop.getNumFaces(inNode)) + 1):
        vs = rt.polyop.getFaceVerts(inNode, f)
        out[f] = [tuple(float(c) for c in (p.x, p.y, p.z)) for p in (rt.polyop.getVert(inNode, v) for v in vs)]
    return out


def _is_leg_side(inPts, inOffsetX):
    """다리 원기둥 측면 면인가(모든 버텍스가 반지름 5 원 위)."""
    return all(abs(math.hypot(p[0] - inOffsetX, p[1]) - 5.0) < 1e-3 for p in inPts)


def _draft_definition(inPoly, inTarget, inOccluders):
    """초안 정의(시험 1 차폐물 = 가리개만, 몸 제외)로 판정한다 - 판별력 대조군."""
    inPoly._ensure_functions()
    verts, normals, faces, triangles = inPoly._read_target(inTarget)
    merged = rt.pyjal_polygon_merge(rt.Array(*inOccluders), "PyJalPolygon_tmpOccluder")
    gridOcc = rt.pyjal_polygon_grid(merged, inPoly.GRID_RESOLUTION)
    gridSelf = rt.pyjal_polygon_grid(inTarget, inPoly.GRID_RESOLUTION)
    try:
        dirs = rt.Array(*[rt.Point3(*d) for d in pm.cone_directions(32, 90.0)])
        res = pm.find_occluded_faces(
            verts, faces, normals,
            inPoly._make_query(gridOcc, dirs, inPoly.DEFAULT_EPSILON),
            inPoly._make_query(gridSelf, dirs, inPoly.DEFAULT_EPSILON),
            0.0,
            inTriangles=triangles,
        )
    finally:
        gridOcc.free()
        gridSelf.free()
        rt.delete(merged)
    return {f + 1 for f in res.occludedFaces}


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
except Exception as e:
    reporter.error("TC00 pyjallib 로드 출처", str(e))

# ============================================================
# TC01: Header 등록
# ============================================================
try:
    _reset()
    reporter.assert_test(
        isinstance(Header.get_instance().polygon, Polygon),
        "TC01 Header.polygon이 Polygon 인스턴스",
        f"type={type(Header.get_instance().polygon)}",
    )
except Exception:
    reporter.error("TC01 Header.polygon", traceback.format_exc())

# ============================================================
# 픽스처 1 - 열린 관 + 자기 가림
# ============================================================
fx1 = None
try:
    _reset()
    body = _make_body()
    pants = _make_pants()
    faces = _faces_world(body)
    core = {f for f, ps in faces.items() if _is_leg_side(ps, 0.0) and all(14.0 <= p[2] <= 26.0 for p in ps)}
    buried = {f for f, ps in faces.items() if _is_leg_side(ps, 0.0) and all(35.0 <= p[2] <= 39.0 for p in ps)}
    outside = {f for f, ps in faces.items() if _is_box_outer(ps)}
    rt.clearSelection()
    rt.select(pants)
    rt.setSaveRequired(False)
    nodesBefore = int(rt.objects.count)
    result = polygon.find_occluded_faces(body, [pants], 32, 90.0, 0.0)
    # 씬 무변경 관측은 호출 직후에 떠 둔다(뒤 TC의 대조군 헬퍼가 임시 노드를 만든다)
    after = {
        "tmp": [str(n.name) for n in rt.objects if str(n.name).startswith("PyJalPolygon_tmp")],
        "sel": [str(n.name) for n in rt.selection],
        "nodes": int(rt.objects.count),
        "save": bool(rt.getSaveRequired()),
    }
    fx1 = {
        "body": body, "pants": pants, "core": core, "buried": buried, "outside": outside,
        "result": result, "nodesBefore": nodesBefore, "faces": faces, "after": after,
    }
    # TC02: 픽스처 전제
    reporter.assert_test(
        len(core) == 16 * 4 and len(buried) == 16 and len(outside) == 12,
        "TC02 픽스처 1 전제(가운데 띠 64면·묻힌 띠 16면·박스 면 12)",
        f"core={len(core)} buried={len(buried)} outside={len(outside)}",
    )
except Exception:
    reporter.error("TC02 픽스처 1 생성·판정", traceback.format_exc())

try:
    occluded = set(fx1["result"].occludedFaces)
    reporter.assert_test(
        fx1["core"] <= occluded,
        "TC03 관 가운데 띠의 다리 면이 전부 가려짐",
        f"missing={sorted(fx1['core'] - occluded)} counts={fx1['result'].counts()}",
    )
except Exception:
    reporter.error("TC03 관 가운데 띠", traceback.format_exc())

try:
    occluded = set(fx1["result"].occludedFaces)
    reporter.assert_test(
        not (fx1["outside"] & occluded),
        "TC04 박스 면은 가려짐이 아니다",
        f"wrong={sorted(fx1['outside'] & occluded)}",
    )
except Exception:
    reporter.error("TC04 관 밖", traceback.format_exc())

try:
    selfOcc = set(fx1["result"].selfOccludedFaces)
    occluded = set(fx1["result"].occludedFaces)
    reporter.assert_test(
        fx1["buried"] <= selfOcc and not (fx1["buried"] & occluded),
        "TC05 엉덩이 박스에 묻힌 다리 면은 자기 가림(A7)으로 보존",
        f"notSelf={sorted(fx1['buried'] - selfOcc)} deleted={sorted(fx1['buried'] & occluded)}",
    )
except Exception:
    reporter.error("TC05 자기 가림", traceback.format_exc())

try:
    draftOccluded = _draft_definition(polygon, fx1["body"], [fx1["pants"]])
    leaked = fx1["core"] - draftOccluded
    reporter.assert_test(
        len(leaked) > 0,
        "TC06 판별력: 초안 정의(몸 차폐 제외)는 가운데 띠에서 누출한다",
        f"leaked={len(leaked)}/{len(fx1['core'])}",
    )
except Exception:
    reporter.error("TC06 초안 정의 대조", traceback.format_exc())

try:
    a = fx1["after"]
    reporter.assert_test(
        not a["tmp"] and a["sel"] == ["Pants"] and a["nodes"] == fx1["nodesBefore"] and a["save"] is False,
        "TC07 씬 무변경(임시 노드 0·선택·노드 수·저장 필요 플래그)",
        f"after={a} nodesBefore={fx1['nodesBefore']}",
    )
except Exception:
    reporter.error("TC07 씬 무변경", traceback.format_exc())

try:
    r0 = fx1["result"]
    r2 = polygon.find_occluded_faces(fx1["body"], [fx1["pants"]], 32, 90.0, 2.0)
    c = r2.counts()
    reporter.assert_test(
        set(r2.occludedFaces) <= set(r0.occludedFaces)
        and set(r2.marginKeptFaces) == set(r0.occludedFaces) - set(r2.occludedFaces)
        and c["visible"] + c["selfOccluded"] + c["marginKept"] + c["occluded"] == c["faces"],
        "TC08 여유 2.0: 여유 보존 = 여유 0 가려짐 - 여유 2 가려짐, 분류 합 = 면 수",
        f"r0={r0.counts()} r2={c}",
    )
except Exception:
    reporter.error("TC08 여유", traceback.format_exc())

# ============================================================
# 픽스처 2 - 관통 (A9)
# ============================================================
fx2 = None
try:
    _reset()
    body = _make_body(inOffsetX=9.5)
    pants = _make_pants()
    faces = _faces_world(body)

    def rt_(p):
        return math.hypot(p[0], p[1])

    pokeOut = {f for f, ps in faces.items() if any(rt_(p) > 12.8 for p in ps) and all(3.0 <= p[2] <= 33.0 for p in ps)}
    inside = {f for f, ps in faces.items() if all(rt_(p) < 11.7 for p in ps) and all(14.0 <= p[2] <= 26.0 for p in ps)}
    result = polygon.find_occluded_faces(body, [pants], 32, 90.0, 0.0)
    fx2 = {"pokeOut": pokeOut, "inside": inside, "result": result}
    reporter.assert_test(
        len(pokeOut) > 0 and len(inside) > 0,
        "TC09 픽스처 2 전제(뚫고 나온 면·관 안 면 둘 다 존재)",
        f"pokeOut={len(pokeOut)} inside={len(inside)}",
    )
except Exception:
    reporter.error("TC09 픽스처 2 생성·판정", traceback.format_exc())

try:
    visible = set(fx2["result"].visibleFaces)
    reporter.assert_test(
        fx2["pokeOut"] <= visible,
        "TC10 관통: 관 벽을 뚫고 나온 면은 보임(삭제 안 함)",
        f"notVisible={sorted(fx2['pokeOut'] - visible)}",
    )
except Exception:
    reporter.error("TC10 관통 보임", traceback.format_exc())

try:
    occluded = set(fx2["result"].occludedFaces)
    reporter.assert_test(
        fx2["inside"] <= occluded,
        "TC11 관통: 관 안쪽 가운데 띠 면은 가려짐",
        f"missing={sorted(fx2['inside'] - occluded)} counts={fx2['result'].counts()}",
    )
except Exception:
    reporter.error("TC11 관통 가려짐", traceback.format_exc())

# ============================================================
# 픽스처 3 - 접힌(비평면) 면: 면 대표점이 실제 표면 위에 있어야 한다
# ============================================================
fx3 = None
try:
    _reset()
    body = _make_body()
    # 다리 원기둥 측면 버텍스를 (단 + 변) 홀짝으로 반지름 ±0.4 밀어 모든 측면 사각형을 안장형으로 접는다
    for v in range(1, int(rt.polyop.getNumVerts(body)) + 1):
        p = rt.polyop.getVert(body, v)
        r = math.hypot(p.x, p.y)
        if abs(r - 5.0) > 1e-3 or not (0.0 < p.z < 40.0):
            continue
        ring = int(round(p.z / 2.5))
        seg = int(round(math.atan2(p.y, p.x) / (2.0 * math.pi / 16.0))) % 16
        scale = (5.0 + (0.4 if (ring + seg) % 2 == 0 else -0.4)) / r
        rt.polyop.setVert(body, v, rt.Point3(p.x * scale, p.y * scale, p.z))
    pants = _make_pants()
    faces = _faces_world(body)
    foldedCore = {
        f for f, ps in faces.items()
        if len(ps) == 4 and all(abs(math.hypot(p[0], p[1]) - 5.0) < 0.41 for p in ps) and all(14.0 <= p[2] <= 26.0 for p in ps)
    }
    # 대조: 꼭짓점 평균 대표점(삼각분할 미사용)으로 판정 - 자기 면에 막혀 자기 가림이 나와야 픽스처가 결함을 재현한다
    polygon._ensure_functions()
    verts, normals, polyFaces, triangles = polygon._read_target(body)
    merged = rt.pyjal_polygon_merge(rt.Array(body, pants), "PyJalPolygon_tmpOccluder")
    gAll = rt.pyjal_polygon_grid(merged, polygon.GRID_RESOLUTION)
    gSelf = rt.pyjal_polygon_grid(body, polygon.GRID_RESOLUTION)
    try:
        dirs = rt.Array(*[rt.Point3(*d) for d in pm.cone_directions(32, 90.0)])
        legacy = pm.find_occluded_faces(
            verts, polyFaces, normals,
            polygon._make_query(gAll, dirs, polygon.DEFAULT_EPSILON),
            polygon._make_query(gSelf, dirs, polygon.DEFAULT_EPSILON),
            0.0,
        )
    finally:
        gAll.free()
        gSelf.free()
        rt.delete(merged)
    legacySelfCore = {f + 1 for f in legacy.selfOccludedFaces} & foldedCore
    result = polygon.find_occluded_faces(body, [pants], 32, 90.0, 0.0)
    fx3 = {"core": foldedCore, "result": result, "legacySelfCore": legacySelfCore}
    reporter.assert_test(
        len(foldedCore) == 64 and len(legacySelfCore) > 0,
        "TC14 픽스처 3 전제(접힌 가운데 띠 64면, 꼭짓점 평균 대표점이면 그중 일부가 자기 가림으로 오판)",
        f"core={len(foldedCore)} legacySelfOccludedInCore={len(legacySelfCore)}",
    )
except Exception:
    reporter.error("TC14 픽스처 3 생성·대조", traceback.format_exc())

try:
    occluded = set(fx3["result"].occludedFaces)
    selfOcc = set(fx3["result"].selfOccludedFaces)
    reporter.assert_test(
        fx3["core"] <= occluded and not (fx3["core"] & selfOcc),
        "TC15 접힌 면도 덮인 띠는 전부 가려짐, 자기 가림 오판 0(대표점이 실제 표면 위)",
        f"missing={sorted(fx3['core'] - occluded)} selfInCore={sorted(fx3['core'] & selfOcc)} counts={fx3['result'].counts()}",
    )
except Exception:
    reporter.error("TC15 접힌 면", traceback.format_exc())

# ============================================================
# 입력 거부
# ============================================================
try:
    _reset()
    body = _make_body(inWithBoxes=False)
    pants = _make_pants()
    raised = False
    try:
        polygon.find_occluded_faces(body, [pants, body])
    except ValueError:
        raised = True
    reporter.assert_test(raised, "TC12 대상이 가리개 목록에 있으면 ValueError")
except Exception:
    reporter.error("TC12 겹침 거부", traceback.format_exc())

try:
    _reset()
    body = _make_body(inWithBoxes=False)
    pants = _make_pants()
    errs = []
    for label, call in (
        ("중복 가리개", lambda: polygon.find_occluded_faces(body, [pants, pants])),
        ("가리개 없음", lambda: polygon.find_occluded_faces(body, [])),
        ("음수 여유", lambda: polygon.find_occluded_faces(body, [pants], inMargin=-1.0)),
        ("반각 범위 밖", lambda: polygon.find_occluded_faces(body, [pants], inConeAngle=120.0)),
    ):
        try:
            call()
            errs.append(f"{label}: 예외 없음")
        except ValueError:
            pass
    reporter.assert_test(not errs, "TC13 입력 거부(중복·빈 가리개·음수 여유·반각 범위)", "; ".join(errs))
except Exception:
    reporter.error("TC13 입력 거부", traceback.format_exc())

reporter.summary()
reporter.close()
