# -*- coding: utf-8 -*-
"""특성화 ② 파일 조작 - checkout/add/delete/move/revert 배치·단건 + 이어받기 헬퍼 (Phase 10.4)."""

from pathlib import Path

import pytest
from P4 import P4Exception

from conftest import assert_single_connection

CL = 4242
A = r"D:\ws\proj\A.uasset"
B = r"D:\ws\proj\B.uasset"
DEPOT_A = "//depot/proj/A.uasset"
DEPOT_B = "//depot/proj/B.uasset"


def n(inPath):
    return str(Path(inPath).resolve())


def where(inDepot, inLocal):
    return {"depotFile": inDepot, "clientFile": "//ws" + inDepot[7:], "path": n(inLocal)}


def opened(inDepot, inChange, inAction="edit"):
    return {"depotFile": inDepot, "clientFile": "//ws" + inDepot[7:], "change": str(inChange), "action": inAction}


NOT_OPENED = P4Exception("file(s) not opened on this client.")


# ============================================================================ 입력 가드 (공통)
@pytest.mark.parametrize("method", ["checkout_files", "add_files", "delete_files"])
def test_batch_methods_reject_non_list_and_return_false_on_empty(env, method):
    wrap = env.wrap()
    with pytest.raises(ValueError):
        getattr(wrap, method)("not-a-list", CL)
    assert getattr(wrap, method)([], CL) is False
    assert env.instances == []  # 서버를 건드리지 않는다


# ============================================================================ checkout_files
class TestCheckoutFiles:
    def test_unopened_files_are_edited(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().checkout_files([A, B], CL) is True
        assert env.runs() == [("opened", n(A), n(B)), ("edit", "-c", str(CL), n(A), n(B))]
        assert_single_connection(env)

    def test_file_in_other_changelist_is_reopened_and_not_edited(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, 99)])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.script.on("opened", "-c", "99", result=[])
        assert env.wrap().checkout_files([A], CL) is True
        assert env.runs("reopen") == [("reopen", "-c", str(CL), DEPOT_A)]
        assert env.runs("edit") == []
        assert env.runs("change") == [("change", "-d", "99")]  # 비게 된 원본 CL 정리

    def test_file_already_in_target_changelist_skips_reopen_and_edit(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL)])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().checkout_files([A], CL)
        assert env.runs("reopen") == [] and env.runs("edit") == []

    def test_delete_opened_file_is_reverted_k_then_edited(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL, "delete")])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().checkout_files([A], CL)
        assert env.runs("revert") == [("revert", "-k", n(A))]
        assert env.runs("edit") == [("edit", "-c", str(CL), n(A))]

    def test_mixed_opened_and_unopened(self, env):
        env.script.on("opened", n(A), n(B), result=[opened(DEPOT_A, CL)])
        env.script.on("where", result=[where(DEPOT_A, A), where(DEPOT_B, B)])
        env.wrap().checkout_files([A, B], CL)
        assert env.runs("edit") == [("edit", "-c", str(CL), n(B))]

    def test_edit_failure_propagates(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        env.script.on("edit", raises=P4Exception("locked"))
        with pytest.raises(P4Exception):
            env.wrap().checkout_files([A], CL)
        assert env.events()[-1] == "disconnect"


# ============================================================================ add_files
class TestAddFiles:
    def test_unopened_files_are_added(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().add_files([A, B], CL) is True
        assert env.runs() == [("opened", n(A), n(B)), ("add", "-c", str(CL), n(A), n(B))]
        assert_single_connection(env)

    def test_already_opened_for_add_or_edit_is_not_added_again(self, env):
        env.script.on("opened", n(A), n(B), result=[opened(DEPOT_A, CL, "add"), opened(DEPOT_B, CL, "edit")])
        env.script.on("where", result=[where(DEPOT_A, A), where(DEPOT_B, B)])
        env.wrap().add_files([A, B], CL)
        assert env.runs("add") == []

    def test_opened_with_other_action_is_skipped(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL, "delete")])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().add_files([A], CL)
        assert env.runs("add") == [] and env.runs("revert") == []

    def test_opened_in_other_changelist_is_taken_over(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, "default", "add")])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().add_files([A], CL)
        assert env.runs("reopen") == [("reopen", "-c", str(CL), DEPOT_A)]
        assert env.runs("change") == []  # default 는 정리 대상이 아니다


# ============================================================================ delete_files
class TestDeleteFiles:
    def test_unopened_files_are_deleted(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().delete_files([A], CL) is True
        assert env.runs() == [("opened", n(A)), ("delete", "-c", str(CL), n(A))]

    def test_already_deleted_is_left_alone(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL, "delete")])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().delete_files([A], CL)
        assert env.runs("delete") == [] and env.runs("revert") == []

    def test_opened_for_add_is_reverted_k_and_not_deleted(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL, "add")])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().delete_files([A], CL)
        assert env.runs("revert") == [("revert", "-k", n(A))] and env.runs("delete") == []

    def test_opened_for_edit_is_reverted_k_then_deleted(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL, "edit")])
        env.script.on("where", result=[where(DEPOT_A, A)])
        env.wrap().delete_files([A], CL)
        assert env.runs("revert") == [("revert", "-k", n(A))]
        assert env.runs("delete") == [("delete", "-c", str(CL), n(A))]


