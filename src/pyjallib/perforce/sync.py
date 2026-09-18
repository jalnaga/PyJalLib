# -*- coding: utf-8 -*-
"""싱크 - 갱신 필요 확인과 싱크 실행.

`Perforce`의 Mixin이다 - `pyjallib/perforce.py`(1,671줄)를 서브패키지로 분해하면서
(2026-09-18 ExportToolsRefactor Phase 10) 메서드를 **본문 무변경으로 이동**만 했다(`P4()` 생성 호출만
패키지 이름 조회로 바꿈 - 아래 주석). 인스턴스 속성(`port`/`user`/`workspace_name`/`charset`/
`exception_level`)과 `_normalize_path(s)`는 `core.Perforce`에 있다. 특성화 Type A(`tests/perforce/`)가 계약을 고정한다.
"""

from P4 import P4Exception
from typing import List

# 연결 객체 생성은 `pyjallib.perforce.P4`(패키지 이름)를 **호출 시점에** 조회한다.
# 소비처·테스트가 `patch("pyjallib.perforce.P4", ...)`로 대역을 꽂는 주입점을 분해 전과 같게 유지하기 위해서다
# (모듈 전역 `P4`를 쓰면 패키지 속성을 바꿔도 이 모듈에는 닿지 않는다).
from pyjallib import perforce as _perforcePackage


class _SyncMixin:
    """싱크 - 갱신 필요 확인과 싱크 실행."""

    def check_update_required(self, file_paths: List[str]) -> bool:
        """
        파일들의 싱크 필요 여부 확인

        Args:
            file_paths: 확인할 파일 경로 리스트

        Returns:
            bool: 싱크가 필요하면 True
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 프리뷰 모드로 싱크 확인
            sync_result = p4.run("sync", "-n", *normalized)

            # 결과가 있으면 싱크 필요
            return len(sync_result) > 0
        except P4Exception as e:
            print(f"싱크 확인 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def sync_files(self, file_paths: List[str]) -> bool:
        """
        파일들을 싱크

        Args:
            file_paths: 싱크할 파일 경로 리스트

        Returns:
            bool: 성공 여부
        """
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            normalized = self._normalize_paths(file_paths)

            # 싱크 실행
            p4.run("sync", *normalized)
            return True
        except P4Exception as e:
            print(f"싱크 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()
