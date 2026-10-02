#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Type C - 매테리얼 슬롯 어댑터 실기 검증 (UE5 임베디드 파이썬 전용).

러너: `uv run python tests/run_ue5_tests.py` (판정은 이 스크립트가 쓰는 결과 JSON 단독).

라이브러리를 **배포본이 실제로 도는 방식 그대로** 로드한다 - `inUnreal` 폴더를 `sys.path`에
얹고 평면 import한다(UE5 legacy 템플릿 방식, `ue5/silent_write_paths.md` §8). 로드 출처는
TC00이 `__file__`로 단정한다.

**이 스크립트는 슬롯 쓰기 경로의 복사본을 갖지 않는다.** 쓰기는 전부 라이브러리 헬퍼
(`materialSlots.write_slot_name` / `MaterialSlotRenamer`)로 한다. TC00이 자기 소스를 읽어
배열 프로퍼티 이름 리터럴·메쉬 프로퍼티 되쓰기가 없음을 단정한다. 판별력 TC의 변이도
"사본만 수정"이라 메쉬에 되쓰지 않는다.

에셋: 원본(읽기만) -> `/Game/__PyJalLibTest__/MatSlotTypeC/` 복제 -> 픽스처 슬롯 이름 기록
-> 저장. 이후 TC는 이 복제본만 만진다. 끝에 복제본을 메모리·디스크에서 지운다(헤드레스
`delete_asset`은 메모리만 지우므로 디스크 파일을 직접 지운다). 하니스가 `-SCCProvider=None`
으로 띄우므로 저장이 P4에 닿지 않는다 - TC00이 확인한다.
"""

import json
import os
import re
import stat
import sys
import traceback
from typing import Callable, Dict, List

sys.dont_write_bytecode = True

import unreal  # noqa: E402

_THIS_FILE = os.path.abspath(__file__)
_IN_UNREAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE))), "src", "pyjallib", "ue5", "inUnreal"
)
for _moduleName in ("materialSlots", "materialSlotRules"):
    sys.modules.pop(_moduleName, None)
if _IN_UNREAL_DIR not in sys.path:
    sys.path.insert(0, _IN_UNREAL_DIR)

import materialSlots  # noqa: E402

CONFIG_ENV = "PYJAL_UE5_TEST_CONFIG"
LOG_PREFIX = "[MatSlotTypeC]"

FIXTURE_NAMES = ["Body", "EyeBrow", "Lower", "PyJalTC_Face", "Iris"]
"""복제본에 기록할 슬롯 이름(슬롯 수만큼 순환). rename / 변이 rename / unmapped / already가 다 나온다."""

RENAME_TABLE = {
    "Body": "PyJalTC_Body",
    "Eyebrow": "PyJalTC_Eyebrow",
    "Face": "PyJalTC_Face",
    "Iris": "PyJalTC_Iris",
}
"""목표명을 원본 에셋에 없는 고유 문자열로 둔다 - 디스크 바이트 검색이 공허해지지 않게."""


def _log(inMessage: str) -> None:
    """엔진 로그에 정보 메시지를 남긴다.

    Args:
        inMessage: 메시지
    """
    unreal.log(f"{LOG_PREFIX} {inMessage}")


class _Ctx:
    """TC 사이에서 공유하는 상태."""

    def __init__(self, inConfig: Dict):
        self.config = inConfig
        self.scratchRoot: str = inConfig["scratchRoot"]
        self.meshes: Dict[str, Dict] = {}  # 타입 이름 -> {packagePath, filePath, fixture}


# ---------------------------------------------------------------------------
# 보조
# ---------------------------------------------------------------------------


def _set_read_only(inFilePath: str, inReadOnly: bool) -> None:
    """파일 읽기 전용 속성을 바꾼다.

    Args:
        inFilePath: 파일 경로
        inReadOnly: True면 읽기 전용
    """
    os.chmod(inFilePath, stat.S_IREAD if inReadOnly else stat.S_IREAD | stat.S_IWRITE)


def _file_contains(inFilePath: str, inText: str) -> bool:
    """`.uasset` 바이트에 문자열이 있는지 본다(FName은 이름 표에 평문으로 실린다).

    Args:
        inFilePath: 파일 경로
        inText: ASCII 문자열

    Returns:
        포함 여부
    """
    with open(inFilePath, "rb") as assetFile:
        return inText.encode("ascii") in assetFile.read()


def _names_of(inPackagePath: str) -> List[str]:
    """메쉬를 로드해 슬롯 이름을 읽는다.

    Args:
        inPackagePath: 패키지 경로

    Returns:
        슬롯 이름 목록
    """
    mesh, reason, _ = materialSlots.load_mesh(inPackagePath)
    assert mesh is not None, f"로드 실패: {inPackagePath} ({reason})"
    return materialSlots.read_slot_names(mesh)


def _expected_targets(inFixture: List[str]) -> List[str]:
    """픽스처 이름에 표를 적용한 기대 결과를 만든다(테스트 쪽 독립 계산 - 결정 모듈을 쓰지 않는다).

    Args:
        inFixture: 픽스처 슬롯 이름

    Returns:
        기대 슬롯 이름
    """
    lowered = {key.lower(): value for key, value in RENAME_TABLE.items()}
    return [lowered.get(name.lower(), name) for name in inFixture]


def _cleanup_scratch(inScratchRoot: str) -> List[str]:
    """복제본을 메모리·디스크에서 지운다.

    Args:
        inScratchRoot: 복제본 패키지 폴더

    Returns:
        지우지 못하고 남은 디스크 파일 목록
    """
    if unreal.EditorAssetLibrary.does_directory_exist(inScratchRoot):
        unreal.EditorAssetLibrary.delete_directory(inScratchRoot)
    diskDir = os.path.dirname(materialSlots.package_file_path(f"{inScratchRoot}/x"))
    leftovers: List[str] = []
    if os.path.isdir(diskDir):
        for fileName in os.listdir(diskDir):
            filePath = os.path.join(diskDir, fileName).replace("\\", "/")
            try:
                _set_read_only(filePath, False)
                os.remove(filePath)
            except OSError:
                leftovers.append(filePath)
        for directory in (diskDir, os.path.dirname(diskDir)):
            try:
                os.rmdir(directory)
            except OSError:
                pass
    return leftovers


class _UnrealSpy:
    """`materialSlots`가 보는 `unreal`을 감싸 load_asset / save_asset 호출을 센다.

    "드라이런은 로드도 저장도 하지 않는다"는 결과값으로는 증명되지 않는다 - 호출 0회를 센다
    (`testing/discriminating_power.md` §2).
    """

    def __init__(self, inReal):
        self._real = inReal
        self.loadCalls = 0
        self.saveCalls = 0
        spy = self

        class _EditorAssetLibrarySpy:
            @staticmethod
            def save_asset(*inArgs, **inKwargs):
                spy.saveCalls += 1
                return inReal.EditorAssetLibrary.save_asset(*inArgs, **inKwargs)

            def __getattr__(self, inName):
                return getattr(inReal.EditorAssetLibrary, inName)

        self.EditorAssetLibrary = _EditorAssetLibrarySpy()

    def load_asset(self, *inArgs, **inKwargs):
        """로드 호출을 센다."""
        self.loadCalls += 1
        return self._real.load_asset(*inArgs, **inKwargs)

    def __getattr__(self, inName):
        return getattr(self._real, inName)


def _copy_only_write(inMesh, inSlotIndex: int, inSlotName: str) -> None:
    """변이: 사본만 고치고 메쉬에 되쓰지 않는다(UE5에서 조용히 무시되는 경로)."""
    slots = inMesh.get_editor_property(materialSlots.slot_array_property(inMesh))
    slot = slots[inSlotIndex]
    slot.set_editor_property(materialSlots.SLOT_NAME_FIELD, inSlotName)


# ---------------------------------------------------------------------------
# TC
# ---------------------------------------------------------------------------


def tc00_setup_and_load_source(inCtx: _Ctx) -> Dict:
    """로드 출처·소스 컨트롤 비활성·쓰기 경로 무복사를 단정하고 복제본 픽스처를 만든다."""
    worktreeSrc = os.path.dirname(os.path.dirname(_IN_UNREAL_DIR)).replace("\\", "/")
    adapterFile = materialSlots.__file__.replace("\\", "/")
    rulesFile = materialSlots.materialSlotRules.__file__.replace("\\", "/")
    assert adapterFile.startswith(worktreeSrc), f"어댑터 로드 출처가 이 트리가 아니다: {adapterFile}"
    assert rulesFile.startswith(worktreeSrc), f"규칙 모듈 로드 출처가 이 트리가 아니다: {rulesFile}"
    assert unreal.SourceControl.is_enabled() is False, "소스 컨트롤이 켜져 있다 - 저장이 P4에 닿을 수 있다"

    with open(_THIS_FILE, "r", encoding="utf-8") as selfFile:
        ownSource = selfFile.read()
    # 리터럴을 조합으로 만든다 - 이 줄 자체가 검사에 걸리지 않게
    for propertyName in ("static_" + "mater" + "ials", "materi" + "als"):
        assert f'"{propertyName}"' not in ownSource, f"배열 프로퍼티 리터럴 {propertyName}이 있다"
    assert re.search(r"[Mm]esh\.set_editor_property\(", ownSource) is None, "메쉬 프로퍼티 되쓰기 복사본이 있다"

    leftovers = _cleanup_scratch(inCtx.scratchRoot)
    assert not leftovers, f"이전 실행 잔여물을 지우지 못했다: {leftovers}"

    sources = {
        materialSlots.MESH_TYPE_SKELETAL: inCtx.config["skeletalSource"],
        materialSlots.MESH_TYPE_STATIC: inCtx.config["staticSource"],
    }
    for meshType, sourcePath in sources.items():
        destination = f"{inCtx.scratchRoot}/{sourcePath.rsplit('/', 1)[-1]}"
        duplicated = unreal.EditorAssetLibrary.duplicate_asset(sourcePath, destination)
        assert duplicated is not None, f"복제 실패: {sourcePath}"
        assert materialSlots.mesh_type_of(duplicated) == meshType, f"타입 불일치: {meshType}"
        slotCount = len(materialSlots.read_slot_names(duplicated))
        assert slotCount >= 3, f"픽스처에 슬롯 3개 이상이 필요하다: {sourcePath} ({slotCount})"
        fixture = [FIXTURE_NAMES[i % len(FIXTURE_NAMES)] for i in range(slotCount)]
        for index, name in enumerate(fixture):
            assert materialSlots.write_slot_name(duplicated, index, name), f"픽스처 기록 실패: {index}"
        assert unreal.EditorAssetLibrary.save_asset(destination, only_if_is_dirty=False)
        filePath = materialSlots.package_file_path(destination)
        assert os.path.isfile(filePath), f"픽스처 저장 후 파일이 없다: {filePath}"
        for target in set(_expected_targets(fixture)) - set(fixture):
            assert not _file_contains(filePath, target), f"목표명 {target}이 픽스처에 이미 있다 - 바이트 검증이 공허하다"
        inCtx.meshes[meshType] = {"packagePath": destination, "filePath": filePath, "fixture": fixture}

    return {"adapterFile": adapterFile, "rulesFile": rulesFile, "meshes": inCtx.meshes}


def tc01_dry_run_changes_nothing(inCtx: _Ctx) -> Dict:
    """3.3 드라이런은 로드·저장을 하지 않고 슬롯·mtime·읽기 전용 속성을 바꾸지 않는다."""
    renamer = materialSlots.MaterialSlotRenamer(RENAME_TABLE)
    paths = [m["packagePath"] for m in inCtx.meshes.values()]
    plan = renamer.build_plan(paths)
    assert all(a.willChange for a in plan.assets), "픽스처가 변경 대상이 아니면 드라이런 판정이 공허하다"

    before = {}
    for mesh in inCtx.meshes.values():
        _set_read_only(mesh["filePath"], True)
        before[mesh["filePath"]] = os.path.getmtime(mesh["filePath"])

    realUnreal = materialSlots.unreal
    spy = _UnrealSpy(realUnreal)
    materialSlots.unreal = spy
    try:
        result = renamer.apply_plan(plan)  # 기본값이 드라이런이어야 한다
    finally:
        materialSlots.unreal = realUnreal

    try:
        assert result["dryRun"] is True, "apply_plan 기본값이 드라이런이 아니다"
        assert result["counts"]["dryRun"] == len(paths), result["counts"]
        assert result["savedCount"] == 0
        assert spy.saveCalls == 0, f"드라이런이 save_asset을 {spy.saveCalls}회 불렀다"
        assert spy.loadCalls == 0, f"드라이런이 load_asset을 {spy.loadCalls}회 불렀다"
        for mesh in inCtx.meshes.values():
            assert _names_of(mesh["packagePath"]) == mesh["fixture"]
            assert os.path.getmtime(mesh["filePath"]) == before[mesh["filePath"]]
            assert not os.access(mesh["filePath"], os.W_OK), "드라이런 뒤 읽기 전용이 풀렸다"
    finally:
        for mesh in inCtx.meshes.values():
            _set_read_only(mesh["filePath"], False)
    return {"counts": result["counts"], "saveCalls": spy.saveCalls, "loadCalls": spy.loadCalls}


def _round_trip_forward(inCtx: _Ctx, inMeshType: str) -> Dict:
    """치환 -> 되읽기 전수 -> 보존 확인 -> 디스크 바이트 확인(원복은 별도)."""
    mesh = inCtx.meshes[inMeshType]
    loaded, _, _ = materialSlots.load_mesh(mesh["packagePath"])
    materialsBefore = materialSlots.read_material_asset_paths(loaded)
    mtimeBefore = os.path.getmtime(mesh["filePath"])
    expected = _expected_targets(mesh["fixture"])
    assert expected != mesh["fixture"], "기대값이 픽스처와 같으면 왕복 판정이 공허하다"

    renamer = materialSlots.MaterialSlotRenamer(RENAME_TABLE)
    result = renamer.apply_plan(renamer.build_plan([mesh["packagePath"]]), inDryRun=False)
    record = result["assets"][0]
    assert record["status"] == materialSlots.STATUS_CHANGED, f"{record['status']} {record['failureReason']} {record['failureDetail']}"
    assert record["saved"] is True
    assert [s["after"] for s in record["slots"]] == expected, record["slots"]

    afterNames = _names_of(mesh["packagePath"])
    assert afterNames == expected, f"되읽기 {afterNames} != 기대 {expected}"
    assert len(afterNames) == len(mesh["fixture"]), "슬롯 개수가 바뀌었다"
    assert materialSlots.read_material_asset_paths(loaded) == materialsBefore, "매테리얼 참조가 바뀌었다"
    assert os.path.getmtime(mesh["filePath"]) > mtimeBefore, "저장했다는데 mtime이 그대로다"
    for target in set(expected) - set(mesh["fixture"]):
        assert _file_contains(mesh["filePath"], target), f"디스크 파일에 {target}이 없다"
    return {"expected": expected, "after": afterNames, "renamedSlotCount": result["renamedSlotCount"]}


def _round_trip_restore(inCtx: _Ctx, inMeshType: str) -> Dict:
    """역방향 표(대소문자 구분)로 픽스처 이름까지 되돌린다."""
    mesh = inCtx.meshes[inMeshType]
    expected = _expected_targets(mesh["fixture"])
    reverse = {after: before for before, after in zip(mesh["fixture"], expected) if before != after}
    renamer = materialSlots.MaterialSlotRenamer(reverse, inIgnoreCase=False)
    result = renamer.apply_plan(renamer.build_plan([mesh["packagePath"]]), inDryRun=False)
    record = result["assets"][0]
    assert record["status"] == materialSlots.STATUS_CHANGED, f"{record['failureReason']} {record['failureDetail']}"
    assert _names_of(mesh["packagePath"]) == mesh["fixture"], "원복 실패"
    return {"reverseTable": reverse}


def tc02_skeletal_round_trip(inCtx: _Ctx) -> Dict:
    """3.4 SkeletalMesh 왕복(원복은 tc05 뒤)."""
    return _round_trip_forward(inCtx, materialSlots.MESH_TYPE_SKELETAL)


def tc03_static_round_trip(inCtx: _Ctx) -> Dict:
    """3.5 StaticMesh 왕복(원복은 tc05 뒤)."""
    return _round_trip_forward(inCtx, materialSlots.MESH_TYPE_STATIC)


def tc04_idempotent(inCtx: _Ctx) -> Dict:
    """3.7 같은 표를 다시 적용하면 전부 skip이고 저장 0건, mtime 불변."""
    renamer = materialSlots.MaterialSlotRenamer(RENAME_TABLE)
    paths = [m["packagePath"] for m in inCtx.meshes.values()]
    mtimes = {m["filePath"]: os.path.getmtime(m["filePath"]) for m in inCtx.meshes.values()}
    plan = renamer.build_plan(paths)
    actions = {d.action for a in plan.assets for d in a.decisions}
    assert actions <= {"skip:already", "skip:unmapped"}, actions
    assert "skip:already" in actions, "skip:already가 없으면 멱등 판정이 공허하다"
    result = renamer.apply_plan(plan, inDryRun=False)
    assert result["counts"]["unchanged"] == len(paths), result["counts"]
    assert result["savedCount"] == 0
    for filePath, mtime in mtimes.items():
        assert os.path.getmtime(filePath) == mtime, f"변경 없는 에셋이 저장됐다: {filePath}"
    return {"counts": result["counts"]}


def tc05_restore(inCtx: _Ctx) -> Dict:
    """3.4/3.5 왕복의 원복."""
    return {
        meshType: _round_trip_restore(inCtx, meshType)
        for meshType in (materialSlots.MESH_TYPE_SKELETAL, materialSlots.MESH_TYPE_STATIC)
    }


def tc06_read_only_not_checked_out(inCtx: _Ctx) -> Dict:
    """3.6 읽기 전용 파일은 notCheckedOut으로 떨어지고 저장도 메모리 변경도 없다."""
    details = {}
    for meshType, mesh in inCtx.meshes.items():
        _set_read_only(mesh["filePath"], True)
        try:
            mtime = os.path.getmtime(mesh["filePath"])
            renamer = materialSlots.MaterialSlotRenamer(RENAME_TABLE)
            plan = renamer.build_plan([mesh["packagePath"]])
            assert plan.assets[0].willChange, "변경 대상이 아니면 가드 판정이 공허하다"
            record = renamer.apply_plan(plan, inDryRun=False)["assets"][0]
            assert record["status"] == materialSlots.STATUS_FAILED
            assert record["failureReason"] == materialSlots.FAIL_NOT_CHECKED_OUT, record["failureReason"]
            assert record["saved"] is False
            assert os.path.getmtime(mesh["filePath"]) == mtime, "읽기 전용 파일이 저장됐다"
            assert not os.access(mesh["filePath"], os.W_OK), "읽기 전용이 풀렸다(자동 체크아웃 흔적)"
            assert _names_of(mesh["packagePath"]) == mesh["fixture"], "가드 전에 메모리를 바꿨다"
            details[meshType] = record["failureReason"]
        finally:
            _set_read_only(mesh["filePath"], False)
    return details


def tc07_discriminating_copy_only_write(inCtx: _Ctx) -> Dict:
    """3.8 쓰기를 "사본만 수정"으로 바꾸면 왕복 TC가 실제로 실패하고, 어댑터는 저장하지 않는다."""
    original = materialSlots._write_slot_name_unverified
    materialSlots._write_slot_name_unverified = _copy_only_write
    details = {}
    try:
        for meshType, mesh in inCtx.meshes.items():
            mtime = os.path.getmtime(mesh["filePath"])
            # (1) 왕복 TC 자체가 이 변이에서 실패한다 - 통과하면 왕복 TC는 판별력이 없다
            try:
                _round_trip_forward(inCtx, meshType)
            except AssertionError as caught:
                details[f"{meshType}.roundTripFailed"] = str(caught)[:200]
            else:
                raise AssertionError(f"사본만 수정하는 변이에서 {meshType} 왕복 TC가 통과했다")
            # (2) 어댑터는 되읽기로 실패를 잡아 저장하지 않는다
            renamer = materialSlots.MaterialSlotRenamer(RENAME_TABLE)
            record = renamer.apply_plan(renamer.build_plan([mesh["packagePath"]]), inDryRun=False)["assets"][0]
            assert record["failureReason"] == materialSlots.FAIL_WRITE_NOT_VERIFIED, record["failureReason"]
            assert record["saved"] is False
            assert os.path.getmtime(mesh["filePath"]) == mtime, "검증 실패인데 저장됐다"
            details[f"{meshType}.adapterReason"] = record["failureReason"]
    finally:
        materialSlots._write_slot_name_unverified = original
    # 원래 구현으로 되돌린 뒤 같은 에셋이 다시 정상 동작하는지(변이가 상태를 오염시키지 않았는지)
    for mesh in inCtx.meshes.values():
        assert _names_of(mesh["packagePath"]) == mesh["fixture"]
    return details


TESTS: List[Callable[[_Ctx], Dict]] = [
    tc00_setup_and_load_source,
    tc01_dry_run_changes_nothing,
    tc02_skeletal_round_trip,
    tc03_static_round_trip,
    tc04_idempotent,
    tc05_restore,
    tc06_read_only_not_checked_out,
    tc07_discriminating_copy_only_write,
]


def main() -> None:
    """TC를 순서대로 실행하고 결과 JSON을 쓴다. TC00이 실패하면 뒤 TC는 돌지 않는다."""
    result: Dict = {"success": False, "tests": []}
    outputJsonPath = ""
    ctx = None
    try:
        with open(os.environ[CONFIG_ENV], "r", encoding="utf-8") as configFile:
            config = json.load(configFile)
        outputJsonPath = config["outputJsonPath"]
        ctx = _Ctx(config)
        for testFunc in TESTS:
            entry: Dict = {"name": testFunc.__name__, "passed": False}
            _log(f"TC 시작: {testFunc.__name__}")
            try:
                entry["details"] = testFunc(ctx)
                entry["passed"] = True
            except Exception as testError:  # noqa: BLE001 - TC 실패는 결과로 남긴다
                entry["error"] = f"{type(testError).__name__}: {testError}"
                entry["traceback"] = traceback.format_exc()
                unreal.log_error(f"{LOG_PREFIX} TC 실패: {testFunc.__name__} - {testError}")
            result["tests"].append(entry)
            if testFunc is tc00_setup_and_load_source and not entry["passed"]:
                break
        result["success"] = len(result["tests"]) == len(TESTS) and all(t["passed"] for t in result["tests"])
    except Exception as fatalError:  # noqa: BLE001 - 결과 JSON은 어떤 경우에도 남긴다
        result["error"] = f"{type(fatalError).__name__}: {fatalError}"
        result["traceback"] = traceback.format_exc()
    finally:
        if ctx is not None:
            try:
                result["cleanupLeftovers"] = _cleanup_scratch(ctx.scratchRoot)
            except Exception as cleanupError:  # noqa: BLE001
                result["cleanupLeftovers"] = [f"<cleanup error: {cleanupError}>"]
            if result["cleanupLeftovers"]:
                result["success"] = False

    if outputJsonPath:
        os.makedirs(os.path.dirname(outputJsonPath), exist_ok=True)
        with open(outputJsonPath, "w", encoding="utf-8") as outputFile:
            json.dump(result, outputFile, ensure_ascii=False, indent=2, default=str)
        _log(f"결과 JSON 기록: {outputJsonPath}")


main()
