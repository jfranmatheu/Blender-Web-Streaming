import os
from enum import Enum
from collections import defaultdict
from colorsys import rgb_to_hsv
from uuid import uuid4
from typing import Union, List, Tuple
from functools import wraps
from math import cos, sin, degrees, radians

import gpu
import bpy
from bpy.types import Image
from gpu.types import GPUShader, GPUBatch, GPUTexture
from gpu import state as gpu_state, matrix as gpu_matrix
from gpu_extras.batch import batch_for_shader as new_bat
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector, Matrix, Euler, Quaternion
from gpu.texture import from_image as get_gputex_from_image

from flexspace.ackit import GLOBALS
from flexspace.utils.file import read_file
from flexspace.api.typing import Widget, RectTransform
from flexspace.utils.geometry import FakeRectTransform, Box, rotate_point
from flexspace.paths import Paths


# Assuming the shaders directory structure:
# /shaders
#     /vert
#         ima.vert
#         another.vert
#     /frag
#         ima.frag
#         another.frag

shaders_path = str(GLOBALS.ADDON_SOURCE_PATH / 'lib' / 'shaders')



# ----------------------------------------------------------------

def get_rect_coords(rect) -> dict:
    return {'pos': rect.coords_rotated}

def get_rect_uv_coords(rect) -> dict:
    return {
        'pos': rect.coords_rotated,
        'texco': tex_uv_indices
    }

def get_rect_coords(rect) -> dict:
    return {'pos': rect.coords_rotated}


def get_rect_cage_coords(rect, margin: float = 0) -> dict:
    if margin == 0:
        co = rect.coords_rotated
        return {'pos': (co[0], co[1], co[2], co[3])}

    co = rect.coords
    co_mar = (Vector(co[0]) + Vector((-margin, margin)),
                    Vector(co[1]) + Vector((-margin, -margin)),
                    Vector(co[2]) + Vector((margin, -margin)),
                    Vector(co[3]) + Vector((margin, margin)))
    o = Vector(rect.origin)
    co_mar = tuple(rotate_point(_co, o, rect.rotation) for _co in co_mar)
    return {'pos': co_mar}

def get_cage_coords(x, y, w, h, p) -> dict:
    return {'pos': (
        (x + p, y + h - p),
        (x + p, y + p),
        (x + w - p, y + p),
        (x + w - p, y + h - p)
    )}


# ----------------------------------------------------------------

get_tex_coords = lambda _p, _s: (
    (_p.x,_p.y+_s.y),_p,
    (_p.x+_s.x,_p.y),_p+_s
)
get_rotated_tex_coords = lambda pos, size, origin, angle: tuple(rotate_point(Vector(co), origin, angle).to_tuple() for co in get_tex_coords(pos, size))

tex_uv_indices = ((0,1),(0,0),(1,0),(1,1))
tex_indices = ((0,1,2),(2,3,0))


# ----------------------------------------------------------------

_batch_cache: dict[str, dict[str, GPUBatch]] = defaultdict(dict)

def get_batch_from_cache(data_id: str, graphic_id: str) -> GPUBatch | None:
    return _batch_cache[data_id].get(graphic_id, None)

def set_batch_to_cache(data_id: str, graphic_id: str, batch: GPUBatch) -> None:
    _batch_cache[data_id][graphic_id] = batch

def clear_batch_cache():
    _batch_cache.clear()


# ----------------------------------------------------------------

_gputex_cache: dict[str, GPUTexture] = {}

def get_gputex(image: Image | str) -> GPUBatch | None:
    if isinstance(image, str):
        return get_gputex_from_addon_image(None, image)
    elif isinstance(image, Image):
        if 'uuid' not in image:
            image['uuid'] = uuid4().hex
        if image['uuid'] not in _gputex_cache:
            _gputex_cache[image['uuid']] = get_gputex_from_image(image)
        return _gputex_cache[image['uuid']]
    return None

def get_gputex_from_addon_image(module_name: str | None, filename: str) -> GPUTexture:
    if module_name is None or module_name == '':
        image_path = Paths.LIB_IMAGES(filename)
        idname = f"internal_{filename}"
    else:
        image_path = Paths.MODULES(module_name, 'lib', 'images', filename)
        idname = f"{module_name}_{filename}"
    if idname not in _gputex_cache:
        tmp_image = bpy.data.images.load(image_path)
        _gputex_cache[idname] = get_gputex_from_image(tmp_image)
        bpy.data.images.remove(tmp_image)
        del tmp_image
    return _gputex_cache[idname]

