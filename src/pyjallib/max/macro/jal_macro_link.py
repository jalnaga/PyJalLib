#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymxs import runtime as rt

def jal_link_to_last():
    jal.link.link_to_last_sel()
    
def jal_link_to_first():
    jal.link.link_to_first_sel()

def jal_unlink():
    jal.link.unlink_selection()
    
def jal_unlink_children():
    jal.link.unlink_children()
    
# Register macroscripts
macroScript_Category = "jalTools"

rt.jal_link_to_last = jal_link_to_last
rt.macros.new(
    macroScript_Category,
    "jal_link_to_last",
    "Link to last",
    "Link to last",
    "jal_link_to_last()"
)

rt.jal_link_to_first = jal_link_to_first
rt.macros.new(
    macroScript_Category,
    "jal_link_to_first",
    "Link to first",
    "Link to first",
    "jal_link_to_first()"
)

rt.jal_unlink = jal_unlink
rt.macros.new(
    macroScript_Category,
    "jal_unLink",
    "Unlink",
    "Unlink",
    "jal_unlink()"
)

rt.jal_unlink_children = jal_unlink_children
rt.macros.new(
    macroScript_Category,
    "jal_unLink_children",
    "Unlink children",
    "Unlink children",
    "jal_unlink_children()"
)
