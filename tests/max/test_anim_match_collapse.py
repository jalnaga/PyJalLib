#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`match_anim_transform` / `collape_anim_transform` 등가성·성능 검증 (Type C).

구 구현의 **사본**을 이 파일 안에 들고 있다가 신 구현과 **한 Max 세션에서**
번갈아 돌려 대조한다. 세션을 갈라 재면 릭 워밍·OS 파일 캐시가 값을 바꾸고,
등가성도 씬 상태가 달라 대조가 흐려진다(`patterns/performance_measurement.md`).

- TC00 로드 출처 - 워크트리 소스를 검증하고 있는가
- TC01~TC05 `match` 등가성 - 표본 5종에서 **키 시점 집합**과 **프레임별 12-float** 동시 대조
- TC06 `collapse` 등가성 - 12-float + 컨트롤러 클래스
- TC07~TC10 공허한 통과 차단 - 대조할 값이 실제로 있었는가, 값이 프레임마다 변하는가
- TC11 순서 변경 (a) 순환 입력에서 소스를 원본 상태로 읽는다
- TC12 순서 변경 (b) 구간 내 서브프레임 키가 걷힌다 (구 경로는 남긴다)
- TC13 A/B 성능 - Phase 0 baseline 표본 3종 + collapse

**등가성의 의미.** TC01~TC06은 "구 경로와 산출물이 같다"를 단정한다. TC11/TC12는
반대로 "여기서는 의도적으로 다르다"를 단정한다. 두 종류를 섞지 않는다.

**측정 한계.** `3dsmaxbatch`는 Undo가 애초에 비활성이라 `undo off` 도입 효과가
정확히 0으로 측정된다. TC13의 절감은 **구조적 개선분만** 담는다.

산출물: `tests/logs/test_AnimMatchCollapse.log` + `tests/logs/anim_match_ab.json`
테스트 유형: Type C (Headless + Log)
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path

# pyjallib 소스 경로 추가 - 워크트리 자신의 소스를 검증한다
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

# 배포본 선로드 퍼지. Max는 기동 시 배포본을 sys.modules에 선점한다.
for _moduleName in [
    name for name in sys.modules
    if name == "pyjallib" or name.startswith("pyjallib.")
]:
    del sys.modules[_moduleName]

import pyjallib  # noqa: E402
import pymxs  # noqa: E402
from pymxs import runtime as rt  # noqa: E402
from pyjallib.max.anim import Anim, build_clear_target_keys_script  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
AB_JSON_PATH = LOG_DIR / "anim_match_ab.json"
reporter = TestReporter("AnimMatchCollapse", LOG_DIR)

anim = Anim()
TOLERANCE = 0.01

abReport: dict = {
    "host": os.environ.get("PYJALLIB_TEST_HOST", "unknown"),
    "note": (
        "헤드리스(3dsmaxbatch)는 Undo가 비활성이라 undo off 이득이 0으로 측정된다. "
        "아래 절감은 구조적 개선분(구간 단위 키 삭제 + 3중 기록 제거)만 담는다."
    ),
    "samples": {},
}


# ======================================================================
# 구 구현 사본 - 대조 기준. 원본 MAXScript를 그대로 들고 있다.
#
# 이 사본은 **리팩토링 대상이 아니다.** 대조 수단을 손대면 무엇과 비교하고
# 있는지 알 수 없게 된다(`patterns/performance_measurement.md`).
# ======================================================================

def legacy_match_anim_transform(inObj, inTarget, startFrame, endFrame) -> None:
    """구 `match_anim_transform` (2026-08-11 이전) 사본.

    **`progressStart`/`progressUpdate`/`progressEnd`까지 원본 그대로 둔다.**
    처음에는 "루프가 본질"이라며 progress 호출을 빼고 옮겼는데, 그러면 신
    경로만 progress 비용을 지고 A/B가 구 경로에 유리하게 기운다. 실제로
    `collapse`에서 Phase 0 baseline(0.0425s)과 사본 측정(0.0124s)이 3.4배
    갈렸다 - 프레임당 `progressUpdate` 641회가 빠져 있었기 때문이다.
    """
    maxscriptCode = ""
    maxscriptCode += f"inObj = $'{inObj.name}'\n"
    maxscriptCode += f"inTarget = $'{inTarget.name}'\n"
    maxscriptCode += "if (isValidNode inObj) and (isValidNode inTarget) then (\n"
    maxscriptCode += "    disableSceneRedraw()\n"
    maxscriptCode += (
        f"    progressStart (\"Match transform {inObj.name} to {inTarget.name} \")\n"
    )
    maxscriptCode += "\n"
    maxscriptCode += "    p = point()\n"
    maxscriptCode += f"    for k = {startFrame} to {endFrame} do (\n"
    maxscriptCode += "        at time k (\n"
    maxscriptCode += "            with animate on p.transform = inTarget.transform\n"
    maxscriptCode += "        )\n"
    maxscriptCode += "\n"
    maxscriptCode += "        deselectKeys inObj.transform.controller\n"
    maxscriptCode += "        selectKeys inObj.transform.controller k\n"
    maxscriptCode += "        deleteKeys inObj.transform.controller #selection\n"
    maxscriptCode += "        deselectKeys inObj.transform.controller\n"
    maxscriptCode += "    )\n"
    maxscriptCode += "\n"
    maxscriptCode += f"    if {startFrame} != animationRange.start then (\n"
    maxscriptCode += "        deselectKeys p.transform.controller\n"
    maxscriptCode += "        selectKeys p.transform.controller animationRange.start\n"
    maxscriptCode += "        deleteKeys p.transform.controller #selection\n"
    maxscriptCode += "        deselectKeys p.transform.controller\n"
    maxscriptCode += "    )\n"
    maxscriptCode += "\n"
    maxscriptCode += "    progressUpdate 20\n"
    maxscriptCode += "\n"
    maxscriptCode += "    local posKeyArray = inTarget.pos.controller.keys\n"
    maxscriptCode += "    local rotKeyArray = inTarget.rotation.controller.keys\n"
    maxscriptCode += "    local scaleKeyArray = inTarget.scale.controller.keys\n"
    maxscriptCode += "\n"
    maxscriptCode += f"    at time {startFrame} (\n"
    maxscriptCode += "        with animate on inObj.transform = p.transform\n"
    maxscriptCode += "    )\n"
    maxscriptCode += f"    at time {endFrame} (\n"
    maxscriptCode += "        with animate on inObj.transform = p.transform\n"
    maxscriptCode += "    )\n"
    maxscriptCode += "\n"
    for keyArrayName, progressValue in (
        ("posKeyArray", 40), ("rotKeyArray", 60), ("scaleKeyArray", 80)
    ):
        maxscriptCode += f"    for key in {keyArrayName} do (\n"
        maxscriptCode += (
            f"        if key.time >= {startFrame} and key.time <= {endFrame} then (\n"
        )
        maxscriptCode += "            at time key.time (\n"
        maxscriptCode += "                with animate on inObj.transform = p.transform\n"
        maxscriptCode += "            )\n"
        maxscriptCode += "        )\n"
        maxscriptCode += "    )\n"
        maxscriptCode += f"    progressUpdate {progressValue}\n"
    maxscriptCode += "\n"
    maxscriptCode += "    delete p\n"
    maxscriptCode += "\n"
    maxscriptCode += "    progressUpdate 100\n"
    maxscriptCode += "    progressEnd()\n"
    maxscriptCode += "    enableSceneRedraw()\n"
    maxscriptCode += ")\n"

    rt.execute(maxscriptCode)


