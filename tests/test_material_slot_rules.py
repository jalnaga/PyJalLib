# -*- coding: utf-8 -*-
"""`pyjallib.ue5.materialSlotRules` Type A 테스트.

결정 로직은 `unreal` 없이 전수 검증한다. 계약 단정은 `_check_*` 헬퍼로 두고, 정상 구현과
**결정을 뒤집은 변이 구현** 양쪽에 같은 헬퍼를 건다 - 변이가 실제로 그 헬퍼에서만
실패해야 판별력이 있다(`.claude/references/testing/discriminating_power.md` §1, §3.1).
"""

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Callable, List, Sequence

import pytest

from pyjallib.ue5 import materialSlotRules as rules
from pyjallib.ue5.materialSlotRules import (
    ACTION_RENAME,
    ACTION_SKIP_ALREADY,
    ACTION_SKIP_UNMAPPED,
    RenameTableError,
    SlotDecision,
    build_rename_index,
    decide_slots,
    decision_to_dict,
    has_pending_rename,
)

# 2026-09-15/18 ORV 사이클의 표. 라이브러리 상수가 아니라 **테스트 픽스처**다(표는 주입식).
ORV_TABLE = {
    "Body": "Skin_Body",
    "Face": "Skin_SDF_Face",
    "MouthInterior": "Skin_MouthInterior",
    "Eyebrow": "Skin_SDF_Eyebrow",
    "Iris": "Skin_SDF_Iris",
    "Eyeline": "Skin_SDF_Eyeline",
    "Beard": "Skin_SDF_Beard",
    "Hair": "HairSpec_Hair",
}

# 세 액션이 모두 나오고, 표 밖 슬롯이 중간에 끼고, 정렬하면 순서가 바뀌는 입력
MIXED_SLOTS = ["Face", "Lower", "Skin_Body", "EyeBrow", "Hair", "Upper"]

DecideFn = Callable[[Sequence[str]], List[SlotDecision]]


def _decide(inSlotNames: Sequence[str]) -> List[SlotDecision]:
    """정상 구현(ORV 표, 대소문자 무시).

    Args:
        inSlotNames: 슬롯 이름 목록

    Returns:
        결정 목록
    """
    return decide_slots(inSlotNames, inRenameTable=ORV_TABLE)


# ---------------------------------------------------------------------------
# 계약 단정 헬퍼 - 정상 구현과 변이 구현에 같은 것을 건다
# ---------------------------------------------------------------------------


def _check_unmapped_preserved(inDecide: DecideFn) -> None:
    """표 밖 슬롯은 건드리지 않는다."""
    # 입력을 정렬 순서로 둔다 - 순서 변이가 이 단정까지 깨뜨리면 판별이 겹친다
    decisions = inDecide(["Lower", "Material__001", "Upper"])
    assert [d.action for d in decisions] == [ACTION_SKIP_UNMAPPED] * 3
    assert [d.targetName for d in decisions] == ["Lower", "Material__001", "Upper"]


def _check_already_skipped(inDecide: DecideFn) -> None:
    """이미 정규 목표명이면 스킵한다."""
    decisions = inDecide(["HairSpec_Hair", "Skin_Body"])
    assert [d.action for d in decisions] == [ACTION_SKIP_ALREADY] * 2
    assert not has_pending_rename(decisions)


def _check_order_preserved(inDecide: DecideFn) -> None:
    """입력 순서·개수를 보존한다(인덱스가 슬롯 순서를 따른다)."""
    decisions = inDecide(MIXED_SLOTS)
    assert [d.currentName for d in decisions] == MIXED_SLOTS
    assert [d.slotIndex for d in decisions] == list(range(len(MIXED_SLOTS)))


CONTRACT_CHECKS = {
    "unmapped": _check_unmapped_preserved,
    "already": _check_already_skipped,
    "order": _check_order_preserved,
}


# ---------------------------------------------------------------------------
# 1.5 액션 3종 / 대소문자 변이 / 표 밖 보존 / 순서·개수 보존
# ---------------------------------------------------------------------------


def test_mixed_slots_produce_all_three_actions() -> None:
    decisions = _decide(MIXED_SLOTS)
    assert [(d.action, d.targetName) for d in decisions] == [
        (ACTION_RENAME, "Skin_SDF_Face"),
        (ACTION_SKIP_UNMAPPED, "Lower"),
        (ACTION_SKIP_ALREADY, "Skin_Body"),
        (ACTION_RENAME, "Skin_SDF_Eyebrow"),
        (ACTION_RENAME, "HairSpec_Hair"),
        (ACTION_SKIP_UNMAPPED, "Upper"),
    ]
    assert has_pending_rename(decisions)


@pytest.mark.parametrize("inVariant", ["EyeBrow", "EYEBROW", "eyebrow", "eYeBrOw"])
def test_source_case_variant_converges_to_canonical_target(inVariant: str) -> None:
    [decision] = _decide([inVariant])
    assert decision.action == ACTION_RENAME
    assert decision.targetName == "Skin_SDF_Eyebrow"
    assert decision.variantMatched is True


