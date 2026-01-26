"""
3ds Max Motion Capture 및 Biped 처리를 위한 모듈

이 모듈은 FBX 모션 캡처 데이터를 3ds Max Biped로 변환하고 
리타겟팅하는 기능을 제공합니다.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path

class BipedBoneMapping:
    """Biped 본 매핑 관리 클래스"""
    
    def __init__(self):
        self.mapping_data = self._create_default_mapping()
    
    def _create_default_mapping(self) -> Dict[str, Any]:
        """기본 Biped 본 매핑 구조 생성"""
        mapping = {
            "metadata": {
                "UpAxis": "Z"
            },
            "biped_mapping": []
        }
        
        # COM (Center of Mass)
        mapping["biped_mapping"].append({
            "bip": "Com",
            "fbx": "",
            "biped_index": 13,
            "biped_link": 1
        })
        
        # Pelvis
        mapping["biped_mapping"].append({
            "bip": "Pelvis",
            "fbx": "",
            "biped_index": 12,
            "biped_link": 1
        })
        
        # Spine (최대 10개)
        spine_names = ["Spine", "Spine1", "Spine2", "Spine3", "Spine4", 
                      "Spine5", "Spine6", "Spine7", "Spine8", "Spine9"]
        for i, name in enumerate(spine_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 9,
                "biped_link": i + 1
            })
        
        # Neck (최대 25개)
        neck_names = ["Neck"] + [f"Neck{i}" for i in range(1, 25)]
        for i, name in enumerate(neck_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 17,
                "biped_link": i + 1
            })
        
        # Head
        mapping["biped_mapping"].append({
            "bip": "Head",
            "fbx": "",
            "biped_index": 11,
            "biped_link": 1
        })
        
        # Left Arm (4 links: Clavicle, UpperArm, Forearm, Hand)
        left_arm_names = ["L Clavicle", "L UpperArm", "L Forearm", "L Hand"]
        for i, name in enumerate(left_arm_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 1,
                "biped_link": i + 1
            })
        
        # Right Arm (4 links: Clavicle, UpperArm, Forearm, Hand)
        right_arm_names = ["R Clavicle", "R UpperArm", "R Forearm", "R Hand"]
        for i, name in enumerate(right_arm_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 2,
                "biped_link": i + 1
            })
        
        # Left Fingers (5 fingers x 3 links each = 15 links)
        finger_names = ["Finger0", "Finger1", "Finger2", "Finger3", "Finger4"]
        for finger_idx, finger_base in enumerate(finger_names):
            for link_idx in range(3):
                if link_idx == 0:
                    finger_name = f"L {finger_base}"
                else:
                    finger_name = f"L {finger_base}{link_idx}"
                
                mapping["biped_mapping"].append({
                    "bip": finger_name,
                    "fbx": "",
                    "biped_index": 3,
                    "biped_link": finger_idx * 3 + link_idx + 1
                })
        
        # Right Fingers (5 fingers x 3 links each = 15 links)
        for finger_idx, finger_base in enumerate(finger_names):
            for link_idx in range(3):
                if link_idx == 0:
                    finger_name = f"R {finger_base}"
                else:
                    finger_name = f"R {finger_base}{link_idx}"
                
                mapping["biped_mapping"].append({
                    "bip": finger_name,
                    "fbx": "",
                    "biped_index": 4,
                    "biped_link": finger_idx * 3 + link_idx + 1
                })
        
        # Left Leg (4 links: Thigh, Calf, HorseLink, Foot)
        left_leg_names = ["L Thigh", "L Calf", "L HorseLink", "L Foot"]
        for i, name in enumerate(left_leg_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 5,
                "biped_link": i + 1
            })
        
        # Right Leg (4 links: Thigh, Calf, HorseLink, Foot)
        right_leg_names = ["R Thigh", "R Calf", "R HorseLink", "R Foot"]
        for i, name in enumerate(right_leg_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 6,
                "biped_link": i + 1
            })
        
        # Left Toes (5 toes x 3 links each = 15 links)
        toe_names = ["Toe0", "Toe1", "Toe2", "Toe3", "Toe4"]
        for toe_idx, toe_base in enumerate(toe_names):
            for link_idx in range(3):
                if link_idx == 0:
                    toe_name = f"L {toe_base}"
                else:
                    toe_name = f"L {toe_base}{link_idx}"
                
                mapping["biped_mapping"].append({
                    "bip": toe_name,
                    "fbx": "",
                    "biped_index": 7,
                    "biped_link": toe_idx * 3 + link_idx + 1
                })
        
        # Right Toes (5 toes x 3 links each = 15 links)
        for toe_idx, toe_base in enumerate(toe_names):
            for link_idx in range(3):
                if link_idx == 0:
                    toe_name = f"R {toe_base}"
                else:
                    toe_name = f"R {toe_base}{link_idx}"
                
                mapping["biped_mapping"].append({
                    "bip": toe_name,
                    "fbx": "",
                    "biped_index": 8,
                    "biped_link": toe_idx * 3 + link_idx + 1
                })
        
        # Tail (최대 25개)
        tail_names = ["Tail"] + [f"Tail{i}" for i in range(1, 25)]
        for i, name in enumerate(tail_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 10,
                "biped_link": i + 1
            })
        
        # Ponytail1 (최대 25개)
        ponytail1_names = ["Ponytail1"] + [f"Ponytail1{i}" for i in range(1, 25)]
        for i, name in enumerate(ponytail1_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 18,
                "biped_link": i + 1
            })
        
        # Ponytail2 (최대 25개)
        ponytail2_names = ["Ponytail2"] + [f"Ponytail2{i}" for i in range(1, 25)]
        for i, name in enumerate(ponytail2_names):
            mapping["biped_mapping"].append({
                "bip": name,
                "fbx": "",
                "biped_index": 19,
                "biped_link": i + 1
            })
        
        # Props
        for i in range(1, 4):
            mapping["biped_mapping"].append({
                "bip": f"Prop{i}",
                "fbx": "",
                "biped_index": 19 + i,
                "biped_link": 1
            })
        
        return mapping
    
    def save_mapping(self, in_file_path: str) -> bool:
        """매핑 데이터를 JSON 파일로 저장
        
        Args:
            in_file_path: 저장할 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            file_path = Path(in_file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.mapping_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"매핑 저장 실패: {e}")
            return False
    
    def load_mapping(self, in_file_path: str) -> bool:
        """JSON 파일에서 매핑 데이터 로드
        
        Args:
            in_file_path: 로드할 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            file_path = Path(in_file_path)
            if not file_path.exists():
                print(f"파일이 존재하지 않습니다: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.mapping_data = json.load(f)
            
            return True
        except Exception as e:
            print(f"매핑 로드 실패: {e}")
            return False
    
    def set_fbx_bone_name(self, in_bip_name: str, in_fbx_name: str) -> bool:
        """특정 Biped 본에 FBX 본 이름 설정
        
        Args:
            in_bip_name: Biped 본 이름
            in_fbx_name: 대응하는 FBX 본 이름
            
        Returns:
            성공 여부
        """
        for mapping in self.mapping_data["biped_mapping"]:
            if mapping["bip"] == in_bip_name:
                mapping["fbx"] = in_fbx_name
                return True
        
        print(f"Biped 본을 찾을 수 없습니다: {in_bip_name}")
        return False
    
    def get_fbx_bone_name(self, in_bip_name: str) -> Optional[str]:
        """특정 Biped 본에 대응하는 FBX 본 이름 반환
        
        Args:
            in_bip_name: Biped 본 이름
            
        Returns:
            FBX 본 이름 또는 None
        """
        for mapping in self.mapping_data["biped_mapping"]:
            if mapping["bip"] == in_bip_name:
                return mapping["fbx"] if mapping["fbx"] else None
        
        return None
    
    def get_biped_info(self, in_bip_name: str) -> Optional[Dict[str, Any]]:
        """특정 Biped 본의 정보 반환
        
        Args:
            in_bip_name: Biped 본 이름
            
        Returns:
            Biped 본 정보 딕셔너리 또는 None
        """
        for mapping in self.mapping_data["biped_mapping"]:
            if mapping["bip"] == in_bip_name:
                return mapping.copy()
        
        return None
    
    def get_all_mappings(self) -> List[Dict[str, Any]]:
        """모든 매핑 데이터 반환
        
        Returns:
            매핑 데이터 리스트
        """
        return self.mapping_data["biped_mapping"].copy()
    
    def clear_all_fbx_mappings(self):
        """모든 FBX 매핑을 빈 문자열로 초기화"""
        for mapping in self.mapping_data["biped_mapping"]:
            mapping["fbx"] = ""


class MocapRetargeter:
    """모션 캡처 리타겟팅 클래스"""
    
    def __init__(self):
        self.bone_mapping = BipedBoneMapping()
    
    def analyze_fbx_structure(self, in_fbx_nodes: List[str]) -> Dict[str, Any]:
        """FBX 본 구조 분석
        
        Args:
            in_fbx_nodes: FBX 노드 이름 리스트
            
        Returns:
            분석 결과 딕셔너리
        """
        # TODO: FBX 본 구조 분석 로직 구현
        pass
    
    def create_biped(self, in_height: float = 170.0) -> bool:
        """Biped 생성
        
        Args:
            in_height: Biped 높이
            
        Returns:
            성공 여부
        """
        # TODO: Biped 생성 로직 구현
        pass
    
    def resize_biped(self) -> bool:
        """Biped 크기 조정
        
        Returns:
            성공 여부
        """
        # TODO: Biped 크기 조정 로직 구현
        pass
    
    def retarget_animation(self, in_start_frame: int, in_end_frame: int) -> bool:
        """애니메이션 리타겟팅
        
        Args:
            in_start_frame: 시작 프레임
            in_end_frame: 종료 프레임
            
        Returns:
            성공 여부
        """
        # TODO: 애니메이션 리타겟팅 로직 구현
        pass


# 기본 인스턴스 생성
default_bone_mapping = BipedBoneMapping() 