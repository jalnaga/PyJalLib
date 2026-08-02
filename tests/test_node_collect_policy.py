# -*- coding: utf-8 -*-
"""노드 수집 확장 규칙 엔진(순수 모듈) Type A 회귀 가드.

``nodeCollectPolicy``는 pymxs에 의존하지 않으므로 3ds Max 없이 규칙 전체를
검증한다. 규칙 한 줄을 고칠 때마다 Max를 띄우지 않아도 되도록 분리한 것이므로,
규칙의 발동/미발동 경계를 여기서 전부 고정한다.

핸들은 정수이므로 테스트에서는 의미를 알기 쉬운 번호대를 쓴다.
"""

from pathlib import Path

from pyjallib.max.nodeCollectPolicy import (
    ADD_KEY,
    ALL_RULE_KEYS,
    RULE_ALL_OR_NOTHING,
    RULE_MANDATORY,
    RULE_PARENT_CHAIN,
    RULE_PARENT_CONDITIONAL,
    TRIGGER_KEY,
    NodeCollectPolicy,
    expand_node_set,
)


def _make_all_or_nothing(inLayerName, inTriggerIds, inAddIds=None):
    """규칙 2 항목 dict를 만든다. inAddIds가 None이면 trigger와 같은 집합을 쓴다."""
    return {
        inLayerName: {
            TRIGGER_KEY: set(inTriggerIds),
            ADD_KEY: set(inAddIds) if inAddIds is not None else set(inTriggerIds),
        }
    }


# --------------------------------------------------------------------------- #
#  순수성 (PRD Must-Have 1: pymxs import 0건)
# --------------------------------------------------------------------------- #


def test_engine_module_has_no_pymxs_import():
    """엔진 모듈 소스에 pymxs import가 없어야 한다.

    pymxs가 들어오면 콘솔 pytest로 규칙을 검증할 수 없게 되어 이 파일 전체가
    무력화된다. 그래서 소스 텍스트로 직접 단정한다.
    """
    from pyjallib.max import nodeCollectPolicy

    sourceText = Path(nodeCollectPolicy.__file__).read_text(encoding="utf-8")

    assert "import pymxs" not in sourceText
    assert "from pymxs" not in sourceText


# --------------------------------------------------------------------------- #
#  1.5 규칙 1~3 각 단독 발동 / 미발동
# --------------------------------------------------------------------------- #


def test_no_policy_means_no_expansion():
    """규칙 인자를 전혀 주지 않으면 기준 집합이 그대로 나온다."""
    baseIds = {1, 2, 3}

    expanded = expand_node_set(baseIds)

    assert expanded["result"] == {1, 2, 3}
    assert all(expanded["byRule"][ruleKey] == [] for ruleKey in ALL_RULE_KEYS)


def test_empty_policy_dataclass_is_reported_empty():
    """빈 정서는 is_empty()가 True다. 경계 레이어만 있어도 비어 있는 것으로 본다."""
    assert NodeCollectPolicy().is_empty() is True
    assert NodeCollectPolicy(parentChainBoundaryLayers=["Boundary_*"]).is_empty() is True
    assert NodeCollectPolicy(mandatoryLayers=["A"]).is_empty() is False
    assert NodeCollectPolicy(allOrNothingLayers=["A"]).is_empty() is False
    assert NodeCollectPolicy(parentConditionalLayers=["A"]).is_empty() is False


def test_rule_mandatory_always_adds():
    """규칙 1은 기준 집합과 교집합이 없어도 항상 추가한다."""
    expanded = expand_node_set(
        inBaseIds={1},
        inMandatoryIds={10, 11},
        inParentMap={10: None, 11: None},
    )

    assert expanded["result"] == {1, 10, 11}
    assert sorted(expanded["byRule"][RULE_MANDATORY]) == [10, 11]


def test_rule_mandatory_with_empty_target_does_nothing():
    """규칙 1의 대상 집합이 비면 아무것도 추가하지 않는다."""
    expanded = expand_node_set(inBaseIds={1}, inMandatoryIds=set())

    assert expanded["result"] == {1}
    assert expanded["byRule"][RULE_MANDATORY] == []


