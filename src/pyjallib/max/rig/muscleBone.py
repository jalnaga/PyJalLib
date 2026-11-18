#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""근육 본 모듈 - 본 스케일로 근육의 늘고 줄어듦을 흉내 내는 릭 파트 2종.

원본은 JalTools HandyTool의 MaxScript `muscleBone.ms`(`_MuscleBone` 구조체)다. 이 모듈은
그것을 파이썬으로 옮기되 아래 결정을 따른다(2026-11-10).

- `MuscleBone`: 시작·끝 노드 두 개로 근육 본 1개를 만든다. 스플라인이 없다.
- `MuscleBoneChain`: 스플라인(Line/SplineShape) 하나로 근육 본 N개(N >= 2)를 만든다.

## 스케일 방식 - Max 본 squash를 쓰지 않는다

Max 본의 `boneScaleType = #squash` 늘림·눌림은 `node.transform`이 아니라 `objectTransform`에만
실려 FBX에 기록되지 않는다(2026-11-10 실측: UE5에서 길이 오차 15.0·반경 오차 4.0). 그래서 근육
본은 `boneFreezeLength = True`, `boneScaleType = none`으로 두고 **Scale 컨트롤러(Scale_Script)가
실제 노드 스케일 `[s, s^-k, s^-k]`를 낸다.** s = 현재 근육 길이 / 생성 시 길이, k = `inSquashExponent`
(1.0 = Max squash와 같은 단면 1/s, 0.5 = 부피 보존).

## 계층 - 평평하게

비균등 스케일이 자식에게 전파되면 Max(전단 있음)와 UE5(전단 없음)가 갈라진다. 그래서 체인의 근육
본은 서로 잇지 않고 **전부 루트 헬퍼 직속**이다. 근육 본 아래에는 자기 넙본 하나만 둔다(넙본은 축
정렬이라 전단이 생기지 않는다). 루트 헬퍼는 부모가 없고 몸 본 연결은 사용자가 한다. 소스 노드는
위치·모양 기준으로만 쓰고 그 아래로 링크하지 않는다.

## 회전 - 이전 프레임 기준 최소 회전(aim) + 롤

원본 `create_chain`(LookAtType 2)은 헬퍼 i를 헬퍼 i-1 기준으로 쿼터니언 aim하고 그 위에 롤 평균
층(처음·끝 컨트롤의 X축 비틀림)을 얹는다. 이 모듈은 같은 의미를 **근육 본의 회전 스크립트 하나**로
만든다.

    근육 본 i 회전(루트 공간) = Rx(롤_i) * Swing_i * 이전 프레임
    이전 프레임 = 근육 본 i-1 (i = 0은 루트 헬퍼)
    Swing_i     = 이전 프레임의 X축을 (헬퍼 i -> 헬퍼 i+1) 방향으로 돌리는 최소 회전
    롤_0        = 첫 컨트롤의 루트 기준 X축 비틀림
    롤_i (i>=1) = 끝 컨트롤의 첫 컨트롤 기준 X축 비틀림(생성 시 값을 뺀 증분) / (N - 1)

X축 비틀림은 원본과 같이 XYX 오일러 분해의 첫째·셋째 각의 합이다(양끝에 X 회전을 곱하면 정확히
더해진다). 원본과 다른 점:

- 원본은 aim을 헬퍼의 회전에 걸고 본을 Orientation Constraint로 붙였다. 헬퍼 회전 스크립트가
  자기 위치 컨트롤러 값(`posThisCtrl.value`)을 읽으면 경로 제약 값의 좌표계가 모호해져서, 이 모듈은
  aim을 근육 본 회전에 직접 건다(본 i는 헬퍼 i, i+1과 본 i-1만 참조하므로 순환이 없다). 수동 조정
  층은 근육 본 회전 리스트(Euler_XYZ)와 헬퍼 위치 리스트(Position_XYZ)에 있다.
- 체인 롤의 i >= 1 항은 생성 시의 비틀림을 빼서 레스트에서 0이 되게 했다(원본은 절댓값).

## 스플라인 - 소스에 직접 Spline_IK_Control

