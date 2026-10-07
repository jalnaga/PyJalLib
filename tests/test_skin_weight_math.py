# -*- coding: utf-8 -*-
"""pyjallib.max.skinWeightMath 순수 연산 테스트 (Type A).

항등식(합 == 1, 잠금 본 불변, 대칭 맵 대합성)과 경계(빈 입력, 합 0, 본 제한 == 본 수)를
단정한다. 소프트 셀렉션은 **2026-10-06 Phase 0 실측치**(3ds Max 2024가 계산한 값)를 기대값으로
고정한다 - 공식만 맞추는 것이 아니라 Max와 같은 값이 나오는지가 판정 축이다.
"""

import math
from pathlib import Path

import pytest

from pyjallib.max import skinWeightMath as swm

# ---------------------------------------------------------------------------
# 공용 픽스처
# ---------------------------------------------------------------------------


def _grid(inSegs: int, inSize: float):
    """Plane과 같은 배치(행 우선, x가 먼저 증가)의 격자 위치와 엣지 목록."""
    n = inSegs + 1
    step = inSize / inSegs
    half = inSize / 2.0
    positions = [(-half + step * i, -half + step * j, 0.0) for j in range(n) for i in range(n)]
    edges = []
    for j in range(n):
        for i in range(n):
            v = j * n + i
            if i + 1 < n:
                edges.append((v, v + 1))
            if j + 1 < n:
                edges.append((v, v + n))
    return positions, edges


def _pair_sum(inPair):
    return sum(inPair[1])


# ---------------------------------------------------------------------------
# 순수성
# ---------------------------------------------------------------------------


def test_module_has_no_pymxs_or_numpy_import():
    """라이브러리 경계: stdlib만 쓴다(DCC 내장 Python 이식성)."""
    text = Path(swm.__file__).read_text(encoding="utf-8")
    assert "import pymxs" not in text and "from pymxs" not in text
    assert "numpy" not in text.split('"""', 2)[2]  # docstring 밖


# ---------------------------------------------------------------------------
# 정규화 / 믹스
# ---------------------------------------------------------------------------


def test_normalize_sums_to_one():
    assert sum(swm.normalize_weights([1.0, 3.0])) == pytest.approx(1.0)
    assert swm.normalize_weights([1.0, 3.0]) == pytest.approx([0.25, 0.75])


def test_normalize_zero_sum_gives_first_full_and_keeps_length():
    assert swm.normalize_weights([0.0, 0.0, 0.0]) == [1.0, 0.0, 0.0]


def test_normalize_empty():
    assert swm.normalize_weights([]) == []


def test_mix_weights_ratio_sum_and_order():
    a = ([3, 1], [0.6, 0.4])
    b = ([2], [1.0])
    ids, ws = swm.mix_weights([a, b], [0.5, 0.5])
    assert ids == [1, 2, 3]
    assert ws == pytest.approx([0.2, 0.5, 0.3])
    assert sum(ws) == pytest.approx(1.0)


def test_mix_weights_drops_tiny_and_zero_ratio():
    a = ([1, 2], [0.9995, 0.0005])
    b = ([7], [1.0])
    ids, ws = swm.mix_weights([a, b], [1.0, 0.0])
    assert ids == [1]
    assert ws == pytest.approx([0.9995])


def test_mix_weights_bone_limit_cuts_smallest_and_renormalizes():
    pair = ([1, 2, 3, 4], [0.1, 0.4, 0.2, 0.3])
    ids, ws = swm.mix_weights([pair], [1.0], inBoneLimit=2)
    assert ids == [2, 4]
    assert ws == pytest.approx([0.4 / 0.7, 0.3 / 0.7])
    assert sum(ws) == pytest.approx(1.0)


def test_mix_weights_bone_limit_ties_cut_from_back():
    pair = ([1, 2, 3], [0.25, 0.25, 0.5])
    ids, ws = swm.mix_weights([pair], [1.0], inBoneLimit=2)
    assert ids == [1, 3]
    assert ws == pytest.approx([1 / 3, 2 / 3])


def test_mix_weights_bone_limit_equal_count_untouched():
    pair = ([1, 2], [0.3, 0.7])
    assert swm.mix_weights([pair], [1.0], inBoneLimit=2) == ([1, 2], pytest.approx([0.3, 0.7]))


def test_mix_weights_length_mismatch_raises():
    with pytest.raises(ValueError):
        swm.mix_weights([([1], [1.0])], [0.5, 0.5])


