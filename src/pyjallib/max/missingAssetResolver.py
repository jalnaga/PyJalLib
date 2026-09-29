#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""누락 애셋 검사·정리의 pymxs 어댑터.

``missingAssetPolicy``의 계획 엔진은 순수 모듈이라 씬을 모른다. 이 모듈이 그 사이를
잇는다 - 씬에서 깨진 텍스쳐 슬롯과 잔재 노드를 모아 **확정된 값**으로 엔진에 넘기고,
엔진이 돌려준 계획을 씬에 적용한다.

**공개 형태는 2단계다.**

.. code-block:: python

    plan = missingAsset.build_purge_plan()        # 씬을 바꾸지 않는다
    result = missingAsset.apply_purge_plan(plan)  # 확인 후에만 호출

``build_purge_plan()``이 씬을 전혀 바꾸지 않는다는 점이 "검사 -> 목록 제시 -> 확인 후
정리"의 기술적 근거다. 확인 UI는 소비처가 갖고, 이 라이브러리는 계획과 실행만 제공한다.

---

**두 축이 독립이다.**

- **슬롯 분리** - 깨진 텍스쳐맵을 매테리얼 슬롯에서 떼어낸다. 매테리얼과 메쉬는 그대로
  둔다. 프로덕션에서 실제로 할 일은 거의 전부 이쪽이다(1씬 깨진 슬롯 12건).
- **노드 삭제** - 누락 애셋을 물고 있는 **비지오메트리 잔재**를 지운다. 프로덕션
  표본에서는 0건이었으나 표본 밖과 외부 반입 데이터에 대한 가드로 남긴다.

---

**실측으로 확정된 축** (2026-09-22 프로브 3회 + 2026-09-29 프로브 4회):

- **슬롯 열거·분리는 서브 텍스쳐맵 표준 인터페이스로 한다** -
  ``getNumSubTexmaps`` / ``getSubTexmap`` / ``getSubTexmapSlotName`` /
  ``setSubTexmap``. **클래스를 가리지 않는 것이 이 인터페이스의 값이다.** 기존
  MeshValidator 검증이 ``DirectX_9_Shader`` 전용이라 ``Standardmaterial``의 깨진
  텍스쳐를 놓쳤던 것이 실기 미검출의 원인이었다.

  - 실패한 접근 2종을 기록해 둔다. ``getClassInstances(rt.material)``은 수퍼클래스라
    거부당하고(``requires MAXClass``), ``getPropNames``로 슬롯을 뒤지면 매테리얼 12개를
    찾고도 슬롯명을 **0건** 잡는다. 둘 다 조용히 0을 내므로 되풀이하기 쉽다.
  - **``DirectX_9_Shader``는 ``getSubTexmapSlotName``이 빈 문자열을 준다.** 표시 이름
    폴백은 계획 엔진(``missingAssetPolicy``)이 만든다.

- **부재 판정은 직접 한다** - ``os.path.exists`` + ``rt.mapPaths.getFullFilePath``.
  ``AssetManager``를 쓰지 않는다: 슬롯을 뗀 뒤에도 그 애셋 테이블은 ``ATSOps.Refresh()``
  후까지 줄지 않아 **멱등이 성립하지 않는다**(2026-09-29 실측). 같은 이유로 그 테이블에는
  과거에 제거된 텍스쳐의 기록이 남아 프로덕션에서 누락 78건 중 72건(92%)이 **어떤 객체도
  참조하지 않는** 잔재로 나왔다.
- **매테리얼 열거는 클래스 목록을 하드코딩하지 않는다** - 노드 할당 매테리얼과
  ``sceneMaterials``를 기점으로 모아 재귀한다. 클래스 표를 두면 새 셰이더를 조용히 놓친다.
- **``rt.refs.dependentNodes(asset)``는 무인자로 충분하다.** 키워드 조합
  (``firstOnly`` / ``baseObjectOnly`` / ``immediateOnly``) 5종이 전부 같은 결과를 줬고,
  비트맵을 기점으로 주면 머티리얼을 건너뛰고 노드까지 닿는다.
