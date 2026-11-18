#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""버텍스 I/O 어댑터 - 씬 조작을 `SceneOps` 하나로 모은다.

지휘 로직(`splitService`)이 이 클래스를 **주입받게** 두면, 분기·호출 횟수·선택 복원
순서를 pymxs mock 없이 Type A로 단정할 수 있다. Type C는 씬 조작 자체의 정확성만
지면 된다.

pymxs는 **함수 안에서** import한다. 모듈 최상단에서 import하면 콘솔에서 이 모듈을
건드리는 순간 죽어, 순수 모듈까지 Type A 밖으로 밀려난다.

---

## Phase 0 실측이 이 구현을 규정한다

**읽기 = snapshot 경유 오브젝트 좌표.** `rt.snapshot(node)`은 입력이 Editable_Poly든
Editable_Mesh든 **Editable_mesh 노드**를 돌려주고, 버텍스 수·순서·오브젝트 좌표를
보존하며 노드 트랜스폼도 그대로 유지한다(6케이스 실측). 모디파이어가 있으면 평가된
형상을 잡는다. 그래서 타입별 분기 없이 한 경로로 읽는다. 임시 snapshot 노드는
`finally`에서 `rt.delete()`한다.

**직접 읽기를 쓰지 않는 이유.** `polyop.getVert(node,i)`·`meshop.getVert(node,i)`는
**월드** 좌표를 주고, 모디파이어가 얹혀 있으면 **평가된** 값을 준다. 반면 `setVert`는
**베이스**에 쓴다. 읽기와 쓰기의 대상이 다르므로 읽기-수정-쓰기 왕복이 멱등이 아니다
(Bend를 얹고 월드 `(99,99,99)`를 쓴 뒤 읽으면 `(106.92, 99, 19.13)`). snapshot으로
평탄화한 노드에만 쓰면 이 함정에 걸리지 않는다.

**쓰기 = 오브젝트 좌표를 월드로 바꿔 `setVert`.** `setVert`의 측정된 입력 공간은
월드뿐이다. 항등 트랜스폼에서는 변환이 수치상 무연산이다.

**거짓 값을 돌려주는 지점에는 호출 후 재확인 가드를 둔다.**

