import bpy
from bpy.types import Context, Area
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector


def get_view3d_context(context: Context) -> dict | None:
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return {
                            'window': window,
                            'area': area,
                            'region': region
                        }
    return None


def view3d_set_mode(context: Context, mode: str) -> None:
    view3d_ctx = get_view3d_context(context)
    if view3d_ctx is None:
        return
    with context.temp_override(**view3d_ctx):
        bpy.ops.object.mode_set(mode=mode)


def view3d_point_to_region(context: Context | Area, view3d_point: Vector, default=None) -> Vector:
    ''' context: Context or Area type. '''
    if isinstance(context, Area):
        area = context
        for region in area.regions:
            if region.type == 'WINDOW':
                break
        return location_3d_to_region_2d(region, area.spaces[0].region_3d, view3d_point, default=default)
    else:
        return location_3d_to_region_2d(context.region, context.space_data.region_3d, view3d_point, default=default)
