#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
모프(Morph) 모듈 - 3ds Max용 모프 타겟 관련 기능 제공
원본 MAXScript의 morph.ms를 Python으로 변환하였으며, pymxs 모듈 기반으로 구현됨
"""

from dataclasses import dataclass
from pymxs import runtime as rt


@dataclass
class MorphChannel:
    """
    모프 채널 정보를 저장하는 데이터 클래스
    """
    index: int = 0
    name: str = ""
    hasData: bool = False


class Morph:
    """
    모프(Morph) 관련 기능을 제공하는 클래스.
    MAXScript의 _Morph 구조체 개념을 Python으로 재구현한 클래스이며,
    3ds Max의 기능들을 pymxs API를 통해 제어합니다.
    """
    
    def __init__(self):
        """클래스 초기화"""
        self.channelMaxViewNum = 100
    
    def get_modifier_index(self, inObj):
        """
        객체에서 Morpher 모디파이어의 인덱스를 찾음
        
        Args:
            inObj: 검색할 객체
            
        Returns:
            Morpher 모디파이어의 인덱스 (없으면 0)
        """
        returnVal = 0
        if len(inObj.modifiers) > 0:
            for i in range(len(inObj.modifiers)):
                if rt.classOf(inObj.modifiers[i]) == rt.Morpher:
                    returnVal = i + 1  # MaxScript는 1부터 시작하므로 +1 추가
        
        return returnVal
    
    def get_modifier(self, inObj):
        """
        객체에서 Morpher 모디파이어를 찾음
        
        Args:
            inObj: 검색할 객체
            
        Returns:
            Morpher 모디파이어 (없으면 None)
        """
        returnVal = None
        modIndex = self.get_modifier_index(inObj)
        if modIndex > 0:
            returnVal = inObj.modifiers[modIndex - 1]  # Python 인덱스는 0부터 시작하므로 -1 조정
        
        return returnVal
    
    def get_channel_num(self, inObj):
        """
        객체의 Morpher에 있는 채널 수를 반환
        
        Args:
            inObj: 검색할 객체
            
        Returns:
            모프 채널 수
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
        객체의 모든 모프 채널 정보를 가져옴
        
        Args:
            inObj: 검색할 객체
            
        Returns:
            MorphChannel 객체의 리스트
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
        특정 인덱스에 모프 타겟 추가
        
        Args:
            inObj: 모프를 적용할 객체
            inTarget: 타겟 객체
            inIndex: 채널 인덱스
            
        Returns:
            성공 여부 (True/False)
        """
        returnVal = False
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            rt.WM3_MC_BuildFromNode(morphMod, inIndex, inTarget)
            returnVal = rt.WM3_MC_HasData(morphMod, inIndex)
        
        return returnVal
    
    def add_targets(self, inObj, inTargetArray):
        """
        여러 타겟 객체를 순서대로 모프 채널에 추가
        
        Args:
            inObj: 모프를 적용할 객체
            inTargetArray: 타겟 객체 배열
        """
        morphMod = self.get_modifier(inObj)
        
        if morphMod is not None:
            for i in range(len(inTargetArray)):
                rt.WM3_MC_BuildFromNode(morphMod, i + 1, inTargetArray[i])
    
    def get_all_channel_name(self, inObj):
        """
        객체의 모든 모프 채널 이름을 가져옴
        
        Args:
            inObj: 검색할 객체
            
        Returns:
            채널 이름 리스트
        """
        returnVal = []
        channelArray = self.get_all_channel_info(inObj)
        
        if len(channelArray) > 0:
            returnVal = [item.name for item in channelArray]
        
        return returnVal
    
    def get_channel_name(self, inObj, inIndex):
        """
        특정 인덱스의 모프 채널 이름을 가져옴
        
        Args:
            inObj: 검색할 객체
            inIndex: 채널 인덱스
            
        Returns:
            채널 이름 (없으면 빈 문자열)
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
        채널 이름으로 모프 채널 인덱스를 가져옴
        
        Args:
            inObj: 검색할 객체
            inName: 채널 이름
            
        Returns:
            채널 인덱스 (없으면 0)
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
        채널 이름으로 모프 채널 값을 가져옴
        
        Args:
            inObj: 검색할 객체
            inName: 채널 이름
            
        Returns:
            채널 값 (0.0 ~ 100.0)
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
        인덱스로 모프 채널 값을 가져옴
        
        Args:
            inObj: 검색할 객체
            inIndex: 채널 인덱스
            
        Returns:
            채널 값 (0.0 ~ 100.0)
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
        채널 이름으로 모프 채널 값을 설정
        
        Args:
            inObj: 모프를 적용할 객체
            inName: 채널 이름
            inVal: 설정할 값 (0.0 ~ 100.0)
            
        Returns:
            성공 여부 (True/False)
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
        인덱스로 모프 채널 값을 설정
        
        Args:
            inObj: 모프를 적용할 객체
            inIndex: 채널 인덱스
            inVal: 설정할 값 (0.0 ~ 100.0)
            
        Returns:
            성공 여부 (True/False)
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
        채널 이름을 이름으로 검색하여 변경
        
        Args:
            inObj: 모프를 적용할 객체
            inTargetName: 대상 채널의 현재 이름
            inNewName: 설정할 새 이름
            
        Returns:
            성공 여부 (True/False)
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
        채널 이름을 인덱스로 검색하여 변경
        
        Args:
            inObj: 모프를 적용할 객체
            inIndex: 대상 채널 인덱스
            inName: 설정할 이름
            
        Returns:
            성공 여부 (True/False)
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
        모든 모프 채널 값을 0으로 리셋
        
        Args:
            inObj: 리셋할 객체
        """
        totalChannelNum = self.get_channel_num(inObj)
        
        if totalChannelNum > 0:
            for i in range(1, totalChannelNum + 1):
                self.set_channel_value_by_index(inObj, i, 0.0)
    
    def extract_morph_channel_geometry(self, obj, _feedback_=False):
        """
        모프 채널의 기하학적 형태를 추출하여 개별 객체로 생성
        
        Args:
            obj: 추출 대상 객체
            _feedback_: 피드백 메시지 출력 여부
            
        Returns:
            추출된 객체 배열
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
