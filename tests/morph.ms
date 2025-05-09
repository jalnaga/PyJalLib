struct _MorphChannel
(
    index = 0,
    name = "",
    hasData = false
)

struct _Morph (
    channelMaxViewNum = 100,

    fn get_modifier_index inObj = (
        local returnVal = 0
        if inObj.modifiers.count > 0 then (
            for i = 1 to inObj.modifiers.count do (
                if classOf inObj.modifiers[i] == Morpher then (
                    returnVal = i
                )
            )
        )

        returnVal
    ),

    fn get_modifier inObj = (
        local returnVal = undefined
        local modIndex = get_modifier_index inObj
        if modIndex > 0 then returnVal = inObj.modifiers[modIndex]

        returnval
    ),

    fn get_channel_num inObj = (
        local returnVal = 0
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            local morphChannelExistance = true
            local morphChannelCounter = 0
            while morphChannelExistance do (
                for i = (morphChannelCounter + 1) to (morphChannelCounter + channelMaxViewNum) do (
                    if not(WM3_MC_HasData morphMod i) then (
                        returnVal = i - 1
                        morphChannelExistance = false
                        exit
                    )
                )
                morphChannelCounter = morphChannelCounter + channelMaxViewNum
            )
        )

        returnVal
    ),

    fn get_all_channel_info inObj = (
        local returnVal = #()
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            local channelNum = get_channel_num inObj
            if channelNum > 0 then (
                for i = 1 to channelNum do (
                    local tempChannel = _MorphChannel()
                    tempChannel.index = i
                    tempChannel.hasData = WM3_MC_HasData morphMod i
                    tempChannel.name = WM3_MC_GetName morphMod i
                    append returnVal tempChannel
                )
            )
        )

        returnVal
    ),

    fn add_target inObj inTarget inIndex = (
        local returnVal = false
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            WM3_MC_BuildFromNode morphMod inIndex inTarget
            returnVal = WM3_MC_HasData morphMod inIndex
        )
        returnVal
    ),

    fn add_targets inObj inTargetArray = (
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            for i = 1 to inTargetArray.count do (
                WM3_MC_BuildFromNode morphMod i inTargetArray[i]
            )
        )
    ),

    fn get_all_channel_name inObj = (
        local returnVal = #()
        local channelArray = get_all_channel_info inObj
        if channelArray.count > 0 then returnval = for item in channelArray collect item.name

        returnVal
    ),

    fn get_channel_name inObj inIndex = (
        local returnVal = ""
        local channelArray = get_all_channel_info inObj
        try (if channelArray.count > 0 then returnVal = channelArray[inIndex].name)
        catch returnVal = ""
        returnVal
    ),

    fn get_channel_index inObj inName = (
        local returnVal = 0
        local channelArray = get_all_channel_info inObj
        if channelArray.count > 0 then (
            for item in channelArray do if item.name == inName then (returnval = item.index; exit)
        )
        returnVal
    ),

    fn get_channel_value_by_name inObj inName = (
        local returnVal = 0.0
        local channelIndex = get_channel_index inObj inName
        local morphMod = get_modifier inObj
        if channelIndex > 0 then (
            try (returnVal = WM3_MC_GetValue morphMod channelIndex)
            catch returnVal = 0.0
        )
        returnVal
    ),

    fn get_channel_value_by_index inObj inIndex = (
        local returnVal = 0
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            try (returnVal = WM3_MC_GetValue morphMod inIndex)
            catch returnVal = 0
        )
        returnVal
    ),

    fn set_channel_value_by_name inObj inName inVal = (
        local returnVal = false
        local morphMod = get_modifier inObj
        local channelIndex = get_channel_index inObj inName
        if channelIndex > 0 then (
            try (
                WM3_MC_SetValue morphMod channelIndex inVal
                returnVal = true
            )
            catch returnVal = false
        )
        returnVal
    ),

    fn set_channel_value_by_index inObj inIndex inVal = (
        local returnVal = false
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            try (
                WM3_MC_SetValue morphMod inIndex inVal
                returnVal = true
            )
            catch returnval = false
        )

        returnVal
    ),

    fn set_channel_name_by_name inObj inTargetName inNewName = (
        local returnVal = false
        local channelIndex = get_channel_index inObj inTargetName
        if channelIndex > 0 then (
            WM3_MC_SetName morphMod channelIndex inNewName
            returnVal = true
        )
        returnVal
    ),

    fn set_channel_name_by_index inObj inIndex inName = (
        local returnVal = false
        local morphMod = get_modifier inObj
        if morphMod != undefined then (
            try (
                WM3_MC_SetName morphMod inIndex inName
                returnVal = true
            )
            catch returnVal = false
        )
        returnVal
    ),

    fn reset_all_channel_value inObj = (
        local returnVal = false
        local totalChannelNum = get_channel_num inObj
        if totalChannelNum > 0 then (
            for i = 1 to totalChannelNum do (
                set_channel_value_by_index inObj i 0.0
            )
        )
    ),

    fn extract_morph_channel_geometry obj _feedback_:false = (
        morph_mod = get_modifier obj

        if IsValidMorpherMod morph_mod then (
            channels = for i=1 to (WM3_NumberOfChannels morph_mod) where WM3_MC_HasData morph_mod i collect i
            for i in channels do (
                chan_name = WM3_MC_GetName morph_mod i
                WM3_MC_SetValue morph_mod i 100.0

                obj_snapShot =  snapShot obj
                obj_snapShot.name = chan_name

                WM3_MC_SetValue morph_mod i 0.0

                if _feedback_ do format " - FUNCTION - [ extract_morph_channel_geometry ] - Extracted ---- % ---- successfuly!!\n" obj_snapShot.name
            )
        )
        else(if _feedback_ do format " - FUNCTION - [ extract_morph_channel_geometry ] - No valid morpher found on ---- % ---- " obj.name)
    )
)
