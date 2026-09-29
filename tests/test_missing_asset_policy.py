#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`pyjallib.max.missingAssetPolicy` 순수 엔진 테스트 (Type A, mock 0개).

이 모듈은 pymxs에 의존하지 않으므로 콘솔 pytest로 **경우의 수를 전수** 덮는다.
DCC 안에서는 "지오메트리 판별에 실패한 노드" 같은 경우를 만드는 것 자체가 비싸거나
불가능하다.

**판별력을 함께 단정한다.** 통과만으로는 판별력이 없다 - 분류를 뒤집은 입력과 깨진
계획을 만들어, 이 테스트의 단정이 실제로 그것들을 잡아내는지까지 확인한다
(`testing/discriminating_power.md`).
"""

import pytest

from pyjallib.max.missingAssetPolicy import (
    ACTION_DELETE,
    ACTION_REPORT,
    ASSET_KIND_FILE,
    ASSET_KIND_PLUGIN,
    MAX_LISTED_NODES,
    REASON_GEOMETRY,
    REASON_UNKNOWN,
    build_plan_summary,
    build_purge_confirm_summary,
    build_purge_detail_text,
    build_purge_plan,
    normalize_slots,
    split_nodes_by_action,
    summarize_assets_by_kind,
)


def _node(inHandle, inName, inIsGeometry):
    """테스트용 노드 레코드를 만든다.

    Args:
        inHandle: 노드 핸들
        inName: 노드 이름
        inIsGeometry: 지오메트리 여부(True/False/None)

    Returns:
        dict: 노드 레코드
    """
    return {"handle": inHandle, "name": inName, "isGeometry": inIsGeometry}


def _asset(inKind, inPath, inNodes, inDetail=""):
    """테스트용 애셋 레코드를 만든다.

    Args:
        inKind: 애셋 종류
        inPath: 누락 경로
        inNodes: 노드 레코드 목록
        inDetail: 보조 설명

    Returns:
        dict: 애셋 레코드
    """
    return {"kind": inKind, "path": inPath, "detail": inDetail, "nodes": inNodes}


def _names(inNodes):
    """노드 목록에서 이름만 뽑는다.

    Args:
        inNodes: 노드 레코드 목록

    Returns:
        list[str]: 이름 목록
    """
    return [node["name"] for node in inNodes]


# ============================================================
# 안전 불변식 - 이 사이클의 핵심 축
# ============================================================


def assert_delete_list_is_safe(inPlan):
    """계획의 삭제 목록에 지오메트리·판별 불가 노드가 없음을 단정한다.

    이 사이클의 유일한 비가역 행동이 삭제이므로, 그 목록의 안전성을 한 함수로 모아
    모든 테스트가 같은 축을 쓰게 한다.

    Args:
        inPlan: :func:`build_purge_plan` 결과

    Raises:
        AssertionError: 삭제 목록에 비지오메트리가 아닌 노드가 있으면
    """
    for node in inPlan["deleteNodes"]:
        assert node["isGeometry"] is False, (
            f"삭제 목록에 비지오메트리가 아닌 노드가 있다: "
            f"{node['name']} (isGeometry={node['isGeometry']!r})"
        )
        assert node["action"] == ACTION_DELETE


# ============================================================
# 분류 전수 - 지오메트리 3상태 x 애셋 종류 2종
# ============================================================


@pytest.mark.parametrize("assetKind", [ASSET_KIND_FILE, ASSET_KIND_PLUGIN])
@pytest.mark.parametrize(
    "isGeometry, expectedAction, expectedReason",
    [
        (False, ACTION_DELETE, None),
        (True, ACTION_REPORT, REASON_GEOMETRY),
        (None, ACTION_REPORT, REASON_UNKNOWN),
    ],
)
def test_classification_matrix(assetKind, isGeometry, expectedAction, expectedReason):
    """지오메트리 3상태 x 애셋 종류 2종의 분류를 전수 확인한다."""
    plan = build_purge_plan(
        [_asset(assetKind, "X:/gone.png", [_node(1, "n1", isGeometry)])]
    )

    assert_delete_list_is_safe(plan)
    if expectedAction == ACTION_DELETE:
        assert _names(plan["deleteNodes"]) == ["n1"]
        assert plan["reportNodes"] == []
        assert plan["empty"] is False
    else:
        assert plan["deleteNodes"] == []
        assert _names(plan["reportNodes"]) == ["n1"]
        assert plan["reportNodes"][0]["reason"] == expectedReason
        assert plan["empty"] is True

    assert plan["hasFindings"] is True
    assert summarize_assets_by_kind(plan) == {assetKind: 1}


def test_unknown_geometry_goes_to_report_not_delete():
    """판별 불가는 **보고**로 간다 - 안전측 catch-all."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/gone.png", [_node(7, "unknownNode", None)])]
    )

    assert _names(plan["deleteNodes"]) == []
    assert _names(plan["reportNodes"]) == ["unknownNode"]
    assert plan["reportNodes"][0]["reason"] == REASON_UNKNOWN


