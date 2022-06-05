import bpy, bmesh
from bpy.props import *
from .common import *

class YToggleRestPos(bpy.types.Operator):
    bl_idname = "object.y_toggle_rest_pos"
    bl_label = "Toggle Rig Rest Position"
    bl_description = "Toggle active armature rest position"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type in {'MESH', 'ARMATURE'}

    def execute(self, context):
        obj = context.object

        if obj.type == 'MESH':

            # Get armature modifier
            arm_obj = None
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    arm_obj = mod.object
                    break

            if not arm_obj:
                self.report({'ERROR'}, "No armature object found!")
                return {'CANCELLED'}

            obj = arm_obj

        pos = obj.data.pose_position
        obj.data.pose_position = 'REST' if pos == 'POSE' else 'POSE'

        return {'FINISHED'}

def get_def_parent_name(bone, ori_bone, def_bones, parent_name=''):

    if bone.parent:
        #print(bone.parent.name)

        if bone.parent.name.startswith('ORG-') or bone.parent.name.startswith('MCH-'):
            basename = bone.parent.name[4:]
        else: basename = bone.parent.name

        if def_bones.get(basename):
            parent_name = basename

        if parent_name == '':
            def_name = 'DEF-' + basename
            if def_name != ori_bone.name and def_bones.get(def_name):
                parent_name = def_name

        if parent_name == '':
            parent_name = get_def_parent_name(bone.parent, ori_bone, def_bones, parent_name)

    return parent_name

def get_all_objects_using_rig_with_datas(rig):

    objs = []
    armods = []
    ori_mod_props = []
    ori_mod_idx = []

    child_objs = []
    parent_bones = []
    for o in bpy.context.view_layer.objects:

        if o.type == 'MESH':
            for i, mod in enumerate(o.modifiers):
                if mod.type == 'ARMATURE' and mod.object == rig:
                    objs.append(o)
                    armods.append(mod.name)
                    ori_mod_idx.append(i)

                    # Get original modifier props
                    dicts = {}
                    for prop in dir(mod):
                        try: dicts[prop] = getattr(mod, prop)
                        except: pass
                    ori_mod_props.append(dicts)

                    break

        if o.parent == rig and o.parent_type == 'BONE':
            child_objs.append(o)
            parent_bones.append(o.parent_bone)

    return objs, armods, ori_mod_props, ori_mod_idx, child_objs, parent_bones

def apply_armatures(context, objs, child_objs, armature_modifier_names, apply_above=True):

    #armature_ids = []

    for i, o in enumerate(objs):
        #print(o, armature_modifier_names[i])

        # Apply shapekeys
        #if o.data.shape_keys:
        #    for sk in o.data.shape_keys.key_blocks:
        #        o.shape_key_remove(sk)

        # If object is multi user, make it single user
        if o.data.users > 1:
            o.data = o.data.copy()

        # Set object to active
        context.view_layer.objects.active = o

        # Check for other modifiers
        if apply_above:
            to_be_applied = []
            for mod in o.modifiers:
                if mod.type not in {'SUBSURF'}:
                    to_be_applied.append(mod.name)
                if mod.name == armature_modifier_names[i]:
                    break

            apply_modifiers_with_shape_keys(o, to_be_applied)
            #for mod in to_be_applied:
            #    try: bpy.ops.object.modifier_apply(modifier=mod)
            #    except Exception as e: pass

    # Apply armature modifier
    for i, o in enumerate(objs):
        context.view_layer.objects.active = o
        #armature_ids.append([j for j, m in enumerate(o.modifiers) if m.name == armature_modifier_names[i]][0])
        #try: bpy.ops.object.modifier_apply(modifier=armature_modifier_names[i])
        #except Exception as e: pass
        apply_modifiers_with_shape_keys(o, [armature_modifier_names[i]], False)

    # Apply child of bones
    #bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for o in child_objs:
        o.select_set(True)

    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    #return armature_ids

