#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Polygon.read_map_faces / bake_face_mask 테스트 - 3ds Max 환경에서 실행 (Type C).

픽스처: Plane 10x10, 2x2 세그먼트, 맵 좌표 생성 -> Editable Poly. 맵 버텍스 9개, 면 4개(사각), 각 면의 UV는
단위 사각형의 1/4 타일이다(해석적 정답). 64px에서 한 면 = 정확히 32x32 = 1,024픽셀(타일 경계가 정수 픽셀).

기대 TC 수: 10 (TC00~TC09)

실행:
    uv run python tests/run_max_tests.py test_polygon_uv_mask.py
"""

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import assert_loaded_from_checkout, bootstrap_pyjallib

bootstrap_pyjallib()

from pymxs import runtime as rt

import pyjallib
from pyjallib.max import uvMask
from pyjallib.max.header import Header
from pyjallib.max.polygon import Polygon
from pyjallib.testKit import TestReporter

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("PolygonUvMask", LOG_DIR)
OUT_DIR = LOG_DIR / "_uv_mask_out"


def _reset():
    rt.resetMaxFile(rt.Name("noPrompt"))


def _plane(inMapCoords=True):
    node = rt.Plane(length=10.0, width=10.0, lengthsegs=2, widthsegs=2, mapcoords=inMapCoords)
    rt.convertToPoly(node)
    if not inMapCoords:
        rt.polyop.setMapSupport(node, 1, False)
    node.name = "UvPlane"
    return node


def _direct_map(inNode, inChannel=1):
    verts = [
        (float(p.x), float(p.y))
        for p in (rt.polyop.getMapVert(inNode, inChannel, i) for i in range(1, int(rt.polyop.getNumMapVerts(inNode, inChannel)) + 1))
    ]
    faces = [
        [int(i) - 1 for i in rt.polyop.getMapFace(inNode, inChannel, f)]
        for f in range(1, int(rt.polyop.getNumFaces(inNode)) + 1)
    ]
    return verts, faces


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
except Exception as e:  # noqa: BLE001
    reporter.error("TC00 pyjallib 로드 출처", str(e))

# ============================================================
# TC01: read_map_faces == polyop 직접 조회
# ============================================================
try:
    _reset()
    plane = _plane()
    mapVerts, mapFaces = polygon.read_map_faces(plane, 1)
    directVerts, directFaces = _direct_map(plane)
    sameVerts = len(mapVerts) == 9 and all(
        abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6 for a, b in zip(mapVerts, directVerts)
    )
    reporter.assert_test(
        sameVerts and mapFaces == directFaces and len(mapFaces) == 4 and all(len(f) == 4 for f in mapFaces),
        "TC01 read_map_faces가 polyop 직접 조회와 같다(맵 버텍스 9, 면 4, 0-based)",
        f"verts={len(mapVerts)} faces={mapFaces[:2]} direct={directFaces[:2]}",
    )
except Exception:
    reporter.error("TC01 read_map_faces", traceback.format_exc())

# ============================================================
# TC02: 한 면 베이크 = 정확히 1/4 (64px -> 1,024픽셀), 위치도 UV 타일과 일치
# ============================================================
try:
    _reset()
    plane = _plane()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = str(OUT_DIR / "one_face.tga")
    if os.path.exists(path):
        os.remove(path)
    result = polygon.bake_face_mask(plane, [1], 64, path)
    image = uvMask.read_tga(path)
    mapVerts, mapFaces = polygon.read_map_faces(plane, 1)
    us = [mapVerts[i][0] for i in mapFaces[0]]
    vs = [mapVerts[i][1] for i in mapFaces[0]]
    x0, x1 = int(round(min(us) * 64)), int(round(max(us) * 64))
    y0, y1 = int(round((1.0 - max(vs)) * 64)), int(round((1.0 - min(vs)) * 64))
    expectedBlack = {(x, y) for x in range(x0, x1) for y in range(y0, y1)}
    actualBlack = {(x, y) for y in range(64) for x in range(64) if image.get(x, y) == 0}
    reporter.assert_test(
        image.count(0) == 1024 and actualBlack == expectedBlack and result["paintedPixels"] == 1024,
        "TC02 한 면 베이크 = 1,024픽셀, UV 타일 위치와 일치(v 뒤집기)",
        f"black={image.count(0)} tile=({x0},{y0})-({x1},{y1}) result={result}",
    )
except Exception:
    reporter.error("TC02 한 면 베이크", traceback.format_exc())

# ============================================================
# TC03: 전 면 베이크 = 전부 검정 / TC04: 빈 면 목록 = 전부 흰색
# ============================================================
try:
    _reset()
    plane = _plane()
    pathAll = str(OUT_DIR / "all_faces.tga")
    polygon.bake_face_mask(plane, [1, 2, 3, 4], 32, pathAll)
    imageAll = uvMask.read_tga(pathAll)
    reporter.assert_test(imageAll.count(0) == 32 * 32, "TC03 전 면 베이크 = 전부 검정", f"black={imageAll.count(0)}")
    pathNone = str(OUT_DIR / "no_faces.tga")
    resultNone = polygon.bake_face_mask(plane, [], 32, pathNone)
    imageNone = uvMask.read_tga(pathNone)
    reporter.assert_test(
        imageNone.count(255) == 32 * 32 and resultNone["faceCount"] == 0 and resultNone["paintedPixels"] == 0,
        "TC04 빈 면 목록 = 전부 흰색",
        f"white={imageNone.count(255)} result={resultNone}",
    )
except Exception:
    reporter.error("TC03/04 전 면·빈 면", traceback.format_exc())

# ============================================================
# TC05: 씬 무변경 - 노드 수·선택·저장 필요 플래그·면 선택
# ============================================================
try:
    _reset()
    plane = _plane()
    other = rt.Box(length=1, width=1, height=1)
    rt.select(other)
    rt.setSaveRequired(False)
    rt.polyop.setFaceSelection(plane, [2])
    before = (len(list(rt.objects)), [str(n.name) for n in rt.selection], bool(rt.getSaveRequired()))
    polygon.bake_face_mask(plane, [1, 3], 16, str(OUT_DIR / "unchanged.tga"))
    polygon.read_map_faces(plane, 1)
    after = (len(list(rt.objects)), [str(n.name) for n in rt.selection], bool(rt.getSaveRequired()))
    faceSel = [i + 1 for i, flag in enumerate(rt.polyop.getFaceSelection(plane)) if flag]
    reporter.assert_test(
        before == after and faceSel == [2] and int(rt.polyop.getNumFaces(plane)) == 4,
        "TC05 베이크·읽기가 씬을 바꾸지 않는다(노드 수·선택·저장 플래그·면 선택)",
        f"before={before} after={after} faceSel={faceSel}",
    )
except Exception:
    reporter.error("TC05 씬 무변경", traceback.format_exc())

# ============================================================
# TC06: 맵 채널 없음 -> ValueError / TC07: 면 인덱스 범위 밖·비지오메트리 -> ValueError
# ============================================================
try:
    _reset()
    noMap = _plane(inMapCoords=False)
    errs = []
    try:
        polygon.read_map_faces(noMap, 1)
        errs.append("채널 없음: 예외 없음")
    except ValueError:
        pass
    reporter.assert_test(not errs, "TC06 맵 채널이 없으면 ValueError", "; ".join(errs))
    plane = _plane()
    for label, call in (
        ("범위 밖 면", lambda: polygon.bake_face_mask(plane, [5], 16, str(OUT_DIR / "bad.tga"))),
        ("0번 면(1-based 위반)", lambda: polygon.bake_face_mask(plane, [0], 16, str(OUT_DIR / "bad.tga"))),
        ("비지오메트리", lambda: polygon.read_map_faces(rt.Point(), 1)),
    ):
        try:
            call()
            errs.append(f"{label}: 예외 없음")
        except ValueError:
            pass
    reporter.assert_test(not errs, "TC07 면 인덱스 범위 밖·비지오메트리는 ValueError", "; ".join(errs))
except Exception:
    reporter.error("TC06/07 입력 거부", traceback.format_exc())

# ============================================================
# TC08: 파일 규격(헤더 24-bit, 크기) + 반환 사전 키 / TC09: 등록·버전
# ============================================================
try:
    _reset()
    plane = _plane()
    path = str(OUT_DIR / "spec.tga")
    result = polygon.bake_face_mask(plane, [2], 48, path, inPadding=1)
    info = uvMask.tga_header_info(path)
    keys = {"path", "width", "height", "faceCount", "paintedPixels", "zeroPixelFaces"}
    reporter.assert_test(
        info["width"] == 48 and info["height"] == 48 and info["depth"] == 24 and info["imageType"] == 2
        and set(result) == keys and result["paintedPixels"] > 24 * 24 and result["zeroPixelFaces"] == 0
        and os.path.getsize(path) == 18 + 48 * 48 * 3,
        "TC08 TGA 규격(48x48, 24-bit 비압축)과 반환 키, 팽창 1px로 1/4보다 커짐",
        f"info={info} result={result}",
    )
    header = Header.get_instance()
    # 재명세(2026-10-22 0.5.8 clipMesh 가산): 원래 "== 0.5.7"로 이 기능이 들어간 버전을 단정했다. 다음 가산 bump마다 깨지므로
    # "uvMask가 들어간 버전(0.5.7) 이상"으로 바꾼다 - 지키는 축(기능 등록 + 버전 bump 누락 방지)은 그대로다.
    versionTuple = tuple(int(x) for x in pyjallib.__version__.split(".")[:3])
    reporter.assert_test(
        hasattr(header.polygon, "bake_face_mask") and hasattr(header.polygon, "read_map_faces")
        and versionTuple >= (0, 5, 7) and hasattr(pyjallib.max, "uvMask"),
        "TC09 Header.polygon에 bake_face_mask·read_map_faces, 버전 0.5.7 이상, max.uvMask 노출",
        f"version={pyjallib.__version__}",
    )
except Exception:
    reporter.error("TC08/09 규격·등록", traceback.format_exc())

reporter.summary()
reporter.close()
