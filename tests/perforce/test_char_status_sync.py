# -*- coding: utf-8 -*-
"""특성화 ② 파일 상태 조회 8종 + 싱크 2종 (Phase 10.4)."""

from pathlib import Path

import pytest
from P4 import P4Exception

from conftest import USER, WORKSPACE, assert_single_connection

CL = 4242
A = r"D:\ws\proj\A.uasset"
B = r"D:\ws\proj\B.uasset"
DEPOT_A = "//depot/proj/A.uasset"
DEPOT_B = "//depot/proj/B.uasset"
NOT_OPENED = P4Exception("file(s) not opened on this client.")


def n(inPath):
    return str(Path(inPath).resolve())


def where(inDepot, inLocal):
    return {"depotFile": inDepot, "clientFile": "//ws" + inDepot[7:], "path": n(inLocal)}


def opened_all(inDepot, inUser, inClient):
    return {"depotFile": inDepot, "clientFile": f"//{inClient}" + inDepot[7:], "user": inUser, "client": inClient, "action": "edit"}


# ============================================================================ is_file_checked_out
class TestIsFileCheckedOut:
    def test_true_when_opened(self, env):
        env.script.on("opened", n(A), result=[{"depotFile": DEPOT_A}])
        assert env.wrap().is_file_checked_out(A) is True
        assert env.runs() == [("opened", n(A))]
        assert_single_connection(env)

    def test_false_when_empty_or_error(self, env):
        env.script.on("opened", n(A), result=[])
        assert env.wrap().is_file_checked_out(A) is False
        env.script.on("opened", n(B), raises=NOT_OPENED)
        assert env.wrap().is_file_checked_out(B) is False


# ============================================================================ check_files_checked_out
class TestCheckFilesCheckedOut:
    def test_non_list_raises_before_connect(self, env):
        with pytest.raises(ValueError):
            env.wrap().check_files_checked_out("x")
        assert env.instances == []

    def test_maps_depot_to_local_and_marks(self, env):
        env.script.on("opened", n(A), n(B), result=[{"depotFile": DEPOT_A, "clientFile": "//ws/proj/A.uasset"}])
        env.script.on("where", result=[where(DEPOT_A, A), where(DEPOT_B, B)])
        result = env.wrap().check_files_checked_out([A, B])
        assert result == {n(A): True, n(B): False}
        assert env.runs() == [("opened", n(A), n(B)), ("where", n(A), n(B))]

    def test_none_opened_all_false_without_where(self, env):
        env.script.on("opened", raises=NOT_OPENED)
        assert env.wrap().check_files_checked_out([A]) == {n(A): False}
        assert env.runs("where") == []

    def test_unmapped_depot_file_is_excluded(self, env):
        env.script.on("opened", result=[{"depotFile": DEPOT_A}])
        env.script.on("where", result=[])
        assert env.wrap().check_files_checked_out([A]) == {n(A): False}

    def test_where_failure_propagates(self, env):
        """where 실패는 `_map_depot_to_local`이 삼켜 빈 매핑 → 전부 False."""
        env.script.on("opened", result=[{"depotFile": DEPOT_A}])
        env.script.on("where", raises=P4Exception("x"))
        assert env.wrap().check_files_checked_out([A]) == {n(A): False}


# ============================================================================ is_file_checked_out_by_others
class TestIsFileCheckedOutByOthers:
    def test_other_client_is_true(self, env):
        env.script.on("opened", "-a", n(A), result=[opened_all(DEPOT_A, "Other", "otherws")])
        assert env.wrap().is_file_checked_out_by_others(A) is True
        assert env.runs() == [("opened", "-a", n(A))]

    def test_same_client_same_user_is_false(self, env):
        env.script.on("opened", "-a", n(A), result=[opened_all(DEPOT_A, USER, WORKSPACE)])
        assert env.wrap().is_file_checked_out_by_others(A) is False

    def test_same_client_other_user_is_true(self, env):
        env.script.on("opened", "-a", n(A), result=[opened_all(DEPOT_A, "Other", WORKSPACE)])
        assert env.wrap().is_file_checked_out_by_others(A) is True

    def test_error_or_empty_is_false(self, env):
        env.script.on("opened", "-a", n(A), raises=NOT_OPENED)
        assert env.wrap().is_file_checked_out_by_others(A) is False
        env.script.on("opened", "-a", n(B), result=[])
        assert env.wrap().is_file_checked_out_by_others(B) is False


