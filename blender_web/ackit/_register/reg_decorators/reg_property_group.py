from bpy.types import PropertyGroup
from bpy import types as bpy_types

from enum import Enum

from .._register import BlenderTypes
from ..reg_helpers.help_property import PropertyRegister

from ..property_types import PropertyTypes
from ...globals import GLOBALS


class PGRootTypes(Enum):
    WINDOW_MANAGER = bpy_types.WindowManager
    # TEMPORAL = WINDOW_MANAGER
    SCENE = bpy_types.Scene

    OBJECT = bpy_types.Object
    MESH = bpy_types.Mesh
    LIGHT = bpy_types.Light
    CAMERA = bpy_types.Camera
    IMAGE = bpy_types.Image
    TEXTURE = bpy_types.Texture
    BRUSH = bpy_types.Brush
    ARMATURE = bpy_types.Armature
    ACTION = bpy_types.Action
    CURVE = bpy_types.Curve
    NODE_TREE = bpy_types.NodeTree
    NODE_GROUP = bpy_types.NodeGroup
    GN_GROUP = bpy_types.GeometryNodeGroup
    SPEAKER = bpy_types.Speaker

    ACTION_GROUP = bpy_types.ActionGroup
    ACTION_GROUPS = bpy_types.ActionGroups
    FCURVE = bpy_types.FCurve
    CURVES = bpy_types.Curves
    MODIFIER = bpy_types.Modifier
    CONSTRAINT = bpy_types.Constraint

    def __call__(self, prop_name: str = None) -> PropertyGroup:
        def decorator(decorated_cls):
            decorated_cls.is_root = True
            decorated_cls.bpy_type = self.value
            decorated_cls.prop_name = prop_name
            decorated_cls.data_path = self.name.lower() + '.' + prop_name
            pg_cls = _register_property_group(decorated_cls)
            PropertyRegister(self.value, prop_name if prop_name else GLOBALS.ADDON_MODULE, PropertyTypes.POINTER_CUSTOM(type=pg_cls))
            return pg_cls
        return decorator


def _register_property_group(deco_cls) -> PropertyGroup:
    # from ..reg_types.property_group import PropertyGroup as ACK_PropertyGroup
    idname = GLOBALS.ADDON_MODULE.upper() + '_PG_' + deco_cls.__name__.lower()

    if not hasattr(deco_cls, 'is_root'):
        # Helpful for the AutoCodeGen - '/types.py' generation.
        deco_cls.__name__ = '_' + deco_cls.__name__

    pg_cls = type(
        deco_cls.__name__,
        (PropertyGroup, deco_cls),
        {
            '__annotations__': deco_cls.__annotations__,
            # 'bl_label': deco_cls.bl_label if 'bl_label' in deco_cls else deco_cls.__name__,
            'is_root': hasattr(deco_cls, 'is_root'),
            'bl_idname': idname,
            'original_idname': deco_cls.__name__,
            'original_cls': deco_cls,
        }
    )
    BlenderTypes.PropertyGroup.add_class(pg_cls)
    pg_cls.__module__ = deco_cls.__module__
    deco_cls = pg_cls
    return pg_cls


##########################################################################
##########################################################################
# enum-like-class UTILITY TO REGISTER PROPERTY GROUP CLASSES PER TYPE.
##########################################################################

class PropertyGroupRegister:
    # PropertyGroup added to a root type like Scene, WindowManager or any ID (PG supported) type.
    ROOT = PGRootTypes
    # Child of another PropertyGroup.
    CHILD = _register_property_group
