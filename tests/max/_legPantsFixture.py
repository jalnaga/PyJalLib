# -*- coding: utf-8 -*-
"""다리 + 관 바지 합성 픽스처 (Type C 공용) - 가려진 면 추출·클립 메쉬 테스트가 **import로** 공유한다.

몸 = 다리 원기둥(r 5, z 0..40) + 엉덩이 박스(z 34..42) + 발 박스(z -4..2), 한 Editable Poly.
바지 = Tube r 12..12.5, z 1..35 - 위아래가 열린 관이지만 **양끝이 박스 안으로 1씩 묻힌다.**

양끝을 묻는 이유(2026-10-19 실행 이력, 이후 2회 재발): 관 끝과 박스 사이에 틈을 두면 바깥에서 바짓가랑이 안을
비스듬히 들여다보는 시선이 실제로 생겨 깊은 면도 정의상 "보임"이다. 새 테스트 파일마다 픽스처를 처음부터 다시
만들다 이 조건을 세 번 빠뜨렸다 - 그래서 복붙이 아니라 이 모듈을 import한다(learnings 2026-10-21 MaskBake).
"""

from pymxs import runtime as rt


def reset():
    """새 씬."""
    rt.resetMaxFile(rt.Name("noPrompt"))


def poly(inNode):
    """Editable Poly로 바꾼다."""
    rt.convertToPoly(inNode)
    return inNode


def make_body(inOffsetX=0.0, inWithBoxes=True):
    """몸(다리 + 엉덩이·발 박스) - 다리만 x로 inOffsetX만큼 민다(박스는 원점 중심)."""
    leg = poly(rt.Cylinder(radius=5.0, height=40.0, heightsegs=16, sides=16, capsegs=1))
    leg.pos = rt.Point3(inOffsetX, 0.0, 0.0)
    leg.name = "Body"
    if inWithBoxes:
        hip = poly(rt.Box(length=30.0, width=30.0, height=8.0))
        hip.pos = rt.Point3(0.0, 0.0, 34.0)
        foot = poly(rt.Box(length=30.0, width=30.0, height=6.0))
        foot.pos = rt.Point3(0.0, 0.0, -4.0)
        rt.polyop.attach(leg, hip)
        rt.polyop.attach(leg, foot)
    return leg


def make_pants(inHeightSegs=1):
    """관 바지. inHeightSegs: 높이 분할(1 = 가려진 면 테스트 원래 형태, 클립 메쉬는 버텍스가 관 가운데에도 있어야 한다)."""
    tube = poly(rt.Tube(radius1=12.5, radius2=12.0, height=34.0, sides=32, heightsegs=inHeightSegs, capsegs=1))
    tube.pos = rt.Point3(0.0, 0.0, 1.0)
    tube.name = "Pants"
    return tube
