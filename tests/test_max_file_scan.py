# -*- coding: utf-8 -*-
"""pyjallib.maxFileScan 단위 테스트 (Type A - pymxs 무의존).

합성 `.max` 바이트열로 경우의 수를 덮는다. 실제 씬 파일은 수십 MB라 저장소에 넣을 수
없고, 이 모듈이 판정하는 것은 어차피 **바이트 포맷**이므로 합성 픽스처가 같은 경로를
전부 지난다.
"""

import struct

import pytest

from pyjallib.maxFileScan import (
    KIND_LAYER,
    KIND_NODE,
    REASON_EMPTY,
    REASON_NOT_FOUND,
    REASON_NO_LAYER_RECORD,
    MaxFileScanResult,
    count_names,
    scan_layer_names,
    scan_node_names,
)

# 합성 픽스처에 심을 더미 UTF-16 문자열 개수. 판정 축이 아니라 현실성을 위한 것이다.
FILLER_STRING_COUNT = 50

_LAYER_ANCHOR = b"\x00\x10\x0a\x00\x00\x00\x01\x00\x00\x00\x10\x10"

NODE_NAMES = [
    "Bip001 Bck R Hair 04",
    "Bip001 Fwd R Hair 03",
    "Bip001 Fwd R HairSubA 00",
    "Skinbone Spine",
]
LAYER_NAMES = ["Bip", "Skinbone", "Unmapped"]


def _encode_node(inName: str) -> bytes:
    """노드 이름을 `.max` 저장 형태(UTF-16LE)로 인코딩한다.

    Args:
        inName: 노드 이름

    Returns:
        UTF-16LE 바이트열
    """
    return inName.encode("utf-16-le")


def _encode_layer(inName: str) -> bytes:
    """레이어 이름을 `.max` 저장 형태(앵커 + ASCII)로 인코딩한다.

    Args:
        inName: 레이어 이름

    Returns:
        앵커 + 길이 + ASCII 이름 바이트열
    """
    nameBytes = inName.encode("ascii")
    return _LAYER_ANCHOR + struct.pack("<I", len(nameBytes) + 6) + nameBytes


def _build_max_bytes(
    inNodeNames=None,
    inLayerNames=None,
    inFillerCount=FILLER_STRING_COUNT,
) -> bytes:
    """합성 `.max` 바이트열을 만든다.

    Args:
        inNodeNames: 심을 노드 이름 목록. 기본값은 `NODE_NAMES`.
        inLayerNames: 심을 레이어 이름 목록. 기본값은 `LAYER_NAMES`.
        inFillerCount: 심을 더미 UTF-16 문자열 개수 (현실성용, 판정 축 아님).

    Returns:
        합성된 바이트열
    """
    nodeNames = NODE_NAMES if inNodeNames is None else inNodeNames
    layerNames = LAYER_NAMES if inLayerNames is None else inLayerNames

    chunks = [b"\x00\x00MAXHEADER\x00\x00"]
    for i in range(inFillerCount):
        chunks.append(_encode_node(f"Filler{i:04d}"))
        chunks.append(b"\x00\x00")
    for name in nodeNames:
        chunks.append(_encode_node(name))
        chunks.append(b"\x00\x00")
    for name in layerNames:
        chunks.append(_encode_layer(name))
        chunks.append(b"\x00\x00")
    return b"".join(chunks)


@pytest.fixture
def normalMaxFile(tmp_path):
    """정상 `.max` 픽스처 경로를 만든다.

    Args:
        tmp_path: pytest 임시 디렉토리

    Returns:
        생성한 파일 경로 문자열
    """
    p = tmp_path / "normal.max"
    p.write_bytes(_build_max_bytes())
    return str(p)


# --- scan_node_names ---------------------------------------------------------


def test_scan_node_names_extracts_names(normalMaxFile):
    """정상 파일에서 심어 둔 노드 이름이 전부 나온다."""
    result = scan_node_names(normalMaxFile)

    assert result.scannable is True
    assert result.reason is None
    for name in NODE_NAMES:
        assert name in result.names


def test_scan_node_names_is_deduped_and_sorted(normalMaxFile):
    """노드 이름 목록은 중복 제거되고 정렬이 고정된다."""
    result = scan_node_names(normalMaxFile)

    assert result.names == sorted(set(result.names))


