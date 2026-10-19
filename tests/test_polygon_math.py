# -*- coding: utf-8 -*-
"""pyjallib.max.polygonMath 순수 연산 테스트 (Type A).

판정 표(보임 / 자기 가림 / 가려짐 후보), 면 집계(경계 면 보존), 여유 팽창, 방향 분포, 조기 종료,
오케스트레이터의 질의 범위(시험 2는 시험 1에서 막힌 샘플만)를 단정한다. 관통 형태는 해석적 구
오라클로 정답 면 집합을 계산해 등호로 비교한다.
"""

import math

import pytest

from pyjallib.max import polygonMath as pm

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _uv_sphere(inRadius=1.0, inCenter=(0.0, 0.0, 0.0), inRings=12, inSegs=24):
    """극 삼각형 팬 + 사각형 띠로 된 UV 구. (버텍스, 면, 버텍스 법선)."""
    cx, cy, cz = inCenter
    verts = [(cx, cy, cz + inRadius)]
    for r in range(1, inRings):
        theta = math.pi * r / inRings
        for s in range(inSegs):
            phi = 2.0 * math.pi * s / inSegs
            verts.append(
                (
                    cx + inRadius * math.sin(theta) * math.cos(phi),
                    cy + inRadius * math.sin(theta) * math.sin(phi),
                    cz + inRadius * math.cos(theta),
                )
            )
    verts.append((cx, cy, cz - inRadius))
    south = len(verts) - 1

    def ring(r, s):
        return 1 + (r - 1) * inSegs + (s % inSegs)

    faces = []
    for s in range(inSegs):
        faces.append([0, ring(1, s), ring(1, s + 1)])
    for r in range(1, inRings - 1):
        for s in range(inSegs):
            faces.append([ring(r, s), ring(r + 1, s), ring(r + 1, s + 1), ring(r, s + 1)])
    for s in range(inSegs):
        faces.append([ring(inRings - 1, s), south, ring(inRings - 1, s + 1)])
    normals = [pm.normalize((v[0] - cx, v[1] - cy, v[2] - cz)) for v in verts]
    return verts, faces, normals


def _ray_hits_sphere(inOrigin, inDir, inCenter, inRadius, inMinT=1e-9):
    """레이(t > inMinT)가 구 표면과 만나는가."""
    ox, oy, oz = (inOrigin[0] - inCenter[0], inOrigin[1] - inCenter[1], inOrigin[2] - inCenter[2])
    dx, dy, dz = inDir
    a = dx * dx + dy * dy + dz * dz
    b = 2.0 * (ox * dx + oy * dy + oz * dz)
    c = ox * ox + oy * oy + oz * oz - inRadius * inRadius
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return False
    sq = math.sqrt(disc)
    t1 = (-b - sq) / (2.0 * a)
    t2 = (-b + sq) / (2.0 * a)
    return t1 > inMinT or t2 > inMinT


def _fixed_query(inEscapedByPoint):
    """점 -> 탈출 여부 표로 동작하는 가짜 묶음 질의 + 호출 기록."""
    calls = []

    def _query(points, normals):
        calls.append(list(points))
        return [inEscapedByPoint[p] for p in points]

    return _query, calls


# 사각형 두 장이 버텍스 1·2를 공유하는 띠: 0-1-2-3, 1-4-5-2
_STRIP_VERTS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0), (2, 1, 0)]
_STRIP_FACES = [[0, 1, 2, 3], [1, 4, 5, 2]]
_STRIP_NORMALS = [(0.0, 0.0, 1.0)] * 6


# ---------------------------------------------------------------------------
# 방향 분포 / 프레임
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count,cone", [(1, 90.0), (32, 90.0), (64, 60.0), (16, 10.0)])
def test_cone_directions_count_unit_inside_cone(count, cone):
    dirs = pm.cone_directions(count, cone)
    assert len(dirs) == count
    cosMin = math.cos(math.radians(cone))
    for d in dirs:
        assert abs(math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) - 1.0) < 1e-12
        assert d[2] >= cosMin - 1e-12


def test_cone_directions_deterministic():
    assert pm.cone_directions(32, 75.0) == pm.cone_directions(32, 75.0)


def test_cone_directions_hemisphere_is_balanced():
    """반구 분포의 수평 성분 평균이 0에 가깝다 - 한쪽으로 쏠린 분포면 판정이 방향에 편향된다."""
    dirs = pm.cone_directions(64, 90.0)
    mx = sum(d[0] for d in dirs) / len(dirs)
    my = sum(d[1] for d in dirs) / len(dirs)
    assert abs(mx) < 0.05 and abs(my) < 0.05