@pytest.mark.parametrize("rawValue", ["false", 0, 1, "", [], "geometry"])
def test_non_bool_geometry_flag_is_treated_as_unknown(rawValue):
    """``bool``이 아닌 값은 전부 불명으로 떨어진다 - truthiness로 읽지 않는다.

    어댑터가 판별에 실패해 문자열이나 정수를 흘려도 그것이 삭제로 이어지지 않아야 한다.
    ``0``이 ``False``로 읽히면 지오메트리일 수도 있는 노드가 삭제된다.
    """
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/gone.png", [_node(1, "n1", rawValue)])]
    )

    assert_delete_list_is_safe(plan)
    assert plan["deleteNodes"] == []
    assert plan["reportNodes"][0]["reason"] == REASON_UNKNOWN
    assert plan["reportNodes"][0]["isGeometry"] is None


# ============================================================
# 중복 제거와 관측 충돌
# ============================================================


def test_same_node_across_assets_is_deduped_by_handle():
    """같은 노드가 여러 누락 애셋에 걸려도 계획에는 한 번만 나온다."""
    plan = build_purge_plan(
        [
            _asset(ASSET_KIND_FILE, "X:/a.png", [_node(11, "light", False)]),
            _asset(ASSET_KIND_FILE, "X:/b.png", [_node(11, "light", False)]),
            _asset(ASSET_KIND_PLUGIN, "", [_node(11, "light", False)]),
        ]
    )

    assert _names(plan["deleteNodes"]) == ["light"]
    assert len(plan["assets"]) == 3
    assert summarize_assets_by_kind(plan) == {ASSET_KIND_FILE: 2, ASSET_KIND_PLUGIN: 1}


def test_dedupe_uses_handle_not_name():
    """이름이 같아도 핸들이 다르면 다른 노드다 - 동명 노드가 실재한다."""
    plan = build_purge_plan(
        [
            _asset(
                ASSET_KIND_FILE,
                "X:/a.png",
                [_node(1, "Box001", False), _node(2, "Box001", False)],
            )
        ]
    )

    assert len(plan["deleteNodes"]) == 2
    assert [node["handle"] for node in plan["deleteNodes"]] == [1, 2]


def test_node_without_handle_falls_back_to_name():
    """핸들이 없으면 이름으로 묶는다(차선책이고, 그 사실이 동작으로 드러난다)."""
    plan = build_purge_plan(
        [
            _asset(
                ASSET_KIND_FILE, "X:/a.png", [{"name": "solo", "isGeometry": False}]
            ),
            _asset(
                ASSET_KIND_FILE, "X:/b.png", [{"name": "solo", "isGeometry": False}]
            ),
        ]
    )

    assert len(plan["deleteNodes"]) == 1


