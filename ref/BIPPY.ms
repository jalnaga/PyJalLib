------------------------------------------------------
--		 	  		 BIPPY						--
-- 		 	Created by Geoffrey Samuel			--
--	  	    Email: Geoff@geoffsamuel.com		--
--	  	   Website: www.geoffsamuel.com		--
--				   (Version 1.97)					--
------------------------------------------------------
------------------------------------------------------
------------------------------------------------------
/* LEGAL AND COPYRIGHT  INFO
------------------------------------------------------
Copyright (c) 2007-2010, Geoff Samuel
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

------------------------------------------------------
/* OTHER  INFO
------------------------------------------------------

It would be appreciate if the author could be informed to the use of the plugin/tool/code as to promote the usage of the plugin/tool/code. 
Any modifications done to the plugin/tool/code for improved functionality or stability would be welcome as keep building off a single plugin/tool/code allowing for more people to benefit, 
although this is not mandatory. 

Bugs and feature requests to: Support@GeoffSamuel.com

------------------------------------------------------
/* BUILD AND VERSION INFO
------------------------------------------------------

Build date: 06/04/2011


Further features to be implemented: (build version 2.0)
* T-Pose Matching
* "Linking"
* Bone saw re-impleneted
* Implemenation of the Conform to BIP Vicon Blade Tool
* Linking of Vicon Blade Tools to the batch options
* Use of the prefix tool on batch

Version History: (build version 1.97)
* Adding the ablity to load in a pre-configured .FIG file instead of autocreation.
* Ablity to save out the current loaded file.
* Fixed Motion Builder naming convention
* Added Icon for UI
* Bug Fixes

Version History: (build version 1.9)
* Saving and loading of user defined bone labels
* Steamline biped creation and resizing
* removed redundant functions
* reduced hardcoded biped parts with dynamic file driven approaches

Version History: (build version 1.8)
* Bases of KARl (Keyframe Reduction algrothim) implemented, not fully working
* Unlinked Bone Saw, in need of overhaul, doesnt work properly
* Logo Added and UI Tweaked

Version History: (build version 1.5)
* Vicon Blade tools (Remove Namespace & Fix Flips) added
* Converted from a C++ plugin to a Maxscript plugin with a %5 speed increase on per frame copy
* Added ablity to chose to copy keyframes or keyframe each frame

Version History: (build version 1.0)
* Released to University of Portsmouth Motion Capture team for testing
* Added Bone saw features
* Feet calculated differently
* Converted into C++ Plugin

Version History: (build version 0.6)
* Bug fixes (Batch options, timeline issues)

Version History: (build version 0.5)
* Added Batch options
* Tweaked bone to bone conversions formular
* Added preset names

Version History: (build version 0.1)
* Added UI for standard options
* Automaticly create and re-size a biped based off the fbx bones
* Implemented bone to bone conversions
* Project Started.

*/


max unhide all


struct FBX_converter_struct (
FBX_array = #(), --holds the orignal FBX bone data
FBX_Name_Array = #(),
retarget_array = #(), --holds the new biped bone data
use_bone_detach = false, --use of the bone detach feacture is off until it is turned on
use_batch = false, --use of the batch feacture is off until it is turned on
batch_SaveFirst_File = false,
batch_SaveFirst_Name = "",
number_of_bones_found = 0, --a veribal to count the number of biped bones found
bipObj, --veribal to hold the new biped
biped_ctrl, -- holds the control rig for the biped
frame_START = 0, --global veribal to hold the start frame
frame_STOP = 0, --global veribal to hold the finish frame
rows=#(),		--Empty array to collect FBX_convert_str.rows of data
Bones_to_transfer = #(),
boneNum,
Input_dir = "",
Output_dir= "",
theFiles ,
FilesToBatch =#(),
FileNamesToBatch =#(),
FileNames = #(),
FBX_Check_array = #(),

using_Own_FIG = false,
Fig_File = "",

keyframe_Method = 2,
KRAL_Toerance,
Number_of_files = 1, --used in the batch, min number of files is 1. total number of files going through the batch
current_FRAME_number,  --the current frame being processed
current_FILE_number = 1,--the number of the file going through the batch

convert_rollout,
ConverterFloater,
right_ankle,
left_ankle,

progbar,

Blade_Tools_Remove_Namespace_BATCH = false,
Blade_Tools_Fix_Flips_BATCH = false,
Blade_Tools_Cornform_To_Biped_BATCH = false,

fn Blade_Tools_Remove_Namespace = (

		obj = (objects as array)	
		for i in obj do(
		local temp = i.name
		local new = filterString temp ":"
		if new.count != 1 do(
		i.name = new[2]
		)
	)
),
	fn Blade_Tools_Fixer frameNum = (
		q1 = q2 = quat 0 0 0 0
		p1 = p2 = point3 0 0 0 
		at time (frameNum - 1)(
			q1 = obj.Rotation
			p1 = obj.pos
		)

		at time (frameNum + 1) (
			q2 = obj.Rotation
			p2 = obj.pos
		)
		
		keys =  obj.Rotation.Controller.keys
		u=1
		while(u< keys.count)do(
			if(keys[u].time > frameNum - 1) and (keys[u].time < frameNum + 1) do(
				deleteItem keys u
				u-=1
			)	
			u+=1
		)
		
		
		
		at time frameNum (
			animate on(
				obj.Rotation = quat ((q1.x+q2.x)/2) ((q1.y+q2.y)/2) ((q1.z+q2.z)/2) ((q1.w+q2.w)/2)
				obj.pos = (p1+p2)/2
			)
		)
	),




fn Blade_Tools_Fix_Flips = (

	obj = $Hips
	--gets the first frame of the active time
	anim_Start = ((animationRange.start as float/ TicksPerFrame )as Integer)+1
	--gets the last frame of the active time
	anim_End = ((animationRange.end) as float / TicksPerFrame)as Integer

	fix_array = #()
	for g = anim_Start to anim_End do(
		f = g-1
		tB = tP = tF = quat 0 0 0 0
		at time (f-1) (
			tB = obj.Rotation
		)
		at time f (
			tP = obj.Rotation
		)
		at time (f+1) (
			tF = obj.Rotation
		)
		tBP = quat (tB.x - tP.x) (tB.y - tP.y) (tB.z - tP.z) (tB.w - tP.w)
		--tPF = quat (tP.x - tF.x) (tP.y - tF.y) (tP.z - tF.z) (tP.w - tF.w)
		--tBF = quat (tB.x - tF.x) (tB.y - tF.y) (tB.z - tF.z) (tB.w - tF.w)
		
		if(abs(tBP.x) > 0.2) or (abs(tBP.y) > 0.2) or (abs(tBP.z) > 0.2) or (abs(tBP.w) > 0.2) do(
			if (findItem fix_array (f-1) == 0) do(
				append fix_array f
			)
		)
	)

	for f = 1 to fix_array.count do(
		Blade_Tools_Fixer fix_array[f]
	)
	
),
fn Blade_Tools_Cornform_To_Biped = (
)
)
global lv_objects
FBX_convert_str = FBX_converter_struct()

fn clean_up_array old_array =
(
	do (																		
		num = undefined																--define "num" as undefined for each loop so we can break out of the do while loop if it returns as undefined after the operations
		num = findItem old_array undefined									--defines "num" as the character number that the Findstring finds a \ within string_text, so we can replace that with a //
		if num != 0 do (
			deleteItem old_array num					--replaces the \ with a //
		)
	)While num != 0
	return old_array
)

