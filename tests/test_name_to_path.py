# -*- coding: utf-8 -*-
"""NameToPath.generate_path 단위 테스트 (Type A).

generate_path가 pathConfig의 partOrder를 순서대로 따르는지, RealName이 자신의
위치에 value로 배치되는지, inIncludeRealName 토글이 위치가 아닌 포함 여부만
결정하는지를 검증한다. 파싱 로직과 분리하기 위해 parse_name을 고정 dict로 대체한다.
"""

import json
from pathlib import PureWindowsPath

from pyjallib.nameToPath import NameToPath


def _part(name, ptype, values=None, descriptions=None):
    """테스트용 NamePart dict 생성 헬퍼."""
    values = values or []
    descriptions = descriptions or []
    return {
        "name": name,
        "predefinedValues": values,
        "weights": [5 * (i + 1) for i in range(len(values))],
        "type": ptype,
        "descriptions": descriptions,
        "koreanDescriptions": descriptions,
        "isDirection": False,
    }


def _write_config(pathObj, partOrder, parts):
    """partOrder/nameParts로 config JSON을 tmp에 기록하고 경로 문자열 반환."""
    data = {"paddingNum": 2, "partOrder": partOrder, "nameParts": parts}
    pathObj.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(pathObj)


def _make_ntp(tmp_path, partOrder, parts, parsed, rootPath=None):
    """parse_name이 고정 dict를 반환하는 NameToPath 인스턴스 생성."""
    cfg = _write_config(tmp_path / "cfg.json", partOrder, parts)
    ntp = NameToPath(cfg, cfg, rootPath=rootPath)
    ntp.parse_name = lambda inName: parsed
    return ntp


# 공통 파트 정의: Type(PREFIX), RealName, Slot(SUFFIX)
_TYPE = _part("Type", "PREFIX", ["SK"], ["Mesh"])
_REALNAME = _part("RealName", "REALNAME")
_SLOT = _part("Slot", "SUFFIX", ["Body"], ["BodyFolder"])
_PARSED = {"Type": "SK", "RealName": "Arm", "Slot": "Body"}


def test_realname_follows_partorder_middle(tmp_path):
    """RealName이 partOrder 중간이면 RealName 뒤 파트(Slot)가 하위 폴더로 배치된다."""
    ntp = _make_ntp(tmp_path, ["Type", "RealName", "Slot"],
                    [_TYPE, _REALNAME, _SLOT], _PARSED)
    result = ntp.generate_path("dummy", inIncludeRealName=True)
    assert PureWindowsPath(result).parts == ("Mesh", "Arm", "BodyFolder")


def test_realname_excluded_keeps_after_part(tmp_path):
    """inIncludeRealName=False면 RealName 폴더만 빠지고 뒤 파트는 자기 위치를 유지한다."""
    ntp = _make_ntp(tmp_path, ["Type", "RealName", "Slot"],
                    [_TYPE, _REALNAME, _SLOT], _PARSED)
    result = ntp.generate_path("dummy", inIncludeRealName=False)
    assert PureWindowsPath(result).parts == ("Mesh", "BodyFolder")


def test_realname_last_backward_compat(tmp_path):
    """RealName이 partOrder 마지막이면 기존 동작대로 맨 끝에 배치된다(하위호환)."""
    ntp = _make_ntp(tmp_path, ["Type", "Slot", "RealName"],
                    [_TYPE, _SLOT, _REALNAME], _PARSED)
    result = ntp.generate_path("dummy", inIncludeRealName=True)
    assert PureWindowsPath(result).parts == ("Mesh", "BodyFolder", "Arm")


def test_realname_last_excluded(tmp_path):
    """RealName 마지막 + 제외면 앞 파트들만 남는다."""
    ntp = _make_ntp(tmp_path, ["Type", "Slot", "RealName"],
                    [_TYPE, _SLOT, _REALNAME], _PARSED)
    result = ntp.generate_path("dummy", inIncludeRealName=False)
    assert PureWindowsPath(result).parts == ("Mesh", "BodyFolder")


def test_after_part_absent_in_parsed(tmp_path):
    """파싱 결과에 Slot 값이 없으면(=이름에 슬롯 없음) Slot 폴더는 생기지 않는다."""
    ntp = _make_ntp(tmp_path, ["Type", "RealName", "Slot"],
                    [_TYPE, _REALNAME, _SLOT],
                    {"Type": "SK", "RealName": "Arm"})
    result = ntp.generate_path("dummy", inIncludeRealName=True)
    assert PureWindowsPath(result).parts == ("Mesh", "Arm")


def test_unknown_predefined_value_skipped(tmp_path):
    """일반 파트 값이 predefined에 없으면(description "") 해당 폴더는 생략된다."""
    ntp = _make_ntp(tmp_path, ["Type", "RealName", "Slot"],
                    [_TYPE, _REALNAME, _SLOT],
                    {"Type": "UNKNOWN", "RealName": "Arm", "Slot": "Body"})
    result = ntp.generate_path("dummy", inIncludeRealName=True)
    assert PureWindowsPath(result).parts == ("Arm", "BodyFolder")


def test_root_path_prepended(tmp_path):
    """rootPath가 있으면 폴더 계층 앞에 붙는다."""
    root = tmp_path / "root"
    root.mkdir()
    ntp = _make_ntp(tmp_path, ["Type", "RealName", "Slot"],
                    [_TYPE, _REALNAME, _SLOT], _PARSED, rootPath=str(root))
    result = ntp.generate_path("dummy", inIncludeRealName=True)
    parts = PureWindowsPath(result).parts
    assert parts[-3:] == ("Mesh", "Arm", "BodyFolder")
    assert PureWindowsPath(result).parts[: len(PureWindowsPath(str(root)).parts)] == \
        PureWindowsPath(str(root)).parts
