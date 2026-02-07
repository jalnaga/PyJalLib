#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CheckObject 모듈 - 3ds Max 오브젝트 검사 기능
원본 MAXScript의 ODC_Char_AssetChecks_Struct 중 OBJECT/UV/ANIMATION 섹션을 Python으로 변환
"""

from pymxs import runtime as rt


class CheckObject:
    """
    오브젝트 검사를 위한 클래스

    메쉬 오브젝트의 구조적 유효성(이름, 폴리곤 타입, Ngon, Transform, 모디파이어,
    UV, 애니메이션 등)을 검증하고 수정하는 기능을 제공합니다.
    외부 서비스 의존 없이 pymxs로 직접 판별합니다.
    """

    def __init__(self):
        """
        초기화 함수
        """
        pass

    def has_valid_name(self, inObj, inValidName):
        """
        오브젝트 이름이 외부에서 전달받은 올바른 이름과 일치하는지 비교.

        Args:
            inObj: 검증할 3ds Max 오브젝트
            inValidName: 올바른 이름 문자열

        Returns:
            bool: 이름이 일치하면 True
        """
        if not rt.isValidNode(inObj):
            return False
        return inObj.name == inValidName

    def is_editable_poly(self, inObj):
        """
        오브젝트의 baseObject가 Editable_Poly인지 확인.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: Editable_Poly이면 True
        """
        if not rt.isValidNode(inObj):
            return False
        return rt.classOf(inObj.baseObject) == rt.Editable_Poly

    def fix_editable_poly(self, inObj):
        """
        오브젝트를 Editable_Poly로 변환.

        모디파이어가 있으면 맨 아래에 Edit_Poly를 추가한 후 콜랩스하고,
        없으면 Edit_Poly 추가 후 전체 콜랩스합니다.

        Args:
            inObj: 변환할 3ds Max 오브젝트

        Returns:
            None
        """
        if not rt.isValidNode(inObj):
            return

        if inObj.modifiers.count > 0:
            rt.addModifier(inObj, rt.Edit_Poly(), before=inObj.modifiers.count)
            rt.maxOps.CollapseNodeTo(inObj, inObj.modifiers.count, True)
        else:
            rt.addModifier(inObj, rt.Edit_Poly())
            rt.collapseStack(inObj)

        rt.polyOp.collapseDeadStructs(inObj)

    def check_ngons(self, inObj):
        """
        오브젝트의 Ngon(5각형 이상) 페이스 ID 목록을 반환.

        snapshot으로 메쉬를 복제한 후 각 페이스의 vertex 수를 확인하여
        3각형/4각형이 아닌 페이스를 수집합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            list: Ngon 페이스 ID 리스트
        """
        dupMesh = rt.snapShot(inObj)
        dupMesh = rt.convertToPoly(dupMesh)
        ngons = []

        numFaces = rt.polyOp.getNumFaces(dupMesh)
        for f in range(1, numFaces + 1):
            verts = rt.polyOp.getVertsUsingFace(dupMesh, f)
            numVerts = len(rt.execute(str(verts) + " as array"))
            if numVerts != 3 and numVerts != 4:
                if f not in ngons:
                    ngons.append(f)

        rt.delete(dupMesh)
        return ngons

    def has_ngons(self, inObj):
        """
        오브젝트에 Ngon이 존재하는지 확인.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: Ngon이 있으면 True
        """
        return len(self.check_ngons(inObj)) > 0

    def has_init_xform(self, inObj):
        """
        오브젝트의 Transform이 초기 상태인지 확인.

        rotation이 (0,0,0,1), scale이 (1,1,1)인지 확인합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: Transform이 초기 상태이면 True
        """
        if not rt.isValidNode(inObj):
            return False

        initQuat = rt.quat(0, 0, 0, 1)
        initScale = rt.point3(1, 1, 1)

        if inObj.rotation != initQuat or inObj.scale != initScale:
            return False

        return True

    def fix_xform(self, inObj):
        """
        XForm 모디파이어를 이용하여 오브젝트의 Transform을 초기화.

        임시 Point 헬퍼를 생성하여 자식 노드를 임시로 이동시킨 후,
        XForm 모디파이어를 적용하여 Transform을 초기화하고 자식 노드를 복원합니다.

        Args:
            inObj: 초기화할 3ds Max 오브젝트

        Returns:
            None
        """
        if not rt.isValidNode(inObj):
            return

        objParent = inObj.parent
        objChildren = [child for child in inObj.children]

        tempDum = rt.Point()
        tempDum.Transform = inObj.Transform
        for child in objChildren:
            child.parent = tempDum
        tempDum.parent = objParent
        inObj.parent = None

        xFrm = rt.xForm()
        objTm = inObj.objectTransform
        tm = inObj.transform

        inObj.Transform = rt.matrix3(
            rt.point3(1, 0, 0),
            rt.point3(0, 1, 0),
            rt.point3(0, 0, 1),
            tm.row4
        )
        inObj.objectOffsetPos = rt.point3(0, 0, 0)
        inObj.objectOffsetRot = rt.quat(0, 0, 0, 1)
        inObj.pivot = tm.row4

        rt.addModifier(inObj, xFrm, before=inObj.modifiers.count)
        inObj.xform.gizmo.transform = objTm * rt.inverse(inObj.objectTransform)
        rt.maxOps.CollapseNodeTo(inObj, inObj.modifiers.count, True)

        for child in objChildren:
            child.parent = inObj
        inObj.parent = objParent
        rt.delete(tempDum)

    def is_transform_locked(self, inObj):
        """
        오브젝트의 Transform이 잠겨있는지 확인.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: Transform이 잠겨있으면 True
        """
        locked = rt.getTransformLockFlags(inObj)
        lockedArray = rt.execute(str(locked) + " as Array")
        return len(lockedArray) > 0

    def fix_transform_locked(self, inObj):
        """
        오브젝트의 Transform 잠금을 해제.

        Args:
            inObj: 잠금 해제할 3ds Max 오브젝트

        Returns:
            None
        """
        rt.setTransformLockFlags(inObj, rt.Name("none"))

    def has_correct_mod(self, inObj):
        """
        오브젝트의 모디파이어 스택이 올바른지 확인.

        허용되는 모디파이어: Skin, Morpher
        Skin이 있으면 반드시 최상위(첫 번째)에 위치해야 합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: 모디파이어 스택이 올바르면 True
        """
        mods = [inObj.modifiers[i] for i in range(inObj.modifiers.count)]

        if len(mods) == 0:
            return True

        for item in mods:
            itemClass = rt.classOf(item)
            if itemClass != rt.Skin and itemClass != rt.Morpher:
                return False

        if rt.classOf(mods[0]) != rt.Skin:
            return False

        return True

    def check_uv_range(self, inObj):
        """
        오브젝트의 UV 좌표가 0~1 범위 내인지 확인.

        Unwrap_UVW를 추가하여 각 UV 채널의 버텍스 좌표를 검사합니다.
        오브젝트 이름에 "_FAC_"가 포함된 경우 U 범위를 1~2로 허용합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: 모든 UV가 범위 내이면 True
        """
        # 기존 Unwrap_UVW 모디파이어가 있는지 확인
        hasUvMod = False
        for i in range(inObj.modifiers.count):
            if rt.classOf(inObj.modifiers[i]) == rt.Unwrap_UVW:
                hasUvMod = True
                break

        if not hasUvMod:
            rt.addModifier(inObj, rt.Unwrap_UVW())

        uvMod = inObj.modifiers[rt.Name("Unwrap_UVW")]
        rt.modPanel.setCurrentObject(uvMod)

        isOk = True
        isFac = rt.matchPattern(inObj.name, pattern="*_FAC_*")
        numMaps = rt.polyOp.getNumMaps(inObj)

        for n in range(1, numMaps):
            uvMod.setMapChannel(n)
            self._uv_channel_silent_reset(uvMod)
            rt.redrawViews()

            for i in range(1, uvMod.numbervertices() + 1):
                vert = rt.polyOp.getMapVert(inObj, n, i)
                if not isFac:
                    if vert[0] < 0 or vert[0] > 1 or vert[1] < 0 or vert[1] > 1:
                        isOk = False
                else:
                    if vert[0] < 1 or vert[0] > 2 or vert[1] < 0 or vert[1] > 1:
                        isOk = False
                if not isOk:
                    break
            if not isOk:
                break

        rt.deleteModifier(inObj, uvMod)
        return isOk

    def _uv_channel_silent_reset(self, inUvMod):
        """
        Unwrap UVW 모디파이어의 채널 리셋을 다이얼로그 없이 수행.

        팝업 다이얼로그의 "Yes" 버튼을 자동으로 누르는 콜백을 등록합니다.

        Args:
            inUvMod: Unwrap_UVW 모디파이어 인스턴스

        Returns:
            None
        """
        code = """
        fn confirmReset = (
            local hwnd = dialogMonitorOps.getWindowHandle()
            if UIAccessor.GetWindowText hwnd == "Unwrap UVW" then (
                uiAccessor.pressDefaultButton()
                true
            ) else false
        )
        dialogMonitorOps.unRegisterNotification id:#unwrap_reset
        dialogMonitorOps.enabled = true
        dialogMonitorOps.interactive = false
        dialogMonitorOps.registerNotification confirmReset id:#unwrap_reset
        """
        rt.execute(code)
        inUvMod.reset()
        rt.dialogMonitorOps.enabled = False

    def check_num_uv_channels(self, inObj):
        """
        오브젝트의 UV 채널 수가 1~2개인지 확인.

        Editable_Poly 또는 PolyMeshObject에서 지원되는 UV 채널 수를 카운트합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            bool: UV 채널 수가 1~2이면 True
        """
        objClass = rt.classOf(inObj)
        if objClass != rt.Editable_Poly and objClass != rt.PolyMeshObject:
            return False

        numChan = 0
        numMaps = rt.polyOp.getNumMaps(inObj)
        for i in range(1, numMaps):
            if rt.polyOp.getMapSupport(inObj, i):
                numChan += 1

        return numChan == 1 or numChan == 2

    def check_animation_keys(self, inObj):
        """
        오브젝트의 애니메이션 키를 수집.

        Biped 오브젝트는 controller.keys를 반환하고,
        일반 오브젝트는 mapkeys를 통해 수집합니다.

        Args:
            inObj: 검증할 3ds Max 오브젝트

        Returns:
            list: 애니메이션 키 리스트
        """
        if rt.classOf(inObj) == rt.Biped_Object:
            return inObj.controller.keys

        code = """
        fn collectKeysFromObj obj = (
            fn collect_keys t k = ( append k t; t )
            mapkeys obj collect_keys ( keys=#() ) #allkeys
            return keys
        )
        """
        rt.execute(code)
        keys = rt.collectKeysFromObj(inObj)
        return keys

    def check_animation_keys_fix(self, inObj):
        """
        오브젝트의 모든 애니메이션 키를 삭제.

        Args:
            inObj: 키를 삭제할 3ds Max 오브젝트

        Returns:
            None
        """
        rt.sliderTime = 0
        rt.deleteKeys(inObj, rt.Name("allKeys"))

    def check_meshes_not_animated(self):
        """
        씬 내에서 애니메이션이 있는 메쉬(PolyMeshObject/Editable_Poly)를 수집.

        Returns:
            list: 애니메이션이 있는 메쉬 오브젝트 리스트
        """
        objHaveAnimation = []
        for obj in rt.geometry:
            objClass = rt.classOf(obj)
            if objClass == rt.PolyMeshObject or objClass == rt.Editable_Poly:
                keys = self.check_animation_keys(obj)
                if len(keys) > 0:
                    objHaveAnimation.append(obj)
        return objHaveAnimation
