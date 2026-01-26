"""
Interchange Skeleton Import 테스트 스크립트 생성기

이 스크립트는 로컬(언리얼 밖)에서 실행하여 언리얼 에디터용 스크립트를 생성합니다.
TemplateProcessor를 사용하여 템플릿 기반으로 스크립트를 생성합니다.

실행 방법:
1. 터미널에서 실행: uv run python temp_scripts/test_skeleton_import.py
2. 생성된 파일(test_inUnreal_skeleton_import.py)을 언리얼 에디터에서 실행
"""

import sys
from pathlib import Path

# =============================================================================
# 설정
# =============================================================================

# PyJalLib 패키지 경로
EXT_PACKAGE_PATH = r"J:\My Drive\Programming\Python\PyJalLib-interchange-debug\src"

# FBX 파일 경로
FBX_PATH = r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx"

# NameToPath Config 파일 경로
NAMING_CONFIG_PATH = r"E:\DevStorage_root\DevStorage\Tools\CharNamingConfigFiles\CharModelerNamingConfig.json"
PATH_CONFIG_PATH = r"E:\DevStorage_root\DevStorage\Tools\CharNamingConfigFiles\CharModelerPathConfig.json"

# Windows 경로 → UE5 Content 경로 변환 규칙
WINDOWS_ROOT = r"E:\DevStorage_root\DevStorage\Characters"
UE5_ROOT = "/Game/Omni/Characters"

# 출력 파일 경로
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "test_inUnreal_skeleton_import.py"

# =============================================================================
# 패키지 경로 추가
# =============================================================================

if EXT_PACKAGE_PATH not in sys.path:
    sys.path.insert(0, EXT_PACKAGE_PATH)

# =============================================================================
# 경로 생성 (NameToPath 사용)
# =============================================================================

from pyjallib.nameToPath import NameToPath

def generate_ue5_destination_path(fbx_path: str) -> str:
    """
    FBX 파일 경로에서 UE5 Content 목적지 경로를 생성합니다.
    
    Args:
        fbx_path: FBX 파일의 절대 경로
        
    Returns:
        /Game/... 형식의 UE5 Content 경로
    """
    # FBX 파일명 추출
    skeleton_name = Path(fbx_path).stem
    print(f"[DEBUG] FBX 파일명: {skeleton_name}")
    
    # NameToPath로 상대 경로 생성 (rootPath 없이)
    name_to_path = NameToPath(NAMING_CONFIG_PATH, PATH_CONFIG_PATH)
    relative_path = name_to_path.generate_path(skeleton_name, inIncludeRealName=True)
    print(f"[DEBUG] 상대 경로: {relative_path}")
    
    # 상대 경로를 UE5 Content 경로로 변환 (백슬래시 → 슬래시)
    relative_path_unix = relative_path.replace("\\", "/")
    
    # /Game/Omni/Characters/ prefix 추가
    ue5_path = f"{UE5_ROOT}/{relative_path_unix}"
    print(f"[DEBUG] UE5 Content 경로: {ue5_path}")
    
    return ue5_path

# =============================================================================
# 언리얼 에디터용 스크립트 생성 (TemplateProcessor 사용)
# =============================================================================

def generate_unreal_script():
    """TemplateProcessor를 사용하여 언리얼 에디터용 스크립트를 생성합니다."""
    from pyjallib.ue5.templateProcessor import TemplateProcessor
    
    print("=" * 60)
    print("[스크립트 생성기] 시작 (TemplateProcessor 사용)")
    print("=" * 60)
    
    # UE5 목적지 경로 생성
    destination_path = generate_ue5_destination_path(FBX_PATH)
    
    # 에셋 이름 (FBX 파일명 사용)
    asset_name = Path(FBX_PATH).stem
    
    print(f"[INFO] FBX 파일: {FBX_PATH}")
    print(f"[INFO] 목적지 경로: {destination_path}")
    print(f"[INFO] 에셋 이름: {asset_name}")
    print("-" * 60)
    
    # TemplateProcessor로 스크립트 생성
    processor = TemplateProcessor()
    
    template_data = {
        'inExtPackagePath': EXT_PACKAGE_PATH,
        'inFbxPath': FBX_PATH,
        'inDestinationPath': destination_path,
        'inAssetName': asset_name
    }
    
    print(f"[INFO] 템플릿 데이터: {template_data}")
    print("-" * 60)
    
    # 스켈레톤 임포트 템플릿 처리
    result = processor.process_interchange_skeleton_import_template(
        inTemplateData=template_data,
        inOutputPath=str(OUTPUT_FILE)
    )
    
    print("=" * 60)
    print(f"[SUCCESS] 언리얼용 스크립트 생성 완료!")
    print(f"  - 출력 파일: {OUTPUT_FILE}")
    print("=" * 60)
    print()
    print("다음 단계:")
    print("1. 언리얼 에디터를 실행합니다.")
    print("2. Output Log 창을 엽니다. (Window > Developer Tools > Output Log)")
    print("3. 아래 명령어로 생성된 스크립트를 실행합니다:")
    print()
    print(f'   exec(open(r"{OUTPUT_FILE}").read())')
    print()
    
    return result

# =============================================================================
# 메인 실행
# =============================================================================

if __name__ == "__main__":
    generate_unreal_script()