def test_mix_weights_empty():
    assert swm.mix_weights([], []) == ([], [])


# ---------------------------------------------------------------------------
# 잠금 / 강체
# ---------------------------------------------------------------------------


def test_solve_locked_keeps_locked_value_and_sum_one():
    original = ([1, 2, 3], [0.2, 0.3, 0.5])
    new = ([1, 2, 3], [0.6, 0.1, 0.3])
    ids, ws = swm.solve_locked_weights(original, new, {2})
    result = dict(zip(ids, ws))
    assert result[2] == pytest.approx(0.3)
    assert sum(ws) == pytest.approx(1.0)
    # 비잠금 1,3은 새 비율(0.6:0.3)을 유지하며 0.7을 나눈다
    assert result[1] / result[3] == pytest.approx(2.0)


def test_solve_locked_pinned_bone_value_fixed():
    original = ([1, 2, 3], [0.2, 0.3, 0.5])
    new = ([1, 2, 3], [0.6, 0.1, 0.3])
    ids, ws = swm.solve_locked_weights(original, new, {2}, inPinnedBone=1)
    result = dict(zip(ids, ws))
    assert result[1] == pytest.approx(0.6)
    assert result[2] == pytest.approx(0.3)
    assert result[3] == pytest.approx(0.1)
    assert ids == [3, 2, 1]  # 비잠금 + 잠금 + 고정 순서


def test_solve_locked_pinned_clamped_to_remaining():
    original = ([1, 2], [0.5, 0.5])
    new = ([1, 2], [0.9, 0.1])
    ids, ws = swm.solve_locked_weights(original, new, {2}, inPinnedBone=1)
    result = dict(zip(ids, ws))
    assert result[1] == pytest.approx(0.5)  # 잠금 0.5 + 고정 0.9 > 1 -> 0.5로 깎임
    assert sum(ws) == pytest.approx(1.0)


def test_solve_locked_no_unlocked_in_new_falls_back_to_original():
    original = ([1, 2], [0.4, 0.6])
    new = ([2], [1.0])
    ids, ws = swm.solve_locked_weights(original, new, {2})
    result = dict(zip(ids, ws))
    assert result[2] == pytest.approx(0.6)
    assert result[1] == pytest.approx(0.4)


def test_rigid_average():
    pairs = [([1], [1.0]), ([2], [1.0]), ([1, 2], [0.5, 0.5])]
    ids, ws = swm.rigid_average(pairs)
    assert ids == [1, 2]
    assert ws == pytest.approx([0.5, 0.5])
    assert swm.rigid_average([]) == ([], [])


# ---------------------------------------------------------------------------
# 본 이름 대칭
# ---------------------------------------------------------------------------

_BONES = [
    "spine",
    "Arm_L",
    "Arm_R",
    "L_Hand",
    "R_Hand",
    "LeftLeg",
    "RightLeg",
    "x_L_y",
    "x_R_y",
    "L Foot",
    "R Foot",
    "Lonely_L",
]


def test_mirror_bone_map_pairs_and_self():
    m = swm.build_mirror_bone_map(_BONES)
    named = {_BONES[i]: _BONES[j] for i, j in enumerate(m)}
    assert named["spine"] == "spine"
    assert named["Arm_L"] == "Arm_R" and named["Arm_R"] == "Arm_L"
    assert named["LeftLeg"] == "RightLeg" and named["RightLeg"] == "LeftLeg"
    assert named["x_L_y"] == "x_R_y"
    assert named["Lonely_L"] == "Lonely_L"


def test_mirror_bone_map_prefix_patterns_fixed():
    """원본 결함 수정: 접두 패턴이 ``L_Hand -> R__Hand``가 아니라 ``R_Hand``가 된다."""
    m = swm.build_mirror_bone_map(_BONES)
    named = {_BONES[i]: _BONES[j] for i, j in enumerate(m)}
    assert named["L_Hand"] == "R_Hand"
    assert named["L Foot"] == "R Foot"
    assert swm.mirror_bone_name_candidates("L_Hand")[0] == "R_Hand"


def test_mirror_bone_map_is_involution():
    m = swm.build_mirror_bone_map(_BONES)
    assert all(m[m[i]] == i for i in range(len(_BONES)))


def test_mirror_bone_map_requires_scene_existence():
    """씬에 없는 이름은 짝이 되지 않는다(원본 getNodeByName 확인)."""
    m = swm.build_mirror_bone_map(["Arm_L"], inSceneNames=["Arm_L"])
    assert m == [0]


