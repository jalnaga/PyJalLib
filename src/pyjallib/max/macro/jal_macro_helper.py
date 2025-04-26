#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymxs import runtime as rt
from PySide2 import QtWidgets, QtCore, QtGui
import gc  # Import garbage collector

from pyjallib.max.header import Header

jal = Header()

class HelperTypeSelDialog(QtWidgets.QDialog):
    def __init__(self, parent=QtWidgets.QWidget.find(rt.windows.getMAXHWND())):
        super(HelperTypeSelDialog, self).__init__(parent)
        
        self.selectedHelperType = ""
        self.changeHelperType = False
        
        self.setWindowTitle("Helper Type")
        self.setMinimumWidth(100)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.helper_type_combo = QtWidgets.QComboBox(self)
        typeNamePart = jal.name.get_name_part("Type")
        typeNameDescriptions = typeNamePart.get_descriptions()
        self.helper_type_combo.addItems(typeNameDescriptions)
        self.layout.addWidget(self.helper_type_combo)

        self.ok_button = QtWidgets.QPushButton("OK", self)
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)
        
        self.ok_button.clicked.connect(self.ok_pressed)
    
    def ok_pressed(self):
        selHelperDescription = self.helper_type_combo.currentText()
        typeNamePart = jal.name.get_name_part("Type")
        self.selectedHelperType = typeNamePart.get_value_by_description(selHelperDescription)
        self.changeHelperType = True
        self.accept()

class ModifyHelperShapeDialog(QtWidgets.QDialog):
    def __init__(self, parent=QtWidgets.QWidget.find(rt.windows.getMAXHWND())):
        super(ModifyHelperShapeDialog, self).__init__(parent)
        self.helperArray = []

        self.setWindowTitle("Modify Helper Shape")

        self.layout = QtWidgets.QVBoxLayout(self)

        # Size and Add layout
        sizeLayout = QtWidgets.QHBoxLayout()
        addLayout = QtWidgets.QHBoxLayout()

        sizeLabel = QtWidgets.QLabel("Size:")
        self.size_spinbox = QtWidgets.QDoubleSpinBox()
        self.size_spinbox.setValue(1.0) # Default value
        self.size_spinbox.setSingleStep(0.1)
        sizeLayout.addWidget(sizeLabel)
        sizeLayout.addWidget(self.size_spinbox)

        addLabel = QtWidgets.QLabel("Add:")
        self.add_spinbox = QtWidgets.QDoubleSpinBox()
        self.add_spinbox.setValue(0.0) # Default value
        self.add_spinbox.setSingleStep(0.1)
        addLayout.addWidget(addLabel)
        addLayout.addWidget(self.add_spinbox)

        # Radio button layout
        shapeGroup = QtWidgets.QGroupBox("Shape:")
        radioLayout = QtWidgets.QGridLayout()
        self.radio_box = QtWidgets.QRadioButton("Box")
        self.radio_cross = QtWidgets.QRadioButton("Cross")
        self.radio_axis = QtWidgets.QRadioButton("Axis")
        self.radio_center = QtWidgets.QRadioButton("Center")
        self.radio_box.setChecked(True)  # Default selection
        radioLayout.addWidget(self.radio_box, 0, 0)
        radioLayout.addWidget(self.radio_cross, 0, 1)
        radioLayout.addWidget(self.radio_axis, 1, 0)
        radioLayout.addWidget(self.radio_center, 1, 1)
        shapeGroup.setLayout(radioLayout)
        
        # OK and Cancel buttons (optional but recommended)
        buttonLayout = QtWidgets.QHBoxLayout()
        self.ok_button = QtWidgets.QPushButton("OK")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        buttonLayout.addWidget(self.ok_button)
        buttonLayout.addWidget(self.cancel_button)
        
        self.layout.addLayout(sizeLayout)
        self.layout.addLayout(addLayout)
        self.layout.addWidget(shapeGroup)  # Add the group box to the layout instead of the raw radioLayout
        self.layout.addLayout(buttonLayout)
        
        self.size_spinbox.valueChanged.connect(self.change_helper_size)
        self.add_spinbox.valueChanged.connect(self.add_helper_size)
        self.add_spinbox.editingFinished.connect(self.reset_add_spinbox)
        
        self.radio_box.toggled.connect(self.change_helper_shape)
        self.radio_cross.toggled.connect(self.change_helper_shape)
        self.radio_axis.toggled.connect(self.change_helper_shape)
        self.radio_center.toggled.connect(self.change_helper_shape)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def change_helper_size(self):
        if len(self.helperArray) == 0:
            return
        for obj in self.helperArray:
            jal.helper.set_size(obj, self.size_spinbox.value())
    
    def add_helper_size(self):
        if len(self.helperArray) == 0:
            return
        for obj in self.helperArray:
            jal.helper.add_size(obj, self.add_spinbox.value())
    
    def reset_add_spinbox(self):
        self.add_spinbox.setValue(0.0)  # Reset the add spinbox to 0 after editing is finished
    
    def change_helper_shape(self):
        if len(self.helperArray) == 0:
            return
        for obj in self.helperArray:
            if self.radio_box.isChecked():
                jal.helper.set_shape_to_box(obj)
            elif self.radio_cross.isChecked():
                jal.helper.set_shape_to_cross(obj)
            elif self.radio_axis.isChecked():
                jal.helper.set_shape_to_axis(obj)
            elif self.radio_center.isChecked():
                jal.helper.set_shape_to_center(obj)

