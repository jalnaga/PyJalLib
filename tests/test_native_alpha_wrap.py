# -*- coding: utf-8 -*-
"""pyjallib.native Alpha Wrap 테스트 (Type A) - 추적 ``.pyd``를 콘솔 CPython 3.10에서 직접 부른다.

- 출처: 로드한 ``.pyd``가 이 저장소 ``src/pyjallib/native``이고 벤더링 커밋·정적 런타임과 일치
- 감싸기: 정육면체·구 -> 엔진 규칙 닫힘(``clipMesh.is_mesh_closed``)·부호 부피 > 0·입력 버텍스 전부 안, 결정론, 미참조 버텍스 무시
- 인자: alpha·offset <= 0 / 빈 삼각형 -> ValueError, 범위 밖 인덱스 -> IndexError
- 스레드: 두 스레드 동시 호출 결과 == 순차 결과(GIL 해제 경로가 상태를 공유하지 않는다)
- 부재: ``.pyd`` import 실패를 모사한 별도 인터프리터에서 ``import pyjallib``·``pyjallib.native``가 깨지지 않고, 호출하면 사유를 담은 RuntimeError

정답 도형은 **일반 위치**다 - 축 정렬·원점 대칭 좌표는 엔진 +Z 레이가 감싼 면의 꼭짓점을 지나 홀짝이 뒤집힌다
(Phase 0: 구 극점 (0, 0, ±10) 2점이 "밖"으로 판정, 1e-4 흔들면 안 - PRD §8.1).
"""

import math
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from pyjallib import native
from pyjallib.max import clipMesh as cm

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
UPSTREAM_COMMIT = "00564179c0c839db85514db97caaa6890944542a"
PREDICATES_COMMIT = "49c33980c55e9576c558a30a066940c2e360fcc2"
CENTER = (0.137, -0.291, 0.373)


def cube(inHalf, inCenter=CENTER):
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


def icosphere(inRadius, inLevels, inCenter=CENTER):
    """정이십면체 분할 구(바깥 향). 회전을 줘 축 위에 버텍스가 오지 않게 한다."""
    p = (1.0 + math.sqrt(5.0)) / 2.0
    verts = [(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p), (0, -1, -p), (0, 1, -p),
             (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)]
    tris = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
            (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
            (8, 6, 7), (9, 8, 1)]
    verts = [tuple(c / math.sqrt(sum(x * x for x in v)) for c in v) for v in verts]
    for _ in range(inLevels):
        cache = {}
        out = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = [(verts[a][k] + verts[b][k]) / 2.0 for k in range(3)]
                n = math.sqrt(sum(x * x for x in m))
                verts.append(tuple(x / n for x in m))
                cache[key] = len(verts) - 1
            return cache[key]

        for a, b, c in tris:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        tris = out
    ca, sa = math.cos(0.3), math.sin(0.3)
    cb, sb = math.cos(0.7), math.sin(0.7)
    placed = []
    for x, y, z in verts:
        y, z = y * ca - z * sa, y * sa + z * ca
        x, z = x * cb + z * sb, -x * sb + z * cb
        placed.append((x * inRadius + inCenter[0], y * inRadius + inCenter[1], z * inRadius + inCenter[2]))
    return placed, tris


# 빌드 대상 플랫폼에서는 .pyd가 추적되므로 import 실패는 skip이 아니라 실패다(조용한 초록 차단).
pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or sys.version_info[:2] != (3, 10), reason="alpha_wrap_native 빌드 대상은 Windows x64 + CPython 3.10"
)


def test_source_is_this_repo_and_vendored_commits():
    source = native.alpha_wrap_source()
    assert Path(source["file"]).resolve().parent == SRC_DIR / "pyjallib" / "native"
    assert source["upstreamCommit"] == UPSTREAM_COMMIT
    assert source["predicatesCommit"] == PREDICATES_COMMIT
    assert source["runtime"] == "MT"
    assert source["importError"] is None
    assert (SRC_DIR / "pyjallib" / "native" / native.ALPHA_WRAP_LICENSE_FILE).is_file()


