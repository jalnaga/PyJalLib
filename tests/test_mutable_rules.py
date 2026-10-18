# -*- coding: utf-8 -*-
"""`pyjallib.ue5.mutableRules` Type A 테스트.

결정 로직은 `unreal` 없이 전수 검증한다. 계약 단정은 `_check_*` 헬퍼로 두고, 정상 구현과
**결정을 뒤집은 변이 구현** 양쪽에 같은 헬퍼를 건다 - 변이가 실제로 그 헬퍼에서 실패해야
판별력이 있다(`.claude/references/testing/discriminating_power.md` §1, §3.1).

픽스처의 캐릭터 트리는 2026-10-16 실기 Content 스캔(공필두·정희원)이고, T3D 텍스트는 같은 날
Phase 0 프로브가 UE 5.7.4에서 실제로 익스포트한 파일이다. ORV 경로는 **테스트 픽스처**다
(라이브러리 상수가 아니다 - 규약은 `MutableBuildConfig`로 주입한다).
"""

import ast
from pathlib import Path
from typing import Callable

import pytest

from pyjallib.ue5 import mutableRules as rules
from pyjallib.ue5.mutableRules import (
    FAILED_BASE_UNAVAILABLE,
    FAILED_GROUP_AMBIGUOUS,
    FAILED_GROUP_MISSING,
    FAILED_MATERIAL_MISSING,
    FAILED_MISSING_BASE_MESH,
    FAILED_MISSING_PART_MESH,
    FAILED_MULTIPLE_MESHES,
    FAILED_NAME_MISMATCH,
    FAILED_PLACEHOLDER_AMBIGUOUS,
    FAILED_ROLE_MISMATCH,
    FAILED_TEMPLATE_INVALID,
    IGNORED_EXCLUDED_OUTFIT,
    IGNORED_NOT_MESH_PREFIX,
    IGNORED_NOT_SLOT_MESH,
    IGNORED_OUTSIDE_MESH_FOLDER,
    STATUS_PENDING,
    STATUS_SKIPPED_EXISTS,
    MutableBuildConfig,
    MutableConfigError,
    build_character_plan,
    parse_group_guids_t3d,
    parse_mesh_role,
    parse_t3d_objects,
    placeholder_part,
    plan_to_dict,
    read_t3d_property,
    resolve_component_bindings,
    resolve_group_guid,
    resolve_material_bindings,
    resolve_mesh_bindings,
    to_package_path,
    unconsumed_no_template,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "mutable"
_CHARS = "/Game/Omni/Characters/Main"
_SHARED = "/Game/Omni/Characters/Shared"
SLOTS = ("Body", "Face", "Glove", "Hair", "Lower", "Mask", "Outer", "Shoes", "Upper")

CONFIG = MutableBuildConfig(
    baseTemplatePath=f"{_SHARED}/Mutable/CO_Template_Sh_Base",
    slotTemplatePattern=f"{_SHARED}/Mutable/CO_Template_Sh_{{slot}}Slot",
    meshFolderName="MeshB",
    mutableFolderName="Mutable",
    baseOutfit="Default",
    excludedOutfits=("BaseSkeleton",),
)

GONG_ROOT = f"{_CHARS}/GongPildu"
GONG_MESHES = [
    f"{GONG_ROOT}/MeshB/BaseSkeleton/Face/SK_GongPildu_Mn_BaseSkeleton_Face",
    f"{GONG_ROOT}/MeshB/BaseSkeleton/SK_GongPildu_Mn_BaseSkeleton",
    f"{GONG_ROOT}/MeshB/Default/Body/SK_GongPildu_Mn_Default_Body",
    f"{GONG_ROOT}/MeshB/Default/Face/SK_GongPildu_Mn_Default_Face",
    f"{GONG_ROOT}/MeshB/Default/Hair/SK_GongPildu_Mn_Default_Hair",
    f"{GONG_ROOT}/MeshB/Suit/Lower/SK_GongPildu_Mn_Suit_Lower",
    f"{GONG_ROOT}/MeshB/Suit/Mask/SK_GongPildu_Mn_Suit_Mask",
    f"{GONG_ROOT}/MeshB/Suit/Outer/SK_GongPildu_Mn_Suit_Outer",
    f"{GONG_ROOT}/MeshB/Suit/Shoes/SK_GongPildu_Mn_Suit_Shoes",
    f"{GONG_ROOT}/MeshB/Suit/Upper/SK_GongPildu_Mn_Suit_Upper",
]
GONG_EXISTING = [f"{GONG_ROOT}/Mutable/CO_GongPildu_Mn_Base"]

JEONG_ROOT = f"{_CHARS}/JeongHuiwon"
JEONG_MESHES = [
    f"{JEONG_ROOT}/MeshB/BaseSkeleton/Face/SK_JeongHuiwon_Mn_BaseSkeleton_Face",
    f"{JEONG_ROOT}/MeshB/BaseSkeleton/SK_JeongHuiwon_Mn_BaseSkeleton",
    f"{JEONG_ROOT}/MeshB/BunHair/Hair/SK_JeongHuiwon_Mn_BunHair_Hair",
    f"{JEONG_ROOT}/MeshB/BunHair/SK_JeongHuiwon_Mn_BunHair",
    f"{JEONG_ROOT}/MeshB/Casual/Lower/SK_JeongHuiwon_Mn_Casual_Lower",
    f"{JEONG_ROOT}/MeshB/Casual/Mask/SK_JeongHuiwon_Mn_Casual_Mask",
    f"{JEONG_ROOT}/MeshB/Casual/SK_JeongHuiwon_Mn_Casual",
    f"{JEONG_ROOT}/MeshB/Casual/Shoes/SK_JeongHuiwon_Mn_Casual_Shoes",
    f"{JEONG_ROOT}/MeshB/Casual/Upper/SK_JeongHuiwon_Mn_Casual_Upper",
    f"{JEONG_ROOT}/MeshB/Default/Body/SK_JeongHuiwon_Mn_Default_Body",
    f"{JEONG_ROOT}/MeshB/Default/Eyebrow/SK_JeongHuiwon_Mn_Default_Eyebrow",
    f"{JEONG_ROOT}/MeshB/Default/Eyeline/SK_JeongHuiwon_Mn_Default_Eyeline",
    f"{JEONG_ROOT}/MeshB/Default/Face/SK_JeongHuiwon_Mn_Default_Face",
    f"{JEONG_ROOT}/MeshB/Default/Hair/SK_JeongHuiwon_Mn_Default_Hair",
    f"{JEONG_ROOT}/MeshB/Default/Iris/SK_JeongHuiwon_Mn_Default_Iris",
    f"{JEONG_ROOT}/MeshB/Default/MouthInterior/SK_JeongHuiwon_Mn_Default_MouthInterior",
    f"{JEONG_ROOT}/MeshB/PatchedCasual/Lower/SK_JeongHuiwon_Mn_PatchedCasual_Lower",
    f"{JEONG_ROOT}/MeshB/PatchedCasual/Upper/SK_JeongHuiwon_Mn_PatchedCasual_Upper",
]

PH = f"{_SHARED}/Human-Male/MeshB/Default"
PH_MAT = f"{_SHARED}/Human-Male/Material/Default"
FACE_PLACEHOLDERS = [
    f"{PH}/Face/SK_HumanM_Sh_Default_Face.SK_HumanM_Sh_Default_Face",
    f"{PH}/Eyebrow/SK_HumanM_Sh_Default_Eyebrow.SK_HumanM_Sh_Default_Eyebrow",
    f"{PH}/Eyeline/SK_HumanM_Sh_Default_Eyeline.SK_HumanM_Sh_Default_Eyeline",
    f"{PH}/Iris/SK_HumanM_Sh_Default_Iris.SK_HumanM_Sh_Default_Iris",
    f"{PH}/MouthInterior/SK_HumanM_Sh_Default_MouthInterior.SK_HumanM_Sh_Default_MouthInterior",
]
BODY_PLACEHOLDER = f"{PH}/Body/SK_HumanM_Sh_Default_Body.SK_HumanM_Sh_Default_Body"


def _plan(inRoot, inMeshes, inExisting=(), inSlots=SLOTS, inConfig=CONFIG):
    return build_character_plan(inRoot, inMeshes, list(inExisting), list(inSlots), inConfig)


def _slot(inPlan, inOutfit, inSlot):
    matches = [s for s in inPlan.slots if s.outfit == inOutfit and s.slot == inSlot]
    assert len(matches) == 1, f"{inOutfit}/{inSlot} 계획이 {len(matches)}개"
    return matches[0]


# ---------------------------------------------------------------------------
# 경로·이름
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("inPath, expected", [
    ("/Game/A/B.B", "/Game/A/B"),
    ("/Game/A/B", "/Game/A/B"),
    ("/Game/A/B/", "/Game/A/B"),
    ("/Game/A.v2/B.B", "/Game/A.v2/B"),
    ("/Game/A.v2/B", "/Game/A.v2/B"),
])
def test_to_package_path_cuts_only_last_segment(inPath, expected):
    assert to_package_path(inPath) == expected


def test_placeholder_part_reads_last_token():
    assert placeholder_part(BODY_PLACEHOLDER) == "Body"
    assert placeholder_part(FACE_PLACEHOLDERS[4]) == "MouthInterior"
    assert placeholder_part("/Game/X/NoUnderscore") == "NoUnderscore"


@pytest.mark.parametrize("inName, inChar, inOutfit, inSlot, expected", [
    ("SK_GongPildu_Mn_Default_Body", "GongPildu", "Default", "Body", "Mn"),
    ("SK_KimDokja_test_Mn_Default_Body", "KimDokja_test", "Default", "Body", "Mn"),
    ("SK_GongPildu_Mn_Suit_Body", "GongPildu", "Default", "Body", None),
    ("SK_GongPildu_Mn_Default_Body", "GongPildu", "Default", "Face", None),
    ("SK_GongPildu_A_B_Default_Body", "GongPildu", "Default", "Body", None),
    ("SK_GongPildu__Default_Body", "GongPildu", "Default", "Body", None),
    ("SM_GongPildu_Mn_Default_Body", "GongPildu", "Default", "Body", None),
])
def test_parse_mesh_role(inName, inChar, inOutfit, inSlot, expected):
    assert parse_mesh_role(inName, inChar, inOutfit, inSlot, "SK_") == expected


def test_config_validate_rejects_empty_and_missing_placeholder():
    with pytest.raises(MutableConfigError):
        MutableBuildConfig("", CONFIG.slotTemplatePattern, "MeshB", "Mutable", "Default").validate()
    with pytest.raises(MutableConfigError):
        MutableBuildConfig(CONFIG.baseTemplatePath, "/Game/X/CO_NoSlot", "MeshB", "Mutable", "Default").validate()
    with pytest.raises(MutableConfigError):
        _plan(GONG_ROOT, GONG_MESHES, inConfig=MutableBuildConfig("", "", "", "", ""))


def test_config_library_defaults_carry_no_project_convention():
    """라이브러리 기본값에는 제외 외형이 없다 - BaseSkeleton 제외는 호출자 설정이다(D-Q3)."""
    bare = MutableBuildConfig("a", "b{slot}", "c", "d", "e")
    assert bare.excludedOutfits == ()
    assert bare.slotObjectNameFormat == "{outfit}"


# ---------------------------------------------------------------------------
# 계획 - 공필두(작업 도중 상태)
# ---------------------------------------------------------------------------


def _check_outfit_level_ignored(inPlan, inOutfitLevelPaths):
    ignoredReasons = dict(inPlan.ignored)
    for path in inOutfitLevelPaths:
        assert ignoredReasons.get(path) == IGNORED_NOT_SLOT_MESH, f"외형 직하 메쉬가 제외되지 않았다: {path}"
    planned = {s.meshPath for s in inPlan.slots} | {e[2] for e in inPlan.noTemplate}
    assert not planned & set(inOutfitLevelPaths)


def _check_existing_skipped(inPlan, inExistingBase):
    assert inPlan.base.assetPath == inExistingBase
    assert inPlan.base.status == STATUS_SKIPPED_EXISTS
    # 기존 Base는 재사용되므로 슬롯은 막히지 않는다
    assert all(s.status != FAILED_BASE_UNAVAILABLE for s in inPlan.slots)


def test_gong_plan_targets_and_names():
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING)
    assert plan.character == "GongPildu"
    assert plan.role == "Mn"
    assert plan.base.objectName == "GongPildu_Mn"
    assert plan.base.templatePath == CONFIG.baseTemplatePath
    assert plan.base.partMeshes == {
        "Body": f"{GONG_ROOT}/MeshB/Default/Body/SK_GongPildu_Mn_Default_Body",
        "Face": f"{GONG_ROOT}/MeshB/Default/Face/SK_GongPildu_Mn_Default_Face",
        "Hair": f"{GONG_ROOT}/MeshB/Default/Hair/SK_GongPildu_Mn_Default_Hair",
    }
    assert [(s.outfit, s.slot) for s in plan.slots] == [
        ("Default", "Body"), ("Default", "Face"), ("Default", "Hair"),
        ("Suit", "Lower"), ("Suit", "Mask"), ("Suit", "Outer"), ("Suit", "Shoes"), ("Suit", "Upper"),
    ]
    mask = _slot(plan, "Suit", "Mask")
    assert mask.assetPath == f"{GONG_ROOT}/MeshB/Suit/Mask/CO_GongPildu_Mn_Suit_Mask"
    assert mask.templatePath == f"{_SHARED}/Mutable/CO_Template_Sh_MaskSlot"
    assert mask.objectName == "Suit"  # D-Q2: 슬롯 Base Object 이름 = 외형
    assert all(s.status == STATUS_PENDING for s in plan.slots)
    assert plan.noTemplate == []


