#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
어트리뷰트(Attribute) 모듈 - 3ds Max 커스텀 어트리뷰트 범용 관리 서비스

노드에 커스텀 어트리뷰트를 추가, 조회, 수정, 삭제하고
프로퍼티 읽기/쓰기 및 컨트롤러 할당 기능을 제공합니다.

커스텀 어트리뷰트는 노드의 baseObject뿐 아니라 Attribute Holder
모디파이어에도 부착할 수 있습니다. 모디파이어에 부착하면 모디파이어를
제거할 때 어트리뷰트가 함께 사라지므로 수명 관리가 Max 기반으로 단순해집니다.
"""

from typing import Any, Optional

from pymxs import runtime as rt


class Attribute:
    """노드의 커스텀 어트리뷰트 정의를 추가·조회·수정·삭제하고 프로퍼티 읽기/쓰기와 컨트롤러 할당을 제공한다.

    **대상(target)의 두 가지 형태.** 대부분의 메서드는 첫 인자로 노드뿐 아니라
    **모디파이어 객체**를 받을 수 있다(2026-08-04 프로브 실측). 다만 조회 범위가
    갈린다.

    - 노드를 넘기면 조회 범위는 **baseObject뿐**이다. 모디파이어에 붙은
      어트리뷰트는 ``custAttributes.count``가 0을 반환하며 보이지 않는다.
    - 모디파이어를 넘기면 그 모디파이어에 붙은 어트리뷰트만 다룬다.

    따라서 "이 노드가 어트리뷰트를 갖고 있는가"를 판정할 때 노드만 넘겨서는
    안 된다. ``find_attribute_holder``로 홀더를 얻어 그것도 함께 조회해야 한다.

    모디파이어 대상에서 정상 동작하는 메서드: ``find_attribute_def``,
    ``has_attribute_def``, ``get_all_attribute_defs``, ``remove_attribute_def``,
    ``redefine_attribute_def``, ``get_property``, ``set_property``,
    ``get_all_properties``, ``set_all_properties``, ``assign_float_controllers``,
    ``add_attribute_def_from_source``.

    예외는 ``add_attribute_def``다 - 롤아웃을 포함한 정의를 만들 수 없고 중복 검사
    범위도 좁다(그 docstring 참조). 모디파이어 대상 부착은
    ``add_attribute_def_from_source``를 쓴다.
    """

    # 지원 타입 매핑 (Python 타입명 -> MaxScript 타입 문자열)
    SUPPORTED_TYPES = {
        "float": "#float",
        "integer": "#integer",
        "boolean": "#boolean",
        "string": "#string",
    }

    # Attribute Holder 모디파이어의 표시 이름. 2026-08-04 프로브 실측:
    # rt.EmptyModifier()로 생성되며 classOf는 EmptyModifier, 기본 name은
    # "Attribute Holder"다. MaxScript 이름 조회는 공백을 밑줄로 바꾼
    # #Attribute_Holder를 쓴다.
    ATTRIBUTE_HOLDER_NAME = "Attribute Holder"

    def __init__(self):
        """Attribute 클래스를 초기화한다."""
        pass

    def _convert_default_value(self, inType: str, inDefault: Any) -> str:
        """Python 기본값을 MaxScript 형식 문자열로 변환.

        Args:
            inType: 파라미터 타입 문자열 ("float", "integer", "boolean", "string")
            inDefault: Python 기본값

        Returns:
            MaxScript 형식의 기본값 문자열
        """
        if inType == "float":
            return str(float(inDefault))
        elif inType == "integer":
            return str(int(inDefault))
        elif inType == "boolean":
            return "true" if inDefault else "false"
        elif inType == "string":
            return f'"{inDefault}"'
        return str(inDefault)

    def _get_ca_block(self, inNode, inDefName: str) -> Optional[Any]:
        """노드에서 커스텀 어트리뷰트 블록(caBlock)을 조회.

        find_attribute_def로 정의를 찾은 뒤 rt.custAttributes.get으로
        실제 데이터 블록을 반환합니다.

        Args:
            inNode: 대상 노드
            inDefName: 어트리뷰트 정의 이름

        Returns:
            커스텀 어트리뷰트 블록 객체. 없으면 None.
        """
        attrDef = self.find_attribute_def(inNode, inDefName)
        if attrDef is None:
            return None

        try:
            caBlock = rt.custAttributes.get(inNode, attrDef)
        except Exception:
            return None

        return caBlock

    def build_param_def_string(self, inDefName: str, inParams: list[dict]) -> str:
        """MaxScript 커스텀 어트리뷰트 정의 문자열을 생성한다.

        입력된 파라미터 목록으로부터 MaxScript `attributes ... ( parameters main ( ... ) )`
        형식의 정의 문자열을 생성한다. 이름이 없거나 지원하지 않는 타입의
        파라미터는 건너뛴다.

        Args:
            inDefName (str): 어트리뷰트 정의 이름
            inParams (list[dict]): {name: str, type: str, default: Any} 형태의 파라미터 정의 리스트

        Returns:
            str: MaxScript 어트리뷰트 정의 문자열
        """
        lines = [
            f"attributes {inDefName}",
            "(",
            "    parameters main",
            "    (",
        ]

        for param in inParams:
            paramName = param.get("name", "")
            paramType = param.get("type", "")
            paramDefault = param.get("default")

            if not paramName:
                continue

            if paramType not in self.SUPPORTED_TYPES:
                print(
                    f"[Attribute] 지원하지 않는 타입: {paramType} (파라미터: {paramName})"
                )
                continue

            maxType = self.SUPPORTED_TYPES[paramType]
            maxDefault = self._convert_default_value(paramType, paramDefault)
            lines.append(f"        {paramName} type:{maxType} default:{maxDefault}")

        lines.append("    )")
        lines.append(")")

        return "\n".join(lines)

    def find_attribute_def(self, inNode, inDefName: str) -> Optional[Any]:
        """노드에서 지정된 이름의 커스텀 어트리뷰트 정의를 찾아 반환한다.

        ``inNode`` 자리에 **모디파이어 객체**를 넘겨도 동작한다. 노드를 넘기면
        baseObject만, 모디파이어를 넘기면 그 모디파이어만 조회한다(클래스 docstring 참조).

        Args:
            inNode (rt.Node | rt.Modifier): 검색 대상 노드 또는 모디파이어
            inDefName (str): 어트리뷰트 정의 이름

        Returns:
            Any | None: 커스텀 어트리뷰트 정의 객체. 없거나 노드가 유효하지 않으면 None
        """
        if inNode is None:
            return None

        try:
            numDefs = rt.custAttributes.count(inNode)
        except Exception:
            return None

        for i in range(1, numDefs + 1):
            attrDef = rt.custAttributes.getdef(inNode, i)
            if attrDef is not None and str(attrDef.name) == inDefName:
                return attrDef

        return None

    def has_attribute_def(self, inNode, inDefName: str) -> bool:
        """대상에 지정된 이름의 커스텀 어트리뷰트가 존재하는지 확인한다.

        ``inNode`` 자리에 노드와 **모디파이어 객체**를 모두 넘길 수 있다. 조회 범위는
        클래스 docstring의 규칙을 따른다 - 노드는 baseObject, 모디파이어는 그 모디파이어.

        생존 판정은 ``rt.isvalidnode``가 아니라 ``rt.isDeleted``로 한다.
        ``isvalidnode``는 **살아 있는 모디파이어에도 False를 반환**하므로(2026-08-04
        프로브 실측) 모디파이어를 넘기면 어트리뷰트가 실제로 있어도 False가 나왔다.
        노드 대상의 결과는 종전과 동일하다 - 살아 있는 노드는 ``isDeleted``가 False,
        삭제된 노드는 True다. 노드도 모디파이어도 아닌 값은 ``isDeleted``를 통과하지만
        ``find_attribute_def``의 조회 가드에서 걸러진다.

        Args:
            inNode (rt.Node | rt.Modifier): 검색 대상 노드 또는 모디파이어
            inDefName (str): 어트리뷰트 정의 이름

        Returns:
            bool: 존재하면 True. 없거나 대상이 삭제되었으면 False
        """
        if inNode is None:
            return False

        try:
            if rt.isDeleted(inNode):
                return False
        except Exception:
            return False

        return self.find_attribute_def(inNode, inDefName) is not None

    def get_all_attribute_defs(self, inNode) -> list:
        """노드에 등록된 모든 커스텀 어트리뷰트 정의를 리스트로 반환한다.

        Args:
            inNode (rt.Node): 대상 노드

        Returns:
            list[Any]: 커스텀 어트리뷰트 정의 객체 리스트. 빈 리스트 가능
        """
        result = []

        if inNode is None:
            return result

        try:
            numDefs = rt.custAttributes.count(inNode)
        except Exception:
            return result

        for i in range(1, numDefs + 1):
            attrDef = rt.custAttributes.getdef(inNode, i)
            if attrDef is not None:
                result.append(attrDef)

        return result

    def add_attribute_def(self, inNode, inDefName: str, inParams: list[dict]) -> bool:
        """노드에 커스텀 어트리뷰트 정의를 추가한다.

        이미 동일 이름의 어트리뷰트가 존재하면 중복 방지를 위해 False를 반환한다.
        build_param_def_string으로 MaxScript 정의 문자열을 생성한 뒤
        rt.execute로 정의 객체를 만들고 rt.custAttributes.add로 노드에 추가한다.

        Note:
            이 메서드는 ``parameters main`` 블록만 만들 수 있어 **롤아웃을 포함한
            정의는 부착할 수 없다.** 롤아웃·이벤트 핸들러·정의 레벨 함수가 필요하면
            ``add_attribute_def_from_source``를 쓴다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름
            inParams (list[dict]): {name: str, type: str, default: Any} 형태의 파라미터 정의 리스트

        Returns:
            bool: 추가 성공 여부. 동일 이름이 이미 존재하면 False
        """
        if inNode is None:
            return False

        if self.has_attribute_def(inNode, inDefName):
            print(f"[Attribute] 이미 존재하는 어트리뷰트: {inDefName}")
            return False

        try:
            defString = self.build_param_def_string(inDefName, inParams)
            attrDef = rt.execute(defString)
            if attrDef is None:
                return False
            rt.custAttributes.add(inNode, attrDef)
        except Exception:
            return False

        return True

    def remove_attribute_def(self, inNode, inDefName: str) -> bool:
        """노드에서 지정된 이름의 커스텀 어트리뷰트 정의를 제거한다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름

        Returns:
            bool: 제거 성공 여부. 존재하지 않으면 False
        """
        if inNode is None:
            return False

        attrDef = self.find_attribute_def(inNode, inDefName)
        if attrDef is None:
            return False

        try:
            rt.custAttributes.delete(inNode, attrDef)
        except Exception:
            return False

        return True

    def redefine_attribute_def(
        self, inNode, inDefName: str, inParams: list[dict]
    ) -> bool:
        """노드의 기존 커스텀 어트리뷰트를 새 파라미터로 재정의한다.

        기존 프로퍼티 값을 백업한 뒤 custAttributes.redefine으로 정의를
        변경하고, 동일 이름의 프로퍼티 값을 복원한다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름
            inParams (list[dict]): {name: str, type: str, default: Any} 형태의 새 파라미터 정의 리스트

        Returns:
            bool: 재정의 성공 여부. 어트리뷰트가 존재하지 않으면 False
        """
        if inNode is None:
            return False

        attrDef = self.find_attribute_def(inNode, inDefName)
        if attrDef is None:
            return False

        # 기존 프로퍼티 값 백업
        existingValues = self.get_all_properties(inNode, inDefName)

        # 새 정의 문자열로 재정의
        try:
            defString = self.build_param_def_string(inDefName, inParams)
            rt.custAttributes.redefine(attrDef, defString)
        except Exception:
            return False

        # 기존 값 복원 (동일 이름의 프로퍼티만)
        if existingValues:
            self.set_all_properties(inNode, inDefName, existingValues)

        return True

    def get_property(self, inNode, inDefName: str, inPropName: str) -> Optional[Any]:
        """단일 프로퍼티 값을 읽어 반환한다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름
            inPropName (str): 프로퍼티 이름

        Returns:
            Any | None: 프로퍼티 값. 프로퍼티가 없거나 에러 시 None
        """
        caBlock = self._get_ca_block(inNode, inDefName)
        if caBlock is None:
            return None

        try:
            if rt.isproperty(caBlock, inPropName):
                return rt.getProperty(caBlock, inPropName)
        except Exception:
            pass

        return None

    def set_property(
        self, inNode, inDefName: str, inPropName: str, inValue: Any
    ) -> bool:
        """단일 프로퍼티 값을 설정한다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름
            inPropName (str): 프로퍼티 이름
            inValue (Any): 설정할 값

        Returns:
            bool: 설정 성공 여부
        """
        caBlock = self._get_ca_block(inNode, inDefName)
        if caBlock is None:
            return False

        try:
            if rt.isproperty(caBlock, inPropName):
                rt.setProperty(caBlock, inPropName, inValue)
                return True
        except Exception:
            pass

        return False

    def get_all_properties(self, inNode, inDefName: str) -> dict[str, Any]:
        """어트리뷰트의 모든 프로퍼티를 딕셔너리로 반환한다.

        caBlock을 한 번만 조회한 뒤 루프에서 rt.getProperty로 직접 읽어
        N번 중복 조회를 방지한다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름

        Returns:
            dict[str, Any]: {프로퍼티명: 값} 딕셔너리. 빈 딕셔너리 가능
        """
        result: dict[str, Any] = {}

        caBlock = self._get_ca_block(inNode, inDefName)
        if caBlock is None:
            return result

        try:
            propNames = rt.getPropNames(caBlock)
        except Exception:
            return result

        if propNames is None:
            return result

        for propName in propNames:
            propNameStr = str(propName)
            try:
                result[propNameStr] = rt.getProperty(caBlock, propNameStr)
            except Exception:
                pass

        return result

    def set_all_properties(
        self, inNode, inDefName: str, inValues: dict[str, Any]
    ) -> bool:
        """딕셔너리로 전달받은 값을 해당 프로퍼티에 일괄 설정한다.

        caBlock을 한 번만 조회한 뒤 루프에서 rt.setProperty로 직접 설정하여
        N번 중복 조회를 방지한다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름
            inValues (dict[str, Any]): {프로퍼티명: 값} 딕셔너리

        Returns:
            bool: 하나라도 성공하면 True, 모두 실패하면 False
        """
        if not inValues:
            return False

        caBlock = self._get_ca_block(inNode, inDefName)
        if caBlock is None:
            return False

        success = False
        for propName, value in inValues.items():
            try:
                if rt.isproperty(caBlock, propName):
                    rt.setProperty(caBlock, propName, value)
                    success = True
            except Exception:
                pass

        return success

    def assign_float_controllers(self, inNode, inDefName: str) -> bool:
        """어트리뷰트의 float 프로퍼티에 Bezier Float 컨트롤러를 할당한다.

        이미 컨트롤러가 할당된 프로퍼티와 컨트롤러 할당이 불가능한
        타입(float가 아닌 타입)의 프로퍼티는 건너뛴다.

        Args:
            inNode (rt.Node): 대상 노드
            inDefName (str): 어트리뷰트 정의 이름

        Returns:
            bool: 어트리뷰트/프로퍼티 목록 조회에 실패하면 False, 그 외 True
        """
        caBlock = self._get_ca_block(inNode, inDefName)
        if caBlock is None:
            return False

        try:
            propNames = rt.getPropNames(caBlock)
        except Exception:
            return False

        if propNames is None:
            return False

        for propName in propNames:
            propNameStr = str(propName)
            try:
                ctrl = rt.getPropertyController(caBlock, propNameStr)
                if ctrl is None:
                    rt.setPropertyController(caBlock, propNameStr, rt.Bezier_Float())
            except Exception:
                # float가 아닌 타입은 컨트롤러 할당 불가 -> 건너뛰기
                pass

        return True

    # ------------------------------------------------------------------
    # Attribute Holder 모디파이어 (커스텀 어트리뷰트를 baseObject가 아니라
    # 모디파이어에 종속시킬 때 사용한다. 모디파이어를 제거하면 그 위의 CA와
    # 파라미터 컨트롤러·키가 함께 사라진다 - 2026-08-04 프로브 실측)
    #
    # 인덱싱 규약이 섞여 있으므로 주의한다.
    #   - node.modifiers[i]는 pymxs에서 0-based다.
    #   - rt.deleteModifier(node, i)는 MaxScript 함수라 1-based다.
    #   - rt.getModifier / rt.getNumModifiers는 pymxs에 없다.
    # ------------------------------------------------------------------

    def find_attribute_holder(self, inNode) -> Optional[Any]:
        """노드의 모디파이어 스택에서 Attribute Holder 모디파이어를 찾아 반환한다.

        스택 아래에서부터(인덱스 0부터) 처음 만나는 EmptyModifier를 반환한다.
        이름이 아니라 클래스로 판별하므로 사용자가 모디파이어 이름을 바꿔도 찾는다.

        Args:
            inNode (rt.Node): 대상 노드

        Returns:
            Any | None: Attribute Holder 모디파이어. 없거나 노드가 유효하지 않으면 None
        """
        if inNode is None:
            return None

        try:
            modifierCount = int(inNode.modifiers.count)
        except Exception:
            return None

        for i in range(modifierCount):
            modifier = inNode.modifiers[i]
            if rt.classOf(modifier) == rt.EmptyModifier:
                return modifier

        return None

    def ensure_attribute_holder(self, inNode) -> Optional[Any]:
        """노드에 Attribute Holder 모디파이어가 있음을 보장하고 그것을 반환한다.

        이미 있으면 기존 모디파이어를 그대로 반환하고 새로 만들지 않는다(멱등).
        없으면 EmptyModifier를 생성해 부착한 뒤 스택에서 다시 조회해 반환한다.

        Args:
            inNode (rt.Node): 대상 노드

        Returns:
            Any | None: Attribute Holder 모디파이어. 노드가 유효하지 않거나
                부착에 실패하면 None
        """
        if inNode is None:
            return None

        existingHolder = self.find_attribute_holder(inNode)
        if existingHolder is not None:
            return existingHolder

        rt.addModifier(inNode, rt.EmptyModifier())

        # 부착한 객체를 그대로 돌려주지 않고 스택에서 다시 찾아 반환한다.
        # 스택에 실제로 올라간 모디파이어를 반환해야 호출부의 후속 조작이
        # 씬 상태와 일치한다.
        return self.find_attribute_holder(inNode)

    def find_attribute_holder_index(self, inNode) -> int:
        """Attribute Holder 모디파이어의 0-based 스택 인덱스를 반환한다.

        ``rt.deleteModifier``는 1-based이므로 삭제 시 이 값에 1을 더해 넘긴다.

        Args:
            inNode (rt.Node): 대상 노드

        Returns:
            int: 0-based 인덱스. 없거나 노드가 유효하지 않으면 -1
        """
        if inNode is None:
            return -1

        try:
            modifierCount = int(inNode.modifiers.count)
        except Exception:
            return -1

        for i in range(modifierCount):
            if rt.classOf(inNode.modifiers[i]) == rt.EmptyModifier:
                return i

        return -1

    def remove_attribute_holder(self, inNode) -> bool:
        """노드에서 Attribute Holder 모디파이어를 제거한다.

        모디파이어를 제거하면 그 위에 붙어 있던 커스텀 어트리뷰트 정의와
        파라미터 컨트롤러·애니메이션 키가 함께 사라진다(2026-08-04 프로브 실측).
        되돌릴 수 없으므로 호출부가 사전에 사용자 확인을 받아야 한다.

        pymxs 예외를 삼키지 않는다. "홀더가 없다"는 정상 분기만 False로 알리고,
        그 밖의 실패는 호출부로 전파해 원인이 가려지지 않게 한다.

        Args:
            inNode (rt.Node): 대상 노드

        Returns:
            bool: 제거 성공 여부. 노드가 유효하지 않거나 홀더가 없으면 False
        """
        if inNode is None:
            return False

        holderIndex = self.find_attribute_holder_index(inNode)
        if holderIndex < 0:
            return False

        # rt.deleteModifier는 1-based 인덱스를 받는다.
        rt.deleteModifier(inNode, holderIndex + 1)

        return self.find_attribute_holder(inNode) is None

    def add_attribute_def_from_source(
        self, inTarget, inDefName: str, inDefSource: str
    ) -> bool:
        """MaxScript 정의 소스를 그대로 실행해 대상에 커스텀 어트리뷰트를 부착한다.

        ``add_attribute_def``는 ``build_param_def_string``으로 만든 단순
        ``parameters main`` 블록만 부착할 수 있다. 롤아웃·이벤트 핸들러·정의 레벨
        함수를 포함한 어트리뷰트는 이 메서드로 부착한다.

        ``inTarget``에는 노드뿐 아니라 **모디파이어 객체**를 넘길 수 있다
        (2026-08-04 프로브 실측). 단, 노드를 넘겼을 때의 조회 범위는
        baseObject이며 모디파이어에 붙은 어트리뷰트는 보이지 않는다.

        MaxScript 구문 오류 등 정의 소스 자체의 결함은 예외로 전파시킨다.
        조용히 False를 돌려주면 호출부가 "중복이라 실패한 것"과 구분할 수 없다.

        Args:
            inTarget (rt.Node | rt.Modifier): 어트리뷰트를 부착할 대상
            inDefName (str): 정의 이름. 중복 검사와 정의 소스 정합 검사에 쓴다
            inDefSource (str): ``attributes <name> ( ... )`` 형식의 MaxScript 정의 소스

        Returns:
            bool: 부착 성공 여부. 아래 경우 False.
                - 대상이 None이거나 정의 소스가 비어 있음
                - 같은 이름의 정의가 이미 대상에 있음
                - 정의 소스가 만든 정의의 이름이 ``inDefName``과 다름
        """
        if inTarget is None or not inDefSource:
            return False

        if self.find_attribute_def(inTarget, inDefName) is not None:
            return False

        attrDef = rt.execute(inDefSource)
        if attrDef is None:
            return False

        # 정의 소스의 실제 이름과 인자가 어긋나면 이후 조회·중복 검사가 전부
        # 빗나가므로 부착하지 않고 실패로 알린다.
        if str(attrDef.name) != inDefName:
            return False

        rt.custAttributes.add(inTarget, attrDef)

        return self.find_attribute_def(inTarget, inDefName) is not None
