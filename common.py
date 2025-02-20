import bpy, time

def is_greater_than_400():
    if bpy.app.version >= (4, 0, 0):
        return True
    return False 

def is_greater_than_410():
    if bpy.app.version >= (4, 1, 0):
        return True
    return False 

def get_object_parent_layer_collections(arr, col, obj):
    for o in col.collection.objects:
        if o == obj:
            if col not in arr: arr.append(col)

    if not arr:
        for c in col.children:
            get_object_parent_layer_collections(arr, c, obj)
            if arr: break

    if arr:
        if col not in arr: arr.append(col)

    return arr


def copy_props_to_dict(source, target_dict, debug=False):
    if debug: print()

    for prop in dir(source):
        if prop in {'bl_rna', 'rna_type'}: continue
        if prop.startswith('__'): continue

        val = getattr(source, prop)
        attr_type = str(type(val))

        if attr_type.startswith("<class 'bpy_func"): continue
        if attr_type.startswith("<class 'NoneType"): continue
        #if attr_type.startswith("<class 'bpy_prop"): continue

        if debug: print(prop, attr_type)

        if 'bpy_prop_collection' in attr_type:
            target_dict[prop] = []
            for c in val:
                subdict = {}
                copy_props_to_dict(c, subdict, debug)
                target_dict[prop].append(subdict)
        else:
            try: target_dict[prop] = val
            except Exception as e: pass

    if debug: print()

