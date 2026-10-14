#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""KneeBone 뒤쪽 볼륨 크기 분리 테스트 - 3ds Max 환경에서 실행 (Type C).

전에는 무릎 앞(Pop)·뒤(Back) 볼륨 본이 `inKneeVolumeSize` 하나를 함께 썼고, 리거가 생성
뒤 **뒤쪽 본 Position Script의 상수 `volumeSize`를 손으로 4로** 고쳤다(2026-10-13 마스터).
이제 `inKneeBackVolumeSize`(기본 4.0)가 뒤쪽 본의 그 상수**만** 정한다. 단정하는 것:

- 뒤 본 상수 = `inKneeBackVolumeSize`, 앞 본 상수 = `inKneeVolumeSize` (기본값 / 명시값)
- 두 본의 휴지 오프셋은 둘 다 `inKneeVolumeSize` - 수작업이 스크립트 상수만 바꿨으므로
- 굽힘 자세에서 스크립트 출력이 새 상수를 실제로 쓰는가(상수만 바뀌고 식이 안 읽는 경우 배제)
- 체인 파라미터에 새 인자가 남고, `create_bones_from_chain`(툴 modify 경로)이 값을 보존하는가
- `distanceDir`의 두 분기 - Biped는 양쪽 다리 모두 +1이라(Phase 0 실측) 음수 분기는
  X축을 뒤집은 Point 소스로 따로 만든다

앞/뒤 판별은 **이름이 아니라 `transScale` 상수**로 한다. 헤드리스 Biped 이름에는 FrontBack
파트가 없어 두 본 이름이 같다(Phase 0 실측). Pop과 Back 스케일을 서로 다른 값으로 둬서
판별을 구현의 생성 순서 로직과 독립시킨다.

기대 TC 수: 23 (TC00~TC22)

실행:
    uv run python tests/run_max_tests.py test_knee_back_volume.py
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

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

reporter = TestReporter("KneeBackVolume", LOG_DIR)

reporter.assert_test(
    assert_loaded_from_checkout(pyjallib),
    "TC00 pyjallib이 이 체크아웃에서 로드됐는가",
    f"실제 {getattr(pyjallib, '__file__', None)}",
)

jal = get_pyjallibmaxheader()
SERVICES = (jal.name, jal.anim, jal.helper, jal.bone, jal.constraint, jal.volumeBone)

#: Pop/Back 스케일. 서로 달라야 앞/뒤를 transScale로 가를 수 있다.
POP_SCALE = 0.01
BACK_SCALE = 2.0

#: 휴지 오프셋 허용오차. Phase 0 실측 잡음은 1.5e-06이다.
OFFSET_TOL = 1e-3

#: 굽힘 출력 허용오차. 종아리 -60도 굽힘의 twist 성분은 정확히 1/3로 측정됐다(Phase 0).
BEND_TOL = 1e-3
BEND_DEGREES = -60.0
BEND_TWIST = 1.0 / 3.0


def _script_ctrl(inBone):
    """볼륨 본의 Position Script 컨트롤러를 돌려준다. 없으면 None."""
    posList = jal.constraint.get_pos_list_controller(inBone)
    if posList is None:
        return None
    for index in range(int(posList.count)):
        ctrl = posList[index].controller
        if rt.classOf(ctrl) == rt.Position_Script:
            return ctrl
    return None


def _volume_pair(inChain) -> dict:
    """체인에서 앞/뒤 볼륨 본을 transScale 상수로 갈라 돌려준다.

    Returns:
        dict: {"front": node|None, "back": node|None}
    """
    pair = {"front": None, "back": None}
    for bone in inChain.bones:
        if not rt.isValidNode(bone):
            continue
        ctrl = _script_ctrl(bone)
        if ctrl is None:
            continue
        scale = float(ctrl.getConstant("transScale"))
        if abs(scale - BACK_SCALE) < 1e-6:
            pair["back"] = bone
        elif abs(scale - POP_SCALE) < 1e-6:
            pair["front"] = bone
    return pair


def _volume_size(inBone):
    return float(_script_ctrl(inBone).getConstant("volumeSize")) if inBone else None


def _rest_offset(inBone):
    """루트 본 기준 휴지 오프셋 거리(Position_XYZ 하위 값의 길이)."""
    if inBone is None:
        return None
    posList = jal.constraint.get_pos_list_controller(inBone)
    return float(rt.length(posList[0].controller.value))