- **지오메트리 판별은 ``superClassOf(node) == rt.GeometryClass``다.** 실측 분포:
  정상 메쉬 ``GeometryClass`` / 헬퍼 ``helper`` / 라이트 ``light`` /
  **미해결 XRef 객체 ``system``**. Missing 플러그인 클래스 6종은 ``node``로,
  어느 것도 ``GeometryClass``가 아니다.
- **``rt.delete(node)``는 예외 없이 ``1``(int)을 돌려준다.** 반환값을 확인해 실패를
  기록한다.
- **``max undo``를 롤백 축으로 쓰지 않는다.** 헤드리스에서는 바깥 hold가 열려 있어
  픽스처 생성까지 한 undo 그룹에 묶이고, 실측에서 씬 전체가 비워졌다.
"""

import os
from typing import Any, Dict, List, Optional

import pymxs
from pymxs import runtime as rt

from pyjallib.logger import Logger
from pyjallib.max.missingAssetPolicy import (
    ASSET_KIND_FILE,
    ASSET_KIND_PLUGIN,
    build_plan_summary,
    build_purge_plan,
)

#: 텍스쳐맵에서 파일 경로를 읽을 프로퍼티 후보. 대부분 ``filename``이지만 VRay 계열은
#: 다른 이름을 쓴다. **이 표가 불완전해도 슬롯 열거 자체는 성립하고**, 경로를 못 읽은
#: 슬롯이 "깨졌다"로 오판되지 않을 뿐이다(안전측).
_TEXMAP_PATH_PROPS = ("filename", "HDRIMapName", "fileName")

#: **노드 축**이 쓰는 텍스쳐맵 클래스. 라이트의 ``projectorMap``처럼 노드가 직접 문
#: 텍스쳐는 서브 텍스쳐맵 인터페이스로 노출되지 않아 클래스 열거가 필요하다.
#:
#: 이 표가 불완전하면 **노드가 직접 문 비표준 텍스쳐맵**만 놓친다 - 매테리얼 쪽은
#: 슬롯 축이 클래스 무관으로 덮으므로 구멍이 거기까지 번지지 않는다.
_TEXMAP_CLASSES = ("BitmapTexture", "VRayHDRI")

#: Missing 플러그인 객체의 클래스 이름 접두. 실측된 6종(GeomObject/Helper/Light/
#: Camera/Shape/System)이 전부 이 접두를 쓰고, 어느 것도 ``GeometryClass``가 아니다.
_MISSING_CLASS_PREFIX = "missing"

#: 서브 텍스쳐맵 재귀 깊이 상한. 프로덕션 표본에서 중첩은 0건이었으나 Composite·Mix
#: 계열이 들어올 수 있어 열어 둔다. 순환은 핸들 방문 기록으로 막는다.
_MAX_SLOT_DEPTH = 6

# 모듈 단일 지연 Logger. Logger는 생성 시 같은 로그 파일에 핸들러를 새로 부착하므로
# 인스턴스마다 만들면 긴 DCC 세션에서 파일 핸들이 누수되고 롤오버가 충돌한다.
_logger: Optional[Logger] = None


def _get_logger() -> Logger:
    """모듈 단일 Logger를 지연 생성해 반환한다.

    임포트 시점에 만들지 않는 이유는, 이 기능을 쓰지 않는 프로젝트에서 모듈이
    임포트만 되어도 로그 파일이 생기는 것을 막기 위함이다.

    Returns:
        모듈 단일 Logger 인스턴스
    """
    global _logger
    if _logger is None:
        _logger = Logger(inLogFileName="pyjallib_missingAsset", inEnableConsole=False)
    return _logger


def _norm_path(inPath: Any) -> str:
    """경로를 비교용으로 정규화한다.

    Args:
        inPath: 원본 경로

    Returns:
        소문자 + 정방향 슬래시로 통일한 문자열
    """
    return str(inPath or "").replace("\\", "/").lower()


def _anim_handle(inAnim: Any) -> Optional[int]:
    """애님(노드·매테리얼·텍스쳐맵)의 핸들을 정수로 읽는다.

    Args:
        inAnim: 대상 객체

    Returns:
        핸들 정수. 조회에 실패하면 None
    """
    try:
        return int(rt.getHandleByAnim(inAnim))
    except Exception:
        return None


def _anim_name(inAnim: Any) -> str:
    """애님의 이름을 문자열로 읽는다.

    Args:
        inAnim: 대상 객체

    Returns:
        이름. 조회에 실패하면 빈 문자열
    """
    try:
        return str(inAnim.name)
    except Exception:
        return ""


def _class_name(inAnim: Any) -> str:
    """애님의 클래스 이름을 문자열로 읽는다.

    Args:
        inAnim: 대상 객체

    Returns:
        클래스 이름. 조회에 실패하면 빈 문자열
    """
    try:
        return str(rt.classOf(inAnim))
    except Exception:
        return ""


def is_geometry_node(inNode: Any) -> Optional[bool]:
    """노드가 지오메트리인지 판정한다.

    **판별에 실패하면 ``False``가 아니라 ``None``을 돌려준다.** 계획 엔진은 ``None``을
    보고 쪽으로 보내므로, 판별 실패가 삭제로 이어지지 않는다 - 이 반환 규약이 안전측
    catch-all의 절반을 담당한다.

    Args:
        inNode: 대상 노드

    Returns:
        지오메트리면 True, 아니면 False, 판별 불가면 None
    """
    try:
        return bool(rt.superClassOf(inNode) == rt.GeometryClass)
    except Exception:
        return None


def _node_record(inNode: Any) -> Dict[str, Any]:
    """계획 엔진에 넘길 노드 레코드를 만든다.

    Args:
        inNode: 대상 노드

    Returns:
        ``{"handle", "name", "isGeometry"}`` 레코드
    """
    return {
        "handle": _anim_handle(inNode),
        "name": _anim_name(inNode),
        "isGeometry": is_geometry_node(inNode),
    }


def _dependent_nodes(inObject: Any) -> List[Any]:
    """참조 대상에 의존하는 노드 목록을 돌려준다.

    Args:
        inObject: 역추적 기점이 될 참조 대상

    Returns:
        의존 노드 목록. 조회에 실패하면 빈 목록
    """
    try:
        return list(rt.refs.dependentNodes(inObject))
    except Exception:
        return []


def asset_exists(inFilePath: str) -> bool:
    """애셋 경로가 실제로 존재하는지 **직접** 판정한다.

    절대 경로면 그대로 보고, 상대 경로·맨 파일명이면 Max의 맵 경로 탐색
    (``rt.mapPaths.getFullFilePath``)에 맡긴다.

    ``AssetManager``에 묻지 않는 이유는 멱등이다 - 그 애셋 테이블은 슬롯을 뗀 뒤에도
    ``ATSOps.Refresh()`` 후까지 갱신되지 않아, 정리해도 재스캔이 계속 "누락"이라 한다
    (2026-09-29 실측).

    Args:
        inFilePath: 판정할 경로

    Returns:
        존재하면 True
    """
    if not inFilePath:
        return False
    if os.path.isabs(inFilePath) and os.path.exists(inFilePath):
        return True
    try:
        resolved = rt.mapPaths.getFullFilePath(inFilePath)
    except Exception:
        return False
    return bool(resolved) and os.path.exists(str(resolved))


def _texmap_path(inTexmap: Any) -> str:
    """텍스쳐맵이 물고 있는 파일 경로를 읽는다.

    **두 채널을 분리한다.** 프로퍼티가 없는 것(텍스쳐맵이지만 파일을 안 쓰는 종류)과
    값이 파일 경로가 아닌 것은 둘 다 "경로 없음"이지만, 접근 예외를 경로 없음과 같이
    다루면 진단 정보를 잃는다. 여기서는 후보를 순서대로 시도하고 **처음 읽히는 문자열**을
    쓴다.

    Args:
        inTexmap: 텍스쳐맵 객체

    Returns:
        경로 문자열. 읽지 못하면 빈 문자열
    """
    for propName in _TEXMAP_PATH_PROPS:
        try:
            value = rt.getProperty(inTexmap, propName)
        except Exception:
            continue
        if value is None or isinstance(value, (bool, int, float)):
            continue
        text = str(value)
        if text:
            return text
    return ""


def _slot_owner_roots() -> List[Dict[str, Any]]:
    """슬롯 순회의 기점을 모은다 - **노드와 매테리얼 양쪽**.

    **클래스 목록을 하드코딩하지 않는다.** 클래스 표를 두면 새 셰이더가 들어올 때
    조용히 놓친다.

    **노드도 기점이다.** 라이트의 ``projectorMap``처럼 매테리얼을 거치지 않고 노드가
    직접 텍스쳐를 무는 경우가 있다. 매테리얼만 훑으면 그것이 두 축 모두에서 빠진다
    (2026-09-29 Type C가 실제로 이 구멍에 걸렸다).

    Returns:
        ``{"owner", "isNode"}`` 목록(핸들 기준 중복 제거)
    """
    roots = []
    seen = set()

    def _add(inOwner: Any, inIsNode: bool) -> None:
        """중복을 피해 기점 목록에 넣는다."""
        if inOwner is None:
            return
        handle = _anim_handle(inOwner)
        if handle is None or handle in seen:
            return
        seen.add(handle)
        roots.append({"owner": inOwner, "isNode": inIsNode})

    try:
        sceneNodes = list(rt.objects)
    except Exception as exc:
        _get_logger().warning(f"씬 노드 열거 실패: {exc}")
        sceneNodes = []
    for node in sceneNodes:
        _add(node, True)
        try:
            _add(node.material, False)
        except Exception:
            continue

    try:
        for material in rt.sceneMaterials:
            _add(material, False)
    except Exception as exc:
        _get_logger().debug(f"sceneMaterials 열거 실패: {exc}")

    return roots


def _sub_texmap_count(inOwner: Any) -> int:
    """소유자의 서브 텍스쳐맵 슬롯 수를 읽는다.

    Args:
        inOwner: 매테리얼 또는 텍스쳐맵

    Returns:
        슬롯 수. 조회에 실패하면 0
    """
    try:
        return int(rt.getNumSubTexmaps(inOwner))
    except Exception:
        return 0


def collect_broken_slots() -> List[Dict[str, Any]]:
    """깨진 텍스쳐를 물고 있는 슬롯을 모은다. **씬을 바꾸지 않는다.**

    노드와 매테리얼에서 시작해 서브 텍스쳐맵을 재귀로 훑는다. 텍스쳐맵 자신도 같은
    인터페이스를 가지므로 중첩(Composite·Mix 등)도 같은 코드가 덮는다.

    각 레코드의 ``ownerIsNode``가 두 축을 가른다. **매테리얼 슬롯은 떼고**(메쉬를
    지키면서 고칠 수 있다), **노드가 직접 문 텍스쳐는 노드 축이 다룬다**(그 노드가
    비지오메트리 잔재면 삭제 대상이다). 같은 것을 두 번 손대지 않기 위한 구분이다.

    Returns:
        슬롯 레코드 목록. 각 원소는 ``{"ownerHandle", "ownerName", "ownerClass",
        "ownerIsNode", "slotIndex", "slotName", "path", "nodeNames"}``
    """
    records: List[Dict[str, Any]] = []
    visited = set()

    def _walk(inOwner: Any, inIsNode: bool, inDepth: int) -> None:
        """소유자의 서브 텍스쳐맵을 훑고 중첩으로 내려간다."""
        if inDepth > _MAX_SLOT_DEPTH:
            return
        ownerHandle = _anim_handle(inOwner)
        if ownerHandle is not None:
            if ownerHandle in visited:
                return
            visited.add(ownerHandle)

        for index in range(1, _sub_texmap_count(inOwner) + 1):
            try:
                texmap = rt.getSubTexmap(inOwner, index)
            except Exception:
                continue
            if texmap is None:
                continue

            filePath = _texmap_path(texmap)
            if filePath and not asset_exists(filePath):
                try:
                    slotName = str(rt.getSubTexmapSlotName(inOwner, index))
                except Exception:
                    slotName = ""
                records.append(
                    {
                        "ownerHandle": ownerHandle,
                        "ownerName": _anim_name(inOwner),
                        "ownerClass": _class_name(inOwner),
                        "ownerIsNode": inIsNode,
                        "slotIndex": index,
                        "slotName": slotName,
                        "path": filePath,
                        "nodeNames": [
                            _anim_name(node) for node in _dependent_nodes(texmap)
                        ],
                    }
                )

            # 중첩 텍스쳐맵의 소유자는 더 이상 노드가 아니다 - 텍스쳐맵이다.
            _walk(texmap, False, inDepth + 1)

    for root in _slot_owner_roots():
        _walk(root["owner"], root["isNode"], 0)

    return records


def collect_missing_assets(
    inBrokenSlots: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """씬에서 누락 애셋과 그 의존 노드를 모은다. **씬을 바꾸지 않는다.**

    외부 파일 부재와 Missing 플러그인 객체를 모두 훑는다.

    Args:
        inBrokenSlots: 이미 모아 둔 슬롯 레코드. None이면 여기서 다시 훑는다.
            호출부가 슬롯을 이미 갖고 있으면 넘겨서 **씬을 두 번 훑지 않는다**

    Returns:
        계획 엔진에 넘길 애셋 레코드 목록
    """
    records = list(_collect_missing_files(inBrokenSlots))
    records.extend(_collect_missing_plugins())
    return records


def _collect_missing_files(
    inBrokenSlots: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """깨진 텍스쳐를 참조하는 **노드**를 애셋 레코드로 모은다.

    슬롯 레코드와 같은 순회를 쓰되, 여기서는 "그 텍스쳐를 물고 있는 노드"를 낸다.
    노드 축과 슬롯 축은 독립이고, 이쪽은 **비지오메트리 잔재를 잡는** 데 쓴다.

    Args:
        inBrokenSlots: 이미 모아 둔 슬롯 레코드. None이면 여기서 다시 훑는다

    Returns:
        ``kind``가 ``file``인 애셋 레코드 목록
    """
    byPath: Dict[str, Dict[str, Any]] = {}

    def _record(inTexmap: Any, inDetail: str) -> None:
        """텍스쳐맵 하나를 애셋 레코드로 접는다."""
        filePath = _texmap_path(inTexmap)
        if not filePath or asset_exists(filePath):
            return
        entry = byPath.setdefault(
            _norm_path(filePath),
            {
                "kind": ASSET_KIND_FILE,
                "path": filePath,
                "detail": inDetail,
                "nodes": [],
                "_handles": set(),
            },
        )
        for node in _dependent_nodes(inTexmap):
            nodeRecord = _node_record(node)
            if nodeRecord["handle"] in entry["_handles"]:
                continue
            entry["_handles"].add(nodeRecord["handle"])
            entry["nodes"].append(nodeRecord)

    # 텍스쳐맵을 **클래스로 전수 열거**한다. 슬롯 순회만으로는 부족하다 - 라이트의
    # ``projectorMap``처럼 노드가 직접 문 텍스쳐는 서브 텍스쳐맵 인터페이스로
    # 노출되지 않아 거기서 빠진다(2026-09-29 Type C가 이 구멍에 걸렸다).
    #
    # 이 표가 불완전하면 **노드가 직접 문 비표준 텍스쳐맵**만 놓친다. 매테리얼 쪽은
    # 슬롯 축이 클래스 무관으로 덮으므로 구멍이 거기까지 번지지 않는다.
    for className in _TEXMAP_CLASSES:
        klass = getattr(rt, className, None)
        if klass is None:
            continue
        try:
            instances = list(rt.getClassInstances(klass))
        except Exception as exc:
            _get_logger().debug(f"{className} 열거 실패: {exc}")
            continue
        for texmap in instances:
            _record(texmap, className)

    # 슬롯 순회가 찾은 텍스쳐맵도 합친다 - 위 표에 없는 클래스가 매테리얼 슬롯에
    # 물려 있으면 여기서 건진다.
    slots = collect_broken_slots() if inBrokenSlots is None else inBrokenSlots
    for slot in slots:
        key = _norm_path(slot["path"])
        if key in byPath:
            continue
        byPath[key] = {
            "kind": ASSET_KIND_FILE,
            "path": slot["path"],
            "detail": slot["ownerClass"],
            "nodes": [],
            "_handles": set(),
        }

    for entry in byPath.values():
        entry.pop("_handles", None)
    return list(byPath.values())


def _collect_missing_plugins() -> List[Dict[str, Any]]:
    """플러그인 DLL이 없어 로드되지 않은 객체를 모은다.

    클래스 이름이 ``Missing``으로 시작하는 노드를 후보로 잡는다. 실측된 6종
    (``Missing_GeomObject`` / ``Helper`` / ``Light`` / ``Camera`` / ``Shape`` /
    ``System``)이 전부 이 접두를 쓰고, 어느 것도 ``GeometryClass``가 아니다.

    Returns:
        ``kind``가 ``plugin``인 애셋 레코드 목록
    """
    records = []
    try:
        sceneNodes = list(rt.objects)
    except Exception as exc:
        _get_logger().warning(f"씬 노드 열거 실패: {exc}")
        return records

    for node in sceneNodes:
        classNames = [_class_name(node)]
        try:
            classNames.append(str(rt.classOf(node.baseObject)))
        except Exception:
            pass
        if not any(
            name.lower().startswith(_MISSING_CLASS_PREFIX) for name in classNames if name
        ):
            continue

        records.append(
            {
                "kind": ASSET_KIND_PLUGIN,
                "path": "",
                "detail": classNames[0],
                "nodes": [_node_record(node)],
            }
        )

    return records


class MissingAsset:
    """누락 애셋 검사·정리 파사드.

    계획 수립과 적용이 분리돼 있다. :meth:`build_purge_plan`은 씬을 읽기만 하고,
    :meth:`apply_purge_plan`만이 씬을 바꾼다.

    .. code-block:: python

        missingAsset = MissingAsset()
        plan = missingAsset.build_purge_plan()
        if not plan["empty"]:
            # 사용자 확인을 받은 뒤에만
            result = missingAsset.apply_purge_plan(plan)
    """

    def build_purge_plan(self) -> Dict[str, Any]:
        """씬을 스캔해 정리 계획을 만든다. **씬을 바꾸지 않는다.**

        슬롯을 한 번만 훑어 두 축을 만든다 - 매테리얼 슬롯은 분리 대상으로, 노드가
        직접 문 텍스쳐는 노드 축으로 보낸다.

        Returns:
            :func:`pyjallib.max.missingAssetPolicy.build_purge_plan`의 계획 dict
        """
        brokenSlots = collect_broken_slots()
        # 노드가 직접 문 텍스쳐(라이트 projectorMap 등)는 떼지 않는다 - 그 노드가
        # 비지오메트리 잔재면 노드 축이 통째로 지우고, 지오메트리면 보고로 남는다.
        materialSlots = [slot for slot in brokenSlots if not slot.get("ownerIsNode")]
        plan = build_purge_plan(collect_missing_assets(brokenSlots), materialSlots)
        _get_logger().debug(
            f"계획 수립: 애셋 {len(plan['assets'])}건, "
            f"슬롯 분리 {len(plan['detachSlots'])}개, "
            f"삭제 {len(plan['deleteNodes'])}개, 보고 {len(plan['reportNodes'])}개"
        )
        return plan

    def build_plan_summary(self, inPlan: Dict[str, Any]) -> str:
        """계획의 사람이 읽을 요약 문구를 돌려준다.

        Args:
            inPlan: :meth:`build_purge_plan` 결과

        Returns:
            요약 문구
        """
        return build_plan_summary(inPlan)

    def apply_purge_plan(self, inPlan: Dict[str, Any]) -> Dict[str, Any]:
        """계획을 씬에 적용한다 - 슬롯 분리 후 노드 삭제.

        **순서가 정해져 있다.** 슬롯을 먼저 뗀다 - 노드를 먼저 지우면 그 노드가 물고
        있던 매테리얼이 함께 사라져 슬롯 분리 대상을 복원하지 못할 수 있다. 반대
        순서에는 그런 의존이 없다.

        **``reportNodes``는 손대지 않는다.** 지오메트리이거나 판별 불가이므로 지우지
        않는다 - 그것이 이 사이클의 핵심 안전 축이다.

        Args:
            inPlan: :meth:`build_purge_plan` 결과

        Returns:
            ``{"detached": [...], "deleted": [...], "failed": [{"name", "reason"}...]}``
        """
        detached: List[str] = []
        deleted: List[str] = []
        failed: List[Dict[str, str]] = []

        plan = inPlan or {}
        slotTargets = list(plan.get("detachSlots") or [])
        nodeTargets = list(plan.get("deleteNodes") or [])
        if not slotTargets and not nodeTargets:
            return {"detached": detached, "deleted": deleted, "failed": failed}

        logger = _get_logger()
        with pymxs.undo(True):
            for slot in slotTargets:
                label = f"{slot.get('ownerName')}.{slot.get('displayName')}"
                owner = self._resolve_anim(slot.get("ownerHandle"))
                if owner is None:
                    failed.append({"name": label, "reason": "매테리얼을 찾지 못했다"})
                    continue
                try:
                    rt.setSubTexmap(owner, int(slot.get("slotIndex")), None)
                except Exception as exc:
                    failed.append({"name": label, "reason": f"setSubTexmap 예외: {exc}"})
                    continue
                detached.append(label)

            for record in nodeTargets:
                name = str(record.get("name") or "")
                node = self._resolve_node(record)
                if node is None:
                    failed.append({"name": name, "reason": "노드를 찾지 못했다"})
                    continue

                # 계획을 세운 뒤 씬이 바뀌었을 수 있다. 지우기 직전에 다시 확인한다 -
                # 가드는 계획 쪽과 실행 쪽 양쪽에 둔다.
                if is_geometry_node(node) is not False:
                    failed.append(
                        {"name": name, "reason": "삭제 직전 재확인에서 비지오메트리가 아니었다"}
                    )
                    continue

                try:
                    returned = rt.delete(node)
                except Exception as exc:
                    failed.append({"name": name, "reason": f"rt.delete 예외: {exc}"})
                    continue

                if returned is False:
                    failed.append({"name": name, "reason": "rt.delete가 False를 돌려줬다"})
                    continue
                deleted.append(name)

        logger.info(
            f"정리 실행: 슬롯 분리 {len(detached)}개, 삭제 {len(deleted)}개, "
            f"실패 {len(failed)}개"
        )
        for failure in failed:
            logger.warning(f"정리 실패: {failure['name']} - {failure['reason']}")

        return {"detached": detached, "deleted": deleted, "failed": failed}

    def _resolve_anim(self, inHandle: Any) -> Any:
        """핸들로 애님(매테리얼 등)을 복원한다.

        Args:
            inHandle: 핸들

        Returns:
            복원된 객체. 찾지 못하면 None
        """
        if inHandle is None:
            return None
        try:
            return rt.getAnimByHandle(inHandle)
        except Exception:
            return None

    def _resolve_node(self, inRecord: Dict[str, Any]) -> Any:
        """계획의 노드 레코드를 씬의 실제 노드로 복원한다.

        핸들로 먼저 찾는다. 이름은 씬 안에서 유일하지 않으므로(동명 노드가 실재한다)
        핸들이 없을 때의 차선책일 뿐이다.

        Args:
            inRecord: 노드 레코드

        Returns:
            복원된 노드. 찾지 못하면 None
        """
        node = self._resolve_anim(inRecord.get("handle"))
        if node is not None:
            return node

        name = inRecord.get("name")
        if not name:
            return None
        try:
            return rt.getNodeByName(name)
        except Exception:
            return None