def test_rule_all_or_nothing_fires_only_on_intersection():
    """규칙 2는 판정 집합이 기준 집합과 겹칠 때만 발동한다."""
    layerIds = {20, 21, 22}

    fired = expand_node_set(
        inBaseIds={20},
        inAllOrNothingIdsByLayer=_make_all_or_nothing("AddOn_A", layerIds),
        inParentMap=dict.fromkeys(layerIds, None),
    )
    notFired = expand_node_set(
        inBaseIds={99},
        inAllOrNothingIdsByLayer=_make_all_or_nothing("AddOn_A", layerIds),
        inParentMap=dict.fromkeys(layerIds, None),
    )

    assert fired["result"] == {20, 21, 22}
    assert sorted(fired["byRule"][RULE_ALL_OR_NOTHING]) == [21, 22]
    assert notFired["result"] == {99}
    assert notFired["byRule"][RULE_ALL_OR_NOTHING] == []


def test_rule_parent_conditional_fires_only_when_parent_present():
    """규칙 3은 부모가 결과 집합에 있을 때만 발동한다."""
    parentMap = {30: 1, 31: 2}

    expanded = expand_node_set(
        inBaseIds={1},
        inParentConditionalIds={30, 31},
        inParentMap=parentMap,
    )

    assert expanded["result"] == {1, 30}
    assert expanded["byRule"][RULE_PARENT_CONDITIONAL] == [30]


def test_rule_parent_conditional_skips_orphan():
    """부모가 없는 조건부 노드는 발동 조건 자체가 성립하지 않는다."""
    expanded = expand_node_set(
        inBaseIds={1},
        inParentConditionalIds={30},
        inParentMap={30: None},
    )

    assert expanded["result"] == {1}
    assert expanded["byRule"][RULE_PARENT_CONDITIONAL] == []


# --------------------------------------------------------------------------- #
#  1.6 규칙 2의 trigger != add 비대칭
# --------------------------------------------------------------------------- #


def test_all_or_nothing_trigger_differs_from_add():
    """본이 판정을 발동시키고 Helper만 추가되는 AddOn Helper 동작을 재현한다.

    판정 집합에 본(40, 41)이 있고 추가 집합에는 Helper(42, 43)만 있다. 의존성에
    걸리는 것은 보통 본이므로, 판정에도 Helper 필터를 걸면 규칙이 아예 발동하지
    않는다. 이 비대칭이 클래스 필터 확장의 핵심이다.
    """
    triggerIds = {40, 41, 42, 43}
    addIds = {42, 43}

    expanded = expand_node_set(
        inBaseIds={40},
        inAllOrNothingIdsByLayer=_make_all_or_nothing(
            "Rig_AddOn_Face", triggerIds, addIds
        ),
        inParentMap=dict.fromkeys(triggerIds, None),
    )

    assert expanded["result"] == {40, 42, 43}
    assert sorted(expanded["byRule"][RULE_ALL_OR_NOTHING]) == [42, 43]
    # 판정에만 있던 본 41은 추가 집합에 없으므로 들어오지 않는다.
    assert 41 not in expanded["result"]


def test_all_or_nothing_add_only_filter_does_not_block_trigger():
    """추가 집합이 비면 발동하더라도 추가되는 것이 없다."""
    expanded = expand_node_set(
        inBaseIds={40},
        inAllOrNothingIdsByLayer=_make_all_or_nothing("AddOn_A", {40, 41}, set()),
        inParentMap={40: None, 41: None},
    )

    assert expanded["result"] == {40}
    assert expanded["byRule"][RULE_ALL_OR_NOTHING] == []


# --------------------------------------------------------------------------- #
#  1.7 규칙 2의 레이어별 독립 판정
# --------------------------------------------------------------------------- #


def test_all_or_nothing_layers_are_judged_independently():
    """한 레이어의 발동이 다른 레이어를 끌고 들어오지 않는다."""
    idsByLayer = {}
    idsByLayer.update(_make_all_or_nothing("AddOn_A", {50, 51}))
    idsByLayer.update(_make_all_or_nothing("AddOn_B", {60, 61}))

    expanded = expand_node_set(
        inBaseIds={50},
        inAllOrNothingIdsByLayer=idsByLayer,
        inParentMap=dict.fromkeys([50, 51, 60, 61], None),
    )

    assert expanded["result"] == {50, 51}
    assert expanded["byRule"][RULE_ALL_OR_NOTHING] == [51]


