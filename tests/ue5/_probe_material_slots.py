#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Phase 0 실태 확정 프로브 - 매테리얼 슬롯 (UE5 임베디드 파이썬 전용).

UE5 기동이 회차당 20~30초라 미확정 5개를 **한 실행**에 몰아 넣는다. 섹션은 예외로
서로를 죽이지 않게 격리하고, 결과는 항상 JSON으로 남긴다. 실패 섹션만 `onlySections`로
재실행할 수 있다(`.claude/references/ue5/silent_write_paths.md` §6).

섹션 (상태 변경 여부는 섹션 단위로 표시한다):
    1. staticMeshShape   [읽기]  StaticMesh 슬롯 배열 프로퍼티 실명·원소 타입·슬롯 이름 프로퍼티 + dir 덤프
    2. staticMeshWrite   [쓰기·옵트인]  사본만 / 3단 / 배열 재구성 3형태 비교 (복제본, 저장 안 함)
    3. skeletalMeshRecheck [메모리 쓰기] SkeletalMesh 3단 쓰기의 현행 유효성 1건 (복제본, 저장 안 함)
    4. meshTypeDispatch  [읽기]  isinstance vs get_class().get_name() 판별 축
    5. sideEffects       [메모리 쓰기] StaticMesh 슬롯 1개 변경 시 개수·순서·참조·LOD 보존 (복제본)

**쓰기는 전부 `scratchRoot` 아래의 메모리 복제본에서만 한다.** 원본(프로덕션 정본)은
로드·읽기만 한다. `save_asset`은 어느 섹션도 호출하지 않는다 - 호출 자체가 default CL
체크아웃 + 저장이다.

Phase 0에는 라이브러리 쓰기 헬퍼가 아직 없다. 섹션 2는 어느 경로가 먹는지를 *가르는*
탐색이므로 헬퍼가 될 수 없고, 그래서 이 프로브는 자기 쓰기 코드를 갖는다. Phase 2에서
헬퍼가 생긴 뒤로는 Type C 스크립트가 라이브러리 헬퍼만 import한다.

