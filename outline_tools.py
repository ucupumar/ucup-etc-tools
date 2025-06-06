import bpy
from bpy.props import *
from bpy.app.handlers import persistent
from .common import *

OUTLINE_MAT_NAME = 'Outline'

def get_outline_mat(col, bsdf_type):
    mat = bpy.data.materials.get(OUTLINE_MAT_NAME)
    if not mat:
        mat = bpy.data.materials.new(OUTLINE_MAT_NAME)
        mat.use_nodes = True
        tree = mat.node_tree

        mat.use_backface_culling = True
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'

        # Remove default principled bsdf
        bsdf = tree.nodes.get('Principled BSDF')
        if bsdf: tree.nodes.remove(bsdf)

        # Create new bsdf
        dif_bsdf = tree.nodes.new('ShaderNodeBsdfDiffuse')
        emi_bsdf = tree.nodes.new('ShaderNodeEmission')

        geom = tree.nodes.new('ShaderNodeNewGeometry')
        path = tree.nodes.new('ShaderNodeLightPath')
        transp = tree.nodes.new('ShaderNodeBsdfTransparent')
        mix_0 = tree.nodes.new('ShaderNodeMixShader')
        mix_1 = tree.nodes.new('ShaderNodeMixShader')
        mix_2 = tree.nodes.new('ShaderNodeMixShader')

        try: outp = [n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output][0]
        except: return None

        path.location = (0, 0)
        geom.location = (0, -350)
        emi_bsdf.location = (200, 0)
        dif_bsdf.location = (200, -150)
        transp.location = (200, -300)
        mix_0.location = (400, 0)
        mix_1.location = (600, 0)
        mix_2.location = (800, 0)
        outp.location = (1000, 0)

        tree.links.new(geom.outputs['Backfacing'], mix_0.inputs[0])

        if bsdf_type == 'EMISSION':
            tree.links.new(emi_bsdf.outputs[0], mix_0.inputs[1])
        elif bsdf_type == 'DIFFUSE':
            tree.links.new(dif_bsdf.outputs[0], mix_0.inputs[1])

        tree.links.new(transp.outputs[0], mix_0.inputs[2])

        tree.links.new(path.outputs['Is Camera Ray'], mix_1.inputs[0])
        tree.links.new(transp.outputs[0], mix_1.inputs[1])
        tree.links.new(mix_0.outputs[0], mix_1.inputs[2])

        tree.links.new(transp.outputs[0], mix_2.inputs[1])
        tree.links.new(mix_1.outputs[0], mix_2.inputs[2])

        tree.links.new(mix_2.outputs[0], outp.inputs[0])

        # Set color
        #bsdf.inputs[0].default_value = (col[0], col[1], col[2], 1.0)
        #mix_2.inputs[0].default_value = col[3]

    return mat

def get_outline_modifier(obj):
    m = [m for m in obj.modifiers if m.type == 'SOLIDIFY' and m.material_offset > 0 and m.use_flip_normals]
    if m: return m[0]
    return None

def get_outline_material(obj, mod=None):
    if not mod:
        mod = get_outline_modifier(obj)

    if mod and len(obj.data.materials) > 0:
        idx = min(mod.material_offset, len(obj.data.materials)-1)
        mat = obj.data.materials[idx]
        if mat and (OUTLINE_MAT_NAME in mat.name or OUTLINE_MAT_NAME.lower() in mat.name):
            return mat

    return None

