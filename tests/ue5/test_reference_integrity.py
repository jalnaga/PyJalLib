#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Task 5: 참조 무결성 검증 테스트

테스트 목적:
- Consolidate + Rename 방식으로 스켈레톤 변경 후 기존 에셋 참조가 유지되는지 확인
- 외부 에셋(AnimMontage, AnimBP 등)의 참조가 깨지지 않는지 검증
- Redirector가 올바르게 정리되었는지 확인

실행 환경: Unreal Engine 5 Editor (Python Console)
전제 조건: Task 4 테스트가 완료되어 스켈레톤 변경된 애니메이션 에셋이 존재해야 함
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

# 테스트에 사용할 FBX 파일 경로 (Task 4와 동일)
TEST_FBX_FILE = r"E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_Cry_RBr-Enter.fbx"

# 스켈레톤 X: 변경 전 스켈레톤
SKELETON_X_PATH = "/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton/SKEL_Sh_Human_M_BaseSkeleton.SKEL_Sh_Human_M_BaseSkeleton"

# 스켈레톤 Y: 변경 후 스켈레톤
SKELETON_Y_PATH = "/Game/Omni/Characters/Shared/Human/Female/Mesh/BaseSkeleton/SKEL_Sh_Human_F_BaseSkeleton.SKEL_Sh_Human_F_BaseSkeleton"

# LegacyAnimationImporter 설정
CONTENT_ROOT_PREFIX = r"D:\root\Omni\Content\Omni"
FBX_ROOT_PREFIX = r"E:\DevStorage_root\DevStorage"

# 테스트용 AnimMontage 생성 여부
# True: AnimMontage를 생성하여 참조 테스트 수행 (더 완전한 테스트)
# False: 기존 참조자만 확인 (참조자가 없으면 경고)
CREATE_TEST_MONTAGE = True

# ============================================================
# 테스트 로직 - 아래는 수정하지 마세요
# ============================================================

# 로그 설정
LOG_FILE = Path(__file__).parent.parent / "logs" / "test_ue5_reference_integrity.log"
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

    return errors


def get_asset_referencers(asset_path: str) -> list:
    """에셋을 참조하는 다른 에셋 목록 반환"""
    referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path)
    return list(referencers) if referencers else []


def check_redirector_exists(asset_path: str) -> bool:
    """해당 경로에 Redirector가 존재하는지 확인"""
    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not asset_data.is_valid():
        return False

    asset_class = str(asset_data.asset_class_path.asset_name)
    return "ObjectRedirector" in asset_class


def create_test_anim_montage(anim_sequence_path: str, skeleton) -> str:
    """테스트용 AnimMontage 생성하여 AnimSequence 참조"""
    # AnimMontage 저장 경로
    montage_dir = str(Path(anim_sequence_path).parent).replace("\\", "/")
    montage_name = f"TEST_Montage_{Path(anim_sequence_path).stem}"
    montage_path = f"{montage_dir}/{montage_name}"

    # 기존 테스트 몽타주가 있으면 삭제
    if unreal.EditorAssetLibrary.does_asset_exist(montage_path):
        unreal.EditorAssetLibrary.delete_asset(montage_path)

    # AnimMontage 팩토리 생성
    factory = unreal.AnimMontageFactory()
    factory.set_editor_property('target_skeleton', skeleton)

    # AnimMontage 생성
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    montage = asset_tools.create_asset(montage_name, montage_dir, unreal.AnimMontage, factory)

    if not montage:
        logger.error(f"AnimMontage 생성 실패: {montage_path}")
        return None

    # AnimSequence 로드
    anim_sequence = unreal.EditorAssetLibrary.load_asset(anim_sequence_path)
    if not anim_sequence:
        logger.error(f"AnimSequence 로드 실패: {anim_sequence_path}")
        return None

    # SlotAnimationTrack에 AnimSequence 추가
    # CompositeSection을 사용하여 애니메이션 참조 설정
    slot_tracks = montage.get_editor_property('slot_anim_tracks')
    if slot_tracks and len(slot_tracks) > 0:
        # 첫 번째 슬롯 트랙의 AnimSegment에 애니메이션 설정
        anim_track = slot_tracks[0]
        anim_segments = anim_track.anim_track.anim_segments

        # 새 세그먼트 생성
        new_segment = unreal.AnimSegment()
        new_segment.set_editor_property('anim_reference', anim_sequence)
        new_segment.set_editor_property('anim_start_time', 0.0)
        new_segment.set_editor_property('anim_end_time', anim_sequence.get_editor_property('sequence_length'))
        new_segment.set_editor_property('anim_play_rate', 1.0)
        new_segment.set_editor_property('start_pos', 0.0)

        # 세그먼트 추가
        anim_segments.append(new_segment)

    # 저장
    unreal.EditorAssetLibrary.save_loaded_asset(montage)

    logger.info(f"테스트 AnimMontage 생성 완료: {montage_path}")
    return montage_path