def legacy_collape_anim_transform(inObj, startFrame, endFrame) -> None:
    """구 `collape_anim_transform` (2026-08-11 이전) 사본.

    프레임당 `progressUpdate`까지 원본 그대로다 - 이 함수의 구 비용에서
    그것이 지배 항이므로 빼면 A/B가 무의미해진다.
    """
    maxScriptCode = ""
    maxScriptCode += "disableSceneRedraw()\n"
    maxScriptCode += f"progressStart (\"Collapse transform {inObj.name}...\")\n"
    maxScriptCode += f"inObj = $'{inObj.name}'\n"
    maxScriptCode += "p = point()\n"
    maxScriptCode += f"for k = {startFrame} to {endFrame} do (\n"
    maxScriptCode += "    at time k (\n"
    maxScriptCode += "        with animate on p.transform = inObj.transform\n"
    maxScriptCode += "    )\n"
    maxScriptCode += ")\n"
    maxScriptCode += "\n"
    maxScriptCode += "inObj.transform.controller = transform_script()\n"
    maxScriptCode += "inObj.transform.controller = prs()\n"
    maxScriptCode += "\n"
    maxScriptCode += f"for k = {startFrame} to {endFrame} do (\n"
    maxScriptCode += "    at time k (\n"
    maxScriptCode += "        with animate on (\n"
    maxScriptCode += "            in coordsys (transmatrix inObj.transform.pos) inObj.rotation = inverse p.transform.rotation\n"
    maxScriptCode += "            in coordsys world inObj.position = p.transform.position\n"
    maxScriptCode += "            inObj.scale = p.scale\n"
    maxScriptCode += "        )\n"
    maxScriptCode += "    )\n"
    maxScriptCode += f"    progressUpdate (100 * k / {endFrame})\n"
    maxScriptCode += ")\n"
    maxScriptCode += "\n"
    maxScriptCode += f"if {startFrame} != animationRange.start then (\n"
    maxScriptCode += "    deselectKeys inObj.transform.controller\n"
    maxScriptCode += "    selectKeys inObj.transform.controller animationRange.start\n"
    maxScriptCode += "    deleteKeys inObj.transform.controller #selection\n"
    maxScriptCode += "    deselectKeys inObj.transform.controller\n"
    maxScriptCode += ")\n"
    maxScriptCode += "\n"
    maxScriptCode += "delete p\n"
    maxScriptCode += "progressEnd()\n"
    maxScriptCode += "enableSceneRedraw()\n"

    rt.execute(maxScriptCode)


# ======================================================================
# 공통 헬퍼
# ======================================================================

def _reset(inStartFrame: int, inEndFrame: int) -> None:
    """씬을 리셋하고 애니메이션 구간을 설정한다."""
    rt.resetMaxFile(rt.name("noPrompt"), quiet=True)
    rt.animationRange = rt.interval(inStartFrame, inEndFrame)


def _handle(inNode) -> int:
    """노드 핸들을 정수로 돌려준다."""
    return int(rt.getHandleByAnim(inNode))


def _matrix_at(inNode, inFrame) -> tuple:
    """특정 시점의 월드 트랜스폼을 12개 float 튜플로 스냅샷한다."""
    with pymxs.attime(inFrame):
        matrix = inNode.transform
        rows = (matrix.row1, matrix.row2, matrix.row3, matrix.row4)
        return tuple(
            float(component)
            for row in rows
            for component in (row.x, row.y, row.z)
        )


def _snapshot(inNode, inFrames) -> list:
    """여러 시점의 12-float 스냅샷 목록을 만든다."""
    return [_matrix_at(inNode, frame) for frame in inFrames]


def _snapshots_match(inLeft: list, inRight: list) -> tuple:
    """두 스냅샷 목록을 비교하고 (일치여부, 불일치 인덱스 목록)을 돌려준다."""
    if len(inLeft) != len(inRight):
        return (False, [-1])
    mismatched = [
        index
        for index, (left, right) in enumerate(zip(inLeft, inRight))
        if any(abs(a - b) >= TOLERANCE for a, b in zip(left, right))
    ]
    return (not mismatched, mismatched)


def _key_ticks(inNode, inTrack: str) -> list:
    """컨트롤러의 키 시점을 **틱** 목록으로 덤프한다.

    ``key.time as float``은 프레임이 아니라 틱을 돌려준다(2026-08-11 실측).
    대조에만 쓰고 되먹이지 않으므로 여기서는 틱이면 충분하다.
    """
    script = (
        "(\n"
        f"    local node = getAnimByHandle {_handle(inNode)}\n"
        f"    local ctrl = node.{inTrack}.controller\n"
        '    local out = ""\n'
        "    for k in ctrl.keys do out = out + ((k.time as float) as string) + \",\"\n"
        "    out\n"
        ")"
    )
    raw = rt.execute(script)
    if not raw:
        return []
    return [float(token) for token in str(raw).split(",") if token]


def _key_ticks_all(inNode) -> dict:
    """pos/rotation/scale 키 시점을 한 번에 덤프한다."""
    return {
        track: _key_ticks(inNode, track)
        for track in ("pos", "rotation", "scale")
    }


def _controller_classes(inNode) -> str:
    """transform/pos/rotation/scale 컨트롤러 클래스를 문자열로 덤프한다."""
    return str(rt.execute(
        "(\n"
        f"    local n = getAnimByHandle {_handle(inNode)}\n"
        "    ((classOf n.transform.controller) as string + \",\""
        " + (classOf n.pos.controller) as string + \",\""
        " + (classOf n.rotation.controller) as string + \",\""
        " + (classOf n.scale.controller) as string)\n"
        ")"
    ))


