struct _AutoClavicleBone (
    name, anim, helper, bone, const, bip,

    boneSize = 2.0,

    fn create_bones inClavicle inUpperArm liftScale:0.8 = (
        local clavicleLength = distance inClavicle inUpperArm
        local tempHelperA = point()
        local tempHelperB = point()
        tempHelperA.transform = inClavicle.transform
        tempHelperB.transform = inClavicle.transform
        anim.move_local tempHelperB (clavicleLength/2.0) 0.0 0.0

        local autoClavicleName = name.replace_realName inClavicle.name "AutoClavicle"
        local autoClavicleBones = bone.create_bone #(tempHelperA, tempHelperB) autoClavicleName end:true delPoint:true parent:false size:boneSize
        autoClavicleBones[1].transform = inClavicle.transform
        anim.move_local autoClavicleBones[1] (clavicleLength/2.0) 0.0 0.0
        autoClavicleBones[1].parent = inClavicle

        local ikGoal = IKSys.ikChain autoClavicleBones[1] autoClavicleBones[2] "IKHISolver"
        ikGoal.name = name.replace_type autoClavicleName "IK"
        ikGoal.transform = autoClavicleBones[2].transform

        local autoClavicleRotHelper = helper.create_point (name.replace_type autoClavicleName "Rot")
        autoClavicleRotHelper.transform = autoClavicleBones[1].transform
        autoClavicleRotHelper.parent = inClavicle

        local rotTargetClavicle = helper.create_point (name.replace_type autoClavicleName "T")
        rotTargetClavicle.transform = inClavicle.transform
        anim.move_local rotTargetClavicle clavicleLength 0.0 0.0
        local rotTargetUpperArm = helper.create_point (name.replace_type autoClavicleName "T")
        rotTargetUpperArm.name = name.add_sufix_to_realName rotTargetUpperArm.name "UArm"
        rotTargetUpperArm.transform = inUpperArm.transform
        anim.move_local rotTargetUpperArm ((clavicleLength/2.0)*liftScale) 0.0 0.0

        rotTargetClavicle.parent = inClavicle
        rotTargetUpperArm.parent = inUpperArm

        const.assign_lookAt_multi autoClavicleRotHelper #(rotTargetClavicle, rotTargetUpperArm)
        autoClavicleRotHelper.rotation.controller[2].upnode_world = false
        autoClavicleRotHelper.rotation.controller[2].pickUpNode = inClavicle
        autoClavicleRotHelper.rotation.controller[2].lookat_vector_length = 0.0
        ikGoal.parent = autoClavicleRotHelper

        autoClavicleBones
    )
)