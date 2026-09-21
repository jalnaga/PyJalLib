#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Link 서비스 헤드레스 테스트 스크립트.

3ds Max 내부에서 실행되며, pyjallib.max.link.Link 클래스의
객체 연결/해제 기능을 검증한다.

테스트 유형: Type B (3ds Max 내부 실행)
"""

import sys
from pathlib import Path

# pyjallib 소스 경로 선주입 + 배포본 선점 퍼지.
# 3ds Max는 기동 시 배포본 pyjallib을 sys.modules에 선점하므로, 경로만 앞에 넣으면
# 캐시 히트로 배포본이 검증된다. _bootstrap이 퍼지까지 하고 TC00이 출처를 단정한다.
sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib, assert_loaded_from_checkout  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.link import Link

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("Link", LOG_DIR)

# TC00: 이 체크아웃의 소스를 검증하고 있는가.
# 배포본이 로드되면 워크트리 수정이 한 줄도 실행되지 않는데 초록이 뜬다.
import pyjallib  # noqa: E402

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 로드 출처가 이 체크아웃인가",
    f"pyjallib.__file__={getattr(pyjallib, '__file__', None)}",
)


def _reset_scene():
    """씬을 초기화한다."""
    rt.resetMaxFile(rt.Name("noPrompt"))


# --------------------------------------------------------------------------- #
# TC01: Link 인스턴스 생성
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    link = Link()
    reporter.assert_test(
        link is not None,
        "TC01 Link 인스턴스 생성",
        "Link() 반환값이 None"
    )
except Exception as e:
    reporter.error("TC01 Link 인스턴스 생성", str(e))

# --------------------------------------------------------------------------- #
# TC02: link_to_last_sel() - 마지막 선택 객체에 링크
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    link = Link()

    p1 = rt.Point(name="test1", pos=rt.Point3(0, 0, 0))
    p2 = rt.Point(name="test2", pos=rt.Point3(10, 0, 0))
    p3 = rt.Point(name="test3", pos=rt.Point3(20, 0, 0))

    # p1, p2, p3 순으로 선택 -> 마지막(p3)이 부모가 되어야 함
    rt.select([p1, p2, p3])
    link.link_to_last_sel()

    result = (p1.parent is not None and p1.parent.name == p3.name) and (p2.parent is not None and p2.parent.name == p3.name)
    reporter.assert_test(
        result,
        "TC02 link_to_last_sel",
        f"p1.parent={p1.parent}, p2.parent={p2.parent}, 기대: p3"
    )
except Exception as e:
    reporter.error("TC02 link_to_last_sel", str(e))

# --------------------------------------------------------------------------- #
# TC03: link_to_first_sel() - 첫 번째 선택 객체에 링크
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    link = Link()

    p1 = rt.Point(name="test1", pos=rt.Point3(0, 0, 0))
    p2 = rt.Point(name="test2", pos=rt.Point3(10, 0, 0))
    p3 = rt.Point(name="test3", pos=rt.Point3(20, 0, 0))

    # p1, p2, p3 순으로 선택 -> 첫 번째(p1)가 부모가 되어야 함
    rt.select([p1, p2, p3])
    link.link_to_first_sel()

    result = (p2.parent is not None and p2.parent.name == p1.name) and (p3.parent is not None and p3.parent.name == p1.name)
    reporter.assert_test(
        result,
        "TC03 link_to_first_sel",
        f"p2.parent={p2.parent}, p3.parent={p3.parent}, 기대: p1"
    )
except Exception as e:
    reporter.error("TC03 link_to_first_sel", str(e))

# --------------------------------------------------------------------------- #
# TC04: unlink_selection() - 링크 해제 후 parent is None 확인
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    link = Link()

    p1 = rt.Point(name="test1", pos=rt.Point3(0, 0, 0))
    p2 = rt.Point(name="test2", pos=rt.Point3(10, 0, 0))
    p3 = rt.Point(name="test3", pos=rt.Point3(20, 0, 0))

    # 먼저 링크 설정
    p2.parent = p1
    p3.parent = p1

    # 전체 선택 후 링크 해제
    rt.select([p1, p2, p3])
    link.unlink_selection()

    result = (p1.parent is None) and (p2.parent is None) and (p3.parent is None)
    reporter.assert_test(
        result,
        "TC04 unlink_selection",
        f"p1.parent={p1.parent}, p2.parent={p2.parent}, p3.parent={p3.parent}"
    )
except Exception as e:
    reporter.error("TC04 unlink_selection", str(e))

# --------------------------------------------------------------------------- #
# TC05: unlink_children() - 자식 링크 해제
# --------------------------------------------------------------------------- #
try:
    _reset_scene()
    link = Link()

    p1 = rt.Point(name="test1", pos=rt.Point3(0, 0, 0))
    p2 = rt.Point(name="test2", pos=rt.Point3(10, 0, 0))
    p3 = rt.Point(name="test3", pos=rt.Point3(20, 0, 0))

    # p2, p3을 p1의 자식으로 설정
    p2.parent = p1
    p3.parent = p1

    # p1만 선택 후 자식 링크 해제
    rt.select([p1])
    link.unlink_children()

    result = (p2.parent is None) and (p3.parent is None)
    reporter.assert_test(
        result,
        "TC05 unlink_children",
        f"p2.parent={p2.parent}, p3.parent={p3.parent}, 기대: None"
    )
except Exception as e:
    reporter.error("TC05 unlink_children", str(e))

# --------------------------------------------------------------------------- #
# 결과 요약
# --------------------------------------------------------------------------- #
reporter.summary()
reporter.close()
