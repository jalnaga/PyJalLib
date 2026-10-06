#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""배포본 로드 프로브 - P4 배포처의 `materialSlots`를 UE5 방식(평면 import)으로 띄운다.

워크트리가 아니라 **배포본이 실제로 도는지**를 단정한다(`ue5/silent_write_paths.md` §8).
원본 에셋은 읽기만 하고 드라이런만 한다 - 저장·메모리 쓰기 없음. 배포처를 `.pyc`로
오염시키지 않도록 `sys.dont_write_bytecode`를 import 전에 세운다.
"""

import json
import os
import sys
import traceback

sys.dont_write_bytecode = True

import unreal  # noqa: E402

with open(os.environ["PYJAL_UE5_TEST_CONFIG"], "r", encoding="utf-8") as _configFile:
    CONFIG = json.load(_configFile)

result = {"success": False}
try:
    inUnrealDir = CONFIG["deployInUnrealDir"]
    for name in ("materialSlots", "materialSlotRules"):
        sys.modules.pop(name, None)
    sys.path.insert(0, inUnrealDir)
    import materialSlots  # noqa: E402

    deployRoot = os.path.dirname(os.path.dirname(inUnrealDir)).replace("\\", "/")
    result["adapterFile"] = materialSlots.__file__.replace("\\", "/")
    result["rulesFile"] = materialSlots.materialSlotRules.__file__.replace("\\", "/")
    result["loadedFromDeploy"] = (
        result["adapterFile"].startswith(deployRoot) and result["rulesFile"].startswith(deployRoot)
    )
    result["hasRenamer"] = hasattr(materialSlots, "MaterialSlotRenamer")

    renamer = materialSlots.MaterialSlotRenamer(CONFIG["renameTable"])
    plan = renamer.build_plan(CONFIG["assets"])
    dryRun = renamer.apply_plan(plan)
    result["plan"] = plan.to_dict()
    result["dryRunCounts"] = dryRun["counts"]
    result["dryRunSaved"] = dryRun["savedCount"]
    result["success"] = (
        result["loadedFromDeploy"] and result["hasRenamer"]
        and dryRun["dryRun"] is True and dryRun["savedCount"] == 0
        and plan.to_dict()["loadFailureCount"] == 0
    )
except Exception as probeError:  # noqa: BLE001 - 결과 JSON은 어떤 경우에도 남긴다
    result["error"] = f"{type(probeError).__name__}: {probeError}"
    result["traceback"] = traceback.format_exc()

os.makedirs(os.path.dirname(CONFIG["outputJsonPath"]), exist_ok=True)
with open(CONFIG["outputJsonPath"], "w", encoding="utf-8") as _outputFile:
    json.dump(result, _outputFile, ensure_ascii=False, indent=2)
unreal.log(f"[DeployProbe] success={result['success']}")
