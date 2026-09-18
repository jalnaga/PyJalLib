# -*- coding: utf-8 -*-
"""특성화 ① 연결·정규화·체인지리스트 CRUD·조회 (ExportToolsRefactor Phase 10.3).

각 메서드의 `p4.run` 인자 시퀀스·연결 수명·반환 형태를 **현행 동작 그대로** 고정한다.
서브패키지 분해(10.6~10.11)의 유일한 회귀 판정이므로 기대값은 분해 전 코드에서 초록인 값이다.
"""

from pathlib import Path

import pytest
from P4 import P4Exception

from conftest import PORT, USER, WORKSPACE, assert_single_connection
from pyjallib.perforce import Perforce

CL = 4242
A = r"D:\ws\proj\A.uasset"
B = r"D:\ws\proj\B.uasset"


# ============================================================================ 생성자·연결
class TestInitAndConnect:
    def test_init_defaults(self):
        wrap = Perforce(PORT, USER)
        assert (wrap.port, wrap.user, wrap.workspace_name, wrap.workspaceRoot, wrap.charset, wrap.exception_level) == (
            PORT, USER, None, None, "utf8", 1,
        )

    def test_connect_reads_client_root_and_disconnects(self, env):
        env.script.on("client", "-o", result=[{"Client": WORKSPACE, "Root": r"D:\ws"}])
        wrap = Perforce(PORT, USER)
        assert wrap.connect(WORKSPACE) is True
        assert wrap.workspace_name == WORKSPACE and wrap.workspaceRoot == r"D:\ws"
        assert env.runs() == [("client", "-o", WORKSPACE)]
        assert_single_connection(env)

    def test_connect_failure_propagates_and_disconnects(self, env):
        env.script.on("client", raises=P4Exception("no such client"))
        wrap = Perforce(PORT, USER)
        with pytest.raises(P4Exception):
            wrap.connect(WORKSPACE)
        assert wrap.workspace_name == WORKSPACE and wrap.workspaceRoot is None
        assert env.events()[-1] == "disconnect"

    def test_connect_missing_root_key_is_empty_string(self, env):
        env.script.on("client", "-o", result=[{"Client": WORKSPACE}])
        wrap = Perforce(PORT, USER)
        wrap.connect(WORKSPACE)
        assert wrap.workspaceRoot == ""

    def test_disconnect_resets_state_and_touches_server(self, env):
        wrap = env.wrap()
        wrap.workspaceRoot = r"D:\ws"
        wrap.disconnect()
        assert wrap.workspace_name is None and wrap.workspaceRoot is None
        assert env.events() == ["connect", "disconnect"]
        assert env.instances[0].client == WORKSPACE

    def test_disconnect_swallows_connection_error(self, env):
        wrap = env.wrap()

        def _boom():
            raise P4Exception("down")

        originalFactory = env.factory

        def _factory(*a, **k):
            p4 = originalFactory()
            p4.connect = _boom
            return p4

        import pyjallib.perforce as pkg

        pkg.P4 = _factory
        wrap.disconnect()  # 예외 없음
        assert wrap.workspace_name is None


# ============================================================================ 경로 정규화
class TestNormalize:
    def test_normalize_path_resolves_to_absolute(self):
        wrap = Perforce(PORT, USER)
        assert wrap._normalize_path(A) == str(Path(A).resolve())
        assert wrap._normalize_path(Path(A)) == str(Path(A).resolve())

    def test_normalize_paths_accepts_scalar_and_list(self):
        wrap = Perforce(PORT, USER)
        assert wrap._normalize_paths(A) == [str(Path(A).resolve())]
        assert wrap._normalize_paths([A, Path(B)]) == [str(Path(A).resolve()), str(Path(B).resolve())]
        assert wrap._normalize_paths([]) == []


# ============================================================================ CL 생성
class TestCreateChangeList:
    def test_sequence_and_return_shape(self, env):
        env.script.on("change", "-o", result=[{"Change": "new", "Description": "<enter>", "Files": ["//depot/x"]}])
        env.script.saveChangeResult = [f"Change {CL} created."]
        env.script.fetchChangeResult = {"Description": " my desc \n", "Status": "pending", "User": USER, "Client": WORKSPACE}
        result = env.wrap().create_change_list("my desc")
        assert result == {"id": CL, "description": "my desc", "status": "pending", "user": USER, "client": WORKSPACE}
        assert env.events() == ["connect", "run:change", "save_change", "fetch_change", "disconnect"]
        savedSpec = env.log[2][1]
        assert savedSpec["Description"] == "my desc" and "Files" not in savedSpec
        assert env.log[3] == ("fetch_change", CL)
        assert_single_connection(env)

    def test_returns_id_key_only_not_change_key(self, env):
        """소비처 규약(`{"id": N}` 또는 `{"change": N}` 둘 다 확인)의 현행 답은 `id`다."""
        env.script.on("change", "-o", result=[{"Change": "new"}])
        result = env.wrap().create_change_list("d")
        assert "id" in result and "change" not in result

    def test_failure_propagates_after_disconnect(self, env):
        env.script.on("change", "-o", raises=P4Exception("denied"))
        with pytest.raises(P4Exception):
            env.wrap().create_change_list("d")
        assert env.events()[-1] == "disconnect"


