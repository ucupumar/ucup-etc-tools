import bpy
from bpy.props import *
from .common import *

THRES = 0.0

def any_vert_in_vgroup(group, mesh): 
    for vert in mesh.vertices:
        for vg in vert.groups:
            if vg.group == group.index:
                if vg.weight != 0.0:
                    return True
    return False

def any_mirror_in_modifiers(obj):
    for modf in obj.modifiers:
        if modf.type == 'MIRROR':
            return True
    return False

def remove_unused_vgs(objs):
    for o in objs:
        if o.type != 'MESH': continue

        mesh = o.data
        groups = o.vertex_groups
        mirrored = any_mirror_in_modifiers(o)
        
        # Remove empty groups
        if not mirrored:
            for group in groups:
                if not any_vert_in_vgroup(group, mesh):
                    groups.remove(group)
        else:
            for group in groups:
                if not any_vert_in_vgroup(group, mesh):
                    
                    #print(group.name)
                    
                    #if there's 'L' or 'R' in group name, check if mirrored_group have vertex
                    if '.L' in group.name or '.R' in group.name:
                        
                        if '.L' in group.name:
                            mirrored_group_name = group.name.replace('.L','.R')
                        else:
                            mirrored_group_name = group.name.replace('.R','.L')
                            
                        mirrored_group_index = groups.find(mirrored_group_name)
                        
                        if mirrored_group_index != -1:
                            mirrored_group = groups[mirrored_group_index]
                            
                            #if there are no vertex in mirrored group, remove the group
                            if not any_vert_in_vgroup(mirrored_group,mesh):
                                groups.remove(group)
                        else:
                            groups.remove(group)
                    else:
                        groups.remove(group)
                        
        # Remove zero verts
        for v in o.data.vertices:
            for g in v.groups:
                if g.weight <= THRES:
                    o.vertex_groups[g.group].remove([v.index])
            

class YRemoveunusedVG(bpy.types.Operator):
    bl_idname = "mesh.y_remove_unused_vertex_groups"
    bl_label = "Remove Unused Vertex Groups"
    bl_description = "Remove Unused Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        obj = context.object
        
        ori_mode = ''
        if obj.mode != 'OBJECT':
            ori_mode = obj.mode
            bpy.ops.object.mode_set()

        remove_unused_vgs(context.selected_objects)
                
        if ori_mode != '':
            bpy.ops.object.mode_set(mode=ori_mode)

        return {'FINISHED'}

class YMergeVGDown(bpy.types.Operator):
    bl_idname = "mesh.y_merge_vg_down"
    bl_label = "Merge Vertex Group Down"
    bl_description = "Merge active vertex group down"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj or obj.type != 'MESH': return False
        vgs = obj.vertex_groups
        active_vg = vgs.active
        return active_vg and vgs[-1] != active_vg

    def invoke(self, context, event):

        obj = context.object
        self.vg = obj.vertex_groups.active
        self.vg_index = -1

        # Get vg index
        for i, v in enumerate(obj.vertex_groups):
            if v == self.vg:
                self.vg_index = i
                break

        self.vg1_index = self.vg_index+1
        self.vg1 = obj.vertex_groups[self.vg1_index]

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):

        self.layout.label(text="Are you sure you want to merge vertex group")
        self.layout.label(text="'" + self.vg1.name + "' to '" + self.vg.name + "'?")

    def execute(self, context):

        obj = context.object

        # Merge vg
        for v in obj.data.vertices:
            for vg in v.groups:
                if vg.group == self.vg1_index:
                    obj.vertex_groups[self.vg_index].add([v.index],vg.weight,'ADD')
        
        # Remove merged vg
        obj.vertex_groups.remove(self.vg1)

        return {'FINISHED'}

