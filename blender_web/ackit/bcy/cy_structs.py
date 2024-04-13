from ctypes import POINTER, Structure, c_bool, c_char, c_char_p, c_double, c_float, c_int, c_longlong, c_wchar_p, c_short, c_byte, c_uint, sizeof, cast, byref, c_void_p, c_ubyte
from enum import IntEnum, Enum


##############################################################
# TYPES
##############################################################

c_float_p = POINTER(c_float)
c_int_p = POINTER(c_int)
c_byte_p = POINTER(c_byte)
c_bool_p = POINTER(c_bool)


##############################################################
# CONVERSION
##############################################################

def to_cy_string(_string: str) -> c_wchar_p:
    return c_wchar_p(_string)

def to_cy_array_float(_list: list, ret_size: bool = False, size: int = 0):
    if _list == None:
        if ret_size:
            return None, c_int(0)
        else:
            return None
    if not size:
        size = len(_list)
    clist = (c_float * size)( * _list)
    if ret_size:
        return (c_float_p(clist), c_int(size))
    return c_float_p(clist)

def to_cy_array_int(_list: list, ret_size: bool = False, size: int = 0):
    if not size:
        size = len(_list)
    clist = (c_int * size)( * _list)
    if ret_size:
        return c_int_p(clist), c_int(size)
    return c_int_p(clist)

def to_cy_array_byte(_list: list, ret_size: bool = False, size: int = 0):
    if not size:
        size = len(_list)
    clist = (c_byte * size)( * _list)
    if ret_size:
        return (c_byte_p(clist), c_int(size))
    return c_byte_p(clist)


class ConvertTo(Enum):
    STRING = to_cy_string
    ARRAY_FLOAT = to_cy_array_float
    ARRAY_INT = to_cy_array_int
    ARRAY_BYTE = to_cy_array_byte

    INT = c_int
    FLOAT = c_float
    BYTE = c_byte
    BOOL = c_bool

    def __call__(self, input: str or list or tuple or bool, *args) -> c_wchar_p or c_float_p or c_int_p or c_byte_p or c_bool or c_int or c_float or c_byte:
        return self.value(input, *args)


##############################################################
# CONSTANTS.
##############################################################

UI_MAX_NAME_STR = 128


##############################################################
# STRUCT UTILS.
##############################################################

class EnumerationType(type(c_uint)):
    def __new__(metacls, name, bases, dict):
        if not "_members_" in dict:
            _members_ = {}
            for key,value in dict.items():
                if not key.startswith("_"):
                    _members_[key] = value
            dict["_members_"] = _members_
        cls = type(c_uint).__new__(metacls, name, bases, dict)
        for key,value in cls._members_.items():
            globals()[key] = value
        return cls

    def __contains__(self, value):
        return value in self._members_.values()

    def __repr__(self):
        return "<Enumeration %s>" % self.__name__

class Enumeration(c_uint):
    __metaclass__ = EnumerationType
    _members_ = {}
    def __init__(self, value):
        for k,v in self._members_.items():
            if v == value:
                self.name = k
                break
        else:
            raise ValueError("No enumeration member with value %r" % value)
        c_uint.__init__(self, value)
        

    @classmethod
    def from_param(cls, param):
        if isinstance(param, Enumeration):
            if param.__class__ != cls:
                raise ValueError("Cannot mix enumeration members")
            else:
                return param
        else:
            return cls(param)

    def __repr__(self):
        return "<member %s=%d of %r>" % (self.name, self.value, self.__class__)


##############################################################
# STRUCT DEFINITIONS.
##############################################################

class CY_rect:
    @property
    def position(self):
        return self.xmin, self.ymin

    @property
    def size_x(self):
        return self.xmax - self.xmin

    @property
    def size_y(self):
        return self.ymax - self.ymin

    @property
    def size(self) -> tuple:
        return self.size_x, self.size_y

class CY_recti(CY_rect, Structure):
    _fields_ = [
        ('xmin', c_int),
        ('xmax', c_int),
        ('ymin', c_int),
        ('ymax', c_int)
    ]

class CY_rectf(CY_rect, Structure):
    _fields_ = [
        ('xmin', c_float),
        ('xmax', c_float),
        ('ymin', c_float),
        ('ymax', c_float)
    ]

