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

if "bpy" in locals():
    import imp
    imp.reload(mirror_tools)
    imp.reload(pose_tools)
    imp.reload(mesh_tools)
    imp.reload(vg_tools)
    imp.reload(ui)
else:
    from . import mirror_tools, pose_tools, mesh_tools, vg_tools, ui

import bpy 

def register():
    # Register classes
    mirror_tools.register()
    pose_tools.register()
    mesh_tools.register()
    vg_tools.register()
    ui.register()

    #print('INFO: ' + bl_info['name'] + ' ' + common.get_current_version_str() + ' is registered!')
    print('INFO: ' + bl_info['name'] + ' is registered!')

def unregister():
    # Remove classes
    mirror_tools.unregister()
    pose_tools.unregister()
    mesh_tools.unregister()
    vg_tools.unregister()
    ui.unregister()

    #print('INFO: ' + bl_info['name'] + ' ' + common.get_current_version_str() + ' is unregistered!')
    print('INFO: ' + bl_info['name'] + ' is unregistered!')

if __name__ == "__main__":
    register()