def test_mirror_bone_map_case_insensitive_lookup_returns_actual_bone():
    bones = ["arm_l", "Arm_R"]
    m = swm.build_mirror_bone_map(bones, inSceneNames=bones)
    assert m == [1, 0]


def test_mirror_bone_map_custom_patterns():
    bones = ["hand.lf", "hand.rt"]
    m = swm.build_mirror_bone_map(bones, inPatterns=[("*.lf", "*.rt")])
    assert m == [1, 0]


# ---------------------------------------------------------------------------
# 위치 / 토폴로지 대칭
# ---------------------------------------------------------------------------


def test_spatial_grid_query_and_bad_cell():
    positions, _ = _grid(4, 10.0)
    grid = swm.build_spatial_grid(positions, 2.5)
    assert sorted(grid.query_cube(grid.cell_of(positions[12]), 0)) == [12]
    with pytest.raises(ValueError):
        swm.SpatialGrid(positions, 0.0)


def test_mirror_vertex_map_by_position_symmetric_grid():
    positions, _ = _grid(4, 10.0)
    m = swm.mirror_vertex_map_by_position(positions)
    for v, mv in enumerate(m):
        assert positions[mv][0] == pytest.approx(-positions[v][0])
        assert positions[mv][1] == pytest.approx(positions[v][1])
    assert all(m[m[v]] == v for v in range(len(m)))
    assert m[12] == 12  # 중심


def test_mirror_vertex_map_by_position_other_axis():
    positions, _ = _grid(4, 10.0)
    m = swm.mirror_vertex_map_by_position(positions, inAxis=1)
    assert positions[m[0]][1] == pytest.approx(5.0)
    with pytest.raises(ValueError):
        swm.mirror_vertex_map_by_position(positions, inAxis=3)


def test_mirror_vertex_map_by_position_no_partner_is_self():
    positions = [(10.0, 0.0, 0.0), (200.0, 0.0, 0.0)]
    m = swm.mirror_vertex_map_by_position(positions, inMaxRange=2)
    assert m == [0, 1]


def test_build_adjacency_edge_order_and_dedupe():
    adj = swm.build_adjacency(3, [(0, 1), (1, 2), (0, 1), (2, 2)])
    assert adj == [[1], [0, 2], [1]]


def test_mirror_vertex_map_by_topology_matches_position_on_symmetric_mesh():
    positions, edges = _grid(4, 10.0)
    adj = swm.build_adjacency(len(positions), edges)
    topo = swm.mirror_vertex_map_by_topology(adj, positions, 12)
    pos = swm.mirror_vertex_map_by_position(positions)
    assert len(topo) == len(positions)  # 전부 도달
    assert all(topo[v] == pos[v] for v in topo)
    assert all(topo[topo[v]] == v for v in topo)


def test_mirror_vertex_map_by_topology_survives_position_noise():
    """위치가 조금 흐트러져도(비대칭 노이즈) 토폴로지 대칭은 짝을 유지한다."""
    positions, edges = _grid(4, 10.0)
    noisy = [(x + (0.3 if x > 0 else 0.0), y, z) for x, y, z in positions]
    adj = swm.build_adjacency(len(noisy), edges)
    topo = swm.mirror_vertex_map_by_topology(adj, noisy, 12)
    clean = swm.mirror_vertex_map_by_position(positions)
    assert all(topo[v] == clean[v] for v in topo)


def test_mirror_vertex_map_by_topology_bad_center():
    positions, edges = _grid(2, 2.0)
    adj = swm.build_adjacency(len(positions), edges)
    with pytest.raises(ValueError):
        swm.mirror_vertex_map_by_topology(adj, positions, 99)


# ---------------------------------------------------------------------------
# 이웃 탐색
# ---------------------------------------------------------------------------


def test_edge_neighbor_weights_self_half_and_inverse_distance():
    positions = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 2.0, 0.0)]
    verts, ratios, dists = swm.edge_neighbor_weights(0, [1, 2], positions)
    assert verts == [0, 1, 2]
    assert ratios[0] == pytest.approx(0.5)
    assert ratios[1] == pytest.approx(0.5 * (1.0 / (1.0 + 0.5)))
    assert ratios[2] == pytest.approx(0.5 * (0.5 / (1.0 + 0.5)))
    assert sum(ratios) == pytest.approx(1.0)
    assert dists == pytest.approx([0.0, 1.0, 2.0])


