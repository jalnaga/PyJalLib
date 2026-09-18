#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""UE5 헤드리스 실행기

UE5 에디터를 헤드리스로 띄워 파이썬 스크립트를 실행하고, 종료를 기다리는 동안
호출자가 준 콜백을 주기 호출한다. 세 익스포트 툴(BatchAnimExporter /
NewAnimExporter / MeshValidator)이 각자 들고 있던 실행 코드를 한 벌로 합친 것이다
(2026-09-18 ExportToolsRefactor Phase 1. 원형은 NewAnimExporter `func/ue5Import.py`의
공개형 함수들이고, 세 툴의 차이는 **엄격한 쪽**으로 통일했다 - `-abslog` 항상,
stdout 에러 마커 검출, 스크립트 2단 백업).

규약(`.claude/references/ue5/headless_execution.md`, `patterns/progress_window_pattern.md`):

- **stdout은 PIPE가 아니라 임시 파일로 받는다.** PIPE로 둔 채 `poll()` 루프를 돌면
  파이프 버퍼(Windows 약 64KB)가 찼을 때 자식이 쓰기에서 블로킹해 프로세스가 영영
  끝나지 않는다. UE5 헤드리스 stdout은 MB 단위라 확실히 넘긴다.
- **대기는 `poll()` 폴링 + 틱 콜백**이다. `communicate()`/`wait()`는 UI 스레드를
  통째로 막아 진행 창이 임포트 내내 "응답 없음"이 된다. 진행 표시는 콜백 주입이므로
  이 모듈은 Qt에 의존하지 않는다.
- **종료 코드로 성공을 단정하지 않는다.** 판정은 `importVerdict`가 결과 JSON으로
  한다. 이 모듈은 실행이 끝났다는 사실과 진단 정보(종료 코드·stdout)만 돌려준다.

의존성: 파이썬 표준 라이브러리 + pyjallib `Logger`만 사용한다(pymxs·PySide2 금지).
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from typing import Callable, List, Optional, Tuple, Union

from pyjallib.logger import Logger

_logger: Optional[Logger] = None


def _get_logger() -> Logger:
    """모듈 단일 Logger를 지연 생성해 반환한다.

    Returns:
        Logger: 모듈 전역 Logger 인스턴스
    """
    global _logger
    if _logger is None:
        _logger = Logger(inLogFileName="pyjallib_ue5Headless", inEnableConsole=False)
    return _logger


STDOUT_TAIL_SIZE = 2048
"""진단 로그에 싣는 stdout 끝부분 크기(문자). UE5 stdout 전량은 MB 단위라 tail만 남긴다."""

POLL_INTERVAL_SEC = 0.1
"""`poll()` 루프의 대기 간격(초). 틱 콜백 호출 주기이기도 하다."""

IMPORT_SCRIPT_ERROR_MARKER = "LogEditorPythonExecuter: Error"
"""UE5가 파이썬 스크립트를 예외로 끝냈을 때 stdout에 남기는 마커.

UE5 헤드리스는 스크립트가 예외로 죽어도 returncode=0으로 끝나므로(silent 실패),
이 마커가 스크립트 실패의 유일한 프로세스 수준 지문이다(2026-07-13 실측).
"""

HEADLESS_FLAGS: Tuple[str, ...] = (
    "-stdout",
    "-unattended",
    "-nopause",
    "-nosplash",
    "-NOSOUND",
    "-nullrhi",
    "-RenderOffScreen",
)
"""스크립트·로그 경로를 제외한 고정 플래그. `build_headless_command`가 여기에
`-ExecutePythonScript`와 `-abslog`를 더해 9종을 만든다."""


def detect_import_script_error(inStdoutText: Optional[str]) -> bool:
    """UE5 stdout에서 임포트 스크립트 실행 에러를 감지한다.

    Args:
        inStdoutText: UE5 subprocess stdout 텍스트(stderr 병합본). None 허용.

    Returns:
        임포트 스크립트 에러 마커가 있으면 True
    """
    if not inStdoutText:
        return False
    return IMPORT_SCRIPT_ERROR_MARKER in inStdoutText


