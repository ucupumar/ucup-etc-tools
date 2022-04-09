import bpy
from bpy.props import *

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

class YMakeSubsurfLast(bpy.types.Operator):
    bl_idname = "mesh.y_make_subsurf_last"
    bl_label = "Make Subsurf Last"
    bl_description = "Make Subsurf last on the modifier stack"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        objs = context.selected_objects
        ori_active_obj = context.object
        for obj in context.selected_objects:
            if hasattr(obj, 'modifiers') and any([m for m in obj.modifiers if m.type == 'SUBSURF']):
            #if obj.type == 'MESH' and any([m for m in obj.modifiers if m.type == 'SUBSURF']):
                context.view_layer.objects.active = obj
                mod_name = [m for m in obj.modifiers if m.type == 'SUBSURF'][0].name
                bpy.ops.object.modifier_move_to_index(modifier=mod_name, index=len(obj.modifiers)-1)

            if obj.type == 'MESH':
                obj.data.use_auto_smooth = False

        context.view_layer.objects.active = ori_active_obj

        return {'FINISHED'}

class YToggleGPUSubdiv(bpy.types.Operator):
    bl_idname = "view3d.y_toggle_gpu_subdiv"
    bl_label = "Toggle GPU Subdiv"
    bl_description = "Toggle GPU Subdiv Shortcut"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.app.version >= (3, 1, 0)

    def execute(self, context):
        context.preferences.system.use_gpu_subdivision = not context.preferences.system.use_gpu_subdivision
        return {'FINISHED'}

def register():
    bpy.utils.register_class(YUnionMeshes)
    bpy.utils.register_class(YShapeKeyReset)
    bpy.utils.register_class(YMakeSubsurfLast)
    bpy.utils.register_class(YToggleGPUSubdiv)

def unregister():
    bpy.utils.unregister_class(YUnionMeshes)
    bpy.utils.unregister_class(YShapeKeyReset)
    bpy.utils.unregister_class(YMakeSubsurfLast)
    bpy.utils.unregister_class(YToggleGPUSubdiv)
