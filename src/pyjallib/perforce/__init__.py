# -*- coding: utf-8 -*-
"""Perforce 모듈 - 단순화된 버전. P4Python을 사용하여 Perforce 작업을 수행하는 단일 클래스.

`pyjallib/perforce.py`(1,671줄, 공개 메서드 34)를 2026-09-18 ExportToolsRefactor Phase 10에서 서브패키지로
분해했다. **외부 import 경로는 불변**이다 - `from pyjallib.perforce import Perforce, P4Exception,
OpenedFilesCollectResult`가 그대로 동작하고, 테스트 주입점 `pyjallib.perforce.P4`도 그대로다
(Mixin들이 이 패키지 속성을 호출 시점에 조회한다).

구조:
    core.py         Perforce(Mixin 조립) + __init__/connect/disconnect/_normalize_path(s)
    changeList.py   _ChangeListMixin - CL CRUD·제출·리버트·조회
    fileOps.py      _FileOpsMixin - checkout/add/delete/move/revert
    fileStatus.py   _FileStatusMixin - 열림·타인 체크아웃·CL 소속·depot 존재
    openedMove.py   _OpenedMoveMixin - 열린 파일 CL 이동·수집 + OpenedFilesCollectResult
    sync.py         _SyncMixin - 갱신 확인·싱크
"""

from P4 import P4, P4Exception

from pyjallib.perforce.openedMove import OpenedFilesCollectResult
from pyjallib.perforce.core import Perforce

__all__ = ["Perforce", "P4", "P4Exception", "OpenedFilesCollectResult"]
