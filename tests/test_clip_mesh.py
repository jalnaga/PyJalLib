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


def uv_sphere(inR, inSegs, inRings, inZMin=None):
    """원점 UV 구(바깥 향 감김). inZMin을 주면 그 아래 고리를 버려 아래가 열린 옷을 만든다."""
    verts = []
    rings = []
    for r in range(1, inRings):
        th = math.pi * r / inRings
        z = inR * math.cos(th)
        if inZMin is not None and z < inZMin:
            break
        row = []
        for s in range(inSegs):
            ph = 2.0 * math.pi * s / inSegs
            row.append(len(verts))
            verts.append((inR * math.sin(th) * math.cos(ph), inR * math.sin(th) * math.sin(ph), z))
        rings.append(row)
    top = len(verts)
    verts.append((0.0, 0.0, inR))
    tris = [(top, rings[0][s], rings[0][(s + 1) % inSegs]) for s in range(inSegs)]
    for a, b in zip(rings, rings[1:]):
        for s in range(inSegs):
            s1 = (s + 1) % inSegs
            tris.extend([(a[s], b[s], b[s1]), (a[s], b[s1], a[s1])])
    if inZMin is None:
        bot = len(verts)
        verts.append((0.0, 0.0, -inR))
        tris.extend((bot, rings[-1][(s + 1) % inSegs], rings[-1][s]) for s in range(inSegs))
    return verts, tris


def lumpy(inMesh, inAmp, inFreq=0.7):
    """버텍스를 사인 변위로 울퉁불퉁하게(축 정렬·대칭을 깬다)."""
    verts, tris = inMesh
    moved = [
        (x + inAmp * math.sin(inFreq * y), y + inAmp * math.sin(inFreq * z), z + inAmp * math.sin(inFreq * x))
        for x, y, z in verts
    ]
    return moved, tris


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
    # 두 삼각형 (0,1,2)와 (2,1,3)이 엣지 1-2를 공유. 위 점은 비틀어 옆면이 평면이 아니게 한다.
    # 두 번째 삼각형은 (1,3,2)를 회전한 (2,1,3)으로 준다 - 지역 순서가 정렬 순서와 달라야 규칙이 시험된다(2.11 변이)
    tops = [(0.0, 0.0, 5.0), (4.0, 0.0, 6.0), (0.0, 4.0, 4.5), (4.0, 4.0, 5.5)]
    bottoms = [(0.3, 0.1, 0.0), (4.0, -0.2, -0.5), (-0.1, 4.2, 0.4), (4.1, 4.0, 0.0)]
    tetsA = cm.prism_tetrahedra((0, 1, 2), tops, bottoms)
    tetsB = cm.prism_tetrahedra((2, 1, 3), tops, bottoms)
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


def test_forbidden_cavity_is_not_filled_and_stays_outside():
    """금지 칸(보호 점 칸)은 공동 메움이 채우지 않는다 - 남은 공동은 안쪽 껍질이 되어 그 안의 점이 홀짝상 밖이다(갈림길 3)."""
    shell = [(i, j, k) for i in range(1, 4) for j in range(1, 4) for k in range(1, 4) if (i, j, k) != (2, 2, 2)]
    g = _grid((5, 5, 5), shell)
    g.forbidden.add(g.index(2, 2, 2))
    assert cm.fill_cavities(g) == 0
    assert g.get(2, 2, 2) == 0
    verts, tris = cm.extract_surface(g)
    assert cm.is_mesh_closed(verts, tris)
    assert cm.classify_vertices([(2.3, 2.6, 2.4), (1.3, 1.6, 1.4)], verts, tris) == [False, True]


def _forbidden_edge_contact_grid():
    """2x2x2 꽉 찬 블록에서 금지 칸 둘이 엣지로만 맞닿는다 - 빈 칸이 금지 칸뿐이라 채워서는 고칠 수 없다."""
    g = _grid((4, 4, 4), [(i, j, k) for i in (1, 2) for j in (1, 2) for k in (1, 2)])
    for cell in ((1, 1, 1), (2, 2, 1)):
        idx = g.index(*cell)
        g.occ[idx] = 0
        g.forbidden.add(idx)
    return g


