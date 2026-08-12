#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`match_anim_transform` / `collape_anim_transform` 최적화 Phase 0 프로브 (Type C).

이 파일은 **테스트가 아니라 프로브**다. 판정을 내리는 것이 아니라 코드로 굳히기 전에
모르는 것을 실측한다(`max/max_test_pattern.md` 프로브 4원칙 - `_try`로 실패도 정보,
여러 Phase를 한 파일에서 1회 실행, 결함 수치 재현으로 판별력 보증).

확인 대상:

- P1 MAXScript `sort`가 time 값 배열에서 동작하는가. `key.time as float` 왕복이 tick을 보존하는가
- P2 `disableSceneRedraw`가 중첩 카운트되는가 (`bake_world_transforms` 내부 호출과 겹친다)
- P3 무키 컨트롤러 첫 기록 시 `animationRange.start` 스퓨리어스 키가 생기는가
      (현행 두 함수의 "정리 블록"이 실제로 무엇을 지우는지)
- P4 현행 두 함수가 만드는 **키 시점 집합** 덤프 (Phase 3 등가성 대조의 기대값 출처)
- P5 단일 노드 baseline 계측 (표본 3종). Phase 3 성능 판정 기준의 출처

산출물: `tests/logs/test_AnimMatchProbe.log` + `tests/logs/anim_match_probe.json`

**측정 한계(먼저 적는다):** `3dsmaxbatch`는 Undo가 애초에 비활성이라 `undo off` 도입 효과가
정확히 0으로 측정된다. 여기 숫자는 **구조적 개선분(O(프레임²) 제거·3중 기록 제거)만** 담는다.

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

# 배포본 선로드 퍼지. Max는 기동 시 배포본을 sys.modules에 선점하므로
# 경로 삽입만으로는 워크트리 소스가 로드되지 않는다.
for _moduleName in [
    name for name in sys.modules
    if name == "pyjallib" or name.startswith("pyjallib.")
]:
    del sys.modules[_moduleName]

import pyjallib  # noqa: E402
from pymxs import runtime as rt  # noqa: E402
from pyjallib.max.anim import Anim  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
JSON_PATH = LOG_DIR / "anim_match_probe.json"
reporter = TestReporter("AnimMatchProbe", LOG_DIR)

anim = Anim()

# 프로브 결과를 구조화해 남긴다. 러너 stdout은 tail만 잡히므로 JSON이 정본이다.
findings: dict = {
    "host": os.environ.get("PYJALLIB_TEST_HOST", "unknown"),
    "ticksPerFrame": None,
    "probes": {},
    "baseline": {},
}


# ======================================================================
# 공통 헬퍼
# ======================================================================

def _try(inLabel: str, inFunc):
    """프로브 1건을 실행한다. 실패해도 그 자체가 정보이므로 기록만 하고 계속한다.

    Args:
        inLabel: 프로브 이름
        inFunc: 인자 없이 호출 가능한 프로브 본체

    Returns:
        프로브 반환값. 예외가 나면 None
    """
    try:
        value = inFunc()
        findings["probes"][inLabel] = value
        reporter.assert_test(True, f"PROBE {inLabel}", inDetail=json.dumps(
            value, ensure_ascii=False, default=str
        ))
        return value
    except Exception as e:
        findings["probes"][inLabel] = {"error": str(e)}
        reporter.error(f"PROBE {inLabel}", f"{e}\n{traceback.format_exc()}")
        return None


def _reset(inStartFrame: int, inEndFrame: int) -> None:
    """씬을 리셋하고 애니메이션 구간을 설정한다."""
    rt.resetMaxFile(rt.name("noPrompt"), quiet=True)
    rt.animationRange = rt.interval(inStartFrame, inEndFrame)


def _handle(inNode) -> int:
    """노드 핸들을 정수로 돌려준다. 이름은 동명·자동 리네임에 무너진다."""
    return int(rt.getHandleByAnim(inNode))


