#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`build_match_write_script` 순수부 검증 (Type A).

`match_anim_transform`의 새 경로에서 씬 접근이 필요 없는 부분은 **MAXScript 소스
조립** 하나다. 떼어 놓았으므로 콘솔에서 전수 검증할 수 있다
(`max/max_test_pattern.md` - 판정 규칙은 pymxs 밖 순수 함수로).

여기서 잡으려는 결함은 헤드리스 왕복으로는 **비싸게만** 잡히는 것들이다.

- 키 시점 출처와 값 출처를 **뒤바꿔** 넘기는 실수. 값이 그럴듯하게 나와서
  스냅샷 대조로는 늦게 드러난다
- 구간 경계 비교의 부등호 방향 (`<` vs `<=`)
- **틱/프레임 혼동의 재유입.** `key.time as float`은 틱을 주고 `at time <숫자>`는
  프레임을 읽는다(2026-08-11 실측). 조립문에 `as float`가 다시 들어오면 시간축이
  ticksPerFrame배로 늘어나므로 **부재를 단정**한다
- 세 트랙 중 하나를 빠뜨리는 실수

``conftest.py``가 세션 단위로 ``pymxs`` mock을 등록하므로
``pyjallib.max.anim``을 콘솔에서 import할 수 있다.
"""

import pytest

from pyjallib.max.anim import (
    build_match_write_script,
    build_prs_controller_swap_script,
)


def _script(
    inKeyTimeSourceHandle: int = 11,
    inValueSourceHandle: int = 22,
    inTargetHandle: int = 33,
    inStartFrame: int = 10,
    inEndFrame: int = 40,
) -> str:
    """기본 인자로 조립문을 만든다. 핸들은 서로 다른 값으로 둬 혼동을 드러낸다."""
    return build_match_write_script(
        inKeyTimeSourceHandle,
        inValueSourceHandle,
        inTargetHandle,
        inStartFrame,
        inEndFrame,
    )


# ======================================================================
# 노드 역할 배정 - 뒤바뀜을 직접 단정한다
# ======================================================================

def test_handles_are_bound_to_their_own_roles():
    """세 핸들이 각자의 역할 변수에 묶인다."""
    script = _script(11, 22, 33, 10, 40)

    assert "local keySrc = getAnimByHandle 11" in script
    assert "local valSrc = getAnimByHandle 22" in script
    assert "local tgt = getAnimByHandle 33" in script


def test_key_times_come_from_key_source_and_values_from_value_source():
    """키 시점은 원본에서, 기록 값은 임시 포인트에서 온다.

    이 둘이 바뀌면 임시 포인트(정수 프레임 전량 키)의 키 시점을 쓰게 되어
    희소 소스에서도 매 프레임 키가 생긴다 - 출력 계약이 깨진다.
    """
    script = _script()

    assert (
        "local tracks = #(keySrc.pos.controller.keys, "
        "keySrc.rotation.controller.keys, keySrc.scale.controller.keys)"
    ) in script
    assert "tgt.transform = valSrc.transform" in script
    # 반대 방향은 존재해서는 안 된다
    assert "valSrc.transform = tgt.transform" not in script
    assert "keySrc.transform" not in script


def test_all_three_tracks_are_collected():
    """pos/rotation/scale 세 트랙을 모두 수집한다."""
    script = _script()

    for track in ("pos", "rotation", "scale"):
        assert f"keySrc.{track}.controller.keys" in script


def test_handles_are_coerced_to_int():
    """float 핸들이 들어와도 정수 리터럴로 조립된다.

    ``getHandleByAnim``은 pymxs에서 실수로 넘어올 수 있고, MAXScript에
    ``11.0``이 박히면 ``getAnimByHandle``이 실패한다.
    """
    script = build_match_write_script(11.0, 22.0, 33.0, 0, 5)

    assert "getAnimByHandle 11" in script
    assert "getAnimByHandle 22" in script
    assert "getAnimByHandle 33" in script
    assert "11.0" not in script


# ======================================================================
# 구간 경계
# ======================================================================

def test_range_bounds_use_the_given_frames():
    """구간 비교와 강제 기록에 주어진 프레임이 그대로 박힌다."""
    script = _script(inStartFrame=10, inEndFrame=40)

    assert ".time < 10 do cursors[a] += 1" in script
    assert "candidate <= 40 and" in script
    assert "times[1] != 10 then insertItem 10 times 1" in script
    assert "times[times.count] != 40 then append times 40" in script


def test_start_and_end_are_written_even_without_keys():
    """키가 없어도 시작·끝은 기록한다 (구 동작 보존).

    구 코드는 키 배열 순회 **전에** ``at time S`` / ``at time E``를 무조건
    기록했다. 그 계약을 앞뒤 삽입으로 옮겼다.
    """
    script = _script(inStartFrame=7, inEndFrame=7)

    assert "times.count == 0 or times[1] != 7 then insertItem 7 times 1" in script
    assert "times[times.count] != 7 then append times 7" in script


def test_negative_and_zero_frames_are_assembled_verbatim():
    """음수·0 프레임 구간도 그대로 조립된다."""
    script = _script(inStartFrame=-12, inEndFrame=0)

    assert ".time < -12 do cursors[a] += 1" in script
    assert "candidate <= 0 and" in script
    assert "insertItem -12 times 1" in script
    assert "append times 0" in script


def test_lower_bound_skips_strictly_before_start():
    """구간 시작 **이전** 키만 건너뛴다 (시작 시점의 키는 남긴다).

    ``<=``로 새면 시작 프레임의 키가 병합에서 탈락하고, 강제 삽입 때문에
    값은 맞지만 탄젠트 이웃이 달라진다.
    """
    script = _script(inStartFrame=10, inEndFrame=40)

    assert ".time < 10 do" in script
    assert ".time <= 10 do" not in script


# ======================================================================
# 회귀 가드 - 폐기한 설계가 되돌아오지 못하게
# ======================================================================

def test_script_never_converts_time_to_float():
    """``as float``를 쓰지 않는다.

    ``key.time as float``은 프레임이 아니라 **틱**을 돌려주고
    ``at time <숫자>``는 숫자를 **프레임**으로 읽는다. 두 변환이 서로 역이
    아니므로 float를 거치면 시간축이 ticksPerFrame배로 늘어난다.
    """
    script = _script()

    assert "as float" not in script


def test_script_does_not_sort():
    """``sort``를 쓰지 않는다.

    세 키 배열이 이미 시간 순이므로 커서 병합으로 O(키)에 끝난다.
    ``sort``는 동작하지만(2026-08-11 실측) 불필요한 비용이다.
    """
    script = _script()

    assert "sort " not in script


def test_write_loop_is_wrapped_in_undo_off():
    """기록 루프가 ``undo off`` 안에 있다.

    순서까지 단정한다 - ``undo off``가 루프 **뒤에** 오면 문법은 통과하지만
    Undo 억제가 걸리지 않는다.
    """
    script = _script()

    undoIndex = script.index("with undo off")
    writeIndex = script.index("tgt.transform = valSrc.transform")

    assert undoIndex < writeIndex


def test_merge_advances_every_cursor_that_matches_the_chosen_time():
    """선택된 시점과 같은 커서는 **모두** 전진한다.

    하나만 전진시키면 같은 시점이 트랙 수만큼 중복되어 3중 기록이 되살아난다.
    """
    script = _script()

    assert (
        "if cursors[a] <= tracks[a].count and tracks[a][cursors[a]].time == best "
        "then cursors[a] += 1"
    ) in script


def test_handle_resolution_failure_raises_in_maxscript():
    """핸들 해석 실패를 조용히 넘기지 않는다.

    그냥 두면 대상이 무키로 남아 하류에서 무증상 실패한다.
    """
    script = _script()

    assert "if keySrc == undefined or valSrc == undefined or tgt == undefined then" in script
    assert "throw" in script


# ======================================================================
# 기대값 대조 - 조립문 전체를 한 번 못 박는다
#
# 부분 문자열 단정만 두면 구·신이 함께 틀렸을 때 초록이 된다
# (`testing/debug_process.md` 21). 전문 대조를 하나 둬서 의도하지 않은
# 구조 변경이 반드시 실패로 드러나게 한다.
# ======================================================================

EXPECTED_SCRIPT = """(
    local keySrc = getAnimByHandle 11
    local valSrc = getAnimByHandle 22
    local tgt = getAnimByHandle 33
    if keySrc == undefined or valSrc == undefined or tgt == undefined then (
        throw "match_anim_transform: 노드 핸들 해석에 실패했습니다"
    )
    local tracks = #(keySrc.pos.controller.keys, keySrc.rotation.controller.keys, keySrc.scale.controller.keys)
    local cursors = #(1, 1, 1)
    for a = 1 to tracks.count do (
        while cursors[a] <= tracks[a].count and tracks[a][cursors[a]].time < 10 do cursors[a] += 1
    )
    local times = #()
    while true do (
        local best = undefined
        for a = 1 to tracks.count do (
            if cursors[a] <= tracks[a].count then (
                local candidate = tracks[a][cursors[a]].time
                if candidate <= 40 and (best == undefined or candidate < best) then best = candidate
            )
        )
        if best == undefined then exit
        append times best
        for a = 1 to tracks.count do (
            if cursors[a] <= tracks[a].count and tracks[a][cursors[a]].time == best then cursors[a] += 1
        )
    )
    if times.count == 0 or times[1] != 10 then insertItem 10 times 1
    if times[times.count] != 40 then append times 40
    with undo off (
        for t in times do (
            at time t ( with animate on tgt.transform = valSrc.transform )
        )
    )
    ok
)"""


def test_assembled_script_matches_expected_verbatim():
    """조립문 전문이 기대값과 한 글자도 다르지 않다."""
    assert _script(11, 22, 33, 10, 40) == EXPECTED_SCRIPT


@pytest.mark.parametrize(
    "startFrame, endFrame",
    [(0, 0), (0, 1), (-5, 5), (100, 640)],
)
def test_assembly_is_total_over_valid_ranges(startFrame: int, endFrame: int):
    """유효 구간이면 조립이 예외 없이 끝나고 두 리터럴이 모두 들어간다."""
    script = build_match_write_script(1, 2, 3, startFrame, endFrame)

    assert f"insertItem {startFrame} times 1" in script
    assert f"append times {endFrame}" in script


# ======================================================================
# `build_prs_controller_swap_script` - collape_anim_transform의 핵심 단계
# ======================================================================

EXPECTED_SWAP_SCRIPT = """(
    local tgt = getAnimByHandle 77
    if tgt == undefined then (
        throw "collape_anim_transform: 노드 핸들 해석에 실패했습니다"
    )
    tgt.transform.controller = transform_script()
    tgt.transform.controller = prs()
    ok
)"""


def test_controller_swap_is_two_stage_in_order():
    """``transform_script()`` -> ``prs()`` 2단 교체 순서를 지킨다.

    한 단계로 줄이면 기존 PRS에 재대입이 되어 서브컨트롤러가 남을 수 있다.
    "정리"라는 이름으로 한 줄이 사라지는 것을 이 단정이 막는다.
    """
    script = build_prs_controller_swap_script(77)

    scriptIndex = script.index("transform.controller = transform_script()")
    prsIndex = script.index("transform.controller = prs()")

    assert scriptIndex < prsIndex


def test_controller_swap_matches_expected_verbatim():
    """컨트롤러 교체 조립문 전문이 기대값과 일치한다."""
    assert build_prs_controller_swap_script(77) == EXPECTED_SWAP_SCRIPT


def test_controller_swap_coerces_handle_to_int():
    """float 핸들도 정수 리터럴로 조립된다."""
    script = build_prs_controller_swap_script(77.0)

    assert "getAnimByHandle 77" in script
    assert "77.0" not in script


def test_controller_swap_raises_on_handle_failure():
    """핸들 해석 실패를 조용히 넘기지 않는다.

    그냥 두면 컨트롤러가 교체되지 않은 채 다음 베이크가 기존 스택 위에
    키를 얹어 Constraint 결과와 합산된다.
    """
    script = build_prs_controller_swap_script(77)

    assert "if tgt == undefined then" in script
    assert "throw" in script
