#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pyjallib 네이티브 확장 - C++ 모듈의 **선택적** 로더(pymxs·numpy 비의존).

``import pyjallib``은 이 패키지를 import하지 않는다. 이 패키지를 import할 때 ``.pyd``를 한 번 시도하고, 실패해도
예외를 내지 않고 사유를 남긴다 - 다른 OS·다른 Python 버전에서도 pyjallib이 깨지지 않는다(PRD D2).

## alpha_wrap_native - Alpha Wrapping with an Offset

Portaneri et al.(ACM TOG 2022)의 CGAL 없는 구현(``alecjacobson/alpha-wrap``, MIT)과 Shewchuk 술어(public domain)를
고정 커밋으로 벤더링해 빌드한다(저장소 ``native/alphaWrap/VENDORED.md``, 빌드 ``native/build_native.py``). 입력 삼각형
수프(자기 교차·비다양체·열림 허용)를 offset만큼 띄워 감싼 **닫힌 2-다양체, 바깥 향 메쉬**를 돌려준다. alpha는 감싸는 공의
반지름(이보다 좁은 틈은 메워진다), offset은 입력에서 띄우는 거리이고 둘 다 씬 단위 절대값이다.

- 빌드 대상: Windows x64 + CPython 3.10(3ds Max 2024 내장 Python). 그 밖에서는 ``HAS_ALPHA_WRAP``이 False다.
- 정적 런타임(/MT)이라 ``python310.dll``·``KERNEL32.dll`` 외 DLL에 의존하지 않는다.
- 감싸는 동안 GIL을 푼다 - 여러 스레드에서 동시에 불러도 서로 막지 않는다.
- 같은 입력이면 같은 결과다(결정론).
"""

from typing import Dict, List, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Tri = Tuple[int, int, int]

#: 업스트림 LICENSE 사본 파일명(같은 폴더).
ALPHA_WRAP_LICENSE_FILE = "alpha_wrap_LICENSE.txt"

try:
    from pyjallib.native import alpha_wrap_native as _alphaWrap
except Exception as _exc:  # noqa: BLE001 - ImportError·DLL 로드 실패(OSError) 모두 "없음"으로 본다
    _alphaWrap = None
    ALPHA_WRAP_IMPORT_ERROR: Optional[str] = f"{type(_exc).__name__}: {_exc}"
else:
    ALPHA_WRAP_IMPORT_ERROR = None

#: ``alpha_wrap_native``를 쓸 수 있는가.
HAS_ALPHA_WRAP = _alphaWrap is not None


def alpha_wrap_source() -> Dict[str, Optional[str]]:
    """로드한 ``.pyd``의 출처 - 배포 프로브·테스트가 단정한다(빌드 바이트는 재현되지 않으므로 소스 커밋으로 판정).

    Returns:
        ``file``·``upstreamCommit``·``predicatesCommit``·``runtime``(없으면 각 None)과 ``importError``
    """
    if _alphaWrap is None:
        return {"file": None, "upstreamCommit": None, "predicatesCommit": None, "runtime": None,
                "importError": ALPHA_WRAP_IMPORT_ERROR}
    return {
        "file": _alphaWrap.__file__,
        "upstreamCommit": _alphaWrap.UPSTREAM_COMMIT,
        "predicatesCommit": _alphaWrap.PREDICATES_COMMIT,
        "runtime": _alphaWrap.RUNTIME,
        "importError": None,
    }


def alpha_wrap(
    inVerts: Sequence[Vec3], inTris: Sequence[Tri], inAlpha: float, inOffset: float
) -> Tuple[List[Vec3], List[Tri], Dict[str, int]]:
    """삼각형 수프를 Alpha Wrap으로 감싼다.

    Args:
        inVerts: 버텍스 ``(x, y, z)`` 목록. 삼각형이 참조하지 않는 버텍스는 무시된다
        inTris: 삼각형 ``(a, b, c)`` 0-based 인덱스 목록(1개 이상)
        inAlpha: 감싸는 공의 반지름(> 0, 씬 단위)
        inOffset: 입력에서 띄우는 거리(> 0, 씬 단위)

    Returns:
        (버텍스, 삼각형 0-based 바깥 향, 통계) - 통계 키 ``steiner_points``·``rule1``·``rule2``·``carved``·``gates_popped``·
        ``manifold_cells_reclaimed``·``output_vertices``·``output_faces``

    Raises:
        RuntimeError: 네이티브 모듈이 없음(사유 포함)
        ValueError: alpha·offset <= 0, 삼각형 0개
        IndexError: 삼각형 인덱스가 범위 밖
    """
    if _alphaWrap is None:
        raise RuntimeError(f"alpha_wrap_native를 쓸 수 없다: {ALPHA_WRAP_IMPORT_ERROR}")
    flatVerts = [float(c) for p in inVerts for c in p]
    flatTris = [int(i) for t in inTris for i in t]
    outVerts, outTris, stats = _alphaWrap.wrap(flatVerts, flatTris, float(inAlpha), float(inOffset))
    verts = [(outVerts[i], outVerts[i + 1], outVerts[i + 2]) for i in range(0, len(outVerts), 3)]
    tris = [(outTris[i], outTris[i + 1], outTris[i + 2]) for i in range(0, len(outTris), 3)]
    return verts, tris, dict(stats)
