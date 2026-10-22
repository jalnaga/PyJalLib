# -*- coding: utf-8 -*-
"""clipMesh 순수 모듈 테스트 (Type A) - 정답을 아는 도형으로 부피·이산화·엔진 판정을 단정한다.

- 기하: 삼각형 최근접점 3영역, 면적 가중 노멀, 표면 질의 높이 부호·거리 상한
- 덮임: 감싼 옷 = 전부 덮음 / 안쪽 옷 = 관통 / 먼 옷 = Hmax 초과 / 열린 옷 경계 물림
- 기둥: 이웃 기둥이 공유 옆면을 같은 두 삼각형으로 나눈다(틈·겹침 0)
- 복셀: 공동 메움, 엣지·꼭짓점 접촉 보정 뒤 엔진 규칙 닫힘·오일러 지표
- 엔진 포팅: 닫힘 4경우, 홀짝 - 안/밖/bbox 밖/겹친 상자/엣지 위/**꼭짓점 위 첫 교차 미집계(원본 그대로)**
- 정답 도형: 위 절반만 덮는 열린 옷 -> E == {z >= 0 버텍스}, 복셀 겉면 C == E
"""

import math

import pytest

from pyjallib.max import clipMesh as cm

# ---------------------------------------------------------------------------
# 픽스처 생성기 (clipMesh를 쓰지 않는다)
# ---------------------------------------------------------------------------


def cube(inHalf, inCenter=(0.0, 0.0, 0.0)):
    """8버텍스 12삼각형 상자(바깥 향 감김)."""
    cx, cy, cz = inCenter
    h = inHalf
    verts = [
        (cx - h, cy - h, cz - h), (cx + h, cy - h, cz - h), (cx + h, cy + h, cz - h), (cx - h, cy + h, cz - h),
        (cx - h, cy - h, cz + h), (cx + h, cy - h, cz + h), (cx + h, cy + h, cz + h), (cx - h, cy + h, cz + h),
    ]
    tris = [
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
    ]
    return verts, tris


def grid_box(inHalf, inDivs, inZMin=None, inOpenBottom=False):
    """한 변을 inDivs로 나눈 상자 겉면(버텍스 공유). inZMin을 주면 옆면을 그 높이에서 자르고 바닥을 연다."""
    h = float(inHalf)
    zLo = -h if inZMin is None else float(inZMin)
    vid = {}
    verts = []
    tris = []

    def v(p):
        key = tuple(round(c, 9) for c in p)
        if key not in vid:
            vid[key] = len(verts)
            verts.append(key)
        return vid[key]

    def face(origin, du, dv, nu, nv, flip):
        for i in range(nu):
            for j in range(nv):
                p00 = tuple(origin[k] + du[k] * i + dv[k] * j for k in range(3))
                p10 = tuple(origin[k] + du[k] * (i + 1) + dv[k] * j for k in range(3))
                p11 = tuple(origin[k] + du[k] * (i + 1) + dv[k] * (j + 1) for k in range(3))
                p01 = tuple(origin[k] + du[k] * i + dv[k] * (j + 1) for k in range(3))
                a, b, c, d = v(p00), v(p10), v(p11), v(p01)
                if flip:
                    tris.extend([(a, c, b), (a, d, c)])
                else:
                    tris.extend([(a, b, c), (a, c, d)])

    step = 2.0 * h / inDivs
    zDivs = max(1, int(round((h - zLo) / step)))
    zStep = (h - zLo) / zDivs
    face((-h, -h, h), (step, 0, 0), (0, step, 0), inDivs, inDivs, False)  # 위 (+z)
    if not inOpenBottom and inZMin is None:
        face((-h, -h, -h), (step, 0, 0), (0, step, 0), inDivs, inDivs, True)  # 아래 (-z)
    face((-h, -h, zLo), (step, 0, 0), (0, 0, zStep), inDivs, zDivs, False)  # -y
    face((-h, h, zLo), (step, 0, 0), (0, 0, zStep), inDivs, zDivs, True)  # +y
    face((-h, -h, zLo), (0, step, 0), (0, 0, zStep), inDivs, zDivs, True)  # -x
    face((h, -h, zLo), (0, step, 0), (0, 0, zStep), inDivs, zDivs, False)  # +x
    return verts, tris


