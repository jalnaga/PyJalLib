#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 관절 부피 유지 본(VolumeBone) 모듈

3ds Max에서 관절 변형 시 발생하는 부피 감소 문제를 해결하는 기능을 제공하는 모듈입니다.

## 주요 기능
- 관절 회전 시 유지되는 부피감 있는 보조 본 생성
- 자동 회전 및 위치 제약 설정
- 다양한 회전 및 이동 축 지원
- 스크립트 기반 자동 볼륨 계산

## 구현 정보
- 원본 MAXScript를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
- 스크립트 컨트롤러를 통한 동적 볼륨 조절
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .anim import Anim
from .helper import Helper
from .bone import Bone
from .constraint import Constraint


class VolumeBone:  # Updated class name to match the new file name
    """
    # VolumeBone 클래스
    
    3ds Max에서 관절의 부피를 유지하기 위한 보조 본 시스템을 제공하는 클래스입니다.
    
    ## 주요 기능
    - 관절 회전 시 자동으로 부피감을 유지하는 보조 본 생성
    - 다양한 축을 기준으로 한 부피 유지 본 배치
    - 회전 양에 따른 자동 위치 조정
    - 루트 본과 자식 본의 계층 구조 설정
    
    ## 구현 정보
    - 스크립트 컨트롤러를 통한 자동화된 위치 제약
    - 다양한 서비스 클래스와 연동된 통합 기능
    - 회전 계산을 위한 쿼터니언 기반 수식 사용
    
    ## 사용 예시
    ```python
    # VolumeBone 객체 생성
    vol_bone = VolumeBone()
    
    # 무릎 관절에 볼륨 본 생성
    result = vol_bone.create_bones(calf, thigh, inVolumeSize=5.0, 
                                  inRotAxises=["Z", "Z"], 
                                  inTransAxises=["PosY", "NegY"])
    ```
    """
    def __init__(self, nameService=None, animService=None, constraintService=None, boneService=None, helperService=None):
        """
        VolumeBone 클래스를 초기화합니다.
        
        ## Parameters
        - nameService (Name, optional): 이름 처리 서비스 (기본값: None, 새로 생성)
        - animService (Anim, optional): 애니메이션 서비스 (기본값: None, 새로 생성)
        - constraintService (Constraint, optional): 제약 서비스 (기본값: None, 새로 생성)
        - boneService (Bone, optional): 뼈대 서비스 (기본값: None, 새로 생성)
        - helperService (Helper, optional): 헬퍼 서비스 (기본값: None, 새로 생성)
        
        ## 참고
        - 서비스 인스턴스가 제공되지 않으면 자동으로 생성됩니다.
        - 종속성 있는 서비스들은 적절히 연결됩니다.
        """
        # 서비스 인스턴스 설정 또는 생성
        self.name = nameService if nameService else Name()
        self.anim = animService if animService else Anim()
        
        # 종속성이 있는 서비스들은 이미 생성된 서비스들을 전달
        self.const = constraintService if constraintService else Constraint(nameService=self.name)
        self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
        self.helper = helperService if helperService else Helper(nameService=self.name)
        
        self.rootBone = None
        self.rotHelper = None
        self.limb = None
        self.limbParent = None
        self.bones = []
        self.rotAxises = []
        self.transAxises = []
        self.transScales = []
        self.volumeSize = 5.0
        self.rotScale = 0.5
        
        self.posScriptExpression = (
            "localLimbTm = limb.transform * inverse limbParent.transform\n"
            "localDeltaTm = localLimbTm * inverse localRotRefTm\n"
            "\n"
            "q = localDeltaTm.rotation\n"
            "\n"
            "eulerRot = (quatToEuler q order:5)\n"
            "swizzledRot = (eulerAngles eulerRot.y eulerRot.z eulerRot.x)\n"
            "saturatedTwist = abs ((swizzledRot.x*axis.x + swizzledRot.y*axis.y + swizzledRot.z*axis.z)/180.0)\n"
            "\n"
            "trAxis * saturatedTwist * volumeSize * transScale\n"
        )
    
    def reset(self):
        """
        클래스의 작업 데이터를 초기화합니다.
        
        서비스 객체는 유지하면서 클래스의 작업 상태만 초기화합니다.
        
        ## Returns
        - self: 메소드 체이닝을 위한 자기 자신 반환
        """
        self.rootBone = None
        self.rotHelper = None
        self.limb = None
        self.limbParent = None
        self.bones = []
        self.rotAxises = []
        self.transAxises = []
        self.transScales = []
        self.volumeSize = 5.0
        self.rotScale = 0.5
        
        return self
    
    def create_root_bone(self, inObj, inParent, inRotScale=0.5):
        """
        부피 유지 본 시스템의 루트 본을 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 본을 생성할 객체 (일반적으로 자식 객체)
        - inParent (MaxObject): 부모 객체 (일반적으로 부모 관절)
        - inRotScale (float): 회전 가중치 (0.0~1.0, 기본값: 0.5)
            
        ## Returns
        - MaxObject: 생성된 루트 본 또는 False (실패 시)
        
        ## 동작 방식
        1. 이름 규칙에 따른 루트 본 이름 생성
        2. 루트 본 및 회전 헬퍼 생성
        3. 다중 회전 제약 설정 (객체와 헬퍼 사이)
        """
        if rt.isValidNode(inObj) == False or rt.isValidNode(inParent) == False:
            return False
        
        if rt.isValidNode(self.rootBone) and rt.isValidNode(self.rotHelper):
            return self.rootBone
        
        rootBoneName = inObj.name
        filteringChar = self.name._get_filtering_char(rootBoneName)
        rootBoneName = self.name.add_suffix_to_real_name(rootBoneName, filteringChar+"Vol"+filteringChar+"Root")
        
        rootBone = self.bone.create_nub_bone(rootBoneName, 2)
        rootBone.name = self.name.remove_name_part("Nub", rootBone.name)
        if rootBone.name[0].islower():
            rootBone.name = rootBone.name.lower()
            rootBoneName = rootBoneName.lower()
            
        rt.setProperty(rootBone, "transform", inObj.transform)
        rootBone.parent = inObj
        
        rotHelper = self.helper.create_point(rootBoneName)
        rotHelper.name = self.name.replace_name_part("Type", rotHelper.name, self.name.get_name_part_value_by_description("Type", "Dummy"))
        rt.setProperty(rotHelper, "transform", inObj.transform)
        rotHelper.parent = inParent
        
        oriConst = self.const.assign_rot_const_multi(rootBone, [inObj, rotHelper])
        oriConst.setWeight(1, inRotScale * 100.0)
        oriConst.setWeight(2, (1.0 - inRotScale) * 100.0)
        
        self.rootBone = rootBone
        self.rotHelper = rotHelper
        self.limb = inObj
        self.limbParent = inParent
        
        return self.rootBone
    
    def create_bone(self, inObj, inParent, inRotScale=0.5, inVolumeSize=5.0, inRotAxis="Z", inTransAxis="PosY", inTransScale=1.0, useRootBone=True, inRootBone=None):
        """
        부피 유지 본을 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 본을 생성할 객체
        - inParent (MaxObject): 부모 객체
        - inRotScale (float): 회전 가중치 (0.0~1.0, 기본값: 0.5)
        - inVolumeSize (float): 부피 크기 (기본값: 5.0)
        - inRotAxis (str): 회전 축 ("X", "Y", "Z", 기본값: "Z")
        - inTransAxis (str): 이동 축 ("PosX", "NegX", "PosY", "NegY", "PosZ", "NegZ", 기본값: "PosY")
        - inTransScale (float): 이동 비율 (기본값: 1.0)
        - useRootBone (bool): 기존 루트 본 사용 여부 (기본값: True)
        - inRootBone (MaxObject): 사용할 루트 본 (기본값: None)
            
        ## Returns
        - bool: 성공 여부
        
        ## 동작 방식
        1. 루트 본 생성 또는 가져오기
        2. 이름 규칙에 따른 부피 본 이름 생성
        3. 이동 방향 설정 및 적용
        4. 스크립트 컨트롤러 생성 및 설정
        """
        if rt.isValidNode(inObj) == False or rt.isValidNode(inParent) == False:
            return False
        
        if useRootBone:
            if rt.isValidNode(self.rootBone) == False and rt.isValidNode(self.rotHelper) == False:
                return False
            self.rootBone = inRootBone if inRootBone else self.create_root_bone(inObj, inParent, inRotScale)
        else:
            self.create_root_bone(inObj, inParent, inRotScale)
        
        self.limb = inObj
        self.limbParent = inParent
        
        volBoneName = inObj.name
        filteringChar = self.name._get_filtering_char(volBoneName)
        volBoneName = self.name.add_suffix_to_real_name(volBoneName, filteringChar + "Vol" + filteringChar + inRotAxis + filteringChar+ inTransAxis)
        
        volBone = self.bone.create_nub_bone(volBoneName, 2)
        volBone.name = self.name.remove_name_part("Nub", volBone.name)
        if volBone.name[0].islower():
            volBone.name = volBone.name.lower()
            volBoneName = volBoneName.lower()
        rt.setProperty(volBone, "transform", self.rootBone.transform)
        
        volBoneTrDir = rt.Point3(0.0, 0.0, 0.0)
        if inTransAxis == "PosX":
            volBoneTrDir = rt.Point3(1.0, 0.0, 0.0)
        elif inTransAxis == "NegX":
            volBoneTrDir = rt.Point3(-1.0, 0.0, 0.0)
        elif inTransAxis == "PosY":
            volBoneTrDir = rt.Point3(0.0, 1.0, 0.0)
        elif inTransAxis == "NegY":
            volBoneTrDir = rt.Point3(0.0, -1.0, 0.0)
        elif inTransAxis == "PosZ":
            volBoneTrDir = rt.Point3(0.0, 0.0, 1.0)
        elif inTransAxis == "NegZ":
            volBoneTrDir = rt.Point3(0.0, 0.0, -1.0)
        
        self.anim.move_local(volBone, volBoneTrDir[0]*inVolumeSize, volBoneTrDir[1]*inVolumeSize, volBoneTrDir[2]*inVolumeSize)
        volBone.parent = self.rootBone
        
        rotAxis = rt.Point3(0.0, 0.0, 0.0)
        if inRotAxis == "X":
            rotAxis = rt.Point3(1.0, 0.0, 0.0)
        elif inRotAxis == "Y":
            rotAxis = rt.Point3(0.0, 1.0, 0.0)
        elif inRotAxis == "Z":
            rotAxis = rt.Point3(0.0, 0.0, 1.0)
        
        localRotRefTm = self.limb.transform * rt.inverse(self.rotHelper.transform)
        volBonePosConst = self.const.assign_pos_script_controller(volBone)
        volBonePosConst.addNode("limb", self.limb)
        volBonePosConst.addNode("limbParent", self.rotHelper)
        volBonePosConst.addConstant("axis", rotAxis)
        volBonePosConst.addConstant("transScale", rt.Float(inTransScale))
        volBonePosConst.addConstant("volumeSize", rt.Float(inVolumeSize))
        volBonePosConst.addConstant("localRotRefTm", localRotRefTm)
        volBonePosConst.addConstant("trAxis", volBoneTrDir)
        volBonePosConst.setExpression(self.posScriptExpression)
        volBonePosConst.update()
        
        return True
    
    def create_bones(self, inObj, inParent, inRotScale=0.5, inVolumeSize=5.0, inRotAxises=["Z"], inTransAxises=["PosY"], inTransScales=[1.0]):
        """
        여러 개의 부피 유지 본을 생성합니다.
        
        ## Parameters
        - inObj (MaxObject): 본을 생성할 객체
        - inParent (MaxObject): 부모 객체
        - inRotScale (float): 회전 가중치 (0.0~1.0, 기본값: 0.5)
        - inVolumeSize (float): 부피 크기 (기본값: 5.0)
        - inRotAxises (list): 회전 축 리스트 (기본값: ["Z"])
        - inTransAxises (list): 이동 축 리스트 (기본값: ["PosY"])
        - inTransScales (list): 이동 비율 리스트 (기본값: [1.0])
        
        ## Returns
        - dict: 생성 결과 정보를 담은 딕셔너리 또는 None (실패 시)
            - "RootBone": 루트 본 객체
            - "RotHelper": 회전 헬퍼 객체
            - "RotScale": 회전 가중치
            - "Limb": 대상 객체
            - "LimbParent": 부모 객체
            - "Bones": 생성된 본 배열
            - "RotAxises": 사용된 회전 축 배열
            - "TransAxises": 사용된 이동 축 배열
            - "TransScales": 사용된 이동 비율 배열
            - "VolumeSize": 설정된 부피 크기
        
        ## 동작 방식
        1. 루트 본 생성
        2. 축 리스트 길이 확인 및 각 축 조합으로 본 생성
        3. 생성된 본 수집 및 결과 구성
        4. 클래스 상태 초기화 및 결과 반환
        """
        if rt.isValidNode(inObj) == False or rt.isValidNode(inParent) == False:
            return None
        
        if len(inRotAxises) != len(inTransAxises) or len(inRotAxises) != len(inTransScales):
            return None
        
        rootBone = self.create_root_bone(inObj, inParent, inRotScale=inRotScale)
        
        # 볼륨 본들 생성
        bones = []
        for i in range(len(inRotAxises)):
            self.create_bone(inObj, inParent, inRotScale, inVolumeSize, inRotAxises[i], inTransAxises[i], inTransScales[i], useRootBone=True, inRootBone=rootBone)
            
            # 생성된 본의 이름 패턴으로 찾기
            volBoneName = inObj.name
            filteringChar = self.name._get_filtering_char(volBoneName)
            volBoneName = self.name.add_suffix_to_real_name(volBoneName, 
                          filteringChar + "Vol" + filteringChar + inRotAxises[i] + 
                          filteringChar + inTransAxises[i])
            
            if volBoneName[0].islower():
                volBoneName = volBoneName.lower()
                
            volBone = rt.getNodeByName(self.name.remove_name_part("Nub", volBoneName))
            if rt.isValidNode(volBone):
                bones.append(volBone)
        
        # 클래스 변수에 결과 저장
        self.rootBone = rootBone
        self.limb = inObj
        self.limbParent = inParent
        self.bones = bones
        self.rotAxises = inRotAxises.copy()
        self.transAxises = inTransAxises.copy()
        self.transScales = inTransScales.copy()
        self.volumeSize = inVolumeSize
        self.rotScale = inRotScale
        
        # VolumeBoneChain이 필요로 하는 형태의 결과 딕셔너리 생성
        result = {
            "RootBone": rootBone,
            "RotHelper": self.rotHelper,
            "RotScale": inRotScale,
            "Limb": inObj,
            "LimbParent": inParent,
            "Bones": bones,
            "RotAxises": inRotAxises,
            "TransAxises": inTransAxises,
            "TransScales": inTransScales,
            "VolumeSize": inVolumeSize
        }
        
        # 메소드 호출 후 데이터 초기화
        self.reset()
        
        return result
