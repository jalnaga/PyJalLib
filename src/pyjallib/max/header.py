#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
헤더 모듈 - max 패키지의 인스턴스 관리
3DS Max가 실행될 때 메모리에 한번만 로드되는 패키지 인스턴스들을 관리
"""

import os

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
from .skeleton import Skeleton

from .twistBone import TwistBone
from .autoClavicle import AutoClavicle
from .shoulder import Shoulder
from .groinBone import GroinBone
from .volumeBone import VolumeBone
from .elbow import Elbow
from .wrist import Wrist
from .inguinal import Inguinal
from .kneeBone import KneeBone
from .hip import Hip

from .morph import Morph

from .rootMotion import RootMotion

from .fbxHandler import FBXHandler
from .toolManager import ToolManager

class Header:
    """
    JalLib.max 패키지의 헤더 모듈
    3DS Max에서 사용하는 다양한 기능을 제공하는 클래스들을 초기화하고 관리합니다.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """싱글톤 패턴을 구현한 인스턴스 접근 메소드"""
        if cls._instance is None:
            cls._instance = Header()
        return cls._instance
    
    def __init__(self):
        """
        Header 클래스 초기화
        """
        self.configDir = os.path.join(os.path.dirname(__file__), "ConfigFiles")
        self.nameConfigDir = os.path.join(self.configDir, "3DSMaxNamingConfig.json")

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
        self.skeleton = Skeleton(animService=self.anim, nameService=self.name, boneService=self.bone, bipService=self.bip, layerService=self.layer)

        self.twistBone = TwistBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, bipService=self.bip, boneService=self.bone)
        self.groinBone = GroinBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.autoClavicle = AutoClavicle(nameService=self.name, animService=self.anim, helperService=self.helper, boneService=self.bone, constraintService=self.constraint, bipService=self.bip)
        self.shoulder = Shoulder(nameService=self.name, animService=self.anim, helperService=self.helper, boneService=self.bone, constraintService=self.constraint, bipService=self.bip)
        self.volumeBone = VolumeBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.elbow = Elbow(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.wrist = Wrist(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.inguinal = Inguinal(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.kneeBone = KneeBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper, volumeBoneService=self.volumeBone)
        self.hip = Hip(nameService=self.name, animService=self.anim, helperService=self.helper, boneService=self.bone, constraintService=self.constraint)
        
        self.morph = Morph()
        
        self.rootMotion = RootMotion(nameService=self.name, animService=self.anim, constraintService=self.constraint, helperService=self.helper, bipService=self.bip)
        
        self.fbx = FBXHandler()
        
        self.toolManager = ToolManager()
    
    def update_nameConifg(self, configPath):
        """
        이름 설정을 업데이트합니다.
        
        Args:
            configPath: ConfigPath 인스턴스
        """
        self.name.load_from_config_file(configPath)

# 모듈 레벨에서 전역 인스턴스 생성
_pyjallibmaxheader = Header.get_instance()

def get_pyjallibmaxheader():
    """
    jal 인스턴스를 반환합니다.
    
    Returns:
        Header 인스턴스
    """
    return _pyjallibmaxheader