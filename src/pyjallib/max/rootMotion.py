#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Root Motion 모듈
3DS Max에서 Root Motion을 처리하는 기능을 제공
"""

from pymxs import runtime as rt
from pymxs import attime, animate, undo

from .name import Name
from .anim import Anim
from .helper import Helper
from .constraint import Constraint
from .bip import Bip

class RootMotion:
    """
    Root Motion 관련 기능을 위한 클래스
    3DS Max에서 Root Motion을 처리하는 기능을 제공합니다.
    """

    def __init__(self, nameService=None, animService=None, constraintService=None, helperService=None, bipService=None):
        """
        클래스 초기화.

        Args:
            nameService: 이름 처리 서비스 (제공되지 않으면 새로 생성)
            animService: 애니메이션 서비스 (제공되지 않으면 새로 생성)
            constraintService: 제약 서비스 (제공되지 않으면 새로 생성)
            bipService: Biped 서비스 (제공되지 않으면 새로 생성)
            helperService: 헬퍼 객체 서비스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bip = bipService if bipService else Bip(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)

        # Root Motion 관련 변수 초기화
        self.rootNode = None
        self.lFoot = None
        self.rFoot = None
        self.floorThreshold = 2.0  # 바닥 접촉 임계값 기본값
        
    def create_root_motion_from_foot_contact(self, rootBoneName, startFrame, endFrame):
        """
        발 고정 및 루트 모션 생성 함수
        
        Args:
            rootBoneName (str): 루트 본 이름 (예: "Bip001")
            leftFootBoneName (str): 왼발 본 이름 (예: "Bip001_L_Foot")
            rightFootBoneName (str): 오른발 본 이름 (예: "Bip001_R_Foot")
            startFrame (int): 시작 프레임
            endFrame (int): 끝 프레임
            floorThreshold (float): 바닥 접촉 임계값
        """
        # 본 객체 가져오기
        self.rootNode = rt.getNodeByName(rootBoneName)
        if not rt.isValidNode(self.rootNode):
            return False
        
        bipComs = self.bip.get_coms()
        if len(bipComs) != 1:
            return False
        bip = bipComs[0]
        self.lFoot = self.bip.get_grouped_nodes(bip, "lLeg")[2]
        self.rFoot = self.bip.get_grouped_nodes(bip, "rLeg")[2]
        
        # 이전 프레임의 발 위치 저장 변수
        prevLeftPos = rt.Point3(0, 0, 0)
        prevRightPos = rt.Point3(0, 0, 0)
        leftPlanted = False
        rightPlanted = False
        
        # 애니메이션 범위 설정
        rt.animationRange = rt.Interval(startFrame, endFrame)
        
        # 각 프레임 처리
        for t in range(startFrame, endFrame + 1):
            # 현재 시간 설정
            with attime(t):
                with animate(True):
                    leftPos = self.lFoot.position
                    rightPos = self.rFoot.position
                    
                    # 발이 바닥에 닿았는지 확인
                    leftOnFloor = (leftPos.z <= self.floorThreshold)
                    rightOnFloor = (rightPos.z <= self.floorThreshold)
            
                    # 새로운 루트 위치 계산
                    if leftOnFloor and leftPlanted:
                        # 왼발이 고정되어 있으면 그 차이만큼 루트 본 이동
                        rootDelta = prevLeftPos - leftPos
                        self.rootNode.position += rootDelta
                        print(f"프레임 {t}: 왼발 기준 루트 모션 적용 - 델타: {rootDelta}")
                        
                    elif rightOnFloor and rightPlanted:
                        # 오른발이 고정되어 있으면 그 차이만큼 루트 본 이동
                        rootDelta = prevRightPos - rightPos
                        self.rootNode.position += rootDelta
                        print(f"프레임 {t}: 오른발 기준 루트 모션 적용 - 델타: {rootDelta}")
            
                    # 상태 및 위치 업데이트
                    leftPlanted = leftOnFloor
                    rightPlanted = rightOnFloor
                    prevLeftPos = rt.copy(leftPos)
                    prevRightPos = rt.copy(rightPos)
            
                # 진행률 표시 (10프레임마다)
                if t % 10 == 0:
                    progress = ((t - startFrame) / (endFrame - startFrame)) * 100
                    print(f"진행률: {progress:.1f}% (프레임 {t}/{endFrame})")
        
        # 타임라인을 시작 프레임으로 되돌리기
        rt.sliderTime = startFrame
            