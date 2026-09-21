#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""릭 파트 서브패키지 - 캐릭터 릭의 보조 본 셋업을 만드는 클래스들.

`pyjallib.max`의 릭 파트 14종과 그 산출물인 `BoneChain`을 모은다. 전에는
`pyjallib/max/` 최상위에 15개 파일이 흩어져 있었고, 같은 보일러플레이트
(서비스 폴백·`reset()`·positional 파라미터 언패킹·소문자 전파)를 14번 반복했다.

구조:
    boneChain.py   생성 결과를 담는 값 객체
    rigPart.py     `_RigPartBase` - 공통 골격. `PARAM_SPEC` 표로 구동된다
    limbVolume.py  `_LimbVolumePart` - elbow/wrist/ankle/inguinal의 공통 본체
    <part>.py      각 파트

`pyjallib.max`와 `Header`가 쓰는 **공개 이름은 바뀌지 않는다** - 이 패키지가
같은 클래스명을 re-export하고, `Header`의 속성명(`jal.elbow` 등)도 그대로다.
"""

from .boneChain import BoneChain
from .rigPart import _RigPartBase
from .volumeBone import VolumeBone
from .limbVolume import _LimbVolumePart
from .elbow import Elbow
from .wrist import Wrist
from .ankle import Ankle
from .inguinal import Inguinal
from .twistBone import TwistBone
from .kneeBone import KneeBone
from .hip import Hip
from .chest import Chest
from .armpit import Armpit
from .shoulder import Shoulder
from .autoClavicle import AutoClavicle
from .groinBone import GroinBone
from .jacketPanel import JacketPanel

__all__ = [
    "BoneChain",
    "_RigPartBase",
    "_LimbVolumePart",
    "VolumeBone",
    "Elbow",
    "Wrist",
    "Ankle",
    "Inguinal",
    "TwistBone",
    "KneeBone",
    "Hip",
    "Chest",
    "Armpit",
    "Shoulder",
    "AutoClavicle",
    "GroinBone",
    "JacketPanel",
]
