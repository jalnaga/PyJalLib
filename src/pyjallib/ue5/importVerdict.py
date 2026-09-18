#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""UE5 헤드리스 임포트 결과 판정

**판정 축은 결과 JSON 단독이고, subprocess 종료 코드는 진단 정보일 뿐이다.**

종료 코드는 양방향 모두에서 틀린다는 것이 이 워크스페이스에서 두 번 실측됐다.

1. 3ds Max 배치 호스트(`3dsmaxbatch`)는 **정상 완주에도 returncode 4294967166**을
   돌려준다. 종료 코드를 판정 축에 두면 정상 완주가 전부 실패로 뒤집힌다
   (`.claude/references/max/max_test_pattern.md`).
2. UE5 헤드리스는 반대로 **스크립트가 죽어도 returncode=0**으로 끝난다(silent 실패).
   종료 코드 0은 성공의 근거가 되지 못한다
   (`.claude/references/ue5/headless_silent_failure_diagnosis.md`).

2026-09-17에 이 결함이 실제로 터졌다. UE5가 에셋을 전건 임포트하고 결과 JSON까지
기록한 **뒤에** 에디터 종료 과정에서 크래시했고(`0xC0000005`), 툴은 종료 코드만
보고 실패로 단정해 이미 디스크에 쓰인 성공 결과를 회수하지 않았다. 같은 결함이
MeshValidator·BatchAnimExporter·NewAnimExporter 세 툴에서 **각각** 발견되어 각각
고쳐졌다 - 같은 판정 규칙이 세 벌 있었기 때문이다. 이 모듈은 그 세 벌을 하나로
합친 것이다(2026-09-18 ExportToolsRefactor Phase 1. 원형은 MeshValidator
`func/ue5ResultJudge.py`의 3계층 구조이고, 애님 툴 두 벌이 갖던 stdout 에러 마커
게이트를 `inScriptErrorDetected` 입력으로 흡수했다).

판정 계층:
    1. `collect_result_readout` - 파일 시스템 접근(존재·mtime·JSON 파싱)을 한 번에 모은다.
    2. `judge_import_outcome` - 순수 함수. 같은 입력이면 항상 같은 판정.
    3. `ImportVerdict` - 사유 코드·상세·크래시 여부·체크아웃 실패 목록.

특정 종료 코드를 허용 목록에 넣는 특례는 쓰지 않는다 - 같은 증상이 다른 코드로
나오면 또 실패하기 때문이다. 종료 코드는 버리지 않고 **실패 시 상세와 성공 시
경고**에 싣는다.

판정이 JSON으로 옮겨가면 "낡은 성공을 이번 성공으로 오인"하는 새 통로가 생기므로,
UE5 기동 직전 epoch를 기준으로 한 **mtime 신선도 게이트**를 함께 둔다.

의존성: 파이썬 표준 라이브러리 + pyjallib `Logger`만 사용한다(pymxs·PySide2 금지).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from pyjallib.logger import Logger

_logger: Optional[Logger] = None


def _get_logger() -> Logger:
    """모듈 단일 Logger를 지연 생성해 반환한다.

    `Logger`는 생성 시 파일 핸들러를 새로 부착하므로 호출마다 만들지 않는다.
    임포트 시점에 만들지 않는 이유는 이 모듈을 임포트만 하는 프로젝트에서 로그
    파일이 생기는 것을 막기 위함이다.

    Returns:
        Logger: 모듈 전역 Logger 인스턴스
    """
    global _logger
    if _logger is None:
        _logger = Logger(inLogFileName="pyjallib_ue5ImportVerdict", inEnableConsole=False)
    return _logger


# 판정 실패 사유 코드
REASON_SCRIPT_ERROR = "SCRIPT_ERROR"
"""UE5 stdout에 임포트 스크립트 에러 마커가 있다 - 스크립트가 예외로 종료했다.

UE5 헤드리스는 파이썬 스크립트가 예외로 죽어도 returncode=0으로 끝나므로(silent
실패), 결과 JSON을 보기 전에 이 마커를 먼저 본다. 마커 검출은
`headlessRunner.detect_import_script_error`가 하고 결과만 여기로 들어온다.
"""

