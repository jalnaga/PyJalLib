#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymxs import runtime as rt

def jal_collapse_const():
    if rt.selection.count > 0:
        selArray = rt.getCurrentSelection()
        for selObj in selArray:
            jal.constraint.collapse(selObj)

def jal_pos_const():
    if rt.selection.count > 1:
        selArray = rt.getCurrentSelection()
        oriObj = selArray[0]  # Python uses 0-based indexing
        targetObjArray = []
        
        # Add all objects except the first one to targetObjArray
        for i in range(1, len(selArray)):
            targetObjArray.append(selArray[i])
        
        jal.constraint.assign_pos_const_multi(oriObj, targetObjArray)

def jal_ori_const():
    if rt.selection.count > 1:
        selArray = rt.getCurrentSelection()
        oriObj = selArray[0]  # Python uses 0-based indexing
        targetObjArray = []
        
        # Add all objects except the first one to targetObjArray
        for i in range(1, len(selArray)):
            targetObjArray.append(selArray[i])
        
        jal.constraint.assign_rot_const_multi(oriObj, targetObjArray)

def jal_rot_script_const():
    if rt.selection.count == 2:
        selArray = rt.getCurrentSelection()
        oriObj = selArray[0]
        targetObj = selArray[1]
        
        jal.constraint.assign_rot_const_scripted(oriObj, targetObj)

def jal_lookat_const():
    if rt.selection.count > 1:
        selArray = rt.getCurrentSelection()
        oriObj = selArray[0]  # Python uses 0-based indexing
        targetObjArray = []
        
        # Add all objects except the first one to targetObjArray
        for i in range(1, len(selArray)):
            targetObjArray.append(selArray[i])
        
        jal.constraint.assign_lookat_multi(oriObj, targetObjArray)

def jal_lookat_flipless_const():
    if rt.selection.count == 2:
        selArray = rt.getCurrentSelection()
        oriObj = selArray[0]
        targetObj = selArray[1]
        
        jal.constraint.assign_lookat_flipless(oriObj, targetObj)

def jal_lookat_script_const():
    if rt.selection.count > 1:
        selArray = rt.getCurrentSelection()
        oriObj = selArray[0]  # Python uses 0-based indexing
        targetObjArray = []
        
        # Add all objects except the first one to targetObjArray
        for i in range(1, len(selArray)):
            targetObjArray.append(selArray[i])
        
        jal.constraint.assign_scripted_lookat(oriObj, targetObjArray)

# Register macroscripts
macroScript_Category = "jalTools"

rt.jal_collapse_const = jal_collapse_const
rt.macros.new(
    macroScript_Category,
    "jal_collapse_const",
    "Collapse Constraints",
    "Collapse Constraints",
    "jal_collapse_const()"
)

rt.jal_pos_const = jal_pos_const
rt.macros.new(
    macroScript_Category,
    "jal_pos_const",
    "Constraint Position",
    "Constraint Position",
    "jal_pos_const()"
)

rt.jal_ori_const = jal_ori_const
rt.macros.new(
    macroScript_Category,
    "jal_ori_const",
    "Constraint Orientation",
    "Constraint Orientation",
    "jal_ori_const()"
)

rt.jal_rot_script_const = jal_rot_script_const
rt.macros.new(
    macroScript_Category,
    "jal_rot_script_const",
    "Constraint Rotation Script",
    "Constraint Rotation Script",
    "jal_rot_script_const()"
)

rt.jal_lookat_const = jal_lookat_const
rt.macros.new(
    macroScript_Category,
    "jal_lookat_const",
    "Constraint LookAt",
    "Constraint LookAt",
    "jal_lookat_const()"
)

rt.jal_lookat_flipless_const = jal_lookat_flipless_const
rt.macros.new(
    macroScript_Category,
    "jal_lookat_flipless_const",
    "Constraint LookAt Flipless",
    "Constraint LookAt Flipless",
    "jal_lookat_flipless_const()"
)

rt.jal_lookat_script_const = jal_lookat_script_const
rt.macros.new(
    macroScript_Category,
    "jal_lookat_script_const",
    "Constraint LookAt Script",
    "Constraint LookAt Script",
    "jal_lookat_script_const()"
)
