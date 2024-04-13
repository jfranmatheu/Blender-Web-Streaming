from bpy import types as bpy_types
from bpy.props import _PropertyDeferred
from .operator import Operator, OpsReturn



class InvokeSearchMenu(Operator):

    def invoke(self, context: bpy_types.Context, _event) -> OpsReturn:
        if res := context.window_manager.invoke_search_popup(self):
            return res
        return OpsReturn.UI

    @classmethod
    def tag_register(deco_cls, **kwargs: dict) -> Operator:
        bl_property = ''
        for annot_name, annot in deco_cls.__annotations__.items():
            # print(annot, type(annot), annot.function, annot.keywords)
            if isinstance(annot, _PropertyDeferred) and annot.function.__name__ == 'EnumProperty':
                bl_property = annot_name
                break
        return super().tag_register(**kwargs, bl_property=bl_property)