def test_fix_nonmanifold_carves_when_only_forbidden_cells_are_empty():
    """빈 칸이 금지 칸뿐인 비다양체 블록은 점유 칸을 비워 고친다 - 금지 칸은 끝까지 비고, 겉면은 닫힌다(실기 31 / 13 / 38블록)."""
    g = _forbidden_edge_contact_grid()
    assert not cm.is_mesh_closed(*cm.extract_surface(g))
    cm.close_grid(g)
    assert g.carved >= 1 and g.unresolved == 0
    assert g.get(1, 1, 1) == 0 and g.get(2, 2, 1) == 0
    assert cm.is_mesh_closed(*cm.extract_surface(g))


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


def test_protect_cells_do_not_swallow_vertices_below_rim():
    """보호 칸 금지(갈림길 3, 이전 A11의 목적 그대로) - 옷 테두리(z -2.9) 0.1 아래의 바디 고리(z -3.0)를 자르지 않는다.

    관대한 점유만으로는 이 고리가 든 칸이 점유된다(꼭짓점이 테두리 위) - 칸 중심 판정 때와 같이 고리 80버텍스가 전부 과다가
    된다. 보호 점(기대 집합 밖 대상 버텍스) 칸을 비워 막는다. 같은 도형에서 옷은 감싼다(포함률 1).
    """
    body = grid_box(10.0, 20)
    garment = grid_box(11.0, 20, inZMin=-2.9)
    vol = cm.build_clip_volume(
        [garment], {"Body": body}, inPush=1.0, inVoxelSize=1.0, inInset=0.0, inInnerDepth=3.0, inMaxHeight=10.0
    )
    check = cm.verify_clip(vol.verts, vol.tris, {"Body": body}, vol.expected, vol.guardPoints)
    target = check.targets["Body"]
    ring = [i for i, p in enumerate(body[0]) if abs(p[2] + 3.0) < 1e-9]
    assert len(ring) == 80 and not any(i in vol.expected["Body"] for i in ring)
    assert target.over == []
    assert not any(i in target.clipped for i in ring)
    assert vol.stats["forbidden"] > 0
    assert check.closed and check.guard_ratio() == 1.0


def test_voxel_volume_encloses_occluder_and_push_points():
    """클립이 덮는 메쉬를 감싼다(갈림길 3, 6.5 실기 지적) - 덮는 면 버텍스 g와 푸쉬 점 g + d·n이 전부 클립 안이다.

    감쌀 점은 칸 강제 점유로 버텍스 단위로는 늘 안이다 - **버텍스 사이**(덮는 면 무게중심)까지 감싸는 것은 관대한 점유의 몫이다.
    보수적 점유(8꼭짓점 AND)는 바깥 면을 최대 √3·s 깎아 깎임이 d(0.25)를 넘으면 무게중심이 밖으로 나간다(실기 Shoes 포함 56%, probe r15).
    """
    body = grid_box(10.0, 4)
    garment = grid_box(11.0, 4, inZMin=-2.5)
    vol = cm.build_clip_volume(
        [garment], {"Body": body}, inPush=0.25, inVoxelSize=1.0, inInset=0.0, inInnerDepth=3.0, inMaxHeight=10.0
    )
    check = cm.verify_clip(vol.verts, vol.tris, {"Body": body}, vol.expected, vol.guardPoints)
    assert check.guardTotal == 2 * len(garment[0])
    assert check.guardInside == check.guardTotal
    gv, gt = garment
    centroids = [tuple(sum(gv[i][k] for i in t) / 3.0 for k in range(3)) for t in gt]
    assert all(cm.classify_vertices(centroids, vol.verts, vol.tris))
    assert check.passed()


def test_guard_ratio_without_points_is_one():
    check = cm.verify_clip(*cube(1.0), {"Body": cube(0.5)}, None)
    assert check.guardTotal == 0 and check.guard_ratio() == 1.0