class CY_ListBase(Structure):
    _fields_ = [
        ('first', c_void_p), # POINTER(ListBase)),
        ('last', c_void_p), # POINTER(ListBase)),
    ]


class uiItemType():
    ITEM_BUTTON = 0

    ITEM_LAYOUT_ROW = 1
    ITEM_LAYOUT_COLUMN = 2
    ITEM_LAYOUT_COLUMN_FLOW = 3
    ITEM_LAYOUT_ROW_FLOW = 4
    ITEM_LAYOUT_GRID_FLOW = 5
    ITEM_LAYOUT_BOX = 6
    ITEM_LAYOUT_ABSOLUTE = 7
    ITEM_LAYOUT_SPLIT = 8
    ITEM_LAYOUT_OVERLAP = 9
    ITEM_LAYOUT_RADIAL = 10

    ITEM_LAYOUT_ROOT = 11


class uiEmbossType():
    UI_EMBOSS = 0,          # use widget style for drawing
    UI_EMBOSS_NONE = 1,     # Nothing, only icon and/or text
    UI_EMBOSS_PULLDOWN = 2, # Pull-down menu style
    UI_EMBOSS_RADIAL = 3,   # Pie Menu
    '''
    * The same as #UI_EMBOSS_NONE, unless the button has
    * a coloring status like an animation state or red alert.
    '''
    UI_EMBOSS_NONE_OR_STATUS = 4,

    UI_EMBOSS_UNDEFINED = 255, # For layout engine, use emboss from block.


class CY_uiItem(Structure):
    '''
    @property
    def size(self):
        if self.type == uiItemType.ITEM_BUTTON:
            # uiButtonItem *bitem = (uiButtonItem *)item;
            CY_uiButtonItem_p = POINTER(CY_uiButtonItem)
            bitem = cast(byref(self), CY_uiButtonItem_p).contents

            bitem.but.rect
            w = 
    '''
    def to_layout(self) -> 'CY_uiLayout':
        return cast(byref(self), POINTER(CY_uiLayout)).contents

    def next_item(self) -> 'CY_uiItem' or None:
        if self.next <= 0:
            return None
        return CY_uiItem.from_address(self.next)

    _fields_ = [
        ('next', c_void_p), # POINTER(CY_uiItem)),
        ('prev', c_void_p), # POINTER(CY_uiItem)),
        ('type', c_int), # ENUM # c_short # c_uint
        ('flag', c_int)
    ]


class CY_uiButtonItem(Structure):
    _fields_ = [
        ('item', CY_uiItem),
        ('but', c_longlong) # POINTER(CY_uiBut))
    ]


class CY_uiLayout(Structure):
    x: int
    y: int
    w: int
    h: int

    @property
    def position(self) -> tuple[int, int]:
        return self.x, self.y

    @property
    def size(self) -> tuple[int, int]:
        return self.w, self.h

    @property
    def children_layout(self) -> 'CY_uiLayout' or None:
        if self.child_items_layout == 0:
            return None
        return CY_uiLayout.from_address(self.child_items_layout)

    @property
    def children(self) -> list['CY_uiLayout']:
        if self.items is None:
            return []
        children = []
        layout_size = sizeof(CY_uiLayout)
        next_item = self.items.first
        last_item = self.items.last
        while next_item < last_item:
            children.append(
                CY_uiItem.from_address(next_item))
            next_item += layout_size
        children.append(
            CY_uiItem.from_address(last_item))
        #print(children)
        return children


    _fields_ = [
        ('item', CY_uiItem), # not pointer, just the struct.
        ('root', c_longlong), # uiLayoutRoot
        ('context', c_longlong), # bContextStore
        ('parent', c_longlong), # uiLayout
        ('items', CY_ListBase), # not pointer, just the struct.
        ('heading', c_char * UI_MAX_NAME_STR),
        # Sub layout to add child items, if not the layout itself.
        ('child_items_layout', c_longlong), # uiLayout
        ('x', c_int),
        ('y', c_int),
        ('w', c_int),
        ('h', c_int),
        ('scale', c_float * 2),
        ('space', c_short),
        ('align', c_bool),
        ('active', c_bool),
        ('active_default', c_bool),
        ('activate_init', c_bool),
        ('enabled', c_bool),
        ('redalert', c_bool),
        ('keepaspect', c_bool),
        # For layouts inside grid-flow, they and their items shall never have a fixed maximal size.
        ('variable_size', c_bool),
        ('alignment', c_char),
        ('emboss', c_int), # c_short
        # for fixed width or height to avoid UI size changes */
        ('units', c_float * 2)
    ]

