from enum import Enum
import bpy
from bpy.types import Context, Window


class CursorIcon(Enum):
    DEFAULT       =      'DEFAULT'
    NONE          =         'NONE'
    WAIT          =         'WAIT'
    CROSSHAIR     =    'CROSSHAIR'
    MOVE_X        =       'MOVE_X'
    MOVE_Y        =       'MOVE_Y'
    KNIFE         =        'KNIFE'
    TEXT          =         'TEXT'
    PAINT_BRUSH   =  'PAINT_BRUSH'
    PAINT_CROSS   =  'PAINT_CROSS'
    HAND          =         'HAND'
    SCROLL_X      =     'SCROLL_X'
    SCROLL_Y      =     'SCROLL_Y'
    SCROLL_XY     =    'SCROLL_XY'
    EYEDROPPER    =   'EYEDROPPER'
    DOT           =          'DOT'
    ERASER        =       'ERASER'
    
    # Exposed in +3.0.
    PICK_AREA   = 'PICK_AREA'
    STOP        = 'STOP'
    COPY        = 'COPY'
    CROSS       = 'CROSS'
    MUTE        = 'MUTE'
    ZOOM_IN     = 'ZOOM_IN'
    ZOOM_OUT    = 'ZOOM_OUT'


class Cursor:
    @staticmethod
    def set_icon(context=bpy.context, cursor: CursorIcon = CursorIcon.DEFAULT):
        if not context: context = bpy.context
        context.window.cursor_modal_set(cursor.value)

    @staticmethod
    def wrap(x, y, context: Context | Window = bpy.context):
        if isinstance(context, Window):
            context.cursor_warp(int(x), int(y))
        elif isinstance(context, Context):
            return Cursor.wrap(x, y, context.window)

    @staticmethod
    def restore(context=bpy.context):
        context.window.cursor_modal_restore()
