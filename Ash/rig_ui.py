
import bpy
from mathutils import Matrix, Vector
from math import acos, pi, radians

rig_id = "r2as986g25aa63f5"


############################
## Math utility functions ##
############################

def perpendicular_vector(v):
    """ Returns a vector that is perpendicular to the one given.
        The returned vector is _not_ guaranteed to be normalized.
    """
    # Create a vector that is not aligned with v.
    # It doesn't matter what vector.  Just any vector
    # that's guaranteed to not be pointing in the same
    # direction.
    if abs(v[0]) < abs(v[1]):
        tv = Vector((1,0,0))
    else:
        tv = Vector((0,1,0))

    # Use cross prouct to generate a vector perpendicular to
    # both tv and (more importantly) v.
    return v.cross(tv)


def rotation_difference(mat1, mat2):
    """ Returns the shortest-path rotational difference between two
        matrices.
    """
    q1 = mat1.to_quaternion()
    q2 = mat2.to_quaternion()
    angle = acos(min(1,max(-1,q1.dot(q2)))) * 2
    if angle > pi:
        angle = -angle + (2*pi)
    return angle

def tail_distance(angle,bone_ik,bone_fk):
    """ Returns the distance between the tails of two bones
        after rotating bone_ik in AXIS_ANGLE mode.
    """
    rot_mod=bone_ik.rotation_mode
    if rot_mod != 'AXIS_ANGLE':
        bone_ik.rotation_mode = 'AXIS_ANGLE'
    bone_ik.rotation_axis_angle[0] = angle
    bpy.context.scene.update()

    dv = (bone_fk.tail - bone_ik.tail).length

    bone_ik.rotation_mode = rot_mod
    return dv

def find_min_range(bone_ik,bone_fk,f=tail_distance,delta=pi/8):
    """ finds the range where lies the minimum of function f applied on bone_ik and bone_fk
        at a certain angle.
    """
    rot_mod=bone_ik.rotation_mode
    if rot_mod != 'AXIS_ANGLE':
        bone_ik.rotation_mode = 'AXIS_ANGLE'

    start_angle = bone_ik.rotation_axis_angle[0]
    angle = start_angle
    while (angle > (start_angle - 2*pi)) and (angle < (start_angle + 2*pi)):
        l_dist = f(angle-delta,bone_ik,bone_fk)
        c_dist = f(angle,bone_ik,bone_fk)
        r_dist = f(angle+delta,bone_ik,bone_fk)
        if min((l_dist,c_dist,r_dist)) == c_dist:
            bone_ik.rotation_mode = rot_mod
            return (angle-delta,angle+delta)
        else:
            angle=angle+delta

def ternarySearch(f, left, right, bone_ik, bone_fk, absolutePrecision):
    """
    Find minimum of unimodal function f() within [left, right]
    To find the maximum, revert the if/else statement or revert the comparison.
    """
    while True:
        #left and right are the current bounds; the maximum is between them
        if abs(right - left) < absolutePrecision:
            return (left + right)/2

        leftThird = left + (right - left)/3
        rightThird = right - (right - left)/3

        if f(leftThird, bone_ik, bone_fk) > f(rightThird, bone_ik, bone_fk):
            left = leftThird
        else:
            right = rightThird

#########################################
## "Visual Transform" helper functions ##
#########################################

def get_pose_matrix_in_other_space(mat, pose_bone):
    """ Returns the transform matrix relative to pose_bone's current
        transform space.  In other words, presuming that mat is in
        armature space, slapping the returned matrix onto pose_bone
        should give it the armature-space transforms of mat.
        TODO: try to handle cases with axis-scaled parents better.
    """
    rest = pose_bone.bone.matrix_local.copy()
    rest_inv = rest.inverted()
    if pose_bone.parent:
        par_mat = pose_bone.parent.matrix.copy()
        par_inv = par_mat.inverted()
        par_rest = pose_bone.parent.bone.matrix_local.copy()
    else:
        par_mat = Matrix()
        par_inv = Matrix()
        par_rest = Matrix()

    # Get matrix in bone's current transform space
    smat = rest_inv * (par_rest * (par_inv * mat))

    # Compensate for non-local location
    #if not pose_bone.bone.use_local_location:
    #    loc = smat.to_translation() * (par_rest.inverted() * rest).to_quaternion()
    #    smat.translation = loc

    return smat


def get_local_pose_matrix(pose_bone):
    """ Returns the local transform matrix of the given pose bone.
    """
    return get_pose_matrix_in_other_space(pose_bone.matrix, pose_bone)


def set_pose_translation(pose_bone, mat):
    """ Sets the pose bone's translation to the same translation as the given matrix.
        Matrix should be given in bone's local space.
    """
    if pose_bone.bone.use_local_location == True:
        pose_bone.location = mat.to_translation()
    else:
        loc = mat.to_translation()

        rest = pose_bone.bone.matrix_local.copy()
        if pose_bone.bone.parent:
            par_rest = pose_bone.bone.parent.matrix_local.copy()
        else:
            par_rest = Matrix()

        q = (par_rest.inverted() * rest).to_quaternion()
        pose_bone.location = q * loc


