#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# 모프(Morph) 모듈

3ds Max에서 모프 타겟 및 채널을 관리하는 기능을 제공하는 모듈입니다.

## 주요 기능
- Morpher 모디파이어 관리 및 조작
- 모프 채널 정보 추출 및 설정
- 모프 타겟 추가 및 제거
- 모프 값 설정 및 조회
- 모프 채널 지오메트리 추출

## 구현 정보
- 원본 MAXScript의 morph.ms를 Python으로 변환
- pymxs 모듈을 통해 3ds Max API 접근
- Morpher 모디파이어의 WM3 함수 활용
"""

from dataclasses import dataclass
from pymxs import runtime as rt


@dataclass
class MorphChannel:
    """
    # MorphChannel 클래스
    
    모프 채널 정보를 저장하는 데이터 클래스입니다.
    
    ## 속성
    - index (int): 채널 인덱스
    - name (str): 채널 이름
    - hasData (bool): 채널 데이터 존재 여부
    """
    index: int = 0
    name: str = ""
    hasData: bool = False


class Morph:
    """
    # Morph 클래스
    
    3ds Max에서 모프 타겟 및 채널을 관리하는 기능을 제공합니다.
    
    ## 주요 기능
    - Morpher 모디파이어 검색 및 접근
    - 모프 채널 정보 조회 및 관리
    - 모프 타겟 추가 및 조작
    - 모프 채널 값 읽기 및 설정
    - 모프 채널 이름 변경
    - 모프 채널 지오메트리 추출
    
    ## 구현 정보
    - MAXScript의 _Morph 구조체를 Python 클래스로 재구현
    - WM3 함수를 사용하여 Morpher 모디파이어의 내부 속성 접근
    
    ## 사용 예시
    ```python
    # Morph 객체 생성
    morph = Morph()
    
    # 객체에서 모프 채널 정보 가져오기
    channels = morph.get_all_channel_info(obj)
    
    # 모프 타겟 추가
    morph.add_target(obj, target, 1)
    
    # 모프 값 설정
    morph.set_channel_value_by_name(obj, "Smile", 50.0)
    ```
    """
    
    def __init__(self):
        """
        Morph 클래스를 초기화합니다.
        
        채널 최대 뷰 개수를 100개로 설정합니다.
        """
        self.channelMaxViewNum = 100
    
    def get_modifier_index(self, inObj):
        """
        객체에서 Morpher 모디파이어의 인덱스를 찾습니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
            
        ## Returns
        - int: Morpher 모디파이어의 인덱스 (1부터 시작, 없으면 0)
        
        ## 동작 방식
        객체의 모디파이어 스택을 순회하며 Morpher 타입의 모디파이어를 찾습니다.
        """
        returnVal = 0
        if len(inObj.modifiers) > 0:
            for i in range(len(inObj.modifiers)):
                if rt.classOf(inObj.modifiers[i]) == rt.Morpher:
                    returnVal = i + 1  # MaxScript는 1부터 시작하므로 +1 추가
        
        return returnVal
    
    def get_modifier(self, inObj):
        """
        객체에서 Morpher 모디파이어를 찾습니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
            
        ## Returns
        - Morpher: Morpher 모디파이어 객체 (없으면 None)
        
        ## 동작 방식
        get_modifier_index 함수로 찾은 인덱스를 사용하여 모디파이어 객체를 반환합니다.
        """
        returnVal = None
        modIndex = self.get_modifier_index(inObj)
        if modIndex > 0:
            returnVal = inObj.modifiers[modIndex - 1]  # Python 인덱스는 0부터 시작하므로 -1 조정
        
        return returnVal
    
    def get_channel_num(self, inObj):
        """
        객체의 Morpher에 있는 채널 수를 반환합니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
            
        ## Returns
        - int: 모프 채널 수 (0부터 시작)
        
        ## 동작 방식
        1. Morpher 모디파이어 찾기
        2. 각 채널을 순서대로 확인하며 데이터가 있는지 검사
        3. 데이터가 없는 첫 번째 채널 인덱스-1 반환
        """
        returnVal = 0
        morphMod = self.get_modifier(inObj)
        if morphMod is not None:
            morphChannelExistance = True
            morphChannelCounter = 0
            
            while morphChannelExistance:
                for i in range(morphChannelCounter + 1, morphChannelCounter + self.channelMaxViewNum + 1):
                    if not rt.WM3_MC_HasData(morphMod, i):
                        returnVal = i - 1
                        morphChannelExistance = False
                        break
                
                morphChannelCounter += self.channelMaxViewNum
        
        return returnVal
    
    def get_all_channel_info(self, inObj):
        """
        객체의 모든 모프 채널 정보를 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
            
        ## Returns
        - list: MorphChannel 객체의 리스트
        
        ## 동작 방식
        1. Morpher 모디파이어와 채널 수 확인
        2. 각 채널별로 인덱스, 데이터 존재 여부, 이름 정보를 수집
        3. MorphChannel 객체 리스트로 반환
        """
        returnVal = []
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            channelNum = self.get_channel_num(inObj)
            if channelNum > 0:
                for i in range(1, channelNum + 1):
                    tempChannel = MorphChannel()
                    tempChannel.index = i
                    tempChannel.hasData = rt.WM3_MC_HasData(morphMod, i)
                    tempChannel.name = rt.WM3_MC_GetName(morphMod, i)
                    returnVal.append(tempChannel)
        
        return returnVal
    
    def add_target(self, inObj, inTarget, inIndex):
        """
        특정 인덱스에 모프 타겟을 추가합니다.
        
        ## Parameters
        - inObj (MaxObject): 모프를 적용할 객체
        - inTarget (MaxObject): 타겟 객체
        - inIndex (int): 채널 인덱스
            
        ## Returns
        - bool: 성공 여부 (True/False)
        
        ## 동작 방식
        1. Morpher 모디파이어 찾기
        2. WM3_MC_BuildFromNode 함수로 타겟 설정
        3. 설정 후 데이터 존재 여부로 성공 확인
        """
        returnVal = False
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            rt.WM3_MC_BuildFromNode(morphMod, inIndex, inTarget)
            returnVal = rt.WM3_MC_HasData(morphMod, inIndex)
        
        return returnVal
    
    def add_targets(self, inObj, inTargetArray):
        """
        여러 타겟 객체를 순서대로 모프 채널에 추가합니다.
        
        ## Parameters
        - inObj (MaxObject): 모프를 적용할 객체
        - inTargetArray (list): 타겟 객체 배열
        
        ## 동작 방식
        각 타겟 객체를 순서대로 인덱스 1부터 시작하여 채널에 추가합니다.
        """
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            for i in range(len(inTargetArray)):
                rt.WM3_MC_BuildFromNode(morphMod, i + 1, inTargetArray[i])
    
    def get_all_channel_name(self, inObj):
        """
        객체의 모든 모프 채널 이름을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
            
        ## Returns
        - list: 채널 이름 리스트
        
        ## 동작 방식
        get_all_channel_info 함수의 결과에서 name 필드만 추출합니다.
        """
        returnVal = []
        channelArray = self.get_all_channel_info(inObj)
        
        if len(channelArray) > 0:
            returnVal = [item.name for item in channelArray]
        
        return returnVal
    
    def get_channel_name(self, inObj, inIndex):
        """
        특정 인덱스의 모프 채널 이름을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
        - inIndex (int): 채널 인덱스
            
        ## Returns
        - str: 채널 이름 (없으면 빈 문자열)
        
        ## 동작 방식
        get_all_channel_info 함수의 결과에서 지정된 인덱스의 이름을 반환합니다.
        """
        returnVal = ""
        channelArray = self.get_all_channel_info(inObj)
        
        try:
            if len(channelArray) > 0:
                returnVal = channelArray[inIndex - 1].name
        except:
            returnVal = ""
        
        return returnVal
    
    def get_channelIndex(self, inObj, inName):
        """
        채널 이름으로 모프 채널 인덱스를 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
        - inName (str): 채널 이름
            
        ## Returns
        - int: 채널 인덱스 (없으면 0)
        
        ## 동작 방식
        get_all_channel_info 함수의 결과에서 지정된 이름의 채널 인덱스를 찾습니다.
        """
        returnVal = 0
        channelArray = self.get_all_channel_info(inObj)
        
        if len(channelArray) > 0:
            for item in channelArray:
                if item.name == inName:
                    returnVal = item.index
                    break
        
        return returnVal
    
    def get_channel_value_by_name(self, inObj, inName):
        """
        채널 이름으로 모프 채널 값을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
        - inName (str): 채널 이름
            
        ## Returns
        - float: 채널 값 (0.0 ~ 100.0)
        
        ## 동작 방식
        1. 채널 이름으로 인덱스 검색
        2. 인덱스가 유효하면 WM3_MC_GetValue 함수로 값 반환
        """
        returnVal = 0.0
        channelIndex = self.get_channelIndex(inObj, inName)
        morphMod = self.get_modifier(inObj)
        
        if channelIndex > 0:
            try:
                returnVal = rt.WM3_MC_GetValue(morphMod, channelIndex)
            except:
                returnVal = 0.0
        
        return returnVal
    
    def get_channel_value_by_index(self, inObj, inIndex):
        """
        인덱스로 모프 채널 값을 가져옵니다.
        
        ## Parameters
        - inObj (MaxObject): 검색할 객체
        - inIndex (int): 채널 인덱스
            
        ## Returns
        - float: 채널 값 (0.0 ~ 100.0)
        
        ## 동작 방식
        Morpher 모디파이어와 인덱스가 유효하면 WM3_MC_GetValue 함수로 값 반환
        """
        returnVal = 0
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            try:
                returnVal = rt.WM3_MC_GetValue(morphMod, inIndex)
            except:
                returnVal = 0
        
        return returnVal
    
    def set_channel_value_by_name(self, inObj, inName, inVal):
        """
        채널 이름으로 모프 채널 값을 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 모프를 적용할 객체
        - inName (str): 채널 이름
        - inVal (float): 설정할 값 (0.0 ~ 100.0)
            
        ## Returns
        - bool: 성공 여부 (True/False)
        
        ## 동작 방식
        1. 채널 이름으로 인덱스 검색
        2. 인덱스가 유효하면 WM3_MC_SetValue 함수로 값 설정
        """
        returnVal = False
        morphMod = self.get_modifier(inObj)
        channelIndex = self.get_channelIndex(inObj, inName)
        
        if channelIndex > 0:
            try:
                rt.WM3_MC_SetValue(morphMod, channelIndex, inVal)
                returnVal = True
            except:
                returnVal = False
        
        return returnVal
    
    def set_channel_value_by_index(self, inObj, inIndex, inVal):
        """
        인덱스로 모프 채널 값을 설정합니다.
        
        ## Parameters
        - inObj (MaxObject): 모프를 적용할 객체
        - inIndex (int): 채널 인덱스
        - inVal (float): 설정할 값 (0.0 ~ 100.0)
            
        ## Returns
        - bool: 성공 여부 (True/False)
        
        ## 동작 방식
        Morpher 모디파이어와 인덱스가 유효하면 WM3_MC_SetValue 함수로 값 설정
        """
        returnVal = False
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            try:
                rt.WM3_MC_SetValue(morphMod, inIndex, inVal)
                returnVal = True
            except:
                returnVal = False
        
        return returnVal
    
    def set_channel_name_by_name(self, inObj, inTargetName, inNewName):
        """
        채널 이름을 이름으로 검색하여 변경합니다.
        
        ## Parameters
        - inObj (MaxObject): 모프를 적용할 객체
        - inTargetName (str): 대상 채널의 현재 이름
        - inNewName (str): 설정할 새 이름
            
        ## Returns
        - bool: 성공 여부 (True/False)
        
        ## 동작 방식
        1. 채널 이름으로 인덱스 검색
        2. 인덱스가 유효하면 WM3_MC_SetName 함수로 이름 변경
        """
        returnVal = False
        channelIndex = self.get_channelIndex(inObj, inTargetName)
        morphMod = self.get_modifier(inObj)
        
        if channelIndex > 0:
            rt.WM3_MC_SetName(morphMod, channelIndex, inNewName)
            returnVal = True
        
        return returnVal
    
    def set_channel_name_by_index(self, inObj, inIndex, inName):
        """
        채널 이름을 인덱스로 검색하여 변경합니다.
        
        ## Parameters
        - inObj (MaxObject): 모프를 적용할 객체
        - inIndex (int): 대상 채널 인덱스
        - inName (str): 설정할 이름
            
        ## Returns
        - bool: 성공 여부 (True/False)
        
        ## 동작 방식
        Morpher 모디파이어와 인덱스가 유효하면 WM3_MC_SetName 함수로 이름 변경
        """
        returnVal = False
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            try:
                rt.WM3_MC_SetName(morphMod, inIndex, inName)
                returnVal = True
            except:
                returnVal = False
        
        return returnVal
    
    def reset_all_channel_value(self, inObj):
        """
        모든 모프 채널 값을 0으로 리셋합니다.
        
        ## Parameters
        - inObj (MaxObject): 리셋할 객체
        
        ## 동작 방식
        1. 채널 수 확인
        2. 모든 채널의 값을 0.0으로 설정
        """
        totalChannelNum = self.get_channel_num(inObj)
        
        if totalChannelNum > 0:
            for i in range(1, totalChannelNum + 1):
                self.set_channel_value_by_index(inObj, i, 0.0)
    
    def extract_morph_channel_geometry(self, obj, _feedback_=False):
        """
        모프 채널의 기하학적 형태를 추출하여 개별 객체로 생성합니다.
        
        ## Parameters
        - obj (MaxObject): 추출 대상 객체
        - _feedback_ (bool): 피드백 메시지 출력 여부 (기본값: False)
            
        ## Returns
        - list: 추출된 객체 배열
        
        ## 동작 방식
        1. 유효한 Morpher 모디파이어 확인
        2. 데이터가 있는 모든 채널 인덱스 수집
        3. 각 채널별로:
           - 채널 값을 100%로 설정
           - 스냅샷을 만들어 채널 이름으로 명명
           - 채널 값을 0%로 복원
        4. 모든 스냅샷 객체 반환
        """
        extractedObjs = []
        morphMod = self.get_modifier(obj)
        
        if rt.IsValidMorpherMod(morphMod):
            # 데이터가 있는 모든 채널 인덱스 수집
            channels = [i for i in range(1, rt.WM3_NumberOfChannels(morphMod) + 1) 
                        if rt.WM3_MC_HasData(morphMod, i)]
            
            for i in channels:
                channelName = rt.WM3_MC_GetName(morphMod, i)
                rt.WM3_MC_SetValue(morphMod, i, 100.0)
                
                objSnapshot = rt.snapshot(obj)
                objSnapshot.name = channelName
                extractedObjs.append(objSnapshot)
                
                rt.WM3_MC_SetValue(morphMod, i, 0.0)
                
                if _feedback_:
                    print(f" - FUNCTION - [ extract_morph_channel_geometry ] - Extracted ---- {objSnapshot.name} ---- successfully!!")
        else:
            if _feedback_:
                print(f" - FUNCTION - [ extract_morph_channel_geometry ] - No valid morpher found on ---- {obj.name} ---- ")
        
        return extractedObjs
