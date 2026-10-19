#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Mutable Customizable Object 생성 계획 결정 (unreal 비의존 순수 로직)

캐릭터 폴더의 스켈레탈 메쉬 목록을 받아 "어떤 CO를 어디에 무슨 이름으로 만들고,
템플릿의 어느 노드를 어느 메쉬/매테리얼/그룹으로 바꿀지"만 결정한다. 에셋을 복제하고
노드를 고치는 일은 `inUnreal/mutableObjects.py`가 하고, 이 모듈은 그 결정을 한 곳에 모은다.

**이 모듈은 표준 라이브러리만 쓴다 - 편의가 아니라 요구사항이다.** UE5 임베디드
파이썬에는 pyjallib 전체가 import되지 않으므로(`pyjallib/__init__`이 P4Python을
끌어온다), 인-UE5 어댑터와 콘솔 테스트가 **같은 결정 함수**를 쓰려면 이 모듈이
stdlib만 의존해야 한다(`.claude/references/ue5/silent_write_paths.md` §7).

폴더 규약 (호출자가 `MutableBuildConfig`로 주입한다 - 프로젝트 규약은 상수로 두지 않는다):

    {characterRoot}/{meshFolder}/{outfit}/{slot}/{meshPrefix}{character}_{role}_{outfit}_{slot}
    {characterRoot}/{mutableFolder}/{baseAssetName}          <- Base CO
    {characterRoot}/{meshFolder}/{outfit}/{slot}/{objectPrefix}{character}_{role}_{outfit}_{slot}
                                                              <- 슬롯 CO (메쉬와 같은 폴더)

노드 식별 규칙 (2026-10-16 Phase 0 실측):

- Python에서 Component 이름·노드 핀 연결은 보이지 않는다. 그래서 템플릿이 노드마다
  박아 둔 **플레이스홀더 메쉬/매테리얼 값**을 식별자로 쓴다.
- 플레이스홀더 메쉬 이름의 마지막 `_` 토큰이 부품명이다(`..._Default_Body` -> `Body`).
- 템플릿 SK 노드가 1개면 그 노드는 슬롯 메쉬로 바꾼다(단일 SK 템플릿은 플레이스홀더가
  슬롯과 무관하게 같을 수 있으므로 토큰을 쓰지 않는다). 여러 개면 부품명으로 같은
  외형의 형제 폴더 메쉬를 찾고, 하나라도 없으면 그 CO는 만들지 않는다(fail-closed).
- Mesh Section 매테리얼은 "플레이스홀더 매테리얼이 플레이스홀더 메쉬의 몇 번째 슬롯인가"를
  찾아 새 메쉬의 같은 인덱스 매테리얼로 바꾼다.
- 그룹 GUID는 Base 그룹 노드의 T3D 익스포트 텍스트에서 읽는다(복제 시 그래프 노드 GUID가
  전부 재생성되고 `NodeGuid`는 Python에서 읽히지 않는다).

매칭이 0건이거나 2건 이상이면 추측하지 않고 실패 사유를 남긴다.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

STATUS_PENDING = "pending"
"""계획됨 - 아직 적용하지 않았다(드라이런 결과도 이 상태로 남는다)."""

STATUS_CREATED = "created"
"""생성·검증·저장까지 끝났다."""

STATUS_SKIPPED_EXISTS = "skipped:exists"
"""대상 CO가 이미 있다 - 덮어쓰지 않는다. Base면 기존 것을 슬롯의 Parent로 재사용한다."""

STATUS_SKIPPED_NO_TEMPLATE = "skipped:noTemplate"
"""슬롯 폴더에 대응하는 슬롯 템플릿이 없다."""

FAILED_NAME_MISMATCH = "failed:nameMismatch"
FAILED_ROLE_MISMATCH = "failed:roleMismatch"
FAILED_MULTIPLE_MESHES = "failed:multipleMeshes"
FAILED_MISSING_BASE_MESH = "failed:missingBaseMesh"
FAILED_MISSING_PART_MESH = "failed:missingPartMesh"
FAILED_PLACEHOLDER_AMBIGUOUS = "failed:placeholderAmbiguous"
FAILED_MATERIAL_MISSING = "failed:materialMissing"
FAILED_GROUP_MISSING = "failed:groupMissing"
FAILED_GROUP_AMBIGUOUS = "failed:groupAmbiguous"
FAILED_BASE_UNAVAILABLE = "failed:baseUnavailable"
FAILED_TEMPLATE_INVALID = "failed:templateInvalid"
FAILED_WRITE_NOT_VERIFIED = "failed:writeNotVerified"
FAILED_SAVE = "failed:saveFailed"
FAILED_EXCEPTION = "failed:exception"
"""적용 중 예외 - 한 CO의 실패가 나머지를 멈추지 않게 결과로 흡수한 것."""