class CY_IconTextOverlay(Structure):
    _fields_ = [
        ('text', c_char * 5)
    ]

class CY_PointerRNA(Structure):
    _fields_ = [
        ('owner_id', c_longlong),
        ('type', c_longlong),
        ('data', c_void_p)
    ]

class CY_uiBut(Structure):
    @property
    def size(self) -> tuple[int, int]:
        return self.rect.size

    @property
    def position(self) -> tuple[int, int]:
        return self.rect.position

    _fields_ = [
        ('next', c_longlong),
        ('prev', c_longlong),
        ('layout', POINTER(CY_uiLayout)),
        ('flag', c_int),
        ('drawflag', c_int),
        ('type', c_int), # enum
        ('pointype', c_int), # enum
        ('bit', c_short),
        ('bitnr', c_short),
        ('retval', c_short),
        ('strwidth', c_short),
        ('alignnr', c_short),
        ('ofs', c_short),
        ('pos', c_short),
        ('selsta', c_short),
        ('selend', c_short),
        ('str', c_char_p),
        ('strdata', c_char * UI_MAX_NAME_STR),
        ('drawstr', c_char * UI_MAX_NAME_STR),
        ('rect', CY_rectf),
        ('poin', c_char_p),
        ('hardmin', c_float),
        ('hardmax', c_float),
        ('softmin', c_float),
        ('softmax', c_float),
        ('a1', c_float),
        ('a2', c_float),
        ('col', c_ubyte * 4),
        ('identity_cmp_func', c_longlong), # uiButIdentityCompareFunc # its a reference to a function
        ('func', c_longlong), # uiButHandleFunc # its a reference to a function
        ('func_arg1', c_void_p),
        ('func_arg2', c_void_p),
        ('funcN', c_longlong), # uiButHandleNFunc # its a reference to a function
        ('func_argN', c_void_p),
        ('context', c_longlong), # bContextStore
        ('autocomplete_func', c_longlong), # uiButCompleteFunc # ref to a func
        ('autofunc_arg', c_void_p),
        ('rename_func', c_longlong), # uiButHandleRenameFunc # ref to a func
        ('rename_arg1', c_void_p),
        ('rename_orig', c_void_p),
        ('hold_func', c_longlong), # uiButHandleHoldFunc # ref to a func
        ('hold_argN', c_void_p),
        ('tip', c_char_p),
        ('tip_func', c_longlong), # uiButToolTipFunc # ref to func
        ('tip_arg', c_void_p),
        ('tip_arg_free', c_longlong), # uiFreeArgFunc # ref to func
        ('disabled_info', c_char_p),
        ('icon', c_int), # enum BIFIconID
        ('emboss', c_int), # enum eUIEmbossType
        ('pie_dir', c_int), # enum RadialDirection
        ('changed', c_bool),
        ('unit_type', c_ubyte),
        ('iconadd', c_short),
        ('block_create_func', c_longlong), # uiBlockCreateFunc # ref to func
        ('menu_create_func', c_longlong), # uiMenuCreateFunc # ref to func
        ('menu_step_func', c_longlong), # uiMenuStepFunc # ref to func
        ('rnapoin', CY_PointerRNA),
        ('rnaprop', c_longlong), # CY_PropertyRNA
        ('rnaindex', c_int),
        ('optype', c_longlong),
        ('opptr', c_longlong),
        ('opcontext', c_int), # enum wmOperatorCallContext
        ('menu_key', c_ubyte),
        ('extra_op_icons', CY_ListBase),
        ('dragtype', c_char),
        ('dragflag', c_short),
        ('dragpoin', c_longlong),
        ('imb', c_longlong),
        ('imb_scale', c_float),
        ('active', c_longlong),
        ('custom_data', c_void_p),
        ('editstr', c_char_p),
        ('editval', POINTER(c_double)),
        ('editvec', c_float_p),
        ('pushed_state_func', c_longlong), # ref to func # uiButPushedStateFunc
        ('pushed_state_arg', c_void_p),
        ('icon_overlay_text', CY_IconTextOverlay), # IconTextOverlay
        ('block', c_longlong)
    ]