def set_armature_back(context, rig, objs, child_objs, ori_mod_props, parent_bones, ori_mod_ids=[], back_to_rigify=False):

    # Set armature back
    for i, o in enumerate(objs):

        # Set active object
        context.view_layer.objects.active = o

        num_mods = len(o.modifiers)

        if len(ori_mod_ids) > i:
            ori_mod_idx = ori_mod_ids[i]
        else: ori_mod_idx = 0

        mod = o.modifiers.new('Armature', 'ARMATURE')

        # Recover modifier props
        for prop in dir(mod):
            try: setattr(mod, prop, ori_mod_props[i][prop])
            except: pass

        mod.object = rig

        # Move up new modifier
        #if self.apply_above:
        for j in range(num_mods-ori_mod_idx):
            bpy.ops.object.modifier_move_up(modifier=mod.name)
        #else:
        #    for j in range(num_mods-ori_mod_idx[i]):
        #        bpy.ops.object.modifier_move_up(modifier=mod.name)

    bpy.ops.object.select_all(action='DESELECT')

    # Set back bone parent

    rig.select_set(True)
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')

    if back_to_rigify:
        rig.data.layers[29] = True

    for i, o in enumerate(child_objs):
        o.select_set(True)
        name = parent_bones[i]
        pbone = rig.pose.bones.get(name)
        if not pbone:
            if not back_to_rigify:
                pbone = rig.pose.bones.get('DEF-'+name)

                if name == 'head':
                    pbone = rig.pose.bones.get('DEF-spine.006')
                elif name == 'neck':
                    pbone = rig.pose.bones.get('DEF-spine.004')

            else:
                if name == 'DEF-spine.006':
                    pbone = rig.pose.bones.get('head')
                elif name == 'DEF-spine.004':
                    pbone = rig.pose.bones.get('neck')
                elif name.startswith('DEF-'):
                    pbone = rig.pose.bones.get(name[4:])

        if pbone:
            pbone.bone.select = True
            rig.data.bones.active = pbone.bone

            bpy.ops.object.parent_set(type='BONE')

            o.select_set(False)
            pbone.bone.select = False

    if back_to_rigify:
        rig.data.layers[29] = False

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

class YAppyRigifyToMetarig(bpy.types.Operator):
    bl_idname = "object.y_apply_rigify_to_metarig"
    bl_label = "Apply Rigify to Metarig"
    bl_description = "Apply rigify transform to metarig and regerate rigify back"
    bl_options = {'REGISTER', 'UNDO'}

    apply_above : BoolProperty(
            name = "Apply Above Modifiers",
            description = 'Apply modifiers above armature',
            default = False)

    @classmethod
    def poll(cls, context):
        #return context.object and context.object.type in {'ARMATURE'}
        return context.object and context.object.type == 'ARMATURE' #and context.object.data.get("rig_id") is None

    def execute(self, context):
        if not hasattr(bpy.ops.pose, 'rigify_generate'):
            self.report({'ERROR'}, "Rigify addon need to be installed!")
            return {'CANCELLED'}

        # Get rigify
        rigify = context.object

        # Get metarig
        metarig = None
        for o in context.view_layer.objects:
            if o.type == 'ARMATURE' and hasattr(o.data, 'rigify_target_rig') and o.data.rigify_target_rig == rigify:
                metarig = o
                break

        if not metarig:
            self.report({'ERROR'}, "Metarig is not found!")
            return {'CANCELLED'}

        # Unhide metarig
        ori_metarig_hide = metarig.hide_viewport
        metarig.hide_viewport = False
        metarig.hide_set(False)

        # Get metarig parents
        metarig_layer_cols = get_object_parent_layer_collections([], bpy.context.view_layer.layer_collection, metarig)
        ori_metarig_hide_lcs = []
        ori_metarig_hide_lccs = []
        for lc in metarig_layer_cols:
            ori_metarig_hide_lcs.append(lc.hide_viewport)
            lc.hide_viewport = False
            ori_metarig_hide_lccs.append(lc.collection.hide_viewport)
            lc.collection.hide_viewport = False

        # Get objects using rig
        objs, armods, ori_mod_props, ori_mod_idx, child_objs, parent_bones = get_all_objects_using_rig_with_datas(rigify)

        # Apply armature and modifiers above
        apply_armatures(context, objs, child_objs, armods, apply_above=self.apply_above)

        # Copy deform bones to metarig

        for pb in metarig.pose.bones:
            c = pb.constraints.new('COPY_TRANSFORMS')
            c.target = rigify
            c.subtarget = 'DEF-' + pb.name
        
        # Apply armature deform
        context.view_layer.objects.active = metarig
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.visual_transform_apply()
        bpy.ops.pose.constraints_clear()
        bpy.ops.pose.armature_apply(selected=False)

        # Set armature back to rigify
        set_armature_back(context, rigify, objs, child_objs, ori_mod_props, parent_bones, ori_mod_ids=ori_mod_idx, back_to_rigify=True)

        # Regerate rigify
        context.view_layer.objects.active = metarig
        bpy.ops.object.y_regenerate_rigify()

        # Recover state
        context.view_layer.objects.active = rigify
        metarig.hide_viewport = ori_metarig_hide
        #metarig.hide_set(ori_metarig_hide)

        for i, lc in enumerate(metarig_layer_cols):
            lc.hide_viewport = ori_metarig_hide_lcs[i]
            lc.collection.hide_viewport = ori_metarig_hide_lccs[i]

        return {'FINISHED'}