rollout about_rollout "About" width:318 height:700
(
	label lbl21 "Designed and created by Geoff Samuel" pos:[60,92] width:192 height:17
	label lbl22 "Email: Geoff@GeoffSamuel.com " pos:[78,107] width:157 height:17
	label lbl23 "Website: www.GeoffSamuel.com " pos:[76,108] width:160 height:17
	label lbl17 "Version:" pos:[235,190] width:41 height:14
	label lbl18 "1.97" pos:[276,190] width:35 height:16
	bitmap bmp1 "Bitmap" pos:[5,6] width:301 height:74 fileName:(getDir #userscripts + "\\Bippy/bipp.bmp")
)
rollout batch_rollout "Batch options" width:318 height:700
(
	
	GroupBox grp1 "Batch Options" pos:[5,4] width:303 height:242
	checkbox batch_checkbox "Batch On" pos:[14,1] width:73 height:21
	edittext textbox_input_dir "" pos:[7,41] width:293 height:17 enabled:false
	button button_input_dir "Change Input path" pos:[189,17] width:112 height:18 enabled:false
	label label_input "Input Directory" pos:[13,24] width:72 height:14 enabled:false
	edittext textbox_Output_dir "" pos:[7,223] width:294 height:17 enabled:false
	button button_Output_dir "Change Output path" pos:[186,202] width:115 height:18 enabled:false
	label label_output "Output Directory" pos:[14,205] width:82 height:14 enabled:false
	
	multiListBox FBX_multilistbox "FBX files in input directory:" pos:[11,64] width:286 height:7 enabled:false
	button Select_all "Select All" pos:[9,179] width:95 height:17 enabled:false
	button Select_inverted "Select Inverted" pos:[108,179] width:95 height:17 enabled:false
	button Select_none "Select None" pos:[206,179] width:95 height:17 enabled:false
		
	GroupBox grp2 "" pos:[4,249] width:303 height:66 enabled:false
	checkbox saveFileCheckbox "Save Current Open File" pos:[11,249] width:140 height:15 enabled:false
	editText SaveFileAsEditText "" pos:[9,287] width:289 height:17 enabled:false
	label lbl3 "File Name:" pos:[15,270] width:194 height:15 enabled:false
	fn batch_enable bool = (
			FBX_convert_str.use_batch = bool
		FBX_convert_str.batch_SaveFirst_File = saveFileCheckbox.state
			FBX_multilistbox.enabled = bool
			label_output.enabled = bool
			button_Output_dir.enabled = bool
			textbox_Output_dir.enabled = bool
			label_input.enabled = bool
			button_input_dir.enabled = bool
			textbox_input_dir.enabled = bool
			Select_all.enabled = bool
			Select_inverted.enabled = bool
			Select_none.enabled = bool
		grp2.enabled = saveFileCheckbox.state
		saveFileCheckbox.enabled = bool
		SaveFileAsEditText.enabled = saveFileCheckbox.state
		lbl3.enabled = saveFileCheckbox.state
	)
	
	
			fn update_files_to_batch_names = (
			FBX_convert_str.FileNamesToBatch =#();
			count = FBX_convert_str.FilesToBatch.count 
			for p = 1 to count do(
				string_text = FBX_convert_str.FilesToBatch[p] 										--makes a string varibale with the text in the mesh_path edit text box
				do (																		
				num = undefined																--define "num" as undefined for each loop so we can break out of the do while loop if it returns as undefined after the operations
				num = findString string_text "\\"											--defines "num" as the character number that the Findstring finds a \ within string_text, so we can replace that with a //
					if num != undefined do (
				string_text = replace string_text num 1 "/"							--replaces the \ with a //
					)
				)While num != undefined													--continue looping while there is still a \ in the string_text
				
			strings = filterString string_text "'/"											--creates an array filled with string_text, where each array cotains a bit of the string bewteen the /
			FBX_convert_str.FileNamesToBatch[p] = strings[strings.count]	
			)
		)
	
	
	fn convert_files_to_batch = (
		FBX_convert_str.FilesToBatch= #()
		for i = 1 to FBX_multilistbox.selection.count do(
		if FBX_multilistbox.selection[i] == true do(
			append FBX_convert_str.FilesToBatch FBX_convert_str.theFiles[i]
			)
		)
		update_files_to_batch_names()
	)
	
	
		fn update_mulit_select = (
			FBX_convert_str.theFiles = getFiles (textbox_input_dir.text+"\\*.fbx") --collect all max files in the dir.
			FBX_convert_str.FileNames=#()
			count = FBX_convert_str.theFiles.count 
			for p = 1 to count do(
				string_text = FBX_convert_str.theFiles[p] 										--makes a string varibale with the text in the mesh_path edit text box
				do (																		
				num = undefined																--define "num" as undefined for each loop so we can break out of the do while loop if it returns as undefined after the operations
				num = findString string_text "\\"											--defines "num" as the character number that the Findstring finds a \ within string_text, so we can replace that with a //
					if num != undefined do (
				string_text = replace string_text num 1 "/"							--replaces the \ with a //
					)
				)While num != undefined													--continue looping while there is still a \ in the string_text
				
			strings = filterString string_text "'/"											--creates an array filled with string_text, where each array cotains a bit of the string bewteen the /
			FBX_convert_str.FileNames[p] = strings[strings.count]	
			)
			FBX_multilistbox.items = FBX_convert_str.FileNames
		)
		
		on saveFileCheckbox changed theState do
	(
		if FBX_convert_str.batch_SaveFirst_File == false then (
			---OFF to ON
			batch_enable true
		)else(
			---ON to OFF
			batch_enable false
			)
		)	
	

	on batch_checkbox changed theState do
	(
		if FBX_convert_str.use_batch == false then (
			---OFF to ON
			batch_enable true
		)else(
			---ON to OFF
			batch_enable false
			)
		)
	on SaveFileAsEditText changed  text do
	(
		FBX_convert_str.batch_SaveFirst_Name = SaveFileAsEditText.text
	)
	on textbox_input_dir changed  text do
	(
		update_mulit_select()
		
		FBX_convert_str.Input_dir = textbox_input_dir.text
	)
	on button_input_dir pressed do
	(
			Inpath = getSavePath()
			if Inpath != undefined do --if the user did not cancel
			(
				textbox_input_dir.text = Inpath
				update_mulit_select()
				FBX_convert_str.Input_dir = textbox_input_dir.text
				textbox_Output_dir.text = Inpath
			)
	)
	on textbox_Output_dir entered text do
	(
			FBX_convert_str.Output_dir = textbox_Output_dir.text
		)
	on button_Output_dir pressed do
	(
		Outpath =  getSavePath()
		if Outpath != undefined do --if the user did not cancel
			(
				textbox_Output_dir.text =Outpath
				FBX_convert_str.Output_dir = textbox_Output_dir.text
			)
	)
	on FBX_multilistbox selected val do
	(
			convert_files_to_batch()
			)
	on Select_all pressed do
	(
			local number_array =#()
			for i = 1 to FBX_multilistbox.items.count do (
			 number_array[i] = i
			)
			FBX_multilistbox.selection =number_array
			convert_files_to_batch()
		)
	on Select_inverted pressed do
	(
			local number_array =#()
			for i = 1 to FBX_multilistbox.items.count do (
			num = findItem (FBX_multilistbox.selection) i
				if num == 0 do (
					append  number_array i
				)
			)
			FBX_multilistbox.selection =number_array
			convert_files_to_batch()
		)
	on Select_none pressed do
	(
			FBX_multilistbox.selection =#{}
			convert_files_to_batch()
		)
)
rollout Bone_detachting_rollout "Bone detaching and reataching" width:221 height:700
(
	GroupBox grp1 "Bone Root 1" pos:[8,160] width:204 height:85
	checkbox Bone_root_1_on "Use" pos:[14,175] width:43 height:14
	dropdownList Bone_root_1_DDL "Bone root to copy over" pos:[17,195] width:181 height:40

	GroupBox grp2 "Bone Root 2" pos:[8,250] width:204 height:85
	checkbox Bone_root_2_on "Use" pos:[14,265] width:43 height:14
	dropdownList Bone_root_2_DDL "Bone root to copy over" pos:[17,285] width:181 height:40

	GroupBox grp3 "Bone Root 3" pos:[8,343] width:204 height:85
	checkbox Bone_root_3_on "Use" pos:[14,358] width:43 height:14
	dropdownList Bone_root_3_DDL "Bone root to copy over" pos:[17,378] width:181 height:40

	GroupBox grp4 "Bone Root 4" pos:[8,435] width:204 height:85
	checkbox Bone_root_4_on "Use" pos:[14,450] width:43 height:14
	dropdownList Bone_root_4_DDL "Bone root to copy over" pos:[17,470] width:181 height:40

	GroupBox grp5 "Bone Root 5" pos:[8,528] width:204 height:85
	checkbox Bone_root_5_on "Use" pos:[14,543] width:43 height:14
	dropdownList Bone_root_5_DDL "Bone root to copy over" pos:[17,563] width:181 height:40
	GroupBox grp6 "About" pos:[8,9] width:204 height:146
	label lbl1 "The Bone Deataching and Reataching tool will line up a new biped with the current bone data, at which point it will re-parent the chosen bones to their biped equliviant.You are allowed upto 5 bone detachtings." pos:[17,25] width:185 height:80
	label lbl2 "To use, just turn on the bone root number and select the bone you want to operate on." pos:[16,109] width:186 height:41

fn Get_dropdown_list = (
	bone_parts = #()
	try (
	bip_parts = (execute ("$'"+FBX_convert_str.FBX_array[1].name+"'...*"))
		bone_parts[1] = FBX_convert_str.FBX_array[1].name
		for y= 2 to bip_parts.count do (
			bone_parts[y] = bip_parts[y].name as string
		)
	)catch (bone_parts[1] = "NO BONES")
		return bone_parts
)--FBX_convert_str.Bones_to_transfer

	on Bone_root_1_on changed state do
	(
		if Bone_root_1_on.state == false do (
			FBX_convert_str.Bones_to_transfer[1]= undefined
		)
		list = Get_dropdown_list()
				Bone_root_1_DDL.items = list
	
		)
		
	on Bone_root_1_DDL selected sel do
(
	if Bone_root_1_on.state == true do(
		
	FBX_convert_str.Bones_to_transfer[1] = FBX_convert_str.FBX_array[( findItem  FBX_convert_str.FBX_Name_Array Bone_root_1_DDL.selected )]
		)
	)
	
	
	
	on Bone_root_2_on changed state do
	(
		if Bone_root_2_on.state == false do (
			FBX_convert_str.Bones_to_transfer[2]= undefined
		)
		list = Get_dropdown_list()
				Bone_root_2_DDL.items = list
		)
		
	on Bone_root_2_DDL selected sel do
(
		if Bone_root_2_on.state == true do(
	FBX_convert_str.Bones_to_transfer[2] = FBX_convert_str.FBX_array[( findItem  FBX_convert_str.FBX_Name_Array Bone_root_2_DDL.selected )]
		)
	)
	
	
	
	on Bone_root_3_on changed state do
	(
		if Bone_root_3_on.state == false do (
			FBX_convert_str.Bones_to_transfer[3]= undefined
		)
		list = Get_dropdown_list()
				Bone_root_3_DDL.items = list
		)
		
			on Bone_root_2_DDL selected sel do
(
		if Bone_root_3_on.state == true do(
	FBX_convert_str.Bones_to_transfer[3] = FBX_convert_str.FBX_array[( findItem  FBX_convert_str.FBX_Name_Array Bone_root_3_DDL.selected )]
		)
	)
	
	
	on Bone_root_4_on changed state do
	(
		if Bone_root_4_on.state == false do (
			FBX_convert_str.Bones_to_transfer[4]= undefined
		)
		list = Get_dropdown_list()
				Bone_root_4_DDL.items = list
		)
		
			on Bone_root_4_DDL selected sel do
(
		if Bone_root_4_on.state == true do(
	FBX_convert_str.Bones_to_transfer[4] = FBX_convert_str.FBX_array[( findItem  FBX_convert_str.FBX_Name_Array Bone_root_4_DDL.selected )]
		)
	)
	
	
	on Bone_root_5_on changed state do
	(
		if Bone_root_5_on.state == false do (
			FBX_convert_str.Bones_to_transfer[5]= undefined
		)
		list = Get_dropdown_list()
			Bone_root_5_DDL.items = list
		)
		
			on Bone_root_5_DDL selected sel do
(
		if Bone_root_5_on.state == true do(
	FBX_convert_str.Bones_to_transfer[5] = FBX_convert_str.FBX_array[( findItem  FBX_convert_str.FBX_Name_Array Bone_root_5_DDL.selected )]
		)
	)
)
fn start_prog_bar = (

	FBX_convert_str.progbar.NewBar "BIPPY" (FBX_convert_str.frame_START as string) 0
	FBX_convert_str.progbar.Refresh()
)
fn close_prog_bar = (
	FBX_convert_str.progbar.Close_Bar()
)
fn update_prog_bar = (
	p1 = FBX_convert_str.current_FRAME_number as float
	p2 = FBX_convert_str.frame_STOP as float
	FBX_convert_str.progbar.Update_Bar ((p1/p2) * 100)
)
fn assess_and_create_biped = 
(
	bip_height = (distance FBX_convert_str.FBX_array[140] FBX_convert_str.FBX_array[13])*1.8
	--makes a new biped with the calculated height
	number_of_spines = 0
	for c = 3 to 12 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_spines += 1
		)
	)

	number_of_legs = 0
	for c = 137 to 140 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_legs+=1
		)
	)
		
	number_of_tails = 0
	for c = 165 to 189 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_tails+=1
		)
	)
		
	number_of_ponytails1 = 0
	for c = 39 to 63 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_ponytails1+=1
		)
	)
		
	number_of_necks = 0
	for c = 13 to 37 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_necks+=1
		)
	)
		
	number_of_ponytails2 = 0
	for c = 64 to 88 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_ponytails2+=1
		)
	)		
		
	number_of_fingers = 0
	
	if FBX_convert_str.FBX_array[93] != undefined do(
		number_of_fingers+=1
	)
	if FBX_convert_str.FBX_array[97] != undefined do(
		number_of_fingers+=1
	)
	if FBX_convert_str.FBX_array[101] != undefined do(
		number_of_fingers+=1
	)
	if FBX_convert_str.FBX_array[105] != undefined do(
		number_of_fingers+=1
	)
	if FBX_convert_str.FBX_array[109] != undefined do(
		number_of_fingers+=1
	)

	number_of_fingerlinks = 1
	for c = 95 to 96 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_fingerlinks+=1
		)
	)
	number_of_toes = 0
	if FBX_convert_str.FBX_array[141] != undefined do(
		number_of_toes+=1
	)
	if FBX_convert_str.FBX_array[144] != undefined do(
		number_of_toes+=1
	)
	if FBX_convert_str.FBX_array[147] != undefined do(
		number_of_toes+=1
	)
	if FBX_convert_str.FBX_array[150] != undefined do(
		number_of_toes+=1
	)
	if FBX_convert_str.FBX_array[153] != undefined do(
		number_of_toes+=1
	)
			
	number_of_toelinks = 0
	for c = 141 to 143 do (
		if FBX_convert_str.FBX_array[c] != undefined do(
			number_of_toelinks+=1
		)
	)
	number_of_prop1 = false
	if FBX_convert_str.FBX_array[200] != undefined do(
		number_of_prop1 = true
	)
	number_of_prop2 = false
	if FBX_convert_str.FBX_array[201] != undefined do(
		number_of_prop2 = true
	)
		
	number_of_prop3 = false
	if FBX_convert_str.FBX_array[202] != undefined do(
		number_of_prop3 = true
	)
	
		
	FBX_convert_str.bipObj = biped.createNew bip_height 0 [0,0,0] \
		spineLinks:number_of_spines legLinks:number_of_legs tailLinks:number_of_tails ponyTail1Links:number_of_ponytails1 neckLinks:number_of_necks ponyTail2Links:number_of_ponytails2  \
		fingers:number_of_fingers  fingerLinks:number_of_fingerlinks toes:number_of_toes toeLinks:number_of_toelinks prop1Exists:number_of_prop1 prop2Exists:number_of_prop2 prop3Exists:number_of_prop3

			
			
	local file = (getDir #userscripts + "\\Bippy/Bip.btf")
	local fileIO
	try(
		fileIO = openFile file
	)catch(
		messagebox "Cannot load file" "Bippy"
		return 0
	)		
	nam = FBX_convert_str.bipObj.name
	FBX_convert_str.retarget_array[1] = FBX_convert_str.bipObj
	for bI = 2 to FBX_convert_str.boneNum do(
		name_Temp = "$'"+nam+" "+(readLine fileIO)+"'"
		if FBX_convert_str.FBX_array[bI] != undefined do( 
				FBX_convert_str.retarget_array[bI] =temp = execute(name_Temp)
		)
	)
	flush fileIO
	close fileIO
)
fn resize_biped=(
	--rezises the biped for the file.
	FBX_convert_str.biped_ctrl=FBX_convert_str.bipObj.transform.controller
	FBX_convert_str.biped_ctrl.figureMode =  true
	biped.setTransform FBX_convert_str.retarget_array[1] #pos (FBX_convert_str.FBX_array[1].transform.pos) True
	biped.setTransform FBX_convert_str.retarget_array[1] #rotation (FBX_convert_str.FBX_array[1].transform.rotation) True	
	
	local temp =( distance FBX_convert_str.FBX_array[2] FBX_convert_str.FBX_array[137])*2
biped.setTransform FBX_convert_str.retarget_array[2] #scale ([temp,temp,temp]) True
	
	--Spine
	for i = 1 to 10 do(
		if FBX_convert_str.FBX_array[i+2] != undefined do( 
			if FBX_convert_str.FBX_array[i+3] != undefined then (
				local temp = distance FBX_convert_str.FBX_array[i+2] FBX_convert_str.FBX_array[i+3]
				biped.setTransform FBX_convert_str.retarget_array[i+2] #scale ([temp,temp,temp]) True
			)else(
				local temp = distance FBX_convert_str.FBX_array[i+2] FBX_convert_str.FBX_array[13]
				biped.setTransform FBX_convert_str.retarget_array[i+2] #scale ([temp,temp,temp]) True
			)
		)
	)		
	--Neck
	for i = 1 to 25 do(
		if FBX_convert_str.FBX_array[i+12] != undefined do( 
			if FBX_convert_str.FBX_array[i+13] != undefined then (
				local temp = distance FBX_convert_str.FBX_array[i+12] FBX_convert_str.FBX_array[i+13]
				biped.setTransform FBX_convert_str.retarget_array[i+12] #scale ([temp,temp,temp]) True
			)else(
				local temp = distance FBX_convert_str.FBX_array[i+12] FBX_convert_str.FBX_array[38]
				biped.setTransform FBX_convert_str.retarget_array[i+12] #scale ([temp,temp,temp]) True
			)
		)
	)		
	--Ponytail 1
	for i = 1 to 25 do(
		if FBX_convert_str.FBX_array[i+38] != undefined do( 
			if (FBX_convert_str.FBX_array[i+39] != undefined) and (FBX_convert_str.FBX_array[i+39].parent == FBX_convert_str.FBX_array[i+38]) then (
				local temp = distance FBX_convert_str.FBX_array[i+38] FBX_convert_str.FBX_array[i+39]
				biped.setTransform FBX_convert_str.retarget_array[i+38] #scale ([temp,temp,temp]) True
			)else(
				local temp = distance FBX_convert_str.FBX_array[i+37] FBX_convert_str.FBX_array[i+38]
				biped.setTransform FBX_convert_str.retarget_array[i+38] #scale ([temp,temp,temp]) True
			)
		)
	)	
	--Ponytail 2
	for i = 1 to 25 do(
		if FBX_convert_str.FBX_array[i+63] != undefined do( 
			if (FBX_convert_str.FBX_array[i+64] != undefined) and (FBX_convert_str.FBX_array[i+64].parent == FBX_convert_str.FBX_array[i+63]) then (
				local temp = distance FBX_convert_str.FBX_array[i+63] FBX_convert_str.FBX_array[i+64]
				biped.setTransform FBX_convert_str.retarget_array[i+63] #scale ([temp,temp,temp]) True
			)else(
				print "end of line"
				local temp = distance FBX_convert_str.FBX_array[i+62] FBX_convert_str.FBX_array[i+63]
				biped.setTransform FBX_convert_str.retarget_array[i+63] #scale ([temp,temp,temp]) True
			)
		)
	)

	--Left Arm
	for i = 1 to 3 do(
		local temp = distance FBX_convert_str.FBX_array[i+88] FBX_convert_str.FBX_array[i+89]
		biped.setTransform FBX_convert_str.retarget_array[i+88]#scale ([temp,temp,temp]) True
	)
	if FBX_convert_str.FBX_array[93] != undefined do( 
		local temp = distance FBX_convert_str.FBX_array[92] FBX_convert_str.FBX_array[93]
		biped.setTransform FBX_convert_str.retarget_array[92] #scale ([temp,temp,temp]) True
	)

	----LEFT FINGERS GO HERE
	
	
	--Right Arm
	for i = 1 to 3 do(
		local temp = distance FBX_convert_str.FBX_array[i+112] FBX_convert_str.FBX_array[i+113]
		biped.setTransform FBX_convert_str.retarget_array[i+112]#scale ([temp,temp,temp]) True
	)
	if FBX_convert_str.FBX_array[117] != undefined do( 
		local temp = distance FBX_convert_str.FBX_array[116] FBX_convert_str.FBX_array[117]
		biped.setTransform FBX_convert_str.retarget_array[116] #scale ([temp,temp,temp]) True
	)
	
		----RIGHT FINGERS GO HERE
	
	
	--Left Leg
	for i = 1 to 3 do(
		if FBX_convert_str.FBX_array[i+136] != undefined do( 
			if FBX_convert_str.FBX_array[i+137] != undefined then (
				local temp = distance FBX_convert_str.FBX_array[i+136] FBX_convert_str.FBX_array[i+137]
				biped.setTransform FBX_convert_str.retarget_array[i+136] #scale ([temp,temp,temp]) True
			)else(
				local temp = distance FBX_convert_str.FBX_array[i+136] FBX_convert_str.FBX_array[i+138]
				biped.setTransform FBX_convert_str.retarget_array[i+136] #scale ([temp,temp,temp]) True
			)
		)
	)
	
	--biped.setTransform FBX_convert_str.retarget_array[140] #scale ([(distance FBX_convert_str.FBX_array[140] left_ankle * distance FBX_convert_str.FBX_array[140] left_ankle),(distance  left_ankle FBX_convert_str.FBX_array[141]),(distance FBX_convert_str.FBX_array[140] FBX_convert_str.FBX_array[141])/2]) True

	--biped.setTransform FBX_convert_str.retarget_array[140] #scale ([(distance FBX_convert_str.FBX_array[140] left_ankle ),(distance  left_ankle FBX_convert_str.FBX_array[141])*1.2,(distance FBX_convert_str.FBX_array[140] FBX_convert_str.FBX_array[141])/2]) True
	
	local a = FBX_convert_str.FBX_array[141].pos
	local b = FBX_convert_str.FBX_array[140].pos
	local d = [b.x,b.y,a.z]
	local c = [a.x,a.y,b.z]
	local lenght = distance c b
	local height = distance b d--abs(a.z - b.z)
	--biped.setTransform FBX_convert_str.retarget_array[140] #scale ([height, lenght,lenght/3]) True
	
		----LEFT TOES GO HERE
	
	
	--Right Leg
	for i = 1 to 3 do(
		if FBX_convert_str.FBX_array[i+155] != undefined do( 
			if FBX_convert_str.FBX_array[i+156] != undefined then (
				local temp = distance FBX_convert_str.FBX_array[i+155] FBX_convert_str.FBX_array[i+156]
				biped.setTransform FBX_convert_str.retarget_array[i+155] #scale ([temp,temp,temp]) True
			)else(
				local temp = distance FBX_convert_str.FBX_array[i+155] FBX_convert_str.FBX_array[i+157]
				biped.setTransform FBX_convert_str.retarget_array[i+155] #scale ([temp,temp,temp]) True
			)
		)
	)
		
	--biped.setTransform FBX_convert_str.retarget_array[159] #scale ([(distance FBX_convert_str.FBX_array[159] right_ankle ),(distance  right_ankle FBX_convert_str.FBX_array[160])*1.2,(distance FBX_convert_str.FBX_array[159] FBX_convert_str.FBX_array[160])/2]) True
	local a = FBX_convert_str.FBX_array[160].pos
	local b = FBX_convert_str.FBX_array[159].pos
	local d = [b.x,b.y,a.z]
	local c = [a.x,a.y,b.z]
	local lenght = distance c b
	local height = distance b d--abs(a.z - b.z)
	--biped.setTransform FBX_convert_str.retarget_array[159] #scale ([height, lenght,lenght/3]) True
	----Right TOES GO HERE

	
	
	
	
biped.setTransform FBX_convert_str.retarget_array[3] #pos (FBX_convert_str.FBX_array[3].transform.pos) True
	
	
		local local_fbx_array = deepCopy  FBX_convert_str.FBX_array
	clean_up_array local_fbx_array
	
	local local_retarget_array = deepCopy FBX_convert_str.retarget_array
	clean_up_array local_retarget_array

	
	if(local_retarget_array.count != local_fbx_array.count) do(
		--messagebox "There are some features not supported by Biped, BIPPY will try its best to carry on." title:"BIPPY Warning"
		local_fbx_array = #()
		local_retarget_array = #()
		for i = 1 to FBX_convert_str.FBX_array.count do(
			if((FBX_convert_str.FBX_array[i] != undefined) and (FBX_convert_str.retarget_array[i] != undefined))do(
				local_fbx_array[i] = FBX_convert_str.FBX_array[i]
				local_retarget_array[i] = FBX_convert_str.retarget_array[i]
			)
			
		)
	clean_up_array local_fbx_array
	clean_up_array local_retarget_array
		
	)
	local_number_of_items = local_retarget_array.count
	
	
	
						for b = 1 to local_number_of_items do (
							--local_retarget_array[b].transform = local_fbx_array[b].transform		
							biped.setTransform local_retarget_array[b] #pos ( local_fbx_array[b].transform.pos) True
							biped.setTransform local_retarget_array[b] #rotation ( local_fbx_array[b].transform.rotation) True	
							biped.setTransform local_retarget_array[b] #pos ( local_fbx_array[b].transform.pos) True
							biped.setTransform local_retarget_array[b] #rotation ( local_fbx_array[b].transform.rotation) True	
						)
						
	FBX_convert_str.biped_ctrl.figureMode =  false	

	--delete left_ankle
	--delete right_ankle
	
)

