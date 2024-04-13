from bpy.types import AddonPreferences as BlAddonPreferences

from .ui._base_ui import BaseUI, DrawExtension
from ...globals import GLOBALS


class AddonPreferences(BaseUI, DrawExtension):
    bl_idname: str = GLOBALS.ADDON_MODULE

    @classmethod
    def tag_register(cls) -> 'AddonPreferences':
        return super().tag_register(BlAddonPreferences, None)