# ---------------------------------------------------------------------------
# 기하
# ---------------------------------------------------------------------------


def test_closest_point_vertex_edge_interior_regions():
    a, b, c = (0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)
    q, w = cm.closest_point_on_triangle((-1.0, -1.0, 3.0), a, b, c)
    assert q == a and w == (1.0, 0.0, 0.0)
    q, w = cm.closest_point_on_triangle((1.0, -1.0, 0.0), a, b, c)
    assert q == pytest.approx((1.0, 0.0, 0.0)) and w == pytest.approx((0.5, 0.5, 0.0))
    q, w = cm.closest_point_on_triangle((0.5, 0.5, 4.0), a, b, c)
    assert q == pytest.approx((0.5, 0.5, 0.0)) and sum(w) == pytest.approx(1.0)


def test_vertex_normals_area_weighted_corner():
    verts, tris = cube(1.0)
    normals = cm.vertex_normals(verts, tris)
    # +++ 꼭짓점(6)은 세 면이 같은 면적으로 모이므로 (1,1,1)/sqrt3 방향이 아니라 삼각형 수 가중이 섞인다 - 성분 부호만 단정
    assert all(c > 0 for c in normals[6])
    assert math.isclose(sum(c * c for c in normals[6]), 1.0)


def test_surface_height_sign_and_max_distance():
    surf = cm.TriangleSurface(*grid_box(10.0, 4), inCellSize=2.0)
    hit = surf.nearest((0.0, 0.0, 13.0))
    assert hit.distance == pytest.approx(3.0)
    assert hit.height == pytest.approx(3.0)
    inside = surf.nearest((0.0, 0.0, 9.0))
    assert inside.height == pytest.approx(-1.0)
    assert surf.nearest((0.0, 0.0, 40.0), inMaxDistance=5.0) is None


# ---------------------------------------------------------------------------
# 덮임
# ---------------------------------------------------------------------------


def _coverage(inGarment, inBody, inPush=1.0, inMaxHeight=10.0, inInset=0.0, inDepth=3.0):
    surf = cm.TriangleSurface(*inBody, inCellSize=2.0)
    return cm.compute_coverage(inGarment[0], inGarment[1], surf, inPush, inMaxHeight, inInset, inDepth)


def test_coverage_enclosing_garment_is_fully_covered():
    cov = _coverage(grid_box(11.0, 4), grid_box(10.0, 4))
    assert cov.counts() == {"covered": 192, "penetrating": 0, "tooFar": 0, "inset": 0}  # 6면 x 16칸 x 2
    assert cov.boundaryVerts == set()


def test_coverage_inner_garment_is_penetrating():
    cov = _coverage(grid_box(8.0, 4), grid_box(10.0, 4))
    assert cov.counts()["penetrating"] == 192
    assert cov.prismTris == []


def test_coverage_push_rescues_shallow_penetration():
    body = grid_box(10.0, 4)
    shallow = grid_box(9.6, 4)
    assert _coverage(shallow, body, inPush=0.2).counts()["penetrating"] == 192
    assert _coverage(shallow, body, inPush=1.0).counts()["covered"] == 192


def test_coverage_far_garment_is_too_far():
    cov = _coverage(grid_box(30.0, 4), grid_box(10.0, 4), inMaxHeight=10.0)
    assert cov.counts()["tooFar"] == 192


def test_coverage_open_garment_boundary_and_inset():
    garment = grid_box(11.0, 4, inZMin=-2.75)
    cov0 = _coverage(garment, grid_box(10.0, 4))
    rim = {i for i, p in enumerate(garment[0]) if p[2] == pytest.approx(-2.75)}
    assert cov0.boundaryVerts == rim
    covInset = _coverage(garment, grid_box(10.0, 4), inInset=1.0)
    insetCount = covInset.counts()["inset"]
    # 경계 루프의 버텍스를 쓰는 삼각형 = 아래 행 삼각형(16 칸 x 2 = 옆면 4개 x 4칸 x 2)
    assert insetCount == 32
    for ti in range(len(garment[1])):
        if covInset.triClass[ti] == "inset":
            assert any(v in rim for v in garment[1][ti])


# ---------------------------------------------------------------------------
# 기둥 - 공유 옆면 분할 일관성
# ---------------------------------------------------------------------------