def test_scan_node_names_reports_size_and_string_count(normalMaxFile):
    """스캔 성공 결과는 크기와 문자열 개수를 근거로 싣는다."""
    result = scan_node_names(normalMaxFile)

    assert result.sizeBytes > 0
    assert result.stringCount >= FILLER_STRING_COUNT


# --- scan_layer_names --------------------------------------------------------


def test_scan_layer_names_extracts_layers(normalMaxFile):
    """정상 파일에서 앵커로 저장된 레이어 이름이 전부 나온다."""
    result = scan_layer_names(normalMaxFile)

    assert result.scannable is True
    assert result.names == sorted(LAYER_NAMES)


def test_scan_layer_names_not_found_by_utf16_scan(normalMaxFile):
    """레이어 이름은 UTF-16 스캔(노드 스캐너)에 잡히지 않는다.

    두 함수를 분리한 근거 자체를 테스트로 못 박는다. 이 단정이 깨지면 '레이어 0건'
    오판이 호출부로 새어 나가는 경로가 열린 것이다.
    """
    nodeResult = scan_node_names(normalMaxFile)

    assert "Unmapped" not in nodeResult.names


def test_no_layer_record_is_not_scannable(tmp_path):
    """레이어 레코드가 한 건도 없으면 scannable is False다.

    모든 3ds Max 씬에는 기본 레이어 `"0"`이 반드시 있다. 레코드가 0건인 것은 "레이어가
    없는 씬"이 아니라 **파일을 읽지 못했다**는 뜻이다. 이 판정을 놓치면 압축 저장본이
    "이름 0건"으로 통과해 배치 대상에서 조용히 빠진다(2026-09-16 실측 - 임계값 방식이
    정확히 그렇게 무너졌고, 그 2건은 씬 로드 결과 실제로는 대상 본을 갖고 있었다).
    """
    p = tmp_path / "nolayer.max"
    p.write_bytes(_build_max_bytes(inLayerNames=[]))

    result = scan_layer_names(str(p))

    assert result.scannable is False
    assert result.reason == REASON_NO_LAYER_RECORD
    assert result.names == []


def test_no_layer_record_blocks_node_scan_too(tmp_path):
    """레이어 레코드가 없으면 **노드 스캔도** 판정 근거가 되지 못한다.

    노드 이름이 몇 건 나왔더라도 파일을 온전히 읽은 것이 아니다. 판정 축은 세 함수에
    공통이어야 한다 - 함수마다 갈리면 호출부가 "노드는 읽혔으니 괜찮다"고 오독한다.
    """
    p = tmp_path / "nolayer.max"
    p.write_bytes(_build_max_bytes(inLayerNames=[]))

    nodeResult = scan_node_names(str(p))
    countResult = count_names(str(p), ["Bip001 Bck R Hair 04"])

    assert nodeResult.scannable is False
    assert nodeResult.reason == REASON_NO_LAYER_RECORD
    assert countResult.scannable is False
    assert countResult.counts == {}


# --- count_names -------------------------------------------------------------


def test_count_names_counts_targets(normalMaxFile):
    """표적 노드 이름의 출현 횟수를 센다."""
    result = count_names(normalMaxFile, ["Bip001 Bck R Hair 04", "Bip001 Fwd R Hair 99"])

    assert result.scannable is True
    assert result.counts["Bip001 Bck R Hair 04"] == 1
    assert result.counts["Bip001 Fwd R Hair 99"] == 0


def test_count_names_counts_duplicated_target(tmp_path):
    """같은 이름이 여러 번 저장되어 있으면 그만큼 센다."""
    p = tmp_path / "dup.max"
    p.write_bytes(_build_max_bytes(inNodeNames=["Bip001 Bck R Hair 04"] * 3))

    result = count_names(str(p), ["Bip001 Bck R Hair 04"])

    assert result.counts["Bip001 Bck R Hair 04"] == 3


def test_count_names_layer_kind(normalMaxFile):
    """레이어 종류로 세면 앵커 기반으로 센다."""
    result = count_names(normalMaxFile, ["Unmapped", "NoSuchLayer"], inKind=KIND_LAYER)

    assert result.counts["Unmapped"] == 1
    assert result.counts["NoSuchLayer"] == 0