def _channel_grid():
    """보정이 통로를 막아 공동을 만드는 격자 - 꽉 찬 상자 안에 주머니(3,3,2)와 위로 뚫린 통로(3,3,3~7),
    통로 칸 (3,3,5)와 대각으로만 맞닿는 두 번째 통로(4,4,5 -> +x)."""
    g = cm.VoxelGrid((0.0, 0.0, 0.0), 1.0, (9, 9, 9))
    for k in range(1, 8):
        for j in range(1, 8):
            for i in range(1, 8):
                g.occ[g.index(i, j, k)] = 1
    for cell in [(3, 3, 2)] + [(3, 3, k) for k in range(3, 8)] + [(4, 4, 5), (5, 4, 5), (6, 4, 5), (7, 4, 5)]:
        g.occ[g.index(*cell)] = 0
    return g


def test_close_grid_refills_cavity_created_by_fix():
    """보정이 막아 만든 공동까지 메운다.

    처음엔 공동이 없다(통로가 바깥에 닿는다). 보정이 대각 접촉을 풀려고 통로 칸을 채우면 주머니가 바깥에서 끊긴다 -
    재메움이 없으면 그 공동이 겉면의 안쪽 껍질이 되어 엔진 홀짝을 뒤집는다. (정답 도형에서 처음 관측됐지만 격자
    어긋남 뒤에는 그 도형에서 재현되지 않아, 판별력을 위해 격자를 손으로 구성한다 - 2.11 변이)
    """
    assert cm.fill_cavities(_channel_grid()) == 0
    noRefill = _channel_grid()
    cm.fill_cavities(noRefill)
    assert cm.fix_nonmanifold(noRefill) > 0
    assert cm.fill_cavities(noRefill) > 0  # 보정이 공동을 만들었다
    grid = _channel_grid()
    cavities, fixed = cm.close_grid(grid)
    assert fixed > 0 and cavities > 0
    assert cm.fill_cavities(grid) == 0
    assert grid.get(3, 3, 2) == 1
    assert cm.is_mesh_closed(*cm.extract_surface(grid))


# ---------------------------------------------------------------------------
# 감축 - 닫힘 보존·수축 전용 (PRD A10)
# ---------------------------------------------------------------------------


def _voxels(inDims, inCells):
    g = cm.VoxelGrid((0.0, 0.0, 0.0), 1.0, inDims)
    for c in inCells:
        g.occ[g.index(*c)] = 1
    return cm.extract_surface(g)


def test_decimate_voxel_box_to_exact_cube():
    verts, tris = _voxels((5, 5, 5), [(i, j, k) for i in range(1, 4) for j in range(1, 4) for k in range(1, 4)])
    assert len(tris) == 108
    v2, t2, stats = cm.decimate(verts, tris, 12)
    assert len(t2) == 12 and stats.reachedTarget
    assert cm.is_mesh_closed(v2, t2)
    assert cm.signed_volume(v2, t2) == pytest.approx(27.0)
    corners = {(float(x), float(y), float(z)) for x in (1, 4) for y in (1, 4) for z in (1, 4)}
    assert set(v2) == corners


def test_decimate_keeps_closedness_and_genus_of_ring():
    ring = [(i, j, k) for i in range(1, 7) for j in range(1, 7) for k in (1, 2) if not (2 < i < 5 and 2 < j < 5)]
    verts, tris = _voxels((8, 8, 4), ring)
    assert cm.is_mesh_closed(verts, tris) and _euler(verts, tris) == 0
    v2, t2, stats = cm.decimate(verts, tris, 40)
    assert cm.is_mesh_closed(v2, t2)
    assert _euler(v2, t2) == 0  # 종수 1 유지
    assert set(v2) <= set(verts)  # 새 좌표를 만들지 않는다
    assert len(t2) < len(tris) and stats.collapses > 0


def test_decimate_link_condition_keeps_small_ring_closed():
    """구멍 1칸짜리 고리를 최소 한계까지 몰아도 닫힘·종수를 지킨다.

    link 조건이 없으면 이 도형이 비다양체로 접혀 닫힘을 잃는다(실측 오일러 4) - 다른 거부(중복·퇴화·뒤집힘)로는 막히지
    않는 경우다. 큰 고리(``test_decimate_keeps_closedness_and_genus_of_ring``)는 link 조건 없이도 통과해 판별력이 없었다(2.14 변이).
    """
    cells = [(i, j, 1) for i in range(1, 4) for j in range(1, 4) if (i, j) != (2, 2)]
    verts, tris = _voxels((5, 5, 3), cells)
    v2, t2, stats = cm.decimate(verts, tris, 8)
    assert cm.is_mesh_closed(v2, t2)
    assert _euler(v2, t2) == 0
    assert stats.rejected.get(cm.REJECT_LINK, 0) > 0