def _faces_on(inTets, inPoints):
    """사면체들의 면 중 꼭짓점이 모두 inPoints 위에 있는 것(정렬 튜플 집합)."""
    out = set()
    for tet in inTets:
        for drop in range(4):
            face = tuple(sorted(tet[k] for k in range(4) if k != drop))
            if all(p in inPoints for p in face):
                out.add(face)
    return out


def test_adjacent_prisms_split_shared_side_identically():
    # 두 삼각형 (0,1,2)와 (1,3,2)가 엣지 1-2를 공유. 위 점은 비틀어 옆면이 평면이 아니게 한다
    tops = [(0.0, 0.0, 5.0), (4.0, 0.0, 6.0), (0.0, 4.0, 4.5), (4.0, 4.0, 5.5)]
    bottoms = [(0.3, 0.1, 0.0), (4.0, -0.2, -0.5), (-0.1, 4.2, 0.4), (4.1, 4.0, 0.0)]
    tetsA = cm.prism_tetrahedra((0, 1, 2), tops, bottoms)
    tetsB = cm.prism_tetrahedra((1, 3, 2), tops, bottoms)
    shared = {tops[1], tops[2], bottoms[1], bottoms[2]}
    facesA = _faces_on(tetsA, shared)
    facesB = _faces_on(tetsB, shared)
    assert len(facesA) == 2
    assert facesA == facesB


def test_local_order_split_would_disagree():
    """판별력: 지역 순서(정렬 없이)로 쪼개면 같은 옆면이 다르게 나뉘는 배치가 실제로 있다."""
    tops = [(0.0, 0.0, 5.0), (4.0, 0.0, 6.0), (0.0, 4.0, 4.5), (4.0, 4.0, 5.5)]
    bottoms = [(0.3, 0.1, 0.0), (4.0, -0.2, -0.5), (-0.1, 4.2, 0.4), (4.1, 4.0, 0.0)]

    def unsorted(tri):
        a, b, c = tri
        pa, pb, pc = tops[a], tops[b], tops[c]
        qa, qb, qc = bottoms[a], bottoms[b], bottoms[c]
        return [(pa, pb, pc, qc), (pa, pb, qb, qc), (pa, qa, qb, qc)]

    shared = {tops[1], tops[2], bottoms[1], bottoms[2]}
    assert _faces_on(unsorted((0, 1, 2)), shared) != _faces_on(unsorted((3, 2, 1)), shared)


def test_tet_union_contains_inside_outside_boundary():
    tet = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    union = cm.TetUnion([tet], inCellSize=0.5)
    assert union.contains((0.1, 0.1, 0.1))
    assert not union.contains((0.6, 0.6, 0.6))
    assert union.contains((0.0, 0.0, 0.5))  # 면 위는 안
    assert union.tetCount == 1


# ---------------------------------------------------------------------------
# 복셀
# ---------------------------------------------------------------------------


def _grid(inDims, inCells):
    g = cm.VoxelGrid((0.0, 0.0, 0.0), 1.0, inDims)
    for i, j, k in inCells:
        g.occ[g.index(i, j, k)] = 1
    return g


def _euler(inVerts, inTris):
    return len(inVerts) - len(cm.edge_face_counts(inTris)) + len(inTris)


def test_single_voxel_surface_is_closed_cube():
    g = _grid((3, 3, 3), [(1, 1, 1)])
    verts, tris = cm.extract_surface(g)
    assert (len(verts), len(tris)) == (8, 12)
    assert cm.is_mesh_closed(verts, tris)
    assert cm.signed_volume(verts, tris) == pytest.approx(1.0)


def test_fill_cavities_fills_enclosed_hole():
    shell = [(i, j, k) for i in range(1, 4) for j in range(1, 4) for k in range(1, 4) if (i, j, k) != (2, 2, 2)]
    g = _grid((5, 5, 5), shell)
    assert cm.fill_cavities(g) == 1
    assert g.get(2, 2, 2) == 1


