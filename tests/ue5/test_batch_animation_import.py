"""
Interchange Batch Animation Import 테스트 스크립트 생성기

이 스크립트는 로컬(언리얼 밖)에서 실행하여 언리얼 에디터용 스크립트를 생성합니다.
TemplateProcessor를 사용하여 템플릿 기반으로 스크립트를 생성합니다.

실행 방법:
1. 터미널에서 실행: uv run python tests/ue5/test_batch_animation_import.py
2. 생성된 파일(test_inUnreal_batch_animation_import.py)을 언리얼 에디터에서 실행
"""

import sys
from pathlib import Path

# =============================================================================
# 설정
# =============================================================================

# PyJalLib 패키지 경로
EXT_PACKAGE_PATH = r"J:\My Drive\Programming\Python\PyJalLib-import-asset-save-fix\src"

# 애니메이션 FBX 파일 경로 리스트
FBX_PATHS = [
    r"E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_RhStop_RBr-Enter.fbx",
    r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Animation\Neutral\System\Equipment\A_Sh_Human_M_Neutral_System_Equipment_WriteBasic_Loop.fbx",
    r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\Battle\Action\Fist\A_Nm_GHDtBully_M_Battle_Action_Fist_MonsterSkill_1.fbx",
]

# UE5 Content 경로 리스트 (FBX 파일별 목적지)
DESTINATION_PATHS = [
    "/Game/Omni/Characters/NPC/Human/Male/Animation/Neutral/Storytelling/Default",
    "/Game/Omni/Characters/Shared/Human/Male/Animation/Neutral/System/Equipment",
    "/Game/Omni/Characters/NormalMonster/GumhoDistrictBully/Male/Animation/Battle/Action/Fist",
]

# 스켈레톤 Content 경로 리스트 (모든 파일에 동일한 스켈레톤 사용)
SKELETON_PATH = "/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3"
SKELETON_PATHS = [SKELETON_PATH] * len(FBX_PATHS)

# 출력 파일 경로
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "test_inUnreal_batch_animation_import.py"

# =============================================================================
# 패키지 경로 추가
# =============================================================================

if EXT_PACKAGE_PATH not in sys.path:
    sys.path.insert(0, EXT_PACKAGE_PATH)

# =============================================================================
# 언리얼 에디터용 스크립트 생성 (TemplateProcessor 사용)
# =============================================================================


def generate_unreal_script():
    """TemplateProcessor를 사용하여 언리얼 에디터용 배치 임포트 스크립트를 생성합니다."""
    from pyjallib.ue5.templateProcessor import TemplateProcessor

    print("=" * 60)
    print("[스크립트 생성기] 시작 (TemplateProcessor 사용)")
    print("=" * 60)

    # 에셋 이름 (FBX 파일명 사용)
    asset_names = [Path(fbx).stem for fbx in FBX_PATHS]

    print(f"[INFO] FBX 파일 ({len(FBX_PATHS)}개):")
    for i, fbx in enumerate(FBX_PATHS):
        print(f"  [{i + 1}] {fbx}")
    print("-" * 60)
    print(f"[INFO] 목적지 경로 ({len(DESTINATION_PATHS)}개):")
    for i, dest in enumerate(DESTINATION_PATHS):
        print(f"  [{i + 1}] {dest}")
    print("-" * 60)
    print(f"[INFO] 스켈레톤 경로: {SKELETON_PATH}")
    print("-" * 60)
    print(f"[INFO] 에셋 이름 ({len(asset_names)}개):")
    for i, name in enumerate(asset_names):
        print(f"  [{i + 1}] {name}")
    print("-" * 60)

    # TemplateProcessor로 스크립트 생성
    processor = TemplateProcessor()

    # 템플릿 데이터 - 리스트를 Python 리스트 문자열로 변환
    template_data = {
        "inExtPackagePath": EXT_PACKAGE_PATH,
        "inFbxPaths": repr(FBX_PATHS),
        "inDestinationPaths": repr(DESTINATION_PATHS),
        "inSkeletonPaths": repr(SKELETON_PATHS),
        "inAssetNames": repr(asset_names),
    }

    print("[INFO] 템플릿 데이터 생성 완료")
    print("-" * 60)

    # 배치 애니메이션 임포트 템플릿 처리
    result = processor.process_interchange_batch_anim_import_template(
        inTemplateData=template_data, inOutputPath=str(OUTPUT_FILE)
    )

    print("=" * 60)
    print("[SUCCESS] 언리얼용 스크립트 생성 완료!")
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