@pytest.mark.parametrize("count,cone", [(0, 90.0), (8, 0.0), (8, 91.0), (8, -5.0)])
def test_cone_directions_rejects_invalid(count, cone):
    with pytest.raises(ValueError):
        pm.cone_directions(count, cone)


@pytest.mark.parametrize(
    "normal", [(0, 0, 1), (0, 0, -1), (1, 0, 0), (0.3, -0.2, 0.93), (0.0, 0.43, 0.9), (2.0, 5.0, -1.0)]
)
def test_local_frame_is_orthonormal_and_right_handed(normal):
    t, b, n = pm.local_frame(normal)
    for v in (t, b, n):
        assert abs(math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) - 1.0) < 1e-9
    dot = lambda a, c: a[0] * c[0] + a[1] * c[1] + a[2] * c[2]  # noqa: E731
    assert abs(dot(t, b)) < 1e-9 and abs(dot(t, n)) < 1e-9 and abs(dot(b, n)) < 1e-9
    cross = pm._cross(t, b)
    assert all(abs(cross[i] - n[i]) < 1e-9 for i in range(3))


def test_to_world_maps_local_z_to_normal():
    frame = pm.local_frame((0.0, 1.0, 0.0))
    w = pm.to_world((0.0, 0.0, 1.0), frame)
    assert w == pytest.approx((0.0, 1.0, 0.0))


# ---------------------------------------------------------------------------
# 조기 종료
# ---------------------------------------------------------------------------


def test_sample_escapes_stops_at_first_escape():
    calls = []

    def blocked(origin, direction):
        calls.append(direction)
        return False

    dirs = pm.cone_directions(32, 90.0)
    assert pm.sample_escapes((0, 0, 0), (0, 0, 1), dirs, 0.01, blocked) is True
    assert len(calls) == 1


def test_sample_escapes_all_blocked_shoots_every_ray_from_offset_origin():
    origins = []

    def blocked(origin, direction):
        origins.append(origin)
        return True

    dirs = pm.cone_directions(32, 90.0)
    assert pm.sample_escapes((1.0, 2.0, 3.0), (0, 0, 2), dirs, 0.5, blocked) is False
    assert len(origins) == 32
    assert origins[0] == pytest.approx((1.0, 2.0, 3.5))


def test_make_sample_query_matches_sample_escapes():
    dirs = pm.cone_directions(8, 90.0)

    def blocked(origin, direction):
        return direction[0] > -0.2

    query = pm.make_sample_query(dirs, 0.01, blocked)
    pts = [(0, 0, 0), (1, 1, 1)]
    nrms = [(0, 0, 1), (1, 0, 0)]
    assert query(pts, nrms) == [pm.sample_escapes(p, n, dirs, 0.01, blocked) for p, n in zip(pts, nrms)]


# ---------------------------------------------------------------------------
# 샘플 구성
# ---------------------------------------------------------------------------


def test_build_face_samples_shares_vertices_and_skips_unused():
    verts = _STRIP_VERTS + [(9, 9, 9)]
    normals = _STRIP_NORMALS + [(0, 0, 1)]
    s = pm.build_face_samples(verts, _STRIP_FACES, normals)
    assert len(s.points) == 6 + 2
    assert 6 not in s.vertexSampleIndex
    assert s.faceSampleIds[0][:4] == [s.vertexSampleIndex[v] for v in _STRIP_FACES[0]]
    assert s.faceSampleIds[0][1] == s.faceSampleIds[1][0]  # 공유 버텍스 1은 같은 샘플
    assert s.points[s.faceSampleIds[0][4]] == pytest.approx((0.5, 0.5, 0.0))
    assert s.normals[s.faceSampleIds[0][4]] == pytest.approx((0.0, 0.0, 1.0))


def test_build_face_samples_degenerate_face_uses_vertex_normals():
    verts = [(0, 0, 0), (1, 0, 0), (2, 0, 0)]
    normals = [(0, 1, 0)] * 3
    s = pm.build_face_samples(verts, [[0, 1, 2]], normals)
    assert s.normals[s.faceSampleIds[0][3]] == pytest.approx((0.0, 1.0, 0.0))


@pytest.mark.parametrize("faces", [[[0, 1]], [[0, 1, 9]], [[0, 1, -1]]])
def test_build_face_samples_rejects_bad_faces(faces):
    with pytest.raises(ValueError):
        pm.build_face_samples(_STRIP_VERTS, faces, _STRIP_NORMALS)


def test_build_face_samples_rejects_normal_count_mismatch():
    with pytest.raises(ValueError):
        pm.build_face_samples(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS[:-1])


