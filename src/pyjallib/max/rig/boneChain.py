#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""뼈대 체인(Bone Chain) - 릭 파트가 만든 본·헬퍼와 재생성에 필요한 정보를 담는 값 객체.

릭 파트 클래스(`Elbow`·`TwistBone` 등)의 `create_bones()`가 이것을 돌려주고,
`create_bones_from_chain()`이 이것만으로 같은 셋업을 다시 만든다.

**`parameters`는 이름 붙은 dict다.** 전에는 순서가 곧 계약인 리스트였고, 그래서
`parameters[3]`이 무엇인지가 파트마다 달랐다. elbow·wrist·ankle은 부모(`VolumeBone`)가
저장한 레이아웃과 자기가 읽는 레이아웃이 어긋나 있어서, 라이브러리를 직접 쓰는 재생성이
`Unable to convert: "NegY" to type: Float`로 죽었다(2026-09-21 실측). 저장과 읽기가 같은
**이름**을 보면 어긋날 수 없다.
"""

from typing import Optional

from pymxs import runtime as rt

from pyjallib.logger import Logger

# 모듈 단일 지연 Logger. Logger는 생성 시 같은 로그 파일에 핸들러를 새로 부착하므로
# 인스턴스마다 만들면 긴 DCC 세션에서 파일 핸들이 누수된다(`rules/code-style.md`).
_logger: Optional[Logger] = None


def _get_logger() -> Logger:
    """모듈 단일 Logger를 지연 생성해 반환한다.

    Returns:
        Logger: 모듈 전역 Logger 인스턴스
    """
    global _logger
    if _logger is None:
        _logger = Logger(inLogFileName="pyjallib_rig", inEnableConsole=False)
    return _logger


class BoneChain:
    """릭 파트가 만든 본·헬퍼와 재생성 정보를 담고, 비우기·삭제를 제공하는 값 객체."""

    def __init__(self, inResult: Optional[dict] = None):
        """결과 딕셔너리로부터 체인 속성을 초기화한다.

        Args:
            inResult: 생성 결과 딕셔너리(`Bones`·`Helpers`·`SourceBones`·`Parameters` 키).
                None이면 빈 상태로 초기화한다. `Parameters`는 이름 붙은 dict다.
        """
        if inResult is None:
            self.bones = []
            self.helpers = []
            self.result = {}
            self.sourceBones = []
            self.parameters = {}
        else:
            self.update_from_result(inResult)

    def is_empty(self) -> bool:
        """체인이 비어있는지 확인한다.

        Returns:
            bool: 뼈대가 하나도 없으면 True
        """
        return len(self.bones) == 0

    def clear(self) -> None:
        """체인의 모든 참조를 제거한다. 씬의 노드는 건드리지 않는다."""
        self.bones = []
        self.helpers = []
        self.sourceBones = []
        self.parameters = {}

    def delete(self) -> bool:
        """체인의 모든 뼈대와 헬퍼를 3ds Max 씬에서 삭제한다.

        `sourceBones`와 `parameters`는 유지하므로 삭제 뒤에도 재생성할 수 있다.

        Returns:
            bool: 삭제 성공 시 True. 체인이 비어있거나 삭제에 실패하면 False
        """
        if self.is_empty() and not self.helpers:
            return False

        validNodes = [item for item in self.bones + self.helpers if rt.isValidNode(item)]

        try:
            if validNodes:
                rt.delete(validNodes)
        except RuntimeError as error:
            # pymxs는 씬 조작 실패를 RuntimeError로 올린다. 삼키면 "삭제했다고 믿는
            # 빈 체인"이 남아 재생성이 조용히 어긋난다 - 사유를 남기고 실패로 돌린다.
            _get_logger().error(f"BoneChain.delete 실패: {error}")
            return False

        self.bones = []
        self.helpers = []
        rt.redrawViews()
        return True

    def delete_all(self) -> bool:
        """체인의 뼈대·헬퍼를 씬에서 삭제하고 소스본과 파라미터도 초기화한다.

        Returns:
            bool: 삭제 성공 시 True. 체인이 비어있거나 삭제에 실패하면 False
        """
        if not self.delete():
            return False

        self.sourceBones = []
        self.parameters = {}
        return True

    def get_bones(self) -> list:
        """체인의 모든 뼈대를 가져온다.

        Returns:
            list: 뼈대 배열. 체인이 비어있으면 빈 리스트
        """
        return list(self.bones)

    def get_helpers(self) -> list:
        """체인의 모든 헬퍼를 가져온다.

        Returns:
            list: 헬퍼 배열. 헬퍼가 없으면 빈 리스트
        """
        return list(self.helpers)

    @classmethod
    def from_result(cls, inResult: dict) -> "BoneChain":
        """결과 딕셔너리로부터 체인 인스턴스를 생성한다.

        Args:
            inResult: 생성 결과 딕셔너리

        Returns:
            BoneChain: 생성된 체인 인스턴스
        """
        return cls(inResult)

    def update_from_result(self, inResult: Optional[dict]) -> "BoneChain":
        """기존 체인 인스턴스를 결과 딕셔너리로 갱신한다.

        Args:
            inResult: 생성 결과 딕셔너리. None이면 아무것도 갱신하지 않는다.

        Returns:
            BoneChain: 메서드 체이닝을 위한 자기 자신
        """
        if inResult is None:
            return self

        parameters = inResult.get("Parameters", {})
        if not isinstance(parameters, dict):
            # 구 레이아웃(순서가 계약인 리스트)을 받아 주는 호환 경로를 두지 않는다.
            # 두 형태를 다 받으면 "어느 쪽으로 저장됐는지"가 다시 호출부의 부담이 되고,
            # 이 사이클이 없애려는 결함이 그대로 남는다(`module_replacement.md`
            # §모드를 만들지 말 것). 대신 무엇이 잘못됐는지 바로 알 수 있게 실패한다.
            raise TypeError(
                "BoneChain.parameters는 이름 붙은 dict여야 한다. "
                f"받은 타입: {type(parameters).__name__}"
            )

        self.bones = list(inResult.get("Bones", []))
        self.helpers = list(inResult.get("Helpers", []))
        self.result = inResult
        self.sourceBones = list(inResult.get("SourceBones", []))
        self.parameters = dict(parameters)

        return self