@pytest.mark.parametrize("shape", ["cube", "sphere"])
def test_wrap_is_closed_outward_and_encloses_input(shape):
    verts, tris = cube(5.0) if shape == "cube" else icosphere(5.0, 2)
    wv, wt, stats = native.alpha_wrap(verts, tris, 0.5, 0.05)
    assert len(wt) == stats["output_faces"] > 0
    assert len(wv) == stats["output_vertices"]
    assert cm.is_mesh_closed(wv, wt)
    assert cm.signed_volume(wv, wt) > cm.signed_volume(verts, tris) > 0.0
    assert all(cm.classify_vertices(verts, wv, wt))
    # 감싼 버텍스는 입력에서 offset 거리의 등위면 위에 놓인다(실측 0.5% 이내) - offset이 그대로 전달되는지의 판별 축
    surface = cm.TriangleSurface(verts, tris, 2.0)
    distances = [surface.nearest(p, 10.0).distance for p in wv]
    assert 0.049 < min(distances) and max(distances) < 0.0505


def test_wrap_is_deterministic_and_ignores_unreferenced_vertices():
    verts, tris = cube(5.0)
    first = native.alpha_wrap(verts, tris, 0.7, 0.07)
    padded = list(verts) + [(100.0, 100.0, 100.0), (-50.0, 3.0, 2.0)]
    second = native.alpha_wrap(padded, tris, 0.7, 0.07)
    assert first == second


@pytest.mark.parametrize(
    "alpha, offset, error",
    [(0.0, 0.1, ValueError), (-1.0, 0.1, ValueError), (1.0, 0.0, ValueError), (1.0, -0.1, ValueError)],
)
def test_bad_alpha_offset_raise(alpha, offset, error):
    verts, tris = cube(5.0)
    with pytest.raises(error):
        native.alpha_wrap(verts, tris, alpha, offset)


def test_bad_triangles_raise():
    verts, tris = cube(5.0)
    with pytest.raises(IndexError):
        native.alpha_wrap(verts, list(tris) + [(0, 1, 8)], 1.0, 0.1)
    with pytest.raises(IndexError):
        native.alpha_wrap(verts, list(tris) + [(0, -1, 2)], 1.0, 0.1)
    with pytest.raises(ValueError):
        native.alpha_wrap(verts, [], 1.0, 0.1)


def test_concurrent_threads_match_sequential():
    verts, tris = icosphere(5.0, 3)
    expected = native.alpha_wrap(verts, tris, 0.3, 0.03)
    results = [None, None]

    def job(inIndex):
        results[inIndex] = native.alpha_wrap(verts, tris, 0.3, 0.03)

    threads = [threading.Thread(target=job, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results[0] == expected and results[1] == expected


def test_missing_native_does_not_break_import():
    """``.pyd`` import 실패를 모사한다(``sys.modules``에 None) - 별도 인터프리터라 이 프로세스의 로드 상태와 섞이지 않는다."""
    code = (
        "import sys; sys.modules['pyjallib.native.alpha_wrap_native'] = None\n"
        "import pyjallib\n"
        "assert 'pyjallib.native' not in sys.modules, 'import pyjallib must not load native'\n"
        "from pyjallib import native\n"
        "assert native.HAS_ALPHA_WRAP is False\n"
        "assert native.ALPHA_WRAP_IMPORT_ERROR and 'alpha_wrap_native' in native.ALPHA_WRAP_IMPORT_ERROR\n"
        "assert native.alpha_wrap_source()['file'] is None\n"
        "try:\n"
        "    native.alpha_wrap([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)], 1.0, 0.1)\n"
        "except RuntimeError as exc:\n"
        "    assert native.ALPHA_WRAP_IMPORT_ERROR in str(exc)\n"
        "else:\n"
        "    raise AssertionError('no RuntimeError')\n"
        "print('ok')\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR)
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
