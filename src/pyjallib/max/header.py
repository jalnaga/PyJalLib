#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
헤더 모듈 - max 패키지의 인스턴스 관리
3DS Max가 실행될 때 메모리에 한번만 로드되는 패키지 인스턴스들을 관리
"""

import os

from .configPath import ConfigPath

from .name import Name
from .anim import Anim

from .helper import Helper
from .constraint import Constraint
from .bone import Bone

from .mirror import Mirror
from .layer import Layer
from .align import Align
from .select import Select
from .link import Link

from .bip import Bip
from .skin import Skin

from .twistBone import TwistBone
from .autoClavicle import AutoClavicle
from .groinBone import GroinBone
from .volumePreserveBone import VolumePreserveBone

from .morph import Morph

class Header:
    """
    JalLib.max 패키지의 헤더 모듈
    3DS Max에서 사용하는 다양한 기능을 제공하는 클래스들을 초기화하고 관리합니다.
    """
    _instance = None
    _config_path = None
    
    @classmethod
    def reset_instance(cls):
        """싱글톤 인스턴스를 재설정합니다."""
        cls._instance = None
    
    @classmethod
    def get_instance(cls, config_path=None):
        """
        싱글톤 패턴을 구현한 인스턴스 접근 메소드
        
        Args:
            config_path: ConfigPath 인스턴스, 처음 호출 시에만 필요
        """
        # 이미 인스턴스가 있고 새로운 config_path가 제공된 경우 인스턴스 재설정
        if cls._instance is not None and config_path is not None:
            cls.reset_instance()
            
        if cls._instance is None:
            if config_path is None:
                # 기본 ConfigPath 생성
                config_path = ConfigPath()
            cls._instance = cls(config_path)
        return cls._instance
    
    def __init__(self, configPath):
        """
        Header 클래스 초기화
        """
        self.configDir = configPath.configRootPath
        self.nameConfigDir = configPath.nameconfigPath

        self.name = Name(configPath=self.nameConfigDir)
        self.anim = Anim()

        self.helper = Helper(nameService=self.name)
        self.constraint = Constraint(nameService=self.name, helperService=self.helper)
        self.bone = Bone(nameService=self.name, animService=self.anim, helperService=self.helper, constraintService=self.constraint)

        self.mirror = Mirror(nameService=self.name, boneService=self.bone)
        self.layer = Layer()
        self.align = Align()
        self.sel = Select(nameService=self.name, boneService=self.bone)
        self.link = Link()

        self.bip = Bip(animService=self.anim, nameService=self.name, boneService=self.bone)
        self.skin = Skin()

        self.twistBone = TwistBone(nameService=self.name, animService=self.anim, constService=self.constraint, bipService=self.bip, boneService=self.bone)
        self.autoClavicle = AutoClavicle(nameService=self.name, animService=self.anim, helperService=self.helper, boneService=self.bone, constraintService=self.constraint, bipService=self.bip)
        self.groinBone = GroinBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, bipService=self.bip, boneService=self.bone, twistBoneService=self.twistBone, helperService=self.helper)
        self.volumePreserveBone = VolumePreserveBone(nameService=self.name, animService=self.anim, constService=self.constraint, boneService=self.bone, helperService=self.helper)
        
        self.morph = Morph()
        
        self.tools = []
