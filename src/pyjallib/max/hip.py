#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hip 모듈 - 3ds Max용 Hip 관련 기능 제공
원본 MAXScript의 hip.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint


class Hip:
    """
    Hip 관련 기능을 제공하는 클래스.
    MAXScript의 _Hip 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, animService=None, helperService=None, boneService=None, constraintService=None):
        """
        클래스 초기화.
        
        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 관련 서비스 (제공되지 않으면 새로 생성)
            boneService: 뼈대 관련 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 관련 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 관련 서비스 (제공되지 않으면 새로 생성)
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.helper = helperService if helperService else Helper(nameService=self.name)
        self.const = constraintService if constraintService else Constraint(nameService=self.name, helperService=self.helper)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim, helperService=self.helper, constraintService=self.const)
        
        # 기본 속성 초기화
        self.boneSize = 2.0
        self.boneArray = []
        self.pelvisWeight = 60.0
        self.thighWeight = 40.0
        self.xAxisOffset = 0.1
        
        self.pelvis = None
        self.thigh = None
        self.thighTwist = None
        
        self.pelvisHelper = None
        
    def create_helper(self, inParent=None):
        pass