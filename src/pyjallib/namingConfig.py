#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
namingConfig 모듈 - Naming 클래스의 설정을 관리하는 기능 제공
NamePart 객체를 기반으로 네이밍 설정을 저장하고 불러오는 기능 구현
"""

import json
import os
import copy
from typing import List, Dict, Any, Optional, Union
import csv # Import the csv module


# NamePart 클래스 임포트
from pyjallib.namePart import NamePart, NamePartType


class NamingConfig:
    """
    Naming 클래스의 설정을 관리하는 클래스.
    NamePart 객체 리스트를 관리하고 JSON 파일로 저장/불러오기 기능 제공.
    """
    
    def __init__(self, padding_num: int = 2, name_parts: Optional[List[NamePart]] = None, 
                 config_file_path: str = "", default_file_name: str = "namingConfig.json", 
                 required_parts: Optional[List[str]] = None):
        """
        클래스 초기화 및 기본 설정값 정의
        
        Args:
            padding_num: 인덱스 패딩 자릿수 (기본값: 2)
            name_parts: 초기 NamePart 객체 리스트 (기본값: None, 기본 파트로 초기화)
            config_file_path: 설정 파일 경로 (기본값: 빈 문자열)
            default_file_name: 기본 파일명 (기본값: "namingConfig.json")
            required_parts: 필수 namePart 목록 (기본값: ["RealName"])
        """
        # NamePart 객체 리스트
        self.name_parts = name_parts or []
        
        # 추가 설정
        self.padding_num = padding_num
        
        # NamePart 순서 정보 저장
        self.part_order = []
        
        # 필수 namePart 정의 (삭제 불가능)
        self.required_parts = required_parts or ["RealName"]
        
        # 설정 파일 경로 및 기본 파일명
        self.config_file_path = config_file_path
        self.default_file_name = default_file_name
        
        # 스크립트 디렉토리 기준 기본 경로 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, "ConfigFiles")
        self.default_file_path = os.path.join(config_dir, self.default_file_name)
        
        # name_parts가 제공되지 않은 경우에만 기본 NamePart 초기화
        if not self.name_parts:
            self._initialize_default_parts()
        else:
            # 제공된 name_parts가 있는 경우 순서 업데이트 및 타입 자동 업데이트
            self._update_part_order()
            self._update_part_types_based_on_order()
    
    def _initialize_default_parts(self):
        """기본 NamePart 객체들 초기화"""
        # 기본 순서 정의 (명시적으로 순서를 저장)
        self.part_order = []
        
        # Prefix 부분 (PREFIX 타입)
        prefixPart = NamePart("Prefix", NamePartType.PREFIX, ["Pr"], ["Prefix"], False, ["접두사"]) # Add korean descriptions
        
        # RealName 부분 (REALNAME 타입)
        realNamePart = NamePart("RealName", NamePartType.REALNAME, [], [], False, []) # Add korean descriptions
        
        # Index 부분 (INDEX 타입)
        indexPart = NamePart("Index", NamePartType.INDEX, [], [], False, []) # Add korean descriptions
        
        # Suffix 부분 (SUFFIX 타입)
        suffixPart = NamePart("Suffix", NamePartType.SUFFIX, ["Su"], ["Suffix"], False, ["접미사"]) # Add korean descriptions
        
        # 기본 순서대로 설정
        self.name_parts = [prefixPart, realNamePart, indexPart, suffixPart]
        
        self._update_part_order()  # 초기화 후 순서 업데이트
        
        # 타입 자동 업데이트
        self._update_part_types_based_on_order()
    
    def _update_part_order(self):
        """
        NamePart 순서 업데이트 - 기본적으로 NamePart 객체의 순서에 따라 업데이트
        """
        self.part_order = [part.get_name() for part in self.name_parts]
    
    def _get_real_name_index(self) -> int:
        """
        RealName 파트의 인덱스를 반환합니다.
        
        Returns:
            RealName 파트의 인덱스, 없으면 -1
        """
        for i, part in enumerate(self.name_parts):
            if part.get_type().value == NamePartType.REALNAME.value:
                return i
        return -1
    
    def _update_part_types_based_on_order(self) -> bool:
        """
        NamePart 순서에 따라 파트의 타입을 자동으로 업데이트합니다.
        RealName을 기준으로 앞에 있는 파트는 PREFIX, 뒤에 있는 파트는 SUFFIX로 설정합니다.
        (RealName과 Index 파트는 예외)
        
        Returns:
            업데이트 성공 여부 (True/False)
        """
        # RealName 파트 인덱스 찾기
        real_name_index = self._get_real_name_index()
        if real_name_index == -1:
            print("경고: RealName 파트를 찾을 수 없어 타입 자동 업데이트를 수행할 수 없습니다.")
            return False
        
        # 각 파트의 타입을 순서에 따라 업데이트
        for i, part in enumerate(self.name_parts):
            partName = part.get_name()
            
            # RealName은 항상 REALNAME 타입
            if partName == "RealName":
                part.set_type(NamePartType.REALNAME)
                continue
                
            # Index는 항상 INDEX 타입
            if partName == "Index":
                part.set_type(NamePartType.INDEX)
                continue
            
            # RealName 앞의 파트는 PREFIX, 뒤의 파트는 SUFFIX
            if i < real_name_index:
                part.set_type(NamePartType.PREFIX)
            else:
                part.set_type(NamePartType.SUFFIX)
        
        return True
    
    def get_part_names(self) -> List[str]:
        """
        모든 NamePart 이름 목록 반환
        
        Returns:
            NamePart 이름 목록
        """
        return [part.get_name() for part in self.name_parts]
    
    def get_part_order(self) -> List[str]:
        """
        NamePart 순서 목록 반환
        
        Returns:
            NamePart 이름 순서 목록
        """
        return self.part_order.copy()
    
    def get_part(self, name: str) -> Optional[NamePart]:
        """
        이름으로 NamePart 객체 가져오기
        
        Args:
            name: NamePart 이름
            
        Returns:
            NamePart 객체, 없으면 None
        """
        for part in self.name_parts:
            if part.get_name() == name:
                return part
        return None
    
    def add_part(self, name: str, part_type: NamePartType = NamePartType.UNDEFINED, 
                 values: Optional[List[str]] = None, descriptions: Optional[List[str]] = None,
                 korean_descriptions: Optional[List[str]] = None) -> bool: # Add korean_descriptions parameter
        """
        새 NamePart 객체 추가
        
        Args:
            name: 추가할 NamePart 이름
            part_type: NamePart 타입 (기본값: UNDEFINED)
            values: 사전 정의된 값 목록 (기본값: None)
            descriptions: 값에 대한 설명 목록 (기본값: None, 값과 동일하게 설정됨)
            korean_descriptions: 값에 대한 한국어 설명 목록 (기본값: None, 값과 동일하게 설정됨) # Add korean_descriptions doc
            
        Returns:
            추가 성공 여부 (True/False)
        """
        if not name:
            print("오류: 유효한 NamePart 이름을 입력하세요.")
            return False
        
        # 이미 존재하는지 확인
        if self.get_part(name) is not None:
            print(f"오류: '{name}' NamePart가 이미 존재합니다.")
            return False
        
        # 새 NamePart 객체 생성 - NamePart 클래스의 생성자 활용
        new_part = NamePart(name, part_type, values or [], descriptions, False, korean_descriptions) # Pass korean_descriptions
        
        # 리스트에 추가
        self.name_parts.append(new_part)
        
        # 순서 목록에 추가
        if name not in self.part_order:
            self.part_order.append(name)
        
        # 순서에 따라 타입 업데이트
        self._update_part_types_based_on_order()
        return True
    
    def remove_part(self, name: str) -> bool:
        """
        NamePart 객체 제거 (필수 부분은 제거 불가)
        
        Args:
            name: 제거할 NamePart 이름
            
        Returns:
            제거 성공 여부 (True/False)
        """
        # 필수 부분은 제거 불가능
        if name in self.required_parts:
            print(f"오류: 필수 NamePart '{name}'는 제거할 수 없습니다.")
            return False
        
        # 찾아서 제거
        for i, part in enumerate(self.name_parts):
            if part.get_name() == name:
                del self.name_parts[i]
                
                # 순서 목록에서도 제거
                if name in self.part_order:
                    self.part_order.remove(name)
                
                # 순서에 따라 타입 업데이트
                self._update_part_types_based_on_order()
                return True
        
        print(f"오류: '{name}' NamePart가 존재하지 않습니다.")
        return False
    
    def reorder_parts(self, new_order: List[str]) -> bool:
        """
        NamePart 순서 변경
        
        Args:
            new_order: 새로운 NamePart 이름 순서 배열
            
        Returns:
            변경 성공 여부 (True/False)
        """
        # 배열 길이 확인
        if len(new_order) != len(self.name_parts):
            print("오류: 새 순서의 항목 수가 기존 NamePart와 일치하지 않습니다.")
            return False
        
        # 모든 필수 부분이 포함되어 있는지 확인
        for part in self.required_parts:
            if part not in new_order:
                print(f"오류: 필수 NamePart '{part}'가 새 순서에 포함되어 있지 않습니다.")
                return False
        
        # 모든 이름이 현재 존재하는지 확인
        current_names = self.get_part_names()
        for name in new_order:
            if name not in current_names:
                print(f"오류: '{name}' NamePart가 존재하지 않습니다.")
                return False
        
        # 순서 변경을 위한 새 리스트 생성
        reordered_parts = []
        for name in new_order:
            part = self.get_part(name)
            if part:
                reordered_parts.append(part)
        
        # 새 순서로 업데이트
        self.name_parts = reordered_parts
        self.part_order = new_order.copy()
        
        # 순서에 따라 타입 업데이트
        self._update_part_types_based_on_order()
        return True
    
    def set_padding_num(self, padding_num: int) -> bool:
        """
        인덱스 자릿수 설정
        
        Args:
            padding_num: 설정할 패딩 자릿수
            
        Returns:
            설정 성공 여부 (True/False)
        """
        if not isinstance(padding_num, int) or padding_num < 1:
            print("오류: 패딩 자릿수는 1 이상의 정수여야 합니다.")
            return False
        
        self.padding_num = padding_num
        return True
        
    def set_part_type(self, part_name: str, part_type: NamePartType) -> bool:
        """
        특정 NamePart의 타입 설정
        
        Args:
            part_name: NamePart 이름
            part_type: 설정할 타입 (NamePartType 열거형 값)
            
        Returns:
            설정 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # 필수 RealName 부분은 항상 REALNAME 타입이어야 함
        if part_name == "RealName" and part_type.value != NamePartType.REALNAME.value:
            print("오류: RealName 부분은 반드시 REALNAME 타입이어야 합니다.")
            return False
        
        # Index 부분은 항상 INDEX 타입이어야 함
        if part_name == "Index" and part_type.value != NamePartType.INDEX.value:
            print("오류: Index 부분은 반드시 INDEX 타입이어야 합니다.")
            return False
        
        part.set_type(part_type)
        return True
    
    def get_part_type(self, part_name: str) -> Optional[NamePartType]:
        """
        특정 NamePart의 타입 가져오기
        
        Args:
            part_name: NamePart 이름
            
        Returns:
            NamePart 타입, 없으면 None
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return None
        
        return part.get_type()
    
    def set_part_values(self, part_name: str, values: List[str], 
                        descriptions: Optional[List[str]] = None, 
                        korean_descriptions: Optional[List[str]] = None) -> bool: # Add korean_descriptions parameter
        """
        특정 NamePart의 사전 정의 값 설정
        
        Args:
            part_name: NamePart 이름
            values: 설정할 사전 정의 값 리스트
            descriptions: 설정할 설명 목록 (기본값: None, 값과 같은 설명 사용)
            korean_descriptions: 설정할 한국어 설명 목록 (기본값: None, 값과 같은 설명 사용) # Add korean_descriptions doc
            
        Returns:
            설정 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # REALNAME이나 INDEX 타입은 사전 정의 값 설정 불가
        if part.is_realname() or part.is_index():
            print(f"오류: {part_name} 부분은 {part.get_type().name} 타입이므로 사전 정의 값을 설정할 수 없습니다.")
            return False
        
        if not values:
            print(f"오류: {part_name} 부분의 사전 정의 값은 적어도 하나 이상 있어야 합니다.")
            return False
        
        # 값 설정
        part.set_predefined_values(values, descriptions, korean_descriptions) # Pass korean_descriptions
        
        return True
    
    def set_part_value_by_csv(self, part_name: str, csv_file_path: str) -> bool:
        """
        특정 NamePart의 사전 정의 값을 CSV 파일로 설정
        CSV 파일 형식: value,description,koreanDescription (각 줄당)
        
        Args:
            part_name: NamePart 이름
            csv_file_path: CSV 파일 경로
            
        Returns:
            설정 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # REALNAME이나 INDEX 타입은 사전 정의 값 설정 불가
        if part.is_realname() or part.is_index():
            print(f"오류: {part_name} 부분은 {part.get_type().name} 타입이므로 사전 정의 값을 설정할 수 없습니다.")
            return False
        
        # CSV 파일에서 값, 설명, 한국어 설명 읽기
        values = []
        descriptions = []
        korean_descriptions = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3: # Ensure row has at least 3 columns
                        value = row[0].strip()
                        description = row[1].strip()
                        korean_description = row[2].strip()
                        if value: # Skip empty values
                            values.append(value)
                            descriptions.append(description if description else value) # Use value if description is empty
                            korean_descriptions.append(korean_description if korean_description else value) # Use value if korean_description is empty
                    elif len(row) == 2: # Handle case with value and description only
                        value = row[0].strip()
                        description = row[1].strip()
                        if value:
                            values.append(value)
                            descriptions.append(description if description else value)
                            korean_descriptions.append(value) # Use value as korean description
                    elif len(row) == 1: # Handle case with value only
                        value = row[0].strip()
                        if value:
                            values.append(value)
                            descriptions.append(value)
                            korean_descriptions.append(value)

            if not values:
                print(f"오류: CSV 파일 '{csv_file_path}'에서 유효한 값을 찾을 수 없습니다.")
                return False

            # 값, 설명, 한국어 설명 설정
            return self.set_part_values(part_name, values, descriptions, korean_descriptions)
        except FileNotFoundError:
            print(f"오류: CSV 파일을 찾을 수 없습니다: {csv_file_path}")
            return False
        except Exception as e:
            print(f"오류: CSV 파일을 읽는 중 오류 발생: {e}")
            return False
    
    def add_part_value(self, part_name: str, value: str, 
                       description: Optional[str] = None, 
                       korean_description: Optional[str] = None) -> bool: # Add korean_description parameter
        """
        특정 NamePart에 사전 정의 값 추가
        
        Args:
            part_name: NamePart 이름
            value: 추가할 사전 정의 값
            description: 추가할 값의 설명 (기본값: None, 값과 같은 설명 사용)
            korean_description: 추가할 값의 한국어 설명 (기본값: None, 값과 같은 설명 사용) # Add korean_description doc
            
        Returns:
            추가 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # REALNAME이나 INDEX 타입은 사전 정의 값 추가 불가
        if part.is_realname() or part.is_index():
            print(f"오류: {part_name} 부분은 {part.get_type().name} 타입이므로 사전 정의 값을 추가할 수 없습니다.")
            return False
        
        # 값이 이미 존재하는지 확인
        if part.contains_value(value):
            print(f"오류: '{value}'가 이미 {part_name} 부분의 사전 정의 값에 존재합니다.")
            return False
        
        # description이 없으면 값을 설명으로 사용
        if description is None:
            description = value
            
        # korean_description이 없으면 값을 설명으로 사용
        if korean_description is None:
            korean_description = value
            
        # NamePart 클래스의 add_predefined_value 메소드 직접 활용
        return part.add_predefined_value(value, description, korean_description) # Pass korean_description
    
    def remove_part_value(self, part_name: str, value: str) -> bool:
        """
        특정 NamePart에서 사전 정의 값과 해당 설명 제거
        
        Args:
            part_name: NamePart 이름
            value: 제거할 사전 정의 값
            
        Returns:
            제거 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # REALNAME이나 INDEX 타입은 사전 정의 값 제거 불가
        if part.is_realname() or part.is_index():
            print(f"오류: {part_name} 부분은 {part.get_type().name} 타입이므로 사전 정의 값을 제거할 수 없습니다.")
            return False
        
        # 값이 존재하는지 확인
        if not part.contains_value(value):
            print(f"오류: '{value}'가 {part_name} 부분의 사전 정의 값에 존재하지 않습니다.")
            return False
        
        # 마지막 값인지 확인
        if part.get_value_count() <= 1:
            print(f"오류: {part_name} 부분의 사전 정의 값은 적어도 하나 이상 있어야 합니다.")
            return False
        
        # NamePart 클래스의 remove_predefined_value 메소드 직접 활용
        return part.remove_predefined_value(value)
    
    def set_part_descriptions(self, part_name: str, descriptions: List[str]) -> bool:
        """
        특정 NamePart의 설명 목록 설정
        
        Args:
            part_name: NamePart 이름
            descriptions: 설정할 설명 목록
            
        Returns:
            설정 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # REALNAME이나 INDEX 타입은 설명 설정 불가
        if part.is_realname() or part.is_index():
            print(f"오류: {part_name} 부분은 {part.get_type().name} 타입이므로 설명을 설정할 수 없습니다.")
            return False
        
        # NamePart 클래스 메소드 활용하여 설명 설정
        values = part.get_predefined_values()
        
        # 길이 맞추기
        if len(descriptions) < len(values):
            descriptions.extend([""] * (len(values) - len(descriptions)))
        elif len(descriptions) > len(values):
            descriptions = descriptions[:len(values)]
        
        # 각 값에 대한 설명 설정 (NamePart.set_description 사용)
        success = True
        for i, value in enumerate(values):
            if not part.set_description(value, descriptions[i]):
                success = False # 실패 시 기록 (이론상 발생하지 않음)
                
        return success

    def get_part_descriptions(self, part_name: str) -> List[str]:
        """
        특정 NamePart의 설명 목록 가져오기
        
        Args:
            part_name: NamePart 이름
            
        Returns:
            설명 목록
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return []
        
        return part.get_descriptions()

    def set_part_korean_descriptions(self, part_name: str, korean_descriptions: List[str]) -> bool:
        """
        특정 NamePart의 한국어 설명 목록 설정
        
        Args:
            part_name: NamePart 이름
            korean_descriptions: 설정할 한국어 설명 목록
            
        Returns:
            설정 성공 여부 (True/False)
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return False
        
        # REALNAME이나 INDEX 타입은 설명 설정 불가
        if part.is_realname() or part.is_index():
            print(f"오류: {part_name} 부분은 {part.get_type().name} 타입이므로 한국어 설명을 설정할 수 없습니다.")
            return False
        
        # NamePart 클래스 메소드 활용하여 설명 설정
        values = part.get_predefined_values()
        
        # 길이 맞추기
        if len(korean_descriptions) < len(values):
            korean_descriptions.extend([""] * (len(values) - len(korean_descriptions)))
        elif len(korean_descriptions) > len(values):
            korean_descriptions = korean_descriptions[:len(values)]
            
        # 각 값에 대한 한국어 설명 설정 (NamePart.set_korean_description 사용)
        success = True
        for i, value in enumerate(values):
            if not part.set_korean_description(value, korean_descriptions[i]):
                success = False # 실패 시 기록 (이론상 발생하지 않음)
                
        return success

    def get_part_korean_descriptions(self, part_name: str) -> List[str]:
        """
        특정 NamePart의 한국어 설명 목록 가져오기
        
        Args:
            part_name: NamePart 이름
            
        Returns:
            한국어 설명 목록
        """
        part = self.get_part(part_name)
        if not part:
            print(f"오류: '{part_name}' NamePart가 존재하지 않습니다.")
            return []
        
        return part.get_korean_descriptions()
    
    def get_prefix_parts(self) -> List[NamePart]:
        """
        모든 PREFIX 타입 NamePart 가져오기
        
        Returns:
            PREFIX 타입의 NamePart 객체 리스트
        """
        return [part for part in self.name_parts if part.is_prefix()]
    
    def get_suffix_parts(self) -> List[NamePart]:
        """
        모든 SUFFIX 타입 NamePart 가져오기
        
        Returns:
            SUFFIX 타입의 NamePart 객체 리스트
        """
        return [part for part in self.name_parts if part.is_suffix()]
    
    def get_realname_part(self) -> Optional[NamePart]:
        """
        REALNAME 타입 NamePart 가져오기
        
        Returns:
            REALNAME 타입의 NamePart 객체, 없으면 None
        """
        for part in self.name_parts:
            if part.is_realname():
                return part
        return None
    
    def get_index_part(self) -> Optional[NamePart]:
        """
        INDEX 타입 NamePart 가져오기
        
        Returns:
            INDEX 타입의 NamePart 객체, 없으면 None
        """
        for part in self.name_parts:
            if part.is_index():
                return part
        return None
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """
        현재 설정을 JSON 파일로 저장
        
        Args:
            file_path: 저장할 파일 경로 (기본값: self.default_file_path)
            
        Returns:
            저장 성공 여부 (True/False)
        """
        save_path = file_path or self.default_file_path
        
        try:
            # 저장할 데이터 준비
            save_data = {
                "paddingNum": self.padding_num,
                "partOrder": self.part_order,  # 순서 정보 저장
                "nameParts": []
            }
            
            # 각 NamePart 객체를 딕셔너리로 변환하여 추가
            for part in self.name_parts:
                save_data["nameParts"].append(part.to_dict())
            
            # JSON 파일로 저장
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4, ensure_ascii=False)
            
            self.config_file_path = save_path
            return True
        except Exception as e:
            print(f"설정 저장 중 오류 발생: {e}")
            return False
    
    def load(self, file_path: Optional[str] = None) -> bool:
        """
        JSON 파일에서 설정 불러오기
        
        Args:
            file_path: 불러올 파일 경로 (기본값: self.default_file_path)
            
        Returns:
            로드 성공 여부 (True/False)
        """
        load_path = file_path or self.default_file_path
        
        try:
            if os.path.exists(load_path):
                with open(load_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # 필수 키가 있는지 확인
                if "nameParts" not in loaded_data:
                    print("경고: 설정 파일에 필수 키 'nameParts'가 없습니다.")
                    return False
                
                # paddingNum 불러오기
                if "paddingNum" in loaded_data:
                    self.padding_num = loaded_data["paddingNum"]
                
                # 파트 순서 불러오기
                if "partOrder" in loaded_data:
                    self.part_order = loaded_data["partOrder"]
                else:
                    # 없으면 기본 순서 생성
                    self.part_order = [part_data["name"] for part_data in loaded_data["nameParts"]]
                
                # NamePart 객체 리스트 생성
                new_parts = []
                for part_data in loaded_data["nameParts"]:
                    part = NamePart.from_dict(part_data)
                    new_parts.append(part)
                
                # 필수 NamePart가 포함되어 있는지 확인
                part_names = [part.get_name() for part in new_parts]
                for required_name in self.required_parts:
                    if required_name not in part_names:
                        print(f"경고: 필수 NamePart '{required_name}'가 설정에 포함되어 있지 않습니다.")
                        return False
                
                # 모든 확인이 통과되면 데이터 업데이트
                self.name_parts = new_parts
                self.config_file_path = load_path
                
                # 순서에 따라 타입 업데이트
                self._update_part_types_based_on_order()
                self._update_part_order()  # 순서 업데이트
                return True
            else:
                print(f"설정 파일을 찾을 수 없습니다: {load_path}")
                return False
        except Exception as e:
            print(f"설정 로드 중 오류 발생: {e}")
            return False
    
    def apply_to_naming(self, naming_instance) -> bool:
        """
        설정을 Naming 인스턴스에 적용
        
        Args:
            naming_instance: 설정을 적용할 Naming 클래스 인스턴스
            
        Returns:
            적용 성공 여부 (True/False)
        """
        try:
            # NamePart 객체 리스트 복사하여 적용
            naming_instance._nameParts = copy.deepcopy(self.name_parts)
            
            # paddingNum 설정
            naming_instance._paddingNum = self.padding_num
            
            return True
        except Exception as e:
            print(f"설정 적용 중 오류 발생: {e}")
            return False
    
    def insert_part(self, name: str, part_type: NamePartType, position: int,
                    values: Optional[List[str]] = None, 
                    descriptions: Optional[List[str]] = None,
                    korean_descriptions: Optional[List[str]] = None) -> bool: # Add value/description parameters
        """
        특정 위치에 새 NamePart 삽입
        
        Args:
            name: 삽입할 NamePart 이름
            part_type: NamePart 타입
            position: 삽입할 위치 (인덱스)
            values: 사전 정의된 값 목록 (기본값: None) # Add doc
            descriptions: 값에 대한 설명 목록 (기본값: None) # Add doc
            korean_descriptions: 값에 대한 한국어 설명 목록 (기본값: None) # Add doc
            
        Returns:
            삽입 성공 여부 (True/False)
        """
        if not name:
            print("오류: 유효한 NamePart 이름을 입력하세요.")
            return False
        
        # 이미 존재하는지 확인
        if self.get_part(name) is not None:
            print(f"오류: '{name}' NamePart가 이미 존재합니다.")
            return False
        
        # 위치 범위 확인
        if position < 0 or position > len(self.name_parts):
            print(f"오류: 위치가 유효하지 않습니다. 0에서 {len(self.name_parts)} 사이의 값이어야 합니다.")
            return False
        
        # 새 NamePart 생성 (값과 설명 포함)
        new_part = NamePart(name, part_type, values or [], descriptions, False, korean_descriptions) # Pass values/descriptions
        
        # 지정된 위치에 삽입
        self.name_parts.insert(position, new_part)
        
        # 순서 목록 업데이트
        if name not in self.part_order:
            self.part_order.insert(position, name)
        
        # 순서에 따라 타입 업데이트
        self._update_part_types_based_on_order()
        return True