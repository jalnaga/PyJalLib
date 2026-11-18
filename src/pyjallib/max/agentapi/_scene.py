# -*- coding: utf-8 -*-
"""agentapi 내부 보조 — 장면 노드 handle 집합 차이로 생성 노드를 찾는다(비공개).

agentapi 하위 모듈이 원본 함수가 반환하지 않는 부수 생성물(스냅샷 메시, 대체 Dummy 등)까지
``created``에 담을 수 있도록, 호출 전후 장면 노드 handle 집합을 비교한다.
이 모듈은 에이전트 함수가 아니며 ``agentSupport`` 계약도 넓히지 않는다(명세 J-5).

함수 목록:
    snapshot_handles — 장면 모든 노드의 노드 handle 집합을 돌려준다 [none]
    created_since — 이전 집합에 없던 현재 노드 목록을 handle 오름차순으로 돌려준다 [none]

사전 조건:
    3ds Max의 Python에서만 동작한다. pymxs는 함수 안에서만 지연 import한다.

handle 규약:
    handle은 ``agentSupport``와 같은 노드 handle(``node.inode.handle``)이다.
"""


def _runtime():
    """pymxs runtime을 지연 import해 돌려준다."""
    from pymxs import runtime as rt

    return rt


def _scene_nodes(inRt) -> list:
    """장면의 유효한 노드 목록(``rt.objects``)을 돌려준다."""
    return [node for node in inRt.objects if inRt.isValidNode(node)]


def snapshot_handles() -> set:
    """장면 모든 노드의 노드 handle 집합을 돌려준다.

    Returns:
        ``node.inode.handle`` 정수 집합

    Side effects: none
    Undo: n/a
    """
    rt = _runtime()
    return {int(node.inode.handle) for node in _scene_nodes(rt)}


def created_since(inBefore: set) -> list:
    """``inBefore``에 없던 현재 장면 노드를 handle 오름차순으로 돌려준다.

    Args:
        inBefore: ``snapshot_handles()``가 호출 전에 돌려준 handle 집합

    Returns:
        새로 생긴 pymxs 노드 list(handle 오름차순)

    Side effects: none
    Undo: n/a
    """
    rt = _runtime()
    before = set(inBefore)
    created = [node for node in _scene_nodes(rt) if int(node.inode.handle) not in before]
    created.sort(key=lambda node: int(node.inode.handle))
    return created
