import bpy, bmesh, time
from .common import *

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

        ori_mode = context.object.mode
        ori_active = context.object

        objs = [context.object]
        objs.extend([o for o in context.selected_objects if o not in objs])
        objs.extend([o for o in context.objects_in_mode_unique_data if o not in objs])

        # Deselect all objects first if many objects is selected
        if len(objs) > 1:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

        for obj in objs:
            #obj = context.object
            context.view_layer.objects.active = obj
            obj.select_set(True)

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
                if len(objs) == 1:
                    self.report({'ERROR'}, "Need mirror modifier and it must be first")
                    return {'CANCELLED'}

                self.report({'WARNING'}, "Need mirror modifier and it must be first")
                continue

            # Check if mirror modifier has only one axis
            axis = [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]]
            axis_num = 0
            for a in axis:
                if a: axis_num += 1
            if axis_num > 1 or axis_num == 0:

                if len(objs) == 1:
                    self.report({'ERROR'}, "Can only flip with only one axis")
                    return {'CANCELLED'}

                self.report({'WARNING'}, "Can only flip with only one axis")
                continue

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
            self.use_mirror_udim = mod.use_mirror_udim
            self.mirror_offset_u = mod.mirror_offset_u
            self.mirror_offset_v = mod.mirror_offset_v
            self.offset_u = mod.offset_u
            self.offset_v = mod.offset_v
            self.mirror_object = mod.mirror_object
            self.merge_threshold = mod.merge_threshold

            # Disable merge and clip before applying
            mod.use_mirror_merge = False
            mod.use_clip = False

            # Get number of vertices
            num_verts = len(obj.data.vertices)

            # Apply mirror modifier
            apply_modifiers_with_shape_keys(obj, [mod.name])

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
            new_mod.use_mirror_u = self.use_mirror_u
            new_mod.use_mirror_v = self.use_mirror_v
            new_mod.use_mirror_udim = self.use_mirror_udim
            new_mod.mirror_offset_u = self.mirror_offset_u
            new_mod.mirror_offset_v = self.mirror_offset_v
            new_mod.offset_u = self.offset_u
            new_mod.offset_v = self.offset_v
            new_mod.mirror_object = self.mirror_object
            new_mod.merge_threshold = self.merge_threshold

            # Deselect current object if there are more than 1 objects
            if len(objs) > 1:
                bpy.ops.object.mode_set(mode='OBJECT')
                obj.select_set(False)

        # Recover selections and active object
        if len(objs) > 1:
            for obj in objs:
                obj.select_set(True)
            context.view_layer.objects.active = ori_active

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

class YFlipMultiresMesh(bpy.types.Operator):
    bl_idname = "mesh.y_flip_multires_mesh"
    bl_label = "Flip Multires Mesh"
    bl_description = "Flip Multires Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        scene = context.scene
        obj = context.object
        ori_mode = obj.mode
        ori_orientation = scene.transform_orientation_slots[0].type
        ori_select = obj.select_get()

        # Get multires modifier
        multires = [m for m in obj.modifiers if m.type == 'MULTIRES']
        if not multires:
            self.report({'ERROR'}, "Need mesh with multires modifier")
            return {'CANCELLED'}

        multires = multires[0]
        mod_name = multires.name

        # Remember multires props
        ori_levels = multires.levels

        # Get other modifiers
        mod_names = [m.name for m in obj.modifiers if m.type != multires]
        ori_mod_viewports = []
        for mname in mod_names:
            m = obj.modifiers.get(mname)
            ori_mod_viewports.append(m.show_viewport)
            m.show_viewport = False

        # Axis mirror will be based on first mirror modifier if available
        axis = 'x'
        mirrors = [m for m in obj.modifiers if m.type == 'MIRROR']
        if any(mirrors):
            first_mirror = mirrors[0]
            if first_mirror.use_axis[0]:
                axis = 'x'
            elif first_mirror.use_axis[1]:
                axis = 'y'
            elif first_mirror.use_axis[2]:
                axis = 'z'

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

        # Always select object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        # Mirror object and duplicate
        scene.transform_orientation_slots[0].type = 'LOCAL'
        bpy.ops.transform.mirror(constraint_axis=(axis=='x', axis=='y', axis=='z'))
        bpy.ops.object.duplicate()
        dup_obj = context.object

        # Apply multires
        multires.levels = multires.total_levels
        apply_modifiers_with_shape_keys(dup_obj, [multires.name])

        # Apply transform
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

        # Also flip vertex groups if using x axis
        if axis == 'x':
            flip_vertex_groups(obj)

        # Flip normal
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()

        bpy.ops.mesh.select_all(action='DESELECT')

        # Reselect
        bm = bmesh.from_edit_mesh(obj.data)
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

        bpy.ops.object.mode_set(mode='OBJECT')

        # Recover stuffs
        for i, mname in enumerate(mod_names):
            m = obj.modifiers.get(mname)
            m.show_viewport = ori_mod_viewports[i]

        multires = obj.modifiers.get(mod_name)
        multires.levels = ori_levels

        bpy.ops.object.mode_set(mode=ori_mode)
        scene.transform_orientation_slots[0].type = ori_orientation
        obj.select_set(ori_select)

        return {'FINISHED'}