# ---------------------------------------------------------------------------
# 판정 표 / 면 집계
# ---------------------------------------------------------------------------


def test_classify_faces_table_rows():
    """판정 표 3행: 시험 1 탈출 -> 보임 / 전부 막힘 + 시험 2 막힘 -> 자기 가림 / 나머지 -> 후보."""
    faceIds = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    test1 = [False, True, False, False, False, False, False, False, False]
    visible, selfOcc, cand = pm.classify_faces(faceIds, test1, inSelfBlocked={4})
    assert visible == {0}
    assert selfOcc == {1}
    assert cand == {2}


def test_classify_faces_boundary_face_with_one_visible_sample_is_kept():
    """샘플 하나만 보여도 보임 - 옷 경계를 가로지르는 면은 남는다."""
    visible, selfOcc, cand = pm.classify_faces([[0, 1, 2, 3, 4]], [False, False, False, False, True], set())
    assert visible == {0} and not cand


def test_classify_faces_visible_wins_over_self_blocked():
    visible, selfOcc, cand = pm.classify_faces([[0, 1]], [True, False], inSelfBlocked={1})
    assert visible == {0} and not selfOcc


# ---------------------------------------------------------------------------
# 여유 팽창
# ---------------------------------------------------------------------------


def test_margin_zero_keeps_nothing():
    assert pm.margin_keep(_STRIP_VERTS, _STRIP_FACES, {0}, {1}, 0.0) == set()


def test_margin_positive_keeps_face_sharing_a_vertex():
    assert pm.margin_keep(_STRIP_VERTS, _STRIP_FACES, {0}, {1}, 0.01) == {1}


def test_margin_distance_boundary_is_inclusive():
    verts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (3, 0, 0), (4, 0, 0), (3, 1, 0)]
    faces = [[0, 1, 2], [3, 4, 5]]
    assert pm.margin_keep(verts, faces, {0}, {1}, 2.0) == {1}  # 1 -> 3 거리 2.0
    assert pm.margin_keep(verts, faces, {0}, {1}, 1.999) == set()


def test_margin_rejects_negative():
    with pytest.raises(ValueError):
        pm.margin_keep(_STRIP_VERTS, _STRIP_FACES, {0}, {1}, -1.0)


# ---------------------------------------------------------------------------
# 오케스트레이터
# ---------------------------------------------------------------------------


def test_find_occluded_faces_queries_test2_only_for_blocked_samples():
    s = pm.build_face_samples(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS)
    # 면 0 샘플 전부 막힘, 면 1은 버텍스 4가 보임
    escaped1 = {p: False for p in s.points}
    escaped1[s.points[s.vertexSampleIndex[4]]] = True
    escaped2 = {p: True for p in s.points}
    q1, calls1 = _fixed_query(escaped1)
    q2, calls2 = _fixed_query(escaped2)
    result = pm.find_occluded_faces(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS, q1, q2, 0.0)
    assert sum(len(c) for c in calls1) == len(s.points)
    queried2 = [p for c in calls2 for p in c]
    assert len(queried2) == len(s.points) - 1
    assert s.points[s.vertexSampleIndex[4]] not in queried2
    assert result.visibleFaces == [1]
    assert result.occludedFaces == [0]
    assert result.test1BlockedSamples == len(s.points) - 1
    assert result.selfBlockedSamples == 0


def test_find_occluded_faces_self_blocked_face_is_preserved():
    """시험 2에서 막힌 샘플이 있는 면은 자기 가림 - 삭제 후보가 아니다(A7)."""
    s = pm.build_face_samples(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS)
    escaped1 = {p: False for p in s.points}
    escaped2 = {p: True for p in s.points}
    escaped2[s.points[s.faceSampleIds[0][4]]] = False  # 면 0 중심이 몸에 가림
    q1, _ = _fixed_query(escaped1)
    q2, _ = _fixed_query(escaped2)
    result = pm.find_occluded_faces(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS, q1, q2, 0.0)
    assert result.selfOccludedFaces == [0]
    assert result.occludedFaces == [1]


def test_find_occluded_faces_chunks_and_reports_progress():
    s = pm.build_face_samples(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS)
    q1, calls1 = _fixed_query({p: False for p in s.points})
    q2, _ = _fixed_query({p: True for p in s.points})
    events = []
    pm.find_occluded_faces(
        _STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS, q1, q2, 0.0,
        inProgressCallback=lambda name, cur, tot: events.append((name, cur, tot)), inChunkSize=3,
    )
    assert [len(c) for c in calls1] == [3, 3, 2]
    test1Events = [e for e in events if e[0].startswith("시험 1")]
    assert test1Events[0][1] == 0 and test1Events[-1][1] == test1Events[-1][2] == 8