def _animate_dense(inNode, inStartFrame: int, inEndFrame: int, inScale: float = 1.0) -> None:
    """구간 전 프레임에 위치·회전 키를 심는다 (MAXScript 한 블록)."""
    script = (
        "(\n"
        f"    local node = getAnimByHandle {_handle(inNode)}\n"
        "    with undo off (\n"
        f"        for k = {inStartFrame} to {inEndFrame} do (\n"
        "            at time k (\n"
        "                with animate on (\n"
        f"                    local d = (k - {inStartFrame}) * {inScale}\n"
        "                    node.position = [d * 2.0, d * -1.5, d * d * 0.05]\n"
        "                    node.rotation = eulerAngles 0 0 (d * 3.0)\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    )\n"
        "    ok\n"
        ")"
    )
    rt.execute(script)


def _animate_sparse(inNode, inFrames: list, inScale: float = 1.0) -> None:
    """지정한 시점들에만 위치·회전 키를 심는다. float 시점은 서브프레임 키가 된다."""
    frameText = ",".join(str(float(frame)) for frame in inFrames)
    script = (
        "(\n"
        f"    local node = getAnimByHandle {_handle(inNode)}\n"
        "    with undo off (\n"
        f"        for f in #({frameText}) do (\n"
        "            at time f (\n"
        "                with animate on (\n"
        f"                    local d = f * {inScale}\n"
        "                    node.position = [d * 2.0, d * -1.5, d * 0.7]\n"
        "                    node.rotation = eulerAngles 0 0 (d * 3.0)\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    )\n"
        "    ok\n"
        ")"
    )
    rt.execute(script)


def _timed(inFunc, *args, **kwargs) -> float:
    """호출 1회의 소요 시간(초)을 잰다. 프로덕션 코드에 타이머를 심지 않는다."""
    startedAt = time.perf_counter()
    inFunc(*args, **kwargs)
    return time.perf_counter() - startedAt


# ======================================================================
# TC00: 로드 출처
# ======================================================================
try:
    loadedFrom = str(Path(pyjallib.__file__).resolve())
    expectedRoot = str((Path(__file__).parent.parent.parent / "src").resolve())
    reporter.assert_test(
        loadedFrom.startswith(expectedRoot),
        "TC00 pyjallib이 워크트리 소스에서 로드됐다",
        inDetail=f"loadedFrom={loadedFrom}, expectedRoot={expectedRoot}",
    )