def test_edge_neighbor_weights_isolated_vertex():
    assert swm.edge_neighbor_weights(0, [], [(0.0, 0.0, 0.0)]) == ([], [], [])


def test_radius_neighbor_weights_blend_self():
    positions, _ = _grid(4, 10.0)
    grid = swm.build_spatial_grid(positions)
    verts, ratios = swm.radius_neighbor_weights(12, positions, grid, 3.0)
    assert set(verts) == {7, 11, 12, 13, 17}  # 반경 3 미만: 자기 + 엣지 거리 2.5 이웃 4개
    assert ratios[verts.index(12)] == pytest.approx(0.5)
    assert sum(ratios) == pytest.approx(1.0)


def test_radius_neighbor_weights_attach_excludes_and_max_count():
    positions, _ = _grid(4, 10.0)
    grid = swm.build_spatial_grid(positions)
    verts, ratios = swm.radius_neighbor_weights(
        12, positions, grid, 4.0, inMaxCount=4, inExclude={12}, inBlendSelf=False
    )
    assert 12 not in verts
    assert set(verts) == {7, 11, 13, 17}  # 4번째 최근접(2.5) 이하만 - 대각(3.54) 탈락
    assert sum(ratios) == pytest.approx(1.0)


def test_radius_neighbor_weights_none_found():
    positions = [(0.0, 0.0, 0.0), (50.0, 0.0, 0.0)]
    grid = swm.build_spatial_grid(positions)
    assert swm.radius_neighbor_weights(0, positions, grid, 1.0, inExclude={0}) == ([], [])


def test_depth_distances_shortest_path_with_depth_limit():
    positions, edges = _grid(4, 10.0)
    adj = swm.build_adjacency(len(positions), edges)

    def neighbor_fn(v):
        verts, _, dists = swm.edge_neighbor_weights(v, adj[v], positions)
        return verts, dists

    verts, dists = swm.depth_distances(12, neighbor_fn, 2)
    byVert = dict(zip(verts, dists))
    assert verts[0] == 12 and byVert[12] == 0.0
    assert byVert[13] == pytest.approx(2.5)
    assert byVert[14] == pytest.approx(5.0)
    assert byVert[6] == pytest.approx(5.0)  # 대각은 엣지 2개
    assert 0 not in byVert  # 엣지 4개 거리
    assert len(verts) == 13  # 맨해튼 거리 2 이내


# ---------------------------------------------------------------------------
# 소프트 셀렉션 - Phase 0 실측치(Max 2024) 대조
# ---------------------------------------------------------------------------

# Plane 10x10, 4x4 세그먼트, 중심 버텍스 13(1-based) 선택
_MAX_FALLOFF4 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0373, 0.3164, 0.0373, 0.0, 0.0, 0.3164, 1.0, 0.3164, 0.0, 0.0, 0.0373, 0.3164, 0.0373, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
_MAX_EDGEDIST1_FALLOFF4 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3164, 0.0, 0.0, 0.0, 0.3164, 1.0, 0.3164, 0.0, 0.0, 0.0, 0.3164, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
_MAX_EDGEDIST2_FALLOFF6 = [0.0, 0.0, 0.0741, 0.0, 0.0, 0.0, 0.0741, 0.6238, 0.0741, 0.0, 0.0741, 0.6238, 1.0, 0.6238, 0.0741, 0.0, 0.0741, 0.6238, 0.0741, 0.0, 0.0, 0.0, 0.0741, 0.0, 0.0]
_MAX_PINCH05_BUBBLE07_FALLOFF6 = [0.0, 0.1314, 0.2824, 0.1314, 0.0, 0.1314, 0.5179, 0.6238, 0.5179, 0.1314, 0.2824, 0.6238, 1.0, 0.6238, 0.2824, 0.1314, 0.5179, 0.6238, 0.5179, 0.1314, 0.0, 0.1314, 0.2824, 0.1314, 0.0]

