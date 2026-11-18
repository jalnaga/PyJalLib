# -*- coding: utf-8 -*-
"""UE5 왕복 비교기(`tests/_muscleRoundtrip.py`)의 판별력 (Type A).

비교기는 새로 만든 측정 도구다 - 도구가 틀리면 왕복 판정의 수치는 주장일 뿐이다.
합성 데이터로 다음을 단정한다.

- 같은 변형이면 오차 0 (공허하지 않게: 스케일이 실제로 0.5·1.5로 변하는 데이터)
- UE가 스케일을 잃으면(2026-11-10 실측의 Max squash 방식 증상: 길이 오차 15, 반경 오차 4) 잡는다
- 넙본 위치는 Y를 뒤집어 비교한다(뒤집지 않은 UE 값은 잡는다)
- 본을 못 찾으면 실패, 공백이 `_`로 바뀐 이름은 대응한다
- 프레임이 빠지면 실패
"""

import copy
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _muscleRoundtrip as rtc  # noqa: E402

FRAMES = [0, 1, 2]
SCALES = {0: 1.0, 1: 0.5, 2: 1.5}
MUSCLE = "Bip001 L UpperArm Muscle 00"
NUB = "Bip001 L UpperArm Muscle 01"
TUBE = "Tube 00"
REST_LEN = 30.0
RADIUS = 4.0


def _rest_verts():
    """X축 0..30, 반경 4인 원기둥 점(링 4개 x 8방향)."""
    verts = []
    for ring in range(4):
        x = REST_LEN * ring / 3.0
        for side in range(8):
            angle = 2.0 * math.pi * side / 8.0
            verts.append([x, RADIUS * math.cos(angle), RADIUS * math.sin(angle)])
    return verts


def _max_case():
    """Max 단계 형식의 합성 케이스. 본은 원점·X축, 스케일 [s, 1/s, 1/s], 넙본은 y=+3에서 끝을 따라간다."""
    data = {}
    for frame in FRAMES:
        s = SCALES[frame]
        verts = [[v[0] * s, v[1] / s, v[2] / s] for v in _rest_verts()]
        data[str(frame)] = {
            "bones": {
                MUSCLE: {
                    "world": [[s, 0, 0], [0, 1 / s, 0], [0, 0, 1 / s], [0, 0, 0]],
                    "localScale": [s, 1 / s, 1 / s],
                }
            },
            "nubs": {NUB: [REST_LEN * s, 3.0, 0.0]},
            "tubes": {TUBE: verts},
        }
    return {"frames": FRAMES, "muscles": [MUSCLE], "nubs": [NUB], "tubes": {TUBE: MUSCLE}, "data": data}


def _trs(inT, inS, inQ=(0.0, 0.0, 0.0, 1.0)):
    return {"t": list(inT), "q": list(inQ), "s": list(inS)}


def _ue_pass(inScaleLost=False, inNubFlip=True, inMuscleName=MUSCLE):
    """UE 단계 형식의 합성 패스. 기본은 Max와 같은 변형(Y 반전 반영)."""
    frames = {}
    for frame in FRAMES:
        s = 1.0 if inScaleLost else SCALES[frame]
        scale = (s, 1 / s, 1 / s)
        nubY = -3.0 if inNubFlip else 3.0
        frames[str(frame)] = {
            inMuscleName: {"local": _trs((0, 0, 0), scale), "world": _trs((0, 0, 0), scale)},
            NUB: {"local": _trs((REST_LEN, 0, 0), (1, 1, 1)),
                  "world": _trs((REST_LEN * SCALES[frame], nubY, 0), (1, 1, 1))},
        }
    return {"frames": frames}


def test_identical_transform_gives_zero_error():
    """같은 변형이면 전 항목 오차 0이고 전 프레임을 비교한다."""
    result = rtc.compare_case(_max_case(), _ue_pass())
    assert result["ok"], result
    assert result["comparedFrames"] == len(FRAMES)
    for key in ("maxLenErr", "maxRadErr", "maxNubErr", "maxScaleErr"):
        assert result[key] < 1e-9, (key, result)


def test_material_scale_actually_varies():
    """판별 재료: 합성 Max 데이터의 스케일이 실제로 1에서 벗어난다(오차 0이 공허하지 않음)."""
    ranges = rtc.max_scale_range(_max_case())
    low, high = ranges[MUSCLE]
    assert low < 0.8 and high > 1.2, ranges


