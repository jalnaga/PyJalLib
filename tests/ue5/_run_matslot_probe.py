#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Phase 0 매테리얼 슬롯 프로브 러너.

실행:
    uv run python tests/ue5/_run_matslot_probe.py [섹션 ...]

섹션을 생략하면 **5섹션 전부를 명시 지정**해 한 번에 돈다(쓰기 섹션 `staticMeshWrite`
포함 - 이 러너를 부르는 것 자체가 옵트인이다). 실패 섹션만 다시 돌리려면 이름을 준다.

판정은 결과 JSON 단독이다(종료 코드는 진단 정보로만 출력한다).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ue5HeadlessHarness import run_ue5_script  # noqa: E402

PROBE_SCRIPT = Path(__file__).resolve().parent / "_probe_material_slots.py"

# 프로브 대상 - 프로덕션 정본이 아닌 것(개발자 폴더·블록아웃·마켓플레이스·엔진 기본 도형).
# 원본은 읽기만 하고, 쓰기 섹션은 scratchRoot 아래 메모리 복제본만 만진다.
PROBE_CONFIG = {
    "staticCandidates": [
        "/Game/Developers/Sonic/BossPrototype/Meshes/SM_MiniTurret_Joined",
        "/Game/Omni/Environment/BlockOut/BlockOut_ChungmuroSt/SM_CMRSt_DAEHAN_F5_O",
        "/Game/Marketplace/FluidNinjaLive2/Meshes/Primitives/SM_bendedplane_200x200",
        "/Engine/BasicShapes/Cube",
    ],
    # 2026-09-15 1차 사이클 apiShape 프로브 대상과 같은 에셋(승계 실측의 재확인)
    "skeletalSource": (
        "/Game/Omni/Characters/Shared/Human-Male/CustomObject/CIHBattle/"
        "SK_CO_HumanM_Sh_ArmSevered_CIHBattle_Face"
    ),
    "scratchRoot": "/Game/__PyJalLibTest__/MatSlotProbe",
    "onlySections": [
        "staticMeshShape",
        "staticMeshWrite",
        "skeletalMeshRecheck",
        "meshTypeDispatch",
        "sideEffects",
    ],
}


def main() -> None:
    """프로브를 실행하고 섹션별 결과를 요약 출력한다."""
    config = dict(PROBE_CONFIG)
    if len(sys.argv) > 1:
        config["onlySections"] = sys.argv[1:]

    run = run_ue5_script(PROBE_SCRIPT, config, "matslot_probe")
    print(f"판정: success={run.verdict.success} reason={run.verdict.reasonCode}")
    print(f"상세: {run.verdict.detail}")
    print(f"종료 코드: {run.returnCode} (판정 축 아님)")
    print(f"결과 JSON: {run.resultJsonPath}")
    print(f"엔진 로그: {run.engineLogPath}")
    if run.resultJson is None:
        print("--- stdout tail ---")
        print(run.stdoutTail)
        sys.exit(1)
    for name, section in run.resultJson.get("sections", {}).items():
        print(f"[{name}] succeeded={section.get('succeeded')} error={section.get('error', '')}")
    print("environment:", json.dumps(run.resultJson.get("environment"), ensure_ascii=False))
    sys.exit(0 if run.verdict.success else 1)


if __name__ == "__main__":
    main()
