#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`.max` 파일 정적 스캔 모듈 (Max 기동 없이 이름을 뽑는 1차 정찰).

3ds Max 씬 파일은 OLE2 복합 문서이고, 그 안의 스트림에 노드 이름과 레이어 이름을
평문 바이트열로 품고 있다. 따라서 Max를 띄우지 않고 파일을 바이트로 훑는 것만으로
"이 씬에 이런 이름이 있는가"를 수천 파일 단위로 빠르게 좁힐 수 있다.

**이 모듈이 내는 결과는 1차 정찰이며 확정 근거가 아니다.** 확정 판정은 항상 씬을
로드해서 한다. 이 모듈은 "전수를 훑어 후보를 좁히는" 용도이고, 좁힌 후보를 씬 로드로
확정하는 것이 이 모듈을 쓰는 올바른 형태다.

이 모듈은 **stdlib만 사용한다.** ``pymxs``를 import하지 않으므로 3ds Max 밖의 콘솔
환경에서 그대로 import·테스트할 수 있다. 이것이 이 모듈이 ``pyjallib.max`` 밑이 아니라
패키지 루트에 있는 이유다 - ``pyjallib.max`` 패키지는 로드 시점에 39개 pymxs 모듈을
즉시 import하므로, 그 밑에 두면 **Max 없이 도는 것이 존재 의미인 이 스캐너에 정작
Max 없이는 닿을 수 없다.**

인코딩이 두 가지라는 것이 이 모듈의 핵심 함정이다:

    - **노드 이름은 UTF-16LE**로 저장된다.
    - **레이어 이름은 단일바이트 ASCII + 앵커 바이트열**로 저장된다.

UTF-16만 훑으면 레이어 이름이 **0건**으로 나와 "이 파일에 레이어 정보가 없다"고
오판한다(실측 사례 있음). 그래서 노드용과 레이어용 함수를 **합치지 않고 분리**한다 -
합치면 그 오판이 호출부로 새어 나간다.

**"스캔 가능"의 판정 축은 레이어 레코드의 존재다** - 임의 임계값이 아니다. 압축 저장된
`.max`는 스트림이 압축되어 이름이 하나도 평문으로 나오지 않는데, 그것을 "이름이 없다"로
읽으면 **대상에서 파일이 조용히 빠진다.** 문자열 개수 임계값으로 가르려던 1차 설계는
실측에서 무너졌다(2026-09-16, 232개 모집단):

    | 실제 상태                  | UTF-16 문자열 | 레이어 레코드 |
    |:---------------------------|-------------:|-------------:|
    | 정상 씬 (224건)            | 11,212~73,111 |       32~53 |
    | 정상 씬, 표적 이름 없음(6) |  2,628~19,559 |       27~37 |
    | **스캔 불가 (2건)**        |     162~180  |        **0** |

문자열 개수는 정상 파일끼리도 162배 차이가 나서 어떤 임계값으로도 가를 수 없었지만
(임계값 50은 스캔 불가 2건을 정상으로 통과시켰고, 그 2건은 씬 로드 결과 실제로는 대상
본을 갖고 있었다), **레이어 레코드는 0과 27 사이에서 깨끗이 갈렸다.** 그리고 이것은
우연이 아니라 포맷 불변식이다 - 모든 3ds Max 씬에는 기본 레이어 `"0"`이 반드시 있으므로,
**레이어 레코드가 한 건도 없다는 것은 파일을 읽지 못했다는 뜻**이다.

사용처:
    - 배치 작업의 대상 후보 축소 (전수 열거 → 정적 스캔 히트로 좁히기)
    - 변경 확산 범위 조사 (특정 이름이 몇 개 씬에 퍼져 있는가)
