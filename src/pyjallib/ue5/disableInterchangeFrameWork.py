import json
from pathlib import Path
from .logger import ue5_logger

def add_disabled_plugins_to_uproject(uproject_path):
    """
    특정 플러그인들을 Enabled=false 상태로 추가하여 temp_ 접두사가 붙은 새 파일로 저장
    
    Args:
        uproject_path (str): 원본 .uproject 파일 경로
    """
    
    # 비활성화 상태로 추가할 플러그인들
    plugins_to_add = [
        {
            "Name": "MeshPainting",
            "Enabled": False
        },
        {
            "Name": "InterchangeEditor",
            "Enabled": False,
            "SupportedTargetPlatforms": [
                "Win64",
                "Linux",
                "Mac"
            ]
        },
        {
            "Name": "GLTFExporter",
            "Enabled": False
        },
        {
            "Name": "InterchangeTests",
            "Enabled": False
        },
        {
            "Name": "Interchange",
            "Enabled": False,
            "SupportedTargetPlatforms": [
                "Win64",
                "Linux",
                "Mac"
            ]
        },
        {
            "Name": "InterchangeAssets",
            "Enabled": False
        }
    ]
    
    # 파일 읽기
    with open(uproject_path, 'r', encoding='utf-8') as f:
        project_data = json.load(f)
    
    # 기존 플러그인 이름들 확인
    existing_plugin_names = set()
    if 'Plugins' in project_data:
        existing_plugin_names = {plugin['Name'] for plugin in project_data['Plugins']}
    
    # 새 플러그인 추가 (중복 체크)
    added_count = 0
    for plugin in plugins_to_add:
        if plugin['Name'] not in existing_plugin_names:
            project_data['Plugins'].append(plugin)
            added_count += 1
            ue5_logger.info(f"추가됨 (비활성화): {plugin['Name']}")
        else:
            ue5_logger.info(f"이미 존재: {plugin['Name']}")
    
    # 출력 파일 경로 생성 (temp_ 접두사 추가)
    input_path = Path(uproject_path)
    output_filename = f"temp_{input_path.name}"
    output_path = input_path.parent / output_filename
    
    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent='\t', ensure_ascii=False)
    
    ue5_logger.info(f"총 {added_count}개 플러그인 추가 (비활성화 상태)")
    ue5_logger.info(f"출력 파일: {output_path}")
    
    return output_path