# ============================================================================ CL 삭제·리버트
class TestDeleteAndRevertChangeList:
    def test_delete_reverts_then_deletes(self, env):
        assert env.wrap().delete_change_list(CL) is True
        assert env.runs() == [("revert", "-c", str(CL), "//..."), ("change", "-d", str(CL))]
        assert_single_connection(env)

    def test_delete_ignores_revert_error(self, env):
        env.script.on("revert", raises=P4Exception("nothing to revert"))
        assert env.wrap().delete_change_list(CL) is True
        assert env.runs("change") == [("change", "-d", str(CL))]

    def test_delete_failure_propagates(self, env):
        env.script.on("change", "-d", raises=P4Exception("has shelved"))
        with pytest.raises(P4Exception):
            env.wrap().delete_change_list(CL)

    def test_revert_change_list_same_sequence(self, env):
        assert env.wrap().revert_change_list(CL) is True
        assert env.runs() == [("revert", "-c", str(CL), "//..."), ("change", "-d", str(CL))]

    def test_revert_change_list_ignores_revert_error_but_not_delete_error(self, env):
        env.script.on("revert", raises=P4Exception("x"))
        env.script.on("change", "-d", raises=P4Exception("y"))
        with pytest.raises(P4Exception):
            env.wrap().revert_change_list(CL)


class TestDeleteEmptyChangeList:
    def test_deletes_only_empty_pending_changelists(self, env):
        env.script.on("changes", result=[{"change": "10"}, {"change": "11"}, {"change": "0"}, {"change": "12"}])
        env.script.on("opened", "-c", "10", result=[{"depotFile": "//d/a"}])
        env.script.on("opened", "-c", "11", raises=P4Exception("not opened"))
        env.script.on("opened", "-c", "12", result=[])
        deleted = env.wrap().delete_empty_change_list()
        assert deleted == [11, 12]
        assert env.runs("changes") == [("changes", "-s", "pending", "-u", USER, "-c", WORKSPACE)]
        assert env.runs("change") == [("change", "-d", "11"), ("change", "-d", "12")]
        assert_single_connection(env)

    def test_delete_failure_of_one_is_skipped(self, env):
        env.script.on("changes", result=[{"change": "11"}, {"change": "12"}])
        env.script.on("change", "-d", "11", raises=P4Exception("shelved"))
        assert env.wrap().delete_empty_change_list() == [12]

    def test_changes_failure_propagates(self, env):
        env.script.on("changes", raises=P4Exception("down"))
        with pytest.raises(P4Exception):
            env.wrap().delete_empty_change_list()


# ============================================================================ 제출
class TestSubmitChangeList:
    def test_default_reverts_unchanged_then_submits(self, env):
        env.script.on("opened", "-c", str(CL), result=[{"depotFile": "//d/a"}])
        assert env.wrap().submit_change_list(CL) is True
        assert env.runs() == [
            ("revert", "-a", "-c", str(CL)),
            ("opened", "-c", str(CL)),
            ("submit", "-c", str(CL)),
        ]
        assert_single_connection(env)

    def test_auto_revert_false_skips_revert(self, env):
        env.script.on("opened", "-c", str(CL), result=[{"depotFile": "//d/a"}])
        assert env.wrap().submit_change_list(CL, auto_revert_unchanged=False) is True
        assert env.runs() == [("opened", "-c", str(CL)), ("submit", "-c", str(CL))]

    def test_empty_after_revert_deletes_and_returns_false(self, env):
        env.script.on("opened", "-c", str(CL), result=[])
        assert env.wrap().submit_change_list(CL) is False
        assert env.runs("change") == [("change", "-d", str(CL))]
        assert env.runs("submit") == []

    def test_revert_error_is_ignored(self, env):
        env.script.on("revert", raises=P4Exception("no files"))
        env.script.on("opened", "-c", str(CL), result=[{"depotFile": "//d/a"}])
        assert env.wrap().submit_change_list(CL) is True

    def test_submit_failure_propagates(self, env):
        env.script.on("opened", "-c", str(CL), result=[{"depotFile": "//d/a"}])
        env.script.on("submit", raises=P4Exception("conflict"))
        with pytest.raises(P4Exception):
            env.wrap().submit_change_list(CL)
        assert env.events()[-1] == "disconnect"