def test_exact_source_is_not_flagged_as_variant() -> None:
    [decision] = _decide(["Eyebrow"])
    assert decision.targetName == "Skin_SDF_Eyebrow"
    assert decision.variantMatched is False


def test_target_case_variant_is_normalized_not_skipped() -> None:
    # 목표명의 대소문자 변이는 "이미 목표명"이 아니다 - 정규 표기로 맞춘다
    [decision] = _decide(["skin_body"])
    assert decision.action == ACTION_RENAME
    assert decision.targetName == "Skin_Body"
    assert decision.variantMatched is True


def test_unmapped_slots_are_preserved() -> None:
    _check_unmapped_preserved(_decide)


def test_order_and_count_preserved_including_duplicates() -> None:
    _check_order_preserved(_decide)
    duplicated = ["Body", "Body", "Lower", "Body"]
    decisions = _decide(duplicated)
    assert len(decisions) == 4
    assert [d.targetName for d in decisions] == ["Skin_Body", "Skin_Body", "Lower", "Skin_Body"]


def test_decision_to_dict_keys_and_values() -> None:
    [decision] = _decide(["EyeBrow"])
    assert decision_to_dict(decision) == {
        "slotIndex": 0,
        "currentName": "EyeBrow",
        "targetName": "Skin_SDF_Eyebrow",
        "action": ACTION_RENAME,
        "variantMatched": True,
    }


def test_has_pending_rename_pair() -> None:
    # 짝: 치환이 있는 목록은 True, 스킵뿐인 목록은 False, 그리고 둘이 실제로 갈린다
    withRename = has_pending_rename(_decide(["Body", "Lower"]))
    skipsOnly = has_pending_rename(_decide(["Skin_Body", "Lower"]))
    assert withRename is True
    assert skipsOnly is False
    assert withRename != skipsOnly


# ---------------------------------------------------------------------------
# 1.6 멱등 + 경계
# ---------------------------------------------------------------------------


def test_idempotent_rerun_yields_only_skips() -> None:
    first = _decide(MIXED_SLOTS)
    second = _decide([d.targetName for d in first])
    assert {d.action for d in second} <= {ACTION_SKIP_ALREADY, ACTION_SKIP_UNMAPPED}
    assert not has_pending_rename(second)
    # 첫 실행에서 바뀐 슬롯은 재실행에서 정확히 skip:already 가 된다
    renamedIndexes = [d.slotIndex for d in first if d.action == ACTION_RENAME]
    assert renamedIndexes
    assert all(second[i].action == ACTION_SKIP_ALREADY for i in renamedIndexes)


def test_empty_table_leaves_everything_unmapped() -> None:
    decisions = decide_slots(["Body", "Face"], inRenameTable={})
    assert [d.action for d in decisions] == [ACTION_SKIP_UNMAPPED] * 2


def test_empty_slot_list_yields_empty_decisions() -> None:
    assert _decide([]) == []
    assert has_pending_rename([]) is False


def test_case_sensitive_mode_drops_variants_to_unmapped() -> None:
    decisions = decide_slots(["EyeBrow", "Eyebrow", "skin_body"], inRenameTable=ORV_TABLE, inIgnoreCase=False)
    assert [(d.action, d.targetName) for d in decisions] == [
        (ACTION_SKIP_UNMAPPED, "EyeBrow"),
        (ACTION_RENAME, "Skin_SDF_Eyebrow"),
        (ACTION_SKIP_UNMAPPED, "skin_body"),
    ]
    # 짝: 같은 입력이 기본(대소문자 무시)에서는 치환된다 - 인자가 실제로 결과를 가른다
    assert _decide(["EyeBrow"])[0].action == ACTION_RENAME


def test_case_sensitive_mode_allows_case_only_distinct_keys() -> None:
    # 대소문자 구분이면 Body/body는 서로 다른 키다 - 오류가 아니다
    index = build_rename_index({"Body": "Skin_Body", "body": "Skin_body"}, inIgnoreCase=False)
    assert index.sourceByKey == {"Body": "Body", "body": "body"}


@pytest.mark.parametrize(
    "inTable",
    [
        {"Body": "Skin_Body", "body": "Skin_Body2"},          # 구 이름 키 충돌
        {"Body": "Skin_Body", "Torso": "skin_body"},          # 목표명 표기 충돌
        {"A": "B", "B": "C"},                                  # 연쇄 치환
        {"A": "B", "b": "C"},                                  # 대소문자 무시 연쇄
        {"": "X"},                                             # 빈 키
        {"X": ""},                                             # 빈 값
        {"X": 1},                                              # 문자열 아님
    ],
)
def test_ambiguous_tables_are_rejected(inTable: dict) -> None:
    with pytest.raises(RenameTableError):
        build_rename_index(inTable)


def test_non_mapping_table_is_rejected() -> None:
    with pytest.raises(RenameTableError):
        build_rename_index([("Body", "Skin_Body")])


