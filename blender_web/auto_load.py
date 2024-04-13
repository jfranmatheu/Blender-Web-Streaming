import os
import bpy
import sys
import typing
import inspect
import pkgutil
import importlib
from pathlib import Path

from .ackit.globals import GLOBALS
from .ackit.debug import print_debug

__all__ = (
    "_init",
    "_register",
    "_unregister",
)

blender_version = bpy.app.version

modules = None
ordered_classes = None
initilized = False


def get_classes():
    global ordered_classes
    return ordered_classes


def clean_modules():
    global initilized
    global modules
    global ordered_classes

    initilized = False
    GLOBALS.set_addon_global_value("IS_INITIALIZED", False)

    if modules is None or GLOBALS.ADDON_MODULE not in sys.modules:
        return

    for module_name in list(sys.modules.keys()):
        if module_name == __name__:
            continue
        if module_name.startswith(GLOBALS.ADDON_MODULE):
            del sys.modules[module_name]

    modules.clear()
    ordered_classes.clear()

    return

    if not GLOBALS.check_in_production():
        return
    if GLOBALS.ADDON_MODULE not in sys.modules:
        return
    for module_name in list(sys.modules.keys()):
        if module_name.startswith(GLOBALS.ADDON_MODULE):
            del sys.modules[module_name]


def init_addon():
    global initilized  # We use this and the globals one since the globals can be reset by Blender and its important to control the init state.
    print("Initializing addon...")

    if initilized or GLOBALS.get_addon_global_value("IS_INITIALIZED", False):
        print("WARN! Already initialized! Is this correct?")
        return

    global modules
    global ordered_classes

    GLOBALS.set_addon_global_value("IS_INITIALIZED", False)

    clean_modules()
    modules = get_all_submodules(GLOBALS.ADDON_SOURCE_PATH)
    ordered_classes = get_ordered_classes_to_register(modules)

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "init_pre"):
            module.init_pre()

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "init"):
            module.init()

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "init_post"):
            module.init_post()

    GLOBALS.set_addon_global_value("IS_INITIALIZED", True)
    initilized = True


def register_addon():
    global modules

    if modules is None or (isinstance(modules, list) and len(modules) == 0):
        global initilized
        initilized = False
        GLOBALS.set_addon_global_value("IS_INITIALIZED", False)
        init_addon()

    print("Registering addon...")

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "register_pre"):
            module.register_pre()

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "register"):
            module.register()

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "register_post"):
            module.register_post()

    for cls in ordered_classes:
        if "bl_rna" in cls.__dict__:
            ### print_debug(
            ###     f"[AutoLoad] WARN! Trying to register an already registered class: {cls.__name__}, {id(cls)}"
            ### )
            continue
        print_debug(f"[AutoLoad] Register class: {cls.__name__}, {id(cls)}")
        bpy.utils.register_class(cls)


def unregister_addon():
    print("UNregistering addon...")

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "unregister_pre"):
            module.unregister_pre()

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "unregister"):
            module.unregister()

    for module in modules:
        if module.__name__ in {__name__, GLOBALS.ADDON_MODULE}:
            continue
        if hasattr(module, "unregister_post"):
            module.unregister_post()

    for cls in reversed(ordered_classes):
        if "bl_rna" not in cls.__dict__:
            ### print_debug(
            ###     f"[AutoLoad] WARN! Trying to unregister a class that is not registered: {cls.__name__}, {id(cls)}"
            ### )
            continue
        print_debug(f"[AutoLoad] UNregister class: {cls.__name__}, {id(cls)}")
        bpy.utils.unregister_class(cls)

    clean_modules()


# Import modules
#################################################

def get_all_submodules(directory):
    return list(iter_submodules(directory, directory.name))

def iter_submodules(path, package_name):
    # print(f"######### ITER SUBMODULES FOR PACKAGE '{package_name}' #########")
    for name in sorted(iter_submodule_names(path, depth=0)):
        yield importlib.import_module("." + name, package_name)

def iter_submodule_names(path, root="", depth: int = 0):
    for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
        space = '\t'.join(['' for i in range(depth)])
        if is_package:
            sub_path = path / module_name
            sub_root = root + module_name + "."
            # print(f"{space}> {module_name}/")
            yield from iter_submodule_names(sub_path, sub_root, depth=depth + 1)
        else:
            # print(f"{space}- {module_name}.py")
            yield root + module_name


# Find classes to register
#################################################

def get_ordered_classes_to_register(modules):
    return toposort(get_register_deps_dict(modules))

def get_register_deps_dict(modules):
    my_classes = set(iter_my_classes(modules))
    my_classes_by_idname = {cls.bl_idname : cls for cls in my_classes if hasattr(cls, "bl_idname")}

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_idname))
    return deps_dict

def iter_my_register_deps(cls, my_classes, my_classes_by_idname):
    yield from iter_my_deps_from_annotations(cls, my_classes)
    yield from iter_my_deps_from_parent_id(cls, my_classes_by_idname)

def iter_my_deps_from_annotations(cls, my_classes):
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            if dependency in my_classes:
                yield dependency

def get_dependency_from_annotation(value):
    if blender_version >= (2, 93):
        if isinstance(value, bpy.props._PropertyDeferred):
            return value.keywords.get("type")
    else:
        if isinstance(value, tuple) and len(value) == 2:
            if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
                return value[1]["type"]
    return None

def iter_my_deps_from_parent_id(cls, my_classes_by_idname):
    if bpy.types.Panel in cls.__bases__:
        parent_idname = getattr(cls, "bl_parent_id", None)
        if parent_idname is not None:
            parent_cls = my_classes_by_idname.get(parent_idname)
            if parent_cls is not None:
                yield parent_cls

def iter_my_classes(modules):
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        if any(base in base_types for base in cls.__bases__):
            if not getattr(cls, "is_registered", False):
                yield cls

def get_classes_in_modules(modules):
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes

def iter_classes_in_module(module):
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value

def get_register_base_types():
    return set(getattr(bpy.types, name) for name in [
        "Panel", "Operator", "PropertyGroup",
        "AddonPreferences", "Header", "Menu",
        "Node", "NodeSocket", "NodeTree",
        "UIList", "RenderEngine",
        "Gizmo", "GizmoGroup", "AssetShelf"
    ])


# Find order to register to solve dependencies
#################################################

def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value : deps_dict[value] - sorted_values for value in unsorted}
    return sorted_list


def get_ordered_pg_classes_to_register(classes) -> list:
    my_classes = set(classes)
    my_classes_by_idname = {
        cls.bl_idname: cls for cls in classes if hasattr(cls, "bl_idname")
    }

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(
            iter_my_register_deps(cls, my_classes, my_classes_by_idname)
        )

    return toposort(deps_dict)
