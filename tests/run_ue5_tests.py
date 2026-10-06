#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""UE5 Type C 러너 - `tests/ue5/ue5_test_*.py`를 헤드레스 UE5로 실행한다.

실행:
    uv run python tests/run_ue5_tests.py

**판정은 결과 JSON 단독이다.** 종료 코드는 진단 정보로만 출력한다(UE5 헤드레스는
스크립트가 죽어도 0을 낸다 - `patterns/subprocess_verdict_axis.md`). 실행·신선도 게이트는
`tests/ue5/_ue5HeadlessHarness.py`가 라이브러리 부품으로 한다.

UE5가 없는 머신에서는 skip이 아니라 **실패**한다 - 이 워크스페이스의 툴은 DCC 호스트를
전제로 한다.
"""

import sys
from pathlib import Path

_UE5_TESTS_DIR = Path(__file__).resolve().parent / "ue5"
sys.path.insert(0, str(_UE5_TESTS_DIR))

from _ue5HeadlessHarness import UE5_EDITOR_PATH, UE5_PROJECT_PATH, run_ue5_script  # noqa: E402

SCRATCH_DISK_ROOT = Path(UE5_PROJECT_PATH).parent / "Content" / "__PyJalLibTest__"
"""스위트가 복제본을 두는 `/Game/__PyJalLibTest__/`의 디스크 위치."""


def check_scratch_disk_leftovers() -> list:
    """UE5 종료 후 스크래치 폴더의 디스크 잔여물을 검사한다.

    인-UE5 정리는 파일을 지우지만, 엔진이 디렉토리 핸들을 쥐고 있어 **빈 폴더**는 실행 중에
    지워지지 않을 수 있다(2026-10-02 실측). 엔진이 내려간 뒤 빈 폴더만 지우고, 파일이 남아
    있으면 지우지 않고 잔여물로 보고한다 - 무엇이 남았는지 사람이 봐야 한다.

    Returns:
        남은 파일 경로 목록(빈 목록이면 깨끗하다)
    """
    if not SCRATCH_DISK_ROOT.exists():
        return []
    leftovers = [p.as_posix() for p in SCRATCH_DISK_ROOT.rglob("*") if p.is_file()]
    if leftovers:
        return leftovers
    for directory in sorted(SCRATCH_DISK_ROOT.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        directory.rmdir()
    SCRATCH_DISK_ROOT.rmdir()
    return []

SUITES = {
    "ue5_test_material_slots.py": {
        # 원본은 읽기·복제만 한다(Phase 0 프로브와 같은 에셋)
        "skeletalSource": (
            "/Game/Omni/Characters/Shared/Human-Male/CustomObject/CIHBattle/"
            "SK_CO_HumanM_Sh_ArmSevered_CIHBattle_Face"
        ),
        "staticSource": "/Game/Developers/Sonic/BossPrototype/Meshes/SM_MiniTurret_Joined",
        "scratchRoot": "/Game/__PyJalLibTest__/MatSlotTypeC",
    },
}


def main() -> None:
    """등록된 스위트를 실행하고 TC별 결과를 출력한다."""
    if not Path(UE5_EDITOR_PATH).is_file():
        print(f"[FAIL] UE5 에디터가 없다: {UE5_EDITOR_PATH}")
        sys.exit(1)

    allPassed = True
    for scriptName, config in SUITES.items():
        run = run_ue5_script(_UE5_TESTS_DIR / scriptName, config, Path(scriptName).stem)
        print("=" * 60)
        print(f"{scriptName}: success={run.verdict.success} reason={run.verdict.reasonCode}")
        print(f"  종료 코드: {run.returnCode} (판정 축 아님), 결과 JSON: {run.resultJsonPath}")
        if run.resultJson is None:
            print(run.stdoutTail)
            allPassed = False
            continue
        for test in run.resultJson.get("tests", []):
            mark = "PASS" if test["passed"] else "FAIL"
            print(f"  [{mark}] {test['name']} {test.get('error', '')}")
        leftovers = run.resultJson.get("cleanupLeftovers", [])
        print(f"  정리 잔여물: {leftovers if leftovers else '없음'}")
        if run.resultJson.get("error"):
            print(f"  치명적 오류: {run.resultJson['error']}")
        allPassed = allPassed and run.verdict.success

    diskLeftovers = check_scratch_disk_leftovers()
    print("=" * 60)
    print(f"디스크 잔여물({SCRATCH_DISK_ROOT.as_posix()}): {diskLeftovers if diskLeftovers else '없음'}")
    allPassed = allPassed and not diskLeftovers
    print("=" * 60)
    print("ALL PASSED" if allPassed else "FAILED")
    sys.exit(0 if allPassed else 1)


if __name__ == "__main__":
    main()
