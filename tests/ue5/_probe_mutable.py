#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Phase 0 실태 확정 프로브 - Mutable Customizable Object (UE5 임베디드 파이썬 전용).

UE5 기동이 회차당 20~30초라 미확정 8개를 **한 실행**에 몰아 넣는다. 섹션은 예외로
서로를 죽이지 않게 격리하고, 결과는 항상 JSON으로 남긴다. 실패 섹션만 `onlySections`로
재실행할 수 있다(`.claude/references/ue5/silent_write_paths.md` §6).

섹션 (상태 변경 여부는 섹션 단위로 표시한다):
    1. environment      [읽기]  Mutable 클래스 노출·템플릿/표본 로드·SCC 상태
    2. nodeEnum         [읽기]  그래프 노드 열거 경로 비교 + 소요 시간 + 노드 속성 전수 덤프
    3. propAccess       [읽기]  PRD §3.1 속성별 읽기 가능 여부(예측 대조)
    4. groupGuid        [읽기]  템플릿 슬롯 vs 수작업 표본 슬롯의 parent_object_group_id
    5. duplicateWrite   [쓰기·옵트인]  메모리 복제본에 메쉬·이름·매테리얼·Parent 쓰기 + 되읽기
    6. groupFallback    [쓰기·옵트인]  NewCustomizableObject 임시 CO로 그룹 GUID 획득
    7. verifyMeans      [쓰기·옵트인]  복제본 저장 후 바이트 판정 + 컴파일 상태 (끝나면 삭제)
    8. materialIndex    [읽기]  플레이스홀더 MI <-> SK 매테리얼 인덱스 매핑 vs 표본

**쓰기는 전부 `scratchRoot` 아래의 복제본에서만 한다.** 원본(템플릿·SK·표본)은
로드·읽기만 하고 저장하지 않는다. 헤드레스는 `-SCCProvider=None`으로 뜬다.

Phase 0에는 라이브러리 헬퍼가 아직 없다. 이 프로브는 어느 경로가 먹는지를 *가르는*
탐색이므로 자기 코드를 갖는다. Phase 2 이후 Type C는 라이브러리 헬퍼만 import한다.

설정은 환경변수 `PYJAL_UE5_TEST_CONFIG`가 가리키는 JSON에서 읽는다.
"""

import json
import os
import re
import struct
import sys
import time
import traceback
from typing import Callable, Dict, List, Optional

sys.dont_write_bytecode = True

import unreal  # noqa: E402

CONFIG_ENV = "PYJAL_UE5_TEST_CONFIG"
LOG_PREFIX = "[MutableProbe]"

WRITE_SECTIONS = ("duplicateWrite", "guidRecovery", "groupFallback", "verifyMeans")
"""상태를 바꾸는 섹션. `onlySections`에 명시해야만 돈다."""

ALL_SECTIONS = (
    "environment",
    "nodeEnum",
    "propAccess",
    "groupGuid",
    "duplicateWrite",
    "guidRecovery",
    "groupFallback",
    "verifyMeans",
    "materialIndex",
)

NODE_CLASS_NAMES = (
    "CustomizableObjectNodeObject",
    "CustomizableObjectNodeObjectGroup",
    "CustomizableObjectNodeComponentMesh",
    "CustomizableObjectNodeComponentMeshAddTo",
    "CustomizableObjectNodeSkeletalMesh",
    "CustomizableObjectNodeMaterial",
    "CustomizableObjectNodeStaticString",
)

CANDIDATE_PROPS = (
    "ReferenceSkeletalMesh",
    "SkeletalMesh",
    "Material",
    "ParentObject",
    "ParentObjectGroupId",
    "GroupName",
    "ObjectName",
    "ComponentName",
    "NodeGuid",
    "Identifier",
    "bIsBase",
    "Value",
    "NodePosX",
)
"""읽기를 시도할 속성 후보 - **C++ 이름**이다.