@pytest.mark.parametrize(
    "observations, expectedReason",
    [
        ([False, True], REASON_GEOMETRY),
        ([True, False], REASON_GEOMETRY),
        ([False, None], REASON_UNKNOWN),
        ([None, False], REASON_UNKNOWN),
        ([True, None], REASON_GEOMETRY),
        ([None, True], REASON_GEOMETRY),
    ],
)
def test_conflicting_observations_resolve_to_the_safe_side(
    observations, expectedReason
):
    """관측이 엇갈리면 **안전한 쪽이 이긴다** - 삭제는 전원 합의일 때만."""
    plan = build_purge_plan(
        [
            _asset(ASSET_KIND_FILE, f"X:/{index}.png", [_node(5, "conflicted", value)])
            for index, value in enumerate(observations)
        ]
    )

    assert_delete_list_is_safe(plan)
    assert plan["deleteNodes"] == []
    assert _names(plan["reportNodes"]) == ["conflicted"]
    assert plan["reportNodes"][0]["reason"] == expectedReason


def test_all_false_observations_still_delete():
    """모든 관측이 비지오메트리면 삭제한다 - 충돌 규칙이 정상 경로를 막지 않는다."""
    plan = build_purge_plan(
        [
            _asset(ASSET_KIND_FILE, "X:/a.png", [_node(5, "light", False)]),
            _asset(ASSET_KIND_FILE, "X:/b.png", [_node(5, "light", False)]),
        ]
    )

    assert _names(plan["deleteNodes"]) == ["light"]


# ============================================================
# 빈 계획과 empty / hasFindings의 축 분리
# ============================================================


@pytest.mark.parametrize(
    "records", [None, [], [_asset(ASSET_KIND_FILE, "X:/a.png", [])]]
)
def test_empty_plan(records):
    """누락이 없거나 의존 노드가 없으면 계획이 비어 있다."""
    plan = build_purge_plan(records)

    assert plan["deleteNodes"] == []
    assert plan["reportNodes"] == []
    assert plan["empty"] is True
    assert plan["hasFindings"] is False


def test_empty_is_the_delete_axis_not_the_findings_axis():
    """``empty``는 "적용할 일이 있는가"이고, 누락 유무는 ``hasFindings``가 말한다.

    지오메트리만 걸린 씬은 정리할 것이 없지만 보고할 것은 있다. 두 축을 합치면
    소비처가 "할 일 없음"과 "누락 없음"을 구분하지 못한다.
    """
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "mesh", True)])]
    )

    assert plan["empty"] is True
    assert plan["hasFindings"] is True


def test_idempotency_second_plan_has_nothing_to_delete():
    """삭제 후 재스캔에 해당하는 계획은 ``empty``가 ``True``다(멱등).

    비지오메트리가 사라진 뒤 남는 것은 지오메트리 보고뿐이고, 그것은 다시 지워지지
    않는다 - 두 번 실행해도 무해하다.
    """
    firstPlan = build_purge_plan(
        [
            _asset(
                ASSET_KIND_FILE,
                "X:/a.png",
                [_node(1, "light", False), _node(2, "mesh", True)],
            )
        ]
    )
    assert _names(firstPlan["deleteNodes"]) == ["light"]

    # 삭제가 반영된 뒤의 재스캔을 모사한다 - 지오메트리만 남는다.
    secondPlan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(2, "mesh", True)])]
    )

    assert secondPlan["empty"] is True
    assert secondPlan["deleteNodes"] == []
    assert _names(secondPlan["reportNodes"]) == ["mesh"]


