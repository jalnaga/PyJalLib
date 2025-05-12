#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UE 모듈 - 3ds Max에서 Unreal Engine5용으로 관련된 기능
"""


import os

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .anim import Anim
from .name import Name
from .bone import Bone
from .helper import Helper
from .constraint import Constraint
from .bip import Bip


class UE:
    """
    UE 관련 기능을 위한 클래스
    3DS Max에서 Unreal Engine5용으로 관련된 기능을 제공합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None, bipService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim, helperService=self.helper, constraintService=self.const)