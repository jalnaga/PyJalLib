"""
템플릿 프로세서 테스트 및 사용 예제
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from pyjallib.ue5.template_processor import TemplateProcessor


def test_template_processing():
    """템플릿 처리 테스트"""
    
    # 테스트용 템플릿 변수
    template_vars = {
        'inExtPackagePath': r'C:\Users\Username\Documents\PyJalLib',
        'inAnimFbxPath': r'D:\Projects\MyGame\Content\Animations\Character\Run.fbx',
        'inSkeletonFbxPath': r'D:\Projects\MyGame\Content\Characters\Character_Skeleton.fbx',
        'inContentRootPrefix': '/Game',
        'inFbxRootPrefix': '/Game/Characters'
    }
    
    # 템플릿 파일 경로
    template_path = project_root / "src" / "pyjallib" / "ue5" / "animImportTemplate.py"
    output_path = project_root / "test_output" / "generated_anim_import_script.py"
    
    print(f"템플릿 파일: {template_path}")
    print(f"출력 파일: {output_path}")
    print(f"템플릿 변수: {template_vars}")
    
    # 템플릿 처리 실행
    success = TemplateProcessor.create_animation_import_script(
        in_template_path=str(template_path),
        in_output_path=str(output_path),
        in_ext_package_path=template_vars['inExtPackagePath'],
        in_anim_fbx_path=template_vars['inAnimFbxPath'],
        in_skeleton_fbx_path=template_vars['inSkeletonFbxPath'],
        in_content_root_prefix=template_vars['inContentRootPrefix'],
        in_fbx_root_prefix=template_vars['inFbxRootPrefix']
    )
    
    if success:
        print("✅ 템플릿 처리 성공!")
        print(f"생성된 파일: {output_path}")
        
        # 생성된 파일 내용 확인
        with open(output_path, 'r', encoding='utf-8') as f:
            generated_content = f.read()
            print("\n생성된 스크립트 내용:")
            print("=" * 50)
            print(generated_content)
            print("=" * 50)
    else:
        print("❌ 템플릿 처리 실패!")


def test_string_template_processing():
    """문자열 템플릿 처리 테스트"""
    
    # 간단한 템플릿 문자열
    template_string = """
    Hello {name}!
    Your age is {age}.
    You live in {city}.
    """
    
    template_vars = {
        'name': 'John',
        'age': 30,
        'city': 'Seoul'
    }
    
    result = TemplateProcessor.process_template_string(template_string, template_vars)
    
    print("문자열 템플릿 처리 결과:")
    print(result)


if __name__ == "__main__":
    print("템플릿 프로세서 테스트 시작")
    print("-" * 30)
    
    test_string_template_processing()
    print("\n" + "-" * 30)
    test_template_processing() 