def test_decimate_is_shrink_only_groove_stays_outside():
    """홈 안(원 부피 밖)의 점은 감축 뒤에도 밖이다 - 부피를 밖으로 부풀리면 과다 클립이 된다(수축 전용 축)."""
    cells = [(i, j, k) for i in range(1, 7) for j in range(1, 7) for k in range(1, 4) if not (k == 3 and 3 <= i <= 4)]
    verts, tris = _voxels((8, 8, 5), cells)
    groove = [(4.0, float(j) + 0.5, 3.6) for j in range(1, 7)]  # 홈 바닥(z 3) 위, 원 윗면(z 4) 아래
    assert cm.classify_vertices(groove, verts, tris) == [False] * len(groove)
    v2, t2, stats = cm.decimate(verts, tris, 12)
    assert cm.is_mesh_closed(v2, t2)
    assert cm.classify_vertices(groove, v2, t2) == [False] * len(groove)
    assert cm.signed_volume(v2, t2) <= cm.signed_volume(verts, tris) + 1e-9
    assert stats.rejected.get(cm.REJECT_GROW, 0) > 0


def test_decimate_max_shrink_limits_collapses():
    sphere = [
        (i, j, k) for i in range(12) for j in range(12) for k in range(12)
        if (i - 5.5) ** 2 + (j - 5.5) ** 2 + (k - 5.5) ** 2 <= 25
    ]
    verts, tris = _voxels((12, 12, 12), sphere)
    free = cm.decimate(verts, tris, 50)
    limited = cm.decimate(verts, tris, 50, inMaxShrink=0.2)
    assert free[2].trianglesAfter < limited[2].trianglesAfter
    assert not limited[2].reachedTarget
    assert limited[2].rejected.get(cm.REJECT_SHRINK_LIMIT, 0) > 0
    assert cm.is_mesh_closed(limited[0], limited[1])


def test_decimate_tetrahedron_is_not_flattened():
    verts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    tris = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2)]
    assert cm.is_mesh_closed(verts, tris)
    v2, t2, stats = cm.decimate(verts, tris, 2)
    assert len(t2) == 4 and not stats.reachedTarget
    assert cm.is_mesh_closed(v2, t2)


@pytest.fixture(scope="module")
def half_cover_fine():
    body = grid_box(10.0, 8)
    garment = grid_box(11.0, 8, inZMin=-2.4)
    vol = cm.build_clip_volume(
        [garment], {"Body": body}, inPush=1.0, inVoxelSize=1.0, inInset=0.0, inInnerDepth=3.0, inMaxHeight=10.0
    )
    return body, vol


def test_decimate_clip_volume_guarded_growth(half_cover_fine):
    """보호된 성장 조립(갈림길 2) - 작은 F까지 줄여도 닫힘·과다 0, 과소는 감축 전 이하.

    "수축 전용보다 낫다"는 이 도형으로는 드러나지 않는다(둘 다 F 60·과소 0) - 실기 3슬롯 실측(probe r09·r10, PRD §9 갈림길 2)이 근거다.
    가드 각각의 판별력은 아래 두 도형이 따로 고정한다.
    """
    body, vol = half_cover_fine
    targets = {"Body": body}
    before = cm.verify_clip(vol.verts, vol.tris, targets, vol.expected).targets["Body"]
    verts, tris, stats = cm.decimate_clip_volume(vol, targets, 60)
    check = cm.verify_clip(verts, tris, targets, vol.expected)
    after = check.targets["Body"]
    assert check.closed
    assert after.over == []
    assert len(after.under) <= len(before.under)
    assert len(tris) <= 60 and stats.reachedTarget


