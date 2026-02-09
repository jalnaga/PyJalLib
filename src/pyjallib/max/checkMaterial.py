#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckMaterial 모듈 - 3ds Max 머티리얼 검사 기능
원본 MAXScript의 ODC_Char_AssetChecks_Struct 중 MATERIAL 섹션을 Python으로 변환
"""

import os

from pymxs import runtime as rt


class CheckMaterial:
    """
    머티리얼 검사를 위한 클래스

    오브젝트에 할당된 머티리얼의 유효성(Material ID 연속성, 머티리얼 타입)을 검증합니다.
    외부 서비스 의존 없이 pymxs로 직접 판별합니다.
    """

    def __init__(self):
        """
        초기화 함수
        """
        pass

    def is_mat_ids_continued(self, inObj):
        """
        오브젝트의 Material ID가 1부터 연속적인지 확인.

        snapshotasmesh로 메쉬를 복제한 후 페이스별 MatID를 수집하고,
        1부터 max(ID)까지 연속된 ID인지 검증합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

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

    def has_correct_material(self, inObj):
        """
        오브젝트의 머티리얼이 유효한지 확인.

        유효 조건:
        - Multimaterial이면 유효
        - DirectX_9_Shader이면서 effectFile 파일명이 "ORV"로 시작하면 유효

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: 머티리얼이 유효하면 True
        """
        objMat = inObj.material
        if objMat is None:
            return False

        matClass = rt.classOf(objMat)

        if matClass == rt.Multimaterial:
            return True

        if matClass == rt.DirectX_9_Shader:
            effectFile = objMat.effectFile
            if effectFile is not None and effectFile != "":
                fileName = os.path.basename(effectFile)
                if fileName.upper().startswith("ORV"):
                    return True

        return False