1차 실행(2026-10-16)에서 노드 클래스가 Python에 export되지 않아 래퍼가 부모 타입
`CustomizableObjectNode`로 잡히고, snake_case -> C++ 이름 변환이 일어나지 않았다
(`identifier`는 한 단어라 우연히 `Identifier`로 풀렸다). PRD §3.1 예측:
ObjectName/ComponentName/NodeGuid/Identifier/bIsBase/Value는 protected로 읽기 불가.
"""


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


def _jsonable(inValue):
    """unreal 값을 결과 JSON에 넣을 수 있는 형태로 바꾼다.

    Args:
        inValue: 임의 값

    Returns:
        JSON 직렬화 가능한 값
    """
    if inValue is None or isinstance(inValue, (bool, int, float, str)):
        return inValue
    if isinstance(inValue, (list, tuple)):
        return [_jsonable(item) for item in inValue]
    if isinstance(inValue, unreal.Object):
        try:
            return inValue.get_path_name()
        except Exception:  # noqa: BLE001
            return repr(inValue)
    for method in ("export_text", "to_string", "get_asset_path_name"):
        if hasattr(inValue, method):
            try:
                return str(getattr(inValue, method)())
            except Exception:  # noqa: BLE001
                pass
    return str(inValue)


def _try_prop(inObj, inName: str) -> Dict:
    """속성 하나를 읽어 성공 여부와 값을 남긴다.

    Args:
        inObj: 대상 객체
        inName: 속성 이름(python 표기)

    Returns:
        {"ok": bool, "value"|"error": ...}
    """
    try:
        return {"ok": True, "value": _jsonable(inObj.get_editor_property(inName))}
    except Exception as readError:  # noqa: BLE001
        return {"ok": False, "error": _err(readError)}


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


def _load(inPackagePath: str):
    """에셋을 로드한다.

    Args:
        inPackagePath: 패키지 경로

    Returns:
        에셋 객체

    Raises:
        RuntimeError: 로드 실패
    """
    asset = unreal.EditorAssetLibrary.load_asset(inPackagePath)
    if asset is None:
        raise RuntimeError(f"로드 실패: {inPackagePath}")
    return asset


def _all_cos(inConfig: Dict) -> List[str]:
    """템플릿 + 표본 CO 경로 목록.

    Args:
        inConfig: 프로브 설정

    Returns:
        패키지 경로 리스트
    """
    paths = [inConfig["templateBase"]] + list(inConfig["templateSlots"].values())
    paths += [inConfig["sampleBase"], inConfig["sampleSlot"]]
    return paths


# ---------------------------------------------------------------------------
# 노드 열거 - 경로 후보 3개를 함께 잰다
# ---------------------------------------------------------------------------

_nodeClasses: Dict[str, object] = {}


def _node_classes() -> Dict[str, object]:
    """노드 UClass를 경로로 로드한다(Python 타입 export 여부와 무관).

    Returns:
        {클래스 이름: unreal.Class}
    """
    if not _nodeClasses:
        for className in NODE_CLASS_NAMES:
            try:
                loaded = unreal.load_class(None, f"/Script/CustomizableObjectEditor.{className}")
            except Exception:  # noqa: BLE001
                loaded = None
            if loaded is not None:
                _nodeClasses[className] = loaded
    return _nodeClasses


def _package_name(inObj) -> str:
    """객체가 속한 패키지 이름.

    Args:
        inObj: 객체

    Returns:
        패키지 이름(`/Game/...`)
    """
    return inObj.get_outermost().get_name()


def enum_by_class_iterator(inPackagePath: str) -> List:
    """노드 클래스별 ObjectIterator로 해당 패키지의 노드를 모은다.

    Args:
        inPackagePath: CO 패키지 경로

    Returns:
        노드 객체 리스트
    """
    nodes = []
    for nodeClass in _node_classes().values():
        for obj in unreal.ObjectIterator(nodeClass):
            if _package_name(obj) == inPackagePath:
                nodes.append(obj)
    return nodes


def enum_by_python_type(inPackagePath: str) -> List:
    """노드 python 타입(export된 경우)으로 ObjectIterator를 돈다.

    Args:
        inPackagePath: CO 패키지 경로

    Returns:
        노드 객체 리스트

    Raises:
        AttributeError: 노드 타입이 하나도 export되지 않음
    """
    types = [getattr(unreal, name) for name in NODE_CLASS_NAMES if hasattr(unreal, name)]
    if not types:
        raise AttributeError("노드 python 타입이 export되지 않았다")
    nodes = []
    for nodeType in types:
        for obj in unreal.ObjectIterator(nodeType):
            if _package_name(obj) == inPackagePath:
                nodes.append(obj)
    return nodes


def enum_by_find_source(inCo) -> Dict:
    """`find_object`로 Source 그래프를 찾는다.

    Args:
        inCo: CO 에셋

    Returns:
        시도 결과 dict
    """
    result: Dict = {}
    for candidate in ("Source", "CustomizableObjectGraph"):
        try:
            found = unreal.find_object(inCo, candidate)
            result[candidate] = _jsonable(found)
        except Exception as findError:  # noqa: BLE001
            result[candidate] = f"<error: {_err(findError)}>"
    return result


def _describe_node(inNode) -> Dict:
    """노드 하나의 클래스·경로·후보 속성을 덤프한다.

    Args:
        inNode: 노드

    Returns:
        덤프 dict
    """
    props = {}
    for name in CANDIDATE_PROPS:
        read = _try_prop(inNode, name)
        if read["ok"] or "protected" in read.get("error", "") or "AccessProtected" in read.get("error", ""):
            props[name] = read
    outer = inNode.get_outer()
    return {
        "class": inNode.get_class().get_name(),
        "pythonType": type(inNode).__name__,
        "path": inNode.get_path_name(),
        "outerClass": outer.get_class().get_name() if outer else None,
        "outerName": outer.get_name() if outer else None,
        "props": props,
    }


_enumMode: Dict[str, str] = {}
"""주 열거 경로에서 실제로 쓰인 방식(패키지별). 결과 JSON에 남긴다."""


def enum_by_full_scan(inPackagePath: str) -> List:
    """전체 객체 순회 + 클래스 이름 접두 + 패키지 필터(최후 폴백).

    Args:
        inPackagePath: CO 패키지 경로

    Returns:
        노드 리스트
    """
    nodes = []
    for obj in unreal.ObjectIterator(unreal.Object):
        objClass = obj.get_class() if obj is not None else None
        if objClass is None:
            continue
        if objClass.get_name().startswith("CustomizableObjectNode") and _package_name(obj) == inPackagePath:
            nodes.append(obj)
    return nodes


def _nodes_of(inPackagePath: str) -> List:
    """주 열거 경로(클래스 iterator)로 노드를 모은다. 실패하면 전체 순회로 폴백한다.

    Args:
        inPackagePath: CO 패키지 경로

    Returns:
        노드 리스트
    """
    try:
        nodes = enum_by_class_iterator(inPackagePath)
        _enumMode[inPackagePath] = "classIterator"
        return nodes
    except Exception:  # noqa: BLE001 - 폴백 경로를 같은 실행에서 잰다
        _enumMode[inPackagePath] = "fullScan"
        return enum_by_full_scan(inPackagePath)


def _by_class(inNodes: List, inClassName: str) -> List:
    """클래스 이름이 정확히 일치하는 노드만 고른다.

    Args:
        inNodes: 노드 리스트
        inClassName: 클래스 이름

    Returns:
        필터된 리스트
    """
    return [node for node in inNodes if node.get_class().get_name() == inClassName]


# ---------------------------------------------------------------------------
# 쓰기 헬퍼 (탐색용 - Phase 2 헬퍼가 생기면 버린다)
# ---------------------------------------------------------------------------


def _set_string_by_name(inObj, inPropName: str, inValue: str) -> Dict:
    """`KismetSystemLibrary.SetStringPropertyByName`을 call_method로 부른다.

    Args:
        inObj: 대상 객체
        inPropName: C++ 속성 이름
        inValue: 값

    Returns:
        시도 결과
    """
    result: Dict = {}
    try:
        inObj.modify()
    except Exception as modifyError:  # noqa: BLE001
        result["modifyError"] = _err(modifyError)
    cdo = unreal.SystemLibrary.get_default_object()
    try:
        returned = cdo.call_method("SetStringPropertyByName", (inObj, inPropName, inValue))
        result.update({"ok": True, "returned": _jsonable(returned)})
    except Exception as callError:  # noqa: BLE001
        result.update({"ok": False, "error": _err(callError)})
    return result


def _set_and_read(inObj, inName: str, inValue) -> Dict:
    """set_editor_property 후 되읽어 일치 여부를 남긴다.

    Args:
        inObj: 대상 객체
        inName: 속성 이름
        inValue: 값

    Returns:
        시도 결과
    """
    before = _try_prop(inObj, inName)
    try:
        inObj.set_editor_property(inName, inValue)
    except Exception as setError:  # noqa: BLE001
        return {"before": before, "ok": False, "error": _err(setError)}
    after = _try_prop(inObj, inName)
    return {
        "before": before,
        "ok": True,
        "after": after,
        "matches": after.get("value") == _jsonable(inValue),
    }


_scratch: Dict[str, object] = {}


def _duplicate(inSourcePath: str, inScratchRoot: str, inName: str):
    """복제본을 만든다(같은 실행 안에서 재사용).

    Args:
        inSourcePath: 원본 패키지 경로
        inScratchRoot: 복제본 폴더
        inName: 복제본 에셋 이름

    Returns:
        복제본

    Raises:
        RuntimeError: 복제 실패
    """
    destination = f"{inScratchRoot}/{inName}"
    if destination in _scratch:
        return _scratch[destination]
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(inSourcePath, destination)
    if duplicated is None:
        raise RuntimeError(f"복제 실패: {inSourcePath} -> {destination}")
    _scratch[destination] = duplicated
    return duplicated


def _skeletal_materials(inMesh) -> List[str]:
    """SK의 매테리얼 슬롯 매테리얼 경로 목록.

    Args:
        inMesh: SkeletalMesh

    Returns:
        경로 리스트(없으면 None 원소)
    """
    out = []
    for slot in inMesh.get_editor_property("materials"):
        material = slot.get_editor_property("material_interface")
        out.append(material.get_path_name() if material else None)
    return out


def _soft_path(inValue) -> Optional[str]:
    """TSoftObjectPtr 값의 경로 문자열.

    Args:
        inValue: 속성 값

    Returns:
        경로 또는 None
    """
    if inValue is None:
        return None
    return _jsonable(inValue)


# ---------------------------------------------------------------------------
# 섹션
# ---------------------------------------------------------------------------


def section_environment(inConfig: Dict) -> Dict:
    """Mutable 클래스 노출과 대상 에셋 로드 가능 여부.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    exported = {name: hasattr(unreal, name) for name in NODE_CLASS_NAMES}
    exported["CustomizableObject"] = hasattr(unreal, "CustomizableObject")
    exported["CustomizableObjectEditorFunctionLibrary"] = hasattr(
        unreal, "CustomizableObjectEditorFunctionLibrary"
    )
    exported["NewCustomizableObjectParameters"] = hasattr(unreal, "NewCustomizableObjectParameters")
    exported["EdGraph"] = hasattr(unreal, "EdGraph")
    exported["EdGraphNode"] = hasattr(unreal, "EdGraphNode")
    loadedClasses = {name: (cls.get_path_name() if cls else None) for name, cls in _node_classes().items()}
    loads = {}
    for path in _all_cos(inConfig):
        try:
            asset = _load(path)
            loads[path] = asset.get_class().get_name()
        except Exception as loadError:  # noqa: BLE001
            loads[path] = f"<error: {_err(loadError)}>"
    libMembers = []
    if hasattr(unreal, "CustomizableObjectEditorFunctionLibrary"):
        libMembers = sorted(
            n for n in dir(unreal.CustomizableObjectEditorFunctionLibrary) if not n.startswith("_")
        )
    coMembers = sorted(n for n in dir(unreal.CustomizableObject) if not n.startswith("_"))
    return {
        "succeeded": all(not str(v).startswith("<error") for v in loads.values()),
        "exported": exported,
        "loadedNodeClasses": loadedClasses,
        "loads": loads,
        "editorFunctionLibraryMembers": libMembers,
        "customizableObjectMembers": coMembers,
    }