설정은 환경변수 `PYJAL_UE5_TEST_CONFIG`가 가리키는 JSON에서 읽는다.
"""

import json
import os
import sys
import traceback
from typing import Callable, Dict, List, Optional

sys.dont_write_bytecode = True

import unreal  # noqa: E402

CONFIG_ENV = "PYJAL_UE5_TEST_CONFIG"
LOG_PREFIX = "[MatSlotProbe]"
PROBE_NAME = "__PyJalProbeSlotName__"

WRITE_SECTIONS = ("staticMeshWrite",)
"""상태를 바꾸는 섹션. `onlySections`에 명시해야만 돈다."""

ALL_SECTIONS = (
    "staticMeshShape",
    "staticMeshWrite",
    "skeletalMeshRecheck",
    "meshTypeDispatch",
    "sideEffects",
)


def _log(inMessage: str) -> None:
    """엔진 로그에 정보 메시지를 남긴다.

    Args:
        inMessage: 메시지
    """
    unreal.log(f"{LOG_PREFIX} {inMessage}")


def _log_error(inMessage: str) -> None:
    """엔진 로그에 에러 메시지를 남긴다.

    Args:
        inMessage: 메시지
    """
    unreal.log_error(f"{LOG_PREFIX} {inMessage}")


def _err(inError: Exception) -> str:
    """예외를 결과 JSON용 문자열로 접는다.

    Args:
        inError: 예외

    Returns:
        `타입: 메시지`
    """
    return f"{type(inError).__name__}: {inError}"


def _public_members(inObj, inKeyword: str = "") -> List[str]:
    """공개 멤버 이름 목록을 만든다(dir 덤프).

    Args:
        inObj: 대상 객체
        inKeyword: 소문자 포함 필터. 빈 문자열이면 전부.

    Returns:
        정렬된 멤버 이름 리스트
    """
    return sorted(
        name for name in dir(inObj)
        if not name.startswith("_") and inKeyword in name.lower()
    )


def _package_to_file(inPackagePath: str) -> str:
    """`/Game/X` 패키지 경로를 로컬 `.uasset` 절대 경로로 바꾼다.

    Args:
        inPackagePath: `/Game/...` 패키지 경로

    Returns:
        `.uasset` 절대 경로(정방향 슬래시)
    """
    contentDir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    relative = inPackagePath[len("/Game/"):]
    return (contentDir.rstrip("/") + "/" + relative + ".uasset").replace("\\", "/")


# ---------------------------------------------------------------------------
# 복제본 관리 - 쓰기 섹션은 원본이 아니라 이것만 만진다
# ---------------------------------------------------------------------------

_duplicates: Dict[str, object] = {}


def _get_duplicate(inSourcePath: str, inScratchRoot: str):
    """원본 에셋의 메모리 복제본을 만든다(같은 실행 안에서 재사용).

    Args:
        inSourcePath: 원본 패키지 경로
        inScratchRoot: 복제본을 둘 패키지 폴더

    Returns:
        복제된 에셋 객체

    Raises:
        RuntimeError: 복제 실패
    """
    if inSourcePath in _duplicates:
        return _duplicates[inSourcePath]
    assetName = inSourcePath.rsplit("/", 1)[-1]
    destination = f"{inScratchRoot}/{assetName}"
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(inSourcePath, destination)
    if duplicated is None:
        raise RuntimeError(f"복제 실패: {inSourcePath} -> {destination}")
    _duplicates[inSourcePath] = duplicated
    return duplicated


# ---------------------------------------------------------------------------
# 읽기 헬퍼 (프로퍼티 이름은 인자로 받는다 - 추정을 코드에 박지 않는다)
# ---------------------------------------------------------------------------


def _slot_field(inSlot, inFieldName: str) -> str:
    """슬롯 구조체의 필드를 문자열로 읽는다(실패는 마커 문자열).

    Args:
        inSlot: 슬롯 구조체
        inFieldName: 필드 이름

    Returns:
        필드 값 문자열 또는 `<error: ...>`
    """
    try:
        value = inSlot.get_editor_property(inFieldName)
    except Exception as readError:  # noqa: BLE001 - 노출 여부 자체가 관측 대상이다
        return f"<error: {_err(readError)}>"
    if value is None:
        return ""
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    return str(value)


def _read_slots(inMesh, inArrayProp: str) -> List[Dict]:
    """메쉬의 슬롯 배열을 필드별로 읽는다.

    Args:
        inMesh: 메쉬
        inArrayProp: 슬롯 배열 프로퍼티 이름

    Returns:
        슬롯별 `{slotName, importedSlotName, material}` 리스트
    """
    slots = inMesh.get_editor_property(inArrayProp)
    return [
        {
            "slotName": _slot_field(slot, "material_slot_name"),
            "importedSlotName": _slot_field(slot, "imported_material_slot_name"),
            "material": _slot_field(slot, "material_interface"),
        }
        for slot in slots
    ]


def _slot_names(inMesh, inArrayProp: str) -> List[str]:
    """슬롯 이름만 순서대로 읽는다.

    Args:
        inMesh: 메쉬
        inArrayProp: 슬롯 배열 프로퍼티 이름

    Returns:
        슬롯 이름 리스트
    """
    return [slot["slotName"] for slot in _read_slots(inMesh, inArrayProp)]


def _write_three_stage(inMesh, inArrayProp: str, inIndex: int, inName: str) -> None:
    """3단 쓰기(사본 수정 -> 배열 대입 -> 프로퍼티 대입). 프로브 전용 탐색 코드.

    Args:
        inMesh: 메쉬
        inArrayProp: 슬롯 배열 프로퍼티 이름
        inIndex: 슬롯 인덱스
        inName: 새 슬롯 이름
    """
    slots = inMesh.get_editor_property(inArrayProp)
    slot = slots[inIndex]
    slot.set_editor_property("material_slot_name", inName)
    slots[inIndex] = slot
    inMesh.set_editor_property(inArrayProp, slots)


def _lod_count(inMesh) -> Dict:
    """LOD 개수를 가능한 모든 경로로 읽는다(어느 경로가 노출되는지가 관측 대상).

    Args:
        inMesh: 메쉬

    Returns:
        경로별 결과 dict
    """
    result: Dict = {}
    if hasattr(inMesh, "get_num_lods"):
        try:
            result["get_num_lods"] = int(inMesh.get_num_lods())
        except Exception as lodError:  # noqa: BLE001
            result["get_num_lods"] = f"<error: {_err(lodError)}>"
    for subsystemName in ("StaticMeshEditorSubsystem", "SkeletalMeshEditorSubsystem"):
        subsystemClass = getattr(unreal, subsystemName, None)
        if subsystemClass is None:
            continue
        try:
            subsystem = unreal.get_editor_subsystem(subsystemClass)
            result[subsystemName] = int(subsystem.get_lod_count(inMesh))
        except Exception as lodError:  # noqa: BLE001
            result[subsystemName] = f"<error: {_err(lodError)}>"
    return result


def _find_static_array_prop(inMesh) -> str:
    """StaticMesh에서 슬롯 배열로 읽히는 프로퍼티 이름을 실측으로 찾는다.

    Args:
        inMesh: StaticMesh

    Returns:
        읽히는 첫 후보 이름

    Raises:
        RuntimeError: 후보가 하나도 읽히지 않음
    """
    for candidate in ("static_materials", "materials"):
        try:
            inMesh.get_editor_property(candidate)
            return candidate
        except Exception:  # noqa: BLE001 - 다음 후보로
            continue
    raise RuntimeError("StaticMesh 슬롯 배열 프로퍼티 후보가 모두 읽히지 않는다")


# ---------------------------------------------------------------------------
# 섹션
# ---------------------------------------------------------------------------


def section_static_mesh_shape(inConfig: Dict) -> Dict:
    """섹션 1 [읽기]: StaticMesh 슬롯 배열의 실제 노출 형태를 덤프한다.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    perAsset: List[Dict] = []
    for packagePath in inConfig["staticCandidates"]:
        entry: Dict = {"packagePath": packagePath}
        perAsset.append(entry)
        asset = unreal.load_asset(packagePath)
        if asset is None:
            entry["error"] = "loadReturnedNone"
            continue
        entry["className"] = asset.get_class().get_name()
        if not isinstance(asset, unreal.StaticMesh):
            entry["error"] = "notStaticMesh"
            continue

        entry["materialMembers"] = _public_members(asset, "material")
        entry["lodMembers"] = _public_members(asset, "lod")
        propertyProbe: Dict = {}
        for candidate in ("static_materials", "materials"):
            try:
                array = asset.get_editor_property(candidate)
            except Exception as propError:  # noqa: BLE001 - 노출 여부가 관측 대상이다
                propertyProbe[candidate] = {"readable": False, "error": _err(propError)}
                continue
            probeEntry: Dict = {
                "readable": True,
                "arrayType": type(array).__name__,
                "length": len(array),
            }
            if len(array) > 0:
                element = array[0]
                probeEntry["elementType"] = type(element).__name__
                probeEntry["elementMembers"] = _public_members(element)
            propertyProbe[candidate] = probeEntry
        entry["propertyProbe"] = propertyProbe

        try:
            arrayProp = _find_static_array_prop(asset)
            entry["arrayProp"] = arrayProp
            entry["slots"] = _read_slots(asset, arrayProp)
        except Exception as readError:  # noqa: BLE001
            entry["slotsError"] = _err(readError)
        entry["lodCount"] = _lod_count(asset)

    staticEntries = [item for item in perAsset if "arrayProp" in item]
    return {
        "succeeded": bool(staticEntries),
        "staticMeshCount": len(staticEntries),
        "arrayPropsFound": sorted({item["arrayProp"] for item in staticEntries}),
        "staticMaterialClassExists": hasattr(unreal, "StaticMaterial"),
        "perAsset": perAsset,
    }