def decode_process_stdout(inStdoutBytes: bytes) -> str:
    """subprocess stdout 바이트를 텍스트로 디코딩한다.

    utf-8 실패 시 cp949로 폴백하고, 모두 실패하면 errors='replace'로 디코딩한다.

    Args:
        inStdoutBytes: subprocess에서 캡처한 stdout 바이트

    Returns:
        디코딩된 stdout 텍스트. 입력이 비어 있으면 빈 문자열.
    """
    if not inStdoutBytes:
        return ""
    for encoding in ("utf-8", "cp949"):
        try:
            return inStdoutBytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return inStdoutBytes.decode("utf-8", errors="replace")


def stdout_tail(inStdoutText: str, inSize: int = STDOUT_TAIL_SIZE) -> str:
    """stdout 텍스트의 끝부분을 돌려준다(진단 로그용).

    Args:
        inStdoutText: 디코딩된 stdout 텍스트
        inSize: 남길 문자 수. 기본값 `STDOUT_TAIL_SIZE`.

    Returns:
        끝부분 문자열. 입력이 비어 있으면 빈 문자열.
    """
    if not inStdoutText:
        return ""
    return inStdoutText[-inSize:]


def backup_import_script(
    inScriptPath: Union[str, Path],
    inBackupDir: Union[str, Path],
    inIsFailed: bool = False,
) -> Optional[Path]:
    """임포트 스크립트를 사후 검사 가능한 위치로 백업한다.

    실행 후 항상 `_last_` 백업을 만들고, 실패 시 추가로 `_failed_` 백업을 만드는
    것이 호출 규약이다(2단 백업). 백업 파일명은 `{원본 stem}{_last_|_failed_}{시각}.py`.

    백업 디렉토리는 호출자가 준다 - 어디에 둘지는 툴(ORV의 경우
    `DevStorage/Temp`)이 정하는 것이고 이 라이브러리가 알 일이 아니다.

    Args:
        inScriptPath: 원본 스크립트 경로
        inBackupDir: 백업을 둘 디렉토리. 없으면 만든다.
        inIsFailed: 실패 여부. True면 `_failed_` 접두사로 백업. 기본값 False.

    Returns:
        백업된 파일 경로. 원본 부재 또는 복사 실패 시 None(백업 실패가 임포트
        흐름을 막으면 안 되므로 예외를 전파하지 않는다).
    """
    scriptPath = Path(inScriptPath)
    if not scriptPath.exists():
        return None

    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        prefix = "_failed_" if inIsFailed else "_last_"
        backupDir = Path(inBackupDir)
        backupDir.mkdir(parents=True, exist_ok=True)
        backupPath = backupDir / f"{scriptPath.stem}{prefix}{timestamp}.py"
        copyfile(str(scriptPath), str(backupPath))
        return backupPath
    except Exception as e:
        _get_logger().error(f"임포트 스크립트 백업 실패 ({scriptPath}): {e}")
        return None


def build_headless_command(
    inEditorPath: str,
    inProjectPath: str,
    inScriptPath: Union[str, Path],
    inLogPath: Union[str, Path],
) -> List[str]:
    """UE5 헤드리스 실행 명령줄을 만든다(순수 함수).

    플래그 9종을 이 한 곳에 고정한다. `-abslog`는 **항상** 포함한다 - 세 툴 중
    BatchAnimExporter만 빠져 있었고, UE5 로그 경로가 없으면 실패 진단이 stdout
    tail에만 의존하게 된다.

    Args:
        inEditorPath: UnrealEditor 실행 파일 경로
        inProjectPath: `.uproject` 경로
        inScriptPath: 실행할 파이썬 스크립트 절대 경로
        inLogPath: UE5 로그 파일 절대 경로(`-abslog`)

    Returns:
        subprocess에 넘길 명령 리스트
    """
    return [
        str(inEditorPath),
        str(inProjectPath),
        f"-ExecutePythonScript={inScriptPath}",
        *HEADLESS_FLAGS,
        f"-abslog={inLogPath}",
    ]


