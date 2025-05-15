#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 헤더 모듈

3ds Max용 PyJalLib 패키지의 모듈 인스턴스를 관리하는 싱글톤 모듈입니다.

## 주요 기능
- 모든 Max 관련 모듈의 인스턴스 초기화 및 중앙 관리
- 서비스 간 의존성 자동 주입 및 처리
- 공유 설정 및 구성 관리
- 애플리케이션 수명 주기 동안 일관된 인스턴스 제공

## 사용 방법
max 패키지 내 모든 모듈은 이 헤더를 통해 접근할 수 있습니다.
'jal' 전역 변수를 통해 모든 서비스에 접근 가능합니다.
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

from .twistBone import TwistBone
from .autoClavicle import AutoClavicle
from .groinBone import GroinBone
from .volumeBone import VolumeBone
from .kneeBone import KneeBone
from .hip import Hip

from .morph import Morph

class Header:
    """
    # Header 클래스
    
    3ds Max에서 사용되는 PyJalLib 모듈들의 인스턴스를 관리하는 싱글톤 클래스입니다.
    
    ## 주요 기능
    - 모든 모듈의 단일 인스턴스 생성 및 수명 주기 관리
    - 모듈 간 의존성 자동 주입
    - 공통 설정 및 구성 파일 관리
    - 일관된 접근 인터페이스 제공
    
    ## 사용 예시
    ```python
    # 전역 jal 객체를 통한 서비스 접근
    from pyjallib.max.header import jal
    
    # 뼈대 생성
    bone_array = jal.bone.create_simple_bone(10, "Arm")
    
    # 자동 쇄골 생성
    result = jal.autoClavicle.create_bones(clavicle, upper_arm)
    ```
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        클래스의 싱글톤 인스턴스를 반환합니다.
        
        ## Returns
        - Header: 싱글톤 Header 인스턴스
        
        싱글톤 패턴을 구현하여 애플리케이션 내에서 
        단일 인스턴스만 존재하도록 보장합니다.
        """
        if cls._instance is None:
            cls._instance = Header()
        return cls._instance
    
    def __init__(self):
        """
        Header 클래스를 초기화합니다.
        
        모든 모듈의 인스턴스를 생성하고 필요한 의존성을 주입합니다.
        각 서비스는 적절한 구성으로 초기화되며 다른 서비스에 대한
        참조가 필요한 경우 자동으로 연결됩니다.
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

        self.twistBone = TwistBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, bipService=self.bip, boneService=self.bone)
        self.groinBone = GroinBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.autoClavicle = AutoClavicle(nameService=self.name, animService=self.anim, helperService=self.helper, boneService=self.bone, constraintService=self.constraint, bipService=self.bip)
        self.volumeBone = VolumeBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper)
        self.kneeBone = KneeBone(nameService=self.name, animService=self.anim, constraintService=self.constraint, boneService=self.bone, helperService=self.helper, volumeBoneService=self.volumeBone)
        self.hip = Hip(nameService=self.name, animService=self.anim, helperService=self.helper, boneService=self.bone, constraintService=self.constraint)
        
        self.morph = Morph()
        
        self.tools = []
    
    def update_nameConifg(self, configPath):
        """
        이름 설정을 업데이트합니다.
        
        ## Parameters
        - configPath (str): 새 설정 파일 경로
        
        이름 규칙과 관련된 설정을 업데이트하고,
        name 서비스가 새 설정을 사용하도록 합니다.
        """
        self.name.load_from_config_file(configPath)
    
    def add_tool(self, tool):
        """
        도구를 추가합니다.
        
        ## Parameters
        - tool (object): 추가할 도구 객체
        
        이미 존재하는 도구인 경우 먼저 제거한 후 새로 추가합니다.
        tools 목록에 도구들을 관리하여 플러그인이나 확장 기능을
        체계적으로 등록할 수 있습니다.
        """
        if tool in self.tools:
            self.tools.remove(tool)
        
        self.tools.append(tool)

# 모듈 레벨에서 전역 인스턴스 생성
PyJalLibMax = Header.get_instance()

# 다른 모듈에서 jal 객체에 접근하기 위한 함수
def get_header():
    """
    전역 PyJalLibMax 인스턴스를 반환합니다.
    모든 PyJalLib 모듈과 스크립트에서 이 함수를 통해 동일한 jal 객체에 접근할 수 있습니다.

    ## Returns
    - **Header**: 싱글톤 Header 인스턴스
    """
    return PyJalLibMax