def _script_y(inBone):
    return float(_script_ctrl(inBone).value.y) if inBone else None


def _bend_biped_calf(inCalf, inDegrees) -> None:
    """Biped 종아리를 로컬 Z로 굽힌다(transform 대입은 Biped에 안 먹는다)."""
    tm = rt.copy(inCalf.transform)
    rt.preRotateZ(tm, inDegrees)
    rt.biped.setTransform(inCalf, rt.Name("rotation"), tm.rotation, False)


def _distance_dir(inThigh, inCalf) -> float:
    """라이브러리와 같은 식으로 다리 방향 부호를 잰다."""
    facing = inCalf.transform.position - inThigh.transform.position
    return 1.0 if rt.dot(inCalf.objectTransform.row1, facing) > 0 else -1.0


def _assert_default_case(inLabel, inSources) -> None:
    """뒤 본 인자를 생략한 생성이 기본 4.0을 쓰는지 단정한다(TC 3개)."""
    knee = rig.KneeBone(*SERVICES)
    chain = knee.create_bones(*inSources, 0.08, 5.0, POP_SCALE, BACK_SCALE)
    pair = _volume_pair(chain) if chain else {"front": None, "back": None}
    reporter.assert_test(
        _volume_size(pair["back"]) == 4.0 and _volume_size(pair["front"]) == 5.0,
        f"{inLabel}a 인자 생략 시 뒤 본 volumeSize 4.0 / 앞 본 5.0인가",
        f"back={_volume_size(pair['back'])} front={_volume_size(pair['front'])} chain={chain!r}",
    )
    offsets = (_rest_offset(pair["back"]), _rest_offset(pair["front"]))
    reporter.assert_test(
        all(value is not None and abs(value - 5.0) < OFFSET_TOL for value in offsets),
        f"{inLabel}b 두 본의 휴지 오프셋이 inKneeVolumeSize(5.0)로 남는가",
        f"(back, front)={offsets}",
    )
    params = dict(chain.parameters) if chain else {}
    reporter.assert_test(
        params.get("inKneeBackVolumeSize") == 4.0,
        f"{inLabel}c 체인 파라미터에 inKneeBackVolumeSize 4.0이 남는가",
        f"parameters={params}",
    )
    if chain:
        chain.delete()


def _point(inName, inPos, inXAxis):
    """X축을 지정한 Point 소스를 만든다. Y는 월드 Y, Z는 X x Y."""
    xAxis = rt.Point3(*inXAxis)
    yAxis = rt.Point3(0.0, 1.0, 0.0)
    zAxis = rt.cross(xAxis, yAxis)
    node = rt.Point(name=inName)
    node.transform = rt.Matrix3(xAxis, yAxis, zAxis, rt.Point3(*inPos))
    return node


