# -*- coding: utf-8 -*-
"""특성화 ② 열린 파일 이동·수집 - `move_opened_files_to_new_change_list` 롤백 경로 포함 (Phase 10.4).

`test_perforce_move_opened_files.py` / `test_perforce_collect_opened_files.py`가 이미 계약을 덮고 있어
여기서는 **연결 수명·롤백 시퀀스·사후 대조 헬퍼**처럼 그쪽이 고정하지 않은 면을 보탠다.
"""

from pathlib import Path

import pytest
from P4 import P4Exception

from conftest import WORKSPACE, assert_single_connection
from pyjallib.perforce import OpenedFilesCollectResult

CL = 4242
A = r"D:\ws\proj\A.uasset"
B = r"D:\ws\proj\B.uasset"
DEPOT_A = "//depot/proj/A.uasset"
DEPOT_B = "//depot/proj/B.uasset"


def n(inPath):
    return str(Path(inPath).resolve())


def where(inDepot, inLocal):
    return {"depotFile": inDepot, "clientFile": "//ws" + inDepot[7:], "path": n(inLocal)}


def opened(inDepot):
    return {"depotFile": inDepot, "clientFile": "//ws" + inDepot[7:], "change": str(CL), "action": "edit"}


class TestMoveOpenedFiles:
    def test_full_sequence_single_connection(self, env):
        env.script.on("change", "-o", result=[{"Change": "new", "Files": ["//depot/other"]}])
        env.script.on("opened", "-c", str(CL), result=[opened(DEPOT_A), opened(DEPOT_B)])
        env.script.on("where", result=[where(DEPOT_A, A), where(DEPOT_B, B)])
        result = env.wrap().move_opened_files_to_new_change_list("desc", [A, B])
        assert result == {"succeeded": True, "changelist": CL, "movedCount": 2, "missingPaths": []}
        assert env.events() == ["connect", "run:change", "save_change", "run:reopen", "run:opened", "run:where", "disconnect"]
        assert env.runs("reopen") == [("reopen", "-c", str(CL), n(A), n(B))]
        assert env.runs("opened") == [("opened", "-c", str(CL), n(A), n(B))]
        assert "Files" not in env.log[2][1] and env.log[2][1]["Description"] == "desc"
        assert_single_connection(env)

    def test_non_list_rejected_and_empty_makes_no_changelist(self, env):
        wrap = env.wrap()
        with pytest.raises(ValueError):
            wrap.move_opened_files_to_new_change_list("d", "x")
        assert wrap.move_opened_files_to_new_change_list("d", []) == {"succeeded": False, "changelist": None, "movedCount": 0, "missingPaths": []}
        assert env.instances == []

    def test_reopen_failure_rolls_back_in_same_connection(self, env):
        env.script.on("change", "-o", result=[{"Change": "new"}])
        env.script.on("reopen", "-c", str(CL), raises=P4Exception("reopen failed"))
        with pytest.raises(P4Exception):
            env.wrap().move_opened_files_to_new_change_list("d", [A])
        assert env.runs("reopen") == [("reopen", "-c", str(CL), n(A)), ("reopen", "-c", "default", n(A))]
        assert env.runs("change") == [("change", "-o"), ("change", "-d", str(CL))]
        assert env.runs("revert") == []  # 파일 내용은 리버트하지 않는다
        assert env.events()[-1] == "disconnect" and len(env.instances) == 1

    def test_failure_before_changelist_creation_has_no_rollback(self, env):
        env.script.on("change", "-o", raises=P4Exception("down"))
        with pytest.raises(P4Exception):
            env.wrap().move_opened_files_to_new_change_list("d", [A])
        assert env.runs("change") == [("change", "-o")]

    def test_partial_move_reports_missing_and_keeps_changelist(self, env):
        env.script.on("change", "-o", result=[{"Change": "new"}])
        env.script.on("opened", "-c", str(CL), result=[opened(DEPOT_A)])
        env.script.on("where", result=[where(DEPOT_A, A), where(DEPOT_B, B)])
        result = env.wrap().move_opened_files_to_new_change_list("d", [A, B])
        assert result == {"succeeded": False, "changelist": CL, "movedCount": 1, "missingPaths": [n(B)]}
        assert env.runs("change") == [("change", "-o")]


