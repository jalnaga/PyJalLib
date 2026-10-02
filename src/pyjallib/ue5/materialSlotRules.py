#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""매테리얼 슬롯 이름 치환 결정 (unreal 비의존 순수 로직)

슬롯 이름 목록 + 치환 표를 받아 슬롯별로 "무엇을 어떻게 바꿀지"만 결정한다. 메쉬를
건드리는 일은 `inUnreal/materialSlots.py`가 하고, 이 모듈은 그 결정을 한 곳에 모은다.

**이 모듈은 표준 라이브러리만 쓴다 - 편의가 아니라 요구사항이다.** UE5 임베디드
파이썬에는 pyjallib 전체가 import되지 않으므로(`pyjallib/__init__`이 P4Python을
끌어온다), 인-UE5 어댑터와 콘솔 테스트가 **같은 결정 함수**를 쓰려면 이 모듈이
stdlib만 의존해야 한다. 그래야 "드라이런에서 본 것"과 "실집행에서 바뀐 것"이 같다고
말할 수 있다(`.claude/references/ue5/silent_write_paths.md` §7).

결정 규칙 (2026-09-15 `UE5MatSlotRename` 사이클 D2~D4 승계, 2026-10-02 라이브러리 승격):

- **치환 표는 호출자가 주입한다.** 표의 내용(예: ORV의 `Skin_` 접두)은 프로젝트 규약이고
  범용 라이브러리가 상수로 가질 것이 아니다. 그래서 대소문자 무시 역인덱스도 모듈 전역
  캐시가 아니라 **표마다** `build_rename_index`로 만든다.
- 표에 없는 슬롯은 건드리지 않고 `skip:unmapped`로 열거만 한다. 정책이 아니라 "변경
  대상을 넓히지 않는다"는 일반 규율이라 끌 수 있는 옵션으로 두지 않는다.
- 이미 정규 목표명인 슬롯은 `skip:already`로 스킵한다(멱등 - 결과를 다시 넣으면 전부
  스킵).
- 대소문자 무시 매칭은 **기본 켜짐**이다(`EyeBrow` -> 표의 정규 목표명). 결과는 항상
  표에 적힌 정규 표기이고, 변이로 매칭됐는지는 `variantMatched`로 남긴다. 범용
  라이브러리이므로 호출자가 끌 수 있다.