def clear_gputex_cache():
    _gputex_cache.clear()


# ----------------------------------------------------------------

def new_gpush(vertex_id: str, fragment_id: str, lib_id: str) -> GPUShader:
    vertex_filename = os.path.join(shaders_path, "vert", f"{vertex_id.lower()}.vert")
    fragment_filename = os.path.join(shaders_path, "frag", f"{fragment_id.lower()}.frag")
    libcode_filename = os.path.join(shaders_path, "lib", f"{lib_id.lower()}.glsl")
    with open(vertex_filename, "r") as vertex_file, open(fragment_filename, "r") as fragment_file:
        vertex_code = vertex_file.read()
        fragment_code = fragment_file.read()
        lib_code = read_file(libcode_filename, default='')
        return GPUShader(vertex_code, fragment_code, libcode=lib_code)

def set_uniforms(gpush: GPUShader, **uniforms) -> None:
    for name, value in uniforms.items():
        if isinstance(value, (float, Vector, Matrix)):
            gpush.uniform_float(name, value)
        elif isinstance(value, int):
            gpush.uniform_int(name, value)
        elif isinstance(value, (list, tuple)):
            #if isinstance(value[0], (tuple, list, float)):
            gpush.uniform_float(name, value)
            #elif isinstance(value[0], int):
            #    gpush.uniform_int(name, value)
        elif isinstance(value, bool):
            gpush.uniform_bool(name, value)
        elif isinstance(value, (str, Image, GPUTexture)):
            if isinstance(value, (str, Image)):
                gputex = get_gputex(value)
                if gputex is None:
                    continue
            else:
                gputex = value
            gpush.uniform_sampler(name, gputex)
        else:
            gpush.uniform_float(name, value)


class DrawByShaderType:
    @staticmethod
    def TRIS(draw_batch, rect: RectTransform | None = None) -> None:
        if rect is None:
            draw_batch()
            return
        with gpu_matrix.push_pop():
            if rect.rotation == 0:
                gpu_matrix.translate(rect.position.to_tuple())
                gpu_matrix.scale(rect.size.to_tuple())
            else:
                model_view_mat = gpu_matrix.get_model_view_matrix()
                wg_mat = Matrix.LocRotScale(
                    Vector((*rect.origin, 0)),
                    Euler((0, 0, rect.rotation), 'XYZ'),
                    Vector((*(rect.dimensions), 0))
                )

                pivot_displacement = rotate_point((rect.bottom_left - Vector(rect.origin)), Vector((0, 0)), rect.rotation).to_tuple()
                pivot_translation = Matrix.Translation(Vector((*pivot_displacement, 0)))

                # Multiply the matrices to apply translation and rotation
                matrix = model_view_mat @ pivot_translation @ wg_mat

                # Load the resulting matrix
                gpu.matrix.load_matrix(matrix)

            draw_batch()

    @staticmethod
    def POINTS(draw_batch, point_size: float) -> None:
        gpu_state.point_size_set(point_size)
        draw_batch()
        gpu_state.point_size_set(1.0)

    @staticmethod
    def LINES(draw_batch, line_width: float) -> None:
        gpu_state.line_width_set(line_width)
        draw_batch()
        gpu_state.line_width_set(1.0)