def test_split_nodes_by_action_returns_copies():
    """접근자가 돌려준 목록을 고쳐도 계획이 바뀌지 않는다."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "light", False)])]
    )
    deleteNodes, reportNodes = split_nodes_by_action(plan)
    deleteNodes.clear()
    reportNodes.append({"name": "침입"})

    assert len(plan["deleteNodes"]) == 1
    assert plan["reportNodes"] == []


# ============================================================
# 요약 문구 - 나열 상한 경계
# ============================================================


@pytest.mark.parametrize(
    "count, expectFold",
    [
        (MAX_LISTED_NODES - 1, False),
        (MAX_LISTED_NODES, False),
        (MAX_LISTED_NODES + 1, True),
    ],
)
def test_summary_listing_cap_boundary(count, expectFold):
    """나열 상한 경계(-1 / 상한 / +1)에서 접힘이 정확히 한 번 일어난다."""
    nodes = [_node(index, f"light{index:03d}", False) for index in range(count)]
    plan = build_purge_plan([_asset(ASSET_KIND_FILE, "X:/a.png", nodes)])
    summary = build_plan_summary(plan)

    assert f"삭제 대상 비지오메트리 노드 {count}개" in summary
    if expectFold:
        assert f"및 {count - MAX_LISTED_NODES}개 더" in summary
        assert "light030" not in summary
    else:
        assert "개 더" not in summary
        assert f"light{count - 1:03d}" in summary


def test_summary_keeps_full_list_in_the_plan():
    """문구는 접혀도 **전체 목록은 계획 dict가 갖는다**."""
    nodes = [
        _node(index, f"light{index:03d}", False)
        for index in range(MAX_LISTED_NODES + 5)
    ]
    plan = build_purge_plan([_asset(ASSET_KIND_FILE, "X:/a.png", nodes)])

    assert len(plan["deleteNodes"]) == MAX_LISTED_NODES + 5
    assert "및 5개 더" in build_plan_summary(plan)


def test_summary_when_nothing_is_missing():
    """누락이 없으면 그 사실을 말한다."""
    assert build_plan_summary(build_purge_plan([])) == "누락된 애셋이 없습니다."


def test_summary_states_geometry_is_not_deleted():
    """지오메트리를 지우지 않는다는 사실이 문구에 드러난다.

    확인 다이얼로그에 그대로 실리는 문구이므로, 사용자가 "메쉬도 지워지나"를 묻지
    않아도 되게 자기완결형이어야 한다.
    """
    plan = build_purge_plan(
        [
            _asset(
                ASSET_KIND_FILE,
                "X:/a.png",
                [_node(1, "light", False), _node(2, "mesh", True)],
            )
        ]
    )
    summary = build_plan_summary(plan)

    assert "삭제하지 않고 보고만 합니다" in summary
    assert "mesh" in summary
    assert "light" in summary


def test_summary_reports_unknown_separately_from_geometry():
    """판별 불가는 지오메트리와 **별도 문장**으로 보고한다 - 원인이 다르다."""
    plan = build_purge_plan(
        [
            _asset(
                ASSET_KIND_FILE,
                "X:/a.png",
                [_node(1, "mesh", True), _node(2, "weird", None)],
            )
        ]
    )
    summary = build_plan_summary(plan)

    assert "지오메트리 노드 1개는 삭제하지 않고" in summary
    assert "판별하지 못한 노드 1개도" in summary


def test_summary_counts_both_asset_kinds():
    """요약에 애셋 종류별 건수가 함께 나온다."""
    plan = build_purge_plan(
        [
            _asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "light", False)]),
            _asset(ASSET_KIND_PLUGIN, "", [_node(2, "ghost", False)]),
        ]
    )
    summary = build_plan_summary(plan)

    assert "외부 파일 부재 1건" in summary
    assert "플러그인 미로드 1건" in summary


def test_unknown_asset_kind_is_preserved_not_coerced():
    """모르는 애셋 종류는 아는 값으로 바꾸지 않는다 - 진단 정보를 잃지 않는다."""
    plan = build_purge_plan(
        [_asset("photometric", "X:/a.ies", [_node(1, "light", False)])]
    )

    assert plan["assets"][0]["kind"] == "photometric"
    assert "photometric 1건" in build_plan_summary(plan)


# ============================================================
# 판별력 증명 - 단정이 실제로 잡아내는가
# ============================================================


def test_safety_invariant_rejects_a_broken_plan():
    """안전 불변식이 **깨진 계획을 실제로 잡아낸다**.

    통과만으로는 판별력이 없다. 지오메트리를 삭제 목록에 넣은 계획을 일부러 만들어
    :func:`assert_delete_list_is_safe`가 그것을 거부하는지 확인한다 - 이 단정이 없으면
    위 테스트들이 전부 공허할 수 있다.
    """
    brokenPlan = {
        "deleteNodes": [
            {"handle": 1, "name": "mesh", "isGeometry": True, "action": ACTION_DELETE}
        ],
        "reportNodes": [],
    }

    with pytest.raises(AssertionError, match="비지오메트리가 아닌 노드"):
        assert_delete_list_is_safe(brokenPlan)


def test_safety_invariant_rejects_unknown_in_delete_list():
    """판별 불가를 삭제로 보낸 계획도 불변식이 거부한다."""
    brokenPlan = {
        "deleteNodes": [
            {"handle": 1, "name": "weird", "isGeometry": None, "action": ACTION_DELETE}
        ],
        "reportNodes": [],
    }

    with pytest.raises(AssertionError):
        assert_delete_list_is_safe(brokenPlan)


def test_a_permissive_classifier_would_produce_a_plan_the_invariant_rejects():
    """ "불명도 지우는" 분류기가 만들었을 계획은 불변식에 걸린다.

    실제 구현을 고치지 않고도, 뒤집힌 분류가 **통과하지 못함**을 같은 입력으로 보인다.
    """
    nodes = [_node(1, "light", False), _node(2, "weird", None), _node(3, "mesh", True)]
    records = [_asset(ASSET_KIND_FILE, "X:/a.png", nodes)]

    realPlan = build_purge_plan(records)
    assert_delete_list_is_safe(realPlan)
    assert _names(realPlan["deleteNodes"]) == ["light"]

    # 관대한 분류기: 지오메트리로 **확정되지 않은** 것은 전부 삭제한다.
    permissiveDelete = [
        dict(node, action=ACTION_DELETE)
        for node in [dict(item) for item in nodes]
        if node["isGeometry"] is not True
    ]
    with pytest.raises(AssertionError):
        assert_delete_list_is_safe({"deleteNodes": permissiveDelete, "reportNodes": []})


def test_plan_does_not_mutate_input_records():
    """입력 레코드를 건드리지 않는다 - 호출부가 같은 재료를 재사용할 수 있다."""
    nodes = [_node(1, "light", False)]
    records = [_asset(ASSET_KIND_FILE, "X:/a.png", nodes)]
    build_purge_plan(records)

    assert nodes[0] == {"handle": 1, "name": "light", "isGeometry": False}
    assert "nodeKeys" not in records[0]


# ============================================================
# 슬롯 분리 축 - 실기 판정으로 추가된 축 (2026-09-29)
# ============================================================


def _slot(inOwnerHandle, inOwnerName, inSlotIndex, inSlotName, inPath="X:/gone.tga"):
    """테스트용 슬롯 레코드를 만든다.

    Args:
        inOwnerHandle: 매테리얼 핸들
        inOwnerName: 매테리얼 이름
        inSlotIndex: 슬롯 인덱스
        inSlotName: 슬롯 이름. DX9는 빈 문자열이 온다
        inPath: 깨진 텍스쳐 경로

    Returns:
        dict: 슬롯 레코드
    """
    return {
        "ownerHandle": inOwnerHandle,
        "ownerName": inOwnerName,
        "ownerClass": "Standardmaterial",
        "slotIndex": inSlotIndex,
        "slotName": inSlotName,
        "path": inPath,
        "nodeNames": [],
    }


def test_slot_records_land_in_detach_axis():
    """슬롯 레코드가 ``detachSlots``로 들어간다."""
    plan = build_purge_plan([], [_slot(10, "Face", 1, "Diffuse Color")])

    assert len(plan["detachSlots"]) == 1
    assert plan["detachSlots"][0]["ownerName"] == "Face"
    assert plan["detachSlots"][0]["slotIndex"] == 1
    assert plan["deleteNodes"] == []


def test_slot_axis_is_independent_of_node_axis():
    """슬롯과 노드는 **독립 축**이다.

    프로덕션 실측에서 행동 가능한 것은 거의 전부 슬롯 쪽이었다(13씬 삭제 대상 0건
    vs 1씬 깨진 슬롯 12건). 두 축을 합치면 "할 일 있음"이 어느 쪽인지 말할 수 없다.
    """
    slotOnly = build_purge_plan([], [_slot(10, "Face", 1, "Diffuse Color")])
    nodeOnly = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "light", False)])]
    )

    assert slotOnly["detachSlots"] and not slotOnly["deleteNodes"]
    assert nodeOnly["deleteNodes"] and not nodeOnly["detachSlots"]
    assert slotOnly["empty"] is False
    assert nodeOnly["empty"] is False


def test_empty_requires_both_axes_to_be_empty():
    """``empty``는 **두 축이 모두** 비었을 때만 ``True``다."""
    assert build_purge_plan([], []).get("empty") is True
    assert (
        build_purge_plan([], [_slot(10, "Face", 1, "Diffuse Color")])["empty"] is False
    )


def test_actionable_counts_only_what_can_be_fixed():
    """``actionable``은 **조치 가능한 것만** 센다 - 보고는 조치가 아니다.

    프로덕션 실측에서 누락 78건 중 72건(92%)이 어떤 객체도 참조하지 않는 레지스트리
    잔재였다. 그것까지 세면 사용자가 무엇을 할 수 있는지 알 수 없다.
    """
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "mesh", True)])],
        [_slot(10, "Face", 1, "Diffuse Color")],
    )

    assert plan["actionable"] == 1
    assert len(plan["reportNodes"]) == 1
    assert plan["hasFindings"] is True


def test_same_slot_is_deduped_by_owner_and_index():
    """같은 매테리얼의 같은 슬롯은 한 번만 뗀다."""
    plan = build_purge_plan(
        [],
        [
            _slot(10, "Face", 1, "Diffuse Color"),
            _slot(10, "Face", 1, "Diffuse Color"),
            _slot(10, "Face", 2, "Bump"),
            _slot(11, "Body", 1, "Diffuse Color"),
        ],
    )

    assert len(plan["detachSlots"]) == 3


def test_slot_dedupe_key_is_not_the_name():
    """중복 제거 키는 **이름이 아니라 인덱스**다.

    `DirectX_9_Shader`는 슬롯 이름이 빈 문자열이라(2026-09-29 실측) 이름으로 묶으면
    서로 다른 슬롯이 하나로 뭉개진다.
    """
    plan = build_purge_plan(
        [],
        [_slot(10, "Body", 1, ""), _slot(10, "Body", 2, ""), _slot(10, "Body", 3, "")],
    )

    assert len(plan["detachSlots"]) == 3


def test_empty_slot_name_falls_back_to_index():
    """슬롯 이름이 비면 인덱스로 부를 수 있는 표시 이름이 생긴다."""
    plan = build_purge_plan([], [_slot(10, "Body", 7, "")])

    assert plan["detachSlots"][0]["slotName"] == ""
    assert plan["detachSlots"][0]["displayName"] == "슬롯 7"


def test_named_slot_keeps_its_name():
    """이름이 있으면 그대로 쓴다."""
    plan = build_purge_plan([], [_slot(10, "Face", 1, "Diffuse Color")])

    assert plan["detachSlots"][0]["displayName"] == "Diffuse Color"


# ============================================================
# 슬롯 요약 문구
# ============================================================


def test_summary_leads_with_actionable_items():
    """요약은 **조치 가능한 것으로 시작**한다 - 총계를 앞세우면 노이즈가 가린다."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "mesh", True)])],
        [_slot(10, "Face", 1, "Diffuse Color")],
    )
    summary = build_plan_summary(plan)

    assert summary.startswith("정리할 수 있는 것:")
    assert "깨진 텍스쳐 슬롯 1개" in summary


