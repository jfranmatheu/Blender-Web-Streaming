from bpy.types import Panel, Menu

from typing import Union


appended_ui = {}
to_append_ui = {}


def UIAppend(bl_ui_class: Union[Panel, Menu],
             poll: callable = None,
             prepend: bool = False):
    ''' This is a Decorator. Use it over Blender UI built-in classes of Panel, Menu... type. '''
    def decorator(fun):
        if poll is not None:
            setattr(fun, 'poll', poll)
        def wrapper(_self, _context): # *args, **kwargs):
            if hasattr(fun, 'poll'):
                if not fun.poll(_self, _context):
                    return
            return fun(_self, _context)
        #wrapper = lambda self, context: fun(self, context)
        # global is_registered
        # if is_registered:
        #     bl_ui_class.append_reg(fun, prepend=prepend)
        # else:
        # NOTE: Delay rna subscription due to a registration bug.
        to_append_ui[fun] = (bl_ui_class, prepend)
        return wrapper
    return decorator


def register():
    for func, (cls, prepend) in to_append_ui.items():
        if func in appended_ui:
            continue
        appended_ui[func] = cls
        if prepend:
            cls.prepend(func)
        else:
            cls.append(func)

def unregister():
    for func, cls in appended_ui.items():
        cls.remove(func)

    appended_ui.clear()