def _draw_shader(shader: GPUShader, vert_id: str, shader_type: str, use_dimensions: bool = False):
    # EXAMPLE USAGE: @_draw_shader()def image(graphic_id: str, owner: Widget | None, u_image: Image, u_opacity: bool, input: FakeRectTransform | Box | None = None, dirty: bool | None = None): pass
    def decorator(func):
        @wraps(func)
        def wrapper(graphic_id: str | None, owner: Widget | None, input: Union[FakeRectTransform, Box, Tuple[Vector], List[Vector] | Vector] = None, dirty: bool | str | None = None, point_size: float = 1.0, line_width: float = 1.0, use_line_loop: bool = False, **uniforms):
            ''' Parameters:
                - `graphic_id` : the identifier of the graphic to draw. (for caching purposes) if None then it will work without caching.
                - `owner` : the owner of the graphic, either a Widget or a Box object (for 'TRIS' shader types),
                            but in the case of shader type of 'LINES' or 'POINTS', use mathutils.Vector or tuples or lists.
                - `dirty` : wheter this graphic should be refreshed (aka the coordinates/inputs have changed).
                - `uniforms`: all uniforms for styling. '''
            # --- Resolve dirty state ----------------------------------------------------------------
            if graphic_id is None or owner is None:
                dirty = True # immediate drawing... no caching!
            elif isinstance(dirty, str):
                dirty = owner.dirty or owner.get_state(dirty, True)
                owner.set_state(dirty, False) # Automatically turn off the dirty state.
            elif dirty is None:
                dirty = owner.dirty or dirty

            if not dirty and (batch := get_batch_from_cache(owner.uuid, graphic_id)) is not None:
                # --- Use Cached Batch ----------------------------------------------------------------
                pass
            else:
                # --- Update Batch ----------------------------------------------------------------
                if shader_type == 'ANY':
                    if owner is not None or (input is not None and isinstance(input, (Box, FakeRectTransform))):
                        _shader_type = 'TRIS'
                    elif isinstance(input, Vector):
                        _shader_type = 'POINTS'
                    elif isinstance(input, (list, tuple)):
                        _shader_type = 'LINES' if isinstance(input[0], (list, tuple)) and isinstance(input[0][0], (list, tuple, Vector)) else 'POINTS'
                else:
                    _shader_type = shader_type

                if _shader_type == 'TRIS':
                    # assert isinstance(owner, FakeRectTransform) or owner_is_wg, "WARN! Owner '%r' type not supported for shader '%r' with vert_id '%s' and shader_type '%s" % (owner, func, vert_id, shader_type)
                    # coords = get_tex_coords(pos, size) if angle == 0 else get_rotated_tex_coords(pos, size, origin if origin is not None else pos+size*0.5, angle)
                    if input is None and hasattr(owner, 'rect_transform'):
                        # _coords = owner.rect_transform.coords_rotated # NOTE: new RectTransform will have 'coords' attr with rotated coordinates.
                        _coords = tex_uv_indices # ((-0.5, 0.5), (-0.5, -0.5), (0.5, -0.5), (0.5, 0.5))
                        # if owner.rect_transform.rotation != 0:
                        #     angle = owner.rect_transform.rotation
                        #     o = Vector(owner.rect_transform.pivot)
                        #     _coords = [
                        #         rotate_point(Vector(co), o, angle)
                        #         for co in _coords
                        #     ]
                    elif isinstance(input, (Box, FakeRectTransform)):
                        _coords = input.coords
                    else:
                        raise ValueError("'input' value is invalid! expected None, Box or FakeRectTransform types!", input)
                elif _shader_type == 'POINTS':
                    assert isinstance(input, (Vector, tuple, list))
                    if isinstance(input, Vector):
                        _coords = [input] # fix input.
                    else:
                        _coords = input
                elif _shader_type == 'LINES':
                    assert isinstance(input, (tuple, list))
                    if use_line_loop:
                        _shader_type = 'LINE_LOOP'
                    if isinstance(input[0][0], (float, int)):
                        _coords = [input] # fix input.
                    else:
                        _coords = input
                if vert_id in {'UV', 'IMA'}:
                    _input = {'pos': _coords, 'texco': tex_uv_indices}
                else:
                    _input = {'pos': _coords}
                batch: GPUBatch = new_bat(shader,_shader_type,_input,indices=tex_indices if _shader_type == 'TRIS' else None)
                # batch.program_set(shader)
                if graphic_id is not None and owner is not None:
                    set_batch_to_cache(owner.uuid, graphic_id, batch)

            # --- Draw ----------------------------------------------------------------
            if shader_type == 'TRIS':
                if use_dimensions:
                    if input is None and hasattr(owner, 'rect_transform'):
                        u_dimensions = owner.rect_transform.dimensions
                    elif isinstance(input, (Box, FakeRectTransform)):
                        u_dimensions = input.dimensions
                    shader.uniform_float('u_dimensions', u_dimensions)
            set_uniforms(shader, **uniforms)
            gpu_state.blend_set('ALPHA')
            draw_batch = lambda : batch.draw(shader)
            if shader_type == 'TRIS':
                rect: RectTransform = owner.rect_transform if input is None and hasattr(owner, 'rect_transform') else None
                DrawByShaderType.TRIS(draw_batch, rect)
            elif shader_type == 'POINTS':
                DrawByShaderType.POINTS(draw_batch, point_size)
            elif shader_type in {'LINES', 'LINE_LOOP'}:
                DrawByShaderType.LINES(draw_batch, line_width)
            else:
                draw_batch()
            gpu_state.blend_set('NONE')
        return wrapper
    return decorator
