import bpy, bmesh

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

def register():
    bpy.utils.register_class(YFlipMirrorModifier)
    bpy.utils.register_class(YFlipVertexGroups)
    bpy.utils.register_class(YFlipMultiresMesh)

def unregister():
    bpy.utils.unregister_class(YFlipMirrorModifier)
    bpy.utils.unregister_class(YFlipVertexGroups)
    bpy.utils.unregister_class(YFlipMultiresMesh)
