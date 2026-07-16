# -*- coding: utf-8 -*-
"""reopen 이어받기 실 P4 통합 시나리오 (옵트인).

재익스포트 충돌 시나리오를 실제 P4 서버로 재현한다:
CL A에 파일을 열어둔 채(미제출) 같은 파일을 새 CL B로 다시 열면,
과거에는 "이미 열려있습니다" 예외로 중단됐고 수정 후에는 CL B로 이어받아야 한다.

실서버(pending CL 생성/삭제)를 건드리므로 기본 pytest 실행에서는 스킵되고,
환경변수 PYJALLIB_P4_INTEGRATION=1 로 옵트인했을 때만 실행된다.
depot에 아무것도 submit하지 않는다 (pending 상태만 사용 후 전부 revert/삭제).
"""

import configparser
import os
from pathlib import Path

import pytest

_ORV_INI = Path.home() / "Documents" / "ORV" / "ORV_Setting.ini"

pytestmark = pytest.mark.skipif(
    os.environ.get("PYJALLIB_P4_INTEGRATION") != "1" or not _ORV_INI.exists(),
    reason="실 P4 통합 테스트는 PYJALLIB_P4_INTEGRATION=1 옵트인 + ORV_Setting.ini 필요",
)

_PORT = "PC-Build:1666"
_USER = "Dev"


def _read_devstorage_config():
    """ORV_Setting.ini에서 DevStorage 워크스페이스/루트를 읽는다."""
    config = configparser.ConfigParser()
    config.read(_ORV_INI, encoding="utf-8")
    workspace = config.get("P4", "devstorage")
    devStorageRoot = Path(config.get("Folder", "devstorage"))
    return workspace, devStorageRoot


def test_reexport_conflict_scenario_takes_over_to_new_changelist():
    """CL A에 add로 열린 파일을 새 CL B로 다시 열면 이어받아(CL B 이동) 에러가 없어야 한다."""
    from pyjallib.perforce import Perforce

    workspace, devStorageRoot = _read_devstorage_config()
    tempDir = devStorageRoot / "DevStorage" / "Temp"
    testFile = tempDir / "_p4_takeover_integration_test.txt"

    p4wrap = Perforce(_PORT, _USER)
    p4wrap.connect(workspace)

    clA = None
    clB = None
    try:
        tempDir.mkdir(parents=True, exist_ok=True)
        testFile.write_text("p4 takeover integration test", encoding="utf-8")

        # 1) 첫 익스포트 상황 재현: CL A 생성 + 파일 add로 열기 (미제출 방치)
        clA = p4wrap.create_change_list("[TA 김동석] pyjallib takeover 통합테스트 CL A (자동 정리됨)")["id"]
        assert p4wrap.add_files([str(testFile)], clA) is True
        assert p4wrap.is_file_in_pending_changelist(str(testFile), clA) is True

        # 2) 재익스포트 상황 재현: 새 CL B로 같은 파일을 다시 연다
        #    (수정 전에는 여기서 "파일이 체인지리스트 {A}에 이미 열려있습니다" P4Exception)
        clB = p4wrap.create_change_list("[TA 김동석] pyjallib takeover 통합테스트 CL B (자동 정리됨)")["id"]
        assert p4wrap.add_files([str(testFile)], clB) is True

        # 3) 파일이 CL B로 이어받아졌는지 확인 (CL A에는 더 이상 없음)
        assert p4wrap.is_file_in_pending_changelist(str(testFile), clB) is True
        assert p4wrap.is_file_in_pending_changelist(str(testFile), clA) is False

        # 4) checkout_files 경로도 동일 시나리오로 확인 (add로 열린 파일을 CL A로 재이동)
        assert p4wrap.checkout_files([str(testFile)], clA) is True
        assert p4wrap.is_file_in_pending_changelist(str(testFile), clA) is True
    finally:
        # 정리: 전부 revert 후 CL 삭제, 로컬 파일 제거 (depot에 아무것도 남기지 않음)
        for cl in (clA, clB):
            if cl is not None:
                try:
                    p4wrap.revert_files(cl)
                except Exception:
                    pass
                try:
                    p4wrap.delete_change_list(cl)
                except Exception:
                    pass
        if testFile.exists():
            testFile.unlink()
