# -*- coding: utf-8 -*-
"""Phase 0 프로브 - Knee 뒤쪽 볼륨 본의 Position Script 상수 교체를 실측한다.

미확정 3건을 한 실행에 몰아 잰다(`planning_guide.md` §2.5).

1. master 경로로 왼·오른 다리 Knee 생성 -> 앞/뒤 볼륨 본 이름, Position_list 구성,
   각 Position Script 상수(`volumeSize`·`transScale`), 휴지 오프셋. 좌·우 `distanceDir`과
   뒤쪽 본 판별이 실제로 어느 본을 가리키는지
2. 상수 교체 호출 형태 비교(`setConstant` / `SetConstant` / 재-`addConstant`) -> 되는 형태,
   교체 뒤 굽힘 자세에서 스크립트 출력이 새 비율로 바뀌는지, 휴지 오프셋 불변인지
3. 2가 전부 실패하면 분기 B1(`VolumeBone.create_bone` 단건) 경로가 쓸 만한지

판정 TC는 두지 않는다 - 기록 전용(`planning_guide.md` §2.5-8). 결과는 JSON.

실행:
    uv run python tests/_run_probe.py _probe_knee_back_volume.py
"""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib  # noqa: E402

bootstrap_pyjallib()

from pymxs import runtime as rt  # noqa: E402
import pyjallib  # noqa: E402
from pyjallib.max.header import get_pyjallibmaxheader  # noqa: E402
from pyjallib.max import rig  # noqa: E402

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = LOG_DIR / "probe_knee_back_volume.json"

jal = get_pyjallibmaxheader()
SERVICES = (jal.name, jal.anim, jal.helper, jal.bone, jal.constraint)


def _try(inCall):
    """호출 결과 또는 예외 문자열을 돌려준다."""
    try:
        return {"ok": True, "value": repr(inCall())}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _p3(inValue) -> list:
    return [float(inValue.x), float(inValue.y), float(inValue.z)]


def _script_ctrl(inBone):
    posList = jal.constraint.get_pos_list_controller(inBone)
    if posList is None:
        return None
    for index in range(int(posList.count)):
        ctrl = posList[index].controller
        if rt.classOf(ctrl) == rt.Position_Script:
            return ctrl
    return None


def _const(inCtrl, inName):
    result = _try(lambda: inCtrl.getConstant(inName))
    return result.get("value", result.get("error"))


def _describe_bone(inBone) -> dict:
    posList = jal.constraint.get_pos_list_controller(inBone)
    ctrl = _script_ctrl(inBone)
    parentTm = inBone.parent.transform if inBone.parent else rt.matrix3(1)
    return {
        "name": str(inBone.name),
        "parent": str(inBone.parent.name) if inBone.parent else None,
        "localPos": _p3((inBone.transform * rt.inverse(parentTm)).position),
        "posListSubs": (
            [str(rt.classOf(posList[i].controller)) for i in range(int(posList.count))]
            if posList is not None else None
        ),
        "firstSubValue": _p3(posList[0].controller.value) if posList is not None else None,
        "scriptValue": _p3(ctrl.value) if ctrl is not None else None,
        "volumeSize": _const(ctrl, "volumeSize") if ctrl is not None else None,
        "transScale": _const(ctrl, "transScale") if ctrl is not None else None,
        "trAxis": _const(ctrl, "trAxis") if ctrl is not None else None,
    }


def _bend_calf(inCalf, inDegrees) -> dict:
    """종아리를 로컬 Z로 굽힌다. Biped는 transform 대입이 안 먹으므로 biped.setTransform."""
    def _do():
        tm = rt.copy(inCalf.transform)
        rt.preRotateZ(tm, inDegrees)
        rt.biped.setTransform(inCalf, rt.Name("rotation"), tm.rotation, False)
        return True
    return _try(_do)


def _volume_bones(inChain) -> list:
    """체인에서 Position Script를 가진 볼륨 본만 고른다."""
    return [
        bone for bone in inChain.bones
        if rt.isValidNode(bone) and _script_ctrl(bone) is not None
    ]