def run_headless_with_pump(
    inCommand: List[str],
    inStdoutPath: Union[str, Path],
    inTickCallback: Optional[Callable[[], None]] = None,
    inLogger: Optional[Logger] = None,
) -> Tuple[Optional[int], bytes]:
    """UE5 헤드리스 프로세스를 실행하고, 종료를 기다리는 동안 콜백을 주기 호출한다.

    호출자(UI 레이어)가 `inTickCallback`으로 `QApplication.processEvents()`를
    넘기면 대기 중에도 창이 살아 있다. 콜백이 예외를 던져도 대기는 계속된다 -
    진행 표시는 부가 기능이고 임포트 완주가 본체다.

    판정에 쓸 기동 시각(`importVerdict.judge_import_outcome`의 `inStartedAtEpoch`)은
    **호출자가 이 함수를 부르기 직전에 `time.time()`으로 찍는다.** 이 함수가 돌려주지
    않는 이유는 결과 JSON 선삭제 등 호출자의 준비 단계가 기동 시각보다 앞에 있어야
    하기 때문이다.

    Args:
        inCommand: 실행할 명령 리스트(`build_headless_command`의 결과)
        inStdoutPath: stdout(stderr 병합)을 받을 임시 파일 경로. 상위 디렉토리가
            없으면 만든다.
        inTickCallback: 대기 중 주기 호출할 콜백. None이면 호출하지 않는다.
        inLogger: 진단 로거. None이면 모듈 Logger를 쓴다.

    Returns:
        (returncode, stdout 바이트 전량). 프로세스를 띄우지도 못한 경우 returncode는
        None이다(실행 실패와 "실행했고 코드가 0"을 구분한다).
    """
    logger = inLogger if inLogger is not None else _get_logger()
    stdoutPath = Path(inStdoutPath)
    stdoutPath.parent.mkdir(parents=True, exist_ok=True)

    # 창 숨김 처리 (Windows 전용 API - 다른 플랫폼에서는 생략)
    popenKwargs = {}
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        popenKwargs["startupinfo"] = startupinfo

    logger.info(f"UE5 헤드리스 실행 시작: {inCommand}")

    with open(str(stdoutPath), "wb") as stdoutFile:
        try:
            process = subprocess.Popen(
                inCommand,
                stdout=stdoutFile,
                stderr=subprocess.STDOUT,
                **popenKwargs,
            )
        except Exception as e:
            logger.error(f"UE5 헤드리스 프로세스 기동 실패: {e}")
            return (None, b"")

        while process.poll() is None:
            if inTickCallback is not None:
                try:
                    inTickCallback()
                except Exception as e:
                    logger.warning(f"tickCallback 호출 실패(무시하고 대기 계속): {e}")
            time.sleep(POLL_INTERVAL_SEC)
        returncode = process.returncode

    try:
        stdoutBytes = stdoutPath.read_bytes()
    except OSError as e:
        logger.error(f"UE5 stdout 임시 파일 읽기 실패: {e}")
        stdoutBytes = b""

    logger.info(
        f"UE5 헤드리스 실행 종료 (returncode={returncode}, "
        f"stdout_file_size={len(stdoutBytes)}B, {stdoutPath})"
    )
    logger.debug(f"UE5 stdout tail:\n{stdout_tail(decode_process_stdout(stdoutBytes))}")
    return (returncode, stdoutBytes)


__all__ = [
    "STDOUT_TAIL_SIZE",
    "POLL_INTERVAL_SEC",
    "IMPORT_SCRIPT_ERROR_MARKER",
    "HEADLESS_FLAGS",
    "detect_import_script_error",
    "decode_process_stdout",
    "stdout_tail",
    "backup_import_script",
    "build_headless_command",
    "run_headless_with_pump",
]