def test_decimate_clip_volume_keeps_guard_points_inside(half_cover_fine):
    """감축이 바깥 면을 덮는 메쉬 안쪽으로 끌어들이지 않는다 - 감축 전 안이던 감쌀 점은 감축 뒤에도 안이다(갈림길 3).

    유지 점에 감쌀 점을 넣지 않으면 실기 Shoes 포함률이 감축에서 56% -> 48%로 떨어졌다(probe r15).
    """
    body, vol = half_cover_fine
    targets = {"Body": body}
    before = cm.verify_clip(vol.verts, vol.tris, targets, vol.expected, vol.guardPoints)
    verts, tris, _stats = cm.decimate_clip_volume(vol, targets, 60)
    after = cm.verify_clip(verts, tris, targets, vol.expected, vol.guardPoints)
    assert before.guardInside == before.guardTotal > 0
    assert after.guardInside == before.guardInside
    assert after.passed()


def test_decimate_guard_checks_both_orientations_lumpy_garment():
    """쓸린 사면체는 **방향과 무관하게** 보호 점을 품으면 안 된다 - 수축 사면체가 밖의 보호 점을 품으면 접힘(감김수 -1)으로 "안"이 된다.

    수축 쪽에서 유지 점만 보던 규칙은 이 도형(울퉁불퉁한 구 바디 + 아래가 열린 옷, F 250)에서 과다 1을 냈다(실기 Upper와 같은 기제,
    probe r19·r20·r22). 복셀 부피 자체는 과다 0이다 - 과다는 감축에서만 생긴다.
    """
    body = lumpy(uv_sphere(10.0, 32, 16), 1.5)
    garment = lumpy(uv_sphere(11.2, 20, 10, inZMin=-3.0), 1.5)
    targets = {"Body": body}
    vol = cm.build_clip_volume([garment], targets, 1.0, 1.0, 0.0, 3.0, 10.0)
    assert cm.verify_clip(vol.verts, vol.tris, targets, vol.expected).passed()
    verts, tris, _stats = cm.decimate_clip_volume(vol, targets, 250)
    check = cm.verify_clip(verts, tris, targets, vol.expected)
    assert check.closed
    assert check.targets["Body"].over == []


def test_guard_capture_keeps_protected_point_in_groove_outside():
    """성장이 홈을 메우면 홈 안의 보호 점이 삼켜진다 - capture 검사가 그 붕괴를 거부한다."""
    cells = [(i, j, k) for i in range(1, 7) for j in range(1, 7) for k in range(1, 4) if not (k == 3 and 3 <= i <= 4)]
    verts, tris = _voxels((8, 8, 5), cells)
    protect = [(4.0, float(j) + 0.5, 3.6) for j in range(1, 7)]
    v2, t2, stats = cm.decimate(verts, tris, 12, inProtect=protect, inKeep=[])
    assert cm.is_mesh_closed(v2, t2)
    assert cm.classify_vertices(protect, v2, t2) == [False] * len(protect)
    assert stats.rejected.get(cm.REJECT_CAPTURE, 0) > 0


def test_guard_release_keeps_inner_points_inside():
    """수축이 볼록 계단을 깎으면 표면 바로 안쪽 점이 밖으로 나간다 - release 검사가 그 붕괴를 거부한다(수축 전용 대조군은 놓친다)."""
    sphere = [
        (i, j, k) for i in range(12) for j in range(12) for k in range(12)
        if (i - 5.5) ** 2 + (j - 5.5) ** 2 + (k - 5.5) ** 2 <= 25
    ]
    verts, tris = _voxels((12, 12, 12), sphere)
    inside = cm.classify_vertices([(i + 0.5, j + 0.5, k + 0.5) for i, j, k in sphere], verts, tris)
    keep = [(i + 0.5, j + 0.5, k + 0.5) for (i, j, k), flag in zip(sphere, inside) if flag]
    assert len(keep) == len(sphere)
    sv, st, _ = cm.decimate(verts, tris, 50)
    assert not all(cm.classify_vertices(keep, sv, st))  # 대조군: 수축 전용은 칸 중심을 놓는다
    gv, gt, stats = cm.decimate(verts, tris, 50, inProtect=[], inKeep=keep)
    assert cm.is_mesh_closed(gv, gt)
    assert all(cm.classify_vertices(keep, gv, gt))
    assert stats.rejected.get(cm.REJECT_RELEASE, 0) > 0


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


