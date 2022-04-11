import bpy

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

class UCUPTOOLS_PT_outline_tools(bpy.types.Panel):
    bl_label = "Outline Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('object.y_add_outline', icon='OBJECT_DATA', text='Add Outline')
        c.operator('object.y_remove_outline', icon='OBJECT_DATA', text='Remove Outline')

class UCUPTOOLS_PT_vg_tools(bpy.types.Panel):
    bl_label = "Vertex Groups"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('mesh.y_remove_unused_vertex_groups', icon='MESH_DATA', text='Remove Unused Vertex Groups')
        c.operator('mesh.y_transfer_weights_and_setup', icon='MESH_DATA', text='Transfer Weights from last selected')

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

        c.operator('object.y_apply_rigify_to_metarig', icon='ARMATURE_DATA', text='Apply Rigify to Metarig')
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
        #c.separator()
        #c.operator('mesh.y_remove_unused_vertex_groups', icon='MESH_DATA', text='Remove Unused Vertex Groups')

class UCUPTOOLS_PT_subdiv_tools(bpy.types.Panel):
    bl_label = "Subdivision Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Ucup Etc"

    def draw(self, context):
        c = self.layout.column()
        c.operator('mesh.y_make_subsurf_last', icon='MOD_SUBSURF', text='Make Subsurf Last & Disable Autosmooth')
        c.alert = bpy.app.version >= (3, 1, 0) and context.preferences.system.use_gpu_subdivision
        c.operator('view3d.y_toggle_gpu_subdiv', icon='MOD_SUBSURF', text='Toggle GPU Subdiv')
        c.alert = False

def register():
    bpy.utils.register_class(UCUPTOOLS_PT_pose_helper)
    bpy.utils.register_class(UCUPTOOLS_PT_mirror_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_mesh_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_subdiv_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_vg_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_item_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_outline_tools)
    bpy.utils.register_class(UCUPTOOLS_PT_advanced)

def unregister():
    bpy.utils.unregister_class(UCUPTOOLS_PT_pose_helper)
    bpy.utils.unregister_class(UCUPTOOLS_PT_mirror_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_mesh_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_subdiv_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_vg_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_item_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_outline_tools)
    bpy.utils.unregister_class(UCUPTOOLS_PT_advanced)