def test_summary_states_material_and_mesh_are_kept():
    """슬롯만 뗀다는 사실이 문구에 드러난다 - 사용자가 되묻지 않게."""
    plan = build_purge_plan([], [_slot(10, "Face", 1, "Diffuse Color")])
    summary = build_plan_summary(plan)

    assert "매테리얼과 메쉬는 그대로 둡니다" in summary
    assert "Face.Diffuse Color" in summary


def test_summary_says_so_when_nothing_is_actionable():
    """조치할 것이 없으면 그 사실을 먼저 말한다."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "mesh", True)])]
    )
    summary = build_plan_summary(plan)

    assert summary.startswith("정리할 수 있는 것이 없습니다")


def test_summary_puts_scene_total_at_the_end():
    """씬 전체 누락 총계는 **맨 뒤 맥락**으로 간다."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "light", False)])],
        [_slot(10, "Face", 1, "Diffuse Color")],
    )
    summary = build_plan_summary(plan)

    assert summary.index("정리할 수 있는 것:") < summary.index(
        "참고 - 씬 전체 누락 애셋:"
    )


@pytest.mark.parametrize(
    "count, expectFold",
    [
        (MAX_LISTED_NODES - 1, False),
        (MAX_LISTED_NODES, False),
        (MAX_LISTED_NODES + 1, True),
    ],
)
def test_slot_listing_cap_boundary(count, expectFold):
    """슬롯 나열도 상한 경계에서 정확히 한 번 접힌다."""
    slots = [
        _slot(index, f"mat{index:03d}", 1, "Diffuse Color") for index in range(count)
    ]
    summary = build_plan_summary(build_purge_plan([], slots))

    assert f"텍스쳐 슬롯 {count}개를" in summary
    if expectFold:
        assert f"및 {count - MAX_LISTED_NODES}개 더" in summary


