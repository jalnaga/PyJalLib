#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""매테리얼 슬롯 이름 변경 어댑터 (UE5 임베디드 파이썬 전용)

SkeletalMesh / StaticMesh의 매테리얼 슬롯 이름을 치환 표에 따라 바꾼다. 무엇을 바꿀지는
`ue5/materialSlotRules.py`(unreal 비의존)가 결정하고, 이 모듈은 메쉬 읽기·쓰기·저장만 한다.

**이 영역의 쓰기는 실패해도 예외도 `False`도 내지 않는다.** 그래서 규칙은 하나다 -
**쓰기의 성공 판정은 되읽기다**(`.claude/references/ue5/silent_write_paths.md`).

UE 5.7 실측 (2026-09-15 SkeletalMesh, 2026-10-02 StaticMesh Phase 0):

- 슬롯 배열은 **구조체 배열**이라 원소를 꺼내면 **사본**이 나온다. 사본에
  `set_editor_property`만 하면 사본만 바뀌고 메쉬는 그대로다(반환 `None`, 예외 없음).
- 먹는 경로는 **3단**뿐이다 - 사본 수정 -> 배열 인덱스에 대입 -> 배열을 프로퍼티에 대입.
  두 메쉬 타입에서 같고, 다른 것은 배열 프로퍼티 이름 하나다
  (`SkeletalMesh.materials` / `StaticMesh.static_materials`. StaticMesh의 `materials`는
  protected라 읽을 수도 없다).
- 새 구조체로 배열을 재구성하는 경로는 반영은 되지만 `imported_material_slot_name`을
  **비가역적으로 잃는다** - 채택하지 않는다.
- 슬롯 이름 변경 전용 API는 어느 메쉬 타입·서브시스템에도 없다.

저장 경계 (P4는 이 모듈 밖이다):

- **저장 전 `os.access(path, os.W_OK)`를 확인한다.** `save_asset`은 읽기 전용 파일에서도
  예외 없이 `True`를 돌려주고, 소스 컨트롤이 켜져 있으면 파일을 **default CL에 자동
  체크아웃한 뒤** 저장한다. 읽기 전용이면 메모리도 건드리지 않고 `notCheckedOut`으로 기록한다.
- **변경된 에셋만 저장한다.** `save_asset`은 논리적 변경이 없어도 재직렬화로 바이트를
  바꾸므로 서밋 시 `auto_revert_unchanged`가 걸러 주지 못한다.
- **드라이런은 메쉬를 로드조차 하지 않고 `save_asset`을 부르지 않는다.**
- CL 생성·체크아웃·서밋과 **default CL 누출 검사(`p4 opened -c default`)는 호출자 책임**이다.
  UE5 임베디드 파이썬에는 P4Python이 없다.

로깅은 `unreal.log` 계열을 쓴다 - 임베디드 파이썬에는 pyjallib `Logger` 경로가 없다.
"""

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import unreal


def _load_rules_module():
    """순수 결정 모듈 `materialSlotRules`를 로드한다.

    패키지로 import되면(`pyjallib.ue5.inUnreal.materialSlots`) 상대 import를 쓰고, UE5
    legacy 템플릿처럼 `inUnreal` 폴더를 `sys.path`에 얹어 **평면 import**되면 형제 폴더의
    파일을 경로로 직접 로드한다. `sys.path`에 `ue5/`를 얹지 않는 이유는 `templates` 같은
    흔한 이름이 다른 패키지를 가릴 수 있어서다.

    Returns:
        `materialSlotRules` 모듈
    """
    try:
        from .. import materialSlotRules as rulesModule
        return rulesModule
    except ImportError:
        pass

    existing = sys.modules.get("materialSlotRules")
    if existing is not None:
        return existing
    rulesPath = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "materialSlotRules.py"
    )
    spec = importlib.util.spec_from_file_location("materialSlotRules", rulesPath)
    rulesModule = importlib.util.module_from_spec(spec)
    sys.modules["materialSlotRules"] = rulesModule
    spec.loader.exec_module(rulesModule)
    return rulesModule


materialSlotRules = _load_rules_module()

LOG_PREFIX = "[MaterialSlots]"

MESH_TYPE_SKELETAL = "SkeletalMesh"
MESH_TYPE_STATIC = "StaticMesh"

_SLOT_ARRAY_PROPERTY_BY_TYPE: Tuple[Tuple[type, str, str], ...] = (
    (unreal.SkeletalMesh, MESH_TYPE_SKELETAL, "materials"),
    (unreal.StaticMesh, MESH_TYPE_STATIC, "static_materials"),
)
"""메쉬 타입 -> (타입 이름, 슬롯 배열 프로퍼티 이름). 2026-10-02 Phase 0 실측값이다.