def section_node_enum(inConfig: Dict) -> Dict:
    """노드 열거 경로 3종 비교 + 노드 덤프.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    perCo = {}
    for path in _all_cos(inConfig):
        co = _load(path)
        entry: Dict = {"findSource": enum_by_find_source(co)}
        started = time.perf_counter()
        try:
            classNodes = enum_by_class_iterator(path)
            entry["classIterator"] = {
                "count": len(classNodes),
                "seconds": round(time.perf_counter() - started, 4),
            }
        except Exception as iterError:  # noqa: BLE001
            entry["classIterator"] = {"error": _err(iterError)}
            started = time.perf_counter()
            classNodes = enum_by_full_scan(path)
            entry["fullScanFallback"] = {
                "count": len(classNodes),
                "seconds": round(time.perf_counter() - started, 4),
            }
        started = time.perf_counter()
        try:
            typeNodes = enum_by_python_type(path)
            entry["pythonTypeIterator"] = {
                "count": len(typeNodes),
                "seconds": round(time.perf_counter() - started, 4),
            }
        except Exception as typeError:  # noqa: BLE001
            entry["pythonTypeIterator"] = {"error": _err(typeError)}
        entry["nodes"] = [_describe_node(node) for node in classNodes]
        perCo[path] = entry

    # 전체 객체 순회 비용(한 번만 잰다 - 노드 클래스 iterator가 실패할 때의 폴백 후보)
    started = time.perf_counter()
    total = 0
    matched = 0
    target = inConfig["templateBase"]
    for obj in unreal.ObjectIterator(unreal.Object):
        total += 1
        objClass = obj.get_class() if obj is not None else None
        if objClass is None:
            continue
        if objClass.get_name().startswith("CustomizableObjectNode") and _package_name(obj) == target:
            matched += 1
    fullScan = {"objects": total, "matchedInTemplateBase": matched,
                "seconds": round(time.perf_counter() - started, 3)}
    anyNodes = any(len(entry["nodes"]) > 0 for entry in perCo.values())
    return {"succeeded": anyNodes, "perCo": perCo, "fullObjectScan": fullScan}


def section_prop_access(inConfig: Dict) -> Dict:
    """클래스별 속성 읽기 가능 여부 요약(nodeEnum 덤프와 별개로 전 후보를 기록).

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    table: Dict[str, Dict[str, str]] = {}
    for path in _all_cos(inConfig):
        for node in _nodes_of(path):
            className = node.get_class().get_name()
            row = table.setdefault(className, {})
            for name in CANDIDATE_PROPS:
                if name in row and row[name] == "ok":
                    continue
                read = _try_prop(node, name)
                row[name] = "ok" if read["ok"] else read["error"][:160]
    return {"succeeded": bool(table), "table": table}