def test_plan_without_slot_records_stays_backward_compatible():
    """슬롯 인자를 주지 않으면 **기존 동작 그대로**다.

    Phase 2의 호출부가 무변경으로 통과해야 "축을 더한 것이지 바꾼 것이 아니다"가
    테스트로 증명된다.
    """
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "light", False)])]
    )

    assert plan["detachSlots"] == []
    assert _names(plan["deleteNodes"]) == ["light"]
    assert plan["empty"] is False


# ============================================================
# 확인 다이얼로그 문구 빌더
# ============================================================


def test_detail_text_separates_action_from_preservation():
    """상세 텍스트가 **조치와 보존을 구획으로 가른다**.

    섞어 놓으면 사용자가 "무엇이 지워지는가"를 목록에서 골라내야 한다.
    """
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "mesh", True)])],
        [_slot(10, "Face", 1, "Diffuse Color")],
    )
    detail = build_purge_detail_text(plan)

    assert "[정리] 매테리얼에서 떼어낼 텍스쳐 슬롯 - 1개" in detail
    assert "[보존] 건드리지 않는 메쉬 - 1개" in detail
    assert detail.index("[정리]") < detail.index("[보존]")


def test_detail_text_has_no_listing_cap():
    """상세 텍스트는 **상한 없이 전부** 나열한다 - 스크롤 영역이기 때문이다."""
    slots = [_slot(index, f"mat{index:03d}", 1, "Diffuse Color") for index in range(50)]
    detail = build_purge_detail_text(build_purge_plan([], slots))

    assert "mat049" in detail
    assert "개 더" not in detail


