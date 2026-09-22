#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""누락 애셋 검사·정리의 pymxs 어댑터.

``missingAssetPolicy``의 계획 엔진은 순수 모듈이라 씬을 모른다. 이 모듈이 그 사이를
잇는다 - 씬에서 누락 애셋과 그 의존 노드를 모아 **확정된 값**(경로·핸들·지오메트리
여부)으로 엔진에 넘기고, 엔진이 돌려준 계획을 씬에 적용한다.

역할 분담이 이렇게 갈리는 이유는 검증 비용이다. 분류 규칙은 순수하게 분리해야 콘솔
pytest(Type A)로 경우의 수를 전수 덮을 수 있고, 씬 접근과 클래스 판정은 원리적으로
3ds Max 안에서만 확인된다(Type C).

**공개 형태는 2단계다.**

.. code-block:: python

    plan = missingAsset.build_purge_plan()        # 씬을 바꾸지 않는다
    result = missingAsset.apply_purge_plan(plan)  # 확인 후에만 호출

``build_purge_plan()``이 씬을 전혀 바꾸지 않는다는 점이 "검사 -> 목록 제시 -> 확인 후
삭제"의 기술적 근거다. 확인 UI는 소비처가 갖고, 이 라이브러리는 계획과 실행만 제공한다.

---

**실측으로 확정된 축** (2026-09-22 / 3ds Max 2024 헤드리스 프로브 3회):

- **열거는 ``rt.AssetManager``로 한다.** ``getClassInstances(BitmapTexture)`` 열거는
  프로덕션 씬에서 **누락을 한 건도 못 찾았다** - 이 파이프라인의 머티리얼이
  ``DirectX_9_Shader``이고 텍스쳐가 셰이더 파라미터 안에 있어 ``BitmapTexture``
  인스턴스로 열거되지 않기 때문이다.
- **부재 판정은 ``AssetUser.GetFullFilePath()``가 빈 문자열인가로 한다.** Max 자신의
  애셋 탐색(맵 경로·상대 경로 해석)을 그대로 쓰므로 ``os.path.exists`` 자체 판정이
  상대 경로에서 갈릴 여지가 없다. 합성 씬에서 두 축의 불일치는 0건이었다.
- **``AssetUser``는 역추적 기점이 못 된다** - 참조 대상(ReferenceTarget)이 아니라
  기록이다. 그래서 "애셋에서 노드로"가 아니라 **"경로를 들고 있는 객체를 열거하고
  거기서 ``refs.dependentNodes``로 노드로"** 간다.
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

#: 경로를 들고 있을 수 있는 클래스 - ``(클래스명, 파일 프로퍼티, 슬롯 파라미터까지
#: 훑을지)``. 역추적 기점을 모으는 데 쓴다. 열거 자체는 ``AssetManager``가 하므로 이
#: 표가 불완전해도 **누락을 놓치지는 않고**, 그 애셋에 노드가 붙지 않을 뿐이다(안전측).
#:
#: 세 번째 값은 셰이더처럼 텍스쳐를 **파라미터로 갖는** 클래스에만 켠다. 비트맵마다
#: ``getPropNames``를 부르면 텍스쳐 수백 개짜리 씬에서 그만큼 왕복이 생기고 얻는 것은
#: 없다(비트맵의 경로는 ``filename`` 하나로 끝난다).
_ASSET_HOLDER_SPECS = (
    ("BitmapTexture", "filename", False),
    ("DirectX_9_Shader", "effectfile", True),
    ("VRayHDRI", "HDRIMapName", False),
)

#: Missing 플러그인 객체의 클래스 이름 접두. 실측된 6종(GeomObject/Helper/Light/
#: Camera/Shape/System)이 전부 이 접두를 쓰고, 어느 것도 ``GeometryClass``가 아니다.
_MISSING_CLASS_PREFIX = "missing"

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


def _node_handle(inNode: Any) -> Optional[int]:
    """노드 핸들을 정수로 읽는다.

    Args:
        inNode: 대상 노드

    Returns:
        핸들 정수. 조회에 실패하면 None
    """
    try:
        return int(rt.getHandleByAnim(inNode))
    except Exception:
        return None


def _node_name(inNode: Any) -> str:
    """노드 이름을 문자열로 읽는다.

    Args:
        inNode: 대상 노드

    Returns:
        노드 이름. 조회에 실패하면 빈 문자열
    """
    try:
        return str(inNode.name)
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
        "handle": _node_handle(inNode),
        "name": _node_name(inNode),
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