def apply_modifiers_with_shape_keys(obj, selectedModifiers, disable_armatures=True):

    list_properties = []
    properties = ["interpolation", "mute", "name", "relative_key", "slider_max", "slider_min", "value", "vertex_group"]
    shapesCount = 0
    vertCount = -1
    startTime = time.time()

    view_layer = bpy.context.view_layer
    scene = bpy.context.scene

    disabled_armature_modifiers = []
    if disable_armatures:
        for modifier in obj.modifiers:
            if modifier.name not in selectedModifiers and modifier.type == 'ARMATURE' and modifier.show_viewport == True:
                disabled_armature_modifiers.append(modifier)
                modifier.show_viewport = False
    
    if obj.data.shape_keys:
        shapesCount = len(obj.data.shape_keys.key_blocks)

    ori_active = view_layer.objects.active
    view_layer.objects.active = obj
    
    if(shapesCount == 0):
        for modifierName in selectedModifiers:
            try: bpy.ops.object.modifier_apply(modifier=modifierName)
            except Exception as e: print(e)
        if disable_armatures:
            for modifier in disabled_armature_modifiers:
                modifier.show_viewport = True
        view_layer.objects.active = ori_active
        return (True, None)

    # Remember original selected objects
    ori_selected_objs = [o for o in view_layer.objects if o.select_get()]
    
    # We want to preserve original object, so all shapes will be joined to it.
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    originalIndex = obj.active_shape_key_index
    
    originalHide = obj.hide_get()
    obj.hide_set(False)
    
    # Copy object which will holds all shape keys.
    copyObject = obj.copy()
    scene.collection.objects.link(copyObject)
    copyObject.data = copyObject.data.copy()
    copyObject.select_set(False)
    
    # Return selection to original object.
    view_layer.objects.active = obj
    obj.select_set(True)
    
    # Save key shape properties
    for i in range(0, shapesCount):
        key_b = obj.data.shape_keys.key_blocks[i]
        print (obj.data.shape_keys.key_blocks[i].name, key_b.name)
        properties_object = {p:None for p in properties}
        properties_object["name"] = key_b.name
        properties_object["mute"] = key_b.mute
        properties_object["interpolation"] = key_b.interpolation
        properties_object["relative_key"] = key_b.relative_key.name
        properties_object["slider_max"] = key_b.slider_max
        properties_object["slider_min"] = key_b.slider_min
        properties_object["value"] = key_b.value
        properties_object["vertex_group"] = key_b.vertex_group
        list_properties.append(properties_object)

    # Save animation data
    ori_fcurves = []
    ori_action_name = ''
    if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.action:
        ori_action_name = obj.data.shape_keys.animation_data.action.name
        for fc in obj.data.shape_keys.animation_data.action.fcurves:
            fc_dic = {}

            for prop in dir(fc):
                copy_props_to_dict(fc, fc_dic) #, True)

            ori_fcurves.append(fc_dic)

    # Handle base shape in original object
    print("apply_modifiers_with_shape_keys: Applying base shape key")

    # Make sure active shape key index is set to avoid error
    obj.active_shape_key_index = 0

    bpy.ops.object.shape_key_remove(all=True)
    for modifierName in selectedModifiers:
        try: bpy.ops.object.modifier_apply(modifier=modifierName)
        except Exception as e: print(e)
    vertCount = len(obj.data.vertices)
    bpy.ops.object.shape_key_add(from_mix=False)
    obj.select_set(False)

    # Handle other shape-keys: copy object, get right shape-key, apply modifiers and merge with original object.
    # We handle one object at time here.
    for i in range(1, shapesCount):
        currTime = time.time()
        elapsedTime = currTime - startTime

        print("apply_modifiers_with_shape_keys: Applying shape key %d/%d ('%s', %0.2f seconds since start)" % (i+1, shapesCount, list_properties[i]["name"], elapsedTime))

        # Select copy object.
        copyObject.select_set(True)
        
        # Copy temp object.
        tmpObject = copyObject.copy()
        scene.collection.objects.link(tmpObject)
        tmpObject.data = tmpObject.data.copy()
        view_layer.objects.active = tmpObject

        bpy.ops.object.shape_key_remove(all=True)
        copyObject.active_shape_key_index = i
        
        # Get right shape-key.
        bpy.ops.object.shape_key_transfer()
        tmpObject.active_shape_key_index = 0
        bpy.ops.object.shape_key_remove()
        bpy.ops.object.shape_key_remove(all=True)
        
        # Time to apply modifiers.
        for modifierName in selectedModifiers:
            try: bpy.ops.object.modifier_apply(modifier=modifierName)
            except Exception as e: print(e)
        
        # Verify number of vertices.
        if vertCount != len(tmpObject.data.vertices):
            errorInfo = ("Shape keys ended up with different number of vertices!\n"
                         "All shape keys needs to have the same number of vertices after modifier is applied.\n"
                         "Otherwise joining such shape keys will fail!")
            return (False, errorInfo)
    
        # Join with original object
        copyObject.select_set(False)
        view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.join_shapes()
        obj.select_set(False)
        
        # Remove tmpObject
        bpy.data.objects.remove(tmpObject, do_unlink=True)
    
    # Restore shape key properties like name, mute etc.
    view_layer.objects.active = obj
    for i in range(0, shapesCount):
        key_b = view_layer.objects.active.data.shape_keys.key_blocks[i]
        key_b.name = list_properties[i]["name"]
        key_b.interpolation = list_properties[i]["interpolation"]
        key_b.mute = list_properties[i]["mute"]
        key_b.slider_max = list_properties[i]["slider_max"]
        key_b.slider_min = list_properties[i]["slider_min"]
        key_b.value = list_properties[i]["value"]
        key_b.vertex_group = list_properties[i]["vertex_group"]
        rel_key = list_properties[i]["relative_key"]
    
        for j in range(0, shapesCount):
            key_brel = view_layer.objects.active.data.shape_keys.key_blocks[j]
            if rel_key == key_brel.name:
                key_b.relative_key = key_brel
                break
    
    # Remove copyObject.
    bpy.data.objects.remove(copyObject, do_unlink=True)
    
    # Select original object.
    view_layer.objects.active = obj
    view_layer.objects.active.select_set(True)
    
    if disable_armatures:
        for modifier in disabled_armature_modifiers:
            modifier.show_viewport = True

    obj.active_shape_key_index = originalIndex

    # Recover animation data
    if any(ori_fcurves):

        obj.data.shape_keys.animation_data_create()
        obj.data.shape_keys.animation_data.action = bpy.data.actions.new(name=ori_action_name)

        for ofc in ori_fcurves:
            fcurve = obj.data.shape_keys.animation_data.action.fcurves.new(
                data_path=ofc['data_path'], #index=2
            )

            for key, val in ofc.items():
                if key in {'data_path', 'keyframe_points'}: continue
                try: setattr(fcurve, key, val)
                except Exception as e: pass

            for kp in ofc['keyframe_points']:
                k = fcurve.keyframe_points.insert(
                frame=kp['co'][0],
                value=kp['co'][1]
                )

                for key, val in kp.items():
                    try: setattr(k, key, val)
                    except Exception as e: pass

            for mod in ofc['modifiers']:
                m = fcurve.modifiers.new(type=mod['type'])
                for key, val in mod.items():
                    try: setattr(m, key, val)
                    except Exception as e: pass

    obj.hide_set(originalHide)

    # Recover selected objects
    bpy.ops.object.select_all(action='DESELECT')
    for o in ori_selected_objs:
        o.select_set(True)
    view_layer.objects.active = ori_active
    
    return (True, None)

def is_strokegen_available():
    scene = bpy.context.scene
    return hasattr(scene, 'npr') and hasattr(scene.npr, 'disable_strokegen')

def get_modifiers_by_type(obj, mod_type):
    mods = []

    for m in obj.modifiers:
        if m.type == mod_type:
            mods.append(m)

    return mods