def test_lost_scale_is_detected():
    """UE가 스케일을 잃으면 길이·반경·스케일 오차가 잡힌다(실측 증상: 길이 15 / 반경 4)."""
    result = rtc.compare_case(_max_case(), _ue_pass(inScaleLost=True))
    assert not result["ok"]
    assert abs(result["maxLenErr"] - 15.0) < 1e-6, result
    assert abs(result["maxRadErr"] - 4.0) < 1e-6, result
    assert result["maxScaleErr"] > 0.5, result


def test_nub_is_compared_with_y_flip():
    """넙본은 Y를 뒤집어 비교한다 - 뒤집지 않은 UE 값(y=+3)은 오차 6으로 잡힌다."""
    result = rtc.compare_case(_max_case(), _ue_pass(inNubFlip=False))
    assert not result["ok"]
    assert abs(result["maxNubErr"] - 6.0) < 1e-6, result


def test_missing_bone_fails():
    """UE에 근육 본이 없으면 실패하고 missing에 남는다."""
    result = rtc.compare_case(_max_case(), _ue_pass(inMuscleName="Other"))
    assert not result["ok"]
    assert result["missing"] == [MUSCLE]


def test_sanitized_bone_name_is_matched():
    """UE가 공백을 `_`로 바꾼 이름도 대응한다."""
    result = rtc.compare_case(_max_case(), _ue_pass(inMuscleName="Bip001_L_UpperArm_Muscle_00"))
    assert result["ok"], result
    assert result["mapping"][MUSCLE] == "Bip001_L_UpperArm_Muscle_00"


def test_missing_frame_fails():
    """UE 쪽에 프레임이 빠지면 비교 프레임 수가 모자라 실패한다."""
    uePass = _ue_pass()
    del uePass["frames"]["2"]
    result = rtc.compare_case(_max_case(), uePass)
    assert not result["ok"]
    assert result["comparedFrames"] == len(FRAMES) - 1


def test_qrot_quarter_turn():
    """회전 보조 함수: Z축 90도 회전이 X를 Y로 보낸다(쿼터니언 x, y, z, w)."""
    half = math.sqrt(0.5)
    rotated = rtc.qrot((0.0, 0.0, half, half), [1.0, 0.0, 0.0])
    assert all(abs(a - b) < 1e-9 for a, b in zip(rotated, [0.0, 1.0, 0.0])), rotated
    back = rtc.qrot(rtc.qinv((0.0, 0.0, half, half)), rotated)
    assert all(abs(a - b) < 1e-9 for a, b in zip(back, [1.0, 0.0, 0.0])), back


def test_rotated_bone_rigid_motion_keeps_metrics():
    """본이 회전·이동해도(같은 스케일) 길이·반경 비교가 0이다 - Max 쪽도 같은 강체 변형을 준다."""
    half = math.sqrt(0.5)
    quat = (0.0, 0.0, half, half)  # Z축 90도 (UE 좌표)
    maxCase = _max_case()
    uePass = _ue_pass()
    for frame in FRAMES:
        key = str(frame)
        s = SCALES[frame]
        # UE: 0프레임은 원점·무회전(바인드), 이후 프레임은 회전 + 이동
        if frame != 0:
            world = uePass["frames"][key][MUSCLE]["world"]
            world["q"] = list(quat)
            world["t"] = [10.0, 20.0, 5.0]
            # Max(Y 반전 좌표)에서 같은 강체 변형: UE 점 p -> R p + t 를 Max로 되돌린다
            maxVerts = []
            for v in maxCase["data"][key]["tubes"][TUBE]:
                ue = rtc.flip_y(v)
                moved = rtc.qrot(quat, ue)
                moved = [moved[i] + world["t"][i] for i in range(3)]
                maxVerts.append(rtc.flip_y(moved))
            maxCase["data"][key]["tubes"][TUBE] = maxVerts
            axisUe = rtc.qrot(quat, [s, 0, 0])
            maxCase["data"][key]["bones"][MUSCLE]["world"] = [
                rtc.flip_y(axisUe), [0, 0, 0], [0, 0, 0], rtc.flip_y(world["t"])
            ]
    result = rtc.compare_case(maxCase, copy.deepcopy(uePass))
    assert result["maxLenErr"] < 1e-9 and result["maxRadErr"] < 1e-9, result
