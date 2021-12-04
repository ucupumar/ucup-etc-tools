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
    imp.reload(mirror)
    imp.reload(pose)
    imp.reload(ui)
else:
    from . import mirror, pose, ui

import bpy 

def register():
    # Register classes
    mirror.register()
    pose.register()
    ui.register()

    #print('INFO: ' + bl_info['name'] + ' ' + common.get_current_version_str() + ' is registered!')
    print('INFO: ' + bl_info['name'] + ' is registered!')

def unregister():
    # Remove classes
    mirror.unregister()
    pose.unregister()
    ui.unregister()

    #print('INFO: ' + bl_info['name'] + ' ' + common.get_current_version_str() + ' is unregistered!')
    print('INFO: ' + bl_info['name'] + ' is unregistered!')

if __name__ == "__main__":
    register()
