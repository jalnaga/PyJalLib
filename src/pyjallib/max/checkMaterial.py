#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckMaterial 모듈 - 3ds Max 머티리얼 검사 기능
원본 MAXScript 에셋 검사 구조체 중 MATERIAL 섹션을 Python으로 변환
"""

import os

from pymxs import runtime as rt


class CheckMaterial:
    """오브젝트에 할당된 머티리얼의 유효성(Material ID 연속성, 머티리얼 타입)을 검증하는 클래스.

    외부 서비스 의존 없이 pymxs로 직접 판별한다.
    """

    def __init__(self):
        """CheckMaterial을 초기화한다."""
        pass

    def is_mat_ids_continued(self, inObj):
        """오브젝트의 Material ID가 1부터 연속적인지 확인한다.

        snapshotAsMesh로 메쉬를 복제한 후 페이스별 MatID를 수집하고,
        1부터 max(ID)까지 빠짐없이 존재하는지 검증한다.

        Args:
            inObj (rt.Node): 검증할 오브젝트

        Returns:
            bool: Material ID가 1부터 max(ID)까지 연속이면 True
        """
        dupMesh = rt.snapshotAsMesh(inObj)
        polyNum = dupMesh.numfaces
        matIDSet = set()

        for i in range(1, polyNum + 1):
            matIDSet.add(rt.getFaceMatID(dupMesh, i))

        rt.delete(dupMesh)

        maxID = max(matIDSet)
        expectedSet = set(range(1, maxID + 1))
        return matIDSet == expectedSet

    @staticmethod
    def _normalize_shader_prefixes(inShaderNamePrefixes):
        """셰이더 파일 이름 접두 인자를 검증해 대문자 접두 튜플로 바꾼다.

        Args:
            inShaderNamePrefixes (str | Iterable[str]): 접두 하나 또는 접두 iterable

        Returns:
            tuple[str, ...]: 대소문자 무시 비교용 대문자 접두 튜플

        Raises:
            ValueError: 접두가 하나도 없거나, str이 아닌 원소가 있거나,
                빈 문자열(공백만 있는 문자열 포함) 원소가 있는 경우
        """
        if isinstance(inShaderNamePrefixes, str):
            prefixes = (inShaderNamePrefixes,)
        else:
            try:
                prefixes = tuple(inShaderNamePrefixes)
            except TypeError:
                raise ValueError(
                    f"셰이더 이름 접두는 str 또는 str의 iterable이어야 합니다: {inShaderNamePrefixes!r}"
                ) from None

        if not prefixes:
            raise ValueError("셰이더 이름 접두가 비어 있습니다.")
        for prefix in prefixes:
            if not isinstance(prefix, str):
                raise ValueError(f"셰이더 이름 접두는 str이어야 합니다: {prefix!r}")
            if not prefix.strip():
                raise ValueError(f"셰이더 이름 접두에 빈 문자열이 있습니다: {prefix!r}")

        return tuple(prefix.upper() for prefix in prefixes)

    def is_valid_shader_material(self, inMaterial, inShaderNamePrefixes):
        """머티리얼 하나가 셰이더 이름 규약을 따르는지 확인한다.

        DirectX_9_Shader이면서 effectFile의 파일 이름(`os.path.basename`)이 주어진
        접두 중 하나로 시작하면(대소문자 무시) 유효하다. 폴더 이름은 보지 않는다.
        Multimaterial을 포함해 DirectX_9_Shader가 아닌 머티리얼은 모두 False이며,
        서브 머티리얼 순회는 호출자 책임이다.
        접두 인자는 머티리얼 값과 관계없이 먼저 검증한다.

        Args:
            inMaterial (rt.Material | None): 검증할 머티리얼
            inShaderNamePrefixes (str | Iterable[str]): 유효한 DX9 셰이더 파일 이름 접두.
                str 하나 또는 str의 iterable(튜플·리스트 등). 예: "PBR_", ("PBR_", "Toon_")

        Returns:
            bool: 셰이더 이름 규약을 따르면 True. 머티리얼이 None이거나,
                effectFile이 비어 있거나, DirectX_9_Shader가 아니면 False

        Raises:
            ValueError: 접두가 비어 있거나(빈 iterable, 빈 문자열·공백만 있는 원소),
                str이 아닌 원소가 있거나, str도 iterable도 아닌 경우
        """
        upperPrefixes = self._normalize_shader_prefixes(inShaderNamePrefixes)

        if inMaterial is None:
            return False

        if rt.classOf(inMaterial) != rt.DirectX_9_Shader:
            return False

        effectFile = inMaterial.effectFile
        if effectFile is None or effectFile == "":
            return False

        fileName = os.path.basename(effectFile).upper()
        return fileName.startswith(upperPrefixes)

    def has_correct_material(self, inObj, inShaderNamePrefixes):
        """오브젝트의 머티리얼이 유효한지 확인한다.

        Multimaterial이면 서브 머티리얼과 관계없이 유효하다. 그 밖의 머티리얼은
        `is_valid_shader_material`과 같은 규칙으로 판정한다(DirectX_9_Shader이면서
        effectFile의 파일 이름이 주어진 접두 중 하나로 시작하면 유효, 대소문자 무시).
        유효한 셰이더 이름 규약은 프로젝트마다 다르므로 호출자가 접두를 넘긴다.
        접두 인자는 머티리얼 종류와 관계없이 먼저 검증한다.

        Args:
            inObj (rt.Node): 검증할 오브젝트
            inShaderNamePrefixes (str | Iterable[str]): 유효한 DX9 셰이더 파일 이름 접두.
                str 하나 또는 str의 iterable(튜플·리스트 등). 예: "PBR_", ("PBR_", "Toon_")

        Returns:
            bool: 머티리얼이 유효하면 True. 머티리얼이 없으면 False

        Raises:
            ValueError: 접두가 비어 있거나(빈 iterable, 빈 문자열 원소)
                str이 아닌 원소가 있는 경우
        """
        # 일회성 iterable(제너레이터 등)을 두 번 소비하지 않도록 정규화한 튜플을 넘긴다.
        upperPrefixes = self._normalize_shader_prefixes(inShaderNamePrefixes)

        objMat = inObj.material
        if objMat is None:
            return False

        if rt.classOf(objMat) == rt.Multimaterial:
            return True

        return self.is_valid_shader_material(objMat, upperPrefixes)