def test_gong_plan_reuses_existing_base():
    _check_existing_skipped(_plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING), GONG_EXISTING[0])


def test_gong_plan_excludes_base_skeleton_and_outfit_level():
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING)
    ignored = dict(plan.ignored)
    assert ignored[f"{GONG_ROOT}/MeshB/BaseSkeleton/Face/SK_GongPildu_Mn_BaseSkeleton_Face"] == IGNORED_EXCLUDED_OUTFIT
    _check_outfit_level_ignored(plan, [f"{GONG_ROOT}/MeshB/BaseSkeleton/SK_GongPildu_Mn_BaseSkeleton"])


def test_base_skeleton_is_planned_when_not_excluded():
    """제외는 설정이 한다 - 설정에서 빼면 BaseSkeleton Face도 슬롯 계획에 들어온다."""
    config = MutableBuildConfig(CONFIG.baseTemplatePath, CONFIG.slotTemplatePattern, "MeshB", "Mutable", "Default")
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING, inConfig=config)
    assert ("BaseSkeleton", "Face") in [(s.outfit, s.slot) for s in plan.slots]


# ---------------------------------------------------------------------------
# 계획 - 정희원(Face 부품 SK 있음, 외형 직하 SK 있음)
# ---------------------------------------------------------------------------


