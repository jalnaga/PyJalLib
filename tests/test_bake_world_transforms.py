#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""``bake_world_transforms`` 순수부 검증 (Type A).

MAXScript 소스 조립과 청크 분할은 씬 접근이 필요 없는 문자열·산술 문제다.
떼어 놓았으므로 경우의 수를 콘솔에서 전수 검증할 수 있다
(`max/max_test_pattern.md` - 판정 규칙은 pymxs 밖 순수 함수로).

여기서 잡으려는 결함은 헤드리스 왕복 테스트로는 **비싸게만** 잡히는 것들이다:
청크 경계 off-by-one, 재기준 오프셋 부호, 대상 키 삭제 구간의 끝 프레임.

``conftest.py``가 세션 단위로 ``pymxs`` mock을 등록하므로
``pyjallib.max.anim``을 콘솔에서 import할 수 있다.
"""

from unittest.mock import MagicMock, patch

import pytest

from pyjallib.max import anim as animModule
from pyjallib.max.anim import (
    Anim,
    build_bake_chunk_script,
    build_bake_frame_chunks,
    build_clear_target_keys_script,
    build_handle_array_text,
)


class _FakeNode:
    """핸들만 갖는 노드 대역."""

    def __init__(self, inHandle: int):
        self.handle = inHandle


def _make_fake_rt() -> MagicMock:
    """``getHandleByAnim``이 정수를 돌려주는 rt 대역을 만든다."""
    fakeRt = MagicMock()
    fakeRt.getHandleByAnim.side_effect = lambda node: node.handle
    return fakeRt


# ======================================================================
# 청크 분할
# ======================================================================

def test_chunks_cover_range_exactly_when_divisible():
    """구간이 청크 크기로 정확히 나누어떨어지는 경우."""
    chunks = build_bake_frame_chunks(0, 99, 50)

    assert chunks == [(0, 49), (50, 99)]


def test_chunks_keep_remainder_as_last_chunk():
    """나머지가 남으면 마지막 청크가 짧아진다."""
    chunks = build_bake_frame_chunks(0, 200, 50)

    assert chunks == [(0, 49), (50, 99), (100, 149), (150, 199), (200, 200)]


def test_chunks_are_contiguous_and_cover_every_frame():
    """청크가 빈틈·중복 없이 구간 전체를 덮는다.

    베이크는 프레임 하나가 비어도 그 프레임만 조용히 무키로 남는다.
    경계 산식은 예시가 아니라 **커버리지 불변식**으로 단정한다.
    """
    startFrame, endFrame = -7, 133
    chunks = build_bake_frame_chunks(startFrame, endFrame, 16)

    coveredFrames = [
        frame
        for chunkStart, chunkEnd in chunks
        for frame in range(chunkStart, chunkEnd + 1)
    ]

    assert coveredFrames == list(range(startFrame, endFrame + 1))


def test_chunks_handle_single_frame_range():
    """시작과 끝이 같은 1프레임 구간."""
    assert build_bake_frame_chunks(12, 12, 50) == [(12, 12)]


def test_chunks_handle_negative_start_frame():
    """음수 시작 구간도 정상 분할된다 (음수 시작 소스 회귀)."""
    chunks = build_bake_frame_chunks(-10, 30, 20)

    assert chunks[0] == (-10, 9)
    assert chunks[-1][1] == 30


def test_chunk_size_larger_than_range_yields_one_chunk():
    """청크 크기가 구간보다 크면 청크는 하나다."""
    assert build_bake_frame_chunks(0, 10, 1000) == [(0, 10)]


def test_chunk_size_one_yields_one_chunk_per_frame():
    """청크 크기 1이면 프레임마다 한 청크."""
    assert build_bake_frame_chunks(5, 8, 1) == [(5, 5), (6, 6), (7, 7), (8, 8)]


def test_inverted_range_raises_value_error():
    """구간이 뒤집히면 즉시 거부한다.

    그대로 두면 청크가 0개가 되어 **대상이 조용히 무키로 남는다**.
    """
    with pytest.raises(ValueError, match="뒤집"):
        build_bake_frame_chunks(50, 10, 50)


def test_non_positive_chunk_size_raises_value_error():
    """청크 크기가 1 미만이면 즉시 거부한다 (무한 루프 방지)."""
    with pytest.raises(ValueError, match="청크 크기"):
        build_bake_frame_chunks(0, 100, 0)
    with pytest.raises(ValueError, match="청크 크기"):
        build_bake_frame_chunks(0, 100, -5)


# ======================================================================
# 핸들 배열 텍스트
# ======================================================================

def test_handle_array_text_preserves_order():
    """핸들 순서가 그대로 보존된다.

    소스와 대상은 인덱스로 1:1 대응하므로 순서가 뒤집히면 **엉뚱한 노드에**
    트랜스폼이 실린다. 정렬하지 않는다는 것 자체가 계약이다.
    """
    assert build_handle_array_text([30, 10, 20]) == "30,10,20"


def test_handle_array_text_accepts_float_like_handles():
    """pymxs가 돌려주는 실수형 핸들도 정수 텍스트가 된다."""
    assert build_handle_array_text([12.0, 34.0]) == "12,34"


def test_handle_array_text_on_empty_list():
    """빈 목록은 빈 문자열 (MAXScript ``#()``이 된다)."""
    assert build_handle_array_text([]) == ""


# ======================================================================
# 베이크 청크 스크립트 조립
# ======================================================================

def test_chunk_script_embeds_handles_and_frames():
    """핸들 배열과 프레임 경계가 스크립트에 그대로 박힌다."""
    script = build_bake_chunk_script([1, 2], [7, 8], 10, 19, 0)

    assert "#(1,2)" in script
    assert "#(7,8)" in script
    assert "for k = 10 to 19 do" in script
    assert "at time (0 + j - 1)" in script


def test_chunk_script_offsets_target_start_per_chunk():
    """두 번째 청크의 대상 시작 프레임이 청크만큼 밀린다.

    이 오프셋이 틀리면 뒤 청크가 앞 청크를 덮어써 **구간 뒷부분이 통째로
    사라진다** - 조용히 잘못된 결과가 나가는 형태다.
    """
    script = build_bake_chunk_script([1], [2], 60, 69, 50)

    assert "for k = 60 to 69 do" in script
    assert "at time (50 + j - 1)" in script


def test_chunk_script_suppresses_undo_and_enables_animate():
    """Undo 기록을 끊고 애니메이션 모드로 기록한다.

    ``with animate on``이 빠지면 키가 아니라 정적 값만 바뀌어 **베이크가
    통째로 무효**가 된다.
    """
    script = build_bake_chunk_script([1], [2], 0, 10, 0)

    assert "with undo off" in script
    assert "with animate on" in script


def test_chunk_script_snapshots_before_writing():
    """읽기를 ``copy``로 값 확보한 뒤에 기록한다.

    읽는 시점과 쓰는 시점이 다르므로 라이브 참조를 들고 있으면 기록 시점의
    값으로 평가될 수 있다.
    """
    script = build_bake_chunk_script([1], [2], 0, 10, 0)

    assert "copy srcs[i].transform" in script
    assert script.index("copy srcs[i].transform") < script.index("with undo off")


def test_chunk_script_guards_unresolved_handles():
    """핸들이 해석되지 않으면 조용히 넘어가지 않고 throw 한다."""
    script = build_bake_chunk_script([1], [2], 0, 10, 0)

    assert "findItem srcs undefined" in script
    assert "findItem tgts undefined" in script
    assert "throw" in script


# ======================================================================
# 대상 키 삭제 스크립트 조립
# ======================================================================

def test_clear_script_uses_single_interval_selection():
    """구간 선택 1회로 지운다 (프레임 루프가 없어야 한다).

    프레임마다 ``selectKeys``를 부르던 것이 O(프레임²)의 원인이었다.
    루프가 다시 들어오면 이 테스트가 실패한다.
    """
    script = build_clear_target_keys_script([1, 2], 0, 640)

    assert "selectKeys ctrl (interval 0 640)" in script
    assert "for k =" not in script


def test_clear_script_covers_target_time_axis():
    """삭제 구간이 **대상** 시간축 기준이다.

    소스가 (10, 50)이고 0기준으로 실으면 지워야 할 대상 구간은 (0, 40)이다.
    소스 구간을 그대로 쓰면 실을 자리의 키가 남아 새 키와 섞인다.
    """
    script = build_clear_target_keys_script([9], 0, 40)

    assert "interval 0 40" in script


def test_clear_script_deselects_before_and_after():
    """선택 상태를 남기지 않는다 (다음 노드의 삭제에 새어 들어간다)."""
    script = build_clear_target_keys_script([1], 0, 10)

    assert script.count("deselectKeys ctrl") == 2


# ======================================================================
# bake_world_transforms 호출 경로 (rt 대역)
# ======================================================================

def test_bake_rejects_node_count_mismatch_before_touching_scene():
    """개수 불일치는 씬을 건드리기 전에 거부한다.

    한 번이라도 실행되고 나서 실패하면 씬이 반쯤 베이크된 상태로 남는다.
    """
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        with pytest.raises(ValueError, match="노드 수가 다릅니다"):
            Anim().bake_world_transforms(
                [_FakeNode(1), _FakeNode(2)], [_FakeNode(3)], 0, 10
            )

    fakeRt.execute.assert_not_called()
    fakeRt.disableSceneRedraw.assert_not_called()


def test_bake_rejects_inverted_range_before_touching_scene():
    """구간 역전도 실행 전에 거부한다."""
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        with pytest.raises(ValueError, match="뒤집"):
            Anim().bake_world_transforms(
                [_FakeNode(1)], [_FakeNode(2)], 50, 10
            )

    fakeRt.execute.assert_not_called()


def test_bake_rejects_bad_chunk_size_before_touching_scene():
    """청크 크기 0은 실행 전에 거부한다."""
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        with pytest.raises(ValueError, match="청크 크기"):
            Anim().bake_world_transforms(
                [_FakeNode(1)], [_FakeNode(2)], 0, 10, inChunkSize=0
            )

    fakeRt.execute.assert_not_called()


def test_bake_on_empty_node_lists_is_a_no_op():
    """대상이 없으면 아무것도 실행하지 않는다."""
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        Anim().bake_world_transforms([], [], 0, 10)

    fakeRt.execute.assert_not_called()
    fakeRt.disableSceneRedraw.assert_not_called()


def test_bake_issues_one_execute_per_chunk_and_restores_redraw():
    """청크마다 실행 1회, 뷰포트 갱신은 반드시 복원된다."""
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        Anim().bake_world_transforms(
            [_FakeNode(1), _FakeNode(2)],
            [_FakeNode(11), _FakeNode(12)],
            0,
            99,
            inChunkSize=50,
        )

    assert fakeRt.execute.call_count == 2
    fakeRt.disableSceneRedraw.assert_called_once()
    fakeRt.enableSceneRedraw.assert_called_once()

    firstScript = fakeRt.execute.call_args_list[0][0][0]
    secondScript = fakeRt.execute.call_args_list[1][0][0]
    assert "#(1,2)" in firstScript and "#(11,12)" in firstScript
    assert "for k = 0 to 49 do" in firstScript
    assert "for k = 50 to 99 do" in secondScript


def test_bake_restores_redraw_even_when_execute_raises():
    """실행이 터져도 ``enableSceneRedraw``는 복원된다.

    복원하지 않으면 3ds Max 뷰포트가 이후 내내 갱신되지 않는다.
    """
    fakeRt = _make_fake_rt()
    fakeRt.execute.side_effect = RuntimeError("MAXScript 실패")

    with patch.object(animModule, "rt", fakeRt):
        with pytest.raises(RuntimeError):
            Anim().bake_world_transforms(
                [_FakeNode(1)], [_FakeNode(2)], 0, 10
            )

    fakeRt.enableSceneRedraw.assert_called_once()


def test_bake_clears_target_keys_once_before_all_chunks():
    """대상 키 삭제는 **첫 청크 앞에서 딱 한 번**이다.

    청크마다 지우면 두 번째 청크가 첫 번째 청크의 결과를 지운다 - 구간
    앞부분이 통째로 사라지는 조용한 오류가 된다.
    """
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        Anim().bake_world_transforms(
            [_FakeNode(1)],
            [_FakeNode(2)],
            0,
            99,
            inChunkSize=50,
            inClearTargetKeys=True,
        )

    scripts = [call[0][0] for call in fakeRt.execute.call_args_list]
    assert len(scripts) == 3
    assert "selectKeys ctrl (interval 0 99)" in scripts[0]
    assert sum(1 for script in scripts if "selectKeys" in script) == 1


def test_bake_clear_range_follows_target_time_axis():
    """재기준이 걸리면 삭제 구간도 대상 시간축을 따른다."""
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        Anim().bake_world_transforms(
            [_FakeNode(1)],
            [_FakeNode(2)],
            10,
            50,
            inTargetStartFrame=0,
            inChunkSize=100,
            inClearTargetKeys=True,
        )

    clearScript = fakeRt.execute.call_args_list[0][0][0]
    assert "interval 0 40" in clearScript


def test_bake_skips_clear_when_not_requested():
    """저장 경로(신규 헬퍼)에서는 삭제 스크립트를 내지 않는다."""
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        Anim().bake_world_transforms(
            [_FakeNode(1)], [_FakeNode(2)], 0, 10, inClearTargetKeys=False
        )

    scripts = [call[0][0] for call in fakeRt.execute.call_args_list]
    assert all("selectKeys" not in script for script in scripts)


def test_bake_reports_progress_per_chunk():
    """청크마다 누적 프레임 수를 보고한다 (긴 베이크가 침묵하지 않게)."""
    reported = []
    fakeRt = _make_fake_rt()
    with patch.object(animModule, "rt", fakeRt):
        Anim().bake_world_transforms(
            [_FakeNode(1)],
            [_FakeNode(2)],
            0,
            120,
            inChunkSize=50,
            inProgressCallback=lambda done, total: reported.append((done, total)),
        )

    assert reported == [(50, 121), (100, 121), (121, 121)]
