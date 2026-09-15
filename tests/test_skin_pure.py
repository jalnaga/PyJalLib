# -*- coding: utf-8 -*-
"""Skin 가중치 이전 프리미티브의 순수 부분 Type A 회귀 가드.

``merge_vertex_weights``(모듈 함수)와 ``Skin.get_used_bone_handles``는 pymxs를 호출하지
않는다. 다대일 합산 규칙과 사용 본 판정 규칙을 3ds Max 없이 여기서 고정한다.
conftest가 pymxs를 mock하므로 ``pyjallib.max.skin`` import는 콘솔에서 성립한다.

본 ID는 1-based 정수, 노드 핸들은 의미를 알기 쉬운 번호대(1000번대)를 쓴다.
"""

import pytest

from pyjallib.max.skin import (
    Skin,
    diff_weights_by_handle,
    expected_weights_by_handle,
    merge_vertex_weights,
)


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


# --------------------------------------------------------------------------- #
#  expected_weights_by_handle / diff_weights_by_handle
#
#  `addBone`(빈 슬롯 재사용)과 `removeBone`(제거 후 압축)이 양쪽에서 본 ID를 밀기
#  때문에, 이전 전후 대조는 반드시 **노드 핸들** 기준이어야 한다. 그 규칙을 여기서
#  고정한다 - 3ds Max 없이 콘솔에서 돌아간다.
# --------------------------------------------------------------------------- #


def test_expected_many_to_one_merges_on_target_handle():
    """다대일 - 여러 원본 핸들이 한 대상 핸들로 합산된다."""
    snapshot = {1: {1001: 0.5, 1002: 0.3, 1003: 0.2}}

    assert expected_weights_by_handle(snapshot, {1002: 1001, 1003: 1001}) == {
        1: {1001: pytest.approx(1.0)}
    }


def test_expected_target_handle_absent_creates_entry():
    """대상 핸들이 버텍스에 없던 경우 새 항목이 생긴다."""
    snapshot = {1: {1005: 0.4, 1002: 0.35, 1003: 0.25}}
    result = expected_weights_by_handle(snapshot, {1002: 1009, 1003: 1009})

    assert set(result[1]) == {1005, 1009}
    assert result[1][1009] == pytest.approx(0.6)


def test_expected_untouched_vertex_is_unchanged():
    """remap에 걸리지 않는 핸들만 있으면 스냅샷 그대로다."""
    snapshot = {7: {1001: 0.6, 1002: 0.4}}

    assert expected_weights_by_handle(snapshot, {1099: 1001}) == {7: {1001: 0.6, 1002: 0.4}}


def test_expected_does_not_mutate_snapshot():
    """입력 스냅샷을 건드리지 않는다."""
    snapshot = {1: {1001: 0.5, 1002: 0.5}}
    expected_weights_by_handle(snapshot, {1002: 1001})

    assert snapshot == {1: {1001: 0.5, 1002: 0.5}}


def test_diff_returns_empty_when_identical():
    """일치하면 빈 리스트."""
    expected = {1: {1001: 1.0}, 2: {1002: 0.5, 1003: 0.5}}

    assert diff_weights_by_handle(expected, dict(expected)) == []


def test_diff_absorbs_renormalization_ulp():
    """`ReplaceVertexWeights` 재정규화 ULP(약 4.5e-8)는 기본 허용오차 1e-6에 흡수된다."""
    expected = {1: {1001: 1.0}}
    actual = {1: {1001: 1.0 + 4.5e-8}}

    assert diff_weights_by_handle(expected, actual) == []


def test_diff_flags_just_over_tolerance():
    """허용오차를 넘으면 (버텍스, 핸들, 기대, 실제)로 잡는다."""
    expected = {1: {1001: 1.0}}
    actual = {1: {1001: 1.0 + 2e-6}}
    deviations = diff_weights_by_handle(expected, actual)

    assert len(deviations) == 1
    vertIndex, handle, expectedWeight, actualWeight = deviations[0]
    assert (vertIndex, handle) == (1, 1001)
    assert expectedWeight == pytest.approx(1.0)
    assert actualWeight == pytest.approx(1.0 + 2e-6)


def test_diff_missing_bone_counts_as_zero():
    """한쪽에만 있는 본은 다른 쪽을 가중치 0으로 본다 - 결함의 전형적 지문이다."""
    expected = {3: {1001: 1.0}}
    actual = {3: {1001: 0.7, 1004: 0.3}}
    deviations = diff_weights_by_handle(expected, actual)

    assert sorted((v, h) for v, h, _, _ in deviations) == [(3, 1001), (3, 1004)]


def test_diff_vertex_set_mismatch_is_a_deviation():
    """버텍스 집합이 다르면 없는 쪽을 빈 dict로 보고 그 차이도 편차로 잡는다."""
    deviations = diff_weights_by_handle({1: {1001: 1.0}}, {})

    assert deviations == [(1, 1001, 1.0, 0.0)]


def test_diff_zero_weight_bone_on_both_sides_is_not_a_deviation():
    """양쪽 모두 0이면 편차가 아니다(둘 다 0인 경로를 오검출하지 않는다)."""
    assert diff_weights_by_handle({1: {1001: 0.0}}, {1: {}}) == []


def test_diff_custom_tolerance():
    """허용오차는 인자로 조절된다."""
    expected = {1: {1001: 1.0}}
    actual = {1: {1001: 1.001}}

    assert diff_weights_by_handle(expected, actual) != []
    assert diff_weights_by_handle(expected, actual, inTolerance=1e-2) == []
