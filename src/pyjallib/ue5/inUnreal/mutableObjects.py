#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Mutable Customizable Object 생성 어댑터 (UE5 임베디드 파이썬 전용)

캐릭터 폴더의 스켈레탈 메쉬로 Base CO와 슬롯 CO를 템플릿 복제로 만든다. 무엇을 어디에
만들고 어느 노드를 무엇으로 바꿀지는 `ue5/mutableRules.py`(unreal 비의존)가 결정하고,
이 모듈은 에셋 스캔·템플릿 읽기·복제·노드 쓰기·검증·저장만 한다.

사용 예::

    from pyjallib.ue5.mutableRules import MutableBuildConfig
    from pyjallib.ue5.inUnreal.mutableObjects import MutableObjectBuilder

    config = MutableBuildConfig(
        baseTemplatePath="/Game/Shared/Mutable/CO_Template_Base",
        slotTemplatePattern="/Game/Shared/Mutable/CO_Template_{slot}Slot",
        meshFolderName="Meshes",
        mutableFolderName="Mutable",
        baseOutfit="Default",
    )
    builder = MutableObjectBuilder(config)
    plan = builder.build_plan("/Game/Characters/Hero")    # 에셋을 바꾸지 않는다
    result = builder.apply_plan(plan, inDryRun=False)      # 확인 후에만

UE 5.7.4 실측 (2026-10-16 Phase 0, `.ai_planning/archive/PyJalLib/*Mutable*`):

- Mutable 노드 클래스는 Python 타입으로 export되지 않는다. 래퍼는 부모 타입
  `CustomizableObjectNode`로 잡히고 **속성은 C++ 이름 문자열로만** 접근된다
  (`get_editor_property("SkeletalMesh")` - snake_case는 `Failed to find property`).
- 노드 열거는 `unreal.load_class`로 얻은 노드 UClass별 `unreal.ObjectIterator` + 패키지 필터다.
  CO의 `Source` 그래프 속성은 protected라 읽히지 않는다.
- `ObjectName`(Base Object 노드 이름)은 protected다. `KismetSystemLibrary.SetStringPropertyByName`이
  플래그 검사 없이 쓰고(`KismetSystemLibrary.cpp`), `call_method`가 export 여부를 보지 않고
  부르므로(`PyWrapperObject.cpp`) 그 경로로 쓴다. **엔진 내부용 함수에 기대므로 엔진
  업그레이드 시 깨질 수 있다** - 쓰기 헬퍼는 `write_object_name` 하나에만 둔다.
- protected 속성(`ObjectName`, `ComponentName`, `NodeGuid`)의 되읽기는 **T3D 익스포트**다
  (`AssetExportTask` + `ObjectExporterT3D`). 에셋 복제는 그래프 노드 GUID를 전부
  재생성하므로(`CustomizableObjectGraph.cpp` `PostDuplicate`) 슬롯이 붙을 그룹 GUID도
  새 Base를 T3D로 익스포트해 읽는다. `NewCustomizableObject`는 그룹 인자를 쓰지 않으므로
  쓰지 않는다.

저장 경계 (P4는 이 모듈 밖이다):

- 계획이 만든 **신규 CO 경로만** 저장한다. 템플릿·메쉬·기존 CO는 저장하지 않는다.
- 대상이 레지스트리나 디스크에 이미 있으면 만들지 않는다(`skipped:exists`).
- 한 CO가 검증에 실패하면 그 복제본은 저장하지 않고 메모리에서 지운다(반쪽 CO를 남기지 않는다).
- 에디터가 소스 컨트롤에 연결되어 있으면 `save_asset`이 신규 파일을 **default CL에 add**한다.
  **CL 정리(이동·서밋·누출 검사)는 호출자 책임이다** - UE5 임베디드 파이썬에는 P4Python이 없다.

로깅은 `unreal.log` 계열을 쓴다 - 임베디드 파이썬에는 pyjallib `Logger` 경로가 없다.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

import unreal


def _load_rules_module():
    """순수 결정 모듈 `mutableRules`를 로드한다.

    패키지로 import되면 상대 import를 쓰고, `inUnreal` 폴더를 `sys.path`에 얹어 **평면
    import**되면 형제 폴더의 파일을 경로로 직접 로드한다(`materialSlots`와 같은 방식).

    Returns:
        `mutableRules` 모듈
    """
    try:
        from .. import mutableRules as rulesModule
        return rulesModule
    except ImportError:
        pass

    existing = sys.modules.get("mutableRules")
    if existing is not None:
        return existing
    rulesPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mutableRules.py")
    spec = importlib.util.spec_from_file_location("mutableRules", rulesPath)
    rulesModule = importlib.util.module_from_spec(spec)
    sys.modules["mutableRules"] = rulesModule
    spec.loader.exec_module(rulesModule)
    return rulesModule