def test_count_names_layer_name_not_counted_as_node(normalMaxFile):
    """레이어 이름을 노드 종류로 세면 0이다 (인코딩이 다르므로).

    인코딩을 섞어 셀 수 없다는 것을 못 박는다.
    """
    result = count_names(normalMaxFile, ["Unmapped"], inKind=KIND_NODE)

    assert result.counts["Unmapped"] == 0


def test_count_names_rejects_unknown_kind(normalMaxFile):
    """알 수 없는 종류는 조용히 넘기지 않고 예외로 막는다."""
    with pytest.raises(ValueError):
        count_names(normalMaxFile, ["Unmapped"], inKind="material")


def test_count_names_does_not_fill_names(normalMaxFile):
    """count_names는 전체 추출을 하지 않는다 (names는 비어 있다)."""
    result = count_names(normalMaxFile, ["Bip001 Bck R Hair 04"])

    assert result.names == []


# --- scannable is False 경로 --------------------------------------------------


@pytest.mark.parametrize(
    "scanFunc",
    [scan_node_names, scan_layer_names],
)
def test_missing_path_is_not_scannable(tmp_path, scanFunc):
    """부재 경로는 scannable is False + notFound."""
    result = scanFunc(str(tmp_path / "nope.max"))

    assert result.scannable is False
    assert result.reason == REASON_NOT_FOUND
    assert result.names == []


def test_missing_path_count_names_is_not_scannable(tmp_path):
    """부재 경로는 count_names에서도 scannable is False다."""
    result = count_names(str(tmp_path / "nope.max"), ["Bip001 Bck R Hair 04"])

    assert result.scannable is False
    assert result.reason == REASON_NOT_FOUND
    assert result.counts == {}


@pytest.mark.parametrize(
    "scanFunc",
    [scan_node_names, scan_layer_names],
)
def test_empty_file_is_not_scannable(tmp_path, scanFunc):
    """빈 파일은 scannable is False + empty."""
    p = tmp_path / "empty.max"
    p.write_bytes(b"")

    result = scanFunc(str(p))

    assert result.scannable is False
    assert result.reason == REASON_EMPTY


@pytest.mark.parametrize(
    "scanFunc",
    [scan_node_names, scan_layer_names],
)
def test_compressed_file_is_not_scannable(tmp_path, scanFunc):
    """압축 저장본은 scannable is False + noLayerRecord.

    **0건을 '없음'으로 읽지 않게 하는 것이 이 단정의 목적이다.** 이 경로가 무너지면
    배치 대상에서 파일이 조용히 빠진다.
    """
    p = tmp_path / "compressed.max"
    p.write_bytes(b"\x1f\x8b\x08" + bytes(range(1, 200)) * 40)

    result = scanFunc(str(p))

    assert result.scannable is False
    assert result.reason == REASON_NO_LAYER_RECORD


def test_compressed_file_count_names_is_not_scannable(tmp_path):
    """압축 저장본은 count_names에서도 counts가 판정 근거가 되지 못한다."""
    p = tmp_path / "compressed.max"
    p.write_bytes(b"\x1f\x8b\x08" + bytes(range(1, 200)) * 40)

    result = count_names(str(p), ["Bip001 Bck R Hair 04"])

    assert result.scannable is False
    assert result.counts == {}


def test_string_count_does_not_decide_scannable(tmp_path):
    """문자열이 거의 없어도 **레이어 레코드가 있으면** 스캔 가능이다.

    문자열 개수를 판정 축으로 쓰던 1차 설계를 되살리지 못하게 막는다. 실측에서 정상
    파일끼리도 문자열 개수가 162배 차이 나(162 vs 73,111) 어떤 임계값으로도 가를 수
    없었고, 임계값 50은 스캔 불가 2건을 정상으로 통과시켰다.
    """
    p = tmp_path / "sparse.max"
    p.write_bytes(
        _build_max_bytes(inNodeNames=["Bip001 Bck R Hair 04"], inFillerCount=0)
    )

    result = scan_node_names(str(p))

    assert result.scannable is True
    assert result.stringCount < FILLER_STRING_COUNT
    assert "Bip001 Bck R Hair 04" in result.names


def test_result_type(normalMaxFile):
    """세 함수 모두 MaxFileScanResult를 돌려준다."""
    assert isinstance(scan_node_names(normalMaxFile), MaxFileScanResult)
    assert isinstance(scan_layer_names(normalMaxFile), MaxFileScanResult)
    assert isinstance(count_names(normalMaxFile, []), MaxFileScanResult)