# ---------------------------------------------------------------------------
# Alpha Wrap 경로 - 기둥 수프·비율 환산·주입형 감싸기와 과다 반복 제거 (2026-10-23)
# ---------------------------------------------------------------------------


def _single_prism():
    """덮는 면 하나(+Z를 보는 반시계)의 기둥 - 위 z 1, 아래 z -1."""
    tops = [(0.0, 0.0, 1.0), (2.0, 0.0, 1.0), (0.0, 2.0, 1.0)]
    bottoms = [(0.0, 0.0, -1.0), (2.0, 0.0, -1.0), (0.0, 2.0, -1.0)]
    coverage = cm.Coverage(tops, bottoms, [1.0, 1.0, 1.0], [cm.COVER_COVERED], [0], set())
    return coverage, [(0, 1, 2)]


def test_prism_soup_single_prism_is_closed_outward_prism():
    coverage, tris = _single_prism()
    verts, soup = cm.prism_soup(coverage, tris)
    assert len(soup) == 8
    assert verts == coverage.tops + coverage.bottoms
    assert cm.is_mesh_closed(verts, soup)
    assert cm.signed_volume(verts, soup) == pytest.approx(4.0)  # 밑넓이 2 x 높이 2, 바깥 향이면 +


def test_prism_soup_counts_eight_per_prism_and_keeps_shared_sides(half_cover_fine):
    body, _vol = half_cover_fine
    garment = grid_box(11.0, 8, inZMin=-2.4)
    prism = cm.build_prism_volume([garment], {"Body": body}, 1.0, 0.0, 3.0, 10.0)
    verts, soup = cm.prism_soup(prism.coverage, prism.occTris)
    assert len(soup) == 8 * len(prism.coverage.prismTris) > 0
    sides = {}
    for t in soup:
        key = frozenset(t)
        sides[key] = sides.get(key, 0) + 1
    assert max(sides.values()) == 1  # 공유 옆면은 양쪽 감김이 반대라 같은 삼각형이 두 번 나오지 않는다
    assert len(verts) == 2 * len(prism.occVerts)


def test_build_prism_volume_matches_voxel_path(half_cover):
    body, vol = half_cover
    garment = grid_box(11.0, 4, inZMin=-2.5)
    prism = cm.build_prism_volume([garment], {"Body": body}, 1.0, 0.0, 3.0, 10.0)
    assert prism.expected == vol.expected
    assert prism.guardPoints == vol.guardPoints
    assert len(prism.protectPoints) == len(body[0]) - len(vol.expected["Body"])


@pytest.mark.parametrize(
    "triangles, ratio, budget",
    [(20396, 10.0, 2040), (168516, 10.0, 16852), (169432, 10.0, 16944), (1000, 100.0, 0), (10, 1.0, 4), (1000, 0.5, 5)],
)
def test_face_budget_from_ratio(triangles, ratio, budget):
    assert cm.face_budget_from_ratio(triangles, ratio) == budget


@pytest.mark.parametrize("ratio", [0.0, -1.0, 100.5])
def test_face_budget_from_ratio_rejects_out_of_range(ratio):
    with pytest.raises(ValueError):
        cm.face_budget_from_ratio(1000, ratio)


@pytest.fixture(scope="module")
def half_prism():
    body = grid_box(10.0, 4)
    garment = grid_box(11.0, 4, inZMin=-2.5)
    return body, cm.build_prism_volume([garment], {"Body": body}, 1.0, 0.0, 3.0, 10.0)


class _FakeWrap:
    """감싸기 가짜 - 호출 인자를 기록하고, ``inLeak`` 기둥이 수프에 있으면 보호 점 하나를 품는 상자를 돌려준다."""

    def __init__(self, inLeakTri=None, inLeakPoint=None):
        self.calls = []
        self._leakTri = inLeakTri
        self._leakPoint = inLeakPoint

    def __call__(self, inVerts, inTris, inAlpha, inOffset):
        self.calls.append((list(inVerts), list(inTris), inAlpha, inOffset))
        leaking = self._leakTri is not None and tuple(self._leakTri) in {tuple(t) for t in inTris}
        verts, tris = cube(0.5, self._leakPoint if leaking else (100.3, 100.7, 100.1))
        return verts, tris, {"output_faces": len(tris), "output_vertices": len(verts)}