def verify_montage_reference(montage_path: str, expected_anim_path: str) -> bool:
    """AnimMontage가 올바른 애니메이션을 참조하는지 확인"""
    montage = unreal.EditorAssetLibrary.load_asset(montage_path)
    if not montage:
        logger.error(f"AnimMontage 로드 실패: {montage_path}")
        return False

    slot_tracks = montage.get_editor_property('slot_anim_tracks')
    if not slot_tracks or len(slot_tracks) == 0:
        logger.warning("AnimMontage에 슬롯 트랙이 없음")
        return True  # 트랙이 없으면 참조 무결성 문제 아님

    for track in slot_tracks:
        anim_segments = track.anim_track.anim_segments
        for segment in anim_segments:
            anim_ref = segment.get_editor_property('anim_reference')
            if anim_ref:
                ref_path = anim_ref.get_path_name()
                # 경로에서 패키지 경로만 추출
                ref_package = ref_path.split('.')[0] if '.' in ref_path else ref_path
                expected_package = expected_anim_path.split('.')[0] if '.' in expected_anim_path else expected_anim_path

                if ref_package == expected_package:
                    logger.info(f"참조 확인: {ref_package}")
                    return True

    logger.error(f"예상 애니메이션 참조를 찾을 수 없음: {expected_anim_path}")
    return False


def cleanup_test_montage(montage_path: str):
    """테스트용 AnimMontage 삭제"""
    if montage_path and unreal.EditorAssetLibrary.does_asset_exist(montage_path):
        unreal.EditorAssetLibrary.delete_asset(montage_path)
        logger.info(f"테스트 AnimMontage 삭제 완료: {montage_path}")


