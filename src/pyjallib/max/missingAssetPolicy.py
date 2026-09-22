#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""누락 애셋 정리 계획 엔진 (순수 모듈).

`.max` 씬은 외부 파일(비트맵·XRef 등)과 플러그인 DLL에 의존한다. 그 의존이 끊어지면
머지·임포트가 끌고 들어온 잔재 노드가 씬에 남아 익스포트·검증·구조 변환을 각자 다른
얼굴로 오염시킨다. 이 모듈은 "무엇을 지우고 무엇을 보고할 것인가"를 판정한다.

**판정 축은 "누락 애셋을 참조하는가"가 아니라 "누락 애셋을 참조하는 비지오메트리
노드인가"다.** 텍스쳐 한 장이 없다는 이유로 메쉬를 지우면 되돌릴 수 없는 작업 손실이다.
그래서 지오메트리는 **삭제하지 않고 보고**한다. 이 비대칭이 이 모듈의 존재 이유이고,
삭제 대상을 넓히는 변경은 그 자체로 설계 위반이다.

안전측 규율 세 가지가 서로를 보강한다.

1. 지오메트리 여부가 **불명(``None``)이면 보고**로 보낸다. 판별에 실패한 노드를
   삭제하지 않는다 - catch-all이 안전한 쪽에 있어야 오판의 대가가 작다.
2. 같은 노드가 여러 애셋에 걸려 **관측이 엇갈리면 안전한 쪽이 이긴다.** 한 번이라도
   지오메트리이거나 불명으로 관측됐으면 보고다.
3. 계획을 세우는 것과 적용하는 것을 분리한다. 이 모듈은 계획만 만들고 씬을 모른다.

``pymxs``에 의존하지 않는다. 씬에서 재료를 모으는 일은 ``missingAssetResolver``
어댑터가 하고, 이 모듈은 이미 확정된 값(경로·핸들·지오메트리 여부)만 받는다. 그래야
경우의 수를 콘솔 pytest(Type A)로 전수 검증할 수 있다 - DCC 안에서는 "지오메트리
판별에 실패한 노드" 같은 경우를 만드는 것 자체가 비싸거나 불가능하다.

노드 식별자는 3ds Max 노드 핸들(정수)을 쓴다. pymxs 노드 래퍼는 같은 노드라도 조회
경로에 따라 서로 다른 객체가 되어 ``set`` 원소로 쓸 수 없기 때문이다.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

#: 애셋 종류 - 외부 파일이 없다(비트맵·XRef·포토메트릭 등).
ASSET_KIND_FILE = "file"

#: 애셋 종류 - 플러그인 DLL이 없어 객체가 로드되지 않았다(Missing 계열).
ASSET_KIND_PLUGIN = "plugin"

ALL_ASSET_KINDS = (ASSET_KIND_FILE, ASSET_KIND_PLUGIN)

#: 노드에 내리는 조치 - 삭제한다(비지오메트리로 **실측된** 노드에 한한다).
ACTION_DELETE = "delete"

#: 노드에 내리는 조치 - 보고만 한다(지오메트리이거나 판별 불가).
ACTION_REPORT = "report"

#: 보고 사유 - 지오메트리로 실측됐다.
REASON_GEOMETRY = "geometry"

#: 보고 사유 - 지오메트리 여부를 판별하지 못했다(안전측 catch-all).
REASON_UNKNOWN = "unknown"

#: 문구에 나열할 노드 수 상한. 잔재가 수백 개인 씬이 실재하므로(프로덕션 표본에서
#: 씬당 누락 후보 최대 72건) 상한 없이 나열하면 문구가 행동 지시를 묻는다. 넘는
#: 나머지는 개수로 접고 **전체 목록은 계획 dict가 갖는다**.
MAX_LISTED_NODES = 30


def _node_key(inNode: Dict[str, Any]) -> Any:
    """노드 레코드의 중복 제거 키를 돌려준다.

    핸들이 있으면 핸들을 쓴다. 이름은 씬 안에서 유일하지 않으므로(동명 노드가
    실재한다) 핸들이 없을 때의 차선책일 뿐이다.

    Args:
        inNode: 노드 레코드

    Returns:
        해시 가능한 키
    """
    handle = inNode.get("handle")
    if handle is not None:
        return ("handle", handle)
    return ("name", inNode.get("name"))


def _normalize_geometry_flag(inValue: Any) -> Optional[bool]:
    """지오메트리 여부 값을 ``True`` / ``False`` / ``None``으로 정규화한다.

    truthiness로 읽지 않는다. ``bool``이 아닌 값은 전부 **불명**으로 떨어뜨려
    안전측 경로로 보낸다 - 어댑터가 판별에 실패해 문자열이나 정수를 흘려도
    그것이 삭제로 이어지지 않아야 한다.

    Args:
        inValue: 어댑터가 실측한 값

    Returns:
        ``bool`` 이면 그 값, 그 외는 ``None``
    """
    if inValue is True:
        return True
    if inValue is False:
        return False
    return None


