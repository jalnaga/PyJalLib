# -*- coding: utf-8 -*-
"""`pyjallib.perforce` 특성화 하네스 (ExportToolsRefactor Phase 10.2).

`P4` 클래스를 **기록형 대역**으로 바꾼다. `Perforce`는 메서드마다 `P4()`를 새로 만들어
connect → run… → disconnect 하므로, 대역 팩토리는 인스턴스마다 새 `RecordingP4`를 돌려주되
호출 기록(`log`)과 응답 표(`script`)는 환경 하나가 공유한다. 테스트는

    - `env.script.on("opened", "-c", "4242", result=[...])` 로 명령 접두별 응답(값·예외·콜러블)을 심고
    - `env.wrap()` 으로 workspace가 설정된 래퍼를 얻어 메서드를 부른 뒤
    - `env.runs("reopen")` / `env.log` 로 `p4.run` 인자 시퀀스와 연결 수명을 단정한다.

기존 `test_perforce_*`가 쓰던 `patch("pyjallib.perforce.P4", ...)` 방식(생성자만 가로채기)을
승격한 것이다 - `P4` 모듈 자체를 sys.modules에서 바꾸지 않으므로 `P4Exception`은 실물이다.
서브패키지 분해 뒤에도 `pyjallib.perforce.P4`(패키지 이름)를 바꾸면 모든 Mixin이 그 이름을
호출 시점에 조회하므로 같은 하네스가 그대로 동작한다.
"""

from typing import Any, List, Optional, Tuple

import pytest

from P4 import P4Exception  # noqa: F401 - 테스트가 `conftest.P4Exception`을 쓰지는 않지만 실물 확인용
from pyjallib.perforce import Perforce

PORT = "server:1666"
USER = "Dev"
WORKSPACE = "ws"


class Script:
    """명령 접두 → 응답 표. 먼저 등록된 규칙이 우선한다. 미등록 명령은 `[]`."""

    def __init__(self):
        self._rules: List[Tuple[Tuple[str, ...], Any]] = []
        self.saveChangeResult: Any = ["Change 4242 created."]
        self.fetchChangeResult: Any = {"Description": "desc\n", "Status": "pending", "User": USER, "Client": WORKSPACE}

    def on(self, *inPrefix: str, result: Any = None, raises: Optional[Exception] = None) -> "Script":
        """`run(*args)`의 앞부분이 `inPrefix`와 같으면 `result`를 돌려주거나 `raises`를 던진다."""
        self._rules.append((tuple(str(p) for p in inPrefix), raises if raises is not None else result))
        return self

    def dispatch(self, inArgs: Tuple[str, ...]) -> Any:
        args = tuple(str(a) for a in inArgs)
        for prefix, outcome in self._rules:
            if args[: len(prefix)] == prefix:
                if isinstance(outcome, BaseException):
                    raise outcome
                if callable(outcome):
                    return outcome(args)
                return outcome
        return []


class RecordingP4:
    """P4Python `P4` 대역 - 속성 대입·연결 수명·명령을 기록한다."""

    def __init__(self, inScript: Script, inLog: List[Tuple]):
        self.port = None
        self.user = None
        self.client = None
        self.charset = None
        self.exception_level = None
        self._connected = False
        self._script = inScript
        self._log = inLog

    def connect(self):
        self._connected = True
        self._log.append(("connect",))

    def disconnect(self):
        self._connected = False
        self._log.append(("disconnect",))

    def connected(self):
        return self._connected

    def run(self, *inArgs):
        self._log.append(("run",) + tuple(inArgs))
        return self._script.dispatch(inArgs)

    def save_change(self, inSpec):
        self._log.append(("save_change", dict(inSpec)))
        outcome = self._script.saveChangeResult
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def fetch_change(self, inNumber):
        self._log.append(("fetch_change", inNumber))
        outcome = self._script.fetchChangeResult
        if isinstance(outcome, BaseException):
            raise outcome
        return dict(outcome) if isinstance(outcome, dict) else outcome


class P4Env:
    """대역 팩토리 + 공유 기록."""

    def __init__(self):
        self.script = Script()
        self.log: List[Tuple] = []
        self.instances: List[RecordingP4] = []

    def factory(self, *inArgs, **inKwargs) -> RecordingP4:
        p4 = RecordingP4(self.script, self.log)
        self.instances.append(p4)
        return p4

    def wrap(self, inWorkspace: Optional[str] = WORKSPACE) -> Perforce:
        wrap = Perforce(PORT, USER)
        wrap.workspace_name = inWorkspace
        return wrap

    def runs(self, inCommand: Optional[str] = None) -> List[Tuple[str, ...]]:
        """`run` 호출 인자 목록 (명령을 주면 그 명령만)."""
        calls = [entry[1:] for entry in self.log if entry[0] == "run"]
        if inCommand is None:
            return calls
        return [c for c in calls if c and c[0] == inCommand]

    def events(self) -> List[str]:
        """이벤트 종류 순서 (connect / run:<cmd> / save_change / fetch_change / disconnect)."""
        names = []
        for entry in self.log:
            if entry[0] == "run":
                names.append(f"run:{entry[1]}")
            else:
                names.append(entry[0])
        return names


@pytest.fixture
def env(monkeypatch) -> P4Env:
    """`pyjallib.perforce.P4`를 기록형 대역 팩토리로 바꾼 환경."""
    environment = P4Env()
    monkeypatch.setattr("pyjallib.perforce.P4", environment.factory)
    return environment


def assert_single_connection(inEnv: P4Env) -> None:
    """메서드 1회 = P4 인스턴스 1개, connect 1회 → … → disconnect 1회 (Stateless 계약)."""
    assert len(inEnv.instances) == 1, inEnv.instances
    events = inEnv.events()
    assert events[0] == "connect" and events[-1] == "disconnect", events
    assert events.count("connect") == 1 and events.count("disconnect") == 1
    p4 = inEnv.instances[0]
    assert (p4.port, p4.user, p4.client, p4.charset, p4.exception_level) == (PORT, USER, WORKSPACE, "utf8", 1)