def _pick_static_source(inConfig: Dict) -> str:
    """쓰기 섹션이 쓸 StaticMesh 원본을 고른다(슬롯이 가장 많은 것).

    Args:
        inConfig: 프로브 설정

    Returns:
        원본 패키지 경로

    Raises:
        RuntimeError: StaticMesh 후보가 없음
    """
    best = ""
    bestCount = -1
    for packagePath in inConfig["staticCandidates"]:
        asset = unreal.load_asset(packagePath)
        if asset is None or not isinstance(asset, unreal.StaticMesh):
            continue
        try:
            count = len(asset.get_editor_property(_find_static_array_prop(asset)))
        except Exception:  # noqa: BLE001
            continue
        if count > bestCount:
            best, bestCount = packagePath, count
    if not best:
        raise RuntimeError("StaticMesh 후보가 없다")
    return best


def _compare_write_paths(inMesh, inArrayProp: str, inStructClassName: str) -> Dict:
    """사본만 / 3단 / 배열 재구성 3형태를 같은 메쉬에서 비교한다(각 형태 뒤 원복).

    Args:
        inMesh: 복제본 메쉬
        inArrayProp: 슬롯 배열 프로퍼티 이름
        inStructClassName: 재구성에 쓸 구조체 클래스 이름(`StaticMaterial` 등)

    Returns:
        형태별 결과
    """
    result: Dict = {"arrayProp": inArrayProp}
    original = _read_slots(inMesh, inArrayProp)
    originalName = original[0]["slotName"]
    result["originalSlots"] = original

    def _restore(inKey: str) -> None:
        try:
            _write_three_stage(inMesh, inArrayProp, 0, originalName)
            result[f"{inKey}Restored"] = _slot_names(inMesh, inArrayProp)[0] == originalName
        except Exception as restoreError:  # noqa: BLE001 - 원복 실패는 반드시 드러나야 한다
            result[f"{inKey}Restored"] = False
            result[f"{inKey}RestoreError"] = _err(restoreError)

    # 형태 A: 사본만 수정
    try:
        slots = inMesh.get_editor_property(inArrayProp)
        slot = slots[0]
        returned = slot.set_editor_property("material_slot_name", PROBE_NAME)
        result["copyOnly"] = {
            "setReturned": repr(returned),
            "copyTook": _slot_field(slot, "material_slot_name") == PROBE_NAME,
            "arrayElementTook": _slot_field(slots[0], "material_slot_name") == PROBE_NAME,
            "meshTook": _slot_names(inMesh, inArrayProp)[0] == PROBE_NAME,
        }
    except Exception as copyError:  # noqa: BLE001
        result["copyOnly"] = {"error": _err(copyError)}
    _restore("copyOnly")

    # 형태 B: 3단
    try:
        _write_three_stage(inMesh, inArrayProp, 0, PROBE_NAME)
        after = _read_slots(inMesh, inArrayProp)
        threeStage: Dict = {
            "meshTook": after[0]["slotName"] == PROBE_NAME,
            "importedNameAfter": after[0]["importedSlotName"],
            "materialPreserved": after[0]["material"] == original[0]["material"],
        }
        if hasattr(inMesh, "get_material_index"):
            threeStage["getMaterialIndexOfNewName"] = int(inMesh.get_material_index(PROBE_NAME))
        result["threeStage"] = threeStage
    except Exception as threeError:  # noqa: BLE001
        result["threeStage"] = {"error": _err(threeError)}
    _restore("threeStage")

    # 형태 C: 새 구조체로 배열 재구성
    try:
        structClass = getattr(unreal, inStructClassName)
        slots = inMesh.get_editor_property(inArrayProp)
        rebuilt = []
        for index, slot in enumerate(slots):
            newSlot = structClass()
            newSlot.set_editor_property(
                "material_interface", slot.get_editor_property("material_interface")
            )
            newSlot.set_editor_property(
                "material_slot_name",
                PROBE_NAME if index == 0 else slot.get_editor_property("material_slot_name"),
            )
            rebuilt.append(newSlot)
        inMesh.set_editor_property(inArrayProp, rebuilt)
        after = _read_slots(inMesh, inArrayProp)
        result["rebuild"] = {
            "meshTook": after[0]["slotName"] == PROBE_NAME,
            "materialPreserved": after[0]["material"] == original[0]["material"],
            # 재구성은 imported 이름 등 옮기지 않은 필드를 잃는다 - 채택하지 않는 근거
            "importedNameAfter": after[0]["importedSlotName"],
            "importedNamePreserved": after[0]["importedSlotName"] == original[0]["importedSlotName"],
        }
    except Exception as rebuildError:  # noqa: BLE001
        result["rebuild"] = {"error": _err(rebuildError)}
    # 재구성은 imported 이름을 잃었을 수 있으므로 원본 슬롯 전체로 되돌린다
    try:
        slots = inMesh.get_editor_property(inArrayProp)
        for index, slot in enumerate(slots):
            slot.set_editor_property("material_slot_name", original[index]["slotName"])
            if original[index]["importedSlotName"] and not original[index]["importedSlotName"].startswith("<error"):
                slot.set_editor_property("imported_material_slot_name", original[index]["importedSlotName"])
            slots[index] = slot
        inMesh.set_editor_property(inArrayProp, slots)
        result["rebuildRestored"] = _read_slots(inMesh, inArrayProp) == original
    except Exception as restoreError:  # noqa: BLE001
        result["rebuildRestored"] = False
        result["rebuildRestoreError"] = _err(restoreError)
    return result