def test_jeong_plan_new_base_and_sample_slot_path():
    plan = _plan(JEONG_ROOT, JEONG_MESHES)
    assert plan.base.status == STATUS_PENDING
    assert plan.base.assetPath == f"{JEONG_ROOT}/Mutable/CO_JeongHuiwon_Mn_Base"
    hair = _slot(plan, "BunHair", "Hair")
    # 수작업 정답 표본과 같은 경로·이름
    assert hair.assetPath == f"{JEONG_ROOT}/MeshB/BunHair/Hair/CO_JeongHuiwon_Mn_BunHair_Hair"
    assert hair.objectName == "BunHair"


def test_jeong_plan_counts_no_template_folders():
    plan = _plan(JEONG_ROOT, JEONG_MESHES)
    assert sorted((o, s) for o, s, _ in plan.noTemplate) == [
        ("Default", "Eyebrow"), ("Default", "Eyeline"), ("Default", "Iris"), ("Default", "MouthInterior"),
    ]
    face = _slot(plan, "Default", "Face")
    assert set(face.outfitPartMeshes) == {"Body", "Eyebrow", "Eyeline", "Face", "Hair", "Iris", "MouthInterior"}


def test_jeong_plan_ignores_outfit_level_meshes():
    _check_outfit_level_ignored(_plan(JEONG_ROOT, JEONG_MESHES), [
        f"{JEONG_ROOT}/MeshB/BaseSkeleton/SK_JeongHuiwon_Mn_BaseSkeleton",
        f"{JEONG_ROOT}/MeshB/BunHair/SK_JeongHuiwon_Mn_BunHair",
        f"{JEONG_ROOT}/MeshB/Casual/SK_JeongHuiwon_Mn_Casual",
    ])