class YApplyMultiresMirror(bpy.types.Operator):
    bl_idname = "mesh.y_apply_multires_mirror"
    bl_label = "Apply Multires Mirror"
    bl_description = "Apply Mirror modifier below Multires"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        scene = context.scene
        obj = context.object
        ori_orientation = scene.transform_orientation_slots[0].type

        # Get multires modifier
        multires = None
        mirror = None

        if len(obj.modifiers) > 0 and obj.modifiers[0].type == 'MULTIRES' and obj.modifiers[0].show_viewport:
            multires = obj.modifiers[0]
        multires_name = multires.name

        mirrors = [m for m in obj.modifiers if m.type == 'MIRROR' and m.show_viewport]
        if any(mirrors): mirror = mirrors[0]
            
        if not multires or not mirror:
            self.report({'ERROR'}, "Need mesh with both multires and mirror modifer enabled!")
            return {'CANCELLED'}

        # Set orientation
        scene.transform_orientation_slots[0].type = 'LOCAL'

        # Select object first
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        # Get props
        use_axis = [ua for ua in mirror.use_axis]
        use_merge = mirror.use_mirror_merge

        # Remove mirror modifier
        bpy.ops.object.modifier_remove(modifier=mirror.name)

        # Loop through mirror axis
        for i in range(3):
            if not use_axis[i]: continue

            # Duplicate and mirror
            bpy.ops.object.duplicate()
            bpy.ops.transform.mirror(constraint_axis=(i==0, i==1, i==2))
            dup = context.object
            obj.select_set(False)

            # Duplicate for applied multires
            bpy.ops.object.duplicate()
            dup_source = context.object

            # Apply multires
            mod = dup_source.modifiers.get(multires_name)
            mod.levels = multires.total_levels
            apply_modifiers_with_shape_keys(dup_source, [multires_name])

            # Apply transform
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

            # Back to actual object and apply transform
            dup_source.select_set(False)
            dup.select_set(True)
            context.view_layer.objects.active = dup
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

            # Reshape multires
            dup_source.select_set(True)
            bpy.ops.object.multires_reshape(modifier=multires_name)

            # Delete duplicated object
            dup.select_set(False)
            bpy.ops.object.delete()
            dup.select_set(True)

            # Flip normal
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.flip_normals()
            bpy.ops.mesh.select_all(action='DESELECT')

            # Back to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            # Join duplicated object to main object
            context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.join()

            # Merge objects using remove doubles
            # Not the best solution but it works most of the time
            if use_merge:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.region_to_loop()
                bpy.ops.mesh.remove_doubles()
                bpy.ops.mesh.select_all(action='DESELECT')

                # Back to object mode
                bpy.ops.object.mode_set(mode='OBJECT')

        scene.transform_orientation_slots[0].type = ori_orientation

        return {'FINISHED'}

def register():
    bpy.utils.register_class(YFlipMirrorModifier)
    bpy.utils.register_class(YFlipVertexGroups)
    bpy.utils.register_class(YFlipMultiresMesh)
    bpy.utils.register_class(YApplyMultiresMirror)

def unregister():
    bpy.utils.unregister_class(YFlipMirrorModifier)
    bpy.utils.unregister_class(YFlipVertexGroups)
    bpy.utils.unregister_class(YFlipMultiresMesh)
    bpy.utils.unregister_class(YApplyMultiresMirror)