REASON_NO_RESULT = "NO_RESULT"
"""결과 JSON이 없다 - 스크립트가 실행되지 않았거나 기록 전에 죽었다."""

REASON_UNREADABLE = "UNREADABLE"
"""결과 JSON을 읽을 수 없다 - 파손(기록 도중 중단) 또는 읽기 오류."""

REASON_STALE = "STALE"
"""결과 JSON이 이번 실행의 것이 아니다 - mtime이 UE5 기동 시각보다 이르다."""

REASON_IMPORT_FAILED = "IMPORT_FAILED"
"""결과 JSON이 `success: false`로 임포트 실패를 보고했다."""

REASON_OK = "OK"
"""임포트 성공."""

FRESHNESS_TOLERANCE_SECONDS = 2.0
"""신선도 게이트가 허용하는 타임스탬프 오차(초).

파일 수정 시각은 `time.time()`과 **같은 시계로 찍히지 않는다.** Windows의
FILETIME(100ns 단위)을 `st_mtime`의 double로 담는 과정에서 반올림이 일어나
방금 쓴 파일의 mtime이 직전에 찍은 epoch보다 **앞설 수 있고**(실측: 50회 중
11회), FAT·네트워크 파일시스템은 2초 단위 해상도를 갖는다.

이만큼을 허용해도 판정이 무뎌지지 않는다 - 이 게이트가 막으려는 것은 **이전
실행의 잔존물**이고, UE5 헤드리스 실행은 최소 수십 초가 걸리므로 두 실행의
결과 JSON은 2초보다 훨씬 멀리 떨어져 있다.
"""


@dataclass
class ImportResultReadout:
    """결과 JSON을 한 번 읽어 모은 값.

    파일 시스템 접근을 이 데이터클래스 수집 단계에 가두어, 판정 함수를
    순수 함수로 유지한다(Type A로 진리표 전수를 덮기 위함).

    Attributes:
        exists: 결과 JSON 파일이 존재했는가.
        readable: JSON으로 파싱됐는가. `exists`가 False면 의미 없다.
        mtime: 파일 수정 시각(epoch 초). 존재하지 않으면 None.
        success: JSON의 `success` 값.
        error: JSON의 `error` 문자열. 성공이면 보통 None.
        openedFiles: 소스 컨트롤에 실제로 연 파일의 절대경로 리스트.
        failedFiles: 소스 컨트롤에 여는 데 실패한 항목
            (`{"contentPath", "reason"}`). 구 JSON에는 키가 없어 빈 리스트가 된다.
        readError: 존재·파싱 실패 시의 사람이 읽는 사유. 정상이면 None.
    """

    exists: bool = False
    readable: bool = False
    mtime: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    openedFiles: List[str] = field(default_factory=list)
    failedFiles: List[dict] = field(default_factory=list)
    readError: Optional[str] = None


@dataclass
class ImportVerdict:
    """판정 결과.

    Attributes:
        success: 임포트 성공 여부. 이것이 툴의 흐름을 가른다.
        reasonCode: 사유 코드 상수(`REASON_*`).
        detail: 사람이 읽는 상세. 사용자 메시지·로그에 그대로 실린다.
        crashedAtExit: 판정은 성공인데 종료 코드가 0이 아닌 경우 True.
            임포트는 끝났고 엔진이 종료 중 비정상 종료했다는 뜻이다.
        failedFiles: 소스 컨트롤 등록에 실패한 항목. 판정과 **직교한다** -
            에셋은 저장됐고 실패한 것은 P4 등록이므로 성공 판정을 뒤집지 않는다.
        openedFiles: 소스 컨트롤에 연 파일의 절대경로 리스트. 성공 판정일 때만
            채워지며 체인지리스트 이동의 입력이다. 실패 판정이면 빈 리스트.
    """

    success: bool
    reasonCode: str
    detail: str
    crashedAtExit: bool = False
    failedFiles: List[dict] = field(default_factory=list)
    openedFiles: List[str] = field(default_factory=list)


