#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""UE5 Type C 하니스 (최소형, 콘솔 프로세스 쪽).

PyJalLib에는 3ds Max의 `MaxTestRunner`에 해당하는 UE5 하니스가 없었다. 새 판정 로직을
만들지 않고 **이미 라이브러리에 있는 부품만 조합**한다.

- 실행: `pyjallib.ue5.headlessRunner.build_headless_command` / `run_headless_with_pump`
- 판정: `pyjallib.ue5.importVerdict.collect_result_readout` / `judge_import_outcome`
  - **판정 축은 결과 JSON이다. 종료 코드가 아니다** - UE5 헤드레스는 스크립트가 죽어도
    0을 돌려주고, 작업을 다 끝낸 뒤 종료 크래시로 0xC0000005를 내기도 한다
    (`.claude/references/patterns/subprocess_verdict_axis.md`).
  - 기동 **직전** epoch + 결과 JSON mtime 신선도 게이트(두 시계는 허용 오차로 비교 -
    `FRESHNESS_TOLERANCE_SECONDS`)가 `judge_import_outcome` 안에 이미 있다.
  - 결과 JSON은 최상위 `success: bool`을 갖는 것이 이 하니스의 계약이다.

**`-SCCProvider=None`을 항상 붙인다.** 테스트는 `/Game/__PyJalLibTest__/` 아래 임시
복제본에만 쓰지만, 소스 컨트롤이 켜져 있으면 `save_asset`이 새 파일을 default CL에
add하거나 읽기 전용 파일을 자동 체크아웃할 수 있다(`ue5/silent_write_paths.md` §2).
P4 통로를 하니스 수준에서 끊는다.

UE5 스크립트에는 설정 JSON 경로를 환경변수 `PYJAL_UE5_TEST_CONFIG`로 넘긴다
(`-ExecutePythonScript` 인자 인용 문제를 피한다). `run_headless_with_pump`는 env 인자가
없으므로 현재 프로세스 환경에 얹어 상속시킨다.
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from pyjallib.ue5.headlessRunner import (  # noqa: E402
    build_headless_command,
    decode_process_stdout,
    detect_import_script_error,
    run_headless_with_pump,
    stdout_tail,
)
from pyjallib.ue5.importVerdict import (  # noqa: E402
    ImportVerdict,
    collect_result_readout,
    judge_import_outcome,
)

UE5_EDITOR_PATH = os.environ.get(
    "PYJAL_UE5_EDITOR", "D:/root/UE5/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
)
UE5_PROJECT_PATH = os.environ.get("PYJAL_UE5_PROJECT", "D:/root/Omni/Omni.uproject")
CONFIG_ENV = "PYJAL_UE5_TEST_CONFIG"
EXTRA_FLAGS = ("-SCCProvider=None",)
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


@dataclass
class HarnessRun:
    """UE5 스크립트 1회 실행 결과.

    Attributes:
        verdict: 결과 JSON 단독 판정
        resultJson: 결과 JSON 내용(읽지 못하면 None)
        returnCode: 종료 코드(진단 정보, 판정 축 아님)
        resultJsonPath: 결과 JSON 경로
        engineLogPath: 엔진 로그 경로
        stdoutTail: stdout 끝부분(진단용)
        command: 실행한 명령
    """

    verdict: ImportVerdict
    resultJson: Optional[Dict]
    returnCode: Optional[int]
    resultJsonPath: str
    engineLogPath: str
    stdoutTail: str
    command: List[str] = field(default_factory=list)


def run_ue5_script(
    inScriptPath: Path,
    inConfig: Dict,
    inRunName: str,
    inLogDir: Path = LOG_DIR,
) -> HarnessRun:
    """UE5 헤드레스로 스크립트를 실행하고 결과 JSON으로 판정한다.

    Args:
        inScriptPath: UE5 안에서 실행할 스크립트 절대 경로
        inConfig: 스크립트에 넘길 설정. `outputJsonPath`는 이 함수가 채운다.
        inRunName: 로그·결과 파일 이름 접두
        inLogDir: 산출물 디렉토리. 기본값 `tests/logs`.

    Returns:
        실행 결과
    """
    inLogDir.mkdir(parents=True, exist_ok=True)
    resultPath = inLogDir / f"{inRunName}_result.json"
    configPath = inLogDir / f"{inRunName}_config.json"
    engineLogPath = inLogDir / f"{inRunName}_engine.log"
    stdoutPath = inLogDir / f"{inRunName}_stdout.txt"

    # 이전 결과를 지운다. 실패해도 진행한다 - 보증은 아래 신선도 게이트가 한다.
    try:
        if resultPath.exists():
            resultPath.unlink()
    except OSError as unlinkError:
        print(f"[WARN] 이전 결과 JSON 삭제 실패(신선도 게이트가 대신 막는다): {unlinkError}")

    config = dict(inConfig)
    config["outputJsonPath"] = resultPath.as_posix()
    configPath.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.environ[CONFIG_ENV] = configPath.as_posix()

    command = build_headless_command(
        UE5_EDITOR_PATH, UE5_PROJECT_PATH, Path(inScriptPath).as_posix(), engineLogPath.as_posix()
    )
    command.extend(EXTRA_FLAGS)

    startedAt = time.time()  # 기동 직전 - 신선도 게이트의 기준
    returnCode, stdoutBytes = run_headless_with_pump(command, stdoutPath)
    stdoutText = decode_process_stdout(stdoutBytes)

    readout = collect_result_readout(resultPath)
    verdict = judge_import_outcome(
        returnCode, readout, startedAt, detect_import_script_error(stdoutText)
    )
    resultJson: Optional[Dict] = None
    if readout.readable:
        resultJson = json.loads(resultPath.read_text(encoding="utf-8"))

    return HarnessRun(
        verdict=verdict,
        resultJson=resultJson,
        returnCode=returnCode,
        resultJsonPath=resultPath.as_posix(),
        engineLogPath=engineLogPath.as_posix(),
        stdoutTail=stdout_tail(stdoutText),
        command=command,
    )
