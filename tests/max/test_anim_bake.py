#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""``Anim.bake_world_transforms`` 단독 검증 (Type C).

프리미티브만 떼어 검증한다. 소비처(orvlib 헬퍼 전송)의 왕복 테스트는 전송
경로 전체를 보므로, 프리미티브 자체의 계약이 깨졌을 때 원인이 한 단계
멀어진다. 여기서 계약을 직접 못 박는다.

- TC01: 같은 시간축 베이크 - 프레임별 월드 트랜스폼 12-float 일치
- TC02: 재기준 베이크 - 소스 (10, 40)이 대상 (0, 30)으로 이동
- TC03: 계층 대상 - 부모 먼저 순서로 넘기면 자식 월드 결과가 보존된다
- TC04: ``inClearTargetKeys`` - 대상의 기존 키가 구간 단위로 걷힌다
- TC05: 청크 경계 - 청크 크기보다 긴 구간에서 이음매 프레임이 정확하다

테스트 유형: Type C (Headless + Log)
로그: tests/logs/test_AnimBake.log
"""

import sys
import traceback
from pathlib import Path

# pyjallib 소스 경로 추가
_srcPath = str(Path(__file__).parent.parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

# 배포본 선로드 퍼지 - 워크트리 소스를 검증하기 위함
for _moduleName in [
    name for name in sys.modules
    if name == "pyjallib" or name.startswith("pyjallib.")
]:
    del sys.modules[_moduleName]

import pymxs
from pymxs import runtime as rt
from pyjallib.testKit import TestReporter
from pyjallib.max.anim import Anim

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("AnimBake", LOG_DIR)

anim = Anim()
TOLERANCE = 0.01


def _matrix_at(inNode, inFrame: int) -> tuple:
    """특정 프레임의 월드 트랜스폼을 12개 float 튜플로 스냅샷한다."""
    with pymxs.attime(inFrame):
        matrix = inNode.transform
        rows = (matrix.row1, matrix.row2, matrix.row3, matrix.row4)
        return tuple(
            float(component)
            for row in rows
            for component in (row.x, row.y, row.z)
        )


def _matrices_match(inLeft: tuple, inRight: tuple) -> bool:
    """두 스냅샷이 허용 오차 내에서 일치하는지 확인한다."""
    return all(
        abs(left - right) < TOLERANCE for left, right in zip(inLeft, inRight)
    )


def _animate_point(inNode, inStartFrame: int, inEndFrame: int, inScale: float) -> None:
    """구간 전 프레임에 위치·회전 키를 심는다."""
    with pymxs.animate(True):
        for frame in range(inStartFrame, inEndFrame + 1):
            offset = float(frame - inStartFrame)
            with pymxs.attime(frame):
                inNode.position = rt.Point3(
                    offset * 2.0 * inScale,
                    offset * -1.5 * inScale,
                    offset * offset * 0.05 * inScale,
                )
                inNode.rotation = rt.eulerAngles(0.0, 0.0, offset * 3.0 * inScale)


def _reset(inStartFrame: int, inEndFrame: int) -> None:
    """씬을 리셋하고 구간을 설정한다."""
    rt.resetMaxFile(rt.name("noPrompt"), quiet=True)
    rt.animationRange = rt.interval(inStartFrame, inEndFrame)


# ============================================================
# TC01: 같은 시간축 베이크
# ============================================================
try:
    _reset(0, 30)
    sourceNode = rt.Point(name="src01")
    _animate_point(sourceNode, 0, 30, 1.0)
    expected = [_matrix_at(sourceNode, frame) for frame in range(0, 31)]

    targetNode = rt.Point(name="tgt01")
    anim.bake_world_transforms([sourceNode], [targetNode], 0, 30)

    allMatch = all(
        _matrices_match(expected[frame], _matrix_at(targetNode, frame))
        for frame in range(0, 31)
    )
    reporter.assert_test(
        allMatch,
        "TC01 같은 시간축 베이크: 31프레임 월드 트랜스폼 12-float 일치",
    )
except Exception as e:
    reporter.error("TC01 같은 시간축 베이크", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC02: 재기준 베이크 (소스 10~40 -> 대상 0~30)
# ============================================================
try:
    _reset(10, 40)
    sourceNode = rt.Point(name="src02")
    _animate_point(sourceNode, 10, 40, 1.2)
    expected = [_matrix_at(sourceNode, frame) for frame in range(10, 41)]

    targetNode = rt.Point(name="tgt02")
    anim.bake_world_transforms(
        [sourceNode], [targetNode], 10, 40, inTargetStartFrame=0
    )

    allMatch = all(
        _matrices_match(expected[offset], _matrix_at(targetNode, offset))
        for offset in range(0, 31)
    )
    reporter.assert_test(
        allMatch,
        "TC02 재기준 베이크: 소스 프레임 10+k가 대상 프레임 k에 실린다",
    )
except Exception as e:
    reporter.error("TC02 재기준 베이크", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC03: 계층 대상 - 부모 먼저 순서
# ============================================================
try:
    _reset(0, 20)
    sourceParent = rt.Point(name="srcParent03")
    sourceChild = rt.Point(name="srcChild03")
    sourceChild.parent = sourceParent
    _animate_point(sourceParent, 0, 20, 1.0)
    _animate_point(sourceChild, 0, 20, 0.4)
    expectedParent = [_matrix_at(sourceParent, frame) for frame in range(0, 21)]
    expectedChild = [_matrix_at(sourceChild, frame) for frame in range(0, 21)]

    targetParent = rt.Point(name="tgtParent03")
    targetChild = rt.Point(name="tgtChild03")
    targetChild.parent = targetParent

    # 부모 먼저(깊이 오름차순)로 넘긴다 - 순서가 곧 적용 순서다.
    anim.bake_world_transforms(
        [sourceParent, sourceChild], [targetParent, targetChild], 0, 20
    )

    parentMatch = all(
        _matrices_match(expectedParent[frame], _matrix_at(targetParent, frame))
        for frame in range(0, 21)
    )
    childMatch = all(
        _matrices_match(expectedChild[frame], _matrix_at(targetChild, frame))
        for frame in range(0, 21)
    )
    reporter.assert_test(
        parentMatch and childMatch,
        "TC03 계층 대상: 부모 먼저 순서로 넘기면 자식의 월드 결과가 보존된다",
        inDetail=f"parentMatch={parentMatch}, childMatch={childMatch}",
    )
except Exception as e:
    reporter.error("TC03 계층 대상", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC04: inClearTargetKeys - 대상의 기존 키 제거
# ============================================================
try:
    _reset(0, 20)
    sourceNode = rt.Point(name="src04")
    _animate_point(sourceNode, 0, 20, 1.0)
    expected = [_matrix_at(sourceNode, frame) for frame in range(0, 21)]

    # 대상에 **다른** 애니메이션을 미리 실어 둔다 (복원 씬의 조건 모사).
    targetNode = rt.Point(name="tgt04")
    _animate_point(targetNode, 0, 20, -3.0)

    anim.bake_world_transforms(
        [sourceNode], [targetNode], 0, 20, inClearTargetKeys=True
    )

    allMatch = all(
        _matrices_match(expected[frame], _matrix_at(targetNode, frame))
        for frame in range(0, 21)
    )
    keyCount = int(
        rt.execute(f'$\'{targetNode.name}\'.position.controller.keys.count')
    )
    reporter.assert_test(
        allMatch and keyCount == 21,
        "TC04 기존 키가 실린 대상도 구간 삭제 후 정확히 21개 키로 덮인다",
        inDetail=f"allMatch={allMatch}, keyCount={keyCount}",
    )
except Exception as e:
    reporter.error("TC04 기존 키 제거", f"{e}\n{traceback.format_exc()}")


# ============================================================
# TC05: 청크 경계 - 이음매 프레임 정확성
# ============================================================
try:
    _reset(0, 47)
    sourceNode = rt.Point(name="src05")
    _animate_point(sourceNode, 0, 47, 0.9)
    expected = [_matrix_at(sourceNode, frame) for frame in range(0, 48)]

    targetNode = rt.Point(name="tgt05")
    # 청크 크기 7이면 48프레임이 7개 청크 + 나머지로 갈린다.
    anim.bake_world_transforms(
        [sourceNode], [targetNode], 0, 47, inChunkSize=7
    )

    mismatched = [
        frame for frame in range(0, 48)
        if not _matrices_match(expected[frame], _matrix_at(targetNode, frame))
    ]
    reporter.assert_test(
        not mismatched,
        "TC05 청크 경계: 48프레임을 청크 7로 나눠도 이음매 프레임이 정확하다",
        inDetail=f"mismatchedFrames={mismatched}",
    )
except Exception as e:
    reporter.error("TC05 청크 경계", f"{e}\n{traceback.format_exc()}")


reporter.summary()
reporter.close()