def section_static_mesh_write(inConfig: Dict) -> Dict:
    """섹션 2 [쓰기·옵트인]: StaticMesh에서 3형태 쓰기를 비교한다(복제본, 저장 안 함).

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    sourcePath = _pick_static_source(inConfig)
    mesh = _get_duplicate(sourcePath, inConfig["scratchRoot"])
    arrayProp = _find_static_array_prop(mesh)
    result = _compare_write_paths(mesh, arrayProp, "StaticMaterial")
    result["sourcePath"] = sourcePath
    result["duplicatePath"] = mesh.get_path_name()
    result["succeeded"] = True
    return result


def section_skeletal_mesh_recheck(inConfig: Dict) -> Dict:
    """섹션 3: SkeletalMesh 3단 쓰기가 현행 엔진에서도 성립하는지 1건 재확인한다.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    sourcePath = inConfig["skeletalSource"]
    mesh = _get_duplicate(sourcePath, inConfig["scratchRoot"])
    if not isinstance(mesh, unreal.SkeletalMesh):
        return {"succeeded": False, "error": f"notSkeletalMesh: {mesh.get_class().get_name()}"}
    result = _compare_write_paths(mesh, "materials", "SkeletalMaterial")
    result["sourcePath"] = sourcePath
    result["duplicatePath"] = mesh.get_path_name()
    result["lodCount"] = _lod_count(mesh)
    result["succeeded"] = True
    return result