FAILURE_CODES = (
    FAILED_NAME_MISMATCH,
    FAILED_ROLE_MISMATCH,
    FAILED_MULTIPLE_MESHES,
    FAILED_MISSING_BASE_MESH,
    FAILED_MISSING_PART_MESH,
    FAILED_PLACEHOLDER_AMBIGUOUS,
    FAILED_MATERIAL_MISSING,
    FAILED_GROUP_MISSING,
    FAILED_GROUP_AMBIGUOUS,
    FAILED_BASE_UNAVAILABLE,
    FAILED_TEMPLATE_INVALID,
    FAILED_WRITE_NOT_VERIFIED,
    FAILED_SAVE,
    FAILED_EXCEPTION,
)
"""실패 사유 코드 전체. 결과 JSON을 읽는 쪽이 집계 키로 쓴다."""

IGNORED_NOT_SLOT_MESH = "ignored:notSlotMesh"
"""`{meshFolder}/{outfit}/{slot}/` 깊이가 아니다(예: 외형 폴더 직하 메쉬)."""

IGNORED_NOT_MESH_PREFIX = "ignored:notMeshPrefix"
"""메쉬 접두(`SK_` 등)로 시작하지 않는다."""

IGNORED_EXCLUDED_OUTFIT = "ignored:excludedOutfit"
"""설정의 제외 외형이다."""

IGNORED_OUTSIDE_MESH_FOLDER = "ignored:outsideMeshFolder"
"""캐릭터의 메쉬 폴더 밖이다."""

_GUID_PATTERN = re.compile(r"^[0-9A-Fa-f]{32}$")


class MutableConfigError(ValueError):
    """설정이 결정을 내릴 수 없게 비어 있거나 형식이 틀린 경우의 오류."""


@dataclass(frozen=True)
class MutableBuildConfig:
    """CO 생성 규약. 프로젝트 규약 값은 전부 호출자가 넣는다(기본값 없음).

    Attributes:
        baseTemplatePath: Base CO 템플릿 패키지 경로
        slotTemplatePattern: 슬롯 템플릿 패키지 경로 형식. `{slot}` 자리표시자 필수.
        meshFolderName: 캐릭터 루트 아래 메쉬 폴더 이름
        mutableFolderName: 캐릭터 루트 아래 Base CO를 둘 폴더 이름
        baseOutfit: Base CO의 Component 메쉬를 가져올 외형 이름
        excludedOutfits: 슬롯 CO를 만들지 않을 외형 이름들
        meshPrefix: 스켈레탈 메쉬 에셋 이름 접두
        objectPrefix: CO 에셋 이름 접두(슬롯 CO 이름 = 메쉬 이름의 접두만 바꾼 것)
        baseAssetNameFormat: Base CO 에셋 이름 형식. `{character}` `{role}` 사용 가능.
        baseObjectNameFormat: Base CO의 Base Object 노드 이름 형식. `{character}` `{role}`.
        slotObjectNameFormat: 슬롯 CO의 Base Object 노드 이름 형식.
            `{character}` `{role}` `{outfit}` `{slot}` 사용 가능.
    """

    baseTemplatePath: str
    slotTemplatePattern: str
    meshFolderName: str
    mutableFolderName: str
    baseOutfit: str
    excludedOutfits: Tuple[str, ...] = ()
    meshPrefix: str = "SK_"
    objectPrefix: str = "CO_"
    baseAssetNameFormat: str = "{objectPrefix}{character}_{role}_Base"
    baseObjectNameFormat: str = "{character}_{role}"
    slotObjectNameFormat: str = "{outfit}"

    def validate(self) -> None:
        """설정이 결정을 내릴 수 있는 상태인지 확인한다.

        Raises:
            MutableConfigError: 필수 값이 비었거나 형식 자리표시자가 없음
        """
        required = {
            "baseTemplatePath": self.baseTemplatePath,
            "slotTemplatePattern": self.slotTemplatePattern,
            "meshFolderName": self.meshFolderName,
            "mutableFolderName": self.mutableFolderName,
            "baseOutfit": self.baseOutfit,
            "meshPrefix": self.meshPrefix,
            "objectPrefix": self.objectPrefix,
        }
        empty = [name for name, value in required.items() if not value]
        if empty:
            raise MutableConfigError(f"필수 설정이 비었다: {', '.join(empty)}")
        if "{slot}" not in self.slotTemplatePattern:
            raise MutableConfigError("slotTemplatePattern에 {slot} 자리표시자가 없다")

    def slot_template_path(self, inSlot: str) -> str:
        """슬롯 이름의 템플릿 패키지 경로.

        Args:
            inSlot: 슬롯 이름

        Returns:
            패키지 경로
        """
        return self.slotTemplatePattern.format(slot=inSlot)