class CY_uiLayoutItemBx(Structure):
    @property
    def button(self) -> CY_uiBut:
        return CY_uiBut.from_address(self.roundbox)

    _fields_ = [
        ('litem', CY_uiLayout),
        ('roundbox', c_longlong)
    ]


######################################
# GIZMOS

class CY_wmGizmoGroup(Structure):
    _fields_ = [
        ('next', c_longlong),
        ('prev', c_longlong),
        ('type', c_longlong), # wmGizmoGroupType
        ('gizmos', CY_ListBase), # wmGizmo
        ('parent_gzmap', c_longlong),
        ('py_instance', c_void_p),
        ('reports', c_longlong), # ReportList
        ('hide', c_uint * 2), # weird struct union hack
        ('tag_remove', c_bool),
        ('customdata', c_void_p),
        ('customdata_free', c_void_p), # beauty: void (*customdata_free)(void *)
        ('init_flag', c_int) # enum eWM_GizmoFlagGroupInitFlag
    ]

class CY_wmGizmoMapSelectState(Structure):
    _fields_ = [
        ('items', c_longlong), # **items... wmGizmo
        ('len', c_int),
        ('len_alloc', c_int)
    ]

class CY_GizmoMapContext(Structure):
    _fields_ = [
        ('highlight', c_longlong), # wmGizmo
        ('modal', c_longlong), # wmGizmo
        ('select', CY_wmGizmoMapSelectState), # wmGizmoMapSelectState
        ('event_xy', c_int * 2),
        ('event_grabcursor', c_short),
        ('last_cursor', c_int)
    ]

class CY_wmGizmoMap(Structure):
    @property
    def context(self) -> CY_GizmoMapContext:
        return self.gzmap_context

    @property
    def group(self) -> CY_wmGizmoGroup:
        return self.groups

    _fields_ = [
        ('type', c_int),
        ('groups', CY_ListBase), # wmGizmoGroup
        ('update_flag', c_char * 2),
        ('is_init', c_bool),
        ('tag_remove_group', c_bool),
        ('gzmap_context', CY_GizmoMapContext)
    ]


######################################
# AREGION

class CY_SmoothView2DStore(Structure):
    _fields_ = [
        ('orig_cur', CY_rectf),
        ('new_rect', CY_rectf),
        ('time_allowed', c_double)
    ]

class CY_View2D(Structure):
    _fields_ = [
        # Tot - area that data can be drawn in; cur - region of tot that is visible in viewport.
        ('tot', CY_rectf),
        ('cur', CY_rectf),
        # Vert - vertical scroll-bar region; hor - horizontal scroll-bar region.
        ('vert', CY_recti),
        ('hor', CY_recti),
        # Mask - region (in screen-space) within which 'cur' can be viewed.
        ('mask', CY_recti),
        # Min/max sizes of 'cur' rect (only when keepzoom not set).
        ('min', c_float * 2),
        ('max', c_float * 2),
        # Allowable zoom factor range (only when (keepzoom & V2D_LIMITZOOM)) is set.
        ('minzoom', c_float),
        ('maxzoom', c_float),
        # Scroll - scroll-bars to display (bit-flag).
        ('scroll', c_short),
        # Scroll_ui - temp settings used for UI drawing of scrollers.
        ('scroll_ui', c_short),
        # Keeptot - 'cur' rect cannot move outside the 'tot' rect?
        ('keeptot', c_short),
        # Keepzoom - axes that zooming cannot occur on, and also clamp within zoom-limits.
        ('keepzoom', c_short),
        # Keepofs - axes that translation is not allowed to occur on.
        ('keepofs', c_short),
        # Settings.
        ('flag', c_short),
        # Alignment of content in totrect.
        ('align', c_short),
        # Storage of current winx/winy values, set in UI_view2d_size_update.
        ('winx', c_short),
        ('winy', c_short),
        # Storage of previous winx/winy values encountered by #UI_view2d_curRect_validate(),
        # for keep-aspect.
        ('oldwinx', c_short),
        ('oldwiny', c_short),
        # Pivot point for transforms (rotate and scale).
        ('around', c_short),
        # Usually set externally (as in, not in view2d files).
        # Alpha of vertical and horizontal scroll-bars (range is [0, 255]).
        ('alpha_vert', c_char),
        ('alpha_hor', c_char),
        # Mem Spacing.
        ('_pad', c_char * 2),
        # When set (not 0), determines how many pixels to scroll when scrolling an entire page.
        # Otherwise the height of #View2D.mask is used.
        ('page_size_y', c_float),
        # Animated smooth view.
        ('sms', POINTER(CY_SmoothView2DStore)),
        ('smooth_timer', c_longlong) # POINTER(wmTimer)
    ]