def test_wrap_clip_volume_passes_soup_and_returns_wrap_result(half_prism):
    _body, prism = half_prism
    fake = _FakeWrap()
    vol = cm.wrap_clip_volume(prism, 1.25, 0.125, fake, 0.0, 5)
    assert len(fake.calls) == 1
    verts, tris, alpha, offset = fake.calls[0]
    assert (verts, tris) == cm.prism_soup(prism.coverage, prism.occTris)
    assert (alpha, offset) == (1.25, 0.125)
    assert (vol.verts, vol.tris) == cube(0.5, (100.3, 100.7, 100.1))
    assert vol.expected is prism.expected and vol.guardPoints is prism.guardPoints
    assert vol.stats["wrap_output_faces"] == 12 and vol.stats["pruneIterations"] == 0
    assert vol.stats["prismsKept"] == vol.stats["prisms"] == len(prism.coverage.prismTris)
    assert vol.iterations == [{"prisms": len(prism.coverage.prismTris), "triangles": 12, "over": 0}]


def _leak_setup(inPrism):
    """보호 점과 가장 가까운 기둥 쌍 - 반경을 그 거리로 두면 그 근처 기둥만 빠진다(먼 쌍이면 반경이 커져 전부 빠진다)."""
    cov = inPrism.coverage
    best = None
    for ti in cov.prismTris:
        for vi in inPrism.occTris[ti]:
            for p in inPrism.protectPoints:
                d = math.dist(p, cov.bottoms[vi])
                if best is None or d < best[0]:
                    best = (d, ti, p)
    dist, ti, leak = best
    return inPrism.occTris[ti], leak, dist


def test_wrap_clip_volume_prunes_prisms_around_over_points(half_prism):
    """과다 반복 제거(PRD B8) - 1회차에 보호 점이 안이면 그 점을 품는 기둥을 빼고 다시 감싸 과다 0으로 멈춘다."""
    _body, prism = half_prism
    leakTri, leak, dist = _leak_setup(prism)
    fake = _FakeWrap(leakTri, leak)
    vol = cm.wrap_clip_volume(prism, 1.0, 0.1, fake, dist, 5)
    assert len(fake.calls) == 2
    first, second = len(fake.calls[0][1]), len(fake.calls[1][1])
    assert second < first and (first - second) % 8 == 0
    assert tuple(leakTri) not in {tuple(t) for t in fake.calls[1][1]}
    assert vol.stats["pruneIterations"] == 1 and vol.stats["overRemaining"] == 0
    assert vol.stats["prismsKept"] == second // 8 < vol.stats["prisms"]
    assert [it["over"] for it in vol.iterations] == [1, 0]


def test_wrap_clip_volume_stops_at_max_iterations(half_prism):
    _body, prism = half_prism
    leakTri, leak, dist = _leak_setup(prism)
    fake = _FakeWrap(leakTri, leak)
    vol = cm.wrap_clip_volume(prism, 1.0, 0.1, fake, dist, 0)
    assert len(fake.calls) == 1
    assert vol.stats["overRemaining"] == 1 and vol.stats["pruneIterations"] == 0


def test_wrap_clip_volume_rejects_bad_params(half_prism):
    _body, prism = half_prism
    for args in ((0.0, 0.1, 0.0, 1), (1.0, 0.0, 0.0, 1), (1.0, 0.1, -0.1, 1), (1.0, 0.1, 0.0, -1)):
        with pytest.raises(ValueError):
            cm.wrap_clip_volume(prism, args[0], args[1], _FakeWrap(), args[2], args[3])