판별은 `isinstance`로 한다 - 실측에서 클래스 이름 축과 같은 답을 냈고, 두 클래스는 서로의
서브클래스가 아니어서 배타 판별이 된다."""

SLOT_NAME_FIELD = "material_slot_name"
MATERIAL_FIELD = "material_interface"

# load_mesh 사유 코드
REASON_LOAD_EXCEPTION = "loadException"
REASON_LOAD_RETURNED_NONE = "loadReturnedNone"
REASON_NOT_MESH = "notMesh"

# apply_plan 실패 사유 코드
FAIL_LOAD = "loadFailed"
FAIL_UNSUPPORTED_MOUNT = "unsupportedMountPoint"
FAIL_FILE_MISSING = "fileMissing"
FAIL_NOT_CHECKED_OUT = "notCheckedOut"
FAIL_PLAN_STALE = "planStale"
FAIL_WRITE_EXCEPTION = "writeException"
FAIL_WRITE_NOT_VERIFIED = "writeNotVerified"
FAIL_READBACK_MISMATCH = "readbackMismatch"
FAIL_SAVE_EXCEPTION = "saveException"
FAIL_SAVE_RETURNED_FALSE = "saveReturnedFalse"
FAIL_SAVE_NOT_ON_DISK = "saveNotOnDisk"

# apply_plan 에셋 상태
STATUS_CHANGED = "changed"
STATUS_UNCHANGED = "unchanged"
STATUS_DRY_RUN = "dryRun"
STATUS_FAILED = "failed"


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
# 프리미티브
# ---------------------------------------------------------------------------


def mesh_type_of(inAsset) -> str:
    """에셋의 메쉬 타입 이름을 돌려준다.

    Args:
        inAsset: 로드된 에셋

    Returns:
        `MESH_TYPE_SKELETAL` / `MESH_TYPE_STATIC`. 지원하지 않는 타입이면 빈 문자열.
    """
    for meshClass, typeName, _ in _SLOT_ARRAY_PROPERTY_BY_TYPE:
        if isinstance(inAsset, meshClass):
            return typeName
    return ""


def slot_array_property(inMesh) -> str:
    """메쉬 타입에 맞는 슬롯 배열 프로퍼티 이름을 돌려준다.

    Args:
        inMesh: SkeletalMesh 또는 StaticMesh

    Returns:
        `materials` 또는 `static_materials`

    Raises:
        TypeError: 지원하지 않는 타입
    """
    for meshClass, _, propertyName in _SLOT_ARRAY_PROPERTY_BY_TYPE:
        if isinstance(inMesh, meshClass):
            return propertyName
    raise TypeError(f"매테리얼 슬롯을 다룰 수 없는 타입이다: {type(inMesh).__name__}")


def load_mesh(inPackagePath: str) -> Tuple[Optional[object], str, str]:
    """패키지 경로로 메쉬(SkeletalMesh / StaticMesh)를 로드한다.

    실패는 예외로 던지지 않고 사유 코드로 돌려준다 - 목록 처리 중 한 건의 실패가 나머지를
    멈추면 안 된다.

    Args:
        inPackagePath: `/Game/...` 패키지 경로(오브젝트 경로도 된다)

    Returns:
        `(메쉬 또는 None, 사유 코드, 실제 클래스 이름)`. 성공이면 사유 코드는 빈 문자열.
    """
    try:
        asset = unreal.load_asset(inPackagePath)
    except Exception as loadError:  # noqa: BLE001 - 로드 실패 형태를 그대로 수집한다
        _log_warning(f"로드 예외: {inPackagePath} - {type(loadError).__name__}: {loadError}")
        return None, REASON_LOAD_EXCEPTION, ""

    if asset is None:
        return None, REASON_LOAD_RETURNED_NONE, ""

    className = asset.get_class().get_name()
    if not mesh_type_of(asset):
        return None, REASON_NOT_MESH, className
    return asset, "", className


def read_slot_names(inMesh) -> List[str]:
    """메쉬의 매테리얼 슬롯 이름을 슬롯 인덱스 순서로 읽는다.

    Args:
        inMesh: SkeletalMesh 또는 StaticMesh

    Returns:
        슬롯 이름 목록
    """
    slots = inMesh.get_editor_property(slot_array_property(inMesh))
    return [str(slot.get_editor_property(SLOT_NAME_FIELD)) for slot in slots]


def read_material_asset_paths(inMesh) -> List[str]:
    """슬롯에 할당된 매테리얼 인터페이스의 에셋 경로를 슬롯 인덱스 순서로 읽는다.

    Args:
        inMesh: SkeletalMesh 또는 StaticMesh

    Returns:
        매테리얼 경로 목록. 비어 있는 슬롯은 빈 문자열.
    """
    slots = inMesh.get_editor_property(slot_array_property(inMesh))
    paths: List[str] = []
    for slot in slots:
        materialInterface = slot.get_editor_property(MATERIAL_FIELD)
        paths.append(materialInterface.get_path_name() if materialInterface else "")
    return paths


def _write_slot_name_unverified(inMesh, inSlotIndex: int, inSlotName: str) -> None:
    """3단 쓰기만 한다(검증 없음). 외부에서 직접 부르지 않는다 - `write_slot_name`을 쓴다.

    Args:
        inMesh: SkeletalMesh 또는 StaticMesh
        inSlotIndex: 슬롯 인덱스
        inSlotName: 새 슬롯 이름
    """
    propertyName = slot_array_property(inMesh)
    slots = inMesh.get_editor_property(propertyName)
    slot = slots[inSlotIndex]                          # 사본이다
    slot.set_editor_property(SLOT_NAME_FIELD, inSlotName)
    slots[inSlotIndex] = slot                          # (1) 배열에 되쓴다
    inMesh.set_editor_property(propertyName, slots)    # (2) 메쉬에 되쓴다


def verify_slot_name(inMesh, inSlotIndex: int, inExpectedName: str) -> bool:
    """슬롯 이름을 메쉬에서 되읽어 기대값과 같은지 확인한다.

    Args:
        inMesh: SkeletalMesh 또는 StaticMesh
        inSlotIndex: 슬롯 인덱스
        inExpectedName: 기대하는 슬롯 이름

    Returns:
        되읽은 이름이 기대값과 같으면 True
    """
    names = read_slot_names(inMesh)
    return 0 <= inSlotIndex < len(names) and names[inSlotIndex] == inExpectedName


def write_slot_name(inMesh, inSlotIndex: int, inSlotName: str) -> bool:
    """슬롯 이름 하나를 바꾸고(메모리, 저장 안 함) 되읽어 확인한다.

    **성공 판정은 되읽기뿐이다.** 쓰기 호출의 반환값·예외 부재는 근거가 아니다. 검증을
    끄는 인자는 두지 않는다 - 끌 수 있으면 조용한 실패가 다시 열린다.

    Args:
        inMesh: SkeletalMesh 또는 StaticMesh
        inSlotIndex: 슬롯 인덱스
        inSlotName: 새 슬롯 이름

    Returns:
        되읽은 이름이 새 이름이면 True

    Raises:
        IndexError: 슬롯 인덱스가 범위 밖
        TypeError: 지원하지 않는 메쉬 타입
    """
    slotCount = len(inMesh.get_editor_property(slot_array_property(inMesh)))
    if not 0 <= inSlotIndex < slotCount:
        raise IndexError(f"슬롯 인덱스 범위 밖: {inSlotIndex} (슬롯 {slotCount}개)")
    _write_slot_name_unverified(inMesh, inSlotIndex, inSlotName)
    return verify_slot_name(inMesh, inSlotIndex, inSlotName)


def package_file_path(inPackagePath: str) -> Optional[str]:
    """`/Game/...` 패키지 경로를 로컬 `.uasset` 절대 경로로 바꾼다.

    오브젝트 경로(`/Game/A/B.B`)도 받는다. `.` 절단은 마지막 `/` 뒤 세그먼트에 한정한다 -
    폴더 이름에 `.`이 있어도 경로 중간이 잘리면 안 된다.

    Args:
        inPackagePath: 패키지 경로 또는 오브젝트 경로

    Returns:
        정방향 슬래시 절대 경로. `/Game/` 밖 마운트 포인트(엔진·플러그인)면 None.
    """
    path = str(inPackagePath).replace("\\", "/")
    if not path.startswith("/Game/"):
        return None
    separatorIndex = path.rfind("/")
    lastSegment = path[separatorIndex + 1:]
    dotIndex = lastSegment.find(".")
    if dotIndex > 0:
        path = path[:separatorIndex + 1] + lastSegment[:dotIndex]
    contentDir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    return contentDir.replace("\\", "/").rstrip("/") + "/" + path[len("/Game/"):] + ".uasset"


# ---------------------------------------------------------------------------
# 계획 / 결과 레코드
# ---------------------------------------------------------------------------


@dataclass
class AssetPlan:
    """에셋 1개의 치환 계획. `build_plan`이 만들고 메쉬를 바꾸지 않는다.

    Attributes:
        packagePath: 호출자가 넘긴 경로 원본(정규화하지 않는다 - 호출자가 자기 입력으로 대조한다)
        meshType: `MESH_TYPE_*`. 로드 실패면 빈 문자열.
        className: 실제 클래스 이름
        loadFailure: 로드 실패 사유 코드. 성공이면 빈 문자열.
        slotNamesBefore: 계획 시점의 슬롯 이름
        materialPaths: 계획 시점의 매테리얼 참조
        decisions: 슬롯별 결정
    """

    packagePath: str
    meshType: str = ""
    className: str = ""
    loadFailure: str = ""
    slotNamesBefore: List[str] = field(default_factory=list)
    materialPaths: List[str] = field(default_factory=list)
    decisions: List = field(default_factory=list)

    @property
    def willChange(self) -> bool:
        """치환이 하나라도 있으면 True(저장 대상)."""
        return not self.loadFailure and materialSlotRules.has_pending_rename(self.decisions)

    def to_dict(self) -> Dict:
        """결과 JSON용 dict. 키는 추가만 한다.

        Returns:
            직렬화 가능한 dict
        """
        return {
            "packagePath": self.packagePath,
            "meshType": self.meshType,
            "className": self.className,
            "loadFailure": self.loadFailure,
            "slotNamesBefore": list(self.slotNamesBefore),
            "materialPaths": list(self.materialPaths),
            "decisions": [materialSlotRules.decision_to_dict(d) for d in self.decisions],
            "willChange": self.willChange,
        }


@dataclass
class RenamePlan:
    """치환 계획 전체.

    Attributes:
        renameTable: 계획에 쓴 치환 표 사본
        ignoreCase: 대소문자 무시 매칭 여부
        assets: 에셋별 계획(입력 순서)
    """

    renameTable: Dict[str, str]
    ignoreCase: bool
    assets: List[AssetPlan] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """결과 JSON용 dict. 키는 추가만 한다.

        Returns:
            직렬화 가능한 dict
        """
        actionCounts = {action: 0 for action in materialSlotRules.ACTIONS}
        for asset in self.assets:
            for decision in asset.decisions:
                actionCounts[decision.action] += 1
        return {
            "renameTable": dict(self.renameTable),
            "ignoreCase": self.ignoreCase,
            "assetCount": len(self.assets),
            "loadFailureCount": sum(1 for a in self.assets if a.loadFailure),
            "willChangeCount": sum(1 for a in self.assets if a.willChange),
            "actionCounts": actionCounts,
            "assets": [a.to_dict() for a in self.assets],
        }


def _new_asset_record(inAssetPlan: AssetPlan, inDryRun: bool) -> Dict:
    """`apply_plan` 결과 레코드의 초기값을 만든다.

    결과 JSON 스키마는 **추가만** 한다 - 키를 더하고 기존 키의 의미·타입은 바꾸지 않는다
    (읽는 쪽이 `.get(key, 기본값)`이면 구 JSON과 자동 하위호환된다).

    Args:
        inAssetPlan: 에셋 계획
        inDryRun: 드라이런 여부

    Returns:
        결과 레코드
    """
    return {
        "packagePath": inAssetPlan.packagePath,
        "meshType": inAssetPlan.meshType,
        "className": inAssetPlan.className,
        "dryRun": inDryRun,
        "status": "",
        "failureReason": "",
        "failureDetail": "",
        "saved": False,
        "filePath": "",
        "slots": [
            {
                "slotIndex": d.slotIndex,
                "before": d.currentName,
                "targetName": d.targetName,
                "after": d.currentName,
                "action": d.action,
                "variantMatched": d.variantMatched,
            }
            for d in inAssetPlan.decisions
        ],
    }


def _fail(inRecord: Dict, inReason: str, inDetail: str = "") -> Dict:
    """레코드를 실패로 표시하고 로그를 남긴다.

    Args:
        inRecord: 결과 레코드
        inReason: `FAIL_*` 사유 코드
        inDetail: 사람이 읽는 상세

    Returns:
        같은 레코드
    """
    inRecord["status"] = STATUS_FAILED
    inRecord["failureReason"] = inReason
    inRecord["failureDetail"] = inDetail
    _log_error(f"실패 {inReason}: {inRecord['packagePath']} {inDetail}")
    return inRecord


def _restore_names(inMesh, inNames: Sequence[str]) -> bool:
    """실패한 에셋의 메모리 상태를 계획 시점 이름으로 되돌린다(최선 노력).

    저장하지 않더라도 메모리에 반쯤 바뀐 상태가 남으면 같은 세션의 다른 저장이 그것을
    디스크에 올릴 수 있다.

    Args:
        inMesh: 메쉬
        inNames: 되돌릴 슬롯 이름 목록

    Returns:
        되읽기로 전부 되돌아갔으면 True
    """
    try:
        current = read_slot_names(inMesh)
        for index, name in enumerate(inNames):
            if index < len(current) and current[index] != name:
                _write_slot_name_unverified(inMesh, index, name)
        return read_slot_names(inMesh) == list(inNames)
    except Exception as restoreError:  # noqa: BLE001 - 원복 실패는 결과로 드러낸다
        _log_error(f"메모리 원복 실패: {type(restoreError).__name__}: {restoreError}")
        return False


# ---------------------------------------------------------------------------
# 파사드
# ---------------------------------------------------------------------------


class MaterialSlotRenamer:
    """매테리얼 슬롯 이름 치환 파사드.

    사용 순서는 **계획 -> 확인 -> 적용**이다. `build_plan`은 에셋을 바꾸지 않으므로 그
    결과를 사람·호출자가 확인한 뒤에만 `apply_plan(inDryRun=False)`를 부른다.

    경계 (호출자 책임):
        - **P4 CL 생성·체크아웃·서밋은 이 클래스가 하지 않는다.** 저장할 에셋은 호출 전에
          체크아웃해 쓰기 가능 상태로 두어야 한다. 읽기 전용이면 `notCheckedOut`으로
          실패하고 저장하지 않는다.
        - **default CL 누출 검사(`p4 opened -c default`)는 호출자가 실행 후에 한다.**
          이 클래스는 쓰기 가능 파일만 저장하지만, 소스 컨트롤이 켜진 세션에서는 엔진이
          다른 경로로 파일을 열 수 있고 이 클래스는 P4를 보지 않는다.
        - 체크아웃 범위는 목록 전체가 아니라 **드라이런으로 확정한 변경 대상**(결과의
          `status == "dryRun"`)으로 잡는 것을 권한다 - 안 바뀐 파일을 CL에 싣지 않는다.

    Example:
        >>> renamer = MaterialSlotRenamer({"Body": "Skin_Body"})
        >>> plan = renamer.build_plan(["/Game/Chars/SK_Hero"])
        >>> preview = renamer.apply_plan(plan)                  # 드라이런(기본)
        >>> result = renamer.apply_plan(plan, inDryRun=False)   # 확인 후에만
    """

    def __init__(self, inRenameTable: Mapping[str, str], inIgnoreCase: bool = True):
        """치환 표로 파사드를 만든다.

        Args:
            inRenameTable: 구 이름 -> 정규 목표명 표
            inIgnoreCase: 대소문자 무시 매칭 여부. 기본값 True.

        Raises:
            materialSlotRules.RenameTableError: 표가 결정을 모호하게 만드는 경우
        """
        self._index = materialSlotRules.build_rename_index(inRenameTable, inIgnoreCase)

    def build_plan(self, inPackagePaths: Sequence[str]) -> RenamePlan:
        """에셋별 치환 계획을 만든다. **에셋을 바꾸지 않는다.**

        Args:
            inPackagePaths: `/Game/...` 패키지 경로 목록

        Returns:
            치환 계획(입력 순서·개수 보존, 로드 실패도 항목으로 남는다)
        """
        plan = RenamePlan(renameTable=dict(self._index.renameTable), ignoreCase=self._index.ignoreCase)
        for packagePath in inPackagePaths:
            mesh, reason, className = load_mesh(packagePath)
            if mesh is None:
                plan.assets.append(AssetPlan(packagePath=packagePath, className=className, loadFailure=reason))
                continue
            slotNames = read_slot_names(mesh)
            plan.assets.append(
                AssetPlan(
                    packagePath=packagePath,
                    meshType=mesh_type_of(mesh),
                    className=className,
                    slotNamesBefore=slotNames,
                    materialPaths=read_material_asset_paths(mesh),
                    decisions=materialSlotRules.decide_slots(slotNames, inIndex=self._index),
                )
            )
        _log(
            f"계획: 에셋 {len(plan.assets)}건, 변경 대상 {sum(1 for a in plan.assets if a.willChange)}건, "
            f"로드 실패 {sum(1 for a in plan.assets if a.loadFailure)}건"
        )
        return plan

    def apply_plan(self, inPlan: RenamePlan, inDryRun: bool = True) -> Dict:
        """계획을 적용한다. 기본은 드라이런이다.

        드라이런은 메쉬를 로드하지도 바꾸지도 않고 `save_asset`을 부르지 않는다 - 계획의
        결정을 결과 레코드 형태로 펼칠 뿐이다.

        실집행 에셋 1건의 순서(앞 단계가 실패하면 뒤 단계는 하지 않는다):
            1. 로컬 파일 확인 -> **쓰기 가능 가드**(메모리를 건드리기 전에)
            2. 다시 로드해 슬롯 이름이 계획 시점과 같은지 확인(`planStale`)
            3. 치환 슬롯마다 3단 쓰기 + 되읽기
            4. 전 슬롯 되읽기 + 매테리얼 참조·슬롯 개수 보존 확인
            5. `save_asset` 반환값 + 저장 후 되읽기 + 파일 mtime 전진 확인
            실패하면 메모리 상태를 계획 시점으로 되돌리고 저장하지 않는다.

        Args:
            inPlan: `build_plan` 결과
            inDryRun: True면 아무것도 바꾸지 않는다. 기본값 True.

        Returns:
            결과 dict(`assets` = 에셋별 레코드, `counts` = 상태별 개수, `savedCount`,
            `renamedSlotCount`). 키는 추가만 한다.
        """
        records = [self._apply_asset(assetPlan, inDryRun) for assetPlan in inPlan.assets]
        counts = {status: 0 for status in (STATUS_CHANGED, STATUS_UNCHANGED, STATUS_DRY_RUN, STATUS_FAILED)}
        for record in records:
            counts[record["status"]] += 1
        result = {
            "dryRun": inDryRun,
            "renameTable": dict(inPlan.renameTable),
            "ignoreCase": inPlan.ignoreCase,
            "assetCount": len(records),
            "counts": counts,
            "savedCount": sum(1 for r in records if r["saved"]),
            "renamedSlotCount": sum(
                1 for r in records if r["status"] == STATUS_CHANGED
                for s in r["slots"] if s["action"] == materialSlotRules.ACTION_RENAME
            ),
            "failures": [
                {"packagePath": r["packagePath"], "reason": r["failureReason"], "detail": r["failureDetail"]}
                for r in records if r["status"] == STATUS_FAILED
            ],
            "assets": records,
        }
        _log(f"적용 완료(dryRun={inDryRun}): {counts}, 저장 {result['savedCount']}건")
        return result

    def _apply_asset(self, inAssetPlan: AssetPlan, inDryRun: bool) -> Dict:
        """에셋 1건을 적용한다.

        Args:
            inAssetPlan: 에셋 계획
            inDryRun: 드라이런 여부

        Returns:
            결과 레코드
        """
        record = _new_asset_record(inAssetPlan, inDryRun)
        if inAssetPlan.loadFailure:
            return _fail(record, FAIL_LOAD, inAssetPlan.loadFailure)
        if not inAssetPlan.willChange:
            record["status"] = STATUS_UNCHANGED
            return record
        if inDryRun:
            record["status"] = STATUS_DRY_RUN
            return record

        filePath = package_file_path(inAssetPlan.packagePath)
        if filePath is None:
            return _fail(record, FAIL_UNSUPPORTED_MOUNT, inAssetPlan.packagePath)
        record["filePath"] = filePath
        if not os.path.isfile(filePath):
            return _fail(record, FAIL_FILE_MISSING, filePath)
        # 저장 가드는 메모리를 바꾸기 **전에** 건다 - 읽기 전용 에셋을 dirty로 남기지 않는다
        if not os.access(filePath, os.W_OK):
            return _fail(record, FAIL_NOT_CHECKED_OUT, filePath)

        mesh, reason, _ = load_mesh(inAssetPlan.packagePath)
        if mesh is None:
            return _fail(record, FAIL_LOAD, reason)
        if read_slot_names(mesh) != list(inAssetPlan.slotNamesBefore):
            return _fail(record, FAIL_PLAN_STALE, f"계획 후 슬롯 이름이 바뀌었다: {read_slot_names(mesh)}")

        expected = [d.targetName for d in inAssetPlan.decisions]
        try:
            for decision in inAssetPlan.decisions:
                if decision.action != materialSlotRules.ACTION_RENAME:
                    continue
                if not write_slot_name(mesh, decision.slotIndex, decision.targetName):
                    self._record_readback(record, mesh)
                    _restore_names(mesh, inAssetPlan.slotNamesBefore)
                    return _fail(
                        record, FAIL_WRITE_NOT_VERIFIED,
                        f"슬롯 {decision.slotIndex} -> {decision.targetName!r} 되읽기 불일치",
                    )
        except Exception as writeError:  # noqa: BLE001 - 한 에셋의 실패가 목록을 멈추지 않게
            _restore_names(mesh, inAssetPlan.slotNamesBefore)
            return _fail(record, FAIL_WRITE_EXCEPTION, f"{type(writeError).__name__}: {writeError}")

        self._record_readback(record, mesh)
        afterNames = [slot["after"] for slot in record["slots"]]
        afterMaterials = read_material_asset_paths(mesh)
        if afterNames != expected or afterMaterials != list(inAssetPlan.materialPaths):
            _restore_names(mesh, inAssetPlan.slotNamesBefore)
            return _fail(
                record, FAIL_READBACK_MISMATCH,
                f"이름 {afterNames} (기대 {expected}), 참조 보존 {afterMaterials == list(inAssetPlan.materialPaths)}",
            )

        mtimeBefore = os.path.getmtime(filePath)
        try:
            saveReturned = unreal.EditorAssetLibrary.save_asset(inAssetPlan.packagePath, only_if_is_dirty=False)
        except Exception as saveError:  # noqa: BLE001
            _restore_names(mesh, inAssetPlan.slotNamesBefore)
            return _fail(record, FAIL_SAVE_EXCEPTION, f"{type(saveError).__name__}: {saveError}")
        if not saveReturned:
            _restore_names(mesh, inAssetPlan.slotNamesBefore)
            return _fail(record, FAIL_SAVE_RETURNED_FALSE, filePath)
        # 반환값 True는 근거가 아니다 - 디스크에 실제로 쓰였는지와 저장 후 상태를 되읽는다
        if os.path.getmtime(filePath) <= mtimeBefore:
            return _fail(record, FAIL_SAVE_NOT_ON_DISK, f"save_asset True인데 mtime 불변: {filePath}")
        # 여기부터는 디스크에 쓰였다 - 뒤 검증이 실패해도 saved는 사실대로 True다
        record["saved"] = True
        self._record_readback(record, mesh)
        if [slot["after"] for slot in record["slots"]] != expected:
            return _fail(record, FAIL_READBACK_MISMATCH, "저장 후 되읽기 불일치")

        record["status"] = STATUS_CHANGED
        _log(f"저장: {inAssetPlan.packagePath} ({sum(1 for e, b in zip(expected, inAssetPlan.slotNamesBefore) if e != b)}슬롯)")
        return record

    @staticmethod
    def _record_readback(inRecord: Dict, inMesh) -> None:
        """메쉬에서 되읽은 슬롯 이름을 레코드의 `after`에 싣는다.

        Args:
            inRecord: 결과 레코드
            inMesh: 메쉬
        """
        names = read_slot_names(inMesh)
        for slot in inRecord["slots"]:
            index = slot["slotIndex"]
            slot["after"] = names[index] if index < len(names) else ""


__all__ = [
    "MESH_TYPE_SKELETAL",
    "MESH_TYPE_STATIC",
    "REASON_LOAD_EXCEPTION",
    "REASON_LOAD_RETURNED_NONE",
    "REASON_NOT_MESH",
    "FAIL_LOAD",
    "FAIL_UNSUPPORTED_MOUNT",
    "FAIL_FILE_MISSING",
    "FAIL_NOT_CHECKED_OUT",
    "FAIL_PLAN_STALE",
    "FAIL_WRITE_EXCEPTION",
    "FAIL_WRITE_NOT_VERIFIED",
    "FAIL_READBACK_MISMATCH",
    "FAIL_SAVE_EXCEPTION",
    "FAIL_SAVE_RETURNED_FALSE",
    "FAIL_SAVE_NOT_ON_DISK",
    "STATUS_CHANGED",
    "STATUS_UNCHANGED",
    "STATUS_DRY_RUN",
    "STATUS_FAILED",
    "mesh_type_of",
    "slot_array_property",
    "load_mesh",
    "read_slot_names",
    "read_material_asset_paths",
    "verify_slot_name",
    "write_slot_name",
    "package_file_path",
    "AssetPlan",
    "RenamePlan",
    "MaterialSlotRenamer",
]