class YApplyRigifyDeform(bpy.types.Operator):
    bl_idname = "object.y_apply_rigiy_deform"
    bl_label = "Apply Rigify Deform"
    bl_description = "Apply Rigify Deform"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type in {'ARMATURE'}
        #return context.object and context.object.type == 'ARMATURE' and context.active_object.data.get("rig_id") is None

    def execute(self, context):

        if not hasattr(bpy.ops.pose, 'rigify_generate'):
            self.report({'ERROR'}, "Rigify addon need to be installed!")
            return {'CANCELLED'}

        scene = context.scene
        ori = context.object

        # RECOVER RIG

        if ori.name.startswith('APPLIED-'):
            # Get original rig
            rig = context.view_layer.objects.get(ori.name[8:])
            if not rig: return {'CANCELLED'}

            # Unhide original rig
            rig.hide_set(False)
            rig.hide_viewport = False
            rig.data.pose_position = 'REST'

            # Get objects using rig
            objs, armods, ori_mod_props, ori_mod_idx, child_objs, parent_bones = get_all_objects_using_rig_with_datas(ori)

            # Remove parents
            context.view_layer.objects.active = ori
            ori.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            for bone in ori.data.edit_bones:
                bone.parent = None

            # Add constraints
            bpy.ops.object.mode_set(mode='POSE')
            for bone in ori.pose.bones:
                c = bone.constraints.new('COPY_TRANSFORMS')
                c.target = rig
                c.subtarget = bone.name

            bpy.ops.object.mode_set(mode='OBJECT')

            #return {'FINISHED'}

            # Apply armature and modifiers above
            apply_armatures(context, objs, child_objs, armods)

            # Apply armature deform
            context.view_layer.objects.active = ori
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.armature_apply(selected=False)

            # Remove constraints
            for bone in ori.pose.bones:
                for bc in bone.constraints:
                    bone.constraints.remove(bc)

            # Get rigify bone length
            bpy.context.view_layer.objects.active = rig
            bpy.ops.object.mode_set(mode='POSE')
            lengths = {}
            for b in ori.data.bones:
                bone = rig.pose.bones.get(b.name)
                lengths[b.name] = abs((bone.tail - bone.head).length)
            bpy.ops.object.mode_set(mode='OBJECT')
                
            # Scale bones according to proportions
            bpy.context.view_layer.objects.active = ori
            for bone in ori.pose.bones:
                l = abs((bone.tail - bone.head).length)
                proportion = lengths[bone.name] / l
                bone.scale.y *= proportion

            # Set armature back to ori
            set_armature_back(context, ori, objs, child_objs, ori_mod_props, parent_bones, back_to_rigify=False)
            objs, armods, ori_mod_props, ori_mod_idx, child_objs, parent_bones = get_all_objects_using_rig_with_datas(ori)

            # Apply again
            apply_armatures(context, objs, child_objs, armods)

            #return {'FINISHED'}

            # Scale some bones

            # Delete applied rig
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = ori
            ori.select_set(True)
            bpy.ops.object.delete()

            # Set armature back again
            set_armature_back(context, rig, objs, child_objs, ori_mod_props, parent_bones, back_to_rigify=True)

            context.view_layer.objects.active = rig
            rig.select_set(True)

            rig.data.pose_position = 'POSE'

            return {'FINISHED'}

        # APPLY RIG

        # Get objects using rig
        objs, armods, ori_mod_props, ori_mod_idx, child_objs, parent_bones = get_all_objects_using_rig_with_datas(ori)

        # Apply armature and modifiers above
        apply_armatures(context, objs, child_objs, armods)
        #return {'FINISHED'}

        # Copy rig object
        rig = ori.copy()
        rig.data = rig.data.copy()
        scene.collection.objects.link(rig)
        context.view_layer.objects.active = rig
        rig.select_set(True)
        ori.select_set(False)
        rig.name = 'APPLIED-' + ori.name

        # Remove drivers
        for d in reversed(rig.animation_data.drivers):
            rig.animation_data.drivers.remove(d)
        for d in reversed(rig.data.animation_data.drivers):
            rig.data.animation_data.drivers.remove(d)

        # Remove non deform bones
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in rig.data.edit_bones:
            if not bone.use_deform:
                rig.data.edit_bones.remove(bone)

        # Remove constraints
        bpy.ops.object.mode_set(mode='POSE')
        for bone in rig.pose.bones:
            for bc in bone.constraints:
                bone.constraints.remove(bc)

        # Set layer
        for i in range(32):
            rig.data.layers[i] = True

        # Get missing parents
        bpy.ops.object.mode_set(mode='EDIT')
        parent_dict = {}
        for bone in rig.data.edit_bones:
            ori_bone = ori.data.bones[bone.name]

            if not bone.parent:
                #print()
                parent_name = get_def_parent_name(ori_bone, ori_bone, rig.data.bones)
                #print(parent_name)
                bone.parent = rig.data.edit_bones.get(parent_name)

            if bone.parent:
                parent_dict[bone.name] = bone.parent.name

        # Temporarily remove all parents for saving scale data
        for bone in rig.data.edit_bones:
            bone.parent = None

        # Unlock transformation
        bpy.ops.object.mode_set(mode='POSE')
        for bone in rig.pose.bones:

            bone.lock_location[0] = False
            bone.lock_location[1] = False
            bone.lock_location[2] = False

            bone.lock_rotation_w = False
            bone.lock_rotation[0] = False
            bone.lock_rotation[1] = False
            bone.lock_rotation[2] = False

            bone.lock_scale[0] = False
            bone.lock_scale[1] = False
            bone.lock_scale[2] = False

        # Add constraints
        for bone in rig.pose.bones:
            c = bone.constraints.new('COPY_TRANSFORMS')
            c.target = ori
            c.subtarget = bone.name

        # Bake constraint
        #bpy.ops.nla.bake(frame_start=1, frame_end=1, only_selected=False, visual_keying=True, clear_constraints=True, bake_types={'POSE'})        

        # Remove action
        #action = rig.animation_data.action
        #rig.animation_data.action = None
        #bpy.data.actions.remove(action)

        ## Save scale data
        #for bone in rig.pose.bones:
        #    b = rig.data.y_applied_bones.add()
        #    b.name = bone.name
        #    b.scale = (bone.scale[0], bone.scale[1], bone.scale[2])

        #for b in rig.data.y_applied_bones:
        #    print(b.name, b.scale[0], b.scale[1], b.scale[2])

        # Apply pose
        bpy.ops.pose.armature_apply(selected=False)

        #return {'FINISHED'}

        # Remove constraints
        bpy.ops.object.mode_set(mode='POSE')
        for bone in rig.pose.bones:
            for bc in bone.constraints:
                bone.constraints.remove(bc)

        # Reparent
        bpy.ops.object.mode_set(mode='EDIT')
        for key, val in parent_dict.items():
            bone = rig.data.edit_bones.get(key)
            parent = rig.data.edit_bones.get(val)
            if bone and parent: bone.parent = parent

        bpy.ops.object.mode_set(mode='OBJECT')

        # Set armature back
        set_armature_back(context, rig, objs, child_objs, ori_mod_props, parent_bones, back_to_rigify=False)

        context.view_layer.objects.active = rig
        rig.select_set(True)

        # Hide original rig
        ori.hide_set(True)
        ori.hide_viewport = True

        return {'FINISHED'}