# ============================================================================ check_files_checked_out_all_users + 파생 2종
class TestCheckFilesCheckedOutAllUsers:
    def _script(self, env):
        env.script.on("where", n(A), result=[where(DEPOT_A, A)])
        env.script.on("where", n(B), result=[where(DEPOT_B, B)])
        env.script.on("opened", "-a", result=[opened_all(DEPOT_A, "Other", "otherws"), opened_all(DEPOT_B, USER, WORKSPACE)])

    def test_non_list_raises(self, env):
        with pytest.raises(ValueError):
            env.wrap().check_files_checked_out_all_users("x")

    def test_per_file_status(self, env):
        self._script(env)
        result = env.wrap().check_files_checked_out_all_users([A, B])
        assert result[n(A)] == {"checked_out": True, "by_current_user": False, "by_others": True, "user": "Other", "client": "otherws"}
        assert result[n(B)] == {"checked_out": True, "by_current_user": True, "by_others": False, "user": USER, "client": WORKSPACE}
        assert env.runs() == [("where", n(A)), ("where", n(B)), ("opened", "-a", n(A), n(B))]
        assert_single_connection(env)

    def test_unopened_and_where_failure_default_false(self, env):
        env.script.on("where", n(A), raises=P4Exception("not in client view"))
        env.script.on("opened", "-a", raises=NOT_OPENED)
        result = env.wrap().check_files_checked_out_all_users([A])
        assert result == {n(A): {"checked_out": False, "by_current_user": False, "by_others": False, "user": None, "client": None}}

    def test_same_client_other_user_is_by_others(self, env):
        env.script.on("where", n(A), result=[where(DEPOT_A, A)])
        env.script.on("opened", "-a", result=[opened_all(DEPOT_A, "Other", WORKSPACE)])
        result = env.wrap().check_files_checked_out_all_users([A])
        assert result[n(A)]["by_others"] is True and result[n(A)]["by_current_user"] is False

    def test_get_file_checkout_info_all_users(self, env):
        self._script(env)
        info = env.wrap().get_file_checkout_info_all_users(A)
        assert info["by_others"] is True and info["client"] == "otherws"

    def test_get_files_checked_out_by_others(self, env):
        self._script(env)
        assert env.wrap().get_files_checked_out_by_others([A, B]) == [{"path": n(A), "user": "Other", "client": "otherws"}]


# ============================================================================ is_file_in_pending_changelist / is_file_in_perforce
class TestMembershipAndExistence:
    def test_in_pending_changelist(self, env):
        env.script.on("opened", "-c", str(CL), n(A), result=[{"depotFile": DEPOT_A}])
        assert env.wrap().is_file_in_pending_changelist(A, CL) is True
        assert env.runs() == [("opened", "-c", str(CL), n(A))]
        env.script.on("opened", "-c", str(CL), n(B), raises=NOT_OPENED)
        assert env.wrap().is_file_in_pending_changelist(B, CL) is False

    def test_is_file_in_perforce(self, env):
        env.script.on("files", n(A), result=[{"depotFile": DEPOT_A}])
        env.script.on("files", n(B), raises=P4Exception("no such file"))
        wrap = env.wrap()
        assert wrap.is_file_in_perforce(A) is True
        assert wrap.is_file_in_perforce(B) is False
        assert env.runs() == [("files", n(A)), ("files", n(B))]


# ============================================================================ 싱크
class TestSync:
    def test_check_update_required(self, env):
        env.script.on("sync", "-n", result=[{"depotFile": DEPOT_A}])
        assert env.wrap().check_update_required([A, B]) is True
        assert env.runs() == [("sync", "-n", n(A), n(B))]
        assert_single_connection(env)

    def test_check_update_not_required(self, env):
        env.script.on("sync", "-n", result=[])
        assert env.wrap().check_update_required([A]) is False

    def test_check_update_failure_propagates_and_non_list_rejected(self, env):
        with pytest.raises(ValueError):
            env.wrap().check_update_required("x")
        env.script.on("sync", "-n", raises=P4Exception("x"))
        with pytest.raises(P4Exception):
            env.wrap().check_update_required([A])

    def test_sync_files(self, env):
        assert env.wrap().sync_files([A, B]) is True
        assert env.runs() == [("sync", n(A), n(B))]
        assert_single_connection(env)

    def test_sync_files_guards(self, env):
        with pytest.raises(ValueError):
            env.wrap().sync_files("x")
        env.script.on("sync", raises=P4Exception("x"))
        with pytest.raises(P4Exception):
            env.wrap().sync_files([A])