def section_mesh_type_dispatch(inConfig: Dict) -> Dict:
    """섹션 4 [읽기]: 메쉬 타입 판별 축(isinstance vs 클래스 이름)을 실측한다.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    paths = [inConfig["skeletalSource"], *inConfig["staticCandidates"]]
    perAsset: List[Dict] = []
    materialPath = ""
    for packagePath in paths:
        asset = unreal.load_asset(packagePath)
        if asset is None:
            perAsset.append({"packagePath": packagePath, "error": "loadReturnedNone"})
            continue
        perAsset.append({
            "packagePath": packagePath,
            "className": asset.get_class().get_name(),
            "pythonType": type(asset).__name__,
            "isSkeletalMesh": isinstance(asset, unreal.SkeletalMesh),
            "isStaticMesh": isinstance(asset, unreal.StaticMesh),
        })
        if not materialPath and isinstance(asset, unreal.StaticMesh):
            try:
                firstMaterial = asset.get_material(0)
                materialPath = firstMaterial.get_path_name() if firstMaterial else ""
            except Exception:  # noqa: BLE001
                materialPath = ""

    # 메쉬가 아닌 에셋이 어느 쪽에도 걸리지 않는지 (notMesh 사유코드의 근거)
    nonMesh: Dict = {"packagePath": materialPath}
    if materialPath:
        nonMeshAsset = unreal.load_asset(materialPath.split(".")[0])
        if nonMeshAsset is not None:
            nonMesh.update({
                "className": nonMeshAsset.get_class().get_name(),
                "isSkeletalMesh": isinstance(nonMeshAsset, unreal.SkeletalMesh),
                "isStaticMesh": isinstance(nonMeshAsset, unreal.StaticMesh),
            })

    return {
        "succeeded": True,
        "skeletalIsSubclassOfStatic": issubclass(unreal.SkeletalMesh, unreal.StaticMesh),
        "staticIsSubclassOfSkeletal": issubclass(unreal.StaticMesh, unreal.SkeletalMesh),
        "perAsset": perAsset,
        "nonMesh": nonMesh,
    }


def section_side_effects(inConfig: Dict) -> Dict:
    """섹션 5: StaticMesh 슬롯 1개 변경 시 부수 영향을 확인한다(복제본, 저장 안 함).

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    sourcePath = _pick_static_source(inConfig)
    mesh = _get_duplicate(sourcePath, inConfig["scratchRoot"])
    arrayProp = _find_static_array_prop(mesh)
    before = _read_slots(mesh, arrayProp)
    beforeLod = _lod_count(mesh)
    result: Dict = {"sourcePath": sourcePath, "arrayProp": arrayProp, "before": before}
    try:
        _write_three_stage(mesh, arrayProp, 0, PROBE_NAME)
        after = _read_slots(mesh, arrayProp)
        result.update({
            "after": after,
            "slotCountPreserved": len(after) == len(before),
            "onlyTargetSlotChanged": after[1:] == before[1:],
            "materialRefsPreserved": [s["material"] for s in after] == [s["material"] for s in before],
            "importedNamesPreserved": (
                [s["importedSlotName"] for s in after] == [s["importedSlotName"] for s in before]
            ),
            "lodCountBefore": beforeLod,
            "lodCountAfter": _lod_count(mesh),
        })
        result["lodCountPreserved"] = result["lodCountBefore"] == result["lodCountAfter"]
    finally:
        try:
            _write_three_stage(mesh, arrayProp, 0, before[0]["slotName"])
            result["restored"] = _read_slots(mesh, arrayProp) == before
        except Exception as restoreError:  # noqa: BLE001
            result["restored"] = False
            result["restoreError"] = _err(restoreError)
    result["succeeded"] = True
    return result