def collect_result_readout(inResultJsonPath: Union[str, Path]) -> ImportResultReadout:
    """UE5 임포트 스크립트가 남긴 결과 JSON을 한 번의 읽기로 모은다.

    UE5 헤드리스는 별도 프로세스라 반환값을 직접 받을 수 없다. 임포트
    스크립트(`inUnreal/importResultWriter.write_import_result`)가 연 파일
    절대경로와 체크아웃 실패 목록을 JSON으로 남기고 툴이 이 함수로 회수한다.
    `openedFiles`가 체인지리스트 이동의 입력이며, 경로 사전 계산을 대체한다 -
    사전 계산은 임포터가 부수적으로 연 의존 에셋을 알 수 없다.

    **JSON 파싱 지점은 이 함수 하나로 유지한다.** 판정 함수가 파일을 다시
    읽으면 두 지점이 서로 다른 해석을 갖게 된다.

    Args:
        inResultJsonPath: 결과 JSON 파일 경로

    Returns:
        ImportResultReadout: 존재 여부·mtime·success·error·연 파일·실패 파일
    """
    logger = _get_logger()
    resultPath = Path(inResultJsonPath)

    if not resultPath.exists():
        message = f"임포트 결과 JSON이 없습니다: {inResultJsonPath}"
        logger.error(message)
        return ImportResultReadout(exists=False, readable=False, readError=message)

    try:
        mtime = resultPath.stat().st_mtime
    except OSError as e:
        message = f"임포트 결과 JSON 정보 조회 실패 ({inResultJsonPath}): {e}"
        logger.error(message)
        return ImportResultReadout(exists=True, readable=False, readError=message)

    try:
        with open(resultPath, "r", encoding="utf-8") as resultFile:
            resultData = json.load(resultFile)
    except (OSError, json.JSONDecodeError) as e:
        message = f"임포트 결과 JSON 읽기 실패 ({inResultJsonPath}): {e}"
        logger.error(message)
        return ImportResultReadout(
            exists=True, readable=False, mtime=mtime, readError=message
        )

    if not isinstance(resultData, dict):
        message = f"임포트 결과 JSON 형식이 올바르지 않습니다 ({inResultJsonPath})"
        logger.error(message)
        return ImportResultReadout(
            exists=True, readable=False, mtime=mtime, readError=message
        )

    openedFiles = resultData.get("openedFiles", [])
    failedFiles = resultData.get("failedFiles", [])
    success = bool(resultData.get("success"))
    error = resultData.get("error")

    logger.info(
        f"임포트 결과 JSON 회수: success={success}, "
        f"openedFiles_count={len(openedFiles)}, failedFiles_count={len(failedFiles)}"
    )
    logger.debug(f"openedFiles_all={openedFiles}")

    return ImportResultReadout(
        exists=True,
        readable=True,
        mtime=mtime,
        success=success,
        error=error,
        openedFiles=list(openedFiles),
        failedFiles=list(failedFiles),
        readError=None,
    )