def test_edge_contact_is_fixed_to_manifold():
    g = _grid((4, 4, 3), [(1, 1, 1), (2, 2, 1)])
    before = cm.extract_surface(g)
    assert not cm.is_mesh_closed(*before)  # 엣지 하나를 면 4개가 공유
    assert cm.fix_nonmanifold(g) >= 1
    verts, tris = cm.extract_surface(g)
    assert cm.is_mesh_closed(verts, tris)
    assert _euler(verts, tris) == 2


def test_vertex_contact_is_fixed():
    g = _grid((4, 4, 4), [(1, 1, 1), (2, 2, 2)])
    assert cm.fix_nonmanifold(g) >= 1
    verts, tris = cm.extract_surface(g)
    assert cm.is_mesh_closed(verts, tris)
    assert _euler(verts, tris) == 2


# ---------------------------------------------------------------------------
# 엔진 포팅 - 닫힘
# ---------------------------------------------------------------------------


def test_engine_closed_cube_true():
    assert cm.is_mesh_closed(*cube(1.0))


def test_engine_closed_missing_face_false():
    verts, tris = cube(1.0)
    assert not cm.is_mesh_closed(verts, tris[:-1])


def test_engine_closed_degenerate_face_false():
    verts, tris = cube(1.0)
    assert not cm.is_mesh_closed(verts, tris + [(0, 0, 1)])


def test_engine_closed_split_vertices_at_same_position_true():
    """UV 이음새처럼 위치가 같은 분리 버텍스는 엔진이 합치므로 닫힌 것으로 본다."""
    verts, tris = cube(1.0)
    verts = list(verts) + [verts[4], verts[5], verts[6]]
    tris = list(tris)
    tris[2] = (8, 9, 10)  # 윗면 삼각형 하나를 복제 버텍스로
    assert cm.is_mesh_closed(verts, tris)


# ---------------------------------------------------------------------------
# 엔진 포팅 - 홀짝
# ---------------------------------------------------------------------------


def test_classify_inside_outside_and_outside_bbox():
    clip = cube(1.0)
    base = [(0.1, 0.2, 0.3), (0.5, 0.5, 2.0), (3.0, 0.0, 0.0), (0.2, -0.3, -0.9)]
    assert cm.classify_vertices(base, *clip) == [True, False, False, True]


def test_classify_overlapping_cubes_cancel_in_overlap():
    a = cube(1.0)
    b = cube(1.0, (0.0, 0.0, 1.0))
    verts, tris, _ = cm.merge_meshes([a, b])
    inside = cm.classify_vertices([(0.1, 0.2, 0.5), (0.1, 0.2, -0.5), (0.1, 0.2, 1.5)], verts, tris)
    # 겹친 곳(z 0~1)은 위로 두 윗면을 지나 짝수 = 밖. 겹친 부피는 엔진에서 지워지지 않는다
    assert inside == [False, True, True]


def test_classify_ray_through_shared_edge_counts_once():
    # 윗면 대각선 (-1,-1)-(1,1) 위를 지나는 레이 - 두 삼각형이 공유한 엣지를 한 번만 센다
    assert cm.classify_vertices([(0.25, 0.25, 0.0)], *cube(1.0)) == [True]


def test_classify_ray_through_vertex_engine_quirk():
    """원본 287행 - 꼭짓점 위 교차는 첫 번째를 세지 않는다.

    윗면 꼭짓점 (1,1,1)은 윗면 삼각형 2개가 공유해 1번 센다(안). (1,-1,1)은 1개만 써서 0번(밖).
    엔진이 이렇게 판정하므로 에뮬레이터도 그대로 둔다 - 고치면 이 테스트가 실패해야 한다.
    """
    inside = cm.classify_vertices([(1.0, 1.0, 0.0), (1.0, -1.0, 0.0)], *cube(1.0))
    assert inside == [True, False]


def test_cull_faces_strategies():
    tris = [(0, 1, 2), (1, 2, 3)]
    inside = [True, True, True, False]
    assert cm.cull_faces(tris, inside, cm.CULL_ALL_VERTICES) == [0]
    assert cm.cull_faces(tris, inside, cm.CULL_ONE_VERTEX) == [0, 1]
    with pytest.raises(ValueError):
        cm.cull_faces(tris, inside, "nope")