# 닫힌 Box 10x10x10, 2x2x2 세그먼트(26 버텍스), 윗면 중앙 버텍스 14(1-based) 선택, falloff 30
_BOX_POSITIONS = [(-5.0, -5.0, 0.0), (0.0, -5.0, 0.0), (5.0, -5.0, 0.0), (-5.0, 0.0, 0.0), (0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (-5.0, 5.0, 0.0), (0.0, 5.0, 0.0), (5.0, 5.0, 0.0), (-5.0, -5.0, 10.0), (0.0, -5.0, 10.0), (5.0, -5.0, 10.0), (-5.0, 0.0, 10.0), (0.0, 0.0, 10.0), (5.0, 0.0, 10.0), (-5.0, 5.0, 10.0), (0.0, 5.0, 10.0), (5.0, 5.0, 10.0), (-5.0, -5.0, 5.0), (0.0, -5.0, 5.0), (5.0, -5.0, 5.0), (5.0, 0.0, 5.0), (5.0, 5.0, 5.0), (0.0, 5.0, 5.0), (-5.0, 5.0, 5.0), (-5.0, 0.0, 5.0)]
_MAX_BOX_BACKFACING_ON = [0.6361, 0.6869, 0.6361, 0.6869, 0.7407, 0.6869, 0.6361, 0.6869, 0.6361, 0.8595, 0.9259, 0.8595, 0.9259, 1.0, 0.9259, 0.8595, 0.9259, 0.8595, 0.7981, 0.8595, 0.7981, 0.8595, 0.7981, 0.8595, 0.7981, 0.8595]
_MAX_BOX_BACKFACING_OFF = [0.0] * 9 + _MAX_BOX_BACKFACING_ON[9:]


def _box_normals():
    """면 위에 놓인 축 방향 법선의 합(정규화) - 박스 버텍스 법선."""
    normals = []
    for x, y, z in _BOX_POSITIONS:
        n = (
            (1.0 if x == 5.0 else -1.0 if x == -5.0 else 0.0),
            (1.0 if y == 5.0 else -1.0 if y == -5.0 else 0.0),
            (1.0 if z == 10.0 else -1.0 if z == 0.0 else 0.0),
        )
        length = math.sqrt(sum(c * c for c in n))
        normals.append(tuple(c / length for c in n))
    return normals


def _rounded(inValues):
    return [round(v, 4) for v in inValues]


def test_affect_region_endpoints():
    assert swm.affect_region(0.0, 4.0, 0.0, 0.0) == pytest.approx(1.0)
    assert swm.affect_region(4.0, 4.0, 0.0, 0.0) == pytest.approx(0.0)
    assert swm.affect_region(5.0, 4.0, 0.0, 0.0) == 0.0
    assert swm.affect_region(1.0, 0.0, 0.0, 0.0) == 0.0


def test_soft_selection_euclid_matches_max():
    positions, _ = _grid(4, 10.0)
    got = swm.soft_selection_weights([12], positions, 4.0)
    assert _rounded(got) == _MAX_FALLOFF4


def test_soft_selection_pinch_bubble_matches_max():
    positions, _ = _grid(4, 10.0)
    got = swm.soft_selection_weights([12], positions, 6.0, inPinch=0.5, inBubble=0.7)
    assert _rounded(got) == _MAX_PINCH05_BUBBLE07_FALLOFF6


def test_soft_selection_edge_distance_is_path_length_matches_max():
    positions, edges = _grid(4, 10.0)
    adj = swm.build_adjacency(len(positions), edges)
    got1 = swm.soft_selection_weights([12], positions, 4.0, inAdjacency=adj, inEdgeDistance=1)
    got2 = swm.soft_selection_weights([12], positions, 6.0, inAdjacency=adj, inEdgeDistance=2)
    assert _rounded(got1) == _MAX_EDGEDIST1_FALLOFF4
    assert _rounded(got2) == _MAX_EDGEDIST2_FALLOFF6


def test_soft_selection_backfacing_matches_max():
    normals = _box_normals()
    on = swm.soft_selection_weights([13], _BOX_POSITIONS, 30.0)
    off = swm.soft_selection_weights(
        [13], _BOX_POSITIONS, 30.0, inNormals=normals, inAffectBackfacing=False
    )
    assert _rounded(on) == _MAX_BOX_BACKFACING_ON
    assert _rounded(off) == _MAX_BOX_BACKFACING_OFF


def test_soft_selection_requires_inputs_and_empty_selection():
    positions, _ = _grid(2, 2.0)
    assert swm.soft_selection_weights([], positions, 4.0) == [0.0] * len(positions)
    with pytest.raises(ValueError):
        swm.soft_selection_weights([0], positions, 4.0, inEdgeDistance=2)
    with pytest.raises(ValueError):
        swm.soft_selection_weights([0], positions, 4.0, inAffectBackfacing=False)