class CY_ARegion_Runtime(Structure):
    _fields_ = [
        ('category', c_char_p),
        ('visible_rect', CY_recti),
        ('offset_x', c_int),
        ('offset_y', c_int),
        ('block_name_map', c_longlong) # POINTER(GHash)
    ]


class CY_ARegion(Structure):
    @property
    def size(self) -> tuple[int, int]:
        return self.sizex, self.sizey

    def resize_x(self, width) -> None:
        self.sizex = width

    def resize_y(self, height) -> None:
        self.sizey = height

    @property
    def size_win(self) -> tuple[int, int]:
        return self.winx, self.winy

    @property
    def size_view2d(self) -> tuple[int, int]:
        return self.v2d.cur.size

    @property
    def view2d_scroll(self) -> int:
        return self.v2d.scroll

    _fields_ = [
        ('next', c_longlong), # ARegion
        ('prev', c_longlong), # ARegion
        ('v2d', CY_View2D),
        ('winrct', CY_recti),
        ('drawrct', CY_recti),
        ('winx', c_short),
        ('winy', c_short),
        # This is a Y offset on the panel tabs that represents pixels,
        # where zero represents no scroll - the first category always shows first at the top.
        ('category_scroll', c_int), # 3.6
        ('_pad0', c_char * 4), # 3.6
        ('visible', c_short),
        ('regiontype', c_short),
        ('alignment', c_short),
        ('flag', c_short),
        # Current split size in unscaled pixels (if zero it uses regiontype).
        #    To convert to pixels use: `UI_DPI_FAC * region->sizex + 0.5f`.
        #    However to get the current region size, you should usually use winx/winy from above, not this! '''
        ('sizex', c_short),
        ('sizey', c_short),
        ('do_draw', c_short),
        ('do_draw_paintcursor', c_short),
        ('overlap', c_short),
        ('flagfullscreen', c_short),
        ('type', c_longlong), # POINTER(ARegionType)
        ('uiblocks', CY_ListBase),
        ('panels', CY_ListBase),
        ('panels_category_active', CY_ListBase),
        ('ui_lists', CY_ListBase),
        ('ui_previews', CY_ListBase),
        ('handlers', CY_ListBase),
        ('panels_category', CY_ListBase),
        ('gizmo_map', c_longlong), # POINTER(wmGizmoMap)
        ('regiontimer', c_longlong), # POINTER(wmTimer)
        ('draw_buffer', c_longlong), # POINTER(wmDrawBuffer)
        ('headerstr', POINTER(c_char)),
        ('regiondata', c_void_p), # 3.6?
        ('runtime', CY_ARegion_Runtime) # ARegion_Runtime
    ]



######################################

class CyBlStruct(Enum):
    _UI_ITEM = CY_uiItem
    _UI_LAYOUT = CY_uiLayout
    _UI_LAYOUT_BOX = CY_uiLayoutItemBx

    _UI_REGION = CY_ARegion

    @classmethod
    def UI_LAYOUT(cls, bl_struct) -> CY_uiLayout:
        return cls._UI_LAYOUT(bl_struct)

    @classmethod
    def UI_LAYOUT_BOX(cls, bl_struct) -> CY_uiLayoutItemBx:
        return cls._UI_LAYOUT_BOX(bl_struct)

    @classmethod
    def UI_ITEM(cls, bl_struct) -> CY_uiItem:
        return cls._UI_ITEM(bl_struct)

    @classmethod
    def UI_REGION(cls, bl_struct) -> CY_ARegion:
        return cls._UI_REGION(bl_struct)

    def __call__(self, bl_struct):
        return self.value.from_address(bl_struct.as_pointer())
