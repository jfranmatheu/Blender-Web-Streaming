from bpy.types import Event, Context
from mathutils import Vector, Matrix

from ..node_editor import get_node_editor_zoom, get_node_editor_region_coord

from math import modf


class _RectTransform:
    origin: Vector
    size: Vector
    rotation: float
    bound_box: list[Vector] # Order: ``Top-Left``, ``Bottom-Left``, ``Bottom-Right``, ``Top-Right``.
    bound_box_size: Vector
    coords: list[Vector]
    coords_rotated: list[Vector]

    def convert_abs_coord_to_rel_coord(self, point: Vector) -> Vector: pass


class Mouse:
    current: Vector   # current mouse position.
    prev: Vector      # previous mouse position.
    start: Vector     # initial mouse position.
    offset: Vector    # mouse offset between initial position and current position.
    delta: Vector     # difference of mouse position between prev and current.

    # local: Vector     # local space coordinates.
    local_rel: Vector # local space coordinates, relative factor between [0, 1].
    local_current: Vector # current local space coordinates.
    local_prev: Vector
    local_start: Vector
    local_offset: Vector
    local_delta: Vector
    local_dir: Vector
    local_delta_int: Vector # Same as local_delta but it always returns a integer value, with cumulative effect.
    local_delta_acummulative: Vector # Exclusively used for 'local_delta_int' as a cumulative delta value.

    view_current: Vector
    view_prev: Vector
    view_start: Vector
    view_offset: Vector
    view_delta: Vector

    dir: Vector       # direction of mouse taking into account previous position.
    
    error: object | None | str | bool


    @staticmethod
    def init(event: Event, context: Context | None = None, local_space__rect: _RectTransform | None = None) -> 'Mouse':
        mouse = Mouse()
        mouse.error = False
        mouse_region_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        mouse.start = mouse_region_pos
        mouse.current = mouse_region_pos.copy()
        mouse.prev = mouse_region_pos.copy()
        mouse.offset = Vector((0, 0))
        mouse.delta = Vector((0, 0))
        mouse.dir = Vector((0, 0))

        if context is not None:
            view2d = context.region.view2d
        else:
            view2d = None

        if view2d is not None:
            view_pos = view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
            mouse.view_current = Vector(view_pos)
            mouse.view_prev = Vector(view_pos)
            mouse.view_start = Vector(view_pos)
            mouse.view_offset = Vector((0, 0))
            mouse.view_delta = Vector((0, 0))

            if local_space__rect is not None:
                mouse.update_local_space(context, local_space__rect, first_time=True)

        return mouse

    def update(self, event: Event, context: Context | None = None, local_space__rect: _RectTransform | None = None) -> None:
        if self.error:
            self.init(event, context, local_space__rect)
            self.error = False
            return

        self.prev.x = self.current.x
        self.prev.y = self.current.y
        self.current.x = event.mouse_region_x
        self.current.y = event.mouse_region_y
        self.delta.x = self.current.x - self.prev.x
        self.delta.y = self.current.y - self.prev.y
        self.offset.x = self.current.x - self.start.x
        self.offset.y = self.current.y - self.start.y

        if context is not None:
            view2d = context.region.view2d
        else:
            view2d = None

        if view2d is not None:
            view_pos = view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
            self.view_delta.x = self.view_current.x - self.view_prev.x
            self.view_delta.y = self.view_current.y - self.view_prev.y
            self.view_prev.x = self.view_current.x
            self.view_prev.y = self.view_current.y
            self.view_current.x = view_pos[0]
            self.view_current.y = view_pos[1]
            self.view_offset.x = self.view_current.x - self.view_start.x
            self.view_offset.y = self.view_current.y - self.view_start.y

            if local_space__rect is not None:
                self.update_local_space(context, local_space__rect)

        self.dir.x = 0 if self.delta.x==0 else 1 if self.delta.x > 0 else -1
        self.dir.y = 0 if self.delta.y==0 else 1 if self.delta.y > 0 else -1

            # print("Local Current", self.local_current)
            # print("Local Delta", self.local_delta)
            # print("Local Dir", self.local_dir)


    def update_local_space(self, context: Context, local_space__rect: _RectTransform, first_time: bool = False) -> None:
        # Get projected size.
        view_size = local_space__rect.size
        view_zoom = get_node_editor_zoom(context)

        reg_size = view_size * view_zoom

        # Project from View2D to Region.
        top_left, bottom_left, bottom_right, top_right = local_space__rect.coords_rotated
        top_left = get_node_editor_region_coord(context, top_left)
        bottom_left = get_node_editor_region_coord(context, bottom_left)
        bottom_right = get_node_editor_region_coord(context, bottom_right)
        # top_right = get_node_editor_region_coord(context, top_right)

        # Change from region to local coordinates.
        l_co = bottom_left
        l_hor = bottom_right - l_co
        l_ver = top_left - l_co

        a, b = l_hor.x, l_ver.x
        c, d = l_hor.y, l_ver.y

        A_det = a * d - b * c
        if A_det == 0:
            self.error = True
            return

        A = Matrix((
            (a, b), # a b
            (c, d)  # c d
        ))
        A.invert()

        # A_adj = ((d, -b), (-c, a))
        ## k = (1 / A_det)
        ## A = Matrix(((k*d, k*-b), (k*-c, k*a)))

        Q = self.current - l_co

        local_rel_mouse = A @ Q

        local_abs_mouse = Vector((
            local_rel_mouse.x * reg_size.x,
            local_rel_mouse.y * reg_size.y
        ))

        # print("> LocalRelMouse:", local_rel_mouse)
        # print("> LocalAbsMouse:", local_abs_mouse)

        '''
        rotation = local_space__rect.rotation

        view_bbox = local_space__rect.bound_box
        view_bbox_bot_left = view_bbox[1] # Left Bottom corner.
        view_co_bot_left: Vector = local_space__rect.bottom_left
        view_origin = Vector(local_space__rect.origin)
        view_bbox_size = local_space__rect.bound_box_size
        view_size = local_space__rect.size
        view_zoom = get_node_editor_zoom(context)
        # view_zoom_inv = 1 / view_zoom

        reg_mouse = self.current
        reg_pos = get_node_editor_region_coord(context, view_co_bot_left)
        reg_origin = get_node_editor_region_coord(context, view_origin)
        reg_bbox_size = view_bbox_size * view_zoom
        reg_size = view_size * view_zoom

        reg_origin_norm = reg_origin - reg_pos
        reg_mouse_norm = reg_mouse - reg_pos

        if rotation == 0:
            reg_mouse_norm_t = reg_mouse_norm
            reg_size_t = view_size
        else:
            reg_mouse_norm_t = rotate_point(reg_mouse_norm, Vector((0, 0)), -rotation)
            reg_size_t = rotate_point(reg_size, Vector((0, 0)), -rotation)

        rel_mouse = Vector((
            clamp(reg_mouse_norm_t.x / reg_size_t.x),
            clamp(reg_mouse_norm_t.y / reg_size_t.y)
        ))

        # reg_mouse_norm_t === LOCAL COORDINATES... But with error if rotation is present...
        # rel_mouse === RELATIVE LOCAL COORDINATES... Mapped between [0, 1].
        '''

        self.local_rel = local_rel_mouse

        if first_time:
            self.local_start = local_abs_mouse.copy()
            self.local_current = local_abs_mouse.copy()
            self.local_prev = local_abs_mouse.copy()
            self.local_offset = Vector((0, 0))
            self.local_delta = Vector((0, 0))
            self.local_dir = Vector((0, 0))
            self.local_delta_int = Vector((0, 0))
            self.local_delta_acummulative = Vector((0, 0))
        else:
            self.local_prev.x = self.local_current.x
            self.local_prev.y = self.local_current.y
            self.local_current.x = local_abs_mouse.x
            self.local_current.y = local_abs_mouse.y

            self.local_delta.x = local_abs_mouse.x - self.local_prev.x
            self.local_delta.y = local_abs_mouse.y - self.local_prev.y

            cummulative = self.local_delta_acummulative + self.local_delta
            self.local_delta_acummulative.x, self.local_delta_int.x = modf(cummulative.x) # NOTE: CAN CAUSE FLOATINT POINT ROUNDING ERROR.
            self.local_delta_acummulative.y, self.local_delta_int.y = modf(cummulative.y) # NOTE: CAN CAUSE FLOATINT POINT ROUNDING ERROR.

            # self.local_delta = rotate_point(self.local_delta, Vector((0, 0)), local_space__rect.rotation)
            self.local_offset.x = self.local_current.x - self.local_start.x
            self.local_offset.y = self.local_current.y - self.local_start.y

            self.local_dir.x = 0 if self.local_delta.x==0 else 1 if self.local_delta.x > 0 else -1
            self.local_dir.y = 0 if self.local_delta.y==0 else 1 if self.local_delta.y > 0 else -1

        # print(self.local_current, " ----- ", self.local_rel) # " ----- ", reg_size)
        # print("Region Dimensions:", reg_bbox_size)


def get_mouse_pos(event: Event) -> Vector:
    return Vector((event.mouse_region_x, event.mouse_region_y))