# ---------------------------------------------------------------------------
# 계획 - 경계·실패
# ---------------------------------------------------------------------------


def test_existing_slot_is_skipped():
    existing = [f"{GONG_ROOT}/MeshB/Suit/Mask/CO_GongPildu_Mn_Suit_Mask.CO_GongPildu_Mn_Suit_Mask"]
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING + existing)
    assert _slot(plan, "Suit", "Mask").status == STATUS_SKIPPED_EXISTS
    assert _slot(plan, "Suit", "Outer").status == STATUS_PENDING


def test_missing_base_meshes_blocks_slots():
    meshes = [p for p in GONG_MESHES if "/Default/" not in p]
    plan = _plan(GONG_ROOT, meshes)
    assert plan.base.status == FAILED_MISSING_BASE_MESH
    assert {s.status for s in plan.slots} == {FAILED_BASE_UNAVAILABLE}


def test_role_mismatch_fails_base():
    meshes = GONG_MESHES + [f"{GONG_ROOT}/MeshB/Suit/Glove/SK_GongPildu_Xx_Suit_Glove"]
    plan = _plan(GONG_ROOT, meshes)
    assert plan.base.status == FAILED_ROLE_MISMATCH
    assert plan.role == ""


def test_name_mismatch_fails_slot_only():
    meshes = GONG_MESHES + [f"{GONG_ROOT}/MeshB/Suit/Glove/SK_Gong_Mn_Suit_Glove"]
    plan = _plan(GONG_ROOT, meshes, GONG_EXISTING)
    assert _slot(plan, "Suit", "Glove").status == FAILED_NAME_MISMATCH
    assert plan.base.status == STATUS_SKIPPED_EXISTS