def test_many_to_one_and_identity_tables_are_allowed() -> None:
    index = build_rename_index({"Body": "Skin_Body", "Torso": "Skin_Body", "Skin_Body": "Skin_Body"})
    decisions = decide_slots(["Body", "Torso", "Skin_Body"], inIndex=index)
    assert [(d.action, d.targetName) for d in decisions] == [
        (ACTION_RENAME, "Skin_Body"),
        (ACTION_RENAME, "Skin_Body"),
        (ACTION_SKIP_ALREADY, "Skin_Body"),
    ]


def test_table_or_index_exactly_one() -> None:
    index = build_rename_index(ORV_TABLE)
    with pytest.raises(ValueError):
        decide_slots(["Body"])
    with pytest.raises(ValueError):
        decide_slots(["Body"], inRenameTable=ORV_TABLE, inIndex=index)


def test_index_is_built_per_table_without_global_cache() -> None:
    # 표가 주입이다 - 앞선 호출의 표가 뒤 호출에 새면 안 된다
    first = decide_slots(["Body"], inRenameTable={"Body": "A_Body"})
    second = decide_slots(["Body"], inRenameTable={"Body": "B_Body"})
    assert first[0].targetName == "A_Body"
    assert second[0].targetName == "B_Body"


def test_index_copies_table_so_later_mutation_does_not_leak() -> None:
    table = {"Body": "Skin_Body"}
    index = build_rename_index(table)
    table["Body"] = "Mutated"
    assert decide_slots(["Body"], inIndex=index)[0].targetName == "Skin_Body"


# ---------------------------------------------------------------------------
# 1.7 판별력 증명 - 결정을 뒤집은 변이가 **자기 단정에서만** 실패한다
# ---------------------------------------------------------------------------


def _mutant_renames_unmapped(inSlotNames: Sequence[str]) -> List[SlotDecision]:
    """변이: 표 밖 슬롯도 치환한다."""
    return [
        SlotDecision(d.slotIndex, d.currentName, f"X_{d.currentName}", ACTION_RENAME, False)
        if d.action == ACTION_SKIP_UNMAPPED else d
        for d in _decide(inSlotNames)
    ]


def _mutant_rerenames_already(inSlotNames: Sequence[str]) -> List[SlotDecision]:
    """변이: 이미 목표명인 슬롯도 다시 치환한다."""
    return [
        SlotDecision(d.slotIndex, d.currentName, d.targetName, ACTION_RENAME, False)
        if d.action == ACTION_SKIP_ALREADY else d
        for d in _decide(inSlotNames)
    ]


def _mutant_sorts_input(inSlotNames: Sequence[str]) -> List[SlotDecision]:
    """변이: 입력을 정렬한 뒤 결정한다."""
    return _decide(sorted(inSlotNames))


MUTANTS = {
    "unmapped": _mutant_renames_unmapped,
    "already": _mutant_rerenames_already,
    "order": _mutant_sorts_input,
}


def test_real_implementation_passes_every_contract_check() -> None:
    for check in CONTRACT_CHECKS.values():
        check(_decide)


@pytest.mark.parametrize("inMutantName", sorted(MUTANTS))
def test_mutant_fails_exactly_its_own_contract_check(inMutantName: str) -> None:
    mutant = MUTANTS[inMutantName]
    failed = set()
    for checkName, check in CONTRACT_CHECKS.items():
        try:
            check(mutant)
        except AssertionError:
            failed.add(checkName)
    # 주입 1건 -> 실패 1건. 여러 단정이 함께 실패하면 무엇이 무엇을 지키는지 모른다
    assert failed == {inMutantName}


def test_sort_mutant_keeps_count_so_count_only_check_is_blind() -> None:
    # 정렬 변이는 개수는 맞추므로 "개수만" 보는 단정으로는 잡히지 않는다 - 순서 단정이 필요한 이유
    mutantDecisions = _mutant_sorts_input(MIXED_SLOTS)
    assert len(mutantDecisions) == len(MIXED_SLOTS)
    assert [d.currentName for d in mutantDecisions] != MIXED_SLOTS


# ---------------------------------------------------------------------------
# stdlib-only 요구사항 - UE5 임베디드 파이썬에서 단독 로드된다
# ---------------------------------------------------------------------------

_MODULE_PATH = Path(rules.__file__)


def test_module_imports_only_stdlib() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "상대 import 금지 - 평면 로드가 깨진다"
            imported.add(node.module.split(".")[0])
    assert imported, "import를 하나도 못 찾으면 이 단정은 공허하다"
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)


def test_module_loads_standalone_without_package_context() -> None:
    # UE5 legacy 템플릿처럼 패키지 밖에서 파일 하나만 평면 로드한다
    spec = importlib.util.spec_from_file_location("materialSlotRules_standalone", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.decide_slots(["Body"], inRenameTable={"Body": "Skin_Body"})[0].targetName == "Skin_Body"
