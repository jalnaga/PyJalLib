#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""출력 노드 이름 규약 (pymxs 무의존 순수 모듈).

기본 규약은 `{포즈메쉬이름}_L` / `{포즈메쉬이름}_R`이고 접미사는 UI에서 바꿀 수 있다.

**동명 노드를 3ds Max의 자동 리네임에 맡기지 않는다.** Max는 이름이 겹치면 조용히
`Funnel_L001` 같은 이름을 붙이는데, 그러면 사용자가 방금 만든 노드가 어느 것인지
알 수 없고 이전 결과가 씬에 남아 있는 것도 눈치채지 못한다. 충돌은 **명시적으로
감지해 보고**한다.

기존 이름 목록을 인자로 받으므로 씬 접근이 필요 없다 - 어댑터가 목록을 모아 넘긴다.
"""

from dataclasses import dataclass

DEFAULT_LEFT_SUFFIX = "_L"
DEFAULT_RIGHT_SUFFIX = "_R"


@dataclass(frozen=True)
class SplitNames:
    """분리 결과 노드의 이름 한 쌍.

    Attributes:
        left: 좌 포즈 노드 이름
        right: 우 포즈 노드 이름
    """

    left: str
    right: str


def build_split_names(
    inPoseName: str,
    inLeftSuffix: str = DEFAULT_LEFT_SUFFIX,
    inRightSuffix: str = DEFAULT_RIGHT_SUFFIX,
) -> SplitNames:
    """포즈 메쉬 이름과 접미사로 출력 이름 한 쌍을 만든다.

    Args:
        inPoseName: 포즈 메쉬 노드 이름
        inLeftSuffix: 좌 접미사. 기본 "_L".
        inRightSuffix: 우 접미사. 기본 "_R".

    Returns:
        SplitNames

    Raises:
        ValueError: 포즈 이름이 비었거나, 접미사가 비었거나, 두 접미사가 같을 때
    """
    poseName = "" if inPoseName is None else str(inPoseName).strip()
    if not poseName:
        raise ValueError("포즈 메쉬 이름이 비어 있다.")

    leftSuffix = "" if inLeftSuffix is None else str(inLeftSuffix)
    rightSuffix = "" if inRightSuffix is None else str(inRightSuffix)

    if not leftSuffix.strip():
        raise ValueError("좌 접미사가 비어 있다.")
    if not rightSuffix.strip():
        raise ValueError("우 접미사가 비어 있다.")
    if leftSuffix == rightSuffix:
        raise ValueError(
            f"좌·우 접미사가 같다({leftSuffix!r}). 두 결과가 같은 이름이 되어 구분할 수 없다."
        )

    return SplitNames(left=poseName + leftSuffix, right=poseName + rightSuffix)


def detect_name_collisions(inNames: SplitNames, inExistingNames) -> list[str]:
    """만들려는 이름이 이미 씬에 있는지 감지한다.

    Args:
        inNames: 만들려는 이름 한 쌍
        inExistingNames: 씬에 있는 노드 이름들

    Returns:
        충돌한 이름 목록. 비어 있으면 충돌 없음.
    """
    # 3ds Max의 노드 이름 비교는 대소문자를 구분하지 않는다. 대소문자만 다른 이름을
    # "충돌 아님"으로 판정하면 자동 리네임이 발동해 감지를 우회한다.
    existing = {str(n).strip().lower() for n in (inExistingNames or [])}

    collisions = []
    for name in (inNames.left, inNames.right):
        if name.strip().lower() in existing:
            collisions.append(name)
    return collisions


def format_collision_message(inCollisions) -> str:
    """충돌 보고 메시지를 만든다.

    Args:
        inCollisions: 충돌한 이름 목록

    Returns:
        사람이 읽는 메시지. 충돌이 없으면 빈 문자열.
    """
    names = list(inCollisions or [])
    if not names:
        return ""

    joined = ", ".join(names)
    return (
        f"같은 이름의 노드가 이미 씬에 있다: {joined}. "
        "3ds Max의 자동 리네임에 맡기지 않고 멈춘다 - 접미사를 바꾸거나 기존 노드를 정리한다."
    )