"""

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

ACTION_RENAME = "rename"
"""슬롯 이름을 표의 정규 목표명으로 바꾼다."""

ACTION_SKIP_ALREADY = "skip:already"
"""이미 정규 목표명이다 - 바꾸지 않는다(멱등)."""

ACTION_SKIP_UNMAPPED = "skip:unmapped"
"""치환 표 밖이다 - 바꾸지 않고 열거만 한다."""

ACTIONS = (ACTION_RENAME, ACTION_SKIP_ALREADY, ACTION_SKIP_UNMAPPED)
"""결정 액션 전체. 결과 JSON을 읽는 쪽이 집계 키로 쓴다."""


class RenameTableError(ValueError):
    """치환 표가 결정을 모호하게 만드는 경우의 오류.

    조용히 한쪽을 고르면 어느 슬롯이 어디로 가는지가 표의 dict 순서에 좌우되므로,
    표를 만드는 시점에 명시적으로 거절한다.
    """


@dataclass(frozen=True)
class SlotDecision:
    """슬롯 1개에 대한 치환 결정.

    Attributes:
        slotIndex: 매테리얼 슬롯의 0-기반 인덱스
        currentName: 현재 슬롯 이름
        targetName: 치환 후 이름. 스킵이면 `currentName`과 같다.
        action: `ACTION_RENAME` / `ACTION_SKIP_ALREADY` / `ACTION_SKIP_UNMAPPED`
        variantMatched: 대소문자 변이로 매칭되었는지 여부(리포트용)
    """

    slotIndex: int
    currentName: str
    targetName: str
    action: str
    variantMatched: bool


@dataclass(frozen=True)
class RenameIndex:
    """치환 표 1개에서 만든 매칭용 역인덱스.

    Attributes:
        renameTable: 원 치환 표 사본(구 이름 -> 정규 목표명)
        ignoreCase: 대소문자 무시 매칭 여부
        sourceByKey: 매칭 키 -> 표에 적힌 구 이름
        targetByKey: 매칭 키 -> 표에 적힌 정규 목표명
    """

    renameTable: Dict[str, str]
    ignoreCase: bool
    sourceByKey: Dict[str, str]
    targetByKey: Dict[str, str]

    def key_of(self, inName: str) -> str:
        """이름을 이 인덱스의 매칭 키로 바꾼다.

        Args:
            inName: 슬롯 이름

        Returns:
            대소문자 무시면 casefold한 이름, 아니면 이름 그대로
        """
        return inName.casefold() if self.ignoreCase else inName


def build_rename_index(inRenameTable: Mapping[str, str], inIgnoreCase: bool = True) -> RenameIndex:
    """치환 표에서 매칭용 역인덱스를 만든다.

    표마다 새로 만든다 - 모듈 전역 캐시를 두지 않는다(표가 주입이므로 전역 캐시는
    다른 호출자의 표로 오염된다).

    거절하는 표(`RenameTableError`):
        - 키·값이 비었거나 문자열이 아니다.
        - 매칭 키로 같아지는 구 이름이 둘 이상이다(대소문자 무시에서 `Body`/`body`).
        - 매칭 키로 같아지는데 표기가 다른 목표명이 있다(`Skin_Body`/`skin_body`).
        - 한 항목의 구 이름이 **다른 항목의** 목표명이다(`A->B`, `B->C`). 이 슬롯이
          "이미 목표명"인지 "바꿀 대상"인지가 모호하고, 멱등이 깨진다.

    Args:
        inRenameTable: 구 이름 -> 정규 목표명 표
        inIgnoreCase: 대소문자 무시 매칭 여부. 기본값 True.

    Returns:
        역인덱스

    Raises:
        RenameTableError: 표가 결정을 모호하게 만드는 경우
    """
    if not isinstance(inRenameTable, Mapping):
        raise RenameTableError(f"치환 표는 Mapping이어야 한다: {type(inRenameTable).__name__}")

    def _key(inName: str) -> str:
        return inName.casefold() if inIgnoreCase else inName

    sourceByKey: Dict[str, str] = {}
    targetByKey: Dict[str, str] = {}
    for source, target in inRenameTable.items():
        if not isinstance(source, str) or not isinstance(target, str) or not source or not target:
            raise RenameTableError(f"치환 표 항목은 비지 않은 문자열이어야 한다: {source!r} -> {target!r}")

        sourceKey = _key(source)
        if sourceKey in sourceByKey:
            raise RenameTableError(
                f"매칭 키가 같은 구 이름이 둘 이상이다: {sourceByKey[sourceKey]!r}, {source!r}"
            )
        sourceByKey[sourceKey] = source

        targetKey = _key(target)
        existingTarget = targetByKey.get(targetKey)
        if existingTarget is not None and existingTarget != target:
            raise RenameTableError(
                f"매칭 키가 같은데 표기가 다른 목표명이 있다: {existingTarget!r}, {target!r}"
            )
        targetByKey[targetKey] = target

    for sourceKey, source in sourceByKey.items():
        chainedTarget = targetByKey.get(sourceKey)
        if chainedTarget is not None and _key(inRenameTable[source]) != sourceKey:
            raise RenameTableError(
                f"구 이름 {source!r}이 다른 항목의 목표명 {chainedTarget!r}과 같다(연쇄 치환)"
            )

    return RenameIndex(
        renameTable=dict(inRenameTable),
        ignoreCase=inIgnoreCase,
        sourceByKey=sourceByKey,
        targetByKey=targetByKey,
    )


def decide_slot(inSlotIndex: int, inSlotName: str, inIndex: RenameIndex) -> SlotDecision:
    """슬롯 이름 하나에 대한 치환 결정을 만든다.

    목표명 판정을 구 이름 판정보다 먼저 한다 - 그래야 결과를 다시 넣었을 때 전부
    `skip:already`가 된다(멱등).

    Args:
        inSlotIndex: 매테리얼 슬롯의 0-기반 인덱스
        inSlotName: 현재 슬롯 이름
        inIndex: `build_rename_index` 결과

    Returns:
        결정 결과
    """
    key = inIndex.key_of(inSlotName)

    canonicalTarget = inIndex.targetByKey.get(key)
    if canonicalTarget is not None:
        if inSlotName == canonicalTarget:
            return SlotDecision(inSlotIndex, inSlotName, inSlotName, ACTION_SKIP_ALREADY, False)
        # 목표명의 대소문자 변이 - 정규 표기로 맞춘다
        return SlotDecision(inSlotIndex, inSlotName, canonicalTarget, ACTION_RENAME, True)

    canonicalSource = inIndex.sourceByKey.get(key)
    if canonicalSource is not None:
        return SlotDecision(
            inSlotIndex,
            inSlotName,
            inIndex.renameTable[canonicalSource],
            ACTION_RENAME,
            inSlotName != canonicalSource,
        )

    return SlotDecision(inSlotIndex, inSlotName, inSlotName, ACTION_SKIP_UNMAPPED, False)


def decide_slots(
    inSlotNames: Sequence[str],
    inRenameTable: Optional[Mapping[str, str]] = None,
    inIgnoreCase: bool = True,
    inIndex: Optional[RenameIndex] = None,
) -> List[SlotDecision]:
    """에셋 하나의 슬롯 이름 목록에 대한 결정 목록을 만든다.

    입력 순서와 개수를 그대로 보존한다 - 슬롯 순서가 매테리얼 할당 순서이므로 정렬하거나
    중복을 제거하지 않는다.

    표(`inRenameTable`)나 미리 만든 인덱스(`inIndex`) 중 **정확히 하나**를 준다. 여러
    에셋에 같은 표를 적용하면 인덱스를 한 번 만들어 넘기는 쪽이 싸다.

    Args:
        inSlotNames: 슬롯 이름 목록(슬롯 인덱스 순서)
        inRenameTable: 구 이름 -> 정규 목표명 표
        inIgnoreCase: 대소문자 무시 매칭 여부. `inRenameTable`을 줄 때만 쓴다. 기본값 True.
        inIndex: `build_rename_index` 결과

    Returns:
        입력과 같은 길이·순서의 결정 목록

    Raises:
        ValueError: 표와 인덱스를 둘 다 주거나 둘 다 주지 않은 경우
        RenameTableError: 표가 결정을 모호하게 만드는 경우
    """
    if (inRenameTable is None) == (inIndex is None):
        raise ValueError("inRenameTable과 inIndex 중 정확히 하나를 줘야 한다")
    index = inIndex if inIndex is not None else build_rename_index(inRenameTable, inIgnoreCase)
    return [decide_slot(slotIndex, name, index) for slotIndex, name in enumerate(inSlotNames)]


def has_pending_rename(inDecisions: Sequence[SlotDecision]) -> bool:
    """결정 목록에 실제 치환이 하나라도 있는지 확인한다.

    "변경된 에셋만 저장"의 판정 근거다. `save_asset`은 논리적 변경이 없어도 재직렬화로
    바이트를 바꾸므로 이 판정이 저장 범위를 정하는 유일한 방어선이다.

    Args:
        inDecisions: `decide_slots` 결과

    Returns:
        `rename` 액션이 하나 이상이면 True
    """
    return any(decision.action == ACTION_RENAME for decision in inDecisions)


def decision_to_dict(inDecision: SlotDecision) -> Dict:
    """결정을 결과 JSON에 넣을 dict로 바꾼다.

    키는 추가만 한다 - 기존 키의 의미·타입을 바꾸지 않는다(읽는 쪽 하위호환).

    Args:
        inDecision: 결정 결과

    Returns:
        직렬화 가능한 dict
    """
    return {
        "slotIndex": inDecision.slotIndex,
        "currentName": inDecision.currentName,
        "targetName": inDecision.targetName,
        "action": inDecision.action,
        "variantMatched": inDecision.variantMatched,
    }


__all__ = [
    "ACTION_RENAME",
    "ACTION_SKIP_ALREADY",
    "ACTION_SKIP_UNMAPPED",
    "ACTIONS",
    "RenameTableError",
    "SlotDecision",
    "RenameIndex",
    "build_rename_index",
    "decide_slot",
    "decide_slots",
    "has_pending_rename",
    "decision_to_dict",
]