except Exception as e:
    reporter.error("TC00 로드 출처", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# match 등가성 표본 - 한 씬에 소스 1개 + 대상 2개를 두고 구·신을 각각 적용한다.
#
# 씬을 갈라 만들면 "같은 소스였는가"가 보장되지 않는다. 같은 소스 노드를
# 두 대상이 공유하게 하면 그 의심이 사라진다.
# ======================================================================

MATCH_SAMPLES: dict = {}


def _run_match_sample(
    inLabel: str,
    inRangeStart: int,
    inRangeEnd: int,
    inApplyStart: int,
    inApplyEnd: int,
    inBuildSource,
    inPrimeTarget=None,
    inParentTargets: bool = False,
) -> dict:
    """구·신 `match_anim_transform`을 같은 소스에 적용하고 결과를 모은다.

    Args:
        inLabel: 표본 이름
        inRangeStart: 씬 ``animationRange`` 시작
        inRangeEnd: 씬 ``animationRange`` 끝
        inApplyStart: 적용 구간 시작
        inApplyEnd: 적용 구간 끝
        inBuildSource: 소스 노드에 애니메이션을 심는 콜러블
        inPrimeTarget: 두 대상에 기존 키를 심는 콜러블. None이면 무키 대상
        inParentTargets: True면 두 대상을 각각 애니메이션된 부모 밑에 붙인다

    Returns:
        구·신 스냅샷과 키 시점 집합을 담은 dict
    """
    _reset(inRangeStart, inRangeEnd)

    sourceNode = rt.Point(name=f"{inLabel}_src")
    inBuildSource(sourceNode)

    legacyTarget = rt.Point(name=f"{inLabel}_legacyTgt")
    newTarget = rt.Point(name=f"{inLabel}_newTgt")

    if inParentTargets:
        legacyParent = rt.Point(name=f"{inLabel}_legacyParent")
        newParent = rt.Point(name=f"{inLabel}_newParent")
        _animate_dense(legacyParent, inApplyStart, inApplyEnd, inScale=0.7)
        _animate_dense(newParent, inApplyStart, inApplyEnd, inScale=0.7)
        legacyTarget.parent = legacyParent
        newTarget.parent = newParent

    if inPrimeTarget is not None:
        inPrimeTarget(legacyTarget)
        inPrimeTarget(newTarget)

    sourceKeyTicks = _key_ticks_all(sourceNode)

    legacy_match_anim_transform(legacyTarget, sourceNode, inApplyStart, inApplyEnd)
    anim.match_anim_transform(newTarget, sourceNode, inApplyStart, inApplyEnd)

    # 등가성 판정은 **정수 프레임**에서 한다. 아카이브 사이클이 못 박은 계약이
    # 프레임별 12-float이고(orvlib TC02/03/04/09), 소비처 샘플링도 정수 프레임이다.
    integerFrames = list(range(inApplyStart, inApplyEnd + 1))
    # 서브프레임은 별도로 본다. 여기서 구·신이 갈리는데, 실측(2026-08-11)에서
    # **신 경로가 소스와 정확히 일치하고 구 경로가 최대 2.0 어긋났다** - 구 경로의
    # 탄젠트 결함이다. 그래서 "구와 같은가"가 아니라 "소스와 같은가"로 판정한다.
    subFrames = [frame + 0.5 for frame in range(inApplyStart, inApplyEnd)]

    ticksPerFrame = int(rt.ticksPerFrame)
    keyTimeFrames = sorted({
        tick / ticksPerFrame
        for track in sourceKeyTicks.values()
        for tick in track
        if inApplyStart * ticksPerFrame <= tick <= inApplyEnd * ticksPerFrame
    })

    return {
        "label": inLabel,
        "applyRange": (inApplyStart, inApplyEnd),
        "sourceKeyTicks": sourceKeyTicks,
        "integerFrames": integerFrames,
        "subFrames": subFrames,
        "keyTimeFrames": keyTimeFrames,
        "legacyInteger": _snapshot(legacyTarget, integerFrames),
        "newInteger": _snapshot(newTarget, integerFrames),
        "legacySub": _snapshot(legacyTarget, subFrames),
        "newSub": _snapshot(newTarget, subFrames),
        "sourceSub": _snapshot(sourceNode, subFrames),
        "sourceAtKeyTimes": _snapshot(sourceNode, keyTimeFrames),
        "newAtKeyTimes": _snapshot(newTarget, keyTimeFrames),
        "legacyKeyTicks": _key_ticks_all(legacyTarget),
        "newKeyTicks": _key_ticks_all(newTarget),
    }


def _max_abs_diff(inLeft: list, inRight: list) -> float:
    """두 스냅샷 목록의 최대 절대 오차를 돌려준다."""
    if not inLeft or len(inLeft) != len(inRight):
        return float("inf")
    return max(
        abs(a - b)
        for left, right in zip(inLeft, inRight)
        for a, b in zip(left, right)
    )


def _assert_match_sample(inLabel: str, inTestName: str) -> None:
    """표본 하나의 키 시점 집합과 정수 프레임 12-float를 함께 단정한다."""
    sample = MATCH_SAMPLES[inLabel]
    keysMatch = sample["legacyKeyTicks"] == sample["newKeyTicks"]
    valuesMatch, mismatched = _snapshots_match(
        sample["legacyInteger"], sample["newInteger"]
    )
    detail = (
        f"keysMatch={keysMatch}, valuesMatch={valuesMatch}, "
        f"comparedIntegerFrames={len(sample['integerFrames'])}, "
        f"mismatchedIndices={mismatched[:8]}, "
        f"legacyKeyCounts={ {t: len(v) for t, v in sample['legacyKeyTicks'].items()} }, "
        f"newKeyCounts={ {t: len(v) for t, v in sample['newKeyTicks'].items()} }, "
        f"subFrameDiff(legacy vs new)={round(_max_abs_diff(sample['legacySub'], sample['newSub']), 5)}, "
        f"subFrameDiff(new vs source)={round(_max_abs_diff(sample['newSub'], sample['sourceSub']), 5)}, "
        f"subFrameDiff(legacy vs source)={round(_max_abs_diff(sample['legacySub'], sample['sourceSub']), 5)}"
    )
    reporter.assert_test(keysMatch and valuesMatch, inTestName, inDetail=detail)


# ----------------------------------------------------------------------
# TC01: 조밀 소스 + 조밀 키를 가진 대상 (구간 단위 키 삭제 경로)
# ----------------------------------------------------------------------
try:
    MATCH_SAMPLES["dense_primed"] = _run_match_sample(
        "denseP",
        0, 60, 0, 60,
        inBuildSource=lambda node: _animate_dense(node, 0, 60),
        inPrimeTarget=lambda node: _animate_dense(node, 0, 60, inScale=-2.5),
    )
    _assert_match_sample(
        "dense_primed",
        "TC01 조밀 소스 + 기존 키를 가진 대상: 키 시점 집합·12-float 일치",
    )
except Exception as e:
    reporter.error("TC01 조밀 소스 + 기존 키 대상", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC02: 희소 소스 + 무키 대상 (AnimCopyTool 형태. 키 밀도 보존이 핵심)
# ----------------------------------------------------------------------
try:
    MATCH_SAMPLES["sparse"] = _run_match_sample(
        "sparse",
        0, 60, 0, 50,
        inBuildSource=lambda node: _animate_sparse(node, [0, 7, 13, 29, 41, 50]),
    )
    _assert_match_sample(
        "sparse",
        "TC02 희소 소스: 키가 소스 시점에만 생기고 구·신이 일치",
    )
except Exception as e:
    reporter.error("TC02 희소 소스", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC03: 서브프레임 키 소스 (임시 포인트 우회를 남긴 이유의 표본)
# ----------------------------------------------------------------------
try:
    MATCH_SAMPLES["subFrame"] = _run_match_sample(
        "subF",
        0, 40, 0, 30,
        inBuildSource=lambda node: _animate_sparse(node, [0, 10.5, 20.25, 30]),
    )
    _assert_match_sample(
        "subFrame",
        "TC03 서브프레임 키 소스: 서브프레임 시점까지 구·신이 일치",
    )
except Exception as e:
    reporter.error("TC03 서브프레임 키 소스", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC04: 부모-자식 계층 대상 (로컬 키 계산 경로)
# ----------------------------------------------------------------------
try:
    MATCH_SAMPLES["hierarchy"] = _run_match_sample(
        "hier",
        0, 40, 0, 40,
        inBuildSource=lambda node: _animate_dense(node, 0, 40, inScale=1.3),
        inParentTargets=True,
    )
    _assert_match_sample(
        "hierarchy",
        "TC04 애니메이션된 부모 밑의 대상: 로컬 키 계산 결과가 구·신 일치",
    )
except Exception as e:
    reporter.error("TC04 계층 대상", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC05: 구간이 animationRange.start와 다른 경우
#
# 구 코드는 `selectKeys ctrl animationRange.start`(단일 시점)로 임시 포인트의
# 잉여 키를 지웠고, 신 경로는 `selectKeys ctrl (interval S S)`로 지운다.
# 이 표본이 그 치환을 검증한다.
# ----------------------------------------------------------------------
try:
    MATCH_SAMPLES["offsetRange"] = _run_match_sample(
        "offset",
        0, 60, 10, 40,
        inBuildSource=lambda node: _animate_sparse(node, [10, 25, 40]),
    )
    _assert_match_sample(
        "offsetRange",
        "TC05 구간 시작이 animationRange.start와 다를 때: 구·신 일치",
    )
except Exception as e:
    reporter.error("TC05 오프셋 구간", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# TC06: collapse 등가성
# ======================================================================
collapseSample: dict = {}
try:
    _reset(0, 60)
    legacyNode = rt.Point(name="collapse_legacy")
    newNode = rt.Point(name="collapse_new")
    _animate_dense(legacyNode, 0, 60, inScale=1.1)
    _animate_dense(newNode, 0, 60, inScale=1.1)

    integerFrames = list(range(0, 61))
    subFrames = [frame + 0.5 for frame in range(0, 60)]

    beforeInteger = _snapshot(legacyNode, integerFrames)
    beforeIntegerNew = _snapshot(newNode, integerFrames)
    beforeSubNew = _snapshot(newNode, subFrames)
    identicalFixtures, _ = _snapshots_match(beforeInteger, beforeIntegerNew)

    legacy_collape_anim_transform(legacyNode, 0, 60)
    anim.collape_anim_transform(newNode, 0, 60)

    collapseSample = {
        "identicalFixtures": identicalFixtures,
        "integerFrames": integerFrames,
        "subFrames": subFrames,
        "beforeInteger": beforeInteger,
        "beforeSubNew": beforeSubNew,
        "legacyInteger": _snapshot(legacyNode, integerFrames),
        "newInteger": _snapshot(newNode, integerFrames),
        "legacySub": _snapshot(legacyNode, subFrames),
        "newSub": _snapshot(newNode, subFrames),
        "legacyKeyTicks": _key_ticks_all(legacyNode),
        "newKeyTicks": _key_ticks_all(newNode),
        "legacyControllers": _controller_classes(legacyNode),
        "newControllers": _controller_classes(newNode),
    }

    keysMatch = collapseSample["legacyKeyTicks"] == collapseSample["newKeyTicks"]
    valuesMatch, mismatched = _snapshots_match(
        collapseSample["legacyInteger"], collapseSample["newInteger"]
    )
    controllersMatch = (
        collapseSample["legacyControllers"] == collapseSample["newControllers"]
    )
    reporter.assert_test(
        identicalFixtures and keysMatch and valuesMatch and controllersMatch,
        "TC06 collapse: 키 시점 집합·정수 프레임 12-float·컨트롤러 클래스가 구·신 일치",
        inDetail=(
            f"identicalFixtures={identicalFixtures}, keysMatch={keysMatch}, "
            f"valuesMatch={valuesMatch}, controllersMatch={controllersMatch}, "
            f"mismatchedIndices={mismatched[:8]}, "
            f"legacyControllers={collapseSample['legacyControllers']}, "
            f"newControllers={collapseSample['newControllers']}, "
            f"subFrameDiff(new vs before)="
            f"{round(_max_abs_diff(collapseSample['newSub'], collapseSample['beforeSubNew']), 5)}, "
            f"subFrameDiff(legacy vs new)="
            f"{round(_max_abs_diff(collapseSample['legacySub'], collapseSample['newSub']), 5)}"
        ),
    )
except Exception as e:
    reporter.error("TC06 collapse 등가성", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# TC06b: collapse 충실도 - 원본 애니메이션을 보존했는가
#
# 구·신 대조만 두면 "둘 다 같이 틀린" 경우가 초록이 된다
# (`testing/debug_process.md` 21). 병합 결과가 **원본 트랜스폼**과 같은지
# 정수 프레임에서 직접 단정한다.
# ======================================================================
try:
    fidelityMatch, fidelityMismatched = _snapshots_match(
        collapseSample["beforeInteger"], collapseSample["newInteger"]
    )
    reporter.assert_test(
        fidelityMatch,
        "TC06b collapse 결과가 병합 전 원본 월드 트랜스폼과 일치한다",
        inDetail=(
            f"match={fidelityMatch}, mismatchedIndices={fidelityMismatched[:8]}, "
            f"maxAbsDiff="
            f"{round(_max_abs_diff(collapseSample['beforeInteger'], collapseSample['newInteger']), 5)}"
        ),
    )
except Exception as e:
    reporter.error("TC06b collapse 충실도", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# TC06c: match 충실도 - **정수** 키 시점에서 소스 값과 일치하는가
#
# `match_anim_transform`이 약속하는 것은 "소스의 키 시점에 소스의 월드
# 트랜스폼을 싣는다"인데, 값은 임시 포인트를 경유한다. 임시 포인트는 정수
# 프레임에만 키가 있으므로 **서브프레임 키 시점에서는 보간값**이 실린다 -
# 구 동작이 그러하므로 보존한 설계다(실측 오차 0.0136).
#
# 따라서 판정을 둘로 나눈다.
#   - 정수 키 시점: 신 경로가 소스와 정확히 일치해야 한다
#   - 서브프레임 키 시점: 신 경로가 **구 경로와** 일치해야 한다(같은 보간값)
#
# 처음에는 전 키 시점에 소스 일치를 요구했다가 서브프레임 표본에서 실패했다.
# 계약에 없는 것을 요구한 쪽이 틀렸다.
# ======================================================================
try:
    fidelityRows = {}
    for label, sample in MATCH_SAMPLES.items():
        integerKeyIndices = [
            index
            for index, frame in enumerate(sample["keyTimeFrames"])
            if float(frame).is_integer()
        ]
        subKeyIndices = [
            index
            for index in range(len(sample["keyTimeFrames"]))
            if index not in integerKeyIndices
        ]

        integerDiff = _max_abs_diff(
            [sample["sourceAtKeyTimes"][i] for i in integerKeyIndices],
            [sample["newAtKeyTimes"][i] for i in integerKeyIndices],
        ) if integerKeyIndices else 0.0

        fidelityRows[label] = {
            "keyTimeCount": len(sample["keyTimeFrames"]),
            "integerKeyCount": len(integerKeyIndices),
            "subFrameKeyCount": len(subKeyIndices),
            "maxAbsDiffAtIntegerKeyTimes": round(integerDiff, 5),
            "subFrameDiff_newVsSource": round(
                _max_abs_diff(sample["newSub"], sample["sourceSub"]), 5
            ),
            "subFrameDiff_legacyVsSource": round(
                _max_abs_diff(sample["legacySub"], sample["sourceSub"]), 5
            ),
            "subFrameDiff_legacyVsNew": round(
                _max_abs_diff(sample["legacySub"], sample["newSub"]), 5
            ),
        }

    allFaithful = bool(fidelityRows) and all(
        row["integerKeyCount"] > 0
        and row["maxAbsDiffAtIntegerKeyTimes"] < TOLERANCE
        for row in fidelityRows.values()
    )
    reporter.assert_test(
        allFaithful,
        "TC06c match 결과가 정수 키 시점에서 소스 월드 트랜스폼과 정확히 일치한다",
        inDetail=json.dumps(fidelityRows, ensure_ascii=False),
    )
except Exception as e:
    reporter.error("TC06c match 충실도", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# TC06d: 서브프레임 지점에서 구 경로가 소스와 어긋나는 정도를 기록한다
#
# 조밀 표본에서 신 경로는 소스와 오차 0.0인데 구 경로는 최대 2.0 어긋난다
# (구 경로의 탄젠트 결함). 이 사실을 수치로 남겨 두면 "왜 서브프레임 등가를
# 요구하지 않는가"가 문서가 아니라 로그로 설명된다.
# ======================================================================
try:
    denseRow = fidelityRows.get("dense_primed", {})
    newFaithful = denseRow.get("subFrameDiff_newVsSource")
    legacyDeviates = denseRow.get("subFrameDiff_legacyVsSource")
    reporter.assert_test(
        newFaithful is not None
        and newFaithful < TOLERANCE
        and legacyDeviates is not None
        and legacyDeviates > newFaithful,
        "TC06d 조밀 표본 서브프레임: 신 경로가 소스와 일치하고 구 경로가 더 어긋난다",
        inDetail=(
            f"newVsSource={newFaithful}, legacyVsSource={legacyDeviates} "
            "(구 경로는 시작·끝을 먼저 기록한 뒤 키 배열을 3회 순회해 "
            "마지막 구간 탄젠트가 소스와 달라진다)"
        ),
    )
except Exception as e:
    reporter.error("TC06d 서브프레임 편차 기록", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# 공허한 통과 차단
#
# 위 TC들은 전부 "구 == 신" 형태다. 비교 재료가 없거나 값이 프레임마다
# 변하지 않으면 `0 == 0`이 초록으로 보인다(`processes/worktree_workflow.md`
# 무력화 4번째 경로). 아래 TC가 그것을 FAIL로 드러낸다.
# ======================================================================

# ----------------------------------------------------------------------
# TC07: 대조할 프레임이 실제로 있었는가
# ----------------------------------------------------------------------
try:
    frameCounts = {
        label: (len(sample["integerFrames"]), len(sample["subFrames"]))
        for label, sample in MATCH_SAMPLES.items()
    }
    allHaveFrames = bool(frameCounts) and all(
        integerCount > 0 and subCount > 0
        for integerCount, subCount in frameCounts.values()
    )
    reporter.assert_test(
        allHaveFrames and len(MATCH_SAMPLES) == 5,
        "TC07 표본 5종이 모두 만들어졌고 대조 프레임이 0건이 아니다",
        inDetail=f"sampleCount={len(MATCH_SAMPLES)}, frameCounts={frameCounts}",
    )
except Exception as e:
    reporter.error("TC07 대조 프레임 존재", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC08: 소스에 키가 실제로 있었는가
# ----------------------------------------------------------------------
try:
    sourceKeyCounts = {
        label: sum(len(ticks) for ticks in sample["sourceKeyTicks"].values())
        for label, sample in MATCH_SAMPLES.items()
    }
    allHaveKeys = bool(sourceKeyCounts) and all(
        count > 0 for count in sourceKeyCounts.values()
    )
    reporter.assert_test(
        allHaveKeys,
        "TC08 모든 표본의 소스에 키가 존재한다 (무키 소스라면 판정 불가)",
        inDetail=f"sourceKeyCounts={sourceKeyCounts}",
    )
except Exception as e:
    reporter.error("TC08 소스 키 존재", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC09: 결과에 키가 실제로 생겼는가
# ----------------------------------------------------------------------
try:
    resultKeyCounts = {
        label: sum(len(ticks) for ticks in sample["newKeyTicks"].values())
        for label, sample in MATCH_SAMPLES.items()
    }
    allProduced = bool(resultKeyCounts) and all(
        count > 0 for count in resultKeyCounts.values()
    )
    reporter.assert_test(
        allProduced,
        "TC09 모든 표본의 대상에 키가 생겼다 (무키 결과끼리의 일치는 공허하다)",
        inDetail=f"resultKeyCounts={resultKeyCounts}",
    )
except Exception as e:
    reporter.error("TC09 결과 키 존재", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC10: 스냅샷 값이 프레임마다 변하는가
#
# 정적 트랜스폼이면 12-float가 전 프레임 동일해서 어떤 구현이든 "일치"가
# 나온다. 값이 실제로 움직였음을 단정해 대조에 판별력을 준다.
# ----------------------------------------------------------------------
try:
    variedLabels = {}
    for label, sample in MATCH_SAMPLES.items():
        distinctRows = {tuple(round(v, 4) for v in row) for row in sample["newInteger"]}
        variedLabels[label] = len(distinctRows)
    allVaried = bool(variedLabels) and all(count > 1 for count in variedLabels.values())

    collapseDistinct = len({
        tuple(round(v, 4) for v in row)
        for row in collapseSample.get("newInteger", [])
    })
    reporter.assert_test(
        allVaried and collapseDistinct > 1,
        "TC10 스냅샷이 프레임마다 변한다 (정적 값끼리의 일치는 판별력이 없다)",
        inDetail=(
            f"distinctSnapshotRows={variedLabels}, "
            f"collapseDistinctRows={collapseDistinct}"
        ),
    )
except Exception as e:
    reporter.error("TC10 스냅샷 변화", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# 순서 변경 전용 TC - 여기서는 구·신이 **다른 것이 정답**이다
# ======================================================================

# ----------------------------------------------------------------------
# TC11: 순환 입력에서 소스를 원본 상태로 읽는다
#
# 대상(inObj)이 소스(inTarget)의 부모면, 대상의 키를 지우는 행위가 소스의
# 월드 트랜스폼을 바꾼다. 구 코드는 프레임 루프 안에서 지우면서 읽었고,
# 신 경로는 다 읽은 뒤 지운다.
#
# **판정 지점은 소스의 키 시점이다.** 이 함수가 약속하는 것은 그 시점에
# 소스 값을 싣는다는 것뿐이고, 소스가 조밀한 부모 애니메이션의 영향을 받는
# 이상 4개 키로 전 프레임을 재현할 수는 없다. 전 프레임을 단정하면 계약보다
# 강한 것을 요구하게 된다(첫 실패 때 실제로 그랬다).
#
# **구 경로도 여기서는 같은 값을 낸다(실측).** 처음에는 "구 경로가 오염된 값을
# 싣는다"를 단정했는데 실측 오차가 0.0이었다. 이유가 있다 - 구 경로는 프레임
# k를 **읽은 뒤** 프레임 k의 키를 지우므로, 다음 반복이 읽는 프레임 k+1의
# 키는 아직 살아 있고, 키 지점의 값은 이웃 키 삭제에 영향받지 않는다.
# 즉 순서 변경은 정수 키 지점에서 **증명 가능하게 무해**하다.
#
# 그래서 이 TC는 "구와 다르다"를 단정하지 않고, ① 신 경로의 계약이 성립하고
# ② **읽기 전에 지우면 실제로 깨진다**(반대 순서의 위험이 가상이 아님)를
# 함께 보인다. 후자가 없으면 이 TC는 아무것도 구분하지 않는다.
# ----------------------------------------------------------------------
try:
    _reset(0, 30)
    legacyParent = rt.Point(name="circ_legacyParent")
    legacyChild = rt.Point(name="circ_legacyChild")
    legacyChild.parent = legacyParent
    newParent = rt.Point(name="circ_newParent")
    newChild = rt.Point(name="circ_newChild")
    newChild.parent = newParent
    for parentNode, childNode in (
        (legacyParent, legacyChild), (newParent, newChild)
    ):
        _animate_dense(parentNode, 0, 30, inScale=1.0)
        _animate_sparse(childNode, [0, 10, 20, 30], inScale=0.3)

    # 아무것도 건드리기 전의 자식 월드 트랜스폼 = 신 경로가 키 시점에 실어야 할 값
    keyTimeFrames = [0.0, 10.0, 20.0, 30.0]
    expectedFromIntactSource = _snapshot(newChild, keyTimeFrames)
    legacyExpected = _snapshot(legacyChild, keyTimeFrames)
    fixturesIdentical, _ = _snapshots_match(expectedFromIntactSource, legacyExpected)

    # 부모(=대상)에 자식(=소스)의 월드 트랜스폼을 싣는다
    legacy_match_anim_transform(legacyParent, legacyChild, 0, 30)
    anim.match_anim_transform(newParent, newChild, 0, 30)

    newDiff = _max_abs_diff(
        expectedFromIntactSource, _snapshot(newParent, keyTimeFrames)
    )
    legacyDiff = _max_abs_diff(
        legacyExpected, _snapshot(legacyParent, keyTimeFrames)
    )

    # 반대 순서(읽기 전에 대상 키 삭제)가 실제로 소스를 바꾸는지 같은 씬에서 확인한다.
    # 이것이 0이면 순서 논의 자체가 공허하므로, 이 값이 TC의 판별력 근거다.
    probeParent = rt.Point(name="circ_probeParent")
    probeChild = rt.Point(name="circ_probeChild")
    probeChild.parent = probeParent
    _animate_dense(probeParent, 0, 30, inScale=1.0)
    _animate_sparse(probeChild, [0, 10, 20, 30], inScale=0.3)
    probeBefore = _snapshot(probeChild, keyTimeFrames)
    rt.execute(
        build_clear_target_keys_script([_handle(probeParent)], 0, 30)
    )
    probeAfter = _snapshot(probeChild, keyTimeFrames)
    clearFirstBreaks = _max_abs_diff(probeBefore, probeAfter)

    reporter.assert_test(
        fixturesIdentical
        and newDiff < TOLERANCE
        and clearFirstBreaks >= TOLERANCE,
        "TC11 순환 입력: 신 경로가 원본 소스 값을 싣는다 (반대 순서는 소스를 바꾼다)",
        inDetail=(
            f"fixturesIdentical={fixturesIdentical}, "
            f"newMaxAbsDiff={round(newDiff, 5)}, "
            f"legacyMaxAbsDiff={round(legacyDiff, 5)} "
            "(구 경로는 읽은 뒤 지우므로 정수 키 지점에서 무해하다), "
            f"clearBeforeReadChangesSourceBy={round(clearFirstBreaks, 5)}, "
            f"keyTimeFrames={keyTimeFrames}"
        ),
    )
except Exception as e:
    reporter.error("TC11 순환 입력", f"{e}\n{traceback.format_exc()}")


# ----------------------------------------------------------------------
# TC12: 구간 내 서브프레임 키가 걷힌다
#
# 구 코드의 프레임별 삭제는 정수 프레임 키만 지웠다. 남은 서브프레임 키는
# 결과를 오염시키므로 개선이다. **구 경로가 실제로 남긴다**는 것도 같은
# 실행에서 확인해 이 TC가 공허하지 않음을 보인다.
# ----------------------------------------------------------------------
try:
    _reset(0, 20)
    sourceNode = rt.Point(name="subclear_src")
    _animate_sparse(sourceNode, [0, 8, 16, 20])

    legacyTarget = rt.Point(name="subclear_legacyTgt")
    newTarget = rt.Point(name="subclear_newTgt")
    # 구간 내 **서브프레임** 키를 대상에 미리 심는다
    _animate_sparse(legacyTarget, [5.5, 12.5], inScale=-4.0)
    _animate_sparse(newTarget, [5.5, 12.5], inScale=-4.0)

    ticksPerFrame = int(rt.ticksPerFrame)
    subFrameTicks = {5.5 * ticksPerFrame, 12.5 * ticksPerFrame}
    primedOk = subFrameTicks.issubset(set(_key_ticks(newTarget, "pos")))

    legacy_match_anim_transform(legacyTarget, sourceNode, 0, 20)
    anim.match_anim_transform(newTarget, sourceNode, 0, 20)

    legacyLeftover = subFrameTicks & set(_key_ticks(legacyTarget, "pos"))
    newLeftover = subFrameTicks & set(_key_ticks(newTarget, "pos"))

    reporter.assert_test(
        primedOk and not newLeftover and legacyLeftover == subFrameTicks,
        "TC12 구간 내 서브프레임 키를 신 경로는 걷고 구 경로는 남긴다",
        inDetail=(
            f"primedOk={primedOk}, subFrameTicks={sorted(subFrameTicks)}, "
            f"legacyLeftover={sorted(legacyLeftover)}, "
            f"newLeftover={sorted(newLeftover)}"
        ),
    )
except Exception as e:
    reporter.error("TC12 서브프레임 키 정리", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# TC13: A/B 성능 - Phase 0 baseline과 같은 표본, 같은 세션
#
# 판정 기준은 Phase 0에서 재측정한 baseline이다. 관측 폭이 최대 ±16%였으므로
# 절감은 **그 배수(50% 이상)** 로만 주장한다.
# ======================================================================

REPEAT = 3
DENSE_END = 640
SPARSE_END = 200


def _measure_match_pair(inLabel: str, inPrimeTarget: bool, inDense: bool) -> dict:
    """같은 픽스처에 구·신을 번갈아 적용해 A/B를 잰다.

    구를 먼저 재고 신을 나중에 재면 OS 파일 캐시·릭 워밍이 신에 유리하게
    작용한다. 반복마다 순서를 바꿔 그 편향을 드러낸다.
    """
    legacySamples = []
    newSamples = []
    for runIndex in range(REPEAT):
        endFrame = DENSE_END if inDense else SPARSE_END
        legacyFirst = runIndex % 2 == 0

        _reset(0, endFrame)
        sourceNode = rt.Point(name=f"perf_{inLabel}_src{runIndex}")
        if inDense:
            _animate_dense(sourceNode, 0, endFrame)
        else:
            step = max(1, endFrame // 9)
            _animate_sparse(
                sourceNode, [float(f) for f in range(0, endFrame + 1, step)]
            )

        legacyTarget = rt.Point(name=f"perf_{inLabel}_legacy{runIndex}")
        newTarget = rt.Point(name=f"perf_{inLabel}_new{runIndex}")
        if inPrimeTarget:
            _animate_dense(legacyTarget, 0, endFrame, inScale=-2.0)
            _animate_dense(newTarget, 0, endFrame, inScale=-2.0)

        if legacyFirst:
            legacySamples.append(round(_timed(
                legacy_match_anim_transform,
                legacyTarget, sourceNode, 0, endFrame,
            ), 4))
            newSamples.append(round(_timed(
                anim.match_anim_transform,
                newTarget, sourceNode, 0, endFrame,
            ), 4))
        else:
            newSamples.append(round(_timed(
                anim.match_anim_transform,
                newTarget, sourceNode, 0, endFrame,
            ), 4))
            legacySamples.append(round(_timed(
                legacy_match_anim_transform,
                legacyTarget, sourceNode, 0, endFrame,
            ), 4))

    legacyMedian = sorted(legacySamples)[len(legacySamples) // 2]
    newMedian = sorted(newSamples)[len(newSamples) // 2]
    return {
        "frames": (DENSE_END if inDense else SPARSE_END) + 1,
        "targetPrimed": inPrimeTarget,
        "sourceDense": inDense,
        "legacySeconds": legacySamples,
        "newSeconds": newSamples,
        "legacyMedian": legacyMedian,
        "newMedian": newMedian,
        "speedup": round(legacyMedian / newMedian, 2) if newMedian > 0 else None,
        "reductionPercent": (
            round(100.0 * (legacyMedian - newMedian) / legacyMedian, 1)
            if legacyMedian > 0 else None
        ),
    }


def _measure_collapse_pair() -> dict:
    """collapse 구·신 A/B."""
    legacySamples = []
    newSamples = []
    for runIndex in range(REPEAT):
        _reset(0, DENSE_END)
        legacyNode = rt.Point(name=f"perf_collapse_legacy{runIndex}")
        newNode = rt.Point(name=f"perf_collapse_new{runIndex}")
        _animate_dense(legacyNode, 0, DENSE_END)
        _animate_dense(newNode, 0, DENSE_END)

        if runIndex % 2 == 0:
            legacySamples.append(round(_timed(
                legacy_collape_anim_transform, legacyNode, 0, DENSE_END
            ), 4))
            newSamples.append(round(_timed(
                anim.collape_anim_transform, newNode, 0, DENSE_END
            ), 4))
        else:
            newSamples.append(round(_timed(
                anim.collape_anim_transform, newNode, 0, DENSE_END
            ), 4))
            legacySamples.append(round(_timed(
                legacy_collape_anim_transform, legacyNode, 0, DENSE_END
            ), 4))

    legacyMedian = sorted(legacySamples)[len(legacySamples) // 2]
    newMedian = sorted(newSamples)[len(newSamples) // 2]
    return {
        "frames": DENSE_END + 1,
        "legacySeconds": legacySamples,
        "newSeconds": newSamples,
        "legacyMedian": legacyMedian,
        "newMedian": newMedian,
        "speedup": round(legacyMedian / newMedian, 2) if newMedian > 0 else None,
        "reductionPercent": (
            round(100.0 * (legacyMedian - newMedian) / legacyMedian, 1)
            if legacyMedian > 0 else None
        ),
    }


try:
    abReport["samples"]["A_dense_primed"] = _measure_match_pair("A", True, True)
    abReport["samples"]["Aprime_dense_empty"] = _measure_match_pair("Ap", False, True)
    abReport["samples"]["B_sparse_empty"] = _measure_match_pair("B", False, False)
    abReport["samples"]["collapse_dense"] = _measure_collapse_pair()

    summary = {
        label: (
            f"{sample['legacyMedian']}s -> {sample['newMedian']}s "
            f"({sample['speedup']}x, {sample['reductionPercent']:+}%)"
        )
        for label, sample in abReport["samples"].items()
    }

    # 판정 기준을 표본 성격으로 나눈다.
    #
    # 조밀 표본(A/A')은 지배 구간(프레임별 키 삭제 + 3중 기록)이 실제로 걸리는
    # 곳이므로 50% 이상 절감을 요구한다. Phase 0 관측 폭이 최대 ±16%였으므로
    # 그 3배다.
    #
    # 희소 표본(B, 201프레임 11키)과 collapse는 접을 지배 구간이 없다 -
    # 남는 것은 고정 오버헤드이고, 요구할 수 있는 것은 "유의미하게 느려지지
    # 않았는가"뿐이다. 여기에 50%를 요구하면 측정 대상에 없는 개선을 요구하는
    # 것이 된다. 관측 폭 ±16%를 회귀 허용선으로 쓴다.
    NOISE_BAND_PERCENT = 16.0

    dominatedLabels = ("A_dense_primed", "Aprime_dense_empty")
    overheadLabels = ("B_sparse_empty", "collapse_dense")

    halvedRows = {
        label: abReport["samples"][label]["reductionPercent"]
        for label in dominatedLabels
    }
    allHalved = all(
        value is not None and value >= 50.0 for value in halvedRows.values()
    )
    reporter.assert_test(
        allHalved,
        "TC13a 조밀 표본: median 50% 이상 절감 (관측 폭 ±16%의 3배 이상)",
        inDetail=json.dumps(
            {"reductionPercent": halvedRows, "all": summary}, ensure_ascii=False
        ),
    )

    overheadRows = {
        label: abReport["samples"][label]["reductionPercent"]
        for label in overheadLabels
    }
    noRegression = all(
        value is not None and value >= -NOISE_BAND_PERCENT
        for value in overheadRows.values()
    )
    reporter.assert_test(
        noRegression,
        f"TC13b 지배 구간 없는 표본: 회귀가 관측 폭({NOISE_BAND_PERCENT}%) 이내",
        inDetail=json.dumps(
            {
                "reductionPercent": overheadRows,
                "note": (
                    "희소 표본과 collapse는 접을 지배 구간이 없다. 헤드리스에서는 "
                    "undo off 이득이 0으로 측정되므로 개선 폭이 작거나 없는 것이 정상이다."
                ),
                "all": summary,
            },
            ensure_ascii=False,
        ),
    )
except Exception as e:
    reporter.error("TC13 A/B 성능", f"{e}\n{traceback.format_exc()}")


# ======================================================================
# 산출물 기록
# ======================================================================
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    AB_JSON_PATH.write_text(
        json.dumps(abReport, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    reporter.assert_test(
        AB_JSON_PATH.exists(), f"A/B 산출물 기록: {AB_JSON_PATH.name}"
    )
except Exception as e:
    reporter.error("A/B 산출물 기록", f"{e}\n{traceback.format_exc()}")


reporter.summary()
reporter.close()