# ---------------------------------------------------------------------------
# 정답 도형 - 위 절반만 덮는 열린 옷
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def half_cover():
    body = grid_box(10.0, 4)
    garment = grid_box(11.0, 4, inZMin=-2.5)
    vol = cm.build_clip_volume(
        [garment], {"Body": body}, inPush=1.0, inVoxelSize=0.5, inInset=0.0, inInnerDepth=3.0, inMaxHeight=10.0
    )
    return body, vol


def test_half_cover_expected_is_upper_half(half_cover):
    body, vol = half_cover
    upper = {i for i, p in enumerate(body[0]) if p[2] >= 0.0}
    assert vol.expected["Body"] == upper
    assert len(upper) == 57  # 4분할 상자 98버텍스 중 z >= 0: 윗면 25 + z 5 고리 16 + z 0 고리 16


def test_half_cover_voxel_surface_reproduces_expected(half_cover):
    """복셀 겉면이 닫히고 엔진 판정이 E를 그대로 재현한다.

    종수(오일러 지표)는 단정하지 않는다 - 볼록 모서리 안쪽(바디 표면 2 cm 아래)에서 기둥 아래면 사이에 단일 복셀
    통로가 생겨 손잡이가 되지만 클립 대상 버텍스가 없는 곳이고, 엔진 홀짝은 종수와 무관하게 성립한다. 판정 축은
    닫힘과 과다·과소 0이다. 이 픽스처의 버텍스는 0.5 격자 위에 있어 격자 원점 어긋남(``LATTICE_OFFSET``)이 없으면
    z = 0 고리 16버텍스의 레이가 겉면 꼭짓점을 지나 과소가 된다(판별력 - 2.11 변이).
    """
    body, vol = half_cover
    assert cm.is_mesh_closed(vol.verts, vol.tris)
    check = cm.verify_clip(vol.verts, vol.tris, {"Body": body}, vol.expected)
    target = check.targets["Body"]
    assert target.over == [] and target.under == []
    assert check.passed()
    assert target.facesAll > 0 and target.facesOne >= target.facesAll


def test_close_grid_leaves_no_cavity():
    """보정이 막아 만든 공동까지 메운다 - close_grid 뒤 바깥에서 닿지 않는 빈 칸이 0이다.

    이 정답 도형은 보정(fix_nonmanifold)이 가는 통로를 막아 공동을 새로 만든다(실측 63칸). 재메움이 없으면 그 공동이
    겉면의 안쪽 껍질이 된다. 공동 위치가 대상 버텍스의 레이 경로 밖이라 C == E 단정만으로는 잡히지 않아 따로 둔다.
    """
    body = grid_box(10.0, 4)
    garment = grid_box(11.0, 4, inZMin=-2.5)
    surf = cm.TriangleSurface(*body, inCellSize=2.0)
    cov = cm.compute_coverage(garment[0], garment[1], surf, 1.0, 10.0, 0.0, 3.0)
    grid = cm.voxelize_union(cm.build_prism_union(cov, garment[1], 1.0), 0.5)
    cavities, fixed = cm.close_grid(grid)
    assert fixed > 0
    assert cm.fill_cavities(grid) == 0


def test_verify_reports_over_and_under():
    body = grid_box(10.0, 2)
    clip = cube(11.0, (0.0, 0.0, 11.0))  # z 0~22 상자 - z >= 0 버텍스를 자른다
    upper = {i for i, p in enumerate(body[0]) if p[2] > 0.0}
    expected = {i for i, p in enumerate(body[0]) if p[2] >= 0.0}
    expected -= {min(upper)}  # 하나는 기대에서 빼 과다로
    expected.add(next(i for i, p in enumerate(body[0]) if p[2] < 0.0))  # 하나는 아래에서 넣어 과소로
    check = cm.verify_clip(*clip, {"Body": body}, {"Body": expected})
    target = check.targets["Body"]
    assert min(upper) in target.over
    assert len(target.under) >= 1
    assert target.overDistanceMax > 0.0
    assert not check.passed()


def test_build_rejects_empty_and_bad_params():
    body = cube(10.0)
    with pytest.raises(ValueError):
        cm.build_clip_volume([], {"Body": body}, 1.0, 1.0, 0.0, 3.0, 10.0)
    with pytest.raises(ValueError):
        cm.build_clip_volume([cube(11.0)], {"Body": body}, 1.0, 0.0, 0.0, 3.0, 10.0)
