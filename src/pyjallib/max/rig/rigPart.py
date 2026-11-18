#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""릭 파트 공통 골격 - `_RigPartBase`.

릭 파트 14종이 같은 보일러플레이트를 14번 반복하고 있었다(2026-09-21 실측).

| 반복 항목 | 실측 |
|:--|:--|
| `__init__`의 서비스 폴백 `nameService if nameService else Name()` | 10개 모듈 x 5~6줄 |
| `reset()` | 14개 전부 |
| `create_bones_from_chain()`의 positional 언패킹 | 10개 모듈, 합계 40+줄 |
| 이름 생성 뒤 `islower()` 소문자 전파 | 14개 전부 |

이 모듈이 그 넷을 한 벌로 만든다. 파트 클래스는 **표 두 개**(`PARAM_SPEC`,
`WORK_DEFAULTS`)와 자기 `create_bones()` 본문만 갖는다.

## 서비스는 필수 주입이다 - 폴백을 두지 않는다

전 구현은 `nameService if nameService else Name()` 꼴로 폴백을 만들었다. 그러나 릭 파트를
만드는 지점은 `Header` 하나뿐이고, `Header`는 **항상** 서비스를 주입한다. 즉 폴백 경로는
프로덕션에서 한 번도 실행되지 않는 죽은 코드였고, 14벌 있었다. 더 나쁜 것은 폴백이
**따로 만든 `Name()`**을 쥐게 되어 설정 파일을 공유하지 않는다는 점이다 - 만약 실행됐다면
이름 규칙이 조용히 갈렸을 것이다.

## `PARAM_SPEC`이 파라미터의 단일 정본이다

`(("inRotScale", 0.5), ("inVolumeSize", 4.0), ...)` 꼴로 **`create_bones()`의 키워드
파라미터와 1:1·같은 순서**로 선언한다. 이것이

- `create_bones_from_chain()`이 dict에서 키워드 인자를 만드는 근거이고,
- `build_result()`가 결과 dict의 `Parameters`를 채우는 근거이며,
- 툴 `partSpecs.py`의 파라미터 표와 대조하는 기준이고,
- Type A 테스트(`tests/test_rig_param_spec.py`)가 시그니처와 대조하는 기준이다.

정본이 하나이므로 "저장 레이아웃과 읽기 레이아웃이 어긋나는" 결함이 구조적으로 생길 수 없다.

## 실패는 `None`이다

