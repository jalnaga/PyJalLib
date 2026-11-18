# -*- coding: utf-8 -*-
"""근육 본 UE5 왕복 비교기 (순수 파이썬 - DCC 없이 import된다).

`run_muscle_bone_roundtrip.py`가 Max 단계 JSON과 UE5 단계 JSON을 이것으로 비교하고,
`tests/test_muscle_roundtrip_compare.py`(Type A)가 이 비교기 자체의 판별력을 지킨다.

## 무엇을 비교하는가 (2026-11-10 실측 프로브와 같은 방법)

- **메쉬 근육축 길이·최대 반경**: Max 쪽은 실제 스킨 결과 버텍스(`snapshotAsMesh`)를 본의 월드
  원점·X축에 투영해 잰다. UE 쪽은 버텍스를 직접 읽을 수 없어 **같은 선형 스키닝 식**으로
  만든다 - 메쉬는 본 하나에 100% 스킨이므로 `v_f = W_f * inverse(W_0) * v_0`(TRS)이고,
  v_0은 Max 0프레임 버텍스(= 바인드 포즈)를 UE 좌표로 옮긴 것이다. 엔진 사이에 갈리는 것은
  본 트랜스폼이고 스키닝 식은 같다 - UE 쪽 수치가 Max와 같으면 본 트랜스폼이 같은 변형을 낸다.
- **넙본 월드 위치**, **근육 본 로컬 스케일**(부모 = 루트 헬퍼 기준).

좌표: UE = Max의 Y 반전(FBX 임포트 변환, 단위 cm 동일). 길이·반경은 반전에 불변이고 위치만
Y를 뒤집어 비교한다.

## 이름 대응

FBX/UE가 본 이름의 공백 등을 바꿀 수 있어, 정확히 같은 이름이 없으면 영숫자 외 문자를 `_`로
접은 소문자 키로 대응한다. 대응하지 못한 본은 `missing`에 남고 비교는 실패한다.
"""

import math
import re

#: 허용 오차
TOLERANCE = 1e-3


def qrot(inQ, inV):
    """쿼터니언 (x, y, z, w)로 벡터를 회전한다(v' = q v q*)."""
    x, y, z, w = inQ
    tx = 2.0 * (y * inV[2] - z * inV[1])
    ty = 2.0 * (z * inV[0] - x * inV[2])
    tz = 2.0 * (x * inV[1] - y * inV[0])
    return [
        inV[0] + w * tx + (y * tz - z * ty),
        inV[1] + w * ty + (z * tx - x * tz),
        inV[2] + w * tz + (x * ty - y * tx),
    ]


def qinv(inQ):
    """단위 쿼터니언의 역."""
    return [-inQ[0], -inQ[1], -inQ[2], inQ[3]]


def axis_metrics(inVerts, inOrigin, inAxis):
    """버텍스를 축에 투영한 길이 구간(max - min)과 축에서의 최대 거리.

    Returns:
        tuple: (길이, 최대 반경)
    """
    norm = math.sqrt(sum(a * a for a in inAxis))
    axis = [a / norm for a in inAxis]
    lens, rads = [], []
    for vert in inVerts:
        p = [vert[i] - inOrigin[i] for i in range(3)]
        t = sum(p[i] * axis[i] for i in range(3))
        lens.append(t)
        rads.append(math.sqrt(max(0.0, sum(c * c for c in p) - t * t)))
    return max(lens) - min(lens), max(rads)


def flip_y(inV):
    """Max 좌표 -> UE 좌표(Y 반전)."""
    return [inV[0], -inV[1], inV[2]]


def name_key(inName: str) -> str:
    """이름 대응 키 - 영숫자 외 문자를 `_`로 접은 소문자."""
    return re.sub(r"[^0-9a-zA-Z]+", "_", inName).strip("_").lower()


def match_bone_names(inMaxNames, inUeNames) -> tuple:
    """Max 본 이름 -> UE 본 이름 대응.

    Returns:
        tuple: (대응 dict, 못 찾은 Max 이름 목록)
    """
    ueSet = set(inUeNames)
    ueByKey = {}
    for name in inUeNames:
        ueByKey.setdefault(name_key(name), []).append(name)
    mapping, missing = {}, []
    for name in inMaxNames:
        if name in ueSet:
            mapping[name] = name
            continue
        candidates = ueByKey.get(name_key(name), [])
        if len(candidates) == 1:
            mapping[name] = candidates[0]
        else:
            missing.append(name)
    return mapping, missing