def judge_import_outcome(
    inReturnCode: Optional[int],
    inReadout: ImportResultReadout,
    inStartedAtEpoch: float,
    inScriptErrorDetected: bool = False,
) -> ImportVerdict:
    """결과 JSON 단독으로 임포트 성공 여부를 판정한다.

    파일 시스템 접근은 `collect_result_readout`이 이미 끝냈으므로 이 함수는
    순수하다 - 같은 입력이면 항상 같은 판정이 나온다.

    판정 진리표(위에서부터 먼저 맞는 행이 판정이다):
        | stdout 마커 | 종료 코드 | 결과 JSON | 판정 |
        |:---|:---|:---|:---|
        | 있음 | 임의 | 임의 | 실패 (`SCRIPT_ERROR`) |
        | 없음 | 임의 | 없음 | 실패 (`NO_RESULT`) |
        | 없음 | 임의 | 읽기 실패(파손) | 실패 (`UNREADABLE`) |
        | 없음 | 임의 | mtime < 기동 시각 | 실패 (`STALE`) |
        | 없음 | 임의 | `success: false` | 실패 (`IMPORT_FAILED`) |
        | 없음 | 0 | `success: true` | 성공 |
        | 없음 | ≠ 0 | `success: true` | 성공 + `crashedAtExit` |

    마지막 행이 2026-09-17 결함의 수정 지점이다. 첫 행은 애님 툴 두 벌이 갖던
    silent 실패 게이트를 흡수한 것이다 - 스크립트가 예외로 죽으면 템플릿이
    `success: false`를 남기고 예외를 전파하지만, 기록 자체가 실패하거나 기록
    이후 코드가 죽는 경로도 있으므로 마커를 결과 JSON보다 앞에 둔다.

    Args:
        inReturnCode: UE5 subprocess의 종료 코드. **판정 축이 아니라 진단
            정보다** - 실패 시 상세에, 성공 시 경고에 싣는다. 프로세스를 띄우지
            못했으면 None이 들어오고, 그 경우 결과 JSON이 없거나 낡았으므로
            앞선 행에서 실패로 떨어진다.
        inReadout: `collect_result_readout`이 모은 값.
        inStartedAtEpoch: UE5 기동 **직전**에 찍은 epoch 초. 결과 JSON의
            mtime이 이보다 `FRESHNESS_TOLERANCE_SECONDS` 넘게 이르면 이전
            실행의 잔존물이다.
        inScriptErrorDetected: stdout 에러 마커 검출 여부
            (`headlessRunner.detect_import_script_error`의 결과). 기본값 False.

    Returns:
        ImportVerdict: 성공 여부·사유 코드·상세·크래시 여부·체크아웃 실패 목록·연 파일
    """
    if inScriptErrorDetected:
        return ImportVerdict(
            success=False,
            reasonCode=REASON_SCRIPT_ERROR,
            detail=(
                "UE5 임포트 스크립트가 에러로 종료했습니다 - stdout에 에러 마커가 "
                f"있습니다 (종료 코드: {inReturnCode})"
            ),
        )

    if not inReadout.exists:
        return ImportVerdict(
            success=False,
            reasonCode=REASON_NO_RESULT,
            detail=(
                "UE5 임포트 결과가 기록되지 않았습니다 - 스크립트가 실행되지 않았거나 "
                f"기록 전에 종료되었습니다 (종료 코드: {inReturnCode})"
            ),
        )

    if not inReadout.readable:
        return ImportVerdict(
            success=False,
            reasonCode=REASON_UNREADABLE,
            detail=(
                f"UE5 임포트 결과를 읽을 수 없습니다: {inReadout.readError} "
                f"(종료 코드: {inReturnCode})"
            ),
        )

    if (inReadout.mtime is None
            or inReadout.mtime < inStartedAtEpoch - FRESHNESS_TOLERANCE_SECONDS):
        return ImportVerdict(
            success=False,
            reasonCode=REASON_STALE,
            detail=(
                "UE5 임포트 결과가 이번 실행의 것이 아닙니다 - 이전 실행의 잔존물입니다 "
                f"(종료 코드: {inReturnCode})"
            ),
        )

    if not inReadout.success:
        return ImportVerdict(
            success=False,
            reasonCode=REASON_IMPORT_FAILED,
            detail=(
                f"UE5 임포트가 실패를 보고했습니다: {inReadout.error} "
                f"(종료 코드: {inReturnCode})"
            ),
            failedFiles=list(inReadout.failedFiles),
        )

    crashedAtExit = inReturnCode != 0
    if crashedAtExit:
        detail = (
            "임포트는 완료되었으나 UE5가 종료 과정에서 비정상 종료했습니다 "
            f"(종료 코드: {inReturnCode})"
        )
    else:
        detail = "UE5 임포트 완료"

    return ImportVerdict(
        success=True,
        reasonCode=REASON_OK,
        detail=detail,
        crashedAtExit=crashedAtExit,
        failedFiles=list(inReadout.failedFiles),
        openedFiles=list(inReadout.openedFiles),
    )


__all__ = [
    "REASON_SCRIPT_ERROR",
    "REASON_NO_RESULT",
    "REASON_UNREADABLE",
    "REASON_STALE",
    "REASON_IMPORT_FAILED",
    "REASON_OK",
    "FRESHNESS_TOLERANCE_SECONDS",
    "ImportResultReadout",
    "ImportVerdict",
    "collect_result_readout",
    "judge_import_outcome",
]