def jal_create_parentHelper():
    jal.helper.create_parent_helper()

def jal_create_helper():
    dialog = HelperTypeSelDialog()
    result = dialog.exec_()
    changeHelperType = dialog.changeHelperType
    if changeHelperType:
        helperType = dialog.selectedHelperType
        genHelpers = jal.helper.create_helper()
        for item in genHelpers:
            item.name = jal.name.replace_name_part("Type", item.name, helperType)
        
    dialog.deleteLater()
    dialog = None  # Clear the reference to the dialog object
    gc.collect()  # Force garbage collection to free up memory

def jal_create_average_helper():
    sel_array = rt.getCurrentSelection()
    
    if len(sel_array) > 0:
        temp_transform = rt.matrix3(1)
        temp_transform.rotation = jal.anim.create_average_rot_transform(sel_array).rotation
        temp_transform.position = jal.anim.create_average_pos_transform(sel_array).position
        
        dum_name = jal.helper.gen_helper_name_from_obj(sel_array[0])
        dum_shape = jal.helper.gen_helper_shape_from_obj(sel_array[0])
        average_dum = jal.helper.create_point(
            dum_name[0], 
            size=dum_shape[0],
            boxToggle=dum_shape[2],
            crossToggle=dum_shape[1]
        )
        average_dum.transform = temp_transform

def jal_create_pos_average_helper():
    sel_array = rt.getCurrentSelection()
    
    if len(sel_array) > 0:
        temp_transform = rt.matrix3(1)
        temp_transform.position = jal.anim.create_average_pos_transform(sel_array).position
        
        dum_name = jal.helper.gen_helper_name_from_obj(sel_array[0])
        dum_shape = jal.helper.gen_helper_shape_from_obj(sel_array[0])
        average_dum = jal.helper.create_point(
            dum_name[0], 
            size=dum_shape[0],
            boxToggle=dum_shape[2],
            crossToggle=dum_shape[1]
        )
        average_dum.transform = temp_transform
        average_dum.name = jal.name.replace_name_part("Type", average_dum.name, "Pos")

