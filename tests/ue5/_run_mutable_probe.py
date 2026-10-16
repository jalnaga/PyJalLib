#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Phase 0 Mutable 프로브 러너.

실행:
    uv run python tests/ue5/_run_mutable_probe.py [섹션 ...]

섹션을 생략하면 **8섹션 전부를 명시 지정**해 한 번에 돈다(쓰기 섹션 포함 - 이 러너를
부르는 것 자체가 옵트인이다). 실패 섹션만 다시 돌리려면 이름을 준다. 쓰기 섹션은
`/Game/__PyJalLibTest__/MutableProbe/` 아래 복제본만 만지고, `verifyMeans`가 끝에서 지운다.

판정은 결과 JSON 단독이다(종료 코드는 진단 정보로만 출력한다).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _ue5HeadlessHarness import run_ue5_script  # noqa: E402
from run_ue5_tests import check_scratch_disk_leftovers  # noqa: E402

PROBE_SCRIPT = Path(__file__).resolve().parent / "_probe_mutable.py"

_SHARED = "/Game/Omni/Characters/Shared/Mutable"
_JEONG = "/Game/Omni/Characters/Main/JeongHuiwon"
_SLOTS = ("Body", "Face", "Glove", "Hair", "Lower", "Mask", "Outer", "Shoes", "Upper")

PROBE_CONFIG = {
    "templateBase": f"{_SHARED}/CO_Template_Sh_Base",
    "templateSlots": {slot: f"{_SHARED}/CO_Template_Sh_{slot}Slot" for slot in _SLOTS},
    # 수작업 정답 표본(마스터 작성, 2026-10-16)
    "sampleBase": f"{_JEONG}/Mutable/CO_JeongHuiwon_Mn_Base",
    "sampleSlot": f"{_JEONG}/MeshB/BunHair/Hair/CO_JeongHuiwon_Mn_BunHair_Hair",
    "sampleSlotName": "Hair",
    "sampleSlotMesh": f"{_JEONG}/MeshB/BunHair/Hair/SK_JeongHuiwon_Mn_BunHair_Hair",
    "sampleBaseMeshes": {
        "Body": f"{_JEONG}/MeshB/Default/Body/SK_JeongHuiwon_Mn_Default_Body",
        "Face": f"{_JEONG}/MeshB/Default/Face/SK_JeongHuiwon_Mn_Default_Face",
    },
    "probeBaseObjectName": "ProbeChar_Pr",
    "probeSlotObjectName": "ProbeOutfit",
    "scratchRoot": "/Game/__PyJalLibTest__/MutableProbe",
    # 2차 실행 결과로 추가(2026-10-16): 복제 시 그룹 GUID가 재생성되고 NewCustomizableObject는
    # 그룹 인자를 무시한다 -> 바이트(템플릿 실측 GroupName FString 기준 +87)/T3D로 복원을 잰다
    "guidOffset": 87,
    "templateHairGuid": "7FDD3EF6447EE5FFEC5B058C7A846F05",
    "exportDir": str(Path(__file__).resolve().parents[1] / "logs" / "mutable_probe_t3d"),
    "onlySections": [
        "environment",
        "nodeEnum",
        "propAccess",
        "groupGuid",
        "duplicateWrite",
        "guidRecovery",
        "groupFallback",
        "verifyMeans",
        "materialIndex",
    ],
}


def main() -> None:
    """프로브를 실행하고 섹션별 결과를 요약 출력한다."""
    config = dict(PROBE_CONFIG)
    if len(sys.argv) > 1:
        config["onlySections"] = sys.argv[1:]

    run = run_ue5_script(PROBE_SCRIPT, config, "mutable_probe")
    print(f"판정: success={run.verdict.success} reason={run.verdict.reasonCode}")
    print(f"상세: {run.verdict.detail}")
    print(f"종료 코드: {run.returnCode} (판정 축 아님)")
    print(f"결과 JSON: {run.resultJsonPath}")
    print(f"엔진 로그: {run.engineLogPath}")
    leftovers = check_scratch_disk_leftovers()
    print(f"스크래치 디스크 잔여: {leftovers}")
    if run.resultJson is None:
        print("--- stdout tail ---")
        print(run.stdoutTail)
        sys.exit(1)
    for name, section in run.resultJson.get("sections", {}).items():
        print(f"[{name}] succeeded={section.get('succeeded')} error={section.get('error', '')}")
    print("environment:", json.dumps(run.resultJson.get("environment"), ensure_ascii=False))
    sys.exit(0 if run.verdict.success and not leftovers else 1)


if __name__ == "__main__":
    main()