사용자가 준 스플라인에 직접 Spline_IK_Control을 걸고(원본 방식), 매듭마다 컨트롤 헬퍼를 둔다.
이 파트가 건 모디파이어는 이름 `MODIFIER_NAME`으로 표시한다. 재생성(`create_bones_from_chain`)은
옛 체인을 지운 뒤 헬퍼가 모두 사라진 그 모디파이어를 새것으로 교체한다. `BoneChain.delete()`는
스플라인 노드를 지우지 않는다(체인 노드 목록에 없다).
"""

import math
from typing import Optional

from pymxs import runtime as rt

from .boneChain import BoneChain, _get_logger
from .rigPart import _RigPartBase

#: 이 파트가 소스 스플라인에 건 Spline_IK_Control의 이름. 재생성 때 교체 대상을 알아보는 표시다.
MODIFIER_NAME = "Muscle Spline IK"

#: 이름 RealName 접미사. 소스 RealName이 소문자로 시작하면 소문자로 쓴다.
_SUFFIX_MUSCLE = "Muscle"
_SUFFIX_NUB = "MuscleNub"
_SUFFIX_ROOT = "MuscleRoot"

#: 길이·방향 판정 하한
_EPSILON = 1e-4


# ---------------------------------------------------------------------------
# 순수 계산 (pymxs 값 없이 - tests/test_muscle_bone_internal.py가 지킨다)
# ---------------------------------------------------------------------------


def twist_sum_degrees(inRow1, inRow2, inRow3) -> float:
    """회전 행렬의 X축 비틀림(XYX 오일러 첫째·셋째 각의 합)을 도 단위로 돌려준다.

    Max 행 벡터 규약(M = Rx(a) * Ry(b) * Rx(c), 행 = 축의 상)에서 a + c를 구한다. 양쪽에 X 회전을
    곱하면(Rx(g) * M * Rx(-h)) 합이 정확히 g - h만큼 바뀐다 - 원본 롤 층의
    `quatToEuler ... order:7`의 `rot.x + rot.z`와 같은 양이다. 회전 스크립트 컨트롤러 안의
    MaxScript(`_twist_script`)와 같은 식이며, 생성 시 레스트 값을 구할 때 쓴다.

    Args:
        inRow1: 행렬 1행 (x, y, z)
        inRow2: 행렬 2행
        inRow3: 행렬 3행

    Returns:
        float: (-180, 180] 범위의 비틀림 각(도)
    """
    rows = [_normalize(row) for row in (inRow1, inRow2, inRow3)]
    r1, r2, r3 = rows
    sinB = math.sqrt(r1[1] * r1[1] + r1[2] * r1[2])
    if sinB < 1e-6:
        angle = math.atan2(r2[2], r2[1])
    else:
        angle = math.atan2(r2[0], r3[0]) + math.atan2(r1[1], -r1[2])
    return wrap_degrees(math.degrees(angle))


def wrap_degrees(inAngle: float) -> float:
    """각을 (-180, 180] 범위로 접는다.

    Args:
        inAngle: 각(도)

    Returns:
        float: 접은 각(도)
    """
    return math.degrees(math.atan2(math.sin(math.radians(inAngle)), math.cos(math.radians(inAngle))))


def squash_scale(inStretch: float, inExponent: float) -> tuple:
    """근육 본 노드 스케일 `[s, s^-k, s^-k]`를 돌려준다(Scale_Script와 같은 식).

    Args:
        inStretch: s = 현재 길이 / 생성 시 길이
        inExponent: k

    Returns:
        tuple: (x, y, z) 스케일
    """
    stretch = max(inStretch, 1e-6)
    side = stretch ** (-inExponent)
    return (stretch, side, side)


def _normalize(inVec) -> tuple:
    """3차원 벡터를 정규화한다. 길이가 0이면 그대로 돌려준다."""
    length = math.sqrt(sum(c * c for c in inVec))
    if length < 1e-12:
        return tuple(float(c) for c in inVec)
    return tuple(float(c) / length for c in inVec)


def _float_literal(inValue: float) -> str:
    """MaxScript 실수 리터럴."""
    return f"{float(inValue):.9f}"


# ---------------------------------------------------------------------------
# 컨트롤러 스크립트 (MaxScript)
# ---------------------------------------------------------------------------


def _relative_positions_script() -> str:
    """루트 공간의 시작·끝 위치를 구하는 공통 앞부분."""
    return (
        "local mbRootTM = rootNode.transform\n"
        "local mbStart = (startNode.transform * inverse mbRootTM).translationpart\n"
        "local mbEnd = (endNode.transform * inverse mbRootTM).translationpart\n"
    )


def _scale_script(inRestLength: float, inExponent: float) -> str:
    """근육 본 Scale_Script 본문 - [s, s^-k, s^-k]."""
    return (
        "(\n"
        + _relative_positions_script()
        + f"local mbS = (length (mbEnd - mbStart)) / {_float_literal(inRestLength)}\n"
        "if mbS < 0.000001 do mbS = 0.000001\n"
        f"local mbT = pow mbS (-{_float_literal(inExponent)})\n"
        "[mbS, mbT, mbT]\n"
        ")"
    )


def _twist_script() -> str:
    """rollA 기준 rollB의 X축 비틀림(도)을 mbTwist에 담는 MaxScript(`twist_sum_degrees`와 같은 식)."""
    return (
        "local mbRm = rollB.transform * inverse rollA.transform\n"
        "local mbR1 = normalize mbRm.row1\n"
        "local mbR2 = normalize mbRm.row2\n"
        "local mbR3 = normalize mbRm.row3\n"
        "local mbSinB = sqrt (mbR1.y * mbR1.y + mbR1.z * mbR1.z)\n"
        "local mbTwist = 0.0\n"
        "if mbSinB < 0.000001 then mbTwist = atan2 mbR2.z mbR2.y\n"
        "else mbTwist = (atan2 mbR2.x mbR3.x) + (atan2 mbR1.y (-mbR1.z))\n"
    )


def _aim_script(inHasPrev: bool, inHasRoll: bool, inRestTwist: float = 0.0, inRollWeight: float = 1.0) -> str:
    """근육 본 회전 스크립트 본문 - 이전 프레임 기준 최소 회전 aim + X축 롤.

    참조(스크립트 변수): rootNode, startNode(헬퍼 i), endNode(헬퍼 i+1),
    inHasPrev면 prevNode(근육 본 i-1), inHasRoll이면 rollA·rollB(롤 기준·대상 컨트롤).
    값은 부모(루트 헬퍼) 공간의 회전이다.

    Args:
        inHasPrev: 이전 프레임이 근육 본 i-1인지(False면 루트 헬퍼)
        inHasRoll: 롤 층을 쓰는지
        inRestTwist: 롤에서 뺄 생성 시 비틀림(도)
        inRollWeight: 롤 가중치

    Returns:
        str: 스크립트 본문
    """
    lines = ["(", _relative_positions_script()]
    if inHasPrev:
        lines.append(
            "local mbPm = prevNode.transform * inverse mbRootTM\n"
            "local mbPx = normalize mbPm.row1\n"
            "local mbPz = normalize (cross mbPx mbPm.row2)\n"
            "local mbPy = normalize (cross mbPz mbPx)\n"
            "local mbPrev = matrix3 mbPx mbPy mbPz [0,0,0]\n"
        )
    else:
        lines.append("local mbPrev = matrix3 1\n")
    lines.append(
        "local mbDir = mbEnd - mbStart\n"
        "local mbV = [1,0,0]\n"
        "if (length mbDir) > 0.000001 do mbV = normalize (mbDir * inverse mbPrev)\n"
        "local mbC = mbV.x\n"
        "local mbAxis = cross [1,0,0] mbV\n"
        "local mbSn = length mbAxis\n"
        "local mbSwing = matrix3 1\n"
        "if mbSn < 0.000001 then (\n"
        "    if mbC < 0 do mbSwing = matrix3 [-1,0,0] [0,-1,0] [0,0,1] [0,0,0]\n"
        ") else (\n"
        "    local mbK = mbAxis / mbSn\n"
        "    local mbOc = 1.0 - mbC\n"
        "    local mbRx = [1,0,0] * mbC + (cross mbK [1,0,0]) * mbSn + mbK * (mbK.x * mbOc)\n"
        "    local mbRy = [0,1,0] * mbC + (cross mbK [0,1,0]) * mbSn + mbK * (mbK.y * mbOc)\n"
        "    local mbRz = [0,0,1] * mbC + (cross mbK [0,0,1]) * mbSn + mbK * (mbK.z * mbOc)\n"
        "    mbSwing = matrix3 mbRx mbRy mbRz [0,0,0]\n"
        ")\n"
    )
    if inHasRoll:
        lines.append(_twist_script())
        lines.append(
            f"local mbRoll = (mod (mbTwist - {_float_literal(inRestTwist)} + 540.0) 360.0) - 180.0\n"
            f"mbRoll = mbRoll * {_float_literal(inRollWeight)}\n"
            "((rotateXMatrix mbRoll) * mbSwing * mbPrev).rotation\n"
        )
    else:
        lines.append("(mbSwing * mbPrev).rotation\n")
    lines.append(")")
    return "".join(lines)


# ---------------------------------------------------------------------------
# pymxs 보조
# ---------------------------------------------------------------------------


def _vec(inPoint3) -> tuple:
    """Point3를 튜플로 바꾼다."""
    return (float(inPoint3.x), float(inPoint3.y), float(inPoint3.z))


def _p3(inVec) -> "rt.Point3":
    """튜플을 Point3로 바꾼다."""
    return rt.Point3(float(inVec[0]), float(inVec[1]), float(inVec[2]))


def _cross(a, b) -> tuple:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _sub(a, b) -> tuple:
    return tuple(a[i] - b[i] for i in range(3))


def _length(a) -> float:
    return math.sqrt(_dot(a, a))


def _frame_matrix(inXDir, inPos, inUpHint=(0.0, 0.0, 1.0)) -> "rt.Matrix3":
    """X축 = inXDir, Z축 = inUpHint 쪽인 오른손 프레임 행렬.

    inUpHint가 X축과 거의 평행하면 월드 Y를 대신 쓴다.

    Args:
        inXDir: X축 방향
        inPos: 위치
        inUpHint: Z축이 향할 쪽

    Returns:
        rt.Matrix3: 프레임 행렬
    """
    xAxis = _normalize(inXDir)
    up = _normalize(inUpHint)
    if abs(_dot(xAxis, up)) > 0.99:
        up = (0.0, 1.0, 0.0) if abs(xAxis[1]) < 0.99 else (0.0, 0.0, 1.0)
    yAxis = _normalize(_cross(up, xAxis))
    zAxis = _normalize(_cross(xAxis, yAxis))
    return rt.Matrix3(_p3(xAxis), _p3(yAxis), _p3(zAxis), _p3(inPos))


def _set_rotation_script_with_manual(inNode, inScriptText: str, inNodes: dict) -> "rt.Rotation_Script":
    """회전 컨트롤러 = Rotation_List[스크립트, Euler_XYZ(수동 조정, 활성)].

    스크립트를 먼저 회전 컨트롤러로 걸고 리스트로 감싸야 첫 칸이 스크립트가 된다(기존 Euler_XYZ의
    초기 회전이 리스트에 끼어들지 않는다).

    Args:
        inNode: 대상 노드
        inScriptText: 스크립트 본문
        inNodes: 스크립트 변수 이름 -> 노드

    Returns:
        rt.Rotation_Script: 만든 스크립트 컨트롤러
    """
    script = rt.Rotation_Script()
    for varName, node in inNodes.items():
        script.addNode(varName, node)
    script.script = inScriptText
    rt.setPropertyController(inNode.controller, "Rotation", script)
    rotList = rt.Rotation_list()
    rt.setPropertyController(inNode.controller, "Rotation", rotList)
    rt.setPropertyController(rotList, "Available", rt.Euler_XYZ())
    rotList.setActive(rotList.count)
    return script


def _set_scale_script(inNode, inScriptText: str, inNodes: dict) -> "rt.Scale_Script":
    """Scale 컨트롤러를 Scale_Script로 바꾼다.

    Args:
        inNode: 대상 노드
        inScriptText: 스크립트 본문
        inNodes: 스크립트 변수 이름 -> 노드

    Returns:
        rt.Scale_Script: 만든 스크립트 컨트롤러
    """
    script = rt.Scale_Script()
    for varName, node in inNodes.items():
        script.addNode(varName, node)
    script.script = inScriptText
    rt.setPropertyController(inNode.controller, "Scale", script)
    return script


def _assign_path_with_manual(inNode, inSpline, inPercent: float) -> None:
    """위치 컨트롤러 = Position_List[Path_Constraint(고정 percent), Position_XYZ(수동 조정, 활성)].

    원본 `create_chain`의 경로 헬퍼 + ManCtrlsBool 구성이다.

    Args:
        inNode: 대상 헬퍼
        inSpline: 경로 스플라인
        inPercent: 경로 위 위치(0~100)
    """
    pathConst = rt.Path_Constraint()
    rt.setPropertyController(inNode.controller, "Position", pathConst)
    pathConst.appendTarget(inSpline, 100.0)
    rt.deleteKeys(rt.getPropertyController(pathConst, "percent"))
    pathConst.percent = float(inPercent)
    posList = rt.Position_list()
    rt.setPropertyController(inNode.controller, "Position", posList)
    rt.setPropertyController(posList, "Available", rt.Position_XYZ())
    posList.setActive(posList.count)


def _delete_nodes(inNodes) -> None:
    """유효한 노드만 지운다(생성 실패 시 정리용)."""
    valid = [node for node in inNodes if node is not None and rt.isValidNode(node)]
    if valid:
        rt.delete(rt.Array(*valid))


# ---------------------------------------------------------------------------
# 공통 골격
# ---------------------------------------------------------------------------


class _MusclePartBase(_RigPartBase):
    """근육 본 두 파트의 공통 - 이름 규칙과 근육 본·넙본 생성."""

    #: 마지막 생성 결과(작업 데이터). `create_bones()` 시작 때 `reset()`으로 비운다.
    WORK_DEFAULTS = {
        "bones": [],
        "helpers": [],
        "sourceBones": [],
    }

    def muscle_names(self, inRefName: str, inBoneCount: int, inCtrlCount: int = 0) -> dict:
        """이름 규칙으로 생성할 노드 이름을 만든다.

        R = 기준 이름의 RealName. 기준 이름의 다른 파트(Base·Side 등)는 유지한다.

            근육 본 i  = RealName R+"Muscle",     Index i
            넙본 i     = RealName R+"MuscleNub",  Index i
            헬퍼 i     = Type Dummy, RealName R+"Muscle", Index i (i = 0..N)
            루트 헬퍼  = Type Dummy, RealName R+"MuscleRoot", Index 0
            컨트롤 j   = Type Control, RealName R+"Muscle", Index j

        RealName이 소문자로 시작하면 접미사도 소문자로 붙인다("muscle" 등). Type 값은 naming
        설정의 값을 그대로 쓴다(소문자로 바꾸면 Type으로 읽히지 않는다).

        Args:
            inRefName: 기준 이름(inName 또는 첫 소스 노드 이름)
            inBoneCount: 근육 본 수 N
            inCtrlCount: 스플라인 컨트롤 수

        Returns:
            dict: muscles / nubs / helpers / ctrls (리스트), root (문자열)
        """
        realName = self.name.get_name("RealName", inRefName)
        lower = bool(realName) and realName[0].islower()

        def suffix(inText: str) -> str:
            return inText.lower() if lower else inText

        dummyType = self.name.get_name_part_value_by_description("Type", "Dummy")
        ctrlType = self.name.get_name_part_value_by_description("Type", "Control")

        def make(inSuffix: str, inType: Optional[str], inIndex: int) -> str:
            nodeName = self.name.replace_name_part("RealName", inRefName, realName + suffix(inSuffix))
            if inType:
                nodeName = self.name.replace_name_part("Type", nodeName, inType)
            return self.name.replace_name_part("Index", nodeName, str(inIndex))

        return {
            "muscles": [make(_SUFFIX_MUSCLE, None, i) for i in range(inBoneCount)],
            "nubs": [make(_SUFFIX_NUB, None, i) for i in range(inBoneCount)],
            "helpers": [make(_SUFFIX_MUSCLE, dummyType, i) for i in range(inBoneCount + 1)],
            "ctrls": [make(_SUFFIX_MUSCLE, ctrlType, j) for j in range(inCtrlCount)],
            "root": make(_SUFFIX_ROOT, dummyType, 0),
        }

    def create_point(self, inName: str, inSize: float, inColor: tuple, inParent=None, inTransform=None):
        """박스 모양 포인트 헬퍼를 만든다.

        Args:
            inName: 이름
            inSize: 크기
            inColor: 와이어 색 (r, g, b)
            inParent: 부모 노드
            inTransform: 월드 트랜스폼

        Returns:
            rt.Node: 포인트 헬퍼
        """
        point = self.helper.create_point(inName, size=inSize, boxToggle=True, crossToggle=False, pointColor=inColor)
        if inTransform is not None:
            point.transform = inTransform
        if inParent is not None:
            point.parent = inParent
        return point

    def build_muscles(
        self,
        inRoot,
        inHelpers: list,
        inNames: dict,
        inBoneSize: float,
        inSquashExponent: float,
        inRollNodes: Optional[list] = None,
    ) -> tuple:
        """헬퍼 위치로 근육 본 N개와 넙본 N개를 만들고 컨트롤러를 건다.

        근육 본 i: 부모 = 루트, 위치 = 헬퍼 i(Position Constraint), 회전 = aim 스크립트(이전 프레임 기준,
        롤 층 선택), 스케일 = Scale_Script [s, s^-k, s^-k]. 넙본 i: 부모 = 근육 본 i, 위치 = 헬퍼 i+1.

        Args:
            inRoot: 루트 헬퍼
            inHelpers: 헬퍼 N+1개 (현재 시간 위치가 레스트)
            inNames: `muscle_names()` 결과
            inBoneSize: 본 폭·높이
            inSquashExponent: k
            inRollNodes: 롤 층 [첫 컨트롤, 끝 컨트롤]. None이면 롤 없음

        Returns:
            tuple: (근육 본 리스트, 넙본 리스트, 생성한 노드 리스트)
        """
        created = []
        muscles, nubs = [], []
        rootUp = _vec(inRoot.transform.row3)
        helperPos = [_vec(helper.transform.row4) for helper in inHelpers]
        boneCount = len(inHelpers) - 1

        restTwist = 0.0
        if inRollNodes is not None:
            rel = inRollNodes[1].transform * rt.inverse(inRollNodes[0].transform)
            restTwist = twist_sum_degrees(_vec(rel.row1), _vec(rel.row2), _vec(rel.row3))

        for i in range(boneCount):
            start, end = helperPos[i], helperPos[i + 1]
            restLength = _length(_sub(end, start))
            if restLength < _EPSILON:
                raise RuntimeError(f"헬퍼 {i}·{i + 1} 사이 길이가 0이다(겹친 매듭)")
            xDir = _normalize(_sub(end, start))
            up = rootUp if abs(_dot(xDir, _normalize(rootUp))) < 0.99 else _vec(inRoot.transform.row2)
            normal = _p3(_cross(up, xDir))

            boneArray = self.bone.create_bone(
                [inHelpers[i], inHelpers[i + 1]], inNames["muscles"][i], end=False, size=inBoneSize,
                normals=[normal, normal],
            )
            muscle = boneArray[0]
            created.append(muscle)
            muscle.name = inNames["muscles"][i]
            muscle.parent = inRoot
            muscle.boneFreezeLength = True
            muscle.boneScaleType = rt.Name("none")

            nub = self.bone.create_nub_bone(inNames["nubs"][i], inBoneSize * 0.5)
            created.append(nub)
            nub.name = inNames["nubs"][i]
            nub.transform = rt.Matrix3(muscle.transform.row1, muscle.transform.row2, muscle.transform.row3, _p3(end))
            nub.parent = muscle

            self.const.assign_pos_const(muscle, inHelpers[i])
            scriptNodes = {"rootNode": inRoot, "startNode": inHelpers[i], "endNode": inHelpers[i + 1]}
            hasPrev = i > 0
            if hasPrev:
                scriptNodes["prevNode"] = muscles[i - 1]
            hasRoll = inRollNodes is not None
            rollRest, rollWeight = 0.0, 1.0
            if hasRoll:
                if i == 0:
                    scriptNodes["rollA"], scriptNodes["rollB"] = inRoot, inRollNodes[0]
                else:
                    scriptNodes["rollA"], scriptNodes["rollB"] = inRollNodes[0], inRollNodes[1]
                    rollRest = restTwist
                    rollWeight = 1.0 / float(boneCount - 1)
            _set_rotation_script_with_manual(
                muscle, _aim_script(hasPrev, hasRoll, rollRest, rollWeight), scriptNodes
            )
            _set_scale_script(
                muscle,
                _scale_script(restLength, inSquashExponent),
                {"rootNode": inRoot, "startNode": inHelpers[i], "endNode": inHelpers[i + 1]},
            )
            self.const.assign_pos_const(nub, inHelpers[i + 1])

            muscles.append(muscle)
            nubs.append(nub)
        return muscles, nubs, created

    @staticmethod
    def interleave(inMuscles: list, inNubs: list) -> list:
        """Bones 순서 [근육0, 넙0, 근육1, 넙1, ...]."""
        return [node for pair in zip(inMuscles, inNubs) for node in pair]


# ---------------------------------------------------------------------------
# MuscleBone - 본 1개
# ---------------------------------------------------------------------------


class MuscleBone(_MusclePartBase):
    """시작·끝 노드로 근육 본 1개를 만드는 클래스(스플라인 없음).

    구성: 루트 헬퍼(시작 위치, X축 = 끝 방향, 부모 없음) 아래에 헬퍼 0(시작)·끝 헬퍼(헬퍼 1)·근육 본.
    근육 본은 헬퍼 0 위치에서 끝 헬퍼를 aim하고, 넙본은 끝 헬퍼를 따른다. 끝 헬퍼를 움직이면
    근육 본 노드 스케일이 [s, s^-k, s^-k]로 바뀐다.
    """

    PARAM_SPEC = (
        ("inName", ""),
        ("inBoneSize", 2.0),
        ("inSquashExponent", 1.0),
    )

    SOURCE_SPEC = ("inStartObj", "inEndObj")

    def create_bones(
        self,
        inStartObj,
        inEndObj,
        inName: str = "",
        inBoneSize: float = 2.0,
        inSquashExponent: float = 1.0,
    ) -> Optional[BoneChain]:
        """시작·끝 노드 사이에 근육 본을 만든다.

        Args:
            inStartObj: 시작 노드(위치 기준)
            inEndObj: 끝 노드(위치 기준)
            inName: 기준 이름. 빈 문자열이면 시작 노드 이름을 쓴다.
            inBoneSize: 근육 본 폭·높이
            inSquashExponent: 단면 지수 k. 스케일 = [s, s^-k, s^-k]

        Returns:
            BoneChain | None: Bones = [근육 본, 넙본], Helpers = [루트, 헬퍼 0, 끝 헬퍼]. 실패하면 None
        """
        self.reset()
        if not self.validate_source_nodes(inStartObj, inEndObj):
            return None
        if rt.getHandleByAnim(inStartObj) == rt.getHandleByAnim(inEndObj):
            _get_logger().warning("MuscleBone: 시작 노드와 끝 노드가 같다")
            return None
        startPos = _vec(inStartObj.transform.row4)
        endPos = _vec(inEndObj.transform.row4)
        if _length(_sub(endPos, startPos)) < _EPSILON:
            _get_logger().warning("MuscleBone: 시작·끝 노드 위치가 같아 근육 길이가 0이다")
            return None

        refName = inName if inName else str(inStartObj.name)
        names = self.muscle_names(refName, 1)
        created = []
        try:
            rootTm = _frame_matrix(_sub(endPos, startPos), startPos)
            root = self.create_point(names["root"], inBoneSize * 1.5, (0, 255, 0), inTransform=rootTm)
            created.append(root)
            startHelper = self.create_point(
                names["helpers"][0], inBoneSize * 0.5, (0, 0, 255), inParent=root, inTransform=rootTm
            )
            created.append(startHelper)
            endTm = rt.Matrix3(rootTm.row1, rootTm.row2, rootTm.row3, _p3(endPos))
            endHelper = self.create_point(
                names["helpers"][1], inBoneSize * 0.5, (0, 0, 255), inParent=root, inTransform=endTm
            )
            created.append(endHelper)

            muscles, nubs, bonesCreated = self.build_muscles(
                root, [startHelper, endHelper], names, inBoneSize, inSquashExponent
            )
            created.extend(bonesCreated)
        except Exception as error:  # noqa: BLE001 - 만든 노드를 정리하고 None으로 실패한다
            _get_logger().error(f"MuscleBone: 생성 실패 - {type(error).__name__}: {error}")
            _delete_nodes(created)
            return None

        bones = self.interleave(muscles, nubs)
        helpers = [root, startHelper, endHelper]
        self.tag_as_skin_bones(bones + helpers, [inStartObj, inEndObj])
        self.bones, self.helpers, self.sourceBones = list(bones), list(helpers), [inStartObj, inEndObj]
        rt.redrawViews()

        result = self.build_result(
            bones,
            helpers,
            [inStartObj, inEndObj],
            {"inName": inName, "inBoneSize": inBoneSize, "inSquashExponent": inSquashExponent},
        )
        return BoneChain.from_result(result)


# ---------------------------------------------------------------------------
# MuscleBoneChain - 스플라인, 본 N개
# ---------------------------------------------------------------------------


class MuscleBoneChain(_MusclePartBase):
    """스플라인으로 근육 본 N개(N >= 2) 체인을 만드는 클래스.

    원본 HandyTool `create()`의 기본 경로(`assign_splineIK` 타입 1 + `create_chain`)를 옮긴다.

    - 소스 스플라인의 매듭마다 컨트롤 헬퍼(Ctrl)를 두고, 소스 스플라인에 직접 Spline_IK_Control을
      걸어 매듭이 컨트롤을 따르게 한다(탄젠트 없음, 매듭 smooth).
    - 헬퍼 i(i = 0..N)는 스플라인 위 i/N 지점(Path_Constraint) + 수동 조정 Position_XYZ.
    - 근육 본 i는 헬퍼 i 위치에서 헬퍼 i+1을 aim하고, 처음·끝 컨트롤의 X축 비틀림을 롤로 나눠 받는다.
    - 루트 헬퍼(부모 없음)는 첫 컨트롤과 같은 트랜스폼이고, 컨트롤·헬퍼·근육 본이 전부 그 직속이다.
    """

    PARAM_SPEC = (
        ("inName", ""),
        ("inLinkNum", 2),
        ("inBoneSize", 2.0),
        ("inSquashExponent", 1.0),
    )

    SOURCE_SPEC = ("inSpline",)

    def create_bones(
        self,
        inSpline,
        inName: str = "",
        inLinkNum: int = 2,
        inBoneSize: float = 2.0,
        inSquashExponent: float = 1.0,
    ) -> Optional[BoneChain]:
        """스플라인을 따라 근육 본 체인을 만든다.

        Args:
            inSpline: Line 또는 SplineShape 노드(첫 스플라인을 쓴다)
            inName: 기준 이름. 빈 문자열이면 스플라인 이름을 쓴다.
            inLinkNum: 근육 본 수 N (2 이상)
            inBoneSize: 근육 본 폭·높이
            inSquashExponent: 단면 지수 k. 스케일 = [s, s^-k, s^-k]

        Returns:
            BoneChain | None: Bones = [근육0, 넙0, 근육1, 넙1, ...],
                Helpers = [루트, 헬퍼 0..N, 컨트롤 0..매듭-1]. 실패하면 None
        """
        self.reset()
        if not self.validate_source_nodes(inSpline):
            return None
        baseClass = rt.classOf(inSpline.baseObject)
        if baseClass != rt.Line and baseClass != rt.SplineShape:
            _get_logger().warning(f"MuscleBoneChain: 소스가 Line/SplineShape가 아니다 ({baseClass})")
            return None
        if isinstance(inLinkNum, bool) or int(inLinkNum) != inLinkNum or int(inLinkNum) < 2:
            _get_logger().warning(f"MuscleBoneChain: inLinkNum은 2 이상의 정수여야 한다 ({inLinkNum!r})")
            return None
        linkNum = int(inLinkNum)
        if int(rt.numSplines(inSpline)) < 1 or int(rt.numKnots(inSpline, 1)) < 2:
            _get_logger().warning("MuscleBoneChain: 스플라인에 매듭이 2개 이상인 첫 스플라인이 없다")
            return None
        if not self._release_old_modifier(inSpline):
            return None

        knotCount = int(rt.numKnots(inSpline, 1))
        refName = inName if inName else str(inSpline.name)
        names = self.muscle_names(refName, linkNum, knotCount)
        created = []
        modifier = None
        try:
            ctrls = self._create_controls(inSpline, names["ctrls"], inBoneSize)
            created.extend(ctrls)
            modifier = self._assign_spline_ik(inSpline, ctrls)

            root = self.create_point(names["root"], inBoneSize * 1.5, (0, 255, 0), inTransform=ctrls[0].transform)
            created.append(root)
            for ctrl in ctrls:
                ctrl.parent = root

            helpers = []
            for i in range(linkNum + 1):
                helper = self.create_point(
                    names["helpers"][i], inBoneSize * 0.5, (0, 0, 255), inParent=root, inTransform=root.transform
                )
                created.append(helper)
                _assign_path_with_manual(helper, inSpline, 100.0 * i / linkNum)
                helpers.append(helper)

            # 경로 헬퍼를 지금 평가해 둔다. Spline_IK_Control은 생성 뒤 한 번 평가되기 전에 컨트롤에 첫 키가
            # 들어가면 그 뒤 시간 평가가 레스트 형상에 머문다(2026-11-10 배치 실측) - 여기서 평가가 끝난다.
            rt.classOf(inSpline)
            for helper in helpers:
                _ = helper.transform

            muscles, nubs, bonesCreated = self.build_muscles(
                root, helpers, names, inBoneSize, inSquashExponent, inRollNodes=[ctrls[0], ctrls[-1]]
            )
            created.extend(bonesCreated)
        except Exception as error:  # noqa: BLE001 - 만든 노드·모디파이어를 정리하고 None으로 실패한다
            _get_logger().error(f"MuscleBoneChain: 생성 실패 - {type(error).__name__}: {error}")
            _delete_nodes(created)
            if modifier is not None:
                self._remove_modifier(inSpline, modifier)
            return None

        bones = self.interleave(muscles, nubs)
        helperNodes = [root] + helpers + ctrls
        self.tag_as_skin_bones(bones + helperNodes, [inSpline])
        self.bones, self.helpers, self.sourceBones = list(bones), list(helperNodes), [inSpline]
        rt.redrawViews()

        result = self.build_result(
            bones,
            helperNodes,
            [inSpline],
            {
                "inName": inName,
                "inLinkNum": linkNum,
                "inBoneSize": inBoneSize,
                "inSquashExponent": inSquashExponent,
            },
        )
        return BoneChain.from_result(result)

    # ------------------------------------------------------------------
    # 스플라인 IK
    # ------------------------------------------------------------------

    @staticmethod
    def _spline_ik_modifiers(inSpline) -> list:
        """스플라인의 Spline_IK_Control 모디파이어 목록."""
        return [
            inSpline.modifiers[i]
            for i in range(int(inSpline.modifiers.count))
            if rt.classOf(inSpline.modifiers[i]) == rt.Spline_IK_Control
        ]

    def _release_old_modifier(self, inSpline) -> bool:
        """이 파트가 전에 건 Spline_IK_Control을 정리한다.

        헬퍼(컨트롤)가 모두 지워졌으면(옛 체인 삭제 뒤 - 재생성 경로) 지운다. 살아 있는 컨트롤이
        있으면 다른 근육 체인이 쓰고 있으므로 실패한다. 이 파트가 걸지 않은 Spline_IK_Control이
        있어도 매듭 구동이 겹치므로 실패한다.

        Args:
            inSpline: 소스 스플라인

        Returns:
            bool: 진행해도 되면 True
        """
        for modifier in self._spline_ik_modifiers(inSpline):
            if str(modifier.name) != MODIFIER_NAME:
                _get_logger().warning("MuscleBoneChain: 스플라인에 이미 다른 Spline_IK_Control이 있다")
                return False
            helperList = modifier.helper_list
            helperItems = list(helperList) if helperList is not None else []
            liveHelpers = [h for h in helperItems if h is not None and rt.isValidNode(h)]
            if liveHelpers:
                _get_logger().warning("MuscleBoneChain: 스플라인이 이미 살아 있는 근육 체인에 쓰이고 있다")
                return False
        for modifier in self._spline_ik_modifiers(inSpline):
            self._remove_modifier(inSpline, modifier)
        return True

    @staticmethod
    def _remove_modifier(inSpline, inModifier) -> None:
        """스플라인에서 모디파이어 하나를 지운다."""
        for i in range(int(inSpline.modifiers.count)):
            if rt.getHandleByAnim(inSpline.modifiers[i]) == rt.getHandleByAnim(inModifier):
                rt.deleteModifier(inSpline, i + 1)
                return

    def _create_controls(self, inSpline, inNames: list, inBoneSize: float) -> list:
        """매듭마다 컨트롤 헬퍼를 만든다(원본 `assign_splineIK`).

        컨트롤 트랜스폼: X축 = 매듭의 진행 방향 접선, Z축 = X x 월드 Y, 위치 = 매듭. 매듭은 smooth로
        바꾼다(원본 "탄젠트 없음" 경로).

        Args:
            inSpline: 소스 스플라인
            inNames: 컨트롤 이름(매듭 순)
            inBoneSize: 본 크기(컨트롤 크기 = 1.2배)

        Returns:
            list: 컨트롤 헬퍼
        """
        knotCount = len(inNames)
        for k in range(1, knotCount + 1):
            rt.setKnotType(inSpline, 1, k, rt.Name("smooth"))
        rt.updateShape(inSpline)

        knots = [_vec(rt.getKnotPoint(inSpline, 1, k)) for k in range(1, knotCount + 1)]
        ctrls = []
        for j in range(knotCount):
            tangent = self._knot_tangent(inSpline, j + 1, knots)
            zAxis = _cross(tangent, (0.0, 1.0, 0.0))
            if _length(zAxis) < 1e-6:
                zAxis = _cross(tangent, (0.0, 0.0, 1.0))
            zAxis = _normalize(zAxis)
            yAxis = _normalize(_cross(zAxis, tangent))
            tm = rt.Matrix3(_p3(tangent), _p3(yAxis), _p3(zAxis), _p3(knots[j]))
            ctrls.append(self.create_point(inNames[j], inBoneSize * 1.2, (255, 0, 0), inTransform=tm))
        return ctrls

    @staticmethod
    def _knot_tangent(inSpline, inKnot: int, inKnots: list) -> tuple:
        """매듭의 진행 방향 단위 접선. smooth 매듭의 핸들 방향, 핸들이 0이면 이웃 매듭 방향."""
        count = len(inKnots)
        knot = inKnots[inKnot - 1]
        outVec = _vec(rt.getOutVec(inSpline, 1, inKnot))
        inVec = _vec(rt.getInVec(inSpline, 1, inKnot))
        if inKnot == 1:
            tangent = _sub(outVec, knot)
        elif inKnot == count:
            tangent = _sub(knot, inVec)
        else:
            tangent = _sub(outVec, inVec)
        if _length(tangent) < 1e-6:
            prevKnot = inKnots[max(inKnot - 2, 0)]
            nextKnot = inKnots[min(inKnot, count - 1)]
            tangent = _sub(nextKnot, prevKnot)
        return _normalize(tangent)

    @staticmethod
    def _assign_spline_ik(inSpline, inCtrls: list):
        """소스 스플라인에 Spline_IK_Control을 걸고 컨트롤을 연결한다(링크 없음).

        Args:
            inSpline: 소스 스플라인
            inCtrls: 컨트롤 헬퍼(매듭 순)

        Returns:
            rt.Spline_IK_Control: 건 모디파이어
        """
        modifier = rt.Spline_IK_Control()
        rt.addModifier(inSpline, modifier)
        modifier.name = MODIFIER_NAME
        modifier.noLinking()
        modifier.helper_list = rt.Array(*inCtrls)
        return modifier
