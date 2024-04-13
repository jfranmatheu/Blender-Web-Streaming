from ctypes import Structure, c_float, c_short, c_char, c_void_p

from .vec_types import rctf


class BCY_View2D(Structure):
    _fields_ = [
        ('tot', rctf),
        ('cur', rctf),
        ('vert', rctf),
        ('hor', rctf),
        ('mask', rctf),

        ('min', c_float * 2),
        ('max', c_float * 2),
        ('minzoom', c_float),
        ('maxzoom', c_float),

        ('scroll', c_short),
        ('scroll_ui', c_short),

        ('keeptot', c_short),
        ('keepzoom', c_short),
        ('keepofs', c_short),

        ('flag', c_short),
        ('align', c_short),

        ('winx', c_short),
        ('winy', c_short),
        ('oldwinx', c_short),
        ('oldwiny', c_short),

        ('around', c_short),

        ('alpha_vert', c_char),
        ('alpha_hor', c_char),

        ('_pad', c_char * 6),

        # ('page_size_y', c_float),

        ('sms', c_void_p),
        ('smooth_timer', c_void_p)

        # -------------------
    ]

    @classmethod
    def get(cls, data) -> 'BCY_View2D':
        return cls.from_address(data.as_pointer())



'''
/** View 2D data - stored per region. */
typedef struct View2D {
  /** Tot - area that data can be drawn in; cur - region of tot that is visible in viewport. */
  rctf tot, cur;
  /** Vert - vertical scroll-bar region; hor - horizontal scroll-bar region. */
  rcti vert, hor;
  /** Mask - region (in screen-space) within which 'cur' can be viewed. */
  rcti mask;

  /** Min/max sizes of 'cur' rect (only when keepzoom not set). */
  float min[2], max[2];
  /** Allowable zoom factor range (only when (keepzoom & V2D_LIMITZOOM)) is set. */
  float minzoom, maxzoom;

  /** Scroll - scroll-bars to display (bit-flag). */
  short scroll;
  /** Scroll_ui - temp settings used for UI drawing of scrollers. */
  short scroll_ui;

  /** Keeptot - 'cur' rect cannot move outside the 'tot' rect? */
  short keeptot;
  /** Keepzoom - axes that zooming cannot occur on, and also clamp within zoom-limits. */
  short keepzoom;
  /** Keepofs - axes that translation is not allowed to occur on. */
  short keepofs;

  /** Settings. */
  short flag;
  /** Alignment of content in totrect. */
  short align;

  /** Storage of current winx/winy values, set in UI_view2d_size_update. */
  short winx, winy;
  /**
   * Storage of previous winx/winy values encountered by #UI_view2d_curRect_validate(),
   * for keep-aspect.
   */
  short oldwinx, oldwiny;

  /** Pivot point for transforms (rotate and scale). */
  short around;

  /* Usually set externally (as in, not in view2d files). */
  /** Alpha of vertical and horizontal scroll-bars (range is [0, 255)). */
  char alpha_vert, alpha_hor;

  char _pad[2];
  /** When set (not 0), determines how many pixels to scroll when scrolling an entire page.
   * Otherwise the height of #View2D.mask is used. */
  float page_size_y;

  /* animated smooth view */
  struct SmoothView2DStore *sms;
  struct wmTimer *smooth_timer;
} View2D;
'''