class YTransferWeightsAndSetup(bpy.types.Operator):
    bl_idname = "mesh.y_transfer_weights_and_setup"
    bl_label = "Transfer Weights and Armature Setup"
    bl_description = "Transfer Weights and Armature Setup from last to other selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    put_new_mod_above_subsurf : BoolProperty(
            name = "Above Subsurf",
            description = "Put New Modifier above Subdivision Surface",
            default = True)

    do_normalize : BoolProperty(
            name = 'Use Normalize',
            description = "Do normalize all after transfer",
            default = True
            )

    @classmethod
    def poll(cls, context):
        obj = context.object
        objs = [o for o in context.selected_objects if o.type == 'MESH']
        return obj and obj.type == 'MESH' and len(objs) > 1

    def invoke(self, context, event):
        self.num_of_flags = 32
        return context.window_manager.invoke_props_dialog(self)

    def check(self, context):
        return True

    def draw(self, context):
        self.layout.prop(self, 'do_normalize')
        self.layout.prop(self, 'put_new_mod_above_subsurf')

    def execute(self, context):

        obj = ori_obj = context.object
        ori_objs = [o for o in context.selected_objects]
        objs = [o for o in context.selected_objects if o != obj and o.type == 'MESH']
        ori_mode = obj.mode

        # Check armature setup
        rig = None
        mod = [m for m in obj.modifiers if m.type == 'ARMATURE' and m.object and m.show_viewport]
        if mod: 
            mod = mod[0]
            rig = mod.object

        # Deselect all first
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        obj.select_set(True)

        for o in objs:
            # Select object
            context.view_layer.objects.active = o
            o.select_set(True)

            # Go to vertex paint mode
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

            try: 
                bpy.ops.object.data_transfer(use_reverse_transfer=True, data_type='VGROUP_WEIGHTS', vert_mapping='POLYINTERP_NEAREST', layers_select_src='NAME', layers_select_dst='ALL')
            except Exception as e: 
                print(e)

            # Set armature
            if rig: 
                # Check if armature already been set
                mod_founds = [m for m in o.modifiers if m.type == 'ARMATURE' and m.object == rig and m.show_render and m.show_viewport]
                if not mod_founds:
                    new_mod = o.modifiers.new('Armature', 'ARMATURE')
                    #new_mod.object = rig
                    for prop in dir(mod):
                        try: setattr(new_mod, prop, getattr(mod, prop))
                        except: pass

                    # Put new modifier above subsurf
                    if self.put_new_mod_above_subsurf:
                        subsurf_ids = [i for i, m in enumerate(o.modifiers) if m.type == 'SUBSURF']
                        if subsurf_ids:
                            cur_id = len(o.modifiers)-1
                            step = cur_id - subsurf_ids[0]
                            for i in range(step):
                                bpy.ops.object.modifier_move_up(modifier=new_mod.name)

                    # Check if object is parented to bone
                    if o.parent == rig and o.parent_type == 'BONE':
                        o.parent_type = 'OBJECT'

            if self.do_normalize:
                if is_bl_newer_than(4): 
                    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL')
                else: bpy.ops.object.vertex_group_normalize_all(group_select_mode='BONE_DEFORM')

            # Deselect object
            bpy.ops.object.mode_set(mode='OBJECT')
            o.select_set(False)

        # Remove unused vertex groups
        remove_unused_vgs(objs)

        # Recover selections
        for o in ori_objs: o.select_set(True)
        context.view_layer.objects.active = ori_obj
        bpy.ops.object.mode_set(mode=ori_mode)

        return {'FINISHED'}

class YWeightPaintEnableSelectBones(bpy.types.Operator):
    bl_idname = "mesh.y_weight_paint_enable_select_bones"
    bl_label = "Weight Paint with Bones Selection Mode"
    bl_description = "Enable select bones mode on weight paint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        obj = context.object

        rig = None

        # Search for the rig
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                if mod.object:
                    rig = mod.object
                    break

        if not rig:
            self.report({'ERROR'}, "No armature object found!")
            return {'CANCELLED'}

        # Go to weight paint mode
        if obj.mode != 'WEIGHT_PAINT':
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

        # Select rig object
        context.view_layer.objects.active = rig
        rig.select_set(True)

        # Go to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        # Back to original object
        context.view_layer.objects.active = obj

        return {'FINISHED'}

def register():
    bpy.utils.register_class(YRemoveunusedVG)
    bpy.utils.register_class(YMergeVGDown)
    bpy.utils.register_class(YTransferWeightsAndSetup)
    bpy.utils.register_class(YWeightPaintEnableSelectBones)

def unregister():
    bpy.utils.unregister_class(YRemoveunusedVG)
    bpy.utils.unregister_class(YMergeVGDown)
    bpy.utils.unregister_class(YTransferWeightsAndSetup)
    bpy.utils.unregister_class(YWeightPaintEnableSelectBones)