def _normalize_node(inNode: Dict[str, Any]) -> Dict[str, Any]:
    """노드 레코드를 정규화한다.

    Args:
        inNode: ``{"handle", "name", "isGeometry"}`` 형태의 원본 레코드

    Returns:
        정규화된 노드 레코드
    """
    return {
        "handle": inNode.get("handle"),
        "name": str(inNode.get("name") or ""),
        "isGeometry": _normalize_geometry_flag(inNode.get("isGeometry")),
    }


def _normalize_kind(inKind: Any) -> str:
    """애셋 종류를 정규화한다.

    아는 종류가 아니면 ``file``로 떨어뜨리지 않고 **원문을 보존**한다. 종류는
    보고 문구에만 쓰이고 삭제 판정에 관여하지 않으므로, 모르는 값을 아는 값으로
    바꾸면 진단 정보만 잃는다.

    Args:
        inKind: 원본 종류 값

    Returns:
        종류 문자열
    """
    text = str(inKind or "").strip()
    return text or ASSET_KIND_FILE


def build_purge_plan(inAssetRecords: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """누락 애셋 레코드에서 정리 계획을 만든다.

    이 함수는 씬을 모르고 아무것도 바꾸지 않는다. 계획을 세우는 것과 적용하는 것이
    분리돼 있다는 점이 "검사 → 목록 제시 → 확인 후 삭제"의 기술적 근거다.

    Args:
        inAssetRecords: 누락 애셋 레코드의 순회 가능 객체. 각 레코드는
            ``{"kind", "path", "detail", "nodes"}`` 형태이고, ``nodes``의 각 원소는
            ``{"handle", "name", "isGeometry"}`` 형태다. ``isGeometry``가 ``None``
            이면 판별 실패를 뜻하고 그 노드는 보고 쪽으로 간다.

    Returns:
        계획 dict.

        - ``assets``: 정규화된 애셋 레코드 목록(입력 순서 보존)
        - ``deleteNodes``: 삭제 대상 노드 목록. **모든 관측에서 비지오메트리로
          실측된 노드만** 들어간다
        - ``reportNodes``: 보고 대상 노드 목록. 각 원소에 ``reason``
          (``geometry`` | ``unknown``)이 붙는다
        - ``empty``: 삭제할 것이 없으면 ``True``. **보고가 남아 있어도 삭제 대상이
          없으면 ``True``다** - 이 플래그의 축은 "적용할 일이 있는가"이고,
          누락 애셋 자체의 유무는 ``hasFindings``가 말한다
        - ``hasFindings``: 삭제든 보고든 하나라도 있으면 ``True``
    """
    assets: List[Dict[str, Any]] = []
    orderedKeys: List[Any] = []
    nodeByKey: Dict[Any, Dict[str, Any]] = {}
    # 관측이 엇갈릴 수 있으므로 노드마다 관측값을 모아 두고 마지막에 판정한다.
    observationsByKey: Dict[Any, List[Optional[bool]]] = {}

    for record in inAssetRecords or []:
        nodes = [_normalize_node(node) for node in (record.get("nodes") or [])]
        nodeKeys = []
        for node in nodes:
            key = _node_key(node)
            nodeKeys.append(key)
            if key not in nodeByKey:
                orderedKeys.append(key)
                nodeByKey[key] = node
                observationsByKey[key] = []
            observationsByKey[key].append(node["isGeometry"])

        assets.append(
            {
                "kind": _normalize_kind(record.get("kind")),
                "path": str(record.get("path") or ""),
                "detail": str(record.get("detail") or ""),
                "nodes": nodes,
                "nodeKeys": nodeKeys,
            }
        )

    deleteNodes: List[Dict[str, Any]] = []
    reportNodes: List[Dict[str, Any]] = []

    for key in orderedKeys:
        node = dict(nodeByKey[key])
        observations = observationsByKey[key]

        # 안전측 판정: 한 번이라도 지오메트리이거나 불명이면 보고다.
        # 삭제로 가는 유일한 경로는 "모든 관측이 False"뿐이다.
        if any(value is True for value in observations):
            node["isGeometry"] = True
            node["action"] = ACTION_REPORT
            node["reason"] = REASON_GEOMETRY
            reportNodes.append(node)
            continue
        if any(value is None for value in observations):
            node["isGeometry"] = None
            node["action"] = ACTION_REPORT
            node["reason"] = REASON_UNKNOWN
            reportNodes.append(node)
            continue

        node["isGeometry"] = False
        node["action"] = ACTION_DELETE
        deleteNodes.append(node)

    return {
        "assets": assets,
        "deleteNodes": deleteNodes,
        "reportNodes": reportNodes,
        "empty": not deleteNodes,
        "hasFindings": bool(deleteNodes or reportNodes),
    }


def _format_node_names(
    inNodes: Iterable[Dict[str, Any]], inLimit: int = MAX_LISTED_NODES
) -> str:
    """노드 이름을 상한까지 나열하고 나머지는 개수로 접는다.

    Args:
        inNodes: 노드 레코드 목록
        inLimit: 나열 상한

    Returns:
        ``"a, b, c 및 5개 더"`` 형태의 문자열. 노드가 없으면 빈 문자열
    """
    names = [str(node.get("name") or "") for node in inNodes]
    if not names:
        return ""
    listed = ", ".join(names[:inLimit])
    remaining = len(names) - min(len(names), inLimit)
    if remaining > 0:
        listed += f" 및 {remaining}개 더"
    return listed


def summarize_assets_by_kind(inPlan: Dict[str, Any]) -> Dict[str, int]:
    """계획의 애셋을 종류별로 센다.

    Args:
        inPlan: :func:`build_purge_plan` 결과

    Returns:
        ``{종류: 개수}``
    """
    counts: Dict[str, int] = {}
    for asset in inPlan.get("assets") or []:
        kind = asset.get("kind") or ASSET_KIND_FILE
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def build_plan_summary(inPlan: Dict[str, Any], inLimit: int = MAX_LISTED_NODES) -> str:
    """사람이 읽을 계획 요약 문구를 만든다.

    문구는 **자기완결형**이다 - 무엇이 몇 건이고, 무엇을 지우며, 무엇을 지우지 않는지가
    한 문단에서 끝난다. 호출부가 문맥을 덧붙이지 않아도 뜻이 통해야 확인 다이얼로그에
    그대로 실을 수 있다.

    Args:
        inPlan: :func:`build_purge_plan` 결과
        inLimit: 이름 나열 상한. 넘는 나머지는 개수로 접는다

    Returns:
        요약 문구. 누락 애셋이 하나도 없으면 그 사실을 말하는 문구
    """
    deleteNodes = inPlan.get("deleteNodes") or []
    reportNodes = inPlan.get("reportNodes") or []
    assets = inPlan.get("assets") or []

    if not deleteNodes and not reportNodes:
        return "누락된 애셋이 없습니다."

    kindCounts = summarize_assets_by_kind(inPlan)
    kindParts = []
    if kindCounts.get(ASSET_KIND_FILE):
        kindParts.append(f"외부 파일 부재 {kindCounts[ASSET_KIND_FILE]}건")
    if kindCounts.get(ASSET_KIND_PLUGIN):
        kindParts.append(f"플러그인 미로드 {kindCounts[ASSET_KIND_PLUGIN]}건")
    for kind, count in sorted(kindCounts.items()):
        if kind not in ALL_ASSET_KINDS:
            kindParts.append(f"{kind} {count}건")

    lines = [
        f"누락 애셋 {len(assets)}건을 찾았습니다"
        + (f" ({', '.join(kindParts)})" if kindParts else "")
        + "."
    ]

    if deleteNodes:
        lines.append(
            f"삭제 대상 비지오메트리 노드 {len(deleteNodes)}개: "
            f"{_format_node_names(deleteNodes, inLimit)}."
        )
    else:
        lines.append("삭제할 비지오메트리 노드는 없습니다.")

    geometryNodes = [
        node for node in reportNodes if node.get("reason") == REASON_GEOMETRY
    ]
    unknownNodes = [
        node for node in reportNodes if node.get("reason") == REASON_UNKNOWN
    ]

    if geometryNodes:
        lines.append(
            f"지오메트리 노드 {len(geometryNodes)}개는 삭제하지 않고 보고만 합니다"
            f"(작업 손실 방지): {_format_node_names(geometryNodes, inLimit)}."
        )
    if unknownNodes:
        lines.append(
            f"지오메트리 여부를 판별하지 못한 노드 {len(unknownNodes)}개도 "
            f"삭제하지 않습니다: {_format_node_names(unknownNodes, inLimit)}."
        )

    return " ".join(lines)


def split_nodes_by_action(
    inPlan: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """계획의 노드를 조치별로 나눠 돌려준다.

    호출부가 키 이름을 직접 알 필요가 없게 하는 얇은 접근자다.

    Args:
        inPlan: :func:`build_purge_plan` 결과

    Returns:
        ``(삭제 대상, 보고 대상)`` 튜플
    """
    return (
        list(inPlan.get("deleteNodes") or []),
        list(inPlan.get("reportNodes") or []),
    )