def test_detail_text_shows_the_missing_path_per_slot():
    """슬롯마다 **어떤 파일이 없는지**를 보여 준다."""
    plan = build_purge_plan(
        [], [_slot(10, "Face", 1, "Diffuse Color", "X:/gone/face.tga")]
    )
    detail = build_purge_detail_text(plan)

    assert "X:/gone/face.tga" in detail


def test_detail_text_marks_unactionable_assets():
    """조치할 수 없는 누락이 **몇 건인지 명시**한다.

    프로덕션 실측에서 92%가 그런 것이었다. 총계만 보여 주면 사용자는 정리가
    실패했다고 읽는다.
    """
    plan = build_purge_plan(
        [
            _asset(ASSET_KIND_FILE, "X:/a.png", []),
            _asset(ASSET_KIND_FILE, "X:/b.png", []),
            _asset(ASSET_KIND_FILE, "X:/c.png", [_node(1, "light", False)]),
        ]
    )
    detail = build_purge_detail_text(plan)

    assert "[참고] 씬 전체 누락 애셋 - 3건" in detail
    assert "2건은 씬의 어떤 객체도 참조하지 않아" in detail


def test_detail_text_when_nothing_is_missing():
    """누락이 없으면 그 사실만 말한다."""
    assert build_purge_detail_text(build_purge_plan([])) == "누락된 애셋이 없습니다."