class TestPostMoveHelpers:
    def test_collect_comparable_paths(self, env):
        env.script.on("opened", "-c", str(CL), result=[opened(DEPOT_A), "junk", {"depotFile": "//depot/unmapped"}])
        env.script.on("where", result=[where(DEPOT_A, A)])
        moved = env.wrap()._collect_comparable_paths_in_change_list(env.factory(), CL, [n(A), n(B)])
        assert moved == {n(A).replace("\\", "/").lower()}

    def test_collect_returns_empty_on_error_or_none(self, env):
        env.script.on("opened", raises=P4Exception("none"))
        assert env.wrap()._collect_comparable_paths_in_change_list(env.factory(), CL, [n(A)]) == set()
        env2_script_empty = env.script
        env2_script_empty._rules.clear()
        env2_script_empty.on("opened", result=[])
        assert env.wrap()._collect_comparable_paths_in_change_list(env.factory(), CL, [n(A)]) == set()
        assert env.runs("where") == []

    def test_rollback_swallows_both_errors(self, env):
        env.script.on("reopen", raises=P4Exception("a"))
        env.script.on("change", "-d", raises=P4Exception("b"))
        env.wrap()._rollback_change_list_move(env.factory(), CL, [A])  # 예외 없음
        assert env.runs() == [("reopen", "-c", "default", n(A)), ("change", "-d", str(CL))]


class TestCollectOpenedFilesIntoChangeList:
    def _happy(self, env):
        env.script.on("change", "-o", result=[{"Change": "new"}])
        env.script.on("opened", "-c", str(CL), result=[opened(DEPOT_A)])
        env.script.on("where", result=[where(DEPOT_A, A)])

    def test_pending_keeps_one_connection(self, env):
        self._happy(env)
        result = env.wrap().collect_opened_files_into_change_list("desc", [A])
        assert isinstance(result, OpenedFilesCollectResult)
        assert (result.succeeded, result.changelist, result.movedCount, result.submitted) == (True, CL, 1, False)
        assert result.message == f"체인지리스트 {CL}에 1개 파일 이동 (pending 유지)"
        assert len(env.instances) == 1

    def test_submit_uses_second_connection_with_default_auto_revert(self, env):
        self._happy(env)
        result = env.wrap().collect_opened_files_into_change_list("desc", [A], inShouldSubmit=True)
        assert result.submitted is True and result.message == f"체인지리스트 {CL} 제출 완료 (1개 파일)"
        assert len(env.instances) == 2
        assert env.runs("revert") == [("revert", "-a", "-c", str(CL))]
        assert env.runs("submit") == [("submit", "-c", str(CL))]

    def test_submit_of_unchanged_content_reports_deleted(self, env):
        env.script.on("change", "-o", result=[{"Change": "new"}])
        env.script.on("opened", "-c", str(CL), n(A), result=[opened(DEPOT_A)])
        env.script.on("opened", "-c", str(CL), result=[])  # 제출 단계 확인은 파일 인자 없이 → 빈 CL
        env.script.on("where", result=[where(DEPOT_A, A)])
        result = env.wrap().collect_opened_files_into_change_list("desc", [A], inShouldSubmit=True)
        assert result.succeeded is True and result.submitted is False
        assert "빈 체인지리스트로 삭제" in result.message

    @pytest.mark.parametrize("bad", ["", "  ", None])
    def test_empty_description_rejected(self, env, bad):
        with pytest.raises(ValueError):
            env.wrap().collect_opened_files_into_change_list(bad, [A])
        assert env.instances == []

    def test_client_field_in_default_result(self, env):
        assert env.wrap().get_default_change_list()["client"] == WORKSPACE