def _holder_map() -> Dict[str, List[Any]]:
    """ "애셋 경로 -> 그 경로를 참조하는 노드들" 맵을 만든다.

    ``AssetManager``의 ``AssetUser``는 참조 대상이 아니라 기록이라 역추적 기점이 되지
    못한다. 그래서 반대 방향으로 간다 - 경로를 들고 있을 수 있는 클래스를 열거하고,
    각각에서 ``refs.dependentNodes``로 노드를 얻어 경로에 붙인다.

    Returns:
        ``{정규화 경로: [노드, ...]}``
    """
    byPath: Dict[str, List[Any]] = {}

    for className, propName, walkSlots in _ASSET_HOLDER_SPECS:
        klass = getattr(rt, className, None)
        if klass is None:
            continue
        try:
            instances = list(rt.getClassInstances(klass))
        except Exception:
            continue

        for instance in instances:
            nodes = _dependent_nodes(instance)
            if not nodes:
                continue
            for path in _holder_paths(instance, propName, walkSlots):
                byPath.setdefault(path, []).extend(nodes)

    return byPath


def _holder_paths(
    inHolder: Any, inPropName: str, inWalkSlots: bool = False
) -> List[str]:
    """보유 객체가 들고 있는 애셋 경로를 모은다.

    **두 예외 채널을 분리한다.** 프로퍼티 접근이 예외를 던진 것("애셋이 물려 있는데
    못 열었다")과 값이 애셋이 아닌 것(bool 파라미터 등)은 전혀 다르다. 이 둘을 합치면
    이름에 ``texture``가 든 bool 파라미터가 누락으로 새어나간다.

    Args:
        inHolder: 경로를 들고 있을 수 있는 객체
        inPropName: 대표 파일 프로퍼티 이름
        inWalkSlots: 텍스쳐 슬롯 파라미터까지 훑을지 여부. 셰이더처럼 텍스쳐를
            **파라미터로 갖는** 클래스에만 켠다 - 비트맵 하나하나에 ``getPropNames``를
            부르면 텍스쳐가 수백 개인 씬에서 그만큼 왕복이 생기고 얻는 것은 없다

    Returns:
        정규화된 경로 목록
    """
    paths = []

    primary = _read_path_property(inHolder, inPropName)
    if primary:
        paths.append(primary)

    if not inWalkSlots:
        return paths

    # DirectX_9_Shader는 텍스쳐를 **파라미터**로 갖는다. 이름은 후보를 좁히고
    # 값만이 판정한다 - 이름에 texture가 든 bool 파라미터가 실재한다.
    try:
        propertyNames = [str(name) for name in rt.getPropNames(inHolder)]
    except Exception:
        propertyNames = []

    for propertyName in propertyNames:
        if "texture" not in propertyName.lower():
            continue
        try:
            slotValue = rt.getProperty(inHolder, propertyName)
        except Exception:
            # 접근 예외 = 텍스쳐가 물려 있다. 경로는 모르므로 여기서는 보탤 것이 없다.
            continue
        if slotValue is None or isinstance(slotValue, (bool, int, float)):
            continue
        nested = _read_path_property(slotValue, "filename")
        if nested:
            paths.append(nested)

    return paths


def _read_path_property(inObject: Any, inPropName: str) -> str:
    """객체의 파일 프로퍼티를 읽어 정규화된 경로로 돌려준다.

    Args:
        inObject: 대상 객체
        inPropName: 프로퍼티 이름

    Returns:
        정규화된 경로. 경로가 아니면 빈 문자열
    """
    try:
        value = rt.getProperty(inObject, inPropName)
    except Exception:
        return ""
    if value is None or isinstance(value, (bool, int, float)):
        return ""
    text = str(value)
    if not text:
        return ""
    return _norm_path(text)


def collect_missing_assets() -> List[Dict[str, Any]]:
    """씬에서 누락 애셋과 그 의존 노드를 모은다. **씬을 바꾸지 않는다.**

    외부 파일 부재와 Missing 플러그인 객체를 모두 훑는다.

    Returns:
        계획 엔진에 넘길 애셋 레코드 목록
    """
    records = list(_collect_missing_files())
    records.extend(_collect_missing_plugins())
    return records


