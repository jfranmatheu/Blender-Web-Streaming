from bpy.types import Panel, Menu

from typing import Union

from ...debug import CM_PrintDebug
from ..override_cache import set_cls_attribute


to_override = []


def ui_override(bl_ui_class: Union[Panel, Menu],
                attr_name: str,
                poll: callable):
    ''' This is a Decorator. Use it over Blender UI built-in classes of Panel, Menu... type. '''
    def decorator(fun):
        setattr(fun, 'poll', poll)
        # setattr(fun, 'old', get_attr_from_cache(bl_ui_class, attr_name, None))
        def wrapper(_self, _context): # *args, **kwargs):
            if not fun.poll(_context):
                if fun.old is not None:
                    fun.old(_self, _context)
            else:
                fun(_self, _context)
        to_override.append((bl_ui_class, attr_name, wrapper, fun))
        # setattr(fun, 'old', set_cls_attribute(bl_ui_class, attr_name, wrapper))
        return wrapper
    # cache_cls_attributes(bl_ui_class)
    return decorator


def register():
    with CM_PrintDebug('UI Overrides') as print_debug:
        for (bl_ui_class, attr_name, wrapper, fun) in to_override:
            setattr(fun, 'old', set_cls_attribute(bl_ui_class, attr_name, wrapper))
            print_debug(f"{bl_ui_class.__name__}.{attr_name} --(overriden by)--> '{fun.__name__}' in module '{fun.__module__}'")