전 구현은 입력 노드가 무효면 `False`, 생성에 실패하면 `None`을 돌려줘 호출부가 둘 다
검사해야 했다. 이제 **실패는 전부 `None`**이고 사유는 Logger에 남는다.
"""

from typing import Any, Optional

from pymxs import runtime as rt

from .boneChain import BoneChain, _get_logger


class _RigPartBase:
    """릭 파트의 공통 골격. 서비스 주입·`reset()`·파라미터 표 구동 재생성을 제공한다.

    하위 클래스가 선언할 것:
        `PARAM_SPEC`: `create_bones()`의 키워드 파라미터와 1:1인 `(이름, 기본값)` 표
        `SOURCE_SPEC`: `create_bones()`의 소스 본 파라미터 이름을 순서대로
        `WORK_DEFAULTS`: `reset()`이 되돌릴 작업 데이터의 기본값
    """

    #: `create_bones()`의 키워드 파라미터와 1:1·동순. `((name, default), ...)`
    PARAM_SPEC: tuple = ()

    #: `create_bones()`의 소스 본 파라미터 이름. `BoneChain.sourceBones`의 순서이기도 하다.
    SOURCE_SPEC: tuple = ()

    #: `reset()`이 되돌릴 작업 데이터. 리스트·dict 기본값은 매번 새로 복제된다.
    WORK_DEFAULTS: dict = {}

    def __init__(
        self,
        inNameService,
        inAnimService,
        inHelperService,
        inBoneService,
        inConstService,
    ):
        """릭 파트를 초기화한다. 서비스는 전부 필수다.

        Args:
            inNameService: 이름 처리 서비스 (`Name`)
            inAnimService: 애니메이션 서비스 (`Anim`)
            inHelperService: 헬퍼 객체 서비스 (`Helper`)
            inBoneService: 뼈대 서비스 (`Bone`)
            inConstService: 제약 서비스 (`Constraint`)

        Raises:
            ValueError: 서비스 중 하나라도 None이면
        """
        services = {
            "inNameService": inNameService,
            "inAnimService": inAnimService,
            "inHelperService": inHelperService,
            "inBoneService": inBoneService,
            "inConstService": inConstService,
        }
        missing = [key for key, value in services.items() if value is None]
        if missing:
            raise ValueError(
                f"{type(self).__name__}: 서비스는 필수 주입이다. 누락: {', '.join(missing)}"
            )

        self.name = inNameService
        self.anim = inAnimService
        self.helper = inHelperService
        self.bone = inBoneService
        self.const = inConstService

        self.reset()

    # ------------------------------------------------------------------
    # 작업 데이터
    # ------------------------------------------------------------------

    def reset(self) -> "_RigPartBase":
        """작업 데이터를 `WORK_DEFAULTS`로 되돌린다. 서비스는 건드리지 않는다.

        Returns:
            _RigPartBase: 메서드 체이닝을 위한 자기 자신
        """
        for attrName, default in self.WORK_DEFAULTS.items():
            if isinstance(default, list):
                setattr(self, attrName, list(default))
            elif isinstance(default, dict):
                setattr(self, attrName, dict(default))
            else:
                setattr(self, attrName, default)
        return self

    # ------------------------------------------------------------------
    # 파라미터 표
    # ------------------------------------------------------------------

    @classmethod
    def param_names(cls) -> tuple:
        """`PARAM_SPEC`의 파라미터 이름만 순서대로 돌려준다.

        Returns:
            tuple: 파라미터 이름 튜플
        """
        return tuple(name for name, _ in cls.PARAM_SPEC)

    @classmethod
    def default_parameters(cls) -> dict:
        """`PARAM_SPEC`의 기본값을 dict로 돌려준다.

        리스트·dict 기본값은 **복제해서** 돌려준다. 표를 그대로 넘기면 호출부가 그것을
        수정했을 때 클래스 전역 기본값이 오염된다.

        Returns:
            dict: 파라미터 이름 -> 기본값
        """
        defaults = {}
        for name, default in cls.PARAM_SPEC:
            if isinstance(default, list):
                defaults[name] = list(default)
            elif isinstance(default, dict):
                defaults[name] = dict(default)
            else:
                defaults[name] = default
        return defaults

    @classmethod
    def resolve_parameters(cls, inParameters: Optional[dict]) -> dict:
        """주어진 파라미터 dict를 `PARAM_SPEC` 기준으로 채워 돌려준다.

        표에 없는 키는 버린다 - 그것을 `create_bones(**params)`에 넘기면
        `TypeError`가 되고, 사유가 호출 스택 깊은 곳에서 나타난다.

        Args:
            inParameters: 파라미터 dict. None이면 기본값만 돌려준다.

        Returns:
            dict: `PARAM_SPEC`의 모든 이름이 채워진 dict
        """
        resolved = cls.default_parameters()
        if not inParameters:
            return resolved

        unknown = [key for key in inParameters if key not in resolved]
        if unknown:
            _get_logger().warning(
                f"{cls.__name__}: PARAM_SPEC에 없는 파라미터를 무시한다: {unknown}"
            )
        resolved.update({key: value for key, value in inParameters.items() if key in resolved})
        return resolved

    def build_result(self, inBones: list, inHelpers: list, inSourceBones: list, inParameters: dict) -> dict:
        """`BoneChain`이 받는 결과 딕셔너리를 만든다.

        Args:
            inBones: 생성된 뼈대
            inHelpers: 생성된 헬퍼
            inSourceBones: 소스 본 (`SOURCE_SPEC` 순서)
            inParameters: 사용한 파라미터

        Returns:
            dict: `Bones`·`Helpers`·`SourceBones`·`Parameters` 키를 가진 딕셔너리
        """
        return {
            "Bones": list(inBones),
            "Helpers": list(inHelpers),
            "SourceBones": list(inSourceBones),
            "Parameters": self.resolve_parameters(inParameters),
        }

    # ------------------------------------------------------------------
    # 재생성
    # ------------------------------------------------------------------

    def create_bones_from_chain(self, inBoneChain: Optional[BoneChain]) -> Optional[BoneChain]:
        """기존 `BoneChain`에서 같은 셋업을 다시 만든다.

        기존 본·헬퍼를 지운 뒤 `sourceBones`와 `parameters`로 `create_bones()`를
        다시 부른다. 파라미터는 **이름으로** 전달되므로 순서가 어긋날 수 없다.

        Args:
            inBoneChain: 재생성할 체인

        Returns:
            BoneChain | None: 재생성된 체인. 체인이 비었거나 소스 본이 유효하지 않으면 None
        """
        if not inBoneChain or inBoneChain.is_empty():
            _get_logger().warning(f"{type(self).__name__}: 비어 있는 체인은 재생성하지 않는다")
            return None

        sourceBones = list(inBoneChain.sourceBones)
        parameters = dict(inBoneChain.parameters)

        sourceCount = len(self.SOURCE_SPEC)
        if len(sourceBones) < sourceCount:
            _get_logger().warning(
                f"{type(self).__name__}: 소스 본이 부족하다 "
                f"(필요 {sourceCount}, 실제 {len(sourceBones)})"
            )
            return None
        if not all(rt.isValidNode(item) for item in sourceBones[:sourceCount]):
            _get_logger().warning(f"{type(self).__name__}: 소스 본 중 유효하지 않은 노드가 있다")
            return None

        inBoneChain.delete()

        return self.create_bones(
            *sourceBones[:sourceCount], **self.resolve_parameters(parameters)
        )

    def create_bones(self, *args, **kwargs) -> Optional[BoneChain]:
        """릭 파트의 본을 생성한다. 하위 클래스가 구현한다.

        Args:
            *args: `SOURCE_SPEC` 순서의 소스 본
            **kwargs: `PARAM_SPEC`의 파라미터

        Returns:
            BoneChain | None: 생성된 체인. 실패하면 None

        Raises:
            NotImplementedError: 하위 클래스가 구현하지 않았으면
        """
        raise NotImplementedError(f"{type(self).__name__}.create_bones()가 구현되지 않았다")

    # ------------------------------------------------------------------
    # 이름 생성 헬퍼
    # ------------------------------------------------------------------

    def validate_source_nodes(self, *args) -> bool:
        """소스 노드가 전부 유효한지 확인하고, 아니면 사유를 남긴다.

        Args:
            *args: 검사할 노드들

        Returns:
            bool: 전부 유효하면 True
        """
        for index, node in enumerate(args):
            if not rt.isValidNode(node):
                sourceName = (
                    self.SOURCE_SPEC[index] if index < len(self.SOURCE_SPEC) else f"#{index}"
                )
                _get_logger().warning(
                    f"{type(self).__name__}: 소스 노드 {sourceName}이(가) 유효하지 않다"
                )
                return False
        return True

    def filtering_char(self, inName: str) -> str:
        """이름에 쓰인 구분 문자를 돌려준다.

        전 구현은 같은 목적에 공개 `get_filtering_char`와 비공개 `_get_filtering_char`를
        섞어 썼다(elbow·ankle은 공개, wrist·inguinal은 비공개). 동작은 같고 호출 위생만
        달랐으므로 공개 쪽으로 통일한다.

        Args:
            inName: 기준이 되는 노드 이름

        Returns:
            str: 구분 문자
        """
        return self.name.get_filtering_char(inName)

    def is_lower_case_name(self, inName: str) -> bool:
        """이름의 `RealName` 부분이 소문자로 시작하는지 확인한다.

        Args:
            inName: 검사할 노드 이름

        Returns:
            bool: 소문자로 시작하면 True
        """
        realName = self.name.get_name("RealName", inName)
        return bool(realName) and realName[0].islower()

    def propagate_lower_case(self, inReferenceName: str, inNames: dict) -> dict:
        """기준 이름이 소문자면 생성한 이름들을 전부 소문자로 내린다.

        14개 파트가 똑같이 반복하던 단계다.

        Args:
            inReferenceName: 소문자 여부의 기준이 되는 노드 이름
            inNames: 생성한 이름들 (키 -> 이름)

        Returns:
            dict: 소문자 전파를 적용한 이름 dict. 기준이 대문자면 원본 그대로
        """
        if not self.is_lower_case_name(inReferenceName):
            return dict(inNames)
        return {key: value.lower() for key, value in inNames.items()}

    def dummy_name(self, inName: str) -> str:
        """이름의 `Type` 부분을 Dummy 값으로 바꾼 이름을 돌려준다.

        Args:
            inName: 원본 이름

        Returns:
            str: Type이 Dummy로 바뀐 이름
        """
        return self.name.replace_name_part(
            "Type", inName, self.name.get_name_part_value_by_description("Type", "Dummy")
        )

    def tag_as_skin_bones(self, inNodes: list, inSourceNodes: list) -> None:
        """소스 중 하나라도 스킨 본이면 생성한 노드들을 스킨 본으로 표시한다.

        14개 파트가 똑같이 반복하던 단계다.

        Args:
            inNodes: 표시할 노드들(본·헬퍼)
            inSourceNodes: 판정 기준이 되는 소스 노드들
        """
        if not any(self.bone.is_skin_bone(item) for item in inSourceNodes):
            return
        for item in inNodes:
            self.bone.set_skin_bone_property(item, True)
            self.bone.set_skin_bone_parent(item)

    def find_node(self, inName: str) -> Any:
        """이름으로 노드를 찾는다. 없으면 None.

        Args:
            inName: 찾을 노드 이름

        Returns:
            노드 또는 None
        """
        node = rt.getNodeByName(inName)
        return node if rt.isValidNode(node) else None