class YRegenerateRigify(bpy.types.Operator):
    bl_idname = "object.y_regenerate_rigify"
    bl_label = "Regenerate Rigify"
    bl_description = "Regenerate Rigify and make sure all the pose bones transform stays"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        #return context.object and context.object.type in {'ARMATURE'}
        return context.object and context.object.type == 'ARMATURE' and context.object.data.get("rig_id") is None

    def execute(self, context):

        if not hasattr(bpy.ops.pose, 'rigify_generate'):
            self.report({'ERROR'}, "Rigify addon need to be installed!")
            return {'CANCELLED'}

        metarig = context.object

        rig = metarig.data.rigify_target_rig
        rig_name = rig.name

        if not rig:
            self.report({'ERROR'}, "Target rig need to be set!")
            return {'CANCELLED'}

        # Remember stuffs
        ori_mode = rig.mode
        rig_data_dict = {}
        props = dir(rig.data)
        for prop in props:
            if prop.startswith('__') or prop in ['bl_rna', 'rna_type']: continue
            try: rig_data_dict[prop] = getattr(rig.data, prop)
            except: 
                print('Cannot get prop', prop, 'from', rig.data.name)
                continue
        #ori_pose_position = rig.data.pose_position

        # Make sure to unhide rig
        rig.hide_set(False)

        # Set rig object to active
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        # Enable all layers
        ori_layer_enables = []
        for i in range(32):
            if rig.data.layers[i]: ori_layer_enables.append(i)
            rig.data.layers[i] = True

        # Copy all pose bones
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.copy()

        # Check contraints that need to be kept
        pbcos = {}
        for pb in rig.pose.bones:
            for co in pb.constraints:
                if co.name.startswith('KEEP-'):
                    if pb.name not in pbcos:
                        pbcos[pb.name] = []
                    co_dict = {}
                    props = dir(co)
                    for prop in props:
                        if prop.startswith('__') or prop in ['bl_rna', 'rna_type']: continue
                        try: co_dict[prop] = getattr(co, prop)
                        except:
                            print('Cannot get prop', prop, 'from', co.name)
                            continue

                    pbcos[pb.name].append(co_dict)

        # Check NLA data (still incomplete since this only keep basic action data)
        acts = []
        frame_starts = []
        for track in rig.animation_data.nla_tracks:
            if len(track.strips) == 0: continue
            strip = track.strips[0]
            acts.append(strip.action)
            frame_starts.append(strip.frame_start)

        # Get action
        action = rig.animation_data.action

        # Regenerate rigify
        context.view_layer.objects.active = metarig
        bpy.ops.pose.rigify_generate()

        # Paste to new rig
        rig = bpy.data.objects.get(rig_name)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        bpy.ops.pose.paste()

        # Recreate constraints
        for pb_name, co_lists in pbcos.items():
            pb = rig.pose.bones.get(pb_name)
            if not pb: 
                print('No bone named', pb_name)
                continue

            for co_dict in co_lists:
                co = pb.constraints.new(co_dict['type'])
                for key, value in co_dict.items():
                    try: setattr(co, key, value)
                    except: pass

        # Set action
        rig.animation_data.action = action

        # Recover NLA data
        for i, act in enumerate(acts):
            track = rig.animation_data.nla_tracks.new()
            strip = track.strips.new(act.name, int(frame_starts[i]), act)

        # Enable layers
        for i in range(32):
            rig.data.layers[i] = True if i in ori_layer_enables else False

        # Recover stuffs
        bpy.ops.object.mode_set(mode=ori_mode, toggle=False)
        #rig.data.pose_position = ori_pose_position 
        for key, value in rig_data_dict.items():
            try: setattr(rig.data, key, value)
            except: pass

        return {'FINISHED'}