def _collect_missing_files() -> List[Dict[str, Any]]:
    """해석되지 않는 외부 파일 애셋을 모은다.

    Returns:
        ``kind``가 ``file``인 애셋 레코드 목록
    """
    assetMan = getattr(rt, "AssetManager", None)
    if assetMan is None:
        _get_logger().warning(
            "rt.AssetManager가 노출되지 않아 외부 파일 검사를 건너뛴다"
        )
        return []

    try:
        assetCount = int(assetMan.GetNumAssets())
    except Exception as exc:
        _get_logger().warning(f"AssetManager.GetNumAssets 실패: {exc}")
        return []

    holderMap = _holder_map()
    records = []

    for index in range(1, assetCount + 1):
        try:
            assetUser = assetMan.GetAssetByIndex(index)
        except Exception as exc:
            _get_logger().debug(f"GetAssetByIndex({index}) 실패: {exc}")
            continue
        if assetUser is None:
            continue

        fileName = _safe_str(lambda: assetUser.GetFileName())
        fullPath = _safe_str(lambda: assetUser.GetFullFilePath())
        assetType = _safe_str(lambda: assetUser.GetType()) or ASSET_KIND_FILE

        # 해석에 성공했으면 부재가 아니다. 이 축이 Max 자신의 애셋 탐색을 그대로 쓴다.
        if fullPath:
            continue

        nodes = holderMap.get(_norm_path(fileName), [])
        records.append(
            {
                "kind": ASSET_KIND_FILE,
                "path": fileName,
                "detail": assetType,
                "nodes": [_node_record(node) for node in nodes],
            }
        )

    return records


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
        classNames = []
        for getter in (
            lambda: str(rt.classOf(node)),
            lambda: str(rt.classOf(node.baseObject)),
        ):
            try:
                classNames.append(getter())
            except Exception:
                continue
        if not any(
            name.lower().startswith(_MISSING_CLASS_PREFIX) for name in classNames
        ):
            continue

        records.append(
            {
                "kind": ASSET_KIND_PLUGIN,
                "path": "",
                "detail": classNames[0] if classNames else "",
                "nodes": [_node_record(node)],
            }
        )

    return records


def _safe_str(inGetter) -> str:
    """호출 결과를 문자열로 읽되 실패하면 빈 문자열을 돌려준다.

    Args:
        inGetter: 인자 없는 호출 가능 객체

    Returns:
        문자열 결과. 실패하면 빈 문자열
    """
    try:
        value = inGetter()
    except Exception:
        return ""
    return "" if value is None else str(value)


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

        Returns:
            :func:`pyjallib.max.missingAssetPolicy.build_purge_plan`의 계획 dict
        """
        plan = build_purge_plan(collect_missing_assets())
        _get_logger().debug(
            f"계획 수립: 애셋 {len(plan['assets'])}건, "
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
        """계획의 삭제 대상을 씬에서 지운다.

        **``deleteNodes``만 지운다.** ``reportNodes``는 지오메트리이거나 판별 불가라
        이 메서드가 손대지 않는다 - 그것이 이 사이클의 핵심 안전 축이다.

        삭제는 undo 컨텍스트 안에서 수행하고, ``rt.delete``의 **반환값을 확인해**
        실패를 기록한다. 노드가 이미 사라졌거나 삭제가 거부돼도 예외로 중단하지 않고
        ``failed``에 남긴다 - 한 노드의 실패가 나머지 정리를 막지 않아야 한다.

        Args:
            inPlan: :meth:`build_purge_plan` 결과

        Returns:
            ``{"deleted": [이름...], "failed": [{"name", "reason"}...]}``
        """
        deleted: List[str] = []
        failed: List[Dict[str, str]] = []

        targets = list((inPlan or {}).get("deleteNodes") or [])
        if not targets:
            return {"deleted": deleted, "failed": failed}

        logger = _get_logger()
        with pymxs.undo(True):
            for record in targets:
                name = str(record.get("name") or "")
                node = self._resolve_node(record)
                if node is None:
                    failed.append({"name": name, "reason": "노드를 찾지 못했다"})
                    continue

                # 계획을 세운 뒤 씬이 바뀌었을 수 있다. 지우기 직전에 다시 확인한다 -
                # 가드는 계획 쪽과 실행 쪽 양쪽에 둔다.
                if is_geometry_node(node) is not False:
                    failed.append(
                        {
                            "name": name,
                            "reason": "삭제 직전 재확인에서 비지오메트리가 아니었다",
                        }
                    )
                    continue

                try:
                    returned = rt.delete(node)
                except Exception as exc:
                    failed.append({"name": name, "reason": f"rt.delete 예외: {exc}"})
                    continue

                if returned is False:
                    failed.append(
                        {"name": name, "reason": "rt.delete가 False를 돌려줬다"}
                    )
                    continue
                deleted.append(name)

        logger.info(f"정리 실행: 삭제 {len(deleted)}개, 실패 {len(failed)}개")
        for failure in failed:
            logger.warning(f"삭제 실패: {failure['name']} - {failure['reason']}")

        return {"deleted": deleted, "failed": failed}

    def _resolve_node(self, inRecord: Dict[str, Any]) -> Any:
        """계획의 노드 레코드를 씬의 실제 노드로 복원한다.

        핸들로 먼저 찾는다. 이름은 씬 안에서 유일하지 않으므로(동명 노드가 실재한다)
        핸들이 없을 때의 차선책일 뿐이다.

        Args:
            inRecord: 노드 레코드

        Returns:
            복원된 노드. 찾지 못하면 None
        """
        handle = inRecord.get("handle")
        if handle is not None:
            try:
                node = rt.getAnimByHandle(handle)
                if node is not None:
                    return node
            except Exception:
                pass

        name = inRecord.get("name")
        if not name:
            return None
        try:
            return rt.getNodeByName(name)
        except Exception:
            return None