def section_group_guid(inConfig: Dict) -> Dict:
    """템플릿 슬롯과 수작업 표본 슬롯의 그룹 GUID 비교 + Base 그룹 이름.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    def _object_node_info(inPath: str) -> Dict:
        objects = _by_class(_nodes_of(inPath), "CustomizableObjectNodeObject")
        return {
            "count": len(objects),
            "parentObject": [_try_prop(n, "ParentObject") for n in objects],
            "parentObjectGroupId": [_try_prop(n, "ParentObjectGroupId") for n in objects],
        }

    slots = {slot: _object_node_info(path) for slot, path in inConfig["templateSlots"].items()}
    sample = _object_node_info(inConfig["sampleSlot"])
    hairTemplate = slots.get(inConfig["sampleSlotName"], {})
    sameAsTemplate = (
        hairTemplate.get("parentObjectGroupId") == sample.get("parentObjectGroupId")
        and bool(sample.get("parentObjectGroupId"))
    )
    groups = {}
    for path in (inConfig["templateBase"], inConfig["sampleBase"]):
        groupNodes = _by_class(_nodes_of(path), "CustomizableObjectNodeObjectGroup")
        groups[path] = [_try_prop(n, "GroupName").get("value") for n in groupNodes]
    distinctTemplateGuids = sorted({
        str(info["parentObjectGroupId"]) for info in slots.values()
    })
    return {
        "succeeded": True,
        "templateSlots": slots,
        "sampleSlot": sample,
        "sampleGuidEqualsTemplateGuid": sameAsTemplate,
        "distinctTemplateSlotGuidCount": len(distinctTemplateGuids),
        "baseGroupNames": groups,
    }


def section_duplicate_write(inConfig: Dict) -> Dict:
    """메모리 복제본에 Base·슬롯 쓰기를 시도하고 되읽는다. 저장하지 않는다.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    scratch = inConfig["scratchRoot"]
    result: Dict = {}

    # --- Base ---
    base = _duplicate(inConfig["templateBase"], scratch, "CO_ProbeChar_Pr_Base")
    basePath = base.get_outermost().get_name()
    baseNodes = _nodes_of(basePath)
    result["baseNodeCount"] = len(baseNodes)
    components = _by_class(baseNodes, "CustomizableObjectNodeComponentMesh")
    componentWrites = []
    for component in components:
        placeholder = _try_prop(component, "ReferenceSkeletalMesh").get("value")
        part = str(placeholder or "").rsplit("_", 1)[-1].split(".")[0]
        targetPath = inConfig["sampleBaseMeshes"].get(part)
        entry: Dict = {"placeholder": placeholder, "part": part, "target": targetPath}
        if targetPath:
            entry["write"] = _set_and_read(component, "ReferenceSkeletalMesh", _load(targetPath))
        componentWrites.append(entry)
    result["componentWrites"] = componentWrites
    baseObjects = _by_class(baseNodes, "CustomizableObjectNodeObject")
    result["baseObjectNameWrite"] = [
        _set_string_by_name(n, "ObjectName", inConfig["probeBaseObjectName"]) for n in baseObjects
    ]
    result["baseObjectNameReadAfter"] = [_try_prop(n, "ObjectName") for n in baseObjects]

    # --- 슬롯: 순서 A(SK 먼저) / 순서 B(매테리얼 먼저) ---
    slotMesh = _load(inConfig["sampleSlotMesh"])
    slotMaterials = _skeletal_materials(slotMesh)
    result["slotMeshMaterials"] = slotMaterials
    for order in ("meshFirst", "materialFirst"):
        slot = _duplicate(
            inConfig["templateSlots"][inConfig["sampleSlotName"]], scratch, f"CO_ProbeChar_Pr_{order}"
        )
        slotPath = slot.get_outermost().get_name()
        nodes = _nodes_of(slotPath)
        skNodes = _by_class(nodes, "CustomizableObjectNodeSkeletalMesh")
        materialNodes = _by_class(nodes, "CustomizableObjectNodeMaterial")
        objectNodes = _by_class(nodes, "CustomizableObjectNodeObject")
        entry = {"skNodeCount": len(skNodes), "materialNodeCount": len(materialNodes)}
        newMaterial = _load(slotMaterials[0]) if slotMaterials and slotMaterials[0] else None

        def _write_mesh():
            entry["meshWrite"] = [_set_and_read(n, "SkeletalMesh", slotMesh) for n in skNodes]

        def _write_material():
            entry["materialWrite"] = [_set_and_read(n, "Material", newMaterial) for n in materialNodes]

        if order == "meshFirst":
            _write_mesh()
            _write_material()
        else:
            _write_material()
            _write_mesh()
        entry["materialAfterBoth"] = [_try_prop(n, "Material") for n in materialNodes]
        entry["meshAfterBoth"] = [_try_prop(n, "SkeletalMesh") for n in skNodes]
        entry["nodeCountAfter"] = len(_nodes_of(slotPath))
        entry["parentWrite"] = [_set_and_read(n, "ParentObject", base) for n in objectNodes]
        entry["groupIdAfterParent"] = [_try_prop(n, "ParentObjectGroupId") for n in objectNodes]
        entry["objectNameWrite"] = [
            _set_string_by_name(n, "ObjectName", inConfig["probeSlotObjectName"]) for n in objectNodes
        ]
        result[order] = entry
    result["succeeded"] = True
    return result


