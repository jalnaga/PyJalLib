#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JalTools 3DS 패키지
3DS Max 작업을 위한 모듈 모음
"""

# 모듈 임포트
from pyjallib.max.header import Header

from pyjallib.max.name import Name
from pyjallib.max.anim import Anim

from pyjallib.max.helper import Helper
from pyjallib.max.constraint import Constraint
from pyjallib.max.bone import Bone

from pyjallib.max.mirror import Mirror
from pyjallib.max.layer import Layer
from pyjallib.max.align import Align
from pyjallib.max.select import Select
from pyjallib.max.link import Link

from pyjallib.max.bip import Bip
from pyjallib.max.skin import Skin
from pyjallib.max.morph import Morph

from pyjallib.max.boneChain import BoneChain

from pyjallib.max.twistBone import TwistBone
from pyjallib.max.groinBone import GroinBone
from pyjallib.max.autoClavicle import AutoClavicle
from pyjallib.max.volumeBone import VolumeBone
from pyjallib.max.kneeBone import KneeBone
from pyjallib.max.hip import Hip

from pyjallib.max.ui.Container import Container

# 모듈 내보내기
__all__ = [
    'Header',
    'Name',
    'Anim',
    'Helper', 
    'Constraint',
    'Bone',
    'Mirror',
    'Layer',
    'Align',
    'Select',
    'Link',
    'Bip',
    'Skin',
    'Morph',
    'BoneChain',
    'TwistBone',
    'TwistBoneChain',
    'GroinBone',
    'GroinBoneChain',
    'AutoClavicle',
    'AutoClavicleChain',
    'VolumeBone',
    'VolumeBoneChain',
    'KneeBone',
    'Hip',
    'Container'
]