def test_multiple_meshes_in_slot_folder_fails():
    meshes = GONG_MESHES + [f"{GONG_ROOT}/MeshB/Suit/Mask/SK_GongPildu_Mn_Suit_Mask_02"]
    plan = _plan(GONG_ROOT, meshes, GONG_EXISTING)
    assert _slot(plan, "Suit", "Mask").status == FAILED_MULTIPLE_MESHES


def test_prefix_and_outside_folder_ignored():
    meshes = GONG_MESHES + [
        f"{GONG_ROOT}/MeshB/Suit/Mask/SM_GongPildu_Mn_Suit_Mask",
        f"{GONG_ROOT}/Other/SK_GongPildu_Mn_Suit_Mask",
    ]
    ignored = dict(_plan(GONG_ROOT, meshes, GONG_EXISTING).ignored)
    assert ignored[f"{GONG_ROOT}/MeshB/Suit/Mask/SM_GongPildu_Mn_Suit_Mask"] == IGNORED_NOT_MESH_PREFIX
    assert ignored[f"{GONG_ROOT}/Other/SK_GongPildu_Mn_Suit_Mask"] == IGNORED_OUTSIDE_MESH_FOLDER


def test_slot_without_template_is_counted_not_planned():
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING, inSlots=[s for s in SLOTS if s != "Shoes"])
    assert ("Suit", "Shoes") not in [(s.outfit, s.slot) for s in plan.slots]
    assert ("Suit", "Shoes", f"{GONG_ROOT}/MeshB/Suit/Shoes/SK_GongPildu_Mn_Suit_Shoes") in plan.noTemplate


def test_object_paths_from_registry_are_normalized():
    meshes = [f"{p}.{p.rsplit('/', 1)[-1]}" for p in GONG_MESHES]
    plan = _plan(GONG_ROOT + "/", meshes, GONG_EXISTING)
    assert plan.base.status == STATUS_SKIPPED_EXISTS
    assert _slot(plan, "Suit", "Mask").meshPath == f"{GONG_ROOT}/MeshB/Suit/Mask/SK_GongPildu_Mn_Suit_Mask"


# ---------------------------------------------------------------------------
# 바인딩
# ---------------------------------------------------------------------------


def test_component_bindings_by_placeholder_part():
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING)
    result = resolve_component_bindings([BODY_PLACEHOLDER, FACE_PLACEHOLDERS[0]], plan.base.partMeshes)
    assert result.failure == ""
    assert result.bindings == [
        (BODY_PLACEHOLDER, f"{GONG_ROOT}/MeshB/Default/Body/SK_GongPildu_Mn_Default_Body"),
        (FACE_PLACEHOLDERS[0], f"{GONG_ROOT}/MeshB/Default/Face/SK_GongPildu_Mn_Default_Face"),
    ]


