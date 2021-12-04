bl_info = {
    "name": "Ucup Etc Tools",
    "author": "Yusuf Umar",
    "version": (0, 1, 1),
    "blender": (2, 80, 0),
    "location": "View 3D > Tool Shelf > Ucup Etc Tools",
    "description": "Miscellaneous tools for posing and stuff",
    "wiki_url": "https://github.com/ucupumar/ucup-etc-tools",
    "category": "Mesh",
}

import bpy, bmesh
from bpy.props import *

mirror_dict = {
        'left' : 'right',
        'Left' : 'Right',
        '.L' : '.R',
        '_L' : '_R',
        '.l' : '.r',
        '_l' : '_r'
        }

def get_mirror_name(name):

    # Split name for detect digit at the end
    splitnames = name.split('.')
    last_word = splitnames[-1]

    # If last word is digit, crop it
    extra = ''
    crop_name = name
    if last_word.isdigit() and len(splitnames) > 1:
        extra = '.' + last_word
        crop_name = name[:-len(last_word)-1]

    mir_name = ''
    for l, r in mirror_dict.items():

        if crop_name.endswith(l):
            ori = l
            mir = r
        elif crop_name.endswith(r):
            ori = r
            mir = l
        else:
            continue

        mir_name = crop_name[:-len(ori)] + mir + extra
        break

    return mir_name

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

def get_objects_rig_data(objs):
    pass

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

def apply_armatures(context, objs, child_objs, armature_modifier_names):
    for i, o in enumerate(objs):

        # Apply shapekeys
        if o.data.shape_keys:
            for sk in o.data.shape_keys.key_blocks:
                o.shape_key_remove(sk)

        # If object is multi user, make it single user
        if o.data.users > 1:
            o.data = o.data.copy()

        # Set object to active
        context.view_layer.objects.active = o

        # Check for mirror modifiers
        #if self.apply_above:
        #print(o.name)
        to_be_applied = []
        for mod in o.modifiers:
            if mod.type not in {'SUBSURF'}:
                to_be_applied.append(mod)
                #bpy.ops.object.modifier_apply(modifier=mod.name)
            if mod.name == armature_modifier_names[i]:
                break

        for mod in to_be_applied:
            bpy.ops.object.modifier_apply(modifier=mod.name)

        # Apply armature modifier
        bpy.ops.object.modifier_apply(modifier=armature_modifier_names[i])

    # Apply child of bones
    #bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for o in child_objs:
        o.select_set(True)

    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

def set_armature_back(context, rig, objs, child_objs, ori_mod_props, parent_bones, back_to_rigify=False):

    # Set armature back
    for i, o in enumerate(objs):

        # Set active object
        context.view_layer.objects.active = o

        num_mods = len(o.modifiers)

        mod = o.modifiers.new('Armature', 'ARMATURE')

        # Recover modifier props
        for prop in dir(mod):
            try: setattr(mod, prop, ori_mod_props[i][prop])
            except: pass

        mod.object = rig

        # Move up new modifier
        #if self.apply_above:
        for j in range(num_mods):
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
            if o.data and hasattr(o.data, 'shape_keys') and o.data.shape_keys:
                continue

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
                        to_be_applied.append(mod)
                    if mod.name == armods[i]:
                        break

            for mod in to_be_applied:
                bpy.ops.object.modifier_apply(modifier=mod.name)

            # Apply armature modifier
            bpy.ops.object.modifier_apply(modifier=armods[i])

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

def bmesh_vert_active(bm):
    if bm.select_history:
        elem = bm.select_history[-1]
        if isinstance(elem, bmesh.types.BMVert):
            return elem
    return None

def bmesh_edge_active(bm):
    if bm.select_history:
        elem = bm.select_history[-1]
        if isinstance(elem, bmesh.types.BMEdge):
            return elem
    return None