def get_diffuse_bsdf(mat):
    bsdfs = [n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfDiffuse']
    if bsdfs: return bsdfs[0]
    return None

def get_emission_bsdf(mat):
    bsdfs = [n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeEmission']
    if bsdfs: return bsdfs[0]
    return None

def get_first_link_and_mix_node(mat, dif_bsdf=None, emi_bsdf=None):
    if not dif_bsdf: dif_bsdf = get_diffuse_bsdf(mat)
    if not emi_bsdf: emi_bsdf = get_emission_bsdf(mat)

    # Get the mix node
    mix_links = [l for l in dif_bsdf.outputs[0].links if l.to_node.bl_idname == 'ShaderNodeMixShader']
    if not mix_links:
        mix_links = [l for l in emi_bsdf.outputs[0].links if l.to_node.bl_idname == 'ShaderNodeMixShader']

    if mix_links:
        link = mix_links[0]
        mix = link.to_node

        return link, mix

    return None, None

def get_last_mix_node(mat):
    try: outp = [n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output][0]
    except: return None
    if any(outp.inputs[0].links):
        l = outp.inputs[0].links[0]
        if l.from_node.bl_idname == 'ShaderNodeMixShader':
            return l.from_node
    return None

class YAddStrokeGenOutline(bpy.types.Operator):
    bl_idname = "object.y_add_strokegen_outline"
    bl_label = "Add Outline"
    bl_description = "Add StrokeGen outline to selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    thickness : FloatProperty(
        name = 'Outline Thickness', 
        description = 'Thickness of generated outline',
        default=1.0, min=0.1, max=100.0
        )

    add_triangulate_modifier : BoolProperty(
        name = 'Add Triangulate Modifier',
        description = 'Strokegen works better with triangulate modifier',
        default = True
        )

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and is_strokegen_available()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self) #, width=420)

    def draw(self, context):
        obj = context.object
        self.layout.prop(self, 'thickness')
        self.layout.prop(self, 'add_triangulate_modifier')

    def execute(self, context):
        scene = context.scene
        objs = context.selected_objects
        npr = scene.npr

        # StrokeGen global settings
        if npr.disable_strokegen:
            npr.disable_strokegen = False
        npr.global_curve_width = 1.0

        for o in objs:
            if o.type != 'MESH': continue

            # StrokeGen object settings
            if not o.strokegen.contour:
                o.strokegen.contour = True

            # Disable traditional solidify modifiers
            m = get_outline_modifier(o)
            outline_mat_idx = -1
            if m:
                m.show_viewport = False
                m.show_render = False

                outline_mat_idx = m.material_offset

            for i, m in enumerate(o.data.materials):
                if not m or i == outline_mat_idx: continue
                m.strokegen.used_for_strokegen = True
                m.strokegen.curve_width = self.thickness

            # Add triangulate modifier
            if self.add_triangulate_modifier:

                tria = None
                trias = get_modifiers_by_type(o, 'TRIANGULATE')
                if trias: tria = trias[0]
                if not tria:
                    tria = o.modifiers.new('Triangulate', 'TRIANGULATE')

        return {'FINISHED'}

class YAddOutline(bpy.types.Operator):
    bl_idname = "object.y_add_outline"
    bl_label = "Add Outline"
    bl_description = "Add outline to selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    thickness : FloatProperty(
            name = 'Outline Thickness', 
            description = 'Thickness of generated outline',
            default=0.01, min=0.0001, max=0.1)

    bsdf_type : EnumProperty(
            name = 'BSDF Type',
            description = 'BSDF Type of the outline',
            items = (('EMISSION', 'Emission', ''),
                     ('DIFFUSE', 'Diffuse', '')),
            default = 'EMISSION')

    color : FloatVectorProperty(
            name='Color', size=4,
            subtype='COLOR',
            default=(0.0, 0.0, 0.0, 0.5),
            min=0.0, max=1.0
            )

    viewport_bc : BoolProperty(
            name = 'Set Viewport Backface Culling',
            description = 'Set Viewport to Use Backface Culling',
            default = True)

    @classmethod
    def poll(cls, context):
        return context.object #and context.object.type == 'MESH'

    def invoke(self, context, event):
        obj = context.object

        # Try to get already used thickness
        m = get_outline_modifier(obj)
        mat = None
        if m: 
            self.thickness = -m.thickness
            mat = get_outline_material(obj, m)

        # Check if material already created
        if not mat:
            mat = bpy.data.materials.get(OUTLINE_MAT_NAME)

        if mat:
            # Get bsdfs
            dif_bsdf = get_diffuse_bsdf(mat)
            emi_bsdf = get_emission_bsdf(mat)
            link, mix = get_first_link_and_mix_node(mat, dif_bsdf, emi_bsdf)
            if link:
                if link.from_node == emi_bsdf:
                    self.bsdf_type = 'EMISSION'
                if link.from_node == dif_bsdf:
                    self.bsdf_type = 'DIFFUSE'

                self.color = (
                        link.from_node.inputs[0].default_value[0],
                        link.from_node.inputs[0].default_value[1],
                        link.from_node.inputs[0].default_value[2],
                        1.0
                        )

            # Get last mix
            last_mix = get_last_mix_node(mat)
            if last_mix:
                self.color = (
                        self.color[0],
                        self.color[1],
                        self.color[2],
                        last_mix.inputs[0].default_value
                        )

        return self.execute(context)

    def execute(self, context):
        objs = bpy.context.selected_objects
        
        for o in objs:
            if not hasattr(o.data, 'materials') or o.type in {'META'}: continue
            # Try to get outline modifiers
            m = get_outline_modifier(o)
            mat = None

            if m: 
                #if len(o.data.materials) > m.material_offset:
                #    mat = o.data.materials[m.material_offset]
                mat = get_outline_material(o, m)
            else:

                # Create empty material slots if object has no material 
                if len(o.data.materials) == 0:
                    o.data.materials.append(None)

                m = o.modifiers.new('Solidify', 'SOLIDIFY')
                m.use_flip_normals = True

                mat = get_outline_mat(self.color, self.bsdf_type)
                
                if not any([m for m in o.data.materials if m == mat]):
                    o.data.materials.append(mat)
                
                idx = [i for i, m in enumerate(o.data.materials) if m == mat][0]
                
                m.material_offset = idx
                m.material_offset_rim = idx

            # Set thickness
            m.thickness = -self.thickness

            # Set outline color and alpha
            if mat:
                # Set material color
                mat.diffuse_color = (self.color[0], self.color[1], self.color[2], 1.0)

                # Set Bsdf Color
                bsdfs = [n for n in mat.node_tree.nodes if n.bl_idname in {'ShaderNodeBsdfDiffuse', 'ShaderNodeEmission'}]
                for b in bsdfs:
                    b.inputs[0].default_value = (self.color[0], self.color[1], self.color[2], 1.0)

                # Check active bsdf
                dif_bsdf = get_diffuse_bsdf(mat)
                emi_bsdf = get_emission_bsdf(mat)

                # Get first mix node
                link, mix = get_first_link_and_mix_node(mat, dif_bsdf, emi_bsdf)

                if mix:
                    if self.bsdf_type == 'EMISSION':
                        if link.from_node != emi_bsdf: mat.node_tree.links.new(emi_bsdf.outputs[0], mix.inputs[1])
                    elif self.bsdf_type == 'DIFFUSE':
                        if link.from_node != dif_bsdf: mat.node_tree.links.new(dif_bsdf.outputs[0], mix.inputs[1])

                # Get last mix node 
                last_mix = get_last_mix_node(mat)
                if last_mix: last_mix.inputs[0].default_value = self.color[3]

        # Set context screen to use backface culling
        if self.viewport_bc:
            context.area.spaces[0].shading.show_backface_culling = True

        return {'FINISHED'}