"""

import os
import re
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

# UTF-16LE로 저장된 ASCII 가시문자 3자 이상의 연속. 노드 이름 후보를 긁는 패턴이다.
_UTF16_STRING_PATTERN = re.compile(rb"(?:[\x20-\x7e]\x00){3,}")

# 레이어 이름 레코드의 앵커 바이트열.
#   00 10 0a 00 00 00 01 00 00 00 | 10 10 <len:u32LE> <name>
# 앵커 직후 u32LE가 레코드 길이이고, 실제 이름 길이는 그 값에서 6을 뺀 값이다.
_LAYER_ANCHOR = b"\x00\x10\x0a\x00\x00\x00\x01\x00\x00\x00\x10\x10"
_LAYER_NAME_LENGTH_OFFSET = 6

# 레이어 이름으로 받아들일 최대 바이트 길이. 앵커가 우연히 일치했을 때 쓰레기 바이트를
# 이름으로 채택하는 것을 막는 상한이다.
_LAYER_NAME_MAX_BYTES = 300

# scannable is False 인 사유 코드.
REASON_NOT_FOUND = "notFound"
REASON_EMPTY = "empty"
REASON_UNREADABLE = "unreadable"
REASON_NO_LAYER_RECORD = "noLayerRecord"

# count_names / 스캔 대상 종류.
KIND_NODE = "node"
KIND_LAYER = "layer"


@dataclass
class MaxFileScanResult:
    """`.max` 정적 스캔 1건의 결과.

    **`scannable`을 결과에 싣는 것이 이 dataclass의 존재 이유다.** `bool`이나 `list`를
    그냥 돌려주면 호출부가 "0건"을 "없음"으로 읽는다. 압축 저장되어 아무것도 못 읽은
    파일과 정말로 그 이름이 없는 파일은 전혀 다른데, 그 구분이 사라지면 **대상에서
    파일이 조용히 빠진다.** 배치 작업의 후보 집합은 그래서
    "스캔 히트 ∪ `scannable is False`"로 잡아야 한다.

    Attributes:
        filePath: 스캔한 `.max` 파일 경로
        scannable: 파일을 읽어 이름을 뽑을 수 있었는지 여부. `False`면 `names`/`counts`는
            판정 근거가 되지 못한다.
        reason: `scannable is False`일 때의 사유 코드. 스캔에 성공했으면 `None`.
        names: 추출한 이름 목록(중복 제거, 정렬 고정). `count_names`는 비워 둔다.
        counts: 표적 이름별 출현 횟수. `count_names`만 채운다.
        stringCount: 파일에서 찾은 UTF-16LE 문자열 개수. **판정 축이 아니라 진단값이다** -
            정상 파일끼리도 162배 차이가 나 임계값으로 쓸 수 없다(모듈 docstring 참조).
        sizeBytes: 파일 크기(바이트)
    """

    filePath: str
    scannable: bool
    reason: Optional[str] = None
    names: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    stringCount: int = 0
    sizeBytes: int = 0


def _read_max_bytes(inMaxFilePath: str) -> "tuple[Optional[bytes], Optional[str]]":
    """`.max` 파일을 바이트로 읽고 읽기 실패 사유를 함께 돌려준다.

    Args:
        inMaxFilePath: 읽을 `.max` 파일 경로

    Returns:
        `(데이터, 사유)` 튜플. 읽기에 성공하면 `(bytes, None)`, 실패하면 `(None, 사유 코드)`.
    """
    if not os.path.isfile(inMaxFilePath):
        return (None, REASON_NOT_FOUND)

    try:
        with open(inMaxFilePath, "rb") as f:
            data = f.read()
    except OSError:
        return (None, REASON_UNREADABLE)

    if len(data) == 0:
        return (None, REASON_EMPTY)

    return (data, None)


def _make_unscannable_result(inMaxFilePath: str, inReason: str) -> MaxFileScanResult:
    """스캔 불가 결과를 만든다.

    Args:
        inMaxFilePath: 스캔 대상 경로
        inReason: 사유 코드

    Returns:
        `scannable is False`인 결과 객체
    """
    sizeBytes = 0
    if os.path.isfile(inMaxFilePath):
        try:
            sizeBytes = os.path.getsize(inMaxFilePath)
        except OSError:
            sizeBytes = 0

    return MaxFileScanResult(
        filePath=inMaxFilePath,
        scannable=False,
        reason=inReason,
        sizeBytes=sizeBytes,
    )


def _extract_utf16_strings(inData: bytes) -> List[str]:
    """바이트열에서 UTF-16LE ASCII 문자열을 모두 뽑는다.

    Args:
        inData: `.max` 파일 전체 바이트열

    Returns:
        추출한 문자열 목록(원본 출현 순서, 중복 포함)
    """
    return [m.decode("utf-16-le") for m in _UTF16_STRING_PATTERN.findall(inData)]


def _extract_layer_names(inData: bytes) -> List[str]:
    """바이트열에서 레이어 이름 레코드를 앵커로 찾아 뽑는다.

    레이어 이름은 노드 이름과 달리 **단일바이트 ASCII**로 저장되므로 UTF-16 스캔으로는
    한 건도 잡히지 않는다.

    Args:
        inData: `.max` 파일 전체 바이트열

    Returns:
        추출한 레이어 이름 목록(원본 출현 순서, 중복 포함)
    """
    layerNames: List[str] = []
    anchorLen = len(_LAYER_ANCHOR)
    searchIdx = 0

    while True:
        anchorIdx = inData.find(_LAYER_ANCHOR, searchIdx)
        if anchorIdx < 0:
            break

        lengthIdx = anchorIdx + anchorLen
        searchIdx = lengthIdx

        if lengthIdx + 4 > len(inData):
            break

        recordLen = struct.unpack_from("<I", inData, lengthIdx)[0]
        nameLen = recordLen - _LAYER_NAME_LENGTH_OFFSET
        if nameLen <= 0 or nameLen > _LAYER_NAME_MAX_BYTES:
            continue

        nameStart = lengthIdx + 4
        nameEnd = nameStart + nameLen
        if nameEnd > len(inData):
            continue

        try:
            layerNames.append(inData[nameStart:nameEnd].decode("ascii"))
        except UnicodeDecodeError:
            continue

    return layerNames


def _prepare_scan(inMaxFilePath: str):
    """파일을 읽고 스캔 가능 여부까지 판정한다.

    세 함수가 같은 전처리를 하므로 한 곳에 둔다 - 복사하면 판정 축이 함수마다 갈린다.

    Args:
        inMaxFilePath: 스캔할 `.max` 파일 경로

    Returns:
        `(데이터, 레이어 이름 목록, 문자열 개수, 스캔 불가 결과)` 튜플. 스캔이 가능하면
        마지막 원소가 `None`이고, 불가능하면 앞 세 원소가 `None`이다.
    """
    data, reason = _read_max_bytes(inMaxFilePath)
    if data is None:
        return (None, None, 0, _make_unscannable_result(inMaxFilePath, reason))

    stringCount = len(_UTF16_STRING_PATTERN.findall(data))
    layerNames = _extract_layer_names(data)

    # 모든 3ds Max 씬에는 기본 레이어 "0"이 반드시 있다. 레이어 레코드가 한 건도 없다는
    # 것은 "레이어가 없는 씬"이 아니라 **파일을 읽지 못했다**는 뜻이다.
    if len(layerNames) == 0:
        unscannable = _make_unscannable_result(inMaxFilePath, REASON_NO_LAYER_RECORD)
        unscannable.stringCount = stringCount
        unscannable.sizeBytes = len(data)
        return (None, None, stringCount, unscannable)

    return (data, layerNames, stringCount, None)


def scan_node_names(inMaxFilePath: str) -> MaxFileScanResult:
    """`.max` 파일에서 노드 이름 후보를 뽑는다 (UTF-16LE).

    **1차 정찰이며 확정 근거가 아니다.** 반환되는 문자열에는 노드 이름이 아닌 것(머티리얼
    이름, 클래스 이름, 경로 문자열 등)도 섞인다. "이 이름이 이 파일에 있는가"를 좁히는
    데 쓰고, 확정 판정은 씬 로드로 한다.

    Args:
        inMaxFilePath: 스캔할 `.max` 파일 경로

    Returns:
        `names`에 중복 제거·정렬된 문자열 목록을 담은 결과. 읽기 실패나 압축 저장본이면
        `scannable is False`이고 `names`는 비어 있다.
    """
    data, _layerNames, stringCount, unscannable = _prepare_scan(inMaxFilePath)
    if unscannable is not None:
        return unscannable

    return MaxFileScanResult(
        filePath=inMaxFilePath,
        scannable=True,
        names=sorted(set(_extract_utf16_strings(data))),
        stringCount=stringCount,
        sizeBytes=len(data),
    )


def scan_layer_names(inMaxFilePath: str) -> MaxFileScanResult:
    """`.max` 파일에서 레이어 이름을 뽑는다 (단일바이트 ASCII + 앵커).

    **1차 정찰이며 확정 근거가 아니다.** 확정 판정은 씬 로드로 한다.

    `scan_node_names`와 분리되어 있는 이유는 인코딩이 다르기 때문이다. UTF-16LE로
    훑으면 레이어가 **0건**으로 나오고, 그것을 "레이어가 없다"로 읽는 오판이 호출부까지
    새어 나간다.

    Args:
        inMaxFilePath: 스캔할 `.max` 파일 경로

    Returns:
        `names`에 중복 제거·정렬된 레이어 이름 목록을 담은 결과. 읽기 실패나 압축
        저장본이면 `scannable is False`이고 `names`는 비어 있다.
    """
    data, layerNames, stringCount, unscannable = _prepare_scan(inMaxFilePath)
    if unscannable is not None:
        return unscannable

    return MaxFileScanResult(
        filePath=inMaxFilePath,
        scannable=True,
        names=sorted(set(layerNames)),
        stringCount=stringCount,
        sizeBytes=len(data),
    )


def count_names(
    inMaxFilePath: str,
    inNames: Sequence[str],
    inKind: str = KIND_NODE,
) -> MaxFileScanResult:
    """표적 이름들의 출현 횟수만 센다 (전체 추출 없이).

    전수 스캔에서 실제로 쓰는 형태다. 파일마다 수만 개의 문자열을 전부 추출·정렬하는
    대신 표적 바이트열만 세므로, 수 GB 규모의 모집단을 훨씬 빠르게 훑는다.

    **1차 정찰이며 확정 근거가 아니다.** 특히 `0`은 "그 이름이 없다"가 아니라 "정적으로
    찾지 못했다"이고, `scannable is False`면 `counts` 전체가 판정 근거가 되지 못한다.

    Args:
        inMaxFilePath: 스캔할 `.max` 파일 경로
        inNames: 셀 표적 이름 목록
        inKind: 표적의 종류. `"node"`(기본, UTF-16LE) 또는 `"layer"`(ASCII 앵커).
            인코딩이 다르므로 섞어서 셀 수 없다.

    Returns:
        `counts`에 `{이름: 출현 횟수}`를 담은 결과. 읽기 실패나 압축 저장본이면
        `scannable is False`이고 `counts`는 비어 있다.

    Raises:
        ValueError: `inKind`가 `"node"`도 `"layer"`도 아닐 때
    """
    if inKind not in (KIND_NODE, KIND_LAYER):
        raise ValueError(f"inKind는 '{KIND_NODE}' 또는 '{KIND_LAYER}'여야 한다: {inKind!r}")

    data, layerNames, stringCount, unscannable = _prepare_scan(inMaxFilePath)
    if unscannable is not None:
        return unscannable

    counts: Dict[str, int] = {}
    if inKind == KIND_NODE:
        for name in inNames:
            counts[name] = data.count(name.encode("utf-16-le"))
    else:
        for name in inNames:
            counts[name] = layerNames.count(name)

    return MaxFileScanResult(
        filePath=inMaxFilePath,
        scannable=True,
        counts=counts,
        stringCount=stringCount,
        sizeBytes=len(data),
    )
