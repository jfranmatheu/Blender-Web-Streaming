from enum import Enum

from bpy import types as btypes
from bpy.props import PointerProperty
from bpy.utils import register_class

from ._btypes import PropertyBpyTypes


class PointerPropertyTypes(Enum):
    OBJECT = btypes.Object
    MESH = btypes.Mesh
    CAMERA = btypes.Camera
    LIGHT = btypes.Light
    ARMATURE = btypes.Armature
    NODE_TREE = btypes.NodeTree
    NODE_GROUP = btypes.NodeGroup
    BRUSH = btypes.Brush
    IMAGE = btypes.Image
    TEXTURE = btypes.Texture
    # CUSTOM = None

    @staticmethod
    def CUSTOM(name: str, type, **kwargs) -> btypes.PointerProperty:
        ### if 'bl_rna' not in type.__dict__:
        ###     print(f"WARN! {name} PointerProperty type {type} is not registered! {type.__module__}")
        ###     register_class(type)
            ### print("\tRegistering...")
            ### raise RuntimeError(f"{name}'s PointerProperty type {type} is not registered!")
        return PointerProperty(name=name, type=type, **kwargs)

    def __call__(self, name: str = '', **kwargs: dict) -> btypes.PointerProperty:
        if self.value is None:
            if 'type' not in kwargs:
                raise AttributeError("'type' kwarg must be specified to create a - CUSTOM - PointerProperty")
            return PointerProperty(name=name, **kwargs)
        return PointerProperty(type=self.value, name=name, **kwargs)