@dataclass
class BaseObjectPlan:
    """Base CO 1개의 생성 계획.

    Attributes:
        assetPath: 만들 CO 패키지 경로
        objectName: Base Object 노드에 쓸 이름
        templatePath: 복제할 템플릿 패키지 경로
        partMeshes: 기준 외형의 {부품(슬롯) 이름: 메쉬 패키지 경로}
        status: 상태(`STATUS_*` / `FAILED_*`)
        detail: 상태 사유 설명
        componentBindings: [(플레이스홀더 메쉬, 새 메쉬)] - Component 순서
        groupGuids: {그룹 이름: [NodeGuid...]} - 적용 시 채운다
    """

    assetPath: str
    objectName: str
    templatePath: str
    partMeshes: Dict[str, str]
    status: str = STATUS_PENDING
    detail: str = ""
    componentBindings: List[Tuple[str, str]] = field(default_factory=list)
    groupGuids: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class SlotObjectPlan:
    """슬롯 CO 1개의 생성 계획.

    Attributes:
        outfit: 외형 이름
        slot: 슬롯 이름
        meshPath: 슬롯 메쉬 패키지 경로
        assetPath: 만들 CO 패키지 경로
        objectName: Base Object 노드에 쓸 이름
        templatePath: 복제할 슬롯 템플릿 패키지 경로
        outfitPartMeshes: 같은 외형의 {슬롯 폴더 이름: 메쉬 패키지 경로}(다중 SK 템플릿용)
        status: 상태
        detail: 상태 사유 설명
        meshBindings: [(플레이스홀더 메쉬, 새 메쉬)] - SK 노드 순서
        materialBindings: [(플레이스홀더 매테리얼, 새 매테리얼)] - Mesh Section 노드 순서
        groupGuid: 붙일 Base 그룹의 NodeGuid(32 hex) - 적용 시 채운다
    """

    outfit: str
    slot: str
    meshPath: str
    assetPath: str
    objectName: str
    templatePath: str
    outfitPartMeshes: Dict[str, str]
    status: str = STATUS_PENDING
    detail: str = ""
    meshBindings: List[Tuple[str, str]] = field(default_factory=list)
    materialBindings: List[Tuple[str, str]] = field(default_factory=list)
    groupGuid: str = ""


