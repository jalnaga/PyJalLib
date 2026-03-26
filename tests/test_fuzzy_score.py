# -*- coding: utf-8 -*-
"""_fuzzy_score 함수 단위 테스트."""

from pyjallib.max.ui.fuzzySearchComboBox import _fuzzy_score


def test_match_success_kd_kimdokja():
    """'kd' -> 'KimDokja' 매칭 성공, 점수 > 0."""
    score = _fuzzy_score("kd", "KimDokja")
    assert score > 0


def test_match_success_abc_aabbcc():
    """'abc' -> 'AaBbCc' 매칭 성공, 점수 > 0."""
    score = _fuzzy_score("abc", "AaBbCc")
    assert score > 0


def test_match_failure_xyz_kimdokja():
    """'xyz' -> 'KimDokja' 매칭 실패, 반환값 -1."""
    score = _fuzzy_score("xyz", "KimDokja")
    assert score == -1


def test_empty_pattern_returns_zero():
    """빈 패턴은 0 반환 (전체 매칭)."""
    score = _fuzzy_score("", "KimDokja")
    assert score == 0


def test_consecutive_match_higher_than_nonconsecutive():
    """연속 매칭('Kim' -> 'KimDokja')이 비연속('KDj' -> 'KimDokja')보다 높은 점수."""
    consecutive_score = _fuzzy_score("Kim", "KimDokja")
    nonconsecutive_score = _fuzzy_score("KDj", "KimDokja")
    assert consecutive_score > nonconsecutive_score


def test_word_start_match_higher_than_middle_match():
    """단어 시작점 매칭이 중간 매칭보다 높은 점수."""
    # "K"는 "KimDokja"의 단어 시작 (인덱스 0)
    word_start_score = _fuzzy_score("K", "KimDokja")
    # "i"는 "KimDokja" 중간 문자
    middle_score = _fuzzy_score("i", "KimDokja")
    assert word_start_score > middle_score
