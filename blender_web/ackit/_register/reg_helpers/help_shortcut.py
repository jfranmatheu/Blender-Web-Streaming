import bpy
from bpy.types import Operator, KeyMap, KeyMapItems, KeyMapItem

from typing import List
from dataclasses import dataclass


@dataclass
class ShortcutOperator:
    keymap_idname: str
    operator: Operator
    event_type: str
    event_value: str
    space_type: str = 'EMPTY'
    region_type: str = 'WINDOW'
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    any: bool = False


operator_shortcuts: List[ShortcutOperator] = []


def _register_shortcut__operator(keymap_idname: str,
                                 operator: Operator,
                                 event_type: str,
                                 event_value: str,
                                 space_type: str = 'EMPTY',
                                 region_type: str = 'WINDOW',
                                 ctrl: bool = False,
                                 alt: bool = False,
                                 shift: bool = False,
                                 any: bool = False) -> None:
    operator_shortcuts.append(
        ShortcutOperator(
            keymap_idname,
            operator,
            event_type,
            event_value,
            space_type,
            region_type,
            ctrl,
            alt,
            shift,
            any
        )
    )

###########################################


class ShortcutRegister:
    OPERATOR = _register_shortcut__operator
    MODAL = None # Not Implemented
    TOOL = None # Not Implemented


###########################################


def register_post():
    ''' Executed after everything has been registered. '''
    addon_km_config = bpy.context.window_manager.keyconfigs.active

    for shortcut in operator_shortcuts:
        km: KeyMap = addon_km_config.keymaps.get(shortcut.keymap_idname, None)
        if km is None:
            km = addon_km_config.keymaps.new(shortcut.keymap_idname, space_type=shortcut.space_type, region_type=shortcut.region_type)
        km.keymap_items.new(shortcut.operator.bl_idname,
                            type=shortcut.event_type, value=shortcut.event_value,
                            alt=shortcut.alt, shift=shortcut.shift, ctrl=shortcut.ctrl, any=shortcut.any)

        # print("Register Shortcut", km.name, shortcut.operator.bl_idname)


def unregister():
    addon_km_config = bpy.context.window_manager.keyconfigs.addon

    for shortcut in operator_shortcuts:
        km: KeyMap = addon_km_config.keymaps.get(shortcut.keymap_idname, None)
        if km is None:
            continue
        km_items: KeyMapItems = km.keymap_items
        if kmi := km_items.get(shortcut.operator.bl_idname):
            km_items.remove(kmi)
