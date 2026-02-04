#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Task 4: 재임포트 시 스켈레톤 변경 동작 검증 테스트

테스트 목적:
- 기존 스켈레톤 X로 임포트된 애니메이션을 스켈레톤 Y로 재임포트
- 재임포트 후 스켈레톤이 Y로 변경되었는지 확인

실행 환경: Unreal Engine 5 Editor (Python Console)
"""

import unreal
import logging
import sys
from pathlib import Path

# legacyAnimationImporter 모듈 경로 추가
PYJALLIB_INUNREAL_PATH = Path(__file__).parent.parent.parent / "src" / "pyjallib" / "ue5" / "inUnreal"
if str(PYJALLIB_INUNREAL_PATH) not in sys.path:
    sys.path.insert(0, str(PYJALLIB_INUNREAL_PATH))

# ============================================================
# 사용자 설정 영역 - 테스트 전 아래 값들을 수정하세요
# ============================================================

# 테스트에 사용할 FBX 파일 경로 (절대 경로)
TEST_FBX_FILE = r"E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_Cry_RBr-Enter.fbx"

# 스켈레톤 X: 초기 임포트에 사용할 스켈레톤의 Content 경로
SKELETON_X_PATH = "/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton/SKEL_Sh_Human_M_BaseSkeleton.SKEL_Sh_Human_M_BaseSkeleton"

# 스켈레톤 Y: 재임포트에 사용할 스켈레톤의 Content 경로
SKELETON_Y_PATH = "/Game/Omni/Characters/Shared/Human/Female/Mesh/BaseSkeleton/SKEL_Sh_Human_F_BaseSkeleton.SKEL_Sh_Human_F_BaseSkeleton"

# LegacyAnimationImporter 설정
CONTENT_ROOT_PREFIX = r"D:\root\Omni\Content\Omni"
FBX_ROOT_PREFIX = r"E:\DevStorage_root\DevStorage"

# 테스트 모드 설정
# True: 기존 에셋이 있으면 초기 임포트 건너뛰고 재임포트만 테스트
# False: 항상 에셋 삭제 후 전체 테스트 수행
SKIP_INITIAL_IMPORT_IF_EXISTS = True

# ============================================================
# 테스트 로직 - 아래는 수정하지 마세요
# ============================================================

# 로그 설정
LOG_FILE = Path(__file__).parent.parent / "logs" / "test_ue5_skeleton_reimport.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8',
    force=True
)
logger = logging.getLogger(__name__)


def validate_config():
    """설정값 검증"""
    errors = []

    if not Path(TEST_FBX_FILE).exists():
        errors.append(f"FBX 파일이 존재하지 않음: {TEST_FBX_FILE}")

    skeleton_x_data = unreal.EditorAssetLibrary.find_asset_data(SKELETON_X_PATH)
    if not skeleton_x_data.is_valid():
        errors.append(f"스켈레톤 X를 찾을 수 없음: {SKELETON_X_PATH}")

    skeleton_y_data = unreal.EditorAssetLibrary.find_asset_data(SKELETON_Y_PATH)
    if not skeleton_y_data.is_valid():
        errors.append(f"스켈레톤 Y를 찾을 수 없음: {SKELETON_Y_PATH}")

    if SKELETON_X_PATH == SKELETON_Y_PATH:
        errors.append("스켈레톤 X와 Y가 동일함 - 서로 다른 스켈레톤을 지정해야 합니다")

    return errors


def get_animation_skeleton(asset_path: str):
    """애니메이션 에셋의 현재 스켈레톤 반환"""
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        return None
    if not isinstance(asset, unreal.AnimSequence):
        return None
    skeleton = asset.get_editor_property('skeleton')
    return skeleton


def build_asset_path_from_result(result: dict) -> str:
    """import_animation 결과에서 에셋 전체 경로 생성"""
    return f"{result['Path']}/{result['Name']}"


def run_test():
    """
    Task 4 테스트 실행

    테스트 시나리오:
    1. 스켈레톤 X로 애니메이션 초기 임포트 (또는 기존 에셋 사용)
    2. 스켈레톤 Y로 동일 애니메이션 재임포트
    3. 재임포트 후 스켈레톤이 Y로 변경되었는지 검증
    """
    logger.info("=" * 60)
    logger.info("=== TEST START: Task 4 - 재임포트 시 스켈레톤 변경 검증 ===")
    logger.info("=" * 60)

    # Step 0: 설정값 검증
    logger.info("[Step 0] 설정값 검증 시작")
    unreal.log("[Test] Step 0: 설정값 검증 시작...")
    config_errors = validate_config()
    if config_errors:
        for error in config_errors:
            logger.error(f"CONFIG ERROR: {error}")
            unreal.log_error(f"[Test] CONFIG ERROR: {error}")
        logger.info("=== TEST END: FAIL (설정 오류) ===")
        unreal.log_error("[Test] 설정 오류로 테스트 중단. 로그 파일을 확인하세요.")
        return False
    logger.info("[Step 0] SUCCESS: 설정값 검증 통과")
    unreal.log("[Test] Step 0: SUCCESS - 설정값 검증 통과")

    try:
        # LegacyAnimationImporter import
        from legacyAnimationImporter import LegacyAnimationImporter

        importer = LegacyAnimationImporter(CONTENT_ROOT_PREFIX, FBX_ROOT_PREFIX)

        # 예상 에셋 경로 계산 (LegacyBaseImporter와 동일한 로직)
        expected_asset_path = importer.convert_fbx_path_to_content_path(TEST_FBX_FILE)
        if expected_asset_path.endswith('.uasset'):
            expected_asset_path = expected_asset_path[:-7]  # .uasset 제거

        logger.info(f"예상 에셋 경로: {expected_asset_path}")
        unreal.log(f"[Test] 예상 에셋 경로: {expected_asset_path}")

        # 기존 에셋 존재 여부 확인
        existing_asset = unreal.EditorAssetLibrary.load_asset(expected_asset_path)
        asset_exists = existing_asset is not None and isinstance(existing_asset, unreal.AnimSequence)

        skeleton_x_asset = unreal.EditorAssetLibrary.find_asset_data(SKELETON_X_PATH).get_asset()
        skeleton_y_asset = unreal.EditorAssetLibrary.find_asset_data(SKELETON_Y_PATH).get_asset()

        # Step 1: 초기 임포트 또는 기존 에셋 사용
        if asset_exists and SKIP_INITIAL_IMPORT_IF_EXISTS:
            logger.info(f"[Step 1] 기존 에셋 발견 - 초기 임포트 건너뜀")
            unreal.log("[Test] Step 1: 기존 에셋 발견 - 초기 임포트 건너뜀")

            current_skeleton = existing_asset.get_editor_property('skeleton')
            logger.info(f"  - 기존 에셋: {expected_asset_path}")
            logger.info(f"  - 현재 스켈레톤: {current_skeleton.get_name() if current_skeleton else 'None'}")

            # 현재 스켈레톤이 Y가 아닌지 확인 (Y라면 테스트 의미 없음)
            if current_skeleton == skeleton_y_asset:
                logger.warning("  - 주의: 현재 스켈레톤이 이미 Y입니다. 테스트 의미가 약해질 수 있습니다.")
                unreal.log_warning("[Test] 주의: 현재 스켈레톤이 이미 Y입니다.")

            skeleton_after_first = current_skeleton
            asset_full_path = expected_asset_path
        else:
            logger.info(f"[Step 1] 스켈레톤 X로 초기 임포트 시작")
            unreal.log("[Test] Step 1: 스켈레톤 X로 초기 임포트 시작...")
            logger.info(f"  - FBX: {TEST_FBX_FILE}")
            logger.info(f"  - 스켈레톤 X: {SKELETON_X_PATH}")

            # 기존 에셋이 있으면 삭제 (깨끗한 테스트 환경)
            if asset_exists:
                logger.info(f"  - 기존 에셋 삭제: {expected_asset_path}")
                unreal.EditorAssetLibrary.delete_asset(expected_asset_path)

            result1 = importer.import_animation(
                inFbxFile=TEST_FBX_FILE,
                inSkeletonContentPath=SKELETON_X_PATH
            )

            if not result1.get('Success', False):
                logger.error(f"FAIL: 초기 임포트 실패")
                logger.info("=== TEST END: FAIL ===")
                unreal.log_error("[Test] FAIL: 초기 임포트 실패")
                return False

            asset_full_path = build_asset_path_from_result(result1)
            logger.info(f"  - 임포트 결과 경로: {asset_full_path}")

            # 초기 임포트 후 스켈레톤 확인
            skeleton_after_first = get_animation_skeleton(asset_full_path)
            if skeleton_after_first is None:
                logger.error(f"FAIL: 초기 임포트 후 애니메이션 에셋을 찾을 수 없음")
                logger.info("=== TEST END: FAIL ===")
                unreal.log_error("[Test] FAIL: 초기 임포트 후 애니메이션 에셋을 찾을 수 없음")
                return False

            if skeleton_after_first != skeleton_x_asset:
                logger.error(f"FAIL: 초기 임포트 후 스켈레톤이 X가 아님")
                logger.error(f"  - 예상: {skeleton_x_asset.get_name()}")
                logger.error(f"  - 실제: {skeleton_after_first.get_name()}")
                logger.info("=== TEST END: FAIL ===")
                unreal.log_error("[Test] FAIL: 초기 임포트 후 스켈레톤이 X가 아님")
                return False

            logger.info(f"[Step 1] SUCCESS: 스켈레톤 X로 초기 임포트 완료")
            logger.info(f"  - 현재 스켈레톤: {skeleton_after_first.get_name()}")
            unreal.log(f"[Test] Step 1: SUCCESS - 스켈레톤 {skeleton_after_first.get_name()}로 임포트 완료")

        # Step 2: 스켈레톤 Y로 재임포트
        logger.info(f"[Step 2] 스켈레톤 Y로 재임포트 시작")
        logger.info(f"  - 스켈레톤 Y: {SKELETON_Y_PATH}")
        unreal.log("[Test] Step 2: 스켈레톤 Y로 재임포트 시작...")

        result2 = importer.import_animation(
            inFbxFile=TEST_FBX_FILE,
            inSkeletonContentPath=SKELETON_Y_PATH
        )

        if not result2.get('Success', False):
            logger.error(f"FAIL: 재임포트 실패")
            logger.info("=== TEST END: FAIL ===")
            unreal.log_error("[Test] FAIL: 재임포트 실패")
            return False

        logger.info(f"[Step 2] SUCCESS: 재임포트 완료")
        unreal.log("[Test] Step 2: SUCCESS - 재임포트 완료")

        # Step 3: 재임포트 후 스켈레톤 검증
        logger.info(f"[Step 3] 재임포트 후 스켈레톤 검증")
        unreal.log("[Test] Step 3: 재임포트 후 스켈레톤 검증...")

        # 에셋 다시 로드 (캐시 방지)
        reimported_asset = unreal.EditorAssetLibrary.load_asset(asset_full_path)
        if reimported_asset:
            unreal.EditorAssetLibrary.save_loaded_asset(reimported_asset)
        skeleton_after_reimport = get_animation_skeleton(asset_full_path)

        if skeleton_after_reimport is None:
            logger.error(f"FAIL: 재임포트 후 애니메이션 에셋을 찾을 수 없음")
            logger.info("=== TEST END: FAIL ===")
            unreal.log_error("[Test] FAIL: 재임포트 후 애니메이션 에셋을 찾을 수 없음")
            return False

        before_name = skeleton_after_first.get_name() if skeleton_after_first else 'None'
        after_name = skeleton_after_reimport.get_name() if skeleton_after_reimport else 'None'
        expected_name = skeleton_y_asset.get_name() if skeleton_y_asset else 'None'

        logger.info(f"  - 재임포트 전 스켈레톤: {before_name}")
        logger.info(f"  - 재임포트 후 스켈레톤: {after_name}")
        logger.info(f"  - 기대 스켈레톤 (Y): {expected_name}")

        if skeleton_after_reimport == skeleton_y_asset:
            logger.info(f"[Step 3] SUCCESS: 스켈레톤이 Y로 정상 변경됨")
            logger.info("=" * 60)
            logger.info("=== TEST END: SUCCESS ===")
            logger.info("=" * 60)
            unreal.log(f"[Test] SUCCESS: Task 4 테스트 통과! ({before_name} -> {after_name})")
            return True
        else:
            logger.error(f"FAIL: 스켈레톤이 Y로 변경되지 않음")
            logger.error(f"  - 예상: {expected_name}")
            logger.error(f"  - 실제: {after_name}")
            logger.info("=" * 60)
            logger.info("=== TEST END: FAIL ===")
            logger.info("=" * 60)
            unreal.log_error(f"[Test] FAIL: 스켈레톤이 {expected_name}로 변경되지 않음 (실제: {after_name})")
            return False

    except Exception as e:
        logger.error(f"ERROR: 예외 발생 - {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("=== TEST END: ERROR ===")
        unreal.log_error(f"[Test] ERROR: {e}")
        return False


# 스크립트 실행
if __name__ == "__main__":
    run_test()
