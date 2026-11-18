#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""퍼지 문자열 매칭 모듈.

패턴의 문자들이 대상 텍스트에 순서대로(부분수열로) 존재하는지 판정하고,
연속 매칭과 단어 시작점 매칭에 보너스를 준 스코어를 계산한다.

이 모듈은 **stdlib만 사용한다.** ``pymxs``도 ``PySide2``도 import하지 않으므로
3ds Max 밖의 콘솔 환경에서 그대로 import·테스트할 수 있다. 이것이 이 모듈이
``pyjallib.max.ui`` 밑이 아니라 패키지 루트에 있는 이유다 - ``pyjallib.max``
패키지는 로드 시점에 ``pymxs``를 요구하므로, 그 밑에 두면 순수 판정 로직에
DCC 없이는 닿을 수 없다.

사용처:
    - ``pyjallib.max.ui.fuzzySearchComboBox``: 콤보박스 팝업의 검색·정렬
    - 리스트 위젯의 검색 필터 등, 이름 집합을 패턴으로 좁히는 모든 UI
"""


def fuzzy_score(inPattern: str, inText: str) -> int:
    """퍼지 매칭 스코어를 계산한다.

    패턴의 모든 문자가 텍스트에 순서대로 존재하면 매칭 성공.
    연속 매칭과 단어 시작점 매칭에 보너스를 부여한다.

    대소문자는 구분하지 않는다.

    Args:
        inPattern: 검색 패턴 문자열
        inText: 매칭 대상 텍스트

    Returns:
        매칭 스코어. 매칭 실패 시 -1, 빈 패턴은 0.
    """
    if not inPattern:
        return 0

    patternLower = inPattern.lower()
    textLower = inText.lower()

    score = 0
    patternIdx = 0
    prevMatchIdx = -2  # -2로 초기화하여 첫 매칭에서 연속 보너스 방지

    for textIdx in range(len(textLower)):
        if patternIdx >= len(patternLower):
            break

        if textLower[textIdx] == patternLower[patternIdx]:
            # 기본 매칭 점수
            score += 1

            # 연속 매칭 보너스: 이전 매칭 위치 바로 다음에 매칭되면
            if textIdx == prevMatchIdx + 1:
                score += 6

            # 단어 시작점 보너스: 대문자이거나 _/- 바로 뒤 문자
            if is_word_start(inText, textIdx):
                score += 10

            prevMatchIdx = textIdx
            patternIdx += 1

    # 패턴의 모든 문자가 매칭되지 않으면 실패
    if patternIdx < len(patternLower):
        return -1

    return score


def is_word_start(inText: str, inIdx: int) -> bool:
    """해당 인덱스의 문자가 단어 시작점인지 판별한다.

    단어 시작점 조건:
    - 첫 번째 문자
    - 대문자이면서 이전 문자가 소문자인 경우 (camelCase 경계)
    - '_' 또는 '-' 바로 뒤의 문자

    Args:
        inText: 전체 텍스트
        inIdx: 판별 대상 인덱스

    Returns:
        단어 시작점이면 True
    """
    if inIdx == 0:
        return True

    currentChar = inText[inIdx]
    prevChar = inText[inIdx - 1]

    # 대문자이면서 이전 문자가 소문자 (camelCase 경계)
    if currentChar.isupper() and prevChar.islower():
        return True

    # '_' 또는 '-' 바로 뒤의 문자
    if prevChar in ("_", "-"):
        return True

    return False
