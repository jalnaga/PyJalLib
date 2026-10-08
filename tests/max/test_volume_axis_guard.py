#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VolumeBone 미등록 축 거절 테스트 - 3ds Max 환경에서 실행 (Type C).

전에는 미등록 축(`"Y"`처럼 접두가 빠진 이동 축, 오타 회전 축)이 영벡터로 바뀌어
**생성은 성공하고 볼륨 본은 루트에 붙어 움직이지 않았다.** 툴이 Inguinal 이동 축을
`"PosY"` 대신 `"Y"`로 넘기던 결함이 그 폴백 뒤에서 출하됐다(2026-10-08).

이제 `create_volume_bones`/`create_bones`는 None, `create_bone`은 False를 돌려주고
경고를 남긴다. 단정하는 것:

- 거절 3형태(이동 축 `"Y"` · 파생 오류 `"Neg"` · 회전 축 `"W"`)가 None이고 **씬 노드 수가
  그대로**인가 - 본을 하나도 만들기 전에 거절하는가
- 거절 사유가 경고로 남는가 - 모듈 로거를 수집 래퍼로 갈아 끼워 내용을 본다
- 짝 케이스: 같은 소스·정상 축은 생성에 성공하는가 - "항상 거절하는 구현"을 배제한다
- 파트 경유: `Inguinal.create_bones`에 `"Y"`를 넣어도 None인가

기대 TC 수: 11 (TC00~TC10)

실행:
    uv run python tests/run_max_tests.py test_volume_axis_guard.py
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import assert_loaded_from_checkout, bootstrap_pyjallib  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt  # noqa: E402
import pyjallib  # noqa: E402
from pyjallib.testKit import TestReporter  # noqa: E402
from pyjallib.max.header import get_pyjallibmaxheader  # noqa: E402
from pyjallib.max import rig  # noqa: E402
from pyjallib.max.rig import volumeBone as volumeBoneModule  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

reporter = TestReporter("VolumeAxisGuard", LOG_DIR)

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib이 이 체크아웃에서 로드됐는가",
    f"실제 {getattr(pyjallib, '__file__', None)}",
)

jal = get_pyjallibmaxheader()
SERVICES = (jal.name, jal.anim, jal.helper, jal.bone, jal.constraint)


class _CollectingLogger:
    """경고만 모으는 로거 대역. 나머지 호출은 무시한다."""

    def __init__(self):
        self.warnings = []

    def warning(self, inMessage):
        self.warnings.append(str(inMessage))

    def __getattr__(self, inName):
        return lambda *args, **kwargs: None


def _node_count() -> int:
    return len(rt.objects)


def _build_sources() -> dict:
    """Biped를 만들고 다리 소스 본을 돌려준다."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    com = rt.biped.createNew(100.0, 100.0, rt.Point3(0.0, 0.0, 0.0))
    return {
        "pelvis": rt.biped.getNode(com, rt.Name("pelvis"), link=1),
        "thigh": rt.biped.getNode(com, rt.Name("lLeg"), link=1),
        "calf": rt.biped.getNode(com, rt.Name("lLeg"), link=2),
    }


def _assert_rejected(inLabel, inCall, inExpectedFragment) -> None:
    """호출이 None/False로 거절되고 노드를 남기지 않고 경고를 남기는지 단정한다.

    Args:
        inLabel: TC 접두 (예: "TC02")
        inCall: 실행할 호출 (인자 없는 콜러블)
        inExpectedFragment: 경고 문구에 있어야 하는 잘못된 값 표기
    """
    collector = _CollectingLogger()
    original = volumeBoneModule._get_logger
    volumeBoneModule._get_logger = lambda: collector
    before = _node_count()
    try:
        result = inCall()
    finally:
        volumeBoneModule._get_logger = original
    after = _node_count()

    reporter.assert_test(
        result is None or result is False,
        f"{inLabel}a 거절되는가 (None/False)",
        f"실제 {result!r}",
    )
    reporter.assert_test(
        after == before,
        f"{inLabel}b 씬에 노드를 남기지 않는가",
        f"노드 수 {before} -> {after}",
    )
    reporter.assert_test(
        any(inExpectedFragment in message for message in collector.warnings),
        f"{inLabel}c 거절 사유가 경고로 남는가 ({inExpectedFragment})",
        f"경고 {collector.warnings}",
    )


def run_tests() -> None:
    src = _build_sources()
    volumeBone = rig.VolumeBone(*SERVICES)

    # TC01 짝 케이스 - 같은 소스, 정상 축은 생성된다.
    chain = volumeBone.create_bones(src["calf"], src["thigh"], 0.5, 5.0, ["Z"], ["PosY"], [1.0])
    reporter.assert_test(
        chain is not None and len(chain.bones) == 2,
        "TC01 정상 축(Z/PosY)은 루트 + 볼륨 본 1개로 생성되는가",
        f"chain={chain!r}",
    )
    if chain is not None:
        chain.delete()

    # TC02~TC04 - 접두가 빠진 이동 축 (툴 결함이 넘기던 값)
    _assert_rejected(
        "TC02",
        lambda: volumeBone.create_bones(src["calf"], src["thigh"], 0.5, 5.0, ["Z"], ["Y"], [1.0]),
        "trans='Y'",
    )
    # TC05~TC07 - 회전 축 오타
    _assert_rejected(
        "TC05",
        lambda: volumeBone.create_bones(src["calf"], src["thigh"], 0.5, 5.0, ["W"], ["PosY"], [1.0]),
        "rot='W'",
    )
    # TC08 - 단일 본 진입점도 거절한다(루트 본 생성 전).
    before = _node_count()
    single = volumeBone.create_bone(
        src["calf"], src["thigh"], 0.5, 5.0, "Z", "Neg", 1.0, inUseRootBone=False
    )
    reporter.assert_test(
        single is False and _node_count() == before,
        "TC08 create_bone이 파생 오류 축('Neg')을 노드 생성 없이 False로 거절하는가",
        f"반환 {single!r}, 노드 수 {before} -> {_node_count()}",
    )
    volumeBone.reset()

    # TC09 - 파트 경유: Inguinal에 툴 결함 값을 넣으면 None
    inguinal = rig.Inguinal(*SERVICES)
    before = _node_count()
    rejected = inguinal.create_bones(
        src["thigh"], src["pelvis"], src["calf"], 0.5, 6.0, "Z", "Y", "Y", "Z", 2.0, 2.0
    )
    reporter.assert_test(
        rejected is None and _node_count() == before,
        "TC09 Inguinal이 축 문자('Y'/'Z')를 노드 생성 없이 None으로 거절하는가",
        f"반환 {rejected!r}, 노드 수 {before} -> {_node_count()}",
    )

    # TC10 짝 - Inguinal 정상 축은 루트 + 볼륨 본 2개
    inguinal.reset()
    accepted = inguinal.create_bones(
        src["thigh"], src["pelvis"], src["calf"], 0.5, 6.0, "Z", "Y", "PosY", "PosZ", 2.0, 2.0
    )
    reporter.assert_test(
        accepted is not None and len(accepted.bones) == 3,
        "TC10 Inguinal 정상 축(PosY/PosZ)은 루트 + 볼륨 본 2개로 생성되는가",
        f"chain={accepted!r}",
    )


try:
    run_tests()
except Exception:  # noqa: BLE001
    reporter.error("TC99 스위트 실행", traceback.format_exc())

reporter.summary()
reporter.close()
