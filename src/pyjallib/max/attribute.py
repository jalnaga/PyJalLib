#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
어트리뷰트(Attribute) 모듈 - 3ds Max 커스텀 어트리뷰트 범용 관리 서비스

노드에 커스텀 어트리뷰트를 추가, 조회, 수정, 삭제하고
프로퍼티 읽기/쓰기 및 컨트롤러 할당 기능을 제공합니다.
"""

from typing import Any, Optional

from pymxs import runtime as rt


class Attribute:
    """노드의 커스텀 어트리뷰트 정의를 추가·조회·수정·삭제하고 프로퍼티 읽기/쓰기와 컨트롤러 할당을 제공한다."""

    # 지원 타입 매핑 (Python 타입명 -> MaxScript 타입 문자열)
    SUPPORTED_TYPES = {
        "float": "#float",
        "integer": "#integer",
        "boolean": "#boolean",
        "string": "#string",
    }

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

        Args:
            inNode (rt.Node): 검색 대상 노드
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
        """노드에 지정된 이름의 커스텀 어트리뷰트가 존재하는지 확인한다.

        Args:
            inNode (rt.Node): 검색 대상 노드
            inDefName (str): 어트리뷰트 정의 이름

        Returns:
            bool: 존재하면 True. 없거나 노드가 유효하지 않으면 False
        """
        if inNode is None:
            return False

        try:
            if not rt.isvalidnode(inNode):
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