def test_all_or_nothing_fires_per_layer_when_both_hit():
    """두 레이어가 각각 걸리면 둘 다 발동한다."""
    idsByLayer = {}
    idsByLayer.update(_make_all_or_nothing("AddOn_A", {50, 51}))
    idsByLayer.update(_make_all_or_nothing("AddOn_B", {60, 61}))

    expanded = expand_node_set(
        inBaseIds={50, 60},
        inAllOrNothingIdsByLayer=idsByLayer,
        inParentMap=dict.fromkeys([50, 51, 60, 61], None),
    )

    assert expanded["result"] == {50, 51, 60, 61}
    assert sorted(expanded["byRule"][RULE_ALL_OR_NOTHING]) == [51, 61]


# --------------------------------------------------------------------------- #
#  1.8 부모 체인 경계
# --------------------------------------------------------------------------- #


def test_parent_chain_stops_outside_boundary():
    """경계 밖 부모에서 추적을 멈춘다.

    계층: 72 -> 71 -> 70 -> 900(경계 밖). 경계는 {70, 71, 72}뿐이므로 900은
    결과에 들어오지 않는다.
    """
    parentMap = {72: 71, 71: 70, 70: 900, 900: None}

    expanded = expand_node_set(
        inBaseIds=set(),
        inMandatoryIds={72},
        inParentMap=parentMap,
        inParentChainBoundaryIds={70, 71, 72},
    )

    assert expanded["result"] == {70, 71, 72}
    assert expanded["byRule"][RULE_MANDATORY] == [72]
    assert expanded["byRule"][RULE_PARENT_CHAIN] == [71, 70]


def test_parent_chain_without_boundary_does_not_expand():
    """경계 집합이 비면 부모 체인 확장이 일어나지 않는다."""
    expanded = expand_node_set(
        inBaseIds=set(),
        inMandatoryIds={72},
        inParentMap={72: 71, 71: 70, 70: None},
    )

    assert expanded["result"] == {72}
    assert expanded["byRule"][RULE_PARENT_CHAIN] == []


def test_parent_chain_stops_at_already_collected_parent():
    """이미 결과 집합에 있는 부모를 만나면 즉시 중단한다.

    71이 기준 집합에 있으므로 72의 추적은 71에서 끝나고 70까지 가지 않는다.
    결과 집합의 핸들은 자신의 부모 체인 추적을 이미 마쳤다는 불변식이다.
    """
    expanded = expand_node_set(
        inBaseIds={71},
        inMandatoryIds={72},
        inParentMap={72: 71, 71: 70, 70: None},
        inParentChainBoundaryIds={70, 71, 72},
    )

    assert expanded["result"] == {71, 72}
    assert expanded["byRule"][RULE_PARENT_CHAIN] == []


def test_parent_chain_stops_at_root_without_parent():
    """부모가 None인 루트에서 멈춘다(무한 루프 방지)."""
    expanded = expand_node_set(
        inBaseIds=set(),
        inMandatoryIds={72},
        inParentMap={72: 71, 71: None},
        inParentChainBoundaryIds={71, 72},
    )

    assert expanded["result"] == {71, 72}
    assert expanded["byRule"][RULE_PARENT_CHAIN] == [71]


# --------------------------------------------------------------------------- #
#  1.9 규칙 3 연쇄 + 종료 보장
# --------------------------------------------------------------------------- #


def test_parent_conditional_chains_through_newly_added():
    """새로 추가된 조건부 노드에 매달린 조건부 노드까지 연쇄 발동한다.

    계층: 81(부모 1) -> 82(부모 81) -> 83(부모 82). 1만 기준 집합에 있어도
    세 개가 순차로 들어온다.
    """
    expanded = expand_node_set(
        inBaseIds={1},
        inParentConditionalIds={81, 82, 83},
        inParentMap={81: 1, 82: 81, 83: 82},
    )

    assert expanded["result"] == {1, 81, 82, 83}
    assert expanded["byRule"][RULE_PARENT_CONDITIONAL] == [81, 82, 83]