def test_confirm_summary_states_what_will_happen():
    """상단 요약이 **무엇을 물어보는지**를 말한다."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "light", False)])],
        [_slot(10, "Face", 1, "Diffuse Color")],
    )
    summary = build_purge_confirm_summary(plan)

    assert "깨진 텍스쳐 슬롯 1개" in summary
    assert "잔재 노드 1개" in summary
    assert "메쉬와 매테리얼은 그대로 둡니다" in summary
    assert "진행하시겠습니까?" in summary
    # **취소가 무엇을 뜻하는지 적혀 있어야 한다.** 없으면 사용자가 "정리만 건너뛴다"로
    # 읽고 취소를 누른 뒤, 아무 일도 없는 것을 실패로 오해한다(2026-09-29 3차 지시).
    assert "작업을 중단합니다" in summary


def test_confirm_summary_when_nothing_is_actionable():
    """조치할 것이 없으면 묻지 않고 확인만 요청한다."""
    plan = build_purge_plan(
        [_asset(ASSET_KIND_FILE, "X:/a.png", [_node(1, "mesh", True)])]
    )

    assert "정리할 수 있는 것이 없습니다" in build_purge_confirm_summary(plan)


# ============================================================
# 계획을 거치지 않는 슬롯 정규화 (노드 범위 조회용)
# ============================================================


@pytest.mark.parametrize("slots", [None, [], ()])
def test_normalize_slots_on_nothing(slots):
    """빈 입력은 빈 목록이 된다."""
    assert normalize_slots(slots) == []


def test_normalize_slots_fills_display_name():
    """DX9의 빈 슬롯명에 인덱스 폴백이 붙는다."""
    normalized = normalize_slots([_slot(11, "Body", 2, "")])

    assert normalized[0]["displayName"] == "슬롯 2"


def test_normalize_slots_keeps_real_slot_name():
    """이름이 있으면 그대로 쓴다."""
    normalized = normalize_slots([_slot(11, "Body", 2, "Diffuse Color")])

    assert normalized[0]["displayName"] == "Diffuse Color"


def test_normalize_slots_dedupes_on_owner_and_index():
    """같은 매테리얼의 같은 슬롯은 한 번만 남는다."""
    normalized = normalize_slots(
        [_slot(11, "Body", 2, "Diffuse Color"), _slot(11, "Body", 2, "Diffuse Color")]
    )

    assert len(normalized) == 1


def test_normalize_slots_keeps_distinct_indices():
    """같은 매테리얼이어도 인덱스가 다르면 둘 다 남는다."""
    normalized = normalize_slots([_slot(11, "Body", 2, ""), _slot(11, "Body", 3, "")])

    assert [slot["displayName"] for slot in normalized] == ["슬롯 2", "슬롯 3"]


def test_normalize_slots_matches_plan_normalization():
    """계획이 만든 슬롯과 **같은 모양**이 나온다.

    두 경로의 정규화가 갈리면 같은 슬롯이 검사 버튼과 Pick에서 다른 이름으로 불린다.
    """
    slot = _slot(11, "Body", 2, "")
    fromPlan = build_purge_plan([], [slot])["detachSlots"][0]
    fromDirect = normalize_slots([slot])[0]

    assert fromPlan == fromDirect