def set_pose_rotation(pose_bone, mat):
    """ Sets the pose bone's rotation to the same rotation as the given matrix.
        Matrix should be given in bone's local space.
    """
    q = mat.to_quaternion()

    if pose_bone.rotation_mode == 'QUATERNION':
        pose_bone.rotation_quaternion = q
    elif pose_bone.rotation_mode == 'AXIS_ANGLE':
        pose_bone.rotation_axis_angle[0] = q.angle
        pose_bone.rotation_axis_angle[1] = q.axis[0]
        pose_bone.rotation_axis_angle[2] = q.axis[1]
        pose_bone.rotation_axis_angle[3] = q.axis[2]
    else:
        pose_bone.rotation_euler = q.to_euler(pose_bone.rotation_mode)


def set_pose_scale(pose_bone, mat):
    """ Sets the pose bone's scale to the same scale as the given matrix.
        Matrix should be given in bone's local space.
    """
    pose_bone.scale = mat.to_scale()


def match_pose_translation(pose_bone, target_bone):
    """ Matches pose_bone's visual translation to target_bone's visual
        translation.
        This function assumes you are in pose mode on the relevant armature.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_translation(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')


def match_pose_rotation(pose_bone, target_bone):
    """ Matches pose_bone's visual rotation to target_bone's visual
        rotation.
        This function assumes you are in pose mode on the relevant armature.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_rotation(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')


def match_pose_scale(pose_bone, target_bone):
    """ Matches pose_bone's visual scale to target_bone's visual
        scale.
        This function assumes you are in pose mode on the relevant armature.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_scale(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')

def correct_rotation(bone_ik, bone_fk):
    """ Corrects the ik rotation in ik2fk snapping functions
    """

    alfarange = find_min_range(bone_ik,bone_fk)
    alfamin = ternarySearch(tail_distance,alfarange[0],alfarange[1],bone_ik,bone_fk,0.1)

    rot_mod = bone_ik.rotation_mode
    if rot_mod != 'AXIS_ANGLE':
        bone_ik.rotation_mode = 'AXIS_ANGLE'
    bone_ik.rotation_axis_angle[0] = alfamin
    bone_ik.rotation_mode = rot_mod

##############################
## IK/FK snapping functions ##
##############################

def match_pole_target(ik_first, ik_last, pole, match_bone, length):
    """ Places an IK chain's pole target to match ik_first's
        transforms to match_bone.  All bones should be given as pose bones.
        You need to be in pose mode on the relevant armature object.
        ik_first: first bone in the IK chain
        ik_last:  last bone in the IK chain
        pole:  pole target bone for the IK chain
        match_bone:  bone to match ik_first to (probably first bone in a matching FK chain)
        length:  distance pole target should be placed from the chain center
    """
    a = ik_first.matrix.to_translation()
    b = ik_last.matrix.to_translation() + ik_last.vector

    # Vector from the head of ik_first to the
    # tip of ik_last
    ikv = b - a

    # Get a vector perpendicular to ikv
    pv = perpendicular_vector(ikv).normalized() * length

    def set_pole(pvi):
        """ Set pole target's position based on a vector
            from the arm center line.
        """
        # Translate pvi into armature space
        ploc = a + (ikv/2) + pvi

        # Set pole target to location
        mat = get_pose_matrix_in_other_space(Matrix.Translation(ploc), pole)
        set_pose_translation(pole, mat)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')

    set_pole(pv)

    # Get the rotation difference between ik_first and match_bone
    angle = rotation_difference(ik_first.matrix, match_bone.matrix)

    # Try compensating for the rotation difference in both directions
    pv1 = Matrix.Rotation(angle, 4, ikv) * pv
    set_pole(pv1)
    ang1 = rotation_difference(ik_first.matrix, match_bone.matrix)

    pv2 = Matrix.Rotation(-angle, 4, ikv) * pv
    set_pole(pv2)
    ang2 = rotation_difference(ik_first.matrix, match_bone.matrix)

    # Do the one with the smaller angle
    if ang1 < ang2:
        set_pole(pv1)


def fk2ik_arm(obj, fk, ik):
    """ Matches the fk bones in an arm rig to the ik bones.
        obj: armature object
        fk:  list of fk bone names
        ik:  list of ik bone names
    """
    uarm  = obj.pose.bones[fk[0]]
    farm  = obj.pose.bones[fk[1]]
    hand  = obj.pose.bones[fk[2]]
    uarmi = obj.pose.bones[ik[0]]
    farmi = obj.pose.bones[ik[1]]
    handi = obj.pose.bones[ik[2]]

    if 'auto_stretch' in handi.keys():
        # This is kept for compatibility with legacy rigify Human
        # Stretch
        if handi['auto_stretch'] == 0.0:
            uarm['stretch_length'] = handi['stretch_length']
        else:
            diff = (uarmi.vector.length + farmi.vector.length) / (uarm.vector.length + farm.vector.length)
            uarm['stretch_length'] *= diff

        # Upper arm position
        match_pose_rotation(uarm, uarmi)
        match_pose_scale(uarm, uarmi)

        # Forearm position
        match_pose_rotation(farm, farmi)
        match_pose_scale(farm, farmi)

        # Hand position
        match_pose_rotation(hand, handi)
        match_pose_scale(hand, handi)
    else:
        # Upper arm position
        match_pose_translation(uarm, uarmi)
        match_pose_rotation(uarm, uarmi)
        match_pose_scale(uarm, uarmi)

        # Forearm position
        #match_pose_translation(hand, handi)
        match_pose_rotation(farm, farmi)
        match_pose_scale(farm, farmi)

        # Hand position
        match_pose_translation(hand, handi)
        match_pose_rotation(hand, handi)
        match_pose_scale(hand, handi)


def ik2fk_arm(obj, fk, ik):
    """ Matches the ik bones in an arm rig to the fk bones.
        obj: armature object
        fk:  list of fk bone names
        ik:  list of ik bone names
    """
    uarm  = obj.pose.bones[fk[0]]
    farm  = obj.pose.bones[fk[1]]
    hand  = obj.pose.bones[fk[2]]
    uarmi = obj.pose.bones[ik[0]]
    farmi = obj.pose.bones[ik[1]]
    handi = obj.pose.bones[ik[2]]

    main_parent = obj.pose.bones[ik[4]]

    if ik[3] != "" and main_parent['pole_vector']:
        pole  = obj.pose.bones[ik[3]]
    else:
        pole = None


    if pole:
        # Stretch
        # handi['stretch_length'] = uarm['stretch_length']

        # Hand position
        match_pose_translation(handi, hand)
        match_pose_rotation(handi, hand)
        match_pose_scale(handi, hand)
        # Pole target position
        match_pole_target(uarmi, farmi, pole, uarm, (uarmi.length + farmi.length))

    else:
        # Hand position
        match_pose_translation(handi, hand)
        match_pose_rotation(handi, hand)
        match_pose_scale(handi, hand)

        # Upper Arm position
        match_pose_translation(uarmi, uarm)
        match_pose_rotation(uarmi, uarm)
        match_pose_scale(uarmi, uarm)
        # Rotation Correction
        correct_rotation(uarmi, uarm)

def fk2ik_leg(obj, fk, ik):
    """ Matches the fk bones in a leg rig to the ik bones.
        obj: armature object
        fk:  list of fk bone names
        ik:  list of ik bone names
    """
    thigh  = obj.pose.bones[fk[0]]
    shin   = obj.pose.bones[fk[1]]
    foot   = obj.pose.bones[fk[2]]
    mfoot  = obj.pose.bones[fk[3]]
    thighi = obj.pose.bones[ik[0]]
    shini  = obj.pose.bones[ik[1]]
    footi  = obj.pose.bones[ik[2]]
    mfooti = obj.pose.bones[ik[3]]

    if 'auto_stretch' in footi.keys():
        # This is kept for compatibility with legacy rigify Human
        # Stretch
        if footi['auto_stretch'] == 0.0:
            thigh['stretch_length'] = footi['stretch_length']
        else:
            diff = (thighi.vector.length + shini.vector.length) / (thigh.vector.length + shin.vector.length)
            thigh['stretch_length'] *= diff

        # Thigh position
        match_pose_rotation(thigh, thighi)
        match_pose_scale(thigh, thighi)

        # Shin position
        match_pose_rotation(shin, shini)
        match_pose_scale(shin, shini)

        # Foot position
        mat = mfoot.bone.matrix_local.inverted() * foot.bone.matrix_local
        footmat = get_pose_matrix_in_other_space(mfooti.matrix, foot) * mat
        set_pose_rotation(foot, footmat)
        set_pose_scale(foot, footmat)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')

    else:
        # Thigh position
        match_pose_translation(thigh, thighi)
        match_pose_rotation(thigh, thighi)
        match_pose_scale(thigh, thighi)

        # Shin position
        match_pose_rotation(shin, shini)
        match_pose_scale(shin, shini)

        # Foot position
        mat = mfoot.bone.matrix_local.inverted() * foot.bone.matrix_local
        footmat = get_pose_matrix_in_other_space(mfooti.matrix, foot) * mat
        set_pose_rotation(foot, footmat)
        set_pose_scale(foot, footmat)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')


def ik2fk_leg(obj, fk, ik):
    """ Matches the ik bones in a leg rig to the fk bones.
        obj: armature object
        fk:  list of fk bone names
        ik:  list of ik bone names
    """
    thigh    = obj.pose.bones[fk[0]]
    shin     = obj.pose.bones[fk[1]]
    mfoot    = obj.pose.bones[fk[2]]
    if fk[3] != "":
        foot      = obj.pose.bones[fk[3]]
    else:
        foot = None
    thighi   = obj.pose.bones[ik[0]]
    shini    = obj.pose.bones[ik[1]]
    footi    = obj.pose.bones[ik[2]]
    footroll = obj.pose.bones[ik[3]]

    main_parent = obj.pose.bones[ik[6]]

    if ik[4] != "" and main_parent['pole_vector']:
        pole     = obj.pose.bones[ik[4]]
    else:
        pole = None
    mfooti   = obj.pose.bones[ik[5]]

    if (not pole) and (foot):

        # Clear footroll
        set_pose_rotation(footroll, Matrix())

        # Foot position
        mat = mfooti.bone.matrix_local.inverted() * footi.bone.matrix_local
        footmat = get_pose_matrix_in_other_space(foot.matrix, footi) * mat
        set_pose_translation(footi, footmat)
        set_pose_rotation(footi, footmat)
        set_pose_scale(footi, footmat)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')

        # Thigh position
        match_pose_translation(thighi, thigh)
        match_pose_rotation(thighi, thigh)
        match_pose_scale(thighi, thigh)

        # Rotation Correction
        correct_rotation(thighi,thigh)

    else:
        # Stretch
        if 'stretch_lenght' in footi.keys() and 'stretch_lenght' in thigh.keys():
            # Kept for compat with legacy rigify Human
            footi['stretch_length'] = thigh['stretch_length']

        # Clear footroll
        set_pose_rotation(footroll, Matrix())

        # Foot position
        mat = mfooti.bone.matrix_local.inverted() * footi.bone.matrix_local
        footmat = get_pose_matrix_in_other_space(mfoot.matrix, footi) * mat
        set_pose_translation(footi, footmat)
        set_pose_rotation(footi, footmat)
        set_pose_scale(footi, footmat)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')

        # Pole target position
        match_pole_target(thighi, shini, pole, thigh, (thighi.length + shini.length))


##############################
## IK/FK snapping operators ##
##############################

class Rigify_Arm_FK2IK(bpy.types.Operator):
    """ Snaps an FK arm to an IK arm.
    """
    bl_idname = "pose.rigify_arm_fk2ik_" + rig_id
    bl_label = "Rigify Snap FK arm to IK"
    bl_options = {'UNDO'}

    uarm_fk = bpy.props.StringProperty(name="Upper Arm FK Name")
    farm_fk = bpy.props.StringProperty(name="Forerm FK Name")
    hand_fk = bpy.props.StringProperty(name="Hand FK Name")

    uarm_ik = bpy.props.StringProperty(name="Upper Arm IK Name")
    farm_ik = bpy.props.StringProperty(name="Forearm IK Name")
    hand_ik = bpy.props.StringProperty(name="Hand IK Name")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.user_preferences.edit.use_global_undo
        context.user_preferences.edit.use_global_undo = False
        try:
            fk2ik_arm(context.active_object, fk=[self.uarm_fk, self.farm_fk, self.hand_fk], ik=[self.uarm_ik, self.farm_ik, self.hand_ik])
        finally:
            context.user_preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class Rigify_Arm_IK2FK(bpy.types.Operator):
    """ Snaps an IK arm to an FK arm.
    """
    bl_idname = "pose.rigify_arm_ik2fk_" + rig_id
    bl_label = "Rigify Snap IK arm to FK"
    bl_options = {'UNDO'}

    uarm_fk = bpy.props.StringProperty(name="Upper Arm FK Name")
    farm_fk = bpy.props.StringProperty(name="Forerm FK Name")
    hand_fk = bpy.props.StringProperty(name="Hand FK Name")

    uarm_ik = bpy.props.StringProperty(name="Upper Arm IK Name")
    farm_ik = bpy.props.StringProperty(name="Forearm IK Name")
    hand_ik = bpy.props.StringProperty(name="Hand IK Name")
    pole    = bpy.props.StringProperty(name="Pole IK Name")

    main_parent = bpy.props.StringProperty(name="Main Parent", default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.user_preferences.edit.use_global_undo
        context.user_preferences.edit.use_global_undo = False
        try:
            ik2fk_arm(context.active_object, fk=[self.uarm_fk, self.farm_fk, self.hand_fk], ik=[self.uarm_ik, self.farm_ik, self.hand_ik, self.pole, self.main_parent])
        finally:
            context.user_preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class Rigify_Leg_FK2IK(bpy.types.Operator):
    """ Snaps an FK leg to an IK leg.
    """
    bl_idname = "pose.rigify_leg_fk2ik_" + rig_id
    bl_label = "Rigify Snap FK leg to IK"
    bl_options = {'UNDO'}

    thigh_fk = bpy.props.StringProperty(name="Thigh FK Name")
    shin_fk  = bpy.props.StringProperty(name="Shin FK Name")
    foot_fk  = bpy.props.StringProperty(name="Foot FK Name")
    mfoot_fk = bpy.props.StringProperty(name="MFoot FK Name")

    thigh_ik = bpy.props.StringProperty(name="Thigh IK Name")
    shin_ik  = bpy.props.StringProperty(name="Shin IK Name")
    foot_ik  = bpy.props.StringProperty(name="Foot IK Name")
    mfoot_ik = bpy.props.StringProperty(name="MFoot IK Name")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.user_preferences.edit.use_global_undo
        context.user_preferences.edit.use_global_undo = False
        try:
            fk2ik_leg(context.active_object, fk=[self.thigh_fk, self.shin_fk, self.foot_fk, self.mfoot_fk], ik=[self.thigh_ik, self.shin_ik, self.foot_ik, self.mfoot_ik])
        finally:
            context.user_preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class Rigify_Leg_IK2FK(bpy.types.Operator):
    """ Snaps an IK leg to an FK leg.
    """
    bl_idname = "pose.rigify_leg_ik2fk_" + rig_id
    bl_label = "Rigify Snap IK leg to FK"
    bl_options = {'UNDO'}

    thigh_fk = bpy.props.StringProperty(name="Thigh FK Name")
    shin_fk  = bpy.props.StringProperty(name="Shin FK Name")
    mfoot_fk = bpy.props.StringProperty(name="MFoot FK Name")
    foot_fk = bpy.props.StringProperty(name="Foot FK Name", default="")
    thigh_ik = bpy.props.StringProperty(name="Thigh IK Name")
    shin_ik  = bpy.props.StringProperty(name="Shin IK Name")
    foot_ik  = bpy.props.StringProperty(name="Foot IK Name")
    footroll = bpy.props.StringProperty(name="Foot Roll Name")
    pole     = bpy.props.StringProperty(name="Pole IK Name")
    mfoot_ik = bpy.props.StringProperty(name="MFoot IK Name")

    main_parent = bpy.props.StringProperty(name="Main Parent", default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.user_preferences.edit.use_global_undo
        context.user_preferences.edit.use_global_undo = False
        try:
            ik2fk_leg(context.active_object, fk=[self.thigh_fk, self.shin_fk, self.mfoot_fk, self.foot_fk], ik=[self.thigh_ik, self.shin_ik, self.foot_ik, self.footroll, self.pole, self.mfoot_ik, self.main_parent])
        finally:
            context.user_preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


###################
## Rig UI Panels ##
###################

class RigUI(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rig Main Properties"
    bl_idname = rig_id + "_PT_rig_ui"

    @classmethod
    def poll(self, context):
        if context.mode != 'POSE':
            return False
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        layout = self.layout
        pose_bones = context.active_object.pose.bones
        try:
            selected_bones = [bone.name for bone in context.selected_pose_bones]
            selected_bones += [context.active_pose_bone.name]
        except (AttributeError, TypeError):
            return

        def is_selected(names):
            # Returns whether any of the named bones are selected.
            if type(names) == list:
                for name in names:
                    if name in selected_bones:
                        return True
            elif names in selected_bones:
                return True
            return False



        
        controls = ['head', 'neck', 'chest', 'hips', 'torso']
        torso    = 'torso'
        
        if is_selected( controls ):
            if hasattr(pose_bones[torso],'["head_follow"]'):
                layout.prop( pose_bones[ torso ], '["head_follow"]', slider = True )
            if hasattr(pose_bones[torso],'["neck_follow"]'):
                layout.prop( pose_bones[ torso ], '["neck_follow"]', slider = True )
            if hasattr(pose_bones[torso],'["tail_follow"]'):
                layout.prop( pose_bones[ torso ], '["tail_follow"]', slider = True )
        

        
        controls = ['thigh_ik.L', 'thigh_fk.L', 'shin_fk.L', 'foot_fk.L', 'toe.L', 'foot_heel_ik.L', 'foot_ik.L', 'MCH-foot_fk.L', 'thigh_parent.L']
        tweaks   = ['thigh_tweak.L.001', 'shin_tweak.L', 'shin_tweak.L.001']
        ik_ctrl  = ['foot_ik.L', 'MCH-thigh_ik.L', 'MCH-thigh_ik_target.L']
        fk_ctrl  = 'thigh_fk.L'
        parent   = 'thigh_parent.L'
        foot_fk = 'foot_fk.L'
        pole = 'thigh_ik_target.L'
        
        # IK/FK Switch on all Control Bones
        if is_selected( controls ):
            layout.prop( pose_bones[parent], '["IK_FK"]', slider = True )
            props = layout.operator("pose.rigify_leg_fk2ik_" + rig_id, text="Snap FK->IK (" + fk_ctrl + ")")
            props.thigh_fk = controls[1]
            props.shin_fk  = controls[2]
            props.foot_fk  = controls[3]
            props.mfoot_fk = controls[7]
            props.thigh_ik = controls[0]
            props.shin_ik  = ik_ctrl[1]
            props.foot_ik = ik_ctrl[2]
            props.mfoot_ik = ik_ctrl[2]
            props = layout.operator("pose.rigify_leg_ik2fk_" + rig_id, text="Snap IK->FK (" + fk_ctrl + ")")
            props.thigh_fk  = controls[1]
            props.shin_fk   = controls[2]
            props.foot_fk  = controls[3]
            props.mfoot_fk  = controls[7]
            props.thigh_ik  = controls[0]
            props.shin_ik   = ik_ctrl[1]
            props.foot_ik   = controls[6]
            props.pole      = pole
            props.footroll  = controls[5]
            props.mfoot_ik  = ik_ctrl[2]
            props.main_parent = parent
            props = layout.operator("rigify.rotation_pole", text="Toggle Rotation and Pole")
            props.bone_name = controls[1]
            props.window = "CURRENT"
            props.toggle = True
            props.bake = False
        
        # BBone rubber hose on each Respective Tweak
        for t in tweaks:
            if is_selected( t ):
                layout.prop( pose_bones[ t ], '["rubber_tweak"]', slider = True )
        
        # IK Stretch and pole_vector on IK Control bone
        if is_selected( ik_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["IK_Stretch"]', slider = True )
            layout.prop( pose_bones[ parent ], '["pole_vector"]')
        
        # FK limb follow
        if is_selected( fk_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["FK_limb_follow"]', slider = True )
        
        controls = ['thigh_ik.L', 'foot_ik.L', 'foot_heel_ik.L', 'thigh_parent.L']
        ctrl    = 'thigh_parent.L'
        
        if is_selected( controls ):
            layout.prop( pose_bones[ ctrl ], '["IK_follow"]')
            if 'pole_follow' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["pole_follow"]', slider = True )
            if 'root/parent' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["root/parent"]', slider = True )
        

        
        controls = ['thigh_ik.R', 'thigh_fk.R', 'shin_fk.R', 'foot_fk.R', 'toe.R', 'foot_heel_ik.R', 'foot_ik.R', 'MCH-foot_fk.R', 'thigh_parent.R']
        tweaks   = ['thigh_tweak.R.001', 'shin_tweak.R', 'shin_tweak.R.001']
        ik_ctrl  = ['foot_ik.R', 'MCH-thigh_ik.R', 'MCH-thigh_ik_target.R']
        fk_ctrl  = 'thigh_fk.R'
        parent   = 'thigh_parent.R'
        foot_fk = 'foot_fk.R'
        pole = 'thigh_ik_target.R'
        
        # IK/FK Switch on all Control Bones
        if is_selected( controls ):
            layout.prop( pose_bones[parent], '["IK_FK"]', slider = True )
            props = layout.operator("pose.rigify_leg_fk2ik_" + rig_id, text="Snap FK->IK (" + fk_ctrl + ")")
            props.thigh_fk = controls[1]
            props.shin_fk  = controls[2]
            props.foot_fk  = controls[3]
            props.mfoot_fk = controls[7]
            props.thigh_ik = controls[0]
            props.shin_ik  = ik_ctrl[1]
            props.foot_ik = ik_ctrl[2]
            props.mfoot_ik = ik_ctrl[2]
            props = layout.operator("pose.rigify_leg_ik2fk_" + rig_id, text="Snap IK->FK (" + fk_ctrl + ")")
            props.thigh_fk  = controls[1]
            props.shin_fk   = controls[2]
            props.foot_fk  = controls[3]
            props.mfoot_fk  = controls[7]
            props.thigh_ik  = controls[0]
            props.shin_ik   = ik_ctrl[1]
            props.foot_ik   = controls[6]
            props.pole      = pole
            props.footroll  = controls[5]
            props.mfoot_ik  = ik_ctrl[2]
            props.main_parent = parent
            props = layout.operator("rigify.rotation_pole", text="Toggle Rotation and Pole")
            props.bone_name = controls[1]
            props.window = "CURRENT"
            props.toggle = True
            props.bake = False
        
        # BBone rubber hose on each Respective Tweak
        for t in tweaks:
            if is_selected( t ):
                layout.prop( pose_bones[ t ], '["rubber_tweak"]', slider = True )
        
        # IK Stretch and pole_vector on IK Control bone
        if is_selected( ik_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["IK_Stretch"]', slider = True )
            layout.prop( pose_bones[ parent ], '["pole_vector"]')
        
        # FK limb follow
        if is_selected( fk_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["FK_limb_follow"]', slider = True )
        
        controls = ['thigh_ik.R', 'foot_ik.R', 'foot_heel_ik.R', 'thigh_parent.R']
        ctrl    = 'thigh_parent.R'
        
        if is_selected( controls ):
            layout.prop( pose_bones[ ctrl ], '["IK_follow"]')
            if 'pole_follow' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["pole_follow"]', slider = True )
            if 'root/parent' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["root/parent"]', slider = True )
        

        
        controls = ['upper_arm_ik.L', 'upper_arm_fk.L', 'forearm_fk.L', 'hand_fk.L', 'hand_ik.L', 'MCH-hand_fk.L', 'upper_arm_parent.L']
        tweaks   = ['upper_arm_tweak.L.001', 'forearm_tweak.L', 'forearm_tweak.L.001']
        ik_ctrl  = ['hand_ik.L', 'MCH-upper_arm_ik.L', 'MCH-upper_arm_ik_target.L']
        fk_ctrl  = 'upper_arm_fk.L'
        parent   = 'upper_arm_parent.L'
        hand_fk   = 'hand_fk.L'
        pole = 'upper_arm_ik_target.L'
        
        # IK/FK Switch on all Control Bones
        if is_selected( controls ):
            layout.prop( pose_bones[parent], '["IK_FK"]', slider = True )
            props = layout.operator("pose.rigify_arm_fk2ik_" + rig_id, text="Snap FK->IK (" + fk_ctrl + ")")
            props.uarm_fk = controls[1]
            props.farm_fk = controls[2]
            props.hand_fk = controls[3]
            props.uarm_ik = controls[0]
            props.farm_ik = ik_ctrl[1]
            props.hand_ik = controls[4]
            props = layout.operator("pose.rigify_arm_ik2fk_" + rig_id, text="Snap IK->FK (" + fk_ctrl + ")")
            props.uarm_fk = controls[1]
            props.farm_fk = controls[2]
            props.hand_fk = controls[3]
            props.uarm_ik = controls[0]
            props.farm_ik = ik_ctrl[1]
            props.hand_ik = controls[4]
            props.pole = pole
            props.main_parent = parent
            props = layout.operator("rigify.rotation_pole", text="Switch Rotation-Pole")
            props.bone_name = controls[1]
            props.window = "CURRENT"
            props.toggle = True
            props.bake = False
        
        
        # BBone rubber hose on each Respective Tweak
        for t in tweaks:
            if is_selected( t ):
                layout.prop( pose_bones[ t ], '["rubber_tweak"]', slider = True )
        
        # IK Stretch and pole_vector on IK Control bone
        if is_selected( ik_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["IK_Stretch"]', slider = True )
            layout.prop( pose_bones[ parent ], '["pole_vector"]')
        
        # FK limb follow
        if is_selected( fk_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["FK_limb_follow"]', slider = True )
        
        controls = ['upper_arm_ik.L', 'hand_ik.L', 'upper_arm_parent.L']
        ctrl    = 'upper_arm_parent.L'
        
        if is_selected( controls ):
            layout.prop( pose_bones[ ctrl ], '["IK_follow"]')
            if 'pole_follow' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["pole_follow"]', slider = True )
            if 'root/parent' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["root/parent"]', slider = True )
        

        
        controls = ['upper_arm_ik.R', 'upper_arm_fk.R', 'forearm_fk.R', 'hand_fk.R', 'hand_ik.R', 'MCH-hand_fk.R', 'upper_arm_parent.R']
        tweaks   = ['upper_arm_tweak.R.001', 'forearm_tweak.R', 'forearm_tweak.R.001']
        ik_ctrl  = ['hand_ik.R', 'MCH-upper_arm_ik.R', 'MCH-upper_arm_ik_target.R']
        fk_ctrl  = 'upper_arm_fk.R'
        parent   = 'upper_arm_parent.R'
        hand_fk   = 'hand_fk.R'
        pole = 'upper_arm_ik_target.R'
        
        # IK/FK Switch on all Control Bones
        if is_selected( controls ):
            layout.prop( pose_bones[parent], '["IK_FK"]', slider = True )
            props = layout.operator("pose.rigify_arm_fk2ik_" + rig_id, text="Snap FK->IK (" + fk_ctrl + ")")
            props.uarm_fk = controls[1]
            props.farm_fk = controls[2]
            props.hand_fk = controls[3]
            props.uarm_ik = controls[0]
            props.farm_ik = ik_ctrl[1]
            props.hand_ik = controls[4]
            props = layout.operator("pose.rigify_arm_ik2fk_" + rig_id, text="Snap IK->FK (" + fk_ctrl + ")")
            props.uarm_fk = controls[1]
            props.farm_fk = controls[2]
            props.hand_fk = controls[3]
            props.uarm_ik = controls[0]
            props.farm_ik = ik_ctrl[1]
            props.hand_ik = controls[4]
            props.pole = pole
            props.main_parent = parent
            props = layout.operator("rigify.rotation_pole", text="Switch Rotation-Pole")
            props.bone_name = controls[1]
            props.window = "CURRENT"
            props.toggle = True
            props.bake = False
        
        
        # BBone rubber hose on each Respective Tweak
        for t in tweaks:
            if is_selected( t ):
                layout.prop( pose_bones[ t ], '["rubber_tweak"]', slider = True )
        
        # IK Stretch and pole_vector on IK Control bone
        if is_selected( ik_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["IK_Stretch"]', slider = True )
            layout.prop( pose_bones[ parent ], '["pole_vector"]')
        
        # FK limb follow
        if is_selected( fk_ctrl ) or is_selected(parent):
            layout.prop( pose_bones[ parent ], '["FK_limb_follow"]', slider = True )
        
        controls = ['upper_arm_ik.R', 'hand_ik.R', 'upper_arm_parent.R']
        ctrl    = 'upper_arm_parent.R'
        
        if is_selected( controls ):
            layout.prop( pose_bones[ ctrl ], '["IK_follow"]')
            if 'pole_follow' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["pole_follow"]', slider = True )
            if 'root/parent' in pose_bones[ctrl].keys():
                layout.prop( pose_bones[ ctrl ], '["root/parent"]', slider = True )
        

        
        all_controls   = ['jaw_master', 'ear.L', 'ear.R', 'teeth.T', 'teeth.B', 'tongue_master', 'eye.L', 'eye.R', 'eyes', 'master_eye.L', 'master_eye.R', 'brow.B.L', 'brow.B.L.001', 'brow.B.L.002', 'brow.B.L.003', 'brow.B.L.004', 'brow.B.R', 'brow.B.R.001', 'brow.B.R.002', 'brow.B.R.003', 'brow.B.R.004', 'brow.T.L', 'brow.T.L.001', 'brow.T.L.002', 'brow.T.L.003', 'brow.T.R', 'brow.T.R.001', 'brow.T.R.002', 'brow.T.R.003', 'cheek.B.L.001', 'cheek.B.R.001', 'cheek.T.L.001', 'cheek.T.R.001', 'chin', 'chin.001', 'chin.002', 'chin.L', 'chin.R', 'ear.L.002', 'ear.L.003', 'ear.L.004', 'ear.R.002', 'ear.R.003', 'ear.R.004', 'jaw', 'jaw.L', 'jaw.L.001', 'jaw.R', 'jaw.R.001', 'lid.B.L', 'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', 'lid.B.R', 'lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003', 'lid.T.L', 'lid.T.L.001', 'lid.T.L.002', 'lid.T.L.003', 'lid.T.R', 'lid.T.R.001', 'lid.T.R.002', 'lid.T.R.003', 'lip.B.L.001', 'lip.B.R.001', 'lip.T.L.001', 'lips.L', 'lip.T.R.001', 'lips.R', 'nose', 'nose.001', 'nose.002', 'nose.003', 'nose.004', 'nose.005', 'nose.L', 'nose.L.001', 'nose.R', 'nose.R.001', 'tongue', 'tongue.001', 'tongue.002', 'tongue.003', 'lip.B', 'lip.T']
        jaw_ctrl_name  = 'jaw_master'
        eyes_ctrl_name = 'eyes'
        
        if is_selected(all_controls):
            layout.prop(pose_bones[jaw_ctrl_name],  '["mouth_lock"]', slider=True)
            layout.prop(pose_bones[eyes_ctrl_name], '["eyes_follow"]', slider=True)
        

class RigLayers(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rig Layers"
    bl_idname = rig_id + "_PT_rig_layers"

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=0, toggle=True, text='Face')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=1, toggle=True, text='Face (Primary)')
        row.prop(context.active_object.data, 'layers', index=2, toggle=True, text='Face (Secondary)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=3, toggle=True, text='Torso')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=4, toggle=True, text='Torso (Tweak)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=5, toggle=True, text='Fingers')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=6, toggle=True, text='Fingers (Tweak)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=7, toggle=True, text='Arm.L (IK)')
        row.prop(context.active_object.data, 'layers', index=10, toggle=True, text='Arm.R (IK)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=8, toggle=True, text='Arm.L (FK)')
        row.prop(context.active_object.data, 'layers', index=11, toggle=True, text='Arm.R (FK)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=9, toggle=True, text='Arm.L (Tweak)')
        row.prop(context.active_object.data, 'layers', index=12, toggle=True, text='Arm.R (Tweak)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=13, toggle=True, text='Leg.L (IK)')
        row.prop(context.active_object.data, 'layers', index=16, toggle=True, text='Leg.R (IK)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=14, toggle=True, text='Leg.L (FK)')
        row.prop(context.active_object.data, 'layers', index=17, toggle=True, text='Leg.R (FK)')

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=15, toggle=True, text='Leg.L (Tweak)')
        row.prop(context.active_object.data, 'layers', index=18, toggle=True, text='Leg.R (Tweak)')

        row = col.row()
        row.separator()
        row = col.row()
        row.separator()

        row = col.row()
        row.prop(context.active_object.data, 'layers', index=28, toggle=True, text='Root')


def register():
    bpy.utils.register_class(Rigify_Arm_FK2IK)
    bpy.utils.register_class(Rigify_Arm_IK2FK)
    bpy.utils.register_class(Rigify_Leg_FK2IK)
    bpy.utils.register_class(Rigify_Leg_IK2FK)
    bpy.utils.register_class(RigUI)
    bpy.utils.register_class(RigLayers)

def unregister():
    bpy.utils.unregister_class(Rigify_Arm_FK2IK)
    bpy.utils.unregister_class(Rigify_Arm_IK2FK)
    bpy.utils.unregister_class(Rigify_Leg_FK2IK)
    bpy.utils.unregister_class(Rigify_Leg_IK2FK)
    bpy.utils.unregister_class(RigUI)
    bpy.utils.unregister_class(RigLayers)

register()
