#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Type C - Mutable CO 생성 어댑터 실기 검증 (UE5 임베디드 파이썬 전용).

러너: `uv run python tests/run_ue5_tests.py` (판정은 이 스크립트가 쓰는 결과 JSON 단독).

라이브러리를 **배포본이 실제로 도는 방식 그대로** 로드한다 - `inUnreal` 폴더를 `sys.path`에
얹고 평면 import한다. 로드 출처는 TC00이 `__file__`로 단정한다.

**이 스크립트는 쓰기 경로의 복사본을 갖지 않는다.** CO 생성·노드 쓰기는 전부
`mutableObjects.MutableObjectBuilder`가 하고, 이 스크립트는 라이브러리의 **읽기** 헬퍼
(`list_graph_nodes` / `node_value_path` / `export_t3d_text`)로 결과를 되읽는다. TC00이 자기
소스에 이름 쓰기 함수·T3D 익스포터 리터럴이 없음을 단정한다.

픽스처: 정희원 SK(읽기만)를 `/Game/__PyJalLibTest__/MutableTypeC/Characters/Main/PyJalTcChar/`
아래 규약 이름으로 복제·저장해 캐릭터 트리를 만든다. 템플릿은 실기 템플릿을 읽기·복제만 한다.
끝에 스크래치 폴더를 메모리·디스크에서 지운다. 하니스가 `-SCCProvider=None`으로 띄우므로
저장이 P4에 닿지 않는다 - TC00이 확인한다.
"""

import json
import os
import struct
import sys
import traceback
from typing import Callable, Dict, List

sys.dont_write_bytecode = True

import unreal  # noqa: E402

_THIS_FILE = os.path.abspath(__file__)
_IN_UNREAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE))), "src", "pyjallib", "ue5", "inUnreal"
)
for _moduleName in ("mutableObjects", "mutableRules"):
    sys.modules.pop(_moduleName, None)
if _IN_UNREAL_DIR not in sys.path:
    sys.path.insert(0, _IN_UNREAL_DIR)

import mutableObjects  # noqa: E402

rules = mutableObjects.mutableRules

CONFIG_ENV = "PYJAL_UE5_TEST_CONFIG"
LOG_PREFIX = "[MutableTypeC]"
CHARACTER = "PyJalTcChar"
ROLE = "Tc"
FACE_PARTS = ("Eyebrow", "Eyeline", "Iris", "MouthInterior")


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
        self.root = f"{self.scratchRoot}/Characters/Main/{CHARACTER}"
        self.buildConfig = rules.MutableBuildConfig(
            baseTemplatePath=inConfig["baseTemplatePath"],
            slotTemplatePattern=inConfig["slotTemplatePattern"],
            meshFolderName="MeshB",
            mutableFolderName="Mutable",
            baseOutfit="Default",
            excludedOutfits=("BaseSkeleton",),
        )
        self.meshes: Dict[str, str] = {}  # "Outfit/Slot" -> 패키지 경로
        self.lastResult: Dict = {}

    def mesh(self, inOutfit: str, inSlot: str) -> str:
        return f"{self.root}/MeshB/{inOutfit}/{inSlot}/SK_{CHARACTER}_{ROLE}_{inOutfit}_{inSlot}"

    def slot_object(self, inOutfit: str, inSlot: str) -> str:
        return f"{self.root}/MeshB/{inOutfit}/{inSlot}/CO_{CHARACTER}_{ROLE}_{inOutfit}_{inSlot}"

    @property
    def base_object(self) -> str:
        return f"{self.root}/Mutable/CO_{CHARACTER}_{ROLE}_Base"


# ---------------------------------------------------------------------------
# 보조
# ---------------------------------------------------------------------------


def _pkg(inPath: str) -> str:
    return rules.to_package_path(inPath or "")


def _disk_fstrings(inPackagePath: str) -> List[str]:
    """저장된 `.uasset`의 길이접두 ASCII FString 목록.

    Args:
        inPackagePath: 패키지 경로

    Returns:
        문자열 목록
    """
    with open(mutableObjects.package_file_path(inPackagePath), "rb") as handle:
        data = handle.read()
    found = []
    index = 0
    while index < len(data) - 4:
        (length,) = struct.unpack_from("<i", data, index)
        end = index + 4 + length
        if 2 <= length <= 400 and end <= len(data) and data[end - 1] == 0:
            raw = data[index + 4:end - 1]
            if all(32 <= b < 127 for b in raw):
                found.append(raw.decode("ascii"))
                index = end
                continue
        index += 1
    return found


def _delete_co(inPackagePath: str) -> None:
    """테스트가 만든 CO 1개를 메모리·디스크에서 지운다(재생성 TC용).

    Args:
        inPackagePath: 패키지 경로
    """
    if unreal.EditorAssetLibrary.does_asset_exist(inPackagePath):
        unreal.EditorAssetLibrary.delete_asset(inPackagePath)
    filePath = mutableObjects.package_file_path(inPackagePath)
    if os.path.exists(filePath):
        os.chmod(filePath, 0o666)
        os.remove(filePath)
    # 같은 경로에 다시 복제하므로 지운 패키지가 메모리에 남지 않게 GC를 돌린다
    unreal.SystemLibrary.collect_garbage()
    assert not unreal.EditorAssetLibrary.does_asset_exist(inPackagePath), f"삭제 실패: {inPackagePath}"


def _cleanup_scratch(inScratchRoot: str) -> List[str]:
    """스크래치 폴더를 메모리·디스크에서 지운다.

    Args:
        inScratchRoot: 스크래치 패키지 폴더

    Returns:
        지우지 못하고 남은 디스크 파일 목록
    """
    if unreal.EditorAssetLibrary.does_directory_exist(inScratchRoot):
        unreal.EditorAssetLibrary.delete_directory(inScratchRoot)
    diskRoot = os.path.dirname(mutableObjects.package_file_path(f"{inScratchRoot}/x"))
    leftovers: List[str] = []
    if os.path.isdir(diskRoot):
        for current, _, files in os.walk(diskRoot, topdown=False):
            for fileName in files:
                filePath = os.path.join(current, fileName).replace("\\", "/")
                try:
                    os.chmod(filePath, 0o666)
                    os.remove(filePath)
                except OSError:
                    leftovers.append(filePath)
            try:
                os.rmdir(current)
            except OSError:
                pass
    return leftovers


class _UnrealSpy:
    """`mutableObjects`가 보는 `unreal`을 감싸 duplicate_asset / save_asset 호출을 센다.

    "드라이런은 복제도 저장도 하지 않는다"는 결과값으로는 증명되지 않는다 - 호출 0회를 센다.
    """

    def __init__(self, inReal):
        self._real = inReal
        self.duplicateCalls = 0
        self.saveCalls = 0
        spy = self

        class _EditorAssetLibrarySpy:
            @staticmethod
            def save_asset(*inArgs, **inKwargs):
                spy.saveCalls += 1
                return inReal.EditorAssetLibrary.save_asset(*inArgs, **inKwargs)

            @staticmethod
            def duplicate_asset(*inArgs, **inKwargs):
                spy.duplicateCalls += 1
                return inReal.EditorAssetLibrary.duplicate_asset(*inArgs, **inKwargs)

            def __getattr__(self, inName):
                return getattr(inReal.EditorAssetLibrary, inName)

        self.EditorAssetLibrary = _EditorAssetLibrarySpy()

    def __getattr__(self, inName):
        return getattr(self._real, inName)


def _slot_record(inResult: Dict, inOutfit: str, inSlot: str) -> Dict:
    matches = [s for s in inResult["slots"] if s["outfit"] == inOutfit and s["slot"] == inSlot]
    assert len(matches) == 1, f"{inOutfit}/{inSlot} 레코드 {len(matches)}개"
    return matches[0]


# ---------------------------------------------------------------------------
# 결과 단정 헬퍼 (판별력 TC가 변이 구현에 같은 헬퍼를 건다)
# ---------------------------------------------------------------------------


def _check_base(inCtx: _Ctx) -> Dict:
    """Base CO: Component 메쉬·이름·그룹이 계획대로이고 디스크에도 실렸는가."""
    base = unreal.EditorAssetLibrary.load_asset(inCtx.base_object)
    assert base is not None, "Base CO가 없다"
    components = mutableObjects.list_graph_nodes(base, mutableObjects.NODE_COMPONENT_MESH)
    meshes = sorted(_pkg(mutableObjects.node_value_path(n, mutableObjects.PROP_REFERENCE_MESH)) for n in components)
    assert meshes == sorted([inCtx.mesh("Default", "Body"), inCtx.mesh("Default", "Face")]), meshes
    text = mutableObjects.export_t3d_text(base)
    assert rules.read_t3d_property(text, "CustomizableObjectNodeObject", "ObjectName") == [f"{CHARACTER}_{ROLE}"]
    assert sorted(rules.read_t3d_property(text, "CustomizableObjectNodeComponentMesh", "ComponentName")) == ["Body", "Face"]
    groups = rules.parse_group_guids_t3d(text)
    assert all(len(v) == 1 for v in groups.values()) and len(groups) >= 2, groups
    disk = _disk_fstrings(inCtx.base_object)
    assert f"{CHARACTER}_{ROLE}" in disk, "디스크에 새 Base Object 이름이 없다"
    assert not any("Template_Sh" in s for s in disk), "디스크에 템플릿 이름이 남아 있다"
    return {"groups": groups}


def _check_slot(inCtx: _Ctx, inOutfit: str, inSlot: str, inExpectedParts: Dict[str, str]) -> Dict:
    """슬롯 CO: SK·매테리얼·Parent·그룹 GUID·이름이 맞는가.

    Args:
        inCtx: 컨텍스트
        inOutfit: 외형
        inSlot: 슬롯
        inExpectedParts: {부품: 기대 메쉬 경로} - SK 노드 집합과 같아야 한다

    Returns:
        상세
    """
    path = inCtx.slot_object(inOutfit, inSlot)
    co = unreal.EditorAssetLibrary.load_asset(path)
    assert co is not None, f"슬롯 CO가 없다: {path}"
    skNodes = mutableObjects.list_graph_nodes(co, mutableObjects.NODE_SKELETAL_MESH)
    meshes = sorted(_pkg(mutableObjects.node_value_path(n, mutableObjects.PROP_SKELETAL_MESH)) for n in skNodes)
    assert meshes == sorted(inExpectedParts.values()), meshes
    expectedMaterials = sorted(_pkg(mutableObjects.mesh_material_paths(m)[0]) for m in inExpectedParts.values())
    materialNodes = mutableObjects.list_graph_nodes(co, mutableObjects.NODE_MATERIAL)
    materials = sorted(_pkg(mutableObjects.node_value_path(n, mutableObjects.PROP_MATERIAL)) for n in materialNodes)
    assert materials == expectedMaterials, f"매테리얼 {materials} != {expectedMaterials}"
    objectNode = mutableObjects.list_graph_nodes(co, mutableObjects.NODE_OBJECT)[0]
    assert _pkg(mutableObjects.node_value_path(objectNode, mutableObjects.PROP_PARENT_OBJECT)) == inCtx.base_object
    baseGroups = mutableObjects.read_group_guids(unreal.EditorAssetLibrary.load_asset(inCtx.base_object))
    groupId = mutableObjects.guid_text(objectNode.get_editor_property(mutableObjects.PROP_PARENT_GROUP_ID))
    assert groupId == baseGroups[inSlot][0], f"그룹 GUID {groupId} != Base {inSlot} {baseGroups[inSlot]}"
    assert mutableObjects.read_object_names(co) == [inOutfit], "슬롯 Base Object 이름이 외형이 아니다"
    disk = _disk_fstrings(path)
    assert inOutfit in disk and f"{inSlot}Slot" not in disk, "디스크의 슬롯 이름이 갱신되지 않았다"
    return {"meshes": meshes, "materials": materials, "groupId": groupId}


# ---------------------------------------------------------------------------
# TC
# ---------------------------------------------------------------------------


def tc00_setup_and_load_source(inCtx: _Ctx) -> Dict:
    """로드 출처·소스 컨트롤 비활성·쓰기 무복사를 단정하고 캐릭터 트리 픽스처를 만든다."""
    worktreeSrc = os.path.dirname(os.path.dirname(_IN_UNREAL_DIR)).replace("\\", "/")
    adapterFile = mutableObjects.__file__.replace("\\", "/")
    rulesFile = rules.__file__.replace("\\", "/")
    assert adapterFile.startswith(worktreeSrc), f"어댑터 로드 출처가 이 트리가 아니다: {adapterFile}"
    assert rulesFile.startswith(worktreeSrc), f"규칙 모듈 로드 출처가 이 트리가 아니다: {rulesFile}"
    assert unreal.SourceControl.is_enabled() is False, "소스 컨트롤이 켜져 있다 - 저장이 P4에 닿을 수 있다"
    with open(_THIS_FILE, "r", encoding="utf-8") as selfFile:
        ownSource = selfFile.read()
    for forbidden in ("SetString" + "PropertyByName", "ObjectExporter" + "T3D", "set_editor" + "_property("):
        assert forbidden not in ownSource, f"쓰기 경로 복사본 {forbidden}이 있다"

    leftovers = _cleanup_scratch(inCtx.scratchRoot)
    assert not leftovers, f"이전 실행 잔여물을 지우지 못했다: {leftovers}"

    source = inCtx.config["sourceMeshes"]
    layout = {f"Default/{part}": source[f"Default/{part}"] for part in ("Body", "Face", "Hair") + FACE_PARTS}
    layout["BunHair/Hair"] = source["BunHair/Hair"]
    layout["NoParts/Face"] = source["Default/Face"]          # 부품 SK가 없는 Face 외형 (D-Q1)
    layout["BaseSkeleton/Face"] = source["Default/Face"]     # 제외 외형 (D-Q3)
    for key, sourcePath in layout.items():
        outfit, slot = key.split("/")
        destination = inCtx.mesh(outfit, slot)
        assert unreal.EditorAssetLibrary.duplicate_asset(sourcePath, destination) is not None, f"복제 실패: {key}"
        assert unreal.EditorAssetLibrary.save_asset(destination, only_if_is_dirty=False), f"저장 실패: {key}"
        inCtx.meshes[key] = destination
    outfitLevel = f"{inCtx.root}/MeshB/BunHair/SK_{CHARACTER}_{ROLE}_BunHair"  # 외형 직하 메쉬
    assert unreal.EditorAssetLibrary.duplicate_asset(source["BunHair/Hair"], outfitLevel) is not None
    assert unreal.EditorAssetLibrary.save_asset(outfitLevel, only_if_is_dirty=False)
    inCtx.meshes["outfitLevel"] = outfitLevel

    meshes, _ = mutableObjects.scan_character_assets(inCtx.root)
    assert sorted(meshes) == sorted(inCtx.meshes.values()), f"레지스트리 스캔 불일치: {meshes}"
    return {"adapterFile": adapterFile, "rulesFile": rulesFile, "meshes": inCtx.meshes}


def tc01_dry_run_changes_nothing(inCtx: _Ctx) -> Dict:
    """드라이런: 계획은 완전하고, 복제·저장 호출 0회, 대상 에셋 0건."""
    spy = _UnrealSpy(unreal)
    mutableObjects.unreal = spy
    try:
        builder = mutableObjects.MutableObjectBuilder(inCtx.buildConfig)
        result = builder.apply_plan(builder.build_plan(inCtx.root), inDryRun=True)
    finally:
        mutableObjects.unreal = unreal
    assert (spy.duplicateCalls, spy.saveCalls) == (0, 0), f"드라이런 호출: 복제 {spy.duplicateCalls} 저장 {spy.saveCalls}"
    assert result["base"]["status"] == rules.STATUS_PENDING, result["base"]
    assert len(result["base"]["componentBindings"]) == 2
    assert _slot_record(result, "BunHair", "Hair")["status"] == rules.STATUS_PENDING
    face = _slot_record(result, "Default", "Face")
    assert face["status"] == rules.STATUS_PENDING and len(face["meshBindings"]) == 5, face
    noParts = _slot_record(result, "NoParts", "Face")
    assert noParts["status"] == rules.FAILED_MISSING_PART_MESH, noParts
    assert result["noTemplateUnconsumed"] == [], result["noTemplateUnconsumed"]
    ignored = dict(map(tuple, result["ignored"]))
    assert ignored[inCtx.meshes["BaseSkeleton/Face"]] == rules.IGNORED_EXCLUDED_OUTFIT
    assert ignored[inCtx.meshes["outfitLevel"]] == rules.IGNORED_NOT_SLOT_MESH
    targets = [inCtx.base_object] + [s["assetPath"] for s in result["slots"]]
    assert not any(unreal.EditorAssetLibrary.does_asset_exist(t) for t in targets), "드라이런이 에셋을 만들었다"
    return {"statusCounts": result["statusCounts"]}


def tc02_apply_creates_base(inCtx: _Ctx) -> Dict:
    """실집행: Base + 슬롯 생성. Base의 Component·이름·그룹·디스크를 단정한다."""
    builder = mutableObjects.MutableObjectBuilder(inCtx.buildConfig)
    result = builder.apply_plan(builder.build_plan(inCtx.root), inDryRun=False)
    inCtx.lastResult = result
    assert result["base"]["status"] == rules.STATUS_CREATED, result["base"]
    details = _check_base(inCtx)
    details["statusCounts"] = result["statusCounts"]
    details["savedPaths"] = result["savedPaths"]
    return details


def tc03_single_slot_matches_sample(inCtx: _Ctx) -> Dict:
    """단일 SK 슬롯(BunHair/Hair): 계획대로이고, 수작업 표본과 매테리얼·이름 규칙이 같다."""
    record = _slot_record(inCtx.lastResult, "BunHair", "Hair")
    assert record["status"] == rules.STATUS_CREATED, record
    details = _check_slot(inCtx, "BunHair", "Hair", {"Hair": inCtx.meshes["BunHair/Hair"]})
    sample = unreal.EditorAssetLibrary.load_asset(inCtx.config["sampleSlot"])
    sampleMaterial = [
        _pkg(mutableObjects.node_value_path(n, mutableObjects.PROP_MATERIAL))
        for n in mutableObjects.list_graph_nodes(sample, mutableObjects.NODE_MATERIAL)
    ]
    assert details["materials"] == sampleMaterial, f"표본 매테리얼 {sampleMaterial}"
    assert mutableObjects.read_object_names(sample) == ["BunHair"], "표본 이름 규칙이 D-Q2와 다르다"
    details["sampleMaterial"] = sampleMaterial
    return details


def tc04_face_slot_binds_parts(inCtx: _Ctx) -> Dict:
    """다중 SK 슬롯(Default/Face): 5개 SK 노드가 같은 외형 부품 메쉬로, 매테리얼도 각각."""
    assert _slot_record(inCtx.lastResult, "Default", "Face")["status"] == rules.STATUS_CREATED
    parts = {part: inCtx.meshes[f"Default/{part}"] for part in ("Face",) + FACE_PARTS}
    return _check_slot(inCtx, "Default", "Face", parts)


def tc05_missing_parts_create_nothing(inCtx: _Ctx) -> Dict:
    """D-Q1: 부품 SK가 없는 Face는 실패로 남고 에셋이 생기지 않는다. 단일 슬롯도 함께 확인."""
    record = _slot_record(inCtx.lastResult, "NoParts", "Face")
    assert record["status"] == rules.FAILED_MISSING_PART_MESH, record
    target = inCtx.slot_object("NoParts", "Face")
    assert not unreal.EditorAssetLibrary.does_asset_exist(target)
    assert not os.path.exists(mutableObjects.package_file_path(target))
    for slot in ("Body", "Hair"):
        assert _slot_record(inCtx.lastResult, "Default", slot)["status"] == rules.STATUS_CREATED
        _check_slot(inCtx, "Default", slot, {slot: inCtx.meshes[f"Default/{slot}"]})
    return {"detail": record["detail"]}


def tc06_idempotent_skip(inCtx: _Ctx) -> Dict:
    """재실행: 전부 skipped:exists(실패 1건 제외)이고 저장 0건."""
    builder = mutableObjects.MutableObjectBuilder(inCtx.buildConfig)
    result = builder.apply_plan(builder.build_plan(inCtx.root), inDryRun=False)
    assert result["base"]["status"] == rules.STATUS_SKIPPED_EXISTS
    assert result["savedPaths"] == [], result["savedPaths"]
    statuses = {(s["outfit"], s["slot"]): s["status"] for s in result["slots"]}
    assert statuses.pop(("NoParts", "Face")) == rules.FAILED_MISSING_PART_MESH
    assert set(statuses.values()) == {rules.STATUS_SKIPPED_EXISTS}, statuses
    return {"statusCounts": result["statusCounts"]}


def tc07_existing_base_reused(inCtx: _Ctx) -> Dict:
    """D-Q4: 슬롯만 지우고 재실행하면 기존 Base(T3D로 읽은 그룹 GUID)에 다시 붙는다."""
    _delete_co(inCtx.slot_object("BunHair", "Hair"))
    builder = mutableObjects.MutableObjectBuilder(inCtx.buildConfig)
    plan = builder.build_plan(inCtx.root)
    hair = [s for s in plan.slots if (s.outfit, s.slot) == ("BunHair", "Hair")][0]
    assert plan.base.status == rules.STATUS_SKIPPED_EXISTS and hair.status == rules.STATUS_PENDING
    assert hair.groupGuid, "기존 Base에서 그룹 GUID를 계획 단계에 읽지 못했다"
    result = builder.apply_plan(plan, inDryRun=False)
    assert result["savedPaths"] == [inCtx.slot_object("BunHair", "Hair")], result["savedPaths"]
    return _check_slot(inCtx, "BunHair", "Hair", {"Hair": inCtx.meshes["BunHair/Hair"]})


def _recreate_with(inCtx: _Ctx, inAttr: str, inMutant) -> Dict:
    """BunHair/Hair를 지우고 어댑터 함수 하나를 변이로 바꿔 다시 만든다.

    Args:
        inCtx: 컨텍스트
        inAttr: 바꿀 `mutableObjects` 함수 이름
        inMutant: 변이 함수

    Returns:
        apply 결과
    """
    _delete_co(inCtx.slot_object("BunHair", "Hair"))
    original = getattr(mutableObjects, inAttr)
    setattr(mutableObjects, inAttr, inMutant)
    try:
        builder = mutableObjects.MutableObjectBuilder(inCtx.buildConfig)
        return builder.apply_plan(builder.build_plan(inCtx.root), inDryRun=False)
    finally:
        setattr(mutableObjects, inAttr, original)


def tc08_discriminating_mutants(inCtx: _Ctx) -> Dict:
    """판별력: 그룹 GUID 미기록 / 매테리얼 미기록 변이는 `_check_slot`이 잡고, 이름 미기록 변이는
    어댑터 자신의 T3D 검증이 잡아 저장하지 않는다."""
    expected = {"Hair": inCtx.meshes["BunHair/Hair"]}
    details: Dict = {}

    original_asset_write = mutableObjects.set_node_asset_verified

    def _skip_material(inNode, inPropName, inAsset):
        if inPropName == mutableObjects.PROP_MATERIAL:
            return True
        return original_asset_write(inNode, inPropName, inAsset)

    for label, attr, mutant in (
        ("groupNotWritten", "set_group_id_verified", lambda inNode, inGuid: True),
        ("materialNotWritten", "set_node_asset_verified", _skip_material),
    ):
        result = _recreate_with(inCtx, attr, mutant)
        assert _slot_record(result, "BunHair", "Hair")["status"] == rules.STATUS_CREATED, f"{label}: 변이도 생성은 된다"
        try:
            _check_slot(inCtx, "BunHair", "Hair", expected)
        except AssertionError as caught:
            details[label] = f"caught: {caught}"
        else:
            raise AssertionError(f"{label} 변이를 _check_slot이 잡지 못했다")

    result = _recreate_with(inCtx, "write_object_name", lambda inNode, inName: None)
    record = _slot_record(result, "BunHair", "Hair")
    assert record["status"] == rules.FAILED_WRITE_NOT_VERIFIED, record
    assert not unreal.EditorAssetLibrary.does_asset_exist(inCtx.slot_object("BunHair", "Hair")), "검증 실패인데 남았다"
    details["nameNotWritten"] = record["detail"]

    # 원 구현으로 돌아와 같은 대상이 다시 정상 생성되는지(변이가 상태를 오염시키지 않았는지)
    builder = mutableObjects.MutableObjectBuilder(inCtx.buildConfig)
    builder.apply_plan(builder.build_plan(inCtx.root), inDryRun=False)
    _check_slot(inCtx, "BunHair", "Hair", expected)
    return details


TESTS: List[Callable[[_Ctx], Dict]] = [
    tc00_setup_and_load_source,
    tc01_dry_run_changes_nothing,
    tc02_apply_creates_base,
    tc03_single_slot_matches_sample,
    tc04_face_slot_binds_parts,
    tc05_missing_parts_create_nothing,
    tc06_idempotent_skip,
    tc07_existing_base_reused,
    tc08_discriminating_mutants,
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
