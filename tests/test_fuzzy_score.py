# -*- coding: utf-8 -*-
"""_fuzzy_score 함수 단위 테스트.

kd 성공·xyz 실패·빈 패턴·연속 우위는 test_fuzzy_match_module.py::test_score_values_preserved가
같은 단정을 하므로 여기서는 그 밖의 케이스만 둔다(2026-11-05 테스트 정리에서 중복 제거).
"""

from pyjallib.max.ui.fuzzySearchComboBox import _fuzzy_score


def test_match_success_abc_aabbcc():
    """'abc' -> 'AaBbCc' 매칭 성공, 점수 > 0."""
    score = _fuzzy_score("abc", "AaBbCc")
    assert score > 0


def test_word_start_match_higher_than_middle_match():
    """단어 시작점 매칭이 중간 매칭보다 높은 점수."""
    # "K"는 "KimDokja"의 단어 시작 (인덱스 0)
    word_start_score = _fuzzy_score("K", "KimDokja")
    # "i"는 "KimDokja" 중간 문자
    middle_score = _fuzzy_score("i", "KimDokja")
    assert word_start_score > middle_score