def main() -> dict:
    out = {
        "pyjallib": str(pyjallib.__file__),
        "frontBackValues": {
            "Forward": str(jal.name.get_name_part_value_by_description("FrontBack", "Forward")),
            "Backward": str(jal.name.get_name_part_value_by_description("FrontBack", "Backward")),
        },
    }
    rt.resetMaxFile(rt.Name("noPrompt"))
    com = rt.biped.createNew(100.0, 100.0, rt.Point3(0.0, 0.0, 0.0))

    for side, legKey in (("L", "lLeg"), ("R", "rLeg")):
        thigh = rt.biped.getNode(com, rt.Name(legKey), link=1)
        calf = rt.biped.getNode(com, rt.Name(legKey), link=2)
        foot = rt.biped.getNode(com, rt.Name(legKey), link=3)
        facing = calf.transform.position - thigh.transform.position
        sideOut = {
            "distanceDir": 1.0 if rt.dot(calf.objectTransform.row1, facing) > 0 else -1.0,
            "sources": [str(thigh.name), str(calf.name), str(foot.name)],
        }

        knee = rig.KneeBone(*SERVICES, jal.volumeBone)
        chain = knee.create_bones(thigh, calf, foot, 0.08, 5.0, 0.01, 2.0)
        if chain is None:
            sideOut["error"] = "create_bones None"
            out[side] = sideOut
            continue
        sideOut["allBones"] = [str(b.name) for b in chain.bones if rt.isValidNode(b)]
        sideOut["parameters"] = repr(chain.parameters)
        volBones = _volume_bones(chain)
        sideOut["restVolumeBones"] = [_describe_bone(b) for b in volBones]

        sideOut["bend"] = _bend_calf(calf, -60.0)
        sideOut["bentVolumeBones"] = [_describe_bone(b) for b in volBones]

        # 상수 교체 호출 형태 비교. 헤드리스 Biped 이름에는 FrontBack 파트가 없어
        # 두 볼륨 본 이름이 같다(1차 실행 실측) -> transScale이 Back Push(2.0)인 본을 대상으로 한다.
        targets = [
            b for b in volBones
            if abs(float(_script_ctrl(b).getConstant("transScale")) - 2.0) < 1e-6
        ]
        sideOut["volumeBoneOrder"] = [
            float(_script_ctrl(b).getConstant("transScale")) for b in volBones
        ]
        sideOut["backTarget"] = str(targets[0].name) if targets else None
        if targets:
            ctrl = _script_ctrl(targets[0])
            attempts = {}
            attempts["setConstant_4"] = _try(lambda: ctrl.setConstant("volumeSize", rt.Float(4.0)))
            attempts["after_setConstant"] = _const(ctrl, "volumeSize")
            attempts["SetConstant_3"] = _try(lambda: ctrl.SetConstant("volumeSize", 3.0))
            attempts["after_SetConstant"] = _const(ctrl, "volumeSize")
            attempts["addConstant_2"] = _try(lambda: ctrl.addConstant("volumeSize", rt.Float(2.0)))
            attempts["after_addConstant"] = _const(ctrl, "volumeSize")
            # 최종적으로 4.0으로 맞춘 뒤 굽힘 상태의 출력을 다시 본다.
            attempts["reset_4"] = _try(lambda: ctrl.setConstant("volumeSize", rt.Float(4.0)))
            attempts["update"] = _try(lambda: ctrl.update())
            sideOut["attempts"] = attempts
            sideOut["bentAfterSet"] = [_describe_bone(b) for b in volBones]

        sideOut["unbend"] = _bend_calf(calf, 60.0)
        sideOut["restAfterSet"] = [_describe_bone(b) for b in volBones]
        out[side] = sideOut
    return out


try:
    result = main()
except Exception:  # noqa: BLE001
    result = {"error": traceback.format_exc()}

OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