def ue_skinned_verts(inRestVertsUe, inW0, inWf):
    """본 하나 100% 선형 스키닝: v_f = W_f * inverse(W_0) * v_0 (UE TRS: 스케일 -> 회전 -> 이동)."""
    out = []
    for vert in inRestVertsUe:
        local = qrot(qinv(inW0["q"]), [vert[i] - inW0["t"][i] for i in range(3)])
        local = [local[i] / inW0["s"][i] for i in range(3)]
        scaled = [local[i] * inWf["s"][i] for i in range(3)]
        rotated = qrot(inWf["q"], scaled)
        out.append([rotated[i] + inWf["t"][i] for i in range(3)])
    return out


def compare_case(inMax: dict, inUePass: dict) -> dict:
    """한 케이스·한 임포트 패스를 프레임별로 비교한다.

    Args:
        inMax: Max 단계 케이스 JSON
            {"frames": [...], "muscles": [...], "nubs": [...](근육 본과 같은 순서), "tubes": {tube: bone},
             "data": {"<f>": {"bones": {name: {"world": [r1, r2, r3, r4], "localScale": [..]}},
                              "nubs": {name: [x, y, z]}, "tubes": {tube: [[x, y, z], ...]}}}}
        inUePass: UE 단계 패스 JSON {"frames": {"<f>": {ueBone: {"local": trs, "world": trs}}}}

    Returns:
        dict: comparedFrames / missing / mapping / max{Len,Rad,Nub,Scale}Err / worst / ok
    """
    ueFrames = inUePass.get("frames", {})
    firstUe = ueFrames.get(str(inMax["frames"][0]), {})
    wanted = list(inMax["muscles"]) + list(inMax["nubs"])
    mapping, missing = match_bone_names(wanted, list(firstUe.keys()))

    result = {
        "comparedFrames": 0,
        "expectedFrames": len(inMax["frames"]),
        "missing": missing,
        "mapping": mapping,
        "maxLenErr": 0.0,
        "maxRadErr": 0.0,
        "maxNubErr": 0.0,
        "maxScaleErr": 0.0,
        "worst": {},
    }
    if missing:
        result["ok"] = False
        return result

    frame0 = str(inMax["frames"][0])
    restUe = {tube: [flip_y(v) for v in inMax["data"][frame0]["tubes"][tube]] for tube in inMax["tubes"]}

    def bump(inKey, inValue, inFrame, inWhat):
        if inValue > result[inKey]:
            result[inKey] = inValue
            result["worst"][inKey] = {"frame": inFrame, "what": inWhat, "value": inValue}

    for frame in inMax["frames"]:
        key = str(frame)
        maxFrame = inMax["data"].get(key)
        ueFrame = ueFrames.get(key)
        if maxFrame is None or ueFrame is None:
            continue
        for tube, bone in inMax["tubes"].items():
            world = maxFrame["bones"][bone]["world"]
            maxLen, maxRad = axis_metrics(maxFrame["tubes"][tube], world[3], world[0])
            ue0 = ueFrames[frame0][mapping[bone]]["world"]
            ueF = ueFrame[mapping[bone]]["world"]
            verts = ue_skinned_verts(restUe[tube], ue0, ueF)
            ueLen, ueRad = axis_metrics(verts, ueF["t"], qrot(ueF["q"], [1.0, 0.0, 0.0]))
            bump("maxLenErr", abs(maxLen - ueLen), frame, f"{tube} Max {maxLen:.4f} UE {ueLen:.4f}")
            bump("maxRadErr", abs(maxRad - ueRad), frame, f"{tube} Max {maxRad:.4f} UE {ueRad:.4f}")
        for bone in inMax["muscles"]:
            maxScale = maxFrame["bones"][bone]["localScale"]
            ueScale = [abs(c) for c in ueFrame[mapping[bone]]["local"]["s"]]
            bump("maxScaleErr", max(abs(maxScale[i] - ueScale[i]) for i in range(3)), frame,
                 f"{bone} Max {maxScale} UE {ueScale}")
        for nub in inMax["nubs"]:
            nubUe = ueFrame[mapping[nub]]["world"]["t"]
            nubMax = flip_y(maxFrame["nubs"][nub])
            bump("maxNubErr", math.sqrt(sum((nubMax[i] - nubUe[i]) ** 2 for i in range(3))), frame,
                 f"{nub} Max {nubMax} UE {nubUe}")
        result["comparedFrames"] += 1

    result["ok"] = (
        result["comparedFrames"] == result["expectedFrames"]
        and all(result[k] <= TOLERANCE for k in ("maxLenErr", "maxRadErr", "maxNubErr", "maxScaleErr"))
    )
    return result


def max_scale_range(inMax: dict) -> dict:
    """판별 재료 확인 - 근육 본마다 프레임 전체의 로컬 X 스케일 최소·최대."""
    ranges = {}
    for bone in inMax["muscles"]:
        values = [inMax["data"][str(f)]["bones"][bone]["localScale"][0] for f in inMax["frames"]]
        ranges[bone] = (min(values), max(values))
    return ranges