def test_parent_conditional_terminates_on_parent_cycle():
    """조건부 노드가 서로를 부모로 갖는 순환에서도 종료한다.

    부모가 결과 집합에 없으므로 아무것도 추가되지 않고 첫 반복에서 끝난다.
    """
    expanded = expand_node_set(
        inBaseIds={1},
        inParentConditionalIds={85, 86},
        inParentMap={85: 86, 86: 85},
    )

    assert expanded["result"] == {1}
    assert expanded["byRule"][RULE_PARENT_CONDITIONAL] == []


def test_rule_two_pulls_parent_that_rule_three_hangs_on():
    """규칙 2가 끌어온 부모에 규칙 3이 걸리는 상호작용.

    규칙 2가 91을 넣으면서 부모 체인으로 90을 끌어오고, 90을 부모로 갖는
    조건부 노드 95가 규칙 3에서 발동한다. 규칙 적용 순서(1 -> 2 -> 3)가
    이 경로를 성립시킨다.
    """
    parentMap = {91: 90, 90: None, 92: 90, 95: 90}

    expanded = expand_node_set(
        inBaseIds={92},
        inAllOrNothingIdsByLayer=_make_all_or_nothing("AddOn_A", {91, 92}),
        inParentConditionalIds={95},
        inParentMap=parentMap,
        inParentChainBoundaryIds={90, 91, 92},
    )

    assert expanded["result"] == {90, 91, 92, 95}
    assert expanded["byRule"][RULE_ALL_OR_NOTHING] == [91]
    assert expanded["byRule"][RULE_PARENT_CHAIN] == [90]
    assert expanded["byRule"][RULE_PARENT_CONDITIONAL] == [95]


# --------------------------------------------------------------------------- #
#  1.10 입력 불변 / byRule 계약
# --------------------------------------------------------------------------- #


def test_input_sets_are_not_mutated():
    """입력 집합을 제자리에서 변경하지 않는다."""
    baseIds = {1}
    mandatoryIds = {10}
    conditionalIds = {30}
    boundaryIds = {1, 10}
    layerEntry = _make_all_or_nothing("AddOn_A", {1, 2})

    expand_node_set(
        inBaseIds=baseIds,
        inMandatoryIds=mandatoryIds,
        inAllOrNothingIdsByLayer=layerEntry,
        inParentConditionalIds=conditionalIds,
        inParentMap={10: 1, 30: 1, 2: None, 1: None},
        inParentChainBoundaryIds=boundaryIds,
    )

    assert baseIds == {1}
    assert mandatoryIds == {10}
    assert conditionalIds == {30}
    assert boundaryIds == {1, 10}
    assert layerEntry["AddOn_A"][TRIGGER_KEY] == {1, 2}
    assert layerEntry["AddOn_A"][ADD_KEY] == {1, 2}


def test_by_rule_always_has_all_four_keys():
    """byRule은 추가가 없어도 항상 4개 키를 갖는다."""
    expanded = expand_node_set(inBaseIds=set())

    assert set(expanded["byRule"].keys()) == set(ALL_RULE_KEYS)
    assert len(ALL_RULE_KEYS) == 4


def test_result_is_a_new_set_object():
    """반환 집합은 기준 집합과 다른 객체다(호출부가 원본을 계속 쓸 수 있어야 한다)."""
    baseIds = {1, 2}

    expanded = expand_node_set(inBaseIds=baseIds)

    assert expanded["result"] == baseIds
    assert expanded["result"] is not baseIds


def test_all_three_rules_fire_together():
    """규칙 3종 동시 발동. 각 규칙의 기여가 byRule에서 분리된다."""
    parentMap = {
        10: None,  # 규칙 1 대상
        21: 20,
        20: None,  # 규칙 2 레이어 (20이 기준에 있음)
        30: 20,  # 규칙 3 대상 (부모 20)
    }

    expanded = expand_node_set(
        inBaseIds={20},
        inMandatoryIds={10},
        inAllOrNothingIdsByLayer=_make_all_or_nothing("AddOn_A", {20, 21}),
        inParentConditionalIds={30},
        inParentMap=parentMap,
        inParentChainBoundaryIds={10, 20, 21, 30},
    )

    assert expanded["result"] == {10, 20, 21, 30}
    assert expanded["byRule"][RULE_MANDATORY] == [10]
    assert expanded["byRule"][RULE_ALL_OR_NOTHING] == [21]
    assert expanded["byRule"][RULE_PARENT_CONDITIONAL] == [30]