class YFlipMirrorModifier(bpy.types.Operator):
    bl_idname = "mesh.y_flip_mirror_modifier"
    bl_label = "Flip Mirror Modifier"
    bl_description = "Flip Mirror Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        obj = context.object
        ori_mode = obj.mode

        # Get mirror modifier
        mod = None
        mod_idx = -1
        for i, m in enumerate(obj.modifiers):
            if m.type == 'MIRROR':
                mod = m
                mod_idx = i
                break

        # Check if mirror modifier is first or not
        if mod_idx != 0:
            self.report({'ERROR'}, "Need mirror modifier and it must be first")
            return {'CANCELLED'}

        # Check if mirror modifier has only one axis
        axis = [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]]
        axis_num = 0
        for a in axis:
            if a: axis_num += 1
        if axis_num > 1 or axis_num == 0:
            self.report({'ERROR'}, "Can only flip with only one axis")
            return {'CANCELLED'}

        # Go to object mode to get selection
        bpy.ops.object.mode_set(mode='OBJECT')

        # Remember selection
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        sel_verts = [i for i, v in enumerate(bm.verts) if v.select]
        sel_edges = [i for i, e in enumerate(bm.edges) if e.select]
        sel_faces = [i for i, f in enumerate(bm.faces) if f.select]

        active_vert = bmesh_vert_active(bm)
        if active_vert: active_vert = active_vert.index

        active_edge = bmesh_edge_active(bm)
        if active_edge: active_edge = active_edge.index

        active_face = bm.faces.active
        if active_face: active_face = active_face.index

        bpy.ops.object.mode_set(mode='OBJECT')

        # Remember some variable
        self.use_mirror_merge = mod.use_mirror_merge
        self.use_clip = mod.use_clip
        self.use_mirror_vertex_groups = mod.use_mirror_vertex_groups
        self.use_mirror_u = mod.use_mirror_u
        self.use_mirror_v = mod.use_mirror_v
        self.mirror_object = mod.mirror_object

        # Disable merge and clip before applying
        mod.use_mirror_merge = False
        mod.use_clip = False

        # Get number of vertices
        num_verts = len(obj.data.vertices)

        # Apply mirror modifier
        #bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # Go to edit mode to delete half
        bpy.ops.object.mode_set(mode='EDIT')

        # Get bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        # Deselect all first
        bpy.ops.mesh.select_all(action='DESELECT')

        # Select all with index below num of verts before applying
        for i in range(0, num_verts):
            bm.verts[i].select = True

        # Delete half
        bpy.ops.mesh.delete(type='VERT')

        # Reselect
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for i in sel_verts:
            bm.verts[i].select = True
        for i in sel_edges:
            bm.edges[i].select = True
        for i in sel_faces:
            bm.faces[i].select = True
        if active_vert:
            bm.select_history.add(bm.verts[active_vert])
        if active_edge:
            bm.select_history.add(bm.edges[active_edge])
        if active_face:
            bm.faces.active = bm.faces[active_face]

        # Bring back modifier
        bpy.ops.object.modifier_add(type='MIRROR')

        # Move up new mirror modifier
        new_mod = obj.modifiers[-1]
        for i in range(len(obj.modifiers) - 1):
            bpy.ops.object.modifier_move_up(modifier = new_mod.name)

        # Bring back modifier attributes
        new_mod.use_axis[0] = axis[0]
        new_mod.use_axis[1] = axis[1]
        new_mod.use_axis[2] = axis[2]
        new_mod.use_mirror_merge = self.use_mirror_merge
        new_mod.use_clip = self.use_clip
        new_mod.use_mirror_vertex_groups = self.use_mirror_vertex_groups
        new_mod.mirror_object = self.mirror_object

        bpy.ops.object.mode_set(mode=ori_mode)

        return {'FINISHED'}

def flip_vertex_groups(obj):
    vg_founds = []
    for vg in obj.vertex_groups:
        if vg in vg_founds: continue

        vg_name = vg.name
        mir_name = get_mirror_name(vg.name)

        mir_vg = obj.vertex_groups.get(mir_name)
        if mir_vg:
            mir_vg.name = '_____TEMP____'
            vg.name = mir_name
            mir_vg.name = vg_name

            vg_founds.append(vg)
            vg_founds.append(mir_vg)

class YFlipVertexGroups(bpy.types.Operator):
    bl_idname = "mesh.y_flip_vertex_groups"
    bl_label = "Flip Vertex Groups"
    bl_description = "Flip Vertex Groups from L to R, or vice versa"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        flip_vertex_groups(context.object)
        return {'FINISHED'}

class YFlipMultiresMesh(bpy.types.Operator):
    bl_idname = "mesh.y_flip_multires_mesh"
    bl_label = "Flip Multires Mesh"
    bl_description = "Flip Multires Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        obj = context.object

        multires = [m for m in obj.modifiers if m.type == 'MULTIRES']
        if not multires:
            self.report({'ERROR'}, "Need mesh with multires modifier")
            return {'CANCELLED'}

        multires = multires[0]
        mod_name = multires.name

        # Always select object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        bpy.ops.transform.mirror(constraint_axis=(True, False, False), use_proportional_edit=False)
        bpy.ops.object.duplicate()

        dup_obj = context.object
        #bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod_name)
        bpy.ops.object.modifier_apply(modifier=mod_name)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Back to actual object and apply transform
        dup_obj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Reshape multires
        dup_obj.select_set(True)
        bpy.ops.object.multires_reshape(modifier=mod_name)

        # Delete duplicated object
        obj.select_set(False)
        bpy.ops.object.delete()
        obj.select_set(True)

        # Also flip vertex groups
        flip_vertex_groups(obj)

        # Flip normal
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