# ============================================================================ move_files
class TestMoveFiles:
    def test_rejects_non_list_and_empty(self, env):
        wrap = env.wrap()
        with pytest.raises(ValueError):
            wrap.move_files("x", CL)
        assert wrap.move_files([], CL) is False
        assert env.instances == []

    def test_edit_then_move_per_pair(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        target = r"D:\ws\proj\A2.uasset"
        assert env.wrap().move_files([(A, target)], CL) is True
        assert env.runs() == [
            ("opened", n(A)),
            ("edit", "-c", str(CL), n(A)),
            ("move", "-c", str(CL), n(A), n(target)),
        ]
        assert_single_connection(env)

    def test_already_opened_source_skips_edit(self, env):
        env.script.on("opened", n(A), result=[opened(DEPOT_A, CL)])
        env.script.on("where", result=[where(DEPOT_A, A)])
        target = r"D:\ws\proj\A2.uasset"
        env.wrap().move_files([(A, target)], CL)
        assert env.runs("edit") == []
        assert env.runs("move") == [("move", "-c", str(CL), n(A), n(target))]


# ============================================================================ revert_files + 단건 위임
class TestRevertFiles:
    def test_specific_files(self, env):
        assert env.wrap().revert_files(CL, [A, B]) is True
        assert env.runs() == [("revert", "-c", str(CL), n(A), n(B))]
        assert_single_connection(env)

    def test_all_files_when_none(self, env):
        env.wrap().revert_files(CL)
        assert env.runs() == [("revert", "-c", str(CL), "//...")]

    def test_empty_list_means_all(self, env):
        env.wrap().revert_files(CL, [])
        assert env.runs() == [("revert", "-c", str(CL), "//...")]

    def test_non_list_raises_value_error_after_connect(self, env):
        with pytest.raises(ValueError):
            env.wrap().revert_files(CL, "x")
        assert env.events() == ["connect", "disconnect"]


class TestSingleFileDelegation:
    def test_checkout_file(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().checkout_file(A, CL) is True
        assert env.runs("edit") == [("edit", "-c", str(CL), n(A))]

    def test_add_file(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().add_file(A, CL) is True
        assert env.runs("add") == [("add", "-c", str(CL), n(A))]

    def test_delete_file(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().delete_file(A, CL) is True
        assert env.runs("delete") == [("delete", "-c", str(CL), n(A))]

    def test_revert_file(self, env):
        assert env.wrap().revert_file(A, CL) is True
        assert env.runs() == [("revert", "-c", str(CL), n(A))]


# ============================================================================ 이어받기 헬퍼
class TestTakeoverHelpers:
    def test_comparable_path_normalizes_separator_and_case(self):
        from pyjallib.perforce import Perforce

        assert Perforce._comparable_path(r"D:\WS\Proj\A.uasset") == "d:/ws/proj/a.uasset"

    def test_map_depot_to_local_skips_unmapped(self, env):
        env.script.on("where", result=[where(DEPOT_A, A), {"depotFile": DEPOT_B, "unmap": "", "path": "x"}, "junk"])
        p4 = env.factory()
        assert env.wrap()._map_depot_to_local(p4, [n(A), n(B)]) == {DEPOT_A: n(A)}

    def test_map_depot_to_local_failure_is_empty(self, env):
        env.script.on("where", raises=P4Exception("x"))
        assert env.wrap()._map_depot_to_local(env.factory(), [n(A)]) == {}

    def test_takeover_not_opened_returns_empty(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap()._takeover_opened_files(env.factory(), [n(A)], CL) == {}

    def test_takeover_unexpected_error_propagates(self, env):
        env.script.on("opened", raises=P4Exception("connection lost"))
        with pytest.raises(P4Exception):
            env.wrap()._takeover_opened_files(env.factory(), [n(A)], CL)

    def test_takeover_reopens_and_cleans_emptied_source(self, env):
        env.script.on("opened", n(A), n(B), result=[opened(DEPOT_A, 77), opened(DEPOT_B, CL)])
        env.script.on("where", result=[where(DEPOT_A, A), where(DEPOT_B, B)])
        env.script.on("opened", "-c", "77", result=[])
        p4 = env.factory()
        actions = env.wrap()._takeover_opened_files(p4, [n(A), n(B)], CL)
        assert actions == {n(A).replace("\\", "/").lower(): "edit", n(B).replace("\\", "/").lower(): "edit"}
        assert env.runs("reopen") == [("reopen", "-c", str(CL), DEPOT_A)]
        assert env.runs("change") == [("change", "-d", "77")]

    def test_delete_emptied_changelists_keeps_nonempty_and_swallows_errors(self, env):
        env.script.on("opened", "-c", "1", result=[{"depotFile": "//d/x"}])
        env.script.on("opened", "-c", "2", result=[])
        env.script.on("opened", "-c", "3", raises=P4Exception("x"))
        env.wrap()._delete_emptied_changelists(env.factory(), ["1", "2", "3"])
        assert env.runs("change") == [("change", "-d", "2")]