SECTIONS: Dict[str, Callable[[Dict], Dict]] = {
    "staticMeshShape": section_static_mesh_shape,
    "staticMeshWrite": section_static_mesh_write,
    "skeletalMeshRecheck": section_skeletal_mesh_recheck,
    "meshTypeDispatch": section_mesh_type_dispatch,
    "sideEffects": section_side_effects,
}


def _run_section(inName: str, inConfig: Dict) -> Dict:
    """섹션 하나를 격리 실행한다(예외는 결과로 흡수).

    Args:
        inName: 섹션 이름
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    _log(f"섹션 시작: {inName}")
    try:
        sectionResult = SECTIONS[inName](inConfig)
    except Exception as sectionError:  # noqa: BLE001 - 섹션 격리가 목적이다
        _log_error(f"섹션 예외: {inName} - {sectionError}")
        return {"succeeded": False, "error": _err(sectionError), "traceback": traceback.format_exc()}
    _log(f"섹션 완료: {inName} (succeeded={sectionResult.get('succeeded')})")
    return sectionResult


def _selected_sections(inOnlySections: List[str]) -> List[str]:
    """실행할 섹션을 고른다. 쓰기 섹션은 명시 지정 시에만 포함한다.

    Args:
        inOnlySections: 설정의 `onlySections`

    Returns:
        실행할 섹션 이름 리스트
    """
    if inOnlySections:
        return [name for name in ALL_SECTIONS if name in inOnlySections]
    return [name for name in ALL_SECTIONS if name not in WRITE_SECTIONS]


def _environment_facts(inConfig: Dict) -> Dict:
    """실행 환경 사실(소스 컨트롤 상태, 복제본의 디스크 존재 여부)을 모은다.

    Args:
        inConfig: 프로브 설정

    Returns:
        환경 사실 dict
    """
    facts: Dict = {"engineVersion": unreal.SystemLibrary.get_engine_version()}
    try:
        facts["sourceControlEnabled"] = bool(unreal.SourceControl.is_enabled())
    except Exception as scError:  # noqa: BLE001
        facts["sourceControlEnabled"] = f"<error: {_err(scError)}>"
    duplicateFiles = {}
    for sourcePath in _duplicates:
        assetName = sourcePath.rsplit("/", 1)[-1]
        filePath = _package_to_file(f"{inConfig['scratchRoot']}/{assetName}")
        duplicateFiles[filePath] = os.path.exists(filePath)
    # 메모리 복제본은 저장하지 않으므로 디스크에 하나도 없어야 한다
    facts["duplicateFilesOnDisk"] = duplicateFiles
    facts["anyDuplicateOnDisk"] = any(duplicateFiles.values())
    return facts


def main() -> None:
    """프로브를 실행하고 결과 JSON을 쓴다."""
    result: Dict = {"success": False, "sections": {}}
    outputJsonPath: Optional[str] = None
    try:
        configPath = os.environ.get(CONFIG_ENV, "")
        with open(configPath, "r", encoding="utf-8") as configFile:
            config = json.load(configFile)
        outputJsonPath = config["outputJsonPath"]
        result["config"] = config
        selected = _selected_sections(config.get("onlySections", []))
        result["selectedSections"] = selected
        for name in selected:
            result["sections"][name] = _run_section(name, config)
        result["environment"] = _environment_facts(config)
        result["success"] = bool(selected) and all(
            section.get("succeeded", False) for section in result["sections"].values()
        )
    except Exception as fatalError:  # noqa: BLE001 - 결과 JSON은 어떤 경우에도 남긴다
        _log_error(f"프로브 치명적 실패: {fatalError}")
        result["error"] = _err(fatalError)
        result["traceback"] = traceback.format_exc()

    if outputJsonPath:
        os.makedirs(os.path.dirname(outputJsonPath), exist_ok=True)
        with open(outputJsonPath, "w", encoding="utf-8") as outputFile:
            json.dump(result, outputFile, ensure_ascii=False, indent=2)
        _log(f"결과 JSON 기록: {outputJsonPath}")
    else:
        _log_error("결과 JSON 경로를 알 수 없어 기록하지 못했다")


main()
