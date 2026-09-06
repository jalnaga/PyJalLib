# -*- coding: utf-8 -*-
"""Skin 가중치 이전 프리미티브의 순수 부분 Type A 회귀 가드.

``merge_vertex_weights``(모듈 함수)와 ``Skin.get_used_bone_handles``는 pymxs를 호출하지
않는다. 다대일 합산 규칙과 사용 본 판정 규칙을 3ds Max 없이 여기서 고정한다.
conftest가 pymxs를 mock하므로 ``pyjallib.max.skin`` import는 콘솔에서 성립한다.

본 ID는 1-based 정수, 노드 핸들은 의미를 알기 쉬운 번호대(1000번대)를 쓴다.
"""

import pytest

from pyjallib.max.skin import Skin, merge_vertex_weights


# --------------------------------------------------------------------------- #
#  merge_vertex_weights
# --------------------------------------------------------------------------- #


def test_merge_many_to_one_target_present():
    """다대일(2본→1본) 합산 - 대상 본이 버텍스에 이미 있으면 그 항목에 더한다."""
    entries = [(1, 0.5), (2, 0.3), (3, 0.2)]
    ids, weights, touched = merge_vertex_weights(entries, {2: 1, 3: 1})

    assert touched is True
    assert ids == [1]
    assert weights == pytest.approx([1.0])


def test_merge_many_to_one_target_absent():
    """대상 본이 버텍스에 없으면 첫 remap 항목 위치에 새 항목이 생긴다."""
    entries = [(5, 0.4), (2, 0.35), (3, 0.25)]
    ids, weights, touched = merge_vertex_weights(entries, {2: 9, 3: 9})

    assert touched is True
    assert ids == [5, 9]
    assert weights == pytest.approx([0.4, 0.6])


def test_merge_preserves_first_appearance_order():
    """결과 순서는 remap 적용 후 ID의 첫 등장 순이다."""
    entries = [(4, 0.1), (1, 0.2), (7, 0.3), (1, 0.4)]
    ids, weights, touched = merge_vertex_weights(entries, {7: 4})

    assert touched is True
    assert ids == [4, 1]
    assert weights == pytest.approx([0.4, 0.6])


def test_merge_untouched_vertex_returns_false_and_keeps_entries():
    """remap 대상이 없는 버텍스는 touched False, 항목은 그대로."""
    entries = [(1, 0.7), (2, 0.3)]
    ids, weights, touched = merge_vertex_weights(entries, {9: 1})

    assert touched is False
    assert ids == [1, 2]
    assert weights == pytest.approx([0.7, 0.3])


def test_merge_empty_entries():
    """빈 항목은 빈 결과 + touched False."""
    ids, weights, touched = merge_vertex_weights([], {1: 2})

    assert ids == []
    assert weights == []
    assert touched is False


def test_merge_zero_weight_remapped_entry_still_touches():
    """가중치 0인 원본 항목도 remap되며(touched True) 대상에 0을 더한다."""
    entries = [(1, 1.0), (2, 0.0)]
    ids, weights, touched = merge_vertex_weights(entries, {2: 1})

    assert touched is True
    assert ids == [1]
    assert weights == pytest.approx([1.0])


def test_merge_missing_target_raises():
    """remap 대상이 None이면 ValueError - 이전 대상이 없는 본을 조용히 넘기지 않는다."""
    with pytest.raises(ValueError):
        merge_vertex_weights([(1, 0.5), (2, 0.5)], {2: None})


def test_merge_does_not_mutate_inputs():
    """입력 항목과 remap dict를 바꾸지 않는다."""
    entries = [(1, 0.5), (2, 0.5)]
    remap = {2: 1}
    merge_vertex_weights(entries, remap)

    assert entries == [(1, 0.5), (2, 0.5)]
    assert remap == {2: 1}


# --------------------------------------------------------------------------- #
#  Skin.get_used_bone_handles
# --------------------------------------------------------------------------- #


def _table(*inRows):
    """``(boneId, handle)`` 행으로 대조표를 만든다."""
    return {boneId: {"name": f"bone{boneId}", "handle": handle, "byName": False} for boneId, handle in inRows}


def test_used_handles_basic():
    """가중치 > 0인 본의 핸들만 모인다."""
    table = _table((1, 1001), (2, 1002), (3, 1003))
    weights = {1: [(1, 0.5), (2, 0.5)], 2: [(2, 1.0)]}

    assert Skin().get_used_bone_handles(table, weights) == {1001, 1002}


def test_used_handles_excludes_zero_weight():
    """가중치 0인 항목만 가진 본은 사용 본이 아니다."""
    table = _table((1, 1001), (2, 1002))
    weights = {1: [(1, 1.0), (2, 0.0)]}

    assert Skin().get_used_bone_handles(table, weights) == {1001}


def test_used_handles_excludes_none_handle():
    """핸들이 None인 본(노드를 못 찾은 본)은 결과에서 제외한다."""
    table = _table((1, 1001), (2, None))
    weights = {1: [(1, 0.5), (2, 0.5)]}

    assert Skin().get_used_bone_handles(table, weights) == {1001}


def test_used_handles_ignores_unknown_bone_id():
    """대조표에 없는 본 ID는 무시한다(예외 없이)."""
    table = _table((1, 1001))
    weights = {1: [(1, 0.5), (99, 0.5)]}

    assert Skin().get_used_bone_handles(table, weights) == {1001}


def test_used_handles_empty_weights():
    """가중치가 없으면 빈 집합."""
    assert Skin().get_used_bone_handles(_table((1, 1001)), {}) == set()