fn Map_biped_to_FBX = 
(
--stops the screen from re-drawing
	if(FBX_convert_str.using_Own_FIG == false) then (
		assess_and_create_biped()
		resize_biped()	
	)
	else (
		assess_and_create_biped()
		Needed_Bones = 0
		Got_Bones = 0
		(
			local local_fbx_array = deepCopy  FBX_convert_str.FBX_array
			clean_up_array local_fbx_array
			Needed_Bones = local_fbx_array.count
		)
		FBX_convert_str.biped_ctrl=FBX_convert_str.bipObj.transform.controller
		FBX_convert_str.biped_ctrl.figureMode =  true
		try (
			biped.LoadFigFile FBX_convert_str.biped_ctrl FBX_convert_str.Fig_File
		)
		catch (
			messagebox "Can not read FIG File.\nFATAL ERROR" title:"BIPPY Warning"
			resize_biped()	
		)
		FBX_convert_str.biped_ctrl.figureMode =  false
		(
			local local_fbx_array = deepCopy  FBX_convert_str.FBX_array
			clean_up_array local_fbx_array
			Got_Bones = local_fbx_array.count
		)
		if (Got_Bones != Needed_Bones) then (
			messagebox "FIG File unknown match.\nFATAL ERROR" title:"BIPPY Warning"
			resize_biped()	
		)
	)
	--BONE TRANSPLANT
-------------------------------------Setting up Baking part
--sets the first frame of the active time 
anim_Start = animationRange.start
--sets the last frame of the active time
  	anim_End = animationRange.end
	--for loop between the first and last frame
	start_int = FBX_convert_str.frame_START as Integer
	stop_int = FBX_convert_str.frame_STOP as Integer
	
	bipctrl = FBX_convert_str.bipobj.transform.controller
	
	local local_fbx_array = deepCopy  FBX_convert_str.FBX_array
	clean_up_array local_fbx_array
	
	local local_retarget_array = deepCopy FBX_convert_str.retarget_array
	clean_up_array local_retarget_array

	
	if(local_retarget_array.count != local_fbx_array.count) do(
		if(use_batch != true)do(
			--messagebox "There are some features not supported by Biped, BIPPY will try its best to carry on." title:"BIPPY Warning"
		)
		local_fbx_array = #()
		local_retarget_array = #()
		for i = 1 to FBX_convert_str.FBX_array.count do(
			if((FBX_convert_str.FBX_array[i] != undefined) and (FBX_convert_str.retarget_array[i] != undefined))do(
				local_fbx_array[i] = FBX_convert_str.FBX_array[i]
				local_retarget_array[i] = FBX_convert_str.retarget_array[i]
			)
			
		)
	clean_up_array local_fbx_array
	clean_up_array local_retarget_array
		
	)
	local_number_of_items = local_retarget_array.count
	
	
	undo off (-- the undo has been turned off
		--starts animating
		start_prog_bar()
		try(
			For t = start_int  to stop_int Do
			(
				FBX_convert_str.current_FRAME_number = t as integer
				update_prog_bar()
				--sets the time to the loop incremation
				at time t (
					animate on(
						for b = 1 to local_number_of_items do (
							local_retarget_array[b].transform = local_fbx_array[b].transform		
						)
					gc()
					)
				)
			)
		)catch(
			close_prog_bar()
			messagebox "Opps, Something went wrong" title:"BIPPY ERROR"
		)
	--FBX_convert_str.Run_KeyFrameReduction()
	)--undo
	close_prog_bar()
)--function
rollout Blade_Tools_rollout "Vicon Blade Tools" width:318 height:246
(
	GroupBox grp4 "Batch Tools" pos:[11,144] width:286 height:93
	checkbox Batch_Namespace "Remove NameSpace" pos:[20,165] width:126 height:18
	checkbox Batch_Flips "Fix Flips" pos:[20,189] width:126 height:18
	checkbox Batch_BIP "Conform to BIP" pos:[20,213] width:126 height:18
	
	button Button_NameSpace "Remove NameSpace" pos:[15,11] width:286 height:30
	button Button_Flips "Fix Flips" pos:[15,54] width:286 height:30
	button Button_BIP "Confrom to BIP" pos:[15,101] width:286 height:30


	
	
	on Batch_Namespace changed state do
	(
			FBX_convert_str.Blade_Tools_Remove_Namespace_BATCH = state
		)
	on Batch_Flips changed state do
	(
			FBX_convert_str.Blade_Tools_Fix_Flips_BATCH = state
		)
	on Batch_BIP changed state do
	(
			FBX_convert_str.Blade_Tools_Cornform_To_Biped_BATCH = state
		)
	on Button_NameSpace pressed do
	(
			FBX_convert_str.Blade_Tools_Remove_Namespace()
		)
	on Button_Flips pressed do
	(
			FBX_convert_str.Blade_Tools_Fix_Flips()
		)
	on Button_BIP pressed do
	(
			FBX_convert_str.Blade_Tools_Cornform_To_Biped()
		)
)
rollout savefileDialog "Save file" width:392 height:131
(
	label lbl1 "Filename:" pos:[22,29] width:58 height:14
	editText filenname "" pos:[21,46] width:343 height:17
	button savebtn "Save" pos:[31,81] width:115 height:24
	button cancelbtn "Cancel" pos:[233,81] width:115 height:24

	on savebtn pressed do(
		if(filenname.text != "")do(
			makedir (getDir #animations + "\\Bippy")
			makedir (getDir #animations + "\\Bippy\\User Defined")
			io = createFile (getDir #animations + "\\Bippy\\User Defined/"+filenname.text+".btf")
			if(io != undefined)then(
				for i = 1 to FBX_convert_str.boneNum do(
					if(FBX_convert_str.FBX_array[i] == undefined)then(
						format "\n" to:io
					)else(
						format "%\n" FBX_convert_str.FBX_array[i].name to:io
					)
				)
				close io
				DestroyDialog savefileDialog
			)else(
			)
		)
	)
	on cancelbtn pressed do(
		DestroyDialog savefileDialog
	)
	
)
rollout loadfileDialog "Load file" width:392 height:131
(
	button loadbtn "Load" pos:[31,81] width:115 height:24
	button cancelbtn "Cancel" pos:[233,81] width:115 height:24
	dropDownList ddl1 "User Defined Templates" pos:[22,27] width:335 height:40
	on loadfileDialog open do( 
			local templates = getFiles (getDir #animations + "\\Bippy\\User Defined\\*.btf") --collect all max files in the dir.
			local count = templates.count 
			for p = 1 to count do(
				string_text = templates[p] 										--makes a string varibale with the text in the mesh_path edit text box
				string_text = replace string_text (string_text.count-3) 4 ""	
				do (																		
				num = undefined																--define "num" as undefined for each loop so we can break out of the do while loop if it returns as undefined after the operations
				num = findString string_text "\\"											--defines "num" as the character number that the Findstring finds a \ within string_text, so we can replace that with a //
					if num != undefined do (
				string_text = replace string_text num 1 "/"							--replaces the \ with a //
					)
				)While num != undefined													--continue looping while there is still a \ in the string_text
				
			strings = filterString string_text "'/"											--creates an array filled with string_text, where each array cotains a bit of the string bewteen the /
			templates[p] = strings[strings.count]	
			)
			ddl1.items = templates
	)
	on loadbtn pressed do
	(
	local file = (getDir #animations + "\\Bippy\\User Defined/")
	file+=(ddl1.selected  + ".btf")
	local fileIO
	try(
	fileIO = openFile file
	)catch(
		messagebox "Cannot load file" "Bippy"
		return 0
	)		
	for bone_num = 1 to FBX_convert_str.boneNum do(
		local name_Temp = "$'"+(readLine fileIO)+"'"
		temp = execute(name_Temp)
		
		if temp  != undefined do (
			sub_li= FBX_convert_str.rows[bone_num].subitems.item[1]
			sub_li.text = name_Temp
			FBX_convert_str.FBX_array[bone_num] = temp
			FBX_convert_str.number_of_bones_found += 1
		)
	)
	flush fileIO
	close fileIO
DestroyDialog loadfileDialog
	)
	on cancelbtn pressed do
	(
			DestroyDialog loadfileDialog
		)
)
rollout listview_rollout "Standard Setting" width:318 height:917
(
	dotNetControl lv_objects "system.windows.forms.listView" pos:[6,23] width:303 height:299 
 
	label lbl1 "FBX bones to Biped Bones:" pos:[6,7] width:189 height:14
	dropdownList defult_bone_names "Defult bone names to use:" pos:[6,378] width:221 height:40 enabled:true items:#("CLEAR", "Bip01", "Bip02", "Bip03", "Motion Builder character")
	button updatelist_button "Update list" pos:[239,378] width:65 height:41
	GroupBox Timelines "Time setting" pos:[5,692] width:303 height:99
	edittext start_frame_box "" pos:[76,709] width:224 height:17
	edittext end_frame_box "" pos:[76,735] width:224 height:17
	label start_frame_label "Start Frame" pos:[12,712] width:64 height:16
	label end_frame_label "End Frame" pos:[12,738] width:56 height:16
	button Getcurrenttimeline "Get current timeline" pos:[10,762] width:290 height:24
	button start_convert "GO!" pos:[5,797] width:303 height:28
	label lbl4 "Number of Bones matched up:" pos:[7,345] width:146 height:18
	label Bones_matched_up_label "0" pos:[155,346] width:57 height:15
	GroupBox grp2 "Prefix Tools" pos:[5,427] width:303 height:56
	spinner prefix_spinner "" pos:[19,459] width:96 height:16 range:[0,1000,0] type:#integer
	button prefix_button "Delete Prefix" pos:[198,459] width:101 height:18
	
	GroupBox grp3 "Key Frame Options" pos:[5,489] width:303 height:90
	spinner KRAL_Toerance "KRAl Toerance" pos:[171,555] width:115 height:16 enabled:false range:[0,100,0.5] scale:0.001

	label lbl49 "Number of letter to REMOVE" pos:[17,443] width:145 height:14
	radiobuttons keyframe_Method "Methods:" pos:[45,508] width:97 height:62 labels:#("Per Frame", "Smart Keyframe", "KRAl") default:2 columns:1
	checkbox chk5 "Use on Batch" pos:[205,440] width:94 height:17	
	
	button LoadDef "Load Definition" pos:[110,325] width:95 height:15
	button SaveDef "Save Definition" pos:[6,324] width:95 height:15
	button ClearDef "Clear Definition" pos:[210,325] width:95 height:15
	
	GroupBox grp4 "Biped Reconstruction Options" pos:[5,582] width:303 height:102
	radioButtons BipedConstructionMethod "Method:" pos:[17,600] width:88 height:46 enabled:true labels:#("AutoBuild", "From .FIG File") columns:1
	editText FIG_BrowseBox "" pos:[15,653] width:280 height:16 enabled:false
	button FIG_BrowseButton "Browse" pos:[235,628] width:62 height:21 enabled:false
	
	
	on BipedConstructionMethod changed arg do
	(
		if(arg == 1)then(
			FBX_convert_str.using_Own_FIG = false
			FIG_BrowseBox.enabled=false
			FIG_BrowseButton.enabled=false
		)else(
			FBX_convert_str.using_Own_FIG = true		
			FIG_BrowseBox.enabled=true			
			FIG_BrowseButton.enabled=true
		)
	)
	
	on FIG_BrowseButton pressed do(
		f = getOpenFileName caption:"FIG File to use:" types:"Biped Figure(*.Fig)|*.Fig|" historyCategory:"BIPPTFIGURE"
		if(f != undefined)do(
			FIG_BrowseBox.text = f
			FBX_convert_str.Fig_File = FIG_BrowseBox.text
		)			
	)
	
	on FIG_BrowseBox  changed  arg do(
		FBX_convert_str.Fig_File = FIG_BrowseBox.text
		
	)
	fn initLv theLv=
	(
		--Setup the forms view
		theLv.view=(dotNetClass "system.windows.forms.view").details
		theLv.Fullrowselect=true		--Set so full width of listView is selected and not just first column.
		theLv.GridLines=true			--Show lines between the items. 
		theLv.MultiSelect=false			--Allow for multiple selections. 
	)

	--Add columns. 
	fn addColumns theLv columnsAr=
	(
		w=(theLv.width/columnsAr.count)-1		--Calculate the width of each column.
		for x in columnsAr do		--Loop through all the column names to be added. 
		(
			theLv.columns.add x w		--Add each new column to the listview control. 
		)
	)

--Adds FBX_convert_str.rows of data to the listView
	fn populateList theLv=
	(
		
			
	local file = (getDir #userscripts + "\\Bippy/Biped Definition.btf")
	local fileIO
	try(
	fileIO = openFile file
	)catch(
		messagebox "Cannot load file" "Bippy"
		return 0
	)		
	bone_num = 0
	while(eof fileIO != true) do(
	--for bone_num = 1 to 192 do(
		local name_Temp = (readLine fileIO)
		li=dotNetObject "System.Windows.Forms.ListViewItem"  name_Temp
		append FBX_convert_str.rows li
		if ((findString name_Temp "*")!= undefined) do(
			append FBX_convert_str.FBX_Check_array (bone_num+1)
		)
		bone_num +=1
	)
	FBX_convert_str.boneNum = bone_num
	flush fileIO
	close fileIO
		
		theLv.items.addRange FBX_convert_str.rows		--Add the array of FBX_convert_str.rows to the listView control. 
		
		--FBX_convert_str.rows[2].subitems.item[1].text = "hell0"
	)
	fn check_biped = (
	local min_specs = true
		for n = 1 to FBX_convert_str.FBX_Check_array.count do(
			if FBX_convert_str.FBX_array[FBX_convert_str.FBX_Check_array[n]] == undefined do (
				min_specs = false
			)
		)
	return min_specs 
	)
	fn Check_for_problems = (
		biped_ok = check_biped()
		if (biped_ok != true) do (
		return  "Missing Vital Biped Bones"
		)
		--Batch Problems
		if (FBX_convert_str.use_batch == true) do (
			if (FBX_convert_str.Input_dir == "") do (
				 return  "No Input Directory"
			)
			if (FBX_convert_str.Output_dir == "") do (
				 return  "No Output Directory"
			)
				if (FBX_convert_str.FilesToBatch[1]  ==  undefined) do (
				return  "No Selected Files to Batch"
			)
		)
			return true
	)
	fn clear_spreadsheet = 
	(
	for p = 1 to FBX_convert_str.boneNum do (
	FBX_convert_str.rows[p].subitems.item[1].text = ""
					)
	)
				
	fn Match_Preset_Bone_Names type = (
		
		local file = (getDir #userscripts + "\\Bippy\\Presets/")
		file+=(type + ".btf")
		local fileIO
		try(
		fileIO = openFile file
		)catch(
			messagebox "Cannot load file" "Bippy"
			return 0
		)		
		for bone_num = 1 to FBX_convert_str.boneNum do(
			local name_Temp = "$'"+(readLine fileIO)+"'"
			temp = execute(name_Temp)
			
			if temp  != undefined do (
				sub_li= FBX_convert_str.rows[bone_num].subitems.item[1]
				sub_li.text = name_Temp
				FBX_convert_str.FBX_array[bone_num] = temp
				FBX_convert_str.number_of_bones_found += 1
			)
		)
		flush fileIO
		close fileIO
	)

	fn update_bones_arrays msg_box= (
		defult_names = defult_bone_names.selected
		FBX_convert_str.number_of_bones_found = 0
		FBX_convert_str.FBX_array = #()
		if defult_names == "CLEAR" do 
		(
			clear_spreadsheet()
		)
			
		if defult_names == "Bip01" do 
		(
			clear_spreadsheet()
			Match_Preset_Bone_Names "Bip01"
			messagebox_text = "Number of Biped bones matched up: " + (FBX_convert_str.number_of_bones_found as string)
			if msg_box == true do (Messagebox messagebox_text)
			)
			
		if defult_names == "Bip02" do 
			(
							clear_spreadsheet()
	Match_Preset_Bone_Names "Bip02"
						messagebox_text = "Number of Biped bones matched up: " + (FBX_convert_str.number_of_bones_found as string)
			if msg_box == true do (Messagebox messagebox_text)
			)
			
		if defult_names == "Bip03" do 
			(
							clear_spreadsheet()
	Match_Preset_Bone_Names "Bip03"
						messagebox_text = "Number of Biped bones matched up: " + (FBX_convert_str.number_of_bones_found as string)
			if msg_box == true do (Messagebox messagebox_text)
			)
			
		if defult_names == "Motion Builder character" do 
			(
							clear_spreadsheet()
	Match_Preset_Bone_Names "MotionBuilder"
						messagebox_text = "Number of Biped bones matched up: " + (FBX_convert_str.number_of_bones_found as string)
			if msg_box == true do (Messagebox messagebox_text)
			)	
	Bones_matched_up_label.text = FBX_convert_str.number_of_bones_found as string
			
			FBX_convert_str.FBX_Name_Array = #()
		for r = 1 to FBX_convert_str.FBX_array.count do (
		if FBX_convert_str.FBX_array[r] != undefined do (
		FBX_convert_str.FBX_NAME_Array[r] = FBX_convert_str.FBX_array[r].name
		)
		)
			
			
	)
	on listview_rollout open do
	(
	
		initLv lv_objects
		addColumns lv_objects #("Biped Node", "FBX Node")
		populateList lv_objects
		
		for p =1 to FBX_convert_str.boneNum do (
	FBX_convert_str.rows[p].subitems.add ("")
		)
		
		start_frame_box.text = animationRange.start as string
		end_frame_box.text = animationRange.end as string
	)
	on lv_objects mouseDown arg do
	(
		if arg.Clicks  == 2 do (
			hit=(lv_objects.HitTest (dotNetObject "System.Drawing.Point" arg.x arg.y))
			hit.item.subItems.item[1].text = ""
	FBX_convert_str.FBX_array[(hit.item.index+1)] = undefined
				FBX_convert_str.number_of_bones_found -= 1
		)
		if arg.Clicks  == 1 do (
		hit=(lv_objects.HitTest (dotNetObject "System.Drawing.Point" arg.x arg.y))
			for i in selection do( 
				if hit.item.subItems.item[1].text == "" do (
				FBX_convert_str.number_of_bones_found += 1	
				)
		hit.item.subItems.item[1].text = "$'" + i.name +"'"
	FBX_convert_str.FBX_array[(hit.item.index+1)] = i
			)
		)
				Bones_matched_up_label.text = FBX_convert_str.number_of_bones_found as string
			
		
	)
	on updatelist_button pressed do
	(
		update_bones_arrays false
	)
	on Getcurrenttimeline pressed do
	(
			start_frame_box.text = animationRange.start as string
			end_frame_box.text = animationRange.end as string
	)
	on start_convert pressed do
	(
		--disableSceneRedraw()
	--try(
		--BATCH
		if FBX_convert_str.use_batch == true then (
				checked = Check_for_problems()
				if (checked == true) then (
					if(FBX_convert_str.batch_SaveFirst_File == true)do(
						Map_biped_to_FBX()
						FBX_convert_str.biped_ctrl=FBX_convert_str.bipObj.transform.controller
						biped.saveBipFile FBX_convert_str.biped_ctrl (FBX_convert_str.Output_dir +"/" + FBX_convert_str.batch_SaveFirst_Name + ".bip")
					)

					FBX_convert_str.Number_of_files=FBX_convert_str.FilesToBatch.count

					local tempFBX_Array = deepCopy FBX_convert_str.FBX_array
					local tempFBX_Name_Array = #()
					for item in FBX_convert_str.FBX_array do (
						if item != undefined then (
							append tempFBX_Name_Array item.name
						)
						else (
							append tempFBX_Name_Array undefined
						)
					)
					
					for i = 1 to FBX_convert_str.Number_of_files do (
						resetMaxFile #noPrompt 
						FBX_convert_str.retarget_array = #()
						FBX_convert_str.current_FILE_number +=1
						FbxImporterSetParam "Animation" true
						importFile FBX_convert_str.FilesToBatch[i] #noPrompt
						FBX_convert_str.FBX_array = #()
						for item in tempFBX_Name_Array do (
							if item != undefined then (
								append FBX_convert_str.FBX_array (getNodeByName item)
							)
							else append FBX_convert_str.FBX_array undefined
						)
						--update_bones_arrays false
						if(Check_for_problems() == false)do(
								close_prog_bar()
								messagebox "FATAL ERROR"
								exit
						)
						if FBX_convert_str.use_bone_detach == true do (
							--bone_detach_fn --NOT YET IMPLEMENTED
						)

						l = FBX_convert_str.FBX_array[1][3][1].keys
						animationRange = interval 0 l[l.count].time

						start_frame_box.text = animationRange.start as string
						end_frame_box.text = animationRange.end as string
						FBX_convert_str.frame_START = animationRange.start as string
						FBX_convert_str.frame_STOP = animationRange.end as string
						FBX_convert_str.current_FRAME_number = start_frame_box.text as string
						Map_biped_to_FBX()
						FBX_convert_str.biped_ctrl=FBX_convert_str.bipObj.transform.controller
						dir = replace FBX_convert_str.FileNamesToBatch[i] (FBX_convert_str.FileNamesToBatch[i].count - 2) 3 "BIP"
						biped.saveBipFile FBX_convert_str.biped_ctrl (FBX_convert_str.Output_dir +"/" +  dir)
						local convertedMaxFileName = replace FBX_convert_str.FileNamesToBatch[i] (FBX_convert_str.FileNamesToBatch[i].count - 2) 3 "max"
						saveMaxFile (FBX_convert_str.Output_dir +"\\" + convertedMaxFileName) clearNeedSaveFlag:true quiet:true
					)
					closeRolloutFloater FBX_convert_str.ConverterFloater
				)
				else(
					messagebox checked
				)
		)
		--SINGLE
		else (
			is_ok = check_biped()
			if is_ok == true then (
			--if FBX_convert_str.use_bone_detach == true do (
				--bone_detach_fn --NOT YET IMPLEMENTED
			--	)
				FBX_convert_str.Number_of_files = 1
				FBX_convert_str.frame_START = start_frame_box.text as string
				FBX_convert_str.frame_STOP = end_frame_box.text as string
				FBX_convert_str.current_FRAME_number = start_frame_box.text as string
			--open_status_bar()
				Map_biped_to_FBX()
			--close_status_bar()
						
				closeRolloutFloater FBX_convert_str.ConverterFloater
			)
		 else (
			messagebox "MISSING VITAL BIPED BONES"
			)
		)
		enableSceneRedraw()
	--) --try
	/*catch(
		close_prog_bar()
		enableSceneRedraw()
		closeRolloutFloater FBX_convert_str.ConverterFloater
		messagebox "FATAL ERROR"
	) --catch*/
	) -- on
	on prefix_button pressed do
	(
	for i in selection do(
	string_temp = i.name
	i.name  = replace string_temp 1 prefix_spinner.value ""
	)
	clearSelection()
	)
	on KRAL_Toerance changed arg do
	(
			FBX_convert_str.KRAL_Toerance = arg
		)
	on keyframe_Method changed arg do
	(
			FBX_convert_str.keyframe_Method = arg
			if arg == 3 do(
				messagebox "The Keyframe Reduction Algroithm(KRAl) has not yet been fully implemented" title:"Bippy"
			)
		)
	on LoadDef pressed do
	(
			createDialog loadfileDialog width:392 height:131 style:#(#style_border,#style_titlebar)
		)
	on SaveDef pressed do
	(
			createDialog savefileDialog width:392 height:131 style:#(#style_border,#style_titlebar)
		)
	on ClearDef pressed do
	(
			FBX_convert_str.number_of_bones_found = 0
			FBX_convert_str.FBX_array = #()
			clear_spreadsheet()
		)
)
try(destroyDialog listview_rollout)catch()

function MakerolloutFloat = 
(
	if(is64bitApplication())then(
		dotnet.loadAssembly (getDir #userscripts + "\\Bippy\\GTools 64 - Bippy.dll")
	)else(
		dotnet.loadAssembly (getDir #userscripts + "\\Bippy\\GTools 32 - Bippy.dll")
	)
	FBX_convert_str.progbar = dotnetobject "GTools.progBar"  


	
	
	if undefined != FBX_convert_str.ConverterFloater then closeRolloutFloater FBX_convert_str.ConverterFloater 
	FBX_convert_str.ConverterFloater = newRolloutFloater "BIPPY Converter" 325 500
	addRollout About_rollout FBX_convert_str.ConverterFloater rolledup:false
	addRollout listview_rollout FBX_convert_str.ConverterFloater rolledup:true
	--addRollout Blade_Tools_rollout FBX_convert_str.ConverterFloater rolledup:true
	--addRollout Bone_detachting_rollout FBX_convert_str.ConverterFloater rolledup:true
	addRollout batch_rollout FBX_convert_str.ConverterFloater rolledup:true
	
	
	
	
	
	
	)
MakerolloutFloat()
--)