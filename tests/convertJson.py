import sys
import os
import json
import glob
from pathlib import Path

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

resourcePath = r"E:\DevStorage_root\DevStorage\Characters"

import pyjallib
pyjallib.reload_modules()

def analyze_and_fix_json_files(in_resource_path):
    """
    resourcePath와 모든 하위 폴더에서 JSON 파일을 찾아 baseSkeleton 값을 분석하고 수정합니다.
    
    Args:
        in_resource_path (str): 분석할 리소스 경로
    """
    print(f"리소스 경로에서 JSON 파일 분석 시작: {in_resource_path}")
    
    # 모든 JSON 파일 찾기
    json_pattern = os.path.join(in_resource_path, "**", "*.json")
    json_files = glob.glob(json_pattern, recursive=True)
    
    print(f"발견된 JSON 파일 수: {len(json_files)}")
    
    processed_count = 0
    modified_count = 0
    
    for json_file_path in json_files:
        file_name = os.path.basename(json_file_path)
        
        # A_로 시작하는 파일만 처리
        if not file_name.startswith("A_"):
            continue
            
        processed_count += 1
        print(f"\n처리 중: {file_name}")
        
        try:
            # JSON 파일 읽기
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # baseSkeleton 키가 있는지 확인
            if "baseSkeleton" not in data:
                print(f"  - baseSkeleton 키가 없음, 건너뜀")
                continue
            
            base_skeleton_value = data["baseSkeleton"]
            print(f"  - 현재 baseSkeleton 값: {base_skeleton_value}")
            
            # 경로명인지 확인 (슬래시나 백슬래시가 포함되어 있는지)
            if not isinstance(base_skeleton_value, str) or ('/' not in base_skeleton_value and '\\' not in base_skeleton_value):
                print(f"  - 경로명이 아님, 건너뜀")
                continue
            
            # 경로에서 파일명 제외한 부분 추출
            path_obj = Path(base_skeleton_value)
            directory_part = str(path_obj.parent)
            file_name_part = path_obj.name
            
            print(f"  - 디렉토리 부분: {directory_part}")
            print(f"  - 파일명 부분: {file_name_part}")
            
            # 파일명이 .max로 끝나고 _BaseSkeleton으로 끝나는지 확인
            if not file_name_part.endswith('.max') or not file_name_part.endswith('_BaseSkeleton.max'):
                print(f"  - .max 파일이 아니거나 _BaseSkeleton으로 끝나지 않음, 건너뜀")
                continue
            
            # 디렉토리 부분이 Mesh로 끝나는지 확인
            if not directory_part.endswith("Mesh"):
                print(f"  - Mesh로 끝나지 않음, 건너뜀")
                continue
            
            # 새로운 경로 생성: Mesh 뒤에 BaseSkeleton 하위 폴더 추가
            new_directory = os.path.join(directory_part, "BaseSkeleton")
            new_path = os.path.join(new_directory, file_name_part)
            
            # Windows 경로 형식으로 변환 (백슬래시 사용)
            new_path = new_path.replace('/', '\\')
            
            print(f"  - 수정된 baseSkeleton 값: {new_path}")
            
            # 데이터 업데이트
            data["baseSkeleton"] = new_path
            
            # 파일에 다시 쓰기
            with open(json_file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            
            modified_count += 1
            print(f"  - 파일 수정 완료")
            
        except Exception as e:
            print(f"  - 오류 발생: {str(e)}")
            continue
    
    print(f"\n=== 처리 완료 ===")
    print(f"처리된 파일 수: {processed_count}")
    print(f"수정된 파일 수: {modified_count}")

if __name__ == "__main__":
    # JSON 파일 분석 및 수정 실행
    analyze_and_fix_json_files(resourcePath)
