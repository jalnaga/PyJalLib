"""
UE5 테스트 스크립트 생성기

templateProcessor를 사용하여 Interchange 임포터 테스트용 스크립트를 생성합니다.
이 스크립트는 로컬 환경(UE5 외부)에서 실행합니다.

사용법:
    uv run python temp_scripts/generate_ue5_test_scripts.py
"""

import sys
from pathlib import Path

# PyJalLib 경로 추가
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from pyjallib.ue5.templateProcessor import TemplateProcessor

# === 설정 ===
EXT_PACKAGE_PATH = str(src_path)
CONTENT_ROOT_PREFIX = r'/Game/'
FBX_ROOT_PREFIX = r'E:\DevStorage_root\DevStorage'

# 테스트용 FBX 파일 경로
SKELETON_FBX = r'E:\DevStorage_root\DevStorage\Characters\Shared\Human\Female\Mesh\BaseSkeleton3\Sh_Human_F_BaseSkeleton3.fbx'
SKELETAL_MESH_FBX = r'E:\DevStorage_root\DevStorage\Characters\Shared\Human\Female\Mesh\Default3\Body\SK_Sh_Human_F_Default3_Body.fbx'

# 출력 경로
OUTPUT_DIR = project_root / "temp_scripts"


def main():
    processor = TemplateProcessor()
    processor.set_default_output_directory(str(OUTPUT_DIR))
    
    print("=" * 60)
    print("UE5 테스트 스크립트 생성기")
    print("=" * 60)
    
    # 1. Skeleton Import 스크립트 생성
    print("\n[1] Interchange Skeleton Import 스크립트 생성...")
    skeleton_data = {
        'inExtPackagePath': EXT_PACKAGE_PATH,
        'inSkeletonFbxPath': SKELETON_FBX,
        'inContentRootPrefix': CONTENT_ROOT_PREFIX,
        'inFbxRootPrefix': FBX_ROOT_PREFIX,
    }
    skeleton_output = str(OUTPUT_DIR / "ue5_interchange_skeleton_import.py")
    processor.process_interchange_skeleton_import_template(skeleton_data, skeleton_output)
    print(f"    생성 완료: {skeleton_output}")
    
    # 2. SkeletalMesh Import 스크립트 생성
    print("\n[2] Interchange SkeletalMesh Import 스크립트 생성...")
    skeletal_mesh_data = {
        'inExtPackagePath': EXT_PACKAGE_PATH,
        'inSkeletalMeshFbxPath': SKELETAL_MESH_FBX,
        'inSkeletonFbxPath': SKELETON_FBX,
        'inContentRootPrefix': CONTENT_ROOT_PREFIX,
        'inFbxRootPrefix': FBX_ROOT_PREFIX,
    }
    skeletal_mesh_output = str(OUTPUT_DIR / "ue5_interchange_skeletal_mesh_import.py")
    processor.process_interchange_skeletal_mesh_import_template(skeletal_mesh_data, skeletal_mesh_output)
    print(f"    생성 완료: {skeletal_mesh_output}")
    
    print("\n" + "=" * 60)
    print("스크립트 생성 완료!")
    print("=" * 60)
    print("\nUE5 에디터에서 다음 명령으로 테스트하세요:")
    print(f'\n1. Skeleton 임포트:')
    print(f'   py "{skeleton_output.replace(chr(92), "/")}"')
    print(f'\n2. SkeletalMesh 임포트 (Skeleton 먼저 임포트 필요):')
    print(f'   py "{skeletal_mesh_output.replace(chr(92), "/")}"')


if __name__ == "__main__":
    main()