class YApplyArmature(bpy.types.Operator):
    bl_idname = "object.y_apply_armature"
    bl_label = "Advanced Apply Armature"
    bl_description = "Apply Armature as Rest Pose and all meshes using it will also follows"
    bl_options = {'REGISTER', 'UNDO'}

    apply_above : BoolProperty(
            name = "Apply Above Modifiers",
            description = 'Apply modifiers above armature',
            default = True)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type in {'MESH', 'ARMATURE'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        self.layout.label(text='WARNING: Multi user objects will be single user if using the armature deform', icon='ERROR')
        self.layout.label(text='(Object with bone parent will not affected though)', icon='ERROR')
        self.layout.prop(self, 'apply_above', text='Apply Modifiers above armature')

    def execute(self, context):
        obj = context.object

        rig_obj = None
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    rig_obj = mod.object
                    break
        elif obj.type == 'ARMATURE':
            rig_obj = obj

        if not rig_obj:
            self.report({'ERROR'}, "No rig object found!")
            return {'CANCELLED'}

        # Never forget
        ori_selects = [o for o in context.view_layer.objects if o.select_get()]
        ori_hide_viewports = [o for o in context.view_layer.objects if o.hide_viewport]
        ori_hide_selects = [o for o in context.view_layer.objects if o.hide_select]
        ori_active = obj
        ori_mode = obj.mode

        ori_col_hide_viewports = [col for col in context.view_layer.layer_collection.children if col.hide_viewport]
        ori_col_hide_selects = [col for col in bpy.data.collections if col.hide_select]

        # Unhide all
        for o in context.view_layer.objects:
            if o.hide_viewport:
                o.hide_viewport = False
            if o.hide_select:
                o.hide_select = False

        for col in context.view_layer.layer_collection.children:
            if col.hide_viewport:
                col.hide_viewport = False

        for col in bpy.data.collections:
            if col.hide_select:
                col.hide_select = False

        #return {'FINISHED'}

        # Go to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # Get all objects using the rig
        objs = []
        armods = []
        ori_mod_props = []
        ori_mod_idx = []

        child_objs = []
        parent_bones = []

        for o in context.view_layer.objects:

            # Check if objects has shape keys
            #if o.data and hasattr(o.data, 'shape_keys') and o.data.shape_keys:
            #    continue

            if o.type == 'MESH':
                for i, mod in enumerate(o.modifiers):
                    if mod.type == 'ARMATURE' and mod.object == rig_obj:
                        objs.append(o)
                        armods.append(mod.name)
                        ori_mod_idx.append(i)

                        # Get original modifier props
                        dicts = {}
                        for prop in dir(mod):
                            try: dicts[prop] = getattr(mod, prop)
                            except: pass
                        ori_mod_props.append(dicts)

                        break

            if o.parent == rig_obj and o.parent_type == 'BONE':
                child_objs.append(o)
                parent_bones.append(o.parent_bone)

        # Apply armature and modifiers above
        for i, o in enumerate(objs):

            # If object is multi user, make it single user
            if o.data.users > 1:
                o.data = o.data.copy()

            # Set object to active
            context.view_layer.objects.active = o

            # Check for mirror modifiers
            to_be_applied = []
            if self.apply_above:
                for mod in o.modifiers:
                    if mod.type not in {'SUBSURF'}:
                        #bpy.ops.object.modifier_apply(modifier=mod.name)
                        to_be_applied.append(mod.name)
                    if mod.name == armods[i]:
                        break

            #for mod in to_be_applied:
            #    bpy.ops.object.modifier_apply(modifier=mod.name)
            apply_modifiers_with_shape_keys(o, to_be_applied)

            # Apply armature modifier
            #bpy.ops.object.modifier_apply(modifier=armods[i])
            apply_modifiers_with_shape_keys(o, [armods[i]], False)

        # Apply child of bones
        for o in child_objs:
            o.select_set(True)

        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

        # Apply armature
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = rig_obj
        rig_obj.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply(selected=False)

        # Back to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # Set armature back
        for i, o in enumerate(objs):

            # Set active object
            context.view_layer.objects.active = o

            num_mods = len(o.modifiers)

            mod = o.modifiers.new('Armature', 'ARMATURE')
            #mod.object = rig_obj

            # Recover modifier props
            for prop in dir(mod):
                try: setattr(mod, prop, ori_mod_props[i][prop])
                except: pass

            # Move up new modifier
            if self.apply_above:
                for j in range(num_mods):
                    bpy.ops.object.modifier_move_up(modifier=mod.name)
            else:
                for j in range(num_mods-ori_mod_idx[i]):
                    bpy.ops.object.modifier_move_up(modifier=mod.name)

        bpy.ops.object.select_all(action='DESELECT')

        # Set back bone parent

        rig_obj.select_set(True)
        context.view_layer.objects.active = rig_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')

        for i, o in enumerate(child_objs):
            o.select_set(True)
            pbone = rig_obj.pose.bones.get(parent_bones[i])
            pbone.bone.select = True
            rig_obj.data.bones.active = pbone.bone

            bpy.ops.object.parent_set(type='BONE')

            o.select_set(False)
            pbone.bone.select = False

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # Recover hide and select

        for col in ori_col_hide_viewports:
            col.hide_viewport = True 

        for col in ori_col_hide_selects:
            col.hide_select = True

        for o in ori_hide_selects:
            o.hide_select = True

        for o in ori_hide_viewports:
            o.hide_viewport = True

        for o in ori_selects:
            o.select_set(True)

        context.view_layer.objects.active = ori_active
        bpy.ops.object.mode_set(mode=ori_mode)

        return {'FINISHED'}

class YAppliedBone(bpy.types.PropertyGroup):
    name : StringProperty(default='')
    scale : FloatVectorProperty(
            size=3, #precision=3, 
            default=(1.0, 1.0, 1.0),
            )
    #rotation_mode = StringProperty(default='')
    #rotation_quaternion = FloatVectorProperty(
    #        size=4, #precision=3, 
    #        default=(0.0, 0.0, 0.0, 0.0),
    #        )

def register():
    bpy.utils.register_class(YToggleRestPos)
    bpy.utils.register_class(YRegenerateRigify)
    bpy.utils.register_class(YAppyRigifyToMetarig)
    bpy.utils.register_class(YApplyRigifyDeform)
    bpy.utils.register_class(YApplyArmature)
    bpy.utils.register_class(YAppliedBone)

    bpy.types.Armature.y_applied_bones = CollectionProperty(type=YAppliedBone)

def unregister():
    bpy.utils.unregister_class(YToggleRestPos)
    bpy.utils.unregister_class(YRegenerateRigify)
    bpy.utils.unregister_class(YAppyRigifyToMetarig)
    bpy.utils.unregister_class(YApplyRigifyDeform)
    bpy.utils.unregister_class(YApplyArmature)
    bpy.utils.unregister_class(YAppliedBone)
