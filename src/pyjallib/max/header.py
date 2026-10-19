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

from .rig.twistBone import TwistBone
from .rig.autoClavicle import AutoClavicle
from .rig.shoulder import Shoulder
from .rig.armpit import Armpit
from .rig.chest import Chest
from .rig.jacketPanel import JacketPanel
from .rig.groinBone import GroinBone
from .rig.volumeBone import VolumeBone
from .rig.elbow import Elbow
from .rig.wrist import Wrist
from .rig.ankle import Ankle
from .rig.inguinal import Inguinal
from .rig.kneeBone import KneeBone
from .rig.hip import Hip
from .ue5Skeleton import UE5Skeleton

from .morph import Morph
from .attribute import Attribute
from .polygon import Polygon

from .rootMotion import RootMotion

from .dependent import Dependent

from .checkViewport import CheckViewport
from .checkLayer import CheckLayer
from .checkMaterial import CheckMaterial
from .checkObject import CheckObject

from .fbxHandler import FBXHandler
from .toolManager import ToolManager


class Header:
    """pyjallib.max 패키지의 서비스 클래스 인스턴스들을 한 번만 생성하여 보관하는 싱글톤 헤더 클래스."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """싱글톤 Header 인스턴스를 반환한다.

        인스턴스가 없으면 새로 생성한다.

        Returns:
            Header: 싱글톤 Header 인스턴스
        """
        if cls._instance is None:
            cls._instance = Header()
        return cls._instance

    def __init__(self):
        """모든 서비스 클래스 인스턴스를 생성하고 의존성을 주입하여 초기화한다."""
        self.configDir = os.path.join(os.path.dirname(__file__), "ConfigFiles")
        self.nameConfigDir = os.path.join(self.configDir, "3DSMaxNamingConfig.json")

        self.name = Name(configPath=self.nameConfigDir)
        self.anim = Anim()

        self.helper = Helper(nameService=self.name)
        self.constraint = Constraint(nameService=self.name, helperService=self.helper)
        self.bone = Bone(
            nameService=self.name,
            animService=self.anim,
            helperService=self.helper,
            constraintService=self.constraint,
        )

        self.mirror = Mirror(nameService=self.name, boneService=self.bone)
        self.layer = Layer()
        self.align = Align()
        self.sel = Select(nameService=self.name, boneService=self.bone, layerService=self.layer)
        self.link = Link()

        self.bip = Bip(
            animService=self.anim, nameService=self.name, boneService=self.bone
        )
        self.skin = Skin()
        self.skeleton = Skeleton(
            animService=self.anim,
            nameService=self.name,
            boneService=self.bone,
            bipService=self.bip,
            layerService=self.layer,
        )

        # 릭 파트는 서비스를 **필수 주입**으로 받는다(`rig/rigPart.py`). 공통 다섯은
        # (name, anim, helper, bone, constraint) 순서로 고정이고, 그 뒤에 파트별
        # 추가 서비스가 붙는다.
        self.twistBone = TwistBone(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.bip
        )
        self.groinBone = GroinBone(
            self.name, self.anim, self.helper, self.bone, self.constraint
        )
        self.autoClavicle = AutoClavicle(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.bip
        )
        self.shoulder = Shoulder(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.bip
        )
        self.armpit = Armpit(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.align
        )
        self.chest = Chest(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.align
        )
        self.jacketPanel = JacketPanel(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.align
        )
        self.volumeBone = VolumeBone(
            self.name, self.anim, self.helper, self.bone, self.constraint
        )
        self.elbow = Elbow(self.name, self.anim, self.helper, self.bone, self.constraint)
        self.wrist = Wrist(self.name, self.anim, self.helper, self.bone, self.constraint)
        self.ankle = Ankle(self.name, self.anim, self.helper, self.bone, self.constraint)
        self.inguinal = Inguinal(
            self.name, self.anim, self.helper, self.bone, self.constraint
        )
        self.kneeBone = KneeBone(
            self.name, self.anim, self.helper, self.bone, self.constraint, self.volumeBone
        )
        self.hip = Hip(self.name, self.anim, self.helper, self.bone, self.constraint)
        self.ue5Skeleton = UE5Skeleton(
            nameService=self.name,
            animService=self.anim,
            boneService=self.bone,
            bipService=self.bip,
            constraintService=self.constraint,
        )

        self.morph = Morph()
        self.attribute = Attribute()
        self.polygon = Polygon()

        self.rootMotion = RootMotion(
            nameService=self.name,
            animService=self.anim,
            constraintService=self.constraint,
            helperService=self.helper,
            bipService=self.bip,
        )

        self.dependent = Dependent(layerService=self.layer)

        self.checkViewport = CheckViewport()
        self.checkLayer = CheckLayer(layerService=self.layer)
        self.checkMaterial = CheckMaterial()
        self.checkObject = CheckObject()

        self.fbx = FBXHandler()

        self.toolManager = ToolManager()

    def update_name_config(self, inConfigPath):
        """이름 설정 파일을 다시 로드하여 네이밍 설정을 업데이트한다.

        Args:
            inConfigPath (str): 네이밍 설정 JSON 파일 경로
        """
        self.name.load_from_config_file(inConfigPath)

    def update_nameConifg(self, configPath):
        """`update_name_config`의 **오타 유지용 별칭**이다.

        원래 이름에 오타(`Conifg`)가 있었고, 이미 두 프로젝트가 그 이름으로 부르고 있다.
        바른 이름을 **가산으로** 추가하고 구 이름은 동작하는 별칭으로 남긴다 - 소비처를
        수정하지 않아도 되므로 이 사이클의 변경 범위가 넓어지지 않는다.

        **후속 이관 대상:** `orvlib/src/PyJalMaxLibLoader.py`,
        `PyJalMaxNamer/src/maxnamer/ui/namePartInput.py`.
        두 소비처가 새 이름으로 옮기면 이 별칭을 삭제한다.

        Args:
            configPath (str): 네이밍 설정 JSON 파일 경로
        """
        self.update_name_config(configPath)

    def configure_node_collect_policy(self, inPolicy) -> None:
        """노드 수집 확장 정서를 dependent와 sel 양쪽에 함께 배선한다.

        두 서비스는 싱글톤 Header를 경유해 얻어지므로 생성자에 정서를 넣을 자리가
        없다. 그래서 설정 메서드를 둔다.

        **한 지점에서 두 서비스에 함께 배선하는 것이 이 메서드의 존재 이유다.**
        서비스별 setter만 두면 한쪽 설정 누락이 잠복하는데, 그것이 두 서비스의 수집
        로직이 서로 어긋났던 경로와 같다.

        Args:
            inPolicy (NodeCollectPolicy | None): 배선할 정서. None을 주면 규칙을
                해제한다(확장 없음)
        """
        self.dependent.collectPolicy = inPolicy
        self.sel.collectPolicy = inPolicy


# 모듈 레벨에서 전역 인스턴스 생성
_pyjallibmaxheader = Header.get_instance()


def get_pyjallibmaxheader():
    """모듈 레벨에서 생성된 전역 Header 싱글톤 인스턴스를 반환한다.

    Returns:
        Header: 전역 Header 인스턴스
    """
    return _pyjallibmaxheader