def test_component_bindings_failures():
    assert resolve_component_bindings([], {"Body": "x"}).failure == FAILED_TEMPLATE_INVALID
    missing = resolve_component_bindings([BODY_PLACEHOLDER, FACE_PLACEHOLDERS[0]], {"Body": "x"})
    assert (missing.failure, missing.bindings) == (FAILED_MISSING_BASE_MESH, [])
    dup = resolve_component_bindings([BODY_PLACEHOLDER, BODY_PLACEHOLDER], {"Body": "x"})
    assert dup.failure == FAILED_PLACEHOLDER_AMBIGUOUS


def test_single_sk_template_binds_slot_mesh_regardless_of_placeholder():
    """단일 SK 템플릿 8종은 플레이스홀더가 전부 Body다 - 토큰을 쓰면 Hair가 Body로 간다."""
    plan = _plan(JEONG_ROOT, JEONG_MESHES)
    hair = _slot(plan, "BunHair", "Hair")
    result = resolve_mesh_bindings([BODY_PLACEHOLDER], hair.slot, hair.meshPath, hair.outfitPartMeshes)
    assert result.bindings == [(BODY_PLACEHOLDER, hair.meshPath)]


def _check_missing_part_fails(inResolver: Callable):
    plan = _plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING)
    face = _slot(plan, "Default", "Face")
    result = inResolver(FACE_PLACEHOLDERS, face.slot, face.meshPath, face.outfitPartMeshes)
    assert result.failure == FAILED_MISSING_PART_MESH
    assert result.bindings == []
    for part in ("Eyebrow", "Eyeline", "Iris", "MouthInterior"):
        assert part in result.detail


def test_face_template_binds_sibling_part_meshes():
    plan = _plan(JEONG_ROOT, JEONG_MESHES)
    face = _slot(plan, "Default", "Face")
    result = resolve_mesh_bindings(FACE_PLACEHOLDERS, face.slot, face.meshPath, face.outfitPartMeshes)
    assert result.failure == ""
    assert [dst for _, dst in result.bindings] == [
        f"{JEONG_ROOT}/MeshB/Default/{part}/SK_JeongHuiwon_Mn_Default_{part}"
        for part in ("Face", "Eyebrow", "Eyeline", "Iris", "MouthInterior")
    ]
    face.meshBindings = result.bindings
    assert unconsumed_no_template(plan) == []


def test_face_template_missing_parts_fail_closed():
    """D-Q1: 부품 SK가 하나라도 없으면 그 CO를 만들지 않는다(공필두)."""
    _check_missing_part_fails(resolve_mesh_bindings)


def test_mesh_bindings_template_invalid_and_ambiguous():
    assert resolve_mesh_bindings([], "Face", "x", {}).failure == FAILED_TEMPLATE_INVALID
    dup = resolve_mesh_bindings([FACE_PLACEHOLDERS[0], FACE_PLACEHOLDERS[0]], "Face", "x", {})
    assert dup.failure == FAILED_PLACEHOLDER_AMBIGUOUS
    noSelf = resolve_mesh_bindings(FACE_PLACEHOLDERS[1:3], "Face", "x", {"Eyebrow": "a", "Eyeline": "b"})
    assert noSelf.failure == FAILED_PLACEHOLDER_AMBIGUOUS


def test_material_bindings_same_index_on_new_mesh():
    phBody = f"{PH_MAT}/Body/MI_HumanM_Sh_Default_Body.MI_HumanM_Sh_Default_Body"
    newMesh = f"{JEONG_ROOT}/MeshB/BunHair/Hair/SK_JeongHuiwon_Mn_BunHair_Hair"
    newMat = f"{JEONG_ROOT}/Material/BunHair/Hair/MI_JeongHuiwon_Mn_BunHair_Hair.MI_JeongHuiwon_Mn_BunHair_Hair"
    result = resolve_material_bindings(
        [phBody],
        {BODY_PLACEHOLDER: [phBody]},
        [(BODY_PLACEHOLDER, newMesh)],
        {newMesh: [newMat]},
    )
    assert result.failure == ""
    assert result.bindings == [(phBody, newMat)]