def _point_sources(inXDown: bool) -> tuple:
    """Biped 없이 다리 소스 3개를 만든다. X가 아래(+1 분기) 또는 위(-1 분기)."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    xAxis = (0.0, 0.0, -1.0) if inXDown else (0.0, 0.0, 1.0)
    thigh = _point("Bip001 L Thigh", (0.0, 0.0, 100.0), xAxis)
    calf = _point("Bip001 L Calf", (0.0, -2.0, 55.0), xAxis)
    foot = _point("Bip001 L Foot", (0.0, 0.0, 8.0), xAxis)
    calf.parent = thigh
    foot.parent = calf
    return thigh, calf, foot


def run_tests() -> None:
    rt.resetMaxFile(rt.Name("noPrompt"))
    com = rt.biped.createNew(100.0, 100.0, rt.Point3(0.0, 0.0, 0.0))
    legs = {}
    for side, legKey in (("L", "lLeg"), ("R", "rLeg")):
        legs[side] = tuple(
            rt.biped.getNode(com, rt.Name(legKey), link=link) for link in (1, 2, 3)
        )

    # TC01~TC06 - Biped 양쪽 다리, 인자 생략(라이브러리 기본 4.0)
    _assert_default_case("TC01-03 L", legs["L"])
    _assert_default_case("TC04-06 R", legs["R"])

    # TC07~TC12 - 명시값(앞 6.0 / 뒤 3.0) + 굽힘 출력 + 재생성 보존
    thigh, calf, foot = legs["L"]
    knee = rig.KneeBone(*SERVICES)
    chain = knee.create_bones(thigh, calf, foot, 0.08, 6.0, POP_SCALE, BACK_SCALE, 3.0)
    pair = _volume_pair(chain) if chain else {"front": None, "back": None}
    reporter.assert_test(
        _volume_size(pair["back"]) == 3.0,
        "TC07 명시값: 뒤 본 volumeSize가 inKneeBackVolumeSize(3.0)인가",
        f"back={_volume_size(pair['back'])}",
    )
    reporter.assert_test(
        _volume_size(pair["front"]) == 6.0,
        "TC08 명시값: 앞 본 volumeSize가 inKneeVolumeSize(6.0)인가",
        f"front={_volume_size(pair['front'])}",
    )
    offsets = (_rest_offset(pair["back"]), _rest_offset(pair["front"]))
    reporter.assert_test(
        all(value is not None and abs(value - 6.0) < OFFSET_TOL for value in offsets),
        "TC09 명시값: 두 본의 휴지 오프셋이 inKneeVolumeSize(6.0)인가",
        f"(back, front)={offsets}",
    )

    _bend_biped_calf(calf, BEND_DEGREES)
    backY, frontY = _script_y(pair["back"]), _script_y(pair["front"])
    _bend_biped_calf(calf, -BEND_DEGREES)
    expectedBack = 3.0 * BACK_SCALE * BEND_TWIST
    expectedFront = 6.0 * POP_SCALE * BEND_TWIST
    reporter.assert_test(
        backY is not None and abs(abs(backY) - expectedBack) < BEND_TOL,
        "TC10 굽힘 출력: 뒤 본이 새 상수로 밀리는가 (|y| = 3.0 x 2.0 x 1/3)",
        f"backY={backY} 기대 {expectedBack}",
    )
    reporter.assert_test(
        frontY is not None and abs(abs(frontY) - expectedFront) < BEND_TOL,
        "TC11 굽힘 출력: 앞 본은 inKneeVolumeSize로 밀리는가 (|y| = 6.0 x 0.01 x 1/3)",
        f"frontY={frontY} 기대 {expectedFront}",
    )

    rebuilt = rig.KneeBone(*SERVICES).create_bones_from_chain(chain) if chain else None
    rebuiltPair = _volume_pair(rebuilt) if rebuilt else {"front": None, "back": None}
    reporter.assert_test(
        _volume_size(rebuiltPair["back"]) == 3.0 and _volume_size(rebuiltPair["front"]) == 6.0,
        "TC12 재생성(create_bones_from_chain)이 뒤 본 3.0 / 앞 본 6.0을 보존하는가",
        f"back={_volume_size(rebuiltPair['back'])} front={_volume_size(rebuiltPair['front'])}",
    )
    if rebuilt:
        rebuilt.delete()

    # TC13~TC22 - distanceDir 두 분기 (Point 소스)
    for label, xDown, expectedDir in (("TC13-17 +1", True, 1.0), ("TC18-22 -1", False, -1.0)):
        sources = _point_sources(xDown)
        actualDir = _distance_dir(sources[0], sources[1])
        reporter.assert_test(
            actualDir == expectedDir,
            f"{label} 전제: 소스가 의도한 distanceDir 분기({expectedDir:+.0f})를 타는가",
            f"실제 {actualDir}",
        )
        _assert_default_case(f"{label}", sources)
        # 분기별 3+1 = 4 TC에 맞춰 명시값 1건을 더 본다.
        knee = rig.KneeBone(*SERVICES)
        chain = knee.create_bones(*sources, 0.08, 5.0, POP_SCALE, BACK_SCALE, 2.5)
        pair = _volume_pair(chain) if chain else {"front": None, "back": None}
        reporter.assert_test(
            _volume_size(pair["back"]) == 2.5 and _volume_size(pair["front"]) == 5.0,
            f"{label}e 명시값 2.5가 뒤 본에만 들어가는가",
            f"back={_volume_size(pair['back'])} front={_volume_size(pair['front'])}",
        )
        if chain:
            chain.delete()


try:
    run_tests()
except Exception:  # noqa: BLE001
    reporter.assert_test(False, "TCxx 예외 없이 끝났는가", traceback.format_exc())

reporter.summary()
reporter.close()
