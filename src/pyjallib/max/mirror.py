#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
미러 모듈 - 3ds Max용 객체 미러링 관련 기능 제공
원본 MAXScript의 mirror.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from pymxs import runtime as rt

# Import necessary service classes for default initialization
from .name import Name
from .bone import Bone


class Mirror:
    """
    객체 미러링 관련 기능을 제공하는 클래스.
    MAXScript의 _Mirror 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self, nameService=None, boneService=None):
        """
        클래스 초기화
        
        Args:
            nameService: Name 서비스 인스턴스 (제공되지 않으면 새로 생성)
            boneService: Bone 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.name = nameService if nameService else Name()
        self.bone = boneService if boneService else Bone(nameService=self.name) # Pass the potentially newly created nameService
    
    def mirror_matrix(self, mAxis="x", mFlip="x", tm=None, pivotTM=None):
        """
        미러링 행렬 생성
        
        Args:
            mAxis: 미러링 축 (기본값: "x")
            mFlip: 뒤집는 축 (기본값: "x")
            tm: 변환 행렬 (기본값: 단위 행렬)
            pivotTM: 피벗 변환 행렬 (기본값: 단위 행렬)
            
        Returns:
            미러링된 변환 행렬
        """
        def fetch_reflection(a):
            """
            반사 벡터 값 반환
            
            Args:
                a: 축 식별자 ("x", "y", "z")
                
            Returns:
                해당 축에 대한 반사 벡터
            """
            if a == "x":
                return [-1, 1, 1]  # YZ 평면에 대한 반사
            elif a == "y":
                return [1, -1, 1]  # ZX 평면에 대한 반사
            elif a == "z":
                return [1, 1, -1]  # XY 평면에 대한 반사
            else:
                return [1, 1, 1]  # 반사 없음
        
        # 기본값 설정
        if tm is None:
            tm = rt.matrix3(1)
        if pivotTM is None:
            pivotTM = rt.matrix3(1)
        
        # 반사 행렬 생성
        a_reflection = rt.scalematrix(rt.Point3(*fetch_reflection(mAxis)))
        f_reflection = rt.scalematrix(rt.Point3(*fetch_reflection(mFlip)))
        
        # 미러링된 변환 행렬 계산: fReflection * tm * aReflection * pivotTm
        return f_reflection * tm * a_reflection * pivotTM
    
    def apply_mirror(self, inObj, axis=1, flip=2, pivotObj=None, cloneStatus=2, negative=False):
        """
        객체에 미러링 적용
        
        Args:
            inObj: 미러링할 객체
            axis: 미러링 축 인덱스 (1=x, 2=y, 3=z, 기본값: 1)
            flip: 뒤집기 축 인덱스 (1=x, 2=y, 3=z, 4=none, 기본값: 2)
            pivotObj: 피벗 객체 (기본값: None)
            cloneStatus: 복제 상태 (1=원본 변경, 2=복제본 생성, 3=스냅샷, 기본값: 2)
            negative: 음수 좌표계 사용 여부 (기본값: False)
            
        Returns:
            미러링된 객체 (복제본 또는 원본)
        """
        axisArray = ["x", "y", "z", "none"]
        copyObj = rt.copy(inObj)
        objTM = inObj.transform
        pivotTM = rt.matrix3(1)
        mirrorIndexAxis = axis
        flipAxisIndex = flip
        copyObjName = self.name.gen_mirroring_name(inObj.name)
        
        # 피벗 객체가 지정된 경우 피벗 변환 행렬 사용
        if pivotObj is not None:
            pivotTM = pivotObj.transform
        
        # negative가 True인 경우 뒤집기 없음으로 설정
        if negative:
            flipAxisIndex = 4
        
        # 복제본 초기 설정
        copyObj.name = copyObjName
        copyObj.parent = None
        copyObj.wirecolor = inObj.wirecolor
        
        # 복제 상태에 따른 처리
        if cloneStatus == 1:  # 원본 변경
            rt.delete(copyObj)
            copyObj = None
            inObj.transform = self.mirror_matrix(
                mAxis=axisArray[mirrorIndexAxis-1],
                mFlip=axisArray[flipAxisIndex-1],
                tm=objTM,
                pivotTM=pivotTM
            )
            copyObj = inObj
        elif cloneStatus == 2:  # 복제본 생성
            copyObj.transform = self.mirror_matrix(
                mAxis=axisArray[mirrorIndexAxis-1],
                mFlip=axisArray[flipAxisIndex-1],
                tm=objTM,
                pivotTM=pivotTM
            )
        elif cloneStatus == 3:  # 스냅샷 생성
            rt.delete(copyObj)
            copyObj = None
            copyObj = rt.snapShot(inObj)
            copyObj.transform = self.mirror_matrix(
                mAxis=axisArray[mirrorIndexAxis-1],
                mFlip=axisArray[flipAxisIndex-1],
                tm=objTM,
                pivotTM=pivotTM
            )
        
        return copyObj
    
    def mirror_object(self, inObjArray, mAxis=1, pivotObj=None, cloneStatus=2):
        """
        객체 배열을 음수 좌표계를 사용하여 미러링
        
        Args:
            inObjArray: 미러링할 객체 배열
            mAxis: 미러링 축 (기본값: 1)
            pivotObj: 피벗 객체 (기본값: None)
            cloneStatus: 복제 상태 (기본값: 2)
            
        Returns:
            미러링된 객체 배열
        """
        returnArray = []
        
        for item in inObjArray:
            mirroredObj = self.apply_mirror(
                item, 
                axis=mAxis, 
                pivotObj=pivotObj, 
                cloneStatus=cloneStatus, 
                negative=True
            )
            returnArray.append(mirroredObj)
        
        return returnArray
    
    def mirror_without_negative(self, inMirrorObjArray, mAxis=1, pivotObj=None, cloneStatus=2):
        """
        객체 배열을 양수 좌표계를 사용하여 미러링
        
        Args:
            inMirrorObjArray: 미러링할 객체 배열
            mAxis: 미러링 축 인덱스 (1-6, 기본값: 1)
            pivotObj: 피벗 객체 (기본값: None)
            cloneStatus: 복제 상태 (기본값: 2)
            
        Returns:
            미러링된 객체 배열
        """
        # 미러링 축과 뒤집기 축 매핑
        # 1=XY, 2=XZ, 3=YX, 4=YZ, 5=ZX, 6=ZY
        axisIndex = 1
        flipIndex = 1
        
        # 미러링 축 인덱스에 따른 매핑
        if mAxis == 1:
            axisIndex = 1  # x
            flipIndex = 2  # y
        elif mAxis == 2:
            axisIndex = 1  # x
            flipIndex = 3  # z
        elif mAxis == 3:
            axisIndex = 2  # y
            flipIndex = 1  # x
        elif mAxis == 4:
            axisIndex = 2  # y
            flipIndex = 3  # z
        elif mAxis == 5:
            axisIndex = 3  # z
            flipIndex = 1  # x
        elif mAxis == 6:
            axisIndex = 3  # z
            flipIndex = 2  # y
        else:
            axisIndex = 1  # x
            flipIndex = 1  # x
        
        # 미러링 적용
        returnArray = []
        for item in inMirrorObjArray:
            mirroredObj = self.apply_mirror(
                item, 
                axis=axisIndex, 
                flip=flipIndex, 
                pivotObj=pivotObj, 
                cloneStatus=cloneStatus, 
                negative=False
            )
            returnArray.append(mirroredObj)
        
        return returnArray
    
    def mirror_bone(self, inBoneArray, mAxis=1, flipZ=False, offset=0.0):
        """
        뼈대 객체를 미러링
        
        Args:
            inBoneArray: 미러링할 뼈대 배열
            mAxis: 미러링 축 (1=x, 2=y, 3=z, 기본값: 1)
            flipZ: Z축 뒤집기 여부 (기본값: False)
            offset: 미러링 오프셋 (기본값: 0.0)
            
        Returns:
            미러링된 뼈대 배열
        """
        # 계층 구조에 따라 뼈대 정렬
        bones = self.bone.sort_bones_as_hierarchy(inBoneArray)
        
        # 미러링 축 팩터 설정
        axisFactor = [1, 1, 1]
        if mAxis == 1:
            axisFactor = [-1, 1, 1]  # x축 미러링
        elif mAxis == 2:
            axisFactor = [1, -1, 1]  # y축 미러링
        elif mAxis == 3:
            axisFactor = [1, 1, -1]  # z축 미러링
        
        # 새 뼈대와 부모 정보 저장 배열 준비
        parents = []
        created = []
        
        # 시작점 위치 (미러링 중심) 설정
        root = bones[0].transform.translation
        
        # 정렬된 뼈대 순서대로 처리
        for i in range(len(bones)):
            original = bones[i]
            if rt.classOf(original) != rt.BoneGeometry:  # 실제 뼈대가 아닌 경우
                parents.append(None)  # 부모 없음 표시
                continue
            
            # 원본 뼈대의 시작점, 끝점, Z축 방향 가져오기
            boneStart = original.pos
            boneEnd = self.bone.get_bone_end_position(original)
            boneZ = original.dir
            
            # 미러링 적용
            for k in range(3):  # x, y, z 좌표
                if axisFactor[k] < 0:
                    boneStart[k] = 2.0 * root[k] - boneStart[k] + offset
                    boneEnd[k] = 2.0 * root[k] - boneEnd[k] + offset
                    boneZ[k] = -boneZ[k]
            
            # Z축 뒤집기 옵션 적용
            if flipZ:
                boneZ = -boneZ
            
            # 새 뼈대 생성
            reflection = rt.bonesys.createbone(boneStart, boneEnd, boneZ)
            
            # 원본 뼈대의 속성을 복사
            reflection.backfin = original.backfin
            reflection.backfinendtaper = original.backfinendtaper
            reflection.backfinsize = original.backfinsize
            reflection.backfinstarttaper = original.backfinstarttaper
            reflection.frontfin = original.frontfin
            reflection.frontfinendtaper = original.frontfinendtaper
            reflection.frontfinsize = original.frontfinsize
            reflection.frontfinstarttaper = original.frontfinstarttaper
            reflection.height = original.height
            
            # 이름 생성 (좌우/앞뒤 방향이 있는 경우 미러링된 이름 생성)
            if self.name.has_Side(original.name) or self.name.has_FrontBack(original.name):
                reflection.name = self.name.gen_mirroring_name(original.name, axis=mAxis)
            else:
                reflection.name = self.name.add_suffix_to_real_name(original.name, "Mirrored")
                
            reflection.sidefins = original.sidefins
            reflection.sidefinsendtaper = original.sidefinsendtaper
            reflection.sidefinssize = original.sidefinssize
            reflection.sidefinsstarttaper = original.sidefinsstarttaper
            reflection.taper = original.taper
            reflection.width = original.width
            reflection.wirecolor = original.wirecolor
            
            created.append(reflection)
            parents.append(reflection)
        
        # 계층 구조 연결 (자식부터 상위로)
        for i in range(len(created)-1, 0, -1):
            pIndex = bones.index(bones[i].parent) if bones[i].parent in bones else 0
            if pIndex != 0:
                created[i].parent = parents[pIndex]
        
        # 루트 뼈대의 부모 설정
        created[0].parent = bones[0].parent
        
        # 부모가 없는 뼈대는 위치 조정
        for i in range(len(created)):
            if created[i].parent is None:
                created[i].position = rt.Point3(
                    bones[i].position.x * axisFactor[0],
                    bones[i].position.y * axisFactor[1],
                    bones[i].position.z * axisFactor[2]
                )
        
        return created
    
    def mirror_geo(self, inMirrorObjArray, mAxis=1, pivotObj=None, cloneStatus=2):
        """
        지오메트리 객체 미러링 (폴리곤 노멀 방향 조정 포함)
        
        Args:
            inMirrorObjArray: 미러링할 객체 배열
            mAxis: 미러링 축 (기본값: 1)
            pivotObj: 피벗 객체 (기본값: None)
            cloneStatus: 복제 상태 (기본값: 2)
            
        Returns:
            미러링된 객체 배열
        """
        # 객체 미러링
        mirroredArray = self.mirror_object(
            inMirrorObjArray,
            mAxis=mAxis,
            pivotObj=pivotObj,
            cloneStatus=cloneStatus
        )
        
        # 리셋 대상, 비리셋 대상 분류
        resetXformArray = []
        nonResetXformArray = []
        returnArray = []
        
        # 객체 타입에 따라 분류
        for item in mirroredArray:
            caseIndex = 0
            if rt.classOf(item) == rt.Editable_Poly:
                caseIndex += 1
            if rt.classOf(item) == rt.Editable_mesh:
                caseIndex += 1
            if item.modifiers.count > 0:
                caseIndex += 1
                
            if caseIndex == 1:  # 폴리곤, 메시 또는 모디파이어가 있는 경우
                resetXformArray.append(item)
            else:
                nonResetXformArray.append(item)
        
        # 리셋 대상 객체에 XForm 리셋 및 노멀 방향 뒤집기 적용
        for item in resetXformArray:
            rt.ResetXForm(item)
            tempNormalMod = rt.normalModifier()
            tempNormalMod.flip = True
            rt.addModifier(item, tempNormalMod)
            rt.collapseStack(item)
        
        # 처리된 객체들 합치기
        returnArray.extend(resetXformArray)
        returnArray.extend(nonResetXformArray)
        
        return returnArray