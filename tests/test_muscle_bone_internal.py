# -*- coding: utf-8 -*-
"""근육 본 모듈의 순수 계산 내부 단위 테스트 (Type A).

`pyjallib.max.rig.muscleBone`의 pymxs 없는 함수만 본다 - X축 비틀림(XYX 합)과 스케일 식.
기대값은 행렬을 직접 곱해 만든 회전에서 끌어낸다(구현 함수를 기대값 계산에 쓰지 않는다).

pymxs는 `tests/conftest.py`가 세션 전역에 mock으로 등록한다.
"""

import math
import random

import pytest

from pyjallib.max.rig import muscleBone as mb


def _rx(inDeg):
    """Max 행 벡터 규약의 X축 오른손 회전 행렬(rotateXMatrix와 같은 행)."""
    c, s = math.cos(math.radians(inDeg)), math.sin(math.radians(inDeg))
    return [[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]]


def _ry(inDeg):
    """Max 행 벡터 규약의 Y축 오른손 회전 행렬."""
    c, s = math.cos(math.radians(inDeg)), math.sin(math.radians(inDeg))
    return [[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]]


def _rz(inDeg):
    """Max 행 벡터 규약의 Z축 오른손 회전 행렬."""
    c, s = math.cos(math.radians(inDeg)), math.sin(math.radians(inDeg))
    return [[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _twist(inMatrix):
    return mb.twist_sum_degrees(*inMatrix)


def _angle_diff(a, b):
    return abs(mb.wrap_degrees(a - b))


@pytest.mark.parametrize("alpha, beta, gamma", [(10.0, 30.0, 25.0), (-70.0, 80.0, 40.0), (5.0, -45.0, -15.0)])
def test_twist_is_sum_of_outer_x_angles(alpha, beta, gamma):
    """M = Rx(a) Ry(b) Rx(c)이면 비틀림 = a + c."""
    matrix = _mul(_mul(_rx(alpha), _ry(beta)), _rx(gamma))
    assert _angle_diff(_twist(matrix), alpha + gamma) < 1e-6


def test_twist_degenerate_pure_x_rotation():
    """X축만 돈 행렬(b = 0)은 그 각이 그대로 나온다."""
    assert _angle_diff(_twist(_rx(37.0)), 37.0) < 1e-6
    assert _angle_diff(_twist(_rx(-120.0)), -120.0) < 1e-6


def test_twist_is_additive_under_outer_x_rotations():
    """임의 회전 R에 대해 Rx(g) R Rx(-h)의 비틀림 = R의 비틀림 + g - h (롤 평균의 근거)."""
    rng = random.Random(7)
    for _ in range(50):
        base = _mul(_mul(_rz(rng.uniform(-170, 170)), _ry(rng.uniform(-80, 80))), _rx(rng.uniform(-170, 170)))
        g, h = rng.uniform(-60, 60), rng.uniform(-60, 60)
        moved = _mul(_mul(_rx(g), base), _rx(-h))
        assert _angle_diff(_twist(moved), _twist(base) + g - h) < 1e-6


def test_twist_ignores_row_scale():
    """행 길이(스케일)가 섞여도 정규화해서 같은 값을 낸다."""
    matrix = _mul(_mul(_rx(15.0), _ry(50.0)), _rx(20.0))
    scaled = [[c * f for c in row] for row, f in zip(matrix, (2.0, 0.5, 3.0))]
    assert _angle_diff(_twist(scaled), 35.0) < 1e-6


def test_wrap_degrees_range():
    """접은 각은 (-180, 180] 범위다."""
    for value in (-540.0, -181.0, -180.0, 0.0, 179.0, 181.0, 720.5):
        wrapped = mb.wrap_degrees(value)
        assert -180.0 - 1e-9 <= wrapped <= 180.0 + 1e-9
        assert abs(math.sin(math.radians(wrapped)) - math.sin(math.radians(value))) < 1e-9


@pytest.mark.parametrize("stretch, exponent, expected", [
    (1.0, 1.0, (1.0, 1.0, 1.0)),
    (0.5, 1.0, (0.5, 2.0, 2.0)),
    (1.5, 0.5, (1.5, 1.5 ** -0.5, 1.5 ** -0.5)),
])
def test_squash_scale(stretch, exponent, expected):
    """스케일 = [s, s^-k, s^-k]."""
    actual = mb.squash_scale(stretch, exponent)
    assert all(abs(a - e) < 1e-12 for a, e in zip(actual, expected))


def test_scale_script_text_uses_rest_and_exponent():
    """Scale_Script 본문에 레스트 길이와 지수가 리터럴로 들어간다."""
    text = mb._scale_script(30.0, 0.5)
    assert "30.000000000" in text and "-0.500000000" in text
    assert "rootNode" in text and "startNode" in text and "endNode" in text


def test_aim_script_variants_reference_expected_nodes():
    """aim 스크립트가 이전 프레임·롤 유무에 맞는 변수만 참조한다."""
    plain = mb._aim_script(False, False)
    assert "prevNode" not in plain and "rollA" not in plain
    full = mb._aim_script(True, True, 12.5, 0.5)
    assert "prevNode" in full and "rollA" in full and "rollB" in full
    assert "12.500000000" in full and "0.500000000" in full