#class YResetMultiresFaces(bpy.types.Operator):
#    bl_idname = "mesh.y_reset_multires_faces"
#    bl_label = "Reset Multires Faces"
#    bl_description = "Reset Multires Faces"
#    bl_options = {'REGISTER', 'UNDO'}
#
#    @classmethod
#    def poll(cls, context):
#        obj = context.object
#        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'
#
#    def execute(self, context):
#        obj = context.object
#
#        bpy.ops.mesh.select_mirror()
#
#        return {'FINISHED'}

class YUnionMeshes(bpy.types.Operator):
    bl_idname = "mesh.y_union_meshes"
    bl_label = "Union Meshes"
    bl_description = "Do union boolean on selected meshes"
    bl_options = {'REGISTER', 'UNDO'}

    ignore_non_manifold : BoolProperty(
            name = "Ignore Non-manifold Meshes",
            description = 'Ignore non-manifold meshes',
            default = False)

    union_loose_parts : BoolProperty(
            name = "Union Loose Parts",
            description = 'Union loose parts within inside meshes',
            default = False)

    disable_subsurf : BoolProperty(
            name = "Disable Subsurf when joining",
            description = "Disable Subsurf modifier when joining",
            default = True)

    @classmethod
    def poll(cls, context):
        return context.object #and context.object.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self) #, width=420)

    def draw(self, context):
        self.layout.prop(self, 'ignore_non_manifold')
        self.layout.prop(self, 'union_loose_parts')
        self.layout.prop(self, 'disable_subsurf')

    def execute(self, context):
        obj = context.object
        objs = [o for o in context.selected_objects if o.type == 'MESH']
        ori_mode = obj.mode

        if obj.type != 'MESH' or not obj.select_get():
            self.report({'ERROR'}, "Active object must be selected and it must be a mesh")
            return {'CANCELLED'}

        if not self.union_loose_parts and len(objs) < 2:
            self.report({'ERROR'}, "Need at least two mesh objects selected!")
            return {'CANCELLED'}

        tool = bpy.context.tool_settings

        # Check for non manifold meshes
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        if not tool.mesh_select_mode[0]:
            #tool.mesh_select_mode = (True, False, False)
            bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Check non manifold
        if not self.ignore_non_manifold:
            for o in objs:
                selected_verts = list(filter(lambda v: v.select, o.data.vertices))
                if selected_verts:
                    bpy.ops.object.mode_set(mode='EDIT')
                    self.report({'ERROR'}, "Found non-manifold objects! Union cancelled!")
                    return {'FINISHED'}

        # Check if active object using subsurf modifier
        #subsurf_found = any([m for m in obj.modifiers if m.type == 'SUBSURF'])

        # Separate by loose parts
        if self.union_loose_parts:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')
            objs = [o for o in context.selected_objects if o.type == 'MESH']

        for o in objs:
            if o == obj: continue

            # Disable subsurf modifier 
            #if subsurf_found:
            if self.disable_subsurf:
                for mod in o.modifiers:
                    if mod.type == 'SUBSURF':
                        mod.levels = 0

            # Add boolean modifier to active object
            bpy.ops.object.modifier_add(type='BOOLEAN')
            boolmod = obj.modifiers[-1]
            boolmod.object = o
            boolmod.operation = 'UNION'

            # Apply modifier
            #bpy.ops.object.modifier_apply(apply_as='DATA', modifier=boolmod.name)
            bpy.ops.object.modifier_apply(modifier=boolmod.name)

        bpy.ops.object.select_all(action='DESELECT')
        # Delete objects
        for o in objs:
            if o == obj: continue
            o.select_set(True)
        bpy.ops.object.delete()

        # Back to select active object
        obj.select_set(True)

        #print('Aaaaa')
        return {'FINISHED'}