# ============================================================================ 수정
class TestEditChangeList:
    def test_description_only(self, env):
        env.script.fetchChangeResult = {"Description": "old", "Status": "pending", "User": USER, "Client": WORKSPACE}
        result = env.wrap().edit_change_list(CL, description="new")
        assert env.events() == ["connect", "fetch_change", "save_change", "fetch_change", "disconnect"]
        assert env.log[2][1]["Description"] == "new"
        assert result["id"] == CL and result["description"] == "old"  # 반환은 두 번째 fetch 결과(대역은 고정값)
        assert env.runs() == []

    def test_add_and_remove_files_reopen(self, env):
        env.wrap().edit_change_list(CL, add_file_paths=[A], remove_file_paths=[B])
        nA, nB = str(Path(A).resolve()), str(Path(B).resolve())
        assert env.runs() == [("reopen", "-c", str(CL), nA), ("reopen", "-c", "default", nB)]
        assert env.events().count("save_change") == 0
        assert env.events().count("fetch_change") == 1  # 마지막 정보 조회만

    def test_no_changes_still_fetches_info(self, env):
        result = env.wrap().edit_change_list(CL)
        assert env.events() == ["connect", "fetch_change", "disconnect"]
        assert set(result) == {"id", "description", "status", "user", "client"}

    def test_failure_propagates(self, env):
        env.script.on("reopen", raises=P4Exception("bad"))
        with pytest.raises(P4Exception):
            env.wrap().edit_change_list(CL, add_file_paths=[A])


# ============================================================================ 조회 5종
class TestQueries:
    CHANGES = [
        {"change": "10", "desc": " first \n", "status": "pending", "user": USER, "client": WORKSPACE},
        {"change": "11", "desc": "second", "status": "pending", "user": USER, "client": WORKSPACE},
        {"change": "12", "desc": "first-ish", "status": "pending", "user": USER, "client": WORKSPACE},
    ]

    def test_get_pending_change_list(self, env):
        env.script.on("changes", result=self.CHANGES)
        result = env.wrap().get_pending_change_list()
        assert env.runs() == [("changes", "-l", "-s", "pending", "-u", USER, "-c", WORKSPACE)]
        assert [r["id"] for r in result] == [10, 11, 12]
        assert result[0] == {"id": 10, "description": "first", "status": "pending", "user": USER, "client": WORKSPACE}
        assert_single_connection(env)

    def test_get_pending_change_list_failure_propagates(self, env):
        env.script.on("changes", raises=P4Exception("down"))
        with pytest.raises(P4Exception):
            env.wrap().get_pending_change_list()

    def test_get_change_list_by_number(self, env):
        env.script.fetchChangeResult = {"Description": " d \n", "Status": "pending", "User": USER, "Client": WORKSPACE}
        result = env.wrap().get_change_list_by_number(CL)
        assert env.events() == ["connect", "fetch_change", "disconnect"]
        assert result == {"id": CL, "description": "d", "status": "pending", "user": USER, "client": WORKSPACE}

    def test_get_change_list_by_number_failure_propagates(self, env):
        env.script.fetchChangeResult = P4Exception("no such change")
        with pytest.raises(P4Exception):
            env.wrap().get_change_list_by_number(CL)

    def test_get_change_list_by_description_exact_first_match(self, env):
        env.script.on("changes", result=self.CHANGES)
        assert env.wrap().get_change_list_by_description("first")["id"] == 10
        assert env.wrap().get_change_list_by_description("nope") == {}

    def test_get_change_list_by_description_pattern(self, env):
        env.script.on("changes", result=self.CHANGES)
        wrap = env.wrap()
        assert [r["id"] for r in wrap.get_change_list_by_description_pattern("first")] == [10, 12]
        assert [r["id"] for r in wrap.get_change_list_by_description_pattern("first", exact_match=True)] == [10]
        assert wrap.get_change_list_by_description_pattern("zzz") == []

    def test_get_default_change_list_has_no_server_call(self, env):
        wrap = env.wrap()
        assert wrap.get_default_change_list() == {"id": "default", "description": "Default Change", "status": "pending", "user": "", "client": WORKSPACE}
        assert env.instances == []
        wrap.workspace_name = None
        assert wrap.get_default_change_list()["client"] == ""