def test_find_occluded_faces_rejects_query_result_count_mismatch():
    def bad(points, normals):
        return [True] * (len(points) + 1)

    with pytest.raises(ValueError):
        pm.find_occluded_faces(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS, bad, bad, 0.0)


@pytest.mark.parametrize("margin,chunk", [(-0.1, 10), (0.0, 0)])
def test_find_occluded_faces_rejects_bad_parameters(margin, chunk):
    ok = lambda p, n: [True] * len(p)  # noqa: E731
    with pytest.raises(ValueError):
        pm.find_occluded_faces(_STRIP_VERTS, _STRIP_FACES, _STRIP_NORMALS, ok, ok, margin, inChunkSize=chunk)


# ---------------------------------------------------------------------------
# 관통 형태 (해석적 정답)
# ---------------------------------------------------------------------------

_BODY_C, _BODY_R = (0.0, 0.0, 0.0), 1.0
# 버텍스 189/266이 옷 안쪽, 옷 표면까지 최소 간격 0.024(전제 단정 0.02를 넘도록 고른 배치)
_CLOTH_C, _CLOTH_R = (0.76, 0.0, 0.0), 1.43


def _penetration_setup():
    verts, faces, normals = _uv_sphere(_BODY_R, _BODY_C)
    inside = [math.dist(v, _CLOTH_C) < _CLOTH_R for v in verts]
    # 전제: 옷 표면에 너무 가까운 버텍스가 없다(시작점 오프셋이 경계를 넘나들지 않는다)
    assert min(abs(math.dist(v, _CLOTH_C) - _CLOTH_R) for v in verts) > 0.02
    # 전제: 몸이 옷을 실제로 뚫고 나온다(안·밖 버텍스가 둘 다 있다)
    assert any(inside) and not all(inside)
    dirs = pm.cone_directions(32, 90.0)

    # 몸은 볼록 다면체라 표면 샘플에서 바깥 반구로 쏜 레이가 몸에 다시 맞지 않는다 - 몸 차폐는 없다.
    # (매끈한 해석적 구로 몸을 판정하면 면 중심 샘플이 현(chord) 위라 구 안쪽에 놓여 자기 가림으로
    # 오판한다 - 실제 메쉬에는 없는 오라클 오차다.)
    def blocked1(origin, direction):
        return _ray_hits_sphere(origin, direction, _CLOTH_C, _CLOTH_R)

    def blocked2(origin, direction):
        return False

    q1 = pm.make_sample_query(dirs, 0.01, blocked1)
    q2 = pm.make_sample_query(dirs, 0.01, blocked2)
    expectedOccluded = sorted(f for f, fv in enumerate(faces) if all(inside[v] for v in fv))
    return verts, faces, normals, q1, q2, expectedOccluded


def test_penetration_poked_out_part_is_kept_and_covered_part_is_occluded():
    """몸 일부가 옷을 뚫고 나온 형태(A9): 옷 안 버텍스만으로 된 면 == 가려짐, 나머지는 보임."""
    verts, faces, normals, q1, q2, expected = _penetration_setup()
    result = pm.find_occluded_faces(verts, faces, normals, q1, q2, 0.0)
    assert result.occludedFaces == expected
    assert result.selfOccludedFaces == []
    assert sorted(result.visibleFaces + result.occludedFaces) == list(range(len(faces)))
    assert 0 < len(expected) < len(faces)


def test_penetration_margin_keeps_a_ring_around_the_poke_out():
    verts, faces, normals, q1, q2, expected = _penetration_setup()
    r0 = pm.find_occluded_faces(verts, faces, normals, q1, q2, 0.0)
    r1 = pm.find_occluded_faces(verts, faces, normals, q1, q2, 0.3)
    assert set(r1.occludedFaces) < set(r0.occludedFaces)
    assert set(r1.marginKeptFaces) == set(r0.occludedFaces) - set(r1.occludedFaces)
    visibleVerts = {v for f in r1.visibleFaces for v in faces[f]}
    for f in r1.marginKeptFaces:
        assert min(math.dist(verts[v], verts[w]) for v in faces[f] for w in visibleVerts) <= 0.3
    for f in r1.occludedFaces:
        assert min(math.dist(verts[v], verts[w]) for v in faces[f] for w in visibleVerts) > 0.3


def test_result_counts_sum_to_face_count():
    verts, faces, normals, q1, q2, _ = _penetration_setup()
    c = pm.find_occluded_faces(verts, faces, normals, q1, q2, 0.3).counts()
    assert c["visible"] + c["selfOccluded"] + c["marginKept"] + c["occluded"] == c["faces"] == len(faces)