def section_group_fallback(inConfig: Dict) -> Dict:
    """NewCustomizableObject 임시 CO로 그룹 GUID를 얻을 수 있는가.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    scratch = inConfig["scratchRoot"]
    library = unreal.CustomizableObjectEditorFunctionLibrary
    result: Dict = {}
    parents = {"templateBase": _load(inConfig["templateBase"])}
    duplicatedBase = _scratch.get(f"{scratch}/CO_ProbeChar_Pr_Base")
    if duplicatedBase is None:
        duplicatedBase = _duplicate(inConfig["templateBase"], scratch, "CO_ProbeChar_Pr_Base")
    parents["duplicatedBase"] = duplicatedBase
    for label, parent in parents.items():
        for groupName in (inConfig["sampleSlotName"], "__NoSuchGroup__"):
            key = f"{label}:{groupName}"
            try:
                params = unreal.NewCustomizableObjectParameters()
                params.set_editor_property("package_path", scratch)
                params.set_editor_property("asset_name", f"CO_ProbeTmp_{label}_{groupName.strip('_')}")
                params.set_editor_property("parent_object", parent)
                params.set_editor_property("parent_group_node", groupName)
                created = library.new_customizable_object(params)
                if created is None:
                    result[key] = {"created": False}
                    continue
                createdPath = created.get_outermost().get_name()
                _scratch[createdPath] = created
                objects = _by_class(_nodes_of(createdPath), "CustomizableObjectNodeObject")
                result[key] = {
                    "created": True,
                    "path": createdPath,
                    "onDisk": os.path.exists(_package_to_file(createdPath)),
                    "parentObjectGroupId": [_try_prop(n, "ParentObjectGroupId") for n in objects],
                    "parentObject": [_try_prop(n, "ParentObject") for n in objects],
                }
            except Exception as createError:  # noqa: BLE001
                result[key] = {"error": _err(createError)}
    result["succeeded"] = any(isinstance(v, dict) and v.get("created") for v in result.values())
    return result


def _fstrings(inFilePath: str) -> List[str]:
    """`.uasset`의 길이접두 ASCII FString을 모은다.

    Args:
        inFilePath: 파일 경로

    Returns:
        문자열 리스트
    """
    with open(inFilePath, "rb") as handle:
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


def _guid_hex_from_bytes(inBytes: bytes) -> str:
    """FGuid 16바이트(리틀엔디언 uint32 x4)를 32자리 대문자 hex로.

    Args:
        inBytes: 16바이트

    Returns:
        `unreal.Guid` 문자열 표기와 같은 형식
    """
    return "".join(f"{part:08X}" for part in struct.unpack("<4I", inBytes))


def _groups_from_bytes(inFilePath: str, inGroupNames: List[str], inOffset: int) -> Dict:
    """그룹 이름 FString 뒤 inOffset 위치의 16바이트를 NodeGuid로 읽는다.

    Args:
        inFilePath: `.uasset` 경로
        inGroupNames: 그룹 이름 목록
        inOffset: FString 시작 기준 GUID 오프셋(템플릿 실측 87)

    Returns:
        {그룹 이름: [guid hex 후보...]}
    """
    with open(inFilePath, "rb") as handle:
        data = handle.read()
    out: Dict[str, List[str]] = {}
    for name in inGroupNames:
        encoded = struct.pack("<i", len(name) + 1) + name.encode("ascii") + b"\x00"
        hits = []
        start = 0
        while True:
            position = data.find(encoded, start)
            if position < 0:
                break
            guidBytes = data[position + inOffset:position + inOffset + 16]
            if len(guidBytes) == 16:
                hits.append(_guid_hex_from_bytes(guidBytes))
            start = position + 1
        out[name] = hits
    return out


def _make_guid(inHex: str):
    """32자리 hex에서 unreal.Guid를 만든다(형태 여럿을 시도하고 문자열 왕복으로 확인).

    Args:
        inHex: 32자리 hex

    Returns:
        (Guid 또는 None, 시도 기록 dict)
    """
    attempts: Dict = {}
    parts = [int(inHex[i:i + 8], 16) for i in range(0, 32, 8)]
    signed = [p - (1 << 32) if p >= (1 << 31) else p for p in parts]

    def _check(inLabel: str, inGuid) -> Optional[object]:
        text = str(_jsonable(inGuid)).upper().replace("-", "")
        attempts[inLabel] = text
        return inGuid if inHex.upper() in text else None

    try:
        returned = unreal.GuidLibrary.parse_string_to_guid(inHex)
        guid = returned[0] if isinstance(returned, tuple) else returned
        hit = _check("parseStringToGuid", guid)
        if hit is not None:
            return hit, attempts
    except Exception as parseError:  # noqa: BLE001
        attempts["parseStringToGuid"] = f"<error: {_err(parseError)}>"
    for label, values in (("ctorUnsigned", parts), ("ctorSigned", signed)):
        try:
            hit = _check(label, unreal.Guid(*values))
            if hit is not None:
                return hit, attempts
        except Exception as ctorError:  # noqa: BLE001
            attempts[label] = f"<error: {_err(ctorError)}>"
    return None, attempts


def _export_t3d(inObj, inFilePath: str) -> Dict:
    """객체를 T3D 텍스트로 익스포트해 NodeGuid/GroupName 줄을 뽑는다.

    Args:
        inObj: 대상 객체
        inFilePath: 출력 파일

    Returns:
        시도 결과
    """
    result: Dict = {}
    try:
        task = unreal.AssetExportTask()
        task.set_editor_property("object", inObj)
        task.set_editor_property("filename", inFilePath)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        if hasattr(unreal, "ObjectExporterT3D"):
            task.set_editor_property("exporter", unreal.ObjectExporterT3D())
        result["ran"] = bool(unreal.Exporter.run_asset_export_task(task))
        if os.path.exists(inFilePath):
            with open(inFilePath, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            result["chars"] = len(text)
            result["nodeGuidLines"] = re.findall(r"NodeGuid=\S+", text)[:20]
            result["groupNameLines"] = re.findall(r"GroupName=\"[^\"]*\"", text)[:20]
            result["head"] = text[:600]
    except Exception as exportError:  # noqa: BLE001
        result["error"] = _err(exportError)
    return result


def _group_enum_values(inCo, inGroupName: str) -> Dict:
    """컴파일된 CO에서 그룹 파라미터(enum)의 값 목록.

    Args:
        inCo: CO
        inGroupName: 그룹 이름

    Returns:
        {"count", "values"} 또는 오류
    """
    try:
        count = inCo.get_enum_parameter_num_values(inGroupName)
        values = [str(inCo.get_enum_parameter_value(inGroupName, i)) for i in range(count)]
        return {"count": count, "values": values}
    except Exception as readError:  # noqa: BLE001
        return {"error": _err(readError)}


def section_guid_recovery(inConfig: Dict) -> Dict:
    """복제된 Base의 그룹 GUID를 바이트/T3D로 복원하고, 컴파일로 부착 여부를 단정한다.

    duplicateWrite가 만든 `CO_ProbeChar_Pr_Base`와 `CO_ProbeChar_Pr_meshFirst`(Parent=복제 Base,
    GUID=템플릿 Base의 Hair - 복제 시 GUID가 재생성되므로 낡은 값)를 쓴다.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    scratch = inConfig["scratchRoot"]
    library = unreal.CustomizableObjectEditorFunctionLibrary
    basePath = f"{scratch}/CO_ProbeChar_Pr_Base"
    slotPath = f"{scratch}/CO_ProbeChar_Pr_meshFirst"
    base = _scratch[basePath]
    groupName = inConfig["sampleSlotName"]
    result: Dict = {}

    for path in (basePath, slotPath):
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    groupNodes = _by_class(_nodes_of(basePath), "CustomizableObjectNodeObjectGroup")
    groupNames = [_try_prop(n, "GroupName").get("value") for n in groupNodes]
    result["groupNames"] = groupNames
    result["bytesTemplate"] = _groups_from_bytes(
        _package_to_file(inConfig["templateBase"]), groupNames, inConfig["guidOffset"]
    )
    result["bytesDuplicate"] = _groups_from_bytes(_package_to_file(basePath), groupNames, inConfig["guidOffset"])
    result["templateSlotGuid"] = inConfig["templateHairGuid"]

    exportDir = inConfig["exportDir"]
    os.makedirs(exportDir, exist_ok=True)
    result["t3dGroupNode"] = _export_t3d(groupNodes[0], f"{exportDir}/group0.t3d") if groupNodes else None
    result["t3dAsset"] = _export_t3d(base, f"{exportDir}/base.t3d")

    slotObjects = _by_class(_nodes_of(slotPath), "CustomizableObjectNodeObject")
    staleGuid = _try_prop(slotObjects[0], "ParentObjectGroupId").get("value")
    result["slotGuidBefore"] = staleGuid
    library.compile_customizable_object_synchronously(base)
    result["enumBeforeFix"] = _group_enum_values(base, groupName)

    candidates = result["bytesDuplicate"].get(groupName, [])
    if len(candidates) == 1:
        recovered, attempts = _make_guid(candidates[0])
        result["guidMakeAttempts"] = attempts
        result["recoveredGuid"] = _jsonable(recovered)
        if recovered is None:
            result["succeeded"] = False
            return result
        result["fixWrite"] = _set_and_read(slotObjects[0], "ParentObjectGroupId", recovered)
        unreal.EditorAssetLibrary.save_asset(slotPath, only_if_is_dirty=False)
        library.compile_customizable_object_synchronously(base)
        result["enumAfterFix"] = _group_enum_values(base, groupName)
    else:
        result["recoveredGuid"] = f"<ambiguous: {candidates}>"
    result["succeeded"] = True
    return result


