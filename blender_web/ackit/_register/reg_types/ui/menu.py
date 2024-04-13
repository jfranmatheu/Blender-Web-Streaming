from ._base_ui import BaseUI, UILayout
from ....globals import GLOBALS

import bpy
from bpy.types import Menu as BlMenu


ui_idname_cache = {}


class Menu(BaseUI):
    label: str

    @classmethod
    def popup(cls) -> None:
        bpy.ops.wm.call_menu('INVOKE_DEFAULT', name=cls.bl_idname)

    @classmethod
    def draw_in_layout(cls, layout: UILayout, label: str = None):
        layout.menu(cls.bl_idname, text=label if label else cls.bl_label)

    @classmethod
    def tag_register(deco_cls) -> 'Menu':
        return super().tag_register(BlMenu, 'MT')