def test_material_bindings_follow_index_not_first_slot():
    """플레이스홀더 매테리얼이 인덱스 1이면 새 메쉬도 인덱스 1을 쓴다(외곽선 슬롯 혼동 방지)."""
    result = resolve_material_bindings(
        ["/G/MI_Outline"],
        {"/G/SK_Ph": ["/G/MI_Main", "/G/MI_Outline"]},
        [("/G/SK_Ph", "/G/SK_New")],
        {"/G/SK_New": ["/G/MI_NewMain", "/G/MI_NewOutline"]},
    )
    assert result.bindings == [("/G/MI_Outline", "/G/MI_NewOutline")]


def test_material_bindings_failures():
    base = ({"/G/SK_Ph": ["/G/MI_A"]}, [("/G/SK_Ph", "/G/SK_New")])
    missing = resolve_material_bindings(["/G/MI_Z"], base[0], base[1], {"/G/SK_New": ["/G/MI_N"]})
    assert missing.failure == FAILED_MATERIAL_MISSING
    outOfRange = resolve_material_bindings(["/G/MI_A"], base[0], base[1], {"/G/SK_New": []})
    assert outOfRange.failure == FAILED_MATERIAL_MISSING
    emptySlot = resolve_material_bindings(["/G/MI_A"], base[0], base[1], {"/G/SK_New": [None]})
    assert emptySlot.failure == FAILED_MATERIAL_MISSING
    ambiguous = resolve_material_bindings(
        ["/G/MI_A"], {"/G/SK_Ph": ["/G/MI_A", "/G/MI_A"]}, base[1], {"/G/SK_New": ["x", "y"]}
    )
    assert ambiguous.failure == FAILED_PLACEHOLDER_AMBIGUOUS


# ---------------------------------------------------------------------------
# T3D (Phase 0 실측 익스포트)
# ---------------------------------------------------------------------------

ASSET_GROUP_GUIDS = {
    "Body": "5784E2214637C1F99F8FCA867D1A12B5",
    "Face": "746CE2914A613C0FCEBD5E99F448A78F",
    "Hair": "3689EB20442109F5B45254BA8EBCC611",
    "Mask": "69734DCD4DF3ED94AB280AAE1D96B163",
    "Outer": "83061ADE42BF2EDB3BF892862BC412DB",
    "Glove": "BB8B7AB4409BDF17EC3FBF9B8F61D212",
    "Upper": "74CF6D3A4B495206B9EF83BB74E6C21D",
    "Lower": "F72005514C42256BEA7B6BA28AD65268",
    "Shoes": "34EF85874A394F72332338AB98A5BDA9",
}


def _fixture(inName):
    return (_FIXTURES / inName).read_text(encoding="utf-8")


def test_t3d_single_group_node_export():
    assert parse_group_guids_t3d(_fixture("group_node_export.t3d")) == {"Body": [ASSET_GROUP_GUIDS["Body"]]}


def test_t3d_whole_asset_two_pass_export():
    """에셋 전체 익스포트는 1패스(Class)와 2패스(ExportPath+속성)로 나뉜다 - 병합해야 9개가 나온다."""
    parsed = parse_group_guids_t3d(_fixture("base_asset_export.t3d"))
    assert parsed == {name: [guid] for name, guid in ASSET_GROUP_GUIDS.items()}


def test_t3d_reads_protected_names():
    text = _fixture("base_asset_export.t3d")
    assert read_t3d_property(text, "CustomizableObjectNodeObject", "ObjectName") == ["ProbeChar_Pr"]
    assert read_t3d_property(text, "CustomizableObjectNodeComponentMesh", "ComponentName") == ["Body", "Face"]


def test_t3d_child_object_lines_do_not_leak_into_parent():
    text = "\n".join([
        'Begin Object Class=/Script/M.CustomizableObjectNodeObjectGroup Name="G"',
        '   Begin Object Class=/Script/M.Other Name="Child"',
        "      NodeGuid=11111111111111111111111111111111",
        '      GroupName="Wrong"',
        "   End Object",
        '   GroupName="Hair"',
        "   NodeGuid=22222222222222222222222222222222",
        "   CustomProperties Pin (PinId=33333333333333333333333333333333)",
        "End Object",
    ])
    assert parse_group_guids_t3d(text) == {"Hair": ["22222222222222222222222222222222"]}
    objects = parse_t3d_objects(text)
    assert [o.className for o in objects] == ["CustomizableObjectNodeObjectGroup", "Other"]


def test_t3d_ignores_group_without_valid_guid():
    text = 'Begin Object Class=/Script/M.CustomizableObjectNodeObjectGroup Name="G"\n   GroupName="Hair"\n   NodeGuid=XYZ\nEnd Object'
    assert parse_group_guids_t3d(text) == {}