class YShapeKeyReset(bpy.types.Operator):
    bl_idname = "mesh.y_shape_key_reset"
    bl_label = "Reset Shape Key"
    bl_description = "Reset shape key value on selected vertices"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT' and obj.data.shape_keys

    def execute(self, context):

        obj = context.object
        mesh = obj.data
        keys = [obj.active_shape_key]

        if obj.active_shape_key.name == 'Basis':
            sks = [sk for sk in bpy.data.shape_keys if sk.user == mesh]
            if sks:
                keys = [key for key in sks[0].key_blocks if key != obj.active_shape_key]

        bpy.ops.object.mode_set(mode='OBJECT')

        for key in keys:
            for i, v in enumerate(mesh.vertices):
                if v.select:
                    #print(i, key.data[i].co, v.co)
                    key.data[i].co.x = v.co.x
                    key.data[i].co.y = v.co.y
                    key.data[i].co.z = v.co.z

        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class UCUPTOOLS_PT_pose_helper(bpy.types.Panel):
    bl_label = "Pose Helper"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('object.y_apply_armature', icon='ARMATURE_DATA', text='Apply Armature')

class UCUPTOOLS_PT_mirror_tools(bpy.types.Panel):
    bl_label = "Mirror Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('mesh.y_flip_mirror_modifier', icon='MOD_MIRROR', text='Flip Mirror Modifier')
        c.operator('mesh.y_flip_vertex_groups', icon='MOD_MIRROR', text='Flip Vertex Groups')
        c.operator('mesh.y_flip_multires_mesh', icon='MOD_MIRROR', text='Flip Multires Mesh')

        c.separator()

        #c.operator('mesh.y_reset_multires_faces', icon='FILE_REFRESH', text='Reset Mulitires Faces')

class UCUPTOOLS_PT_item_tools(bpy.types.Panel):
    bl_label = "Ucup Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"

    def draw(self, context):
        c = self.layout.column()
        #c.operator('object.y_reset_armature', icon='ARMATURE_DATA', text='Reset Armature')
        c.operator('mesh.y_flip_mirror_modifier', icon='MOD_MIRROR', text='Flip Mirror Modifier')
        c.operator('object.y_toggle_rest_pos', icon='ARMATURE_DATA', text='Toggle Rig Rest Position')

        obj = context.object
        scene = context.scene
        space = context.space_data

        if obj and obj.mode == 'EDIT':
            r = c.row()
            r.prop(space.overlay, 'show_weight') #, text='')
            if space.overlay.show_weight:
                r.prop(scene.tool_settings, 'vertex_group_user', expand=True) #, text='')

class UCUPTOOLS_PT_advanced(bpy.types.Panel):
    bl_label = "Advanced"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('object.y_toggle_rest_pos', icon='ARMATURE_DATA', text='Toggle Rig Rest Position')

        c.separator()

        c.operator('object.y_regenerate_rigify', icon='ARMATURE_DATA', text='Regenerate Rigify')

        c.separator()

        c.operator('object.y_apply_rigiy_deform', icon='ARMATURE_DATA', text='Apply Rigify Deform')

class UCUPTOOLS_PT_mesh_tools(bpy.types.Panel):
    bl_label = "Mesh Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('mesh.y_union_meshes', icon='MOD_BOOLEAN', text='Union Meshes')
        c.operator('mesh.y_shape_key_reset', icon='SHAPEKEY_DATA', text='Shape Key Reset')

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
    bpy.utils.register_class(YApplyRigifyDeform)
    bpy.utils.register_class(YApplyArmature)
    bpy.utils.register_class(YFlipMirrorModifier)
    bpy.utils.register_class(YFlipVertexGroups)
    bpy.utils.register_class(YFlipMultiresMesh)
    bpy.utils.register_class(YUnionMeshes)
    bpy.utils.register_class(YShapeKeyReset)
    bpy.utils.register_class(UCUPTOOLS_PT_pose_helper)
    bpy.utils.register_class(UCUPTOOLS_PT_mirror_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_mesh_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_item_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_advanced)
    bpy.utils.register_class(YAppliedBone)

    bpy.types.Armature.y_applied_bones = CollectionProperty(type=YAppliedBone)

def unregister():
    bpy.utils.unregister_class(YToggleRestPos)
    bpy.utils.unregister_class(YRegenerateRigify)
    bpy.utils.unregister_class(YApplyRigifyDeform)
    bpy.utils.unregister_class(YApplyArmature)
    bpy.utils.unregister_class(YFlipMirrorModifier)
    bpy.utils.unregister_class(YFlipVertexGroups)
    bpy.utils.unregister_class(YFlipMultiresMesh)
    bpy.utils.unregister_class(YUnionMeshes)
    bpy.utils.unregister_class(YShapeKeyReset)
    bpy.utils.unregister_class(UCUPTOOLS_PT_pose_helper)
    bpy.utils.unregister_class(UCUPTOOLS_PT_mirror_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_mesh_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_item_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_advanced)
    bpy.utils.unregister_class(YAppliedBone)