@dataclass
class CharacterPlan:
    """캐릭터 1명의 CO 생성 계획 전체.

    Attributes:
        characterRoot: 캐릭터 루트 패키지 폴더
        character: 캐릭터 이름(루트 폴더명)
        role: 메쉬 이름에서 읽은 역할 약어(못 읽으면 빈 문자열)
        base: Base CO 계획
        slots: 슬롯 CO 계획 목록(외형·슬롯 이름순)
        noTemplate: 템플릿이 없는 슬롯 폴더 [(외형, 슬롯, 메쉬 경로)]
        ignored: 대상에서 뺀 메쉬 [(메쉬 경로, 사유 코드)]
    """

    characterRoot: str
    character: str
    role: str
    base: BaseObjectPlan
    slots: List[SlotObjectPlan] = field(default_factory=list)
    noTemplate: List[Tuple[str, str, str]] = field(default_factory=list)
    ignored: List[Tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 경로·이름
# ---------------------------------------------------------------------------


def to_package_path(inPath: str) -> str:
    """오브젝트 경로(`/Game/A/B.B`)를 패키지 경로(`/Game/A/B`)로 바꾼다.

    `.` 절단은 마지막 `/` 뒤 세그먼트에만 한다 - 폴더명에 `.`이 있으면 경로 중간이 잘린다
    (`.claude/references/ue5/path_rules.md`). 끝의 `/`도 떼어 낸다.

    Args:
        inPath: 패키지 또는 오브젝트 경로

    Returns:
        패키지 경로
    """
    text = str(inPath).strip().rstrip("/")
    head, separator, tail = text.rpartition("/")
    if "." in tail:
        tail = tail.split(".", 1)[0]
    return f"{head}{separator}{tail}"


def asset_name(inPath: str) -> str:
    """경로의 에셋 이름.

    Args:
        inPath: 패키지 또는 오브젝트 경로

    Returns:
        마지막 세그먼트(오브젝트 접미 제외)
    """
    return to_package_path(inPath).rsplit("/", 1)[-1]


def placeholder_part(inPlaceholderPath: str) -> str:
    """플레이스홀더 메쉬 경로에서 부품명(이름의 마지막 `_` 토큰)을 읽는다.

    Args:
        inPlaceholderPath: 플레이스홀더 메쉬 경로

    Returns:
        부품명. `_`가 없으면 이름 전체.
    """
    return asset_name(inPlaceholderPath).rsplit("_", 1)[-1]


def parse_mesh_role(inMeshName: str, inCharacter: str, inOutfit: str, inSlot: str, inMeshPrefix: str) -> Optional[str]:
    """`{prefix}{character}_{role}_{outfit}_{slot}`에서 역할 약어를 읽는다.

    `_`로 쪼개지 않는다 - 캐릭터 이름에 `_`가 있을 수 있다(`KimDokja_test`). 폴더에서 아는
    토큰을 앞뒤로 맞추고 가운데를 역할 약어로 읽는다.

    Args:
        inMeshName: 메쉬 에셋 이름
        inCharacter: 캐릭터 이름(루트 폴더명)
        inOutfit: 외형 이름(폴더명)
        inSlot: 슬롯 이름(폴더명)
        inMeshPrefix: 메쉬 접두

    Returns:
        역할 약어. 형식이 맞지 않으면 None.
    """
    prefix = f"{inMeshPrefix}{inCharacter}_"
    suffix = f"_{inOutfit}_{inSlot}"
    if not (inMeshName.startswith(prefix) and inMeshName.endswith(suffix)):
        return None
    if len(inMeshName) <= len(prefix) + len(suffix):
        return None
    role = inMeshName[len(prefix):len(inMeshName) - len(suffix)]
    if not role or "_" in role:
        return None
    return role


def slot_object_asset_name(inMeshName: str, inConfig: MutableBuildConfig) -> str:
    """슬롯 CO 에셋 이름 - 메쉬 이름의 메쉬 접두를 CO 접두로 바꾼 것.

    Args:
        inMeshName: 메쉬 에셋 이름(메쉬 접두로 시작한다고 가정)
        inConfig: 생성 규약

    Returns:
        CO 에셋 이름
    """
    return inConfig.objectPrefix + inMeshName[len(inConfig.meshPrefix):]


def base_object_asset_path(inCharacterRoot: str, inCharacter: str, inRole: str, inConfig: MutableBuildConfig) -> str:
    """Base CO 패키지 경로.

    Args:
        inCharacterRoot: 캐릭터 루트 패키지 폴더
        inCharacter: 캐릭터 이름
        inRole: 역할 약어
        inConfig: 생성 규약

    Returns:
        패키지 경로
    """
    name = inConfig.baseAssetNameFormat.format(
        objectPrefix=inConfig.objectPrefix, character=inCharacter, role=inRole
    )
    return f"{to_package_path(inCharacterRoot)}/{inConfig.mutableFolderName}/{name}"


# ---------------------------------------------------------------------------
# 계획
# ---------------------------------------------------------------------------


def _classify_meshes(
    inRoot: str, inCharacter: str, inMeshPaths: Sequence[str], inConfig: MutableBuildConfig
) -> Tuple[Dict[str, Dict[str, List[str]]], List[Tuple[str, str]]]:
    """메쉬 경로를 {외형: {슬롯: [경로...]}}로 묶고 대상 밖은 사유와 함께 뺀다.

    Args:
        inRoot: 캐릭터 루트(패키지 경로)
        inCharacter: 캐릭터 이름
        inMeshPaths: 캐릭터 루트 아래 스켈레탈 메쉬 경로 목록
        inConfig: 생성 규약

    Returns:
        (외형별 슬롯 메쉬, 제외 목록)
    """
    meshRoot = f"{inRoot}/{inConfig.meshFolderName}/"
    grouped: Dict[str, Dict[str, List[str]]] = {}
    ignored: List[Tuple[str, str]] = []
    for rawPath in inMeshPaths:
        path = to_package_path(rawPath)
        if not path.startswith(meshRoot):
            ignored.append((path, IGNORED_OUTSIDE_MESH_FOLDER))
            continue
        parts = path[len(meshRoot):].split("/")
        if len(parts) != 3:
            ignored.append((path, IGNORED_NOT_SLOT_MESH))
            continue
        outfit, slot, name = parts
        if not name.startswith(inConfig.meshPrefix):
            ignored.append((path, IGNORED_NOT_MESH_PREFIX))
            continue
        if outfit in inConfig.excludedOutfits:
            ignored.append((path, IGNORED_EXCLUDED_OUTFIT))
            continue
        grouped.setdefault(outfit, {}).setdefault(slot, []).append(path)
    return grouped, ignored


def build_character_plan(
    inCharacterRoot: str,
    inMeshPaths: Sequence[str],
    inExistingPaths: Sequence[str],
    inTemplateSlots: Sequence[str],
    inConfig: MutableBuildConfig,
) -> CharacterPlan:
    """캐릭터 1명의 CO 생성 계획을 세운다(바인딩은 템플릿을 읽은 뒤 채운다).

    Args:
        inCharacterRoot: 캐릭터 루트 패키지 폴더(`/Game/.../{Role}/{Character}`)
        inMeshPaths: 루트 아래 스켈레탈 메쉬 경로 목록
        inExistingPaths: 이미 있는 에셋 경로 목록(대상 CO 존재 판정용)
        inTemplateSlots: 슬롯 템플릿이 실제로 있는 슬롯 이름들
        inConfig: 생성 규약

    Returns:
        계획

    Raises:
        MutableConfigError: 설정이 비었거나 형식이 틀림
    """
    inConfig.validate()
    root = to_package_path(inCharacterRoot)
    character = root.rsplit("/", 1)[-1]
    existing = {to_package_path(path) for path in inExistingPaths}
    templateSlots = set(inTemplateSlots)
    grouped, ignored = _classify_meshes(root, character, inMeshPaths, inConfig)

    roles = set()
    slotEntries: List[Tuple[str, str, str, Optional[str], str]] = []
    noTemplate: List[Tuple[str, str, str]] = []
    for outfit in sorted(grouped):
        for slot in sorted(grouped[outfit]):
            paths = sorted(grouped[outfit][slot])
            meshPath = paths[0]
            role = parse_mesh_role(asset_name(meshPath), character, outfit, slot, inConfig.meshPrefix)
            if role is not None:
                roles.add(role)
            if slot not in templateSlots:
                noTemplate.append((outfit, slot, meshPath))
                continue
            if len(paths) > 1:
                slotEntries.append((outfit, slot, meshPath, role, FAILED_MULTIPLE_MESHES))
            elif role is None:
                slotEntries.append((outfit, slot, meshPath, role, FAILED_NAME_MISMATCH))
            else:
                slotEntries.append((outfit, slot, meshPath, role, STATUS_PENDING))

    characterRole = next(iter(roles)) if len(roles) == 1 else ""
    basePartMeshes = {
        slot: sorted(paths)[0]
        for slot, paths in grouped.get(inConfig.baseOutfit, {}).items()
    }
    base = BaseObjectPlan(
        assetPath=base_object_asset_path(root, character, characterRole or "{role}", inConfig),
        objectName=inConfig.baseObjectNameFormat.format(character=character, role=characterRole or "{role}"),
        templatePath=inConfig.baseTemplatePath,
        partMeshes=basePartMeshes,
    )
    if len(roles) > 1:
        base.status = FAILED_ROLE_MISMATCH
        base.detail = f"메쉬 이름의 역할 약어가 여러 개다: {', '.join(sorted(roles))}"
    elif not roles:
        base.status = FAILED_NAME_MISMATCH
        base.detail = "규약에 맞는 메쉬 이름이 없어 역할 약어를 읽지 못했다"
    elif base.assetPath in existing:
        base.status = STATUS_SKIPPED_EXISTS
        base.detail = "기존 Base CO를 슬롯의 Parent로 재사용한다"
    elif not basePartMeshes:
        base.status = FAILED_MISSING_BASE_MESH
        base.detail = f"기준 외형 '{inConfig.baseOutfit}'의 메쉬가 없다"

    plan = CharacterPlan(characterRoot=root, character=character, role=characterRole, base=base,
                         noTemplate=noTemplate, ignored=ignored)
    for outfit, slot, meshPath, role, status in slotEntries:
        meshName = asset_name(meshPath)
        folder = meshPath.rsplit("/", 1)[0]
        slotPlan = SlotObjectPlan(
            outfit=outfit,
            slot=slot,
            meshPath=meshPath,
            assetPath=f"{folder}/{slot_object_asset_name(meshName, inConfig)}",
            objectName=inConfig.slotObjectNameFormat.format(
                character=character, role=role or characterRole, outfit=outfit, slot=slot
            ),
            templatePath=inConfig.slot_template_path(slot),
            outfitPartMeshes={name: sorted(paths)[0] for name, paths in grouped[outfit].items()},
            status=status,
        )
        if status == FAILED_MULTIPLE_MESHES:
            slotPlan.detail = f"슬롯 폴더에 메쉬가 여러 개다: {', '.join(sorted(grouped[outfit][slot]))}"
        elif status == FAILED_NAME_MISMATCH:
            slotPlan.detail = f"메쉬 이름이 규약과 다르다: {meshName}"
        elif slotPlan.assetPath in existing:
            slotPlan.status = STATUS_SKIPPED_EXISTS
            slotPlan.detail = "대상 CO가 이미 있다"
        elif base.status not in (STATUS_PENDING, STATUS_SKIPPED_EXISTS):
            slotPlan.status = FAILED_BASE_UNAVAILABLE
            slotPlan.detail = f"Base CO를 쓸 수 없다({base.status})"
        plan.slots.append(slotPlan)
    return plan


# ---------------------------------------------------------------------------
# 바인딩 (템플릿 플레이스홀더 -> 새 값)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BindingResult:
    """바인딩 결정 결과.

    Attributes:
        bindings: [(플레이스홀더, 새 값)] - 입력 순서 보존. 실패면 빈 리스트.
        failure: 실패 사유 코드. 성공이면 빈 문자열.
        detail: 실패 설명
    """

    bindings: List[Tuple[str, str]]
    failure: str = ""
    detail: str = ""


def resolve_component_bindings(inPlaceholders: Sequence[str], inBasePartMeshes: Mapping[str, str]) -> BindingResult:
    """Base 템플릿 Component의 플레이스홀더를 기준 외형 메쉬로 바인딩한다.

    Args:
        inPlaceholders: Component 노드 순서의 플레이스홀더 메쉬 경로
        inBasePartMeshes: 기준 외형의 {부품 이름: 메쉬 경로}

    Returns:
        바인딩 결과
    """
    if not inPlaceholders:
        return BindingResult([], FAILED_TEMPLATE_INVALID, "Base 템플릿에 Component 노드가 없다")
    parts = [placeholder_part(path) for path in inPlaceholders]
    duplicated = sorted({part for part in parts if parts.count(part) > 1})
    if duplicated:
        return BindingResult([], FAILED_PLACEHOLDER_AMBIGUOUS, f"부품명이 겹친다: {', '.join(duplicated)}")
    missing = [part for part in parts if part not in inBasePartMeshes]
    if missing:
        return BindingResult([], FAILED_MISSING_BASE_MESH, f"기준 외형에 없는 부품: {', '.join(missing)}")
    return BindingResult([(path, inBasePartMeshes[part]) for path, part in zip(inPlaceholders, parts)])


def resolve_mesh_bindings(
    inPlaceholders: Sequence[str], inSlot: str, inSlotMesh: str, inOutfitPartMeshes: Mapping[str, str]
) -> BindingResult:
    """슬롯 템플릿 SK 노드의 플레이스홀더를 새 메쉬로 바인딩한다.

    Args:
        inPlaceholders: SK 노드 순서의 플레이스홀더 메쉬 경로
        inSlot: 슬롯 이름
        inSlotMesh: 슬롯 메쉬 경로
        inOutfitPartMeshes: 같은 외형의 {슬롯 폴더 이름: 메쉬 경로}

    Returns:
        바인딩 결과
    """
    if not inPlaceholders:
        return BindingResult([], FAILED_TEMPLATE_INVALID, "슬롯 템플릿에 Skeletal Mesh 노드가 없다")
    if len(inPlaceholders) == 1:
        return BindingResult([(inPlaceholders[0], inSlotMesh)])
    parts = [placeholder_part(path) for path in inPlaceholders]
    duplicated = sorted({part for part in parts if parts.count(part) > 1})
    if duplicated:
        return BindingResult([], FAILED_PLACEHOLDER_AMBIGUOUS, f"부품명이 겹친다: {', '.join(duplicated)}")
    if inSlot not in parts:
        return BindingResult([], FAILED_PLACEHOLDER_AMBIGUOUS, f"플레이스홀더에 슬롯 자신('{inSlot}')이 없다")
    bindings: List[Tuple[str, str]] = []
    missing: List[str] = []
    for path, part in zip(inPlaceholders, parts):
        target = inSlotMesh if part == inSlot else inOutfitPartMeshes.get(part)
        if target is None:
            missing.append(part)
        else:
            bindings.append((path, target))
    if missing:
        return BindingResult([], FAILED_MISSING_PART_MESH, f"같은 외형에 없는 부품 메쉬: {', '.join(missing)}")
    return BindingResult(bindings)


def resolve_material_bindings(
    inSectionMaterials: Sequence[str],
    inPlaceholderMeshMaterials: Mapping[str, Sequence[Optional[str]]],
    inMeshBindings: Sequence[Tuple[str, str]],
    inTargetMeshMaterials: Mapping[str, Sequence[Optional[str]]],
) -> BindingResult:
    """Mesh Section의 플레이스홀더 매테리얼을 새 메쉬의 같은 인덱스 매테리얼로 바인딩한다.

    Args:
        inSectionMaterials: Mesh Section 노드 순서의 플레이스홀더 매테리얼 경로
        inPlaceholderMeshMaterials: {플레이스홀더 메쉬: 매테리얼 슬롯 순서의 매테리얼 경로}
        inMeshBindings: 메쉬 바인딩 [(플레이스홀더 메쉬, 새 메쉬)]
        inTargetMeshMaterials: {새 메쉬: 매테리얼 슬롯 순서의 매테리얼 경로}

    Returns:
        바인딩 결과
    """
    # 비교는 패키지 경로로 하고, 돌려주는 새 매테리얼은 입력 원문 그대로 둔다(어댑터가 그 값으로 로드한다)
    meshByPlaceholder = {to_package_path(src): to_package_path(dst) for src, dst in inMeshBindings}
    placeholderMaterials = {to_package_path(k): [to_package_path(m) if m else None for m in v]
                            for k, v in inPlaceholderMeshMaterials.items()}
    targetMaterials = {to_package_path(k): list(v) for k, v in inTargetMeshMaterials.items()}
    bindings: List[Tuple[str, str]] = []
    for sectionMaterial in inSectionMaterials:
        key = to_package_path(sectionMaterial) if sectionMaterial else None
        hits = [
            (meshPath, index)
            for meshPath, materials in placeholderMaterials.items()
            if meshPath in meshByPlaceholder
            for index, material in enumerate(materials)
            if key is not None and material == key
        ]
        if len(hits) != 1:
            code = FAILED_MATERIAL_MISSING if not hits else FAILED_PLACEHOLDER_AMBIGUOUS
            return BindingResult([], code, f"플레이스홀더 매테리얼 매칭 {len(hits)}건: {sectionMaterial}")
        meshPath, index = hits[0]
        newMaterials = targetMaterials.get(meshByPlaceholder[meshPath], [])
        if index >= len(newMaterials) or not newMaterials[index]:
            return BindingResult(
                [], FAILED_MATERIAL_MISSING,
                f"새 메쉬 {meshByPlaceholder[meshPath]}에 매테리얼 슬롯 {index}이 없다",
            )
        bindings.append((sectionMaterial, newMaterials[index]))
    return BindingResult(bindings)


# ---------------------------------------------------------------------------
# 그룹 GUID (T3D 익스포트 텍스트)
# ---------------------------------------------------------------------------

_BEGIN_OBJECT = re.compile(r"^\s*Begin Object\b(?P<rest>.*)$")
_END_OBJECT = re.compile(r"^\s*End Object\s*$")
_CLASS_ATTR = re.compile(r"\bClass=(?P<cls>\S+)")
_NAME_ATTR = re.compile(r'\bName="(?P<name>[^"]*)"')
_EXPORT_PATH_ATTR = re.compile(r"\bExportPath=\"(?P<cls>[^']*)'(?P<path>[^']*)'\"")
_PROPERTY_LINE = re.compile(r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*?)\s*$")

GROUP_NODE_CLASS = "CustomizableObjectNodeObjectGroup"
"""그룹 노드 UClass 이름(엔진 클래스 이름이지 프로젝트 규약이 아니다)."""


@dataclass
class T3DObject:
    """T3D 텍스트의 객체 1개.

    Attributes:
        className: 클래스 이름(경로의 마지막 `.` 뒤)
        name: 객체 이름
        path: ExportPath의 객체 경로(없으면 이름)
        props: 직속 `Key=Value` 줄(값은 원문 그대로, 같은 키는 첫 값)
    """

    className: str
    name: str
    path: str
    props: Dict[str, str] = field(default_factory=dict)


def t3d_string_value(inRaw: str) -> str:
    """T3D 값 원문의 따옴표 문자열을 푼다(따옴표가 없으면 그대로).

    Args:
        inRaw: 값 원문

    Returns:
        문자열 값
    """
    if len(inRaw) >= 2 and inRaw.startswith('"') and inRaw.endswith('"'):
        return inRaw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return inRaw


def parse_t3d_objects(inText: str) -> List[T3DObject]:
    """T3D 익스포트 텍스트를 객체 목록으로 읽는다.

    `Begin Object` / `End Object` 중첩을 따라가며 각 객체의 **직속** `Key=Value` 줄만
    그 객체에 붙인다(하위 객체 줄은 섞지 않는다). 객체 하나를 익스포트하면 클래스와 속성이
    한 블록에 오고, 에셋 전체를 익스포트하면 1패스(`Class=`만)와 2패스(`ExportPath`와 속성)로
    나뉘므로 같은 경로의 블록을 병합한다(2026-10-16 프로브 실측 형식). 클래스는 `Class=`가
    없으면 `ExportPath`에서 읽는다. `CustomProperties` 줄(핀)은 속성이 아니므로 버린다.

    Args:
        inText: T3D 텍스트

    Returns:
        객체 목록(처음 나타난 순서)
    """
    objects: Dict[str, T3DObject] = {}
    order: List[str] = []
    stack: List[T3DObject] = []
    for line in inText.splitlines():
        beginMatch = _BEGIN_OBJECT.match(line)
        if beginMatch:
            rest = beginMatch.group("rest")
            classMatch = _CLASS_ATTR.search(rest)
            nameMatch = _NAME_ATTR.search(rest)
            exportMatch = _EXPORT_PATH_ATTR.search(rest)
            classPath = classMatch.group("cls") if classMatch else (exportMatch.group("cls") if exportMatch else "")
            name = nameMatch.group("name") if nameMatch else ""
            key = exportMatch.group("path") if exportMatch else name
            obj = objects.get(key)
            if obj is None:
                obj = T3DObject(className=classPath.rsplit(".", 1)[-1], name=name, path=key)
                objects[key] = obj
                order.append(key)
            elif not obj.className and classPath:
                obj.className = classPath.rsplit(".", 1)[-1]
            stack.append(obj)
            continue
        if _END_OBJECT.match(line):
            if stack:
                stack.pop()
            continue
        if not stack or line.lstrip().startswith("CustomProperties"):
            continue
        propMatch = _PROPERTY_LINE.match(line)
        if propMatch:
            stack[-1].props.setdefault(propMatch.group("key"), propMatch.group("value"))
    return [objects[key] for key in order]


def read_t3d_property(inText: str, inClassName: str, inPropName: str) -> List[str]:
    """T3D 텍스트에서 특정 클래스 객체들의 속성 값(따옴표 해제)을 모은다.

    Python에서 protected라 `get_editor_property`로 못 읽는 속성(`ObjectName`, `ComponentName`,
    `NodeGuid`)의 되읽기 수단이다.

    Args:
        inText: T3D 텍스트
        inClassName: 클래스 이름
        inPropName: 속성 이름(C++ 표기)

    Returns:
        값 목록(객체 순서, 속성이 없는 객체는 빠진다)
    """
    return [
        t3d_string_value(obj.props[inPropName])
        for obj in parse_t3d_objects(inText)
        if obj.className == inClassName and inPropName in obj.props
    ]


def parse_group_guids_t3d(inText: str, inGroupClassName: str = GROUP_NODE_CLASS) -> Dict[str, List[str]]:
    """T3D 익스포트 텍스트에서 그룹 노드의 {GroupName: [NodeGuid...]}를 읽는다.

    그룹 노드 한 개를 익스포트한 텍스트와 CO 에셋 전체를 익스포트한 텍스트 둘 다 받는다.

    Args:
        inText: T3D 텍스트
        inGroupClassName: 그룹 노드 클래스 이름

    Returns:
        {그룹 이름: [32 hex 대문자 NodeGuid...]} - 이름 또는 GUID가 없는 노드는 빠진다
    """
    result: Dict[str, List[str]] = {}
    for obj in parse_t3d_objects(inText):
        if obj.className != inGroupClassName:
            continue
        name = obj.props.get("GroupName")
        guid = obj.props.get("NodeGuid", "")
        if name is None or not _GUID_PATTERN.match(guid):
            continue
        result.setdefault(t3d_string_value(name), []).append(guid.upper())
    return result


def resolve_group_guid(inGroupGuids: Mapping[str, Sequence[str]], inSlot: str) -> Tuple[str, str, str]:
    """슬롯 이름에 해당하는 그룹 GUID를 하나로 정한다.

    Args:
        inGroupGuids: {그룹 이름: [NodeGuid...]}
        inSlot: 슬롯 이름

    Returns:
        (GUID 또는 빈 문자열, 실패 코드 또는 빈 문자열, 설명)
    """
    guids = list(inGroupGuids.get(inSlot, []))
    if not guids:
        available = ", ".join(sorted(inGroupGuids)) or "(없음)"
        return "", FAILED_GROUP_MISSING, f"Base에 '{inSlot}' 그룹이 없다. 있는 그룹: {available}"
    if len(guids) > 1:
        return "", FAILED_GROUP_AMBIGUOUS, f"Base에 '{inSlot}' 그룹이 {len(guids)}개다"
    if not _GUID_PATTERN.match(guids[0]):
        return "", FAILED_GROUP_AMBIGUOUS, f"GUID 형식이 아니다: {guids[0]}"
    return guids[0].upper(), "", ""


# ---------------------------------------------------------------------------
# 요약·직렬화
# ---------------------------------------------------------------------------


def unconsumed_no_template(inPlan: CharacterPlan) -> List[Tuple[str, str, str]]:
    """템플릿 없는 슬롯 폴더 중 어떤 슬롯 CO의 부품으로도 쓰이지 않은 것.

    Args:
        inPlan: 계획(바인딩이 채워진 뒤 호출해야 의미가 있다)

    Returns:
        [(외형, 슬롯, 메쉬 경로)]
    """
    used = {to_package_path(dst) for slot in inPlan.slots for _, dst in slot.meshBindings}
    return [entry for entry in inPlan.noTemplate if to_package_path(entry[2]) not in used]


def plan_to_dict(inPlan: CharacterPlan) -> Dict:
    """계획을 결과 JSON용 dict로 직렬화한다.

    스키마는 **추가만** 한다(읽는 쪽이 `.get`으로 하위 호환을 유지할 수 있게).

    Args:
        inPlan: 계획

    Returns:
        dict
    """
    def _base(inBase: BaseObjectPlan) -> Dict:
        return {
            "assetPath": inBase.assetPath,
            "objectName": inBase.objectName,
            "templatePath": inBase.templatePath,
            "status": inBase.status,
            "detail": inBase.detail,
            "partMeshes": dict(inBase.partMeshes),
            "componentBindings": [list(pair) for pair in inBase.componentBindings],
        }

    def _slot(inSlot: SlotObjectPlan) -> Dict:
        return {
            "outfit": inSlot.outfit,
            "slot": inSlot.slot,
            "meshPath": inSlot.meshPath,
            "assetPath": inSlot.assetPath,
            "objectName": inSlot.objectName,
            "templatePath": inSlot.templatePath,
            "status": inSlot.status,
            "detail": inSlot.detail,
            "meshBindings": [list(pair) for pair in inSlot.meshBindings],
            "materialBindings": [list(pair) for pair in inSlot.materialBindings],
            "groupGuid": inSlot.groupGuid,
        }

    statusCounts: Dict[str, int] = {}
    for status in [inPlan.base.status] + [slot.status for slot in inPlan.slots]:
        statusCounts[status] = statusCounts.get(status, 0) + 1
    return {
        "characterRoot": inPlan.characterRoot,
        "character": inPlan.character,
        "role": inPlan.role,
        "base": _base(inPlan.base),
        "slots": [_slot(slot) for slot in inPlan.slots],
        "noTemplate": [list(entry) for entry in inPlan.noTemplate],
        "noTemplateUnconsumed": [list(entry) for entry in unconsumed_no_template(inPlan)],
        "ignored": [list(entry) for entry in inPlan.ignored],
        "statusCounts": statusCounts,
    }
