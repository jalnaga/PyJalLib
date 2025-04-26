#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymxs import runtime as rt

def jal_selFilter_all():
    jal.sel.set_selectionSet_to_all()
    if rt.selection.count > 0:
        rt.getCurrentSelection()

def jal_selFilter_bone():
    jal.sel.set_selectionSet_to_bone()
    if rt.selection.count > 0:
        jal.sel.filter_bone()

def jal_selFilter_bip():
    jal.sel.set_selectionSet_to_bone()
    if rt.selection.count > 0:
        jal.sel.filter_bip()

def jal_selFilter_point():
    jal.sel.set_selectionSet_to_point()
    if rt.selection.count > 0:
        jal.sel.filter_helper()

def jal_selFilter_expTm():
    jal.sel.set_selectionSet_to_helper()
    if rt.selection.count > 0:
        jal.sel.filter_expTm()

def jal_selFilter_spline():
    jal.sel.set_selectionSet_to_spline()
    if rt.selection.count > 0:
        jal.sel.filter_spline()

# Register macroscripts
macroScript_Category = "jalTools"

rt.jal_selFilter_all = jal_selFilter_all
rt.macros.new(
    macroScript_Category,
    "jal_selFilter_all",
    "Selection filter All",
    "Selection filter All",
    "jal_selFilter_all()"
)

rt.jal_selFilter_bone = jal_selFilter_bone
rt.macros.new(
    macroScript_Category,
    "jal_selFilter_bone",
    "Selection filter Bone",
    "Selection filter Bone", 
    "jal_selFilter_bone()"
)

rt.jal_selFilter_bip = jal_selFilter_bip
rt.macros.new(
    macroScript_Category,
    "jal_selFilter_bip",
    "Selection filter Bip",
    "Selection filter Bip",
    "jal_selFilter_bip()"
)

rt.jal_selFilter_point = jal_selFilter_point
rt.macros.new(
    macroScript_Category,
    "jal_selFilter_point",
    "Selection filter Point",
    "Selection filter Point",
    "jal_selFilter_point()"
)

rt.jal_selFilter_expTm = jal_selFilter_expTm
rt.macros.new(
    macroScript_Category,
    "jal_selFilter_expTm",
    "Selection filter ExpTm",
    "Selection filter ExpTm",
    "jal_selFilter_expTm()"
)

rt.jal_selFilter_spline = jal_selFilter_spline
rt.macros.new(
    macroScript_Category,
    "jal_selFilter_spline",
    "Selection filter Spline",
    "Selection filter Spline",
    "jal_selFilter_spline()"
)