#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""입력 검증 (pymxs 무의존 순수 모듈).

씬에서 모은 **확정된 값**만 받는다(노드 래퍼를 받지 않는다). 그래서 검증 규칙의
경우의 수를 콘솔 pytest에서 전수로 덮을 수 있다.

검증은 문제 목록을 **모아서** 돌려준다. 첫 문제에서 예외를 던지면 사용자가 한 번에
두 가지를 고칠 수 없고, UI가 "무엇이 잘못됐는지" 한 화면에 못 보여준다.

`None` / `True` / `False` 비교는 반드시 `is` / `is not`을 쓴다. `0 == False`가 참이라
값 비교로 하면 "버텍스 0개"와 "노드 없음"이 뒤섞인다.
"""

from dataclasses import dataclass, field


@dataclass
class SplitInputFacts:
    """검증에 필요한, **버텍스를 읽기 전에** 확정할 수 있는 사실들.

    대칭축 방향 폭이 0인 퇴화 메쉬처럼 좌표를 읽어야 아는 문제는 여기서 보지 않는다.
    그것은 `splitCore`의 해석 함수가 `ValueError`로 낸다. 읽기 전 단계에 자리표시자
    값을 끼워 넣고 "검증했다"고 하면, 실제로는 아무것도 보지 않은 통과가 된다.

    Attributes:
        neutralExists: 뉴트럴 노드가 유효한 지오메트리 노드인가
        poseExists: 포즈 노드가 유효한 지오메트리 노드인가
        sameNode: 두 입력이 같은 노드인가 (노드 핸들로 판정된 결과)
        neutralVertCount: 뉴트럴 버텍스 수
        poseVertCount: 포즈 버텍스 수
        bandHalfWidth: 사용자가 **절대값**으로 지정한 밴드 반폭. 비율을 쓸 때는 None.
        bandRatio: 사용자가 **비율**로 지정한 밴드 반폭 비율. 절대값을 쓸 때는 None.
    """

    neutralExists: bool = False
    poseExists: bool = False
    sameNode: bool = False
    neutralVertCount: int = 0
    poseVertCount: int = 0
    bandHalfWidth: float | None = None
    bandRatio: float | None = None


@dataclass
class ValidationResult:
    """검증 결과.

    Attributes:
        problems: 사람이 읽는 문제 설명 목록. 비어 있으면 통과.
    """

    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """문제가 하나도 없으면 True."""
        return len(self.problems) == 0

    def as_message(self) -> str:
        """문제 목록을 한 줄씩 묶은 메시지로 만든다."""
        return "\n".join(f"- {p}" for p in self.problems)


def validate_split_inputs(inFacts: SplitInputFacts) -> ValidationResult:
    """분리 실행 전 입력을 검증한다.

    Args:
        inFacts: 씬에서 확정한 사실들

    Returns:
        문제 목록을 담은 ValidationResult
    """
    problems: list[str] = []

    if inFacts.neutralExists is not True:
        problems.append(
            "뉴트럴 메쉬가 지정되지 않았거나 유효한 지오메트리 노드가 아니다."
        )
    if inFacts.poseExists is not True:
        problems.append(
            "포즈 메쉬가 지정되지 않았거나 유효한 지오메트리 노드가 아니다."
        )

    if inFacts.sameNode is True:
        problems.append(
            "뉴트럴과 포즈가 같은 노드다. 서로 다른 두 메쉬를 지정해야 한다."
        )

    # 버텍스 수는 "0개"와 "노드 없음"이 다른 문제다. 각각 따로 본다.
    # 빈 메쉬의 getNumVerts는 예외 없이 0을 돌려주므로(Phase 0 섹션 G) 이 가드가 필수다.
    if inFacts.neutralExists is True and inFacts.neutralVertCount <= 0:
        problems.append("뉴트럴 메쉬에 버텍스가 없다.")
    if inFacts.poseExists is True and inFacts.poseVertCount <= 0:
        problems.append("포즈 메쉬에 버텍스가 없다.")

    if (
        inFacts.neutralVertCount > 0
        and inFacts.poseVertCount > 0
        and inFacts.neutralVertCount != inFacts.poseVertCount
    ):
        problems.append(
            "뉴트럴과 포즈의 버텍스 수가 다르다 "
            f"({inFacts.neutralVertCount} vs {inFacts.poseVertCount}). "
            "모프 타겟 전제가 깨진 것이므로 부분 처리하지 않는다."
        )

    problems.extend(_validate_band(inFacts))
    return ValidationResult(problems=problems)


def _validate_band(inFacts: SplitInputFacts) -> list[str]:
    """밴드 반폭 입력을 검증한다.

    절대값이 지정되면 그것을, 아니면 비율을 본다. 둘 다 없으면 그것 자체가 문제다 -
    0을 기본값으로 삼으면 "유효한 설정"으로 오인된다.

    Args:
        inFacts: 검증 대상 사실

    Returns:
        문제 설명 목록
    """
    if inFacts.bandHalfWidth is not None:
        if not float(inFacts.bandHalfWidth) > 0.0:
            return [f"밴드 반폭이 0보다 커야 한다 (현재 {inFacts.bandHalfWidth})."]
        return []

    if inFacts.bandRatio is not None:
        if not float(inFacts.bandRatio) > 0.0:
            return [f"밴드 반폭 비율이 0보다 커야 한다 (현재 {inFacts.bandRatio})."]
        return []

    return ["밴드 반폭이 비율도 절대값도 지정되지 않았다."]