def section_verify_means(inConfig: Dict) -> Dict:
    """복제본을 저장해 바이트 판정이 성립하는지, 컴파일 상태가 축이 되는지 잰다.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    scratch = inConfig["scratchRoot"]
    result: Dict = {"saved": {}, "bytes": {}, "compile": {}}
    targets = [path for path in _scratch if path.startswith(scratch)]
    for path in targets:
        try:
            result["saved"][path] = bool(unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False))
        except Exception as saveError:  # noqa: BLE001
            result["saved"][path] = f"<error: {_err(saveError)}>"
        filePath = _package_to_file(path)
        if os.path.exists(filePath):
            strings = _fstrings(filePath)
            joined = "\n".join(strings)
            result["bytes"][path] = {
                "probeBaseName": strings.count(inConfig["probeBaseObjectName"]),
                "probeSlotName": strings.count(inConfig["probeSlotObjectName"]),
                "templateShToken": len(re.findall("Template_Sh", joined)),
                "templateBaseRef": joined.count(inConfig["templateBase"]),
                "slotSuffixName": strings.count(f"{inConfig['sampleSlotName']}Slot"),
                "sampleSlotMeshRef": joined.count(inConfig["sampleSlotMesh"]),
                "probeBaseRef": joined.count(f"{scratch}/CO_ProbeChar_Pr_Base"),
            }

    library = unreal.CustomizableObjectEditorFunctionLibrary
    compileTargets = {
        "duplicatedBase": _scratch.get(f"{scratch}/CO_ProbeChar_Pr_Base"),
        "sampleBase": _load(inConfig["sampleBase"]),
    }
    for label, co in compileTargets.items():
        if co is None:
            continue
        started = time.perf_counter()
        try:
            state = library.compile_customizable_object_synchronously(co)
            result["compile"][label] = {
                "state": str(state),
                "seconds": round(time.perf_counter() - started, 2),
            }
        except Exception as compileError:  # noqa: BLE001
            result["compile"][label] = {"error": _err(compileError)}

    # 정리 - 메모리 삭제 + 디스크 파일 직접 삭제(헤드레스 delete_asset은 메모리만 지운다)
    cleanup = {}
    for path in targets:
        try:
            unreal.EditorAssetLibrary.delete_asset(path)
        except Exception as deleteError:  # noqa: BLE001
            cleanup[path] = f"<delete_asset error: {_err(deleteError)}>"
        filePath = _package_to_file(path)
        if os.path.exists(filePath):
            try:
                os.remove(filePath)
            except OSError as removeError:
                cleanup[path] = f"<os.remove error: {removeError}>"
        cleanup.setdefault(path, "removed" if not os.path.exists(filePath) else "left")
    result["cleanup"] = cleanup
    result["succeeded"] = bool(result["bytes"])
    return result


def section_material_index(inConfig: Dict) -> Dict:
    """플레이스홀더 MI가 플레이스홀더 SK의 몇 번째 슬롯인지, 표본과 일치하는지.

    Args:
        inConfig: 프로브 설정

    Returns:
        섹션 결과
    """
    templates = {}
    for slot, path in inConfig["templateSlots"].items():
        nodes = _nodes_of(path)
        skNodes = _by_class(nodes, "CustomizableObjectNodeSkeletalMesh")
        materialNodes = _by_class(nodes, "CustomizableObjectNodeMaterial")
        meshes = {}
        for node in skNodes:
            meshValue = node.get_editor_property("SkeletalMesh")
            meshPath = _soft_path(meshValue)
            mesh = None
            try:
                mesh = meshValue.load_synchronous() if hasattr(meshValue, "load_synchronous") else None
            except Exception:  # noqa: BLE001
                mesh = None
            if mesh is None and meshPath:
                try:
                    mesh = _load(str(meshPath).split(".")[0])
                except Exception:  # noqa: BLE001
                    mesh = None
            meshes[str(meshPath)] = _skeletal_materials(mesh) if mesh else "<load failed>"
        mapping = []
        for node in materialNodes:
            material = _try_prop(node, "Material").get("value")
            hits = [
                {"mesh": meshPath, "index": materials.index(material)}
                for meshPath, materials in meshes.items()
                if isinstance(materials, list) and material in materials
            ]
            mapping.append({"material": material, "hits": hits})
        templates[slot] = {"skMeshes": meshes, "materialMapping": mapping}

    sampleNodes = _nodes_of(inConfig["sampleSlot"])
    sampleMaterial = [
        _try_prop(n, "Material").get("value")
        for n in _by_class(sampleNodes, "CustomizableObjectNodeMaterial")
    ]
    sampleMeshMaterials = _skeletal_materials(_load(inConfig["sampleSlotMesh"]))
    hairMapping = templates.get(inConfig["sampleSlotName"], {}).get("materialMapping", [])
    predicted = None
    if hairMapping and hairMapping[0]["hits"]:
        index = hairMapping[0]["hits"][0]["index"]
        predicted = sampleMeshMaterials[index] if index < len(sampleMeshMaterials) else None
    return {
        "succeeded": True,
        "templates": templates,
        "sampleMaterial": sampleMaterial,
        "sampleMeshMaterials": sampleMeshMaterials,
        "predictedSampleMaterial": predicted,
        "predictionMatchesSample": bool(sampleMaterial) and predicted == sampleMaterial[0],
    }


SECTIONS: Dict[str, Callable[[Dict], Dict]] = {
    "environment": section_environment,
    "nodeEnum": section_node_enum,
    "propAccess": section_prop_access,
    "groupGuid": section_group_guid,
    "duplicateWrite": section_duplicate_write,
    "guidRecovery": section_guid_recovery,
    "groupFallback": section_group_fallback,
    "verifyMeans": section_verify_means,
    "materialIndex": section_material_index,
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
    started = time.perf_counter()
    try:
        sectionResult = SECTIONS[inName](inConfig)
    except Exception as sectionError:  # noqa: BLE001 - 섹션 격리가 목적이다
        _log_error(f"섹션 예외: {inName} - {sectionError}")
        sectionResult = {"succeeded": False, "error": _err(sectionError), "traceback": traceback.format_exc()}
    sectionResult["seconds"] = round(time.perf_counter() - started, 3)
    _log(f"섹션 완료: {inName} (succeeded={sectionResult.get('succeeded')})")
    return sectionResult


def _selected_sections(inOnlySections: List[str]) -> List[str]:
    """실행할 섹션을 고른다. 쓰기 섹션은 명시 지정 시에만 포함한다.

    Args:
        inOnlySections: 설정의 `onlySections`

    Returns:
        실행할 섹션 이름 리스트(실행 순서는 ALL_SECTIONS 순)
    """
    if inOnlySections:
        return [name for name in ALL_SECTIONS if name in inOnlySections]
    return [name for name in ALL_SECTIONS if name not in WRITE_SECTIONS]


def _environment_facts(inConfig: Dict) -> Dict:
    """실행 환경 사실(소스 컨트롤 상태, 스크래치 잔여 디스크 파일).

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
    leftovers = {path: os.path.exists(_package_to_file(path)) for path in _scratch}
    facts["enumMode"] = dict(_enumMode)
    facts["scratchFilesOnDisk"] = leftovers
    facts["anyScratchOnDisk"] = any(leftovers.values())
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