def test_wrap_clip_volume_without_prisms_does_not_call_wrap():
    body = grid_box(10.0, 2)
    far = cube(5.0, (0.0, 0.0, 60.0))  # Hmax 10 밖 - 덮는 면 0
    prism = cm.build_prism_volume([far], {"Body": body}, 1.0, 0.0, 3.0, 10.0)
    fake = _FakeWrap()
    vol = cm.wrap_clip_volume(prism, 1.0, 0.1, fake, 0.0, 3)
    assert fake.calls == [] and vol.tris == [] and vol.stats["prisms"] == 0


def test_half_cover_real_native_wrap_is_closed_without_over(half_prism):
    """정답 도형에서 실제 네이티브로 - 닫힘·과다 0, |E|·|C|·포함률을 같이 단정한다(대상이 비지 않았는지).

    감싼 결과는 E를 대부분 자른다(과소 비율 상한 0.5 - 반복 제거가 기둥을 빼면 과소가 생긴다, B8). 감축(비율 50%)을 거쳐도 닫힘·과다 0.
    """
    native = pytest.importorskip("pyjallib.native")
    body, prism = half_prism
    targets = {"Body": body}
    vol = cm.wrap_clip_volume(prism, 1.0, 0.05, native.alpha_wrap, 0.0, 8)
    check = cm.verify_clip(vol.verts, vol.tris, targets, vol.expected, vol.guardPoints)
    target = check.targets["Body"]
    assert check.closed and target.over == []
    assert len(vol.expected["Body"]) == 57 and len(target.clipped) > 0
    assert target.under_ratio() < 0.5
    assert check.guard_ratio() > 0.5
    budget = cm.face_budget_from_ratio(len(vol.tris), 50.0)
    dv, dt, _stats = cm.decimate_clip_volume(vol, targets, budget)
    after = cm.verify_clip(dv, dt, targets, vol.expected)
    assert after.closed and after.targets["Body"].over == []


def test_prism_distance_inside_zero_and_outside_exact():
    coverage, tris = _single_prism()  # 밑변 (0,0)-(2,0)-(0,2), z -1..1
    assert cm.prism_distance((0.4, 0.3, 0.2), tris[0], coverage.tops, coverage.bottoms) == 0.0
    assert cm.prism_distance((0.5, 0.5, 3.0), tris[0], coverage.tops, coverage.bottoms) == pytest.approx(2.0)
    assert cm.prism_distance((2.0, 2.0, 0.0), tris[0], coverage.tops, coverage.bottoms) == pytest.approx(math.sqrt(2.0))


def test_wrap_clip_volume_keeps_large_prism_whose_bbox_but_not_shape_is_near():
    """제거는 형상까지의 거리로 판정한다(실기 판정 1회차 "구멍") - 큰 덮는 면의 bbox + R 안이어도 빗변에서 먼 과다 점은 기둥을 빼지 않는다.

    직각삼각형 (0,0)-(10,0)-(0,10) 기둥과 점 (9, 9): bbox(0..10) 안이지만 빗변까지 약 5.66. 반경 1.1이면 남아야 한다 - 처음 규칙
    (bbox + R)은 이 기둥을 뺐다. 감싸기 가짜는 이 기둥이 있으면 그 점을 품는 상자를 돌려준다 -> 과다가 남고 더 뺄 것이 없어 멈춘다.
    """
    tops = [(0.0, 0.0, 1.0), (10.0, 0.0, 1.0), (0.0, 10.0, 1.0)]
    bottoms = [(0.0, 0.0, -1.0), (10.0, 0.0, -1.0), (0.0, 10.0, -1.0)]
    coverage = cm.Coverage(tops, bottoms, [1.0, 1.0, 1.0], [cm.COVER_COVERED], [0], set())
    occTris = [(0, 1, 2)]
    leak = (9.0, 9.0, 0.0)
    prism = cm.PrismVolume(
        occVerts=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0)], occTris=occTris, coverage=coverage,
        union=cm.build_prism_union(coverage, occTris), expected={"Body": set()}, guardPoints=[], protectPoints=[leak],
    )
    fake = _FakeWrap((0, 1, 2), leak)
    vol = cm.wrap_clip_volume(prism, 1.0, 0.1, fake, 0.0, 5)
    assert len(fake.calls) == 1
    assert vol.stats["prismsKept"] == 1 and vol.stats["overRemaining"] == 1 and vol.stats["pruneIterations"] == 0