def _key_tick_times(inNode, inTrack: str) -> list:
    """컨트롤러의 키 시점을 **틱** 목록으로 덤프한다.

    pymxs는 키 조회 API를 노출하지 않으므로 MAXScript를 경유한다
    (`max/pymxs_pitfalls_advanced.md`).

    **단위 주의(P1 실측).** ``key.time as float``은 **프레임이 아니라 틱**을
    돌려준다. 반대로 ``at time <숫자>``는 숫자를 **프레임**으로 읽으므로 이
    값을 그대로 되먹이면 시간축이 ticksPerFrame배로 늘어난다. 그래서
    프로덕션 경로는 float 변환 없이 time 값을 그대로 다룬다.

    Args:
        inNode: 대상 노드
        inTrack: ``"pos"`` / ``"rotation"`` / ``"scale"``

    Returns:
        틱 단위 float 목록. 키가 없으면 빈 목록
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


def _all_key_times(inNode) -> dict:
    """pos/rotation/scale 키 시점을 한 번에 덤프한다."""
    return {
        track: _key_tick_times(inNode, track)
        for track in ("pos", "rotation", "scale")
    }


def _animate_dense(inNode, inStartFrame: int, inEndFrame: int, inScale: float = 1.0) -> None:
    """구간 전 프레임에 위치·회전 키를 심는다 (MAXScript 한 블록).

    픽스처 생성 비용은 계측 대상이 아니므로 ``undo off``로 감싼다.
    """
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
    """지정한 시점들에만 위치·회전 키를 심는다.

    Args:
        inNode: 대상 노드
        inFrames: 키를 심을 시점 목록 (프레임. float면 서브프레임 키가 된다)
        inScale: 값 스케일
    """
    frameText = ",".join(str(float(frame)) for frame in inFrames)
    script = (
        "(\n"
        f"    local node = getAnimByHandle {_handle(inNode)}\n"
        f"    local frames = #({frameText})\n"
        "    with undo off (\n"
        "        for f in frames do (\n"
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
    """호출 1회의 소요 시간(초)을 잰다.

    프로덕션 코드에 타이머를 심지 않고 **호출부에서** 잰다
    (`patterns/performance_measurement.md`).
    """
    startedAt = time.perf_counter()
    inFunc(*args, **kwargs)
    return time.perf_counter() - startedAt


# ======================================================================
# TC00: 로드 출처 어서션
#
# 이 한 줄이 "통과했지만 배포본을 검증한" 무력화를 영구히 막는다
# (`processes/worktree_workflow.md`).
# ======================================================================
try:
    loadedFrom = str(Path(pyjallib.__file__).resolve())
    expectedRoot = str((Path(__file__).parent.parent.parent / "src").resolve())
    findings["pyjallibLoadedFrom"] = loadedFrom
    reporter.assert_test(
        loadedFrom.startswith(expectedRoot),
        "TC00 pyjallib이 워크트리 소스에서 로드됐다",
        inDetail=f"loadedFrom={loadedFrom}, expectedRoot={expectedRoot}",
    )
except Exception as e:
    reporter.error("TC00 로드 출처", f"{e}\n{traceback.format_exc()}")


findings["ticksPerFrame"] = int(rt.ticksPerFrame)
findings["frameRate"] = int(rt.frameRate)


# ======================================================================
# P1: MAXScript sort / key.time 표현
#
# 신 경로는 pos/rot/scale 키 시점을 **한 배열에 모아 정렬·중복 제거**한 뒤
# 시점마다 1회만 기록한다. 그 조립이 성립하는지 먼저 잰다.
# ======================================================================

def _probe_sort_and_time_roundtrip() -> dict:
    """time 값 배열의 정렬과 float 왕복을 확인한다."""
    _reset(0, 30)
    sourceNode = rt.Point(name="p1_src")
    # 역순으로 심어 sort가 실제로 일을 하게 만든다. 10.5는 서브프레임 키다.
    _animate_sparse(sourceNode, [20.0, 0.0, 10.5, 7.0])

    script = (
        "(\n"
        f"    local node = getAnimByHandle {_handle(sourceNode)}\n"
        "    local raw = #()\n"
        "    for k in node.pos.controller.keys do append raw k.time\n"
        "    local asIs = raw as string\n"
        "    sort raw\n"
        "    local sortedTimes = raw as string\n"
        "    local floats = #()\n"
        "    for k in node.pos.controller.keys do append floats (k.time as float)\n"
        "    sort floats\n"
        "    local tickBack = #()\n"
        "    for f in floats do append tickBack ((at time f currentTime) as integer)\n"
        "    (asIs + \"|\" + sortedTimes + \"|\" + (floats as string)"
        " + \"|\" + (tickBack as string))\n"
        ")"
    )
    parts = str(rt.execute(script)).split("|")

    # float 시점으로 다른 노드에 기록해도 같은 tick에 키가 앉는지 확인한다.
    targetNode = rt.Point(name="p1_tgt")
    sourceTimes = _key_tick_times(sourceNode, "pos")
    _animate_sparse(targetNode, sourceTimes)
    targetTimes = _key_tick_times(targetNode, "pos")

    return {
        "keysAsCollected": parts[0] if len(parts) > 0 else None,
        "keysAfterSort": parts[1] if len(parts) > 1 else None,
        "floatsAfterSort": parts[2] if len(parts) > 2 else None,
        "ticksFromFloat": parts[3] if len(parts) > 3 else None,
        "sourceKeyTimes": sourceTimes,
        "targetKeyTimesAfterFloatWrite": targetTimes,
        "roundTripPreserved": sourceTimes == targetTimes,
    }


_try("P1_sort_and_time_roundtrip", _probe_sort_and_time_roundtrip)


# ======================================================================
# P2: disableSceneRedraw 중첩 카운트
#
# 재구현한 두 함수는 자신도 redraw를 끄면서 내부에서
# `bake_world_transforms`(자체 disable/enable)를 부른다. 카운트되지 않으면
# 내부의 enable이 남은 구간의 redraw를 되살린다.
# ======================================================================

def _probe_disable_scene_redraw_nesting() -> dict:
    """disableSceneRedraw / enableSceneRedraw 반환값을 관찰한다."""
    _reset(0, 10)
    script = (
        "(\n"
        "    local a = disableSceneRedraw()\n"
        "    local b = disableSceneRedraw()\n"
        "    local c = enableSceneRedraw()\n"
        "    local d = enableSceneRedraw()\n"
        "    ((a as string) + \",\" + (b as string) + \",\""
        " + (c as string) + \",\" + (d as string))\n"
        ")"
    )
    raw = str(rt.execute(script))
    values = [token.strip() for token in raw.split(",")]
    return {
        "returns": values,
        "note": "값이 증감하면 중첩 카운트, 전부 같으면 단일 플래그",
    }


_try("P2_disable_scene_redraw_nesting", _probe_disable_scene_redraw_nesting)


# ======================================================================
# P3: animationRange.start 스퓨리어스 키
#
# 현행 두 함수는 "S != animationRange.start이면 animationRange.start의 키를
# 지운다"는 블록을 갖고 있다. 그 블록이 지우는 것이 실제로 존재하는지,
# `bake_world_transforms` 경로에서도 생기는지 확인한다.
# ======================================================================

def _probe_spurious_range_start_key() -> dict:
    """무키 노드에 구간 밖 시점부터 기록할 때 생기는 키를 관찰한다."""
    _reset(0, 100)
    sourceNode = rt.Point(name="p3_src")
    _animate_dense(sourceNode, 10, 40)

    # (a) 현행 방식: at time k + animate on 직접 루프
    manualNode = rt.Point(name="p3_manual")
    script = (
        "(\n"
        f"    local src = getAnimByHandle {_handle(sourceNode)}\n"
        f"    local tgt = getAnimByHandle {_handle(manualNode)}\n"
        "    for k = 10 to 40 do (\n"
        "        at time k (with animate on tgt.transform = src.transform)\n"
        "    )\n"
        "    ok\n"
        ")"
    )
    rt.execute(script)

    # (b) 신 경로: bake_world_transforms
    bakedNode = rt.Point(name="p3_baked")
    anim.bake_world_transforms(
        [sourceNode], [bakedNode], 10, 40, inTargetStartFrame=10
    )

    manualTimes = _all_key_times(manualNode)
    bakedTimes = _all_key_times(bakedNode)
    return {
        "animationRange": [
            int(rt.animationRange.start), int(rt.animationRange.end)
        ],
        "manualLoopKeyTimes": manualTimes,
        "bakeWorldTransformsKeyTimes": bakedTimes,
        "manualHasRangeStartKey": 0.0 in manualTimes["pos"],
        "bakeHasRangeStartKey": 0.0 in bakedTimes["pos"],
    }


_try("P3_spurious_range_start_key", _probe_spurious_range_start_key)


# ======================================================================
# P4: 현행 두 함수의 키 시점 집합 덤프
#
# 등가 최적화이므로 **이 집합이 Phase 3의 기대값**이다. 값만 대조하면
# "키가 늘어난 것"을 놓친다.
# ======================================================================

def _probe_current_match_key_times() -> dict:
    """현행 match_anim_transform이 만드는 키 시점을 표본별로 덤프한다."""
    result = {}

    # (a) 희소 소스 - AnimCopyTool 형태. 키 시점 보존이 핵심인 표본
    _reset(0, 50)
    sparseSource = rt.Point(name="p4_sparse_src")
    sparseFrames = [0.0, 7.0, 13.0, 29.0, 41.0, 50.0]
    _animate_sparse(sparseSource, sparseFrames)
    sparseTarget = rt.Point(name="p4_sparse_tgt")
    anim.match_anim_transform(sparseTarget, sparseSource, 0, 50)
    result["sparse"] = {
        "sourceKeyTimes": _all_key_times(sparseSource),
        "targetKeyTimes": _all_key_times(sparseTarget),
    }

    # (b) 조밀 소스 - orvlib 헬퍼 형태
    _reset(0, 30)
    denseSource = rt.Point(name="p4_dense_src")
    _animate_dense(denseSource, 0, 30)
    denseTarget = rt.Point(name="p4_dense_tgt")
    anim.match_anim_transform(denseTarget, denseSource, 0, 30)
    result["dense"] = {
        "sourceKeyCount": len(_key_tick_times(denseSource, "pos")),
        "targetKeyTimes": _all_key_times(denseTarget),
    }

    # (c) 서브프레임 키 소스 - 임시 포인트 우회를 남긴 이유의 표본
    _reset(0, 30)
    subFrameSource = rt.Point(name="p4_sub_src")
    _animate_sparse(subFrameSource, [0.0, 10.5, 20.25, 30.0])
    subFrameTarget = rt.Point(name="p4_sub_tgt")
    anim.match_anim_transform(subFrameTarget, subFrameSource, 0, 30)
    result["subFrame"] = {
        "sourceKeyTimes": _all_key_times(subFrameSource),
        "targetKeyTimes": _all_key_times(subFrameTarget),
    }

    # (d) 구간이 animationRange.start와 다른 경우 - 정리 블록이 발동하는 표본
    _reset(0, 60)
    offsetSource = rt.Point(name="p4_offset_src")
    _animate_sparse(offsetSource, [10.0, 25.0, 40.0])
    offsetTarget = rt.Point(name="p4_offset_tgt")
    anim.match_anim_transform(offsetTarget, offsetSource, 10, 40)
    result["offsetRange"] = {
        "animationRangeStart": int(rt.animationRange.start),
        "sourceKeyTimes": _all_key_times(offsetSource),
        "targetKeyTimes": _all_key_times(offsetTarget),
    }

    return result


_try("P4_current_match_key_times", _probe_current_match_key_times)


def _probe_current_collapse_key_times() -> dict:
    """현행 collape_anim_transform의 결과 키 시점과 컨트롤러 클래스를 덤프한다."""
    _reset(0, 30)
    node = rt.Point(name="p4_collapse")
    _animate_dense(node, 0, 30)
    beforeTimes = _all_key_times(node)

    anim.collape_anim_transform(node, 0, 30)

    controllerClasses = str(rt.execute(
        "(\n"
        f"    local n = getAnimByHandle {_handle(node)}\n"
        "    ((classOf n.transform.controller) as string + \",\""
        " + (classOf n.pos.controller) as string + \",\""
        " + (classOf n.rotation.controller) as string + \",\""
        " + (classOf n.scale.controller) as string)\n"
        ")"
    ))
    return {
        "keyTimesBefore": beforeTimes,
        "keyTimesAfter": _all_key_times(node),
        "controllerClassesAfter": controllerClasses,
    }


_try("P4_current_collapse_key_times", _probe_current_collapse_key_times)


# ======================================================================
# P5: 단일 노드 baseline 계측
#
# 표본 3종으로 갈라 "무엇이 비용인지"를 분리한다.
#   A  조밀 소스 + **조밀 키를 이미 가진 대상**  -> 프레임별 키 삭제의 O(F²) 발현
#   A' 조밀 소스 + 무키 대상                    -> 삭제 비용을 뺀 값 (차분이 O(F²) 몫)
#   B  희소 소스 + 무키 대상                    -> AnimCopyTool 형태
#
# 표본마다 3회 반복해 노이즈 폭을 먼저 확정한다. 절감은 그 배수로만 주장한다.
# ======================================================================

REPEAT = 3
DENSE_END = 640
SPARSE_END = 200


def _measure_match(inLabel: str, inPrimeTarget: bool, inDense: bool) -> dict:
    """match_anim_transform 1회 호출을 REPEAT번 재서 표본 하나를 만든다.

    Args:
        inLabel: 표본 이름
        inPrimeTarget: True면 대상에 미리 조밀 키를 실어 둔다
        inDense: True면 소스를 매 프레임 키로, False면 희소 키로 만든다

    Returns:
        표본 계측 결과 dict
    """
    endFrame = DENSE_END if inDense else SPARSE_END
    samples = []
    targetKeyCounts = []
    for runIndex in range(REPEAT):
        _reset(0, endFrame)
        sourceNode = rt.Point(name=f"{inLabel}_src{runIndex}")
        if inDense:
            _animate_dense(sourceNode, 0, endFrame)
        else:
            step = max(1, endFrame // 9)
            _animate_sparse(
                sourceNode, [float(f) for f in range(0, endFrame + 1, step)]
            )

        targetNode = rt.Point(name=f"{inLabel}_tgt{runIndex}")
        if inPrimeTarget:
            _animate_dense(targetNode, 0, endFrame, inScale=-2.0)

        elapsed = _timed(
            anim.match_anim_transform, targetNode, sourceNode, 0, endFrame
        )
        samples.append(round(elapsed, 4))
        targetKeyCounts.append(len(_key_tick_times(targetNode, "pos")))

    return {
        "frames": endFrame + 1,
        "sourceDense": inDense,
        "targetPrimed": inPrimeTarget,
        "samplesSeconds": samples,
        "minSeconds": min(samples),
        "medianSeconds": sorted(samples)[len(samples) // 2],
        "targetKeyCounts": targetKeyCounts,
    }


def _probe_baseline_match() -> dict:
    """표본 3종의 현행 baseline을 잰다.

    실행 순서가 값을 바꾸므로(OS 파일 캐시·릭 워밍) 순서를 기록에 남긴다.
    """
    order = ["A_dense_primed", "Aprime_dense_empty", "B_sparse_empty"]
    result = {"executionOrder": order}
    result["A_dense_primed"] = _measure_match("A", True, True)
    result["Aprime_dense_empty"] = _measure_match("Ap", False, True)
    result["B_sparse_empty"] = _measure_match("B", False, False)
    return result


baselineMatch = _try("P5_baseline_match", _probe_baseline_match)
if baselineMatch is not None:
    findings["baseline"]["match_anim_transform"] = baselineMatch


def _probe_baseline_collapse() -> dict:
    """현행 collape_anim_transform의 baseline을 잰다."""
    samples = []
    for runIndex in range(REPEAT):
        _reset(0, DENSE_END)
        node = rt.Point(name=f"collapse_src{runIndex}")
        _animate_dense(node, 0, DENSE_END)
        samples.append(
            round(_timed(anim.collape_anim_transform, node, 0, DENSE_END), 4)
        )
    return {
        "frames": DENSE_END + 1,
        "samplesSeconds": samples,
        "minSeconds": min(samples),
        "medianSeconds": sorted(samples)[len(samples) // 2],
    }


baselineCollapse = _try("P5_baseline_collapse", _probe_baseline_collapse)
if baselineCollapse is not None:
    findings["baseline"]["collape_anim_transform"] = baselineCollapse


# ======================================================================
# 2차 프로브 - 1차 결과(P1)가 설계를 바꿨다
#
# `key.time as float`이 틱을 주고 `at time <숫자>`가 프레임을 읽으므로
# "float로 바꿔 정렬" 설계는 폐기했다. time 값을 그대로 두고 **이미 정렬된
# 세 배열을 3방향 병합**하는 쪽으로 간다. 그 병합이 성립하는지 여기서 잰다.
# ======================================================================

# Phase 1에 이식할 병합 블록의 프로토타입. 세 키 배열은 Max가 항상 시간 순으로
# 유지하므로(`max/pymxs_pitfalls_advanced.md`) 커서 3개로 O(키) 병합이 된다.
# `sort`도, float 변환도 쓰지 않는다.
_MERGE_PROTOTYPE = """(
    local ref = getAnimByHandle {refHandle}
    local tracks = #(
        ref.pos.controller.keys,
        ref.rotation.controller.keys,
        ref.scale.controller.keys
    )
    local cursors = #(1, 1, 1)
    for a = 1 to 3 do (
        while cursors[a] <= tracks[a].count \\
            and tracks[a][cursors[a]].time < {startFrame} do cursors[a] += 1
    )
    local merged = #()
    while true do (
        local best = undefined
        for a = 1 to 3 do (
            if cursors[a] <= tracks[a].count then (
                local candidate = tracks[a][cursors[a]].time
                if candidate <= {endFrame} \\
                    and (best == undefined or candidate < best) then best = candidate
            )
        )
        if best == undefined then exit
        append merged best
        for a = 1 to 3 do (
            if cursors[a] <= tracks[a].count \\
                and tracks[a][cursors[a]].time == best then cursors[a] += 1
        )
    )
    local out = ""
    for t in merged do out = out + ((t as float) as string) + ","
    out
)"""


def _animate_tracks_separately(
    inNode, inPosFrames: list, inRotFrames: list, inScaleFrames: list
) -> None:
    """트랙마다 **다른** 시점에 키를 심는다.

    세 배열을 이어 붙이면 전체가 정렬되지 않으므로, 병합·정렬 로직의 실제
    시험대가 된다. 트랙 키 시점이 모두 같은 픽스처는 아무것도 검증하지 못한다.
    """
    def _block(inTrackExpr: str, inFrames: list, inValueExpr: str) -> str:
        if not inFrames:
            return ""
        frameText = ",".join(str(float(frame)) for frame in inFrames)
        return (
            f"        for f in #({frameText}) do (\n"
            "            at time f (\n"
            f"                with animate on node.{inTrackExpr} = {inValueExpr}\n"
            "            )\n"
            "        )\n"
        )

    script = (
        "(\n"
        f"    local node = getAnimByHandle {_handle(inNode)}\n"
        "    with undo off (\n"
        + _block("position", inPosFrames, "[f * 2.0, f * -1.5, f * 0.7]")
        + _block("rotation", inRotFrames, "eulerAngles 0 0 (f * 3.0)")
        + _block("scale", inScaleFrames, "[1.0 + f * 0.01, 1.0, 1.0]")
        + "    )\n"
        "    ok\n"
        ")"
    )
    rt.execute(script)


def _probe_sort_on_time_values() -> dict:
    """이어 붙여 **정렬되지 않은** time 값 배열에 sort가 먹는지 확인한다.

    1차 P1은 이미 정렬된 배열을 넣어 sort를 사실상 시험하지 않았다.
    """
    _reset(0, 40)
    node = rt.Point(name="p6_src")
    _animate_tracks_separately(node, [0, 12, 24], [4, 16, 28], [8, 20, 32])

    script = (
        "(\n"
        f"    local n = getAnimByHandle {_handle(node)}\n"
        "    local merged = #()\n"
        "    for k in n.pos.controller.keys do append merged k.time\n"
        "    for k in n.rotation.controller.keys do append merged k.time\n"
        "    for k in n.scale.controller.keys do append merged k.time\n"
        "    local before = merged as string\n"
        "    sort merged\n"
        "    local monotonic = true\n"
        "    for i = 2 to merged.count do (\n"
        "        if merged[i] < merged[i - 1] then monotonic = false\n"
        "    )\n"
        "    (before + \"|\" + (merged as string) + \"|\" + (monotonic as string))\n"
        ")"
    )
    parts = str(rt.execute(script)).split("|")
    return {
        "beforeSort": parts[0] if len(parts) > 0 else None,
        "afterSort": parts[1] if len(parts) > 1 else None,
        "monotonicAfterSort": parts[2] if len(parts) > 2 else None,
        "trackKeyTicks": _all_key_times(node),
    }


_try("P6_sort_on_time_values", _probe_sort_on_time_values)


def _probe_three_way_merge() -> dict:
    """3방향 병합 프로토타입의 결과를 Python이 계산한 합집합과 대조한다.

    표본 3종으로 갈라 "겹치는 경우 / 어긋나는 경우 / 서브프레임"을 모두 통과시킨다.
    """
    result = {}

    samples = {
        # 트랙마다 다른 시점 - 병합이 실제로 일할 표본
        "interleaved": {
            "range": (0, 40),
            "pos": [0, 12, 24],
            "rot": [4, 16, 28],
            "scale": [8, 20, 32],
        },
        # 전 트랙 동일 시점 - 중복 제거가 3배를 걷어내는 표본
        "coincident": {
            "range": (0, 20),
            "pos": [0, 5, 10, 15, 20],
            "rot": [0, 5, 10, 15, 20],
            "scale": [0, 5, 10, 15, 20],
        },
        # 서브프레임 + 구간 밖 키 - 필터와 정밀도를 함께 보는 표본
        "subFrameAndOutside": {
            "range": (10, 30),
            "pos": [0, 10.5, 18, 35],
            "rot": [5, 20.25, 30],
            "scale": [12, 30],
        },
    }

    for label, spec in samples.items():
        startFrame, endFrame = spec["range"]
        _reset(0, 60)
        node = rt.Point(name=f"p7_{label}")
        _animate_tracks_separately(node, spec["pos"], spec["rot"], spec["scale"])

        raw = rt.execute(
            _MERGE_PROTOTYPE.format(
                refHandle=_handle(node),
                startFrame=startFrame,
                endFrame=endFrame,
            )
        )
        mergedTicks = [
            float(token) for token in str(raw or "").split(",") if token
        ]

        trackTicks = _all_key_times(node)
        ticksPerFrame = int(rt.ticksPerFrame)
        lowerTick = startFrame * ticksPerFrame
        upperTick = endFrame * ticksPerFrame
        expectedTicks = sorted({
            tick
            for track in trackTicks.values()
            for tick in track
            if lowerTick <= tick <= upperTick
        })

        result[label] = {
            "range": [startFrame, endFrame],
            "ticksPerFrame": ticksPerFrame,
            "trackKeyTicks": trackTicks,
            "mergedTicks": mergedTicks,
            "expectedTicks": expectedTicks,
            "matchesExpected": mergedTicks == expectedTicks,
            "writeReduction": (
                sum(len(track) for track in trackTicks.values()),
                len(mergedTicks),
            ),
        }

    return result


_try("P7_three_way_merge", _probe_three_way_merge)


def _probe_range_start_key_location() -> dict:
    """animationRange.start가 0이 아닐 때 스퓨리어스 키가 어디에 생기는지 본다.

    현행 정리 블록은 ``animationRange.start``의 키를 지운다. 실제 생성 지점이
    프레임 0이면 그 블록은 구간이 0으로 시작하는 씬에서만 유효하다는 뜻이다.
    """
    _reset(5, 100)
    sourceNode = rt.Point(name="p8_src")
    _animate_dense(sourceNode, 10, 40)

    targetNode = rt.Point(name="p8_tgt")
    anim.bake_world_transforms(
        [sourceNode], [targetNode], 10, 40, inTargetStartFrame=10
    )

    ticksPerFrame = int(rt.ticksPerFrame)
    targetTicks = _all_key_times(targetNode)
    return {
        "animationRange": [
            int(rt.animationRange.start), int(rt.animationRange.end)
        ],
        "ticksPerFrame": ticksPerFrame,
        "targetKeyTicks": targetTicks,
        "hasKeyAtFrameZero": 0.0 in targetTicks["pos"],
        "hasKeyAtRangeStart": float(5 * ticksPerFrame) in targetTicks["pos"],
        "firstThreeTicks": targetTicks["pos"][:3],
    }


_try("P8_range_start_key_location", _probe_range_start_key_location)


# ======================================================================
# 산출물 기록
# ======================================================================
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps(findings, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    reporter.assert_test(
        JSON_PATH.exists(), f"프로브 산출물 기록: {JSON_PATH.name}"
    )
except Exception as e:
    reporter.error("프로브 산출물 기록", f"{e}\n{traceback.format_exc()}")


reporter.summary()
reporter.close()
