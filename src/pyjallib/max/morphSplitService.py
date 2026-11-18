#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""분리 실행 오케스트레이션 (Facade + 의존성 주입).

씬 조작을 `SceneOps` 하나로 모아 **주입받는다.** 그래서 지휘 로직 - 검증 실패 시
쓰기를 하지 않는지, 읽기 1회·쓰기 2회인지, 선택을 언제 보관·복원하는지 - 를
pymxs mock 없이 Type A로 단정할 수 있다.

**선택 보관은 맨 앞에 둔다.** 부작용을 되돌리는 코드는 부작용을 만드는 모든 경로보다
앞에 있어야 한다. 검증·조회 뒤에 두면 그 조회가 선택해 놓은 것을 "원래 선택"으로
오인한다(`rt.selection`은 라이브 뷰라 이 사고가 실제로 난다).

실패는 삼키지 않는다. 문제를 모아 `SplitError`로 올리고, UI가 그것을 사용자에게 보여준다.
"""

from dataclasses import dataclass

import numpy as np

from pyjallib.max import morphNaming as naming, morphMath as splitCore, morphValidation as validation


class SplitError(Exception):
    """분리 실행이 거부되거나 실패했음을 알리는 예외.

    Attributes:
        problems: 사람이 읽는 문제 설명 목록
    """

    def __init__(self, inMessage: str, inProblems=None) -> None:
        super().__init__(inMessage)
        self.problems: list[str] = list(inProblems or [])


@dataclass
class SplitRequest:
    """분리 실행 요청.

    Attributes:
        neutralNode: 뉴트럴 메쉬 노드
        poseNode: 합쳐진 포즈 메쉬 노드
        axis: 대칭축 ("X" / "Y" / "Z")
        planeOffset: 대칭면 오프셋
        bandRatio: 밴드 반폭 비율. `bandHalfWidth`가 None일 때 쓰인다.
        bandHalfWidth: 밴드 반폭 절대값. None이면 비율로 해석한다.
        leftSuffix: 좌 접미사
        rightSuffix: 우 접미사
    """

    neutralNode: object = None
    poseNode: object = None
    axis: str = splitCore.AXIS_X
    planeOffset: float = 0.0
    bandRatio: float = splitCore.DEFAULT_BAND_RATIO
    bandHalfWidth: float | None = None
    leftSuffix: str = naming.DEFAULT_LEFT_SUFFIX
    rightSuffix: str = naming.DEFAULT_RIGHT_SUFFIX


@dataclass
class SplitResult:
    """분리 실행 결과.

    Attributes:
        leftNode: 생성된 좌 포즈 노드
        rightNode: 생성된 우 포즈 노드
        leftName: 좌 노드 이름
        rightName: 우 노드 이름
        axis: 사용한 대칭축
        planeOffset: 사용한 대칭면 오프셋
        axisWidth: 뉴트럴의 대칭축 방향 폭 W
        bandHalfWidth: **실제로 쓰인** 밴드 반폭 절대값
        bandRatio: **실제로 쓰인** 밴드 반폭 비율
        bandSource: 반폭을 어디서 얻었는지 ("ratio" 또는 "absolute")
        vertexCount: 처리한 버텍스 수
        restorationMaxDev: 순수 연산 단계의 복원 항등식 최대 편차
        maxDelta: 원본 포즈 델타의 최대 크기
        movedVertexCount: **유의미하게** 움직인 버텍스 수 (판정 기준은
            `_count_moved_vertices` 참조)
    """

    leftNode: object = None
    rightNode: object = None
    leftName: str = ""
    rightName: str = ""
    axis: str = splitCore.AXIS_X
    planeOffset: float = 0.0
    axisWidth: float = 0.0
    bandHalfWidth: float = 0.0
    bandRatio: float = 0.0
    bandSource: str = "ratio"
    vertexCount: int = 0
    restorationMaxDev: float = 0.0
    maxDelta: float = 0.0
    movedVertexCount: int = 0

    def as_report(self) -> list[str]:
        """로그·UI에 남길 요약 줄들을 만든다.

        어느 값이 실제로 쓰였는지 남기는 것이 목적이다. 비율만 남기면 다른
        캐릭터에서 재현할 때 무엇이 적용됐는지 알 수 없다.
        """
        return [
            f"좌 노드: {self.leftName}",
            f"우 노드: {self.rightName}",
            f"대칭축: {self.axis} (폭 W = {self.axisWidth:.6g})",
            f"대칭면 오프셋: {self.planeOffset:.6g}",
            (
                f"밴드 반폭: {self.bandHalfWidth:.6g} "
                f"(비율 {self.bandRatio * 100.0:.4g}%, 입력원 {self.bandSource})"
            ),
            (
                f"버텍스: {self.vertexCount}개 "
                f"(유의미하게 움직인 버텍스 {self.movedVertexCount}개, "
                f"최대 델타 {self.maxDelta:.6g})"
            ),
            f"복원 항등식 최대 편차: {self.restorationMaxDev:.6g}",
        ]


def _count_moved_vertices(inDeltas, inRelativeFloor: float = 0.01) -> tuple[float, int]:
    """포즈 델타에서 **유의미하게** 움직인 버텍스 수를 센다.

    `> 0` 으로 세면 안 된다. 실기 애셋은 재익스포트 과정에서 거의 모든 버텍스에
    부동소수 잡음 수준의 차이를 갖는다(실측: 2,116개 전부가 `> 0`인데 실제로 입이
    움직인 것은 216개). 그 숫자를 사용자에게 "델타 있는 버텍스"로 보여주면 아무
    정보도 주지 않는다.

    그래서 최대 델타의 일정 비율을 바닥으로 둔다. float32 왕복 잡음은 최대 델타의
    1%보다 몇 자리 아래이므로, 이 바닥이 "실제로 포즈된 버텍스"와 "익스포트 잡음"을
    가른다.

    Args:
        inDeltas: `(N, 3)` 포즈 델타 배열
        inRelativeFloor: 최대 델타에 대한 비율 바닥. 기본 0.01(1%).

    Returns:
        `(최대 델타 크기, 유의미하게 움직인 버텍스 수)`
    """
    distances = np.linalg.norm(np.asarray(inDeltas, dtype=np.float64), axis=1)
    maxDelta = float(distances.max()) if distances.size else 0.0
    if not maxDelta > 0.0:
        return 0.0, 0
    threshold = max(1e-9, maxDelta * float(inRelativeFloor))
    return maxDelta, int(np.count_nonzero(distances > threshold))


class SplitService:
    """대칭 포즈 분리 실행의 Facade.

    Example:
        service = SplitService(SceneOps())
        result = service.split(SplitRequest(neutralNode=n, poseNode=p))
    """

    def __init__(self, inSceneOps, inLogger=None) -> None:
        """서비스를 초기화한다.

        Args:
            inSceneOps: 씬 조작 어댑터(`meshIO.SceneOps` 또는 같은 인터페이스의 가짜)
            inLogger: 로거. None이면 로깅하지 않는다(순수 Type A 테스트용).
        """
        self._sceneOps = inSceneOps
        self._logger = inLogger

    @property
    def scene_ops(self):
        """주입된 씬 조작 어댑터."""
        return self._sceneOps

    def resolve_band(
        self, inNeutralCoords, inAxis: str, inRequest: SplitRequest
    ) -> tuple:
        """요청에서 실제로 쓸 밴드 반폭을 정한다.

        절대값이 주어지면 그것을 쓰고 비율을 역산한다. 없으면 비율로 해석한다.
        어느 쪽을 썼는지 함께 돌려주므로 로그가 "무엇이 적용됐는지" 남길 수 있다.

        Args:
            inNeutralCoords: `(N, 3)` 뉴트럴 오브젝트 좌표
            inAxis: 대칭축
            inRequest: 분리 요청

        Returns:
            `(반폭 절대값, 비율, 입력원 문자열)`
        """
        if inRequest.bandHalfWidth is not None:
            band = float(inRequest.bandHalfWidth)
            ratio = splitCore.resolve_band_ratio(inNeutralCoords, inAxis, band)
            return band, ratio, "absolute"

        ratio = float(inRequest.bandRatio)
        band = splitCore.resolve_band_half_width(inNeutralCoords, inAxis, ratio)
        return band, ratio, "ratio"

    def split(self, inRequest: SplitRequest) -> SplitResult:
        """합쳐진 포즈를 좌/우 두 노드로 분리한다.

        Args:
            inRequest: 분리 요청

        Returns:
            SplitResult

        Raises:
            SplitError: 검증 실패 또는 실행 실패
        """
        ops = self._sceneOps

        # 1) 선택 보관을 **가장 먼저** 한다. 이후의 어떤 조회도 선택을 건드릴 수 있다.
        savedSelection = ops.get_selection()

        try:
            axis = splitCore.normalize_axis(inRequest.axis)

            # 2) 씬에서 검증 재료를 모은다(판정은 순수 함수가 한다).
            neutralExists = ops.is_valid_geometry_node(inRequest.neutralNode)
            poseExists = ops.is_valid_geometry_node(inRequest.poseNode)
            facts = validation.SplitInputFacts(
                neutralExists=neutralExists,
                poseExists=poseExists,
                sameNode=ops.are_same_node(inRequest.neutralNode, inRequest.poseNode),
                neutralVertCount=ops.get_vertex_count(inRequest.neutralNode)
                if neutralExists
                else 0,
                poseVertCount=ops.get_vertex_count(inRequest.poseNode)
                if poseExists
                else 0,
                # 사용자가 무엇을 지정했는지 그대로 넘긴다. 절대값을 쓰면 비율은 None이고
                # 그 반대도 마찬가지다. 자리표시자를 끼우지 않는다.
                bandHalfWidth=inRequest.bandHalfWidth,
                bandRatio=(
                    inRequest.bandRatio if inRequest.bandHalfWidth is None else None
                ),
            )
            result = validation.validate_split_inputs(facts)
            if not result.ok:
                raise SplitError(
                    "입력 검증에 실패해 분리를 실행하지 않았다.\n"
                    + result.as_message(),
                    result.problems,
                )

            # 3) 이름을 먼저 확정하고 충돌을 감지한다. 씬에 쓰기 전에 멈출 수 있어야 한다.
            names = naming.build_split_names(
                ops.node_name(inRequest.poseNode),
                inRequest.leftSuffix,
                inRequest.rightSuffix,
            )
            collisions = naming.detect_name_collisions(
                names, ops.get_existing_node_names()
            )
            if collisions:
                message = naming.format_collision_message(collisions)
                raise SplitError(message, [message])

            # 4) 읽기 - 뉴트럴 1회, 포즈 1회.
            neutralCoords = ops.read_object_coords(inRequest.neutralNode)
            poseCoords = ops.read_object_coords(inRequest.poseNode)

            axisWidth = splitCore.measure_axis_extent(neutralCoords, axis)
            band, ratio, bandSource = self.resolve_band(neutralCoords, axis, inRequest)

            # 5) 순수 연산.
            left, right = splitCore.split_pose_deltas(
                neutralCoords, poseCoords, axis, inRequest.planeOffset, band
            )

            deltas = poseCoords - neutralCoords
            restored = (left - neutralCoords) + (right - neutralCoords)
            restorationMaxDev = float(np.abs(restored - deltas).max())
            maxDelta, movedCount = _count_moved_vertices(deltas)

            # 6) 쓰기 - 좌 1회, 우 1회.
            leftNode = ops.create_split_node(inRequest.neutralNode, names.left, left)
            rightNode = ops.create_split_node(inRequest.neutralNode, names.right, right)

            splitResult = SplitResult(
                leftNode=leftNode,
                rightNode=rightNode,
                leftName=names.left,
                rightName=names.right,
                axis=axis,
                planeOffset=float(inRequest.planeOffset),
                axisWidth=axisWidth,
                bandHalfWidth=band,
                bandRatio=ratio,
                bandSource=bandSource,
                vertexCount=int(neutralCoords.shape[0]),
                restorationMaxDev=restorationMaxDev,
                maxDelta=maxDelta,
                movedVertexCount=movedCount,
            )
            self._log_result(splitResult)
            return splitResult
        except SplitError:
            raise
        except (ValueError, RuntimeError) as e:
            # 순수 모듈의 검증 실패(ValueError)와 pymxs가 던지는 실패(RuntimeError)를
            # 같은 예외 계약으로 감싼다. RuntimeError를 흘려보내면 UI가 SplitError만
            # 잡으므로 Qt 이벤트 루프로 새어 나가 사용자에게 아무것도 표시되지 않는다.
            raise SplitError(str(e), [str(e)]) from e
        finally:
            # 7) 성공이든 실패든 선택을 되돌린다.
            ops.restore_selection(savedSelection)

    def _log_result(self, inResult: SplitResult) -> None:
        """결과 요약을 로그에 남긴다. 로거가 없으면 아무것도 하지 않는다."""
        if self._logger is None:
            return
        for line in inResult.as_report():
            self._logger.info(f"[MorphSplitter] {line}")