mutableRules = _load_rules_module()

LOG_PREFIX = "[MutableObjects]"

NODE_SCRIPT_PACKAGE = "/Script/CustomizableObjectEditor"
NODE_OBJECT = "CustomizableObjectNodeObject"
NODE_GROUP = mutableRules.GROUP_NODE_CLASS
NODE_COMPONENT_MESH = "CustomizableObjectNodeComponentMesh"
NODE_SKELETAL_MESH = "CustomizableObjectNodeSkeletalMesh"
NODE_MATERIAL = "CustomizableObjectNodeMaterial"
NODE_CLASSES = (NODE_OBJECT, NODE_GROUP, NODE_COMPONENT_MESH, NODE_SKELETAL_MESH, NODE_MATERIAL)
"""열거하는 노드 클래스. 엔진(Mutable 플러그인) 클래스 이름이지 프로젝트 규약이 아니다."""

PROP_OBJECT_NAME = "ObjectName"
PROP_PARENT_OBJECT = "ParentObject"
PROP_PARENT_GROUP_ID = "ParentObjectGroupId"
PROP_GROUP_NAME = "GroupName"
PROP_REFERENCE_MESH = "ReferenceSkeletalMesh"
PROP_SKELETAL_MESH = "SkeletalMesh"
PROP_MATERIAL = "Material"
"""노드 속성의 **C++ 이름**. 미export 클래스라 python 이름(snake_case)으로는 풀리지 않는다."""


def _log(inMessage: str) -> None:
    """엔진 로그에 정보 메시지를 남긴다.

    Args:
        inMessage: 메시지
    """
    unreal.log(f"{LOG_PREFIX} {inMessage}")


def _log_warning(inMessage: str) -> None:
    """엔진 로그에 경고 메시지를 남긴다.

    Args:
        inMessage: 메시지
    """
    unreal.log_warning(f"{LOG_PREFIX} {inMessage}")


def _log_error(inMessage: str) -> None:
    """엔진 로그에 에러 메시지를 남긴다.

    Args:
        inMessage: 메시지
    """
    unreal.log_error(f"{LOG_PREFIX} {inMessage}")


# ---------------------------------------------------------------------------
# 값·경로
# ---------------------------------------------------------------------------


def value_path(inValue) -> Optional[str]:
    """에셋 참조 값(객체·소프트 참조·SoftObjectPath)을 경로 문자열로 바꾼다.

    Args:
        inValue: `get_editor_property` 반환값

    Returns:
        경로 문자열. 비어 있으면 None.
    """
    if inValue is None:
        return None
    if isinstance(inValue, unreal.Object):
        return inValue.get_path_name()
    for method in ("export_text", "to_string", "get_asset_path_name"):
        if hasattr(inValue, method):
            try:
                text = str(getattr(inValue, method)())
            except Exception:  # noqa: BLE001 - 다음 형태를 시도한다
                continue
            text = text.strip().strip('"')
            if text and text.lower() not in ("none", "null"):
                return text
            return None
    text = str(inValue)
    return text or None


def guid_text(inGuid) -> str:
    """`unreal.Guid`를 32자리 대문자 hex로 바꾼다.

    Args:
        inGuid: Guid 값

    Returns:
        32 hex 문자열
    """
    text = value_path(inGuid) or ""
    return text.upper().replace("-", "").replace("{", "").replace("}", "")


def make_guid(inHex: str):
    """32자리 hex에서 `unreal.Guid`를 만든다.

    Args:
        inHex: 32 hex 문자열

    Returns:
        Guid

    Raises:
        ValueError: 만든 Guid가 입력과 왕복되지 않음
    """
    returned = unreal.GuidLibrary.parse_string_to_guid(inHex)
    guid = returned[0] if isinstance(returned, tuple) else returned
    if guid_text(guid) != inHex.upper():
        raise ValueError(f"Guid 왕복 불일치: {inHex} -> {guid_text(guid)}")
    return guid


def package_file_path(inPackagePath: str) -> Optional[str]:
    """`/Game/...` 패키지 경로를 로컬 `.uasset` 절대 경로로 바꾼다.

    Args:
        inPackagePath: 패키지 또는 오브젝트 경로

    Returns:
        정방향 슬래시 절대 경로. `/Game/` 밖이면 None.
    """
    path = mutableRules.to_package_path(str(inPackagePath).replace("\\", "/"))
    if not path.startswith("/Game/"):
        return None
    contentDir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    return contentDir.replace("\\", "/").rstrip("/") + "/" + path[len("/Game/"):] + ".uasset"


def _asset_exists(inPackagePath: str) -> bool:
    """레지스트리 또는 디스크에 에셋이 있는가.

    Args:
        inPackagePath: 패키지 경로

    Returns:
        있으면 True
    """
    if unreal.EditorAssetLibrary.does_asset_exist(inPackagePath):
        return True
    filePath = package_file_path(inPackagePath)
    return bool(filePath and os.path.exists(filePath))


