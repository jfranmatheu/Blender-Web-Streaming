import bpy
import sys
from pathlib import Path

from .. import __package__ as __main_package__#, bl_info


class GLOBALS:
    PYTHON_PATH = sys.executable

    BLENDER_VERSION = bpy.app.version
    IN_BACKGROUND = bpy.app.background

    ADDON_MODULE = __main_package__
    ADDON_MODULE_UPPER = __main_package__.upper().replace('_', '')
    ADDON_SOURCE_PATH = Path(__file__).parent.parent
    ADDON_MODULE_NAME = ADDON_MODULE.replace('_', ' ').title().replace(' ', '')
    #ADDON_NAME = bl_info['name']
    #ADDON_VERSION = bl_info['version']
    #SUPPORTED_BLENDER_VERSION = bl_info['blender']
    ICONS_PATH = ADDON_SOURCE_PATH / 'lib' / 'icons'

    IN_DEVELOPMENT = (hasattr(sys, 'gettrace') and sys.gettrace() is not None) or is_junction(ADDON_SOURCE_PATH) # Just a nice HACK! ;-)
    IN_PRODUCTION  = not IN_DEVELOPMENT

    check_in_development = lambda : (hasattr(sys, 'gettrace') and sys.gettrace() is not None) or is_junction(GLOBALS.ADDON_SOURCE_PATH)
    check_in_production = lambda : not GLOBALS.check_in_development()

    @staticmethod
    def get_addon_global_value(key: str, default_value = None):
        return getattr(bpy, GLOBALS.ADDON_MODULE).get(key, default_value)

    @staticmethod
    def set_addon_global_value(key: str, value) -> None:
        getattr(bpy, GLOBALS.ADDON_MODULE)[key] = value


setattr(bpy, GLOBALS.ADDON_MODULE, dict())
