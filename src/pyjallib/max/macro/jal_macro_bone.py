#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymxs import runtime as rt
from pyjallib.max.header import get_pyjallibmaxheader
jal = get_pyjallibmaxheader()

from PySide2 import QtWidgets, QtCore, QtGui
import gc  # Import garbage collector

class BoneNameDialog(QtWidgets.QDialog):
    def __init__(self, parent=QtWidgets.QWidget.find(rt.windows.getMAXHWND())):
        super().__init__(parent)
        self.boneNameSetted = False
        self.baseName = ""
        self.sideName = ""
        self.frontBackName = ""
        self.RealName = ""
        self.filteringChar = " "
        self.boneName = ""
        
        self.setWindowTitle("Bone Name")
        self.setMinimumWidth(300)

        # Layouts
        main_layout = QtWidgets.QVBoxLayout(self)
        grid_layout = QtWidgets.QGridLayout()
        radio_button_layout = QtWidgets.QHBoxLayout()
        button_layout = QtWidgets.QHBoxLayout()

        # Widgets
        # Base Name
        base_name_label = QtWidgets.QLabel("Base Name:")
        self.base_name_edit = QtWidgets.QLineEdit("Bip001")
        self.base_name_edit.setReadOnly(True)
        self.base_name_combo = QtWidgets.QComboBox() # Placeholder for dropdown
        comboItems = jal.name.get_name_part_predefined_values("Base")
        comboItems.insert(0, "")
        self.base_name_combo.addItems(comboItems)
        self.base_name_combo.setCurrentIndex(2) # Set default index to 0

        # Name
        name_label = QtWidgets.QLabel("Name:")
        self.name_edit = QtWidgets.QLineEdit("TempBone")

        # Side Radio Buttons
        side_group = QtWidgets.QGroupBox("Side:")
        side_layout = QtWidgets.QVBoxLayout()
        self.side_none_radio = QtWidgets.QRadioButton("(None)")
        self.side_l_radio = QtWidgets.QRadioButton("L")
        self.side_r_radio = QtWidgets.QRadioButton("R")
        self.side_none_radio.setChecked(True)
        side_layout.addWidget(self.side_none_radio)
        side_layout.addWidget(self.side_l_radio)
        side_layout.addWidget(self.side_r_radio)
        side_group.setLayout(side_layout)

        # Front Radio Buttons
        front_group = QtWidgets.QGroupBox("Front:")
        front_layout = QtWidgets.QVBoxLayout()
        self.front_none_radio = QtWidgets.QRadioButton("(None)")
        self.front_f_radio = QtWidgets.QRadioButton("F")
        self.front_b_radio = QtWidgets.QRadioButton("B")
        self.front_none_radio.setChecked(True)
        front_layout.addWidget(self.front_none_radio)
        front_layout.addWidget(self.front_f_radio)
        front_layout.addWidget(self.front_b_radio)
        front_group.setLayout(front_layout)

        # Filtering Radio Buttons
        filtering_group = QtWidgets.QGroupBox("Filtering:")
        filtering_layout = QtWidgets.QVBoxLayout()
        self.filter_blank_radio = QtWidgets.QRadioButton("(Blank)")
        self.filter_underBar_radio = QtWidgets.QRadioButton("_")
        self.filter_blank_radio.setChecked(True)
        filtering_layout.addWidget(self.filter_blank_radio)
        filtering_layout.addWidget(self.filter_underBar_radio)
        filtering_group.setLayout(filtering_layout)

        # Result
        result_label = QtWidgets.QLabel("Result:")
        self.result_edit = QtWidgets.QLineEdit("Bip001 TempBone 0")
        self.result_edit.setReadOnly(True) # Make result read-only

        # OK/Cancel Buttons
        self.ok_button = QtWidgets.QPushButton("OK")
        self.cancel_button = QtWidgets.QPushButton("Cancel")

        # Arrange Widgets in Grid Layout
        grid_layout.addWidget(base_name_label, 0, 0)
        grid_layout.addWidget(self.base_name_edit, 0, 1)
        grid_layout.addWidget(self.base_name_combo, 1, 1) # Dropdown below Base Name
        grid_layout.addWidget(name_label, 2, 0)
        grid_layout.addWidget(self.name_edit, 2, 1)

        # Arrange Radio Button Groups
        radio_button_layout.addWidget(side_group)
        radio_button_layout.addWidget(front_group)
        radio_button_layout.addWidget(filtering_group)

        # Arrange Buttons
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        # Add layouts to main layout
        main_layout.addLayout(grid_layout)
        main_layout.addLayout(radio_button_layout)
        main_layout.addWidget(result_label)
        main_layout.addWidget(self.result_edit)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Connect signals
        self.ok_button.clicked.connect(self.ok_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        
        # Connect all relevant UI changes to the update method
        self.base_name_combo.currentTextChanged.connect(self.update_ui)
        self.name_edit.textChanged.connect(self.update_ui)
        self.side_none_radio.toggled.connect(self.update_ui)
        self.side_l_radio.toggled.connect(self.update_ui)
        self.side_r_radio.toggled.connect(self.update_ui)
        self.front_none_radio.toggled.connect(self.update_ui)
        self.front_f_radio.toggled.connect(self.update_ui)
        self.front_b_radio.toggled.connect(self.update_ui)
        self.filter_blank_radio.toggled.connect(self.update_ui)
        self.filter_underBar_radio.toggled.connect(self.update_ui)
        
        self.update_ui()  # Initial update to set the result field
        
    def update_ui(self):
        self.base_name_edit.setText(self.base_name_combo.currentText())
        self.baseName = self.base_name_edit.text()
        
        if self.side_none_radio.isChecked():
            self.sideName = ""
        elif self.side_l_radio.isChecked():
            self.sideName = "L"
        elif self.side_r_radio.isChecked():
            self.sideName = "R"
        
        if self.front_none_radio.isChecked():
            self.frontBackName = ""
        elif self.front_f_radio.isChecked():
            self.frontBackName = "F"
        elif self.front_b_radio.isChecked():
            self.frontBackName = "B"
        
        RealName = self.name_edit.text() if self.name_edit.text() != "" else "TempBone"
        
        if self.filter_blank_radio.isChecked():
            self.filteringChar = " "
        elif self.filter_underBar_radio.isChecked():
            self.filteringChar = "_"
        
        finalName = jal.name.combine(
            inPartsDict={
                "Base":self.baseName, 
                "Type":"", 
                "Side":self.sideName, 
                "FrontBack":self.frontBackName,
                "RealName":RealName,
                "Index":"00"
            }, 
            inFilChar=self.filteringChar
        )
        self.result_edit.setText(finalName)
        self.boneName = finalName
    
    def ok_clicked(self):
        self.update_ui()
        
        existingBoneNum = 0
        nameCheckBoneArray = [item for item in rt.objects if rt.classOf(item) == rt.BoneGeometry]
        namePattern = jal.name.get_string(self.boneName) + self.filteringChar
        for item in nameCheckBoneArray:
            if (item.name.startswith(namePattern)):
                existingBoneNum += 1
        
        if existingBoneNum > 0:
            QtWidgets.QMessageBox.warning(None, "Warning", "Same Name Bone Exist!")
            self.boneNameSetted = False
        else:
            self.boneNameSetted = True
            self.accept()
    
    def cancel_clicked(self):
        self.boneNameSetted = False
        self.reject()

class BoneSizeDialog(QtWidgets.QDialog):
    def __init__(self, parent=QtWidgets.QWidget.find(rt.windows.getMAXHWND())):
        super().__init__(parent)
        self.setWindowTitle("Bone Size")
        self.setMinimumWidth(300)
        
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        
        # UI 변수들 초기화
        self.fin_on = True
        self.fin_size = 2.0
        self.bone_size = 2.0
        self.bone_taper = 90.0
        
        # 원래 본 모양 저장용 변수들
        self.original_bone_shapes = {}  # {본객체: 원래모양배열}
        self.original_selection = []    # 원래 선택된 본들
        
        # Layouts
        main_layout = QtWidgets.QVBoxLayout(self)
        fin_layout = QtWidgets.QHBoxLayout()
        bone_layout = QtWidgets.QHBoxLayout()
        button_layout = QtWidgets.QHBoxLayout()
        
        # Fin On 체크박스와 Fin Size 스피너 (가로로 배치)
        self.fin_on_checkbox = QtWidgets.QCheckBox("Fin On")
        self.fin_on_checkbox.setChecked(self.fin_on)
        fin_layout.addWidget(self.fin_on_checkbox)
        
        fin_layout.addWidget(QtWidgets.QLabel("Fin Size:"))
        
        self.fin_size_spinner = QtWidgets.QDoubleSpinBox()
        self.fin_size_spinner.setRange(0.0, 100.0)
        self.fin_size_spinner.setValue(self.fin_size)
        self.fin_size_spinner.setDecimals(1)
        self.fin_size_spinner.setSingleStep(0.1)
        fin_layout.addWidget(self.fin_size_spinner)
        
        # Bone Size와 Bone Taper 스피너 (가로로 배치)
        bone_layout.addWidget(QtWidgets.QLabel("Bone Size:"))
        
        self.bone_size_spinner = QtWidgets.QDoubleSpinBox()
        self.bone_size_spinner.setRange(0.0, 100.0)
        self.bone_size_spinner.setValue(self.bone_size)
        self.bone_size_spinner.setDecimals(1)
        self.bone_size_spinner.setSingleStep(0.1)
        bone_layout.addWidget(self.bone_size_spinner)
        
        bone_layout.addWidget(QtWidgets.QLabel("Bone Taper:"))
        
        self.bone_taper_spinner = QtWidgets.QDoubleSpinBox()
        self.bone_taper_spinner.setRange(0.0, 100.0)
        self.bone_taper_spinner.setValue(self.bone_taper)
        self.bone_taper_spinner.setDecimals(1)
        self.bone_taper_spinner.setSingleStep(0.1)
        bone_layout.addWidget(self.bone_taper_spinner)
        
        # OK/Cancel Buttons
        self.ok_button = QtWidgets.QPushButton("OK")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        
        # Arrange Buttons
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Add layouts to main layout
        main_layout.addLayout(fin_layout)
        main_layout.addLayout(bone_layout)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.ok_button.clicked.connect(self.ok_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        
        # Connect all relevant UI changes to the update method
        self.fin_on_checkbox.toggled.connect(self.update_ui)
        self.fin_size_spinner.valueChanged.connect(self.update_ui)
        self.bone_size_spinner.valueChanged.connect(self.update_ui)
        self.bone_taper_spinner.valueChanged.connect(self.update_ui)
        
        # 초기 선택된 본들의 원래 모양 저장
        self.save_original_bone_shapes()
        
        self.update_ui()  # Initial update
        
    def save_original_bone_shapes(self):
        """선택된 본들의 원래 모양을 저장합니다."""
        selObjs = rt.getCurrentSelection()
        for item in selObjs:
            if rt.classOf(item) == rt.BoneGeometry:
                self.original_selection.append(item)
                self.original_bone_shapes[item] = jal.bone.get_bone_shape(item)
    
    def restore_original_bone_shapes(self):
        """저장된 원래 모양으로 본들을 되돌립니다."""
        for item, shape_array in self.original_bone_shapes.items():
            if rt.isValidObj(item):
                jal.bone.pasete_bone_shape(item, shape_array)
        rt.redrawViews()
        
    def update_ui(self):
        """UI 값들을 업데이트합니다."""
        self.fin_on = self.fin_on_checkbox.isChecked()
        self.fin_size = self.fin_size_spinner.value()
        self.bone_size = self.bone_size_spinner.value()
        self.bone_taper = self.bone_taper_spinner.value()
        
        # Fin On 상태에 따라 Fin Size 스피너 활성화/비활성화
        self.fin_size_spinner.setEnabled(self.fin_on)
        
        selObjs = rt.getCurrentSelection()
        for item in selObjs:
            if self.fin_on:
                jal.bone.set_fin_on(item, inSize=self.fin_size)
            else:
                jal.bone.set_fin_off(item)
            jal.bone.set_bone_size(item, self.bone_size)
            jal.bone.set_bone_taper(item, self.bone_taper)
        
        rt.redrawViews()
        
    def ok_clicked(self):
        """OK 버튼 클릭 처리"""
        self.update_ui()
        self.accept()
    
    def cancel_clicked(self):
        """Cancel 버튼 클릭 처리"""
        # 원래 모양으로 되돌리기
        self.restore_original_bone_shapes()
        self.reject()
        

def jal_bone_on():
    jal.bone.set_bone_on_selection()

def jal_bone_off():
    jal.bone.set_bone_off_selection()

def jal_bone_length_freeze_on():
    jal.bone.set_freeze_length_on_selection()

def jal_bone_length_freeze_off():
    jal.bone.set_freeze_length_off_selection()

def jal_bone_fin_on():
    sel_array = rt.getCurrentSelection()
    if len(sel_array) > 0:
        for item in sel_array:
            jal.bone.set_fin_on(item)

def jal_bone_fin_off():
    sel_array = rt.getCurrentSelection()
    if len(sel_array) > 0:
        for item in sel_array:
            jal.bone.set_fin_off(item)

def jal_bone_reset_scale():
    sel_array = rt.getCurrentSelection()
    for item in sel_array:
        if rt.classOf(item) == rt.BoneGeometry:
            if item.children.count == 1:
                item.realignBoneToChild()
                jal.bone.correct_negative_stretch(item, True)
                item.ResetBoneStretch()
    
    jal.bone.reset_scale_of_selected_bones(True)

def jal_bone_create():
    selArray = rt.getCurrentSelection()
    simpleBoneLength = 5
        
    dialog = BoneNameDialog()
    result = dialog.exec_()
    
    # Store dialog values in external variables
    boneNameSetted = dialog.boneNameSetted
    boneName = dialog.boneName
    filteringChar = dialog.filteringChar
    
    # Now you can use boneNameSetted and boneName variables
    if boneNameSetted:
        if len(selArray) == 0 or len(selArray) == 1:
            genBoneArray = jal.bone.create_simple_bone(simpleBoneLength, boneName)
            for item in genBoneArray:
                item.name = jal.name.replace_filtering_char(item.name, filteringChar)
            if len(selArray) == 1:
                genBoneArray[0].transform = selArray[0].transform
        elif len(selArray) > 1:
            genBoneArray = jal.bone.create_bone(selArray, boneName, delPoint=True)
            for item in genBoneArray:
                item.name = jal.name.replace_filtering_char(item.name, filteringChar)
    
    # Explicitly delete the dialog and force garbage collection
    dialog.deleteLater()
    dialog = None
    gc.collect()  # Force garbage collection

def jal_bone_nub_create():
    sel_array = rt.getCurrentSelection()
    if len(sel_array) > 0:
        last_bone_array = []
        non_bone_array = []
        
        for item in sel_array:
            if rt.classOf(item) == rt.BoneGeometry:
                last_bone_array.append(item)
            else:
                non_bone_array.append(item)
        
        for item in last_bone_array:
            if item.children.count == 0:
                jal.bone.create_end_bone(item)
                
        for item in non_bone_array:
            jal.bone.create_nub_bone_on_obj(item)
    else:
        jal.bone.create_nub_bone("Temp", 2)

def jal_bone_size_modify():
    dialog = BoneSizeDialog()
    dialog.show()
    
    # 다이얼로그가 닫힐 때까지 대기하지 않고 즉시 반환
    # 사용자가 다이얼로그를 닫으면 자동으로 정리됨

# Register macroscripts
macroScript_Category = "jalTools"

rt.jal_bone_on = jal_bone_on
rt.macros.new(
    macroScript_Category,
    "jal_boneOn",
    "Bone On Selection",
    "Bone On Selection",
    "jal_bone_on()"
)

rt.jal_bone_off = jal_bone_off
rt.macros.new(
    macroScript_Category,
    "jal_boneOff",
    "Bone Off Selection",
    "Bone Off Selection",
    "jal_bone_off()"
)

rt.jal_bone_length_freeze_on = jal_bone_length_freeze_on
rt.macros.new(
    macroScript_Category,
    "jal_boneLengthFreezeOn",
    "Bone Length Freeze On Selection",
    "Bone Length Freeze On Selectionn",
    "jal_bone_length_freeze_on()"
)

rt.jal_bone_length_freeze_off = jal_bone_length_freeze_off
rt.macros.new(
    macroScript_Category,
    "jal_boneLengthFreezeOff",
    "Bone Length Freeze Off Selection",
    "Bone Length Freeze Off Selection",
    "jal_bone_length_freeze_off()"
)

rt.jal_bone_fin_on = jal_bone_fin_on
rt.macros.new(
    macroScript_Category,
    "jal_boneFinOn",
    "Bone Fin On",
    "Bone Fin On",
    "jal_bone_fin_on()"
)

rt.jal_bone_fin_off = jal_bone_fin_off
rt.macros.new(
    macroScript_Category,
    "jal_boneFinOff",
    "Bone Fin Off",
    "Bone Fin Off",
    "jal_bone_fin_off()"
)

rt.jal_bone_reset_scale = jal_bone_reset_scale
rt.macros.new(
    macroScript_Category,
    "jal_boneResetScale",
    "Bone Reset Scale",
    "Bone Reset Scale",
    "jal_bone_reset_scale()"
)

rt.jal_bone_create = jal_bone_create
rt.macros.new(
    macroScript_Category,
    "jal_boneCreate",
    "Bone Create",
    "Bone Create",
    "jal_bone_create()"
)

rt.jal_bone_nub_create = jal_bone_nub_create
rt.macros.new(
    macroScript_Category,
    "jal_boneNubCreate",
    "Bone Nub Create",
    "Bone Nub Create",
    "jal_bone_nub_create()"
)

rt.jal_bone_size_modify = jal_bone_size_modify
rt.macros.new(
    macroScript_Category,
    "jal_boneSizeModify",
    "Bone Size Modify",
    "Bone Size Modify",
    "jal_bone_size_modify()"
)