def _load_asset(inPath: str):
    """에셋을 로드한다.

    Args:
        inPath: 패키지 또는 오브젝트 경로

    Returns:
        에셋

    Raises:
        RuntimeError: 로드 실패
    """
    asset = unreal.EditorAssetLibrary.load_asset(mutableRules.to_package_path(inPath))
    if asset is None:
        raise RuntimeError(f"로드 실패: {inPath}")
    return asset


def mesh_material_paths(inMeshPath: str) -> List[Optional[str]]:
    """스켈레탈 메쉬의 매테리얼 슬롯 순서 매테리얼 경로.

    Args:
        inMeshPath: 메쉬 경로

    Returns:
        경로 리스트(빈 슬롯은 None)
    """
    mesh = _load_asset(inMeshPath)
    paths: List[Optional[str]] = []
    for slot in mesh.get_editor_property("materials"):
        paths.append(value_path(slot.get_editor_property("material_interface")))
    return paths


# ---------------------------------------------------------------------------
# 노드 열거·속성
# ---------------------------------------------------------------------------

_nodeClassCache: Dict[str, object] = {}


def _node_class(inClassName: str):
    """노드 UClass를 경로로 로드한다(Python 타입 export 여부와 무관).

    Args:
        inClassName: 노드 클래스 이름

    Returns:
        unreal.Class

    Raises:
        RuntimeError: 클래스를 찾지 못함(Mutable 에디터 모듈 미로드)
    """
    if inClassName not in _nodeClassCache:
        loaded = unreal.load_class(None, f"{NODE_SCRIPT_PACKAGE}.{inClassName}")
        if loaded is None:
            raise RuntimeError(f"노드 클래스를 찾지 못했다(Mutable 에디터 모듈?): {inClassName}")
        _nodeClassCache[inClassName] = loaded
    return _nodeClassCache[inClassName]


def list_graph_nodes(inCustomizableObject, inClassName: str) -> List:
    """CO 그래프에서 특정 클래스의 노드를 모은다.

    Args:
        inCustomizableObject: CO 에셋(또는 그 패키지 경로)
        inClassName: 노드 클래스 이름(정확히 일치하는 것만 - 하위 클래스 제외)

    Returns:
        노드 리스트
    """
    if isinstance(inCustomizableObject, str):
        packageName = mutableRules.to_package_path(inCustomizableObject)
    else:
        packageName = inCustomizableObject.get_outermost().get_name()
    nodes = []
    for obj in unreal.ObjectIterator(_node_class(inClassName)):
        if obj.get_class().get_name() == inClassName and obj.get_outermost().get_name() == packageName:
            nodes.append(obj)
    return nodes


def node_value_path(inNode, inPropName: str) -> Optional[str]:
    """노드의 에셋 참조 속성을 경로 문자열로 읽는다.

    Args:
        inNode: 노드
        inPropName: 속성 C++ 이름

    Returns:
        경로 또는 None
    """
    return value_path(inNode.get_editor_property(inPropName))


def set_node_asset_verified(inNode, inPropName: str, inAsset) -> bool:
    """노드의 에셋 참조 속성을 쓰고 되읽어 확인한다.

    `set_editor_property`는 `PostEditChangeProperty`를 부르므로 SK 노드는 핀을 재구성한다.
    **성공 판정은 되읽기뿐이다**(반환값·예외 부재는 근거가 아니다).

    Args:
        inNode: 노드
        inPropName: 속성 C++ 이름
        inAsset: 넣을 에셋 객체

    Returns:
        되읽은 경로가 넣은 에셋 경로와 같으면 True
    """
    inNode.set_editor_property(inPropName, inAsset)
    after = node_value_path(inNode, inPropName)
    return (
        after is not None
        and mutableRules.to_package_path(after) == mutableRules.to_package_path(inAsset.get_path_name())
    )


def set_group_id_verified(inNode, inGuidHex: str) -> bool:
    """`ParentObjectGroupId`를 쓰고 되읽어 확인한다.

    Args:
        inNode: Base Object 노드
        inGuidHex: 32 hex 그룹 NodeGuid

    Returns:
        되읽은 값이 같으면 True
    """
    inNode.set_editor_property(PROP_PARENT_GROUP_ID, make_guid(inGuidHex))
    return guid_text(inNode.get_editor_property(PROP_PARENT_GROUP_ID)) == inGuidHex.upper()