class YETCSceneProps(bpy.types.PropertyGroup):
    hide_outline_while_texture_paint : BoolProperty(
            name = 'Hide Outline while Texture Paint',
            description = 'Hide outline modifier while texture painting since it won\'t work with mirrored uv',
            default = False)

class YETCObjectProps(bpy.types.PropertyGroup):
    last_mode : StringProperty(default='')
    outline_mod_name : StringProperty(default='')

@persistent
def yetc_toggle_object_outline(scene):
    if not scene.yetc.hide_outline_while_texture_paint: return

    obj = bpy.context.object

    if obj and obj.yetc.last_mode != obj.mode:
        if obj.mode == 'TEXTURE_PAINT':
            mod = get_outline_modifier(obj)
            if mod and mod.show_viewport:
                obj.yetc.outline_mod_name = mod.name
                mod.show_viewport = False
                print('UCUP ETC: Outline modifier is disabled while on Texture Paint Mode')
        elif obj.yetc.last_mode == 'TEXTURE_PAINT':
            if obj.yetc.outline_mod_name != '':
                mod = obj.modifiers.get(obj.yetc.outline_mod_name)
                if mod: 
                    mod.show_viewport = True
                    print('UCUP ETC: Outline modifier is enabled again!')
            obj.yetc.outline_mod_name = ''
        try: obj.yetc.last_mode = obj.mode
        except Exception as e: print('ETC EXCEPTION: Can\'t set last mode')

class YRemoveOutline(bpy.types.Operator):
    bl_idname = "object.y_remove_outline"
    bl_label = "Remove Outline"
    bl_description = "Remove outline on selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object #and context.object.type == 'MESH'

    def execute(self, context):
        objs = bpy.context.selected_objects

        for o in objs:
            m = get_outline_modifier(o)
            if m: 
                mat = get_outline_material(o, m)
                if mat:
                    idx = [i for i, ma in enumerate(o.data.materials) if ma == mat][0]
                    o.data.materials.pop(index=idx)

                o.modifiers.remove(m)

        return {"FINISHED"}

def register():
    bpy.utils.register_class(YAddOutline)
    bpy.utils.register_class(YAddStrokeGenOutline)
    bpy.utils.register_class(YRemoveOutline)
    bpy.utils.register_class(YETCSceneProps)
    bpy.utils.register_class(YETCObjectProps)

    bpy.types.Scene.yetc = PointerProperty(type=YETCSceneProps)
    bpy.types.Object.yetc = PointerProperty(type=YETCObjectProps)

    bpy.app.handlers.depsgraph_update_post.append(yetc_toggle_object_outline)

def unregister():
    bpy.utils.unregister_class(YAddOutline)
    bpy.utils.unregister_class(YAddStrokeGenOutline)
    bpy.utils.unregister_class(YRemoveOutline)
    bpy.utils.unregister_class(YETCSceneProps)
    bpy.utils.unregister_class(YETCObjectProps)

    bpy.app.handlers.depsgraph_update_post.remove(yetc_toggle_object_outline)