| 상황 | 실측 거동 | 가드 |
|:---|:---|:---|
| 삭제된 노드 접근 | `RuntimeError` | `rt.isValidNode` 선행 |
| 빈 메쉬 `getNumVerts` | 예외 없이 `0` | `> 0` 확인 |
| 프리미티브에 `polyop` | `RuntimeError` | baseObject 클래스 선행 판별 |
| 인덱스 0 / n+1 | `RuntimeError` | 1-based 범위 |
| `WM3_MC_BuildFromNode` 버텍스 수 불일치 | **`True` 반환, `HasData`는 `False`** | 호출 후 `WM3_MC_HasData` 재확인 |
"""

import numpy as np

from pyjallib.max import morphSpaceTransform as spaceTransform


class SceneOps:
    """3ds Max 씬 조작을 한 곳에 모은 어댑터.

    이 클래스가 pymxs와 닿는 유일한 표면이다. 지휘 로직은 이 객체를 주입받으므로
    가짜 구현으로 대체해 콘솔에서 검증할 수 있다.
    """

    # snapshot 임시 노드에 붙이는 접두. 정리 실패 시 씬에서 눈에 띄게 한다.
    TEMP_NODE_PREFIX = "__msSplitTemp__"

    # pymxs가 실제로 던지는 예외 형태(Phase 0 섹션 G 실측):
    #   삭제된 노드 접근 / 프리미티브에 polyop / 범위 밖 인덱스 -> RuntimeError
    #   프로퍼티 부재 -> AttributeError
    # 이 두 개만 잡는다. 광범위 except는 진짜 버그(TypeError 등)까지 삼킨다.
    PYMXS_ERRORS = (RuntimeError, AttributeError)

    def __init__(self, inLogger=None) -> None:
        """어댑터를 초기화한다. pymxs를 여기서 끌어오지 않는다.

        Args:
            inLogger: 정리 실패 같은 부수 문제를 남길 로거. None이면 남기지 않는다.
        """
        self._rt = None
        self._logger = inLogger

    def _warn(self, inMessage: str) -> None:
        """부수 문제를 로그에 남긴다. 로거가 없으면 아무것도 하지 않는다."""
        if self._logger is not None:
            self._logger.warning(f"[MorphSplitter] {inMessage}")

    @property
    def rt(self):
        """pymxs 런타임을 지연 로드해 반환한다.

        Returns:
            `pymxs.runtime`
        """
        if self._rt is None:
            from pymxs import runtime as rt

            self._rt = rt
        return self._rt

    # ------------------------------------------------------------
    # 노드 조회
    # ------------------------------------------------------------
    def is_valid_geometry_node(self, inNode) -> bool:
        """노드가 살아 있는 지오메트리 노드인지 판정한다.

        삭제된 노드에 접근하면 `RuntimeError`가 나므로(실측), 무엇을 하기 전에
        `isValidNode`로 먼저 막는다.

        Args:
            inNode: 검사할 노드. `None`이어도 안전하다.

        Returns:
            유효한 지오메트리 노드면 True
        """
        if inNode is None:
            return False
        try:
            if self.rt.isValidNode(inNode) is not True:
                return False
            return self.rt.superClassOf(inNode) == self.rt.GeometryClass
        except self.PYMXS_ERRORS:
            return False

    def node_name(self, inNode) -> str:
        """노드 이름을 문자열로 반환한다. 유효하지 않으면 빈 문자열."""
        if not self.is_valid_geometry_node(inNode):
            return ""
        return str(inNode.name)

    def node_handle(self, inNode) -> int:
        """노드 핸들을 반환한다.

        노드 동일성은 **핸들로만** 판정한다. 래퍼 객체는 조회 경로마다 다른 객체라
        `is` 비교가 성립하지 않고, 이름은 동명·자동 리네임 때문에 부적합하다.

        Args:
            inNode: 대상 노드

        Returns:
            노드 핸들. 유효하지 않으면 -1.
        """
        if not self.is_valid_geometry_node(inNode):
            return -1
        return int(self.rt.getHandleByAnim(inNode))

    def are_same_node(self, inNodeA, inNodeB) -> bool:
        """두 노드가 같은 노드인지 핸들로 판정한다."""
        handleA = self.node_handle(inNodeA)
        handleB = self.node_handle(inNodeB)
        if handleA < 0 or handleB < 0:
            return False
        return handleA == handleB

    def get_vertex_count(self, inNode) -> int:
        """노드의 버텍스 수를 반환한다.

        `snapshotAsMesh` 경유로 세므로 지오메트리 타입·모디파이어와 무관하다.
        프리미티브에 `polyop`을 부르면 예외가 나므로(실측) 그 경로를 쓰지 않는다.

        Args:
            inNode: 대상 노드

        Returns:
            버텍스 수. 유효하지 않으면 0.
        """
        if not self.is_valid_geometry_node(inNode):
            return 0
        try:
            mesh = self.rt.snapshotAsMesh(inNode)
            return int(self.rt.getNumVerts(mesh))
        except self.PYMXS_ERRORS:
            return 0

    def get_transform(self, inNode) -> spaceTransform.Transform:
        """노드 트랜스폼을 basis + origin으로 읽는다.

        Args:
            inNode: 대상 노드

        Returns:
            Transform 인스턴스

        Raises:
            ValueError: 노드가 유효하지 않을 때
        """
        if not self.is_valid_geometry_node(inNode):
            raise ValueError(
                "트랜스폼을 읽을 수 없다 - 유효한 지오메트리 노드가 아니다."
            )

        matrix = inNode.transform
        rows = []
        for rowName in ("row1", "row2", "row3", "row4"):
            row = getattr(matrix, rowName)
            rows.append((float(row.x), float(row.y), float(row.z)))
        return spaceTransform.make_transform(*rows)

    def get_existing_node_names(self) -> list[str]:
        """씬에 있는 모든 노드 이름을 반환한다.

        이름 충돌 감지에 쓴다. 씬 접근은 여기서 끝나고, 판정은 순수 함수가 한다.
        """
        return [str(n.name) for n in self.rt.objects]

    # ------------------------------------------------------------
    # 선택 보관·복원
    # ------------------------------------------------------------
    def get_selection(self) -> list:
        """현재 선택을 **파이썬 리스트로 떠서** 반환한다.

        `rt.selection`은 스냅샷이 아니라 라이브 뷰다. 그것을 그대로 들고 있으면 이후
        조작이 선택을 바꾸는 순간 "원래 선택"도 함께 변한다.
        """
        return list(self.rt.getCurrentSelection())

    def restore_selection(self, inNodes) -> None:
        """보관한 선택을 되돌린다.

        Args:
            inNodes: `get_selection()`이 돌려준 노드 리스트
        """
        alive = [n for n in (inNodes or []) if self.is_valid_geometry_node(n)]
        if alive:
            self.rt.select(self.rt.Array(*alive))
        else:
            self.rt.clearSelection()

    # ------------------------------------------------------------
    # 읽기
    # ------------------------------------------------------------
    def read_object_coords(self, inNode) -> np.ndarray:
        """노드의 버텍스를 **오브젝트 공간** 좌표 배열로 읽는다.

        snapshot으로 평탄화한 임시 노드를 만들어 그 `mesh` 값에서 읽는다.
        `getVert(mesh, i)`가 오브젝트 공간을 준다는 것이 실측된 유일한 경로다.

        Args:
            inNode: 대상 노드

        Returns:
            `(N, 3)` float64 오브젝트 공간 좌표

        Raises:
            ValueError: 노드가 유효하지 않거나 버텍스가 0개일 때
        """
        if not self.is_valid_geometry_node(inNode):
            raise ValueError("버텍스를 읽을 수 없다 - 유효한 지오메트리 노드가 아니다.")

        rt = self.rt
        tempNode = None
        try:
            tempNode = rt.snapshot(inNode)
            tempNode.name = f"{self.TEMP_NODE_PREFIX}{inNode.name}"

            mesh = tempNode.mesh
            count = int(rt.getNumVerts(mesh))
            # 빈 메쉬의 getNumVerts는 예외 없이 0을 준다(실측). 0을 그냥 넘기면
            # 아래 루프가 조용히 빈 배열을 만들어 "성공"으로 보인다.
            if count <= 0:
                raise ValueError(f"버텍스가 0개다: {inNode.name}")

            coords = np.empty((count, 3), dtype=np.float64)
            getVert = rt.getVert
            for i in range(count):
                point = getVert(mesh, i + 1)
                coords[i, 0] = float(point.x)
                coords[i, 1] = float(point.y)
                coords[i, 2] = float(point.z)
            return coords
        finally:
            if tempNode is not None:
                try:
                    if rt.isValidNode(tempNode) is True:
                        rt.delete(tempNode)
                except self.PYMXS_ERRORS as e:
                    # 정리 실패로 읽기 실패를 덮어쓰지 않는다. 대신 로그에 남긴다 -
                    # 접두가 붙어 있으므로 씬에서도 눈에 띈다.
                    self._warn(
                        f"임시 snapshot 노드 삭제 실패({self.TEMP_NODE_PREFIX}...): {e}"
                    )

    # ------------------------------------------------------------
    # 쓰기
    # ------------------------------------------------------------
    def create_split_node(self, inSourceNode, inName: str, inObjectCoords):
        """소스 노드를 snapshot해 새 노드를 만들고 오브젝트 좌표를 기록한다.

        snapshot 결과는 모디파이어가 없는 Editable_mesh이므로, `setVert`가 베이스에
        쓰는 것과 읽기가 평가 형상을 보는 것의 비대칭에 걸리지 않는다.

        Args:
            inSourceNode: 형상·트랜스폼을 물려받을 소스 노드(뉴트럴)
            inName: 새 노드 이름
            inObjectCoords: `(N, 3)` 오브젝트 공간 좌표

        Returns:
            생성된 노드

        Raises:
            ValueError: 소스가 유효하지 않거나, 버텍스 수가 맞지 않거나,
                기록 후 재확인에서 좌표가 반영되지 않았을 때
        """
        if not self.is_valid_geometry_node(inSourceNode):
            raise ValueError("소스 노드가 유효한 지오메트리 노드가 아니다.")

        rt = self.rt
        coords = np.asarray(inObjectCoords, dtype=np.float64)
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError(f"좌표 배열은 (N, 3) 형태여야 한다: {coords.shape}")

        transform = self.get_transform(inSourceNode)
        worldCoords = spaceTransform.object_to_world(coords, transform)

        newNode = rt.snapshot(inSourceNode)
        try:
            newNode.name = inName

            mesh = newNode.mesh
            count = int(rt.getNumVerts(mesh))
            if count != coords.shape[0]:
                raise ValueError(
                    f"생성 노드의 버텍스 수가 좌표 개수와 다르다: {count} vs {coords.shape[0]}"
                )

            # 쓰기 전에 "실제로 값이 바뀌는" 표본 인덱스를 고른다. 첫·중간·끝 고정으로는
            # 그 지점의 델타가 0일 때 setVert 무동작을 잡지 못한다(실기 애셋은
            # 2,116개 중 216개만 움직이므로 이 위양성이 실제로 가능하다).
            sampleIndices = self._pick_write_samples(newNode, coords)

            setVert = rt.meshop.setVert
            point3 = rt.Point3
            for i in range(count):
                # numpy 스칼라를 그대로 넘기지 않는다. pymxs가 받는 타입을 명시한다.
                setVert(
                    newNode,
                    i + 1,
                    point3(
                        float(worldCoords[i, 0]),
                        float(worldCoords[i, 1]),
                        float(worldCoords[i, 2]),
                    ),
                )
            rt.update(newNode)

            self._assert_coords_written(newNode, coords, sampleIndices)
            return newNode
        except Exception:
            # 반쪽 노드를 씬에 남기지 않는다. 실패는 삼키지 않고 그대로 올린다.
            try:
                if rt.isValidNode(newNode) is True:
                    rt.delete(newNode)
            except self.PYMXS_ERRORS as cleanupError:
                self._warn(f"실패한 노드 {inName} 정리 실패: {cleanupError}")
            raise

    def _pick_write_samples(self, inNode, inTargetObjectCoords) -> list:
        """쓰기가 값을 실제로 바꾸는 지점 3개를 표본으로 고른다.

        `create_split_node`는 소스를 snapshot한 노드에 쓰므로, 목표 좌표가 소스와
        같은 버텍스에서는 쓰기가 원래 무동작이다. 그런 지점을 표본으로 잡으면
        재확인이 공허해진다.

        Args:
            inNode: 쓰기 대상 노드(아직 쓰기 전)
            inTargetObjectCoords: 기록할 오브젝트 좌표

        Returns:
            표본 버텍스 인덱스 리스트(0-based)
        """
        rt = self.rt
        expected = np.asarray(inTargetObjectCoords, dtype=np.float64)
        count = expected.shape[0]

        mesh = inNode.mesh
        initial = np.empty((count, 3), dtype=np.float64)
        getVert = rt.getVert
        for i in range(count):
            point = getVert(mesh, i + 1)
            initial[i, 0] = float(point.x)
            initial[i, 1] = float(point.y)
            initial[i, 2] = float(point.z)

        diffs = np.abs(expected - initial).max(axis=1)
        order = np.argsort(diffs)[::-1]
        samples = [int(i) for i in order[:3] if diffs[int(i)] > 0.0]
        if samples:
            return samples

        # 목표가 소스와 완전히 동일하다(델타 0). 쓰기가 무동작인 것이 정상이므로
        # 존재 확인 수준으로만 본다.
        return sorted({0, count // 2, count - 1})

    def _assert_coords_written(
        self, inNode, inExpectedObjectCoords, inSampleIndices
    ) -> None:
        """기록이 실제로 반영됐는지 되읽어 확인한다.

        3ds Max는 명령이 무동작이어도 예외를 던지지 않는 경우가 있다(실측 §28).
        "썼다"를 믿지 않고 표본을 되읽어 대조한다.

        되읽기는 `node.mesh` 경유이므로 **오브젝트 공간**이다. 기대값도 오브젝트
        공간이라 변환이 끼지 않는다.

        Args:
            inNode: 방금 기록한 노드
            inExpectedObjectCoords: 기대 오브젝트 좌표
            inSampleIndices: 되읽어 대조할 버텍스 인덱스(`_pick_write_samples` 결과)

        Raises:
            ValueError: 표본 좌표가 기대와 다를 때
        """
        rt = self.rt
        expected = np.asarray(inExpectedObjectCoords, dtype=np.float64)
        count = expected.shape[0]

        mesh = inNode.mesh
        sampleIndices = [i for i in inSampleIndices if 0 <= i < count]
        if not sampleIndices:
            raise ValueError("재확인 표본 인덱스가 없다 - 기록 검증을 건너뛸 수 없다.")
        maxDev = 0.0
        for idx in sampleIndices:
            point = rt.getVert(mesh, idx + 1)
            actual = np.array([float(point.x), float(point.y), float(point.z)])
            maxDev = max(maxDev, float(np.abs(actual - expected[idx]).max()))

        # float32 저장 정밀도를 허용한다. 좌표 크기 200 기준 1 ULP는 약 1.5e-5.
        tolerance = 1e-3
        if maxDev > tolerance:
            raise ValueError(
                f"좌표 기록이 반영되지 않았다(표본 최대 편차 {maxDev:.6g} > {tolerance}). "
                "setVert가 무동작이었을 수 있다."
            )