def write_object_name(inNode, inName: str) -> None:
    """Base Object 노드의 `ObjectName`(protected)을 쓴다. 검증은 `export_t3d_text`로 한다.

    `KismetSystemLibrary.SetStringPropertyByName`은 `BlueprintInternalUseOnly`라
    `unreal.SystemLibrary`에 export되지 않지만, `call_method`는 export 여부를 보지 않고
    `FindFunctionByName`으로 부른다. 그 함수는 플래그 검사 없이 `FindFProperty` ->
    `SetPropertyValue_InContainer`로 쓴다(UE 5.7.4 `KismetSystemLibrary.cpp`,
    `PyWrapperObject.cpp` `CallMethod`). 변경 알림이 없으므로 먼저 `modify()`를 부른다.

    Args:
        inNode: Base Object 노드
        inName: 새 이름
    """
    inNode.modify()
    unreal.SystemLibrary.get_default_object().call_method(
        "SetStringPropertyByName", (inNode, PROP_OBJECT_NAME, inName)
    )


def export_t3d_text(inObject) -> str:
    """객체를 T3D 텍스트로 익스포트해 돌려준다(임시 파일은 OS temp에 쓰고 지운다).

    protected 속성(`ObjectName`, `ComponentName`, `NodeGuid`)의 유일한 되읽기 수단이다.
    Content 밖에 쓰므로 에셋 레지스트리·소스 컨트롤과 무관하다.

    Args:
        inObject: 익스포트할 객체(CO 에셋 전체 또는 노드)

    Returns:
        T3D 텍스트

    Raises:
        RuntimeError: 익스포트 실패
    """
    tempDir = tempfile.mkdtemp(prefix="pyjal_mutable_t3d_")
    filePath = os.path.join(tempDir, "export.t3d").replace("\\", "/")
    try:
        task = unreal.AssetExportTask()
        task.set_editor_property("object", inObject)
        task.set_editor_property("filename", filePath)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("exporter", unreal.ObjectExporterT3D())
        if not unreal.Exporter.run_asset_export_task(task) or not os.path.exists(filePath):
            raise RuntimeError(f"T3D 익스포트 실패: {inObject.get_path_name()}")
        with open(filePath, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    finally:
        shutil.rmtree(tempDir, ignore_errors=True)


def read_group_guids(inCustomizableObject) -> Dict[str, List[str]]:
    """CO의 그룹 노드 {GroupName: [NodeGuid...]}를 T3D로 읽는다.

    Args:
        inCustomizableObject: CO 에셋

    Returns:
        그룹 GUID 맵
    """
    return mutableRules.parse_group_guids_t3d(export_t3d_text(inCustomizableObject))


def read_object_names(inCustomizableObject) -> List[str]:
    """CO의 Base Object 노드 `ObjectName`들을 T3D로 읽는다.

    Args:
        inCustomizableObject: CO 에셋

    Returns:
        이름 목록
    """
    return mutableRules.read_t3d_property(export_t3d_text(inCustomizableObject), NODE_OBJECT, PROP_OBJECT_NAME)


# ---------------------------------------------------------------------------
# 스캔
# ---------------------------------------------------------------------------


def scan_character_assets(inCharacterRoot: str) -> Tuple[List[str], List[str]]:
    """캐릭터 루트 아래 스켈레탈 메쉬 경로와 전체 에셋 경로를 레지스트리에서 모은다.

    에셋을 로드하지 않는다.

    Args:
        inCharacterRoot: 캐릭터 루트 패키지 폴더

    Returns:
        (스켈레탈 메쉬 패키지 경로 목록, 전체 에셋 패키지 경로 목록)
    """
    root = mutableRules.to_package_path(inCharacterRoot)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous([root], False)
    meshes: List[str] = []
    everything: List[str] = []
    for data in registry.get_assets_by_path(root, recursive=True):
        packageName = str(data.package_name)
        everything.append(packageName)
        if str(data.asset_class_path.asset_name) == "SkeletalMesh":
            meshes.append(packageName)
    return sorted(meshes), sorted(everything)


# ---------------------------------------------------------------------------
# 파사드
# ---------------------------------------------------------------------------


class MutableObjectBuilder:
    """캐릭터 1명의 Base CO + 슬롯 CO를 템플릿 복제로 만든다.

    `build_plan`은 에셋을 바꾸지 않는다(레지스트리 스캔·템플릿/메쉬 읽기만). `apply_plan`이
    확인 후 적용한다. 드라이런은 복제도 저장도 하지 않는다.

    **P4 CL 정리(신규 파일이 들어간 default CL의 이동·서밋·누출 검사)는 호출자 책임이다.**
    """

    def __init__(self, inConfig):
        """빌더를 만든다.

        Args:
            inConfig: `mutableRules.MutableBuildConfig`
        """
        inConfig.validate()
        self._config = inConfig

    # -- 계획 -------------------------------------------------------------

    def build_plan(self, inCharacterRoot: str):
        """캐릭터 루트의 생성 계획을 바인딩까지 채워 만든다. 에셋을 바꾸지 않는다.

        Args:
            inCharacterRoot: 캐릭터 루트 패키지 폴더

        Returns:
            `mutableRules.CharacterPlan`
        """
        meshPaths, existingPaths = scan_character_assets(inCharacterRoot)
        slotNames = sorted({path.split("/")[-2] for path in meshPaths})
        templateSlots = [
            slot for slot in slotNames
            if unreal.EditorAssetLibrary.does_asset_exist(self._config.slot_template_path(slot))
        ]
        existing = list(existingPaths)
        plan = mutableRules.build_character_plan(inCharacterRoot, meshPaths, existing, templateSlots, self._config)
        baseGroupNames = self._plan_base(plan)
        for slotPlan in plan.slots:
            if slotPlan.status == mutableRules.STATUS_PENDING:
                self._plan_slot(plan, slotPlan, baseGroupNames)
        _log(f"계획: {plan.characterRoot} base={plan.base.status} "
             f"slots={[(s.outfit, s.slot, s.status) for s in plan.slots]}")
        return plan

    def _plan_base(self, inPlan) -> Optional[List[str]]:
        """Base 계획에 Component 바인딩(신규) 또는 그룹 GUID(기존)를 채운다.

        Args:
            inPlan: 캐릭터 계획

        Returns:
            Base가 갖게 될 그룹 이름 목록(알 수 없으면 None)
        """
        base = inPlan.base
        try:
            if base.status == mutableRules.STATUS_SKIPPED_EXISTS:
                base.groupGuids = read_group_guids(_load_asset(base.assetPath))
                return sorted(base.groupGuids)
            if base.status != mutableRules.STATUS_PENDING:
                return None
            if not unreal.EditorAssetLibrary.does_asset_exist(base.templatePath):
                base.status = mutableRules.FAILED_TEMPLATE_INVALID
                base.detail = f"Base 템플릿이 없다: {base.templatePath}"
                return None
            template = _load_asset(base.templatePath)
            placeholders = [
                node_value_path(node, PROP_REFERENCE_MESH)
                for node in list_graph_nodes(template, NODE_COMPONENT_MESH)
            ]
            result = mutableRules.resolve_component_bindings(
                [p for p in placeholders if p], base.partMeshes
            )
            if result.failure:
                base.status, base.detail = result.failure, result.detail
                return None
            base.componentBindings = result.bindings
            return sorted(
                str(node.get_editor_property(PROP_GROUP_NAME))
                for node in list_graph_nodes(template, NODE_GROUP)
            )
        except Exception as planError:  # noqa: BLE001 - 계획 실패를 결과로 남긴다
            base.status = mutableRules.FAILED_EXCEPTION
            base.detail = f"{type(planError).__name__}: {planError}"
            return None

    def _plan_slot(self, inPlan, inSlotPlan, inBaseGroupNames: Optional[List[str]]) -> None:
        """슬롯 계획에 메쉬·매테리얼 바인딩(과 기존 Base면 그룹 GUID)을 채운다.

        Args:
            inPlan: 캐릭터 계획
            inSlotPlan: 슬롯 계획
            inBaseGroupNames: Base 그룹 이름 목록
        """
        try:
            if inPlan.base.status not in (mutableRules.STATUS_PENDING, mutableRules.STATUS_SKIPPED_EXISTS):
                inSlotPlan.status = mutableRules.FAILED_BASE_UNAVAILABLE
                inSlotPlan.detail = f"Base CO를 쓸 수 없다({inPlan.base.status})"
                return
            if inBaseGroupNames is not None and inSlotPlan.slot not in inBaseGroupNames:
                inSlotPlan.status = mutableRules.FAILED_GROUP_MISSING
                inSlotPlan.detail = f"Base에 '{inSlotPlan.slot}' 그룹이 없다. 있는 그룹: {', '.join(inBaseGroupNames)}"
                return
            if inPlan.base.status == mutableRules.STATUS_SKIPPED_EXISTS:
                guid, failure, detail = mutableRules.resolve_group_guid(inPlan.base.groupGuids, inSlotPlan.slot)
                if failure:
                    inSlotPlan.status, inSlotPlan.detail = failure, detail
                    return
                inSlotPlan.groupGuid = guid

            template = _load_asset(inSlotPlan.templatePath)
            if len(list_graph_nodes(template, NODE_OBJECT)) != 1:
                inSlotPlan.status = mutableRules.FAILED_TEMPLATE_INVALID
                inSlotPlan.detail = "슬롯 템플릿의 Base Object 노드가 1개가 아니다"
                return
            placeholders = [node_value_path(n, PROP_SKELETAL_MESH) for n in list_graph_nodes(template, NODE_SKELETAL_MESH)]
            meshResult = mutableRules.resolve_mesh_bindings(
                [p for p in placeholders if p], inSlotPlan.slot, inSlotPlan.meshPath, inSlotPlan.outfitPartMeshes
            )
            if meshResult.failure:
                inSlotPlan.status, inSlotPlan.detail = meshResult.failure, meshResult.detail
                return
            sectionMaterials = [node_value_path(n, PROP_MATERIAL) for n in list_graph_nodes(template, NODE_MATERIAL)]
            placeholderMaterials = {src: mesh_material_paths(src) for src, _ in meshResult.bindings}
            targetMaterials = {dst: mesh_material_paths(dst) for _, dst in meshResult.bindings}
            materialResult = mutableRules.resolve_material_bindings(
                [m for m in sectionMaterials if m], placeholderMaterials, meshResult.bindings, targetMaterials
            )
            if materialResult.failure:
                inSlotPlan.status, inSlotPlan.detail = materialResult.failure, materialResult.detail
                return
            inSlotPlan.meshBindings = meshResult.bindings
            inSlotPlan.materialBindings = materialResult.bindings
        except Exception as planError:  # noqa: BLE001
            inSlotPlan.status = mutableRules.FAILED_EXCEPTION
            inSlotPlan.detail = f"{type(planError).__name__}: {planError}"

    # -- 적용 -------------------------------------------------------------

    def apply_plan(self, inPlan, inDryRun: bool = True) -> Dict:
        """계획을 적용한다.

        드라이런은 아무것도 복제·저장하지 않고 계획을 그대로 돌려준다. 실집행은 Base -> 슬롯
        순으로, CO 하나씩 복제 -> 노드 쓰기 + 되읽기 -> T3D 검증 -> 저장한다. 한 CO의 실패가
        나머지를 멈추지 않는다(Base 실패면 슬롯은 `failed:baseUnavailable`).

        Args:
            inPlan: `build_plan` 결과
            inDryRun: 드라이런 여부. 기본 True.

        Returns:
            결과 dict(`mutableRules.plan_to_dict` + `dryRun` / `savedPaths`)
        """
        savedPaths: List[str] = []
        if not inDryRun:
            baseAsset = self._apply_base(inPlan.base, savedPaths)
            for slotPlan in inPlan.slots:
                if slotPlan.status != mutableRules.STATUS_PENDING:
                    continue
                if baseAsset is None:
                    slotPlan.status = mutableRules.FAILED_BASE_UNAVAILABLE
                    slotPlan.detail = f"Base CO를 쓸 수 없다({inPlan.base.status})"
                    continue
                self._apply_slot(slotPlan, inPlan.base, baseAsset, savedPaths)
        result = mutableRules.plan_to_dict(inPlan)
        result["dryRun"] = inDryRun
        result["savedPaths"] = savedPaths
        _log(f"적용 완료(dryRun={inDryRun}): {result['statusCounts']}, 저장 {len(savedPaths)}건")
        return result

    def _apply_base(self, inBase, inSavedPaths: List[str]):
        """Base CO를 만든다(또는 기존 것을 로드한다).

        Args:
            inBase: Base 계획
            inSavedPaths: 저장 경로 누적 목록

        Returns:
            슬롯의 Parent로 쓸 Base 에셋. 쓸 수 없으면 None.
        """
        if inBase.status == mutableRules.STATUS_SKIPPED_EXISTS:
            try:
                return _load_asset(inBase.assetPath)
            except Exception as loadError:  # noqa: BLE001
                inBase.status = mutableRules.FAILED_BASE_UNAVAILABLE
                inBase.detail = f"기존 Base 로드 실패: {loadError}"
                return None
        if inBase.status != mutableRules.STATUS_PENDING:
            return None
        if _asset_exists(inBase.assetPath):
            # 계획 이후 생겼다 - 덮어쓰지 않고 재사용한다(D-Q4)
            inBase.status = mutableRules.STATUS_SKIPPED_EXISTS
            inBase.detail = "계획 이후 생긴 기존 Base를 재사용한다"
            asset = _load_asset(inBase.assetPath)
            inBase.groupGuids = read_group_guids(asset)
            return asset

        duplicated = None
        try:
            duplicated = unreal.EditorAssetLibrary.duplicate_asset(inBase.templatePath, inBase.assetPath)
            if duplicated is None:
                return self._fail(inBase, mutableRules.FAILED_EXCEPTION, "duplicate_asset이 None을 돌려줬다", None)
            bindings = {mutableRules.to_package_path(src): dst for src, dst in inBase.componentBindings}
            for node in list_graph_nodes(duplicated, NODE_COMPONENT_MESH):
                placeholder = node_value_path(node, PROP_REFERENCE_MESH)
                target = bindings.get(mutableRules.to_package_path(placeholder or ""))
                if target is None:
                    return self._fail(inBase, mutableRules.FAILED_PLACEHOLDER_AMBIGUOUS,
                                      f"복제본 Component 플레이스홀더가 계획과 다르다: {placeholder}", duplicated)
                if not set_node_asset_verified(node, PROP_REFERENCE_MESH, _load_asset(target)):
                    return self._fail(inBase, mutableRules.FAILED_WRITE_NOT_VERIFIED,
                                      f"Component 메쉬 되읽기 불일치: {target}", duplicated)
            objectNodes = list_graph_nodes(duplicated, NODE_OBJECT)
            if len(objectNodes) != 1:
                return self._fail(inBase, mutableRules.FAILED_TEMPLATE_INVALID,
                                  f"Base Object 노드가 {len(objectNodes)}개다", duplicated)
            write_object_name(objectNodes[0], inBase.objectName)
            exported = export_t3d_text(duplicated)
            names = mutableRules.read_t3d_property(exported, NODE_OBJECT, PROP_OBJECT_NAME)
            if names != [inBase.objectName]:
                return self._fail(inBase, mutableRules.FAILED_WRITE_NOT_VERIFIED,
                                  f"Base Object 이름 되읽기 불일치: {names}", duplicated)
            inBase.groupGuids = mutableRules.parse_group_guids_t3d(exported)
            if not self._save(inBase, inSavedPaths):
                return None
            inBase.status = mutableRules.STATUS_CREATED
            _log(f"Base 생성: {inBase.assetPath}")
            return duplicated
        except Exception as applyError:  # noqa: BLE001 - 한 CO의 실패가 목록을 멈추지 않게
            return self._fail(inBase, mutableRules.FAILED_EXCEPTION,
                              f"{type(applyError).__name__}: {applyError}", duplicated)

    def _apply_slot(self, inSlot, inBase, inBaseAsset, inSavedPaths: List[str]) -> None:
        """슬롯 CO 1개를 만든다.

        Args:
            inSlot: 슬롯 계획
            inBase: Base 계획(그룹 GUID 맵)
            inBaseAsset: Parent로 쓸 Base 에셋
            inSavedPaths: 저장 경로 누적 목록
        """
        guid, failure, detail = mutableRules.resolve_group_guid(inBase.groupGuids, inSlot.slot)
        if failure:
            inSlot.status, inSlot.detail = failure, detail
            return
        inSlot.groupGuid = guid
        if _asset_exists(inSlot.assetPath):
            inSlot.status = mutableRules.STATUS_SKIPPED_EXISTS
            inSlot.detail = "계획 이후 대상 CO가 생겼다"
            return

        duplicated = None
        try:
            duplicated = unreal.EditorAssetLibrary.duplicate_asset(inSlot.templatePath, inSlot.assetPath)
            if duplicated is None:
                self._fail(inSlot, mutableRules.FAILED_EXCEPTION, "duplicate_asset이 None을 돌려줬다", None)
                return
            if not self._write_slot_nodes(inSlot, duplicated, inBaseAsset):
                return
            names = read_object_names(duplicated)
            if names != [inSlot.objectName]:
                self._fail(inSlot, mutableRules.FAILED_WRITE_NOT_VERIFIED,
                           f"슬롯 Base Object 이름 되읽기 불일치: {names}", duplicated)
                return
            if self._save(inSlot, inSavedPaths):
                inSlot.status = mutableRules.STATUS_CREATED
                _log(f"슬롯 생성: {inSlot.assetPath} (group={inSlot.slot})")
        except Exception as applyError:  # noqa: BLE001
            self._fail(inSlot, mutableRules.FAILED_EXCEPTION, f"{type(applyError).__name__}: {applyError}", duplicated)

    def _write_slot_nodes(self, inSlot, inDuplicated, inBaseAsset) -> bool:
        """복제된 슬롯 CO의 SK·매테리얼·Parent·그룹·이름을 쓰고 되읽는다.

        Args:
            inSlot: 슬롯 계획
            inDuplicated: 복제본
            inBaseAsset: Parent로 쓸 Base 에셋

        Returns:
            전부 확인되면 True(실패면 `_fail`까지 처리하고 False)
        """
        meshBindings = {mutableRules.to_package_path(src): dst for src, dst in inSlot.meshBindings}
        for node in list_graph_nodes(inDuplicated, NODE_SKELETAL_MESH):
            placeholder = node_value_path(node, PROP_SKELETAL_MESH)
            target = meshBindings.get(mutableRules.to_package_path(placeholder or ""))
            if target is None or not set_node_asset_verified(node, PROP_SKELETAL_MESH, _load_asset(target)):
                self._fail(inSlot, mutableRules.FAILED_WRITE_NOT_VERIFIED,
                           f"SK 노드 쓰기 실패(플레이스홀더 {placeholder} -> {target})", inDuplicated)
                return False
        materialBindings = {mutableRules.to_package_path(src): dst for src, dst in inSlot.materialBindings}
        for node in list_graph_nodes(inDuplicated, NODE_MATERIAL):
            placeholder = node_value_path(node, PROP_MATERIAL)
            target = materialBindings.get(mutableRules.to_package_path(placeholder or ""))
            if target is None or not set_node_asset_verified(node, PROP_MATERIAL, _load_asset(target)):
                self._fail(inSlot, mutableRules.FAILED_WRITE_NOT_VERIFIED,
                           f"Mesh Section 매테리얼 쓰기 실패(플레이스홀더 {placeholder} -> {target})", inDuplicated)
                return False
        objectNodes = list_graph_nodes(inDuplicated, NODE_OBJECT)
        if len(objectNodes) != 1:
            self._fail(inSlot, mutableRules.FAILED_TEMPLATE_INVALID,
                       f"Base Object 노드가 {len(objectNodes)}개다", inDuplicated)
            return False
        objectNode = objectNodes[0]
        if not set_node_asset_verified(objectNode, PROP_PARENT_OBJECT, inBaseAsset):
            self._fail(inSlot, mutableRules.FAILED_WRITE_NOT_VERIFIED, "ParentObject 되읽기 불일치", inDuplicated)
            return False
        if not set_group_id_verified(objectNode, inSlot.groupGuid):
            self._fail(inSlot, mutableRules.FAILED_WRITE_NOT_VERIFIED, "ParentObjectGroupId 되읽기 불일치", inDuplicated)
            return False
        write_object_name(objectNode, inSlot.objectName)
        return True

    @staticmethod
    def _save(inPlanItem, inSavedPaths: List[str]) -> bool:
        """신규 CO 1개를 저장하고 디스크 존재를 확인한다.

        Args:
            inPlanItem: Base 또는 슬롯 계획
            inSavedPaths: 저장 경로 누적 목록

        Returns:
            저장 확인되면 True(실패면 상태를 `failed:saveFailed`로 바꾼다)
        """
        saved = unreal.EditorAssetLibrary.save_asset(inPlanItem.assetPath, only_if_is_dirty=False)
        filePath = package_file_path(inPlanItem.assetPath)
        if not saved or not filePath or not os.path.exists(filePath):
            inPlanItem.status = mutableRules.FAILED_SAVE
            inPlanItem.detail = f"save_asset={saved}, 파일 존재={bool(filePath and os.path.exists(filePath))}"
            _log_error(f"저장 실패: {inPlanItem.assetPath} ({inPlanItem.detail})")
            return False
        inSavedPaths.append(inPlanItem.assetPath)
        return True

    @staticmethod
    def _fail(inPlanItem, inCode: str, inDetail: str, inDuplicated):
        """CO 1개를 실패로 기록하고, 저장하지 않은 복제본을 메모리에서 지운다.

        Args:
            inPlanItem: Base 또는 슬롯 계획
            inCode: 실패 코드
            inDetail: 설명
            inDuplicated: 지울 복제본(없으면 None)

        Returns:
            항상 None(호출부가 `return self._fail(...)`로 쓴다)
        """
        inPlanItem.status = inCode
        inPlanItem.detail = inDetail
        _log_warning(f"실패 {inCode}: {inPlanItem.assetPath} - {inDetail}")
        if inDuplicated is not None:
            try:
                unreal.EditorAssetLibrary.delete_asset(inPlanItem.assetPath)
            except Exception as deleteError:  # noqa: BLE001
                inPlanItem.detail += f" (복제본 삭제 실패: {deleteError})"
            filePath = package_file_path(inPlanItem.assetPath)
            if filePath and os.path.exists(filePath):
                inPlanItem.detail += f" (디스크에 남음: {filePath})"
        return None


def summarize_result(inResult: Dict) -> List[str]:
    """결과 dict를 사람이 읽을 줄 목록으로 요약한다.

    Args:
        inResult: `apply_plan` 결과

    Returns:
        요약 줄 목록
    """
    lines = [
        f"캐릭터: {inResult['character']} (역할 {inResult['role'] or '?'}) dryRun={inResult.get('dryRun')}",
        f"Base: {inResult['base']['status']} {inResult['base']['assetPath']} {inResult['base']['detail']}".rstrip(),
    ]
    for slot in inResult["slots"]:
        lines.append(f"  [{slot['status']}] {slot['outfit']}/{slot['slot']} -> {slot['assetPath']} {slot['detail']}".rstrip())
    for outfit, slot, mesh in inResult.get("noTemplateUnconsumed", []):
        lines.append(f"  [{mutableRules.STATUS_SKIPPED_NO_TEMPLATE}] {outfit}/{slot} {mesh}")
    lines.append(f"제외 {len(inResult.get('ignored', []))}건, 저장 {len(inResult.get('savedPaths', []))}건, "
                 f"집계 {inResult['statusCounts']}")
    return lines