def test_resolve_group_guid():
    guids = {name: [guid] for name, guid in ASSET_GROUP_GUIDS.items()}
    assert resolve_group_guid(guids, "Hair") == (ASSET_GROUP_GUIDS["Hair"], "", "")
    assert resolve_group_guid(guids, "Tail")[1] == FAILED_GROUP_MISSING
    assert resolve_group_guid({"Hair": ["A" * 32, "B" * 32]}, "Hair")[1] == FAILED_GROUP_AMBIGUOUS


# ---------------------------------------------------------------------------
# 직렬화
# ---------------------------------------------------------------------------


def test_plan_to_dict_schema_and_counts():
    data = plan_to_dict(_plan(GONG_ROOT, GONG_MESHES, GONG_EXISTING))
    assert set(data) >= {"characterRoot", "character", "role", "base", "slots", "noTemplate",
                         "noTemplateUnconsumed", "ignored", "statusCounts"}
    assert data["statusCounts"] == {STATUS_SKIPPED_EXISTS: 1, STATUS_PENDING: 8}
    assert data["slots"][0]["assetPath"].endswith("CO_GongPildu_Mn_Default_Body")


# ---------------------------------------------------------------------------
# 판별력 증명 - 결정을 뒤집은 변이에서 같은 헬퍼가 실패해야 한다
# ---------------------------------------------------------------------------


def _mutant_keep_placeholder(inPlaceholders, inSlot, inSlotMesh, inOutfitPartMeshes):
    """부품 메쉬가 없으면 플레이스홀더를 그대로 두고 진행하는 변이(D-Q1 위반)."""
    bindings = [
        (path, inSlotMesh if placeholder_part(path) == inSlot else inOutfitPartMeshes.get(placeholder_part(path), path))
        for path in inPlaceholders
    ]
    return rules.BindingResult(bindings)


def test_power_missing_part_mutant_is_caught():
    with pytest.raises(AssertionError):
        _check_missing_part_fails(_mutant_keep_placeholder)


def test_power_outfit_level_mutant_is_caught(monkeypatch):
    original = rules._classify_meshes

    def _mutant(inRoot, inCharacter, inMeshPaths, inConfig):
        grouped, ignored = original(inRoot, inCharacter, inMeshPaths, inConfig)
        keep = []
        for path, reason in ignored:
            if reason == IGNORED_NOT_SLOT_MESH:
                outfit = path.split("/")[-2]
                grouped.setdefault(outfit, {}).setdefault("Body", []).append(path)
            else:
                keep.append((path, reason))
        return grouped, keep

    monkeypatch.setattr(rules, "_classify_meshes", _mutant)
    with pytest.raises(AssertionError):
        _check_outfit_level_ignored(_plan(JEONG_ROOT, JEONG_MESHES), [f"{JEONG_ROOT}/MeshB/BunHair/SK_JeongHuiwon_Mn_BunHair"])


def test_power_overwrite_mutant_is_caught():
    overwritingPlan = build_character_plan(GONG_ROOT, GONG_MESHES, [], list(SLOTS), CONFIG)
    with pytest.raises(AssertionError):
        _check_existing_skipped(overwritingPlan, GONG_EXISTING[0])


# ---------------------------------------------------------------------------
# 가드 - 라이브러리 소스에 프로젝트 규약 리터럴이 없다
# ---------------------------------------------------------------------------

_SRC = Path(__file__).parent.parent / "src" / "pyjallib" / "ue5"
_GUARDED_SOURCES = (_SRC / "mutableRules.py",)
_FORBIDDEN = ("Omni", "Template_Sh", "HumanM", "GongPildu", "JeongHuiwon", "MeshB")


def _code_string_literals(inPath: Path):
    tree = ast.parse(inPath.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            yield node.lineno, node.value


@pytest.mark.parametrize("inPath", _GUARDED_SOURCES, ids=lambda p: p.name)
def test_no_project_convention_literals(inPath):
    """실행 코드 리터럴만 본다 - docstring의 예시(`KimDokja_test`)는 경위 기록이다."""
    hits = [(line, value) for line, value in _code_string_literals(inPath)
            if any(word in value for word in _FORBIDDEN)]
    assert hits == []
