#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""릭 파트 특성화 baseline 픽스처 생성기 (RiggingToolRefactor Phase 0).

`tests/max/test_probe_rig_parts.py`가 남긴 `tests/logs/probe_rig_parts.json`에서
**판정에 쓸 축만** 추려 `tests/fixtures/rig_parts_baseline.json`(추적 파일)으로 굳힌다.
Phase 1의 Type C 회귀 스위트(`tests/max/test_rig_parts.py`)가 이 파일을 기준값으로 쓴다.

**왜 프로브 JSON을 그대로 쓰지 않는가.** 프로브 JSON은 진단 정보(예외 문자열, 직접 경로
실패, 실행 환경)까지 담고 있어 판정 기준으로 쓰면 무관한 차이에 빨개진다. 굳히는 것은
두 축뿐이다.

- `create`: 툴 기본 파라미터로 생성한 결과
- `modify`: `func_<part>.modify_chain`이 하듯 파라미터를 덮어쓰고 재생성한 결과(프로덕션 경로)

**`parameters`는 판정 축에서 뺀다.** Phase 1이 `BoneChain.parameters`를 리스트에서 이름 붙은
dict로 바꾸는 것이 이 사이클의 목표 중 하나이므로, 굳히면 의도한 변경이 회귀로 잡힌다.
참조용으로 `_reference` 아래에만 남긴다.

**재현성 근거.** 2026-09-21에 프로브를 두 번(run3·run4) 독립 실행해 51개 (파트 x 국면)
조합을 전수 대조했고 **차이 0건**이었다. 위치(순서) 비교를 그대로 쓰는 근거가 이것이다 -
재현되지 않았다면 정렬 멀티셋으로 낮췄어야 한다(`testing/discriminating_power.md`).

사용법:
    uv run python tests/make_rig_baseline.py
    uv run python tests/make_rig_baseline.py --check    # 재생성하지 않고 현행과 대조만
"""

import argparse
import json
import sys
from pathlib import Path

PROBE_PATH = Path(__file__).parent / "logs" / "probe_rig_parts.json"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "rig_parts_baseline.json"

# 노드 스냅샷에서 판정에 쓸 키. 프로브가 담는 `valid`는 항상 True라 제외한다.
NODE_KEYS = (
    "name",
    "parent",
    "class",
    "superClass",
    "transformController",
    "posController",
    "rotController",
    "scaleController",
    "userProps",
)


def _node(inSnapshot: dict) -> dict:
    """노드 스냅샷에서 판정 축만 남긴다.

    Args:
        inSnapshot: 프로브가 찍은 노드 스냅샷

    Returns:
        dict: `NODE_KEYS`만 담은 dict
    """
    return {key: inSnapshot.get(key) for key in NODE_KEYS}


def _chain(inSnapshot) -> dict | None:
    """체인 스냅샷에서 판정 축만 남긴다.

    Args:
        inSnapshot: 프로브가 찍은 체인 스냅샷. None이면 None을 돌려준다.

    Returns:
        dict | None: 본·헬퍼·소스본만 담은 dict
    """
    if not inSnapshot or inSnapshot.get("returned") != "BoneChain":
        return None
    return {
        "bones": [_node(item) for item in inSnapshot.get("bones", [])],
        "helpers": [_node(item) for item in inSnapshot.get("helpers", [])],
        "sourceBones": list(inSnapshot.get("sourceBones", [])),
    }


def build_baseline(inProbeResult: dict) -> dict:
    """프로브 결과에서 baseline 픽스처를 만든다.

    Args:
        inProbeResult: `probe_rig_parts.json`을 읽은 dict

    Returns:
        dict: 파트 키 -> `{"create": ..., "modify": ..., "_reference": ...}`
    """
    baseline = {}
    for partKey, entry in inProbeResult.get("P2", {}).items():
        if partKey.startswith("_") or "create" not in entry:
            continue
        p3 = inProbeResult.get("P3", {}).get(partKey, {})
        createSnapshot = _chain((entry.get("create") or {}).get("snapshot"))
        modifySnapshot = _chain((p3.get("toolPath") or {}).get("snapshot"))
        if createSnapshot is None or modifySnapshot is None:
            print(f"[SKIP] {partKey} - create 또는 modify 스냅샷이 없다", file=sys.stderr)
            continue
        baseline[partKey] = {
            "sources": entry.get("sources", []),
            "create": createSnapshot,
            "modify": modifySnapshot,
            "_reference": {
                "parametersAfterCreate": p3.get("parametersAfterCreate"),
                "deleteRemainingValidBones": (p3.get("delete") or {}).get("remainingValidBones"),
                "directRegenFailed": not (p3.get("direct") or {}).get("ok", True),
            },
        }
    return baseline


def main() -> int:
    """프로브 JSON을 읽어 픽스처를 쓰거나 현행과 대조한다.

    Returns:
        int: 종료 코드. `--check`에서 차이가 있으면 1
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="쓰지 않고 현행 픽스처와 대조만 한다")
    args = parser.parse_args()

    if not PROBE_PATH.exists():
        print(f"프로브 결과가 없다: {PROBE_PATH}", file=sys.stderr)
        print("먼저 `uv run python tests/run_max_tests.py test_probe_rig_parts.py`를 돌린다.", file=sys.stderr)
        return 2

    probeResult = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    baseline = build_baseline(probeResult)
    rendered = json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.check:
        if not FIXTURE_PATH.exists():
            print(f"픽스처가 없다: {FIXTURE_PATH}", file=sys.stderr)
            return 1
        current = FIXTURE_PATH.read_text(encoding="utf-8")
        if current != rendered:
            print("픽스처가 프로브 결과와 다르다.", file=sys.stderr)
            return 1
        print(f"동일하다 ({len(baseline)} 파트)")
        return 0

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(rendered, encoding="utf-8")
    print(f"{FIXTURE_PATH} 기록 완료 ({len(baseline)} 파트)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