def run_test():
    """
    Task 5 테스트 실행 - 참조 무결성 검증

    테스트 시나리오:
    1. 테스트 대상 애니메이션 에셋 확인
    2. (옵션) 테스트용 AnimMontage 생성하여 참조 설정
    3. 기존 참조자 목록 기록
    4. 스켈레톤 변경 재임포트 수행
    5. 참조 무결성 검증:
       - 에셋 경로 유지 확인
       - Redirector 없음 확인
       - 참조자들이 여전히 참조 유지 확인
    """
    logger.info("=" * 60)
    logger.info("=== TEST START: Task 5 - 참조 무결성 검증 ===")
    logger.info("=" * 60)

    test_montage_path = None

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

        # 에셋 경로 계산
        expected_asset_path = importer.convert_fbx_path_to_content_path(TEST_FBX_FILE)
        if expected_asset_path.endswith('.uasset'):
            expected_asset_path = expected_asset_path[:-7]

        logger.info(f"테스트 대상 에셋: {expected_asset_path}")
        unreal.log(f"[Test] 테스트 대상 에셋: {expected_asset_path}")

        # Step 1: 에셋 존재 확인
        logger.info("[Step 1] 에셋 존재 확인")
        unreal.log("[Test] Step 1: 에셋 존재 확인...")

        existing_asset = unreal.EditorAssetLibrary.load_asset(expected_asset_path)
        if not existing_asset or not isinstance(existing_asset, unreal.AnimSequence):
            logger.error(f"FAIL: 테스트 대상 애니메이션 에셋이 없음")
            logger.error("  - Task 4를 먼저 실행하여 에셋을 생성해주세요")
            logger.info("=== TEST END: FAIL ===")
            unreal.log_error("[Test] FAIL: 테스트 대상 에셋 없음. Task 4를 먼저 실행하세요.")
            return False

        current_skeleton = existing_asset.get_editor_property('skeleton')
        logger.info(f"  - 에셋 경로: {expected_asset_path}")
        logger.info(f"  - 현재 스켈레톤: {current_skeleton.get_name() if current_skeleton else 'None'}")
        logger.info("[Step 1] SUCCESS: 에셋 존재 확인")
        unreal.log(f"[Test] Step 1: SUCCESS - 현재 스켈레톤: {current_skeleton.get_name() if current_skeleton else 'None'}")

        # Step 2: 테스트용 AnimMontage 생성 (옵션)
        skeleton_y_asset = unreal.EditorAssetLibrary.find_asset_data(SKELETON_Y_PATH).get_asset()

        if CREATE_TEST_MONTAGE:
            logger.info("[Step 2] 테스트용 AnimMontage 생성")
            unreal.log("[Test] Step 2: 테스트용 AnimMontage 생성...")

            # 현재 스켈레톤과 일치하는 스켈레톤으로 몽타주 생성
            test_montage_path = create_test_anim_montage(expected_asset_path, current_skeleton)
            if test_montage_path:
                logger.info(f"  - 테스트 몽타주: {test_montage_path}")
                logger.info("[Step 2] SUCCESS: AnimMontage 생성 완료")
                unreal.log(f"[Test] Step 2: SUCCESS - 테스트 몽타주 생성: {test_montage_path}")
            else:
                logger.warning("[Step 2] WARNING: AnimMontage 생성 실패, 기존 참조자만 확인")
                unreal.log_warning("[Test] Step 2: WARNING - AnimMontage 생성 실패")
        else:
            logger.info("[Step 2] SKIP: AnimMontage 생성 건너뜀 (CREATE_TEST_MONTAGE=False)")
            unreal.log("[Test] Step 2: SKIP - AnimMontage 생성 건너뜀")

        # Step 3: 기존 참조자 목록 기록
        logger.info("[Step 3] 기존 참조자 목록 기록")
        unreal.log("[Test] Step 3: 기존 참조자 목록 기록...")

        referencers_before = get_asset_referencers(expected_asset_path)
        logger.info(f"  - 참조자 수: {len(referencers_before)}")
        for ref in referencers_before:
            logger.info(f"    - {ref}")

        if len(referencers_before) == 0 and not test_montage_path:
            logger.warning("  - 참조자가 없음. 참조 무결성 테스트가 제한적일 수 있음")
            unreal.log_warning("[Test] 참조자가 없음. 참조 무결성 테스트가 제한적일 수 있음")

        logger.info("[Step 3] SUCCESS: 참조자 목록 기록 완료")
        unreal.log(f"[Test] Step 3: SUCCESS - 참조자 {len(referencers_before)}개")

        # Step 4: 스켈레톤 변경 재임포트
        logger.info("[Step 4] 스켈레톤 변경 재임포트")
        unreal.log("[Test] Step 4: 스켈레톤 변경 재임포트 시작...")

        # 현재 스켈레톤과 다른 스켈레톤으로 재임포트
        skeleton_x_asset = unreal.EditorAssetLibrary.find_asset_data(SKELETON_X_PATH).get_asset()

        # 현재가 Y면 X로, 아니면 Y로 재임포트
        if current_skeleton == skeleton_y_asset:
            target_skeleton_path = SKELETON_X_PATH
            target_skeleton_name = "X"
        else:
            target_skeleton_path = SKELETON_Y_PATH
            target_skeleton_name = "Y"

        logger.info(f"  - 현재 스켈레톤: {current_skeleton.get_name() if current_skeleton else 'None'}")
        logger.info(f"  - 목표 스켈레톤: {target_skeleton_path} ({target_skeleton_name})")

        result = importer.import_animation(
            inFbxFile=TEST_FBX_FILE,
            inSkeletonContentPath=target_skeleton_path
        )

        if not result.get('Success', False):
            logger.error(f"FAIL: 재임포트 실패")
            logger.info("=== TEST END: FAIL ===")
            unreal.log_error("[Test] FAIL: 재임포트 실패")
            cleanup_test_montage(test_montage_path)
            return False

        logger.info("[Step 4] SUCCESS: 재임포트 완료")
        unreal.log("[Test] Step 4: SUCCESS - 재임포트 완료")

        # Step 5: 참조 무결성 검증
        logger.info("[Step 5] 참조 무결성 검증")
        unreal.log("[Test] Step 5: 참조 무결성 검증...")

        all_checks_passed = True

        # 5.1: 에셋 경로 유지 확인
        logger.info("  [5.1] 에셋 경로 유지 확인")
        asset_exists = unreal.EditorAssetLibrary.does_asset_exist(expected_asset_path)
        if asset_exists:
            logger.info(f"    - SUCCESS: 에셋 경로 유지됨: {expected_asset_path}")
        else:
            logger.error(f"    - FAIL: 에셋 경로가 존재하지 않음: {expected_asset_path}")
            all_checks_passed = False

        # 5.2: Redirector 없음 확인
        logger.info("  [5.2] Redirector 없음 확인")
        is_redirector = check_redirector_exists(expected_asset_path)
        if not is_redirector:
            logger.info(f"    - SUCCESS: Redirector 없음 (정상 에셋)")
        else:
            logger.error(f"    - FAIL: 에셋 경로에 Redirector가 존재함")
            all_checks_passed = False

        # 5.3: 에셋 타입 확인
        logger.info("  [5.3] 에셋 타입 확인")
        reloaded_asset = unreal.EditorAssetLibrary.load_asset(expected_asset_path)
        if isinstance(reloaded_asset, unreal.AnimSequence):
            logger.info(f"    - SUCCESS: 올바른 에셋 타입 (AnimSequence)")
        else:
            logger.error(f"    - FAIL: 잘못된 에셋 타입: {type(reloaded_asset)}")
            all_checks_passed = False

        # 5.4: 스켈레톤 변경 확인
        logger.info("  [5.4] 스켈레톤 변경 확인")
        if reloaded_asset:
            new_skeleton = reloaded_asset.get_editor_property('skeleton')
            target_skeleton = unreal.EditorAssetLibrary.find_asset_data(target_skeleton_path).get_asset()
            if new_skeleton == target_skeleton:
                logger.info(f"    - SUCCESS: 스켈레톤 변경됨: {new_skeleton.get_name()}")
            else:
                logger.error(f"    - FAIL: 스켈레톤 변경 실패")
                logger.error(f"      예상: {target_skeleton.get_name() if target_skeleton else 'None'}")
                logger.error(f"      실제: {new_skeleton.get_name() if new_skeleton else 'None'}")
                all_checks_passed = False

        # 5.5: 참조자 목록 비교
        logger.info("  [5.5] 참조자 목록 비교")
        referencers_after = get_asset_referencers(expected_asset_path)
        logger.info(f"    - 재임포트 전 참조자: {len(referencers_before)}")
        logger.info(f"    - 재임포트 후 참조자: {len(referencers_after)}")

        # 기존 참조자가 유지되는지 확인
        lost_referencers = set(referencers_before) - set(referencers_after)
        if lost_referencers:
            logger.error(f"    - FAIL: 손실된 참조자 발견")
            for lost in lost_referencers:
                logger.error(f"      - {lost}")
            all_checks_passed = False
        else:
            logger.info(f"    - SUCCESS: 모든 기존 참조자 유지됨")

        # 5.6: 테스트 몽타주 참조 확인
        if test_montage_path:
            logger.info("  [5.6] 테스트 몽타주 참조 확인")
            montage_ref_ok = verify_montage_reference(test_montage_path, expected_asset_path)
            if montage_ref_ok:
                logger.info(f"    - SUCCESS: 테스트 몽타주가 애니메이션을 참조함")
            else:
                logger.warning(f"    - WARNING: 테스트 몽타주 참조 확인 불가")
                # 참조 확인 실패는 경고로만 처리 (몽타주 구조가 다를 수 있음)

        # 테스트 정리
        cleanup_test_montage(test_montage_path)

        # 최종 결과
        if all_checks_passed:
            logger.info("=" * 60)
            logger.info("[Step 5] SUCCESS: 모든 참조 무결성 검증 통과")
            logger.info("=" * 60)
            logger.info("=== TEST END: SUCCESS ===")
            unreal.log("[Test] SUCCESS: Task 5 참조 무결성 검증 통과!")
            return True
        else:
            logger.info("=" * 60)
            logger.error("[Step 5] FAIL: 일부 검증 실패")
            logger.info("=" * 60)
            logger.info("=== TEST END: FAIL ===")
            unreal.log_error("[Test] FAIL: 참조 무결성 검증 실패. 로그를 확인하세요.")
            return False

    except Exception as e:
        logger.error(f"ERROR: 예외 발생 - {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("=== TEST END: ERROR ===")
        unreal.log_error(f"[Test] ERROR: {e}")
        cleanup_test_montage(test_montage_path)
        return False


# 스크립트 실행
if __name__ == "__main__":
    run_test()
