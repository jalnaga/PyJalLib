#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymxs import runtime as rt

def jal_align_to_last():
    jal.align.align_to_last_sel()
    
def jal_align_to_last_center():
    jal.align.align_to_last_sel_center()

def jal_align_pos_only():
    jal.align.align_pos_only()
    
def jal_align_rot_only():
    jal.align.align_rot_only()
    
def jal_align_mirror_x():
    if rt.selection.count == 0:
        return False
    
    pObj = None
    defMirrorAxis = 0
    oriObjArray = rt.getCurrentSelection()
    boneArray = []
    helperArray = []
    nonBoneArray = []
    
    mirroredBoneArray = []
    mirroredHelperArray = []
    mirroredNonBoneArray = []
    
    mirroredObjArray = []
    
    defMirrorAxis = 1
    
    for item in oriObjArray:
        if rt.classOf(item) == rt.BoneGeometry:
            boneArray.append(item)
        elif rt.superClassOf(item) == rt.Helper:
            helperArray.append(item)
        else:
            nonBoneArray.append(item)
    
    if boneArray.count != 0:
        mirroredBoneArray = jal.mirror.mirror_bone(boneArray, mAxis=defMirrorAxis)
    if helperArray.count != 0:
        mirroredHelperArray = jal.mirror.mirror_geo(helperArray, mAxis=defMirrorAxis, pivotObj=pObj, cloneStatus=2)
    if nonBoneArray.count != 0:
        mirroredNonBoneArray = jal.mirror.mirror_geo(nonBoneArray, mAxis=defMirrorAxis, pivotObj=pObj, cloneStatus=2)
    
    mirroredObjArray.extend(mirroredBoneArray)
    mirroredObjArray.extend(mirroredHelperArray)
    mirroredObjArray.extend(mirroredNonBoneArray)
    
    rt.clearSelection()
    rt.select(mirroredObjArray)

def jal_align_mirror_y():
    if rt.selection.count == 0:
        return False
    
    pObj = None
    defMirrorAxis = 0
    oriObjArray = rt.getCurrentSelection()
    boneArray = []
    helperArray = []
    nonBoneArray = []
    
    mirroredBoneArray = []
    mirroredHelperArray = []
    mirroredNonBoneArray = []
    
    mirroredObjArray = []
    
    defMirrorAxis = 2
    
    for item in oriObjArray:
        if rt.classOf(item) == rt.BoneGeometry:
            boneArray.append(item)
        elif rt.superClassOf(item) == rt.Helper:
            helperArray.append(item)
        else:
            nonBoneArray.append(item)
    
    if boneArray.count != 0:
        mirroredBoneArray = jal.mirror.mirror_bone(boneArray, mAxis=defMirrorAxis)
    if helperArray.count != 0:
        mirroredHelperArray = jal.mirror.mirror_geo(helperArray, mAxis=defMirrorAxis, pivotObj=pObj, cloneStatus=2)
    if nonBoneArray.count != 0:
        mirroredNonBoneArray = jal.mirror.mirror_geo(nonBoneArray, mAxis=defMirrorAxis, pivotObj=pObj, cloneStatus=2)
    
    mirroredObjArray.extend(mirroredBoneArray)
    mirroredObjArray.extend(mirroredHelperArray)
    mirroredObjArray.extend(mirroredNonBoneArray)
    
    rt.clearSelection()
    rt.select(mirroredObjArray)
    
    
macroScript_Category = "jalTools"

rt.jal_align_to_last = jal_align_to_last
rt.macros.new(
    macroScript_Category,
    "jal_align_to_last",
    "Align to last",
    "Align to last",
    "jal_align_to_last()"
)

rt.jal_align_to_last_center = jal_align_to_last_center
rt.macros.new(
    macroScript_Category,
    "jal_align_to_last_center",
    "Align to last center",
    "Align to last center",
    "jal_align_to_last_center()"
)

rt.jal_align_pos_only = jal_align_pos_only
rt.macros.new(
    macroScript_Category,
    "jal_align_pos_only",
    "Align position only",
    "Align position only",
    "jal_align_pos_only()"
)

rt.jal_align_rot_only = jal_align_rot_only
rt.macros.new(
    macroScript_Category,
    "jal_align_rot_only",
    "Align rotation only",
    "Align rotation only",
    "jal_align_rot_only()"
)

rt.jal_align_mirror_x = jal_align_mirror_x
rt.macros.new(
    macroScript_Category,
    "jal_align_mirror_x",
    "Mirror X",
    "Mirror X",
    "jal_align_mirror_x()"
)

rt.jal_align_mirror_y = jal_align_mirror_y
rt.macros.new(
    macroScript_Category,
    "jal_align_mirror_y",
    "Mirror Y",
    "Mirror Y",
    "jal_align_mirror_y()"
)