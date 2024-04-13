import bpy
from bpy.types import KeyConfig, KeyMap


numkeys = (
    'ONE',
    'TWO',
    'THREE',
    'FOUR',
    'FIVE',
    'SIX',
    'SEVEN',
    'EIGHT',
    'NINE',
    'ZERO'
)
hotkeys=(
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
    'O', 'P', 'Q', 'R', 'S', 'T',
    'U', 'V', 'W', 'X', 'Y', 'Z',
    'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
    'LEFT_ARROW', 'DOWN_ARROW', 'RIGHT_ARROW', 'UP_ARROW',
    'LEFTMOUSE', 'RIGHTMOUSE', 'PEN', 'ERASER', 'MIDDLEMOUSE', #'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE',
    'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
    'RET', 'SPACE', 'BACK_SPACE', 'DEL', 'TAB',
    'TIMER',
    # 'LEFT_ALT',
)
op = 'gizmogroup.gizmo_tweak'


class BWS_GZGKM:
    @classmethod
    def setup_keymap(cls, keyconfig: KeyConfig) -> KeyMap: return create_km(cls, None)

def create_km(cls, keyconfig):
    # keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is None:
        keyconfig = bpy.context.window_manager.keyconfigs.addon
    if km := keyconfig.keymaps.get(cls.bl_idname, None):
        if km.keymap_items and len(km.keymap_items) > 1:
            return km

    km = keyconfig.keymaps.new(cls.bl_idname, space_type='NODE_EDITOR', region_type='WINDOW')
    for key in hotkeys:
        km.keymap_items.new(op, key, 'ANY', any=True)
        km.keymap_items.new(op, key, 'RELEASE', any=True)
    return km