def jal_create_rot_average_helper():
    sel_array = rt.getCurrentSelection()
    
    if len(sel_array) > 0:
        temp_transform = rt.matrix3(1)
        temp_transform.rotation = jal.anim.create_average_rot_transform(sel_array).rotation
        
        dum_name = jal.helper.gen_helper_name_from_obj(sel_array[0])
        dum_shape = jal.helper.gen_helper_shape_from_obj(sel_array[0])
        average_dum = jal.helper.create_point(
            dum_name[0], 
            size=dum_shape[0],
            boxToggle=dum_shape[2],
            crossToggle=dum_shape[1]
        )
        average_dum.transform = temp_transform
        average_dum.name = jal.name.replace_name_part("Type", average_dum.name, "Rot")

def jal_create_expHelper():
    jal.helper.create_exp_tm()

def jal_create_two_helper():
    dialog = HelperTypeSelDialog()
    result = dialog.exec_()
    helperType = dialog.selectedHelperType
    genHelpers = jal.helper.create_helper(make_two=True)
    for item in genHelpers:
        item.name = jal.name.replace_name_part("Type", item.name, helperType)
        
    dialog.deleteLater()
    dialog = None  # Clear the reference to the dialog object
    gc.collect()  # Force garbage collection to free up memory

def jal_modify_helperShape():
    # Get current selection
    selArray = rt.getCurrentSelection()
    if not selArray or len(selArray) == 0:
        rt.messageBox("Please select at least one helper object.")
        return
    helperArray = [item for item in selArray if rt.superClassOf(item) == rt.Helper]
    if len(helperArray) == 0:
        return

    # Assuming the first selected object is the one to modify
    helperObj = helperArray[0]

    modDialog = ModifyHelperShapeDialog()

    # Set initial values from the selected helper (if possible)
    modDialog.size_spinbox.setValue(helperObj.size)
    
    modDialog.helperArray = helperArray

    result = modDialog.exec_()

    modDialog.deleteLater()
    modDialog = None
    gc.collect()

# Register macroscripts
macroScript_Category = "jalTools"

rt.jal_create_parentHelper = jal_create_parentHelper
rt.macros.new(
    macroScript_Category,
    "jal_create_parentHelper",
    "Create Parent Helper",
    "Create Parent Helper",
    "jal_create_parentHelper()"
)

rt.jal_create_helper = jal_create_helper
rt.macros.new(
    macroScript_Category,
    "jal_create_helper",
    "Create Helper",
    "Create Helper",
    "jal_create_helper()"
)

rt.jal_create_average_helper = jal_create_average_helper
rt.macros.new(
    macroScript_Category,
    "jal_create_average_helper",
    "Create Average Helper",
    "Create Average Helper",
    "jal_create_average_helper()"
)

rt.jal_create_pos_average_helper = jal_create_pos_average_helper
rt.macros.new(
    macroScript_Category,
    "jal_create_pos_average_helper",
    "Create Pos avrg. Helper",
    "Create Pos avrg. Helper",
    "jal_create_pos_average_helper()"
)

rt.jal_create_rot_average_helper = jal_create_rot_average_helper
rt.macros.new(
    macroScript_Category,
    "jal_create_rot_average_helper",
    "Create Rot avrg. Helper",
    "Create Rot avrg. Helper",
    "jal_create_rot_average_helper()"
)

rt.jal_create_expHelper = jal_create_expHelper
rt.macros.new(
    macroScript_Category,
    "jal_create_expHelper",
    "Create Exp Helper",
    "Create Exp Helper",
    "jal_create_expHelper()"
)

rt.jal_create_two_helper = jal_create_two_helper
rt.macros.new(
    macroScript_Category,
    "jal_create_two_helper",
    "Create Two Helper",
    "Create Two Helper",
    "jal_create_two_helper()"
)

rt.jal_modify_helperShape = jal_modify_helperShape
rt.macros.new(
    macroScript_Category,
    "jal_modify_helperShape",
    "Modify Helper shape",
    "Modify Helper shape",
    "jal_modify_helperShape()"
)
