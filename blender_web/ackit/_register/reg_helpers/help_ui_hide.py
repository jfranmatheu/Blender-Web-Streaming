from bpy.types import Panel, Menu, Context

from typing import Union

from ..override_cache import set_cls_attribute


def ui_hide(bl_ui_class: Union[Panel, Menu],
            poll: callable):
    ''' This is a Decorator. Use it over Blender UI built-in classes of Panel, Menu... type. '''
    def wrapper(cls, context: Context):
        if poll(context):
            return False
        if ori_fun is not None and callable(ori_fun):
            return ori_fun(cls, context)
        return True

    ori_fun = set_cls_attribute(bl_ui_class, 'poll', classmethod(wrapper))
